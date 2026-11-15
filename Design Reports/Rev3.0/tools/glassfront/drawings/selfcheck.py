"""Self-checks of the GF drawing set. Re-opens every DXF with ezdxf, checks geometry against the master,
proves the front-view mirroring with asymmetric references, reads the PDF page sizes, and lists the findings in
the master (inconsistencies) that the drawings had to work around.

  <venv>/Scripts/python.exe selfcheck.py        (standalone: prints the result; make_all.py stores it in the report)
"""
import glob
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from gf_common import (Params, Choices, Rect, OUT_DIR, dxf_inventory, check_rrect_poly, bulge_to_points,
                       poly_area_bulge)
from gf_geom import Geom

TOL = 1e-3
FRONT_VIEW_DXF = ["GF_Sheet_S4.dxf", "GF_Sheet_S8.dxf", "GF_Sheet_R4.dxf", "GF_Glass.dxf", "GF_BondingAids.dxf",
                  "GF_Jig_J1.dxf", "GF_Frame_Inspection.dxf"]
REQUIRED_LAYERS = {
    "GF_Sheet_S4.dxf": ["CUTOUT", "HOLES", "STUD_MARKS", "GLASS_REF", "LIP_REF", "FLANGE_REF", "TAPE_REF", "TEXT"],
    "GF_Sheet_S8.dxf": ["CUTOUT", "HOLES", "STUD_MARKS", "GLASS_REF", "LIP_REF", "FLANGE_REF", "TAPE_REF", "TEXT"],
    "GF_Sheet_R4.dxf": ["CUTOUT", "HOLES", "STUD_MARKS", "GLASS_REF", "LIP_REF", "FLANGE_REF", "TAPE_REF", "TEXT"],
    "GF_Glass.dxf": ["OUTLINE", "PRINT_BLACK", "WINDOW", "LOGO_ZONE", "BEAD_ZONE_REF", "TEXT"],
    "GF_Frame_Inspection.dxf": ["FRONT_VIEW", "BACK_VIEW", "CTF_OUTLINES", "SECTIONS", "TEXT"],
}


def _match_rect(polys, r):
    """find the closed polyline of a layer that matches the rounded rectangle r"""
    best = None
    for p in polys:
        c = check_rrect_poly(p["v"], r)
        if c["ok"] and p["closed"]:
            return c
        best = best or c
    return best or {"ok": False, "why": "no polyline"}


def _circles(doc, layer):
    return [(e.dxf.center.x, e.dxf.center.y, e.dxf.radius) for e in doc.modelspace()
            if e.dxftype() == "CIRCLE" and e.dxf.layer == layer]


def _texts(doc, prefix):
    out = []
    for e in doc.modelspace():
        if e.dxftype() == "TEXT" and e.dxf.text.startswith(prefix):
            out.append((e.dxf.text, e.dxf.insert.x, e.dxf.insert.y))
    return out


def _f_mark_dir(doc):
    """direction of the orientation 'F' bars: +1 if the bars point to +x from the stem (reads correctly)"""
    lines = [e for e in doc.modelspace() if e.dxftype() == "LINE" and e.dxf.layer == "TEXT"]
    if len(lines) < 3:
        return None
    stem = [l for l in lines if abs(l.dxf.start.x - l.dxf.end.x) < 1e-9]
    bars = [l for l in lines if abs(l.dxf.start.y - l.dxf.end.y) < 1e-9]
    if not stem or not bars:
        return None
    sx = stem[0].dxf.start.x
    return 1 if all(max(b.dxf.start.x, b.dxf.end.x) > sx + 1e-9 for b in bars) else -1


def gap_all_round(inner: Rect, outer: Rect):
    """min / max normal distance from the inner boundary to the outer boundary (both rounded rectangles)"""
    pts = inner.boundary(n_arc=180, step=0.05)
    d = -outer.sdf(pts[:, 0], pts[:, 1])
    return float(d.min()), float(d.max())


