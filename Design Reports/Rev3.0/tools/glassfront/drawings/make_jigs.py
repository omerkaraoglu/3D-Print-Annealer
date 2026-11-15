"""Jig drawings for a local machinist (aluminium plate): J2 flush plate and J1 optical-bonding alignment fixture.
A3 sheets (PDF + PNG) and DXFs. Product positions come from the master; jig values from drafting_choices.json.

  <venv>/Scripts/python.exe make_jigs.py   -> Mechanical/Rev3.0_GlassFront/drawings/GF_Jig_J2.*, GF_Jig_J1.*
"""
import datetime
import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import (Params, Choices, Rect, OUT_DIR, n, n2, tr, new_dxf, dxf_poly, dxf_rect, dxf_text,
                       bulge_to_points)
from gf_geom import Geom
from gf_draft import Sheet, View, THICK, THIN, XTHIN, MM_PER_PT, lw

C_REF, C_PIN, C_STOP, C_VAC = "#3b6fb6", "#c0392b", "#2e8b57", "#7b4fa0"


def stops_uv(G, C):
    """three glass stops (centre of the stop pin, front view): two on the top edge, one on the front-view left edge"""
    d = C("j2_stop_d")
    su = C("j2_stop_u")
    g = G.glass
    return {"S1": (su, g.y1 + d / 2.0), "S2": (-su, g.y1 + d / 2.0), "S3": (g.x0 - d / 2.0, 0.0)}


# ================================================================================================================ J2
def j2_dxf(path, P, C, G):
    pl = C("j2_plate")
    gw, gd_, gi, gp = C("j2_groove")
    M = lambda u, v: (-u, v)                       # plate view: seen from above, glass face down -> mirrored
    MR = lambda r: Rect(-r.x1, -r.x0, r.y0, r.y1, r.R, r.name)
    doc, msp = new_dxf([("PLATE", 7, "CONTINUOUS"), ("PIN_HOLES", 1, "CONTINUOUS"), ("STOP_HOLES", 3, "CONTINUOUS"),
                        ("GROOVE_OPT", 200, "DASHED"), ("FLAT_ZONE", 6, "DASHDOT"), ("REF", 5, "DASHED"),
                        ("TEXT", 7, "CONTINUOUS")])
    dxf_rect(msp, Rect(-pl[0] / 2, pl[0] / 2, -pl[1] / 2, pl[1] / 2, 5.0), "PLATE")
    for k in ("F1", "F2", "F3", "F4"):
        f = G.F[k]
        msp.add_circle(M(f["u"], f["v"]), C("j2_pin_d") / 2.0, dxfattribs={"layer": "PIN_HOLES"})
        dxf_text(msp, "pin " + k, M(f["u"], f["v"])[0] + 4, M(f["u"], f["v"])[1] + 4, 2.5)
    for k, (u, v) in stops_uv(G, C).items():
        msp.add_circle(M(u, v), C("j2_stop_d") / 2.0, dxfattribs={"layer": "STOP_HOLES"})
        dxf_text(msp, k, M(u, v)[0] + 3, M(u, v)[1] + 3, 2.5)
    gr = MR(G.glass.offset(-gi))
    gr.R = max(gr.R, gw)
    dxf_rect(msp, gr.offset(gw / 2.0), "GROOVE_OPT")
    dxf_rect(msp, gr.offset(-gw / 2.0), "GROOVE_OPT")
    dxf_rect(msp, MR(G.lip_out.offset(3.0)), "FLAT_ZONE")
    for r in (G.glass, G.lip_out, G.flange):
        dxf_rect(msp, MR(r), "REF")
    dxf_text(msp, "GF JIG J2 FLUSH PLATE - working face seen from ABOVE (glass lies face 1 down: left/right mirrored "
             "to the front view). Origin = glass centre. mm.", -pl[0] / 2, -pl[1] / 2 - 8, 3.0)
    doc.saveas(path)


