# Rev3.0 carrier frame v2 — native Fusion 360 build

These scripts build the v2 frame in Fusion 360. v2 replaces v1's eight cantilevered feet with a continuous perimeter flange and ten M4 stud bosses. The scripts also build the fit-check assembly and its exports. The geometric reference is v1 (`../../frame/frame.py`), in the same coordinate frame:

- X = KiCad absolute x;
- Y = −(KiCad absolute y);
- Z = 0 at the physical PCB back, +Z toward the component side.

Every plan dimension is driven by a user parameter, typed in KiCad absolute coordinates (y down).

## Fusion documents

Project **Oven**, folder **Rev3.0 OVEN CONTROLLER**, two documents:

- `Rev3.0 Frame v2`: the parametric part, one body `Frame v2`.
  - v1: first features.
  - v2: body complete.
  - v3: root fillets.
- `Rev3.0 Frame v2 fit assembly` contains:
  - the frame, as a linked occurrence;
  - the board STEP;
  - the Formex sheet, the compressed gasket and the oven-sheet patch;
  - a hidden check component holding the socket cylinders.

## How the scripts are run

Each `NN_*.py` file defines `run(_context)` and is executed verbatim through `fusion_mcp_execute` (featureType `script`).

- **01–16:** the full text was pasted into the call.
- **17 onward:** a three-line runner executes the file's text:
  `exec(compile(open(P).read(), P, 'exec'), ns); ns['run'](_context)`.
  The executed code is therefore exactly the file.
- **Shared helper:** `fv2lib.py` (reloaded by every script). It holds the parameter, sketch, extrude and fillet helpers, the scans and the assembly helpers.
- **Logging:** progress goes to the session scratchpad `cad/fusion_log.txt`.
- **Guard:** every script first checks that the active document carries the `fv2/doc` attribute of the document it expects. If not, it raises.

## Rebuild order (frame document)