def dxf_checks(G, P, C):
    res = {}
    for path in sorted(glob.glob(os.path.join(OUT_DIR, "*.dxf"))):
        name = os.path.basename(path)
        inv = dxf_inventory(path)
        doc = inv["doc"]
        view_layers = {"FRONT_VIEW", "BACK_VIEW"}           # projected edges are open curves by nature
        r = {"units_mm": inv["units_ok"], "entities_on_layer_0": inv["entities_on_layer_0"],
             "open_polylines": [l for l in inv["open_polylines"] if l not in view_layers],
             "open_projection_edges (not contours, allowed)": sum(1 for l in inv["open_polylines"] if l in view_layers),
             "counts": inv["counts"]}
        req = REQUIRED_LAYERS.get(name, [])
        r["required_layers_present"] = all(l in inv["layers"] for l in req)
        polys = inv["polys"]
        if name.startswith("GF_Sheet_"):
            var = name[9:11]
            r["cutout"] = _match_rect(polys.get("CUTOUT", []), G.cut)
            r["cutout_single_closed"] = len(polys.get("CUTOUT", [])) == 1 and polys["CUTOUT"][0]["closed"]
            fl = ["F1", "F2", "F3", "F4"] + (["F5", "F6", "F7", "F8"] if var == "S8" else [])
            holes, marks = _circles(doc, "HOLES"), _circles(doc, "STUD_MARKS")
            if var == "R4":
                d = P.num("sheet_variants.R4.value", r"dia ([\d.]+) \+([\d.]+)/0 \(dia", 1)
                ok = len(holes) == 4 and all(any(abs(h[0] - G.F[f]["u"]) < TOL and abs(h[1] - G.F[f]["v"]) < TOL and
                                                 abs(2 * h[2] - d) < TOL for h in holes) for f in fl) and not marks
                r["holes"] = {"n": len(holes), "dia": d, "positions_ok": ok, "ok": ok}
            else:
                ok = len(marks) == len(fl) and all(any(abs(h[0] - G.F[f]["u"]) < TOL and abs(h[1] - G.F[f]["v"])
                                                       < TOL for h in marks) for f in fl) and not holes
                r["stud_marks"] = {"n": len(marks), "positions_ok": ok, "ok": ok}
            r["glass_ref"] = _match_rect(polys.get("GLASS_REF", []), G.glass)["ok"]
            r["window_ref"] = _match_rect(polys.get("GLASS_REF", []), G.window)["ok"]
            r["lip_refs"] = all(_match_rect(polys.get("LIP_REF", []), x)["ok"] for x in (G.lip_in, G.lip_out,
                                                                                          G.seat_out))
            r["flange_ref"] = _match_rect(polys.get("FLANGE_REF", []), G.flange)["ok"]
            if var != "S8":
                strips = [p for p in polys.get("TAPE_REF", []) if len(p["v"]) == 4]
                ok = all(any(check_rrect_poly(p["v"], s)["ok"] for p in strips) for s in G.strips.values())
                r["tape_strips"] = {"n": len(strips), "match_master_lengths": ok, "ok": ok}
        if name == "GF_Glass.dxf":
            r["outline"] = _match_rect(polys.get("OUTLINE", []), G.glass)
            r["window"] = _match_rect(polys.get("WINDOW", []), G.window)
            sb = 0.5 * sum(P.num("print", r"setback ([\d.]+)-([\d.]+)", k, name="print_layers") for k in (1, 2))
            po = G.glass.offset(-sb)
            r["print_black_outer"] = _match_rect(polys.get("PRINT_BLACK", []), po)
            r["print_black_inner_is_window"] = _match_rect(polys.get("PRINT_BLACK", []), G.window)["ok"]
            r["print_black_hatch"] = inv["counts"].get("HATCH@PRINT_BLACK", 0) == 1
            r["logo_zone"] = _match_rect(polys.get("LOGO_ZONE", []), G.logo)["ok"]
            r["bead_zone"] = all(_match_rect(polys.get("BEAD_ZONE_REF", []), x)["ok"] for x in (G.bead_out,
                                                                                                G.bead_inn))
        if name == "GF_BondingAids.dxf":
            pip = _circles(doc, "PIPS")
            r["pips"] = len(pip) == 8 and all(any(abs(c[0] - u) < TOL and abs(c[1] - v) < TOL for c in pip)
                                              for u, v in G.pips.values())
            r["slots"] = len(polys.get("SLOTS", [])) == 8
            r["slot_shape"] = all(abs(abs(poly_area_bulge(p["v"])) - (G.slot_w * (G.slot_l - G.slot_w) +
                                                                       math.pi * G.slot_w ** 2 / 4)) < TOL
                                  for p in polys.get("SLOTS", []))
            r["bead_band"] = all(_match_rect(polys.get("BEAD", []), x)["ok"] for x in (G.bead_out, G.bead_inn))
        if name == "GF_Frame_Inspection.dxf":
            secs = polys.get("SECTIONS", [])
            r["D50 sections closed"] = bool(secs) and all(p_["closed"] for p_ in secs)
            r["ctf_lip_outlines"] = all(_match_rect(polys.get("CTF_OUTLINES", []), x)["ok"] for x in (G.lip_in,
                                                                                                    G.lip_out))
        if name == "GF_Jig_J2.dxf":
            pins = _circles(doc, "PIN_HOLES")
            r["pins_mirrored_at_F1_F4"] = len(pins) == 4 and all(
                any(abs(c[0] + G.F[f]["u"]) < TOL and abs(c[1] - G.F[f]["v"]) < TOL for c in pins)
                for f in ("F1", "F2", "F3", "F4"))
        r["ok"] = (r["units_mm"] and r["entities_on_layer_0"] == 0 and not r["open_polylines"] and
                   r["required_layers_present"] and
                   all((v.get("ok", True) if isinstance(v, dict) else (v is not False))
                       for k, v in r.items() if k not in ("counts", "open_polylines", "entities_on_layer_0",
                                                          "units_mm", "required_layers_present", "ok",
                                                          "open_projection_edges (not contours, allowed)")))
        res[name] = r
    return res