def j2_sheet(path_base, P, C, G):
    sh = Sheet()
    sh.frame()
    pl = C("j2_plate")
    gw, gd_, gi, gp = C("j2_groove")
    flat, ra, tolp = C("j2_flatness"), C("j2_ra"), C("j2_pos_tol")
    pin_d, pin_h, pin_p = C("j2_pin_d"), C("j2_pin_proud"), C("j2_pin_press")
    st_d, st_h = C("j2_stop_d"), C("j2_stop_proud")
    pdt = C("j2_pin_detail")
    shim = C("j2_shim")                                   # shim body w x h, count per size (drafting choice)
    shim_sizes = P.val("jig_and_mounting_shims", "J2_glass_centring_shims")    # GF-1.1 round 4
    rule = {"en": P.val("jig_and_mounting_shims", "shim_rule") + "; " + C("shim_rule")["en_extra"],
            "tr": C("shim_rule")["tr"]}
    sizes = " / ".join("%.2f" % x for x in shim_sizes)
    V = View(sh, 100.0, 176.0, 0.5, mirror=True)       # x = -u
    plate = Rect(-pl[0] / 2, pl[0] / 2, -pl[1] / 2, pl[1] / 2, 5.0)
    V.rrect(plate, ec="k", w=THICK)
    fz = G.lip_out.offset(3.0)
    V.rrect(fz, ec="#b0308f", w=THIN, ls=(0, (8, 1.5, 1.5, 1.5)), geom=False)
    for r, st in ((G.flange, (0, (6, 2))), (G.lip_out, (0, (2, 1.5))), (G.glass, (0, (4, 1.5)))):
        V.rrect(r, ec=C_REF, w=XTHIN, ls=st, geom=False)
    gr = G.glass.offset(-gi)
    gr.R = max(gr.R, gw)
    V.rrect(gr, ec=C_VAC, w=THIN, ls=(0, (3, 1.5)), geom=False)
    V.centreline((-pl[0] / 2 - 3, 0), (pl[0] / 2 + 3, 0))
    V.centreline((0, -pl[1] / 2 - 3), (0, pl[1] / 2 + 3))
    for k in ("F1", "F2", "F3", "F4"):
        f = G.F[k]
        x, y = V.P(f["u"], f["v"])
        sh.circle(x, y, pin_d / 2.0 * 0.5 + 0.4, ec=C_PIN, w=THIN, fc="#f6d4d0")
        sh.T(x + (2.5 if x > 100 else -2.5), y + (2.5 if y > 176 else -4.6), "pin " + k, fs=6.3, color=C_PIN,
             ha="left" if x > 100 else "right")
    for k, (u, v) in stops_uv(G, C).items():
        x, y = V.P(u, v)
        sh.circle(x, y, st_d / 2.0 * 0.5 + 0.3, ec=C_STOP, w=THIN, fc="#d4efdc")
        if k == "S3":
            sh.T(x + 2.6, y + 1.2, k, fs=6.5, color=C_STOP, weight="bold")
        else:
            sh.T(x, y - 4.2, k, fs=6.5, color=C_STOP, weight="bold", ha="center")
    # dims (paper), positions to the datum
    F1, F2, F4 = G.F["F1"], G.F["F2"], G.F["F4"]
    top = V.P(0, plate.y1)[1]
    xa, ya = V.P(F1["u"], F1["v"])
    xb, yb = V.P(F2["u"], F2["v"])
    sh.dim_h(xa, ya, xb, yb, top + 6.0, "%s ±%s" % (n2(abs(F1["u"] - F2["u"])), n(tolp)), fs=7)
    left = V.P(plate.x1, 0)[0]
    xa, ya = V.P(F1["u"], F4["v"])
    xb, yb = V.P(F1["u"], F1["v"])
    sh.dim_v(xa, ya, xb, yb, left - 6.0, "%s ±%s" % (n2(abs(F1["v"] - F4["v"])), n(tolp)), fs=7)
    S = stops_uv(G, C)
    xa, ya = V.P(*S["S1"])
    xb, yb = V.P(*S["S2"])
    sh.dim_h(xa, ya, xb, yb, top + 13.0, "S1-S2 %s ±%s" % (n(abs(S["S1"][0] - S["S2"][0])), n(tolp)), fs=7)
    bot = V.P(0, plate.y0)[1]
    x0, y0 = V.P(0, 0)
    xs, ys = V.P(*S["S3"])
    sh.dim_h(x0, y0, xs, ys, bot - 7.0, "%s ±%s (S3 centre to datum)" % (n(abs(S["S3"][0])), n(tolp)), fs=6.5)
    right = V.P(plate.x0, 0)[0]
    sh.dim_v(*V.P(0, 0), *V.P(*S["S1"]), right + 6.0, "%s ±%s" % (n(S["S1"][1]), n(tolp)), fs=6.5, side="right")
    sh.dim_h(*V.P(plate.x1, plate.y1), *V.P(plate.x0, plate.y1), top + 20.0, "%s (free)" % n(pl[0], 0), fs=6.5)
    sh.dim_v(*V.P(plate.x0, plate.y0), *V.P(plate.x0, plate.y1), right + 14.0, "%s (free)" % n(pl[1], 0), fs=6.5,
             side="right")
    sh.T(x0 + 1.2, y0 + 1.2, "datum = glass centre", fs=6.0)
    sh.T(16.0, 279.0, "J2 FLUSH PLATE - working face seen from ABOVE   1 : 2", fs=8.5, weight="bold")
    sh.T(16.0, 274.5, "Glass lies face 1 (front) DOWN, so left / right are mirrored to the front view; the pattern is "
                      "symmetric. Chin towards the operator (bottom).", fs=6.2)
    # legend
    yl = 99.0
    for col, ls, t in ((C_REF, (0, (4, 1.5)), "glass / lip outer / flange outlines (reference, frame lowered "
                                                "face down)"),
                       ("#b0308f", (0, (8, 1.5, 1.5, 1.5)), "FLAT ZONE = lip outer + 3: flatness %s, Ra %s" % (
                           n(flat), n(ra))),
                       (C_VAC, (0, (3, 1.5)), "OPTIONAL vacuum groove %s wide x %s deep, %s inside the glass edge, "
                                              "port dia %s" % (n(gw), n(gd_), n(gi), n(gp)))):
        sh.ax.plot([16, 26], [yl + 0.8, yl + 0.8], color=col, lw=lw(THIN), ls=ls)
        sh.T(28.0, yl, t, fs=6.0, color=col)
        yl -= 3.2
    # hole table
    rows = [["ID", "x (plate)", "y (plate)", "feature", "tol."]]
    for k in ("F1", "F2", "F3", "F4"):
        f = G.F[k]
        rows.append(["pin " + k, n(-f["u"]), n(f["v"]), "pin dia %s h6 x %s proud, pressed %s deep (hole N7)" % (
            n(pin_d), n(pin_h), n(pin_p)), "±%s" % n(tolp)])
    for k, (u, v) in S.items():
        rows.append([k, n(-u), n(v), "hole dia %s H7 x %s; stop pin ISO 2338 %s h8 x %s, %s proud, removable" % (
            n(st_d), n(pdt[2], 0), n(st_d, 0), n(pdt[3], 0), n(st_h)), "±%s" % n(tolp)])
    sh.T(16.0, 86.0, "HOLES (plate coordinates: x = -u, y = v, from the datum)", fs=7, weight="bold")
    y = sh.table(16.0, 85.0, [0, 16, 34, 52, 172], rows, fs=6.2, widths=185)
    # section B-B (schematic, 3:1): through a corner fastener, unrolled; plate at the bottom, depth d upwards
    k2 = 3.0
    xs0, yp = 248.0, 222.0
    Sx = lambda s, d: (xs0 + k2 * s, yp + k2 * d)
    gt = P.d("glass_t")
    Zg = P.level("Z_GLASS_FRONT")
    D = lambda nm: P.level(nm) - Zg
    d_sb, d_ff, d_fb, d_gb, d_land, d_sw, d_ctp, d_tube = (D("Z_SHEET_BACK"), D("Z_FLANGE_FRONT"),
                                                            D("Z_FLANGE_BACK"), D("Z_GLASS_BACK"), D("Z_LAND"),
                                                            D("Z_STEPWALL_BACK"), D("Z_CTP_FRONT"), D("Z_TUBE_TOP"))
    g2, lw_ = G.g2, G.lip_w
    s_lip1, s_ring = g2 + lw_, g2 + lw_ + G.seat_w
    land = G.glass.y1 - G.pocket.y1
    sF = G.fast_off
    rp = G.pad_d / 2.0
    hw = G.slot_w / 2.0
    sL, sR = -land - 1.5, sF + rp + 1.0
    poly = lambda pts, **kw: sh.poly([Sx(*p) for p in pts], **kw)
    poly([(sL - 1, 0), (sR + 1, 0), (sR + 1, -3.0), (sL - 1, -3.0)], fc="#dfe3e8", ec="k", w=THICK, hatch="////")
    ps = -(G.glass.y1 - G.panel.y1)
    poly([(sL, 0), (0, 0), (0, gt), (sL, gt)], fc="#cfe8f3", ec="k", w=THIN)
    poly([(sL, gt), (ps, gt), (ps, d_ctp), (sL, d_ctp)], fc="#f6e7b4", ec="0.4", w=XTHIN, geom=False)
    poly([(sL, d_ctp), (ps, d_ctp), (ps, d_sw + 1.0), (sL, d_sw + 1.0)], fc="#e3e3e3", ec="0.4", w=XTHIN, geom=False)
    poly([(-(G.bead_edge + G.bead_w), gt), (-G.bead_edge, gt), (-G.bead_edge, d_land),
          (-(G.bead_edge + G.bead_w), d_land)], fc="#3a3a3a", ec="k", w=XTHIN, geom=False)
    # frame: lip, step wall, land plate, flange with the corner pad and the tube, cut by the slot (section along
    # the slot axis: slot half-length, counterbore half-length, coring groove r_in..r_out from the tube top)
    cb, co = G.fastener_cuts()
    hl, cl = G.slot_l / 2.0, cb["cb_l"] / 2.0
    d_cb = d_sb + cb["cb_floor_F1-F4"]
    fr = [(g2, 0), (s_lip1, 0), (s_lip1, d_sb), (sF - cl, d_sb), (sF - cl, d_cb), (sF - hl, d_cb),
          (sF - hl, d_tube), (sF - rp, d_tube), (sF - rp, d_fb), (s_ring, d_fb), (s_ring, d_sw), (-land, d_sw),
          (-land, d_land), (g2, d_land)]
    poly(fr, fc="#a7acb3", ec="k", w=THIN, hatch="\\\\\\\\")
    poly([(sF + cl, d_sb), (sF + rp, d_sb), (sF + rp, d_ff), (sR, d_ff), (sR, d_fb), (sF + rp, d_fb),
          (sF + rp, d_tube), (sF + hl, d_tube), (sF + hl, d_cb), (sF + cl, d_cb)], fc="#a7acb3", ec="k", w=THIN,
         hatch="\\\\\\\\")
    for sg in (-1, 1):
        a_, b_ = sF + sg * co["core_r_in"], sF + sg * co["core_r_out"]
        poly([(a_, d_tube - co["core_depth"]), (b_, d_tube - co["core_depth"]), (b_, d_tube + 0.05),
              (a_, d_tube + 0.05)], fc="white", ec="k", w=XTHIN)
    pr = pin_d / 2.0
    poly([(sF - pr, -2.6), (sF + pr, -2.6), (sF + pr, pin_h - 0.5), (sF + pr - 0.5, pin_h),
          (sF - pr + 0.5, pin_h), (sF - pr, pin_h - 0.5)], fc="#f6d4d0", ec=C_PIN, w=THIN)
    for s in (sL, sR):
        sh.L([Sx(s, -3.3)[0]] * 2, [Sx(s, -3.3)[1], Sx(s, d_sw + 1.0)[1]], w=XTHIN, c="0.3", geom=False,
             dashes=(1, 1.5))
    sh.T(*Sx(sL + 0.4, -1.5), "J2 PLATE: working face = flush plane", fs=6.0, allow_geom=True, bg="white",
         va="center")
    sh.T(*Sx(sL / 2.0, gt / 2.0), "glass, face 1 down", fs=6.0, ha="center", va="center", allow_geom=True)
    sh.T(*Sx(sF + 3.0, d_tube + 1.2), "pad, counterbore %s x %s, slot %s x %s, tube with coring groove" % (
        n(cb["cb_w"]), n(cb["cb_l"]), n(G.slot_w), n(G.slot_l)), fs=6.0, ha="center")
    # leaders to the right
    xr = Sx(sR + 1, 0)[0] + 4.0
    lead = [((sF + pr, pin_h * 0.55), 6.0, "pin dia %s, %s proud, in the radial slot" % (n(pin_d), n(pin_h))),
            ((sF + rp - 2.0, d_sb), 3.0, "corner pad %s above the plate (sheet back later)" % n(d_sb))]
    for (s, d), dy, txt in lead:
        sh.leader(*Sx(s, d), xr, Sx(0, dy)[1], txt, fs=6.0, head="arrow")
    yb_ = Sx(0, -3.0)[1]
    sh.leader(*Sx(0.9, 0.0), Sx(3.5, 0)[0], yb_ - 5.0, "lip top ON the plate", fs=6.0, head="arrow")
    sh.leader(*Sx(-0.4, 0.0), Sx(-1.5, 0)[0], yb_ - 5.0, "glass front ON the plate", fs=6.0, head="arrow",
              ha="right")
    sh.leader(*Sx(-2.9, (gt + d_land) / 2.0), Sx(sL, 0)[0] + 2.0, Sx(0, d_sw + 1.8)[1],
              "bead: gap set by the plate", fs=6.0, head="arrow")
    sh.dim_v(*Sx(sL, 0), *Sx(sL, d_sb), Sx(sL, 0)[0] - 3.0, n(d_sb), fs=6.0)
    sh.dim_v(*Sx(sL, d_sb), *Sx(sL, d_ff), Sx(sL, 0)[0] - 3.0, None, arrows="out")
    sh.T(Sx(sL, 0)[0] - 5.0, Sx(0, d_ff + 2.2)[1], "flange %s" % n(d_ff), fs=6.0, ha="right")
    sh.T(Sx(sL, 0)[0], Sx(0, d_sw + 5.5)[1], "SECTION B-B through a corner fastener (schematic)  3 : 1", fs=7.5,
         weight="bold")
    # notes
    J2_en = [
        "AUTHORITATIVE for J2: this sheet supersedes the jig text in concept sec. 6 - pins dia %s in the %s x %s radial "
        "slots (not dia 6 holes), a GRADED set of PTFE glass-centring shims %s (not a single 0.40 or 0.30), glass "
        "stops removable (a fixed stop stands where the lip lands)." % (n(pin_d), n(G.slot_w), n(G.slot_l), sizes),
        "Material: %s, %s thick (free, >= 15); outline free (flange + >= 25 per side), corners free." % (
            C("j2_plate_material"), n(pl[2], 0)),
        "WORKING FACE = FLUSH PLANE: the glass front AND the frame lip top rest on it. Flatness %s over the FLAT "
        "ZONE, Ra <= %s (fly-cut or surface ground); no dents or scratches in the zone." % (n(flat), n(ra)),
        "No film, tape or label on the zone (or one film of constant thickness under BOTH glass and lip): anything "
        "under the glass only becomes a flush error. Remove the glass's protective film before bonding.",
        "4 pins at F1-F4: dia %s h6 (turned steel), %s proud ±%s, %s x 45 chamfer, pressed %s deep; they only "
        "locate the frame roughly in its radial slots (%s per side across)." % (
            n(pin_d), n(pin_h), n(pdt[0]), n(pdt[1]), n(pin_p), n((G.slot_w - pin_d) / 2.0)),
        "3 stop holes S1-S3: dia %s H7 x %s for removable stop pins (%s proud). Place the glass against S1-S3, then "
        "PULL the pins before the frame comes down (the lip lands where the stops stand)." % (
            n(st_d), n(pdt[2], 0), n(st_h)),
        "Positions of pins and stop holes ±%s to the datum (glass centre); everything else free, ISO 2768-m." %
        n(tolp),
        "Use: glass + panel face down against S1-S3 (vacuum on if fitted), pull the stops, stand 8 PTFE shims "
        "%s x %s against the glass edges (2 per side), from the set %s (%d of each size): %s. Lower the frame on "
        "the pins until the lip lands on the plate, %s kg ring weight on the flange back, cure, check g2 against the "
        "acceptance limits on GF-D20." % (n(shim["w"], 0), n(shim["h"], 0), sizes, shim["per_size"],
                                         rule["en"].upper(), n(C("j2_weight"), 0)),
    ]
    J2_tr = [
        "Bu resim J2 için GEÇERLİ olandır; konsept §6 metninin yerine geçer: Ø6 delik değil, %s x %s radyal yuvalarda "
        "Ø%s pim; kademeli PTFE şim takımı %s; sökülebilir cam dayamaları." % (n(G.slot_w), n(G.slot_l), n(pin_d),
                                                                           sizes),
        "Malzeme: %s, kalınlık %s (serbest, >= 15); dış ölçüler ve köşeler serbest." % (
            C("j2_plate_material").replace("cast tooling plate", "döküm kalıp plakası").replace(
                "stress-relieved", "gerilim giderilmiş").replace("or", "veya"), n(pl[2], 0)),
        "ÇALIŞMA YÜZEYİ: cam ön yüzü ve çerçeve dudağı aynı yüzeye oturur. DÜZ BÖLGEDE düzlemsellik %s mm, Ra <= %s "
        "(alın frezesi veya taşlama); çizik ve ezik olmayacak." % (n(flat), n(ra)),
        "4 pim (F1-F4): Ø%s h6, %s ±%s mm dışarıda, %s x 45° pah, %s mm preslenmiş." % (
            n(pin_d), n(pin_h), n(pdt[0]), n(pdt[1]), n(pin_p)),
        "3 dayama deliği S1-S3: Ø%s H7 x %s, sökülebilir dayama pimleri (%s mm dışarıda)." % (
            n(st_d), n(pdt[2], 0), n(st_h)),
        "Pim ve delik konumları referansa göre ±%s mm; diğer ölçüler serbest, ISO 2768-m." % n(tolp),
        "Kullanım: cam kenarlarına 8 PTFE şim %s x %s (her kenarda 2), %s takımından (her ölçüden %d adet): %s." % (
            n(shim["w"], 0), n(shim["h"], 0), sizes, shim["per_size"], rule["tr"].replace("i", "İ").upper()),
    ]
    ye = sh.notes(212.0, 185.0, 98.0, J2_en, fs=6.0, head="NOTES", head_fs=7.2, gap=0.45)
    yt = sh.notes(313.0, 185.0, 96.0, [tr(t) for t in J2_tr], fs=6.0, head="NOTLAR (Türkçe)", head_fs=7.2, gap=0.45)
    sh.title_block({
        "title": "JIG J2 - FLUSH PLATE (glass + panel -> frame)",
        "subtitle": "aluminium plate for a local machinist  /  yapıştırma fikstürü J2 (alüminyum plaka)",
        "source": "product positions from Rev3.0_GlassFront_params.json %s; jig values: drafting_choices.json" %
                  P.revision,
        "project": "files: GF_Jig_J2.dxf (plate view, mm) + this sheet",
        "change": "%s round 3: graded PTFE glass-centring shims %s with the size rule (replaces the single 0.30); "
                  "this sheet is authoritative for J2 (supersedes the concept sec. 6 jig text)." % (P.revision,
                                                                                                    sizes),
        "dwg": "GF-D30", "rev": P.revision, "scale": "1:2, 3:1", "date": datetime.date.today().isoformat(),
        "drawn": "make_jigs.py",
    }, h=42.0)
    issues = sh.check_layout()
    sh.save(path_base + ".pdf", path_base + ".png", dpi=200)
    return issues, J2_en, J2_tr, [round(ye, 1), round(yt, 1), round(y, 1)]


