# Rev3.0 GlassFront frame ("Frame GF") — native Fusion 360 build, stage 1

These scripts build the glass-front carrier frame as a parametric Fusion 360 part, from the frozen master
`Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json` (GF-1.0; revised to GF-1.1 in stage 3, see the last
sections). The concept is in
`../concept/concept.md` (sections 3, 4, 11). Geometry above Z −5.0 is frame v2 (`../../frame_v2/fusion/`, not edited;
`gflib.py` started as a copy of `fv2lib.py`).

Coordinates (as v2): X = KiCad abs x, Y = −(KiCad abs y), Z = 0 at the physical PCB back, −Z towards the oven front.
Every plan value is typed as a user-parameter expression in KiCad abs coordinates (x, y down).

## Fusion document

- Hub `hub1` › project **Oven** › folder **Rev3.0 OVEN CONTROLLER** › **Rev3.0 GlassFront**
  (`urn:adsk.wipprod:dm.lineage:XyXacwE-SnqsV-hz5pHg3w`), version 4 = final.
  - v1 empty document + component (01), v2 body complete (08), v3 fillets + slots (14), v4 final (27).
- Root component `Rev3.0 GlassFront` › occurrence `Frame GF:1` › component **Frame GF** › one body **Frame GF**
  (appearance `Plastic - Matte (Black)`). Stage 2 adds `Glass`, `Oven sheet`, … as sibling components under the root.
- 240 user parameters at document level (lower-case master names; Z levels with the master expressions).
- Guard: attribute `gf/doc = 'Rev3.0 GlassFront'`; every script calls `gflib.check_doc()` first.
- No other document was opened, modified or saved.

## How the scripts are run

Each `NN_*.py` defines `run(_context)` and is executed verbatim through `fusion_mcp_execute` (featureType `script`)
with a three-line runner:

```python
P = r"...\Design Reports\Rev3.0\tools\glassfront\fusion\NN_name.py"
def run(_context: str):
    ns = {"__name__": "gf_script", "__file__": P}
    exec(compile(open(P, encoding="utf-8").read(), P, "exec"), ns); ns["run"](_context)
```

`gflib.py` is re-imported by every script. Log: `%TEMP%\rev3_glassfront\fusion_log.txt`; JSON dumps go to the same
folder. A script that raises is rolled back by Fusion as one transaction (seen twice, see the run log).

## Clean rebuild order

| script | does |
|---|---|
| 01_new_doc_component_save | new parametric doc, mm, guard attribute, component `Frame GF`, saveAs (v1); probes the expression functions (`max(a; b)`, `min`, `floor`, `abs`, `sqrt`) |
| 02_params_planes | all user parameters; 10 hidden planes in `Frame GF`; 8 hidden root planes `REF Z_…` for stage 2. Level snap automatic: `snap_keep = min(1; floor(abs(Z_FLANGE_BACK_RAW − Z_LANDPLATE_BACK_RAW) / level_snap))` |
| 03_flange_plates_lip_pads | Flange plate (new body), Land plate + step wall (back), Seat ring (step wall front), Lip, Corner pads F1-F4; checks the sketch frame and the taper sign |
| 04_wall_block_cells_bosses | v2 outer wall block, tail-wall block, corner cells, PCB bosses H1-H9, cell ribs (front reference Z_LAND) |
| 05_recess_pockets_ribs_window | Glass recess, Clearance pocket, Above-shelf space, 26 PCB support ribs, Window, Tail pocket (no floor) |
| 06_pips_pilots | Pips P1-P8, blind PCB pilots (floor 1.0 behind the land), pilot reliefs |
| 10_fillets_before_tubes | R0.5 edge sets (bosses on walls, cells + cell ribs + cell bosses, support-rib sides, shelf back), rule fillet "wall + step wall to plates", edge sets shelf front, tail walls to wall top |
| 07_tubes_tube_ribs | Fastener tubes F1-F8 (Ø18 top, NEGATIVE extent), tube ribs F1-F4 (45°, top `Z_TRIB_TOP`) |
| 11_rule_fillet_tubes_ribs | rule fillet R0.5 = all concave edges of the tube and tube-rib faces |
| 12_fillets_front_lip_appearance | R0.5 land / recess wall, R0.2 lip root, R0.3 lip top edges, black appearance |
| 13_fastener_slots | radial stadium slots 5.4 × 7.0 at the flange front, 0.5° (back cut F1-F8, front cut through the F1-F4 pads) |
| 14_save_fillets_slots / 27_final_save_docinfo | saves (27 refuses unless all flex parameters are at their defaults) |

In the actual build 07 ran before 10 (10 rolls the marker back to before `Fastener tubes F1-F8 sketch`, so the timeline
order is the clean order above). Checks and outputs (read-only unless noted): `20_scan`, `21_sections_dump`,
`22_carryover_vs_v2_step` (imports the v2 STEP into a temporary occurrence and deletes it again), `23_above_z0_points`,
`24_dimension_check`, `25_export_frame` (writes the STEP / STL), `26_renders` (writes PNGs; section analyses deleted
again), `90_flex_test` (changes parameters and restores them), and offline `gf_offline_checks.py` (shapely:
thin-wall probe, above-Z0, carry-over XOR), `build_report_json.py` (writes the report JSON).

