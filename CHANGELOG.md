# Changelog

All notable changes are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `sdkconfig` from John (example WiFi SSID/password redacted).
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
