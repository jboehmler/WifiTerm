"""@file make_doc.py
@brief Writes the Word build guide (picture + instructions) for the TRS3243E adapter module.
@details Run next to layout.png: python3 make_doc.py trs3243e-adapter-build.docx"""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt

doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)
for s in doc.sections:
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(0.8)

def table(head, rows, widths=None):
    """@brief Adds a simple grid table with a bold header row."""
    t = doc.add_table(rows=1, cols=len(head)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for c, h in zip(t.rows[0].cells, head):
        c.text = ""; c.paragraphs[0].add_run(h).bold = True
    for r in rows:
        for c, v in zip(t.add_row().cells, r):
            c.text = str(v)
    if widths:
        for row in t.rows:
            for c, w in zip(row.cells, widths):
                c.width = Inches(w)
    doc.add_paragraph()

def steps(items):
    """@brief Adds a numbered list that restarts at 1 (plain numbers, hanging indent)."""
    for n, i in enumerate(items, 1):
        p = doc.add_paragraph("%d.\t%s" % (n, i))
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.3)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(0.3))

doc.add_heading("TRS3243E RS-232 module: hand build on an SSOP-28 adapter", 0)
doc.add_paragraph("WiFi Terminal project, 2026-10-24. A hand-built version of the RS-232 board "
                  "(hardware/rs232-shield) using the SSOP-28 adapter from the breakout kit and leaded parts. "
                  "It connects a Wemos D1 mini to a Cisco-style RJ45 console port through a straight Ethernet cable.")

doc.add_heading("Parts", 1)
table(["Qty", "Part", "Mouser no.", "Notes"], [
    ("1", "TI MAX3243ECDBR, SSOP-28", "595-MAX3243ECDBR", "Same pinout as TRS3243ECDBR (also fine, LCSC C544326); Mouser stocks this one"),
    ("1", "SSOP28 / SOP28 adapter board", "-", "From the breakout kit; use the 0.65 mm side"),
    ("2", "1 x 14 header pins, 2.54 mm", "-", "Cut from the strips that came with the D1 minis"),
    ("6", "100 nF 50 V X7R, leaded, 5.08 mm (KEMET C322C104K5R5TA)", "80-C322C104K5R", "C1 to C5, one spare"),
    ("1", "1 uF 50 V X7R, leaded, 5.08 mm (KEMET C322C105K5R5TA)", "80-C322C105K5R5TA", "C6"),
    ("3", "10k 1% 1/4 W (YAGEO MFR-25FBF52-10K)", "603-MFR-25FBF52-10K", "R1 to R3, fitted at the D1 mini"),
    ("-", "Thin hook-up wire, sleeving or heat-shrink", "-", "For links and leads that cross pins"),
    ("1", "RJ45 breakout, or an Ethernet cable cut in half", "-", "Device end of the console link"),
    ("1", "Wemos D1 mini", "-", ""),
], [0.4, 2.5, 1.6, 2.4])

doc.add_heading("Tools", 1)
for t in ("Fine-tip soldering iron, thin solder, flux (pen or paste)", "Solder wick for bridges",
          "Magnifier or loupe", "Multimeter (continuity and DC volts)", "Tweezers, flush cutters"):
    doc.add_paragraph(t, style="List Bullet")

doc.add_heading("Layout", 1)
doc.add_paragraph("Top view, chip side up, pin 1 at top left. Each pin is labelled with its function "
                  "and where its wire goes. Dashed leads cross the chip or other pins: sleeve them.")
doc.add_picture("layout.png", width=Inches(6.9))