## Timeline (77 items, all healthy)

Planes, then: Flange plate · Land plate + step wall (back) · Seat ring (step wall front) · Lip · Corner pads F1-F4 ·
Outer wall block · Tail wall block · Corner cells · PCB bosses H1-H9 · Cell ribs boss to beam · Cell ribs across ·
Glass recess · Clearance pocket · Above-shelf space · PCB support ribs (26) · Window · Tail pocket · Pips P1-P8 ·
PCB pilots H1-H9 · PCB pilot reliefs · 7 root-fillet features (bosses, cells, rib sides, shelf back, wall + step wall
(rule), shelf front, tail walls) · Fastener tubes F1-F8 · Tube ribs F1-F4 · Root fillets tubes + tube ribs (rule) ·
land to recess wall · lip root R0.2 · lip top R0.3 · Fastener slots F1-F8 (back) · Fastener slots F1-F4 (through the
pads).

## Why rule fillets for two sets

The tubes, tube ribs and the step-wall back part change topology with `glass_t`: the F5-F8 tube top is above the
step-wall back below glass 3.5 and below it above 3.5; at the level snap (glass 1.1) the step-wall face behind the
flange vanishes. Edge-set fillets would lose references. Rule fillets re-collect edges on every recompute.
Finding (`diag_rule_fillet_probe*.py`): a rule takes the faces Fusion attributes to a feature, and a face that merges
with a coplanar face of that feature (the tube-rib top is flush with the land-plate back at glass 2.0 / 3.0) becomes
part of it. Hence all non-tube roots are filleted BEFORE the tubes in the timeline, and the tube rule comes after
them: the flex test then shows the same unfilleted-root census in every case.

## Not parametric / fixed choices

- Each sketch has a fixed reference point at abs (−100, −100); all dimensions are measured from it (no sign flip
  when geometry crosses x = 0 or y = 0, the flange and the fastener line lie at negative abs coordinates).
- Tube ribs F1-F4 run at 45° (`cos(45 deg)` in the corner expressions): exact because F1-F4 sit at the glass
  corner + `fast_off` in x and y, i.e. on the diagonal through the glass corner-arc centre.
- Edge-set fillets (bosses, cells, rib sides, shelf back / front, tail walls, land / recess, lip root, lip top)
  reference edges: re-run 10 / 12 if features are added in those regions.
- Bead, tape, sheet cut-out, glass, print window: reference parameters only (stage 2).

## Run log (2026-11-15)

| step | result |
|---|---|
| 01 | doc created, saved v1; `max(1 mm; 2 mm)` valid (`,` is not) |
| 02 | 238 parameters; levels = master table; inline snap check at 1.1 / 2.0 / 4.0 / 3.0 |
| 03–06 | 0 under-constrained curves; 85.20 cm³ after 07 |
| 07 | first tube-rib top = Z_TUBE_TOP left a 0.5 × 0.4 stub on the step-wall back (census 09) |
| 08 | saved v2 |
| 02 (re-run) + 07b | `trib_h_min`, `Z_TRIB_TOP`; rib re-made |
| 90 (pre-fillet) | all 7 cases healthy |
| 10x | first rule fillet (land plate in both sets) took the wrong edges, deleted inline |
| diag_rule_fillet_probe, …probe2 | rule semantics (probe2 timed out on the MCP side but completed; it also deleted the 10y fillets) |
| 10y | superseded fillet set (deleted by probe2) |
| 10 | first run raised on rolled-back items in the health check (rolled back by Fusion); `timeline_health` fixed; second run OK |
| 11, 90 (after_11) | rule fillet tubes; all cases healthy |
| 12 | OK |
| 13 | first run: stadium radius dim `VCS_SKETCH_SOLVING_FAILED` (rolled back); `diag_stadium_probe`: dimension the arc centres directly + tangents + one radius + equal; second run OK |
| 14 | saved v3 |
| 20, 21 (fix: `getStrokes`), 22, 23, 24, 90 final | checks below |
| 25 | STEP 1.48 MB, STL 5.05 MB |
| 26 | renders (section camera fixed, layout grid off) |
| 27 | final save v4 (its docinfo read v3 while the upload was running) |
| 28 | read-only: version refreshed to 4, document not modified |
| offline | `gf_offline_checks.py thin / abovez / carry`, `build_report_json.py` |

## Results (default parameters, glass 3.0)

