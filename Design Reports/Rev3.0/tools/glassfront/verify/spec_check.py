"""A. The frame STEP against the frozen specification (GF-1.0 params), measured on the STEP only.

  <venv>\\Scripts\\python.exe spec_check.py [--frame f.step] [--params p.json]

Every row: item, where, measured, required, diff, tolerance, verdict, note. Tolerance 0.01 mm (0.05 deg for
angles); where draft moves a face away from the nominal line, the face is measured at two or more heights, a line
s(Z) is fitted (slope = draft) and the value at the reference plane of the specification is compared - the note
names that plane. Output: the "spec" block of out/cadcheck.json (written by run_verify / cadcheck).
"""
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import vcommon as C

TOL = 0.01
TOL_DEG = 0.05
T1 = math.tan(math.radians(1.0))


class Rows:
    def __init__(self):
        self.rows = []

    def add(self, group, item, where, measured, required, tol=TOL, note="", info=False, ok=None):
        diff = None
        if isinstance(measured, (int, float)) and isinstance(required, (int, float)):
            diff = float(measured) - float(required)
            if ok is None:
                ok = abs(diff) <= tol + 1e-9
        v = "INFO" if info else ("PASS" if ok else "FAIL")
        self.rows.append({"group": group, "item": item, "where": where,
                          "measured": round(measured, 4) if isinstance(measured, float) else measured,
                          "required": round(required, 4) if isinstance(required, float) else required,
                          "diff": None if diff is None else round(diff, 4), "tol": tol, "verdict": v, "note": note})
        return v


# ----------------------------------------------------------------------------------------------- body
def body(R, ctx):
    G, fi = ctx.G, ctx.frame_info
    R.add("body", "solids in the STEP", "file", fi["solids"], 1, tol=0, note="declared unit %s, read in mm" % fi["declared_unit"])
    R.add("body", "B-rep valid (BRepCheck)", "file", "valid" if fi["valid"] else "INVALID", "valid", ok=fi["valid"])
    fx0, fx1, fy0, fy1, _ = G.FLANGE
    b = fi["bbox_abs"]
    for lab, m, r in (("bbox x min", b["x"][0], fx0), ("bbox x max", b["x"][1], fx1), ("bbox y min (abs)", b["y_down"][0], fy0),
                      ("bbox y max (abs)", b["y_down"][1], fy1), ("bbox Z min = lip top", b["z"][0], G.L["Z_GLASS_FRONT"]),
                      ("bbox Z max = trough top", b["z"][1], G.L["Z_TROUGH_TOP"])):
        R.add("body", lab, "STEP bbox", m, r)
    R.add("body", "volume", "STEP", fi["volume_mm3"] / 1000.0, "~70 (concept estimate)", info=True,
          note="cm3; mass at 1.36 g/cm3 = %.1f g (concept: ~70 cm3 / 95 g, v2 55.06 cm3)" % (fi["volume_mm3"] / 1000 * 1.36))


# ----------------------------------------------------------------------------------------------- Z levels
LEVELS = [  # name, level key, normal sign, expected count (None = any), what
    ("lip top (flush plane)", "Z_GLASS_FRONT", -1, 1, "lip"),
    ("sheet-seat ring + corner pads (hard stops)", "Z_SHEET_BACK", -1, 5, "ring + F1-F4 pads"),
    ("flange front (tape face, parting line)", "Z_FLANGE_FRONT", -1, 1, "flange"),
    ("pip tops", "Z_PIP_TOP", -1, 8, "8 pips"),
    ("land (recess floor, bead face)", "Z_LAND", -1, 1, "land"),
    ("flange back", "Z_FLANGE_BACK", +1, 1, "flange back"),
    ("land-plate back / step-wall back", "Z_LANDPLATE_BACK", +1, None, "land plate, cells"),
    ("fastener tube tops (washer seat)", "Z_TUBE_TOP", +1, 8, "F1-F8"),
    ("shelf front = Formex seat", "Z_SEAT", -1, 1, "shelf"),
    ("shelf back", "Z_SHELF_BACK", +1, None, "shelf between ribs"),
    ("PCB plane (boss / rib / wall tops)", "Z_PCB", +1, None, "contact faces"),
    ("tail-pocket wall / beam top", "Z_TROUGH_TOP", +1, 1, "trough"),
]


def z_levels(R, ctx):
    G, fr = ctx.G, ctx.frame
    groups = {}
    for f in fr.Faces():
        if not C.is_plane_z(f):
            continue
        s = 1 if f.normalAt().z > 0 else -1
        bb = f.BoundingBox()
        groups.setdefault((round((bb.zmin + bb.zmax) / 2, 3), s), []).append(f)
    used = set()
    found = []
    for name, key, sg, n_exp, what in LEVELS:
        z = G.L[key]
        if key == "Z_TUBE_TOP" and G.core:
            n_exp = 16          # GF-1.1: each tube top split by the coring groove into seat + outer skin
        if key == "Z_FLANGE_BACK" and G.core:
            n_exp = None        # GF-1.1: count reported, judged in the fastener rows (tube-base fillets)
        hit = [(k, fs) for k, fs in groups.items() if k[1] == sg and abs(k[0] - z) < 0.02]
        if not hit:
            R.add("Z levels", name, key, "no face", z, ok=False, note="no planar %s face at Z %.3f" % ("+Z" if sg > 0 else "-Z", z))
            continue
        fs = [f for k, f_ in hit for f in f_]
        for k, _ in hit:
            used.add(k)
        zs = [f.BoundingBox().zmin for f in fs] + [f.BoundingBox().zmax for f in fs]
        zm = max(zs, key=lambda q: abs(q - z))
        area = sum(f.Area() for f in fs)
        note = "%d face(s), %.1f mm2" % (len(fs), area)
        if n_exp is not None and len(fs) != n_exp:
            note += "; expected %d" % n_exp
        R.add("Z levels", name, key, zm, z, note=note)
        found.append({"name": name, "key": key, "z_spec": z, "z_worst": zm, "faces": len(fs), "area_mm2": round(area, 2),
                      "count_ok": n_exp is None or len(fs) == n_exp})
        if n_exp is not None and len(fs) != n_exp:
            R.add("Z levels", name + " - face count", key, len(fs), n_exp, tol=0)
    extra = []
    for k, fs in sorted(groups.items()):
        if k in used:
            continue
        bb = [f.BoundingBox() for f in fs]
        extra.append({"z": k[0], "normal": "+Z" if k[1] > 0 else "-Z", "faces": len(fs),
                      "area_mm2": round(sum(f.Area() for f in fs), 2),
                      "first_bbox_abs": [round(bb[0].xmin, 2), round(bb[0].xmax, 2), round(-bb[0].ymax, 2), round(-bb[0].ymin, 2)]})
    # explain the extra levels from carried-over v2 rules
    L = G.L
    known = {round(L["Z_LAND"] + G.PILOT_FLOOR, 3): "PCB pilot floors = Z_LAND + pilot_floor (blind pilots, v2 rule, 1.0 above the front face)",
             round(L["Z_PCB"] - G.CBORE_H, 3): "pilot mouth relief floors = Z_PCB - cbore_h (v2)",
             round(L["Z_LAND"] + G.CELL_RIB_H, 3): "corner-cell rib tops = Z_LAND + cell_rib_h (v2 rule 'rib top 5.0 above the front face')"}
    if G.cb:
        known[round(G.cb_floor_z("F1"), 3)] = "F1-F4 counterbore floors = Z_SHEET_BACK + cb_floor_F1-F4 (GF-1.1), 4 expected"
        known[round(G.cb_floor_z("F5"), 3)] = "F5-F8 counterbore floors = Z_SHEET_BACK + cb_floor_F5-F8 (GF-1.1), 4 expected"
    if G.core:
        known[round(L["Z_TUBE_TOP"] - float(G.core["core_depth"]), 3)] = "tube coring groove floors = Z_TUBE_TOP - core_depth (GF-1.1), 8 expected"
    for e in extra:
        e["explained_by"] = known.get(round(e["z"], 3), "NOT in the specification")
        R.add("Z levels", "extra level Z %.3f (%s, %d faces)" % (e["z"], e["normal"], e["faces"]), "STEP", e["z"],
              e["explained_by"], info=True)
    return {"levels": found, "extra_levels": extra}


