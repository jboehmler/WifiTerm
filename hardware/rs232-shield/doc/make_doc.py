#!/usr/bin/env python3
"""!
@file make_doc.py
@brief Writes the shield's Word picture book: board top and bottom, parts layout, and four 3D
       views of the assembled unit.
@details Usage: python3 make_doc.py OUTFILE.docx   (runs make_views.py first, into a temp folder).
         Parts come from jlcpcb/bom.csv and jlcpcb/cpl.csv, so the tables follow the board files.
"""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
RS = HERE.parent  ##< hardware/rs232-shield


def main() -> None:
    """! @brief Build the document named on the command line. """
    out = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as t:
        pics = Path(t)
        subprocess.run([sys.executable, str(HERE / "make_views.py"), str(pics)], check=True)
        doc = Document()
        doc.styles["Normal"].font.name = "Calibri"
        doc.styles["Normal"].font.size = Pt(11)
        for s in doc.sections:
            s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(0.8)

        def caption(text: str) -> None:
            """! @brief Small centred italic caption. @param text Caption. """
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(text)
            r.italic = True
            r.font.size = Pt(9.5)

        def pair(left: str, right: str, lcap: str, rcap: str, h: float) -> None:
            """! @brief Two pictures side by side with captions, @p h inches high. """
            tb = doc.add_table(rows=2, cols=2)
            tb.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, (png, cap) in enumerate(((left, lcap), (right, rcap))):
                cell = tb.rows[0].cells[i]
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                cell.paragraphs[0].add_run().add_picture(str(pics / png), height=Inches(h))
                c = tb.rows[1].cells[i].paragraphs[0]
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = c.add_run(cap)
                r.italic = True
                r.font.size = Pt(9.5)

        doc.add_heading("RS-232 shield rev 0.2: board and assembled unit", 0)
        doc.add_paragraph(
            "WiFi Terminal project. Pictures are drawn from the JLCPCB files in "
            "hardware/rs232-shield (Gerbers, BOM, CPL) and the 3D model of the assembled unit. "
            "The board is 25.6 x 27.5 mm; with the D1 mini plugged in the unit is 25.6 x 34.4 x 30.9 mm.")

        doc.add_heading("1. The board, top and bottom", 1)
        pair("board-top.png", "board-bottom.png",
             "Top (parts side, under the D1 mini)", "Bottom (jack side), turned over like a page", 4.0)
        doc.add_paragraph(
            "The D1 mini plugs into J2 and J3 on the top, antenna end up the page, over the part of the "
            "board with U1. The RJ45 jack goes on the bottom and opens toward the lower edge, under the "
            "D1 mini's USB port. Bare pads show gold, mask green, silkscreen white.")

        doc.add_heading("2. Parts layout", 1)
        doc.add_picture(str(pics / "board-layout.png"), height=Inches(4.2))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        caption("Top of the board. Red = parts JLCPCB places; blue = parts John fits by hand")

        bom = {}
        for row in csv.DictReader((RS / "jlcpcb" / "bom.csv").open()):
            for ref in row["Designator"].replace('"', "").split(","):
                bom[ref.strip()] = row
        cpl = {r["Designator"]: r for r in csv.DictReader((RS / "jlcpcb" / "cpl.csv").open())}
        rows = []
        for ref in sorted(bom, key=lambda r: (r[0], int(r[1:]))):
            r, c = bom[ref], cpl[ref]
            rows.append((ref, r["Comment"], r["Footprint"].split("_")[0] + " " + r["Footprint"].split("_")[1]
                         if r["Footprint"].startswith(("C_", "R_")) else "SSOP-28",
                         r["LCSC Part #"],
                         f"{float(c['Mid X'][:-2]):.2f}, {-float(c['Mid Y'][:-2]):.2f}", c["Rotation"] + "°",
                         "JLCPCB"))
        rows += [("J1", "RJ45 jack, CONNFLY DS1128-09-S8B8S", "through-hole, underside", "C77851",
                  "", "", "John"),
                 ("J2, J3", "2 x 8-pin female socket, 2.54 mm", "through-hole, top", "(with the D1 mini)",
                  "", "", "John")]
        head = ("Ref", "Part", "Package", "LCSC", "X, Y mm", "Rot", "Fitted by")
        tb = doc.add_table(rows=1, cols=len(head))
        tb.style = "Table Grid"
        tb.alignment = WD_TABLE_ALIGNMENT.CENTER
        for c, h in zip(tb.rows[0].cells, head):
            c.text = ""
            c.paragraphs[0].add_run(h).bold = True
        for r in rows:
            for c, v in zip(tb.add_row().cells, r):
                c.text = str(v)
        for row in tb.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for run in p.runs:
                        run.font.size = Pt(9.5)
        doc.add_paragraph()
        doc.add_paragraph("X, Y are the part centres from the CPL file, measured from the board's top-left "
                          "corner (Y down). Roles: C1-C5 100 nF charge pump and bypass, C6 1 uF bypass, "
                          "R1 and R2 pull-ups on D7 and D6, R3 pull-down on D1, U1 the RS-232 driver.")

        doc.add_heading("3. The assembled unit", 1)
        doc.add_paragraph(
            "Board, jack and a D1 mini plugged in (the D1 mini and jack are simplified shapes, positions "
            "accurate to about 0.3 mm). \"Front\" is the USB and jack end of the unit.")
        pair("unit-front.png", "unit-side.png", "Front: from the USB and jack end",
             "Side: jack end on the left, antenna end on the right", 3.3)
        pair("unit-top.png", "unit-bottom.png", "Top: antenna at the top of the page",
             "Bottom: jack and the D1 mini's USB end at the foot of the page", 3.6)
        doc.add_paragraph(
            "The jack hangs 14 mm below the board. The D1 mini's own micro USB and reset button face down, "
            "between the sockets, above the jack; the antenna end overhangs the board with nothing under it.")
        doc.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
