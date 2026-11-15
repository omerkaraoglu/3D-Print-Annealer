# GlassFront supplier drawings - generator scripts (current master: GF-1.1)

Python scripts that turn the frozen master `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json` into the
supplier drawings and DXFs in `Mechanical/Rev3.0_GlassFront/drawings/`. Nothing here is modelled by hand: every product
dimension is read from the master; values the master does not define (jig design, reference data quoted from
`../research/R1_*.md` / `R2_*.md` and the concept, inspection limits) live in `drafting_choices.json`, each with its
source, and are listed in `drawings_report.json` as judgement calls.

## Regenerate

```
<venv>\Scripts\python.exe make_all.py
```

Venv: Python 3.11 with `ezdxf` (1.4.5) and `matplotlib` (3.11), numpy, Pillow; **cadquery 2.8** (OCCT) for
GF-D50, which reads the frame STEP. The one used:
`C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\c8708701-d586-4d89-8e7b-a64a4af1e14d\scratchpad\cqenv`.
To recreate: `C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe -m venv <venv>` then
`<venv>\Scripts\python.exe -m pip install ezdxf matplotlib cadquery`. Runtime about 60 s. Each `make_*.py` also
runs alone. `make_all.py` runs `make_frame.py` last, so GF-D50 shows the params and the frame STEP as they are at the end
of the run; the report records the STEP sha256 and the counterbore size (params and as measured on the STEP).

## What reads what