# ================================================================================================================ J1
def j1_geom(P, C, G):
    base = C("j1_base")
    top = C("j1_top")
    gd, gu, gv = C("j1_guide")
    cm = C("j1_carrier_margin")
    pc = G.panel
    carrier = pc.offset(cm, "carrier")
    carrier.R = 3.0
    nest = pc.offset(C("j1_nest_clr"), "nest")
    om = C("j1_opening_margin")
    opening = G.window.offset(om, "opening")
    opening.R = 2.0
    tp = G.tail_pocket
    fpc = Rect(tp.x0, tp.x1, carrier.y0 - 2.0, pc.y0 + 1.0, 0.0, "fpc_slot")
    gi = C("j1_groove_inset")
    groove = G.glass.offset(-gi, "groove")
    groove.R = max(groove.R, 2.0)
    guides = [(su * gu, sv * gv) for su in (1, -1) for sv in (1, -1)]
    return dict(base=Rect(-base[0] / 2, base[0] / 2, -base[1] / 2, base[1] / 2, 5.0, "base"),
                top=Rect(-top[0] / 2, top[0] / 2, -top[1] / 2, top[1] / 2, 5.0, "top_plate"), guide_d=gd,
                guides=guides, carrier=carrier, nest=nest, opening=opening, fpc=fpc, groove=groove)


