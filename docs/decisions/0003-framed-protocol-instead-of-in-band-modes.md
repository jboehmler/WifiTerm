# ADR-0003: Framed protocol instead of in-band mode switching

- Status: Proposed (awaiting John)
- Date: 2026-10-11

## Context
Today command mode exists only in the PC client. Mode changes are announced by sending
the literal text `<CMD MODE>\r\n` / `<RAW MODE>\r\n` down the same byte stream that goes
to the RS-232 device, and commands such as `ping` or `reboot` travel the same way. The
firmware has no way to tell commands from data, and the client cannot tell command
replies from device output. See analysis 2026-10-11, section 2.

## Options
1. **Length-prefixed frames on the one TLS connection** (recommended).
   Every message is `type(1) | len(2, big-endian) | payload`. Types: DATA (to/from the
   RS-232 port), CMD (client to ESP), RESP (ESP to client), EVENT (ESP to client: UART
   errors, link state). The firmware has no modes at all; "mode" is purely a client UI state.
2. **Two TCP/TLS ports**: one for raw data, one for commands. Simple, but two handshakes
   (slow on ESP8266, roughly 1 to 3 s each and about 20 KB RAM each) and two sockets to keep in sync.
3. **Telnet IAC escaping / RFC 2217**. A standard (pyserial speaks `rfc2217://`), but escaping
   every 0xFF byte and the telnet option negotiation is more firmware code than option 1,
   and TLS breaks compatibility with stock tools anyway.

## Decision
Pending.

## Consequences (if option 1)
Breaks compatibility with the current client and firmware, so both change together under
a 0.2.0 version. Binary-safe, no escape characters, no mode state on the ESP8266.
