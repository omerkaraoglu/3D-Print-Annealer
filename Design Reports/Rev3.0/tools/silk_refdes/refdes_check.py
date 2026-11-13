"""Exact check of the staged designators (KiCad 10 python + numpy), independent of the placement raster.

python refdes_check.py [stage.kicad_pcb] [placement.json]

1. Every footprint's Reference: on F.SilkS, visible, not mirrored, centre / centre, 0 or 90 deg, height >= 0.8 mm,
   thickness >= 0.10 mm (H1-H9 / DS1: hidden), and at the position / angle / size of placement.json (1 um).
2. Geometry, from the stage board itself (pcbnew polygons, 1 um approximation), for every designator and every new
   legend graphic (frames, leaders):
     F.Mask apertures (pads incl. their mask expansion)   >= 0.15 mm (fiducial apertures >= 1.00 mm)
     any other silk (library silk, board legend, other designators, other blocks) >= 0.15 mm
     board edge and holes                                  >= 0.30 mm
   distances are exact polygon-to-polygon distances of the stroke outlines (0 when they overlap).
3. Ownership of every designator outside a legend block, on its ink box: distance to its own
   courtyard (d_own) and to the nearest other courtyard (d_oth): d_oth >= d_own + 0.22 (centred, within its side)
   or + 0.30, d_oth >= 2 x d_own, no other courtyard touched; legend frames touch no courtyard.
4. KiCad's own DRC with the project rules plus check-only rules (silk_clearance 0.15 mm, 0.30 mm to Edge.Cuts) on a
   copy in work/drc_tight/: every violation that involves a designator or a new graphic is listed.
Writes work/check.json and prints a summary; exit code 1 on any failure.
"""
import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import CLI, LABELS, NAME, PLACEMENT, SKIP, STAGE, WORK  # noqa: E402

MAXERR = 1000
LIM = {"mask": 0.15, "fid": 1.00, "silk": 0.15, "edge": 0.30, "hole": 0.30}
# board legend (functional labels, pin marks, title, mains warning): placed with pads 0.25 / silk, edge, holes 0.5;
# checked here against pads 0.25, any other silk 0.15 (designators may come to 0.15 of a label), edge / holes 0.5
LIM_LABEL = {"mask": 0.25, "fid": 1.00, "silk": 0.15, "edge": 0.50, "hole": 0.50}
OWN_EXEMPT = {"Q1": {"HS1"}}      # BTA24 on the heatsink plate: the heatsink is not an "other part" for Q1's label


def rings_of(ps):
    out = []
    for i in range(ps.OutlineCount()):
        rs = [ps.Outline(i)] + [ps.Hole(i, k) for k in range(ps.HoleCount(i))]
        out.append([np.array([[r.CPoint(j).x / 1e6, r.CPoint(j).y / 1e6] for j in range(r.PointCount())]) for r in rs])
    return out


def poly(item, layer, clearance=0):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, clearance, MAXERR, pcbnew.ERROR_OUTSIDE)
    ps.Simplify()
    return rings_of(ps)


def bbox(rl):
    pts = np.vstack([r for rings in rl for r in rings[:1]])
    return (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())


def edges(rl):
    A, B = [], []
    for rings in rl:
        for r in rings:
            A.append(r)
            B.append(np.roll(r, -1, axis=0))
    return np.vstack(A), np.vstack(B)


def pt_seg(Pt, A, B):
    AB = B - A
    L2 = (AB ** 2).sum(1)
    L2 = np.where(L2 == 0, 1e-30, L2)
    t = ((Pt[:, None, 0] - A[None, :, 0]) * AB[None, :, 0] + (Pt[:, None, 1] - A[None, :, 1]) * AB[None, :, 1]) / L2
    t = np.clip(t, 0, 1)
    X = A[None, :, 0] + t * AB[None, :, 0]
    Y = A[None, :, 1] + t * AB[None, :, 1]
    return np.hypot(Pt[:, None, 0] - X, Pt[:, None, 1] - Y)


def cross(ax, ay, bx, by):
    return ax * by - ay * bx


def inside(pt, rl):
    """point inside a filled polygon list (outline minus holes), ray casting"""
    x, y = pt
    for rings in rl:
        def in_ring(r):
            xs, ys = r[:, 0], r[:, 1]
            xs2, ys2 = np.roll(xs, -1), np.roll(ys, -1)
            c = ((ys > y) != (ys2 > y)) & (x < (xs2 - xs) * (y - ys) / np.where(ys2 == ys, 1e-30, ys2 - ys) + xs)
            return bool(c.sum() % 2)
        if in_ring(rings[0]) and not any(in_ring(h) for h in rings[1:]):
            return True
    return False