def geometry_checks(G, P, C):
    out = {}
    stated = [("glass -> lip inner face (g2)", G.glass, G.lip_in, G.g2),
              ("lip inner -> lip outer (lip_w)", G.lip_in, G.lip_out, G.lip_w),
              ("lip outer -> cut-out (g1)", G.lip_out, G.cut, G.g1),
              ("lip outer -> seat ring outer (seat_ring_w)", G.lip_out, G.seat_out, G.seat_w),
              ("glass -> bead outer edge (bead_edge, inward)", G.bead_out, G.glass, G.bead_edge),
              ("bead outer -> bead inner (bead_w, inward)", G.bead_inn, G.bead_out, G.bead_w)]
    import re as _re
    corner_note = {"glass -> lip inner face (g2)": P.dnote("R_glass"), "lip outer -> cut-out (g1)": P.dnote("R_cut")}
    rows = []
    for name, a, b, g in stated:
        mn, mx = gap_all_round(a, b)
        r = {"pair": name, "stated_sides": g, "min": round(mn, 5), "max_at_corners": round(mx, 5)}
        if name in corner_note:
            m = _re.search(r"~([\d.]+)", corner_note[name])
            exp = float(m.group(1))
            r["master_corner_note"] = "~%s" % m.group(1)
            r["ok"] = abs(mn - g) < TOL and abs(mx - exp) < 0.01
        else:
            r["ok"] = abs(mn - g) < TOL and abs(mx - g) < TOL
        rows.append(r)
    out["gaps_all_round"] = {"rows": rows, "ok": all(r["ok"] for r in rows),
                             "note": "GF-1.1: sides = stated gap, corners about 0.50 (glass R6.25 and cut-out R7.55 "
                                     "are no longer concentric with the lip R6.4 / R7.4)"}
    cons = G.consistency()
    out["master_self_consistency"] = cons
    # holes / studs vs the cut-out
    mind = C("min_hole_to_cutout")
    rivet_d = P.num("fasteners.hardware", r"dia ([\d.]+) LARGE-FLANGE blind rivet", name="rivet")
    hole = P.num("sheet_variants.R4.value", r"dia ([\d.]+) \+([\d.]+)/0 \(dia", 1)
    req = max(mind, 2 * rivet_d)
    hrows = []
    for k, f in G.F.items():
        d = float(G.cut.sdf(f["u"], f["v"]))
        lig = d - hole / 2.0
        r4 = k in ("F1", "F2", "F3", "F4")
        ok = d >= (req if r4 else mind) - 1e-9
        hrows.append({"F": k, "centre_to_cut_edge": round(d, 3), "required": req if r4 else mind,
                      "R4_hole_ligament": round(lig, 3) if r4 else None, "ok": ok})
    out["holes_vs_cutout"] = {"rule": "centre >= %s from the cut-out (concept 11.4); R4 rivets >= max(8, 2d = %s)" % (
        mind, 2 * rivet_d), "rows": hrows, "ok": all(r["ok"] for r in hrows)}
    # R4 large-flange head (GF-1.1 round 3): head edge to the cut-out corner arc, recomputed vs the master note
    head_d = P.num("fasteners.hardware", r"head dia ([\d.]+) 'K\d+'", name="rivet")
    he_m = P.num("sheet_variants.R4.note", r"dia-[\d.]+ head edge ([\d.]+) from the cut-out corner arc")
    he = min(float(G.cut.sdf(G.F[k]["u"], G.F[k]["v"])) for k in ("F1", "F2", "F3", "F4")) - head_d / 2.0
    out["rivet_head_vs_cutout"] = {"head_d": head_d, "edge_to_cut_calc": round(he, 4), "master": he_m,
                                   "ok": abs(round(he, 2) - he_m) < 0.006}
    out["window_inside_glass"] = {"min_border": round(min(G.window.x0 - G.glass.x0, G.glass.x1 - G.window.x1,
                                                          G.glass.y1 - G.window.y1, G.window.y0 - G.glass.y0), 4),
                                  "ok": cons["borders"]["ok"]}
    lz = G.logo
    out["logo_zone"] = {"gap_to_window": round(G.window.y0 - lz.y1, 3),
                        "gap_to_bead_inner_edge": round(lz.y0 - G.bead_inn.y0, 3),
                        "required_gap_to_window": P.num("logo_zone", r">= ([\d.]+) from the window", name="logo_h"),
                        "ok": G.window.y0 - lz.y1 >= P.num("logo_zone", r">= ([\d.]+) from the window",
                                                            name="logo_h") and lz.y0 > G.bead_inn.y0}
    out["front_view_transform"] = G.fv.check_against_master_text()
    return out


