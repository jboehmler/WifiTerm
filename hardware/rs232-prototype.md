# RS-232 chip prototypes: TRS3221E and TRS3243E (I-13, I-15)

- Date: 2026-10-18
- Status: Prototype plan for John's bench build; small-batch PCB comes after both are proven.
- Sources: TI datasheets SLLS792C (TRS3221E) and TRS3243E rev E (pin tables, function
  tables and capacitor values checked 2026-10-18).

Two versions, built the same way (chip on a DIP breakout, on a breadboard next to the
Wemos D1 mini or NodeMCU):

| | Option 1: TRS3221E | Option 2: TRS3243E |
|---|---|---|
| Use | Console (TX, RX) | Console plus RTS/CTS (I-15) |
| Drivers / receivers | 1 / 1 | 3 / 5 |
| Shutdown (FORCEOFF) | yes | yes |
| Cable detect (INVALID) | yes | yes |
| Package (LCSC part) | TSSOP-16, 0.65 mm (TRS3221EIPWR) | SSOP-28, 0.65 mm (TRS3243ECDBR) |
| Price, LCSC 2026-10-11 | $0.86 | $0.48 on sale (list $1.76) |
| Firmware 0.2.0 support | full, after `CHIP_POWER_ON_LEVEL 1` | console, shutdown; RTS/CTS needs firmware work |

Both run from the ESP's 3.3 V and need only 0.1 uF charge-pump capacitors at 3.3 V.

## Breakout boards