# ----------------------------------------------------------------------------------------------- edge profiles
EDGE_PROBES = {"top": (80.0, 130.0), "bottom": (80.0, 130.0), "left": (60.0, 105.0), "right": (60.0, 105.0)}


def _face_line(P, G, edge, along, zs, pick):
    """s of one face at several Z (pick(intervals) -> s or None) and the fitted line s = a + b Z"""
    pts = []
    for z in zs:
        iv = P.s_boundaries(edge, along, z, -40, 40, G)
        s = pick(iv)
        if s is not None:
            pts.append((z, s))
    if len(pts) < 2:
        return None
    Z = np.array([p[0] for p in pts]); S = np.array([p[1] for p in pts])
    b, a = np.polyfit(Z, S, 1)
    res = float(np.max(np.abs(a + b * Z - S)))
    return {"a": a, "b": b, "deg": math.degrees(math.atan(abs(b))), "pts": pts, "fit_resid": res,
            "at": lambda z: a + b * z}


def edge_profiles(R, ctx, P):
    G = ctx.G
    L = G.L
    zg, zsb, zff, zfb, zl, zlb, zs = (L["Z_GLASS_FRONT"], L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"], L["Z_FLANGE_BACK"],
                                      L["Z_LAND"], L["Z_LANDPLATE_BACK"], L["Z_SEAT"])
    # nominal s of the pocket face per edge (pocket rect vs glass rect)
    gx0, gx1, gy0, gy1 = G.GLASS[:4]
    px0, px1, py0, py1 = G.POCKET[:4]
    pocket_s = {"top": gy0 - py0, "bottom": py1 - gy1, "left": gx0 - px0, "right": px1 - gx1}
    tail_s = G.TAIL[3] - gy1
    out = {}
    for edge, alongs in EDGE_PROBES.items():
        for along in alongs:
            w = "%s edge, %s %.1f" % (edge, "x" if edge in ("top", "bottom") else "y", along)
            row = {}
            # recess wall / lip inner face: first interval's start, Z between the lip-top round and the land round
            f_in = _face_line(P, G, edge, along, [zg + 0.35, zg + 0.6, zsb - 0.05, zsb + 0.5, zff + 0.5, zl - 0.6],
                              lambda iv: iv[0][0] if iv and iv[0][0] > -1 else None)
            f_out = _face_line(P, G, edge, along, [zg + 0.35, zg + 0.5, zg + 0.65, zg + 0.75],
                               lambda iv: iv[0][1] if iv and iv[0][1] < 2.0 else None)
            f_ring = _face_line(P, G, edge, along, [zsb + 0.3, zsb + 0.5, zsb + 0.75, zff - 0.05],
                                lambda iv: iv[0][1] if iv and 2.0 < iv[0][1] < 4 else None)
            f_fl = _face_line(P, G, edge, along, [zff + 0.05, zff + 0.8, zfb - 0.6, zfb - 0.05],
                              lambda iv: max(b for a, b in iv) if iv else None)
            f_sw = _face_line(P, G, edge, along, [zfb + 0.6, zfb + 1.2, zlb - 0.05],
                              lambda iv: next((b for a, b in iv if 1.5 < b < 4.0), None))
            f_pk = _face_line(P, G, edge, along, [zl + 0.05, zl + 1.5, zlb + 0.5, zs - 0.6],
                              lambda iv: next((a for a, b in iv if -15 < a < -3), None))
            row = {"recess_wall": f_in, "lip_outer": f_out, "seat_ring_outer": f_ring, "flange_edge": f_fl,
                   "stepwall_back": f_sw, "pocket_face": f_pk}
            out[w] = {k: ({"s_at_ref": None} if v is None else
                          {"fit_deg": round(v["deg"], 3), "slope_ds_dZ": round(v["b"], 5), "resid": round(v["fit_resid"], 5),
                           "points": [(round(z, 3), round(s, 4)) for z, s in v["pts"]]}) for k, v in row.items()}
            chk = [("glass-recess wall (lip inner face) at the lip top", f_in, zg, G.g2, "lip_in rect is 'at the lip top'"),
                   ("lip outer face at the lip root", f_out, zsb, G.g2 + G.lip_w, "lip_out rect; lip_w 1.0 at the root"),
                   ("sheet-seat ring outer edge at the flange front", f_ring, zff, G.g2 + G.lip_w + G.seat_ring_w,
                    "seat_ring_out rect (ring base on the flange front)"),
                   ("flange outer edge at the flange front (parting line)", f_fl, zff, G.flange_beyond_glass, "flange rect"),
                   ("step-wall back face at the flange back", f_sw, zfb, G.g2 + G.lip_w + G.seat_ring_w,
                    "step wall s 0.4..2.9 (concept 4.4)")]
            ps = pocket_s[edge] if not (edge == "bottom" and G.TAIL[0] < along < G.TAIL[1]) else tail_s
            if edge == "bottom" and G.TAIL[0] < along < G.TAIL[1]:
                chk.append(("tail-pocket bottom face at the land (front)", f_pk, zl, ps, "tail_pocket y1 147.70 at the front"))
            else:
                chk.append(("clearance-pocket face at the shelf (Z_SEAT)", f_pk, zs, ps, "pocket rect = panel + 0.8 (tightest at the shelf)"))
                if f_pk is not None:
                    R.add("plan / profiles", "clearance-pocket face at the land (Z_LAND)", w, f_pk["at"](zl), ps, info=True,
                          note="pocket widens to the front by the 1 deg draft (A-side core): +%.3f per side at the land" %
                               (f_pk["at"](zl) - ps if ps > 0 else ps - f_pk["at"](zl)))
            for item, fl, zref, nom, note in chk:
                if fl is None:
                    R.add("plan / profiles", item, w, "not found", nom, ok=False)
                    continue
                m = fl["at"](zref)
                v = R.add("plan / profiles", item, w, m, nom,
                          note="%s; fitted draft %.2f deg over %d heights (resid %.4f)" % (note, fl["deg"], len(fl["pts"]), fl["fit_resid"]))
                R.add("plan / profiles", item + " - draft", w, fl["deg"], 1.0, tol=TOL_DEG)
            # lip section
            if f_in and f_out:
                top_w = f_out["at"](zg) - f_in["at"](zg)
                root_w = f_out["at"](zsb) - f_in["at"](zsb)
                if G.lip_w_root_ad is not None:     # GF-1.1: as-designed widths are the specification
                    R.add("lip", "lip width at the root (Z_SHEET_BACK)", w, root_w, float(G.lip_w_root_ad),
                          note="params lip_w_root_as_designed (GF-1.1 bookkeeping); nominal lip_w %.2f" % G.lip_w)
                    R.add("lip", "lip width at the top (sharp-corner extrapolation)", w, top_w, float(G.lip_w_top_ad),
                          note="params lip_w_top_as_designed")
                else:
                    R.add("lip", "lip width at the root (Z_SHEET_BACK)", w, root_w, G.lip_w,
                          note="lip_in is placed at the top and lip_out at the root, both faces drafted 1 deg -> root %.3f, top %.3f "
                               "(concept 4.4: 1.00 root / 0.97 top)" % (root_w, top_w))
                    R.add("lip", "lip width at the top (sharp-corner extrapolation)", w, top_w, G.lip_w - 2 * T1 * G.t_sheet,
                          info=True, note="concept: top 0.97 (1.00 - 2 x 1 deg x 1.0); follows from the root row")
                g1ad = G.gaps.get("g1_at_front_as_designed", {}).get("value")
                R.add("lip", "visible g1 at the flush plane (cut-out edge s %.2f - lip outer at the top)" % (G.g2 + G.lip_w + G.g1),
                      w, (G.g2 + G.lip_w + G.g1) - f_out["at"](zg), float(g1ad) if g1ad else G.g1, info=g1ad is None,
                      note="straight edges; params g1_at_front_as_designed" if g1ad else
                      "the cut-out edge meets the lip near its root; the visible line at the front face is this wide")
    return out