def j1_dxf(path, P, C, G, J):
    doc, msp = new_dxf([("BASE", 7, "CONTINUOUS"), ("GUIDES", 1, "CONTINUOUS"), ("TOP_PLATE", 4, "CONTINUOUS"),
                        ("TOP_STOPS", 3, "CONTINUOUS"), ("TOP_GROOVE", 200, "DASHED"), ("CARRIER", 6, "CONTINUOUS"),
                        ("REF", 5, "DASHED"), ("TEXT", 7, "CONTINUOUS")])
    dxf_rect(msp, J["base"], "BASE")
    for (u, v) in J["guides"]:
        msp.add_circle((u, v), J["guide_d"] / 2.0, dxfattribs={"layer": "GUIDES"})
    dxf_rect(msp, J["top"], "TOP_PLATE")
    dxf_rect(msp, J["opening"], "TOP_PLATE")
    for k, (u, v) in stops_uv(G, C).items():
        msp.add_circle((u, v), C("j2_stop_d") / 2.0, dxfattribs={"layer": "TOP_STOPS"})
        dxf_text(msp, k, u + 3, v + 3, 2.5)
    dxf_rect(msp, J["groove"], "TOP_GROOVE")
    for r in (J["carrier"], J["nest"], J["fpc"]):
        dxf_rect(msp, r, "CARRIER")
    for r in (G.glass, G.window, G.panel, G.aa):
        dxf_rect(msp, r, "REF")
    dxf_text(msp, "GF JIG J1 OPTICAL-BONDING FIXTURE - plan seen from ABOVE = FRONT VIEW (glass face 1 up). Origin = "
             "glass centre (top-plate datum). mm.", J["base"].x0, J["base"].y0 - 8, 3.0)
    for t, u, v in G.mirror_refs():
        dxf_text(msp, t, u, v, 1.8)
    doc.saveas(path)


