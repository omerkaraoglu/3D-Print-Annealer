# Rev3.0 PCB layout generator

The Rev3.0 board (`KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pcb`) was produced by these scripts; re-run them instead of
hand-editing when the placement or the rules change. Two Python interpreters are used: KiCad's own
(`C:/Program Files/KiCad/10.0/bin/python.exe`, has `pcbnew`) for everything that touches a board file, and a system
Python with numpy / scipy / Pillow / PyMuPDF for the renders. All coordinates in the scripts are "local" board
millimetres (x right, y down, origin at the board's top-left corner); `placement.py` adds the 20 mm KiCad sheet offset.

| Step | Script | Interpreter | What it does |
|---|---|---|---|
| 0 | `gen_footprints.py`, `gen_heatsink_fp.py` | KiCad / any | write the verified footprints into `ComponentsLibrary/User Created/Rev3/Rev3.pretty` (Connfly DS1020-09, Core Master SRI0605B, Viking PCD0403, DEGSON DG127H, LFU09V-103; pass 2: Fischer SK 409 63,5 STC heatsink with its own F.Cu keep-out zones) |
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

## Layout pass 2 (2026-11-11)

`sch_pass2.py` made the schematic edits of pass 2 (Q1 → BTA24-800CWRG, R1 = 1 kW heater, new HS1 heatsink symbol with no-connect
pins; `extract_sym.py` copies the KiCad `Mechanical:Heatsink_Pad_2Pin` symbol into the sheet). `placement.py` now applies every
`placement_override_<region>.py` (display / power / mains) after its own list — each routing agent moved its own parts there;
`build_board.py` and `export_geom.py` accept an output name so each region could rebuild its own placed board. `netclasses.py`
adds the `heatsink_pins_vs_mains/selv` rules. `fill_zones.py` + `deliver.py` fill the zones under the project name and re-export
netlist / BOM / CPL / DRC. The briefs the agents worked from are `AGENT_BRIEF.md` (pass 1, common rules) and `PASS2_BRIEF.md`.

Notes from the pass-2 merge:
- KiCad evaluates **creepage per net pair** (a footprint test such as `memberOfFootprint` is ignored) and a later creepage rule
  cannot relax an earlier one, so the HS1 pin nets (`unconnected-(HS1-Pad1/2)`) are excluded by name from
  `mains_to_selv_creepage` and get their own `heatsink_pins_vs_mains_creepage` (2.5 mm) / `heatsink_pins_vs_selv_creepage`
  (6.4 mm). The intended Q1-on-HS1 courtyard overlap is silenced by `q1_on_heatsink_courtyard` (`severity ignore`).
- The mains "no inner copper" polygon and the SELV plane outline share the corner under the PSU body; it is at y 60 (was 80) so
  that the In2 3V3 plane reaches the strip east of the +5 V island (R125's 3V3 via lives there). Keep the two polygons in step.
- When a region is re-routed, strip **every** stub of the moved parts from `tracks_signals.json`, not only the moved nets:
  pass 2 left nine GND/+3V3 stubs of the old J11 companions behind, which collided with the relocated buck (fixed in the merge).
- `mains2_check.py geom.json crt_all.json tracks_display.json,tracks_signals.json,tracks_power.json` (system Python, shapely) is
  the pass-2 mains placement checker (heatsink envelope vs tall parts, HS1 pins, creepage proxies, edge); `dump_crt.py` writes
  the courtyard JSON it needs from the built board. `d2_lanes.py` / `display_lane_decision.md` hold the RGB lane-order analysis
  (the current netlist is the crossing-minimal mapping; 59 vs 187 ribbon crossings).

## Layout pass 3 (2026-11-12, EMC assessment)

`sch_pass3.py` moved the LC input filter to the mains input (F3 main fuse → L40 → LINE_FILT → triac / relay / F1 → PSU_L → L1); the
mains agent re-placed and re-routed the band, the display agent re-spaced the via rows so that no In1 anti-pads merge
(`in1_web_check.py board.kicad_pcb` must report 0 merged groups; rule: ≥ 1.35 mm between non-GND vias, ≥ 1.10 mm GND-to-signal).
The EMC estimates and the IEC 61000-4-15 flickermeter model live in `Design Reports/Rev3.0/sim/emc/`.
