#!/usr/bin/env python3
"""
@file make_board.py
@brief Builds the RS-232 base board (TRS3243E + RJ45 console jack, D1 mini on top) with the
       KiCad 7 Python API, and exports everything JLCPCB needs.

@details The board is generated, not drawn by hand, so the netlist below is the single source
         of truth and every rebuild is identical. Steps:
           - `place`: footprints, nets, outline, rules -> rs232-shield.kicad_pcb and .dsn
           - (route `rs232-shield.dsn` with Freerouting -> rs232-shield.ses)
           - `finish`: import routes, ground pours, DRC, Gerbers, drill, BOM, CPL, SVG views
         Run with KiCad 7's Python (`python3` on Ubuntu 24.04 with the `kicad` package).
         See README.md in this folder.
"""
import csv
import os
import subprocess
import sys
import zipfile

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "rs232-shield.kicad_pcb")      ##< Generated board file.
DSN = os.path.join(HERE, "rs232-shield.dsn")            ##< Specctra file for Freerouting.
SES = os.path.join(HERE, "rs232-shield.ses")            ##< Routes back from Freerouting.
OUT = os.path.join(HERE, "jlcpcb")                      ##< Files to upload to JLCPCB.
FPLIB = "/usr/share/kicad/footprints/"                  ##< KiCad standard footprint libraries.
VERSION = "0.1"                                         ##< Board revision printed on silkscreen.

# ---------------------------------------------------------------------------------- parts
## Each part: reference -> (library, footprint, value, LCSC number or None, x, y, rotation).
## Coordinates in mm, KiCad convention (y grows downward). None = not assembled by JLCPCB.
PARTS = {
    "U1": ("Package_SO", "SSOP-28_5.3x10.2mm_P0.65mm", "TRS3243ECDBR", "C544326", 12.0, 12.0, 0),
    "J1": ("Connector_RJ", "RJ45_Connfly_DS1128-09-S8xx-S_Horizontal", "DS1128-09-S8B8S", "C77851",
           15.0, 28.06, 180),
    "M1": ("Module", "WEMOS_D1_mini_light", "WEMOS D1 mini (8-pin sockets)", None, 30.0, 10.0, 0),
    "C1": ("Capacitor_SMD", "C_0603_1608Metric", "100nF", "C14663", 18.4, 8.6, 90),
    "C2": ("Capacitor_SMD", "C_0603_1608Metric", "100nF", "C14663", 5.4, 7.6, 90),
    "C3": ("Capacitor_SMD", "C_0603_1608Metric", "100nF", "C14663", 15.6, 4.6, 180),
    "C4": ("Capacitor_SMD", "C_0603_1608Metric", "100nF", "C14663", 5.4, 10.6, 270),
    "C5": ("Capacitor_SMD", "C_0603_1608Metric", "100nF", "C14663", 18.8, 4.6, 0),
    "C6": ("Capacitor_SMD", "C_0603_1608Metric", "1uF", "C15849", 18.8, 2.8, 0),
    "R1": ("Resistor_SMD", "R_0603_1608Metric", "10k", "C25804", 20.5, 13.5, 90),
    "R2": ("Resistor_SMD", "R_0603_1608Metric", "10k", "C25804", 22.5, 13.5, 90),
    "R3": ("Resistor_SMD", "R_0603_1608Metric", "10k", "C25804", 24.5, 13.5, 90),
}

