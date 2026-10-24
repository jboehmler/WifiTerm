# Changelog

All notable changes are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `hardware/rs232-shield/3d/`: printable STL of the assembled unit (board, jack, D1 mini) and a
  STEP of the board, for fit checks and case design.
- `hardware/reference/d1-mini-dimensions-bottom-view.png` (John): D1 mini drawing; USB socket is on
  the mini's underside. 3D model's D1 mini corrected to it.

## [0.0.1] - 2026-10-21

### Changed
- RS-232 board rev 0.2 (John: "under the mini with the rj-45 below the usb port"): 25.6 x 27.5 mm,
  the D1 mini's own width, mini plugged in on top; RJ45 jack moved to the underside below the USB
  port; no copper under the antenna; via keep-out under the jack. Same parts and netlist (the D1
  mini sockets are now J2/J3). DRC clean (copper), every pad's net checked, Gerbers rendered back.

## [0.0.0] - 2026-10-18
First release of the combined project package `wifiterm-0.0.0` (John, 2026-10-18). From here
`VERSION` numbers the whole package; firmware and client keep their own versions (0.2.0-rc.2
below is their history). No code changes.

### Changed
- Layout: `legacy/` is now `archive/0.1.0/`; `archive/wifiterm-0.1.0-original.tar` is John's
  original upload; `docs/rs232-prototype.md` moved to `hardware/rs232-prototype.md`.
- README shows the directory structure. The Docker SDK environment (esp8266-setup) stays a
  separate, generic project (John).

## [0.2.0-rc.2] - 2026-10-18

### Changed
- Firmware: `uart power off` holds device TX (D8) low until power returns, so a chip powered from
  a GPIO is not fed through its input (NOTES I-19).

### Added
- `hardware/rs232-shield/`: RS-232 base board rev 0.1 (TRS3243E, RJ45 jack for a straight cable
  to a Cisco-style console port, D1 mini on top clear of its antenna). Generated with KiCad 7 from
  `make_board.py`, routed with Freerouting, DRC clean (copper); Gerbers, BOM and CPL for JLCPCB.
- `docs/rs232-prototype.md`: wiring for the HiLetgo MAX3232 bench module. NOTES I-19, I-20.

### Added
- `docs/rs232-prototype.md`: bench prototypes for TRS3221E (I-13) and TRS3243E (I-15) on DIP
  breakouts: breakout links, soldering steps, pin-by-pin wiring, parts, bring-up checks.

### Changed
- ADR-0006 accepted by John (2026-10-12), all nine points; no code change.

## [0.2.0-rc.1] - 2026-10-11
Release candidate: everything below is tested on the PC (`bash tools/run-tests.sh`); the
firmware compiles against ESP8266_RTOS_SDK v3.4 but has not yet run on hardware. 0.2.0
follows once John's hardware test passes.

### Added
- **Firmware 0.2.0** (`firmware/`, R1 to R9, R12, ADR-0004, I-12): one bridge task with a
  select loop (no concurrent mbedTLS calls, no task suspension), framed protocol v1, UART0 on
  swapped pins D7/D8 with settings by command and NVS, `uart break`, RS-232 chip power on D1,
  UART receive errors as EVENTs, xon/xoff, logs on D4 plus LOG frames (`log on`), TLS with
  client certificate required, certificate expiry checked against a lower-bound clock,
  keepalive timeout, software watchdog, restart after repeated listen/accept failures, no
  restart on disconnect unless `set reboot-on-disconnect on`, reset reason in `info`, 3 s
  USB recovery window and FLASH-button reset. `firmware/README.md` covers build, flash, wiring.
- Portable firmware command handler (`firmware/main/cmd.c`) checked with gcc against
  `tests/vectors/commands.txt`, the same vectors the mock must pass (74 + 15 C tests).
- `tools/run-tests.sh`: every PC-side test in one command.
- ADR-0006: choices made during implementation, for John's review.
- `tools/make-certs.sh`: private CA, server and client certificates (RSA-2048 or ECDSA P-256,
  10 years) for the ESP8266 and for localhost testing, plus a `bad/` set that must be rejected
  (expired, wrong CA, self-signed, wrong IP). Writes to `certs/` (git-ignored).
