"""66 - stage 4 (GF-2.0), lead decision 3: S8 is dropped; only F1-F4 are moulded (S4 / R4).
Removes everything at the F5-F8 positions, cleanly:
  frame   'Root fillets tube_sw_r - F5-F8 tube to step wall (rule)'  deleted (F5-F8 tube blend)
          'Fastener counterbores F5-F8'                              deleted
          'Coring groove floor edges R core_floor_r' and 'Counterbore floor edges R cb_r' deleted and re-created on
          the F1-F4 floors only (8 + 4 loops)
          F5-F8 curves deleted from the sketches of the tubes, slots, coring and counterbores; the features keep the
          F1-F4 profiles and are renamed '... F1-F4'
  assembly occurrences 'Weld studs S8 F5-F8 (hidden)' and 'Washers, nuts, spacers S8 F5-F8 (hidden)' deleted (studs,
          washers, nuts, DIN 988 shims; there was no gasket body); sockets F5-F8 deleted from the hidden check component
  params  tube_sw_r, cb_floor_mid, spacer_id, spacer_od, f5_* .. f8_* deleted once unused
Refuses to run twice (needs 'Fastener tubes F1-F8 sketch')."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

SK = {"Fastener tubes F1-F8 sketch": "Fastener tubes F1-F4 sketch",
      "Fastener slots F1-F8 sketch": "Fastener slots F1-F4 sketch",
      "Fastener tube coring F1-F8 sketch": "Fastener tube coring F1-F4 sketch",
      "Fastener counterbores F1-F8 sketch": "Fastener counterbores F1-F4 sketch"}
FEAT_RENAME = {"Fastener tubes F1-F8": "Fastener tubes F1-F4", "Fastener slots F1-F8 (back)": "Fastener slots F1-F4 (back)",
               "Fastener tube coring F1-F8": "Fastener tube coring F1-F4"}
DEL_FEATS = ["Root fillets tube_sw_r - F5-F8 tube to step wall (rule)", "Fastener counterbores F5-F8",
             "Coring groove floor edges R core_floor_r", "Counterbore floor edges R cb_r"]
S8_COMPS = ["Weld studs S8 F5-F8 (hidden)", "Washers, nuts, spacers S8 F5-F8 (hidden)"]
CORE_FILLET = "Coring groove floor edges R core_floor_r"
CB_FILLET = "Counterbore floor edges R cb_r"


def fpos(k):
    return L.P("f%d_x" % k), L.P("f%d_y" % k)


def near_f58(geom_bb, tol=12.0):
    cx = (geom_bb.minPoint.x + geom_bb.maxPoint.x) * 5.0
    cy = -(geom_bb.minPoint.y + geom_bb.maxPoint.y) * 5.0
    d58 = min(math.hypot(cx - fpos(k)[0], cy - fpos(k)[1]) for k in (5, 6, 7, 8))
    d14 = min(math.hypot(cx - fpos(k)[0], cy - fpos(k)[1]) for k in (1, 2, 3, 4))
    return d58 < tol and d14 > tol


def drop_curves(sk):
    n = 0
    curves = [sk.sketchCurves.item(i) for i in range(sk.sketchCurves.count)]
    for cu in curves:
        if cu.isValid and near_f58(cu.boundingBox):
            cu.deleteMe()
            n += 1
    # orphan sketch points (arc centres of deleted stadiums are deleted with the arcs; anything else left near F5-F8)
    pts = [sk.sketchPoints.item(i) for i in range(sk.sketchPoints.count)]
    for p in pts:
        if p.isValid and not p.isFixed and p.connectedEntities.count == 0:
            g = p.geometry
            if min(math.hypot(g.x * 10 - fpos(k)[0], -g.y * 10 - fpos(k)[1]) for k in (5, 6, 7, 8)) < 12:
                p.deleteMe()
    return n


def reprofile(feat_name, profiles, tl):
    f = L.feature(feat_name)
    if f is None:
        raise RuntimeError("no feature " + feat_name)
    f.timelineObject.rollTo(True)
    f.profile = profiles
    tl.moveToEnd()
    return f


def floor_loops(zf, ks, nz_up, outer_only):
    b = L.body()
    edges = adsk.core.ObjectCollection.create()
    nfl = 0
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType or abs(f.pointOnFace.z * 10 - zf) > 1e-4:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if (nz_up and n.z < 0.9999) or (not nz_up and n.z > -0.9999):
            continue
        c = f.centroid
        if min(math.hypot(c.x * 10 - fpos(k)[0], -c.y * 10 - fpos(k)[1]) for k in ks) > 2.0:
            continue
        nfl += 1
        for j in range(f.loops.count):
            lp = f.loops.item(j)
            if outer_only and not lp.isOuter:
                continue
            for e in range(lp.edges.count):
                edges.add(lp.edges.item(e))
    return nfl, edges


def add_fillet(edges, radius, name):
    ff = L.comp().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, L.VI(radius), True)
    fi.isRollingBallCorner = True
    fl = ff.add(fi)
    fl.name = name
    return fl


def run(_context: str):
    d = L.check_doc()
    L.log("=== 66 start")
    c = L.comp()
    if c.sketches.itemByName("Fastener tubes F1-F8 sketch") is None:
        raise RuntimeError("66 already applied (no 'Fastener tubes F1-F8 sketch')")
    tl = d.timeline
    v0 = L.body().volume
    out = {}
    # 1 features
    for nm in DEL_FEATS:
        f = L.feature(nm)
        if f is None:
            raise RuntimeError("missing feature " + nm)
        f.deleteMe()
    tl.moveToEnd()
    # 2 S8 hardware
    for cn in S8_COMPS:
        o = L.occ_by_comp(cn)
        o.deleteMe()
    tl.moveToEnd()
    # 3 sketch curves at F5-F8
    for old in SK:
        sk = c.sketches.itemByName(old)
        out[old] = drop_curves(sk)
    sko = L.occ_by_comp(L.CHECK_COMP).component
    ssk = sko.sketches.itemByName("Sockets dia 12 sketch")
    out["sockets"] = drop_curves(ssk)
    d.computeAll()
    # 4 re-profile
    sk = c.sketches.itemByName("Fastener tubes F1-F8 sketch")
    if sk.profiles.count != 4:
        raise RuntimeError("tube profiles %d" % sk.profiles.count)
    reprofile("Fastener tubes F1-F8", L.pick_profiles(sk), tl)
    sk = c.sketches.itemByName("Fastener slots F1-F8 sketch")
    if sk.profiles.count != 4:
        raise RuntimeError("slot profiles %d" % sk.profiles.count)
    reprofile("Fastener slots F1-F8 (back)", L.pick_profiles(sk), tl)
    reprofile("Fastener slots F1-F4 (through the pads)", L.pick_profiles(sk), tl)
    sk = c.sketches.itemByName("Fastener tube coring F1-F8 sketch")
    ring = L.profiles_with_loops(sk, 2)
    if ring.count != 4:
        raise RuntimeError("coring ring profiles %d" % ring.count)
    reprofile("Fastener tube coring F1-F8", ring, tl)
    sk = c.sketches.itemByName("Fastener counterbores F1-F8 sketch")
    if sk.profiles.count != 4:
        raise RuntimeError("counterbore profiles %d" % sk.profiles.count)
    reprofile("Fastener counterbores F1-F4 (pads)", L.pick_profiles(sk), tl)
    # sockets (new bodies)
    sf = None
    for i in range(tl.count):
        if tl.item(i).name == "Sockets dia 12":
            sf = adsk.fusion.ExtrudeFeature.cast(tl.item(i).entity)
    if ssk.profiles.count != 4:
        raise RuntimeError("socket profiles %d" % ssk.profiles.count)
    sf.timelineObject.rollTo(True)
    sf.profile = L.pick_profiles(ssk)
    tl.moveToEnd()
    d.computeAll()
    for i in range(sko.bRepBodies.count):
        b = sko.bRepBodies.item(i)
        bb = b.boundingBox
        cx, cy = (bb.minPoint.x + bb.maxPoint.x) * 5, -(bb.minPoint.y + bb.maxPoint.y) * 5
        k = min((1, 2, 3, 4), key=lambda q: math.hypot(cx - fpos(q)[0], cy - fpos(q)[1]))
        b.name = "socket F%d" % k
    # 5 edge fillets on the F1-F4 floors
    core = L.feature("Fastener tube coring F1-F8")
    core.timelineObject.rollTo(False)
    n1, e1 = floor_loops(L.P("Z_TUBE_TOP") - L.P("core_depth"), (1, 2, 3, 4), True, False)
    if n1 != 4:
        raise RuntimeError("groove floors %d" % n1)
    add_fillet(e1, "core_floor_r", CORE_FILLET)
    tl.moveToEnd()
    n2, e2 = floor_loops(L.P("Z_SHEET_BACK") + L.P("cb_floor"), (1, 2, 3, 4), False, True)
    if n2 != 4:
        raise RuntimeError("counterbore floors %d" % n2)
    add_fillet(e2, "cb_r", CB_FILLET)
    out["fillet_edges"] = (e1.count, e2.count)
    # 6 renames
    for old, new in SK.items():
        c.sketches.itemByName(old).name = new
    for old, new in FEAT_RENAME.items():
        L.feature(old).name = new
    sko.sketches.itemByName("Sockets dia 12 sketch").name = "Sockets dia 12 sketch"
    d.computeAll()
    # 7 parameters
    gone, kept = [], []
    names = ["tube_sw_r", "cb_floor_mid", "spacer_id", "spacer_od"]
    for k in (5, 6, 7, 8):
        names += ["f%d_ux" % k, "f%d_uy" % k, "f%d_x" % k, "f%d_y" % k]
    for nm in names:
        p = d.userParameters.itemByName(nm)
        if p is None:
            continue
        if p.isDeletable and p.deleteMe():
            gone.append(nm)
        else:
            kept.append(nm)
    n, bad = L.timeline_health()
    out.update({"params_deleted": gone, "params_kept": kept, "timeline": n, "unhealthy": bad,
                "volume_before_cm3": round(v0, 4), "frame": L.body_stats()})
    L.dump(out, "gf20/66_drop_s8.json")
    L.log("66 %s" % out)
    print(out)
