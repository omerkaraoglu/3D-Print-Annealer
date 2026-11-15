# Glass-front frame GF-1.0 / GF-1.1 - independent verification toolchain (CadQuery / OCP / VTK)

Checks the injection-moulded glass-front frame that is delivered as a STEP (modelled in Fusion 360 by another
agent) against the frozen specification `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json`. Nothing of
the frame is modelled here and the modelling agent's own reports are not read. The v2 toolchain
(`../../frame_v2/`) is the template; its helpers are COPIED into `vcommon.py`, nothing is imported from it.

## One command

```
<venv>\Scripts\python.exe run_verify.py            # defaults: the GF STEP, the GF params, the v2 STEP, board export
<venv>\Scripts\python.exe run_verify.py --frame other.step --board board_full.step --no-render
```

`<venv>`: Python 3.11 with cadquery 2.8, OCP, VTK 9.6, matplotlib, scipy, ezdxf (as the v2 README:
`python -m venv <venv>; <venv>\Scripts\python.exe -m pip install cadquery matplotlib ezdxf scipy`). The session
venv used for the reported run: `C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\c8708701-d586-4d89-8e7b-a64a4af1e14d\scratchpad\cqenv`.
Runtime about 25-35 min (carry-over rays and the fit check dominate). Each module also runs alone with the same
flags (`spec_check.py`, `mould_check.py`, `carryover.py`, `fit_check.py`, `calc_gf.py`, `render_gf.py`,
`sections_gf.py`).

`summary.json` records the STEP's size, mtime and sha256, compares them with the previous run (key
`step_changed_since_previous_run`) and re-hashes the file at the end (`step_changed_during_this_run`): re-run if
either is true.

## Inputs (all read-only)

| input | default | note |
|---|---|---|
| frame STEP | `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame.step` | Fusion writes it in cm; OCC converts to mm on import (unit reported) |
| specification | `Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json` | levels taken for the frozen `glass_t` (3.0) |
| v2 STEP + params | `Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2.step`, `..._v2_params.json` | carried-over geometry, rib table, v2 stud positions |
| board STEP | `--board`, `%GF_BOARD_STEP%`, `%TEMP%\gf_verify\board_full.step`, else exported | `kicad-cli pcb export step --subst-models --user-origin 0x0mm -D KIPRJMOD=<project dir>` run on a COPY of the .kicad_pcb / .kicad_pro in `%TEMP%\gf_verify` |
| board data | `Design Reports/Rev3.0/tools/frame/out/board_geom.json` | outline, B.Cu pads, mains copper |
| concept grillage | `Design Reports/Rev3.0/tools/glassfront/concept/concept_calc.py` | its sections 1-7 are executed in a private namespace (they only read files); its section 9, which writes the params file, is never executed |

Coordinates as frame v2: X = KiCad abs x, model Y = -(abs y), Z = 0 at the physical PCB back, -Z to the oven
front, pull = Z. Reports give plan values in KiCad abs (x, y down). Board moved +0.08 (copper + mask missing in the
export). The DS1 panel model (sub-parts incl. both folded tails) is moved by Z_PANEL_BACK - (-5.00) = -0.80 (the
panel hangs on the glass); the tails are also evaluated unmoved and in a split model (below).

## Outputs

| file | content |
|---|---|
| `out/summary.json` | inputs with hashes, condensed verdict table (A-E), fails, timings, image list |
| `out/cadcheck.json` | `spec` (A), `mould` (B), `carryover` (C) |
| `out/fitcheck.json`, `out/fitcheck.txt` | D, readable table |
| `out/calc.json`, `out/calc.md` | E |
| `Mechanical/Rev3.0_GlassFront/renders/verify/` | `Frame_front/back/iso_front/iso_back`, `Assembly_iso_front/iso_back/front/side`, `Section_top_x80`, `Section_side_left_y60`, `Section_chin_x103.85`, `Section_F1_slot_axis`, `Section_F8_tube_y82.085`, `Section_F5_slot_axis_x103.85` (GF-1.1), `Plan_lip_Z-14.1`, `Plan_corner_cells_Z-6.0`, `Plan_counterbore_stud_flange` (GF-1.1), `Thickness_map` |

## What each check means

