# Rev3.0 PCB layout generator

The Rev3.0 board (`KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb`) was produced by these scripts; re-run them instead of
hand-editing when the placement or the rules change. Two Python interpreters are used: KiCad's own
(`C:/Program Files/KiCad/10.0/bin/python.exe`, has `pcbnew`) for everything that touches a board file, and a system
Python with numpy / scipy / Pillow / PyMuPDF for the renders. All coordinates in the scripts are "local" board
millimetres (x right, y down, origin at the board's top-left corner); `placement.py` adds the 20 mm KiCad sheet offset.

| Step | Script | Interpreter | What it does |
|---|---|---|---|
| 0 | `gen_footprints.py` | KiCad | writes the verified footprints into `ComponentsLibrary/User Created/Rev3/Rev3.pretty` (Connfly DS1020-09, Core Master SRI0605B, Viking PCD0403, DEGSON DG127H, LFU09V-103) |
| 1 | `kicad-cli sch export netlist --format kicadsexpr -o rev3.net 3dFilamentDryer.kicad_sch` | kicad-cli | netlist used by the builder (`netdump.py` lists it) |
| 2 | `netclasses.py` | any | net classes (IPC-2152 widths) into `3dFilamentDryer.kicad_pro`, isolation / creepage rules into `3dFilamentDryer.kicad_dru` |
| 3 | `build_board.py [out.kicad_pcb]` | KiCad | 4-layer board, outline, slots, mounting holes, placement from `placement.py`, planes, keep-outs, rule areas, texts (no tracks) → `rev3_placed.kicad_pcb` |
| 4 | `export_geom.py board.kicad_pcb geom.json` | KiCad | pads / keep-outs / edges for the routing helpers |
| 5 | `route_display.py`, `route_signals.py`, `route_power.py`, `route_mains.py` | system | hand-routed regions written with the `handroute.py` helper (explicit track / via lists, 0/45/90° only, track ends at pad centres); each writes `tracks_<region>.json` and can check itself against the project DRC |
| 6 | `merge_final.py` | system (calls both) | concatenates the four track files, `import_tracks.py` onto the placed board, `finalize_board.py` (stackup, title block), `drc_run.py`, `metrics.py` |
| - | `render.py`, `crop.py`, `overlap.py`, `metrics.py` | system / KiCad | PNG renders / crops, courtyard-overlap check, per-net lengths and via counts |

`mains_placement_proposal.py` + `mains_propcheck.py` are the checker-driven placement of the 230 V band (2.5 mm
mains-to-mains, 6.4 mm mains-to-SELV, heater loop local to the triac); its `put()` lines were copied into `placement.py`.

Clearances enforced by the DRC rules (and mirrored in the helpers): 0.2 mm SELV, 0.15 mm bus-to-bus, 0.13 mm at the
0.4/0.5 mm pitch packages (rule areas `u10_escape`, `u20_escape`), 2.5 mm mains-to-mains (IPC-2221B B2, 301-500 V
peak), 6.4 mm clearance **and** creepage mains-to-SELV, 1.0 mm mains-to-edge. Component-inherent exceptions (relay coil,
optocoupler and triac pin pitches, the L/N chains) are explicit named rules in the `.kicad_dru`.
