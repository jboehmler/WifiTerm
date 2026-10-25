# WiFi Terminal

An ESP8266 runs as a WiFi access point and TLS server. A Python client on the PC
connects to it. In serial mode every key goes straight to a device on the ESP8266's
RS-232 port; Ctrl-] switches to command mode for the ESP's own settings.

Read `START-HERE.md` first.

## Layout

| Path | What |
|---|---|
```
wifiterm-<version>/
  README.md  START-HERE.md  CHANGELOG.md  VERSION
  firmware/   ESP8266 firmware (C): main/, Makefile, sdkconfig.defaults
  client/     PC terminal client (Python package)
  hardware/   rs232-shield/ (board + JLCPCB files), rs232-prototype.md (bench wiring)
  tools/      make-certs, test-certs, signing key + sign-fw, mock ESP, run-tests
  tests/      client, mock, firmware C tests, shared vectors
  docs/       protocol, decisions (ADRs), NOTES backlog, reviews, plans
  archive/    John's original files: 0.1.0 code and the original upload
```

| Path | What |
|---|---|
| `firmware/` | ESP8266_RTOS_SDK firmware (C). Build, flash, wiring: `firmware/README.md` |
| `client/` | PC client `wifiterm` (Python 3.10+, standard library only): `client/README.md` |
| `hardware/rs232-shield/` | RS-232 base board (TRS3243E, RJ45 console jack) and its JLCPCB files: `README.md` there |
| `hardware/rs232-prototype.md` | Bench wiring: MAX3232 module, TRS3221E/TRS3243E breakouts |
| `tools/` | `make-certs.sh`, `test-certs.sh`, `make-signing-key.sh` + `sign-fw.sh` (firmware updates, ADR-0008), `mock_esp.py` (ESP simulator), `run-tests.sh` |
| `tests/` | pytest (client, mock), gcc tests (firmware C), shared test vectors |
| `archive/` | Originals, not built: `0.1.0/` (John's code), `wifiterm-0.1.0-original.tar` (as uploaded) |
| `docs/protocol.md` | Wire protocol and commands |
| `docs/decisions/` | Architecture decision records (ADRs) |
| `docs/NOTES.md` | Improvement and fix backlog, numbered |
| `CHANGELOG.md`, `VERSION` | Release history, current version (SemVer) |

Versions: `VERSION` numbers the whole package (0.0.0 is the first combined release). The
parts keep their own: firmware and client 0.2.0 (`FW_VERSION`, `client/wifiterm/__init__.py`),
board rev 0.2.

The firmware builds with ESP8266_RTOS_SDK v3.4 (make). The generic Docker build environment
for that SDK is a separate project, **esp8266-setup** (`esp make` in `firmware/`); it is not
part of this package.

## Quick start
```
bash tools/run-tests.sh                       # everything that can be tested without hardware
tools/make-certs.sh -p ~/wifiterm             # certificates (+ copies the PC's into the client profile)
pipx install ./client                         # the client
python3 tools/mock_esp.py --certs certs/localhost --device fortigate &   # try without hardware
wifiterm --host 127.0.0.1
```

## Working rules
See `START-HERE.md`. Private keys are never committed (`.gitignore`).
