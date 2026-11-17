# GlassFront supplier drawings - generator scripts (current master: GF-2.1)

Python scripts that turn the frozen master `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json` into the
supplier drawings and DXFs in `Mechanical/Rev3.0_GlassFront/drawings/`. Nothing here is modelled by hand: every product
dimension is read from the master (GF-D50 also cuts its views and sections from the frozen frame STEP); values the
master does not define (jig design, reference data quoted from `../research/R1_*.md` / `R2_*.md` and the concepts,
inspection limits, the fold gauge) live in `drafting_choices.json`, each with its source, and are listed in
`drawings_report.json` as judgement calls.

## GF-2.1 (2026-11-17, master sha256 bec9e8fc49d51757..., frame STEP d734683ac0c0058a...)

Master GF-2.1 (`change_log`, owner decision via the lead): border **19.0** on all four sides and g_bend **3.23**
(bottom land 6.26), so that both findings of the independent GF-2.0 verification close (verification GF-2.1:
120 PASS / 0 FAIL / 54 INFO, `tools/glassfront/verify/out/summary.json`). Glass 191.48 x 123.32 R6.25, cut-out
195.08 x 126.92 R7.55, flange 233.48 x 166.07, F1-F4 pattern 213.48 x 145.32 (u +-106.74 / v +-72.66), logo centre
y 118.24, print window unchanged. The complete GF-2.0 set is archived unchanged in
`Mechanical/Rev3.0_GlassFront/archive/GF-2.0/drawings/`; sheet numbers and file names are the same as at GF-2.0.

Every title block starts with the red note from `gf_common.rev_note()`: "GF-2.1: border 19.0 all round, g_bend 3.23,
bottom land 6.26 (GF-2.0: 18.5 / 3.00 / 5.99)" plus what changed on that sheet; history labels compare against the
previous revision from the master's `change_log.from` (`prev_rev`).

| drawing | GF-2.1 change |
|---|---|
| GF-D01 / GF-D03 sheets S4 / R4 | cut-out 195.08 x 126.92, F1-F4 at u +-106.74 / v +-72.66 (history: GF-2.0 size) |
| GF-D02 sheet S8 | still **withdrawn** (at GF-2.0, master `sheet_variants.S8_withdrawn`) |
| GF-D10 / GF-D11 glass, print 1:1 | glass 191.48 x 123.32, 19.0 border; logo zone centre y 118.24 (1.25 from the window, 2.75 from the glass edge) |
| GF-D20 bonding aids | lands 11.11 / 13.87 / 13.03 / 6.26 / 8.69; bead -> break edge 1.06 on the land plane (1.07 at Z_LAND + 0.01), 1.36 to the pocket-face plane, A1 met (margin 0.06); the squeeze-out check at the bridge stays REQUIRED at first article and per batch; no "finding" or "fail" wording |
| GF-D21 tail fold gauge + test | gauge made new at slot 3.23 (a GF-2.0 gauge, slot 3.00, is not valid - stated EN / TR); the whole rule from the master `fold_test` block: feeler 0.80, tail outer surface within 2.43, exact feeler 0.758, needed gap at the line 3.188, reserves 0.042 (to g_bend) / 0.102 (to the limit 3.29), assumed tail 2.30 passes with 0.13 to spare, fail branch with land 6.20 (19.5 covers g <= 3.79); the CTP full-worst-case margin 0.009 mm and that passing guarantees the RSS criterion, not the 0.45 full-worst-case intent (EN / TR); criterion 5 "single layer as assumed" (the master has no double-sided figures) |
| GF-D30 / GF-D31 jigs J2 / J1 | pins at F1-F4 213.48 x 145.32, stops follow the glass; section T-T at g_bend 3.23 (tails 0.93 from the bridge face, bead 1.36 behind it) |
| GF-D40 appearance | S4 / R4 at border 19.0; the corner zooms show 20 mm of product at 3.5:1 (the panels are 1 mm wider) |
| GF-D50 frame inspection | STEP d734683a..., 38 of 38 STEP-vs-master checks; note 4 at the GF-2.1 shut-off figures (break top y 122.235, 3.235 slot width at the break top vs the 3.23 plan slot explained, ledge 3.235 x 0.3, >= 3 deg / up to 30.4 deg, B 91 / A 135 deg, 31.4 deg knife edge avoided); CTF 16: "sizes are GF-2.1 at border 19.0, still subject to the real-panel fold test (GF-D21) before glass, sheet or mould are ordered"; land break 0.3 +0.05/-0.10 [P] |

