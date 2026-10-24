"""@file make_layout.py
@brief Draws the soldering layout for a TRS3243E on an SSOP-28 adapter with leaded parts (SVG)."""
import sys

S = 20.0                                  # px per mm
BX, BY, BW, BH = 330, 140, 20.3 * S, 35.5 * S
XL = BX + (20.3 - 17.78) / 2 * S          # left header column
XR = XL + 17.78 * S                       # right header column
P = 2.54 * S
Y0 = BY + (35.5 - 13 * 2.54) / 2 * S

NAMES = {1: "C2+", 2: "C2-", 3: "V-", 4: "RIN1", 5: "RIN2", 6: "RIN3", 7: "RIN4", 8: "RIN5",
         9: "DOUT1", 10: "DOUT2", 11: "DOUT3", 12: "DIN3", 13: "DIN2", 14: "DIN1",
         15: "ROUT5", 16: "ROUT4", 17: "ROUT3", 18: "ROUT2", 19: "ROUT1", 20: "ROUT2B",
         21: "INVALID", 22: "FORCEOFF", 23: "FORCEON", 24: "C1-", 25: "GND", 26: "VCC",
         27: "V+", 28: "C1+"}
## Where each pin's wire goes (off the adapter).
WIRES = {4: "RJ45 3", 5: "RJ45 1", 6: "RJ45 2", 9: "RJ45 6", 10: "RJ45 8", 11: "RJ45 7",
         13: "D1mini D5", 14: "D1mini D8", 18: "D1mini D6", 19: "D1mini D7", 21: "D1mini D2",
         22: "D1mini D1", 25: "D1mini G + RJ45 4,5", 26: "D1mini 3V3"}

def pin(p):
    """@return (x, y) of header pin p, top view (chip side up, pin 1 top left)."""
    return (XL, Y0 + (p - 1) * P) if p <= 14 else (XR, Y0 + (28 - p) * P)

out = []
def add(s): out.append(s)
def lead(pts, colour="#666", dash=""):
    add('<polyline points="%s" fill="none" stroke="%s" stroke-width="3" %s/>' % (
        " ".join("%.1f,%.1f" % q for q in pts), colour, 'stroke-dasharray="%s"' % dash if dash else ""))
def part(x, y, w, h, colour, label, tx=None, ty=None, anchor="middle"):
    add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="6" fill="%s" stroke="#222"/>' % (x - w / 2, y - h / 2, w, h, colour))
    add('<text x="%.1f" y="%.1f" font-size="17" font-weight="bold" text-anchor="%s">%s</text>' % (
        tx if tx is not None else x, ty if ty is not None else y + 6, anchor, label))

CAP, CAP1, RES, WIRE = "#f2c14e", "#e07a5f", "#81b29a", "#3d5a80"
W, H = 1250, 1060
add('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="Helvetica,Arial,sans-serif">' % (W, H))
add('<rect width="100%" height="100%" fill="white"/>')
add('<text x="%d" y="40" font-size="26" font-weight="bold" text-anchor="middle">TRS3243E on SSOP-28 adapter: leaded-part layout (top view, chip side up)</text>' % (W / 2))
add('<text x="%d" y="70" font-size="17" text-anchor="middle">Header pins pushed in from below; parts soldered to the pin stubs on top. Sleeve any lead that crosses the chip or another pin.</text>' % (W / 2))
add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="#2e8b57" opacity="0.85"/>' % (BX, BY, BW, BH))
cx = (XL + XR) / 2
cy = BY + BH / 2
add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#222"/>' % (cx - 2.65 * S, cy - 5.1 * S, 5.3 * S, 10.2 * S))
add('<circle cx="%.1f" cy="%.1f" r="6" fill="#ccc"/>' % (cx - 2.65 * S + 14, cy - 5.1 * S + 14))
add('<text x="%.1f" y="%.1f" font-size="18" fill="white" text-anchor="middle" transform="rotate(-90 %.1f %.1f)">TRS3243E, dot = pin 1</text>' % (cx + 6, cy, cx + 6, cy))

