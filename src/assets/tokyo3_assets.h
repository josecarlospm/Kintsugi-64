#ifndef TOKYO3_ASSETS_H
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
