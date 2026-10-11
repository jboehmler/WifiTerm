# Fix and improvement notes

Backlog of known problems and ideas. IDs are stable; details are in the analysis
file named in each row. Status: Open, Agreed (John said go), Done (version), Dropped.

## Fixes

| ID | Area | Summary | Source | Status |
|---|---|---|---|---|
| F-01 | firmware | 64-byte read buffer stalls SSL to UART path permanently | analysis-2026-10-11 | Open |
| F-02 | firmware | Concurrent mbedtls read/write on one context | analysis-2026-10-11 | Open |
| F-03 | firmware | vTaskSuspend of tasks inside mbedTLS on reset | analysis-2026-10-11 | Open |
| F-04 | firmware | Shared msglen/status race between producer and consumer | analysis-2026-10-11 | Open |
| F-05 | firmware | 255-byte reads can't fit 256-byte message buffer | analysis-2026-10-11 | Open |
| F-06 | firmware | 128-byte UART chunks dropped (no room for NUL) | analysis-2026-10-11 | Open |
| F-07 | firmware | String handling, not binary-safe | analysis-2026-10-11 | Open |
| F-08 | firmware | Device on console UART0 receives logs and boot output | analysis-2026-10-11 | Open |
| F-09 | firmware | esp_restart on station disconnect / 90 s idle | analysis-2026-10-11 | Open |
| F-10 | firmware | Write error default case leaves state RWOK | analysis-2026-10-11 | Open |
| F-11..F-17 | firmware | Hygiene items | analysis-2026-10-11 | Open |
| C-01..C-09, C-12 | client | Snapshot doesn't import/run | analysis-2026-10-11 | Open |
| C-10 | client | Task loop lock raises on first iteration | analysis-2026-10-11 | Open |
| C-11 | client | UTF-8 decode of split reads kills receive thread | analysis-2026-10-11 | Open |
| C-13 | client | macOS/Windows terminal classes are stubs | analysis-2026-10-11 | Open |

## Improvements

| ID | Summary | Status |
|---|---|---|
| I-01 | Single bridge task owns TLS; select() + stream buffers | Open |
| I-02 | Framed protocol (ADR-0003) so the firmware has no modes | Agreed |
| I-03 | Client: one stdin reader, terminal raw for whole session | Open |
| I-04 | Client: asyncio instead of the tasks/ thread framework | Open |
| I-05 | Escape key Ctrl-] instead of bare ESC (ADR-0005) | Agreed |
| I-06 | UART0 pin swap to GPIO13/15, logs on UART1 (ADR-0004) | Agreed |
| I-07 | Firmware command handling with NVS-backed UART and WiFi settings | Open |
| I-08 | Client logging at INFO by default, DEBUG on a flag | Open |
| I-09 | Binary file send in serial mode (DATA frames) | Later |
| I-10 | PC installer (pipx first, frozen installer later) | Later |
| I-11 | sdkconfig: log level INFO, consider MBEDTLS_SSL_IN_CONTENT_LEN 16384 -> RAM (about 20 KB per session) | Open |
| I-12 | GPIO-switched power/enable for the RS-232 chip: off through boot, on after UART swap+config. Suggested GPIO5 (D1) with pull-down. Avoids the break condition D8 (pulled low at reset) would otherwise send. Not in 0.1.0 code. | Open |
