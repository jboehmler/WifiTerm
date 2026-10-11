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

### Changed
- ADR-0003 framed protocol: Accepted.

## [0.1.0] - 2026-10-11

### Added
- `docs/analysis-2026-10-11.md`: first code review, focused on mode-switch fragility.
- `docs/NOTES.md`: numbered fix/improvement backlog (F-xx fixes, I-xx improvements).
- ADR-0001 (record decisions), ADR-0002 (baseline import), ADR-0003 (proposed: framed protocol).
- Baseline import of John's uploaded `wifiterm.tar` (firmware `main/`, client `client/`),
  unchanged. Editor swap files and logs excluded via `.gitignore`.