def j1_sheet(path_base, P, C, G, J):
    sh = Sheet()
    sh.frame()
    V = View(sh, 100.0, 178.0, 0.5)
    b, t, car, nest, op = J["base"], J["top"], J["carrier"], J["nest"], J["opening"]
    V.rrect(b, ec="k", w=THICK)
    V.rrect(car, ec="#b0308f", w=THIN, fc="#f7e9f4", geom=False)
    V.rrect(nest, ec="#b0308f", w=XTHIN, geom=False)
    V.rrect(J["fpc"], ec="#b0308f", w=XTHIN, fc="white", geom=False)
    V.rrect(t, ec="#1f77b4", w=THIN, ls=(0, (8, 1.5, 1.5, 1.5)), geom=False)
    V.rrect(op, ec="#1f77b4", w=THIN, geom=False)
    V.rrect(J["groove"], ec=C_VAC, w=XTHIN, ls=(0, (3, 1.5)), geom=False)
    V.rrect(G.glass, ec=C_REF, w=XTHIN, ls=(0, (4, 1.5)), geom=False)
    V.rrect(G.window, ec=C_REF, w=XTHIN, ls=(0, (1.5, 1.2)), geom=False)
    for (u, v) in J["guides"]:
        V.circle(u, v, J["guide_d"] / 2.0, ec="k", w=THIN, fc="#dddddd")
    for k, (u, v) in stops_uv(G, C).items():
        V.circle(u, v, C("j2_stop_d") / 2.0 + 0.6, ec=C_STOP, w=THIN, fc="#d4efdc")
        x, y = V.P(u, v)
        sh.T(x - 2.8 if k == "S3" else x + 2.8, y + (1.8 if k == "S3" else 0.0), k, fs=6.3, color=C_STOP,
             weight="bold", ha="right" if k == "S3" else "left", va="center")
    # micrometers: X on the front-view left side of the carrier, Y1 / Y2 on the top side
    mic = [("X", (car.x0, car.c[1]), (-1, 0)), ("Y1", (-40.0, car.y1), (0, 1)), ("Y2", (40.0, car.y1), (0, 1))]
    for name, (u, v), (du, dv) in mic:
        x, y = V.P(u, v)
        L = 12.0
        sh.poly([(x + du * 0.5 - dv * 1.2, y + dv * 0.5 + du * 1.2), (x + du * L - dv * 1.2, y + dv * L + du * 1.2),
                 (x + du * L + dv * 1.2, y + dv * L - du * 1.2), (x + du * 0.5 + dv * 1.2, y + dv * 0.5 - du * 1.2)],
                fc="#ffd27f", ec="k", w=XTHIN, geom=False)
        sh.T(x + du * (L + 1.5), y + dv * (L + 1.5), "micrometer " + name, fs=6.0,
             ha="right" if du < 0 else ("center" if du == 0 else "left"), va="center" if du else "bottom")
    for (u, v), (du, dv) in (((car.x1, car.c[1]), (1, 0)), ((-40.0, car.y0), (0, -1)), ((40.0, car.y0), (0, -1))):
        x, y = V.P(u, v)
        sh.L([x, x + du * 6.0], [y, y + dv * 6.0], w=THIN, c="0.3", geom=False)
        sh.circle(x + du * 6.0, y + dv * 6.0, 1.0, ec="0.3", w=XTHIN, geom=False)
    x, y = V.P(car.x1, car.c[1])
    sh.T(x + 8.5, y, "spring", fs=5.8, va="center", color="0.3")
    # microscopes over two diagonal window corners
    for (u, v) in ((G.window.x0, G.window.y1), (G.window.x1, G.window.y0)):
        x, y = V.P(u, v)
        sh.circle(x, y, 3.0, ec="#d35400", w=THIN, geom=False)
        sh.L([x - 4, x + 4], [y, y], w=XTHIN, c="#d35400", geom=False)
        sh.L([x, x], [y - 4, y + 4], w=XTHIN, c="#d35400", geom=False)
    xm, ym = V.P(G.window.x0, G.window.y1)
    sh.T(xm + 4.0, ym - 5.5, "USB microscope 1", fs=5.8, color="#d35400")
    xm, ym = V.P(G.window.x1, G.window.y0)
    sh.T(xm - 4.0, ym + 3.5, "USB microscope 2", fs=5.8, color="#d35400", ha="right")
    V.centreline((b.x0 - 3, 0), (b.x1 + 3, 0))
    V.centreline((0, b.y0 - 3), (0, b.y1 + 3))
    # dims: guide pattern, opening, stops, nest offset
    topy = V.P(0, b.y1)[1]
    gu, gv = J["guides"][0]
    sh.dim_h(*V.P(-gu, gv), *V.P(gu, gv), topy + 6.0, "guides %s" % n(2 * gu, 0), fs=6.5)
    lft = V.P(b.x0, 0)[0]
    sh.dim_v(*V.P(-gu, -gv), *V.P(-gu, gv), lft - 6.0, "guides %s" % n(2 * gv, 0), fs=6.5)
    sh.dim_h(*V.P(op.x0, op.y1), *V.P(op.x1, op.y1), topy + 13.0, "opening %s x %s (window + %s)" % (
        n(op.w), n(op.h), n(C("j1_opening_margin"))), fs=6.5)
    sh.T(16.0, 279.0, "J1 OPTICAL-BONDING FIXTURE - plan seen from ABOVE (= front view, glass face 1 up)   1 : 2",
         fs=8.5, weight="bold")
    sh.T(16.0, 274.5, "Base with the XY-theta panel carrier (magenta); top plate (blue, dash-dot) holds the glass by "
                      "vacuum on face 1, against stops S1-S3; it slides down 4 guide pins onto height stops.", fs=6.0)
    # extra plan dims: stops and opening position (same stop pattern as J2)
    S_ = stops_uv(G, C)
    tolp = C("j2_pos_tol")
    sh.dim_h(*V.P(*S_["S2"]), *V.P(*S_["S1"]), topy + 20.0, "S1-S2 %s ±%s" % (n(abs(S_["S1"][0] - S_["S2"][0])), n(C("j1_stop_tol"))),
             fs=6.5)
    boty = V.P(0, b.y0)[1]
    sh.dim_h(*V.P(*S_["S3"]), *V.P(0, 0), boty - 6.0, "%s ±%s (S3 to datum)" % (n(abs(S_["S3"][0])), n(C("j1_stop_tol"))),
             fs=6.5)
    pcx, pcy = G.panel.c
    sh.T(16.0, 101.0, "Carrier nominal position: panel outline centre at u %s, v %s from the datum (= AA under the "
                      "window); travel ±%s, all carrier dimensions free." % (n(pcx), n(pcy), n(C("j1_travel")[0])),
         fs=6.0)
    # section (schematic, 2:1, not every part to scale): top edge
    k2 = 2.0
    xs0, yb0 = 330.0, 216.0
    Sx = lambda s, h: (xs0 + k2 * s, yb0 + k2 * h)
    poly = lambda pts, **kw: sh.poly([Sx(*p) for p in pts], **kw)
    t_opt = P.d("t_opt")
    gt = P.d("glass_t")
    panel_t = [c["value"] for c in P.raw["carried_over_from_v2"] if c["name"] == "panel_t"][0]
    P._use("carried_over_from_v2.panel_t", panel_t)
    hb, h_car, h_pk, h_top = 5.0, 6.0, 3.0, 8.0          # drawn thicknesses (free)
    s_pe = -(G.glass.y1 - G.panel.y1)
    s_op = -(G.glass.y1 - op.y1)                          # opening edge (top side) from the glass edge
    s_win = -(G.glass.y1 - G.window.y1)
    gvs = gv - G.glass.y1                                 # guide pin axis from the glass edge (top side)
    gd2 = J["guide_d"] / 2.0
    s0, s1 = s_pe - 12.0, gvs + gd2 + 3.0
    poly([(s0, -hb), (s1, -hb), (s1, 0), (s0, 0)], fc="#dfe3e8", ec="k", w=THICK, hatch="////")
    poly([(s0, 0.6), (s_pe + 15.0, 0.6), (s_pe + 15.0, 0.6 + h_car), (s_pe + 0.3, 0.6 + h_car),
          (s_pe + 0.3, 0.6 + h_car - h_pk), (s0, 0.6 + h_car - h_pk)], fc="#f7e9f4", ec="#b0308f", w=THIN)
    yb = 0.6 + h_car - h_pk
    poly([(s0, yb), (s_pe, yb), (s_pe, yb + panel_t), (s0, yb + panel_t)], fc="#e3e3e3", ec="0.3", w=THIN)
    yc = yb + panel_t
    poly([(s0, yc), (s_pe, yc), (s_pe, yc + t_opt), (s0, yc + t_opt)], fc="#f6c342", ec="none", w=XTHIN)
    yg = yc + t_opt
    poly([(s0, yg), (0, yg), (0, yg + gt), (s0, yg + gt)], fc="#cfe8f3", ec="k", w=THIN)
    sh.L([Sx(s0, 0)[0], Sx(s_win, 0)[0]], [Sx(0, yg)[1] + 0.3] * 2, w=0.6, c="k", geom=False)
    yt = yg + gt
    gi = C("j1_groove_inset")
    poly([(s_op, yt), (-gi - 1.0, yt), (-gi - 1.0, yt + 1.5), (-gi + 1.0, yt + 1.5), (-gi + 1.0, yt),
          (gvs - gd2 - 0.5, yt), (gvs - gd2 - 0.5, yt + h_top), (s_op, yt + h_top)], fc="#d6e6f5", ec="#1f77b4",
         w=THIN, hatch="\\\\")
    poly([(gvs + gd2 + 0.5, yt), (s1, yt), (s1, yt + h_top), (gvs + gd2 + 0.5, yt + h_top)], fc="#d6e6f5",
         ec="#1f77b4", w=THIN, hatch="\\\\")
    st_x = C("j2_stop_d") / 2.0
    poly([(st_x - 2.0, yt), (st_x + 2.0, yt), (st_x + 2.0, yt - 2.0), (st_x - 2.0, yt - 2.0)], fc="#d4efdc",
         ec=C_STOP, w=XTHIN)
    poly([(gvs - gd2, -hb + 1.0), (gvs + gd2, -hb + 1.0), (gvs + gd2, yt + h_top + 3.0),
          (gvs - gd2, yt + h_top + 3.0)], fc="#cccccc", ec="k", w=THIN)
    # microscope view
    xm = Sx(s_win, 0)[0]
    sh.L([xm, xm], [Sx(0, yt + h_top + 7.0)[1], Sx(0, yg + gt + 0.4)[1]], w=THIN, c="#d35400", geom=False)
    sh.arrow(xm, Sx(0, yg + gt + 0.4)[1], -math.pi / 2, "#d35400")
    sh.T(xm - 1.0, Sx(0, yt + h_top + 7.5)[1], "microscope looks at the window edge through the opening", fs=5.8,
         color="#d35400", ha="right", va="bottom")
    sh.T(*Sx(s_op + 0.6, yt + h_top / 2.0 + 1.0), "TOP PLATE", fs=6.0, allow_geom=True, bg="white", va="center")
    sh.T(*Sx(s0 + 0.5, -hb / 2.0), "BASE", fs=6.0, allow_geom=True, bg="white", va="center")
    xl = Sx(s0, 0)[0] - 3.0
    labs = [((s_pe + 8.0, 0.6 + h_car * 0.5), 2.5, "carrier on PTFE pads (XY-theta)"),
            ((s_pe - 4.0, yb + panel_t / 2), 6.5, "panel %s, CTP up" % n(panel_t)),
            ((s_pe - 2.0, yc + t_opt / 2), 10.0, "LOCA %s ±%s (hard stops)" % (
                n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1))),
            ((s_win - 3.0, yg + gt / 2), 13.5, "glass, print (face 2) down"),
            ((-gi, yt + 0.8), 17.5, "vacuum groove (face 1)")]
    for (s, h), hy, txt in labs:
        sh.leader(*Sx(s, h), xl, Sx(0, hy)[1], txt, fs=5.8, head="dot", ha="right")
    xr = Sx(s1, 0)[0] + 3.0
    sh.leader(*Sx(st_x + 2.0, yt - 1.0), xr, Sx(0, yt - 3.0)[1], "stop S1", fs=5.8, head="dot")
    sh.leader(*Sx(gvs + gd2, yt + h_top + 1.0), xr, Sx(0, yt + h_top + 2.0)[1], "guide %s" % n(J["guide_d"], 0),
              fs=5.8, head="dot")
    sh.T(214.0, 279.0, "SECTION C-C, top edge (schematic)  2 : 1", fs=7.5, weight="bold")
    # alignment target: magnified window corner
    kz = 20.0
    ax0, ay0 = 236.0, 178.0
    pxh = G.aa.w / C("display_px")[0]
    pxv = G.aa.h / C("display_px")[1]
    pin = P.d("print_inset")
    al_txt = P.text("print", "alignment")
    al_note = P.item("print", "alignment")["note"]
    m = re.search(r"window edge (\d+)-(\d+) px inside", al_note)
    p_lo, p_hi = int(m.group(1)), int(m.group(2))
    gui_px = int(re.search(r"outer (\d+) px black", al_note).group(1))
    Z = lambda a, c: (ax0 + kz * a, ay0 + kz * c)
    n_px = 5
    for i in range(n_px):
        for j in range(n_px):
            lit = (i == 0 or j == 0)
            x, y = Z(i * pxh, -j * pxv)
            sh.poly([(x, y), (x + kz * pxh * 0.9, y), (x + kz * pxh * 0.9, y - kz * pxv * 0.9),
                     (x, y - kz * pxv * 0.9)], fc="#ffffff" if lit else "#8a9599", ec="0.4", w=0.1, geom=False)
    sh.poly([Z(-0.45, 0.45), Z(n_px * pxh, 0.45), Z(n_px * pxh, 0), Z(0, 0), Z(0, -n_px * pxv),
             Z(-0.45, -n_px * pxv)], fc="#1b1b1b", ec="none", geom=False)
    sh.L([Z(pin, 0)[0]] * 2, [Z(0, -pin)[1], Z(0, -n_px * pxv)[1]], w=THICK, c="#c0392b", geom=False)
    sh.L([Z(pin, 0)[0], Z(n_px * pxh, 0)[0]], [Z(0, -pin)[1]] * 2, w=THICK, c="#c0392b", geom=False)
    for pp in (p_lo, p_hi):
        sh.L([Z(pp * pxh, 0)[0]] * 2, [Z(0, 0)[1], Z(0, -n_px * pxv)[1]], w=XTHIN, c="#2e8b57", geom=False,
             dashes=(2, 1.5))
        sh.L([Z(0, 0)[0], Z(n_px * pxh, 0)[0]], [Z(0, -pp * pxv)[1]] * 2, w=XTHIN, c="#2e8b57", geom=False,
             dashes=(2, 1.5))
    sh.T(ax0 - 12.0, ay0 + 14.0, "ALIGNMENT TARGET: top-left window corner, front view  %s : 1" % n(kz, 0), fs=7.0,
         weight="bold")
    tx = Z(n_px * pxh, 0)[0] + 4.0
    for i, (t, col) in enumerate((("white = lit 1-px border on the outermost AA pixels", "k"),
                                  ("grey = image; black = LCD matrix outside the AA", "k"),
                                  ("red = print window edge (face 2): print_inset %s = %s px h, %s px v" % (
                                      n(pin), n(pin / pxh, 2), n(pin / pxv, 2)), "#c0392b"),
                                  ("green dashed = %d px and %d px inside the border: accept band" % (p_lo, p_hi),
                                   "#2e8b57"),
                                  ("1 px = %s mm h x %s mm v (AA / %d x %d px)" % (
                                      n(pxh, 4), n(pxv, 4), C("display_px")[0], C("display_px")[1]), "k"))):
        sh.T(tx, ay0 + 4.0 - i * 3.4, t, fs=5.9, color=col)
    # notes
    rngs = C("j1_travel")
    J1_en = [
        "AUTHORITATIVE for J1: this sheet supersedes concept sec. 6 (glass on the base, panel lowered): the panel "
        "sits on the XY-theta carrier and the glass hangs from the top plate so the microscopes see the window edge "
        "from the user side (R1 sec. 3.3).",
        "ALIGN the print window edge (glass face 2) to the lit 1-px border of the active area (AA): window edge %d-%d "
        "px inside the border on all four sides, left = right and top = bottom within 1 px (1 px = %s x %s mm). "
        "Nominal = print_inset %s = %s px h / %s px v (master: %s)." % (
            p_lo, p_hi, n(pxh, 4), n(pxv, 4), n(pin), n(pin / pxh, 2), n(pin / pxv, 2), al_txt),
        "Glass and panel are NOT aligned by their outlines: the glass sits on stops S1-S3 (±%s), the panel floats "
        "in the carrier (nest = panel + %s per side) and is moved by the micrometers: XY ±%s, theta ±%s deg." % (
            n(C("j1_stop_tol")), n(C("j1_nest_clr")), n(rngs[0]), n(rngs[1])),
        "Gap glass face 2 -> CTP front: LOCA %s ±%s, set by 4 height stops between top plate and base (fine-thread "
        "stop screws with lock nuts or ground shims). Per panel: measure the CTP height in the nest, set the stops "
        "to CTP + %s + measured glass thickness." % (n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1),
                                                    n(t_opt, 2)),
        "Top plate glass face parallel to the base within %s over the panel area; guides %s g6 pins / H7 bushings, "
        "no play that tilts the plate." % (n(C("j1_parallel")), n(J["guide_d"], 0)),
        "Top plate: opening = print window + %s per side, centred %s above the datum (window edge visible "
        "everywhere, UV tack through it); vacuum groove loop %s inside the glass edge (black border only)." % (
            n(C("j1_opening_margin")), n(op.c[1]), n(C("j1_groove_inset"))),
        "Micrometers: %s. Carrier: panel pocket POM-lined, FPC slot at the tail exit, test connector for the lit "
        "border pattern (GUI: outer %d px black in normal use)." % (C("j1_micrometer"), gui_px),
        "LOCA volume = panel outline %s x %s x %s = %s mL (R1: dispense ~5 %% more, dog-bone pattern)." % (
            n(G.panel.w), n(G.panel.h, 0), n(t_opt, 2), n(G.panel.w * G.panel.h * t_opt / 1000.0, 2)),
        "Free (machinist's choice): plate sizes, thicknesses, carrier size, stop-screw type, handles, feet; "
        "general tolerance ISO 2768-m. Al plate, anodised or bare; POM where glass or panel touch.",
    ]
    J1_tr = [
        "Bu resim J1 için GEÇERLİ olandır; konsept §6 metninin yerine geçer (panel XY-açı taşıyıcıda, cam üst plakada).",
        "Hizalama: cam 2. yüzündeki baskı penceresinin kenarı, ekranın aktif alanının yanan 1 piksellik çerçevesinin "
        "%d-%d piksel içinde olacak; dört kenarda eşit (±1 piksel)." % (p_lo, p_hi),
        "Cam S1-S3 dayamalarına (±%s) oturur; panel taşıyıcıda serbesttir ve mikrometrelerle hareket ettirilir: XY "
        "±%s mm, açı ±%s°." % (n(C("j1_stop_tol")), n(rngs[0]), n(rngs[1])),
        "Cam 2. yüzü ile CTP ön yüzü arası %s ±%s mm (4 yükseklik dayaması: ince dişli ayar vidası + kontra somun "
        "veya taşlanmış şim)." % (n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1)),
        "Üst plaka cam yüzeyi tabana paralel: %s mm; kılavuz pimleri Ø%s g6, burçlar H7." % (
            n(C("j1_parallel")), n(J["guide_d"], 0)),
        "Ölçüsü verilmeyen her şey serbest; genel tolerans ISO 2768-m. Cam ve panele değen yüzeyler POM.",
    ]
    ye = sh.notes(212.0, 141.0, 98.0, J1_en, fs=5.8, head="NOTES", head_fs=7.2, gap=0.4)
    yt_ = sh.notes(313.0, 141.0, 96.0, [tr(x) for x in J1_tr], fs=5.8, head="NOTLAR (Türkçe)", head_fs=7.2, gap=0.4)
    # bottom-left: what is aligned to what (table)
    rows = [["what", "aligned to", "how", "tolerance"],
            ["print window edge (glass face 2)", "lit 1-px AA border", "micrometers X / Y1 / Y2, 2 microscopes",
             "%d-%d px inside, sides equal ±1 px" % (p_lo, p_hi)],
            ["glass outline", "top plate stops S1-S3", "by hand, vacuum on", "±%s (only coarse)" % n(C("j1_stop_tol"))],
            ["glass face 2 height", "CTP front", "4 height stops", "%s ±%s" % (
                n(t_opt, 2), re.search(r"\+-([\d.]+)", P.dnote("t_opt")).group(1))],
            ["top plate", "base", "4 guide pins", "parallel %s" % n(C("j1_parallel"))]]
    sh.T(16.0, 92.0, "WHAT IS ALIGNED TO WHAT", fs=7.2, weight="bold")
    ytab = sh.table_wrapped(16.0, 90.0, [48, 36, 54, 52], rows, fs=6.0)
    sh.title_block({
        "title": "JIG J1 - OPTICAL-BONDING ALIGNMENT FIXTURE",
        "subtitle": "panel -> glass, LOCA, active alignment  /  optik yapıştırma hizalama fikstürü J1",
        "source": "product positions from Rev3.0_GlassFront_params.json %s; jig values: drafting_choices.json" %
                  P.revision,
        "project": "files: GF_Jig_J1.dxf (plan = front view, mm) + this sheet",
        "change": "%s: glass corner R%s in the references; this sheet is authoritative for J1 (supersedes the "
                  "concept sec. 6 jig text)." % (P.revision, n(G.glass.R)),
        "dwg": "GF-D31", "rev": P.revision, "scale": "1:2, 2:1, %s:1" % n(kz, 0),
        "date": datetime.date.today().isoformat(), "drawn": "make_jigs.py",
    }, h=42.0)
    issues = sh.check_layout()
    sh.save(path_base + ".pdf", path_base + ".png", dpi=200)
    return issues, J1_en, J1_tr, [round(ye, 1), round(yt_, 1), round(ytab, 1)]


