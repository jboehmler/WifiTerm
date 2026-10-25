# ADR-0007: RJ45 console jack, straight Ethernet cable to a Cisco-pinout port

- Status: Accepted (John, 2026-10-25: "agreed. lock it in.")
- Date: 2026-10-25

## Context
The terminal talks to network gear through its RJ45 console port. RJ45 console ports follow
Cisco's pinout almost everywhere (checked 2026-10-24: Juniper, Extreme Networks, Fortinet,
HP ProCurve; see hardware/rs232-shield/README.md). John wants a standard Ethernet patch cable,
no special console cable.

## Decision
1. The board's RJ45 jack is wired as the mirror of a Cisco console port, so a **straight-through
   8-wire Ethernet patch cable** (T568A or T568B, same on both ends) connects pin n to pin n:

   | Pin | Device (Cisco pinout) | Board |
   |---|---|---|
   | 1 | RTS out | RIN2 (our CTS) |
   | 2 | DTR out | RIN3 (spare, helps cable detect) |
   | 3 | TxD out | RIN1 (our RX) |
   | 4, 5 | GND | GND |
   | 6 | RxD in | DOUT1 (our TX) |
   | 7 | DSR in | DOUT3 (always on) |
   | 8 | CTS in | DOUT2 (our RTS) |

   Same approach as Lantronix SLC8000 "reversed pinout" ports.
2. Supported cable: any Cat5e/Cat6 patch cable with all 8 wires. Not supported (no damage,
   just no link): crossover cables, Cisco rollover (blue console) cables, 4-wire flat cables
   (no ground on 4/5).
3. Never plug the jack into an Ethernet switch port or an APC UPS serial port. Protection
   against that is NOTES I-21 (open).

## Consequences
- Hardware rev 0.2 and the hand-built adapter guide already follow this; no change needed.
- Any future board revision must keep this pinout.
