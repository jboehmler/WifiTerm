# Host unit tests for the portable firmware modules (no ESP SDK needed).
# Usage: make -C tests/firmware          build into tests/firmware/build/ and run
# Warnings are errors, and AddressSanitizer/UBSan catch memory and overflow bugs.

SRC     := ../../firmware/main
BUILD   := build
CFLAGS  := -std=c99 -Wall -Wextra -Werror -O1 -g -fsanitize=address,undefined -I$(SRC)
TESTS   := test_frames

.PHONY: all clean
all: $(addprefix $(BUILD)/,$(TESTS))
	@for t in $^; do echo "== $$t"; $$t ../vectors/frames.txt || exit 1; done

$(BUILD)/test_frames: test_frames.c $(SRC)/frames.c $(SRC)/frames.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ test_frames.c $(SRC)/frames.c

$(BUILD):
	mkdir -p $@

clean:
	rm -rf $(BUILD)
