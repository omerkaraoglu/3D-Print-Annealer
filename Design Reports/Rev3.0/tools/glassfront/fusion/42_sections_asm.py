"""42 - stage 2, Part C (READ-ONLY): plan sections (21_sections_dump.section, verbatim) of the frame, the glass, the
oven sheet (S4) and the DS1 panel parts at the Z levels of the gap checks, plus the frame just below the tube tops
(washer bearing). Writes scratchpad sections_asm.json with the reference outlines for gf_asm_offline.py gaps /
bearing / wires.
Levels (default stack): g2 glass edge -> recess wall on the flat edge band (front arris end, mid, back arris start);
g1 lip -> sheet cut-out inside the sheet thickness; panel -> pocket at the LCM back / mid / sensor / CTP."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)


def run(_context: str):
    L.check_doc()
    p21 = os.path.join(L.GF_DIR, "21_sections_dump.py")
    ns = {"__name__": "gf_21"}
    exec(compile(open(p21, encoding="utf-8").read(), p21, "exec"), ns)
    section = ns["section"]
    fr = A.frame()
    glass = A.part("Glass", "Glass")
    sheet = A.part("Oven sheet", "Oven sheet S4/S8 (no holes)")
    ds = {A.ds1_part(p): b for p, b in A.board() if A.is_ds1(p)}
    zgf, zgb, zsb = L.P("Z_GLASS_FRONT"), L.P("Z_GLASS_BACK"), L.P("Z_SHEET_BACK")
    ar = L.P("glass_arris")
    lv = {}

    tb = adsk.fusion.TemporaryBRepManager.get()

    def sec(b, z):
        try:
            return section(b, z)
        except RuntimeError:          # planeIntersection raises when the plane misses the body
            return []

    def add(z, bodies, extra=None):
        rec = {k: sec(b if k == "Frame GF" else tb.copy(b), z) for k, b in bodies.items()}
        if extra:
            rec.update(extra)
        lv["%.4f" % z] = rec
    for z in (zgf + ar + 0.02, (zgf + zgb) / 2, zgb - ar - 0.02):
        add(z, {"Frame GF": fr, "Glass": glass})
    for z in (zgf + 0.05, (zgf + zsb) / 2, zsb - 0.05):
        add(z, {"Frame GF": fr, "Oven sheet": sheet, "Glass": glass})
    for z, parts in ((L.P("Z_PANEL_BACK") - 0.05, ("lcm_0",)), (-7.5, ("lcm_0",)), (-9.0, ("lcm_0",)),
                     (-9.35, ("pu_tape_1",)), (-10.0, ("sensor_2",)), (L.P("Z_CTP_FRONT") + 0.05, ("cover_print_3",))):
        bodies = {"Frame GF": fr}
        for q in parts:
            bodies["DS1." + q] = ds[q]
        add(z, bodies)
    add(L.P("Z_TUBE_TOP") - 0.005, {"Frame GF": fr}, {"tube_top_level": True})
    P = L.P
    params = {
        "glass": [P("glass_x0"), P("glass_x1"), P("glass_y0"), P("glass_y1"), P("R_glass") + 0.6],
        "cut": [P("glass_x0") - P("s_cut"), P("glass_x1") + P("s_cut"), P("glass_y0") - P("s_cut"),
                P("glass_y1") + P("s_cut"), P("R_glass") + P("s_cut") + 0.6],
        "panel": [P("panel_x0"), P("panel_x1"), P("panel_y0"), P("panel_y1"), 1.0],
        "fasteners": {"F%d" % k: [P("f%d_x" % k), P("f%d_y" % k)] for k in range(1, 9)},
        "w4": [P("w4_od"), P("w4_id")], "w5": [P("w5_od"), P("w5_id")], "nut_s": P("nut_s"),
        "slot": [P("slot_w"), P("slot_l")],
        "f_axis": {"F%d" % k: [P("f%d_ux" % k), P("f%d_uy" % k)] for k in range(1, 9)}}
    out = {"levels": lv, "params": params}
    p = L.dump(out, "sections_asm.json")
    print(p, {k: list(v.keys()) for k, v in lv.items()})
