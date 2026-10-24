"""Assemble the rev 0.2 board (KiCad STEP) with a simplified D1 mini; write STL and preview views."""
import numpy as np, trimesh
from PIL import Image, ImageDraw

sc = trimesh.load("board.glb")
parts = []
for n in sc.graph.nodes_geometry:
    T, g = sc.graph[n]
    m = sc.geometry[g].copy(); m.apply_transform(T); m.apply_scale(1000.0)   # m -> mm
    parts.append(m)
board = trimesh.util.concatenate(parts)

def box(x0, x1, y0, y1, z0, z1):
    """Axis box in mesh mm (X = KiCad x, Y = -KiCad y, Z up)."""
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return b

SOCK = 8.65                  # socket top
HDR = 2.54                   # male header plastic
Z0 = SOCK + HDR              # D1 mini PCB underside
Z1 = Z0 + 1.0                # D1 mini PCB top
Y_ANT, Y_USB = 6.7, -27.5    # D1 mini ends (34.2 mm)
mini = [box(0, 25.6, Y_USB, Y_ANT, Z0, Z1)]
for x in (1.4, 24.26):
    mini.append(box(x - 1.27, x + 1.27, -1.5 - 7 * 2.54 - 1.27, -1.5 + 1.27, SOCK, Z0))   # header plastic
    for i in range(8):
        y = -1.5 - i * 2.54
        mini.append(box(x - .32, x + .32, y - .32, y + .32, SOCK - 3.0, Z1 + 1.5))      # pins
mini.append(box(4.8, 20.8, -17.3, Y_ANT, Z1, Z1 + 0.8))                 # ESP-12F module
mini.append(box(6.3, 19.3, -16.8, -1.8, Z1 + 0.8, Z1 + 3.2))            # its shield can
mini.append(box(0.3, 3.8, -24.5, -21.5, Z1, Z1 + 1.8))                  # reset button
mini.append(box(9.05, 16.55, Y_USB - 0.6, Y_USB + 5.0, Z0 - 2.6, Z0))   # micro USB, underside
mini.append(box(7.8, 17.8, -20.0, -16.0, Z0 - 1.6, Z0))                 # CH340, underside
asm = trimesh.util.concatenate([board] + mini)
asm.apply_translation([0, 0, -asm.bounds[0][2]])                        # sit on z = 0
asm.export("rs232-shield-assembly.stl")
print("bounds mm", asm.bounds.round(2).tolist(), "faces", len(asm.faces))

def view(mesh, d, up, fn, px=900):
    """Flat-shaded orthographic picture, painter's algorithm."""
    d = np.array(d, float); d /= np.linalg.norm(d); up = np.array(up, float)
    r = np.cross(up, -d); r /= np.linalg.norm(r); u = np.cross(-d, r)
    v = mesh.vertices - mesh.vertices.mean(0)
    P = np.c_[v @ r, v @ u]; depth = v @ d
    s = 0.85 * px / (P.max(0) - P.min(0)).max(); P = (P - P.min(0)) * s
    P[:, 1] = P[:, 1].max() - P[:, 1]; off = (px - P.max(0)) / 2; P += off
    tri = mesh.faces; order = np.argsort(-depth[tri].mean(1))
    nrm = mesh.face_normals; L = -d + 0.6 * u; L /= np.linalg.norm(L)
    sh = np.clip(np.abs(nrm @ L), 0.15, 1)
    img = Image.new("RGB", (px, px), "white"); dr = ImageDraw.Draw(img)
    col = np.array(mesh.visual.face_colors[:, :3], float) if hasattr(mesh.visual, "face_colors") else np.full((len(tri), 3), 180.)
    for f in order:
        c = tuple(int(x) for x in col[f] * (0.35 + 0.65 * sh[f]))
        dr.polygon([tuple(p) for p in P[tri[f]]], fill=c)
    img.save(fn)

def colour(m, rgb): m.visual.face_colors = list(rgb) + [255]; return m
cb = []
for p in parts:
    h = p.bounds[1][2] - p.bounds[0][2]
    rgb = (20, 110, 40) if h < 1.7 and p.extents[0] > 20 else ((200, 200, 205) if p.bounds[0][2] < 0 else (60, 60, 60))
    cb.append(colour(p.copy(), rgb))
cm = [colour(m.copy(), (30, 60, 140)) for m in mini[:1]] + [colour(m.copy(), (40, 40, 40)) for m in mini[1:-5]] + \
     [colour(mini[-5].copy(), (30, 60, 140)), colour(mini[-4].copy(), (190, 190, 195)), colour(mini[-3].copy(), (230, 230, 230)),
      colour(mini[-2].copy(), (190, 190, 195)), colour(mini[-1].copy(), (40, 40, 40))]
col = trimesh.util.concatenate(cb + cm)
view(col, (-1, 1.2, -0.8), (0, 0, 1), "view-iso-usb-end.png")
view(col, (1, -1.0, -0.6), (0, 0, 1), "view-iso-antenna-end.png")
view(col, (-1, 0, 0), (0, 0, 1), "view-side.png")