doc.add_heading("Build steps", 1)
steps([
    "Check the adapter: with the meter, confirm that header hole 1 connects to the chip pad marked 1 "
    "(the pad nearest the triangle or pin-1 mark). The layout assumes pad n goes to hole n.",
    "Solder the chip (MAX3243ECDBR or TRS3243ECDBR). Flux the pads, line up the pin-1 dot with pad 1, tack two opposite corner pins, "
    "check alignment, then solder the rest (drag soldering is fine). Wick away bridges. Inspect every "
    "pin with the magnifier.",
    "Push the header pins in from below (long ends down) and solder them on top, leaving short stubs.",
    "C2 (100 nF): across pins 1 and 2, lying just outside the left edge.",
    "C1 (100 nF): from pin 28 to pin 24, lying just outside the right edge, clear of pins 25 to 27.",
    "C3 (100 nF): from pin 27 to pin 25, lying on the board; sleeve the leads.",
    "C4 (100 nF): from pin 3 to pin 25, lying across the chip; sleeve both leads.",
    "C5 (100 nF) and C6 (1 uF): both standing upright between pins 26 and 25.",
    "Link pins 22 and 23 with a short bridge (they are next to each other).",
    "Link pin 12 to pin 25 with an insulated wire (keeps the spare driver's input low).",
    "At the D1 mini, fit the three 10k resistors on its pins: R1 from D7 to 3V3, R2 from D6 to 3V3, "
    "R3 from D1 to G.",
    "Wire the adapter to the D1 mini and to the RJ45 as in the tables below. Keep wires short.",
])

doc.add_heading("Wiring to the D1 mini", 1)
table(["D1 mini pin", "Adapter pin", "Function"], [
    ("D8 (GPIO15)", "14 DIN1", "Our TX, data to the device"),
    ("D7 (GPIO13)", "19 ROUT1", "Our RX, data from the device (R1 pull-up)"),
    ("D5 (GPIO14)", "13 DIN2", "RTS out (future flow control)"),
    ("D6 (GPIO12)", "18 ROUT2", "CTS in (future flow control, R2 pull-up)"),
    ("D1 (GPIO5)", "22 (linked to 23)", "Chip on when high (R3 pull-down)"),
    ("D2 (GPIO4)", "21 INVALID", "Low when no RS-232 signal (cable detect)"),
    ("3V3", "26 VCC", "Power"),
    ("G", "25 GND", "Ground"),
], [1.6, 1.7, 3.4])

doc.add_heading("Wiring to the RJ45 (device console port, straight cable)", 1)
doc.add_paragraph("Wire colours are for a T568B cable cut in half; check yours with the meter.")
table(["RJ45 pin", "T568B colour", "Device signal", "Adapter pin"], [
    ("1", "white/orange", "RTS (device output)", "5 RIN2"),
    ("2", "orange", "DTR (device output)", "6 RIN3"),
    ("3", "white/green", "TxD (device output)", "4 RIN1"),
    ("4", "blue", "GND", "25 GND"),
    ("5", "white/blue", "GND", "25 GND"),
    ("6", "green", "RxD (device input)", "9 DOUT1"),
    ("7", "white/brown", "DSR (device input)", "11 DOUT3"),
    ("8", "brown", "CTS (device input)", "10 DOUT2"),
], [0.9, 1.4, 2.2, 2.2])
doc.add_paragraph("Never plug this RJ45 into an Ethernet switch port.")

doc.add_heading("Checks before power", 1)
steps([
    "No short between 3V3 and G (D1 mini unplugged from USB).",
    "No 0-ohm reading between any two neighbouring chip pins, except 22-23 (linked) and 25-12 (linked).",
    "Each wire in the tables has continuity from end to end.",
])

doc.add_heading("First power-up", 1)
steps([
    "Firmware: set CHIP_POWER_ON_LEVEL 1 in firmware/main/config.h, build and flash.",
    "Power the D1 mini from USB and switch the chip on (D1 high: firmware 'uart power on', or for a "
    "quick test link pin 22 to 3V3 instead of D1).",
    "Measure against GND: pin 27 (V+) about +5.5 V, pin 3 (V-) about -5.5 V, pin 9 (DOUT1) about -5.5 V "
    "when idle. If these are right, the charge pump and capacitors are good.",
    "Connect the device with a straight Ethernet cable and test with the client.",
])

doc.add_heading("Notes", 1)
for t in ("Assumed, check before soldering: adapter pad n connects to header hole n; row spacing about 17.8 mm.",
          "Same circuit as the JLCPCB board (hardware/rs232-shield/README.md); this is the hand-built equivalent.",
          "Source of this document: hardware/adapter-build/make_doc.py and layout.png (make_layout.py)."):
    doc.add_paragraph(t, style="List Bullet")
doc.save(sys.argv[1])
