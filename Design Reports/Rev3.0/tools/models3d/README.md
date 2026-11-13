# Rev3.0 3D models (CadQuery)

Parametric scripts for the parts of the Rev3.0 board that have no usable KiCad
stock model, plus the 7" SATOZ panel with its folded FPC tails. One script per
part (the FPC connector and solder-wire scripts each build a small family).
Outputs go to `KiCad/ComponentsLibrary/User Created/Rev3/Rev3.3dshapes/`
(`.step` used by the footprints, `.wrl` copies scaled to KiCad's 0.1-inch VRML unit).

## Environment

No CAD program is needed. CadQuery runs from a venv on Python 3.11:

```
C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe -m venv <venv>
<venv>\Scripts\python.exe -m pip install cadquery matplotlib
```

(tested with cadquery 2.8.0 / OCP wheels, matplotlib 3.11). KiCad 10's own
Python (`C:\Program Files\KiCad\10.0\bin\python.exe`) is used read-only by
`dump_pads.py` to read the footprint pads.

## Build

```
set MODELS3D_RENDER_DIR=<folder for PNG renders>   (default: .\renders)
<venv>\Scripts\python.exe build_all.py
```

`build_all.py` runs, in order: `dump_pads.py` (KiCad Python) -> every part
script -> `make_mech_footprint.py` -> `set_model_fields.py` ->
`make_models_json.py` -> `dump_board_fps.py` (KiCad Python) ->
`standoff_fitcheck.py`, then re-imports every STEP and prints a table
(pins vs pads PASS/FAIL, bounding box, STEP re-import check). It exits non-zero
on any failure.

| script | part(s) | footprint |
|---|---|---|
| `l_pcd0403.py` | L11, L12 Viking PCD0403 | `Rev3:L_Viking_PCD0403` |
| `l_sri0605b.py` | L30 Core Master SRI0605B | `Rev3:L_CoreMaster_SRI0605B` |
| `l_rc1415u.py` | L40 Core Master RC1415U-101K | `Rev3:L_Radial_CoreMaster_RC1415U` |
| `l_lfu09v103.py` | L1 Core Master LFU09V-103 | `Rev3:LFU09V-103` |
| `c_c42p2105kbs.py` | C40 Faratronic C42P2105KBSC400 | `Rev3:C_Rect_L32.0mm_W9.0mm_P27.50mm_X2` |
| `hs_sk409.py` | HS1 Fischer SK 409 63,5 STC | `Rev3:Heatsink_Fischer_SK409_63.5_STC` |
| `fpc_connectors.py` | J10 Connfly DS1020-09-40VBT1B, J11 KLS1-242D-1.2-06, (unused) DS1020-09-40/06VBT1A | `Rev3:Connfly_*`, `Rev3:KLS_*` |
| `tb_dg127h.py` | J20 DEGSON DG127H-5.08-02P | `Rev3:TerminalBlock_DEGSON_DG127H-5.08-02P` |
| `fuse_reomax_r3_5a.py` | F1, F3 Reomax R3-5A clips + 5x20 fuse | `Fuse:Fuseholder_Clip-5x20mm_Littelfuse_445-030_...` |
| `solderwire_stub.py` | J3, R1, J4 wire ends | `Connector_Wire:SolderWire-*` |
| `tft7_sat070at40d21.py` | SATOZ SAT070AT40D21 7" TFT + CTP, tails folded to J10/J11 | `Rev3:TFT7_SAT070AT40D21_Mech` |

Conventions (all models): millimetres, origin = footprint origin, +Z up from the
board, model Y = -footprint y. Pins are tagged solids; `common.verify()`
compares their XY centres with the pads in `pads.json` (tolerance 0.05 mm).

The display model is built in the panel's front-view frame; its footprint is
placed on **B.Cu** (flip left/right), so KiCad mirrors it into the back view the
PCB top side sees. The tail hang below the board edge is solved from the J10 /
J11 positions (constants at the top of `tft7_sat070at40d21.py`) - re-run after
moving a connector.

### Display stand-off (round 2)

`STANDOFF = 5.0` at the top of `tft7_sat070at40d21.py` is the gap between the
PCB back and the panel back (a spacer in the frame). It is baked into the STEP
(panel back at model z = STANDOFF), so the footprint's `(model ...)` offset
stays `0 0 0`. `J10` / `J11` there are the connector positions the tails are
solved for. `dump_board_fps.py` (KiCad Python, loads a temporary copy of the
board) and `standoff_fitcheck.py` then list the lead protrusion of every
through-hole part below the PCB back against the stand-off
(`out/standoff_clearance.json`) and render `R2_*.png` (bottom edge, gap
section, side view, J10 / J11 fold sections) into `MODELS3D_RENDER_DIR`.

## Files for the board editor

`models.json` lists, per board reference, the model to set (replacing the whole
model list) and, under `"mechanical"`, the display footprint to add (position,
side, orientation). The scripts never write the `.kicad_pcb`.
