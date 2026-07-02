SOURCE_DIR = src
BUILD_DIR = build
include $(N64_INST)/include/n64.mk

# Run asset generation if python3 is available
ifeq ($(shell which python3 >/dev/null 2>&1 && echo "yes"),yes)
dummy := $(shell python3 scripts/compile_assets.py)
endif

SOURCES = $(shell find $(SOURCE_DIR) -name '*.c')
OBJS = $(SOURCES:$(SOURCE_DIR)/%.c=$(BUILD_DIR)/%.o)

all: game.z64

$(BUILD_DIR)/game.elf: $(OBJS)
	$(LD) -o $@ $^ $(LDFLAGS)

clean:
	rm -rf $(BUILD_DIR) *.z64 src/assets src/assets.h

.PHONY: all clean