- `tools/test-certs.sh`: proves good certificates pass and every bad one fails, both
  directions; local mode (openssl test server) or against the ESP8266. Checked: 8/8 for both key types.
- `Makefile`: John's project Makefile (make-based ESP8266_RTOS_SDK), unchanged.
- `tools/legacy-tests/`: John's earlier test scripts (openssl client/server, Python client/server,
  watch loops), unchanged. `shclient.sh`, which several of them call, was not supplied.
- `sdkconfig` from John (example WiFi SSID/password redacted).
- `START-HERE.md`: everything a new session needs.
- `docs/review-recommendations.md`: R1 to R25 for review, including expired certificates (R10) and unenforced client-cert check (R12).
- NOTES: I-12 chip power gating, I-13 TRS3221E with cable detect (wanted, later), parts pricing.
- `docs/protocol.md`: draft wire protocol v1 and command list.
- ADR-0004 (device on swapped UART0, console on UART1), ADR-0005 (client platform, Ctrl-] escape, pass-through).
- Protocol v1 framing in Python (`client/wifiterm/frames.py`) and portable C
  (`firmware/main/frames.c/.h`, no ESP headers), both tested against one shared vector file
  `tests/vectors/frames.txt`: pytest (`tests/client/test_frames.py`, 57 pass) and a gcc test
  with AddressSanitizer/UBSan (`make -C tests/firmware`, 55 pass).
- `tools/mock_esp.py` (R23): simulated ESP8266 for PC-only testing. TLS with required client
  certificate, HELLO/version negotiation, one client at a time, every ESP command,
  PING/PONG, LOG frames, reboot with reconnect, simulated devices `echo`, `fortigate`, `silent`,
  and options for failure tests (`--drop-after`, `--no-pong`, `--proto-min/max`).
- `tests/tools/test_mock_esp.py`: 31 tests, including good and bad certificates made fresh by
  `tools/make-certs.sh` on every run (`tests/conftest.py`).
- `tools/test-certs.sh -t mock`: the same 8 good/bad certificate checks against the mock,
  so John can check his own certificates on his PC before touching the ESP.
- PC client 0.2.0 (`client/`, R14 to R20): asyncio, one TLS session with HELLO and
  capabilities, raw terminal for the whole session (termios / msvcrt thread), Ctrl-] command
  mode with line editor (history, Tab, FortiGate-style `?`), all help on the PC, hold/live
  device output with `cmd*> ` prompt, `wifi set` with YES confirmation recorded in `wifihist`,
  automatic reconnect, keepalive, window title, visible portable profile folder with
  `--where/--export/--import`, `pyproject.toml` (`pipx install ./client`).
- Client tests: 63 more, including end-to-end runs of the real client against the mock
  (`tests/client/test_app.py`). Also checked by hand in a real pseudo-terminal and as a
  pip-installed command. Not yet run on Windows.
- `tools/make-certs.sh -p PROFILE` copies the PC's certificates into the client's profile folder.

### Changed
- Client HELLO carries `time=` (the ESP's clock lower bound); the mock speaks TLS 1.2 and closes
  a second client before TLS, like the firmware (ADR-0006). `docs/protocol.md` updated.
- Old firmware and client moved to `legacy/` (R24); the new firmware Makefile no longer pulls in
  `protocol_examples_common` (R25).
- `tools/test-certs.sh` stops with an error if its test server fails to start, instead of
  reporting every expected failure as correct.
- ADR-0003 framed protocol: Accepted.

## [0.1.0] - 2026-10-11

### Added
- `docs/analysis-2026-10-11.md`: first code review, focused on mode-switch fragility.
- `docs/NOTES.md`: numbered fix/improvement backlog (F-xx fixes, I-xx improvements).
- ADR-0001 (record decisions), ADR-0002 (baseline import), ADR-0003 (proposed: framed protocol).
- Baseline import of John's uploaded `wifiterm.tar` (firmware `main/`, client `client/`),
  unchanged. Editor swap files and logs excluded via `.gitignore`.