# ----------------------------------------------------------------------------------------------- lip details
def lip_details(R, ctx, P):
    G, fr = ctx.G, ctx.frame
    L = G.L
    zg, zsb = L["Z_GLASS_FRONT"], L["Z_SHEET_BACK"]
    # lip height: vertical probes at the lip centre line (s = 0.9) on each edge
    hs = []
    for edge, alongs in EDGE_PROBES.items():
        for along in alongs:
            gx0, gx1, gy0, gy1 = G.GLASS[:4]
            s = G.g2 + G.lip_w / 2
            x, y = {"top": (along, gy0 - s), "bottom": (along, gy1 + s), "left": (gx0 - s, along), "right": (gx1 + s, along)}[edge]
            iv = P.z_intervals(x, y)
            ring_s = G.g2 + G.lip_w + G.seat_ring_w / 2
            x2, y2 = {"top": (along, gy0 - ring_s), "bottom": (along, gy1 + ring_s), "left": (gx0 - ring_s, along),
                      "right": (gx1 + ring_s, along)}[edge]
            iv2 = P.z_intervals(x2, y2)
            if iv and iv2:
                hs.append(iv2[0][0] - iv[0][0])
                R.add("lip", "lip height above the seat ring", "%s %.0f" % (edge, along), iv2[0][0] - iv[0][0], G.t_sheet)
    # flat width of the lip top = 2 A / P of the planar lip-top face (a thin closed band)
    flats = []
    for f in C.faces_at_z(fr, zg, -1, tol=0.005):
        per = sum(e.Length() for e in f.Edges())
        flats.append(2 * f.Area() / per)
    if flats:
        R.add("lip", "lip-top flat width (2A/P of the lip-top face)", "lip top face", min(flats), "0.37 (concept: R0.3 both edges)",
              info=True, note="flat = top width 0.98 minus the two R0.3 rounds on 1-deg walls")
    # edge radii: curved faces in the lip zone
    radii = {"top edge rounds": [], "lip root (outer)": [], "recess wall -> land": [], "lip inner root": []}
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    for f in fr.Faces():
        gt = f.geomType()
        if gt not in ("CYLINDER", "TORUS"):
            continue
        bb = f.BoundingBox()
        ad = BRepAdaptor_Surface(f.wrapped)
        r = ad.Cylinder().Radius() if gt == "CYLINDER" else ad.Torus().MinorRadius()
        if gt == "CYLINDER" and abs(ad.Cylinder().Axis().Direction().Z()) > 0.5:
            continue
        if bb.zmin > zg - 0.01 and bb.zmax < zg + 0.45:
            radii["top edge rounds"].append(r)
        elif bb.zmin > zsb - 0.4 and bb.zmax < zsb + 0.01 and r < 0.6:
            radii["lip root (outer)"].append(r)
        elif bb.zmin > L["Z_LAND"] - 0.7 and bb.zmax < L["Z_LAND"] + 0.01 and r < 1.0:
            radii["recess wall -> land"].append(r)
    for k, v in radii.items():
        if v:
            R.add("lip", "edge radius: " + k, "%d faces" % len(v), float(np.median(v)),
                  {"top edge rounds": "R0.3", "lip root (outer)": "R0.2", "recess wall -> land": "not specified"}.get(k, "-"),
                  info=k not in ("top edge rounds", "lip root (outer)"), ok=(abs(np.median(v) - {"top edge rounds": 0.3,
                                                                                                     "lip root (outer)": 0.2}.get(k, 0)) < 0.011) if k in ("top edge rounds", "lip root (outer)") else None,
                  note="radii found %s" % sorted(set(round(x, 3) for x in v)))
        elif k in ("top edge rounds", "lip root (outer)"):
            R.add("lip", "edge radius: " + k, "-", "none found", {"top edge rounds": "R0.3", "lip root (outer)": "R0.2"}[k], ok=False)
    return {"heights": hs, "flats": flats, "radii": {k: sorted(set(round(x, 3) for x in v)) for k, v in radii.items()}}


