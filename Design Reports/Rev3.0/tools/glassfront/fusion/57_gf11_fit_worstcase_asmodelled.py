"""57 - stage 3 (GF-1.1): (a) worst-case weld flange: stud_fl_d 5.7 / stud_fl_k 1.4 set temporarily, 39_fit_parts run
verbatim (its fit_parts.json renamed fit_parts_worstflange.json), parameters restored to 5.5 / 0.7; (b) as-modelled
numbers for the params / reports -> gf11\\as_modelled.json: frame volume / mass, pad hard-stop face areas at F1-F4,
pad annulus round the counterbore, bead area, H6 jog x, H6 air gap, counterbore floor clearances."""
import importlib
import json
import math
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
    d = L.check_doc()
    ups = d.userParameters
    p39 = os.path.join(L.GF_DIR, "39_fit_parts.py")
    ups.itemByName("stud_fl_d").expression = "5.7 mm"
    ups.itemByName("stud_fl_k").expression = "1.4 mm"
    d.computeAll()
    try:
        ns = {"__name__": "gf_39", "__file__": p39}
        exec(compile(open(p39, encoding="utf-8").read(), p39, "exec"), ns)
        ns["run"](_context)
    finally:
        ups.itemByName("stud_fl_d").expression = "5.5 mm"
        ups.itemByName("stud_fl_k").expression = "0.7 mm"
        d.computeAll()
    src = os.path.join(L.SCR, "fit_parts.json")
    dst = os.path.join(L.SCR, "fit_parts_worstflange.json")
    if os.path.exists(dst):
        os.remove(dst)
    os.rename(src, dst)
    # ------------------------------------------------------------------ as modelled
    b = L.body()
    zs = L.P("Z_SHEET_BACK")
    pads = {}
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType or abs(f.pointOnFace.z * 10 - zs) > 1e-4:
            continue
        c = f.centroid
        for k in (1, 2, 3, 4):
            if math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) < 3.0:
                pads["F%d" % k] = round(f.area * 100, 2)
    bead = A.part("Bead", "Bead (4.0 x t_bond)")
    holes = 8 * math.pi * (L.P("pip_d") / 2) ** 2
    bead_area_net = bead.volume * 1000 / L.P("t_bond")
    am = {"frame_volume_cm3": round(b.volume, 3), "frame_mass_g": round(b.volume * 1.36, 1),
          "pad_faces_mm2": pads, "pad_contact_area_mm2": min(pads.values()) if pads else None,
          "pad_annulus_min": round(L.P("pad_d") / 2 - L.P("cb_l") / 2, 3),
          "pad_annulus_across": round(L.P("pad_d") / 2 - L.P("cb_w") / 2, 3),
          "bead_area_mm2": round(bead_area_net + holes, 1), "bead_area_net_of_pip_holes_mm2": round(bead_area_net, 1),
          "h6_jog_x": round(L.ev("tr_x1 + tail_side_add + ( Z_PCB - Z_LAND ) * tan(draft) + h6_wall_min + "
                                 "( Z_PCB - Z_LANDPLATE_BACK ) * tan(draft)"), 3),
          "h6_air_min": None, "max_sphere_dia": None,
          "cb_floor_clear_over_1.4_flange": {"F1-F4": round(L.P("cb_floor") - 1.4, 3),
                                             "F5-F8": round(L.P("cb_floor_mid") - 1.4, 3)}}
    # H6 air: boss surface at the cell floor vs the corner arc / jogged wall, sampled in plan (analytic, floor level)
    rb = L.P("boss_od") / 2 + (L.P("Z_PCB") - L.P("Z_LANDPLATE_BACK")) * math.tan(math.radians(L.P("draft")))
    hx, hy = L.P("h6_x"), L.P("h6_y")
    xj, rc = am["h6_jog_x"], L.P("h6_corner_r")
    yt = L.P("pocket_y1") + L.P("wall")
    cx, cy = xj + rc, yt + rc
    best = []
    for i in range(0, 91):
        y = cy - rc + i * 0.05                       # along the arc / wall from the top tangent downwards
        xw = cx - math.sqrt(max(0.0, rc * rc - (y - cy) ** 2)) if y < cy else xj
        dyb = y - hy
        if abs(dyb) >= rb:
            continue
        xb = hx - math.sqrt(rb * rb - dyb * dyb)
        best.append((round(xb - xw, 3), round(y, 2)))
    am["h6_air_profile_floor"] = best
    wide = [g for g, y in best if g >= 1.0]
    am["h6_air_min"] = min(wide) if wide else None
    p = os.path.join(L.SCR, "gf11", "as_modelled.json")
    json.dump(am, open(p, "w"), indent=1)
    print(p, {k: v for k, v in am.items() if k != "h6_air_profile_floor"})
