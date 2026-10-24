# 3D model of the assembled unit (rev 0.2)

- `rs232-shield-assembly.stl`: board + parts + D1 mini plugged in, millimetres, sitting on z = 0.
  Size 25.6 x 34.4 x 30.9 mm. For a 3D-printed fit check or for designing a case around it.
- `rs232-shield-board.step`: the board alone with its parts (KiCad export), for CAD.

Approximations:
- The RJ45 is KiCad's Amphenol RJHSE538X model, a stand-in with the same footprint as the
  Connfly DS1128-09 (no Connfly model exists).
- The D1 mini is simple blocks: 34.2 x 25.6 x 1.0 mm PCB, ESP-12F and its can on top; micro USB,
  CH340 and reset button on the underside. Positions are scaled from the drawing in
  `hardware/reference/d1-mini-dimensions-bottom-view.png` (+-0.3 mm): last pin to USB end is
  about 8.9 mm, so the mini's USB end overhangs the board's jack end by about 0.7 mm.
- The jack hangs 14 mm below the board, so printing needs supports.

Rebuild: export STEP with `kicad-cli pcb export step --subst-models` (J1's model set to the
Amphenol .step), convert with `cascadio.step_to_glb(..., "board.glb")`, then run
`python3 make_assembly.py` next to `board.glb` (needs trimesh, numpy, pillow).
