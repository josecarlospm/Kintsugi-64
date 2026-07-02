#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include <libdragon.h>

#define MAP_WIDTH 16
#define MAP_HEIGHT 16

/* Underground Tokyo-3 street grid map: 1 is concrete wall, 2 is neon cyan skyscraper, 3 is red defense barrier, 0 is empty street */
static const uint8_t MAP[MAP_HEIGHT][MAP_WIDTH] = {
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1},
    {1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1},
    {1,0,2,2,0,0,2,0,0,3,3,3,3,0,0,1},
    {1,0,2,0,0,0,0,0,0,0,0,0,3,0,0,1},
    {1,0,2,0,0,0,2,0,0,0,0,0,3,0,0,1},
    {1,0,0,0,0,0,1,0,0,2,2,0,0,0,0,1},
    {1,1,1,0,1,1,1,0,0,2,2,0,0,0,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,1,1,0,1},
    {1,0,3,3,3,0,0,2,2,2,0,0,1,1,0,1},
    {1,0,3,0,3,0,0,2,0,2,0,0,0,0,0,1},
    {1,0,3,3,3,0,0,2,2,2,0,0,0,0,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,3,3,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,3,3,0,1},
    {1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1},
    {1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1}
};

typedef enum {
    STATE_EXPLORING,
    STATE_DIALOGUE_INTRO,
    STATE_DIALOGUE_CHOICE,
    STATE_DIALOGUE_OUTCOME
} GameState;

typedef struct {
    float x, y;
    const char *name;
    const char *intro;
    const char *opt1;
    const char *opt2;
    const char *reaction1;
    const char *reaction2;
    uint32_t color;
} Citizen;

#define NUM_CITIZENS 3
static Citizen citizens[NUM_CITIZENS] = {
    {
        .x = 4.5f, .y = 3.5f,
        .name = "Misato",
        .intro = "Pilot, the Angel has breached the outer dome! State your status!",
        .opt1 = "Ready for combat, Major!",
        .opt2 = "This city is doomed...",
        .reaction1 = "Good. Protect the civilian shelters at all costs!",
        .reaction2 = "Pull yourself together! We are humanity's last hope!",
        .color = 0x9632B4FF // Purple
    },
    {
        .x = 11.5f, .y = 4.5f,
        .name = "Kenji",
        .intro = "Aaaah! Please don't step on me, giant robot! Are you here to save us?!",
        .opt1 = "Yes, stay behind me!",
        .opt2 = "Get out of the combat zone!",
        .reaction1 = "Thank goodness! Good luck out there!",
        .reaction2 = "Okay, okay, I'm running to the bunker!",
        .color = 0x32C864FF // Green
    },
    {
        .x = 11.5f, .y = 10.5f,
        .name = "Rei",
        .intro = "...Why are you talking to me? The Eva is waiting.",
        .opt1 = "You need to evacuate, Rei.",
        .opt2 = "Hmph, fine, whatever.",
        .reaction1 = "I will be fine. I have a duty to fulfill.",
        .reaction2 = "...",
        .color = 0x6496FFFF // Blue
    }
};

/* Mini-map renderer */
void draw_minimap(display_context_t disp, float posX, float posY, float dirX, float dirY) {
    int start_x = 260;
    int start_y = 10;
    int cell_size = 3;
    
    // Mini-map background frame
    uint32_t frame_bg = graphics_make_color(30, 30, 35, 180);
    graphics_draw_box(disp, start_x - 2, start_y - 2, MAP_WIDTH * cell_size + 4, MAP_HEIGHT * cell_size + 4, frame_bg);
    
    // Draw cells
    for (int y = 0; y < MAP_HEIGHT; y++) {
        for (int x = 0; x < MAP_WIDTH; x++) {
            uint32_t cell_color;
            if (MAP[y][x] > 0) {
                cell_color = graphics_make_color(80, 80, 90, 255); // Wall
            } else {
                cell_color = graphics_make_color(15, 15, 20, 255); // Street
            }
            graphics_draw_box(disp, start_x + x * cell_size, start_y + y * cell_size, cell_size, cell_size, cell_color);
        }
    }
    
    // Draw citizens
    for (int k = 0; k < NUM_CITIZENS; k++) {
        int cx = (int)(citizens[k].x * cell_size);
        int cy = (int)(citizens[k].y * cell_size);
        graphics_draw_box(disp, start_x + cx - 1, start_y + cy - 1, 3, 3, citizens[k].color);
    }
    
    // Draw Player dot
    int px = (int)(posX * cell_size);
    int py = (int)(posY * cell_size);
    uint32_t player_color = graphics_make_color(255, 50, 50, 255);
    graphics_draw_box(disp, start_x + px - 1, start_y + py - 1, 3, 3, player_color);
    
    // Draw direction vector line
    int pdx = (int)((posX + dirX * 1.5f) * cell_size);
    int pdy = (int)((posY + dirY * 1.5f) * cell_size);
    graphics_draw_line(disp, start_x + px, start_y + py, start_x + pdx, start_y + pdy, player_color);
}

