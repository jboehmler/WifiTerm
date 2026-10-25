# Host unit tests for the portable firmware modules (no ESP SDK needed).
# Usage: make -C tests/firmware          build into tests/firmware/build/ and run
# Warnings are errors, and AddressSanitizer/UBSan catch memory and overflow bugs.

SRC     := ../../firmware/main
BUILD   := build
CFLAGS  := -std=c99 -Wall -Wextra -Werror -O1 -g -fsanitize=address,undefined -I$(SRC)
TESTS   := test_frames test_cmd test_util test_cabledet test_led

.PHONY: all clean
all: $(addprefix $(BUILD)/,$(TESTS))
	@echo "== test_frames"; $(BUILD)/test_frames ../vectors/frames.txt
	@echo "== test_cmd"; $(BUILD)/test_cmd ../vectors/commands.txt
	@echo "== test_util"; $(BUILD)/test_util
	@echo "== test_cabledet"; $(BUILD)/test_cabledet
	@echo "== test_led"; $(BUILD)/test_led

$(BUILD)/test_frames: test_frames.c $(SRC)/frames.c $(SRC)/frames.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ test_frames.c $(SRC)/frames.c

$(BUILD)/test_cmd: test_cmd.c $(SRC)/cmd.c $(SRC)/cmd.h $(SRC)/cabledet.c $(SRC)/cabledet.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ test_cmd.c $(SRC)/cmd.c $(SRC)/cabledet.c

$(BUILD)/test_cabledet: test_cabledet.c $(SRC)/cabledet.c $(SRC)/cabledet.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ test_cabledet.c $(SRC)/cabledet.c

$(BUILD)/test_util: test_util.c $(SRC)/timeutil.c $(SRC)/frames.c | $(BUILD)
	$(CC) $(CFLAGS) -o $@ test_util.c $(SRC)/timeutil.c $(SRC)/frames.c

$(BUILD)/test_led: test_led.c $(SRC)/led.c $(SRC)/led.h $(SRC)/battery.c $(SRC)/battery.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ test_led.c $(SRC)/led.c $(SRC)/battery.c

$(BUILD):
	mkdir -p $@

clean:
	rm -rf $(BUILD)
