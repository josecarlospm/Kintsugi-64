#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <libdragon.h>

int main(void)
{
    /* Initialize systems */
    display_init(RESOLUTION_320x240, DEPTH_16_BPP, 2, GAMMA_NONE, ANTIALIAS_RESAMPLE);
    controller_init();

    /* Position of our player/mech prototype text/cursor */
    int x = 160;
    int y = 120;
    int frame_count = 0;

    while (1)
    {
        /* Lock a display buffer to draw onto */
        display_context_t disp = 0;
        while (!(disp = display_lock()))
        {
            /* Wait for a buffer to become available */
        }

        /* Clear screen to a dark slate color (using Slate Gray color from the 3D Mech Palette: RGB 50, 55, 65) */
        uint32_t bg_color = graphics_make_color(50, 55, 65, 255);
        graphics_fill_screen(disp, bg_color);

        /* Read controller inputs */
        controller_scan();
        struct controller_data keys;
        controller_read(&keys);

        /* Move cursor/object with D-pad or Analog stick */
        if (keys.c[0].up || keys.c[0].y > 20) {
            y -= 2;
        }
        if (keys.c[0].down || keys.c[0].y < -20) {
            y += 2;
        }
        if (keys.c[0].left || keys.c[0].x < -20) {
            x -= 2;
        }
        if (keys.c[0].right || keys.c[0].x > 20) {
            x += 2;
        }

        /* Clamp boundaries to keep it on screen */
        if (x < 10) x = 10;
        if (x > 310) x = 310;
        if (y < 10) y = 10;
        if (y > 230) y = 230;

        /* Draw a box representing the Mech core/pelvis (Steel grey from palette: RGB 80, 80, 80) */
        uint32_t core_color = graphics_make_color(80, 80, 80, 255);
        graphics_draw_box(disp, x - 15, y - 10, 30, 20, core_color);

        /* Draw a neon visor line (Neon Red/Orange from palette: RGB 255, 40, 0) */
        uint32_t visor_color = graphics_make_color(255, 40, 0, 255);
        graphics_draw_line(disp, x - 10, y - 3, x + 10, y - 3, visor_color);

        /* Draw the text header at the top */
        uint32_t text_color = graphics_make_color(220, 180, 20, 255); // Accent yellow
        uint32_t bg_text_color = graphics_make_color(0, 0, 0, 0);
        graphics_set_color(text_color, bg_text_color);

        graphics_draw_text(disp, 20, 20, "KINTSUGI-64 ENGINE BOILERPLATE");
        graphics_draw_text(disp, 20, 32, "SHOGO INSPIRED MECH PROTOTYPE");

        /* Draw dynamic status information */
        char status_buf[64];
        sprintf(status_buf, "Mech Pos: X=%d Y=%d", x, y);
        graphics_draw_text(disp, 20, 200, status_buf);
        sprintf(status_buf, "Frame: %d", frame_count++);
        graphics_draw_text(disp, 20, 212, status_buf);

        /* Update display buffer */
        display_show(disp);
    }

    return 0;
}