# ----------------------------------------------------------------------------------------------- plan rounded rects
def plan_rects(R, ctx):
    G, fr = ctx.G, ctx.frame
    L = G.L
    out = {}
    jobs = [  # name, Z, loop selector, nominal rect, drift per side at that Z (+ = rect grows), corner centres = glass corners
        ("glass recess (lip inner) loop", L["Z_GLASS_FRONT"] + 0.42, "inner_largest", G.LIP_IN, -T1 * 0.42,
         "lip_in at the lip top; the wall narrows 1 deg to the back"),
        ("lip outer loop", L["Z_GLASS_FRONT"] + 0.42, "outer_of_lip", G.LIP_OUT, -T1 * (L["Z_SHEET_BACK"] - L["Z_GLASS_FRONT"] - 0.42),
         "lip_out at the root; the lip narrows 1 deg to the top"),
        ("sheet-seat ring outer loop", L["Z_SHEET_BACK"] + 0.5, "ring_outer", G.SEAT_OUT, -T1 * 0.5,
         "seat_ring_out at its base (flange front)"),
        ("flange outline", L["Z_FLANGE_FRONT"] + 0.005, "outer_largest", G.FLANGE, -T1 * 0.005,
         "flange at the parting line, R10 centred on F1-F4"),
        ("clearance pocket (+ tail pocket)", L["Z_SEAT"] - 0.6, "inner_largest", G.POCKET, T1 * 0.6,
         "pocket at the shelf; 1 deg wider to the front"),
    ]
    for name, z, sel, nom, drift, note in jobs:
        loops = C.plan_loops(fr, z)
        if not loops:
            R.add("plan rects", name, "Z %.3f" % z, "no section", "-", ok=False)
            continue
        if sel == "outer_largest":
            cand = [l for l in loops if l["outer"]]
            lp = max(cand, key=lambda l: np.ptp(l["pts"][:, 0]) * np.ptp(l["pts"][:, 1]))
        elif sel == "inner_largest":
            cand = [l for l in loops if not l["outer"]]
            lp = max(cand, key=lambda l: np.ptp(l["pts"][:, 0]) * np.ptp(l["pts"][:, 1]))
        elif sel == "outer_of_lip":
            cand = [l for l in loops if l["outer"]]
            lp = max(cand, key=lambda l: np.ptp(l["pts"][:, 0]) * np.ptp(l["pts"][:, 1]))
        elif sel == "ring_outer":
            cand = [l for l in loops if l["outer"]]
            lp = max(cand, key=lambda l: np.ptp(l["pts"][:, 0]) * np.ptp(l["pts"][:, 1]))
        x0, x1, y0, y1, Rn = nom
        ex = (x0 - drift, x1 + drift, y0 - drift, y1 + drift, (Rn or 0) + drift)
        fit = C.rrect_fit(lp["pts"], (x0, x1, y0, y1, Rn))
        sub = {"z": z, "expected_at_z": [round(v, 4) for v in ex], "measured": {k: round(v, 4) for k, v in fit.items() if k != "corners"},
               "corners": {k: {kk: round(vv, 4) for kk, vv in c.items()} for k, c in fit["corners"].items()}}
        out[name] = sub
        if name.startswith("clearance pocket"):
            for k, m, e in (("x0", fit["x0"], ex[0]), ("x1", fit["x1"], ex[1]), ("y0", fit["y0"], ex[2])):
                R.add("plan rects", "%s %s" % (name, k), "Z %.2f" % z, m, e, note=note)
        else:
            for k, m, e in (("x0", fit["x0"], ex[0]), ("x1", fit["x1"], ex[1]), ("y0", fit["y0"], ex[2]), ("y1", fit["y1"], ex[3])):
                R.add("plan rects", "%s %s" % (name, k), "Z %.3f" % z, m, e, note=note)
        if Rn:
            for cn, c in fit["corners"].items():
                ccx = {"TL": x0 + Rn, "TR": x1 - Rn, "BR": x1 - Rn, "BL": x0 + Rn}[cn]
                ccy = {"TL": y0 + Rn, "TR": y0 + Rn, "BR": y1 - Rn, "BL": y1 - Rn}[cn]
                if name.startswith("clearance pocket") and cn in ("BR", "BL"):
                    pass
                R.add("plan rects", "%s corner %s radius" % (name, cn), "Z %.3f" % z, c["R"], ex[4],
                      tol=0.02, note="centre (%.3f, %.3f) vs (%.3f, %.3f), fit rms %.4f" % (c["cx"], c["cy"], ccx, ccy, c["rms"]))
                R.add("plan rects", "%s corner %s centre offset" % (name, cn), "Z %.3f" % z,
                      math.hypot(c["cx"] - ccx, c["cy"] - ccy), 0.0, tol=0.02)
    # tail pocket corners (R1.5 at the bottom, at the front face)
    zt = L["Z_LAND"] + 0.05
    loops = C.plan_loops(fr, zt)
    tx0, tx1, ty0, ty1, tr = G.TAIL
    for lp in loops:
        P_ = lp["pts"]
        for cn, (cx, cy) in (("left", (tx0 + tr, ty1 - tr)), ("right", (tx1 - tr, ty1 - tr))):
            d = np.hypot(P_[:, 0] - cx, P_[:, 1] - cy)
            sel = P_[(np.abs(d - tr) < 0.6) & (P_[:, 1] > cy + 0.2) & ((P_[:, 0] - cx) * (-1 if cn == "left" else 1) > 0.2)]
            if len(sel) >= 6:
                fx, fy, fr_, rms = C.fit_circle(sel)
                exp = tr + T1 * 0.05
                R.add("plan rects", "tail-pocket bottom corner %s radius" % cn, "Z %.2f" % zt, fr_, tr, tol=0.02,
                      note="centre (%.3f, %.3f) vs (%.3f, %.3f); trough_R 1.5" % (fx, fy, cx, cy))
                out["tail corner " + cn] = {"cx": fx, "cy": fy, "R": fr_}
    # tail pocket x limits at the front
    P = C.Probe(fr)
    iv = P.x_intervals(140.0, zt)
    gaps = [(b1, a2) for (a1, b1), (a2, b2) in zip(iv[:-1], iv[1:]) if a2 - b1 > 50]
    if gaps:
        R.add("plan rects", "tail pocket x0 at the front (y 140)", "Z %.2f" % zt, gaps[0][0], tx0, note="v2 tr_x0")
        R.add("plan rects", "tail pocket x1 at the front (y 140)", "Z %.2f" % zt, gaps[0][1], tx1, note="v2 tr_x1")
    return out


# ----------------------------------------------------------------------------------------------- axial features
def axial(fr):
    rows = []
    for f in fr.Faces():
        a = C.axis_z_feature(f)
        if a:
            gt, cx, cy, r, z0, z1, ang, drdz = a
            rows.append({"kind": gt, "x": cx, "y": -cy, "r_mid": r, "z0": z0, "z1": z1, "semi": ang, "drdz": drdz, "face": f})
    return rows


def r_at(c, z):
    return c["r_mid"] + c["drdz"] * (z - (c["z0"] + c["z1"]) / 2)


def pips(R, ctx, ax):
    G = ctx.G
    L = G.L
    out = []
    tops = C.faces_at_z(ctx.frame, L["Z_PIP_TOP"], -1, tol=0.005)
    for n, (x, y) in sorted(G.pips.items()):
        c = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and k["r_mid"] < 1.2]
        t = [f for f in tops if math.hypot(f.Center().x - x, -f.Center().y - y) < 0.3]
        row = {"pip": n, "x": x, "y": y, "found": bool(c) and bool(t)}
        if not c:
            R.add("pips", n + " found", "(%.2f, %.2f)" % (x, y), "not found", "pip", ok=False)
            out.append(row)
            continue
        k = c[0]
        tc = t[0].Center() if t else None
        pos = math.hypot(k["x"] - x, k["y"] - y)
        R.add("pips", n + " position (axis)", "(%.2f, %.2f)" % (x, y), pos, 0.0)
        R.add("pips", n + " base dia at Z_LAND", "", 2 * r_at(k, L["Z_LAND"]), G.pip_d)
        R.add("pips", n + " height (land -> top)", "", (k["z1"] - k["z0"]), G.pip_h, note="cone face Z %.3f..%.3f" % (k["z0"], k["z1"]))
        R.add("pips", n + " draft", "", abs(k["semi"]), 1.0, tol=TOL_DEG)
        row.update({"axis": (k["x"], k["y"]), "base_dia": 2 * r_at(k, L["Z_LAND"]), "top_dia": 2 * r_at(k, L["Z_PIP_TOP"])})
        # bead centre line: 2.9 inside the glass edge
        gx0, gx1, gy0, gy1 = G.GLASS[:4]
        s_in = min(abs(x - gx0), abs(x - gx1), abs(y - gy0), abs(y - gy1))
        R.add("pips", n + " on the bead centre line (inside the glass edge)", "", s_in, G.bead_edge + G.bead_w / 2, info=True)
        out.append(row)
    return out


