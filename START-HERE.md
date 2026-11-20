# Start here (context for a new session)

Read this first if you are picking up the WiFi Terminal project in a new chat.

## Goal
An ESP8266 (NodeMCU for development, Wemos D1 mini for deployment) runs as a WiFi
access point and TLS server. The PC joins its WiFi as a client and runs a Python
terminal client. In serial mode every keystroke goes to an RS-232 device (first use: a
FortiGate console, where a lone `?` must bring up help). In command mode the user
configures the ESP8266 (device UART settings, WiFi settings, reboot). Later: binary file
send in serial mode, and a PC installer.

## John's working rules
- Claude may compile (including the ESP8266 RTOS SDK firmware) and run tests in its own sandbox without asking (John, 2026-10-11). Flashing is done by John; Claude says when a build is ready to flash.
- Anything that leaves the project (GitHub, outside services) needs John's permission.
- Key and certificate generation is part of the user workflow, so Claude runs `tools/make-certs.sh` and `tools/test-certs.sh` in its own test cycle with throwaway certs (John, 2026-10-11). John makes the real device keys himself.
- Claude runs as much testing as possible itself (PC-side tests, mock ESP, gcc unit tests) to cut download/test/feedback cycles (John, 2026-10-11).
- Ask rather than assume. Offer better approaches when you see them.
- "cr" from John means "consider and reply". "a." means "accept".
- Maintain this package: SemVer `VERSION`, git history, `CHANGELOG.md`, ADRs in
  `docs/decisions/`, backlog in `docs/NOTES.md`. Every change gets a CHANGELOG entry.
- Repository stays in this package only (no GitHub for now).
- Packaging: build release archives with `git archive` (see "Building a release archive" below), never plain `tar` of the shared folder, which drops execute bits (gave "Permission denied" on `tools/make-certs.sh`).
- Debugging is currently done over the ESP8266's USB/UART.
- All code gets Doxygen comments, liberal but concise (file, function, struct, non-obvious logic).
- No hidden files or folders; everything (settings, keys, history) must be packageable to move to another PC.

## Where things stand (2026-10-11)
- **Package 0.0.1 (2026-10-21)** combines everything (0.0.1: board rev 0.2 under the D1 mini); firmware/client 0.2.0-rc.2 are written and
  tested on the PC, not yet run on hardware. Next step is
  John's: flash it and try it (order in `docs/plan-0.2.0.md`, "What John tests").
- Building the firmware: John's generic Docker SDK environment is its own project,
  esp8266-setup (separate package, not in this tree).
- Layout: `firmware/` (new firmware, see `firmware/README.md` for build, flash, wiring),
  `client/` (new PC client, `client/README.md`), `tools/` (`make-certs.sh`, `test-certs.sh`,
  `mock_esp.py`, `run-tests.sh`), `tests/` (pytest, gcc tests, shared vectors),
  `hardware/` (RS-232 board, bench wiring), `archive/` (John's original 0.1.0 files, reference only).
- `bash tools/run-tests.sh` runs every PC-side test (about 270): client, mock ESP, firmware C
  code under gcc, and good/bad certificate checks. Run it after any change.
- `docs/protocol.md`: framed protocol v1 (final), plus two additions from implementation.
- `docs/decisions/`: ADR-0003 framed protocol, ADR-0004 UART pins (swapped UART0, D7 = RX
  GPIO13, D8 = TX GPIO15, logs on D4/GPIO2 and over WiFi via `log on`), ADR-0005 client
  platform and Ctrl-], ADR-0006 implementation choices (accepted 2026-10-12).
- `docs/review-recommendations.md`: R1 to R25, all decided by John.
- `docs/analysis-2026-10-11.md`: review of the 0.1.0 code. `docs/NOTES.md`: backlog.

## Claude's sandbox setup for firmware compile checks
Not part of the package; recreate in a new session if needed. ESP8266_RTOS_SDK cloned from
GitHub (`release/v3.4`, submodules except coap), Ubuntu packages `gcc-xtensa-lx106` and
`binutils-xtensa-lx106`, newlib headers from `espressif/newlib-esp32` (tag `esp-2020r3`)
with a wrapper that adds them and sets 32-bit types to `int` like Espressif's toolchain.
dl.espressif.com is blocked there, so the real toolchain is unavailable: the check
compiles `firmware/main` only; it cannot link a flashable image.

Board design (`hardware/rs232-shield/`): Ubuntu packages `kicad kicad-footprints kicad-symbols
kicad-packages3d xvfb librsvg2-bin` (KiCad 7.0), Freerouting 1.9.0 jar from GitHub releases,
then `FREEROUTING=/path/freerouting-1.9.0.jar bash hardware/rs232-shield/build.sh`.

## Hardware notes
- RS-232 chip today: MAX3232 (no shutdown pin). Preferred later: TI TRS3221E (shutdown on
  D1/GPIO5, INVALID cable-detect on D2/GPIO4), John wants cable detection (I-13).
- RS-232 chip must be off through ESP reset (I-12).
- Bench: HiLetgo MAX3232 module (`hardware/rs232-prototype.md`, wiring to the D1 mini: `hardware/max3232-d1mini-wiring.md`). Board: `hardware/rs232-shield/`
  rev 0.2, TRS3243E, under the D1 mini, RJ45 Cisco-style console jack below USB, for JLCPCB (I-20).
  Both need `CHIP_POWER_ON_LEVEL 1` in `firmware/main/config.h`.
- 0.2.0 uses `firmware/sdkconfig.defaults` (`make defconfig`); John's 0.1.0 `sdkconfig` is in
  `archive/0.1.0/` with example WiFi credentials redacted.

## Open questions
- Hardware results from John's first flash.
- Later: RS-232 chip choice (I-13/I-15), power saving (I-14), file send (I-09), installer (I-10).

## Not included
Private keys and certificates. Make them with `tools/make-certs.sh` (output in `../private/certs/`,
outside the project); `firmware/main/` needs ca.crt, server.crt, server.key; the client profile
folder's `keys/` needs ca.crt, client.crt, client.key (`make-certs.sh -p` copies those).

## Building a release archive
The shared project folder does not keep file modes, but git does (scripts are mode 100755 in the index).
Build from a committed tree so modes are preserved, then verify:

    git tag vX.Y.Z
    git archive --format=tar.gz --prefix=wifiterm-X.Y.Z/ -o ../downloads/wifiterm-X.Y.Z.tar.gz vX.Y.Z
    tar -tvzf ../downloads/wifiterm-X.Y.Z.tar.gz | grep -E 'tools/.*\.sh'   # expect -rwxr-xr-x

Note: `git archive` omits `.git`; for an archive with history, also ship `git bundle create`.
New scripts: `git update-index --chmod=+x <file>` before committing.
