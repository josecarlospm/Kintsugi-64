#!/usr/bin/env python3
import os
import math
import zlib
import struct

class MeshBuilder:
    def __init__(self):
        self.vertices = []      # list of (x, y, z, r, g, b)
        self.uvs = []           # list of (u, v)
        self.faces = []         # list of lists of (v_idx, vt_idx)
        self.current_obj = None
        self.objects = {}       # name -> list of faces

    def set_object(self, name):
        self.current_obj = name
        if name not in self.objects:
            self.objects[name] = []

    def add_vertex(self, x, y, z, r=128, g=128, b=128):
        self.vertices.append((x, y, z, r/255.0, g/255.0, b/255.0))
        return len(self.vertices)

    def add_uv(self, u, v):
        self.uvs.append((u, v))
        return len(self.uvs)

    def add_face(self, v_indices, uv_indices=None):
        face = []
        for i in range(len(v_indices)):
            uv_idx = uv_indices[i] if uv_indices else None
            face.append((v_indices[i], uv_idx))
        if self.current_obj:
            self.objects[self.current_obj].append(face)
        else:
            self.faces.append(face)

    def add_box(self, name, cx, cy, cz, dx, dy, dz, color=(128, 128, 128), taper_y=1.0, taper_z=1.0, offset_top_z=0.0, uv_rect=(0.0, 0.0, 1.0, 1.0)):
        self.set_object(name)
        r, g, b = color
        
        # Define 8 corners
        v = []
        for dy_sign in [-1, 1]:
            curr_y = cy + dy_sign * (dy / 2.0)
            tx = taper_y if dy_sign > 0 else 1.0
            tz = taper_z if dy_sign > 0 else 1.0
            to_z = offset_top_z if dy_sign > 0 else 0.0
            
            for dz_sign in [-1, 1]:
                curr_z = cz + dz_sign * (dz / 2.0) * tz + to_z
                for dx_sign in [-1, 1]:
                    curr_x = cx + dx_sign * (dx / 2.0) * tx
                    v.append(self.add_vertex(curr_x, curr_y, curr_z, r, g, b))
                    
        # UV mapping based on uv_rect
        u_min, v_min, u_max, v_max = uv_rect
        u0 = self.add_uv(u_min, v_min)
        u1 = self.add_uv(u_max, v_min)
        u2 = self.add_uv(u_max, v_max)
        u3 = self.add_uv(u_min, v_max)
        
        # 6 Faces (Quads) - winding order counter-clockwise from outside
        # Bottom (-Y): 0, 1, 3, 2
        self.add_face([v[0], v[1], v[3], v[2]], [u0, u1, u2, u3])
        # Top (+Y):    4, 6, 7, 5
        self.add_face([v[4], v[6], v[7], v[5]], [u0, u1, u2, u3])
        # Front (+Z):  2, 3, 7, 6
        self.add_face([v[2], v[3], v[7], v[6]], [u0, u1, u2, u3])
        # Back (-Z):   1, 0, 4, 5
        self.add_face([v[1], v[0], v[4], v[5]], [u0, u1, u2, u3])
        # Left (-X):   0, 2, 6, 4
        self.add_face([v[0], v[2], v[6], v[4]], [u0, u1, u2, u3])
        # Right (+X):  3, 1, 5, 7
        self.add_face([v[3], v[1], v[5], v[7]], [u0, u1, u2, u3])

    def add_cylinder(self, name, cx, cy, cz, radius, height, sides=6, color=(128, 128, 128), axis='y', uv_rect=(0.0, 0.0, 1.0, 1.0)):
        self.set_object(name)
        r, g, b = color
        
        bottom_v = []
        top_v = []
        
        for i in range(sides):
            angle = 2.0 * math.pi * i / sides
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            if axis == 'y':
                bx, by, bz = cx + radius * cos_a, cy - height/2, cz + radius * sin_a
                tx, ty, tz = cx + radius * cos_a, cy + height/2, cz + radius * sin_a
            elif axis == 'x':
                bx, by, bz = cx - height/2, cy + radius * cos_a, cz + radius * sin_a
                tx, ty, tz = cx + height/2, cy + radius * cos_a, cz + radius * sin_a
            else: # z axis
                bx, by, bz = cx + radius * cos_a, cy + radius * sin_a, cz - height/2
                tx, ty, tz = cx + radius * cos_a, cy + radius * sin_a, cz + height/2
                
            bottom_v.append(self.add_vertex(bx, by, bz, r, g, b))
            top_v.append(self.add_vertex(tx, ty, tz, r, g, b))
            
        u_min, v_min, u_max, v_max = uv_rect
        u0 = self.add_uv(u_min, v_min)
        u1 = self.add_uv(u_max, v_min)
        u2 = self.add_uv(u_max, v_max)
        u3 = self.add_uv(u_min, v_max)
        
        # Side faces
        for i in range(sides):
            next_i = (i + 1) % sides
            self.add_face([bottom_v[i], bottom_v[next_i], top_v[next_i], top_v[i]], [u0, u1, u2, u3])
            
        # Cap faces
        self.add_face(bottom_v[::-1], [u0]*sides) # bottom cap
        self.add_face(top_v, [u2]*sides)          # top cap

    def add_quad(self, name, vertices_coords, uv_rect=(0.0, 0.0, 1.0, 1.0), color=(128, 128, 128)):
        self.set_object(name)
        r, g, b = color
        
        v_indices = []
        for x, y, z in vertices_coords:
            v_indices.append(self.add_vertex(x, y, z, r, g, b))
            
        u_min, v_min, u_max, v_max = uv_rect
        u0 = self.add_uv(u_min, v_min)
        u1 = self.add_uv(u_max, v_min)
        u2 = self.add_uv(u_max, v_max)
        u3 = self.add_uv(u_min, v_max)
        
        self.add_face(v_indices, [u0, u1, u2, u3])

    def write_obj(self, filepath, mtl_filename=None):
        with open(filepath, 'w') as f:
            f.write("# N64 Asset - Tokyo-3 Underground City Layout\n")
            f.write("# Generated programmatically by N64 3D Graphics Expert\n")
            if mtl_filename:
                f.write(f"mtllib {mtl_filename}\n")
                
            for v in self.vertices:
                f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {v[3]:.4f} {v[4]:.4f} {v[5]:.4f}\n")
                
            for uv in self.uvs:
                f.write(f"vt {uv[0]:.4f} {uv[1]:.4f}\n")
                
            for obj_name, faces in self.objects.items():
                f.write(f"\no {obj_name}\n")
                if mtl_filename:
                    f.write(f"usemtl {obj_name}_mat\n")
                for face in faces:
                    f.write("f")
                    for v_idx, uv_idx in face:
                        if uv_idx:
                            f.write(f" {v_idx}/{uv_idx}")
                        else:
                            f.write(f" {v_idx}")
                    f.write("\n")

    def compile_component(self, object_names):
        triangles = []
        for obj_name in object_names:
            if obj_name not in self.objects:
                continue
            for face in self.objects[obj_name]:
                if len(face) == 3:
                    triangles.append((face[0], face[1], face[2]))
                elif len(face) == 4:
                    triangles.append((face[0], face[1], face[2]))
                    triangles.append((face[0], face[2], face[3]))
                else:
                    for k in range(1, len(face) - 1):
                        triangles.append((face[0], face[k], face[k+1]))
                        
        chunks = []
        pending_triangles = list(triangles)
        
        while pending_triangles:
            current_chunk_verts = []
            current_chunk_tris = []
            
            i = 0
            while i < len(pending_triangles):
                tri = pending_triangles[i]
                
                tri_verts = []
                for v_idx, uv_idx in tri:
                    x, y, z, r, g, b = self.vertices[v_idx - 1]
                    u, v = self.uvs[uv_idx - 1] if uv_idx else (0.0, 0.0)
                    tri_verts.append((x, y, z, u, v))
                    
                new_verts = [v for v in tri_verts if v not in current_chunk_verts]
                
                if len(current_chunk_verts) + len(new_verts) <= 30:
                    for v in new_verts:
                        current_chunk_verts.append(v)
                    idx0 = current_chunk_verts.index(tri_verts[0])
                    idx1 = current_chunk_verts.index(tri_verts[1])
                    idx2 = current_chunk_verts.index(tri_verts[2])
                    current_chunk_tris.append((idx0, idx1, idx2))
                    pending_triangles.pop(i)
                else:
                    i += 1
                    
            if not current_chunk_tris and pending_triangles:
                tri = pending_triangles.pop(0)
                tri_verts = []
                for v_idx, uv_idx in tri:
                    x, y, z, r, g, b = self.vertices[v_idx - 1]
                    u, v = self.uvs[uv_idx - 1] if uv_idx else (0.0, 0.0)
                    tri_verts.append((x, y, z, u, v))
                for v in tri_verts:
                    current_chunk_verts.append(v)
                current_chunk_tris.append((0, 1, 2))
                
            chunks.append((current_chunk_verts, current_chunk_tris))
            
        return chunks

