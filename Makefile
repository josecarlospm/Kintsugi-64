SOURCE_DIR = src
BUILD_DIR = build
include $(N64_INST)/include/n64.mk

OBJS = $(BUILD_DIR)/main.o

all: game.z64

$(BUILD_DIR)/game.elf: $(OBJS)
	$(LD) -o $@ $^ $(LDFLAGS)

clean:
	rm -rf $(BUILD_DIR) *.z64

.PHONY: all clean