| For | Board | Notes |
|---|---|---|
| TRS3221E (TSSOP-16) | [ProtoSupplies SOIC/TSSOP-16 to DIP, 5-pack, $0.99](https://protosupplies.com/product/pcb-soic-tssop-16-to-dip-adapter-enig/) | TSSOP-16 on one side, SOIC-16 on the other; 0.5 in row spacing; headers not included |
| TRS3221E (TSSOP-16) | [Chip Quik PA0034 at Digi-Key](https://www.digikey.com.mx/en/products/detail/chip-quik-inc/PA0034/5014708) | TSSOP-16 0.65 mm only |
| TRS3243E (SSOP-28) | [MikroE MIKROE-309 TSSOP/SSOP-28 to DIP28 300 mil, $6](https://www.mikroe.com/tssop-ssop-28-to-dip28-300mil-adapter) | Takes both SSOP-28 and TSSOP-28 |

Also needed: 0.1 in male pin headers (straight, 2 x 8 or 2 x 14; machined round pins are
nicer in a breadboard).

## How to use a breakout

Tools: fine-tip iron (about 320 C), thin solder (0.3 to 0.5 mm), flux pen or gel, solder
wick, tweezers, a magnifier or phone camera, multimeter.

1. **Pick the right side.** Use the side whose pads match the chip (0.65 mm for both chips
   here). The DIP pin numbers on the breakout match the chip's pin numbers; check the
   silkscreen.
2. **Flux the pads**, then put a little solder on **one corner pad only**.
3. **Place the chip** with tweezers, pin 1 (dot or chamfered edge) on the pad marked 1.
   Reheat the tinned corner pad so that one pin sticks. Check under magnification that every
   pin sits on its pad; reheat and nudge if not.
4. **Tack the opposite corner**, check alignment again.
5. **Solder the rest**: more flux, then either touch each pin, or drag a slightly loaded tip
   along each row. Bridges between pins are normal at this point.
6. **Remove bridges** with flux and solder wick, pressing the wick lightly on the row.
7. **Inspect** each pin under magnification: a small fillet on every pin, no bridges.
   Then use the meter: no continuity between neighbouring DIP pins (except pins tied inside
   the chip, none on these two), and continuity from each chip pin to its DIP pin.
8. **Headers**: push the headers into a breadboard with the right spacing, lay the breakout
   on them chip side up, and solder. The breadboard keeps the pins straight and parallel.
9. Clean off flux with isopropyl alcohol.

## Wiring common to both

| ESP (label, GPIO) | Connects to | Why |
|---|---|---|
| 3V3 | chip VCC; 0.1 uF + 1 uF to GND at the chip | Supply and bypass (the 1 uF is what TI asks for to meet the IEC ESD rating) |
| GND | chip GND, DB9 pin 5 | One signal ground |
| D8, GPIO15 (device TX) | DIN / DIN1 | Data to the device |
| D7, GPIO13 (device RX) | ROUT / ROUT1, **10k pull-up to 3V3** | Data from the device; the pull-up holds the line idle while the chip is off (its outputs float then) |
| D1, GPIO5 (chip power) | FORCEOFF **and** FORCEON, **10k pull-down to GND** | Chip off through reset; firmware drives it high to turn on. Tying FORCEON to FORCEOFF turns auto-powerdown off while on, so the driver never sleeps mid-session |
| D2, GPIO4 (cable detect) | INVALID | Low when no RS-232 signal on any receiver input for 30 us (firmware reads it later, I-13) |

Firmware: set `CHIP_POWER_ON_LEVEL 1` in `firmware/main/config.h` (0.2.0 defaults to 0 for
the MAX3232 + P-MOSFET). The ESP side of both chips is 3.3 V logic, so no level shifting.

**DB9 connector: male, wired as a PC (DTE)**, so a standard FortiGate/Cisco console cable
(RJ45 to DB9 female) plugs straight in: pin 2 = RXD (in), 3 = TXD (out), 5 = GND,
7 = RTS (out), 8 = CTS (in).

Use ceramic X7R capacitors (no polarity). If electrolytic or tantalum are used for the
charge pump, the V- capacitor's **positive** side goes to GND.

## Option 1: TRS3221E (TSSOP-16)

| Pin | Name | Connect to |
|---|---|---|
| 1 | EN | GND (receiver output always enabled; active low) |
| 2 | C1+ | C1 0.1 uF to pin 4 |
| 3 | V+ | C3 0.1 uF to GND |
| 4 | C1- | C1 |
| 5 | C2+ | C2 0.1 uF to pin 6 |
| 6 | C2- | C2 |
| 7 | V- | C4 0.1 uF to GND |
| 8 | RIN | DB9 pin 2 (RXD) |
| 9 | ROUT | D7, with 10k pull-up to 3V3 |
| 10 | INVALID | D2 |
| 11 | DIN | D8 |
| 12 | FORCEON | pin 16 |
| 13 | DOUT | DB9 pin 3 (TXD) |
| 14 | GND | GND, DB9 pin 5 |
| 15 | VCC | 3V3, 0.1 uF + 1 uF to GND |
| 16 | FORCEOFF | D1, 10k pull-down to GND; pin 12 |

Parts: TRS3221EIPWR, breakout, 4 x 0.1 uF + 1 x 0.1 uF + 1 x 1 uF ceramic, 2 x 10k,
DB9 male, headers, jumper wire.

## Option 2: TRS3243E (SSOP-28)

| Pin | Name | Connect to |
|---|---|---|
| 1 | C2+ | C2 0.1 uF to pin 2 |
| 2 | C2- | C2 |
| 3 | V- | C4 0.1 uF to GND |
| 4 | RIN1 | DB9 pin 2 (RXD) |
| 5 | RIN2 | DB9 pin 8 (CTS) |
| 6, 7, 8 | RIN3, RIN4, RIN5 | open (internal pull-downs); spare for DCD/DSR/RI later |
| 9 | DOUT1 | DB9 pin 3 (TXD) |
| 10 | DOUT2 | DB9 pin 7 (RTS) |
| 11 | DOUT3 | open; spare for DTR later |
| 12 | DIN3 | GND (unused input, do not leave floating) |
| 13 | DIN2 | D5, GPIO14 (RTS out) |
| 14 | DIN1 | D8 |
| 15, 16, 17 | ROUT5, ROUT4, ROUT3 | open |
| 18 | ROUT2 | D6, GPIO12 (CTS in), 10k pull-up to 3V3 (reads "not clear" while the chip is off) |
| 19 | ROUT1 | D7, with 10k pull-up to 3V3 |
| 20 | ROUT2B | open (stays active even in shutdown; could wake the ESP on CTS later) |
| 21 | INVALID | D2 |
| 22 | FORCEOFF | D1, 10k pull-down to GND; pin 23 |
| 23 | FORCEON | pin 22 |
| 24 | C1- | C1 |
| 25 | GND | GND, DB9 pin 5 |
| 26 | VCC | 3V3, 0.1 uF + 1 uF to GND |
| 27 | V+ | C3 0.1 uF to GND |
| 28 | C1+ | C1 0.1 uF to pin 24 |

Parts: TRS3243ECDBR, MIKROE-309, 4 x 0.1 uF + 1 x 0.1 uF + 1 x 1 uF ceramic, 3 x 10k,
DB9 male, headers, jumper wire.

Firmware: 0.2.0 treats this board as a console with shutdown. RTS/CTS on D5/D6 is the
planned `flow=rtscts` (`docs/protocol.md`); it needs `HAVE_RTSCTS 1` plus the GPIO flow code,
not written yet.

## Bring-up check (both boards, before connecting the ESP)

1. 3.3 V to VCC, FORCEOFF and FORCEON jumpered to 3.3 V (chip on).
2. Measure V+ about +5.5 V and V- about -5.5 V. If not: a charge-pump capacitor or a bridge.
3. DIN to GND: DOUT about +5.5 V. DIN to 3.3 V: DOUT about -5.5 V (RS-232 inverts).
4. Jumper DB9 pin 2 to 3 (loopback). Without anything else connected, INVALID should be high
   while DOUT drives RIN, and low with the jumper removed.
5. FORCEOFF to GND: supply current drops to about 1 uA; ROUT floats (the pull-up holds it high).
6. Then wire to the ESP as above and run the hardware test (loopback, then the FortiGate).

## Bench alternative: HiLetgo MAX3232 module (John, 2026-10-18)
John chose a ready-made MAX3232 module (DB9) instead of the breakouts.
- VCC to 3V3 (not 5V), GND to G, module TTL output to D7, D8 to module TTL input through 1k for
  the first test. Module "TXD"/"RXD" labels vary: if a DB9 pin 2-3 loopback gives no echo, swap.
- FortiGate console cable (RJ45 to DB9 female) needs the module's TX on DB9 pin 3. With the
  module powered, the TX pin idles at about -5.5 V: pin 3 = use a male-male gender changer,
  pin 2 = use a male-male null-modem adapter.
- Powering the module from D1 works on the bench (MAX3232 a few mA; GPIO about 12 mA) with
  `CHIP_POWER_ON_LEVEL 1`, but see NOTES I-19 (back-powering through D8).

## Small-batch board
Done as `hardware/rs232-shield/` (TRS3243E, RJ45 console jack instead of DB9, D1 mini on top).
