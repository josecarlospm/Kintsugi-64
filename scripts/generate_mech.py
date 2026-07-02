#!/usr/bin/env python3
import os
import math

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

    def add_box(self, name, cx, cy, cz, dx, dy, dz, color=(128, 128, 128), taper_y=1.0, taper_z=1.0, offset_top_z=0.0):
        self.set_object(name)
        r, g, b = color
        
        # Define 8 corners of the box
        # Lower face: y = cy - dy/2
        # Upper face: y = cy + dy/2
        v = []
        for dy_sign in [-1, 1]:
            curr_y = cy + dy_sign * (dy / 2.0)
            # Apply taper for the upper face
            tx = taper_y if dy_sign > 0 else 1.0
            tz = taper_z if dy_sign > 0 else 1.0
            to_z = offset_top_z if dy_sign > 0 else 0.0
            
            for dz_sign in [-1, 1]:
                curr_z = cz + dz_sign * (dz / 2.0) * tz + to_z
                for dx_sign in [-1, 1]:
                    curr_x = cx + dx_sign * (dx / 2.0) * tx
                    v.append(self.add_vertex(curr_x, curr_y, curr_z, r, g, b))
        
        # Vertex layout in v:
        # 0: -x, -y, -z
        # 1:  x, -y, -z
        # 2: -x, -y,  z
        # 3:  x, -y,  z
        # 4: -x,  y, -z
        # 5:  x,  y, -z
        # 6: -x,  y,  z
        # 7:  x,  y,  z

        # Define UVs for a box (simple wrap or unique mappings)
        # We define a few default UV positions
        u0 = self.add_uv(0.0, 0.0)
        u1 = self.add_uv(1.0, 0.0)
        u2 = self.add_uv(1.0, 1.0)
        u3 = self.add_uv(0.0, 1.0)

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

    def add_cylinder(self, name, cx, cy, cz, radius, height, sides=6, color=(128, 128, 128), axis='y'):
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
            
        u0 = self.add_uv(0.0, 0.0)
        u1 = self.add_uv(1.0, 0.0)
        u2 = self.add_uv(1.0, 1.0)
        u3 = self.add_uv(0.0, 1.0)
        
        # Side faces
        for i in range(sides):
            next_i = (i + 1) % sides
            self.add_face([bottom_v[i], bottom_v[next_i], top_v[next_i], top_v[i]], [u0, u1, u2, u3])
            
        # Cap faces
        self.add_face(bottom_v[::-1]) # bottom cap (reversed for outside normal)
        self.add_face(top_v)          # top cap

    def write_obj(self, filepath, mtl_filename=None):
        with open(filepath, 'w') as f:
            f.write("# N64 Mech Prototype - Low Poly (<500 tris)\n")
            f.write("# Generated programmatically by N64 3D Graphics Expert\n")
            if mtl_filename:
                f.write(f"mtllib {mtl_filename}\n")
                
            # Write vertices with vertex colors (Wavefront OBJ extension: v x y z r g b)
            for v in self.vertices:
                f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f} {v[3]:.4f} {v[4]:.4f} {v[5]:.4f}\n")
                
            # Write UVs
            for uv in self.uvs:
                f.write(f"vt {uv[0]:.4f} {uv[1]:.4f}\n")
                
            # Write objects/groups
            for obj_name, faces in self.objects.items():
                f.write(f"\no {obj_name}\n")
                f.write(f"usemtl {obj_name}_mat\n")
                for face in faces:
                    f.write("f")
                    for v_idx, uv_idx in face:
                        if uv_idx:
                            f.write(f" {v_idx}/{uv_idx}")
                        else:
                            f.write(f" {v_idx}")
                    f.write("\n")

