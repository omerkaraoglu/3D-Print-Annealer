# Rev3.0 carrier frame (CadQuery)

Parametric model, fit check, hand calculations, renders and drawing of the injection-moulded
PA6-GF30 carrier frame that holds the Rev3.0 OVEN CONTROLLER PCB and the 7" SATOZ panel and mounts
them to the oven's front sheet. Design document: `Design Reports/Rev3.0/Rev3.0_Frame_Design.md`.
Outputs go to `<project>/Mechanical/Rev3.0_Frame/`.

## Environment

No CAD program is needed. CadQuery runs from a venv on Python 3.11 (same recipe as `../models3d`):

```
C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe -m venv <venv>
<venv>\Scripts\python.exe -m pip install cadquery matplotlib ezdxf
```

Tested with cadquery 2.8.0 (OCP / VTK 9.6 wheels), matplotlib 3.11, ezdxf. VTK renders off-screen.
KiCad 10 is used read-only: `kicad-cli pcb export step` for the board with every 3D model, and
KiCad's Python (`C:\Program Files\KiCad\10.0\bin\python.exe`) for `dump_board.py`, which loads a
temporary COPY of the `.kicad_pcb` (+ `.kicad_pro` for the net classes). The live board is never written.

## Build

```
set FRAME_TMP=<scratch folder for the 10 MB board STEP>      (default: %TEMP%\rev3_frame)
<venv>\Scripts\python.exe build.py            (add --dump to re-read the board first, --no-render to skip PNGs)
```

| step | what | output |
|---|---|---|
| 1 | `dump_board.py` (KiCad Python, only with `--dump` or when missing) | `out/board_geom.json`: outline, holes, every pad polygon + net + mains flag, mains copper on B.Cu, DS1 drawing |
| 2 | `kicad-cli pcb export step --subst-models --user-origin 0x0mm` | `%FRAME_TMP%/board_full.step` |
| 3 | `frame.py` frame, Formex sheet, gasket, oven-sheet patch | - |
| 4 | frame STEP + STL (STEP re-import checked) | `Rev3.0_Frame.step`, `Rev3.0_Frame.stl` |
| 5 | board STEP + frame + sheet + gasket in one XCAF document (names and colours kept) | `Rev3.0_Assembly.step` |
| 6 | `fitcheck.py`: BRepExtrema distances and common volumes vs every board solid, tails, panel, sheet; Q1 leads trimmed to 2.5 mm; plan checks (support ribs vs pads, mains creepage/clearance); sliver-face scan | `out/fitcheck.json` |
| 7 | `calc.py`: boss bearing / thread shear / hoop, feet bearing, gasket force and tolerance stack, shelf and frame-beam deflection, weight | `out/calc.json` |
| 8 | `render.py` (VTK) iso / front / back / side, `sections.py` sections A-D, `drawing.py` dimensioned drawing + sheet DXF | `*.png`, `Rev3.0_FrontSheet_Pattern.dxf` |
| 9 | everything above in one file | `out/summary.json` |

## Coordinates

X = board absolute x, Y = -(board absolute y), Z = 0 at the PCB back (physical), +Z = component side,
-Z = towards the oven front. The mould's pull direction is Z. All plan parameters in `frame.py` are typed
in KiCad absolute coordinates (y down), exactly as pcbnew shows them.
`Rev3.0_Assembly.step` is in KiCad's own export coordinates (the board core at z 0..1.47, physical PCB back
at z -0.08); the frame parts are shifted by -0.08 to match (`fitcheck.BOARD_DZ`).

## Parameters

Every assumption is a named constant at the top of `frame.py` (panel outline and tolerances, stand-off,
sheet and gasket thickness and compression, oven sheet thickness, wall / rib / draft, boss and screw sizes,
loop envelopes and clearance, feet positions, pegs). Change one, run `build.py`, read `out/summary.json`.
If the board moves a hole or a connector, run `build.py --dump`; if the panel model changes (loops), update
`LOOPS` / `LOOP_Z` from `../models3d/tft7_sat070at40d21.py` (the fit check measures the real tails anyway).
