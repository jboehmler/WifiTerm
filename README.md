# WiFi Terminal

An ESP8266 runs as a WiFi access point and TLS server. A Python client on the PC
connects to it and either sends commands (command mode) or passes typed
characters through to a device on the ESP8266's RS-232 port (serial/raw mode).

Read `START-HERE.md` first.

## Layout

| Path | What |
|---|---|
| `main/` | ESP8266_RTOS_SDK firmware component (C, FreeRTOS, mbedTLS) |
| `client/` | PC client (Python 3.10+) |
| `docs/analysis-*.md` | Code reviews and analyses |
| `docs/decisions/` | Architecture decision records (ADRs) |
| `docs/NOTES.md` | Improvement and fix backlog, numbered |
| `CHANGELOG.md` | Release history |
| `VERSION` | Current package version (SemVer) |

## Working rules

- No builds and no flashing unless John agrees first.
- Ask rather than assume.
- Every change gets a CHANGELOG entry; every design choice gets an ADR.

## Not in the repository

Private keys (`main/server.key`, `client/keys/**/client.key`) are deliberately
excluded by `.gitignore`. The firmware build expects `main/server.key`.
