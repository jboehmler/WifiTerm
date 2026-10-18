# RS-232 base board, revision 0.1 (TRS3243E, RJ45 console jack)

- Date: 2026-10-18
- Status: Design-rule check passes (copper); not yet built. For John's JLCPCB quote.

A 55 x 36 mm two-layer board. The Wemos D1 mini plugs in **on top**, antenna up and clear of
the board (the board is cut away under the antenna), USB end flush with the board edge.
An RJ45 jack on the same end takes a **standard straight 8-wire Ethernet cable** to a
Cisco-style RJ45 console port (FortiGate, Cisco, Juniper and most network gear).

![top](jlcpcb/view-top.png)

## Files for JLCPCB (`jlcpcb/`)

| File | Upload as |
|---|---|
| `rs232-shield-gerbers.zip` | Gerber files (copper, mask, paste, silk, outline, drill) |
| `bom.csv` | BOM (SMT parts, LCSC numbers) |
| `cpl.csv` | Pick-and-place (CPL) |
| `view-top.png`, `view-bottom.png` | Preview only, not uploaded |

## Ordering

1. Upload the Gerber zip. Defaults are right: 2 layers, 1.6 mm, any colour. Quantity 5 is
   the minimum.
2. Turn on **PCB Assembly**, **top side**, then upload `bom.csv` and `cpl.csv`.
3. On the placement preview, check **U1's pin 1** (dot or chamfer) sits at the pad marked with
   the small triangle, top-left of U1. KiCad and JLCPCB sometimes disagree on rotation for
   SSOP parts; if it is off, rotate U1 in the preview until it matches.
4. Parts are JLCPCB "basic" except U1 (extended, one-time loading fee). LCSC stock of U1
   (C544326) was 153 on 2026-10-11.
5. Buy the RJ45 jack with the order (JLCPCB parts or LCSC): **CONNFLY DS1128-09-S8B8S,
   LCSC C77851**. Plain jack (no Ethernet transformer, which would block RS-232); LEDs unused.

## Parts

| Ref | Part | LCSC | Fitted by |
|---|---|---|---|
| U1 | TI TRS3243ECDBR, RS-232 3 drivers / 5 receivers, SSOP-28 | C544326 | JLCPCB |
| C1-C5 | 100 nF X7R 0603 (charge pump, bypass) | C14663 | JLCPCB |
| C6 | 1 uF 0603 (bypass; TI requires 1 uF for the IEC ESD rating) | C15849 | JLCPCB |
| R1, R2 | 10k 0603, pull-ups on D7 and D6 (chip outputs float when it is off) | C25804 | JLCPCB |
| R3 | 10k 0603, pull-down on D1 (chip off through reset) | C25804 | JLCPCB |
| J1 | RJ45 jack, CONNFLY DS1128-09-S8B8S | C77851 | John |
| M1 | 2 x 8-pin female sockets (come with the D1 mini) | - | John |

## Connections

| D1 mini | Board | Function |
|---|---|---|
| D8 (GPIO15) | U1 DIN1 | Data to the device |
| D7 (GPIO13) | U1 ROUT1, R1 pull-up | Data from the device |
| D5 (GPIO14) | U1 DIN2 | RTS out (future `flow=rtscts`) |
| D6 (GPIO12) | U1 ROUT2, R2 pull-up | CTS in (future `flow=rtscts`) |
| D1 (GPIO5) | U1 FORCEOFF + FORCEON, R3 pull-down | Chip on when high (`CHIP_POWER_ON_LEVEL 1`) |
| D2 (GPIO4) | U1 INVALID | Low when nothing drives any RS-232 input (cable detect) |
| 3V3, G | U1 VCC, ground | Power |

| RJ45 pin | Device console port pin (straight cable) | Board signal |
|---|---|---|
| 1 | RTS (device output) | U1 RIN2 -> our CTS |
| 2 | DTR (device output) | U1 RIN3 (spare; helps cable detect) |
| 3 | TxD (device output) | U1 RIN1 -> our RX |
| 4, 5 | GND | GND |
| 6 | RxD (device input) | U1 DOUT1 <- our TX |
| 7 | DSR (device input) | U1 DOUT3, always on (DIN3 grounded) |
| 8 | CTS (device input) | U1 DOUT2 <- our RTS |

The device-side pinout is the common Cisco console pinout (Juniper documents the same:
1 RTS, 2 DTR, 3 TxD, 4/5 GND, 6 RxD, 7 DSR/DCD, 8 CTS). Do **not** plug this jack into an
Ethernet switch port.

## Assembly by John
1. Solder J1 (12 pins, 2 shield tabs, 2 plastic posts snap in).
2. Solder the D1 mini's female sockets to this board, and the D1 mini's male pins to the D1 mini
   (pins pointing down). Plug the D1 mini in with its antenna end over the cut-away corner.

## Firmware
- Set `CHIP_POWER_ON_LEVEL 1` in `firmware/main/config.h`.
- RTS/CTS (D5/D6) and cable detect (D2) are wired but not yet used by the firmware.

## How it is made
`make_board.py` (KiCad 7 Python API) holds the parts, positions and netlist; `build.sh`
places, routes with Freerouting 1.9.0, pours ground on both layers, runs KiCad's
design-rule check (`drc-report.txt`) and writes `jlcpcb/`. There is no KiCad schematic
file; the netlist in `make_board.py` and the tables above are the schematic. Open
`rs232-shield.kicad_pcb` in KiCad to inspect or edit the layout.

DRC: 0 copper errors, 0 unconnected. Remaining warnings are silkscreen only (reference
labels clipped by pads, D1 mini outline drawn past the board edge), which JLCPCB clips.

## Checked, and not yet checked
- Checked: TRS3243E pin functions against TI's datasheet; every pad's net against the
  netlist (script check, 0 mismatches); Gerbers rendered back with gerbv.
- Inferred, please confirm on JLCPCB's 3D preview: the RJ45 opening faces the board edge.
  The KiCad footprint marks the front only indirectly (silkscreen left open on that side).
- Not confirmed: that DS1128-09 has no Ethernet transformer. LCSC lists it as a plain jack and
  its drawing lists no magnetics, but the datasheet PDF could not be read here.
- Not built or powered.