/* Combat HUD renderer */
void draw_hud(display_context_t disp, int hp, int shd, int active_weapon) {
    uint32_t panel_bg = graphics_make_color(20, 20, 25, 150);
    graphics_draw_box(disp, 5, 5, 140, 48, panel_bg);
    
    // HP bar
    uint32_t hp_color = graphics_make_color(0, 220, 100, 255);
    graphics_set_color(hp_color, graphics_make_color(0,0,0,0));
    graphics_draw_text(disp, 10, 10, "EV-01 HP");
    graphics_draw_box(disp, 65, 11, hp * 70 / 100, 6, hp_color);
    
    // Shield bar
    uint32_t shd_color = graphics_make_color(0, 150, 255, 255);
    graphics_set_color(shd_color, graphics_make_color(0,0,0,0));
    graphics_draw_text(disp, 10, 22, "SHIELD");
    graphics_draw_box(disp, 65, 23, shd * 70 / 100, 6, shd_color);
    
    // Weapon indicators
    uint32_t wep_color = graphics_make_color(220, 180, 20, 255);
    graphics_set_color(wep_color, graphics_make_color(0,0,0,0));
    char wep_buf[32];
    sprintf(wep_buf, "WEP: %s", (active_weapon == 0) ? "ENERGY RIFLE" : "ROCKET LAUNCHER");
    graphics_draw_text(disp, 10, 36, wep_buf);
}

/* FPS weapon visual overlays */
void draw_weapon_hud(display_context_t disp, int weapon_type, int bob_frame) {
    uint32_t steel = graphics_make_color(85, 85, 90, 255);
    uint32_t dark_steel = graphics_make_color(45, 45, 48, 255);
    uint32_t cyan = graphics_make_color(0, 220, 255, 255);
    uint32_t orange = graphics_make_color(255, 80, 0, 255);
    
    int bob_y = (int)(sinf(bob_frame * 0.2f) * 4.0f);
    
    if (weapon_type == 0) {
        // Energy Rifle drawing using boxes and lines
        graphics_draw_box(disp, 215, 180 + bob_y, 65, 60, dark_steel);
        graphics_draw_box(disp, 175, 195 + bob_y, 40, 15, steel);
        graphics_draw_box(disp, 225, 168 + bob_y, 30, 12, dark_steel);
        graphics_draw_box(disp, 220, 171 + bob_y, 5, 6, cyan);
        graphics_draw_box(disp, 170, 200 + bob_y, 5, 5, cyan);
        graphics_draw_line(disp, 180, 202 + bob_y, 215, 202 + bob_y, cyan);
    } else {
        // Rocket Launcher drawing
        graphics_draw_box(disp, 205, 160 + bob_y, 75, 80, dark_steel);
        graphics_draw_box(disp, 195, 165 + bob_y, 10, 70, steel);
        graphics_draw_box(disp, 197, 172 + bob_y, 6, 6, orange);
        graphics_draw_box(disp, 197, 184 + bob_y, 6, 6, orange);
        graphics_draw_box(disp, 197, 196 + bob_y, 6, 6, orange);
        graphics_draw_box(disp, 197, 208 + bob_y, 6, 6, orange);
        graphics_draw_line(disp, 210, 165 + bob_y, 270, 165 + bob_y, orange);
        graphics_draw_line(disp, 210, 235 + bob_y, 270, 235 + bob_y, orange);
    }
}

