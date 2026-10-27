# Changelog

All notable changes are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- The bench build now also starts with the RS-232 chip off until the bridge starts, then
  switches it on (`uart power on` is its default); previously `uartdev_start()` switched it on.

### Decided
- ADR-0007 (accepted by John): RJ45 console jack takes a straight 8-wire Ethernet patch cable
  to a Cisco-pinout console port; crossover, rollover and 4-wire cables not supported.

### Changed
- rs232-shield silkscreen (John, 2026-10-27: "all the lettering should be clearly visible"): the
  designators C1-C6, R1-R3 and U1 were printed over their own pads. Now C1-C6 stand upright between
  their pads and U1, R1 and R3 sit above their pads and R2 below, U1 is in the middle of its body,
  all 0.8 mm (U1 1.0 mm) with 0.15 mm strokes and checked clear of every pad and of each other
  (`place_labels()` in make_board.py; `python3 make_board.py labels` re-applies it to the routed board
  without re-routing). U1's silk outline moved to the fab layer. Copper, mask, drill, BOM and CPL are
  unchanged; only the top silkscreen Gerber is new, so the JLCPCB zip changed. KiCad's silkscreen
  warnings fell from 12 to 0 (the J2/J3 socket outlines still touch the board edge, as before).

### Added
- `hardware/rs232-shield/rs232-shield-views.docx` (John, 2026-10-27): Word picture book with the
  board top and bottom as fabricated, a parts layout with designators and the parts table, and
  front, side, top and bottom views of the assembled unit. Built by `doc/make_doc.py` and
  `doc/make_views.py` from the Gerbers, BOM, CPL and 3D model (rev 0.2).
- Firmware update over WiFi with signed images (ADR-0008, NOTES I-25; John: "1"). Client
  `fw update FILE` (asks first, shows progress, reconnects on the new firmware) and `fw`.
  Firmware: `fwup.c` (portable, host-tested) and `ota.c`; FW frame type 0x09; capability
  `fw.update` only with the new two-slot flash layout (`CONFIG_PARTITION_TABLE_TWO_OTA`). The
  signature is checked before erasing; a new firmware that never accepts a client within 3
  boots falls back to the old one. New tools/make-signing-key.sh and tools/sign-fw.sh. The
  simulator takes `--fw-pub` and simulates the slots, the trial and the fallback.
  Untested on hardware; moving to the new layout needs one USB flash after `make erase_flash`.
- Green state LED on D0 (NOTES I-22, John 2026-10-25): steady while booting, slow blink waiting
  for a WiFi station, a wink every 2 s with a station but no terminal, regular 2.5 Hz blink with
  the terminal connected, erratic flicker on traffic. A failed boot step blinks its number then
  pauses 2 s (1 settings, 2 WiFi, 3 TLS; 3 also for 10 s after a failed handshake). New portable
  `led.c` (host-tested) and `statusled.c`.
- Battery level (NOTES I-24): A0 read at boot and once a second (`battery.c`, host-tested;
  `batmon.c`). At boot 1-4 blinks show the charge in quarters, then steady for at least 3 s.
  `info` adds `bat=V/%`; EVENT `battery low` (3.50 V) and `battery empty: shutting down`
  (3.35 V for 10 s), after which everything switches off until the cell is back above 3.70 V.
  No cell fitted: nothing changes. Mock `mock battery <mV>` hook; client shows both EVENTs.
- `bat`, `bat cal <mV>`, `bat cal reset` (John: "1 ok"): show the battery and correct the A0
  scale from a meter reading (within +-10 %, saved in NVS as `batcal`). Capability `bat`.
  Client: help for both, and `status` shows the battery line (John: "6 ok").
- Mock (simulator, John: "simulator needs updating too"): `--battery <mV>`, `bat` commands
  matching the firmware, and the green LED simulated and logged (`led: ...`), with a
  `mock led` hook; TLS failure shows code 3, empty battery turns it off.
- `hardware/prototype/` (John, 2026-10-25): a bench prototype from the D1 mini and HiLetgo
  MAX3232 module that behaves like the rs232-shield rev 0.3. Two schematics
  (`make_schematics.py`, schemdraw): module power switch (PNP), discrete cable detector (NPN on
  the console's TxD), yellow LED for "chip on AND console", green state LED on D0, and the
  battery option (TP4056 USB-C module, switch in the battery branch only, battery level on
  A0). README has the parts list, wiring, console-cable check and first tests.
- Firmware `make BOARD=proto` for that prototype: bench power polarity, cable detect on D2
  with low = console. Device bytes and UART error events are dropped while the chip is off.
- Wrong-port safety, NOTES I-21 option 1 (John: "1 agreed"; defaults accepted): `uart power auto`.
  The RS-232 chip stays off until the TRS3243E's INVALID pin (D2) shows a console's RS-232
  levels for 1 s, and goes off 3 s after they stop, so a cable in an Ethernet port is never
  driven. Default at boot on the shield; saved with `uart save`. `uart power` with no argument
  shows mode, chip and cable. EVENT `cable console` / `cable none` on each change and after
  HELLO; capability `cabledetect`. New `firmware/main/cabledet.c` (portable, host-tested),
  `make BOARD=shield` build switch, mock `--caps ...,cabledetect` with a `mock cable` hook,
  client help and friendlier cable messages. Untested on hardware: INVALID must still work
  with the chip in shutdown.
  With cable detect, `uart power on` is a temporary override (John 2026-10-25): `uart save` does
  not store it and says so, and a reboot or `uart revert` goes back to the saved mode or `auto`.
- `hardware/reference/`: RJ45 jack drawings from John (CONNFLY DS1128-09 / C77851 and
  Ruichuan RCH-56-31 / C708625). J1's footprint matches C77851 in every dimension; the jack has
  no magnetics. Board README updated; C708625 noted as a tight-fitting plastic alternative.
- `hardware/rs232-shield/3d/`: printable STL of the assembled unit (board, jack, D1 mini) and a
  STEP of the board, for fit checks and case design.
- `hardware/reference/d1-mini-dimensions-bottom-view.png` (John): D1 mini drawing; USB socket is on
  the mini's underside. 3D model's D1 mini corrected to it.
- `hardware/adapter-build/`: soldering layout for a hand-built TRS3243E on an SSOP-28 adapter with
  leaded parts (`layout.png`, from `make_layout.py`).
  Word build guide `trs3243e-adapter-build.docx` (parts, steps, wiring, checks; `make_doc.py`).
  Mouser BOM for ten builds at price breaks (`mouser-bom-10.csv`); MAX3243ECDBR, Vishay 100 nF, RJHSE-5380 jack.

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
