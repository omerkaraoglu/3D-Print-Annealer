"""58 - stage 3 (GF-1.1) renders -> Mechanical/Rev3.0_GlassFront/renders/Fusion_GF11_<name>.png (1600 x 1200):
frame only (every other root occurrence hidden, restored):
  counterbores_pad_side_F1     iso from the front onto the F1 pad (7.2 x 8.8 counterbore, slot below)
  counterbore_flange_F8        iso from the front onto F8 (counterbore in the flange front, no pad)
  coring_back_F1               iso from the back onto the F1 tube (annular groove, washer seat, tube rib)
  coring_back_F8               iso from the back onto the F8 tube (groove, R1.2 blend into the step wall)
  H6_cell_back                 plan from the back onto the H6 corner cell (jogged wall, R2.5 corner into the boss)
  H6_cell_iso                  iso from the back onto the H6 cell
assembly (as shown, S4), hatched temporary section analyses with the contrasting section looks of 43:
  section_F1_slot_axis         through F1 along its slot axis (counterbore, stud flange, groove, washer, nut)
  section_F8_y82.085           through F8 (counterbore in the flange front, groove, step wall)
  section_H6_y123.8            through the H6 boss centre line (boss, air to the jogged wall, tail wall, tail pocket)
Uses 43's helpers (cam_shot, section_shot, swap_looks)."""
import importlib
import math
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

R = os.path.join(L.MECH, "renders")


def run(_context: str):
    L.check_doc()
    p43 = os.path.join(L.GF_DIR, "43_asm_renders.py")
    H = {"__name__": "gf_43", "__file__": p43}
    exec(compile(open(p43, encoding="utf-8").read(), p43, "exec"), H)
    p26 = os.path.join(L.GF_DIR, "26_renders.py")
    ns = {"__name__": "gf_26"}
    exec(compile(open(p26, encoding="utf-8").read(), p26, "exec"), ns)
    ns["grid_off"]()
    P = L.P
    f1 = (P("f1_x"), -P("f1_y"))
    f8 = (P("f8_x"), -P("f8_y"))
    out = []
    r = L.root()
    old = {}
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        if o.component.name != L.COMP_NAME:
            old[o.name] = o.isLightBulbOn
            o.isLightBulbOn = False
    try:
        shots = [("counterbores_pad_side_F1", (-0.35, 0.45, -1.0), (f1[0] + 1, f1[1] - 1, -12.0), 24),
                 ("counterbore_flange_F8", (-0.45, 0.35, -1.0), (f8[0] + 1, f8[1], -11.5), 24),
                 ("coring_back_F1", (-0.35, 0.45, 1.0), (f1[0] + 2, f1[1] - 2, -8.5), 30),
                 ("coring_back_F8", (-0.45, 0.3, 1.0), (f8[0] + 3, f8[1], -8.5), 30),
                 ("H6_cell_back", (0, 0, 1), (P("h6_x") - 2, -P("h6_y") - 1, -4.0), 22),
                 ("H6_cell_iso", (-0.3, 0.55, 1.0), (P("h6_x") - 2, -P("h6_y") - 2, -5.0), 22)]
        for name, eye, tgt, ext in shots:
            out.append((name, H["cam_shot"](os.path.join(R, "Fusion_GF11_%s.png" % name), eye, tgt, ext)))
    finally:
        for i in range(r.occurrences.count):
            o = r.occurrences.item(i)
            if o.name in old:
                o.isLightBulbOn = old[o.name]
    lk = H["swap_looks"](H["SECTION_LOOK"])
    try:
        ux, uy = P("f1_ux"), -P("f1_uy")
        th = math.atan2(uy, ux)
        m = adsk.core.Matrix3D.create()
        m.setToRotation(th, adsk.core.Vector3D.create(0, 0, 1), adsk.core.Point3D.create(0, 0, 0))
        m.translation = adsk.core.Vector3D.create(f1[0] / 10.0, f1[1] / 10.0, 0)
        n = (-math.sin(th), math.cos(th), 0)
        tg = (f1[0] + 3 * ux, f1[1] + 3 * uy, -9.0)
        out.append(("section_F1_slot_axis", H["section_shot"]("x", L.root().xZConstructionPlane, 0.0, n, (0, 0, 1),
                                                              tg, 30, m)))
        os.replace(os.path.join(R, "Fusion_Assembly_x.png"), os.path.join(R, "Fusion_GF11_section_F1_slot_axis.png"))
        out.append(("section_F8_y82.085", H["section_shot"]("x", L.root().xZConstructionPlane, -P("gc_y"), (0, 1, 0),
                                                            (0, 0, 1), (f8[0] + 4, f8[1], -8.5), 30)))
        os.replace(os.path.join(R, "Fusion_Assembly_x.png"), os.path.join(R, "Fusion_GF11_section_F8_y82.085.png"))
        out.append(("section_H6_y123.8", H["section_shot"]("x", L.root().xZConstructionPlane, -P("h6_y"), (0, 1, 0),
                                                           (0, 0, 1), (P("h6_x") - 3, -P("h6_y"), -4.0), 22)))
        os.replace(os.path.join(R, "Fusion_Assembly_x.png"), os.path.join(R, "Fusion_GF11_section_H6_y123.8.png"))
    finally:
        H["restore_looks"](lk)
    L.show_iso()
    L.log("58 renders %s" % out)
    print(out, "pending", L.des().snapshots.hasPendingSnapshot, "sections", L.des().analyses.sectionAnalyses.count)