### A. `spec_check.py` - STEP vs the params (tolerance 0.01 mm, 0.05 deg)
- Body: one solid, BRepCheck valid, bbox = flange outline x/y and Z from the lip top to the trough top, volume.
- Z levels: every planar +-Z face is grouped by height; each specified level (lip top, seat ring + 4 pads, flange
  front/back, land, pip tops, land-plate back, tube tops, Formex seat, shelf back, PCB plane, trough top) must exist
  with the right normal and face count; any other level is listed and explained from the carried-over rules or
  flagged.
- Profiles: exact line probes (OCC `IntCurvesFace_ShapeIntersector`, spans classified by the solid classifier) at
  2 stations per edge give the s-position of each face at 3-6 heights; a line s(Z) is fitted (slope = draft) and
  evaluated at the plane the params refer to (lip inner face at the lip top, lip outer at the root, seat ring and
  flange at the flange front, step wall at the flange back, pocket at the shelf, tail pocket at the land). Lip
  width root/top, lip height, flat width, edge radii.
- Plan rectangles: loops of plan sections fitted (bbox + circle fit of each corner arc: radius and centre) vs the
  rectangles of the params, corrected for the draft between the section height and the reference plane.
- Pips (position, base dia, height, draft), fasteners F1-F8 (slot centre, width / length at the flange front, 0.5
  deg draft wider to the back, axis vs the direction to the glass centre and vs `slot_axis`, through, tube dia and
  draft, tube top face, pad F1-F4 / no pad F5-F8, washer bearing area, tube rib width and direction), PCB bosses
  H1-H9 (boss, pilot, relief, blind floor), the 26 support ribs (centre, width, free end at Z -1.0 measured the same
  way on the GF and the v2 STEP), tape band holes.

