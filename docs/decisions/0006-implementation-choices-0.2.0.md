# ADR-0006: Choices made while implementing 0.2.0

- Status: Accepted (John, 2026-10-12, all nine points)
- Date: 2026-10-11

## Context
Writing the 0.2.0 firmware against the real ESP8266_RTOS_SDK v3.4 headers turned up a few
points the protocol and review had not settled. Each choice below is in the code now and
is easy to change if John prefers otherwise.

## Decisions

1. **A second PC is closed before TLS, not sent EVENT `busy`.** Two TLS sessions do not fit
   in the ESP8266's RAM (about 40 KB free with WiFi up; one ECDSA handshake plus buffers
   uses most of it). The firmware accepts the TCP connection and closes it at once. The
   client reports "ESP closed the connection during setup: another PC may be connected, or
   the ESP rejected this PC's certificate". EVENT `busy` stays defined for later firmware.
   The mock does the same by default (`--busy event` gives the old behaviour).

2. **Certificate dates are checked against a lower-bound clock.** The ESP8266 has no
   real-time clock and starts at 1970, so `MBEDTLS_HAVE_TIME_DATE` alone would reject every
   certificate as "not yet valid", and without it expired certificates would pass.
   The firmware sets its clock at boot to the later of its build time and the last time a
   client reported; the client HELLO now carries `time=<unix seconds>` (an extra key, which
   older firmware ignores). "Not yet valid" is ignored; "expired" is enforced. The time is
   saved to NVS at most once per hour of clock advance, to spare the flash.

3. **TLS 1.2.** mbedTLS 2 on the ESP8266 has no TLS 1.3. The client allows 1.2 and up; the
   mock is limited to 1.2 so its behaviour (including how a rejected client certificate
   shows up) matches the firmware.

4. **Access point settings are kept by the firmware in NVS** (namespace `wifiterm`), and the
   WiFi driver is told not to store anything (`WIFI_STORAGE_RAM`). Consequence: **after
   flashing 0.2.0 the access point starts as `WIFITERM` / `WifiTerm`** even if 0.1.0 had
   been given another name, because 0.1.0's settings were stored by the WiFi driver.
   Use `wifi set` (or the recovery menu) to change it again.

5. **Chip power pin D1 is active-low by default** (`CHIP_POWER_ON_LEVEL 0` in `config.h`),
   matching the P-MOSFET plan for the MAX3232 (I-12). With a TRS3221E (FORCEOFF, I-13) set
   it to 1. If nothing is wired to D1 the pin is harmless.

6. **Device output with no PC connected is discarded**, so the UART buffer never overflows
   while nobody is watching.

7. **`sdkconfig.defaults` instead of a full `sdkconfig`.** Only the settings that matter are
   recorded (console on UART1, log levels, TLS memory, certificate dates). `make defconfig`
   builds the full file for whatever SDK version is installed.

8. **SSIDs cannot contain spaces** for now: commands are split on spaces. A quoting rule can
   be added if needed.

9. **The mock ESP needs Python 3.11** (it uses `StreamWriter.start_tls` to refuse a second
   client before TLS). The client itself still needs only 3.10.

## Consequences
`docs/protocol.md` is updated for points 1 and 2. Everything here is covered by tests
except what needs hardware (RAM use, real UART timing, the recovery window).
