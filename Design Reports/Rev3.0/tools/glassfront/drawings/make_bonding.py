"""Bonding and assembly aids: frame-front plan 1:1 (land, bead path, pips, tape strips, corner dabs, F1-F4 slots with
their axes, the GF-2.0 bend-gap slot, Formex sheet carried over from v2 as reference) - A3 sheet (PDF + PNG) and a DXF
(front view).

  <venv>/Scripts/python.exe make_bonding.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_BondingAids.{dxf,pdf,png}
"""
import datetime
import math
import re
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import (Params, Choices, Rect, OUT_DIR, n, n2, tr, new_dxf, dxf_poly, dxf_rect, dxf_text,
                       stadium_pts, bulge_to_points, rev_note, master_ref,
                       s8_withdrawn_rev)
from gf_geom import Geom, gap_temperatures
from gf_draft import Sheet, View, THICK, THIN, XTHIN, MM_PER_PT, lw

LAYERS = [("FLANGE_REF", 8, "CONTINUOUS"), ("SLOTS", 1, "CONTINUOUS"), ("COUNTERBORES", 1, "DASHED"),
          ("SLOT_AXES", 1, "CENTER"),
          ("LAND", 7, "CONTINUOUS"), ("BEAD", 250, "CONTINUOUS"), ("BEAD_CL", 250, "DASHED"),
          ("PIPS", 6, "CONTINUOUS"), ("TAPE", 3, "CONTINUOUS"), ("DABS", 30, "CONTINUOUS"),
          ("GLASS_REF", 5, "DASHED"), ("FORMEX_REF", 200, "DASHDOT"), ("BEND_SLOT", 1, "CONTINUOUS"),
          ("TEXT", 7, "CONTINUOUS")]
C_BEAD, C_TAPE, C_DAB, C_PIP, C_SLOT, C_FMX, C_REF = "#555555", "#2e8b57", "#e08a00", "#b0308f", "#c0392b", \
    "#7b4fa0", "#3b6fb6"


def f_mark(u0, v0, h):
    return [((u0, v0), (u0, v0 + h)), ((u0, v0 + h), (u0 + 0.6 * h, v0 + h)),
            ((u0, v0 + 0.55 * h), (u0 + 0.45 * h, v0 + 0.55 * h))]


def side_rows(G):
    """per front-view side: land width, bead edges, bead -> pocket (from the geometry, checked against the master)"""
    L = G.lands()
    out = []
    for k, v in L.items():
        out.append((k, v, G.bead_edge, G.bead_edge + G.bead_w, v - G.bead_edge - G.bead_w))
    return out


def front_angle(f):
    return math.degrees(math.atan2(f["av"], f["au"]))


