# Plan for 0.2.0

- Date: 2026-10-11
- Basis: review R1 to R25 (all decided), ADR-0003/0004/0005, `docs/protocol.md`.
- Code style: Doxygen comments in all C and Python, liberal but concise.
- Rule: Claude writes and commits code. **No ESP build, no flashing, and no running of
  compiled tests without John's go-ahead.** Pure-Python tests (pytest) run only if John agrees too.

## Steps (each is one or more commits with a CHANGELOG entry)

1. **Repository layout** (R24, R25): move `main/`, `client/` to `legacy/`; new `firmware/`
   (Makefile without `protocol_examples_common`, `main/`), `client/` (pyproject, package
   `wifiterm/`), `tools/`, `tests/`.
2. **Shared protocol** (R21, R22): Python `wifiterm/frames.py` and C `firmware/main/frames.c`
   (no ESP headers), with pytest and a gcc test program using the same test vectors.
3. **Mock ESP8266** (R23): `tools/mock_esp.py`, TLS with `localhost` certs, echo device,
   all commands, FortiGate-style `?` reply, capability list.
4. **Client** (R14 to R20): asyncio session, raw terminal for whole session, Ctrl-] escape,
   line editor, command table with help/`?`/capabilities, frozen settings + logged state object,
   reconnect, visible portable profile folder with `--where/--export/--import`, `wifihist`.
5. **Firmware** (R1 to R9, R12, ADR-0004, I-12): single bridge task with `select()`,
   stream buffers, UART0 swap to D7/D8, logs on UART1/D4 and LOG frames, chip power pin
   (D1, polarity setting), NVS settings, command handler, keepalive, watchdog check-in,
   reset reason, `reboot-on-disconnect`, `VERIFY_REQUIRED`.
6. **Docs**: README usage, wiring diagram for D1/D4/D7/D8, update START-HERE, protocol
   marked final, version 0.2.0 tagged.

## What John tests, in order
1. Client against the mock on one PC (no hardware).
2. `make-certs.sh` then `test-certs.sh` locally.
3. With John's OK: ESP build and flash, then `test-certs.sh -t wifiterm`, then the client
   against the ESP with a loopback plug (TX to RX), then the FortiGate.

## Not in 0.2.0
Binary file send (I-09), frozen installer (I-10), TRS3221E cable detect (I-13, firmware will
have the setting ready), RTS/CTS flow control.
