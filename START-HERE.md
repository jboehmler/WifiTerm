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
- Builds and flashing/downloading to the device only when John agrees, every time.
- Ask rather than assume. Offer better approaches when you see them.
- "cr" from John means "consider and reply". "a." means "accept".
- Maintain this package: SemVer `VERSION`, git history, `CHANGELOG.md`, ADRs in
  `docs/decisions/`, backlog in `docs/NOTES.md`. Every change gets a CHANGELOG entry.
- Repository stays in this package only (no GitHub for now).
- Debugging is currently done over the ESP8266's USB/UART.

## Where things stand
- `0.1.0` = John's original code, unchanged (`main/` firmware, `client/` PC client).
  The client snapshot does not run as packaged; all certificates expired April 2026.
- `docs/analysis-2026-10-11.md`: review of the original code (why mode switching is fragile).
- `docs/protocol.md`: agreed direction, framed protocol v1 (draft wording).
- `docs/review-recommendations.md`: R1 to R25, being reviewed with John as a dialog.
  The "John" column records each decision.
- `docs/decisions/`: ADR-0003 framed protocol (accepted), ADR-0004 UART pins (accepted:
  swapped UART0, D7 = RX GPIO13, D8 = TX GPIO15, logs on D4/GPIO2 and over WiFi via `log on`), ADR-0005 client
  platform, Ctrl-] escape, pass-through (accepted).
- `docs/NOTES.md`: fixes F-xx/C-xx, improvements I-xx, chip pricing.

## Hardware notes
- RS-232 chip today: MAX3232 (no shutdown pin). Preferred later: TI TRS3221E (shutdown on
  D1/GPIO5, INVALID cable-detect on D2/GPIO4), John wants cable detection (I-13).
- RS-232 chip must be off through ESP reset (I-12).
- `sdkconfig` is John's (make-based ESP8266_RTOS_SDK); example WiFi credentials redacted.

## Open questions
- Which review items (R1 to R25) John accepts.

## Not included
Private keys (`main/server.key`, `client/keys/**/client.key`). New ones will come from
`tools/make-certs.sh` once R10 is agreed.