Toolchain changes for GF-2.1: `make_tailgauge.py` reads `fold_test` (and `tail_clearance_criteria`,
`open_findings`) instead of note text and checks every number against the budget; `make_frame.py` checks the
shut-off numbers (slot width at the break = g_bend + 1 deg x 0.3 break, the 30.4 deg maximum = atan(width / rise)) and
compares the STEP sha with `as_modelled_<revision>`; `make_bonding.py` quotes the land-plane bead value (A1);
`gf_geom.py` normalises the master slot axes (4 decimals, |a| = 0.99995) before the stadium slots are built;
`selfcheck.py` carries the GF-2.0 numbers in `STALE` (allowed only next to a GF-2.0 / GF-1.1 history label) and the
GF-2.1 findings G21-1 .. G21-11.

## History: GF-2.0 (2026-11-16, archived in `archive/GF-2.0/drawings/`)

Master GF-2.0 (`change_log`, concept `../concept/concept_gf2.md`): equal 18.5 border on all four sides (glass
190.48 x 122.32, cut-out 194.08 x 125.92, glass centre = cut-out centre = fastener-pattern centre = window centre),
chin removed, FPC tails folded back through the 3.0 bend-gap slot behind a bridge, S8 withdrawn (S4 / R4 only).
Every title block carries the red note "GF-2.0: equal 18.5 border, chin removed, tails folded back, S8 withdrawn" plus
what changed on that sheet. The GF-1.1 set is kept unchanged in `Mechanical/Rev3.0_GlassFront/archive/GF-1.1/drawings/`.

| drawing | file(s) | GF-2.0 change |
|---|---|---|
| GF-D01 sheet S4 / GF-D03 sheet R4 | `GF_Sheet_S4.*`, `GF_Sheet_R4.*` | cut-out 194.08 x 125.92, F1-F4 at u +-106.24 / v +-72.16; section A-A land shown cut (12.53 top land) |
| GF-D02 sheet S8 | - | **withdrawn**; `make_all.py` removes `GF_Sheet_S8.*` (and its preview) from `drawings/` only when the archive holds an identical copy; recorded in the report (`drawings.GF-D02`) |
| GF-D10 glass / GF-D11 print 1:1 | `GF_Glass.*`, `GF_Glass_Print_1to1.pdf` | new outline, window unchanged and centred, logo zone 100 x 15 max at centre y 117.99 (1.0 from the window, 2.5 from the glass edge) |
| GF-D20 bonding aids | `GF_BondingAids.*` | bead path / strips for the new outline, 5 land rows, bend-gap slot drawn, bottom land 5.99 with the 0.3 break, at-land margins from the master pocket note (checked against the lands table), open finding 2 with a required squeeze-out check at the bridge, tail handling in the sequence |
| **GF-D21 tail fold gauge + test** (new) | `GF_TailFoldGauge.*` | gauge forming the 3.0 slot with the panel edge (R1.5 nose at the bridge height), test steps, pass criteria parsed from the master notes (bend-zone clearance criterion, budget 3.06 / limit 3.09 / reserve 0.03), record sheet |
| GF-D30 jig J2 | `GF_Jig_J2.pdf` (2 pages), `_p1.png`, `_p2.png`, `.dxf` | sheet 1: pins / stops for the new size + hole TH; sheet 2 (new): tail handling - fold over the GF-D21 gauge, PET guide card on the panel side of the tails, removable swing-arm post TH, threading sequence (EN / TR). `GF_Jig_J2.png` is replaced by `_p1` / `_p2` |
| GF-D31 jig J1 | `GF_Jig_J1.*` | stops S1-S3 follow the glass, opening on the datum; plates and guide pins unchanged; tails stay flat in J1 |
| GF-D40 appearance | `GF_Appearance.*` | S4 / R4 with the equal border; corner zoom 3.5:1 (4:1 no longer fits beside the wider panels) |
| GF-D50 frame inspection (2 pages) | `GF_Frame_Inspection.*` | sections E-E, F-F, **G-G** (bridge, bend-gap slot, bottom wall), **detail Y** (pocket face, nose R1.5, 0.3 break, stepped A/B parting), **H-H** (divider rib); CTF 13-18 (slot = g_bend, bridge face +-0.05 [P], nose +0.2/0 [P], bottom land / break +-0.1 [P] - provisional, tail pocket floor, rib +-0.2 [P]); stepped / telescopic shut-off and bridge mould notes; 38 STEP-vs-master checks |