# ---------------------------------------------------------------------------------- netlist
## Net name -> list of "REF.PAD". M1 pads follow the KiCad WeMos_D1_mini symbol:
## 4 D5, 5 D6, 6 D7, 7 D8, 8 3V3, 10 GND, 13 D2, 14 D1.
## J1 is wired so a straight 8-wire Ethernet cable reaches a Cisco-style RJ45 console port
## (device side: 1 RTS out, 2 DTR out, 3 TxD out, 4/5 GND, 6 RxD in, 7 DSR in, 8 CTS in).
NETS = {
    "GND": ["M1.10", "U1.25", "U1.12", "J1.4", "J1.5", "J1.SH",
            "C3.2", "C4.2", "C5.2", "C6.2", "R3.2"],
    "+3V3": ["M1.8", "U1.26", "C5.1", "C6.1", "R1.1", "R2.1"],
    "C1P": ["U1.28", "C1.1"], "C1N": ["U1.24", "C1.2"],
    "C2P": ["U1.1", "C2.1"], "C2N": ["U1.2", "C2.2"],
    "VPOS": ["U1.27", "C3.1"], "VNEG": ["U1.3", "C4.1"],
    "DEV_TX": ["M1.7", "U1.14"],                   # D8 -> DIN1
    "DEV_RX": ["M1.6", "U1.19", "R1.2"],           # ROUT1 -> D7, pull-up (chip off = float)
    "RTS": ["M1.4", "U1.13"],                      # D5 -> DIN2
    "CTS": ["M1.5", "U1.18", "R2.2"],              # ROUT2 -> D6, pull-up
    "CHIP_ON": ["M1.14", "U1.22", "U1.23", "R3.1"],  # D1 -> FORCEOFF+FORCEON, pull-down
    "CABLE": ["M1.13", "U1.21"],                   # INVALID -> D2
    "RS_TXD": ["U1.9", "J1.6"],                    # DOUT1 -> device RxD
    "RS_RXD": ["U1.4", "J1.3"],                    # device TxD -> RIN1
    "RS_RTS": ["U1.10", "J1.8"],                   # DOUT2 -> device CTS
    "RS_CTS": ["U1.5", "J1.1"],                    # device RTS -> RIN2
    "RS_DTR": ["U1.11", "J1.7"],                   # DOUT3 (DIN3 = GND, always on) -> device DSR
    "RS_DSR": ["U1.6", "J1.2"],                    # device DTR -> RIN3 (spare, helps INVALID)
}

## Through-hole parts John solders himself (cheaper than JLCPCB through-hole assembly);
## left out of the assembly BOM and CPL. The D1 mini sockets (M1) have no LCSC number at all.
HAND_SOLDER = {"J1"}

## Board outline: L shape, nothing under the D1 mini's antenna (above y = 8.5 right of x = 22).
OUTLINE = [(0, 0), (22, 0), (22, 8.5), (55, 8.5), (55, 36), (0, 36)]


def mm(x, y):
    """@brief Point in KiCad internal units from mm."""
    return pcbnew.VECTOR2I_MM(x, y)


def add_line(board, a, b, layer, width=0.1):
    """@brief Add a straight graphic line."""
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(mm(*a))
    s.SetEnd(mm(*b))
    s.SetLayer(layer)
    s.SetWidth(pcbnew.FromMM(width))
    board.Add(s)