def fasteners(R, ctx, ax, P):
    G, fr = ctx.G, ctx.frame
    L = G.L
    gcx, gcy = G.GC
    out = []
    tube_tops = C.faces_at_z(fr, L["Z_TUBE_TOP"], +1, tol=0.005)
    pads = C.faces_at_z(fr, L["Z_SHEET_BACK"], -1, tol=0.005)
    for n in ["F%d" % i for i in range(1, 9)]:
        x, y = G.fxy(n)
        u = G.slot_axis(n)
        hl = (G.slot_l - G.slot_w) / 2
        ends = [(x - hl * u[0], y - hl * u[1]), (x + hl * u[0], y + hl * u[1])]
        found = []
        for ex, ey in ends:
            c = [k for k in ax if math.hypot(k["x"] - ex, k["y"] - ey) < 0.3 and 2.0 < k["r_mid"] < 3.5]
            found.append(c[0] if c else None)
        row = {"name": n, "x": x, "y": y}
        w = "(%.2f, %.2f)" % (x, y)
        if not all(found):
            R.add("fasteners", n + " slot ends found", w, "%d of 2" % sum(1 for c in found if c), 2, ok=False)
            out.append(row)
            continue
        c1, c2 = found
        mx, my = (c1["x"] + c2["x"]) / 2, (c1["y"] + c2["y"]) / 2
        d12 = math.hypot(c2["x"] - c1["x"], c2["y"] - c1["y"])
        zf = L["Z_FLANGE_FRONT"]
        wid = 2 * (r_at(c1, zf) + r_at(c2, zf)) / 2
        R.add("fasteners", n + " slot centre position", w, math.hypot(mx - x, my - y), 0.0)
        R.add("fasteners", n + " slot width at the flange front", w, wid, G.slot_w)
        R.add("fasteners", n + " slot length at the flange front", w, d12 + wid, G.slot_l)
        R.add("fasteners", n + " slot draft", w, abs(c1["semi"]), 0.5, tol=TOL_DEG, note="0.5 deg, wider to the back: r(Zback) > r(Zfront): %s" %
              (r_at(c1, c1["z1"]) > r_at(c1, c1["z0"])))
        R.add("fasteners", n + " slot wider to the back", w, "yes" if r_at(c1, c1["z1"]) > r_at(c1, c1["z0"]) else "NO", "yes",
              ok=r_at(c1, c1["z1"]) > r_at(c1, c1["z0"]))
        # axis direction vs the direction to the glass centre (the slot's long axis must point at it)
        ax_ = ((c2["x"] - c1["x"]) / d12, (c2["y"] - c1["y"]) / d12)
        rc = (gcx - mx, gcy - my)
        rh = math.hypot(*rc)
        def angdiff(a, b):      # unsigned angle between two lines (atan2 form: exact for small angles)
            return math.degrees(abs(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])))
        ang = min(angdiff(ax_, rc), 180 - angdiff(ax_, rc))
        R.add("fasteners", n + " slot axis vs direction to the glass centre", w, ang, 0.0, tol=TOL_DEG, note="deg")
        angp = min(angdiff(ax_, u), 180 - angdiff(ax_, u))
        R.add("fasteners", n + " slot axis vs params slot_axis", w, angp, 0.0, tol=TOL_DEG,
              note="deg; params give the axis to 4 decimals (|u| = %.5f)" % math.hypot(*u))
        # through / blind
        zfront = min(c1["z0"], c2["z0"])
        zback = max(c1["z1"], c2["z1"])
        if G.cb:
            exp_front = G.cb_floor_z(n)
            R.add("fasteners", n + " slot front end = counterbore floor (GF-1.1)", w, zfront, exp_front,
                  note="the 5.4 x 7.0 slot continues below the counterbore; width at its front end %.4f" % (
                      2 * (r_at(c1, zfront) + r_at(c2, zfront)) / 2))
        else:
            exp_front = L["Z_SHEET_BACK"] if n in ("F1", "F2", "F3", "F4") else L["Z_FLANGE_FRONT"]
            R.add("fasteners", n + " slot front end (through)", w, zfront, exp_front, note="pad face for F1-F4, flange front for F5-F8")
        row["slot_front_z"] = zfront
        row["slot_halfwidth_front"] = (r_at(c1, zfront) + r_at(c2, zfront)) / 2
        row["slot_ends"] = [(c1["x"], c1["y"]), (c2["x"], c2["y"])]
        if G.cb:
            counterbore(R, ctx, n, ax, row, w, (mx, my), ax_, P)
        if G.core:
            coring(R, ctx, n, ax, row, w, P)
        R.add("fasteners", n + " slot back end = tube top (through)", w, zback, L["Z_TUBE_TOP"])
        ivc = P.z_intervals(x, y)
        R.add("fasteners", n + " slot open on its axis (vertical probe)", w, "open" if not ivc else "material %s" % ivc, "open", ok=not ivc)
        # tube
        tc = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 8.0 < k["r_mid"] < 9.6 and k["z1"] > L["Z_FLANGE_BACK"]]
        if tc:
            t = max(tc, key=lambda k: k["z1"])
            R.add("fasteners", n + " tube dia at its top", w, 2 * r_at(t, L["Z_TUBE_TOP"]), 18.0)
            R.add("fasteners", n + " tube draft", w, abs(t["semi"]), 1.0, tol=TOL_DEG)
            row["tube_top_dia"] = 2 * r_at(t, L["Z_TUBE_TOP"])
        else:
            R.add("fasteners", n + " tube (dia 18 cone)", w, "not found", "tube", ok=False)
        top = [f for f in tube_tops if math.hypot(f.Center().x - x, -f.Center().y - y) < 3.0]
        n_top = 2 if G.core else 1
        R.add("fasteners", n + " tube top at Z_TUBE_TOP", w, "%d face" % len(top), "%d face%s" % (n_top, "s (seat + outer skin)" if G.core else ""),
              ok=len(top) == n_top)
        # front pad (F1-F4) / none (F5-F8)
        pc = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 8.0 < k["r_mid"] < 9.6 and k["z1"] <= L["Z_FLANGE_FRONT"] + 0.01]
        pf = [f for f in pads if math.hypot(f.Center().x - x, -f.Center().y - y) < 3.0]
        if n in ("F1", "F2", "F3", "F4"):
            if pc:
                R.add("fasteners", n + " front pad dia at its base (flange front)", w, 2 * r_at(pc[0], L["Z_FLANGE_FRONT"]), G.pad_d,
                      note="dia at the pad face (Z_SHEET_BACK) %.3f (1 deg draft)" % (2 * r_at(pc[0], L["Z_SHEET_BACK"])))
            R.add("fasteners", n + " front pad face at Z_SHEET_BACK", w, "%d face" % len(pf), "1 face", ok=len(pf) == 1)
        else:
            iv = P.z_intervals(x + 6.0 * (-u[1]), y + 6.0 * u[0])
            zmin = iv[0][0] if iv else None
            R.add("fasteners", n + " no front pad: front face beside the slot", w, zmin, L["Z_FLANGE_FRONT"],
                  note="vertical probe 6 mm beside the slot")
        # washer bearing area on the tube top (DIN 9021 M4 dia 12; studs at the slot centre and at the slot ends)
        if top:
            areas = []
            for off in (0.0, -(G.slot_l - 4.0) / 2, (G.slot_l - 4.0) / 2):
                cx, cy = x + off * u[0], y + off * u[1]
                ann = C.tube(cx, cy, L["Z_TUBE_TOP"] - 1, L["Z_TUBE_TOP"] + 1, 12.0, 4.3)
                areas.append(sum(ff.Area() for f in top for ff in C.common_shape(f, ann).Faces()))
            row["washer_area"] = areas
            R.add("fasteners", n + " DIN 9021 M4 washer (12/4.3) bearing on the tube top (stud centred / at either slot end)", w,
                  min(areas), 80.0 if G.core else 82.0, info=True,
                  note="mm2: %.1f / %.1f / %.1f (params: >= 80 as modelled; 6.2 MPa at 500 N)" % tuple(areas))
        # tube rib to the step wall (F1-F4 per spec 'one 1.5 rib to the step wall')
        rib = tube_rib(ctx, n, P)
        row["rib"] = rib
        if rib.get("rib"):
            exp = G.RIB - 2 * T1 * 1.0
            R.add("fasteners", n + " tube rib width at Z_FLANGE_BACK + 1.0", w, rib["width"], exp, tol=0.02,
                  note="1.5 at the root, 1 deg draft -> %.3f at the probe height; %s; r %.2f..%.2f from the tube centre"
                       % (exp, rib["dir"], rib["r_range"][0], rib["r_range"][1]))
        else:
            R.add("fasteners", n + " tube rib", w, "none", "one 1.5 rib (concept 4.4)", info=n not in ("F1", "F2", "F3", "F4"),
                  ok=False, note=rib.get("note", ""))
        out.append(row)
    return out


