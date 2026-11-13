# Rev3.0 smoothing round (2026-11-13)

Scripts that turned the pass-4 board into the "smoothed" board: fan feed off the filter, screw ears, round outline,
tangent-arc fillets at every track bend, KiCad teardrops, cleaned pours, GND stitching. Every step works on a scratch
copy; the real files are only written at the end (KiCad may be open: never touch the `~*.lck` files).

Two interpreters: KiCad's own `C:/Program Files/KiCad/10.0/bin/python.exe` (has `pcbnew`) for every step that reads or
writes a board, and a system Python with shapely / numpy / PyMuPDF for the planners, checkers and renders. Coordinates
in all scripts are local board millimetres (origin at the board's top-left corner, KiCad coordinate − 20 mm).

**Rules directory.** pcbnew and kicad-cli only apply the `.kicad_pro` / `.kicad_dru` that sit next to a board under
the same name. `drc.py` and `fill.py` therefore copy the board into a scratch run directory together with
`3dFilamentDryer.kicad_pro` / `.kicad_dru` from a rules directory. **Zones filled by a bare `LoadBoard()` ignore the
custom rules** (for example, the opto pins come out 0.25 mm from the pour instead of 0.4 mm), so every fill goes
through `fill.py`.

| Step | Script | Interpreter | What it does |
|---|---|---|---|
| 1 | `t1_fanfeed.py in out` | KiCad | K1.1 → LINE_FUSED; deletes the LINE_FILT drop to K1.1; LINE_FILT L40.1 → C40.1 moves to B.Cu (1.0 mm, through-hole pads as the layer change, no vias); new 2.5 mm F.Cu LINE_FUSED feed L40.2 → K1.1, necked to 1.6 mm over the last 4.5 mm (from y 43.5) |
| 2/3 | `t23_outline.py in out` | KiCad | Edge.Cuts rebuilt as one chain of lines and arcs: R3 corners, five ears (9 mm tab, full-round end, R1 fillets, hole centres 5.8 mm outside the edge so the washer keep-outs clear the panel), M3 holes H5…H9 with copies of the 9.4 mm washer keep-outs, and the two overlapping slots merged into one stadium |
| 4 | `fillet.py in out corners.json [caps.json]` | KiCad | tangent arc at every two-segment bend; short jogs become S-curves, short chamfers become compound corners; radius capped at min(max(8w, 1.5), 6) mm and shrunk per corner by the DRC loop |
| 4 | `fillet_loop.py in out rulesdir` | system | fillet → DRC → shrink the corners involved in errors (×0.6) → repeat |
| 4 | `corner_check.py board` | KiCad | lists every remaining corner between two track items (must be 0) |
| 5 | `t5_zones.py in out` + `fill.py` | KiCad | pour smoothing (fillet 1 mm, 0.5 mm on the +5V island), minimum width 0.5 mm on the outer GND pours, pour outlines to the 0.5 mm edge inset |
| 5 | `fills_export.py`, `fill_check.py` | KiCad / system | filled-copper checker: unconnected islands, necks < 0.5 mm, slivers |
| T | `teardrops.py in out report.json [skip.json]` + `fill.py` | KiCad | KiCad teardrop zones (`(attr (teardrop (type padvia/track_end)))`), computed here because TEARDROP_MANAGER is not exposed to Python |
| 6 | `geom_export.py` → `stitch_plan.py` → `stitch_apply.py` + `fill.py` | KiCad / system / KiCad | GND stitching: return vias, U10 / J10 / J11 rings, bus and RGB lanes, 3 mm edge fence, +5V split fence, island vias, then a 4.5 mm grid. The vias are "free" vias, so they keep the GND net. Unconnected outer-pour islands are then removed by the filler |
| 6 | `stitch_stats.py geom plan` | system | via counts, spacing, coverage, return-via distances |
| 7 | `drc.py`, `verify_real.py`, `conn_compare.py`, `tracks_json.py` (+ `../pcb/mains2_check.py`), `render_set.py` | mixed | verification and renders |
| 8 | `t9_final.py in out models.json fplib` | KiCad | final pass: 3D models from `../models3d/models.json`, DS1 display envelope (added on F at its position, then flipped to B), holes renamed H1…H4, all holes board-only / excluded from BOM and position files |
| 4/6 | `o4_probe.py geom.json [clr] [rmin]`, `final_checks.py geom.json` | system | return-via position search for single signal vias; K1 COM-to-coil distances and panel vs ear holes / washer keep-outs |
| all | `build.py original workdir rulesdir [from_step]` | system | runs steps 1…9 in order (9 = DRC), then the round-3 steps 10…15 on `s7` |
| 10 | `r3_j11.py in out` | KiCad | round 3: J11 2.08 mm west, its six escapes re-drawn (same widths / layers / vias, tangent arcs), forced nudges of C226 (0.5 mm), R227 (re-placed horizontal north of the J11 courtyard) and C225's GND via; teardrops in the J11 box removed |
| 11 | `r3_holes.py in out` + `fill.py` | KiCad | round 3: old holes (4,4) (4,95) (97,95.5) (160,95) and their 16 keep-outs deleted, left / bottom ears added (hole centres 4.8 mm outside the edge), outline redrawn by `t23_outline.outline()` with ears on all four edges, holes renumbered H1…H9 clockwise from the top-left, colliding stitching vias in the J11 area removed |
| 12 | `teardrops.py … region=x0,y0,x1,y1` + `fill.py` | KiCad | round 3: teardrops regenerated only inside the J11 box |
| 13 | `stitch_plan.py … region=…` (repeatable) | system | round 3: stitching re-planned on the existing board, new vias only in the J11 box and the four former hole areas; the hand-placed O4 return vias are not duplicated |
| 14 | `r3_ds1.py in out models.json` | KiCad | round 3: applies DS1's model offset / rotation / scale from `models.json` if it changed, else copies the board |
| chk | `r3_checks.py geom.json`, `r3_diff.py before after` | system / KiCad | round 3: hole table (mains, panel, tail loops), envelope, former-hole pour coverage, J11 vs the CTP finger zone; footprint moves and item counts |

Round 3 was run on the board committed as bd375c0: copy it to `workdir/s7.kicad_pcb`, then `build.py x workdir rulesdir 10`.
`t23_outline.py` is now importable (`outline(b, KEEP, top, right, bottom, left, off_*)`); run as a script it still draws the
smoothing-round outline (top and right ears only). `render_set.py` uses the round-3 page box (x −9.3…174.3, y −10.3…108.3).

Helpers: `common.py` (coordinate helpers), `inventory.py`, `netdump.py`, `region.py` (listings), `ear_scan.py`
(clearance of candidate ear-hole positions from mains copper and bodies).

Rules directory used for the round: `.kicad_pro` = the committed (HEAD) version with curved teardrops
(`td_curve_segcount` 5, `td_ontrackend` true). The working-tree copy had been overwritten by an open KiCad session
with stale pass-3 net-class patterns, and its `.kicad_dru` names LINE_FUSED instead of LINE_FILT in the K1 coil
exceptions.