def write_dxf(path, P, C, G):
    doc, msp = new_dxf(LAYERS)
    dxf_rect(msp, G.flange, "FLANGE_REF")
    for f in ("F1", "F2", "F3", "F4"):
        msp.add_circle((G.F[f]["u"], G.F[f]["v"]), G.pad_d / 2.0, dxfattribs={"layer": "FLANGE_REF"})
    cb, _ = G.fastener_cuts()
    for k, f in G.F.items():
        dxf_poly(msp, G.slot(k), "SLOTS")
        dxf_poly(msp, stadium_pts(f["u"], f["v"], f["au"], f["av"], cb["cb_l"], cb["cb_w"]), "COUNTERBORES")
        L = G.slot_l / 2.0 + 6.0
        msp.add_line((f["u"] - f["au"] * L, f["v"] - f["av"] * L), (f["u"] + f["au"] * L, f["v"] + f["av"] * L),
                     dxfattribs={"layer": "SLOT_AXES"})
        dxf_text(msp, k, f["u"] + 5.0, f["v"] + 5.0, 3.0)
    for r in (G.lip_in, G.lip_out, G.seat_out):
        dxf_rect(msp, r, "LAND")
    dxf_poly(msp, [(x, y, 0.0) for x, y in G.land_inner], "LAND")
    dxf_rect(msp, G.bead_out, "BEAD")
    dxf_rect(msp, G.bead_inn, "BEAD")
    dxf_rect(msp, G.bead_cl, "BEAD_CL")
    for k, (u, v) in G.pips.items():
        msp.add_circle((u, v), G.pip_d / 2.0, dxfattribs={"layer": "PIPS"})
        dxf_text(msp, "P" + k[3:], u + 1.5, v + 1.5, 2.0)
    for r in G.strips.values():
        dxf_rect(msp, r, "TAPE")
    for pts in G.dabs.values():
        dxf_poly(msp, [(x, y, 0.0) for x, y in pts], "DABS")
    dxf_rect(msp, G.glass, "GLASS_REF")
    dxf_rect(msp, G.window, "GLASS_REF")
    fm, _ = G.formex()
    dxf_rect(msp, fm, "FORMEX_REF")
    dxf_rect(msp, G.slot_bg, "BEND_SLOT")                 # GF-2.0: the only through-opening at the bottom
    g = G.flange
    dxf_text(msp, "GF BONDING AIDS - %s - FRAME FRONT PLAN = FRONT VIEW (u right, v up), origin = glass centre, mm" %
             P.revision, g.x0, g.y0 - 8.0, 3.0)
    for a, b in f_mark(g.x0 + 2.0, g.y1 + 4.0, 8.0):
        msp.add_line(a, b, dxfattribs={"layer": "TEXT"})
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    for k, w_, b0, b1, bp in side_rows(G):
        if k.startswith("front-view right"):
            dxf_text(msp, "LAND %s (abs left)" % n(w_), G.pocket.x1 + 0.5, 4.0, 1.8)    # clear of MIRROR-REF
        elif k.startswith("front-view left"):
            dxf_text(msp, "LAND %s (abs right)" % n(w_), G.glass.x0 + 0.5, 4.0, 1.8)
    sl = G.slot_bg
    dxf_text(msp, "BEND_SLOT = bend-gap slot %s x %s, through (tails pass here); land %s to the bridge face" % (
        n(sl.w), n(sl.h), n(G.lands()["bottom over the tail span"])), sl.x0, sl.y1 + 1.6, 1.8)
    doc.saveas(path)