def _round_radii(fr, x, y, z_lo, z_hi, rmax=1.6, near=10.0):
    """radii of the horizontal-axis round faces (cylinders not on Z, tori: minor radius) near (x, y) between z_lo, z_hi"""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    out = []
    for f in fr.Faces():
        gt = f.geomType()
        if gt not in ("CYLINDER", "TORUS"):
            continue
        bb = f.BoundingBox()
        if bb.zmin < z_lo - 1e-3 or bb.zmax > z_hi + 1e-3:
            continue
        c = f.Center()
        if math.hypot(c.x - x, -c.y - y) > near:
            continue
        ad = BRepAdaptor_Surface(f.wrapped)
        if gt == "CYLINDER":
            if abs(ad.Cylinder().Axis().Direction().Z()) > 0.5:
                continue
            r = ad.Cylinder().Radius()
        else:
            r = ad.Torus().MinorRadius()
        if r <= rmax:
            out.append(r)
    return sorted(set(round(r, 3) for r in out))


def counterbore(R, ctx, n, ax, row, w, centre, axis, P):
    """GF-1.1 stadium counterbore coaxial with the slot, on the sheet side"""
    G, fr = ctx.G, ctx.frame
    zo, zf = G.cb_open_z(n), G.cb_floor_z(n)
    ends = row["slot_ends"]
    cs = []
    for ex, ey in ends:
        c = [k for k in ax if math.hypot(k["x"] - ex, k["y"] - ey) < 0.05 and 3.4 < k["r_mid"] < 4.0 and abs(k["z0"] - zo) < 0.05]
        cs.append(c[0] if c else None)
    if not all(cs):
        R.add("counterbore", n + " counterbore cones found", w, "%d of 2" % sum(1 for c in cs if c), 2, ok=False)
        return
    c1, c2 = cs
    zref = G.L["Z_SHEET_BACK"]      # params: "stadium width at the opening (Z_SHEET_BACK)"
    wref = r_at(c1, zref) + r_at(c2, zref)
    wid = r_at(c1, zo) + r_at(c2, zo)
    d12 = math.hypot(c2["x"] - c1["x"], c2["y"] - c1["y"])
    R.add("counterbore", n + " counterbore width at Z_SHEET_BACK (params reference)", w, wref, float(G.cb["cb_w"]),
          note="cone extrapolated to Z_SHEET_BACK; at the real opening Z %.2f it is %.4f" % (zo, wid))
    R.add("counterbore", n + " counterbore length at Z_SHEET_BACK (params reference)", w, d12 + wref, float(G.cb["cb_l"]),
          note="at the real opening %.4f" % (d12 + wid))
    if abs(zo - zref) > 0.01:
        R.add("counterbore", n + " counterbore width x length at its real opening (flange front)", w, "%.3f x %.3f" % (wid, d12 + wid),
              "%.1f x %.1f" % (float(G.cb["cb_w"]), float(G.cb["cb_l"])), info=True,
              note="F5-F8 open 1.0 behind Z_SHEET_BACK, so the 1 deg wall has already closed in by %.3f per side" % ((wref - wid) / 2))
    R.add("counterbore", n + " counterbore draft", w, abs(c1["semi"]), float(G.cb["cb_draft"]), tol=TOL_DEG)
    narrowing = r_at(c1, c1["z1"]) < r_at(c1, c1["z0"])
    R.add("counterbore", n + " counterbore narrows with depth (A-side core)", w, "yes" if narrowing else "NO", "yes", ok=narrowing)
    R.add("counterbore", n + " counterbore coaxial with the slot", w,
          max(math.hypot(c["x"] - e[0], c["y"] - e[1]) for c, e in zip(cs, ends)), 0.0)
    fl = [f for f in C.faces_at_z(fr, zf, -1, tol=0.005) if math.hypot(f.Center().x - centre[0], -f.Center().y - centre[1]) < 5]
    R.add("counterbore", n + " counterbore floor (planar, -Z)", w, fl[0].BoundingBox().zmin if fl else "none", zf,
          ok=None if fl else False, note="%s above Z_SHEET_BACK" % ("1.6" if n in ("F1", "F2", "F3", "F4") else "2.0"))
    rr = _round_radii(fr, centre[0], centre[1], zf - 0.4, zf + 0.001, rmax=1.0, near=6.0)
    R.add("counterbore", n + " counterbore floor round", w, max(rr) if rr else "none", float(G.cb["cb_r"]),
          ok=None if rr else False, note="radii found %s" % rr)
    row["cb"] = {"open_z": zo, "floor_z": zf, "w_open": wid, "l_open": d12 + wid, "cones": [(c1["x"], c1["y"]), (c2["x"], c2["y"])],
                 "r_open": wid / 2, "drdz": c1["drdz"]}
    if n in ("F1", "F2", "F3", "F4"):
        pf = [f for f in C.faces_at_z(fr, G.L["Z_SHEET_BACK"], -1, tol=0.005)
              if math.hypot(f.Center().x - centre[0], -f.Center().y - centre[1]) < 3]
        a = sum(f.Area() for f in pf)
        pad_r = 9.0 - (G.L["Z_FLANGE_FRONT"] - G.L["Z_SHEET_BACK"]) * T1
        R.add("counterbore", n + " pad hard-stop face area left round the counterbore", w, a,
              float(G.cb.get("pad_contact_area_F1-F4", 0)) or "-", tol=0.5, info=not G.cb.get("pad_contact_area_F1-F4"),
              note="pad ring %.2f along / %.2f across the slot (pad dia %.3f at its face)" % (
                  pad_r - (d12 + wid) / 2, pad_r - wid / 2, 2 * pad_r))