| script | does |
|---|---|
| 01_new_doc_params_planes | new design doc, mm, all user parameters (≈115 + ear holes), Z construction planes |
| 02_body_flange | outer body block (OUTER, R5, 1° draft) + full flange plate (R12, 1° draft); closed the coordinator's viewing doc |
| 03_save_as | folder + `saveAs('Rev3.0 Frame v2', …)` → v1 |
| 04_tail_block_cells (+ 04b_rename) | tail-wall block to Z_TROUGH_TOP; corner cells (cell face lies on the block's drafted face) |
| 05_pcb_bosses_cell_ribs | 9 bosses Ø8 (cones to Z_FRONT); cell ribs boss→beam and across at `crib_y` |
| 06_pocket_window_trough | panel pocket (0.5°), 45° lead-in, above-shelf space, window, tail pocket |
| 07_pcb_support_ribs | the 26 v1 ribs (fixed geometry); the wall end is buried 0.5 mm |
| 08_pcb_pilots | blind Ø2.4 pilots (0.5°, floor 1.0 above Z_FRONT) + Ø3.2×0.5 reliefs |
| 09_stud_params_tubes | `fh1_x … fh10_y` parameters + 10 stud tubes Ø10 (top) |
| 10_stud_ribs_holes | 1 radial rib per tube (both ends buried 0.5) + Ø4.5 holes (0.5°, widening to the back) |
| 11_pegs | P1/P2 Ø3×0.8 (suppressed when `pegs_on` = 0, re-run 11) |
| 12_save_body_complete | save → v2 |
| 13_scan | read-only scans (slivers, draft/undercut classes) |
| 14a_fillet | R0.5 stud tubes + ribs (80 edges). `14b_fillet_FAILED_old_grouping.py` failed (ASM_BL_END_TOO_CMPLX) and created nothing; superseded by 16x |
| 15_fix_tail_wall_ledge | tail-wall end line referenced at Z_SHELF_BACK (`tail_wall_y0`); removes a 0.153 ledge at Z 0 |
| 16b…16i | root fillet sets (fv2lib.FILLET_SETS, edges grouped by creating features). Run 16b, c, d, e, f, g, h, i in that order |
| 18_redo_shelf_back_fillets | deletes 16e + 16h (run-off wedge across the shelf end) and redoes shelf back without the 2 segments into the tail pocket |
| 19_top_shelf_fillets_appearance | the 2 top shelf-back segments + black nylon appearance |
| 21_delete_tail_corner_fillet | deletes the tail-pocket corner fillet (flap up the tail wall) |
| 17_scan_post_fillet | read-only scans + thin-strip scan + unfilleted-root census (run after 21) |
| 22_save_fillets | save → v3 |
| 23_export_frame | `Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2.step / .stl / .f3d` |
| 20_grid_toggle | attempt to hide the layout grid for screenshots (no effect; list control) |
| 24_frame_renders | 6 frame PNGs → `Mechanical/Rev3.0_Frame/renders_v2/` |

Fusion has no "fillet group" undo, so a clean rebuild runs:

`01 02 03 04 05 06 07 08 09 10 11 12 14a 15 16b 16c 16d 16f 16g 16i`

followed by the shelf-back set from 18 (skip its deletes) and 19. Script 18 does the deletes automatically if the old features exist.

## Assembly document

| script | does |
|---|---|
| 30_asm_new_doc_link_frame | new doc, saveAs, frame inserted as a linked occurrence |
| 31_asm_import_board | board STEP into component `Rev3.0 PCB full (KiCad STEP)` (174 s, 309 occurrences) |
| 32_asm_board_shift_parts | board +0.08 Z (snapshot), assembly parameters, Formex sheet, gasket, oven-sheet patch |
| 37_fix_oven_patch | rebuilds the patch (the negative-coordinate dimension flip, fixed in fv2lib) |
| 33_asm_census | read-only body census → `census.json` |
| 34_fit_frame_vs_board | read-only min distance + overlap, frame vs 292 board bodies → `fit_frame_board.json` |
| 35_fit_parts_tool_access | sheet / gasket / patch vs frame, sheet vs board (lead tips), Ø12 socket cylinders (hidden check component) → `fit_parts.json` |
| 36a, 36b (×4), 36c, 36d (×4) | assembly renders; batched hide and show of the 146 board children (never more than 40 per call) |
| 38_asm_save | assembly milestone save |
| 39_frame_doc_report | read-only report of the frame doc (timeline, parameters, Z 0 faces) → `frame_doc_report.json` |

## v2.1 (coordinator review, 2026-11-13): frame v4, assembly saved again

| script | does |
|---|---|
| 40_v21_strip | deletes every root fillet, the 30 stud features (tube / rib / hole) and the support ribs (71 timeline items) |
| 41_v21_params | symmetric `fl_x0` / `stud_xl`; deletes `stud_offset_l`, `flange_w_l`, `tail_wall_y0`; adds `stud_slot` 0.8 and `tail_wall_step_y` 129.0; tail-wall step face at y 129 at Z_PCB; Window cut to Z_PCB + 1; new fh1..fh10 |
| 42_v21_support_ribs | 26 ribs rebuilt **before** the Window cut (marker rolled back). Free ends run 0.5 past the shelf edge (and past the shelf end over the tail pocket), so the cuts trim them flush. Pad test in `../rib_pad_check.py` (all 26 extended; min 1.147 mm J4.1) |
| 43a_v21_stud_tubes_ribs, 43b_v21_stud_slots | tubes and ribs at the new pattern; 4.5 × 5.3 stadium slots along the edge (centre rectangle + 2 end circles, growing 0.5° taper) |
| 44a/44b_v21_fillets | 8 R0.5 fillet sets (337 roots) |
| 44c/44d | R0.3 attempt on the 2 tail-pocket corners: rises to Z −1.919 (0.18 above the shelf back), deleted |
| 45_scan_v21 | scans (TAG post_fillet_v21) |
| 46_v21_above_z0_points | frame ∩ box Z 0…50 → point cloud; `../above_z0_check.py` proves 0 mm³ inside the PCB outline + 1 mm |
| 47_v21_save_frame | frame saved → v4 |
| 23 (re-run), 48_frame_renders_v21 | exports; renders (stud close-up re-targeted to FH2 x 102.75) |
| 49_frame_doc_report_v21 | report of the newest frame version (the assembly keeps a hidden copy of the old linked version under the same name) |
| 50_v21_asm_update | linked frame → latest version, assembly parameters, patch follows, socket-check cylinders rebuilt |
| 34, 33 (re-run), 51_v21_fit_parts_tool_access, 52_v21_socket_vs_frame_wall | fit checks (old v2.0 JSONs renamed `*_v20.json`) |
| 36a-d (re-run) | assembly renders |
| 53_v21_asm_save | assembly saved |

### v2.1 final: hole shift (frame v5, assembly saved again)

| script | does |
|---|---|
| 54_v21_hole_shift | FH1 x 43.5, FH2 x 103.5, FH4/FH10 y 40.5, FH5/FH9 y 98.5 (parameters only; tubes, ribs, slots and fillets follow); frame saved → v5 |
| 45 (re-run), 23 (re-run), 55_frame_renders_v21_final | scans, exports, renders (stud close-up at FH2 x 103.5) |
| 49 (re-run) | frame report (v5) |
| 56_v21_asm_update_final | assembly: linked frame → v5, fh parameters (patch Ø4.3 holes follow), socket cylinders at the final positions |
| 51, 52, 34, 36a (re-run) | socket and fit checks, iso renders (v2.1a results kept as `*_v21a.json`) |
| 57_v21_asm_save_final | assembly saved |

**Final stud slots** (KiCad absolute, y down). Slot 4.5 × 5.3 (`stud_hole` × `stud_hole + stud_slot`), 0.5° draft wider at the back, axis along the edge.

| slot | x | y | axis | to nearest ear hole | to PCB outline | Ø12 socket to board | socket to frame (wall/bosses above the washer) |
|---|---|---|---|---|---|---|---|
| FH1 | 43.5 | 8.75 | X | H1 14.56 | 10.06 | 4.06 | 1.60 |
| FH2 | 103.5 | 8.75 | X | H2 11.83 | 7.33 | 1.33 | 1.60 |
| FH3 | 162.0 | 8.75 | X | H3 13.18 | 8.68 | 2.68 | 1.60 |
| FH4 | 195.17 | 40.5 | Y | H4 11.79 | 7.30 | 1.29 | 1.60 |
| FH5 | 195.17 | 98.5 | Y | H5 11.79 | 7.30 | 1.29 | 1.60 |
| FH6 | 171.0 | 161.2 | X | H6 37.61 | 33.11 | 9.98 (TFT tail) | 1.60 |
| FH7 | 102.5 | 161.2 | X | H6/H7 81.6 | 42.2 | 9.14 (TFT tail) | 1.60 |
| FH8 | 34.0 | 161.2 | X | H7 37.61 | 33.11 | 23.4 (CTP tail) | 1.60 |
| FH9 | 9.77 | 98.5 | Y | H8 11.82 | 7.32 | 1.32 | 1.60 |
| FH10 | 9.77 | 40.5 | Y | H9 11.82 | 7.32 | 1.32 | 1.60 |

- Top spans are 60.0 / 58.5. Gasket lift (nominal, 1000 h): ≤ 71.6 µm with the exact load model and ≤ 73.7 µm with the smeared model, against a 90 µm limit.

**For the toolmaker: inside corners intentionally left sharp (no R0.5), accepted by the owner (2026-11-13):**

1. Tail-pocket corner, left: the shelf end face (y 119.0) meets the tail-pocket side face (x ≈ 39.2), vertical, Z −4.6 … −2.1. R0.5 rolled 6 mm up the tail wall; R0.3 rose 0.18 above the shelf back.
2. Tail-pocket corner, right: the same at x ≈ 167.4.
3. Shelf back ↔ bottom pocket wall, left segment: y 119.25, x ≈ 29.3–39.0, Z −2.1. The fillet would roll across the free shelf strip at the tail pocket.
4. Shelf back ↔ bottom pocket wall, right segment: y 119.25, x ≈ 167.6–175.7, Z −2.1.

The toolmaker may break these 4 with a small radius in the steel (≤ 0.2) if the polishing allows.

## v2.2 (2026-11-13): frame v6, assembly v5

Two changes:

- **Taller stud tubes.** `stud_boss_h` is now the tube height **above the flange back**: `Z_STUD_TOP = Z_FLANGE_BACK + stud_boss_h` = −3.52, the washer/nut seat. The radial rib runs the full tube height. The stack is 7.5 frame + 1.0 DIN 9021 washer + 5 M4 nyloc = 13.5 mm from the sheet, so the stud is a **PEM FH-M4-18**.
- **Pegs moved and slots made radial.** The pegs are now on the side flanges at P1 (9.77, 69.5) and P2 (195.17, 69.5), front face, Ø3 × 0.8. The datum is `datum_x` = (peg1_x + peg2_x)/2 = 102.47, `datum_y` = 69.5. Each stud slot (4.5 × 5.3) is radial from the datum.

| script | does |
|---|---|
| 58_v22_tubes_pegs | stud_boss_h / Z_STUD_TOP / datum / peg parameters; tube distance `stud_boss_h + flange_t`, rib distance `stud_boss_h`; deletes the axis-aligned slots |
| 59_..._FAILED_rolled_back | the stud fillet re-made AFTER the wall-to-flange fillet failed (ASM_BL_END_TOO_CMPLX); rolled back |
| 59b_v22_stud_fillet_radial_slots | stud fillet re-made at its original timeline position; radial slots cut at the end. The slot sketches are FIXED geometry computed from fhN / datum / stud_hole / stud_slot: **re-run this script if any of those change** |
| 61_v22_fix_tube_direction | FIX: editing the tube distance in 58 had flipped the extrude direction (tubes grew up to +3.98, caught by the above-Z0 check). Each tube is redefined with `setOneSideExtent(NEGATIVE)` at its own position, and the stud fillet re-made (80 roots) |
| 60_scan_v22, 46 (re-run) | scans, above-Z0 proof |
| 62_v22_save_frame | frame → v6 |
| 23 (re-run), 63_frame_renders_v22 | exports; 7 frame renders including `Fusion_Frame_closeup_peg_P1_side_flange` |
| 49 (re-run) | frame report |
| 64_v22_asm_update | assembly: frame → v6, peg parameters. Oven-sheet patch rebuilt: P1 Ø3.2 round, P2 slot 3.2 × 3.9 along X, studs Ø4.3. Socket cylinders now from Z −4.0 |
| 34, 51 (re-run), 65_v22_socket_vs_frame_wall | fit checks; socket vs frame faces above the washer top Z −2.52 |
| 36a (re-run), 66_v22_asm_save | assembly iso renders, assembly → v5 |

**Final v2.2 stud slots** (KiCad absolute, y down). Axis angle from +X, measured in KiCad coordinates. Thermal movement = r × 58e-6 × 60 against a slot travel of 0.4 + 0.25.

| slot | x | y | axis ° | r from datum | move (datum case) | P1-fixed along / across |
|---|---|---|---|---|---|---|
| FH1 | 43.5 | 8.75 | −134.15 | 84.66 | 0.295 | 0.070 / 0.231 |
| FH2 | 103.5 | 8.75 | −89.03 | 60.76 | 0.211 | 0.217 / 0.323 |
| FH3 | 162.0 | 8.75 | −45.58 | 85.06 | 0.296 | 0.522 / 0.230 |
| FH4 | 195.17 | 40.5 | −17.37 | 97.13 | 0.338 | 0.646 / 0.096 |
| FH5 | 195.17 | 98.5 | 17.37 | 97.13 | 0.338 | 0.646 / 0.096 |
| FH6 | 171.0 | 161.2 | 53.23 | 114.48 | 0.398 | 0.591 / 0.258 |
| FH7 | 102.5 | 161.2 | 89.98 | 91.70 | 0.319 | 0.319 / 0.323 |
| FH8 | 34.0 | 161.2 | 126.75 | 114.44 | 0.398 | 0.205 / 0.258 |
| FH9 | 9.77 | 98.5 | 162.63 | 97.13 | 0.338 | 0.030 / 0.096 |
| FH10 | 9.77 | 40.5 | −162.63 | 97.13 | 0.338 | 0.030 / 0.096 |

The "P1-fixed" columns assume the frame grows about P1 (round hole in the sheet) and y 69.5, which is what a round P1 hole plus an X-slotted P2 hole impose. The across-slot movement is then 0.258–0.323 at FH2, FH6, FH7 and FH8, more than the 0.25 clearance. The peg-to-peg growth at 70 ppm is 0.645, more than the 0.45 half travel of the 3.9 slot. See the report for options.

### v2.2 final (owner decision): frame v6 FINAL, assembly v6

- **Oven-sheet peg holes:** both are slot 3.2 × 3.9 along X (`sheet_peg_slot` 0.7), made by script `67_v22_sheet_peg_slots`. The stud holes in the sheet stay round Ø4.3 (PEM FH-M4-18).
- **Frame stud slots:** radial from the datum (102.47, 69.5), 4.5 × 5.3.
- **Kinematics:** the two X-slots fix only the y = 69.5 line and the rotation. x is located by the stud slots themselves (FH2/FH7 are Y-slots with 0.25 across-clearance in x). The frame therefore grows about the pattern centre within ±0.25, so the "datum case" column applies; the "P1-fixed" columns above are superseded. The peg-to-peg growth of 0.645 is shared by the two slots (0.35 travel each).
- **Glass location:** y ±0.1 by the pegs, x ±0.25 by the studs.
- **Scripts:** 51 and 65 re-run (patch vs frame: coplanar contact, 0 overlap; socket results unchanged); 36a-d re-run (assembly renders including both `*_no_PCB` views); `68_v22_asm_save_final` saves the assembly → v6 ("v2.2 final fit: both peg holes X-slots").
- **Exports:** only `Rev3.0_Frame_v2_params.json` was re-exported. The frame STEP / STL / F3D are unchanged from v6.

`../hole_pattern_calc.py` now uses the corrected socket rule (≥ 6.5 from the outline, ≥ 11.0 from H1..H9) and the v2.1 pattern. `../build_params_json.py` writes the v2.1 keys.

## Offline scripts (in `..`)

- **`hole_pattern_calc.py`:** stud-pattern rules and the gasket-lift beam calculation. `--json hole_pattern_result.json`.
- **`fit_analyse.py`:** maps every board body to its KiCad reference and lists the minima. Use `--parts` for the parts, the lead tips and the tool access.
- **`build_params_json.py`:** writes `Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2_params.json`.

## Parameters that matter

- **Stud pattern:** `fhN_x`, `fhN_y`. The coordinate along the stud line is an expression of `stud_yt`, `stud_yb`, `stud_xl` or `stud_xr`.
- **Flange and studs:** `stud_offset` 7.5 (`stud_offset_l` 8.5), `flange_w` 14 (`flange_w_l` 15), `flange_t`, `flange_r`, `stud_boss_od`, `stud_boss_h`, `stud_hole`.
- **Z levels:** all derived from `standoff`, `sheet_t`, `panel_t`, `gasket_t`, `gasket_comp`, `shelf_t`, `loop_z_top` and `loop_clr`.
- **Not parametric:** the 26 support ribs are fixed v1 geometry (pad clearances). Change them in `fv2lib.RIBS` and rebuild 07.