def plan(sh, P, C, G, ox, oy):
    V = View(sh, ox, oy, 1.0)
    g = G.flange
    V.rrect(g, ec="k", w=THICK)
    for r in G.strips.values():
        V.rrect(r, fc="#cfeedd", ec=C_TAPE, w=XTHIN, geom=False)
    for pts in G.dabs.values():
        V.poly(pts, fc=C_DAB, ec="none", geom=False)
    for f in ("F1", "F2", "F3", "F4"):
        V.circle(G.F[f]["u"], G.F[f]["v"], G.pad_d / 2.0, ec="k", w=THIN, geom=False, fc="#e9e9e9")
    # land (between the recess wall = lip inner face and the pocket faces)
    V.rrect(G.lip_in, ec="k", w=THIN, fc="#f4f1e6", geom=False)
    V.poly(G.land_inner, ec="k", w=THIN, fc="white", geom=False)
    V.rrect(G.slot_bg, ec="k", w=THIN, fc="#5f6670", geom=False, hatch="////")      # through-opening (GF-2.0)
    for r in (G.lip_out, G.seat_out):
        V.rrect(r, ec="0.4", w=XTHIN, geom=False)
    # bead band
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    o = V.Pa(G.bead_out.boundary(n_arc=16, step=3.0))
    i = V.Pa(G.bead_inn.boundary(n_arc=16, step=3.0))[::-1]
    verts = list(o) + [o[0]] + list(i) + [i[0]]
    codes = [Path.MOVETO] + [Path.LINETO] * (len(o) - 1) + [Path.CLOSEPOLY] + \
            [Path.MOVETO] + [Path.LINETO] * (len(i) - 1) + [Path.CLOSEPOLY]
    sh.ax.add_patch(PathPatch(Path(verts, codes), fc="#8c8c8c", ec="none", zorder=2))
    q = V.Pa(G.bead_cl.boundary(n_arc=16, step=3.0))
    sh.ax.plot(list(q[:, 0]) + [q[0, 0]], list(q[:, 1]) + [q[0, 1]], color="k", lw=lw(XTHIN), ls=(0, (4, 2)),
               zorder=3)
    V.rrect(G.glass, ec=C_REF, w=XTHIN, ls=(0, (4, 1.5)), geom=False)
    V.rrect(G.window, ec=C_REF, w=XTHIN, ls=(0, (1.5, 1.2)), geom=False)
    fm, _ = G.formex()
    V.rrect(fm, ec=C_FMX, w=THIN, ls=(0, (8, 1.5, 1.5, 1.5)), geom=False)
    # pips
    for k, (u, v) in G.pips.items():
        V.circle(u, v, G.pip_d / 2.0, fc=C_PIP, ec=C_PIP, w=XTHIN, geom=False)
        x, y = V.P(u, v)
        su = 1 if u >= 0 else -1
        sv = 1 if v >= 0 else -1
        if abs(abs(v) - G.bead_cl.y1) < 1e-6:          # top / bottom pips: label inside the pocket
            sh.T(x, y - sv * 8.0, "P" + k[3:], fs=6.5, color=C_PIP, weight="bold", va="center", ha="center")
        else:                                            # side pips
            sh.T(x - su * 5.2, y + 3.0, "P" + k[3:], fs=6.5, color=C_PIP, weight="bold", va="center",
                 ha="right" if su > 0 else "left")
    # slots + axes
    cb, _ = G.fastener_cuts()
    for k, f in G.F.items():
        cbp = stadium_pts(f["u"], f["v"], f["au"], f["av"], cb["cb_l"], cb["cb_w"])
        V.poly([(x, y) for x, y in bulge_to_points(cbp, seg_deg=10.0)], fc="#fbe3e0", ec=C_SLOT, w=XTHIN,
               geom=False, z=4, ls=(0, (2, 1)))
        V.poly([(x, y) for x, y, _ in _flat_stadium(G, k)], fc="white", ec=C_SLOT, w=THIN, geom=False, z=4)
        L = G.slot_l / 2.0 + 7.0
        V.centreline((f["u"] - f["au"] * L, f["v"] - f["av"] * L), (f["u"] + f["au"] * L, f["v"] + f["av"] * L),
                     c=C_SLOT)
        x, y = V.P(f["u"], f["v"])
        su = 0 if abs(f["u"]) < 1e-6 else (1 if f["u"] > 0 else -1)
        sv = 0 if abs(f["v"]) < 1e-6 else (1 if f["v"] > 0 else -1)
        if su and sv:
            tx, ty, ha = x + su * 10.5, y + sv * 10.5, ("left" if su > 0 else "right")
        elif sv:
            tx, ty, ha = x + 4.0, y + sv * 4.5, "left"
        else:
            tx, ty, ha = x + su * 5.0, y + 4.0, ("left" if su > 0 else "right")
        sh.T(tx, ty, k, fs=7, weight="bold", color=C_SLOT, ha=ha, va="center")
    # centre lines + datum + orientation
    V.centreline((g.x0 - 3, 0), (g.x1 + 3, 0))
    V.centreline((0, g.y0 - 3), (0, g.y1 + 3))
    x0, y0 = V.P(0, 0)
    sh.T(x0 + 1.5, y0 + 1.2, "glass centre (datum)", fs=6.0)
    top = V.P(0, g.y1)[1]
    left = V.P(g.x0, 0)[0]
    fx, fy = left, top + 4.0
    for a, b in f_mark(0, 0, 7.0):
        sh.L([fx + a[0], fx + b[0]], [fy + a[1], fy + b[1]], w=THICK, geom=False)
    sh.T(fx + 6.0, fy + 0.3, "TOP", fs=6.5, weight="bold")
    # strip length dims
    st, sr = G.strips["top"], G.strips["left"]
    sh.dim_h(*V.P(st.x0, st.y1), *V.P(st.x1, st.y1), top + 5.0, "top / bottom strips %s" % n2(st.w), fs=7)
    sh.dim_v(*V.P(sr.x0, sr.y0), *V.P(sr.x0, sr.y1), left - 5.0, "side strips %s" % n2(sr.h), fs=7)
    # land / bead labels per side (inside the pocket, short leaders)
    rows = {k: (w_, b0, b1, bp) for k, w_, b0, b1, bp in side_rows(G)}
    pk = G.pocket
    sl = G.slot_bg
    lab = [("front-view right (abs left)", (pk.x1, 12.0), (pk.x1 - 3.0, 12.0), "right", ""),
           ("front-view left (abs right)", (pk.x0, 12.0), (pk.x0 + 3.0, 12.0), "left", ""),
           ("top", (-35.0, pk.y1), (-35.0, pk.y1 - 4.0), "left", ""),
           ("bottom over the tail span", (-32.0, sl.y0), (-32.0, sl.y1 + 2.7), "left", ""),
           ("bottom outside the tail span", (-72.0, pk.y0), (-72.0, pk.y0 + 6.5), "left", "")]
    for k, p, t, ha, extra in lab:
        w_, b0, b1, bp = rows[k]
        px, py = V.P(*p)
        tx, ty = V.P(*t)
        sh.L([px, tx], [py, ty], w=XTHIN, geom=False)
        if k == "bottom over the tail span":       # to the bridge pocket face (bend-gap slot edge)
            txt = "land %s, bead -> face %s, -> break edge %s" % (
                n(w_), n(bp), n2(G.break_edge_notes()["land_plane"]))
        else:
            txt = "land %s, bead -> pocket %s%s" % (n(w_), n(bp), extra)
        sh.T(tx + (-0.5 if ha == "right" else 0.5), ty, txt, fs=6.3, ha=ha, va="center", bg="white")
    # the bend-gap slot (through-opening; the tails pass here)
    px, py = V.P(30.0, (sl.y0 + sl.y1) / 2.0)
    tx, ty = V.P(30.0, sl.y1 + 6.7)
    sh.L([px, tx], [py, ty], w=XTHIN, geom=False)
    sh.T(tx + 0.5, ty, "BEND-GAP SLOT %s x %s (through)" % (n(sl.h), n(sl.w)), fs=6.3, va="center",
         weight="bold")
    # labels outside
    return V


