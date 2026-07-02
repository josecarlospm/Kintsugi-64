# N64 3D Asset Pipeline & Constraints Document

This document defines the Blender-to-N64 3D asset pipeline using the **Fast-64** plugin, optimized for low-poly geometry and TMEM limitations. It is tailored for the Nintendo 64 game project inspired by *SHOGO: Mobile Armor Division*.

---

## 1. Nintendo 64 Hardware Constraints

The Nintendo 64's **RCP (Reality Co-Processor)**, specifically the **RSP (Reality Signal Processor)** for geometry processing and the **RDP (Reality Display Processor)** for rasterization, introduces strict hardware limitations that dictate the design of 3D assets.

### Geometry Constraints
*   **Triangle Count:** Total screen budget per frame at 30 FPS is typically between **3,000 and 15,000 triangles**. For individual dynamic models (like a Mobile Armor/Mech), the budget is strictly **150 to 500 triangles**.
*   **Vertex Cache:** The RSP vertex cache holds only **32 vertices** (or 64 in later microcodes like F3DEX2). Meshes must be grouped and rendered in chunks that fit inside this cache. Fast-64 handles this splitting automatically, but keeping mesh density low reduces vertex loading commands (`gSPVertex`).
*   **Vertex Structure (`Vtx`):** Each vertex takes 16 bytes:
    *   `x, y, z`: 16-bit signed integer coordinates (fixed-point).
    *   `s, t`: 16-bit signed texture coordinates (s10.5 fixed-point format).
    *   `r, g, b, a` or `nx, ny, nz, a`: 8-bit unsigned colors or normals + alpha.
*   **Vertex Colors vs. Textures:** Vertex coloring (`gSP1Triangle` with smooth/flat shading) consumes zero texture memory (TMEM) and is extremely fast to render. Blend textured sections with vertex-colored sections to optimize performance.

### TMEM (Texture Memory) Constraints
The RDP has a tiny **4 KB** high-speed on-chip cache for textures called TMEM. All textures used in a single draw call must fit in this 4 KB budget.

#### Texture Size & Format Combinations
To maximize texture quality, choose the appropriate color format:

| Format | Bits/Px | Description | Max Dimensions (Fits 4 KB) |
| :--- | :--- | :--- | :--- |
| **RGBA16** | 16-bit | 5 bits per R, G, B, and 1-bit alpha. | **64x32**, **32x64**, **32x32** |
| **RGBA32** | 32-bit | 8 bits per R, G, B, A. Double TMEM usage. | **32x32** (split over two TMEM halves) |
| **CI8 (Color Index)** | 8-bit | 256-color palette (512 bytes). | **64x64**, **64x32** (leaves room for palette) |
| **CI4 (Color Index)** | 4-bit | 16-color palette (32 bytes). | **128x64**, **64x64** |
| **IA8 (Intensity/Alpha)** | 8-bit | 4 bits intensity, 4 bits alpha. | **64x64**, **32x64** |
| **IA4 (Intensity/Alpha)** | 4-bit | 3 bits intensity, 1 bit alpha. | **128x64**, **64x64** |
| **I8 (Intensity)** | 8-bit | 8 bits grayscale brightness. | **64x64** |
| **I4 (Intensity)** | 4-bit | 4 bits grayscale brightness. | **128x64**, **128x32** |

#### Wrapping, Clamping, and Mirroring
*   **S/T Tiling:** Textures can wrap or mirror along the S and T axes.
*   **Clamping:** Clamping prevents texture coordinates from wrapping, useful for borders/decals.
*   **Mirroring:** Mirrored textures allow you to double the visual resolution of symmetrical parts (e.g. legs, arms) by mirroring the UV coordinates.

---

## 2. Blender and Fast-64 Setup

**Fast-64** is an open-source Blender plugin that exports Blender scenes directly to N64-compatible C structures and Fast3D display lists.