def run(out_dir=OUT_DIR):
    res = {}
    P, C = Params(), Choices()
    G = Geom(P)
    b2 = os.path.join(out_dir, "GF_Jig_J2")
    j2_dxf(b2 + ".dxf", P, C, G)
    iss, en, trn, yl = j2_sheet(b2, P, C, G)
    res["J2"] = {"files": [b2 + ".dxf", b2 + ".pdf", b2 + ".png"], "layout_issues": iss, "notes_en": en,
                 "notes_tr": trn, "lowest_y": yl}
    P2, C2 = Params(), Choices()
    G2 = Geom(P2)
    J = j1_geom(P2, C2, G2)
    b1 = os.path.join(out_dir, "GF_Jig_J1")
    j1_dxf(b1 + ".dxf", P2, C2, G2, J)
    iss, en, trn, yl = j1_sheet(b1, P2, C2, G2, J)
    res["J1"] = {"files": [b1 + ".dxf", b1 + ".pdf", b1 + ".png"], "layout_issues": iss, "notes_en": en,
                 "notes_tr": trn, "lowest_y": yl}
    res["J2"]["params_used"], res["J2"]["choices_used"] = sorted(P.used.keys()), C.used
    res["J1"]["params_used"], res["J1"]["choices_used"] = sorted(P2.used.keys()), C2.used
    return res


if __name__ == "__main__":
    r = run()
    for k, v in r.items():
        print(k, "issues:", len(v["layout_issues"]), v["lowest_y"])
        for i in v["layout_issues"]:
            print("   ", i)