def mirror_checks(G, P, dx):
    """asymmetric references in every front-view DXF + the mirrored J2 plate"""
    import ezdxf
    rows = {}
    ok = True
    exp = {r[0]: (r[1], r[2]) for r in G.mirror_refs()}
    for name in FRONT_VIEW_DXF:
        doc = ezdxf.readfile(os.path.join(OUT_DIR, name))
        t = _texts(doc, "MIRROR-REF")
        got = {a: (x, y) for a, x, y in t}
        r = {"refs": {k: [round(v[0], 4), round(v[1], 4)] for k, v in got.items()}}
        r["abs_left_at_front_right"] = any(("KiCad left" in k) and v[0] > 0 for k, v in got.items())
        r["chin_at_front_bottom"] = any(("chin" in k) and v[1] < 0 for k, v in got.items())
        r["same_as_transform"] = all(k in got and abs(got[k][0] - e[0]) < TOL and abs(got[k][1] - e[1]) < TOL
                                     for k, e in exp.items())
        fd = _f_mark_dir(doc)
        if fd is not None:
            r["orientation_F_reads_correctly"] = fd > 0
        # window offset (chin) where the window is in the file
        for lay in ("WINDOW", "GLASS_REF"):
            for e in doc.modelspace():
                if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == lay:
                    pts = [(p[0], p[1]) for p in e.get_points("xy")]
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    if abs((max(xs) - min(xs)) - G.window.w) < TOL:
                        r["window_centre_v"] = round((max(ys) + min(ys)) / 2, 4)
        r["ok"] = r["abs_left_at_front_right"] and r["chin_at_front_bottom"] and r["same_as_transform"] and \
            r.get("orientation_F_reads_correctly", True) and \
            ("window_centre_v" not in r or abs(r["window_centre_v"] - G.window.c[1]) < TOL)
        ok &= r["ok"]
        rows[name] = r
    # land asymmetry in the bonding DXF: the narrow land (abs left, 6.11) must sit at u > 0
    doc = ezdxf.readfile(os.path.join(OUT_DIR, "GF_BondingAids.dxf"))
    lt = _texts(doc, "LAND ")
    L = G.lands()
    narrow = min(L.values())
    land_ok = any(("abs left" in a) and x > 0 and ("%.2f" % narrow) in a for a, x, y in lt)
    rows["GF_BondingAids.dxf land asymmetry"] = {"texts": [[a, round(x, 3), round(y, 3)] for a, x, y in lt],
                                                 "narrow_land_abs_left_at_u>0": land_ok}
    ok &= land_ok
    doc = ezdxf.readfile(os.path.join(OUT_DIR, "GF_Jig_J2.dxf"))
    pins = _circles(doc, "PIN_HOLES")
    f1 = G.F["F1"]
    rows["GF_Jig_J2.dxf (plate view, intentionally mirrored)"] = {
        "F1_front_u": f1["u"], "F1_plate_x": [round(c[0], 3) for c in pins if abs(c[1] - f1["v"]) < TOL],
        "mirrored": any(abs(c[0] + f1["u"]) < TOL and abs(c[1] - f1["v"]) < TOL for c in pins)}
    rows["artwork GF_Glass_Print_1to1.pdf"] = {
        "by_construction": "x_page = page_centre - u (seen from face 2); the orientation F is drawn through the same "
                           "transform and appears mirrored at the top-right (checked in the preview PNG)"}
    return {"rows": rows, "ok": ok}


