"""Numerical fit check: carrier frame vs the real Rev3.0 board (KiCad STEP export with every 3D model),
the panel model with its folded tails, the insulating sheet and the gasket.

Inputs : board STEP exported by build.py (kicad-cli pcb export step --subst-models --user-origin 0x0mm),
         out/board_geom.json (dump_board.py), the frame built by frame.py.
Output : out/fitcheck.json, returned dict.

The KiCad export puts the board core at z 0..1.47 and the copper + mask (0.08 mm, not exported)
below it, so the physical PCB back is at z = -0.08 and the B-side panel model's back at -5.08.
BOARD_DZ = +0.08 moves the export into the frame's coordinates (physical PCB back at z = 0).
"""
import json
import math
import os

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

import frame as F

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_DZ = 0.08
Q1_TRIM = 2.5           # Q1 leads trimmed to <= 2.5 mm below the PCB back after soldering (IPC-A-610 class 2)
PANEL_PARTS_TAILS = ("tft_tail", "ctp_tail", "tft_fingers", "ctp_fingers")


def _name(l):
    n = TDataStd_Name()
    return n.Get().ToExtString() if l.FindAttribute(TDataStd_Name.GetID_s(), n) else "?"


def read_doc(path):
    doc = TDocStd_Document(TCollection_ExtendedString("board"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True); r.SetColorMode(True)
    if r.ReadFile(path) != 1:
        raise RuntimeError("cannot read " + path)
    r.Transfer(doc)
    return doc


def board_items(doc, dz=BOARD_DZ):
    """[(ref, part, cq.Shape)] in frame coordinates; DS1 split into its sub-parts."""
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labs = TDF_LabelSequence(); st.GetFreeShapes(labs)
    top = labs.Value(1)
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, dz))
    shift = TopLoc_Location(tr)
    out = []
    comps = TDF_LabelSequence(); st.GetComponents_s(top, comps)
    for i in range(1, comps.Length() + 1):
        c = comps.Value(i)
        ref = TDF_Label(); st.GetReferredShape_s(c, ref)
        loc = shift.Multiplied(st.GetLocation_s(c))
        rname = _name(c)
        if rname.startswith("=>") or "PCB" in _name(ref):
            rname = "PCB"
        if rname == "DS1" and st.IsAssembly_s(ref):
            sub = TDF_LabelSequence(); st.GetComponents_s(ref, sub)
            for k in range(1, sub.Length() + 1):
                sc = sub.Value(k); sref = TDF_Label(); st.GetReferredShape_s(sc, sref)
                shp = st.GetShape_s(sref).Moved(loc.Multiplied(st.GetLocation_s(sc)))
                out.append(("DS1", _name(sref), cq.Shape.cast(shp)))
        else:
            out.append((rname, _name(ref), cq.Shape.cast(st.GetShape_s(ref).Moved(loc))))
    return out


def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


def common_vol(a, b):
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    op.Build()
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(op.Shape(), g)
    return abs(g.Mass())


def bb_gap(a, b):
    A, B = a.BoundingBox(), b.BoundingBox()
    dx = max(A.xmin - B.xmax, B.xmin - A.xmax, 0)
    dy = max(A.ymin - B.ymax, B.ymin - A.ymax, 0)
    dz = max(A.zmin - B.zmax, B.zmin - A.zmax, 0)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def trim_below(shape, zmin):
    box = cq.Workplane("XY").box(1000, 1000, 500, centered=(True, True, False)).translate((0, 0, zmin)).val()
    return shape.intersect(box)


def _seg_rect_dist(px, py, r):
    x0, x1, y0, y1 = r
    dx = max(x0 - px, 0, px - x1)
    dy = max(y0 - py, 0, py - y1)
    return math.hypot(dx, dy)


def plan_checks(ribs):
    """2D: support ribs and bosses vs B.Cu pads; mains copper -> frame contact -> panel metal paths."""
    d = json.load(open(F.BOARD_GEOM))
    res = {"rib_to_pad_min": (1e9, None), "boss_to_pad_min": (1e9, None)}
    pts_pad = []
    for p in d["pads"]:
        if not p["on_bcu"] or p["attr"] == "NPTH" or not p["poly"]:
            continue
        pts = [q for poly in p["poly"] for q in poly]
        pts_pad.append(("%s.%s" % (p["ref"], p["num"]), p["mains"], pts))
    for name, mains, pts in pts_pad:
        for (x0, x1, y0, y1, side) in ribs:
            m = min(_seg_rect_dist(px, py, (x0, x1, y0, y1)) for px, py in pts)
            if m < res["rib_to_pad_min"][0]:
                res["rib_to_pad_min"] = (round(m, 2), name)
        for h, (hx, hy) in F.HOLES.items():
            m = min(math.hypot(px - hx, py - hy) for px, py in pts) - F.BOSS_OD / 2
            if m < res["boss_to_pad_min"][0]:
                res["boss_to_pad_min"] = (round(m, 2), name)
    # mains copper (pads on any layer of mains nets, B.Cu tracks/zones of mains nets)
    mains_pts = [(n, pts) for n, mains, pts in pts_pad if mains]
    for m in d["mains_bcu"]:
        mains_pts.append((m["net"] + " " + m["kind"], [q for poly in m["poly"] for q in poly]))
    best = (1e9, None)
    for name, pts in mains_pts:
        for (x0, x1, y0, y1, side) in ribs:
            mm = min(_seg_rect_dist(px, py, (x0, x1, y0, y1)) for px, py in pts)
            if mm < best[0]:
                best = (round(mm, 2), name)
        for h, (hx, hy) in F.HOLES.items():
            mm = min(math.hypot(px - hx, py - hy) for px, py in pts) - F.BOSS_OD / 2
            if mm < best[0]:
                best = (round(mm, 2), name + " (boss %s)" % h)
    res["mains_to_frame_contact_min"] = best
    # creepage: PCB surface (d) + rib side (2.1) + shelf back to its inner edge (0.5) + shelf inner face (2.5)
    #           + shelf/sheet interface to the sheet edge (SEAT_W - SHEET_INSET) -> panel metal
    h_rib = F.Z_PCB - F.Z_SHELF_BACK
    tail = h_rib + (F.SEAT_W - F.PCB_RIM_W) + F.SHELF_T + (F.SEAT_W - F.SHEET_INSET)
    res["creepage_mains_to_panel_mm"] = round(best[0] + tail, 2)
    # clearance (air, around the shelf inner corner, then the interface): worst mains copper point vs the corner
    worst = 1e9
    for name, pts in mains_pts:
        for px, py in pts:
            e = min(px - F.PX0, F.PX1 - px, py - F.PY0, F.PY1 - py)    # distance inside the panel outline
            if e < 0 or e > 15:
                continue
            c = math.hypot(abs(e - F.SEAT_W), F.Z_PCB - F.Z_SEAT) + (F.SEAT_W - F.SHEET_INSET)
            worst = min(worst, c)
    res["clearance_mains_to_panel_mm"] = round(worst, 2)
    res["creepage_req_mm"], res["clearance_req_mm"] = 6.4, 4.0
    return res


