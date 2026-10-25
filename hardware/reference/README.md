# Reference drawings

- `d1-mini-dimensions-bottom-view.png` (from John, 2026-10-24; HiLetgo D1 mini clone listing):
  **bottom view** (pin labels mirrored). 34.2 x 25.6 mm, pin rows 900 mil (22.86 mm) apart.
  1 = micro USB and 2 = reset button, both on the **underside**, with the CH340. Scaled from
  the picture: first pin (TX/RST) 7.7 mm from the antenna end, last pin (5V/3V3) 8.9 mm from
  the USB end. Also shows the D1 mini schematic (CH340 USB-UART, ESP-12F, RT9013 3.3 V).
- `connfly-ds1128-09-rj45-C77851.pdf` (from John, 2026-10-25): CONNFLY DS1128-09 drawing, the
  board's J1 (LCSC C77851). Checked against the KiCad footprint: all dimensions match
  (`hardware/rs232-shield/README.md`).
- `ruichuan-rch-56-31-rj45-C708625.pdf` (from John, 2026-10-25): Wenzhou Ruichuan RCH-56-31,
  all-plastic jack without LEDs (LCSC C708625). Pegs 12.6 mm apart against the board's 12.7 mm.
- `ruichuan-rch-56-31-led-rj45-C708612.pdf` (from John, 2026-10-25): Ruichuan RCH-56-31 with LEDs
  and a metal shell (LCSC C708612). Read from the drawing: pins as Connfly; pegs 3.25 mm, 12.6 mm
  apart; shell tabs 1.6 mm, 16.1 mm apart, 3.43 mm from the pegs; LED holes 9.14 / 13.72 mm,
  9.14 mm from the pegs. LEDs: 9 cathode / 10 anode, 11 cathode / 12 anode. From the front, yellow
  is on the left and green on the right, so on the footprint yellow = 11/12 and green = 9/10
  (inferred; check with a meter).
