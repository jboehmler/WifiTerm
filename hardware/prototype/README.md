# Prototype: D1 mini + HiLetgo MAX3232 module (2026-10-25)

This is a bench prototype built from the Amazon modules and through-hole parts. It behaves
like the rs232-shield rev 0.3, so the firmware and the LED behaviour can be tried before
any boards are ordered (John, 2026-10-25).

Schematics (from `make_schematics.py`, needs `pip install schemdraw` and `rsvg-convert`):
- [prototype-sheet1-core.png](prototype-sheet1-core.png): RS-232 module power, cable
  detect, yellow LED and green LED.
- [prototype-sheet2-battery.png](prototype-sheet2-battery.png): the battery option.

The sheets connect each circuit by **net name** (D1, D2, VSW, DET ...). The module
wiring is in the table below.

Firmware: `make BOARD=proto` (`firmware/README.md`). Run `make clean` when changing board.

## How it matches the final board

| Function | rs232-shield rev 0.3 | Prototype | Difference |
|---|---|---|---|
| Chip power | TRS3243E FORCEOFF on D1 (high = on) | Q1 PNP switches the module's VCC (D1 low = on) | Polarity only; the firmware build sets it |
| Cable detect | TRS3243E INVALID on D2 (high = valid, both polarities above 2.7 V) | Q2 sees the console's idle TxD below about -1.4 V; DET low = console | Sees only negative (idle) levels. C1 holds DET low through data bits. A console idles negative, so it acts the same |
| Yellow LED | MMBT3904 from INVALID, fed from D1 | Q3 PNP from DET, fed from VSW | Same rule: chip on AND console seen |
| Green LED | D0 → 330 → LED | Same | None |
| RJ45 console | RJ45 jack, straight Ethernet cable to a Cisco-style console | The module's DB9 plus a Cisco console cable (RJ45 to DB9) | See "Console cable" below |
| Battery option | Charger IC, P-FET, USB-C on the board | TP4056 USB-C module, D5 Schottky for the P-FET | 0.3 V lost in D5; module's own charge LEDs |

## Parts (all through-hole; resistors 1/4 W)

| Ref | Part | Notes |
|---|---|---|
| | D1 mini (HiLetgo), MAX3232 module (HiLetgo) | Already have |
| Q1, Q3 | 2N3906 PNP | TO-92 |
| Q2 | 2N3904 NPN | TO-92 |
| D3 | 1N4148 | |
| R1 | 1k | Q1 base |
| R2, R4 | 10k | |
| R5 | 47k | DET pull-up |
| R6 | 22k | Q3 base |
| R7, R8 | 330 | LED current, about 4 mA |
| C1 | 1 uF ceramic | DET filter |
| LED1 | yellow, 3 or 5 mm | Power: chip on AND console seen |
| LED2 | green, 3 or 5 mm | State (NOTES I-22) |
| **Battery option** | | |
| | TP4056 USB-C charger module **with protection** (DW01 + 8205; pads IN+/IN-, B+/B-, OUT+/OUT-) | Its USB-C is the unit's charge and power port |
| | LiPo 3.7 V cell, any size (e.g. 500-1000 mAh) | |
| D4, D5 | 1N5817 Schottky | |
| SW1 | small slide switch | Battery branch only |
| R9 | 100k | Battery voltage to A0 |

## Wiring

| From | To | Note |
|---|---|---|
| D1 mini 3V3 | Q1 emitter, R2, R5 | |
| D1 mini GND | Module GND, Q2 base, C1, LED cathodes; battery option: TP4056 **OUT-** | One ground |
| D1 mini D1 (GPIO5) | R1 | Module power |
| D1 mini D2 (GPIO4) | DET (Q2 collector, R5, C1, R6) | Cable detect |
| D1 mini D7 (GPIO13) | Module TTL pin wired to MAX3232 **pin 12** (R1OUT) | Device RX |
| D1 mini D8 (GPIO15) | Module TTL pin wired to MAX3232 **pin 11** (T1IN) | Device TX |
| D1 mini D0 (GPIO16) | R8 | Green LED |
| Module VCC | VSW: Q1 collector, Q3 emitter | Module now powered only through Q1 |
| MAX3232 **pin 13** (R1IN) | R4 (CON_TXD) | Solder to the chip pin, or to the DB9 pin that beeps to it |
| Battery option: D4 and D5 cathodes | D1 mini 5V | |
| Battery option: TP4056 OUT+ | SW1 and R9 | R9's other end to A0 |

Module TTL labels (TXD/RXD) mean different things on different modules. Use a meter to
find which header pin goes to chip pin 11 and which to pin 12.

Do **not** connect TP4056 IN- to the D1 ground. IN- is the cell's negative before the
protection switch, so tying it to ground would bypass the over-discharge protection.
With USB plugged in, the system current returns through OUT-, which works whenever the
protection switch is closed (normal).

## Console cable

The final unit takes a straight Ethernet cable to a Cisco-style console. On the
prototype, a standard Cisco console cable (RJ45 to DB9 female) on the module's DB9 does
the same job. That cable expects a PC-style male DB9: pin 3 TxD out, pin 2 RxD in,
pin 5 GND.

Check the module before plugging in:
1. Power it with nothing connected. The DB9 pin that reads about -5 V to ground is the
   module's TxD (MAX3232 pin 14).
2. If that pin is 3 and the connector is male, the cable plugs straight in.
3. If the connector is female, use a male-male gender changer. If TxD is on pin 2, use a
   null-modem adapter instead.

## First tests (after `make BOARD=proto` and flashing)

1. No cable: the yellow LED is off; `uart power` shows `mode=auto chip=off cable=none`.
2. Plug into a switch console: after about 1 s the yellow LED lights and the client shows
   "console detected"; type and get the prompt.
3. Unplug: after about 3 s the yellow LED goes off and the client shows "no console detected".
4. Plug into a normal Ethernet port by mistake: the yellow LED stays off; `uart power`
   shows `chip=off`.
5. `uart power on` with no cable: chip on, yellow LED still off (no console seen).
   `uart save`, then reboot: it comes back in auto.
6. Battery option: unplug USB with SW1 on and the unit keeps running; with SW1 off it
   stops; plug in USB with SW1 off and it runs and charges.
7. Green state LED: steady while booting, slow blink until a phone or PC joins the WiFi, a
   wink every 2 s once one has, a regular fast blink with the terminal connected, and a
   flicker while typing or while the device sends.
8. Battery option: at switch-on, 1-4 quick blinks show the charge in quarters, then steady
   for 3 s. `info` shows `bat=`. With a bench supply in place of the cell, 3.45 V gives
   "battery low" in the client, and 3.30 V for 10 s gives "battery empty" and the unit goes
   dark; raise it above 3.70 V and it restarts.