### B. `mould_check.py` - mouldability, pull Z, two-plate tool
- Slivers (owner's rule 2A/P < 0.3 or area < 0.5 mm2), split into design faces and fillet blend patches.
- Draft classification of every face; flagged faces identified.
- Undercut proven by rays: (a) vertical rays on a 0.25 mm grid (VTK OBB tree) - any column crossing the material
  twice is trapped air = undercut (candidates re-checked exactly with OCC); (b) every face sampled, each sample's
  outward side found with the exact solid classifier, then a ray along the pull side its normal faces must be free;
  (c) parting: nothing in front of the flange-front plane may be formed from +Z, the flange edge must be widest at
  the flange front (B side).
- Thin wall / thin gap: inscribed-disc thickness (v2 method) on 12 plan sections (lip, seat ring + pads, flange +
  step wall, pips, land plate, tube + ribs, tubes, cells, shelf, PCB plane, tail walls) and 5 vertical ones; walls
  < 1.0 (the lip is 1.0 by design and is named), gaps < 1.0 = knife-edge tool steel, V-notches listed.
- Thick sections: voxels 0.2 mm (VTK stencil) + 3D EDT; inscribed sphere > 5.0 (2 x the 2.5 wall) listed with
  coordinates; plan map `Thickness_map.png`; the same on the v2 STEP for reference.

### C. `carryover.py` - Z >= -5.0 vs v2
OCC booleans fail on these two models (they share most faces; any fuzzy / glue option returns all of GF), so the
difference is measured with vertical rays: mesh pass on the columns where either part has material in the slab,
exact OCC re-measure of every differing column, connected regions with volume, bbox, Z range and an explanation
from the params (pocket 0.8 instead of 0.25 -> wall moved 0.55; tail pocket 147.70 / R1.5; v2 studs replaced).
Unexplained volume fails. Wall probes give each wall face's shift.

### D. `fit_check.py` - fit against an independently built assembly
Glass, LOCA, panel envelope, Formex, bead ring, 4 VHB strips, oven sheet with the cut-out, S4 / S8 / R4 hardware
(dimensions in the module header; rivet blind side ASSUMED dia 12 x 10). Gaps g2 / g1 measured between the STEP's
lip loops and the params' glass and cut-out outlines all round; thermal cases -20 C and +70 C (sheet +50 C) with
frame 50 / 70 ppm/K, glass 9, steel 12, expanding about the glass centre (radial slots), sides and corners
separately. Board: every component model (Q1 leads trimmed to 2.5), PCB body, DS1 parts, tails, lead
protrusions vs the Formex, v2 electrical checks (Z 0 contact faces vs B.Cu pads, creepage and clearance to the
panel metal), nothing above Z 0 inside the board outline + 1, dia-12 socket access, washer seats, rivet grip.

Tails: the board STEP holds the tails at the v2 stand-off. Three positions are evaluated: (1) rigidly moved -0.80
with the panel, (2) unmoved, (3) split - the part below Z -2.1 (shelf back) moved with the panel, the part above it
left at the connectors. (3) is the best estimate of the real tails (the U-loop takes up the 0.8; concept 3c says the
loop apex moves 0.02-0.44 away from the bottom beam), (1) and (2) bound it.

### E. `calc_gf.py`
Ring section properties on STEP sections (I about the in-plane axis along the edge through the centroid, as the
concept's `ring_section`): mid-top, through F5, mid-sides, mid-bottom, near a corner, the corner apex (diagonal
plane through F1). The concept's grillage re-run with the measured I. Bead area, volume and mass (1.36 g/cm3).

## GF-1.1 additions (round 2)

The params loader reads the GF-1.1 keys when present (`R_frame`, `R_cut`, `tail_side_add`, `lip_w_root/top_as_designed`,
`gaps.g1_at_front_as_designed`, `fasteners.counterbore`, `fasteners.tube_coring`, `corner_cell_H6`); a GF-1.0 file
still runs. New checks:
- A: counterbores (width / length at the params reference Z_SHEET_BACK and at the real opening, 1 deg draft narrowing
  with depth, floor Z, floor round, coaxial with the slot, pad face left), coring grooves (radii at the tube top,
  depth, floor rounds, drafts widening to the back, skin, floor above the front face), F5-F8 tube-base blend radius and
  where its foot lands against the flange edge, H6 cell tail wall; lip widths judged against the as-designed values.
- B: extra plan probes through the counterbores, their floor rounds and the grooves; vertical sections along the F5
  and F8 slot axes, across F5 and through the H6 cell; acute-corner (knife-edge) detector on every plan section.
- C: explanations for the 0.3 tail-wall move and the H6 re-coring.
- D: CD weld stud with its base flange dia 5.7 x 1.4 (worst case) at the centre and 6 extreme positions per slot
  (shank against the slot wall across, at the slot end, both): distances to the counterbore wall / floor round / floor;
  R4 rivet at the same extremes, head support on the pad face, M5 backing washer seat vs outer skin; M4 washer on the
  cored tube top at the extremes; DIN 988 S8 shim bearing; g1 / g2 tolerance cases incl. the corner radii (glass
  profile +0.2; glass +0.2/side with R -0.2; cut-out -0.1 with R +0.1; lip 0.04).
- D also: S8 shim bearing with the smallest flange (dia 5.3, most shim play); M4 washer at a realistic ~0.6 offset along
  the slot (tolerances + differential expansion); S4 VHB area over the F5-F8 counterbore openings; two extra tolerance
  cases that show an alternative drawing callout (glass R6.25 +0.2/-0, cut-out R7.55 +0/-0.2).
- B also lists the five largest inscribed spheres (any value) with their locations (`thick.top_spots`).
- Sections: `Section_F5_slot_axis_x103.85` (S8 hardware, no VHB), `Plan_counterbore_stud_flange`; the F8 and chin
  sections show the S8 hardware without VHB and dimension the counterbore / slot / skin / sleeve.
- run_verify compares every condensed row with an archived run (`out/GF-1.0/summary.json`, or `--compare=<dir>`)
  and lists the changes in `summary.json` -> `changes_vs_previous_revision` (changed rows, new rows, rows no longer
  produced). GF-1.0 outputs and images are kept in `out/GF-1.0/` and `renders/verify/GF-1.0/`.

## Known limits
- The fit uses simple solids from the params (no glass arris, no adhesive fillets, tape at its compressed 1.0).
- Thermal gaps assume uniform in-plane CLTE about the glass centre; anisotropy (30 flow / 70 transverse) is covered
  only by the 50 / 70 bounds.
- Tool-access distances above 2 mm are lower bounds (bbox gap / sampled), flagged in fitcheck.json.
- No FEA: section properties feed the concept's grillage only.
