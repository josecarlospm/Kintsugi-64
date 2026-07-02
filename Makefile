SOURCE_DIR = src
BUILD_DIR = build
include $(N64_INST)/include/n64.mk

# Strict warnings and errors
CFLAGS += -Wall -Werror -Wextra -Wno-unused-parameter -Wno-unused-variable -Wno-unused-but-set-variable

# Source files
SOURCES = $(shell find $(SOURCE_DIR) -name '*.c')
OBJS = $(SOURCES:$(SOURCE_DIR)/%.c=$(BUILD_DIR)/%.o)

all: game.z64

$(BUILD_DIR)/game.elf: $(OBJS)
	$(LD) -o $@ $^ $(LDFLAGS)

clean:
	rm -rf $(BUILD_DIR) *.z64 src/assets src/assets.h models/*.obj models/*.mtl models/*.png

.PHONY: all clean