### GF-2.0 correction pass (2026-11-16, master sha256 662d8380d7173d04...)

The master was corrected after the independent verification (frame STEP unchanged, sha256 7831768c26066dc0). The
drawings were regenerated with it; every sheet cites the params file with its sha256 (`master_ref`), and
`drawings_report.json` records the sha256 per drawing and checks that each sheet prints it (`cites_params_sha`).

- GF-D10 / GF-D11 / GF-D40: logo zone at centre y 117.99, 100 x 15 max, 1.0 from the window, 2.5 from the glass edge;
  the "open" wording on GF-D10 note 11 is gone (EN / TR).
- GF-D20: at-land margins read from the corrected pocket note (5.61 / 8.37 / 7.53 / 3.19) and checked against the
  lands table and the draft; over the bridge bead -> break edge 0.80, -> face plane 1.09 against 1.0 = master open
  finding 2, with a REQUIRED squeeze-out check at the bridge (note 5, sequence step 6); the verified temperature gaps
  are printed (the 20 C restriction is gone).
- GF-D21: budget with the corrected position term 0.31 (0.5 + 1.5 + 0.30 + 0.45 + 0.31 = 3.06, limit 3.09, reserve
  0.03, all parsed and summed); the reserve sentence (EN / TR). The fold-fit rule is the master `fold_test` block
  (see the addendum below).
- GF-D40: note 2 prints the verified gaps over temperature.
- GF-D50: note 4 = stepped / telescopic shut-off of `cad_rules[15]` (numbers parsed and checked against the levels),
  detail Y shows the parting schematically; note 7 (and TR 5): the shelf-end corners x 38.9 / 167.7 are R0.5
  (`cad_rules[19]`); CTF 16 provisional until the border is frozen after the fold test (tool not cut before); note 9
  refers to the owner's decision on the lip finish (design document section 4), no decision number.

### Master addendum (2026-11-16, sha256 7439b098325a09f4..., notes only, STEP unchanged)

- GF-D21 takes the fold-fit rule from the new master block `fold_test` (the one source): gauge slot 3.00, feeler 0.70,
  tail outer surface within 2.30 of the panel edge (= l0 0.5 + R_in 1.5 + t 0.30), `check` / `pass` / `fail` word for
  word (criterion 1), the exact-feeler note (0.67; 0.70 is the nearest standard leaf on the safe side) under the
  criteria table; plan, section A-A (0.70 offset of the gauge face and nose), DXF LIMIT_REF (2.30), test step 5,
  record (largest feeler that passes, tail extent = 3.00 - feeler, needed gap) and the EN / TR notes follow it. A tail
  exactly as assumed passes. `make_tailgauge.py` checks slot - feeler = limit = l0 + R_in + t, the exact feeler
  3.00 - (3.09 - 0.45 - 0.31) = 0.67, and the budget numbers in the pass / fail text. The budget line (3.06) and the
  0.03 reserve sentence stay. The drawing set's earlier conversion is withdrawn (stale-text patterns).
- Bead -> break edge: the master land notes now give 0.80 measured where the land ends (Z_LAND + 0.01) and 0.79 on
  the land plane. `gf_geom.Geom.break_edge_notes()` parses both notes and compares each number with what it describes
  (measured = 1.09 - (0.30 - 0.01), land plane = 1.09 - 0.30, face plane 1.09, and the pocket note); `make_bonding.py`
  and the geometry self-check use it. The drawings quote the measured 0.80.

## Regenerate

```
<venv>\Scripts\python.exe -B make_all.py
```