def generate_mech():
    builder = MeshBuilder()
    
    # Let's design a cohesive color palette
    # Armor main: Dark Slate Grey (50, 55, 65)
    # Armor secondary: Medium Blue-Grey (90, 100, 115)
    # Visor/Glow: Neon Red/Orange (255, 40, 0)
    # Joints/Mechanical: Steel Grey (70, 70, 70)
    # Weapons: Gunmetal (40, 40, 40)
    # Accent: Yellow (220, 180, 20)
    
    c_main = (50, 55, 65)
    c_sec = (90, 100, 115)
    c_visor = (255, 40, 0)
    c_joint = (80, 80, 80)
    c_gun = (40, 40, 40)
    c_accent = (220, 180, 20)
    
    # --- HEAD (Y: 4.0 to 4.6) ---
    # Main head block
    builder.add_box("head_main", cx=0.0, cy=4.3, cz=0.0, dx=0.4, dy=0.4, dz=0.4, color=c_main, taper_y=0.85)
    # Visor (protruding slightly forward)
    builder.add_box("head_visor", cx=0.0, cy=4.35, cz=0.21, dx=0.3, dy=0.12, dz=0.08, color=c_visor)
    # Left antenna
    builder.add_box("head_antenna_l", cx=-0.22, cy=4.5, cz=-0.05, dx=0.05, dy=0.3, dz=0.05, color=c_accent)
    # Right antenna
    builder.add_box("head_antenna_r", cx=0.22, cy=4.5, cz=-0.05, dx=0.05, dy=0.3, dz=0.05, color=c_accent)
    
    # --- TORSO (Y: 2.6 to 4.0) ---
    # Upper chest (tapered, bulky forward)
    builder.add_box("torso_upper", cx=0.0, cy=3.6, cz=0.0, dx=1.1, dy=0.6, dz=0.8, color=c_main, taper_y=1.2, offset_top_z=0.1)
    # Lower chest / Waist
    builder.add_box("torso_lower", cx=0.0, cy=3.0, cz=-0.05, dx=0.8, dy=0.6, dz=0.7, color=c_sec, taper_y=0.8)
    # Backpack / Jump jets
    builder.add_box("backpack", cx=0.0, cy=3.5, cz=-0.5, dx=0.7, dy=0.8, dz=0.3, color=c_gun)
    builder.add_box("thruster_l", cx=-0.25, cy=3.0, cz=-0.6, dx=0.18, dy=0.3, dz=0.18, color=c_accent)
    builder.add_box("thruster_r", cx=0.25, cy=3.0, cz=-0.6, dx=0.18, dy=0.3, dz=0.18, color=c_accent)

    # --- HIPS / PELVIS (Y: 2.2 to 2.6) ---
    builder.add_box("hips", cx=0.0, cy=2.4, cz=-0.05, dx=0.7, dy=0.3, dz=0.6, color=c_joint)

    # --- LEGS (Symmetrical L/R) ---
    # Left Hip Joint
    builder.add_cylinder("hip_joint_l", cx=-0.45, cy=2.4, cz=-0.05, radius=0.15, height=0.2, sides=6, color=c_joint, axis='x')
    # Right Hip Joint
    builder.add_cylinder("hip_joint_r", cx=0.45, cy=2.4, cz=-0.05, radius=0.15, height=0.2, sides=6, color=c_joint, axis='x')
    
    # Thighs
    builder.add_box("thigh_l", cx=-0.5, cy=1.8, cz=0.0, dx=0.3, dy=0.8, dz=0.35, color=c_main, taper_y=0.8)
    builder.add_box("thigh_r", cx=0.5, cy=1.8, cz=0.0, dx=0.3, dy=0.8, dz=0.35, color=c_main, taper_y=0.8)
    
    # Knee joints
    builder.add_cylinder("knee_l", cx=-0.5, cy=1.35, cz=0.0, radius=0.14, height=0.25, sides=6, color=c_joint, axis='x')
    builder.add_cylinder("knee_r", cx=0.5, cy=1.35, cz=0.0, radius=0.14, height=0.25, sides=6, color=c_joint, axis='x')
    
    # Calves (reversed-joint feel or chunky armored lower legs)
    builder.add_box("calf_l", cx=-0.5, cy=0.8, cz=-0.05, dx=0.34, dy=0.9, dz=0.4, color=c_sec, taper_y=1.2, offset_top_z=-0.05)
    builder.add_box("calf_r", cx=0.5, cy=0.8, cz=-0.05, dx=0.34, dy=0.9, dz=0.4, color=c_sec, taper_y=1.2, offset_top_z=-0.05)
    
    # Feet (bulky 3-toe look or solid wedge-like block)
    builder.add_box("foot_l", cx=-0.5, cy=0.2, cz=0.1, dx=0.42, dy=0.3, dz=0.6, color=c_main, taper_y=0.7, offset_top_z=0.1)
    builder.add_box("foot_r", cx=0.5, cy=0.2, cz=0.1, dx=0.42, dy=0.3, dz=0.6, color=c_main, taper_y=0.7, offset_top_z=0.1)

    # --- ARMS (Symmetrical L/R) ---
    # Shoulder joints / Pads
    builder.add_box("shoulder_pad_l", cx=-0.75, cy=3.7, cz=0.05, dx=0.4, dy=0.4, dz=0.5, color=c_sec, taper_y=0.8)
    builder.add_box("shoulder_pad_r", cx=0.75, cy=3.7, cz=0.05, dx=0.4, dy=0.4, dz=0.5, color=c_sec, taper_y=0.8)
    
    # Upper Arms
    builder.add_box("upper_arm_l", cx=-0.75, cy=3.2, cz=0.05, dx=0.25, dy=0.6, dz=0.25, color=c_joint)
    builder.add_box("upper_arm_r", cx=0.75, cy=3.2, cz=0.05, dx=0.25, dy=0.6, dz=0.25, color=c_joint)
    
    # Elbow Joints
    builder.add_cylinder("elbow_l", cx=-0.75, cy=2.8, cz=0.05, radius=0.12, height=0.22, sides=6, color=c_joint, axis='y')
    builder.add_cylinder("elbow_r", cx=0.75, cy=2.8, cz=0.05, radius=0.12, height=0.22, sides=6, color=c_joint, axis='y')
    
    # Forearms (heavy, blocky with shields/weapon integrations)
    # Left Arm: Laser cannon forearm
    builder.add_box("forearm_l", cx=-0.8, cy=2.2, cz=0.15, dx=0.3, dy=0.8, dz=0.35, color=c_main)
    builder.add_cylinder("laser_cannon", cx=-0.8, cy=1.7, cz=0.25, radius=0.08, height=0.5, sides=6, color=c_gun, axis='y')
    
    # Right Arm: Rocket launcher forearm
    builder.add_box("forearm_r", cx=0.8, cy=2.2, cz=0.15, dx=0.3, dy=0.8, dz=0.35, color=c_main)
    # Launcher pod on top of right forearm
    builder.add_box("rocket_pod", cx=0.85, cy=2.4, cz=0.2, dx=0.25, dy=0.3, dz=0.5, color=c_gun)
    builder.add_box("rocket_tubes", cx=0.85, cy=2.4, cz=0.46, dx=0.2, dy=0.2, dz=0.02, color=c_visor) # red warning plate/face

    # Ensure directories exist
    os.makedirs("models", exist_ok=True)
    
    obj_path = "models/mech_prototype.obj"
    mtl_path = "models/mech_prototype.mtl"
    
    builder.write_obj(obj_path, mtl_filename="mech_prototype.mtl")
    print(f"Generated OBJ model: {obj_path} ({len(builder.vertices)} vertices)")
    
    # Write the MTL file for the colors
    with open(mtl_path, 'w') as f:
        f.write("# MTL for N64 Mech Prototype\n\n")
        
        materials = {
            "head_main": c_main,
            "head_visor": c_visor,
            "head_antenna_l": c_accent,
            "head_antenna_r": c_accent,
            "torso_upper": c_main,
            "torso_lower": c_sec,
            "backpack": c_gun,
            "thruster_l": c_accent,
            "thruster_r": c_accent,
            "hips": c_joint,
            "hip_joint_l": c_joint,
            "hip_joint_r": c_joint,
            "thigh_l": c_main,
            "thigh_r": c_main,
            "knee_l": c_joint,
            "knee_r": c_joint,
            "calf_l": c_sec,
            "calf_r": c_sec,
            "foot_l": c_main,
            "foot_r": c_main,
            "shoulder_pad_l": c_sec,
            "shoulder_pad_r": c_sec,
            "upper_arm_l": c_joint,
            "upper_arm_r": c_joint,
            "elbow_l": c_joint,
            "elbow_r": c_joint,
            "forearm_l": c_main,
            "laser_cannon": c_gun,
            "forearm_r": c_main,
            "rocket_pod": c_gun,
            "rocket_tubes": c_visor
        }
        
        for name, color in materials.items():
            r, g, b = color[0]/255.0, color[1]/255.0, color[2]/255.0
            f.write(f"newmtl {name}_mat\n")
            f.write(f"Kd {r:.4f} {g:.4f} {b:.4f}\n")
            f.write(f"Ka {r*0.5:.4f} {g*0.5:.4f} {b*0.5:.4f}\n")
            f.write("Ks 0.1 0.1 0.1\n")
            f.write("Ns 10.0\n")
            f.write("illum 2\n\n")
            
    print(f"Generated MTL file: {mtl_path}")

if __name__ == "__main__":
    generate_mech()