/* Sci-fi dialogue box renderer */
void draw_dialogue_box(display_context_t disp, GameState state, int citizen_idx, int selected_choice) {
    if (citizen_idx < 0 || citizen_idx >= NUM_CITIZENS) return;
    Citizen cit = citizens[citizen_idx];
    
    uint32_t bg_color = graphics_make_color(15, 20, 30, 220); 
    uint32_t border_color = graphics_make_color(220, 180, 20, 255); 
    uint32_t text_color = graphics_make_color(240, 240, 240, 255);
    uint32_t name_color = graphics_make_color(255, 100, 30, 255); 
    
    // Background box
    graphics_draw_box(disp, 10, 155, 300, 75, bg_color);
    
    // Border lines
    graphics_draw_line(disp, 10, 155, 310, 155, border_color);
    graphics_draw_line(disp, 10, 230, 310, 230, border_color);
    graphics_draw_line(disp, 10, 155, 10, 230, border_color);
    graphics_draw_line(disp, 310, 155, 310, 230, border_color);
    
    // Name tag
    char name_buf[48];
    sprintf(name_buf, "%s (Tokyo-3 Evacuee)", cit.name);
    graphics_set_color(name_color, graphics_make_color(0,0,0,0));
    graphics_draw_text(disp, 20, 162, name_buf);
    
    graphics_set_color(text_color, graphics_make_color(0,0,0,0));
    if (state == STATE_DIALOGUE_INTRO) {
        graphics_draw_text(disp, 20, 180, cit.intro);
        graphics_set_color(border_color, graphics_make_color(0,0,0,0));
        graphics_draw_text(disp, 20, 212, "[Press A to respond]");
    } else if (state == STATE_DIALOGUE_CHOICE) {
        char opt1_buf[128];
        char opt2_buf[128];
        sprintf(opt1_buf, "%s %s", (selected_choice == 0) ? ">" : " ", cit.opt1);
        sprintf(opt2_buf, "%s %s", (selected_choice == 1) ? ">" : " ", cit.opt2);
        
        if (selected_choice == 0) {
            graphics_set_color(border_color, graphics_make_color(0,0,0,0));
            graphics_draw_text(disp, 20, 180, opt1_buf);
            graphics_set_color(text_color, graphics_make_color(0,0,0,0));
            graphics_draw_text(disp, 20, 195, opt2_buf);
        } else {
            graphics_set_color(text_color, graphics_make_color(0,0,0,0));
            graphics_draw_text(disp, 20, 180, opt1_buf);
            graphics_set_color(border_color, graphics_make_color(0,0,0,0));
            graphics_draw_text(disp, 20, 195, opt2_buf);
        }
        graphics_set_color(graphics_make_color(150, 150, 150, 255), graphics_make_color(0,0,0,0));
        graphics_draw_text(disp, 20, 212, "[D-Pad Up/Down to choose, A to select]");
    } else if (state == STATE_DIALOGUE_OUTCOME) {
        if (selected_choice == 0) {
            graphics_draw_text(disp, 20, 180, cit.reaction1);
        } else {
            graphics_draw_text(disp, 20, 180, cit.reaction2);
        }
        graphics_set_color(border_color, graphics_make_color(0,0,0,0));
        graphics_draw_text(disp, 20, 212, "[Press A to close dialogue]");
    }
}

