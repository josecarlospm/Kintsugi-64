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

    def write_obj(self, filepath, mtl_filename=None):
        with open(filepath, 'w') as f:
            f.write("# N64 Asset - Low Poly (<500 tris)\n")
            f.write("# Generated programmatically by N64 3D Graphics Expert\n")
            if mtl_filename:
                f.write(f"mtllib {mtl_filename}\n")
                
            # Write vertices with colors (Wavefront OBJ extension: v x y z r g b)
            for v in self.vertices:
                f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {v[3]:.4f} {v[4]:.4f} {v[5]:.4f}\n")
                
            # Write UVs
            for uv in self.uvs:
                f.write(f"vt {uv[0]:.4f} {uv[1]:.4f}\n")
                
            # Write objects/groups
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
        # Gather and triangulate all faces
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
                    # General fan triangulation
                    for k in range(1, len(face) - 1):
                        triangles.append((face[0], face[k], face[k+1]))
                        
        # Partition into chunks of max 30 unique vertices to fit TMEM / RSP cache
        chunks = []
        pending_triangles = list(triangles)
        
        while pending_triangles:
            current_chunk_verts = []
            current_chunk_tris = []
            
            i = 0
            while i < len(pending_triangles):
                tri = pending_triangles[i]
                
                # Resolve vertices
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
                # Force-add the first pending triangle to avoid infinite loop
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
        raw_data += b"\x00"  # Filter type 0 (None)
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
    pixels = [[(0, 0, 0, 255) for _ in range(width)] for _ in range(height)]
    
    # 1. Main Armor (X: 0-31, Y: 0-15)
    for y in range(0, 16):
        for x in range(0, 32):
            r, g, b = 50, 55, 65
            if x == 0 or x == 31 or y == 0 or y == 15:
                r, g, b = 30, 33, 40
            elif x == 1 or y == 1:
                r, g, b = 70, 75, 85
            if (x in [3, 28] and y in [3, 12]):
                r, g, b = 90, 90, 95
            pixels[y][x] = (r, g, b, 255)
            
    # 2. Secondary Armor (X: 32-63, Y: 0-15)
    for y in range(0, 16):
        for x in range(32, 64):
            r, g, b = 90, 100, 115
            if x == 32 or x == 63 or y == 0 or y == 15:
                r, g, b = 60, 67, 77
            elif x == 48 or y == 8:
                r, g, b = 60, 67, 77
            elif (x in range(36, 40) and y in range(4, 7)):
                r, g, b = 220, 180, 20
            pixels[y][x] = (r, g, b, 255)
            
    # 3. Hazard Stripes (X: 0-31, Y: 16-31)
    for y in range(16, 32):
        for x in range(0, 32):
            if ((x + y) // 4) % 2 == 0:
                r, g, b = 220, 180, 20
            else:
                r, g, b = 15, 15, 15
            if x == 0 or x == 31 or y == 16 or y == 31:
                r, g, b = 10, 10, 10
            pixels[y][x] = (r, g, b, 255)
            
    # 4. Visor / Glow (X: 32-47, Y: 16-31)
    for y in range(16, 32):
        for x in range(32, 48):
            dist_to_center = abs(y - 23.5)
            if dist_to_center < 2.0:
                r, g, b = 255, 60, 10
            elif dist_to_center < 4.0:
                r, g, b = 200, 30, 0
            elif dist_to_center < 6.0:
                r, g, b = 100, 10, 0
            else:
                r, g, b = 30, 30, 35
            if x == 32 or x == 47 or y == 16 or y == 31:
                r, g, b = 15, 15, 15
            pixels[y][x] = (r, g, b, 255)
            
    # 5. Mechanical Parts / Gunmetal (X: 48-63, Y: 16-31)
    for y in range(16, 32):
        for x in range(48, 64):
            r, g, b = 45, 45, 48
            if y % 3 == 0:
                r, g, b = 20, 20, 22
            elif (y - 1) % 3 == 0:
                r, g, b = 65, 65, 70
            if x == 48 or x == 63 or y == 16 or y == 31:
                r, g, b = 30, 30, 32
            pixels[y][x] = (r, g, b, 255)
            
    return pixels

def rgba32_to_rgba16(r, g, b, a):
    r5 = int(r * 31 / 255) & 0x1F
    g5 = int(g * 31 / 255) & 0x1F
    b5 = int(b * 31 / 255) & 0x1F
    a1 = 1 if a > 127 else 0
    return (r5 << 11) | (g5 << 6) | (b5 << 1) | a1

def main():
    # --- TEXTURE CONFIGURATION ---
    # UV sub-regions in the 64x32 texture sheet
    uv_main_armor = (0.0, 0.0, 0.5, 0.5)
    uv_sec_armor  = (0.5, 0.0, 1.0, 0.5)
    uv_hazard     = (0.0, 0.5, 0.5, 1.0)
    uv_glow       = (0.5, 0.5, 0.75, 1.0)
    uv_metal      = (0.75, 0.5, 1.0, 1.0)
    
    # 3D Mech colors
    c_main = (50, 55, 65)
    c_sec = (90, 100, 115)
    c_visor = (255, 40, 0)
    c_joint = (80, 80, 80)
    c_gun = (40, 40, 40)
    c_accent = (220, 180, 20)

    # --- 1. GENERATE MECH PROTOTYPE MODEL ---
    mech = MeshBuilder()
    
    # HEAD (Y: 4.0 to 4.6)
    mech.add_box("head_main", cx=0.0, cy=4.3, cz=0.0, dx=0.4, dy=0.4, dz=0.4, color=c_main, taper_y=0.85, uv_rect=uv_main_armor)
    mech.add_box("head_visor", cx=0.0, cy=4.35, cz=0.21, dx=0.3, dy=0.12, dz=0.08, color=c_visor, uv_rect=uv_glow)
    mech.add_box("head_antenna_l", cx=-0.22, cy=4.5, cz=-0.05, dx=0.05, dy=0.3, dz=0.05, color=c_accent, uv_rect=uv_hazard)
    mech.add_box("head_antenna_r", cx=0.22, cy=4.5, cz=-0.05, dx=0.05, dy=0.3, dz=0.05, color=c_accent, uv_rect=uv_hazard)
    
    # TORSO (Y: 2.6 to 4.0)
    mech.add_box("torso_upper", cx=0.0, cy=3.6, cz=0.0, dx=1.1, dy=0.6, dz=0.8, color=c_main, taper_y=1.2, offset_top_z=0.1, uv_rect=uv_main_armor)
    mech.add_box("torso_lower", cx=0.0, cy=3.0, cz=-0.05, dx=0.8, dy=0.6, dz=0.7, color=c_sec, taper_y=0.8, uv_rect=uv_sec_armor)
    mech.add_box("backpack", cx=0.0, cy=3.5, cz=-0.5, dx=0.7, dy=0.8, dz=0.3, color=c_gun, uv_rect=uv_metal)
    mech.add_box("thruster_l", cx=-0.25, cy=3.0, cz=-0.6, dx=0.18, dy=0.3, dz=0.18, color=c_accent, uv_rect=uv_metal)
    mech.add_box("thruster_r", cx=0.25, cy=3.0, cz=-0.6, dx=0.18, dy=0.3, dz=0.18, color=c_accent, uv_rect=uv_metal)

    # PELVIS / HIPS (Y: 2.2 to 2.6)
    mech.add_box("hips", cx=0.0, cy=2.4, cz=-0.05, dx=0.7, dy=0.3, dz=0.6, color=c_joint, uv_rect=uv_metal)

    # LEGS
    mech.add_cylinder("hip_joint_l", cx=-0.45, cy=2.4, cz=-0.05, radius=0.15, height=0.2, sides=6, color=c_joint, axis='x', uv_rect=uv_metal)
    mech.add_cylinder("hip_joint_r", cx=0.45, cy=2.4, cz=-0.05, radius=0.15, height=0.2, sides=6, color=c_joint, axis='x', uv_rect=uv_metal)
    mech.add_box("thigh_l", cx=-0.5, cy=1.8, cz=0.0, dx=0.3, dy=0.8, dz=0.35, color=c_main, taper_y=0.8, uv_rect=uv_main_armor)
    mech.add_box("thigh_r", cx=0.5, cy=1.8, cz=0.0, dx=0.3, dy=0.8, dz=0.35, color=c_main, taper_y=0.8, uv_rect=uv_main_armor)
    mech.add_cylinder("knee_l", cx=-0.5, cy=1.35, cz=0.0, radius=0.14, height=0.25, sides=6, color=c_joint, axis='x', uv_rect=uv_metal)
    mech.add_cylinder("knee_r", cx=0.5, cy=1.35, cz=0.0, radius=0.14, height=0.25, sides=6, color=c_joint, axis='x', uv_rect=uv_metal)
    mech.add_box("calf_l", cx=-0.5, cy=0.8, cz=-0.05, dx=0.34, dy=0.9, dz=0.4, color=c_sec, taper_y=1.2, offset_top_z=-0.05, uv_rect=uv_sec_armor)
    mech.add_box("calf_r", cx=0.5, cy=0.8, cz=-0.05, dx=0.34, dy=0.9, dz=0.4, color=c_sec, taper_y=1.2, offset_top_z=-0.05, uv_rect=uv_sec_armor)
    mech.add_box("foot_l", cx=-0.5, cy=0.2, cz=0.1, dx=0.42, dy=0.3, dz=0.6, color=c_main, taper_y=0.7, offset_top_z=0.1, uv_rect=uv_main_armor)
    mech.add_box("foot_r", cx=0.5, cy=0.2, cz=0.1, dx=0.42, dy=0.3, dz=0.6, color=c_main, taper_y=0.7, offset_top_z=0.1, uv_rect=uv_main_armor)

    # ARMS
    mech.add_box("shoulder_pad_l", cx=-0.75, cy=3.7, cz=0.05, dx=0.4, dy=0.4, dz=0.5, color=c_sec, taper_y=0.8, uv_rect=uv_sec_armor)
    mech.add_box("shoulder_pad_r", cx=0.75, cy=3.7, cz=0.05, dx=0.4, dy=0.4, dz=0.5, color=c_sec, taper_y=0.8, uv_rect=uv_sec_armor)
    mech.add_box("upper_arm_l", cx=-0.75, cy=3.2, cz=0.05, dx=0.25, dy=0.6, dz=0.25, color=c_joint, uv_rect=uv_metal)
    mech.add_box("upper_arm_r", cx=0.75, cy=3.2, cz=0.05, dx=0.25, dy=0.6, dz=0.25, color=c_joint, uv_rect=uv_metal)
    mech.add_cylinder("elbow_l", cx=-0.75, cy=2.8, cz=0.05, radius=0.12, height=0.22, sides=6, color=c_joint, axis='y', uv_rect=uv_metal)
    mech.add_cylinder("elbow_r", cx=0.75, cy=2.8, cz=0.05, radius=0.12, height=0.22, sides=6, color=c_joint, axis='y', uv_rect=uv_metal)
    
    # Forearms (with mounting points for weapon attachments)
    mech.add_box("forearm_l", cx=-0.8, cy=2.2, cz=0.15, dx=0.3, dy=0.8, dz=0.35, color=c_main, uv_rect=uv_main_armor)
    mech.add_cylinder("laser_cannon", cx=-0.8, cy=1.7, cz=0.25, radius=0.08, height=0.5, sides=6, color=c_gun, axis='y', uv_rect=uv_metal)
    mech.add_box("forearm_r", cx=0.8, cy=2.2, cz=0.15, dx=0.3, dy=0.8, dz=0.35, color=c_main, uv_rect=uv_main_armor)
    mech.add_box("rocket_pod", cx=0.85, cy=2.4, cz=0.2, dx=0.25, dy=0.3, dz=0.5, color=c_gun, uv_rect=uv_metal)
    mech.add_box("rocket_tubes", cx=0.85, cy=2.4, cz=0.46, dx=0.2, dy=0.2, dz=0.02, color=c_visor, uv_rect=uv_glow)

    os.makedirs("models", exist_ok=True)
    mech.write_obj("models/mech_prototype.obj", mtl_filename="mech_prototype.mtl")
    
    # Write the MTL for viewport coloring
    with open("models/mech_prototype.mtl", 'w') as f:
        f.write("# MTL for Mech Prototype\n\n")
        materials = {
            "head_main": c_main, "head_visor": c_visor, "head_antenna_l": c_accent, "head_antenna_r": c_accent,
            "torso_upper": c_main, "torso_lower": c_sec, "backpack": c_gun, "thruster_l": c_accent, "thruster_r": c_accent,
            "hips": c_joint, "hip_joint_l": c_joint, "hip_joint_r": c_joint,
            "thigh_l": c_main, "thigh_r": c_main, "knee_l": c_joint, "knee_r": c_joint,
            "calf_l": c_sec, "calf_r": c_sec, "foot_l": c_main, "foot_r": c_main,
            "shoulder_pad_l": c_sec, "shoulder_pad_r": c_sec, "upper_arm_l": c_joint, "upper_arm_r": c_joint,
            "elbow_l": c_joint, "elbow_r": c_joint, "forearm_l": c_main, "laser_cannon": c_gun,
            "forearm_r": c_main, "rocket_pod": c_gun, "rocket_tubes": c_visor
        }
        for name, color in materials.items():
            r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
            f.write(f"newmtl {name}_mat\nKd {r:.4f} {g:.4f} {b:.4f}\nKa {r*0.5:.4f} {g*0.5:.4f} {b*0.5:.4f}\nKs 0.1 0.1 0.1\nNs 10.0\nillum 2\nmap_Kd mech_texture.png\n\n")

    # --- 2. GENERATE WEAPON: ENERGY RIFLE ---
    rifle = MeshBuilder()
    # local coordinates centered around weapon grip/origin
    rifle.add_box("rifle_body", cx=0.0, cy=0.0, cz=0.0, dx=0.15, dy=0.25, dz=0.7, color=c_gun, uv_rect=uv_metal)
    rifle.add_cylinder("rifle_barrel", cx=0.0, cy=0.08, cz=0.6, radius=0.04, height=0.7, sides=6, color=c_joint, axis='z', uv_rect=uv_metal)
    rifle.add_cylinder("rifle_scope", cx=0.0, cy=0.22, cz=0.0, radius=0.03, height=0.3, sides=6, color=c_sec, axis='z', uv_rect=uv_glow)
    rifle.add_box("rifle_mag", cx=0.0, cy=-0.25, cz=0.1, dx=0.1, dy=0.3, dz=0.18, color=c_accent, uv_rect=uv_hazard)
    rifle.add_box("rifle_stock", cx=0.0, cy=-0.12, cz=-0.4, dx=0.08, dy=0.2, dz=0.25, color=c_main, uv_rect=uv_main_armor)
    
    rifle.write_obj("models/weapon_energy_rifle.obj", mtl_filename="weapon_energy_rifle.mtl")
    
    with open("models/weapon_energy_rifle.mtl", 'w') as f:
        f.write("# MTL for Energy Rifle\n\n")
        materials = {"rifle_body": c_gun, "rifle_barrel": c_joint, "rifle_scope": c_sec, "rifle_mag": c_accent, "rifle_stock": c_main}
        for name, color in materials.items():
            r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
            f.write(f"newmtl {name}_mat\nKd {r:.4f} {g:.4f} {b:.4f}\nKa {r*0.5:.4f} {g*0.5:.4f} {b*0.5:.4f}\nKs 0.1 0.1 0.1\nNs 10.0\nillum 2\nmap_Kd mech_texture.png\n\n")

    # --- 3. GENERATE WEAPON: ROCKET LAUNCHER ---
    launcher = MeshBuilder()
    # Pod body
    launcher.add_box("launcher_body", cx=0.0, cy=0.0, cz=0.0, dx=0.35, dy=0.35, dz=0.8, color=c_gun, uv_rect=uv_metal)
    # 4 tubes (inset in front)
    launcher.add_cylinder("launcher_t1", cx=-0.08, cy=0.08, cz=0.4, radius=0.06, height=0.04, sides=6, color=c_visor, axis='z', uv_rect=uv_glow)
    launcher.add_cylinder("launcher_t2", cx=0.08, cy=0.08, cz=0.4, radius=0.06, height=0.04, sides=6, color=c_visor, axis='z', uv_rect=uv_glow)
    launcher.add_cylinder("launcher_t3", cx=-0.08, cy=-0.08, cz=0.4, radius=0.06, height=0.04, sides=6, color=c_visor, axis='z', uv_rect=uv_glow)
    launcher.add_cylinder("launcher_t4", cx=0.08, cy=-0.08, cz=0.4, radius=0.06, height=0.04, sides=6, color=c_visor, axis='z', uv_rect=uv_glow)
    # Mount bracket
    launcher.add_box("launcher_bracket", cx=0.12, cy=0.0, cz=-0.2, dx=0.12, dy=0.15, dz=0.3, color=c_sec, uv_rect=uv_sec_armor)
    
    launcher.write_obj("models/weapon_rocket_launcher.obj", mtl_filename="weapon_rocket_launcher.mtl")
    
    with open("models/weapon_rocket_launcher.mtl", 'w') as f:
        f.write("# MTL for Rocket Launcher\n\n")
        materials = {"launcher_body": c_gun, "launcher_t1": c_visor, "launcher_t2": c_visor, "launcher_t3": c_visor, "launcher_t4": c_visor, "launcher_bracket": c_sec}
        for name, color in materials.items():
            r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
            f.write(f"newmtl {name}_mat\nKd {r:.4f} {g:.4f} {b:.4f}\nKa {r*0.5:.4f} {g*0.5:.4f} {b*0.5:.4f}\nKs 0.1 0.1 0.1\nNs 10.0\nillum 2\nmap_Kd mech_texture.png\n\n")

    # --- 4. GENERATE PNG TEXTURE FILE ---
    pixels = generate_pixels()
    write_png(64, 32, pixels, "models/mech_texture.png")
    print("Generated textures and low-poly models (OBJ/MTL).")

    # --- 5. COMPILE ALL TO N64 C DISPLAY LISTS ---
    os.makedirs("src/assets", exist_ok=True)
    
    c_filepath = "src/assets/mech_assets.c"
    h_filepath = "src/assets/mech_assets.h"
    
    # 5.1 Create Texture u64 array (Big-Endian packing)
    texture_words = []
    for y in range(32):
        for x in range(0, 64, 4):
            p0 = rgba32_to_rgba16(*pixels[y][x])
            p1 = rgba32_to_rgba16(*pixels[y][x+1])
            p2 = rgba32_to_rgba16(*pixels[y][x+2])
            p3 = rgba32_to_rgba16(*pixels[y][x+3])
            word = (p0 << 48) | (p1 << 32) | (p2 << 16) | p3
            texture_words.append(word)
            
    # Compile parts of Mech into components
    mech_components = {
        "head": ["head_main", "head_visor", "head_antenna_l", "head_antenna_r"],
        "torso": ["torso_upper", "torso_lower", "backpack", "thruster_l", "thruster_r"],
        "hips": ["hips", "hip_joint_l", "hip_joint_r"],
        "thigh_l": ["thigh_l"],
        "thigh_r": ["thigh_r"],
        "calf_l": ["knee_l", "calf_l"],
        "calf_r": ["knee_r", "calf_r"],
        "foot_l": ["foot_l"],
        "foot_r": ["foot_r"],
        "upper_arm_l": ["shoulder_pad_l", "upper_arm_l", "elbow_l"],
        "upper_arm_r": ["shoulder_pad_r", "upper_arm_r", "elbow_r"],
        "forearm_l": ["forearm_l", "laser_cannon"],
        "forearm_r": ["forearm_r", "rocket_pod", "rocket_tubes"]
    }
    
    rifle_components = {
        "rifle": ["rifle_body", "rifle_barrel", "rifle_scope", "rifle_mag", "rifle_stock"]
    }
    
    launcher_components = {
        "launcher": ["launcher_body", "launcher_t1", "launcher_t2", "launcher_t3", "launcher_t4", "launcher_bracket"]
    }
    
    # Gather compiled components
    compiled_data = [] # list of (comp_name, chunks)
    
    for comp_name, parts in mech_components.items():
        chunks = mech.compile_component(parts)
        compiled_data.append((f"mech_{comp_name}", chunks))
        
    for comp_name, parts in rifle_components.items():
        chunks = rifle.compile_component(parts)
        compiled_data.append((f"weapon_energy_rifle", chunks))
        
    for comp_name, parts in launcher_components.items():
        chunks = launcher.compile_component(parts)
        compiled_data.append((f"weapon_rocket_launcher", chunks))
        
    # --- WRITE HEADER FILE ---
    with open(h_filepath, 'w') as h_file:
        h_file.write("""#ifndef MECH_ASSETS_H
#define MECH_ASSETS_H

#include <stdint.h>

// Nintendo 64 Vertex structure
typedef union {
    struct {
        int16_t ob[3];      /* x, y, z */
        uint16_t flag;      /* unused */
        int16_t tc[2];      /* s, t */
        uint8_t cn[4];      /* r, g, b, a */
    } v;
} Vtx;

// Nintendo 64 Graphics Display List Command structure
typedef struct {
    uint32_t w0;
    void *w1;
} Gfx;

// Graphics commands macros for display lists initializers
#define gsSPVertex(vtx, n, v0) { (0x01000000 | (((n) & 0xFF) << 16) | (((v0) & 0xFF) << 8)), (void*)(vtx) }
#define gsSP1Triangle(v0, v1, v2, flag) { (0x05000000 | (((v0) & 0xFF) << 16) | (((v1) & 0xFF) << 8) | ((v2) & 0xFF)), (void*)(0) }
#define gsSPEndDisplayList() { 0xDF000000, (void*)(0) }

// Texture: 64x32 pixels, 16-bit RGBA = 4096 bytes (512 64-bit words)
// Aligned to 8 bytes for N64 RDP/TMEM DMA transfer.
extern const uint64_t mech_skin_texture[512] __attribute__((aligned(8)));

// Mech Component Display Lists
extern const Gfx mech_head_dl[];
extern const Gfx mech_torso_dl[];
extern const Gfx mech_hips_dl[];
extern const Gfx mech_thigh_l_dl[];
extern const Gfx mech_thigh_r_dl[];
extern const Gfx mech_calf_l_dl[];
extern const Gfx mech_calf_r_dl[];
extern const Gfx mech_foot_l_dl[];
extern const Gfx mech_foot_r_dl[];
extern const Gfx mech_upper_arm_l_dl[];
extern const Gfx mech_upper_arm_r_dl[];
extern const Gfx mech_forearm_l_dl[];
extern const Gfx mech_forearm_r_dl[];

// Weapon Attachment Display Lists
extern const Gfx weapon_energy_rifle_dl[];
extern const Gfx weapon_rocket_launcher_dl[];

#endif // MECH_ASSETS_H
""")

    # --- WRITE SOURCE FILE ---
    with open(c_filepath, 'w') as c_file:
        c_file.write('#include "mech_assets.h"\n\n')
        
        # Write texture data
        c_file.write("// 64x32 16bpp RGBA Texture Data\n")
        c_file.write("__attribute__((aligned(8))) const uint64_t mech_skin_texture[512] = {\n")
        for i in range(0, len(texture_words), 4):
            row_words = [f"0x{w:016X}ULL" for w in texture_words[i:i+4]]
            c_file.write(f"    {', '.join(row_words)},\n")
        c_file.write("};\n\n")
        
        # Write vertices for each chunk of each component
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
                    # Scale UV to s10.5 format (0 to width*32, 0 to height*32)
                    su = int(round(u * 64.0 * 32.0))
                    # Flip V coordinates for RDP top-left origin
                    tv = int(round((1.0 - v_coord) * 32.0 * 32.0))
                    # Clamp UV to prevent TMEM wrapping bugs
                    su = max(0, min(2047, su))
                    tv = max(0, min(1023, tv))
                    c_file.write(f"    {{{{{{ {ix:5d}, {iy:5d}, {iz:5d} }}, 0, {{ {su:5d}, {tv:5d} }}, {{ 255, 255, 255, 255 }} }}}},\n")
                c_file.write("};\n\n")
                
        # Write display lists
        for comp_name, chunks in compiled_data:
            c_file.write(f"// --- Display List for {comp_name} ---\n")
            c_file.write(f"const Gfx {comp_name}_dl[] = {{\n")
            for chunk_idx, (verts, tris) in enumerate(chunks):
                num_verts = len(verts)
                # Load vertices chunk into RSP vertex buffer (starting at index 0)
                c_file.write(f"    gsSPVertex({comp_name}_vtx_{chunk_idx}, {num_verts}, 0),\n")
                # Draw triangles referencing loaded vertices in RSP cache
                for t in tris:
                    c_file.write(f"    gsSP1Triangle({t[0]}, {t[1]}, {t[2]}, 0),\n")
            c_file.write("    gsSPEndDisplayList(),\n")
            c_file.write("};\n\n")

    print(f"Generated C display lists: {c_filepath} and {h_filepath}")

if __name__ == "__main__":
    main()
