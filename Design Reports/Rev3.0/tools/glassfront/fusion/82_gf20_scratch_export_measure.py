"""82 - stage 4 (GF-2.0): scratch STEP of the frame body to %TEMP%\\rev3_glassfront\\gf20\\frame_scratch.step (for the
offline thickness / thin-wall check, gf20_thickness_check.py) and as-modelled measurements of the frame:
volume, mass at 1.36, faces / edges, bbox, pad hard-stop faces F1-F4 (planar faces at Z_SHEET_BACK within 9.5 of each
fastener), flange outline at the flange front, bridge / slot / rib positions from probes, levels.
Writes gf20/as_modelled_frame.json. The design is not modified (export only)."""
import importlib
import math
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)

OUT = globals().get("OUT") or os.path.join(L.SCR, DUMP, "frame_scratch.step")


def run(_context: str):
    d = L.check_doc()
    b = L.body()
    em = d.exportManager
    opt = em.createSTEPExportOptions(OUT, L.comp())        # component 'Frame GF' (one body), as 25
    ok = em.execute(opt)
    res = {"step": OUT, "export_ok": ok, "frame": L.body_dict(b), "timeline": L.timeline_health()}
    pads = {}
    zs = L.P("Z_SHEET_BACK")
    for k in (1, 2, 3, 4):
        fx, fy = L.P("f%d_x" % k), L.P("f%d_y" % k)
        a = 0.0
        for i in range(b.faces.count):
            f = b.faces.item(i)
            if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
                continue
            if abs(f.pointOnFace.z * 10 - zs) > 1e-4:
                continue
            c = f.centroid
            if math.hypot(c.x * 10 - fx, -c.y * 10 - fy) < 9.5:
                a += f.area * 100
        pads["F%d" % k] = round(a, 2)
    res["pad_hard_stop_faces_mm2"] = pads
    res["params"] = {k: round(L.P(k), 4) for k in (
        "border", "glass_x0", "glass_x1", "glass_y0", "glass_y1", "gc_x", "gc_y", "g_bend", "bend_y1", "fl_y1",
        "flange_y1_bottom", "f_x0", "f_x1", "f_y0", "f_y1", "Z_FLOOR_LOW", "Z_WALL_FRONT", "Z_DISC_FRONT", "Z_TAIL_LEG",
        "logo_cx", "logo_cy", "logo_h", "div_x", "div_t")}
    res["pips"] = {"P%d" % k: [round(L.P("pip%d_x" % k), 4), round(L.P("pip%d_y" % k), 4)] for k in range(1, 9)}
    res["levels"] = {k: round(L.P(k), 4) for k in (
        "Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_PIP_TOP", "Z_LANDPLATE_BACK",
        "Z_STEPWALL_BACK", "Z_TUBE_TOP", "Z_TRIB_TOP", "Z_CELL_RIB_TOP", "Z_TROUGH_TOP")}
    res["timeline_count"] = d.timeline.count
    res["user_parameters"] = d.userParameters.count
    L.dump(res, DUMP + "/as_modelled_frame.json")
    print(res)
