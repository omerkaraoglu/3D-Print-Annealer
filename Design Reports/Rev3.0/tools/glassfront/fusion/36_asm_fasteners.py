"""36 - stage 2, Part B: fastener sets and check bodies (siblings of 'Frame GF' under the root, all parametric):
  'Weld studs S4 F1-F4' +       default variant (visible): M4 x 16 CD weld studs on the sheet back (shank stud_d,
  'Washers + nyloc nuts S4 F1-F4'  ISO 13918 PT weld flange stud_fl_d x stud_fl_k), DIN 9021 M4 washers on the tube
                                tops (Z_TUBE_TOP), ISO 10511 M4 nyloc nuts (hex nut_s x nut_m) on the washers
  'Rivets R4 F1-F4 (hidden)'    dia riv_d blind rivets set from the front: dome head riv_head_d x riv_head_k in front
                                of the sheet (edge rounded riv_head_k - 0.2), shank through sheet / pad / flange / tube /
                                washer, formed blind head envelope riv_blind_d x riv_blind_h (ASSUMED) on DIN 9021 M5
                                backing washers (w5_*) on the tube tops
  'Weld studs S8 F5-F8 (hidden)' + 'Washers, nuts, spacers S8 F5-F8 (hidden)'
                                extra studs, washers, nuts at F5-F8 + DIN 9021 M4 spacer washers (t_gap) between
                                the sheet back and the flange front (master: the S8 hard stop)
  'Check - socket cylinders (hidden)'  dia socket_d from the nut bottom (Z_TUBE_TOP + w4_t) to socket_top, F1-F8.
Body names carry the fastener position (F1..F8)."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

STEEL = "Steel - Galvanized (Small)"
S4_STUDS, S4_NUTS = "Weld studs S4 F1-F4", "Washers + nyloc nuts S4 F1-F4"
S8_STUDS, S8_NUTS = "Weld studs S8 F5-F8 (hidden)", "Washers, nuts, spacers S8 F5-F8 (hidden)"


def fk_of(b, ks):
    bb = b.boundingBox
    x, y = (bb.minPoint.x + bb.maxPoint.x) * 5, -(bb.minPoint.y + bb.maxPoint.y) * 5
    best = min(ks, key=lambda k: math.hypot(x - L.P("f%d_x" % k), y - L.P("f%d_y" % k)))
    return best


def circles(c, name, pl, ks, d_expr, d2_expr=None):
    """sketch with one circle (or annulus d / d2) per fastener; returns the profiles: disks (1 loop) or annuli"""
    sk = L.csketch(c, name, pl)
    for k in ks:
        L.circle(sk, "f%d_x" % k, "f%d_y" % k, d_expr)
        if d2_expr:
            L.circle(sk, "f%d_x" % k, "f%d_y" % k, d2_expr)
    L.solve(sk)
    pr = L.profiles_with_loops(sk, 2 if d2_expr else 1)
    if d2_expr is None:
        # disks only: drop nothing (single circles give exactly one disk each)
        pass
    if pr.count != len(ks):
        raise RuntimeError("%s: %d profiles for %d fasteners" % (name, pr.count, len(ks)))
    return pr


def name_bodies(f, ks, fmt, ap):
    out = []
    for i in range(f.bodies.count):
        b = f.bodies.item(i)
        b.name = fmt % fk_of(b, ks)
        b.appearance = L.appearance(ap)
        out.append(b)
    return out


def studs_washers_nuts(cs, cw, ks, tag):
    """weld studs in component cs (they belong to the sheet), washers + nuts in component cw (stage 2: split so the
    exploded view can separate them; first build had one component per variant, see 36b)"""
    c = cs
    ps = L.cplane(cs, "Z_SHEET_BACK (%s studs)" % tag, "Z_SHEET_BACK")
    pt = L.cplane(cw, "Z_TUBE_TOP (%s washers)" % tag, "Z_TUBE_TOP")
    pn = L.cplane(cw, "Z_TUBE_TOP + w4_t (%s nuts)" % tag, "Z_TUBE_TOP + w4_t")
    f = L.cextrude(c, circles(c, "%s stud shanks" % tag, ps, ks, "stud_d"), "new", "stud_l", +1, "%s stud shanks" % tag)
    studs = name_bodies(f, ks, "Weld stud M4x16 F%d", STEEL)
    fl = L.cextrude(c, circles(c, "%s stud weld flanges" % tag, ps, ks, "stud_fl_d", "stud_d"), "new", "stud_fl_k", +1,
                    "%s stud weld flanges" % tag)
    tools = adsk.core.ObjectCollection.create()
    for i in range(fl.bodies.count):
        tools.add(fl.bodies.item(i))
    flanges = [fl.bodies.item(i) for i in range(fl.bodies.count)]
    for s in studs:
        k = int(s.name[-1])
        mine = adsk.core.ObjectCollection.create()
        for b in flanges:
            if fk_of(b, ks) == k:
                mine.add(b)
        ci = c.features.combineFeatures.createInput(s, mine)
        ci.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        cf = c.features.combineFeatures.add(ci)
        cf.name = "%s stud F%d shank + weld flange" % (tag, k)
    c = cw
    f = L.cextrude(c, circles(c, "%s washers DIN 9021 M4" % tag, pt, ks, "w4_od", "w4_id"), "new", "w4_t", +1,
                   "%s washers DIN 9021 M4" % tag)
    washers = name_bodies(f, ks, "Washer DIN 9021 M4 F%d", STEEL)
    sk = L.csketch(c, "%s nuts ISO 10511 M4" % tag, pn)
    for k in ks:
        L.hexagon(sk, "f%d_x" % k, "f%d_y" % k, "nut_s")
        L.circle(sk, "f%d_x" % k, "f%d_y" % k, "stud_d")
    L.solve(sk)
    pr = L.profiles_with_loops(sk, 2)
    if pr.count != len(ks):
        raise RuntimeError("nut profiles %d" % pr.count)
    f = L.cextrude(c, pr, "new", "nut_m", +1, "%s nuts ISO 10511 M4" % tag)
    nuts = name_bodies(f, ks, "Nyloc nut ISO 10511 M4 F%d", STEEL)
    return studs, washers, nuts


def run(_context: str):
    L.check_doc()
    L.log("=== 36 start")
    res = {}
    # --------------------------------------------------------------------------------------- S4 (default, visible)
    s, w, n = studs_washers_nuts(L.new_comp(S4_STUDS).component, L.new_comp(S4_NUTS).component, [1, 2, 3, 4], "S4")
    res["S4"] = [b.name for b in s + w + n]
    # --------------------------------------------------------------------------------------- R4 (hidden)
    o = L.new_comp("Rivets R4 F1-F4 (hidden)")
    c = o.component
    ks = [1, 2, 3, 4]
    pf = L.cplane(c, "Z_GLASS_FRONT (R4 heads)", "Z_GLASS_FRONT")
    pt = L.cplane(c, "Z_TUBE_TOP (R4 washers)", "Z_TUBE_TOP")
    pw = L.cplane(c, "Z_TUBE_TOP + w5_t (R4 blind heads)", "Z_TUBE_TOP + w5_t")
    f = L.cextrude(c, circles(c, "R4 dome heads", pf, ks, "riv_head_d"), "new", "riv_head_k", -1, "R4 dome heads")
    rivets = name_bodies(f, ks, "Blind rivet 4.8 F%d", "Paint - Enamel Glossy (Black)")
    for nm, pl, d, dist, direc in (("R4 shanks", pf, "riv_d", "Z_TUBE_TOP + w5_t - Z_GLASS_FRONT", +1),
                                   ("R4 blind heads (envelope)", pw, "riv_blind_d", "riv_blind_h", +1)):
        fx = L.cextrude(c, circles(c, nm, pl, ks, d), "new", dist, direc, nm)
        for b in [fx.bodies.item(i) for i in range(fx.bodies.count)]:     # list first: the joins consume them
            k = fk_of(b, ks)
            tgt = [r for r in rivets if r.name.endswith("F%d" % k)][0]
            col = adsk.core.ObjectCollection.create()
            col.add(b)
            ci = c.features.combineFeatures.createInput(tgt, col)
            ci.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
            c.features.combineFeatures.add(ci).name = "%s F%d join" % (nm, k)
    # dome: round the front edge of every head
    edges = adsk.core.ObjectCollection.create()
    zf = L.P("Z_GLASS_FRONT") - L.P("riv_head_k")
    for r in rivets:
        for i in range(r.edges.count):
            e = r.edges.item(i)
            bb = e.boundingBox
            if abs(bb.minPoint.z * 10 - zf) < 1e-4 and abs(bb.maxPoint.z * 10 - zf) < 1e-4 and \
                    (bb.maxPoint.x - bb.minPoint.x) * 10 > L.P("riv_head_d") - 0.1:
                edges.add(e)
    if edges.count != 4:
        raise RuntimeError("rivet head edges %d" % edges.count)
    fi = c.features.filletFeatures.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(edges, L.VI("riv_head_k - 0.2 mm"), False)
    c.features.filletFeatures.add(fi).name = "R4 dome head rounds"
    f = L.cextrude(c, circles(c, "R4 backing washers DIN 9021 M5", pt, ks, "w5_od", "w5_id"), "new", "w5_t", +1,
                   "R4 backing washers DIN 9021 M5")
    rw = name_bodies(f, ks, "Backing washer DIN 9021 M5 F%d", STEEL)
    o.isLightBulbOn = False
    res["R4"] = [b.name for b in rivets + rw]
    # --------------------------------------------------------------------------------------- S8 extra (hidden)
    o8s, o = L.new_comp(S8_STUDS), L.new_comp(S8_NUTS)
    c = o.component
    ks = [5, 6, 7, 8]
    s, w, n = studs_washers_nuts(o8s.component, c, ks, "S8")
    ps = L.cplane(c, "Z_SHEET_BACK (S8 spacers)", "Z_SHEET_BACK")
    f = L.cextrude(c, circles(c, "S8 spacers DIN 9021 M4", ps, ks, "w4_od", "w4_id"), "new", "t_gap", +1,
                   "S8 spacers DIN 9021 M4")
    sp = name_bodies(f, ks, "Spacer DIN 9021 M4 F%d", STEEL)
    o.isLightBulbOn = False
    o8s.isLightBulbOn = False
    res["S8"] = [b.name for b in s + w + n + sp]
    # --------------------------------------------------------------------------------------- socket check cylinders
    o = L.new_comp(L.CHECK_COMP)
    c = o.component
    ks = list(range(1, 9))
    pl = L.cplane(c, "nut bottom (sockets)", "Z_TUBE_TOP + w4_t")
    f = L.cextrude(c, circles(c, "Sockets dia 12", pl, ks, "socket_d"), "new", "socket_top - ( Z_TUBE_TOP + w4_t )",
                   +1, "Sockets dia 12")
    sk_b = name_bodies(f, ks, "socket F%d", "Plastic - Translucent Matte (Green)")
    o.isLightBulbOn = False
    res["sockets"] = [b.name for b in sk_b]
    n_, bad = L.timeline_health()
    L.log("36 %s; timeline %d unhealthy %s" % (res, n_, bad))
    print(res, n_, bad)