def coring(R, ctx, n, ax, row, w, P):
    """GF-1.1 annular coring groove round the fastener tube, from the back"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    x, y = G.fxy(n)
    zt = L["Z_TUBE_TOP"]
    zfl = zt - float(G.core["core_depth"])
    ci = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 5.8 < k["r_mid"] < 6.6 and abs(k["z1"] - zt) < 0.02]
    co = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 7.1 < k["r_mid"] < 7.9 and abs(k["z1"] - zt) < 0.02]
    if not ci or not co:
        R.add("coring", n + " coring groove walls found", w, "%d/%d" % (len(ci), len(co)), "1/1", ok=False)
        return
    ci, co = ci[0], co[0]
    R.add("coring", n + " groove inner radius at the tube top", w, r_at(ci, zt), float(G.core["core_r_in"]))
    R.add("coring", n + " groove outer radius at the tube top", w, r_at(co, zt), float(G.core["core_r_out"]))
    R.add("coring", n + " groove wall drafts", w, max(abs(ci["semi"]), abs(co["semi"])), float(G.core["core_draft"]), tol=TOL_DEG)
    widening = (r_at(co, zt) - r_at(ci, zt)) > (r_at(co, ci["z0"]) - r_at(ci, ci["z0"]))
    R.add("coring", n + " groove widens to the back (B-side core)", w, "yes" if widening else "NO", "yes", ok=widening)
    fl = [f for f in C.faces_at_z(fr, zfl, +1, tol=0.005) if math.hypot(f.Center().x - x, -f.Center().y - y) < 3]
    R.add("coring", n + " groove floor (planar, +Z)", w, fl[0].BoundingBox().zmin if fl else "none", zfl, ok=None if fl else False,
          note="depth %.2f below the tube top" % (zt - zfl))
    rr = _round_radii(fr, x, y, zfl - 0.001, zfl + 0.6, rmax=1.0, near=9.0)
    R.add("coring", n + " groove floor rounds", w, max(rr) if rr else "none", float(G.core["core_floor_r"]), ok=None if rr else False,
          note="radii found %s" % rr)
    skin = 9.0 - r_at(co, zt)
    R.add("coring", n + " outer skin at the tube top (tube r 9.0 - groove r_out)", w, skin, 1.5, info=True)
    front = G.L["Z_SHEET_BACK"] if n in ("F1", "F2", "F3", "F4") else G.L["Z_FLANGE_FRONT"]
    R.add("coring", n + " groove floor above the front face (%s)" % ("pad face" if front == G.L["Z_SHEET_BACK"] else "flange front"),
          w, zfl - front, 2.7 if front == G.L["Z_SHEET_BACK"] else 1.7, info=True,
          note="params: floor 2.7 above the pad face at glass 3.0 (>= 2.0); vs counterbore floor %.2f" % (zfl - G.cb_floor_z(n)) if G.cb else "")
    row["core"] = {"r_in_top": r_at(ci, zt), "r_out_top": r_at(co, zt), "floor_z": zfl}
    # F5-F8: tube-base / step-wall blend radius and where the base fillet foot lands vs the flange edge
    if n not in ("F1", "F2", "F3", "F4"):
        rb = _round_radii(fr, x, y, L["Z_FLANGE_BACK"] - 0.001, L["Z_FLANGE_BACK"] + 1.4, rmax=1.6, near=11.0)
        R.add("coring", n + " tube base / step-wall blend radius (GF-1.1 item 6)", w, max(rb) if rb else "none", 1.2, tol=0.02,
              ok=None if rb else False, note="radii found %s" % rb)
        # outward from the fastener the flange edge is (flange_beyond - fast_off) away at the front, drafted 1 deg
        edge_back = (G.flange_beyond_glass - G.fast_off) - (L["Z_FLANGE_BACK"] - L["Z_FLANGE_FRONT"]) * T1
        tube_base = 9.0 + (L["Z_TUBE_TOP"] - L["Z_FLANGE_BACK"]) * T1
        foot = tube_base + (max(rb) if rb else 0.0)
        R.add("coring", n + " tube-base fillet foot vs the flange outer edge (outward side)", w, foot - edge_back, "< 0 (foot on the flange back)",
              info=True, note="fillet foot r %.3f vs flange edge r %.3f at the flange back: %s" % (
                  foot, edge_back, "the fillet runs off the flange edge (flange back split, fillet meets the edge face)" if foot > edge_back
                  else "foot on the flange back"))


def h6_cell(R, ctx):
    """GF-1.1 H6 corner cell: thinnest tail wall beside the jogged cell wall, and the cell wall position"""
    G, fr = ctx.G, ctx.frame
    if not G.h6:
        return None
    P = C.Probe(fr)
    out = []
    for z in (-0.3, -3.0, -6.0):
        best = None
        for y in np.arange(119.5, 148.0, 0.25):
            iv = P.x_intervals(float(y), z)
            for a, b in iv:
                if a < 168.2 < b and b - a < 6.0:
                    if best is None or b - a < best[0]:
                        best = (b - a, float(y), a, b)
        out.append({"z": z, "min_wall": best})
        if best:
            R.add("H6 cell", "tail wall beside the H6 cell at Z %.1f: thinnest" % z, "y %.2f, x %.2f..%.2f" % (best[1], best[2], best[3]),
                  best[0], float(G.h6.get("h6_wall_min", 1.1)), tol=0.05, info=z != -0.3,
                  note="params h6_wall_min %.2f at Z_PCB; >= 1.0 rule" % float(G.h6.get("h6_wall_min", 1.1)))
    # mirror wall at H7 for comparison
    best = None
    for y in np.arange(119.5, 148.0, 0.25):
        for a, b in P.x_intervals(float(y), -0.3):
            if a < 38.5 < b and b - a < 6.0:
                if best is None or b - a < best[0]:
                    best = (b - a, float(y), a, b)
    if best:
        R.add("H6 cell", "(reference) tail wall beside the H7 cell at Z -0.3: thinnest", "y %.2f" % best[1], best[0], "-", info=True)
    return out


def tube_rib(ctx, n, P):
    """width of the material strip between the tube and the step wall, probed across the expected rib direction
    (towards the glass corner for F1-F4, along the slot axis for F5-F8) at Z_FLANGE_BACK + 1.0"""
    G = ctx.G
    L = G.L
    x, y = G.fxy(n)
    u = G.slot_axis(n)
    z = L["Z_FLANGE_BACK"] + 1.0
    # distance from the tube centre to the step wall back (s 2.9) along u
    gx0, gx1, gy0, gy1 = G.GLASS[:4]
    pts = []
    for r in np.arange(9.75, 18.0, 0.5):
        px, py = x + r * u[0], y + r * u[1]
        sx, sy = -u[1], u[0]
        iv = P.intervals((px - 5 * sx, -(py - 5 * sy), z), (sx, -sy, 0.0), 0.0, 10.0)
        strip = [(a, b) for a, b in iv if b - a < 3.0 and a > 0.0 and b < 10.0]
        if strip:
            a, b = strip[0]
            pts.append((float(r), b - a, (a + b) / 2 - 5.0))
        elif pts:
            break
    if len(pts) < 3:
        return {"rib": False, "note": "no separate rib: the tube runs into the step wall (or no strip found)"}
    core = pts[1:-1] if len(pts) > 3 else pts
    rr = np.array([p[0] for p in core]); off = np.array([p[2] for p in core])
    slope = np.polyfit(rr, off, 1)[0] if len(core) > 1 else 0.0
    return {"rib": True, "width": float(np.median([p[1] for p in core])), "r_range": [pts[0][0], pts[-1][0]],
            "offset_from_slot_axis_mm": float(np.median(off)), "angle_to_slot_axis_deg": math.degrees(math.atan(slope)),
            "dir": "offset %.2f mm and %.1f deg from the slot axis" % (float(np.median(off)), math.degrees(math.atan(slope)))}


def bosses(R, ctx, ax, P):
    G = ctx.G
    L = G.L
    out = []
    for n, (x, y) in G.HOLES.items():
        w = "(%.2f, %.2f)" % (x, y)
        b = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 3.5 < k["r_mid"] < 4.6]
        p = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 1.0 < k["r_mid"] < 1.3]
        cb = [k for k in ax if math.hypot(k["x"] - x, k["y"] - y) < 0.05 and 1.45 < k["r_mid"] < 1.75]
        row = {"name": n, "found": bool(b and p and cb)}
        if not row["found"]:
            R.add("PCB bosses", n + " boss / pilot / relief found", w, "%d/%d/%d" % (len(b), len(p), len(cb)), "1/1/1", ok=False)
            out.append(row)
            continue
        b, p, cb = b[0], p[0], cb[0]
        R.add("PCB bosses", n + " position", w, max(math.hypot(k["x"] - x, k["y"] - y) for k in (b, p, cb)), 0.0)
        R.add("PCB bosses", n + " boss dia at Z_PCB", w, 2 * r_at(b, L["Z_PCB"]), G.BOSS_OD)
        R.add("PCB bosses", n + " boss draft", w, abs(b["semi"]), 1.0, tol=TOL_DEG)
        R.add("PCB bosses", n + " pilot dia at its mouth (Z_PCB - cbore_h)", w, 2 * r_at(p, L["Z_PCB"] - G.CBORE_H), G.PILOT_D,
              tol=0.015, note="pilot_d 2.4 'at Z_PCB'; the 0.5 relief takes Z -0.5..0, so the mouth is at -0.5 (as v2)")
        R.add("PCB bosses", n + " pilot draft", w, abs(p["semi"]), 0.5, tol=TOL_DEG)
        R.add("PCB bosses", n + " relief dia at Z_PCB", w, 2 * r_at(cb, L["Z_PCB"]), G.CBORE_D)
        R.add("PCB bosses", n + " relief depth", w, cb["z1"] - cb["z0"], G.CBORE_H)
        R.add("PCB bosses", n + " boss top", w, b["z1"], L["Z_PCB"])
        iv = P.z_intervals(x, y)
        floor = iv[0] if iv else None
        R.add("PCB bosses", n + " blind pilot floor (front face -> pilot bottom)", w, (floor[1] - floor[0]) if floor else "open",
              G.PILOT_FLOOR, ok=None if floor else False, note="floor Z %s" % (floor,))
        R.add("PCB bosses", n + " front face under the pilot", w, floor[0] if floor else None, L["Z_LAND"],
              note="H6/H7 sit on the corner-cell floors (= land plate)")
        out.append(row)
    return out


def support_ribs(R, ctx):
    """26 ribs vs v2 (Rev3.0_Frame_v2_params.json support_ribs.per_rib): centre line, width and free end at Z -1.0,
    measured the same way on the GF and the v2 STEP"""
    import json
    G = ctx.G
    v2p = json.load(open(C.V2_PARAMS))
    ribs = v2p["support_ribs"]["per_rib"]
    Pg, Pv = C.Probe(ctx.frame), C.Probe(ctx.v2)
    z = -1.0
    out = []
    for rb in ribs:
        x0, x1, y0, y1, sd = rb["x0"], rb["x1"], rb["y0"], rb["y1"], rb["side"]
        if sd in ("T", "B"):
            xm = (x0 + x1) / 2
            yprobe = (y0 + y1) / 2 if sd == "T" else (y0 + y1) / 2
            meas = []
            for PP in (Pg, Pv):
                iv = PP.x_intervals(yprobe, z)
                hit = [(a, b) for a, b in iv if a - 0.5 < xm < b + 0.5 and b - a < 3]
                ivy = PP.y_intervals(xm, z)
                # free end: the end of the material run that contains the rib, towards the panel centre
                run = [(a, b) for a, b in ivy if a - 0.1 < yprobe < b + 0.1]
                free = (run[0][1] if sd == "T" else run[0][0]) if run else None
                meas.append(((hit[0][0] + hit[0][1]) / 2 if hit else None, (hit[0][1] - hit[0][0]) if hit else None, free,
                             (run[0] if run else None)))
        else:
            ym = (y0 + y1) / 2
            xprobe = (x0 + x1) / 2
            meas = []
            for PP in (Pg, Pv):
                iv = PP.y_intervals(xprobe, z)
                hit = [(a, b) for a, b in iv if a - 0.5 < ym < b + 0.5 and b - a < 3]
                ivx = PP.x_intervals(ym, z)
                run = [(a, b) for a, b in ivx if a - 0.1 < xprobe < b + 0.1]
                free = (run[0][1] if sd == "L" else run[0][0]) if run else None
                meas.append(((hit[0][0] + hit[0][1]) / 2 if hit else None, (hit[0][1] - hit[0][0]) if hit else None, free,
                             (run[0] if run else None)))
        (cg, wg, fg, rg), (cv, wv, fv, rv) = meas
        row = {"rib": rb["rib"], "side": sd, "gf_centre": cg, "gf_width": wg, "gf_free_end": fg, "gf_run": rg,
               "v2_centre": cv, "v2_width": wv, "v2_free_end": fv, "v2_run": rv}
        out.append(row)
        w = "rib %d (%s)" % (rb["rib"], sd)
        if cg is None:
            R.add("support ribs", w + " found at Z -1.0", "", "not found", "rib", ok=False)
            continue
        R.add("support ribs", w + " centre line vs v2", "Z -1.0", cg, cv if cv is not None else float("nan"))
        R.add("support ribs", w + " width vs v2", "Z -1.0", wg, wv if wv is not None else float("nan"))
        if fg is not None and fv is not None:
            R.add("support ribs", w + " free end vs v2", "Z -1.0", fg, fv)
    n_found = sum(1 for r in out if r["gf_centre"] is not None)
    R.add("support ribs", "ribs found", "Z -1.0", n_found, 26, tol=0)
    return out


def tape_band(R, ctx):
    """the flange front must be flat over the tape band s 3.9..15.9 (only F5-F8 slots allowed in it)"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    fs = C.faces_at_z(fr, L["Z_FLANGE_FRONT"], -1, tol=0.005)
    holes = []
    for f in fs:
        for wi in f.innerWires():
            bb = wi.BoundingBox()
            holes.append(((bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, bb.xlen, bb.ylen))
    R.add("tape band", "flange front faces at Z_FLANGE_FRONT", "-", len(fs), 1, tol=0)
    R.add("tape band", "holes in the flange-front face", "-", len(holes), "4 slots F5-F8 + 4 pads F1-F4 + inner boundary",
          info=True, note="; ".join("(%.2f, %.2f) %.2fx%.2f" % h for h in holes))
    return {"holes": holes}


def run(ctx, log=C.log):
    t0 = time.time()
    R = Rows()
    fr = ctx.frame
    P = C.Probe(fr)
    log("[A] body, Z levels")
    body(R, ctx)
    res = {"z_levels": z_levels(R, ctx)}
    log("[A] edge profiles (drafted faces fitted over Z)")
    res["edge_profiles"] = edge_profiles(R, ctx, P)
    log("[A] lip details")
    res["lip"] = lip_details(R, ctx, P)
    log("[A] plan rectangles and corner radii")
    res["plan_rects"] = plan_rects(R, ctx)
    ax = axial(fr)
    log("[A] pips, fasteners, bosses")
    res["pips"] = pips(R, ctx, ax)
    res["fasteners"] = fasteners(R, ctx, ax, P)
    res["bosses"] = bosses(R, ctx, ax, P)
    log("[A] support ribs vs v2")
    res["support_ribs"] = support_ribs(R, ctx)
    res["tape_band"] = tape_band(R, ctx)
    res["h6_cell"] = h6_cell(R, ctx)
    res["rows"] = R.rows
    res["fails"] = [r for r in R.rows if r["verdict"] == "FAIL"]
    res["counts"] = {v: sum(1 for r in R.rows if r["verdict"] == v) for v in ("PASS", "FAIL", "INFO")}
    res["seconds"] = round(time.time() - t0, 1)
    log("    rows %s" % res["counts"])
    for r in res["fails"]:
        log("    FAIL %-14s %-60s %-28s %s vs %s (%s)" % (r["group"], r["item"], r["where"], r["measured"], r["required"], r["note"]))
    return res


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    res = run(ctx)
    C.dump(res, ctx.out("spec_only.json"))