def dist(a, b, filled_b=True):
    """exact distance between two polygon lists (0 if they overlap); filled_b False: b is a polyline set"""
    A1, B1 = edges(a)
    A2, B2 = edges(b)
    r1 = B1 - A1
    o1 = cross(r1[:, None, 0], r1[:, None, 1], A2[None, :, 0] - A1[:, None, 0], A2[None, :, 1] - A1[:, None, 1])
    o2 = cross(r1[:, None, 0], r1[:, None, 1], B2[None, :, 0] - A1[:, None, 0], B2[None, :, 1] - A1[:, None, 1])
    r2 = B2 - A2
    o3 = cross(r2[None, :, 0], r2[None, :, 1], A1[:, None, 0] - A2[None, :, 0], A1[:, None, 1] - A2[None, :, 1])
    o4 = cross(r2[None, :, 0], r2[None, :, 1], B1[:, None, 0] - A2[None, :, 0], B1[:, None, 1] - A2[None, :, 1])
    if np.any((o1 * o2 < 0) & (o3 * o4 < 0)):          # proper crossing; touching / collinear contact gives 0 below
        return 0.0
    if filled_b and (inside(a[0][0][0], b) or inside(b[0][0][0], a)):
        return 0.0
    return float(min(pt_seg(A1, A2, B2).min(), pt_seg(A2, A1, B1).min()))


