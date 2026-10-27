#!/usr/bin/env python3
"""!
@file make_views.py
@brief Pictures for the shield Word document: the bare board, top and bottom, as fabricated
       (from the JLCPCB Gerbers), and the assembled unit from four sides (from the 3D model).
@details Usage: python3 make_views.py OUTDIR
         Needs gerbv, trimesh + networkx + scipy, numpy, pillow. Writes
         board-top.png, board-bottom.png, unit-front.png, unit-side.png, unit-top.png,
         unit-bottom.png into OUTDIR.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
RS = HERE.parent  ##< hardware/rs232-shield


def gerber_layer(gerb: Path, name: str, files: list[str], tmp: Path) -> np.ndarray:
    """!
    @brief Draw Gerber/drill files white on black at 1000 dpi, all on the board outline's extent.
    @param gerb Folder with the unzipped Gerbers. @param name Output stem. @param files Files to draw.
    @param tmp Scratch folder.
    @return Boolean image (True where drawn).
    """
    out = tmp / f"{name}.png"
    cmd = ["gerbv", "-x", "png", "-D", "1000", "-B", "2", "-a", "-b", "#000000",
           "-f", "#FFFFFF" if not files else "#000000"]  # outline hidden unless it is what we draw
    for _ in files:
        cmd += ["-f", "#FFFFFF"]
    subprocess.run(cmd + [str(gerb / "rs232-shield-Edge_Cuts.gm1")] + [str(gerb / f) for f in files] +
                   ["-o", str(out)], check=True, capture_output=True)
    return np.array(Image.open(out).convert("L")) > 127


def board_picture(gerb: Path, side: str, tmp: Path) -> Image.Image:
    """!
    @brief The bare board as fabricated: green mask, bare pads, white silkscreen, holes.
    @param gerb Gerber folder. @param side "F" (top) or "B" (bottom, shown turned over).
    @param tmp Scratch folder.
    @return RGB picture.
    """
    cu = gerber_layer(gerb, side + "cu", [f"rs232-shield-{side}_Cu." + ("gtl" if side == "F" else "gbl")], tmp)
    mask = gerber_layer(gerb, side + "mask", [f"rs232-shield-{side}_Mask." + ("gts" if side == "F" else "gbs")], tmp)
    silk = gerber_layer(gerb, side + "silk", [f"rs232-shield-{side}_Silkscreen." + ("gto" if side == "F" else "gbo")], tmp)
    holes = gerber_layer(gerb, "holes", ["rs232-shield-PTH.drl", "rs232-shield-NPTH.drl"], tmp)
    edge = gerber_layer(gerb, "edge", [], tmp)
    regions, _ = ndimage.label(~edge)                           # the region holding the middle is the board
    inside = regions == regions[edge.shape[0] // 2, edge.shape[1] // 2]
    h, w = cu.shape
    img = np.full((h, w, 3), 255, np.uint8)
    img[inside] = (22, 96, 52)                 # solder mask over bare laminate
    img[inside & cu] = (36, 130, 72)           # copper under the mask
    img[inside & cu & mask] = (214, 196, 128)  # exposed pad (HASL / gold look)
    img[inside & holes] = (250, 250, 250)      # drilled holes
    img[inside & silk] = (245, 245, 245)       # silkscreen
    img[edge] = (30, 30, 30)
    pic = Image.fromarray(img)
    if side == "B":
        pic = pic.transpose(Image.FLIP_LEFT_RIGHT)   # turn the board over like a page
    ys, xs = np.where(inside)
    return pic.crop((xs.min() - 12, ys.min() - 12, xs.max() + 13, ys.max() + 13))


def layout_picture(top: Image.Image, gerb: Path, tmp: Path, parts: list[tuple[str, float, float]]) -> Image.Image:
    """!
    @brief Parts layout: the top of the board, faded, with each part's designator on it, plus the
           footprint of the jack on the underside (dashed) and the two D1 mini sockets.
    @param top Output of board_picture(..., "F"). @param gerb Gerber folder. @param tmp Scratch folder.
    @param parts (designator, x mm, y mm) from the CPL file (x right, y negative downward).
    @return RGB picture.
    """
    edge = gerber_layer(gerb, "edge", [], tmp)
    ys, xs = np.where(edge)
    s = (xs.max() - xs.min()) / 25.6                      # pixels per mm
    # board_picture() cropped 12 px outside the inside-region box; recompute that box's origin.
    regions, _ = ndimage.label(~edge)
    inside = regions == regions[edge.shape[0] // 2, edge.shape[1] // 2]
    iy, ix = np.where(inside)
    ox, oy = ix.min() - 12, iy.min() - 12                 # crop origin in gerbv pixels
    X0, Y0 = xs.min() - ox, ys.min() - oy                 # board's top-left corner in the crop

    def px(x: float, y: float) -> tuple[float, float]:
        return X0 + x * s, Y0 - y * s

    img = Image.blend(top, Image.new("RGB", top.size, "white"), 0.55)
    d = ImageDraw.Draw(img, "RGBA")
    from PIL import ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    # Jack footprint on the underside (mesh/CPL coordinates, from the 3D model).
    x0, y0 = px(4.5, -11.8)
    x1, y1 = px(21.0, -27.5)
    for a in range(int(x0), int(x1), 24):                 # dashed outline
        d.line([(a, y0), (min(a + 12, x1), y0)], fill=(20, 60, 160), width=4)
        d.line([(a, y1), (min(a + 12, x1), y1)], fill=(20, 60, 160), width=4)
    for b in range(int(y0), int(y1), 24):
        d.line([(x0, b), (x0, min(b + 12, y1))], fill=(20, 60, 160), width=4)
        d.line([(x1, b), (x1, min(b + 12, y1))], fill=(20, 60, 160), width=4)
    d.text(((x0 + x1) / 2, px(0, -23.5)[1]), "J1 RJ45 jack\n(underside)", font=big, fill=(20, 60, 160), anchor="mm",
           align="center")
    for name, (x, y) in {"J2": (1.4, -9.0), "J3": (24.2, -9.0)}.items():
        cx, cy = px(x, y)
        d.text((cx, cy), name + "\nD1 mini\nsocket", font=small, fill=(20, 60, 160), anchor="mm", align="center")
    for name, x, y in parts:
        cx, cy = px(x, y)
        w = 14 + 17 * len(name)
        d.rounded_rectangle([cx - w / 2, cy - 18, cx + w / 2, cy + 18], 6, fill=(255, 255, 255, 235),
                            outline=(170, 20, 20), width=3)
        d.text((cx, cy), name, font=font, fill=(170, 20, 20), anchor="mm")
    return img


# ---------------------------------------------------------------- 3D views of the assembled unit

def coloured_parts(stl: Path) -> list[tuple[trimesh.Trimesh, tuple[int, int, int]]]:
    """!
    @brief Split the assembly STL into bodies and colour them by size and height.
    @param stl rs232-shield-assembly.stl (mm, board and jack below the D1 mini, z up).
    @return (mesh, rgb) per body.
    """
    m = trimesh.load(stl)
    m.merge_vertices()
    out = []
    for p in m.split(only_watertight=False):
        lo, hi = p.bounds
        ext = hi - lo
        if ext[0] > 20 and ext[1] > 30 and ext[2] < 1.5:
            rgb = (30, 70, 160)                        # D1 mini board (blue)
        elif ext[0] > 20 and ext[1] > 25 and ext[2] < 2.2:
            rgb = (24, 110, 58)                        # shield board (green)
        elif ext[2] > 12 and ext[1] > 10:
            rgb = (205, 205, 210)                      # RJ45 jack (metal shell)
        elif lo[2] > 25 and ext[0] > 10 and ext[2] < 1.2:
            rgb = (28, 28, 34)                         # ESP-12F module board (black)
        elif lo[2] > 25 and ext[0] > 10:
            rgb = (192, 192, 197)                      # ESP-12F shield can (metal)
        elif ext[0] < 1.5 and ext[2] > 4:
            rgb = (212, 175, 55)                       # header pins
        elif ext[2] > 5 and ext[0] < 4:
            rgb = (35, 35, 35)                         # socket / header plastic
        elif lo[2] < 15 and ext[1] > 6:
            rgb = (200, 200, 205)                      # micro USB, reset, CH340 (underside)
        else:
            rgb = (60, 60, 64)                         # chips, passives
        out.append((p, rgb))
    return out


def render(parts, direction, up, px=1400, margin=0.9) -> Image.Image:
    """!
    @brief Orthographic flat-shaded picture (painter's algorithm), drawn 2x and reduced.
    @param parts (mesh, rgb) list. @param direction Viewing direction (from the camera into the scene).
    @param up Up vector on screen. @param px Output size. @param margin Fraction of the picture the model fills.
    @return RGB picture, cropped to the model.
    """
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    r = np.cross(up, -d)
    r /= np.linalg.norm(r)
    u = np.cross(-d, r)
    allv = np.vstack([p.vertices for p, _ in parts])
    c = (allv.max(0) + allv.min(0)) / 2
    P2 = np.c_[(allv - c) @ r, (allv - c) @ u]
    s = margin * 2 * px / (P2.max(0) - P2.min(0)).max()
    tris, cols, depth = [], [], []
    light = -d + 0.5 * u + 0.35 * r
    light /= np.linalg.norm(light)
    for p, rgb in parts:
        v = p.vertices - c
        xy = np.c_[v @ r, v @ u] * s
        xy[:, 1] *= -1
        xy += px                                # centre of the 2x canvas
        sh = np.clip(p.face_normals @ light, 0, 1)
        facing = p.face_normals @ d < 0.02      # drop back faces
        for f in np.where(facing)[0]:
            tris.append(xy[p.faces[f]])
            cols.append(tuple(int(ch * (0.38 + 0.62 * sh[f])) for ch in rgb))
            depth.append((v[p.faces[f]] @ d).mean())
    img = Image.new("RGB", (2 * px, 2 * px), "white")
    dr = ImageDraw.Draw(img)
    for i in np.argsort(depth)[::-1]:           # far to near
        dr.polygon([tuple(q) for q in tris[i]], fill=cols[i], outline=cols[i])
    img = img.filter(ImageFilter.SMOOTH).resize((px, px), Image.LANCZOS)
    a = np.array(img.convert("L")) < 250
    ys, xs = np.where(a)
    return img.crop((xs.min() - 20, ys.min() - 20, xs.max() + 21, ys.max() + 21))


def main() -> None:
    """! @brief Write all pictures into the folder named on the command line. """
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        subprocess.run(["unzip", "-oq", str(RS / "jlcpcb" / "rs232-shield-gerbers.zip"), "-d", str(tmp / "g")], check=True)
        for side, name in (("F", "board-top"), ("B", "board-bottom")):
            pic = board_picture(tmp / "g", side, tmp)
            pic.save(out / f"{name}.png")
            if side == "F":
                cpl = []
                for line in (RS / "jlcpcb" / "cpl.csv").read_text().splitlines()[1:]:
                    f = line.split(",")
                    if len(f) >= 3 and f[0]:
                        cpl.append((f[0], float(f[1].replace("mm", "")), float(f[2].replace("mm", ""))))
                layout_picture(pic, tmp / "g", tmp, cpl).save(out / "board-layout.png")
    parts = coloured_parts(RS / "3d" / "rs232-shield-assembly.stl")
    # Mesh axes: X across the board, Y along it (antenna at +Y, USB and jack at -Y), Z up (D1 mini on top).
    views = {
        "unit-front": ((0, 1, 0), (0, 0, 1)),       # from the USB / jack end, jack opening toward you
        "unit-side": ((-1, 0, 0), (0, 0, 1)),       # from the left side, antenna on the right
        "unit-top": ((0, 0, -1), (0, 1, 0)),        # from above, antenna at the top of the page
        "unit-bottom": ((0, 0, 1), (0, 1, 0)),      # from below, antenna at the top of the page
    }
    for name, (d, up) in views.items():
        render(parts, d, up).save(out / f"{name}.png")
        print("wrote", name)


if __name__ == "__main__":
    main()