def write_png(width, height, data, filepath):
    raw_data = b""
    for row in data:
        raw_data += b"\x00"  # Filter type 0
        for r, g, b, a in row:
            raw_data += struct.pack("BBBB", r, g, b, a)
    compressed = zlib.compress(raw_data)
    
    png = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png += struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    png += struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", zlib.crc32(b"IDAT" + compressed))
    png += struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
    
    with open(filepath, "wb") as f:
        f.write(png)

def generate_pixels():
    width, height = 64, 32
    pixels = [[(0, 0, 0, 0) for _ in range(width)] for _ in range(height)]
    
    # 1. Ground / Street: dark grey with lines (X: 0-31, Y: 0-15)
    for y in range(0, 16):
        for x in range(0, 32):
            r, g, b, a = 45, 45, 48, 255
            if x == 15 or x == 16:
                if y % 4 < 2:
                    r, g, b = 220, 180, 20
            elif x == 3 or x == 28:
                r, g, b = 200, 200, 200
            elif (x + y) % 5 == 0:
                r, g, b = 38, 38, 41
            pixels[y][x] = (r, g, b, a)
            
    # 2. Building Walls / Windows: light grey concrete with glowing windows (X: 32-63, Y: 0-15)
    for y in range(0, 16):
        for x in range(32, 64):
            r, g, b, a = 110, 115, 125, 255
            col = (x - 32) % 4
            row = y % 4
            if col in [1, 2] and row in [1, 2]:
                if (x + y) % 3 == 0:
                    r, g, b = 255, 220, 80 # yellow
                else:
                    r, g, b = 80, 200, 255 # cyan
            elif col == 0 or row == 0:
                r, g, b = 85, 90, 100
            pixels[y][x] = (r, g, b, a)
            
    # 3. Gate texture: metallic plate with hazard stripes (X: 0-31, Y: 16-31)
    for y in range(16, 32):
        for x in range(0, 32):
            r, g, b, a = 60, 62, 68, 255
            if y in range(28, 32):
                if ((x + y) // 3) % 2 == 0:
                    r, g, b = 220, 180, 20
                else:
                    r, g, b = 15, 15, 15
            elif x in [0, 31] or y in [16, 27]:
                r, g, b = 35, 36, 40
            elif x in [8, 16, 24] or y in [20, 24]:
                r, g, b = 45, 46, 50
            pixels[y][x] = (r, g, b, a)
            
    # 4. Elevator texture: industrial metal grate (X: 32-47, Y: 16-31)
    for y in range(16, 32):
        for x in range(32, 48):
            r, g, b, a = 75, 75, 80, 255
            if (x + y) % 3 == 0 or (x - y) % 3 == 0:
                r, g, b = 40, 40, 42
            if x == 32 or x == 47 or y == 16 or y == 31:
                r, g, b = 30, 30, 32
            pixels[y][x] = (r, g, b, a)
            
    # 5. Citizen texture: humanoid silhouette sprite (X: 48-63, Y: 16-31)
    for y in range(16, 32):
        for x in range(48, 64):
            cx_local = x - 48
            cy_local = y - 16
            
            is_head = (cy_local in [2, 3] and cx_local in range(6, 10))
            is_torso = (cy_local in range(4, 10) and cx_local in range(5, 11))
            is_legs = (cy_local in range(10, 15) and (cx_local in [5, 6] or cx_local in [9, 10]))
            is_arms = (cy_local in range(4, 9) and (cx_local in [3, 4] or cx_local in [11, 12]))
            
            if is_head:
                r, g, b, a = 240, 200, 160, 255
            elif is_torso:
                r, g, b, a = 230, 70, 20, 255
            elif is_legs:
                r, g, b, a = 30, 30, 30, 255
            elif is_arms:
                r, g, b, a = 230, 70, 20, 255
            else:
                r, g, b, a = 0, 0, 0, 0
                
            pixels[y][x] = (r, g, b, a)
            
    return pixels

def rgba32_to_rgba16(r, g, b, a):
    r5 = int(r * 31 / 255) & 0x1F
    g5 = int(g * 31 / 255) & 0x1F
    b5 = int(b * 31 / 255) & 0x1F
    a1 = 1 if a > 127 else 0
    return (r5 << 11) | (g5 << 6) | (b5 << 1) | a1

def main():
    # Texture UV coords in sheet (64x32)
    uv_street = (0.0, 0.0, 0.5, 0.5)
    uv_building = (0.5, 0.0, 1.0, 0.5)
    uv_gate = (0.0, 0.5, 0.5, 1.0)
    uv_elevator = (0.5, 0.5, 0.75, 1.0)
    uv_citizen = (0.75, 0.5, 1.0, 1.0)

    # Colors
    c_street = (45, 45, 48)
    c_sidewalk = (100, 100, 100)
    c_building = (110, 115, 125)
    c_gate = (60, 62, 68)
    c_elevator = (75, 75, 80)
    c_rail = (50, 50, 52)
    c_citizen_lp = (230, 70, 20)
    c_skin = (240, 200, 160)

    builder = MeshBuilder()

    # --- 1. GROUND AND STREETS ---
    # Central Street
    builder.add_box("street_main", cx=0.0, cy=0.01, cz=0.0, dx=4.0, dy=0.02, dz=20.0, color=c_street, uv_rect=uv_street)
    # Sidewalks
    builder.add_box("sidewalk_l", cx=-4.5, cy=0.025, cz=0.0, dx=5.0, dy=0.05, dz=20.0, color=c_sidewalk, uv_rect=uv_street)
    builder.add_box("sidewalk_r", cx=4.5, cy=0.025, cz=0.0, dx=5.0, dy=0.05, dz=20.0, color=c_sidewalk, uv_rect=uv_street)

    # --- 2. BUILDINGS ---
    # Building A (Left Back)
    builder.add_box("building_a", cx=-4.5, cy=3.0, cz=-6.0, dx=2.5, dy=6.0, dz=2.5, color=c_building, uv_rect=uv_building)
    # Building B (Right Back)
    builder.add_box("building_b", cx=4.5, cy=2.0, cz=-4.0, dx=2.0, dy=4.0, dz=3.0, color=c_building, uv_rect=uv_building)
    # Building C (Left Front)
    builder.add_box("building_c", cx=-4.5, cy=2.5, cz=4.0, dx=2.2, dy=5.0, dz=2.2, color=c_building, uv_rect=uv_building)
    # Building D (Right Front)
    builder.add_box("building_d", cx=4.5, cy=3.5, cz=5.0, dx=2.4, dy=7.0, dz=2.4, color=c_building, uv_rect=uv_building)

    # --- 3. GATE (OPENS ABOVE TOKYO-3) ---
    # Gate Left
    builder.add_box("gate_l", cx=-3.0, cy=10.0, cz=0.0, dx=6.0, dy=0.3, dz=6.0, color=c_gate, uv_rect=uv_gate)
    # Gate Right
    builder.add_box("gate_r", cx=3.0, cy=10.0, cz=0.0, dx=6.0, dy=0.3, dz=6.0, color=c_gate, uv_rect=uv_gate)

    # --- 4. ELEVATOR ---
    # Elevator platform base (origin at local base y=0)
    builder.add_box("elevator_platform", cx=0.0, cy=0.05, cz=0.0, dx=3.5, dy=0.1, dz=3.5, color=c_elevator, uv_rect=uv_elevator)
    # Side support rails
    builder.add_cylinder("elevator_rail_l", cx=-1.7, cy=1.5, cz=0.0, radius=0.06, height=3.0, sides=6, color=c_rail, axis='y', uv_rect=uv_elevator)
    builder.add_cylinder("elevator_rail_r", cx=1.7, cy=1.5, cz=0.0, radius=0.06, height=3.0, sides=6, color=c_rail, axis='y', uv_rect=uv_elevator)

    # --- 5. CITIZENS (BILLBOARD AND LOW-POLY) ---
    # Citizen Billboard 1
    # Vertical quad facing Z axis
    builder.add_quad("citizen_bb1", 
                     [(-1.5 - 0.2, 0.05, 2.0), (-1.5 + 0.2, 0.05, 2.0), (-1.5 + 0.2, 0.85, 2.0), (-1.5 - 0.2, 0.85, 2.0)], 
                     uv_rect=uv_citizen, color=c_citizen_lp)
    # Citizen Billboard 2
    builder.add_quad("citizen_bb2", 
                     [(1.5 - 0.2, 0.05, -1.0), (1.5 + 0.2, 0.05, -1.0), (1.5 + 0.2, 0.85, -1.0), (1.5 - 0.2, 0.85, -1.0)], 
                     uv_rect=uv_citizen, color=c_citizen_lp)
                     
    # Citizen Low-poly Humanoid shape
    builder.add_box("citizen_lp_body", cx=2.0, cy=0.4, cz=2.0, dx=0.2, dy=0.4, dz=0.15, color=c_citizen_lp, uv_rect=uv_citizen)
    builder.add_box("citizen_lp_head", cx=2.0, cy=0.7, cz=2.0, dx=0.15, dy=0.15, dz=0.15, color=c_skin, uv_rect=uv_citizen)

    # Write model OBJ and MTL
    os.makedirs("models", exist_ok=True)
    builder.write_obj("models/tokyo3_layout.obj", mtl_filename="tokyo3_layout.mtl")
    
    with open("models/tokyo3_layout.mtl", 'w') as f:
        f.write("# MTL for Tokyo-3 Layout\n\n")
        materials = {
            "street_main": c_street, "sidewalk_l": c_sidewalk, "sidewalk_r": c_sidewalk,
            "building_a": c_building, "building_b": c_building, "building_c": c_building, "building_d": c_building,
            "gate_l": c_gate, "gate_r": c_gate,
            "elevator_platform": c_elevator, "elevator_rail_l": c_rail, "elevator_rail_r": c_rail,
            "citizen_bb1": c_citizen_lp, "citizen_bb2": c_citizen_lp,
            "citizen_lp_body": c_citizen_lp, "citizen_lp_head": c_skin
        }
        for name, color in materials.items():
            r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
            f.write(f"newmtl {name}_mat\nKd {r:.4f} {g:.4f} {b:.4f}\nKa {r*0.5:.4f} {g*0.5:.4f} {b*0.5:.4f}\nKs 0.1 0.1 0.1\nNs 10.0\nillum 2\nmap_Kd tokyo3_texture.png\n\n")

    # Generate PNG texture
    pixels = generate_pixels()
    write_png(64, 32, pixels, "models/tokyo3_texture.png")
    print("Generated Tokyo-3 layout models and textures.")

    # --- COMPILE TO N64 DISPLAY LISTS ---
    os.makedirs("src/assets", exist_ok=True)
    
    c_filepath = "src/assets/tokyo3_assets.c"
    h_filepath = "src/assets/tokyo3_assets.h"

    # Pack texture pixels to u64 array (RGBA16 big endian)
    texture_words = []
    for y in range(32):
        for x in range(0, 64, 4):
            p0 = rgba32_to_rgba16(*pixels[y][x])
            p1 = rgba32_to_rgba16(*pixels[y][x+1])
            p2 = rgba32_to_rgba16(*pixels[y][x+2])
            p3 = rgba32_to_rgba16(*pixels[y][x+3])
            word = (p0 << 48) | (p1 << 32) | (p2 << 16) | p3
            texture_words.append(word)

    tokyo3_components = {
        "ground": ["street_main", "sidewalk_l", "sidewalk_r"],
        "buildings": ["building_a", "building_b", "building_c", "building_d"],
        "gate_left": ["gate_l"],
        "gate_right": ["gate_r"],
        "elevator": ["elevator_platform", "elevator_rail_l", "elevator_rail_r"],
        "citizen_billboard": ["citizen_bb1", "citizen_bb2"],
        "citizen_lowpoly": ["citizen_lp_body", "citizen_lp_head"]
    }

    compiled_data = []
    for comp_name, parts in tokyo3_components.items():
        chunks = builder.compile_component(parts)
        compiled_data.append((f"tokyo3_{comp_name}", chunks))

    # Write header
    with open(h_filepath, 'w') as h_file:
        h_file.write("""#ifndef TOKYO3_ASSETS_H
#define TOKYO3_ASSETS_H

#include <stdint.h>

#ifndef MECH_ASSETS_H
// N64 types if not already defined
typedef union {
    struct {
        int16_t ob[3];      /* x, y, z */
        uint16_t flag;      /* unused */
        int16_t tc[2];      /* s, t */
        uint8_t cn[4];      /* r, g, b, a */
    } v;
} Vtx;

typedef struct {
    uint32_t w0;
    void *w1;
} Gfx;

#define gsSPVertex(vtx, n, v0) { (0x01000000 | (((n) & 0xFF) << 16) | (((v0) & 0xFF) << 8)), (void*)(vtx) }
#define gsSP1Triangle(v0, v1, v2, flag) { (0x05000000 | (((v0) & 0xFF) << 16) | (((v1) & 0xFF) << 8) | ((v2) & 0xFF)), (void*)(0) }
#define gsSPEndDisplayList() { 0xDF000000, (void*)(0) }
#endif

// Tokyo-3 Texture: 64x32 pixels, 16-bit RGBA = 4096 bytes (512 64-bit words)
extern const uint64_t tokyo3_texture[512] __attribute__((aligned(8)));

// Tokyo-3 Component Display Lists
extern const Gfx tokyo3_ground_dl[];
extern const Gfx tokyo3_buildings_dl[];
extern const Gfx tokyo3_gate_left_dl[];
extern const Gfx tokyo3_gate_right_dl[];
extern const Gfx tokyo3_elevator_dl[];
extern const Gfx tokyo3_citizen_billboard_dl[];
extern const Gfx tokyo3_citizen_lowpoly_dl[];

#endif // TOKYO3_ASSETS_H
""")

    # Write source C file
    with open(c_filepath, 'w') as c_file:
        c_file.write('#include "tokyo3_assets.h"\n\n')
        c_file.write("// 64x32 16bpp RGBA Texture Data for Tokyo-3\n")
        c_file.write("__attribute__((aligned(8))) const uint64_t tokyo3_texture[512] = {\n")
        for i in range(0, len(texture_words), 4):
            row_words = [f"0x{w:016X}ULL" for w in texture_words[i:i+4]]
            c_file.write(f"    {', '.join(row_words)},\n")
        c_file.write("};\n\n")

        for comp_name, chunks in compiled_data:
            c_file.write(f"// --- Vertices for {comp_name} ---\n")
            for chunk_idx, (verts, _) in enumerate(chunks):
                c_file.write(f"static const Vtx {comp_name}_vtx_{chunk_idx}[] = {{\n")
                for v in verts:
                    x, y, z, u, v_coord = v
                    # Scale coordinates by 100 for N64 16-bit fixed point coordinates
                    ix = int(round(x * 100.0))
                    iy = int(round(y * 100.0))
                    iz = int(round(z * 100.0))
                    # Scale UV to s10.5 format
                    su = int(round(u * 64.0 * 32.0))
                    tv = int(round((1.0 - v_coord) * 32.0 * 32.0))
                    su = max(0, min(2047, su))
                    tv = max(0, min(1023, tv))
                    c_file.write(f"    {{{{{{ {ix:5d}, {iy:5d}, {iz:5d} }}, 0, {{ {su:5d}, {tv:5d} }}, {{ 255, 255, 255, 255 }} }}}},\n")
                c_file.write("};\n\n")

        for comp_name, chunks in compiled_data:
            c_file.write(f"// --- Display List for {comp_name} ---\n")
            c_file.write(f"const Gfx {comp_name}_dl[] = {{\n")
            for chunk_idx, (verts, tris) in enumerate(chunks):
                num_verts = len(verts)
                c_file.write(f"    gsSPVertex({comp_name}_vtx_{chunk_idx}, {num_verts}, 0),\n")
                for t in tris:
                    c_file.write(f"    gsSP1Triangle({t[0]}, {t[1]}, {t[2]}, 0),\n")
            c_file.write("    gsSPEndDisplayList(),\n")
            c_file.write("};\n\n")

    print(f"Generated C display lists: {c_filepath} and {h_filepath}")

if __name__ == "__main__":
    main()
