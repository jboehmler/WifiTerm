# WiFi Terminal

An ESP8266 runs as a WiFi access point and TLS server. A Python client on the PC
connects to it. In serial mode every key goes straight to a device on the ESP8266's
RS-232 port; Ctrl-] switches to command mode for the ESP's own settings.

Read `START-HERE.md` first.

## Layout

| Path | What |
|---|---|
| `firmware/` | ESP8266_RTOS_SDK firmware (C). Build, flash, wiring: `firmware/README.md` |
| `client/` | PC client `wifiterm` (Python 3.10+, standard library only): `client/README.md` |
| `tools/` | `make-certs.sh`, `test-certs.sh`, `mock_esp.py` (ESP simulator), `run-tests.sh` |
| `tests/` | pytest (client, mock), gcc tests (firmware C), shared test vectors |
| `legacy/` | 0.1.0 code, kept for reference, not built |
| `docs/protocol.md` | Wire protocol and commands |
| `docs/decisions/` | Architecture decision records (ADRs) |
| `docs/NOTES.md` | Improvement and fix backlog, numbered |
| `CHANGELOG.md`, `VERSION` | Release history, current version (SemVer) |

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