### Installation & Configuration
1.  Download the latest Fast-64 zip from the [Fast-64 GitHub Repository](https://github.com/Fast-64/fast64).
2.  In Blender, navigate to `Edit -> Preferences -> Add-ons -> Install...` and select the zip file. Enable the add-on.
3.  Set the export target format to **Libultra** (F3DEX2 or F3DEX).

### Essential Mesh Preparation Checklist (Avoid Common Mistakes)
To prevent build failures or rendering errors on N64, ensure the following steps are performed before exporting:

1.  **Apply Transforms (`Ctrl + A`):**
    *   Always select the mesh and apply **Scale** and **Rotation** in Blender (`Ctrl + A -> Rotation & Scale`). If scale is not applied (i.e. scale is not 1.0, 1.0, 1.0), the model will deform or stretch unpredictably in the game engine.
2.  **Recalculate Normals (`Shift + N`):**
    *   Flipped normals result in invisible/back-facing geometry. Select all faces in Edit Mode and press `Shift + N` to recalculate normals outwards.
    *   Enable **Face Orientation** in viewport overlays to verify: all exterior surfaces must be **Blue** (correct), not **Red** (flipped).
3.  **Origin Placement:**
    *   Set the origin point of the Mech model to the base of its feet at `(0, 0, 0)`. This ensures that coordinate translation, rotation, and ground-collision checks work correctly in-engine.
4.  **UV Unwrapping:**
    *   Keep UV islands packed tightly. Make sure texture coordinates do not exceed bounds unless S/T wrapping/tiling is explicitly intended.
5.  **Triangulate Modifiers:**
    *   Ensure all faces are triangulated. While Fast-64 can export quads, manually adding a **Triangulate** modifier or applying triangulation ensures total control over edge direction.

---

## 3. Fast-64 Export Workflow to C/C++ Engine

Once the model and materials are set up, export the assets to C structures.

### Step-by-Step Export Process
1.  **Material Setup:**
    *   Select the mesh, navigate to the Fast-64 material properties panel.
    *   Select the **Cycle Type**: `G_CYC_1CYCLE` (standard rendering) or `G_CYC_2CYCLE` (advanced blending/mipmapping).
    *   Set **Render Mode**: E.g., `G_RM_AA_ZB_OPA_SURF` for opaque solids, or `G_RM_AA_ZB_TEX_EDGE` for cutout transparent textures.
    *   Assign the texture file (e.g. a 64x32 PNG file) and choose the TMEM loading options (Format: `RGBA16`, Width: `64`, Height: `32`).
2.  **Export Configuration:**
    *   Open the Fast-64 panel (`N` sidebar in 3D Viewport -> `Fast-64` tab).
    *   Choose **Export Type**: `Geom Layout / Display Lists` (C files).
    *   Set the output directory (e.g., `src/assets/mech/`).
3.  **Perform Export:**
    *   Select the Mech mesh object.
    *   Click **Export Selected**.

### Generated Code Structure
Fast-64 will generate a `.c` and `.h` pair containing:

#### 1. Texture Arrays
The texture pixels are converted to raw byte arrays:
```c
// RGBA16 texture data: 64x32 pixels = 2048 words (4096 bytes)
ALIGNED8 static const u64 mech_skin_texture[] = {
    0x39E739E739E739E7...,
    ...
};
```

#### 2. Vertex Data
The geometry is written as an array of `Vtx` structures, grouped in sets of <= 32:
```c
static Vtx mech_prototype_vtx_group0[] = {
    {{{   -50,   200,     0}, 0, {     0,     0}, {0x32, 0x37, 0x41, 0xFF}}},
    {{{    50,   200,     0}, 0, {  2048,     0}, {0x32, 0x37, 0x41, 0xFF}}},
    ...
};
```

#### 3. Display List Commands (`Gfx`)
The commands sequence loaded into the RCP/RDP to draw the model:
```c
Gfx mech_prototype_dl[] = {
    gsDPPipeSync(),
    // Set texture combiner and render modes
    gsDPSetCombineMode(G_CC_MODULATERGBA, G_CC_MODULATERGBA),
    gsSPTexture(0xFFFF, 0xFFFF, 0, G_TX_RENDERTILE, G_ON),
    // Load texture to TMEM
    gsDPLoadTextureBlock(mech_skin_texture, G_IM_FMT_RGBA, G_IM_SIZ_16b, 64, 32, 0, G_TX_CLAMP, G_TX_CLAMP, 6, 5, G_TX_NOLOD, G_TX_NOLOD),
    // Load vertices to RSP Cache
    gsSPVertex(mech_prototype_vtx_group0, 32, 0),
    // Draw triangles using cached vertices
    gsSP1Triangle(0, 1, 2, 0),
    gsSP1Triangle(2, 3, 0, 0),
    ...
    gsSPEndDisplayList(),
};
```

---

## 4. Mech Prototype Specifications

The prototype Mech model generated in `models/mech_prototype.obj` adheres to these constraints:
*   **Total Vertices:** 276
*   **Total Triangles:** 428
*   **Height:** 4.6 units (approx 4.6 meters tall in engine coordinates).
*   **Components:** Modular body parts (Head, Torso, Hips, Left/Right Arms, Left/Right Legs) optimized for skeleton binding and hierarchy traversal.
