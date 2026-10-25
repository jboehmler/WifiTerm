# WiFi Terminal firmware (ESP8266, 0.2.0)

ESP8266_RTOS_SDK v3.x, make-based (as John's 0.1.0 setup). One bridge task moves bytes
between the TLS session and the RS-232 device as frames (`docs/protocol.md`).

## Build and flash
```
# 1. Certificates (once; keep certs/ca/ca.key somewhere safe)
tools/make-certs.sh -p ~/wifiterm            # also copies the PC's keys into the client profile
cp certs/wifiterm/{ca.crt,server.crt,server.key} firmware/main/

# 2. Build (first time: sdkconfig from sdkconfig.defaults)
cd firmware
make defconfig
make -j4                 # bench build (MAX3232 module, P-MOSFET power, no cable detect)
make -j4 BOARD=proto     # prototype build (hardware/prototype: MAX3232 module + cable detect)
make -j4 BOARD=shield    # rs232-shield build (TRS3243E; run `make clean` when switching)

# 3. Flash and watch (USB on GPIO1/3, as before)
make flash
```
After flashing, the access point is `WIFITERM`, password `WifiTerm` (see ADR-0006 point 4).
Logs come out on **D4 (GPIO2) at 74880 baud**: connect a second USB-serial adapter's RX to D4
and GND to see them, or use `log on` in the client.

## Wiring (NodeMCU and Wemos D1 mini use the same labels)

| Label | GPIO | Signal | Connect to |
|---|---|---|---|
| D7 | 13 | Device RX (into ESP) | RS-232 chip R1OUT |
| D8 | 15 | Device TX (out of ESP) | RS-232 chip T1IN (must not be pulled high: GPIO15 low at boot) |
| D1 | 5 | RS-232 chip power | Bench: P-MOSFET gate (10k pull-up to 3.3 V = off through reset). Shield: TRS3243E FORCEON+FORCEOFF (high = on) |
| D4 | 2 | Log TX (UART1, 74880) | Optional second USB-serial RX; also the on-board LED |
| D3 | 0 | FLASH button | On the board; hold 5 s at boot to reset all settings |
| D2 | 4 | Cable detect | Shield only: TRS3243E INVALID (high = console seen; drives `uart power auto`, NOTES I-21) |
| D0 | 16 | Green state LED | 330 ohm to the LED, high = on (NOTES I-22) |
| A0 | ADC | Battery level | Battery build: 100k from the cell (with the D1's own divider, 4.2 V = full scale; NOTES I-24). Nothing fitted = no battery |
| USB | 1/3 | Flashing, ROM boot text, recovery menu | As before |

```
  ESP8266 (Wemos / NodeMCU)              RS-232 chip (MAX3232)          Device
  (which DB9 pins are RX/TX depends on the device and cable; check its manual)
  D8  GPIO15 TX  ------------------>  T1IN      T1OUT  ------------->  device RX
  D7  GPIO13 RX  <------------------  R1OUT     R1IN   <-------------  device TX
  D1  GPIO5  ----> P-MOSFET gate (pull-up) ---> chip VCC
  GND ----------------------------------------- GND ----------------- GND
```

## Boot sequence
1. Logs start on D4. The RS-232 chip is off (D1 high with the MOSFET).
2. **Recovery window, 3 s:** the USB port (74880 baud) shows `wifiterm 0.2.0: press r for recovery`.
   `r` opens a menu: show SSID/password, reset WiFi, reset all, continue. Or hold FLASH (D3)
   for 5 s to reset all settings; D4 then blinks fast.
3. UART0 gets the saved serial settings (default 9600,8,N,1), pins swap to D7/D8, chip on.
4. Access point, TLS server on port 8443 (client certificate required), bridge task.

## Source files (`main/`)

| File | What | Tested on the PC |
|---|---|---|
| `frames.c/.h` | Frame encoder/decoder, HELLO helpers | yes, `tests/firmware/test_frames.c` |
| `cmd.c/.h` | All commands, validation, replies | yes, `test_cmd.c` + shared vectors with the mock |
| `timeutil.c/.h` | Build-time parsing for the clock lower bound | yes, `test_util.c` |
| `bridge.c/.h` | The bridge task: select loop, session, keepalive, watchdog, clock | compile only |
| `tls.c/.h` | mbedTLS server, client certificate required | compile only |
| `uartdev.c/.h` | UART0 swap, settings, break, power pin, error events | compile only |
| `settings.c/.h` | NVS storage | compile only |
| `logfwd.c/.h` | Logs to D4 and LOG frames | compile only |
| `recovery.c/.h` | Boot recovery window | compile only |
| `wifi_ap.c/.h` | Access point | compile only |
| `led.c/.h` | Green state LED patterns, failure codes, battery blinks | yes, `test_led.c` |
| `battery.c/.h` | Battery voltage, percent, low and empty checks | yes, `test_led.c` |
| `statusled.c/.h` | Drives D0 from `led.c` on a 10 ms timer | compile only |
| `batmon.c/.h` | Reads A0 | compile only |
| `config.h` | Version, pins, ports, sizes | |
| `app_main.c` | Boot order | compile only |

## What was checked before handing over
- `bash tools/run-tests.sh`: Python, gcc and certificate tests.
- Every `main/` file compiles with no warnings against ESP8266_RTOS_SDK v3.4 (release branch)
  using `-Wall -Wextra`, in Claude's sandbox. That sandbox has no Espressif toolchain or C
  library (download blocked), so it used Ubuntu's `gcc-xtensa-lx106` 13.2 with newlib
  headers: good for catching code errors, **not** a binary to flash. The image to flash
  comes from John's own toolchain.
- Not checked without hardware: RAM headroom during the TLS handshake, real UART timing,
  the recovery window, the power pin.
