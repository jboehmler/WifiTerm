# Changelog

All notable changes are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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
  certificate, HELLO/version negotiation, one client at a time (EVENT busy), every ESP command,
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
