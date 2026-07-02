#ifndef MECH_ASSETS_H
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