def _flat_stadium(G, k):
    from gf_common import bulge_to_points
    return [(x, y, 0) for x, y in bulge_to_points(G.slot(k), seg_deg=10.0)]


def make(out_dir=OUT_DIR):
    P, C = Params(), Choices()
    G = Geom(P)
    base = os.path.join(out_dir, "GF_BondingAids")
    write_dxf(base + ".dxf", P, C, G)
    sh = Sheet()
    sh.frame()
    V = plan(sh, P, C, G, ox=136.0, oy=150.0)
    sh.T(16.0, 279.0, "FRAME FRONT PLAN - bonding and assembly aids   1 : 1  (print A3 at 100 %)", fs=8.5,
         weight="bold")
    sh.T(16.0, 274.5, "Front view = frame front facing you (land up for dispensing). Grey band = bead after "
                      "squeeze; magenta = pips; green = VHB strips; orange = corner dabs; red = slots F1-F4; hatched "
                      "= bend-gap slot.", fs=6.3)
    # ---------------------------------------------------------------- right column: tables
    x = 262.0
    y = 276.0                       # GF-2.0 correction pass: the column needs the room up to the sheet title
    cb_, _ = G.fastener_cuts()
    sh.T(x, y, "FASTENERS F1-F4 (slot %s x %s, counterbore %s x %s, axis to the glass centre)" % (
        n(G.slot_w), n(G.slot_l), n(cb_["cb_w"]), n(cb_["cb_l"])), fs=7, weight="bold")
    rows = [["F", "u", "v", "axis deg", "variants", "front pad"]]
    for k, f in G.F.items():
        rows.append([k, n(f["u"]), n(f["v"]), n(front_angle(f) + 0.0, 2), f["used_by"].split(" (")[0],
                     ("dia %s" % n(G.pad_d)) if f["pad"] else "none"])
    y = sh.table(x, y - 1.0, [0, 8, 26, 44, 60, 113], rows, fs=6.0, widths=146)
    sh.T(x, y - 2.8, "axis deg: front view, from +u counter-clockwise (master: %s from +x, y down)" % "slot_axis_deg",
         fs=5.6, color="0.3")
    y -= 7.0
    sh.T(x, y, "PIPS P1-P8 (stand-offs on the bead centre line)", fs=7, weight="bold")
    prow = [["P", "u", "v", "", "P", "u", "v"]]
    items = list(G.pips.items())
    for j in range(4):
        a = items[j]
        b = items[j + 4]
        prow.append(["P" + a[0][3:], n(a[1][0], 4), n(a[1][1], 4), "", "P" + b[0][3:], n(b[1][0], 4),
                     n(b[1][1], 4)])
    y = sh.table(x, y - 1.0, [0, 8, 26, 46, 52, 60, 78], prow, fs=6.0, widths=146)
    pip_h = P.d("pip_h")
    clr = P.val("pips", "pip_clearance_wc")
    y -= 3.2
    pip_tol = re.search(r"\+-([\d.]+)", P.dnote("pip_h")).group(1)
    pip_dr = re.search(r"([\d.]+) deg draft", P.dnote("pip_d")).group(1)
    sh.T(x, y, "dia %s x %s high (±%s), %s deg draft; top %s below the land; never touch the glass (min %s at "
               "glass_t %s)" % (n(G.pip_d), n(pip_h), pip_tol, pip_dr, n(pip_h), n(clr["%.1f" % P.d("glass_t")]),
                                n(P.d("glass_t"))), fs=5.8)
    # land / bead per side
    y -= 6.0
    sh.T(x, y, "LAND AND BEAD PER SIDE (front view)", fs=7, weight="bold")
    lrow = [["side", "land", "bead from-to", "bead->pocket"]]
    pk_note = P.item("plan_rectangles", "pocket")["note"]
    m_pk = re.search(r"Where the land ends \(Z_LAND \+ ([\d.]+)\) the bead-to-pocket margins are .*?abs left ([\d.]+), "
                     r"abs right ([\d.]+), top ([\d.]+), bottom outside the tail span ([\d.]+); the smallest is over "
                     r"the bridge: ([\d.]+) to the edge of the ([\d.]+) x 45 land break \(([\d.]+) to the pocket-face "
                     r"plane", pk_note)
    assert m_pk, ("master pocket note: at-land margins not found", pk_note)
    pkv = [float(m_pk.group(i)) for i in range(1, 9)]
    P._use("plan_rectangles.pocket.note ~ at-land margins", pkv)
    z_end, brk_edge, face_plane = pkv[0], pkv[5], pkv[7]
    # master land notes: bead -> break edge MEASURED where the land ends (Z_LAND + 0.01, pocket note) and on the LAND
    # PLANE (= A1, the rule value quoted here: 1.36 - 0.30); each compared with its geometry (gf_geom.break_edge_notes)
    be = G.break_edge_notes()
    assert be["ok"], ("master land notes vs land / break geometry", be)
    b_lp, margin = be["land_plane"], round(be["land_plane"] - G.bead_pocket_min, 3)
    assert margin >= 0.0, ("bead -> break edge below the A1 rule", be)
    for k, w_, b0, b1, bp in side_rows(G):
        cell = n(bp) if k != "bottom over the tail span" else "%s (%s to break)" % (n(bp), n2(b_lp))
        lrow.append([k, n(w_), "%s - %s" % (n(b0), n(b1)), cell])
    y = sh.table(x, y - 1.0, [0, 66, 84, 112], lrow, fs=6.0, widths=146)
    dr = (P.level("Z_SEAT") - P.level("Z_LAND")) * math.tan(math.radians(P.val("carried_over_from_v2", "draft")))
    # The clearance pocket is defined at Z_SEAT (0.10 larger per side at the land), the bridge pocket face at Z_LAND.
    # The master pocket note states the margins where the land ends; they are read from it and checked against the
    # lands table + draft (and the break geometry) - a mismatch stops the run.
    at_land = {}
    for k, w_, b0, b1, bp in side_rows(G):
        at_land[k] = bp if k == "bottom over the tail span" else bp - dr
    flat_l = be["flat_land"]
    rows_b = {k: (w_, bp) for k, w_, b0, b1, bp in side_rows(G)}
    assert abs(rows_b["bottom over the tail span"][0] - G.land_break - flat_l) < 1e-6
    assert abs(rows_b["bottom over the tail span"][1] - G.land_break - be["land_plane"]) < 0.006
    assert abs(be["measured"] - brk_edge) < 1e-9 and abs(be["face_plane"] - face_plane) < 1e-9
    calc_m = [at_land["front-view right (abs left)"], at_land["front-view left (abs right)"], at_land["top"],
              at_land["bottom outside the tail span"],
              rows_b["bottom over the tail span"][1] - (G.land_break - z_end), rows_b["bottom over the tail span"][1]]
    for a_, b_ in zip(calc_m, [pkv[1], pkv[2], pkv[3], pkv[4], brk_edge, face_plane]):
        assert abs(round(a_, 2) - b_) < 0.006, ("at-land margins differ from the master pocket note", calc_m, pkv)
    assert abs(pkv[6] - G.land_break) < 1e-9
    for ln in sh.wrap("Land and bead -> pocket at Z_SEAT, where the clearance pocket is defined (%s deg draft); "
                      "where the land ends (Z_LAND + %s) the margins are %s / %s / %s (sides, top) and %s (bottom "
                      "outside the tail span) - master pocket note. Over the tail span the land %s ends at the bridge "
                      "pocket face (defined at the land) with a %s x 45 deg break: bead -> break edge %s on the land "
                      "plane (%s where the land ends), -> face plane %s; A1 bead_pocket_min %s met with %s (verified, "
                      "master). Squeeze-out check: note 5." % (
                          n(P.val("carried_over_from_v2", "draft")), n(z_end), n2(pkv[1]), n2(pkv[2]), n2(pkv[3]),
                          n2(pkv[4]), n(rows_b["bottom over the tail span"][0]), n(G.land_break), n2(b_lp),
                          n2(brk_edge), n2(face_plane), n(G.bead_pocket_min), n2(margin)), 146.0, 5.6):
        y -= 2.6
        sh.T(x, y, ln, fs=5.6, color="0.3")
    # dispense + tape notes
    per = G.bead_cl.perimeter()
    t_bond = P.d("t_bond")
    vol = per * G.bead_w * t_bond / 1000.0
    tri = C("bead_dispense_triangle")
    adh = P.val("bead", "adhesive")
    rng = P.val("bead", "bond_line_range_wc")["%.1f" % P.d("glass_t")]
    tape = P.text("tape_and_gasket", "tape")
    dab = P.text("tape_and_gasket", "corner_seal")
    sl = G.strip_len
    _, fmx_i = G.formex()
    notes = [
        "Bead: %s. After squeeze %s wide x %s (bond line set by the flush jig J2; worst case %s-%s at glass_t %s), "
        "%s-%s inside the glass edge, >= %s to every pocket face." % (adh, n(G.bead_w), n(t_bond), n(rng[0]),
                                                                      n(rng[1]), n(P.d("glass_t")), n(G.bead_edge),
                                                                      n(G.bead_edge + G.bead_w),
                                                                      n(G.bead_pocket_min)),
        "Dispense on the primed land along the bead centre line (dashed, %s inside the glass edge): path %s mm, "
        "volume after squeeze %s mL; triangular nozzle bead about %s wide x %s high (%s mm2 >= %s mm2)." % (
            n(G.bead_edge + G.bead_w / 2.0), n(per, 1), n(vol, 2), n(tri[0]), n(tri[1]), n(tri[0] * tri[1] / 2, 2),
            n(G.bead_w * t_bond)),
        "Tape (S4 / R4): %s. Strips on the flange %s-%s outside the glass edge: top/bottom %s, sides %s, ending %s "
        "before the corner pads; liner stays on until mounting." % (tape, n(G.tape_in.y1 - G.glass.y1),
                                                                      n(G.tape_out.y1 - G.glass.y1),
                                                                      n2(sl["top_bottom"]), n2(sl["sides"]),
                                                                      n(G.tape_margin)),
        "Corner dabs (orange): %s; applied after the liner is removed, just before mounting." % dab,
        "BOTTOM LAND over the tail span: %s from the bridge pocket face to the glass edge, %s x 45 deg break on its "
        "inner edge; the bead inner edge is %s from the break edge (land plane; >= %s, margin only %s) and %s from "
        "the pocket-face plane. REQUIRED CHECK on the first article and on every bonding batch at the bridge: no "
        "adhesive may reach the break edge or the bend-gap slot over the whole %s - reject otherwise. Dispense on "
        "the centre line only." % (
            n(rows_b["bottom over the tail span"][0]), n(G.land_break), n2(b_lp), n(G.bead_pocket_min), n2(margin),
            n2(face_plane), n(G.slot_bg.w)),
        "F1-F4 have the dia %s front pads (hard stops on the sheet); there are no mid-side fasteners (S8 "
        "withdrawn at %s)." % (n(G.pad_d), s8_withdrawn_rev(P)),
        "Formex sheet (purple, reference only; master plan_rectangles 'formex', %s): panel outline - %s per side, "
        "R%s, %s thick (Z %s to %s), PSA on the shelf front face before the panel goes in." % (
            fmx_i["status"], n(fmx_i["inset"]), n(fmx_i["R"]), n(round(fmx_i["z"][1] - fmx_i["z"][0], 3)),
            n(fmx_i["z"][0]), n(fmx_i["z"][1])),
    ]
    y -= 3.0
    y = sh.notes(x, y, 146.0, notes, fs=5.9, head="DISPENSING / TAPE", head_fs=7.0, gap=0.4)
    g2 = G.g2
    js = P.val("jig_and_mounting_shims", "J2_glass_centring_shims")            # GF-1.1 round 4
    ms = P.val("jig_and_mounting_shims", "sheet_mounting_shims")
    ms_n = C("j2_shim")["per_size"]
    rule = {"en": P.val("jig_and_mounting_shims", "shim_rule") + "; " + C("shim_rule")["en_extra"]}
    fmt = lambda L: " / ".join("%.2f" % x for x in L)
    seq = [
        "J1 (GF-D31): optical bond panel -> glass, LOCA %s ±%s (hard stops), active alignment of the print window "
        "to the lit AA." % (n(P.d("t_opt"), 2), __import__("re").search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1)),
        "Formex (PSA) onto the shelf front face of the frame, before the panel goes in.",
        "Prime the land, dispense the bead (this sheet). Prime the strips zone on the flange (VHB primer).",
        "J2 (GF-D30): glass + panel face-down on the plate; pull the 3 stop pins; set 8 PTFE centring shims "
        "against the glass edges (graded set %s: %s); fold both tails up at the panel edge (%s straight, R%s) and "
        "hold them vertical on the guide card in the tail holder TH; lower the frame on the 4 pins - the tails "
        "pass the %s bend-gap slot without touching the bead - until the lip top lands on the plate; weight on the "
        "flange (GF-D30 sheet 2)." % (fmt(js), rule["en"], n(P.d("tail_straight_l0")), n(P.d("tail_R_in_min")),
                                      n(G.g_bend)),
        "Cure: %s." % C("cure"),
        "Check: %s; REQUIRED: no adhesive on the land-break edge or in the bend-gap slot (see note 5)." %
        C("j2_checks"),
        "After the cure (card and TH already removed, GF-D30 sheet 2): fold each tail over the R%s bridge nose into "
        "its compartment (seen from the back: CTP left of the divider rib, TFT right), never tighter than the nose. "
        "Apply the four VHB strips (this sheet), liner on. PCB on the 9 bosses, tails into J10 / J11." % (
            n(G.nose_R)),
        "Mounting: %s." % C("mount_procedure").format(shims="graded set %s, %d of each: %s" % (
            fmt(ms), ms_n, rule["en"])),
        "Inspection: %s." % C("flush_check"),
    ]
    y -= 2.0
    y = sh.notes(x, y, 146.0, seq, fs=5.9, head="ASSEMBLY SEQUENCE (concept sec. 6)", head_fs=7.0, gap=0.4)
    # gap acceptance limits (lead round-3 addition D; drafting_choices gap_acceptance)
    ga = C("gap_acceptance")
    # bottom-left, under the plan (left of the title block)
    xg, yg = 16.0, 49.0
    sh.T(xg, yg, "GAP ACCEPTANCE  (finished module, feeler gauge, %d °C, every side and corner; rule unchanged at "
                 "%s)" % (ga["temp_C"], P.revision), fs=7.0, weight="bold")
    rows = [["gap", "when", "sides", "corners"],
            ["g2  glass edge - lip inner face (nominal %.2f)" % G.g2, "step 6, after the J2 cure",
             "%.2f - %.2f" % tuple(ga["g2_sides"]), ga["corners"]["en"]],
            ["g1  lip outer face - cut-out edge (nominal %.2f)" % G.g1, "step 9, after mounting",
             "%.2f - %.2f" % tuple(ga["g1_sides"]), ga["corners"]["en"]]]
    assert abs(ga["corner_max"] - float(ga["corners"]["en"].split()[-1])) < 1e-9
    yg = sh.table_wrapped(xg, yg - 1.2, [74.0, 44.0, 22.0, 96.0], rows, fs=6.0)
    # derivation from the tolerances (worst case, part centred), for the record
    o_t = P.val("drawing_tolerances.glass", "outline_tol")
    o_f = P.num("drawing_tolerances.glass", r"\+-([\d.]+) is the accepted fallback", name="outline_tol")
    c_t = P.val("drawing_tolerances.sheet", "cut_out_tol")
    l_t = C("frame_lip_outline_tol")
    g2a = (G.g2 - (o_t + l_t) / 2.0, G.g2 + (o_t + l_t) / 2.0)
    g2b = (G.g2 - (o_f + l_t) / 2.0, G.g2 + (o_f + l_t) / 2.0)
    g1a = (G.g1 - (c_t + l_t) / 2.0, G.g1 + (c_t + l_t) / 2.0)
    smax = max(js)
    der = ("Sides, worst case with the part centred: g2 = %.2f ± (glass + lip outline)/2 = %.2f-%.2f with the glass "
           "at ±%s (%.2f-%.2f at ±%s); g1 = %.2f ± (cut-out + lip outline)/2 = %.2f-%.2f (cut-out ±%s, lip outline ±%s "
           "on size = GF-D50 proposal [P]). The shim rule centres to ±0.05 per side while the total clearance across "
           "is below %.2f (2 x %.2f + 0.10); above that, centre by eye and check against the limits." % (
               G.g2, g2a[0], g2a[1], n(o_t), g2b[0], g2b[1], n(o_f), G.g1, g1a[0], g1a[1], n(c_t), n(l_t),
               2 * smax + 0.10, smax))
    gtv = gap_temperatures(P)          # verified values (master gaps notes); raises if missing
    der += (" Over temperature (master, verified at %s; nominal sides, 50 / 70 ppm): g2 -20 °C %s / %s, +70 °C %s / "
            "%s; g1 hot (frame +70, sheet +50 °C) %s / %s, -20 °C %s / %s. At the tolerance limits with 70 ppm g2 can "
            "touch cold (%s) and g1 hot (%s) - harmless (master gaps notes)." % (
                P.revision, n2(gtv["g2_cold_50"]), n2(gtv["g2_cold_70"]), n2(gtv["g2_hot_50"]),
                n2(gtv["g2_hot_70"]), n2(gtv["g1_hot_50"]), n2(gtv["g1_hot_70"]), n2(gtv["g1_cold_50"]),
                n2(gtv["g1_cold_70"]), n2(gtv["g2_touch_wc"]), n2(gtv["g1_touch_wc"])))
    for ln in sh.wrap(der, 236.0, 5.6):
        yg -= 2.6
        sh.T(xg, yg, ln, fs=5.6, color="0.3")
    today = datetime.date.today().isoformat()
    sh.title_block({
        "title": "BONDING AND ASSEMBLY AIDS - GF",
        "subtitle": "frame front plan: land, bead, pips, VHB strips, corner dabs, F1-F4, bend-gap slot, Formex",
        "source": "all dimensions (Formex included) from %s" % master_ref(P),
        "project": "in-house use; files: GF_BondingAids.dxf (front view) + this sheet",
        "change": "%s. Bead path %s, strips %s / %s; bottom land %s + %s break: bead %s to the break edge (A1 met); "
                  "squeeze-out check at the bridge required." % (
                      rev_note(P), n(per, 1), n2(sl["top_bottom"]), n2(sl["sides"]),
                      n(rows_b["bottom over the tail span"][0]), n(G.land_break), n2(b_lp)),
        "dwg": "GF-D20", "rev": P.revision, "scale": "1:1", "date": today, "drawn": "make_bonding.py",
    }, w=146.0, h=40.0)
    issues = sh.check_layout()
    sh.save(base + ".pdf", base + ".png", dpi=200)
    return {"files": [base + ".dxf", base + ".pdf", base + ".png"], "layout_issues": issues,
            "params_used": dict(sorted(P.used.items())), "choices_used": C.used, "notes": notes, "lowest_y": round(y, 1),
            "bead_path_mm": round(per, 2), "bead_volume_ml": round(vol, 3)}


if __name__ == "__main__":
    r = make()
    print("issues:", len(r["layout_issues"]), "lowest", r["lowest_y"])
    for i in r["layout_issues"]:
        print("   ", i)