| script | reads | writes (in `Mechanical/Rev3.0_GlassFront/drawings/`) |
|---|---|---|
| `gf_common.py` | master params, `drafting_choices.json` | - (params access with a usage log, front-view transform, rounded-rectangle maths, DXF helpers and checks) |
| `gf_geom.py` | master params; read-only: `Mechanical/Rev3.0_Frame/Rev3.0_FrontSheet_Pattern_v2.dxf` (v2 window) | - (all plan geometry in the front view, plus its own consistency check against the master's stated results) |
| `gf_draft.py` | - | - (A3 sheet in paper mm, views at true scale, ISO-style dimensions, tables, title block, layout checker) |
| `make_sheet.py` | via `gf_geom` | `GF_Sheet_S4 / S8 / R4 .dxf .pdf .png` (GF-D01..03) |
| `make_glass.py` | via `gf_geom`; lists `Brand Logo/` (read-only) | `GF_Glass.dxf .pdf .png` (GF-D10), `GF_Glass_Print_1to1.pdf` (GF-D11), `previews/GF_Glass_Print_1to1_preview.png` |
| `make_bonding.py` | via `gf_geom` | `GF_BondingAids.dxf .pdf .png` (GF-D20) |
| `make_jigs.py` | via `gf_geom` + jig values from `drafting_choices.json` | `GF_Jig_J2.*` (GF-D30), `GF_Jig_J1.*` (GF-D31) |
| `make_appearance.py` | via `gf_geom` | `GF_Appearance.png .pdf` (GF-D40) |
| `make_frame.py` | via `gf_geom` + `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step` (read-only; hidden-line views and plane sections with OCCT; measures the STEP and compares with the params) | `GF_Frame_Inspection.dxf .pdf` (2 pages), `_p1.png`, `_p2.png` (GF-D50) |
| `selfcheck.py` | the generated DXFs / PDFs + master; read-only cross-checks: `frame_v2/v1_params.json` (Formex), `Rev3.0_GlassFront_Design.md` (counterbore wording) | - (results go into the report) |
| `make_all.py` | all of the above | `previews/*_dxf.png` (ezdxf render of every DXF), `drawings_report.json` |

## Conventions

- **Front view** (all sheet / glass / bonding DXFs, J1): seen from in front of the oven, `u = -(x - xc)`,
  `v = yc - y`, origin = glass centre = cut-out centre (`plan_points.glass_centre`); DXF x = u, y = v, mm.
  The transform is checked against the sentence in the master's `coordinates` field.
- **J2 plate** is drawn from above with the glass face down, i.e. mirrored (`x = -u`). **Print artwork** is seen from
  the printed face 2, also mirrored (`x = -u`).
- DXF: R2010, `$INSUNITS = 4` (mm), true arcs as LWPOLYLINE bulges, nothing on layer 0, named layers per drawing.
  Every front-view DXF carries two `MIRROR-REF` texts whose insert points are the transformed abs-left glass edge and
  the chin edge; `selfcheck.py` reads them back (u > 0, v < 0) in every file.
- Text: English, key supplier notes also in Turkish (DejaVu Sans, TrueType embedded in the PDFs).

## Self-checks (`selfcheck.py`, stored in `drawings_report.json`)

- every DXF re-opened: units mm, no entity on layer 0, all polylines closed, required layers present; cut-out, glass
  outline, window, print boundary, logo zone, bead zone, strips, lip / seat ring / flange references compared with the
  master (area, bbox to 0.001, four 90 deg arcs of the right radius); holes / stud marks / pins at the master positions;
- gaps all round (glass -> lip -> cut-out, seat ring, bead band) from a dense boundary sampling;
- window borders, AA inset, lands and bead-to-pocket, strip lengths, pip positions, fastener u / v and cut-out
  distances recomputed and compared with the master's own stated values;
- holes vs the cut-out (>= 8, R4 >= 2 d);
- mirroring proof (asymmetric references, orientation F, window offset, narrow land at u > 0, J2 mirrored on purpose);
- PDF page count and size; layout checker of every sheet (no text overlap, no text outside the frame, no text crossing
  registered geometry). The PNGs were also inspected by eye.

## Authority (GF-1.1 rounds 3 and 4)

- **Jigs:** GF-D30 (J2) and GF-D31 (J1) are authoritative for the jigs. They supersede the jig text in
  `concept/concept.md` sec. 6: J2 uses dia 5.2 pins in the 5.4 x 7.0 radial slots (not dia 6 holes), a graded set of
  PTFE glass-centring shims and removable glass stop pins (a fixed stop would stand where the lip lands); J1 holds the
  panel on the XY-theta carrier and the glass in the top plate (R1 sec. 3.3), not the other way round.
- **Shims (round 3, lead addition A):** J2 glass centring in g2 0.15 / 0.20 / 0.25 / 0.30, sheet mounting in g1
  0.20 / 0.25 / 0.30; rule: the thickest size that enters on all four sides, the same size on all four sides
  (sizes and the rule from the master `jig_and_mounting_shims`, GF-1.1 round 4; shim body, count per size and the
  rule's second clause from `drafting_choices.json` j2_shim / shim_rule; GF-D30, GF-D20).
- **Gap acceptance (round 3, lead addition D):** g2 sides 0.20-0.60, g1 sides 0.30-0.55 at 20 C; corners not smaller
  than the adjacent sides, at most 0.80 (`gap_acceptance`, GF-D20).
- **Corner radii:** glass R6.25 +0.2/-0 and cut-out R7.55 +0/-0.2, one-sided, read from the master
  (`drawing_tolerances.glass.corner_R`, `drawing_tolerances.sheet.cut_out_corner_R`).
- **Glass outline:** GF-D10 requests +-0.1 (CNC-ground) and accepts +-0.2 if the supplier states it in the quotation
  (master `drawing_tolerances.glass.outline_tol` value and note, round 4).
- **Weld studs:** envelope from the master stud note (lead decision C5); axis +-0.3 to the cut-out =
  `stud_position_tol` (the requirement, round 4); the +-0.2 template accuracy in its note is printed as the recommended
  means only; perpendicularity 1 deg is a proposal (`stud_perpendicularity_deg`).
- **Formex:** from the master (`plan_rectangles` "formex"); the v2 file is only used for a cross-check in `selfcheck.py`.
- **Frame:** the STEP is the geometry master; GF-D50 states what matters and the tolerances. Tolerances marked [P]
  are the drafter's proposals (`drafting_choices.json`, names `frame_*`). Venting and exclusion zones cite the master.

## Revision notes

Every title block carries the master revision and a one-line change note (red). GF-1.1 changes per sheet are listed in
`drawings_report.json` (title-block `change` text) and summarised there under `self_checks.master_findings`.
