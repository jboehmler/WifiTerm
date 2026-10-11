# Recommended changes for review (excluding UART wiring)

- Date: 2026-10-11
- Baseline: 0.1.0. UART pins, chip and power gating are settled separately (ADR-0004, NOTES I-12/I-13).
- For each item John marks: **Accept**, **Reject**, **Modify** (with note), or **Later**.
  Accepted items become ADRs or NOTES entries and go into the version shown.

## Firmware

| ID | Recommendation | Fixes | Why | Target | John |
|---|---|---|---|---|---|
| R1 | One bridge task owns the TLS session: `select()` on the socket plus a task notification from the UART side; all `mbedtls_ssl_read/write` in that one task; no `vTaskSuspend`; on error close, free, back to `accept`. | F-02, F-03, F-10 | mbedTLS forbids concurrent read/write on one context; suspend can freeze a task holding a lock. | 0.2.0 | Accept (2026-10-11) |
| R2 | Byte streams instead of message buffers and C strings: `xStreamBuffer` UART-to-TLS and TLS-to-UART, `uint8_t` with explicit lengths, buffer sizes from one header. | F-01, F-04 to F-07 | Removes the 64-byte permanent stall, shared-length race, NUL truncation, dropped 128-byte chunks. Needed for binary file send later. | 0.2.0 | Accept (2026-10-11) |
| R3 | No reboot when the last station leaves or nobody connects in 90 s. Keep the AP up and wait. Reboot only on command or watchdog. | F-09 | A WiFi blip currently reboots the bridge. | 0.2.0 | Modify, accepted: no reboot on disconnect by default; task-watchdog check-in for bridge task; reboot after N consecutive accept/bind failures; record reset reason, shown in info; setting reboot-on-disconnect (default off) restores old behaviour. John added the old reboots because of hangs (2026-10-11) |
| R4 | Command handling in firmware per `docs/protocol.md` (frames, `info`, `uart ...`, `wifi ...`, `reboot`). | none (new) | Today commands go to the device. | 0.2.0 | Accept, plus PC-side help (2026-10-11): all help text lives in the client; help, ?, help <cmd>, FortiGate-style ? after a partial command; help keys. Client adapts via ESP capability list in HELLO (accepted) |
| R5 | Settings in NVS with a version number and defaults: device UART parameters, AP SSID/password/channel, power-enable pin and polarity. `nvs_flash_init()` at start, erase-and-retry on version mismatch. | F-14 | Configurable by command and survives reboot. | 0.2.0 | |
| R6 | Logging: default INFO, never log payload bytes or passwords at INFO, one TAG per module. LOG frames over WiFi depend on the open log-routing card. | F-13 | DEBUG logging of every buffer slows the bridge and leaks the password. | 0.2.0 | |
| R7 | Hygiene: `void app_main(void)`, task handle `&` fix, consistent `ssl_state_str`, rename `block10ms`, check stack high-water marks and report them in `info`. | F-11, F-12, F-14 to F-17 | Small, safe. | 0.2.0 | |
| R8 | Keepalive: client sends PING every 10 s; ESP drops a session with no traffic for 30 s and returns to `accept`. | none (new) | A PC that sleeps or walks away otherwise holds the only session forever. | 0.2.0 | |
| R9 | Report heap and uptime in `info`. Leave `MBEDTLS_SSL_IN_CONTENT_LEN` at 16384 for now (Python can't negotiate smaller records); revisit only if heap is short. | I-11 | About 20 KB per session on an 80 KB part; measure before changing. | 0.2.0 | |

## Security and certificates

| ID | Recommendation | Why | Target | John |
|---|---|---|---|---|
| R10 | **Regenerate all certificates.** Every certificate in 0.1.0 expired in April 2026 (`main/ca.crt` and `main/server.crt` 2026-04-24, `main/client.crt` 2026-04-21, `client/keys/localhost/ca.crt` 2026-04-22). TLS will fail today. Add `tools/make-certs.sh` (OpenSSL) that makes a private CA, server cert (SAN IP 192.168.4.1) and client cert, valid 10 years. | Can't connect with expired certs. | 0.2.0 | |
| R11 | Use ECDSA P-256 keys instead of RSA-2048. | Handshake on ESP8266 is several times faster with ECDSA, and uses less RAM. | 0.2.0 | |
| R12 | Actually require the client certificate: `mbedtls_ssl_conf_authmode(&conf, MBEDTLS_SSL_VERIFY_REQUIRED)`. The server never sets this, and the default for a server is not to verify, so today any TLS client that trusts the CA can connect. | The mutual authentication you set up isn't enforced. | 0.2.0 | |
| R13 | Give the client certificate a name (e.g. `wifiterm-client`) instead of the IP `192.168.4.2` as its CN. | The PC's address can change; the certificate, not the IP, should identify it. | 0.2.0 | |

## Client (PC)

| ID | Recommendation | Fixes | Why | Target | John |
|---|---|---|---|---|---|
| R14 | Rewrite on `asyncio`: one event loop with the TLS stream and the keyboard; replaces `tasks/`, `term/`, `wifiterm.py`, `ssltasks.py`, `termtasks.py`. | C-01 to C-12 | Removes the two-readers race and the pause/resume machinery; about 700 lines become about 300. | 0.2.0 | |
| R15 | Terminal in raw mode for the whole session; command mode uses a small built-in line editor (backspace, Ctrl-U, history with up/down). Windows via `msvcrt`, Linux/macOS via `termios`. | C-13 | Nothing changes tty mode mid-session, so nothing can race. | 0.2.0 | |
| R16 | Bytes end to end; decode only for display with `errors="replace"`. | C-11 | Device output that isn't UTF-8 can't crash the client. | 0.2.0 | |
| R17 | Command layer: a plain table of name, aliases, help text and handler, keeping your command names and `wifihist`. Drop the decorator/`DataLib` framework. | none | Simpler to extend; `?` and `help` built in. | 0.2.0 | |
| R18 | Automatic reconnect: on link loss, show `[link lost, reconnecting]`, retry every 2 s, show `[connected]`. | none (new) | WiFi blips no longer end the session. | 0.2.0 | |
| R19 | Settings file per user (host, port, cert paths, escape key, log level) plus command-line overrides. | C-06, C-07 | No more hard-coded ports and paths. | 0.2.0 | |
| R20 | Packaging with `pyproject.toml`, entry point `wifiterm`, installable with `pipx`; frozen installer later (I-10). | none | First step toward your installer. | 0.2.0 | |

## Testing (no hardware needed)

| ID | Recommendation | Why | Target | John |
|---|---|---|---|---|
| R21 | Frame encoder/decoder in the client with unit tests (`pytest`). | Protocol bugs caught on the PC. | 0.2.0 | |
| R22 | Firmware frame parser and command parser in plain C with no ESP headers, compiled and unit-tested on the PC. | Most firmware logic tested without flashing. | 0.2.0 | |
| R23 | A Python mock of the ESP8266 server (same protocol, loops DATA back, answers commands) so the client can be run end to end on one PC. | You can try the client before any build or flash. | 0.2.0 | |

## Repository

| ID | Recommendation | Target | John |
|---|---|---|---|
| R24 | Move the old code to `legacy/` when 0.2.0 lands (kept for reference, not built). Remove `main/archive/` from the build tree. | 0.2.0 | |
| R25 | Add a top-level `Makefile` for the firmware project (`PROJECT_NAME := wifiterm`, the make-based SDK layout), missing from the upload. | 0.2.0 | |
