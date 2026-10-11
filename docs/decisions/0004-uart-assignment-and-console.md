# ADR-0004: Device on swapped UART0, console on UART1

- Status: Accepted (John, 2026-10-11): swapped UART0 pins, see Resolved below
- Date: 2026-10-11

## Context
`sdkconfig` (0.1.0) has the console on UART0 at 74880 baud, `CONFIG_ESP_UART0_SWAP_IO`
not set, ROM UART printing enabled and log level DEBUG. `uart.c` uses `UART_NUM_0` with no
pin swap. So the RS-232 device currently shares pins GPIO1/GPIO3 with the ROM boot messages
and every ESP_LOG line. John thought this had been changed; it hasn't in this code/config.
John wants the UART used to be visible in the code.

## Decision
- RS-232 data on UART0 **swapped** pins: RX = GPIO13, TX = GPIO15 (`uart_enable_swap()` called
  explicitly in `uart.c`, with a named constant `DEVICE_UART = UART_NUM_0` and a comment
  naming the pins).
- Console/logs on UART1 TX (GPIO2) via `CONFIG_ESP_CONSOLE_UART_CUSTOM`, `..._NUM=1`.
  UART1 is transmit-only; that's fine for logs.
- Log level default INFO; data payloads are never logged at INFO.
- Device UART parameters (baud, data bits, parity, stop bits, flow control) set by command
  and saved in NVS. Default 9600 8N1, no flow control (FortiGate console default).

## Consequences
- Wiring: device moves to GPIO13/GPIO15 through the level shifter. GPIO15 must be low at boot
  (the usual 10k pull-down stays; the RS-232 driver input must not pull it high).
- ROM boot output still appears on GPIO1 at 74880 but never reaches the device.
- Flashing still uses GPIO1/GPIO3 as before.

## Open (2026-10-11)
John debugs over the USB adapter on UART0's default pins. After the swap the USB port shows
flashing and ROM boot output only. Proposed: logs on UART1/GPIO2 for a second adapter, plus
LOG frames over WiFi on request. Awaiting John's choice.
John's stated intent (2026-10-11): unplug the USB-UART and put a TTL-to-RS-232 chip on the
device link, which must be bidirectional. Both options are full duplex on UART0; the open
question is pins: swapped GPIO13/15 (recommended, device never sees ROM boot output at
74880) vs default GPIO1/3 (ROM boot output reaches the device on every reset; conflicts with
on-board USB chips). Awaiting John's choice and board model.

## Resolved (2026-10-11)
John: boards are NodeMCU (dev) and Wemos D1 mini (likely deployment); he had intended the
UART swap to keep boot junk off the device. Decision: swapped UART0 pins, called right after
boot in `uart.c`. Pin map (same labels on both boards):

| Signal | GPIO | NodeMCU / Wemos label | Connects to |
|---|---|---|---|
| Device RX (into ESP) | GPIO13 | D7 | RS-232 chip receiver output (R1OUT) |
| Device TX (out of ESP) | GPIO15 | D8 | RS-232 chip transmitter input (T1IN) |
| Log TX (UART1) | GPIO2 | D4 | Optional second USB-serial RX; on-board LED also blinks |

GPIO15 has a 10k pull-down on both boards and must be low at reset; the RS-232 module
must not pull T1IN high (some modules fit pull-ups), or the ESP8266 will not boot.
The USB socket stays connected to GPIO1/3 for flashing and ROM boot output.