def pdf_checks():
    out = {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "*.pdf"))):
        b = open(p, "rb").read()
        m = re.findall(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", b)
        pages = len(re.findall(rb"/Type\s*/Page[^s]", b))
        mb = [float(x) for x in m[0]] if m else None
        size_mm = [round((mb[2] - mb[0]) * 25.4 / 72, 1), round((mb[3] - mb[1]) * 25.4 / 72, 1)] if mb else None
        out[os.path.basename(p)] = {"pages": pages, "page_mm": size_mm, "bytes": len(b),
                                    "fonts_embedded_truetype": b.count(b"/FontFile2") > 0}
    return out


def master_findings(G, P, C):
    """status of the earlier findings after GF-1.1 round 3 + remaining inconsistencies between params, STEP, design
    document and drawings"""
    from gf_common import REPO, V2_V1PARAMS
    f = []
    r4 = P.raw["sheet_variants"]["R4"]["value"]
    f.append({"id": "M1", "status": "resolved in GF-1.1", "topic": "R4 hole diameter",
              "detail": "sheet_variants.R4 now: '%s'" % r4.split(";")[0]})
    a0 = P.num("drawing_tolerances.glass", r"arris ([\d.]+)-([\d.]+)", 1, name="edge")
    s1 = P.num("print", r"setback ([\d.]+)-([\d.]+)", 2, name="print_layers")
    f.append({"id": "M2", "status": "open in the master; handled by a drawing note (GF-D10 / GF-D11)",
              "topic": "print setback vs arris", "detail": "setback 0-%s vs a %s-%s face-2 arris: the drawings "
              "allow an unprinted rim up to %s at the arris and ask the supplier to confirm print-to-edge "
              "capability." % (s1, a0, P.num("drawing_tolerances.glass", r"arris ([\d.]+)-([\d.]+)", 2, name="edge"),
                               C("print_rim_max"))})
    f.append({"id": "M3", "status": "resolved in GF-1.1", "topic": "S8 gasket / shim",
              "detail": "gasket '%s'; shim '%s'" % (P.text("tape_and_gasket", "foam_gasket_S8"),
                                                    P.text("fasteners.hardware", "spacer_S8").split(" on the")[0])})
    f.append({"id": "M4", "status": "resolved in GF-1.1", "topic": "ink / enamel strength",
              "detail": "print.ink: '%s'" % P.text("print", "ink")})
    f.append({"id": "M5", "status": "open (supplier question)", "topic": "3.0 mm thermal tempering",
              "detail": "3.0 type still 'thermally tempered (CS if the supplier cannot temper < 3.2)'."})
    fm, fi = G.formex()
    with open(V2_V1PARAMS, encoding="utf-8") as fh:
        v1 = {q["name"]: q["value"] for q in json.load(fh)["parameters"]}
    same = abs(v1["SHEET_INSET"] - fi["inset"]) < 1e-6 and abs(v1["SHEET_R"] - fi["R"]) < 1e-6
    f.append({"id": "M6", "status": "resolved in GF-1.1 round 3" if same else "OPEN - master differs from v2",
              "topic": "Formex outline",
              "detail": "plan_rectangles.formex (%s): panel - %s per side, R%s, z %s; v2 v1_params SHEET_INSET %s / "
                        "SHEET_R %s -> %s. GF-D20 reads the master." % (
                            fi["status"], fi["inset"], fi["R"], fi["z"], v1["SHEET_INSET"], v1["SHEET_R"],
                            "same" if same else "DIFFERENT")})
    f.append({"id": "M7", "status": "resolved in GF-1.1", "topic": "bead area",
              "detail": "master bead_area %s mm2 vs centre-line x width %.1f mm2 (glass-relative bead band)." % (
                  P.raw["as_modelled_GF-1.1"]["bead_area_mm2"], G.bead_cl.perimeter() * G.bead_w)})
    gR, _, _, gRt = P.onesided("drawing_tolerances.glass", "corner_R")
    cR, _, _, cRt = P.onesided("drawing_tolerances.sheet", "cut_out_corner_R")
    f.append({"id": "N1", "status": "resolved in GF-1.1 round 3", "topic": "corner-radius tolerances",
              "detail": "glass R%s %s (GF-D10), cut-out R%s %s (GF-D01..03), both one-sided, read from the master."
                        % (gR, gRt, cR, cRt)})
    stale = [k for k, v in G.consistency()["fasteners_uv_and_cut_distance"]["rows"].items()
             if v["master_d_cut_stale"]]
    f.append({"id": "N2", "status": "resolved in GF-1.1 round 3" if not stale else "OPEN - params stale",
              "topic": "fastener distance to the cut-out",
              "detail": "d_cut_out_edge %s (master) vs %.4f (drawn)%s." % (
                  P.fast("F1")["d_cut_out_edge"], float(G.cut.sdf(G.F["F1"]["u"], G.F["F1"]["v"])),
                  "" if not stale else "; stale for " + ", ".join(stale))})
    cb, _ = G.fastener_cuts()
    dd = os.path.join(REPO, "Design Reports", "Rev3.0", "Rev3.0_GlassFront_Design.md")
    dtxt = open(dd, encoding="utf-8").read() if os.path.exists(dd) else ""
    cbs = "%s × %s" % (cb["cb_w"], cb["cb_l"])
    f.append({"id": "N3", "status": ("resolved (design document)" if cbs in dtxt and "6.6 × 8.2" not in dtxt
                                     else "OPEN - design document"), "topic": "counterbore size",
              "detail": "params / STEP %s x %s; design document mentions '%s': %s, '6.6 × 8.2': %s." % (
                  cb["cb_w"], cb["cb_l"], cbs, cbs in dtxt, "6.6 × 8.2" in dtxt)})
    f.append({"id": "N4", "status": "resolved in GF-1.1 round 3", "topic": "clearance pocket reference level",
              "detail": "plan_rectangles.pocket note: defined at Z_SEAT, 0.10 larger per side at the land; GF-D20 "
                        "footnote and GF-D50 CTF 12 follow it (GF-D20 asserts the four at-land values)."})
    f.append({"id": "N5", "status": "resolved in GF-1.1 round 3", "topic": "lip venting vs exclusion zone",
              "detail": "drawing_tolerances.frame.vent_witness_lip_top %s + cad_rules entry; GF-D50 note 8 cites "
                        "them (no longer [P])." % P.val("drawing_tolerances.frame", "vent_witness_lip_top")})
    # ---- round 3
    env = (P.num("fasteners.hardware", r"must lie within dia ([\d.]+) x ([\d.]+) high", 1, name="stud"),
           P.num("fasteners.hardware", r"must lie within dia ([\d.]+) x ([\d.]+) high", 2, name="stud"))
    sp = P.text("fasteners.hardware", "spacer_S8")
    m = re.search(r"over a ([\d.]+) weld collar", sp)
    m2 = re.search(r"over the dia-([\d.]+) flange \+ collar envelope", sp)
    f.append({"id": "R3-1", "status": ("resolved in GF-1.1 round 4" if (not m and m2 and float(m2.group(1)) == env[0])
                                       else "OPEN - params wording"),
              "topic": "weld-stud envelope",
              "detail": "stud note (lead decision C5): flange within dia %s x %s high, axis +-%s to the cut-out; "
                        "GF-D01 / GF-D02 draw this. spacer_S8 now quotes the dia-%s envelope." % (
                            env[0], env[1], P.num("fasteners.hardware", r"within \+-([\d.]+) of its nominal",
                                                  name="stud"), m2.group(1) if m2 else "?")})
    spt = P.item("drawing_tolerances.sheet", "stud_position_tol")
    f.append({"id": "R3-2", "status": ("resolved in GF-1.1 round 4" if "REQUIREMENT" in spt["note"] else "OPEN"),
              "topic": "stud position wording",
              "detail": "stud_position_tol %s ('%s'); S4 value '%s'. GF-D01 / GF-D02 state the requirement once and "
                        "the template as the recommended means." % (spt["value"], spt["note"],
                                                                    P.raw["sheet_variants"]["S4"]["value"])})
    ot = P.item("drawing_tolerances.glass", "outline_tol")
    f.append({"id": "R3-3", "status": "resolved in GF-1.1 round 4", "topic": "glass outline",
              "detail": "outline_tol %s ('%s'); GF-D10 requests it and names the fallback." % (ot["value"],
                                                                                              ot["note"])})
    f.append({"id": "R4-1", "status": "drawing adds the lead's second clause", "topic": "shim rule",
              "detail": "master shim_rule '%s'; the drawings add '%s' (lead round-3 addition A wording)." % (
                  P.val("jig_and_mounting_shims", "shim_rule"), C("shim_rule")["en_extra"])})
    f.append({"id": "R4-2", "status": "applied (GF-D50 note 2)", "topic": "UL card thickness",
              "detail": "material.UL_card: '%s'." % P.val("material", "UL_card")})
    ga = C("gap_acceptance")
    f.append({"id": "R3-4", "status": "lead values used; design document differs", "topic": "gap acceptance",
              "detail": "drawn: g2 sides %s, g1 sides %s, corners '%s' at %d C. Design document sec. 9 inspection "
                        "table: g2 0.30-0.50 with a +-0.1 glass (0.20-0.60 at +-0.2; opposite sides within 0.10), "
                        "g1 0.25-0.55, corners 0.30-0.80." % (ga["g2_sides"], ga["g1_sides"], ga["corners"]["en"],
                                                              ga["temp_C"])})
    f.append({"id": "R3-5", "status": "note only", "topic": "washer bearing / coring groove",
              "detail": "washer_nut note: '%s'. No drawing says the M5 rivet washer bridges the groove; the [P] "
                        "r_in +0/-0.1 on GF-D50 keeps the dia-12.4 washer seat." % P.item(
                            "fasteners.hardware", "washer_nut")["note"]})
    return f


def run(G=None, P=None, C=None):
    P = P or Params()
    C = C or Choices()
    G = G or Geom(P)
    dx = dxf_checks(G, P, C)
    out = {"dxf": dx, "dxf_all_ok": all(v["ok"] for v in dx.values()),
           "geometry": geometry_checks(G, P, C), "mirroring": mirror_checks(G, P, dx), "pdf": pdf_checks(),
           "master_findings": master_findings(G, P, C)}
    g = out["geometry"]
    out["geometry_all_ok"] = (g["gaps_all_round"]["ok"] and g["holes_vs_cutout"]["ok"] and
                              g["rivet_head_vs_cutout"]["ok"] and
                              g["window_inside_glass"]["ok"] and g["logo_zone"]["ok"] and
                              g["front_view_transform"]["consistent"] and
                              all(v["ok"] for v in g["master_self_consistency"].values()))
    return out


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: (v if k in ("dxf_all_ok", "geometry_all_ok") else "...") for k, v in r.items()}, indent=1))
    for k, v in r["dxf"].items():
        print(k, v["ok"], {kk: vv for kk, vv in v.items() if kk not in ("counts",)} if not v["ok"] else "")
    print("mirroring ok:", r["mirroring"]["ok"])
    for k, v in r["mirroring"]["rows"].items():
        print("  ", k, v.get("ok", v))
    for k, v in r["geometry"].items():
        print("geom", k, v.get("ok", v.get("consistent")) if isinstance(v, dict) else v)
    print(json.dumps(r["pdf"], indent=0))