- One solid, 787 faces, 83.997 cm³, 114.2 g at 1.36 g/cm³, bbox x −7.89…215.59, y −10.83…175.00 (abs), Z −14.42…+4.05.
- Draft scan: 0 flags (planar 0.5° / 1.0°, cones 0.5° / 1.0°, no undrafted face, horizontal faces only at the known levels, no A-side face above Z_SEAT).
- Slivers: 67 fillet-blend patches (57 sphere, 9 torus, 1 cylinder, max 0.40 mm²) + 1 design face (H7 cell strip, 2.28 mm², 2A/P 0.295).
- Thin-wall probe (13 plan sections): only the 1.0 lip (by design) and a 0.55 × 1.37 gap at the bottom of the H6 cell crescent inside the root-fillet band.
- Flex test: glass 2.0 / 4.0 / 1.1, t_sheet 0.8 / 1.5, t_opt 1.0 all healthy, one body, one lump; levels = master table; same root census in every case.
- Carried over: bosses / pilots / ribs / window identical to the v2 STEP; tail walls above Z 0 within 0.0105 mm; 0 mm³ above Z 0 inside the board outline + 1 mm (min 2.663 mm).

Full numbers: `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report.json`.

## Stage 2 (2026-11-15): Part A frame fix, Parts B-D fit assembly