def run(board_step, frame_shape, ribs, sheet, gasket, log=print):
    fr = frame_shape.val() if isinstance(frame_shape, cq.Workplane) else frame_shape
    sh = sheet.val() if isinstance(sheet, cq.Workplane) else sheet
    items = board_items(read_doc(board_step))
    log("board items: %d" % len(items))
    comp_rows, panel_rows, lead_rows = [], [], []
    pcb = None
    for ref, part, s in items:
        if ref == "PCB":
            pcb = s
            continue
        if ref == "DS1":
            dd = dist(fr, s)
            ov = common_vol(fr, s) if dd < 1e-6 else 0.0
            panel_rows.append({"part": part, "min_dist": round(dd, 3), "overlap_mm3": round(ov, 4),
                               "to_sheet": round(dist(sh, s), 3)})
            continue
        s_chk = s
        trimmed = False
        if ref == "Q1":
            s_chk = trim_below(s, -Q1_TRIM)
            trimmed = True
        if bb_gap(fr, s_chk) > 8.0:
            dd = bb_gap(fr, s_chk)
            ov = 0.0
        else:
            dd = dist(fr, s_chk)
            ov = common_vol(fr, s_chk) if dd < 1e-6 else 0.0
        zmin = s_chk.BoundingBox().zmin
        comp_rows.append({"ref": ref, "part": part, "min_dist": round(dd, 3), "overlap_mm3": round(ov, 4),
                          "zmin": round(zmin, 2), "q1_trimmed": trimmed})
        if zmin < -0.05:
            lead_rows.append({"ref": ref, "protrusion": round(-zmin, 2), "gap_to_sheet": round(dist(sh, s_chk), 2),
                              "gap_to_frame": round(dd, 2),
                              "untrimmed_protrusion": round(-s.BoundingBox().zmin, 2) if trimmed else None})
    comp_rows.sort(key=lambda r: r["min_dist"])
    lead_rows.sort(key=lambda r: r["gap_to_sheet"])
    pcb_d = dist(fr, pcb)
    pcb_ov = common_vol(fr, pcb) if pcb_d < 1e-6 else 0.0
    tails = [r for r in panel_rows if r["part"].startswith(PANEL_PARTS_TAILS)]
    body = [r for r in panel_rows if not r["part"].startswith(PANEL_PARTS_TAILS)]
    res = {
        "board_dz": BOARD_DZ,
        "components_checked": len(comp_rows),
        "component_overlaps": [r for r in comp_rows if r["overlap_mm3"] > 1e-4],
        "closest_components": comp_rows[:12],
        "pcb_body": {"min_dist": round(pcb_d, 3), "overlap_mm3": round(pcb_ov, 4),
                     "note": "0.08 = copper + mask not in the KiCad export: physical contact at the bosses and support ribs"},
        "panel_parts": body,
        "tails": tails,
        "tail_min_dist": min(r["min_dist"] for r in tails) if tails else None,
        "panel_min_dist": min(r["min_dist"] for r in body) if body else None,
        "panel_overlap_mm3": sum(r["overlap_mm3"] for r in body),
        "lead_protrusions": lead_rows,
        "sheet_vs_frame": {"min_dist": round(dist(fr, sh), 3), "overlap_mm3": round(common_vol(fr, sh), 4)},
        "gasket_vs_frame": {"min_dist": round(dist(fr, gasket.val() if isinstance(gasket, cq.Workplane) else gasket), 3)},
        "plan": plan_checks(ribs),
    }
    json.dump(res, open(os.path.join(HERE, "out", "fitcheck.json"), "w"), indent=1)
    return res, items


def sliver_report(shape, w_min=0.3, a_min=0.5):
    """Owner's CAD rule (Battery Sentinel cadcheck): no face with 2A/P < 0.3 mm or area < 0.5 mm2."""
    s = shape.val() if isinstance(shape, cq.Workplane) else shape
    bad = []
    for f in s.Faces():
        a = f.Area()
        p = sum(e.Length() for e in f.Edges())
        w = 2 * a / p if p > 0 else 0
        if a < a_min or w < w_min:
            c = f.Center()
            bad.append({"type": f.geomType(), "area": round(a, 3), "2A/P": round(w, 3),
                        "at": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)]})
    return {"faces": len(s.Faces()), "slivers": bad}
