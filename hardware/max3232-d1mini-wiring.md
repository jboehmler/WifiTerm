# Wiring the HiLetgo MAX3232 module to a D1 mini clone

- Board: HiLetgo ESP-12F Mini NodeMCU (a Wemos D1 mini clone); same pin labels as the D1 mini.
- Module: HiLetgo MAX3232 RS-232 to TTL converter with DB9 socket.
- Pins follow ADR-0004 (`docs/decisions/0004-uart-assignment-and-console.md`) and
  `firmware/main/config.h`: device UART is UART0 on the swapped pins.
- Status: **unverified against the module's silkscreen**; check the labels on your unit
  before powering up (see Notes).

## Wires

| # | Module pin | D1 mini pin | GPIO | Notes |
|---|---|---|---|---|
| 1 | GND | G | n/a | Common ground |
| 2 | VCC | 3V3 | n/a | Always on. For the gated bench setup use D1 (GPIO5) instead, see below |
| 3 | TXD (data out of the module, TTL level) | D7 | GPIO13 | ESP device RX (`PIN_DEVICE_RX`, chip R1OUT) |
| 4 | RXD (data into the module, TTL level) | D8 | GPIO15 | ESP device TX (`PIN_DEVICE_TX`, chip T1IN) |

Gated power (NOTES I-12, I-19): connect VCC to D1 (GPIO5, `PIN_CHIP_POWER`) instead of 3V3
so `uart power on|off` can switch the chip. The module draws little, but a GPIO is a weak
supply: if the module misbehaves, use 3V3 or a P-MOSFET as described in I-12.

## Diagram

```
   HiLetgo MAX3232 module              D1 mini clone (ESP-12F)
  +----------------------+           +------------------------+
  |                  GND +-----------+ G                      |
  |                  VCC +-----------+ 3V3   (or D1 = GPIO5)  |
  |  TTL out (TXD)       +-----------+ D7 = GPIO13  (ESP RX)  |
  |  TTL in  (RXD)       +-----------+ D8 = GPIO15  (ESP TX)  |
  |                      |           |                        |
  |  DB9 (female) ------ RS-232      |  USB: GPIO1/3, flash   |
  +----------------------+           |  and console           |
                                     +------------------------+
```

The same drawing as a picture: `max3232-d1mini-wiring.svg`.

## Notes

- GPIO15 (D8) must be low at reset. The board has a 10k pull-down on it already. Make sure
  the module's TXD/RXD input does not pull it high (some modules fit pull-ups), or the
  ESP8266 will not boot (ADR-0004).
- USB stays on GPIO1/3 for flashing and the console. ROM boot text never reaches the RS-232
  side because the device UART is swapped to GPIO13/15.
- If no data flows, swap the D7 and D8 wires: the HiLetgo TXD/RXD labels can be read from
  the module's or from the host's point of view.
- RTS/CTS flow control is **not supported in firmware 0.2.0** (`HAS_RTSCTS` off, no pins
  assigned), and this module only brings out TX/RX to the TTL header. Leave it unwired.
  For RTS/CTS see the TRS3243E option in `rs232-prototype.md` (I-15).
- The DB9 side is female and DCE-style: use a straight-through cable to a PC, a null-modem
  cable to another DTE.
- Default line settings are 9600 8N1, no flow control (ADR-0004).