Same document, same guard, same runner. Stage-1 dumps were copied to `%TEMP%\rev3_glassfront\stage1_dumps\` first.
`gflib.py` got appended assembly helpers (`new_comp`, `cplane`, `csketch`, `cextrude`, `hexagon`, `appearance`,
`min_dist_mm`, `overlap_volume_mm3`, `bodies_under`, ...) and one change: `timeline_health` checks the members of a
timeline group (the STEP import is a group whose own state reads 5). `gfasm.py` = assembly body lists for the checks.

### Part A - H6 / H7 cell corners (frame v5, exported again 14:21)

| script | does |
|---|---|
| diag_cells_probe | read-only: cell sketch arcs / radial dims, faces at the H6 / H7 corners |
| 30_fix_cell_corners | parameters `cell_r_h7` 1.0 and `h6_fill_y`; H7: radius of the boss-side cell corner = `cell_r_h7`; H6: corner arc (cell_r) moved down the left wall, tangent to it, crossing the boss at 90 deg on the cell floor (vertical closing line inside the boss); cell edge-set fillet deleted and re-created at its position (79 edges) |
| 31_partA_checks | runs 20 (TAG partA), 21, 23, 22 verbatim; offline `gf_offline_checks.py thin / abovez / carry` |
| 32_partA_flex | runs 90 verbatim (TAG partA) |
| 33_partA_flex_slivers | sliver rule per flex case, rule-fillet face counts |
| 34_partA_save_export | save (v5) + 25 verbatim (frame STEP / STL) |

Result: 0 design-face slivers (was 1), 0 thin gaps (was the H6 crescent), 0 draft flags, same root census, flex test
7/7 healthy with 0 design slivers in every case; carry-over regions identical; 84.016 cm3.

### Parts B-D - assembly

| script | does |
|---|---|
| 35_asm_params_layers | stage-2 user parameters; components Glass (arris, print layer, logo sketch), Optical bond, Formex sheet, Bead, VHB tape strips, Oven sheet (S4 body + hidden R4 body) |
| 36_asm_fasteners | Weld studs S4 F1-F4, Washers + nyloc nuts S4 F1-F4, Rivets R4 F1-F4 (hidden), Weld studs S8 F5-F8 (hidden), Washers, nuts, spacers S8 F5-F8 (hidden), Check - socket cylinders (hidden) |
| 36b_split_stud_components | migration only: the first 36 run had studs + nuts in one component per variant; deleted and rebuilt split (a clean rebuild skips 36b) |
| 37_asm_import_board | board STEP (kicad-cli from a COPY of the .kicad_pcb, see the docstring) into 'Rev3.0 PCB full (KiCad STEP)', 196 s, 309 occurrences (times out on the MCP side; watch the log) |
| 38_asm_board_shift | board +board_dz, DS1 (incl. rigid tails) by ds1_dz = Z_PANEL_BACK - ds1_model_back (-0.80); snapshot; idempotent via attributes |
| 39_fit_parts | frame vs parts, part pairs, flush plane, pips, layers, fasteners, sockets vs frame -> fit_parts.json |
| 40_fit_board | resumable: frame + parts vs 292 board bodies -> fit_board.json |
| 41_fit_tails_sockets_chin | tails (model and v2 position), fingers, sockets vs board, chin, Q1 leads -> fit_tails.json |
| 42_sections_asm | plan sections for g1 / g2 / panel-pocket / washer bearing -> sections_asm.json |
| gf_asm_offline.py | offline (shapely): `board`, `gaps`, `bearing`, `wires` |
| 43_asm_renders | Fusion_Assembly_*.png (views, R4, exploded with revertPendingSnapshot, hatched sections with contrasting appearances, restored) |
| 44_asm_board_visibility | batched (<= 40) hide / show of the board children for back_no_PCB |
| 45_frame_renders_refresh | stage-1 frame renders again (26 with the other components hidden) |
| 46_asm_save_export | final save, assembly STEP, Glass STEP, .f3d |
| 47_asm_docinfo | read-only docinfo_asm.json (tree, parameters, print window, chin opening) |
| build_stage2_reports.py | offline: Frame report (updated) + Assembly report JSONs |
| diag_board_tree, diag_peek | read-only probes |

Saves: v5 Part A, v6 layers + fasteners, v7 board, v8 studs split, v9 final.

Notes: a rigid DS1 shift puts the tail fingers 0.8 into the PCB (artefact, see the assembly report); renders show a
small point glyph from the board STEP (gone when the board is hidden; not geometry); Fusion's STEP export of the root
omits hidden occurrences / bodies (checked in the file by 46: the assembly STEP holds the S4 assembly only, 191 solids).
Results: `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Assembly_report.json`; Part A in the updated
`Rev3.0_GlassFront_Frame_report.json` (`stage2_partA`).

## Stage 3 (2026-11-15): GF-1.0 → GF-1.1

One batch on the same document (items 1-8 of the GF-1.1 brief + the lead amendment 7.2 × 8.8). Every change is a
user parameter (comment starts `GF-1.1:`) and a named feature. Stage-2 dumps / reports were copied to
`%TEMP%\rev3_glassfront\stage2_dumps\` first.

| script | does |
|---|---|
| 48_gf11_params_assembly | `R_glass` renamed `R_frame` (6.0; Fusion re-points every frame expression), new `R_glass` 6.25 (glass outline, print layer, bead) and `R_cut` 7.55 (both sheet bodies); `spacer_id` / `spacer_od` (DIN 988 6 × 12 × 1.0 S8 spacers, bodies renamed); all new parameters |
| 49_gf11_tail_pocket_h6 | tail-pocket sketch x dims `tr_x0 − tail_side_add` / `tr_x1 + tail_side_add`; H6 cell: jogged wall at `XJ` (tail wall `h6_wall_min` 1.1 at Z_PCB), R `h6_corner_r` 2.5 arc into the boss, slant `h6_jog_y` / `h6_jog_len`; `h6_fill_y` deleted; cell fillet re-created (81 edges) |
| 50_gf11_tube_stepwall_blend | rule fillet `Root fillets tube_sw_r - F5-F8 tube to step wall (rule)` before the R0.5 tube rule |
| 51_gf11_counterbores | first counterbore build (6.6 × 8.2, R0.2) - superseded, its features are deleted by 51b |
| 51b_gf11_counterbores_rebuild | stadium sketch from `cb_w` / `cb_l`, cuts `Fastener counterbores F1-F4 (pads)` (`cb_floor`) and `… F5-F8` (`cb_floor_mid`), floor round `Counterbore floor edges R cb_r` |
| 52_gf11_tube_coring | annular sketch `Fastener tube coring F1-F8` (`core_r_in` / `core_r_out`), cut `core_depth` from the tube top, floor rounds |
| 53_gf11_scratch_export_scan | scratch frame STEP to `%TEMP%\rev3_glassfront\gf11\` + 20_scan (TAG gf11_*) for the iterations |
| 54_gf11_flex_fixes | adaptive `tube_sw_r`, `core_r_out` 7.5, `core_floor_r` 0.4 (flex failures at glass 2.0 / 1.1) |
| 55_gf11_cb_amend_groove_twoside | amendment 7.2 × 8.8, `cb_r` 0.3; groove cut made two-sided (+1 mm above the tube top: no blend remnant over the groove at glass 4.0) |
| 56_gf11_groove_floor_fillet | groove floor fillet re-created (16 edges) after 55; glass 2.0 / 1.1 / 4.0 / 3.0 health + overhang probe |
| 57_gf11_fit_worstcase_asmodelled | worst-case flange 5.7 × 1.4 (39 verbatim → `fit_parts_worstflange.json`, restored 5.5 × 0.7); `gf11\as_modelled.json` (volume, pad faces, annulus, bead area, H6 jog / air) |
| 58_gf11_renders | `renders/Fusion_GF11_*.png` (counterbores pad side, F8 counterbore, coring F1 / F8, H6 cell, sections F1 slot axis / F8 / H6) |
| 59_gf11_save_export | save (v10) + 25 verbatim (frame STEP / STL) + assembly STEP, glass STEP, .f3d |
| 60_gf11_boss_pilot_check | read-only: H1-H9 boss / pilot / relief cones and pilot floors vs stage 2 (identical) |
| 61_gf11_comment_fix_save | comment of `cb_floor` corrected (documentation only), save, .f3d |
| gf11_thickness_check.py | verification thickness / thin-wall check (imports `../verify/vcommon.py` + `mould_check.py` read-only) on a frame STEP; run with the CadQuery env |
| gf11_params_update.py | master params GF-1.0 → GF-1.1 (`change_log` block; backup in `stage1_dumps\params_GF-1.0.json`); refuses a second run |
| build_gf11_reports.py | offline: Frame + Assembly report JSONs for GF-1.1 (assembly checks re-derived with build_stage2_reports.assembly_report) |

Re-runs of 39-42 / 45 / 43 / gf_asm_offline.py on the GF-1.1 model refreshed the assembly dumps and renders.

Lead round 2 (same revision GF-1.1):

| script | does |
|---|---|
| 62_gf11_cb_7p4x9p0 | `cb_w` 7.2 → 7.4, `cb_l` 8.8 → 9.0 (slot + 1.0 per side), parameters only |
| 63_gf11_extreme_stud_tape | measurement only: worst-case flange 5.7 × 1.4, ONE stud (F1, F5) moved by a temporary occurrence transform (bisection until the shank is 0.002 from the slot wall / end, 6 directions; reverted with `revertPendingSnapshot`), flange faces → counterbore walls / floor round / floor face by face; VHB tape over the F5-F8 openings (temporary BReps) → `gf11\extreme_stud_tape.json` |
| gf11_params_round2.py | amends the GF-1.1 params in place (counterbore values, measured margins, tape area, H6 V note, change-log entry); refuses a second run |

Also re-run: 90 (TAG gf11c), 53 (TAG_SUFFIX cb74), 57, 39, 42 + gf_asm_offline gaps / bearing, renders 58 / 45 / 43
(`WHICH` = the two sections), 59 (MSG round 2), 47, gf11_thickness_check on the exported STEP, build_gf11_reports.
H6 V: already R0.5 (the edge is in the 81-edge cell root fillet); not changed.

Saves: v10 GF-1.1 first build, v11 cb_floor comment, v12 = v11 (the MCP executed a top-level runner twice; use the
`def run(_context)` runner above, which executes once), v13 lead round 2 (all exports).

Lead round 3 (frame FROZEN after the independent re-verification of the v13 frame STEP, sha256 `47742d2f…`; no frame
feature touched, frame STEP / STL not re-exported):

| script | does |
|---|---|
| 64_gf11_round3_hardware | R4 `riv_head_d` 10 → 14 (DIN 7337 large-flange K14, `riv_head_k` kept 1.6), S8 `spacer_id` / `spacer_od` 6 / 12 → 7 / 13 (DIN 988 7 × 13 × 1.0, bodies renamed); raises if the frame fingerprint (volume, area, face / edge count, bbox, face-area hash) changes; measures pad face under the head, head edge / axis to the cut-out, `d_cut_out_edge` F1-F8, shim contact and clearances, clearance pocket at the land vs Z_SEAT, bead-to-pocket, Formex outline → `gf11\round3_hardware.json` |
| 63_gf11_extreme_stud_tape | now takes module globals `FL_D` / `FL_K` / `OUT` / `TAPE` and records the stud / frame overlap; run with the 5.9 × 1.5 weld-collar envelope → `gf11\extreme_stud_5p9x1p5.json` |
| 65_gf11_round3_save_f3d | save (v14) + .f3d only, after checking defaults, health, the frame fingerprint and that the R4 / S8 occurrences are hidden (assembly STEP unchanged, not re-exported) |
| gf11_params_round3.py | params GF-1.1 `change_log.round_3` (tolerances, d_cut_out_edge, R4 / S8 hardware, stud and washer notes, counterbore reference plane, pocket reference level, Formex outline, venting); washer bearing at offsets from the tube-top section |
| build_gf11_reports.py `--assembly-only` | refreshes the Assembly report only (the Frame report stays as verified) |
| gf11_params_round4.py | round 4 (bookkeeping): bead adhesive class 50 (or t_bond 1.5 decision), corner seal = 8 strip-end gaps (counted in the assembly → `gf11\strip_ends.json`), S8 shim 0.60 over the Ø5.8 envelope, stud_position_tol ±0.3 as the requirement, graded jig / mounting shims and glass outline ±0.1 requested / ±0.2 fallback, material / UL card; `change_log.round_4` |
| gf11_frame_report_errata.py | `Rev3.0_GlassFront_Frame_report_errata.json` (stale tail-pocket / shelf-back corners and the 6 × 12 shim in the verified Frame report, correct values from the model); embedded in the Assembly report |
| gf11_params_round3_stud.py | lead decision: stud note → flange incl. weld collar / flash within Ø5.8 × 1.4 after welding, stud axis ±0.3 to the cut-out; clearances from 63 at Ø5.8 × 1.4 (`gf11\extreme_stud_5p8x1p4.json`); entry in `change_log.round_3` |

Also re-run: 57 / 39 (R4 / S8 interference), 43 `WHICH = ['front_R4']`, 47.

Results (v13, glass 3.0): 82.188 cm³ / 111.8 g, 922 faces; 0 design-face slivers; draft flags only at the 16 new
floors (counterbore −11.82 / −11.42, groove −10.72); verification thickness on the exported STEP max sphere 4.60 (F6),
then 4.58 (F6), 4.53 (H5, H7, H6) - limit 5.0; no thin wall / gap / V-notch outside the 1.0 lip; flex 7/7 healthy;
worst-case flange 0 overlap, pads seat (198.63 mm² each, annulus 4.5 / 5.3); one stud modelled at its extreme
positions: flange ≥ 0.124 to the walls, ≥ 0.098 to the floor round (F1-F4), 0.119 / 0.326 (F5-F8); tails ≥ 1.763;
g2 corners 0.49 / sides 0.39, g1 corners 0.51 / sides 0.41; nothing above Z 0 inside the board outline + 1. Frame STEP
1 747 323 bytes, 2026-11-15 17:29:54 +03:00, sha256
`47742d2f5ad0235d054db8bac3d47d225917e2fd98089d9f431bb632ac726e82`.

## Sharp inside corners left on purpose

1. 8 pip roots (land Z −10.42) at the pip positions.
2. 4 corner-pad roots on the flange front (Z −12.42), Ø18 round F1-F4 (tape_margin: flat face).
3. Seat-ring root on the flange front (Z −12.42), loop glass + 2.9 (x 10.21…197.49, y 7.27…156.90, R8.9).
4. Tail-pocket corners (v2 1 / 2): (38.78, 118.98) and (167.82, 118.98) since GF-1.1 (stage 1: 39.08 / 167.52),
   Z −4.6…−2.1.
5. Shelf back ↔ bottom pocket wall (v2 3 / 4): y 119.80, x 29.27…38.75 and 167.85…175.67, Z −2.1.
6. Pilot and relief floors (blind holes), as v2.

GF-2.0: the same six; item 3 is now the loop x 5.71…201.99, y 2.77…130.89 (R8.9), item 4 the bend-gap slot's front
corners (same place as GF-1.1's tail-pocket corners).

## Stage 4 (2026-11-16): GF-1.1 → GF-2.0 (equal borders, tails bent back, S8 dropped)

Specification: `../concept/concept_gf2.md` + `concept_gf2_params.json` with the lead's decisions 1-6 (border 18.5 on
all four sides as ONE driving value, `g_bend` 3.00 / nose R1.5 / 0.3 break, S4 + R4 only, divider rib, tail-pocket floor
= bridge + flange plate). Same document, same guard, same runner. The GF-1.1 release set was first copied to
`Mechanical/Rev3.0_GlassFront/archive/GF-1.1/` (README.txt there); the GF-1.1 renders moved to `renders/GF-1.1/`.
Dumps of this stage: `%TEMP%\rev3_glassfront\gf20\` (scans: `%TEMP%\rev3_glassfront\scan_gf20_*.json`).

| script | does |
|---|---|
| 66_gf20_drop_s8_f5_f8 | S8 dropped: F5-F8 curves deleted from the tube / slot / coring / counterbore sketches, features re-profiled and renamed F1-F4, 'Fastener counterbores F5-F8' and the F5-F8 tube blend rule deleted, coring / counterbore floor rounds re-created on F1-F4; S8 components and sockets F5-F8 deleted; f5..f8, tube_sw_r, cb_floor_mid, spacer_* parameters deleted. Save v15 |
| 67_gf20_params_border_bridge | border 18.5, `glass_y1 = pw_y1 + border` (derived), g_bend / bend_y1 / bend_nose_R / land_break / tail_* / div_* / flange_y1_bottom, `fl_y1 = flange_y1_bottom`, logo_h 15; 'Tail pocket' split at bend_y1 = the bend-gap slot; new cut 'Tail pocket over the bridge' (from Z_LANDPLATE_BACK); 'Outer wall block' sketch redefined lower (superseded by 73) |
| 68_gf20_bottom_late_block | late block before 'Fastener tubes F1-F4 sketch': 'Floor over the flange plate (cells + tail pocket)' (cut from Z_PCB down, 3 profiles, front edge on the step-wall back face), 'Cell ribs over the flange plate', divider rib (bridge low / high + over the flange plate), 'Bridge nose R bend_nose_R', 'Bridge land break land_break', rule fillet 'Root fillets R0.5 - floors over the bridge and the flange plate (rule)' (all edges of the late-block features + 'Tail pocket over the bridge') |
| 69_gf20_divider_rib_profiles | the low divider-rib extrude takes both sketch profiles (no shared tapered edge between low and high part) |
| 70_gf20_tails | component 'Tails GF-2.0 (bent-back route)': TFT / CTP tail solids swept from `tail_route.*.centreline_yZ`, 0.30 thick, developed outline per v segment (checked against the DS1 tails by diag_gf20_old_tail_widths); the DS1 tail / finger bodies hidden and renamed 'GF-1.1 reference - ...' |
| 71_gf20_flex_test | flex: glass 2.0 / 4.0 / 1.1, t_sheet 0.8 / 1.5, t_opt 1.0, border 17.5 / 20.5, border 20.5 + g_bend 5.1, default |
| 72_gf20_snap_fix | Z_FLOOR_LOW = min(Z_FLANGE_BACK; Z_LANDPLATE_BACK - 2 fillet_root) + hidden plane, rib sketches re-based on it (first flex: R2 failed at the snap) |
| 73_gf20_rules_wallfront | GF-1.1 rule W restored, R1 'outer wall to the flange plate' re-made; 'Outer wall block' starts at Z_WALL_FRONT = min(Z_LAND; Z_FLANGE_BACK - 0.5) |
| 74_gf20_rule_w_all_edges | R1 and W replaced by ONE rule at W's position: all concave edges of ['Land plate + step wall (back)', 'Outer wall block'] (R1 was empty at the snap) |
| 75_gf20_disc_front | the land plate + step wall solid starts at Z_DISC_FRONT = Z_FLANGE_FRONT + 0.5 (no geometry change) so the parting-plane face stays a flange face and the pad / seat-ring roots stay sharp |
| 76_gf20_scan | runs 20_scan (draft / undercut, slivers, thin strips, root census) with a TAG |
| 77_gf20_coring_taper_fix | coring-groove side-two taper restored to -draft (lost when 66 set the profile) |
| 78_gf20_fit_parts_gaps | frame vs every part (all variants + tails), part pairs, flush, pips, g2 / g1 by rays (sides and 45 deg corners, several Z), bead area, VHB strips vs pads |
| 79_gf20_fit_tails | tails vs frame faces classed by location (nose, pocket face, bridge floor, step, flange floor, divider rib, side walls, bottom face, shelf end), also with the panel edge +-0.35; tails vs glass / print / bead / bond / Formex / board bodies / panel |
| 80_gf20_fit_board | resumable: every visible board body vs the frame and the parts |
| 81_gf20_fasteners | F1-F4: stud flange envelope dia 5.8 x 1.4 + shank centred / +-0.3 (8 directions) / at the shank limit, rivet shank, M4 / M5 washer bearing, R4 pad face under the K14 head, head edge to the cut-out (temporary BReps) |
| 82_gf20_scratch_export_measure | scratch frame STEP + as-modelled numbers (volume, pads, positions, levels) |
| 83_gf20_renders | GROUP frame / gf20 / asm / asm_nopcb: Fusion_FrameGF_*, Fusion_GF20_*, Fusion_Assembly_* (44 hides / shows the board for the no-PCB pair) |
| 84_gf20_save_export | final save + frame STEP / STL, glass STEP, assembly STEP (S4), .f3d; lists what went into the assembly STEP |
| 85_gf20_docinfo | read-only docinfo for the reports |
| gf20_params_update.py | master params GF-1.1 → GF-2.0 (`--stage design`, then `--stage measured`); change_log lists every change, the GF-1.1 log is kept under previous_revisions |
| gf20_thickness_check.py | the verification toolchain's thick-section / thin-wall check on a frame STEP with the GF-2.0 params (+ `--thin-min 1.2`, GF-2.0 probe sections) |
| build_gf20_reports.py | Frame + Assembly report JSONs for GF-2.0 (complete; the GF-1.1 errata file is archived only) |
| diag_gf20_views / _section_map / _old_tail_widths | diagnostic renders (grey), ASCII section maps by point containment, DS1 tail widths |

### Construction of the bottom edge (why it is built this way)

* The bend-gap slot is the GF-1.1 'Tail pocket' cut restricted (split sketch) to y tr_y0 … bend_y1: its front face is
  the unchanged shelf end, its back face between Z_LAND and the land-plate back is the bridge pocket face (1 deg).
* Everything behind the bridge is cut in a LATE BLOCK after the GF-1.1 root fillets: before it the frame keeps a
  GF-1.1-like topology at every glass_t (all cell / bridge floors at Z_LANDPLATE_BACK), so the GF-1.1 edge-set fillets
  keep their edges. The late cut lowers the floors beyond the step-wall back to Z_FLOOR_LOW; it removes the GF-1.1 cell
  ribs there, which are re-made from Z_FLOOR_LOW in the same planes; one rule fillet rounds every new root.
* Z_FLOOR_LOW is never closer than 2 x fillet_root to the land-plate back: at the level snap (glass 1.1) a flat floor
  would make the new fillets continue the GF-1.1 ones through a drafted cut end (General modeling error). Only the
  glass-1.1 variant changes (floor -8.92 instead of -7.92, flange 1.6 there).
* Every cut / join in the block removes / adds material at every glass_t (a cut that removes nothing errors).
* Outlines drawn on another plane than their GF-1.1 reference are offset by dZ tan(draft) so the faces stay the
  same planes (no ledge, no V between adjacent features).
* The flange bottom edge (`fl_y1 = flange_y1_bottom`) is the bottom-wall outer face (150.20 at Z_LAND) continued to the
  flange front (150.235): one flush face.

### Pitfalls met (stage 4)

* Setting `ExtrudeFeature.profile` on a TWO-SIDED extrude reset its side-two taper to 0 deg (coring grooves undrafted,
  found by the scan): re-apply `setTwoSidesExtent` afterwards (77).
* A BETWEEN rule fillet ignores edges whose faces are both in set 1; a feature listed in both sets counts as set 1 (72
  lost the step-wall roots). Three pairwise root sets cannot be one BETWEEN rule: use ALL EDGES of a feature list (74).
* A rule that finds no edge in one parameter state fails there ('No fillet edge found'); at the level snap the flange
  back merges with the land-plate back and the merged face belongs to 'Land plate + step wall (back)'.
* A feature whose start face is coplanar with the flange front takes over the parting-plane face in rule / owner terms
  (the all-edges rule then rounded the pad and seat-ring roots): start such solids inside the plate (75).
* After a script that times out on the MCP side (flex test, exports), the next call can return 'Server unavailable'
  without running anything: check the log and call again.
* STEP export takes a component (`L.comp()`), not a body.

### How to change `border` or `g_bend` later

1. Set the user parameter: `border` (glass outline, all four sides) or `g_bend` (bridge pocket face,
   bend_y1 = panel_y1 + g_bend at Z_LAND). Everything else follows: glass, lip, seat ring, cut-out, tape strips, F1-F4,
   pips, logo zone, flange (bottom = max(glass + 21; bottom wall)), bridge, bead, sheet, studs, rivets.
2. Run 71 (its cases already include border 17.5 / 20.5 and g_bend 5.1), 76, 78-81, 82 + gf20_thickness_check.py,
   then 84, 85, gf20_params_update.py (values) and build_gf20_reports.py.
3. The tail solids (70) do NOT follow g_bend (fixed concept route): for another bend re-sweep them from a new route.
4. Keep the bottom bead_to_pocket >= 1.0: glass_y1 - 4.9 - bend_y1 (1.09 at 18.5 / 3.0); 18.5 holds up to g_bend 3.09.
   (Superseded by stage 5: the verification measures the bead to the EDGE OF THE 0.3 LAND BREAK, i.e.
   glass_y1 - 4.9 - bend_y1 - land_break >= 1.0.)

## Stage 5 (2026-11-16): GF-2.0 → GF-2.1 (border 19.0, g_bend 3.23)

Owner decision after the independent GF-2.0 verification (115 PASS / 1 FAIL): CTP tail → bridge nose 0.239 at the
full worst case (intent >= 0.45) and bead inner edge 0.80 from the land-break edge (rule >= 1.0). Same document; the
change is parameters only (timeline and topology unchanged: 204 items, 889 faces).

| script | does |
|---|---|
| gf21_archive_gf20.py | copies the GF-2.0 release set (f3d v18, STEP / STL, reports, the verification's errata, params sha 7439b098..., drawings/, the design document) to `Mechanical/Rev3.0_GlassFront/archive/GF-2.0/` + README.txt with every sha256, byte-compared; GF-2.0 renders to `renders/GF-2.0/` |
| 86_gf21_bend_zone_probe | derivation probe (parameters set temporarily, restored): tail → frame with the tail at nominal / +0.308 (RSS) / +0.60 (WC) / approx. full WC, bead → break edge by rays; CASES, OUTNAME globals. At 18.5 / 3.00 it reproduces the verification (0.946 / 0.654 / 0.382; full WC 0.257 vs 0.239) |
| gf21_params_update.py | master GF-2.0 → GF-2.1 (`--stage design`, `--stage measured`), byte-exact writer check (indent 1, CRLF), backup `%TEMP%\rev3_glassfront\gf21\params_GF-2.0.json`; fastener d_* values re-derived by the concept 4a rules (board_geom.json read only; reproduces the GF-2.0 table) |
| 87_gf21_params | border 19.0, g_bend 3.23, `logo_cy = ( pw_y1 + 1 mm + glass_y1 - 2.5 mm ) / 2`, value comments |
| 71, 76, 78-85 | re-run with the module globals DUMP = "gf21" (dumps to `%TEMP%\rev3_glassfront\gf21\`), PREFIX = "GF21" (renders Fusion_GF21_*), DEFAULTS = the GF-2.1 values (71, 84), SAVE_MSG (84). 79 now classes frame faces by their own geometry (FACE_CLASSES, default True) |
| build_gf21_reports.py | Frame + Assembly reports for GF-2.1, written so that the GF-2.0 errata points are already correct |

Split: g_bend 3.23 is the smallest 0.01 step with CTP → nose >= 0.45 at the full worst case (0.239 + ~0.93-0.95 per mm);
bottom land 19.0 - 9.51 - 3.23 = 6.26; bead → break edge 1.06 (land plane), 1.36 to the pocket face.

Result (Fusion version 19 = GF-2.1): 84.129 cm³ / 114.4 g, 889 faces, 1 body; flex 10/10; scan as GF-2.0 (8 floor flags
by design, 0 design slivers); max inscribed sphere 4.53 (bosses); walls < 1.2 only the lip and the H6 tail wall 1.1;
CTP → nose 1.165 nominal / 0.872 RSS / 0.597 panel WC / ~0.48 (probe, ~0.46 calibrated) full WC; TFT 1.718; frame STEP
1 585 816 bytes, sha256 d734683ac0c0058a863c4d079b511767ff84a41912745e2ebf592eb1e4e333d6. The GF-2.0 errata JSON was
removed from the live folder (kept in archive/GF-2.0/); GF-2.0 renders in renders/GF-2.0/, live renders Fusion_GF21_*.