def bdist(p, q):
    return math.hypot(max(0, q[0] - p[2], p[0] - q[2]), max(0, q[1] - p[3], p[1] - q[3]))


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else STAGE
    plf = sys.argv[2] if len(sys.argv) > 2 else PLACEMENT
    PL = json.load(open(plf, encoding="utf-8"))
    LB = json.load(open(LABELS, encoding="utf-8"))
    par = PL["params"]
    b = pcbnew.LoadBoard(stage)
    fail = []
    rep = {"refs": {}, "graphics": {}}

    # ---------------------------------------------------------------- 1. field properties
    mine = []                       # (key, rings, bbox, kind, block)
    fps = list(b.GetFootprints())
    for fp in fps:
        ref = fp.GetReference()
        f = fp.Reference()
        want = PL["refs"].get(ref)
        prob = []
        if ref in SKIP:                       # board-only mechanical parts: reference must stay hidden
            if f.IsVisible() and f.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                fail.append((ref, "properties", ["board-only part with a visible reference"]))
            rep["refs"][ref] = {"props": "hidden (board-only)"}
            continue
        if f.GetLayer() != pcbnew.F_SilkS:
            prob.append("layer")
        if not f.IsVisible():
            prob.append("hidden")
        if f.IsMirrored():
            prob.append("mirrored")
        if f.GetHorizJustify() != pcbnew.GR_TEXT_H_ALIGN_CENTER or f.GetVertJustify() != pcbnew.GR_TEXT_V_ALIGN_CENTER:
            prob.append("justify")
        ang = round(f.GetTextAngleDegrees(), 6) % 360
        if ang not in (0.0, 90.0) or round(f.GetDrawRotation().AsDegrees(), 6) % 360 != ang:
            prob.append("angle %s" % ang)
        if f.GetTextHeight() < 800000 or f.GetTextThickness() < 100000 or f.GetTextWidth() < 600000:
            prob.append("size")
        if f.IsBold() or f.IsItalic():
            prob.append("bold/italic")
        if want is None:
            prob.append("not in placement")
        else:
            if abs(f.GetPosition().x / 1e6 - want["x"]) > 0.001 or abs(f.GetPosition().y / 1e6 - want["y"]) > 0.001:
                prob.append("position %.4f,%.4f != %.4f,%.4f" % (f.GetPosition().x / 1e6, f.GetPosition().y / 1e6,
                                                               want["x"], want["y"]))
            if abs(ang - want["ang"]) > 1e-6:
                prob.append("angle != placement")
            if abs(f.GetTextHeight() / 1e6 - want["h"]) > 1e-6 or abs(f.GetTextWidth() / 1e6 - want["w"]) > 1e-6 or \
                    abs(f.GetTextThickness() / 1e6 - want["t"]) > 1e-6:
                prob.append("size != placement")
        rl = poly(f, pcbnew.F_SilkS)
        mine.append((ref, rl, bbox(rl), "ref", (want or {}).get("block")))
        rep["refs"][ref] = {"props": prob or "ok"}
        if prob:
            fail.append((ref, "properties", prob))
    new_uuids = set()
    gfx_names = {}
    import uuid as _u
    NS = _u.UUID("6b1f3c2e-9a57-4f0e-8d3b-5c1a2e7f9b40")
    for g in PL["graphics"]:
        gfx_names[str(_u.uuid5(NS, g["name"]))] = g["name"]
    lab_names = {}
    for g in LB["texts"]:
        if g["layer"] == "F.SilkS":
            lab_names[str(_u.uuid5(NS, g["name"]))] = g["name"]
    for d in b.GetDrawings():
        u = d.m_Uuid.AsString()
        if u in lab_names:
            rl = poly(d, pcbnew.F_SilkS)
            mine.append((lab_names[u], rl, bbox(rl), "label", None))
    if sum(1 for m in mine if m[3] == "label") != len(lab_names):
        fail.append(("labels", "missing in stage", len(lab_names)))
    for d in b.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.m_Uuid.AsString() in LB["delete"]:
            fail.append(("labels", "old text still present", d.GetText()))
    for d in b.GetDrawings():
        u = d.m_Uuid.AsString()
        if u in gfx_names:
            new_uuids.add(u)
            if d.GetLayer() != pcbnew.F_SilkS:
                fail.append((gfx_names[u], "graphic layer", b.GetLayerName(d.GetLayer())))
            rl = poly(d, pcbnew.F_SilkS)
            mine.append((gfx_names[u], rl, bbox(rl), "gfx", gfx_names[u].split("-")[0]))
    if len(new_uuids) != len(gfx_names):
        fail.append(("graphics", "missing in stage", sorted(set(gfx_names) - new_uuids)))

    # ---------------------------------------------------------------- 2. obstacles from the stage board
    mask, silk, cys = [], [], {}
    for fp in fps:
        ref = fp.GetReference()
        for p in fp.Pads():
            if p.IsOnLayer(pcbnew.F_Mask):
                rl = poly(p, pcbnew.F_Cu, p.GetSolderMaskExpansion(pcbnew.F_Mask))
                mask.append((ref + "." + p.GetNumber(), rl, bbox(rl), "fid" if ref.startswith("FID") else "mask"))
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and not (g.GetClass() in ("PCB_TEXT", "PCB_TEXTBOX") and not g.IsVisible()):
                rl = poly(g, pcbnew.F_SilkS)
                silk.append((ref + " library silk", rl, bbox(rl)))
        for f in fp.GetFields():
            if f.GetName() != "Reference" and f.IsVisible() and f.GetLayer() == pcbnew.F_SilkS:
                rl = poly(f, pcbnew.F_SilkS)
                silk.append((ref + " " + f.GetName(), rl, bbox(rl)))
        c = pcbnew.SHAPE_POLY_SET(fp.GetCourtyard(pcbnew.F_CrtYd))
        if c.OutlineCount():
            rl = rings_of(c)
            cys[ref] = (rl, bbox(rl))
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.F_SilkS and d.m_Uuid.AsString() not in new_uuids and \
                d.m_Uuid.AsString() not in lab_names:
            rl = poly(d, pcbnew.F_SilkS)
            silk.append(("board " + (d.GetText() if d.GetClass() == "PCB_TEXT" else d.GetClass()), rl, bbox(rl)))
    ps = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(ps, True)
    outline = rings_of(ps)
    holes = []
    for fp in fps:
        for p in fp.Pads():
            if p.HasHole():
                holes.append((fp.GetReference(), p.GetPosition().x / 1e6, p.GetPosition().y / 1e6,
                              max(p.GetDrillSize().x, p.GetDrillSize().y) / 2e6))

    worst = {"mask": 9, "fid": 9, "silk": 9, "edge": 9, "hole": 9}
    for key, rl, bb, kind, blk in mine:
        r = {}
        LL = LIM_LABEL if kind == "label" else LIM
        for name, orl, obb, k in mask:
            lim = LL[k]
            if bdist(bb, obb) >= lim + 0.5:
                continue
            dd = dist(rl, orl)
            worst[k] = min(worst[k], dd)
            if dd < lim - 1e-6:
                fail.append((key, k, name, round(dd, 4)))
            r[k] = min(r.get(k, 9), round(dd, 4))
        others = [(n, orl, obb) for n, orl, obb in silk] + \
                 [(k2, rl2, bb2) for k2, rl2, bb2, kd2, blk2 in mine if k2 != key and not (
                     # lines and rectangles of one map may touch (frame / leader); its texts may not
                     kind == "gfx" and kd2 == "gfx" and blk2 == blk and "-anchor-" not in key and "-anchor-" not in k2)]
        for name, orl, obb in others:
            if bdist(bb, obb) >= LIM["silk"] + 0.5:
                continue
            dd = dist(rl, orl)
            worst["silk"] = min(worst["silk"], dd)
            if dd < LIM["silk"] - 1e-6:
                fail.append((key, "silk", name, round(dd, 4)))
            r["silk"] = min(r.get("silk", 9), round(dd, 4))
        de = dist(rl, outline, filled_b=False)
        ok_in = inside(rl[0][0][0], outline)
        worst["edge"] = min(worst["edge"], de if ok_in else 0)
        if de < LL["edge"] - 1e-6 or not ok_in:
            fail.append((key, "edge", round(de, 4)))
        r["edge"] = round(de, 4)
        for hr, hx, hy, hrad in holes:
            if bdist(bb, (hx - hrad, hy - hrad, hx + hrad, hy + hrad)) > 1.0:
                continue
            pts = np.vstack([x for rings in rl for x in rings])
            AA, BB = edges(rl)
            dh = float(pt_seg(np.array([[hx, hy]]), AA, BB).min()) - hrad
            if inside((hx, hy), rl):
                dh = 0.0
            worst["hole"] = min(worst["hole"], dh)
            if dh < LL["hole"] - 1e-6:
                fail.append((key, "hole", hr, round(dh, 4)))
            r["hole"] = min(r.get("hole", 9), round(dh, 4))
        # ---------------------------------------------------------------- 3. ownership / courtyards
        if kind == "ref" and blk is None:
            # ownership is judged on the designator's ink box (what the eye groups), exact courtyard polygons
            box = [[np.array([[bb[0], bb[1]], [bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]]])]]
            own = cys.get(key)
            d_own = dist(box, own[0]) if own else 0.0
            d_oth, who = 9.0, None
            for q, (qrl, qbb) in cys.items():
                if q == key or bdist(bb, qbb) >= d_oth or q in OWN_EXEMPT.get(key, ()):
                    continue
                dq = dist(box, qrl)
                if dq < d_oth:
                    d_oth, who = dq, q
            w = PL["refs"][key]
            side_len = None
            margin = par["own_margin"]
            if abs(w.get("off", 0)) <= par["centred_tol"] + 1e-9 and own:
                ob = own[1]
                hs = w["side"] in "TB"
                ext = (bb[2] - bb[0]) if hs else (bb[3] - bb[1])
                if ext <= ((ob[2] - ob[0]) if hs else (ob[3] - ob[1])) + 0.01:
                    margin = par["own_margin_aligned"]
            r.update({"d_own": round(d_own, 4), "d_oth": round(d_oth, 4), "nearest_other": who,
                      "slack": round(d_oth - d_own - margin, 4)})
            if d_oth <= 0 or d_oth < d_own + margin - 1e-6 or d_oth < 2 * d_own - 1e-6:
                fail.append((key, "ownership", who, round(d_own, 3), round(d_oth, 3), margin))
        if kind == "gfx" and key.endswith("-frame"):
            for q, (qrl, qbb) in cys.items():
                if bdist(bb, qbb) < 0.01 and dist(rl, qrl) <= 0:
                    fail.append((key, "frame over courtyard", q))
        (rep["refs"] if kind == "ref" else rep["graphics"]).setdefault(key, {}).update({"clearances": r})

    # ---------------------------------------------------------------- 3b. every legend map is a true scaled copy
    # position of each map item on the stage: the member's name (ink box centre), or its outline's centre when it is
    # drawn as an outline (ICs, anchors); compared with the courtyard centres on the board: one uniform scale for
    # every pair in both axes, same signs (no mirror, no rotation)
    gfx_rect = {}
    for d in b.GetDrawings():
        u = d.m_Uuid.AsString()
        if u in gfx_names and "-outline-" in gfx_names[u]:
            bb_ = d.GetBoundingBox()
            gfx_rect[gfx_names[u]] = ((bb_.GetLeft() + bb_.GetRight()) / 2e6, (bb_.GetTop() + bb_.GetBottom()) / 2e6)
    ink_c = {m[0]: ((m[2][0] + m[2][2]) / 2, (m[2][1] + m[2][3]) / 2) for m in mine if m[3] == "ref"}
    maps_ok = {}
    for blk in PL["blocks"]:
        pts = {}
        for m in blk["members"] + blk.get("anchors", []):
            o = gfx_rect.get("%s-outline-%s" % (blk["name"], m))
            pts[m] = o if o else ink_c[m]
        bc = {m: ((cys[m][1][0] + cys[m][1][2]) / 2, (cys[m][1][1] + cys[m][1][3]) / 2) for m in pts}
        ratios, bad_sign = [], []
        ks = sorted(pts)
        for i, p in enumerate(ks):
            for q in ks[i + 1:]:
                for ax in (0, 1):
                    db = bc[q][ax] - bc[p][ax]
                    dm = pts[q][ax] - pts[p][ax]
                    if abs(db) >= 0.5:
                        ratios.append(dm / db)
                        if dm * db <= 0:
                            bad_sign.append((p, q, "xy"[ax]))
        spread = (max(ratios) - min(ratios)) if ratios else 0.0
        maps_ok[blk["name"]] = {"scale": round(sum(ratios) / len(ratios), 4) if ratios else None,
                                "scale_spread": round(spread, 4), "mirror_or_rotation": bad_sign}
        if bad_sign or spread > 0.01:
            fail.append((blk["name"], "map not a uniform scaled copy", bad_sign, round(spread, 4)))
    rep["maps"] = maps_ok

    # ---------------------------------------------------------------- 4. KiCad DRC with check-only rules
    d = os.path.join(WORK, "drc_tight")
    os.makedirs(d, exist_ok=True)
    sd = os.path.dirname(stage)
    shutil.copyfile(stage, os.path.join(d, NAME + ".kicad_pcb"))
    shutil.copyfile(os.path.join(sd, NAME + ".kicad_pro"), os.path.join(d, NAME + ".kicad_pro"))
    dru = open(os.path.join(sd, NAME + ".kicad_dru"), encoding="utf-8").read()
    dru += ('\n# ---------------- check-only rules (refdes_check.py), never delivered\n'
            '(rule "check: silk clearance 0.15"\n  (condition "A.Layer != \'Edge.Cuts\' && B.Layer != \'Edge.Cuts\'")\n'
            '  (constraint silk_clearance (min 0.15mm)))\n'
            '(rule "check: silk to edge 0.30"\n  (condition "A.Layer == \'Edge.Cuts\' || B.Layer == \'Edge.Cuts\'")\n'
            '  (constraint silk_clearance (min 0.3mm)))\n')
    open(os.path.join(d, "battery sentinel.kicad_dru"), "w", encoding="utf-8").write(dru)
    out = os.path.join(d, "drc_tight.json")
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", out,
                    os.path.join(d, NAME + ".kicad_pcb")], capture_output=True, text=True)
    drc = json.load(open(out, encoding="utf-8"))
    ref_uuids = {}
    for fp in fps:
        ref_uuids[fp.Reference().m_Uuid.AsString()] = fp.GetReference()
    tight = []
    for v in drc["violations"]:
        if any(" on F.Courtyard" in i["description"] or " on F.Fab" in i["description"] for i in v["items"]):
            continue                 # the check-only silk rule also matches courtyard / fab items: not silkscreen
        ids = [i.get("uuid") for i in v["items"]]
        hit = [ref_uuids.get(u) or gfx_names.get(u) or lab_names.get(u) for u in ids
               if u in ref_uuids or u in gfx_names or u in lab_names]
        if hit:
            tight.append({"type": v["type"], "items": [i["description"] for i in v["items"]], "mine": hit})
    for t in tight:
        fail.append(("drc_tight", t["type"], t["items"]))
    rep["worst"] = {k: round(v, 4) for k, v in worst.items()}
    rep["drc_tight_total"] = len(drc["violations"])
    rep["drc_tight_mine"] = tight
    rep["failures"] = [list(map(str, f)) for f in fail]
    sl = [v["clearances"]["slack"] for v in rep["refs"].values() if "slack" in v.get("clearances", {})]
    rep["ownership_min_slack"] = round(min(sl), 4) if sl else None
    json.dump(rep, open(os.path.join(WORK, "check.json"), "w", encoding="utf-8"), indent=1)
    print("designators %d, new map graphics %d, legend texts %d" % (sum(1 for m in mine if m[3] == "ref"),
          sum(1 for m in mine if m[3] == "gfx"), sum(1 for m in mine if m[3] == "label")))
    print("worst clearances (mm):", rep["worst"], "(limits", LIM, ")")
    print("ownership: %d designators outside blocks, smallest slack over the required margin %.3f mm" % (len(sl), min(sl)))
    print("KiCad DRC with check-only rules: %d violations in total, %d involve designators / new graphics" % (
        len(drc["violations"]), len(tight)))
    print("legend maps (uniform scale, board orientation):", {k: (float(v["scale"]), float(v["scale_spread"]), len(v["mirror_or_rotation"])) for k, v in rep["maps"].items()})
    print("FAILURES: %d" % len(fail))
    for f in fail[:60]:
        print("  ", f)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