def add_text(board, text, x, y, size=1.0, layer=pcbnew.F_SilkS):
    """@brief Add silkscreen text centred at (x, y)."""
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(mm(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    t.SetTextThickness(pcbnew.FromMM(size * 0.15))
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def fanout_gnd(board, fps, gnd):
    """@brief Give every SMD ground pad its own short track and via to the back pour.
    @details Small front-pour fragments between fine-pitch pads otherwise leave a pad cut off.
             Passives get the via just past their outer end; U1's GND pin gets it under the chip
             body. Tracks and vias are locked so the autorouter keeps them."""
    for fp in fps.values():
        c = fp.GetPosition()
        for pad in fp.Pads():
            if pad.GetNetname() != "GND" or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            p = pad.GetPosition()
            dx, dy = pcbnew.ToMM(p.x - c.x), pcbnew.ToMM(p.y - c.y)
            if fp.GetReference() == "U1":
                # Inward, under the package body, between the pad rows.
                sgn = -1 if dx > 0 else 1
                start = (pcbnew.ToMM(p.x) + sgn * 0.8, pcbnew.ToMM(p.y))
                end = (pcbnew.ToMM(p.x) + sgn * 2.1, pcbnew.ToMM(p.y))
            else:
                L = (dx * dx + dy * dy) ** 0.5 or 1
                start = (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
                end = (start[0] + dx / L * 1.1, start[1] + dy / L * 1.1)
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(mm(*start))
            t.SetEnd(mm(*end))
            t.SetWidth(pcbnew.FromMM(0.3))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(gnd)
            t.SetLocked(True)
            board.Add(t)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(mm(*end))
            v.SetWidth(pcbnew.FromMM(0.6))
            v.SetDrill(pcbnew.FromMM(0.3))
            v.SetNet(gnd)
            v.SetLocked(True)
            board.Add(v)


def place():
    """@brief Create the board: rules, outline, footprints, nets, text; write PCB and DSN."""
    board = pcbnew.NewBoard(PCB)
    ds = board.GetDesignSettings()
    # JLCPCB 2-layer standard capabilities are well inside these numbers.
    ds.m_TrackMinWidth = pcbnew.FromMM(0.2)
    ds.m_MinClearance = pcbnew.FromMM(0.2)
    ds.m_ViasMinSize = pcbnew.FromMM(0.6)
    ds.m_MinThroughDrill = pcbnew.FromMM(0.3)
    ds.m_CopperEdgeClearance = pcbnew.FromMM(0.4)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetTrackWidth(pcbnew.FromMM(0.25))
    nc.SetClearance(pcbnew.FromMM(0.2))
    nc.SetViaDiameter(pcbnew.FromMM(0.6))
    nc.SetViaDrill(pcbnew.FromMM(0.3))

    for i, a in enumerate(OUTLINE):
        add_line(board, a, OUTLINE[(i + 1) % len(OUTLINE)], pcbnew.Edge_Cuts, 0.1)

    nets = {}
    for name in NETS:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n

    fps = {}
    for ref, (lib, name, value, _lcsc, x, y, rot) in PARTS.items():
        fp = pcbnew.FootprintLoad(FPLIB + lib + ".pretty", name)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        fp.Value().SetVisible(False)
        if ref == "M1":
            fp.Reference().SetVisible(False)
        board.Add(fp)
        fps[ref] = fp

    for name, members in NETS.items():
        for m in members:
            ref, pad = m.split(".")
            found = [p for p in fps[ref].Pads() if p.GetNumber() == pad]
            if not found:
                sys.exit("no pad %s" % m)
            for p in found:                     # J1.SH has two pads
                p.SetNet(nets[name])
                if ref == "J1" and pad in ("4", "5"):
                    # Too crowded between the jack pins for two thermal spokes.
                    p.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    fanout_gnd(board, fps, nets["GND"])

    add_text(board, "WIFITERM RS-232 v" + VERSION, 41.5, 33.6, 1.1)
    add_text(board, "D1 mini on top, antenna up", 41.5, 30.5, 0.9)
    add_text(board, "Straight cable to", 5.5, 23.8, 0.0 + 0.8, pcbnew.B_SilkS)
    add_text(board, "Cisco-style console", 5.5, 25.0, 0.8, pcbnew.B_SilkS)
    add_text(board, "TRS3243E", 12.0, 12.0, 0.8, pcbnew.F_Fab)

    board.Save(PCB)
    if not pcbnew.ExportSpecctraDSN(board, DSN):
        sys.exit("DSN export failed")
    drop_gnd_from_dsn(DSN)
    print("placed:", PCB, DSN)


def sexp(text):
    """@brief Parse an s-expression (Specctra SES) into nested lists of strings."""
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "()":
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = text.index('"', i + 1)
            tokens.append(text[i + 1:j])
            i = j + 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            tokens.append(text[i:j])
            i = j
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t)
    return stack[0][0]


def find(node, key):
    """@brief All child lists of @p node whose first item is @p key."""
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def import_ses(board, path):
    """@brief Add Freerouting's wires and vias to the board.
    @details KiCad 7's ImportSpecctraSES only works inside the pcbnew GUI, so the session file
             is read here. SES units are 0.1 um with y pointing up (DSN export negates y)."""
    for t in list(board.GetTracks()):
        if not t.IsLocked():
            board.Remove(t)
    ses = sexp(open(path).read())
    routes = find(ses, "routes")[0]
    scale = 1e-4                                   # 0.1 um -> mm
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    count = [0, 0]
    for net in find(find(routes, "network_out")[0], "net"):
        if net[1] == "GND":
            continue                               # the pours carry GND (drop_gnd_from_dsn)
        ni = board.FindNet(net[1])
        for wire in find(net, "wire"):
            for path_ in find(wire, "path"):
                layer, width = layers[path_[1]], float(path_[2]) * scale
                pts = [float(v) for v in path_[3:] if not isinstance(v, list)]
                xy = [(pts[k] * scale, -pts[k + 1] * scale) for k in range(0, len(pts), 2)]
                for a, b in zip(xy, xy[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(mm(*a))
                    t.SetEnd(mm(*b))
                    t.SetWidth(pcbnew.FromMM(width))
                    t.SetLayer(layer)
                    t.SetNet(ni)
                    board.Add(t)
                    count[0] += 1
        for via in find(net, "via"):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(mm(float(via[2]) * scale, -float(via[3]) * scale))
            v.SetWidth(pcbnew.FromMM(0.6))
            v.SetDrill(pcbnew.FromMM(0.3))
            v.SetNet(ni)
            board.Add(v)
            count[1] += 1
    print("imported %d track segments, %d vias" % tuple(count))


def drop_gnd_from_dsn(path):
    """@brief Leave GND to the copper pours: give it no pins in the autorouter's net list.
    @details Routing GND as tracks crowds the pads and starves their thermal reliefs; the
             pours on both layers connect it instead, and DRC checks that nothing is left open."""
    text = open(path).read()
    start = text.index("(net GND")
    depth, i = 0, start
    while True:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1
    # Keep the net, without pins, so the locked fan-out wires that name it stay valid.
    open(path, "w").write(text[:start] + "(net GND (pins))" + text[i + 1:])


def seg_dist(p, a, b):
    """@brief Distance from point p to segment a-b (all in mm)."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return ((p[0] - ax - t * dx) ** 2 + (p[1] - ay - t * dy) ** 2) ** 0.5


def inside(p, poly):
    """@brief Point-in-polygon test (ray casting)."""
    x, y = p
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def stitch(board, gnd, pitch=3.0, keep=0.9):
    """@brief GND vias on a grid wherever they fit, tying the two ground pours together.
    @param pitch Grid spacing, mm.
    @param keep Minimum distance from the via centre to any other copper or courtyard, mm."""
    tracks = [(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y),
               pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y), pcbnew.ToMM(t.GetWidth()) / 2)
              for t in board.GetTracks()]
    boxes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            boxes.append([pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())])
    edge = [(x, y) for x, y in OUTLINE]
    added = 0
    y = 1.5
    while y < 36:
        x = 1.5
        while x < 55:
            p = (x, y)
            ok = inside(p, edge) and all(seg_dist(p, a, b) >= 1.2 for a, b in zip(edge, edge[1:] + edge[:1]))
            ok = ok and all(seg_dist(p, (t[0], t[1]), (t[2], t[3])) - t[4] >= keep for t in tracks)
            ok = ok and all(not (b[0] - keep <= x <= b[2] + keep and b[1] - keep <= y <= b[3] + keep)
                            for b in boxes)
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(mm(x, y))
                v.SetWidth(pcbnew.FromMM(0.6))
                v.SetDrill(pcbnew.FromMM(0.3))
                v.SetNet(gnd)
                board.Add(v)
                added += 1
            x += pitch
        y += pitch
    print("stitching vias:", added)


def fix_islands(board, gnd):
    """@brief Add a via inside every front-pour fragment that has none, so each fragment joins
             the back pour. Returns the number of vias added."""
    vias = [v.GetPosition() for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]
    added = 0
    for z in board.Zones():
        if z.GetLayer() != pcbnew.F_Cu:
            continue
        polys = z.GetFilledPolysList(pcbnew.F_Cu)
        for i in range(polys.OutlineCount()):
            ol = polys.Outline(i)
            if any(ol.PointInside(v) for v in vias):
                continue
            bb = ol.BBox()
            spot = None
            step = pcbnew.FromMM(0.25)
            r = pcbnew.FromMM(0.5)
            y = bb.GetTop()
            while y < bb.GetBottom() and not spot:
                x = bb.GetLeft()
                while x < bb.GetRight():
                    pts = [pcbnew.VECTOR2I(x + dx, y + dy)
                           for dx, dy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r),
                                          (r, r), (-r, -r), (r, -r), (-r, r))]
                    if all(ol.PointInside(p) for p in pts) and not any(
                            polys.HoleCount(i) and polys.Hole(i, h).PointInside(p)
                            for h in range(polys.HoleCount(i)) for p in pts):
                        spot = pcbnew.VECTOR2I(x, y)
                        break
                    x += step
                y += step
            if spot is None:
                print("island without room for a via at", pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y))
                continue
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(spot)
            v.SetWidth(pcbnew.FromMM(0.6))
            v.SetDrill(pcbnew.FromMM(0.3))
            v.SetNet(gnd)
            board.Add(v)
            added += 1
    print("island vias:", added)
    return added


def add_zone(board, net, layer):
    """@brief Ground pour over the whole outline on one copper layer."""
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNetCode(net.GetNetCode())
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # SMD pads solid, THT relieved
    z.SetThermalReliefGap(pcbnew.FromMM(0.4))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in OUTLINE:
        ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)


def run(cmd):
    """@brief Run a command, stop on failure."""
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def finish():
    """@brief Import routes, pour ground, check DRC, export the JLCPCB set."""
    board = pcbnew.LoadBoard(PCB)
    if os.path.exists(SES):
        import_ses(board, SES)
    gnd = board.FindNet("GND")
    stitch(board, gnd)
    add_zone(board, gnd, pcbnew.F_Cu)
    add_zone(board, gnd, pcbnew.B_Cu)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if fix_islands(board, gnd):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)

    report = os.path.join(HERE, "drc-report.txt")
    pcbnew.WriteDRCReport(board, report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print(open(report).read()[-1500:])

    os.makedirs(OUT, exist_ok=True)
    gdir = os.path.join(OUT, "gerbers")
    os.makedirs(gdir, exist_ok=True)
    for f in os.listdir(gdir):
        os.remove(os.path.join(gdir, f))
    run(["kicad-cli", "pcb", "export", "gerbers", "-o", gdir + "/",
         "-l", "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
         "--subtract-soldermask", PCB])
    run(["kicad-cli", "pcb", "export", "drill", "-o", gdir + "/", "--format", "excellon",
         "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2", PCB])
    zpath = os.path.join(OUT, "rs232-shield-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)

    write_bom()
    write_cpl()
    for side, layers in (("top", "F.Cu,F.SilkS,F.Mask,Edge.Cuts"),
                         ("bottom", "B.Cu,B.SilkS,B.Mask,Edge.Cuts")):
        args = ["kicad-cli", "pcb", "export", "svg", "-o", os.path.join(OUT, "view-%s.svg" % side),
                "-l", layers, "--exclude-drawing-sheet", "--page-size-mode", "2"]
        if side == "bottom":
            args.append("-m")
        run(args + [PCB])
    print("done:", OUT)


def write_bom():
    """@brief JLCPCB BOM: Comment, Designator, Footprint, LCSC Part #. SMT parts only."""
    groups = {}
    for ref, (_lib, name, value, lcsc, *_pos) in PARTS.items():
        if lcsc and ref not in HAND_SOLDER:
            groups.setdefault((value, name, lcsc), []).append(ref)
    with open(os.path.join(OUT, "bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, name, lcsc), refs in sorted(groups.items(), key=lambda g: g[1][0]):
            w.writerow([value, ",".join(sorted(refs)), name, lcsc])


def write_cpl():
    """@brief JLCPCB CPL from KiCad's position export (mm, y up), for parts in the BOM."""
    tmp = os.path.join(OUT, "pos-kicad.csv")
    run(["kicad-cli", "pcb", "export", "pos", "-o", tmp, "--format", "csv", "--units", "mm",
         "--side", "both", PCB])
    with open(tmp) as f, open(os.path.join(OUT, "cpl.csv"), "w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in csv.DictReader(f):
            ref = row["Ref"]
            if PARTS.get(ref, (None,) * 4)[3] and ref not in HAND_SOLDER:
                w.writerow([ref, row["PosX"] + "mm", row["PosY"] + "mm",
                            "Top" if row["Side"] == "top" else "Bottom",
                            "%g" % (float(row["Rot"]) % 360)])
    os.remove(tmp)


if __name__ == "__main__":
    {"place": place, "finish": finish}[sys.argv[1] if len(sys.argv) > 1 else "place"]()
