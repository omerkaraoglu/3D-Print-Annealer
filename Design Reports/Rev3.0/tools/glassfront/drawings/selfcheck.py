"""Self-checks of the GF drawing set (GF-2.0). Re-opens every DXF with ezdxf, checks geometry against the
master, proves the front-view mirroring with asymmetric references, reads the PDF page sizes, scans every drawn text
for stale GF-1.1 callouts (make_all), and lists the findings in the master (inconsistencies) that the drawings had to
work around.

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
from gf_geom import Geom, gap_temperatures

TOL = 1e-3
FRONT_VIEW_DXF = ["GF_Sheet_S4.dxf", "GF_Sheet_R4.dxf", "GF_Glass.dxf", "GF_BondingAids.dxf",
                  "GF_Jig_J1.dxf", "GF_Frame_Inspection.dxf"]                  # GF-2.0: GF_Sheet_S8 withdrawn
REQUIRED_LAYERS = {
    "GF_Sheet_S4.dxf": ["CUTOUT", "HOLES", "STUD_MARKS", "GLASS_REF", "LIP_REF", "FLANGE_REF", "TAPE_REF", "TEXT"],
    "GF_Sheet_R4.dxf": ["CUTOUT", "HOLES", "STUD_MARKS", "GLASS_REF", "LIP_REF", "FLANGE_REF", "TAPE_REF", "TEXT"],
    "GF_Glass.dxf": ["OUTLINE", "PRINT_BLACK", "WINDOW", "LOGO_ZONE", "BEAD_ZONE_REF", "TEXT"],
    "GF_BondingAids.dxf": ["FLANGE_REF", "SLOTS", "COUNTERBORES", "LAND", "BEAD", "PIPS", "TAPE", "DABS", "BEND_SLOT",
                           "TEXT"],
    "GF_Jig_J2.dxf": ["PLATE", "PIN_HOLES", "STOP_HOLES", "TAIL_HOLDER", "REF", "TEXT"],
    "GF_TailFoldGauge.dxf": ["GAUGE", "NOSE_TANGENT", "ENGRAVE", "LIMIT_REF", "PANEL_REF", "SECTION", "TEXT"],
    "GF_Frame_Inspection.dxf": ["FRONT_VIEW", "BACK_VIEW", "CTF_OUTLINES", "SECTIONS", "TEXT"],
}
# words / numbers that must not appear on a GF-2.1 sheet except as revision history (checked by stale_text_scan)
STALE = [
    # GF-1.1 (chin, S8, F5-F8, GF-1.1 sizes)
    r"\bchin\b", r"\bS8\b", r"\bF[5-8]\b", r"F5-F8", r"44\.5", r"14\.0 border", r"181\.48", r"143\.83",
    r"185\.08", r"147\.43", r"223\.48", r"185\.83", r"203\.48", r"165\.83", r"101\.74", r"82\.915", r"183\.48",
    r"145\.83",
    # wording withdrawn by the GF-2.0 correction passes
    r"\bD9\b", r"to be re-verified", r"\[open\]", r"20 C only", r"meet on its outline", r"\b2\.55\b",
    r"position 0\.25\b", r"\b0\.79\b", r"118\.74", r"\b0\.76\b", r"\b2\.24\b",
    # GF-2.0 numbers and wording (GF-2.1 = border 19.0, g_bend 3.23; both GF-2.0 findings closed)
    r"\b18\.5\b", r"slot 3\.00?\b", r"3\.00? x 128\.8", r"g_bend 3\.00?\b", r"\b3\.00? bend-gap", r"3\.0 = g_bend",
    r"190\.48", r"122\.32", r"194\.08", r"125\.92", r"232\.48", r"165\.57", r"165\.565", r"212\.48", r"144\.32",
    r"192\.48", r"124\.32", r"\b5\.99\b", r"\b10\.61\b", r"\b13\.37\b", r"\b12\.53\b", r"\b8\.19\b",
    r"\b5\.71\b", r"\b8\.47\b", r"\b7\.63\b", r"106\.24", r"72\.16", r"117\.99", r"122\.00\b", r"97\.24",
    r"0\.70 feeler", r"feeler 0\.70", r"within 2\.30\b", r"2\.30 line", r"\b1\.09\b", r"0\.80 to (the )?break",
    r"break edge 0\.80", r"\b0\.946\b", r"\b0\.654\b", r"\b0\.239\b", r"\b28\.6\b", r"\b29\.6\b",
    r"\b0\.67\b", r"\b3\.06\b", r"(?i)open finding", r"(?i)provisional", r"(?i)\bOPEN\b.*finding"]
HISTORY_OK = re.compile(r"GF-1\.1|GF-2\.0|withdrawn|removed|\(was |no longer", re.I)


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


def tail_gauge_check(doc, polys, G, P, C):
    """GF-D21 gauge DXF (plan frame x = abs x - slot centre, y = -distance from the panel edge face) against the
    master: slot = g_bend (= fold_test gauge slot) over the bend-gap slot length, nose tangent at g_bend + R, limit
    line at the fold_test tail outer surface limit (slot - feeler), engraved pair at the divider rib, section height =
    land-plate back above the CTP front"""
    g, R = P.d("g_bend"), P.d("bend_nose_R")
    sl = P.rect("bend_gap_slot")
    Ls, xm = sl.x1 - sl.x0, 0.5 * (sl.x0 + sl.x1)
    tg = C("tg_gauge")
    ft = P.raw["fold_test"]
    lim_ft = ft["tail_outer_surface_limit_from_panel_edge_mm"]
    clr = round(g - lim_ft, 4)                    # = the fold_test feeler
    H = P.level("Z_LANDPLATE_BACK") - P.level("Z_CTP_FRONT")
    out = {}
    out["fold_test_slot_=_g_bend"] = abs(ft["gauge_slot_mm"] - g) < 1e-9
    out["fold_test_slot_-_feeler_=_limit"] = abs(ft["gauge_slot_mm"] - ft["feeler_mm"] - lim_ft) < 1e-9
    gp = polys.get("GAUGE", [])
    v = gp[0]["v"] if len(gp) == 1 else []
    rec = [p for p in v if abs(p[1] + g) < TOL]
    out["slot_face_at_-g_bend"] = len(rec) == 2 and abs(abs(rec[0][0] - rec[1][0]) - Ls) < TOL
    xs = [p[0] for p in v]
    out["overall_length"] = bool(v) and abs((max(xs) - min(xs)) - (Ls + 2 * tg["pad_len"])) < TOL
    out["depth"] = bool(v) and abs(-min(p[1] for p in v) - (g + tg["depth"])) < TOL
    lines = {}
    for e in doc.modelspace():
        if e.dxftype() == "LINE":
            lines.setdefault(e.dxf.layer, []).append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
    nt = lines.get("NOSE_TANGENT", [])
    out["nose_tangent_at_-(g+R)"] = len(nt) == 1 and abs(nt[0][0][1] + g + R) < TOL
    lim = lines.get("LIMIT_REF", [])
    out["limit_line_at_-(fold_test limit)"] = len(lim) == 1 and abs(lim[0][0][1] + lim_ft) < TOL
    eg = sorted(l_[0][0] for l_ in lines.get("ENGRAVE", []))
    out["engraved_pair_at_div_x"] = len(eg) == 2 and abs(eg[0] - (P.d("div_x") - P.d("div_t") / 2 - xm)) < TOL and \
        abs(eg[1] - (P.d("div_x") + P.d("div_t") / 2 - xm)) < TOL
    sp = polys.get("SECTION", [])
    if sp:
        ys = [p[1] for p in sp[0]["v"]]
        out["section_height"] = abs((max(ys) - min(ys)) - H) < TOL
    out["values"] = {"g_bend": g, "R": R, "slot_length": Ls, "feeler": clr, "tail_limit_line": lim_ft,
                     "exact_feeler": ft["exact_feeler_for_the_budget_mm"], "height": H}
    out["ok"] = all(v_ for k_, v_ in out.items() if k_ != "values")
    return out


def n2s(v):
    return "%.2f" % v


def stale_text_scan(sheets):
    """scan every string drawn on every sheet of this run for GF-1.1-only words / numbers; a hit is allowed only
    inside revision history (the same string, or the joined title-block change note, names GF-1.1 / withdrawn /
    removed)"""
    res = {}
    total = 0
    for sh in sheets:
        key = "%s %s" % (sh.dwg, sh.title)
        texts = sh.all_text()
        joined = " ".join(texts)
        hits = []
        for t in texts:
            for pat in STALE:
                for m in re.finditer(pat, t):
                    # allowed: history context in the same string, or in a 60-char window of the joined text
                    j = joined.find(t)
                    win = joined[max(0, j + m.start() - 60): j + m.end() + 60] if j >= 0 else t
                    if HISTORY_OK.search(t) or HISTORY_OK.search(win):
                        continue
                    hits.append({"pattern": pat, "text": t[:160]})
        res[key] = {"texts": len(texts), "stale_hits": hits}
        total += len(hits)
    return {"rule": "patterns %s allowed only as revision history (%s)" % (STALE, HISTORY_OK.pattern),
            "sheets": res, "total_hits": total, "ok": total == 0}


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
            fl = P.fast_names()                                   # GF-2.0: F1-F4 only
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
            r["slots"] = len(polys.get("SLOTS", [])) == len(G.F) == 4
            r["bend_gap_slot"] = _match_rect(polys.get("BEND_SLOT", []), G.slot_bg)["ok"]
            r["land_inner_has_slot"] = any(
                any(abs(v[1] - G.slot_bg.y0) < TOL for v in p["v"]) for p in polys.get("LAND", []))
            r["slot_shape"] = all(abs(abs(poly_area_bulge(p["v"])) - (G.slot_w * (G.slot_l - G.slot_w) +
                                                                       math.pi * G.slot_w ** 2 / 4)) < TOL
                                  for p in polys.get("SLOTS", []))
            r["bead_band"] = all(_match_rect(polys.get("BEAD", []), x)["ok"] for x in (G.bead_out, G.bead_inn))
        if name == "GF_Frame_Inspection.dxf":
            secs = polys.get("SECTIONS", [])
            r["D50 sections closed"] = bool(secs) and all(p_["closed"] for p_ in secs)
            r["ctf_lip_outlines"] = all(_match_rect(polys.get("CTF_OUTLINES", []), x)["ok"] for x in (G.lip_in,
                                                                                                    G.lip_out))
            r["ctf_slot_and_rib"] = all(_match_rect(polys.get("CTF_OUTLINES", []), x)["ok"] for x in (G.slot_bg,
                                                                                                    G.rib))
        if name == "GF_Jig_J2.dxf":
            pins = _circles(doc, "PIN_HOLES")
            r["pins_mirrored_at_F1_F4"] = len(pins) == 4 and all(
                any(abs(c[0] + G.F[f]["u"]) < TOL and abs(c[1] - G.F[f]["v"]) < TOL for c in pins)
                for f in ("F1", "F2", "F3", "F4"))
            th = C("j2_tail_holder")
            thc = _circles(doc, "TAIL_HOLDER")
            r["tail_holder_hole"] = len(thc) == 1 and abs(thc[0][0]) < TOL and \
                abs(thc[0][1] - (G.flange.y0 - th["post_offset"])) < TOL and abs(2 * thc[0][2] - th["post_d"]) < TOL
        if name == "GF_TailFoldGauge.dxf":
            r["gauge"] = tail_gauge_check(doc, polys, G, P, C)
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
    req_w = P.num("logo_zone", r">= ([\d.]+) from the window", name="logo_h")
    req_g = P.num("logo_zone", r">= ([\d.]+) from the glass edge", name="logo_h")
    out["logo_zone"] = {"size": [lz.w, lz.h], "centre_uv": [round(lz.c[0], 4), round(lz.c[1], 4)],
                        "gap_to_window": round(G.window.y0 - lz.y1, 3), "required_gap_to_window": req_w,
                        "gap_to_glass_edge": round(lz.y0 - G.glass.y0, 3), "required_gap_to_glass_edge": req_g,
                        "overlaps_bead_band_by": round(G.bead_inn.y0 - lz.y0, 3),
                        "note": "%s: logo_centre y %s puts the 15-high zone %.2f from the window and %.2f from the "
                                "glass edge (rules >= %s / >= %s). The logo colour lies under the black layer, so the "
                                "bead bonds on black over it." % (
                                    P.revision, P.val("logo_zone", "logo_centre")[1], G.window.y0 - lz.y1,
                                    lz.y0 - G.glass.y0, req_w, req_g),
                        "ok": G.window.y0 - lz.y1 >= req_w - 1e-6 and lz.y0 - G.glass.y0 >= req_g - 1e-6}
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
        r["bottom_edge_at_front_bottom"] = any(("bottom glass edge" in k) and v[1] < 0 for k, v in got.items())
        r["same_as_transform"] = all(k in got and abs(got[k][0] - e[0]) < TOL and abs(got[k][1] - e[1]) < TOL
                                     for k, e in exp.items())
        fd = _f_mark_dir(doc)
        if fd is not None:
            r["orientation_F_reads_correctly"] = fd > 0
        # window position where the window is in the file (GF-2.0: centred, v = 0)
        for lay in ("WINDOW", "GLASS_REF"):
            for e in doc.modelspace():
                if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == lay:
                    pts = [(p[0], p[1]) for p in e.get_points("xy")]
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    if abs((max(xs) - min(xs)) - G.window.w) < TOL:
                        r["window_centre_v"] = round((max(ys) + min(ys)) / 2, 4)
        r["ok"] = r["abs_left_at_front_right"] and r["bottom_edge_at_front_bottom"] and r["same_as_transform"] and \
            r.get("orientation_F_reads_correctly", True) and \
            ("window_centre_v" not in r or abs(r["window_centre_v"] - G.window.c[1]) < TOL)
        ok &= r["ok"]
        rows[name] = r
    # side-land asymmetry in the bonding DXF: the narrower side land (abs left, 10.61) must sit at u > 0; the
    # bend-gap slot (tail side) at v < 0
    doc = ezdxf.readfile(os.path.join(OUT_DIR, "GF_BondingAids.dxf"))
    lt = _texts(doc, "LAND ")
    L = G.lands()
    narrow = min(L["front-view right (abs left)"], L["front-view left (abs right)"])
    land_ok = any(("abs left" in a) and x > 0 and ("%.2f" % narrow) in a for a, x, y in lt)
    sl = [p for p in dxf_inventory(os.path.join(OUT_DIR, "GF_BondingAids.dxf"))["polys"].get("BEND_SLOT", [])]
    slot_ok = len(sl) == 1 and max(v[1] for v in sl[0]["v"]) < 0
    rows["GF_BondingAids.dxf land asymmetry"] = {"texts": [[a, round(x, 3), round(y, 3)] for a, x, y in lt],
                                                 "narrow_side_land_abs_left_at_u>0": land_ok,
                                                 "bend_gap_slot_at_v<0": slot_ok}
    ok &= land_ok and slot_ok
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
    """status of the earlier findings + the inconsistencies between params, STEP, design document and drawings that
    the GF-2.0 drawings had to work around"""
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
    s8 = P.raw["sheet_variants"]["S8_withdrawn"]
    f.append({"id": "M3", "status": "superseded at GF-2.0", "topic": "S8 gasket / shim",
              "detail": "S8 %s; GF-D02 removed from drawings/ (kept in archive/GF-1.1/drawings); no S8 gasket or "
                        "F5-F8 shim on any GF-2.0 sheet." % s8["value"]})
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
    ba = P.val("bead", "bead_area")
    f.append({"id": "M7", "status": "consistent at GF-2.0" if abs(ba - G.bead_cl.perimeter() * G.bead_w) < 0.1
              else "OPEN", "topic": "bead area",
              "detail": "master bead.bead_area %s mm2 vs centre-line x width %.1f mm2 (glass-relative bead band)." % (
                  ba, G.bead_cl.perimeter() * G.bead_w)})
    gR, _, _, gRt = P.onesided("drawing_tolerances.glass", "corner_R")
    cR, _, _, cRt = P.onesided("drawing_tolerances.sheet", "cut_out_corner_R")
    f.append({"id": "N1", "status": "resolved in GF-1.1 round 3", "topic": "corner-radius tolerances",
              "detail": "glass R%s %s (GF-D10), cut-out R%s %s (GF-D01 / GF-D03), both one-sided, read from the "
                        "master." % (gR, gRt, cR, cRt)})
    stale = [k for k, v in G.consistency()["fasteners_uv_and_cut_distance"]["rows"].items()
             if v["master_d_cut_stale"]]
    f.append({"id": "N2", "status": "consistent at GF-2.0" if not stale else "OPEN - params stale",
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
    f.append({"id": "N5", "status": "resolved in GF-1.1 round 3", "topic": "lip venting vs exclusion zone",
              "detail": "drawing_tolerances.frame.vent_witness_lip_top %s + cad_rules entry; GF-D50 note 10 cites "
                        "them." % P.val("drawing_tolerances.frame", "vent_witness_lip_top")})
    env = (P.num("fasteners.hardware", r"must lie within dia ([\d.]+) x ([\d.]+) high", 1, name="stud"),
           P.num("fasteners.hardware", r"must lie within dia ([\d.]+) x ([\d.]+) high", 2, name="stud"))
    spt = P.item("drawing_tolerances.sheet", "stud_position_tol")
    f.append({"id": "R3-2", "status": ("resolved in GF-1.1 round 4" if "REQUIREMENT" in spt["note"] else "OPEN"),
              "topic": "stud envelope and position wording",
              "detail": "stud note: flange within dia %s x %s high; stud_position_tol %s ('%s'); GF-D01 states the "
                        "requirement once and the template as the recommended means." % (
                            env[0], env[1], spt["value"], spt["note"][:80])})
    ot = P.item("drawing_tolerances.glass", "outline_tol")
    f.append({"id": "R3-3", "status": "resolved in GF-1.1 round 4", "topic": "glass outline",
              "detail": "outline_tol %s ('%s'); GF-D10 requests it and names the fallback." % (ot["value"],
                                                                                              ot["note"][:90])})
    f.append({"id": "R4-1", "status": "drawing adds the lead's second clause", "topic": "shim rule",
              "detail": "master shim_rule '%s'; the drawings add '%s' (lead round-3 addition A wording)." % (
                  P.val("jig_and_mounting_shims", "shim_rule"), C("shim_rule")["en_extra"])})
    f.append({"id": "R4-2", "status": "applied (GF-D50 note 2)", "topic": "UL card thickness",
              "detail": "material.UL_card: '%s'." % P.val("material", "UL_card")})
    ga = C("gap_acceptance")
    f.append({"id": "R3-4", "status": "lead values used; design document differs", "topic": "gap acceptance",
              "detail": "drawn: g2 sides %s, g1 sides %s, corners '%s' at %d C (rule unchanged at GF-2.0). Design "
                        "document sec. 9 inspection table: g2 0.30-0.50 with a +-0.1 glass (0.20-0.60 at +-0.2; "
                        "opposite sides within 0.10), g1 0.25-0.55, corners 0.30-0.80." % (
                            ga["g2_sides"], ga["g1_sides"], ga["corners"]["en"], ga["temp_C"])})
    # ---- GF-2.1 (border 19.0, g_bend 3.23); every value read from the master; a wording the checks cannot parse is a
    # FAIL, never an ok
    rv = P.revision
    pk_note = P.item("plan_rectangles", "pocket")["note"]
    m = re.search(r"Where the land ends \(Z_LAND \+ ([\d.]+)\) the bead-to-pocket margins are .*?abs left ([\d.]+), "
                  r"abs right ([\d.]+), top ([\d.]+), bottom outside the tail span ([\d.]+)", pk_note)
    dr = (P.level("Z_SEAT") - P.level("Z_LAND")) * math.tan(math.radians(P.val("carried_over_from_v2", "draft")))
    lands_m = {it["name"]: it["bead_to_pocket"] for it in P.raw["lands"]}
    calc = [lands_m["abs left (front-view right)"] - dr, lands_m["abs right (front-view left)"] - dr,
            lands_m["top"] - dr, lands_m[G.LAND_KEYS["bottom outside the tail span"]] - dr]
    bm = G.bridge_bead_margins()           # raises if the bridge values and the land / break geometry disagree
    if not m:
        st1, got = "FAIL - plan_rectangles.pocket note not parsed (wording changed)", None
    else:
        got = [float(m.group(i)) for i in range(2, 6)]
        st1 = ("consistent" if all(abs(round(c, 2) - g_) < 0.006 for c, g_ in zip(calc, got))
               else "OPEN - pocket note differs from the lands table and the draft")
    f.append({"id": "G21-1", "status": st1, "topic": "at-land bead -> pocket values in the plan_rectangles.pocket note",
              "detail": "note (where the land ends, Z_LAND + %s): %s; from the lands table and the 1 deg draft: abs left "
                        "%.2f, abs right %.2f, top %.2f, bottom outside the span %.2f; over the bridge %s to the break "
                        "edge and %s to the face plane. GF-D20 prints them; make_bonding.py stops on a mismatch." % (
                            bm["z_end"], got, calc[0], calc[1], calc[2], calc[3], bm["to_break_edge"],
                            bm["to_face_plane"])})
    lz = G.logo
    req_g = P.num("logo_zone", r">= ([\d.]+) from the glass edge", name="logo_h")
    req_w = P.num("logo_zone", r">= ([\d.]+) from the window", name="logo_h")
    lz_ok = G.window.y0 - lz.y1 >= req_w - 1e-6 and lz.y0 - G.glass.y0 >= req_g - 1e-6
    f.append({"id": "G21-2", "status": "consistent" if lz_ok else "OPEN - logo zone violates its own clearance rule",
              "topic": "logo zone position vs its rule",
              "detail": "logo_centre abs y %s: %s x %s zone, %.2f from the window (rule >= %s) and %.2f from the glass "
                        "edge (rule >= %s). GF-D10 (note 11, plan), the GF-D11 artwork and GF-D40 draw it." % (
                            P.val("logo_zone", "logo_centre")[1], lz.w, lz.h, G.window.y0 - lz.y1, req_w,
                            lz.y0 - G.glass.y0, req_g)})
    gt = gap_temperatures(P)               # raises if a value or the word 'verified' is missing from the gaps notes
    g2n = P.item("gaps", "g2_glass_lip")["note"]
    f.append({"id": "G21-3", "status": ("verified %s values in the master" % rv) if ("%s over temperature" % rv) in g2n
              else "FAIL - gaps notes do not state the %s values" % rv, "topic": "gaps over temperature",
              "detail": "g2 glass-lip 20 C %s / %s (sides / corner), -20 C %s / %s, +70 C %s / %s (50 / 70 ppm), touch "
                        "%s at WC; g1 lip-sheet 20 C %s / %s, hot %s / %s, -20 C %s / %s, touch %s at WC. GF-D20 "
                        "(acceptance text) and GF-D40 (note 2) print them." % (
                            gt["g2_20C_sides"], gt["g2_20C_corner"], gt["g2_cold_50"], gt["g2_cold_70"],
                            gt["g2_hot_50"], gt["g2_hot_70"], gt["g2_touch_wc"], gt["g1_20C_sides"],
                            gt["g1_20C_corner"], gt["g1_hot_50"], gt["g1_hot_70"], gt["g1_cold_50"],
                            gt["g1_cold_70"], gt["g1_touch_wc"])})
    ft = P._use("fold_test", P.raw["fold_test"])
    f.append({"id": "G21-4", "status": "assumption gated by GF-D21", "topic": "tail bend assumptions",
              "detail": "tail_straight_l0 %s, tail_R_in_min %s, tail_t %s (assumed tail %s, single layer) and the exit "
                        "heights are assumptions / estimates; border %s holds while the needed gap <= %s (master "
                        "fold_test). The master gives no double-sided figures: GF-D21 criterion 5 states 'single "
                        "layer as assumed', anything else goes through the fold_test fail branch." % (
                            P.d("tail_straight_l0"), P.d("tail_R_in_min"), P.d("tail_t"), ft["assumed_tail_mm"],
                            P.d("border"), ft["border_limit_needed_gap_mm"])})
    of = P._use("open_findings", P.raw["open_findings"])
    f1, f2 = of["1_bend_zone_clearance_worst_case"], of["2_bead_to_land_break"]
    closed = f1["status"].startswith("CLOSED at %s" % rv) and f2["status"].startswith("CLOSED at %s" % rv)
    f.append({"id": "G21-5", "status": "closed in the master" if closed else "FAIL - finding status not closed",
              "topic": "GF-2.0 findings 1 (bend zone) and 2 (bead to the land break)",
              "detail": "1: %s - CTP full worst case %s (TFT %s). 2: %s - %s. No sheet says a finding is open; GF-D20 "
                        "keeps the squeeze-out check as a required check." % (
                            f1["status"].split(" - ")[0], f1["measured_GF-2.1_mm"]["CTP"]["full_WC"],
                            f1["measured_GF-2.1_mm"]["TFT"]["full_WC"], f2["status"].split(" - ")[0],
                            f2["result"])})
    try:
        be = G.break_edge_notes()
        st6 = "consistent" if be["ok"] else "OPEN - land notes differ from the geometry"
        d6 = ("land_break and lands['%s'] notes: %s measured where the land ends (Z_LAND + %s; calc %s, = pocket note), "
              "%s on the land plane (calc %s = A1 value quoted on GF-D20 / GF-D50), %s to the face plane (calc %s); "
              "checks %s." % (G.LAND_KEYS["bottom over the tail span"], n2s(be["measured"]), be["z_end"],
                              be["calc_measured"], n2s(be["land_plane"]), be["calc_land_plane"],
                              n2s(be["face_plane"]), be["calc_face_plane"], be["checks"]))
    except AssertionError as e:
        st6, d6 = "FAIL - land notes not parsed (wording changed)", str(e)[:300]
    f.append({"id": "G21-6", "status": st6, "topic": "bead -> break edge in the land_break and lands notes",
              "detail": d6})
    g_old = P.change("driving_parameters.g_bend.value")[0]
    f.append({"id": "G21-7", "status": "used (master fold_test)", "topic": "fold-test pass rule (GF-D21)",
              "detail": "slot %s (the GF-2.0 gauge, slot %.2f, is not valid - stated on GF-D21), feeler %s, tail outer "
                        "surface within %s, exact feeler %s, needed gap at the line %s, reserves %s to g_bend / %s to "
                        "the limit %s, assumed tail %s; make_tailgauge.py checks every number against the budget." % (
                            ft["gauge_slot_mm"], g_old, ft["feeler_mm"],
                            ft["tail_outer_surface_limit_from_panel_edge_mm"], ft["exact_feeler_for_the_budget_mm"],
                            ft["needed_gap_at_the_limit_mm"], ft["reserve_to_g_bend_mm"],
                            round(ft["border_limit_needed_gap_mm"] - ft["needed_gap_at_the_limit_mm"], 3),
                            ft["border_limit_needed_gap_mm"], ft["assumed_tail_mm"])})
    f.append({"id": "G21-8", "status": "stated on the sheets", "topic": "thin margins (open_findings.margins_note)",
              "detail": "%s GF-D21 prints the CTP full-worst-case margin and that passing the gauge guarantees the RSS "
                        "criterion, not the 0.45 full-worst-case intent; GF-D20 / GF-D50 print the bead -> break edge "
                        "on the land plane." % P._use("open_findings.margins_note_GF-2.1",
                                                      of["margins_note_GF-2.1"])})
    rules = P.get("cad_rules")
    so = [r for r in rules if "shut-off A/B is NOT a flat face" in r]
    m_w = re.search(r"top of the land break \(y ([\d.]+),.*?shelf corner \(y ([\d.]+),.*?over the ([\d.]+) slot width",
                    so[0]) if len(so) == 1 else None
    f.append({"id": "G21-9", "status": "explained on GF-D50 note 4" if m_w else "FAIL - shut-off rule not parsed",
              "topic": "slot width at the break top vs the plan slot",
              "detail": "cad_rules shut-off: %s wide at the break top (y %s - %s); plan slot / g_bend %s at Z_LAND; the "
                        "difference is the 1 deg draft over the 0.3 break - both are right." % (
                            m_w.group(3) if m_w else "-", m_w.group(1) if m_w else "-",
                            m_w.group(2) if m_w else "-", P.d("g_bend"))})
    lbt = C("frame_land_break_tol")
    f.append({"id": "G21-10", "status": "drafter's proposal for the owner", "topic": "land-break tolerance",
              "detail": "GF-D50 CTF 16 / detail Y: break 0.3 +%s / -%s [P] (drafting_choices frame_land_break_tol): "
                        "with the bead 1.06 from the break edge, +%s keeps >= %.2f; +-0.1 would allow %.2f." % (
                            lbt[0], lbt[1], lbt[0], 1.06 - lbt[0], 1.06 - 0.1)})
    tbr = P._use("to_be_reverified_at_%s" % rv, P.raw["to_be_reverified_at_%s" % rv])
    f.append({"id": "G21-11", "status": "addressed by this drawing set", "topic": "master re-verification list",
              "detail": "items naming the drawings: %s" % [t[:200] for t in tbr if "drawings" in t]})
    return f


def run(G=None, P=None, C=None):
    P = P or Params()
    C = C or Choices()
    G = G or Geom(P)
    dx = dxf_checks(G, P, C)
    out = {"dxf": dx, "dxf_all_ok": all(v["ok"] for v in dx.values()),
           "geometry": geometry_checks(G, P, C), "mirroring": mirror_checks(G, P, dx), "pdf": pdf_checks(),
           "master_findings": master_findings(G, P, C)}
    out["master_findings_parsed_ok"] = not any(f_["status"].startswith("FAIL") for f_ in out["master_findings"])
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