# Parts (drawn under the pin labels).
x1, y1 = pin(1); x2, y2 = pin(2)
lead([(x1, y1), (x1 - 45, y1), (x1 - 45, y2), (x2, y2)]); part(x1 - 45, (y1 + y2) / 2, 30, 46, CAP, "C2", x1 - 66, (y1 + y2) / 2 + 6, "end")
x3, y3 = pin(3); x25, y25 = pin(25)
lead([(x3, y3), (x3 + 70, y3), (x25 - 70, y25), (x25, y25)], "#666", "8,5"); part((x3 + x25) / 2, (y3 + y25) / 2, 70, 28, CAP, "C4")
x28, y28 = pin(28); x24, y24 = pin(24)
lead([(x28, y28), (x28 + 95, y28), (x28 + 95, y24), (x24, y24)]); part(x28 + 95, (y28 + y24) / 2 - 40, 30, 60, CAP, "C1", x28 + 116, (y28 + y24) / 2 - 34, "start")
x27, y27 = pin(27)
lead([(x27, y27), (x27 - 55, y27), (x27 - 55, y25), (x25, y25)], "#666", "8,5"); part(x27 - 55, (y27 + y25) / 2, 30, 50, CAP, "C3")
x26, y26 = pin(26)
lead([(x26, y26), (x26 + 65, y26)]); lead([(x25, y25), (x26 + 65, y25)])
part(x26 + 30, (y26 + y25) / 2, 22, 40, CAP, "")
part(x26 + 62, (y26 + y25) / 2, 22, 40, CAP1, "")
add('<text x="%.1f" y="%.1f" font-size="15" font-weight="bold" text-anchor="middle">C5 C6</text>' % (x26 + 46, y25 + 40))
x22, y22 = pin(22); x23, y23 = pin(23)
lead([(x22, y22), (x23, y23)], WIRE)
x12, y12 = pin(12)
lead([(x12, y12), (x12 + 40, y12), (x12 + 40, y25 + 18), (x25 - 30, y25 + 18), (x25, y25)], WIRE, "3,4")

for p in range(1, 29):
    x, y = pin(p)
    add('<rect x="%.1f" y="%.1f" width="22" height="22" fill="#d4af37" stroke="#222"/>' % (x - 11, y - 11))
    left = p <= 14
    lx = x - 16 if left else x + 16
    add('<text x="%.1f" y="%.1f" font-size="15" text-anchor="%s" fill="white" font-weight="bold">%d</text>' % (x + (-0 if left else 0), y + 5, "middle", p))
    lab = "%s" % NAMES[p]
    if p in WIRES:
        lab = "%s  — %s" % (NAMES[p], WIRES[p]) if not left else "%s —  %s" % (WIRES[p], NAMES[p])
    add('<text x="%.1f" y="%.1f" font-size="15" text-anchor="%s">%s</text>' % (
        BX - 75 if left else BX + BW + 175, y + 5, "end" if left else "start", lab))

ly = BY + BH + 50
legend = [(CAP, "C1-C5  100 nF ceramic, leaded (5.08 mm)"), (CAP1, "C6  1 µF ceramic, leaded"),
          (WIRE, "Wire links: 22—23 (short bridge), 12—25 (insulated)")]
for i, (c, t) in enumerate(legend):
    add('<rect x="%d" y="%d" width="26" height="18" fill="%s" stroke="#222"/>' % (40 + i * 400, ly, c))
    add('<text x="%d" y="%d" font-size="16">%s</text>' % (75 + i * 400, ly + 15, t))
add('<text x="40" y="%d" font-size="16">Pull-up/down resistors go at the D1 mini end (10k each): D7—3V3, D6—3V3, D1—G. Dashed leads: sleeve them.</text>' % (ly + 50))
add('</svg>')
open(sys.argv[1], "w").write("\n".join(out))
