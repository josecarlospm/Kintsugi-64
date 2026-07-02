#!/usr/bin/env python3
import os
import sys
import subprocess
import struct

def parse_mtl(mtl_path):
    materials = {}
    current_mat = None
    if not os.path.exists(mtl_path):
        return materials

    with open(mtl_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if parts[0] == 'newmtl':
                current_mat = parts[1]
                materials[current_mat] = {'Kd': [0.5, 0.5, 0.5], 'map_Kd': None}
            elif parts[0] == 'Kd' and current_mat:
                materials[current_mat]['Kd'] = [float(x) for x in parts[1:4]]
            elif parts[0] == 'map_Kd' and current_mat:
                materials[current_mat]['map_Kd'] = parts[1]
    return materials

def parse_obj(obj_path):
    vertices = []      # list of [x, y, z, r, g, b]
    uvs = []           # list of [u, v]
    objects = {}       # name -> list of faces
    current_obj = "default"
    current_mat = None
    mtl_libs = []

    with open(obj_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            cmd = parts[0]

            if cmd == 'mtllib':
                mtl_libs.append(parts[1])
            elif cmd == 'o' or cmd == 'g':
                current_obj = parts[1]
                if current_obj not in objects:
                    objects[current_obj] = []
            elif cmd == 'usemtl':
                current_mat = parts[1]
            elif cmd == 'v':
                coords = [float(x) for x in parts[1:4]]
                # vertex colors might be included in the v line
                colors = [0.5, 0.5, 0.5]
                if len(parts) >= 7:
                    colors = [float(x) for x in parts[4:7]]
                vertices.append(coords + colors + [current_mat])
            elif cmd == 'vt':
                uvs.append([float(x) for x in parts[1:3]])
            elif cmd == 'f':
                face = []
                for p in parts[1:]:
                    subparts = p.split('/')
                    v_idx = int(subparts[0])
                    vt_idx = int(subparts[1]) if len(subparts) > 1 and subparts[1] else None
                    face.append((v_idx, vt_idx, current_mat))
                if current_obj not in objects:
                    objects[current_obj] = []
                objects[current_obj].append(face)

    # Load materials
    materials = {}
    obj_dir = os.path.dirname(obj_path)
    for mtl_lib in mtl_libs:
        mtl_path = os.path.join(obj_dir, mtl_lib)
        materials.update(parse_mtl(mtl_path))

    return vertices, uvs, objects, materials

def triangulate_face(face):
    triangles = []
    # face is list of (v_idx, vt_idx, mat)
    if len(face) < 3:
        return triangles
    v0 = face[0]
    for i in range(1, len(face) - 1):
        triangles.append((v0, face[i], face[i+1]))
    return triangles

def compile_obj(obj_path, out_dir, scale=100.0, tex_w=64, tex_h=32):
    name = os.path.splitext(os.path.basename(obj_path))[0]
    vertices, uvs, objects, materials = parse_obj(obj_path)

    c_path = os.path.join(out_dir, f"{name}.c")
    h_path = os.path.join(out_dir, f"{name}.h")

    h_content = []
    c_content = []

    h_content.append(f"#ifndef ASSET_{name.upper()}_H")
    h_content.append(f"#define ASSET_{name.upper()}_H\n")
    h_content.append("#include <stdint.h>")
    h_content.append("#include <libdragon.h>\n")

    # Define Vtx and Gfx structures compatible with libultra
    h_content.append("""#ifndef VTX_DEFINED
#define VTX_DEFINED
typedef struct {
    int16_t ob[3];   // Position (x, y, z)
    uint16_t flag;   // Flag (always 0)
    int16_t tc[2];   // Texture coordinates (s, t)
    uint8_t cn[4];   // Color/Normal (r, g, b, a)
} Vtx_t;

typedef union {
    Vtx_t v;
    long long force_structure_alignment;
} Vtx;
#endif

#ifndef GFX_DEFINED
#define GFX_DEFINED
typedef struct {
    uint32_t w0;
    uint32_t w1;
} Gfx;
#endif

// Display list command helper macros
#define gsSPVertex(vaddr, count, start) { 0x01000000 | ((count) << 16) | (start), (uint32_t)(uintptr_t)(vaddr) }
#define gsSP1Triangle(v0, v1, v2, flag) { 0x05000000, ((v0) << 16) | ((v1) << 8) | (v2) }
#define gsSPEndDisplayList() { 0xDF000000, 0 }
""")

    c_content.append(f'#include "{name}.h"\n')

    for obj_name, faces in objects.items():
        if not faces:
            continue
        
        # Triangulate all faces
        triangles = []
        for face in faces:
            triangles.extend(triangulate_face(face))
            
        if not triangles:
            continue

        # Split triangles into chunks of at most 32 unique vertices
        chunks = []
        current_chunk_verts = []
        current_chunk_tris = []
        
        for tri in triangles:
            # tri is ((v0, vt0, mat0), (v1, vt1, mat1), (v2, vt2, mat2))
            # Determine which vertices of the triangle are not in current_chunk_verts
            new_verts = []
            for v in tri:
                if v not in current_chunk_verts:
                    new_verts.append(v)
            
            if len(current_chunk_verts) + len(new_verts) <= 32:
                current_chunk_verts.extend(new_verts)
                current_chunk_tris.append(tri)
            else:
                # Save current chunk
                chunks.append((current_chunk_verts, current_chunk_tris))
                # Start new chunk
                current_chunk_verts = list(tri)
                current_chunk_tris = [tri]
                
        if current_chunk_verts:
            chunks.append((current_chunk_verts, current_chunk_tris))

        # Write the chunk vertex arrays and build display lists
        dl_commands = []
        
        for chunk_idx, (chunk_verts, chunk_tris) in enumerate(chunks):
            vtx_array_name = f"{name}_{obj_name}_chunk{chunk_idx}_vtx"
            c_content.append(f"static Vtx {vtx_array_name}[] __attribute__((aligned(8))) = {{")
            
            for v in chunk_verts:
                v_idx, vt_idx, mat = v
                # Obj vertices are 1-indexed, handle potential negative index
                v_data = vertices[v_idx - 1]
                x = int(v_data[0] * scale)
                y = int(v_data[1] * scale)
                z = int(v_data[2] * scale)
                
                # Colors
                r, g, b = v_data[3:6]
                if mat in materials:
                    r, g, b = materials[mat]['Kd']
                
                ri = int(r * 255)
                gi = int(g * 255)
                bi = int(b * 255)
                
                # UVs
                s, t = 0, 0
                if vt_idx is not None and vt_idx > 0 and vt_idx <= len(uvs):
                    uv = uvs[vt_idx - 1]
                    s = int(uv[0] * tex_w * 32)
                    t = int((1.0 - uv[1]) * tex_h * 32)
                    
                c_content.append(f"    {{{{{{ {x}, {y}, {z} }}, 0, {{ {s}, {t} }}, {{ {ri}, {gi}, {bi}, 255 }}}}}},")
                
            c_content.append("};\n")
            
            # Add gsSPVertex command to load these vertices
            dl_commands.append(f"    gsSPVertex({vtx_array_name}, {len(chunk_verts)}, 0),")
            
            # Map triangles to local vertex indices in chunk_verts
            for tri in chunk_tris:
                i0 = chunk_verts.index(tri[0])
                i1 = chunk_verts.index(tri[1])
                i2 = chunk_verts.index(tri[2])
                dl_commands.append(f"    gsSP1Triangle({i0}, {i1}, {i2}, 0),")

        dl_commands.append("    gsSPEndDisplayList()")
        
        dl_name = f"{name}_{obj_name}_dl"
        h_content.append(f"extern Gfx {dl_name}[];")
        
        c_content.append(f"Gfx {dl_name}[] __attribute__((aligned(8))) = {{")
        c_content.extend(dl_commands)
        c_content.append("};\n")

    h_content.append(f"\n#endif // ASSET_{name.upper()}_H")

    with open(c_path, 'w') as f:
        f.write("\n".join(c_content))
    with open(h_path, 'w') as f:
        f.write("\n".join(h_content))
    print(f"Generated C/H asset for OBJ: {obj_path} -> {c_path}, {h_path}")

def compile_png(png_path, out_dir):
    name = os.path.splitext(os.path.basename(png_path))[0]
    sprite_path = os.path.join(out_dir, f"{name}.sprite")
    
    # Check if mksprite is in docker or local
    # We will run mksprite through Docker since that's where the toolchain is.
    cwd = os.getcwd()
    # Normalize paths for docker volume mount
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{cwd}:/libdragon",
        "-u", f"{os.getuid()}:{os.getgid()}",
        "anacierdem/libdragon:latest",
        "mksprite", "16",
        # Convert host path to container path by stripping cwd prefix
        png_path.replace(cwd + "/", ""),
        sprite_path.replace(cwd + "/", "")
    ]
    
    print(f"Running mksprite via Docker for {png_path}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running mksprite: {res.stderr}")
        return False
        
    if not os.path.exists(sprite_path):
        print(f"Error: Sprite file not generated at {sprite_path}")
        return False
        
    # Read binary sprite data
    with open(sprite_path, 'rb') as f:
        sprite_data = f.read()
        
    # Delete temporary .sprite file
    os.remove(sprite_path)
    
    # Generate C and H files
    c_path = os.path.join(out_dir, f"{name}_sprite.c")
    h_path = os.path.join(out_dir, f"{name}_sprite.h")
    
    h_content = []
    h_content.append(f"#ifndef ASSET_{name.upper()}_SPRITE_H")
    h_content.append(f"#define ASSET_{name.upper()}_SPRITE_H\n")
    h_content.append("#include <stdint.h>")
    h_content.append("#include <libdragon.h>\n")
    h_content.append(f"extern const uint8_t {name}_sprite_data[] __attribute__((aligned(8)));")
    h_content.append(f"#define {name}_sprite ((sprite_t *){name}_sprite_data)\n")
    h_content.append(f"#endif // ASSET_{name.upper()}_SPRITE_H")
    
    c_content = []
    c_content.append(f'#include "{name}_sprite.h"\n')
    c_content.append(f"const uint8_t {name}_sprite_data[] __attribute__((aligned(8))) = {{")
    
    # format bytes as 12 hex values per line
    for i in range(0, len(sprite_data), 12):
        chunk = sprite_data[i:i+12]
        hex_strs = [f"0x{b:02X}" for b in chunk]
        c_content.append("    " + ", ".join(hex_strs) + ",")
        
    c_content.append("};\n")
    
    with open(c_path, 'w') as f:
        f.write("\n".join(c_content))
    with open(h_path, 'w') as f:
        f.write("\n".join(h_content))
        
    print(f"Generated C/H asset for PNG: {png_path} -> {c_path}, {h_path}")
    return True

def main():
    models_dir = "models"
    out_dir = "src/assets"
    
    os.makedirs(out_dir, exist_ok=True)
    
    # Find and compile OBJ files
    obj_files = []
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            if f.endswith(".obj"):
                obj_files.append(os.path.join(models_dir, f))
                
    for obj in obj_files:
        compile_obj(obj, out_dir)
        
    # Find and compile PNG files
    png_files = []
    if os.path.exists(models_dir):
        for f in os.listdir(models_dir):
            if f.endswith(".png"):
                png_files.append(os.path.join(models_dir, f))
                
    for png in png_files:
        compile_png(png, out_dir)
        
    # Write a general include header src/assets.h for easy access
    assets_h_path = "src/assets.h"
    assets_h = []
    assets_h.append("#ifndef ASSETS_H")
    assets_h.append("#define ASSETS_H\n")
    
    for obj in obj_files:
        name = os.path.splitext(os.path.basename(obj))[0]
        assets_h.append(f'#include "assets/{name}.h"')
        
    for png in png_files:
        name = os.path.splitext(os.path.basename(png))[0]
        assets_h.append(f'#include "assets/{name}_sprite.h"')
        
    assets_h.append("\n#endif // ASSETS_H")
    
    with open(assets_h_path, 'w') as f:
        f.write("\n".join(assets_h))
    print(f"Generated master header: {assets_h_path}")

if __name__ == "__main__":
    main()