Venv: Python 3.11 with `ezdxf` (1.4.5) and `matplotlib` (3.11), numpy, Pillow; **cadquery 2.8** (OCCT) for
GF-D50, which reads the frame STEP. The one used:
`C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\c8708701-d586-4d89-8e7b-a64a4af1e14d\scratchpad\cqenv`.
To recreate: `C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe -m venv <venv>` then
`<venv>\Scripts\python.exe -m pip install ezdxf matplotlib cadquery`. Runtime about 70 s. Each `make_*.py` also
runs alone. `make_all.py` runs `make_frame.py` last, so GF-D50 shows the params and the frame STEP as they are at the end
of the run; the report records the STEP sha256 (and whether it equals the master's `as_modelled_<revision>.frame_step`).
Never import `../concept/concept_calc.py` (it rewrites the master).

## What reads what

| script | reads | writes (in `Mechanical/Rev3.0_GlassFront/drawings/`) |
|---|---|---|
| `gf_common.py` | master params, `drafting_choices.json` | - (params access with a usage log, front-view transform, rounded-rectangle maths, number formatting with half-up rounding, `rev_note` / `master_ref` for the title blocks, DXF helpers and checks) |
| `gf_geom.py` | master params; read-only: `Mechanical/Rev3.0_Frame/Rev3.0_FrontSheet_Pattern_v2.dxf` (v2 window) | - (plan geometry in the front view incl. the GF-2.0 bend-gap slot / bridge / rib, 5 lands, tail route access, plus its own consistency check against the master's stated results: borders, centres, lands, bottom-zone budget 9.51 + 3.23 + 6.26 = 19.0, bead -> break edge notes) |
| `gf_draft.py` | - | - (A3 sheet in paper mm, views at true scale, ISO-style dimensions, tables, title block, layout checker, polygon clipping, sheet registry `ALL_SHEETS` for the report and the stale-text scan) |
| `make_sheet.py` | via `gf_geom` | `GF_Sheet_S4 / R4 .dxf .pdf .png` (GF-D01, GF-D03) |
| `make_glass.py` | via `gf_geom`; lists `Brand Logo/` (read-only) | `GF_Glass.dxf .pdf .png` (GF-D10), `GF_Glass_Print_1to1.pdf` (GF-D11), `previews/GF_Glass_Print_1to1_preview.png` |
| `make_bonding.py` | via `gf_geom` | `GF_BondingAids.dxf .pdf .png` (GF-D20) |
| `make_tailgauge.py` | via `gf_geom` (g_bend, bend_nose_R, bend_gap_slot, div_x, levels, tail_route, notes) + `tg_gauge` / `tg_test` | `GF_TailFoldGauge.dxf .pdf .png` (GF-D21) |
| `make_jigs.py` | via `gf_geom` + jig values from `drafting_choices.json` (incl. `j2_tail_holder`, `j2_tail_card`) | `GF_Jig_J2.pdf` (2 pages) `_p1.png _p2.png .dxf` (GF-D30), `GF_Jig_J1.*` (GF-D31) |
| `make_appearance.py` | via `gf_geom` | `GF_Appearance.png .pdf` (GF-D40) |
| `make_frame.py` | via `gf_geom` + `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step` (read-only; hidden-line views and plane sections with OCCT; measures the STEP and compares with the params) | `GF_Frame_Inspection.dxf .pdf` (2 pages), `_p1.png`, `_p2.png` (GF-D50) |
| `selfcheck.py` | the generated DXFs / PDFs + master; read-only cross-checks: `frame_v2/v1_params.json` (Formex), `Rev3.0_GlassFront_Design.md` (counterbore wording) | - (results go into the report) |
| `make_all.py` | all of the above; `archive/GF-1.1/drawings/` (read-only, for the withdrawn-file check) | `previews/*_dxf.png` (ezdxf render of every DXF), `drawings_report.json` (per drawing: number, title, revision, files, source values used, self-check result) |

## Conventions

- **Front view** (all sheet / glass / bonding DXFs, J1): seen from in front of the oven, `u = -(x - xc)`,
  `v = yc - y`, origin = glass centre = cut-out centre = window centre (`plan_points.glass_centre`, GF-2.x: 103.85,
  66.83); DXF x = u, y = v, mm. The transform is checked against the sentence in the master's `coordinates` field.
- **J2 plate** is drawn from above with the glass face down, i.e. mirrored (`x = -u`). **Print artwork** is seen from
  the printed face 2, also mirrored (`x = -u`). **J2 section T-T** and **GF-D21** use heights above the plate / the CTP
  front (abs y outward to the right). **GF-D50 G-G / H-H** use t = abs y (outward to the right), depth downwards.
- DXF: R2010, `$INSUNITS = 4` (mm), true arcs as LWPOLYLINE bulges, nothing on layer 0, named layers per drawing.
  Every front-view DXF carries two `MIRROR-REF` texts whose insert points are the transformed abs-left glass edge and
  the bottom glass edge (tail side); `selfcheck.py` reads them back (u > 0, v < 0) in every file.
- Text: English, key supplier notes also in Turkish (DejaVu Sans, TrueType embedded in the PDFs).

## Self-checks (`selfcheck.py` + `make_all.py`, stored in `drawings_report.json`)

- every DXF re-opened: units mm, no entity on layer 0, all polylines closed, required layers present; cut-out, glass
  outline, window, print boundary, logo zone, bead zone, strips, lip / seat ring / flange references, bend-gap slot and
  divider rib compared with the master (area, bbox to 0.001, four 90 deg arcs of the right radius); holes / stud marks
  / pins / TH hole at the master (or drafting-choice) positions; GF-D21 gauge: slot = g_bend over the slot length, nose
  tangent, limit line at the `fold_test` tail limit 2.43 (slot 3.23 - feeler 0.80), engraved rib pair, section height;
- gaps all round (glass -> lip -> cut-out, seat ring, bead band) from a dense boundary sampling;
- borders (one value on all four sides), centres coincide, lands (5 rows), bead-to-pocket, bottom-zone budget, strip
  lengths, pip positions, fastener u / v and cut-out distances recomputed and compared with the master's stated values;
- holes vs the cut-out (>= 8, R4 >= 2 d); R4 head edge to the cut-out corner arc;
- mirroring proof (asymmetric references, orientation F, window position, narrower side land at u > 0, bend-gap slot
  at v < 0, J2 mirrored on purpose);
- GF-D50: 38 STEP-vs-master measurements (E-E levels and lip, F1 counterbore / slot / coring, pocket and slot ends at the
  land, G-G bridge face / shelf end / g_bend / break / nose / floors / bottom wall / flange edge, H-H rib top / face /
  thickness / position);
- PDF page count and size; layout checker of every sheet (no text overlap, no text outside the frame, no text crossing
  registered geometry); **stale-text scan** of every string on every sheet (chin, S8, F5-F8, 44.5, GF-1.1 sizes; since
  the correction pass also the decision number, "to be re-verified", the open-bracket flag, "20 C only", "meet on its
  outline", the old 2.55 limit, position 0.25, 0.79, 118.74, the withdrawn gauge conversion values, and at GF-2.1
  the GF-2.0 numbers and wording: 18.5, the 3.00 slot, 190.48 / 122.32, 194.08 / 125.92, 232.48 / 165.57, 212.48 /
  144.32, the GF-2.0 lands and fasteners, the 0.70 feeler and 2.30 line, 0.80 / 1.09 bead, 0.946 / 0.654 / 0.239,
  28.6 / 29.6 deg, "open finding", "provisional" - see `STALE`) - allowed only as revision history; every
  sheet cites the params sha256; the PNGs and the DXF previews were also inspected by eye;
- master findings: `selfcheck.master_findings` parses the corrected notes (pocket margins, logo zone, temperature
  gaps, open findings); a wording it cannot parse is reported as FAIL (`master_findings_parsed_ok`), never as ok.

## Authority

- **Jigs:** GF-D30 (J2, both sheets) and GF-D31 (J1) are authoritative for the jigs and supersede the jig text in
  `concept/concept.md` sec. 6: J2 uses dia 5.2 pins in the 5.4 x 7.0 radial slots, a graded set of PTFE
  glass-centring shims and removable glass stop pins; J1 holds the panel on the XY-theta carrier and the glass in the
  top plate (R1 sec. 3.3). GF-2.0: the J2 tail handling (TH post, guide card, sequence) on GF-D30 sheet 2 implements
  concept_gf2.md 5.3 / risk 3; its values are drafting choices (`j2_tail_holder`, `j2_tail_card`).
- **Tail fold test:** GF-D21 is the real-panel gate of concept_gf2.md 2.4 / risk 1; its whole rule is the master
  `fold_test` block (GF-2.1: slot 3.23, feeler 0.80, tail within 2.43, reserves 0.042 / 0.102, pass / fail, fail branch
  with land 6.20); gauge make and test counts are drafting choices (`tg_gauge`, `tg_test`).
- **Shims (GF-1.1 round 3, unchanged):** J2 glass centring in g2 0.15 / 0.20 / 0.25 / 0.30, sheet mounting in g1
  0.20 / 0.25 / 0.30; rule: the thickest size that enters on all four sides, the same size on all four sides.
- **Gap acceptance (unchanged rule):** g2 sides 0.20-0.60, g1 sides 0.30-0.55 at 20 C; corners not smaller than the
  adjacent sides, at most 0.80 (`gap_acceptance`, GF-D20). GF-2.0: GF-D20 and GF-D40 print the verified values over
  temperature from the master gaps notes (`gf_geom.gap_temperatures`, which stops the run if a value is missing).
- **Corner radii:** glass R6.25 +0.2/-0 and cut-out R7.55 +0/-0.2, one-sided (master `drawing_tolerances`).
- **Glass outline:** GF-D10 requests +-0.1 (CNC-ground) and accepts +-0.2 if stated in the quotation.
- **Weld studs:** envelope dia 5.8 x 1.4 from the master stud note; axis +-0.3 to the cut-out = `stud_position_tol`;
  the +-0.2 template is the recommended means; perpendicularity 1 deg is a proposal.
- **Frame:** the STEP is the geometry master; GF-D50 states what matters and the tolerances. Tolerances marked [P] are
  the drafter's proposals (`drafting_choices.json`, names `frame_*`, GF-2.0 adds `frame_bend_face_tol`,
  `frame_nose_R_tol`, `frame_land_break_tol`, `frame_rib_pos_tol`). GF-2.1: land break 0.3 +0.05 / -0.10 [P] (the
  bead keeps >= 1.01 to the break edge; +-0.1 would allow 0.96) - for the owner's decision. Venting, exclusion zones
  and the bend-gap shut-off cite the master `cad_rules`.

## Master findings at GF-2.1 (also in `drawings_report.json`, `self_checks.master_findings`)

Read from the master (sha256 bec9e8fc49d51757...); a wording the checks cannot parse is reported as FAIL.

- **G21-1** pocket-note margins at the land (6.11 / 8.87 / 8.03 / 3.69) consistent with the lands table and the draft.
- **G21-2** logo zone: 1.25 from the window, 2.75 from the glass edge (rules 1.0 / 2.5).
- **G21-3** gaps over temperature: GF-2.1 values verified in the master, printed on GF-D20 / GF-D40.
- **G21-4** tail bend values are assumptions (GF-D21); no double-sided figures in the master - criterion 5 says
  "single layer as assumed", anything else goes through the fold_test fail branch.
- **G21-5** GF-2.0 findings 1 and 2 are CLOSED at GF-2.1 (CTP full worst case 0.459; bead 1.060 on the land plane).
- **G21-6** bead -> break edge in the land notes: 1.07 measured / 1.06 on the land plane / 1.36 to the face plane,
  each checked against its geometry.
- **G21-7** fold-test rule from `fold_test` (slot 3.23, feeler 0.80, 2.43, 0.758, reserves 0.042 / 0.102).
- **G21-8** thin margins (`open_findings.margins_note_GF-2.1`) stated on GF-D21 (0.009 mm) and GF-D20 / GF-D50 (0.06).
- **G21-9** shut-off slot width 3.235 at the break top vs the 3.23 plan slot: explained on GF-D50 note 4.
- **G21-10** land-break tolerance +0.05 / -0.10 [P]: drafter's proposal for the owner.
- **G21-11** the master's `to_be_reverified_at_GF-2.1` drawings item: the report and every sheet carry the params
  sha256.