int main(void)
{
    /* Initialize systems */
    display_init(RESOLUTION_320x240, DEPTH_16_BPP, 2, GAMMA_NONE, ANTIALIAS_RESAMPLE);
    controller_init();

    /* Player position & direction */
    float posX = 2.5f, posY = 2.5f;
    float dirX = 1.0f, dirY = 0.0f;
    float planeX = 0.0f, planeY = 0.66f;

    /* Gameplay parameters */
    int hp = 100;
    int shield = 80;
    int active_weapon = 0;
    int bob_frame = 0;
    int game_frame = 0;

    GameState state = STATE_EXPLORING;
    int dialogue_citizen_idx = -1;
    int selected_choice = 0;

    float z_buffer[160];

    while (1)
    {
        display_context_t disp = 0;
        while (!(disp = display_lock()))
        {
            /* Wait for buffer */
        }

        /* Read controller inputs */
        controller_scan();
        struct controller_data keys;
        controller_read(&keys);
        struct controller_data keys_down = get_keys_down();

        /* GAME STATE UPDATE */
        if (state == STATE_EXPLORING) {
            float moveSpeed = 0.08f;
            float rotSpeed = 0.06f;
            float moveX = 0.0f;
            float moveY = 0.0f;
            
            // Turning
            float rotate_angle = 0.0f;
            if (keys.c[0].left || keys.c[0].x < -20) {
                rotate_angle = rotSpeed;
            }
            if (keys.c[0].right || keys.c[0].x > 20) {
                rotate_angle = -rotSpeed;
            }
            if (rotate_angle != 0.0f) {
                float oldDirX = dirX;
                dirX = dirX * cosf(rotate_angle) - dirY * sinf(rotate_angle);
                dirY = oldDirX * sinf(rotate_angle) + dirY * cosf(rotate_angle);
                float oldPlaneX = planeX;
                planeX = planeX * cosf(rotate_angle) - planeY * sinf(rotate_angle);
                planeY = oldPlaneX * sinf(rotate_angle) + planeY * cosf(rotate_angle);
            }

            // Movement
            if (keys.c[0].up || keys.c[0].y > 20) {
                moveX = dirX * moveSpeed;
                moveY = dirY * moveSpeed;
            }
            if (keys.c[0].down || keys.c[0].y < -20) {
                moveX = -dirX * moveSpeed;
                moveY = -dirY * moveSpeed;
            }

            if (moveX != 0.0f || moveY != 0.0f) {
                float nextX = posX + moveX;
                float nextY = posY + moveY;
                
                // Sliding collision detection against walls
                if (MAP[(int)posY][(int)nextX] == 0) {
                    posX = nextX;
                }
                if (MAP[(int)nextY][(int)posX] == 0) {
                    posY = nextY;
                }
                
                // Collision against citizens
                for (int k = 0; k < NUM_CITIZENS; k++) {
                    float dx = citizens[k].x - posX;
                    float dy = citizens[k].y - posY;
                    float dist = sqrtf(dx*dx + dy*dy);
                    if (dist < 0.6f) {
                        posX -= moveX;
                        posY -= moveY;
                        break;
                    }
                }
                
                bob_frame++;
            } else {
                if (bob_frame > 0) bob_frame--;
            }

            // Weapon switching
            if (keys_down.c[0].L || keys_down.c[0].R || keys_down.c[0].Z) {
                active_weapon = 1 - active_weapon;
            }

            // Interact trigger logic
            int closest_idx = -1;
            float closest_dist = 999.0f;
            for (int k = 0; k < NUM_CITIZENS; k++) {
                float dx = citizens[k].x - posX;
                float dy = citizens[k].y - posY;
                float dist = sqrtf(dx*dx + dy*dy);
                if (dist < closest_dist) {
                    closest_dist = dist;
                    closest_idx = k;
                }
            }

            if (closest_idx != -1 && closest_dist < 1.3f) {
                if (keys_down.c[0].A) {
                    dialogue_citizen_idx = closest_idx;
                    state = STATE_DIALOGUE_INTRO;
                    selected_choice = 0;
                }
            }
        } else if (state == STATE_DIALOGUE_INTRO) {
            if (keys_down.c[0].A) {
                state = STATE_DIALOGUE_CHOICE;
            }
        } else if (state == STATE_DIALOGUE_CHOICE) {
            if (keys_down.c[0].up || keys_down.c[0].C_up || keys.c[0].y > 30) {
                selected_choice = 0;
            }
            if (keys_down.c[0].down || keys_down.c[0].C_down || keys.c[0].y < -30) {
                selected_choice = 1;
            }
            if (keys_down.c[0].A) {
                state = STATE_DIALOGUE_OUTCOME;
            }
        } else if (state == STATE_DIALOGUE_OUTCOME) {
            if (keys_down.c[0].A) {
                state = STATE_EXPLORING;
                dialogue_citizen_idx = -1;
            }
        }

        /* 3D RENDERING - 160 COLUMNS RAYCASTER */
        uint32_t ceiling_color = graphics_make_color(22, 22, 28, 255);
        uint32_t floor_color = graphics_make_color(38, 40, 44, 255);

        for (int i = 0; i < 160; i++) {
            float cameraX = 2.0f * i / 160.0f - 1.0f;
            float rayDirX = dirX + planeX * cameraX;
            float rayDirY = dirY + planeY * cameraX;

            int mapX = (int)posX;
            int mapY = (int)posY;

            float sideDistX;
            float sideDistY;

            float deltaDistX = (rayDirX == 0) ? 1e30f : fabsf(1.0f / rayDirX);
            float deltaDistY = (rayDirY == 0) ? 1e30f : fabsf(1.0f / rayDirY);
            float perpWallDist;

            int stepX;
            int stepY;

            int hit = 0;
            int side = 0;

            if (rayDirX < 0) {
                stepX = -1;
                sideDistX = (posX - mapX) * deltaDistX;
            } else {
                stepX = 1;
                sideDistX = (mapX + 1.0f - posX) * deltaDistX;
            }
            if (rayDirY < 0) {
                stepY = -1;
                sideDistY = (posY - mapY) * deltaDistY;
            } else {
                stepY = 1;
                sideDistY = (mapY + 1.0f - posY) * deltaDistY;
            }

            while (hit == 0) {
                if (sideDistX < sideDistY) {
                    sideDistX += deltaDistX;
                    mapX += stepX;
                    side = 0;
                } else {
                    sideDistY += deltaDistY;
                    mapY += stepY;
                    side = 1;
                }
                if (mapX < 0 || mapX >= MAP_WIDTH || mapY < 0 || mapY >= MAP_HEIGHT) {
                    break;
                }
                if (MAP[mapY][mapX] > 0) {
                    hit = MAP[mapY][mapX];
                }
            }

            if (side == 0) perpWallDist = (sideDistX - deltaDistX);
            else          perpWallDist = (sideDistY - deltaDistY);

            if (perpWallDist < 0.1f) perpWallDist = 0.1f;
            z_buffer[i] = perpWallDist;

            int lineHeight = (int)(240 / perpWallDist);

            int drawStart = -lineHeight / 2 + 240 / 2;
            if (drawStart < 0) drawStart = 0;
            int drawEnd = lineHeight / 2 + 240 / 2;
            if (drawEnd >= 240) drawEnd = 240 - 1;

            // Pick shaded wall colors based on hit type
            uint32_t wall_color;
            if (hit == 1) {
                // Concrete Grey
                wall_color = (side == 0) ? graphics_make_color(80, 85, 95, 255) : graphics_make_color(55, 60, 70, 255);
            } else if (hit == 2) {
                // Neon Cyan
                wall_color = (side == 0) ? graphics_make_color(0, 180, 255, 255) : graphics_make_color(0, 110, 170, 255);
            } else {
                // Defense Red
                wall_color = (side == 0) ? graphics_make_color(255, 50, 50, 255) : graphics_make_color(170, 30, 30, 255);
            }

            // Draw ceiling
            graphics_draw_box(disp, i * 2, 0, 2, drawStart, ceiling_color);
            // Draw wall
            graphics_draw_box(disp, i * 2, drawStart, 2, drawEnd - drawStart, wall_color);
            // Draw floor
            graphics_draw_box(disp, i * 2, drawEnd, 2, 240 - drawEnd, floor_color);
        }

        /* SPRITES RENDERING - CITIZENS */
        for (int k = 0; k < NUM_CITIZENS; k++) {
            float spriteX = citizens[k].x - posX;
            float spriteY = citizens[k].y - posY;

            float invDet = 1.0f / (planeX * dirY - dirX * planeY);
            float transformX = invDet * (dirY * spriteX - dirX * spriteY);
            float transformY = invDet * (-planeY * spriteX + planeX * spriteY);

            if (transformY > 0.1f && transformY < 12.0f) {
                int spriteScreenX = (int)((160 / 2) * (1.0f + transformX / transformY)) * 2;
                int spriteHeight = abs((int)(240 / transformY));
                int spriteWidth = spriteHeight;

                int drawStartY = -spriteHeight / 2 + 240 / 2;
                if (drawStartY < 0) drawStartY = 0;
                int drawEndY = spriteHeight / 2 + 240 / 2;
                if (drawEndY >= 240) drawEndY = 240 - 1;

                int drawStartX = -spriteWidth / 2 + spriteScreenX;
                if (drawStartX < 0) drawStartX = 0;
                int drawEndX = spriteWidth / 2 + spriteScreenX;
                if (drawEndX >= 320) drawEndX = 320 - 1;

                for (int stripe = drawStartX; stripe < drawEndX; stripe++) {
                    int col = stripe / 2;
                    if (col >= 0 && col < 160 && transformY < z_buffer[col]) {
                        // Draw body block
                        graphics_draw_box(disp, stripe, drawStartY, 1, drawEndY - drawStartY, citizens[k].color);
                        // Draw hair/face details for visual richness
                        int headHeight = (drawEndY - drawStartY) / 4;
                        graphics_draw_box(disp, stripe, drawStartY, 1, headHeight, graphics_make_color(220, 180, 20, 255));
                    }
                }

                // Render name above head
                if (spriteScreenX > 20 && spriteScreenX < 300) {
                    graphics_set_color(graphics_make_color(255, 255, 255, 255), graphics_make_color(0,0,0,0));
                    graphics_draw_text(disp, spriteScreenX - 20, drawStartY - 12, citizens[k].name);
                }
            }
        }

        /* RETICLE CROSSHAIR */
        uint32_t reticle_color = graphics_make_color(255, 50, 50, 180);
        graphics_draw_line(disp, 155, 120, 158, 120, reticle_color);
        graphics_draw_line(disp, 162, 120, 165, 120, reticle_color);
        graphics_draw_line(disp, 160, 115, 160, 118, reticle_color);
        graphics_draw_line(disp, 160, 122, 160, 125, reticle_color);

        /* HUD PANEL */
        draw_hud(disp, hp, shield, active_weapon);

        /* WEAPON OVERLAY */
        draw_weapon_hud(disp, active_weapon, bob_frame);

        /* MINI-MAP */
        draw_minimap(disp, posX, posY, dirX, dirY);

        /* SCREEN OVERLAYS: PROMPT OR DIALOGUE */
        if (state == STATE_EXPLORING) {
            int closest_idx = -1;
            float closest_dist = 999.0f;
            for (int k = 0; k < NUM_CITIZENS; k++) {
                float dx = citizens[k].x - posX;
                float dy = citizens[k].y - posY;
                float dist = sqrtf(dx*dx + dy*dy);
                if (dist < closest_dist) {
                    closest_dist = dist;
                    closest_idx = k;
                }
            }
            if (closest_idx != -1 && closest_dist < 1.3f) {
                char prompt_buf[48];
                sprintf(prompt_buf, "PRESS A TO TALK TO %s", citizens[closest_idx].name);
                graphics_set_color(graphics_make_color(220, 180, 20, 255), graphics_make_color(15, 15, 20, 200));
                graphics_draw_text(disp, 80, 140, prompt_buf);
            }
        } else {
            // Draw active dialogue
            draw_dialogue_box(disp, state, dialogue_citizen_idx, selected_choice);
        }

        /* Show frame count and system info at bottom-left */
        char fps_buf[32];
        sprintf(fps_buf, "TOKYO-3 GRID // F:%d", game_frame++);
        graphics_set_color(graphics_make_color(120, 120, 120, 255), graphics_make_color(0,0,0,0));
        graphics_draw_text(disp, 10, 228, fps_buf);

        /* Render buffer */
        display_show(disp);
    }

    return 0;
}
