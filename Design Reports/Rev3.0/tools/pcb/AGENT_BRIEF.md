# Rev3.0 controller board — hand-routing brief (common part)

Working folder (everything below lives here): `C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\c8708701-d586-4d89-8e7b-a64a4af1e14d\scratchpad`
Board: `rev3_placed.kicad_pcb` (placed, planes/keep-outs present, NO tracks). Geometry for lookups: `geom.json` (pads, nets).
Helper: `handroute.py` (read its docstring first). Coordinates are LOCAL board mm (origin top-left, x right, y down, board 164 × 99).
Placement list with the rationale: `placement.py`. Design rules: `netclasses.py` (net classes) and the generated
`C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\KiCad\3dFilamentDryer\3dFilamentDryer.kicad_dru`.
Design intent: `C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\Rev3.0_Design_Specification.md` §8–§10 and
`...\Design Reports\Rev3.0\EMI_Signal_Integrity_Analysis.md` §4 (the 24 layout rules). Read both sections before routing.

## What "orderly" means here (the owner rejected an autorouted spider web)
1. Every track is drawn by you in a Python script with `Router.track(net, layer, [(x,y),...], w)` — only 0°/45°/90° segments; a 90° turn is two 45° bends (chamfer ≥ 0.5 mm); every track end is **at the pad centre** (or at a via centre).
2. Buses run as parallel bundles with uniform pitch (bus/RGB: 0.25 mm track, 0.4–0.5 mm pitch; keep ≥ 0.5 mm from other signals), with as few bends as possible, in straight channels. No long diagonals wandering across the board. Think like a careful human: fan-out → channel → fan-in.
3. Layer discipline: F.Cu is the main signal layer (reference = In1 GND); B.Cu (reference = In2 3V3/5V plane) for crossings only. Each layer change = one via pair at most per net, and a GND return via within 1.5 mm of each signal via (for bus/RGB/clock/I2C). Vias: signal 0.6/0.3, power 0.9/0.45, mains 1.2/0.6.
4. Decoupling: capacitor pad → pin pad on the same layer, shortest path; the cap's GND pad gets its own via (0.6/0.3) to In1 (0.4 mm stub).
5. Plane connections: a GND pad connects by a via into the In1 plane (anywhere inside the SELV region); a +3V3 pad by a via into In2 (SELV region outside the +5V island x 108..140, y 64..98); a +5V pad by a via inside that island. THT pads reach the planes directly (no via). On the F/B outer layers there are GND pours in the SELV region (thermal relief) — do not rely on them for connectivity; place the vias.
6. Mains (x > 25.5 for y < 35.5, and the band above the dashed boundary on Cmts.User): see the common rules in `handroute.py`. 1.0 mm to the board edge. No vias needed except to cross the heatsink box (F.Cu copper-free) on B.Cu.
7. Keep off other regions' nets; if you need a few mm of someone else's region for a channel, note it in your report.
8. Do not edit `placement.py`, `build_board.py`, `netclasses.py`, `rev3_placed.kicad_pcb`, `geom.json` or any file under the project tree. If a part must move, say so in the report with the proposed coordinates (local mm) — the reviewer moves it.

## Workflow
- Write ONE script `route_<region>.py` that builds the whole region from scratch (idempotent), saves `tracks_<region>.json`.
- Check: `R.check("tracks_<region>.json", nets=[...your nets...], out="check_<region>.kicad_pcb")` → prints DRC violations touching your nets and unconnected pairs. Use `extra_json=[...]` to include other regions' track files when they exist (so you see cross-region conflicts).
- Look at your work: `R.render("check_<region>.kicad_pcb", "<region>.png", x0, y0, x1, y1, dpi)` then view the PNG (Read tool). Review crops at ≥ 300 dpi; the reviewer will do the same and reject stair-steps, 90° corners, ends short of pads, needless vias.
- Also check copper length per net vs the straight-line pad distance (detour ≤ 1.5× except where a detour is forced) and report the longest nets.
- Deliverables: `route_<region>.py`, `tracks_<region>.json`, PNG crops of every part of your region, and a report: nets routed, DRC state for your nets (0 violations / 0 unconnected expected), vias per net, bus lengths, any part you want moved, anything left for the reviewer.
- Two interpreters: the system `python` (numpy/scipy/PIL/fitz) for your script and the renders; `handroute.check()` calls KiCad's python itself.
