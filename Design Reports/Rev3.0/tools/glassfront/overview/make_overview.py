"""Build Design Reports/Rev3.0/Rev3.0_GlassFront_Overview.pdf (A4 landscape) from the master parameters, the
content file, the renders in Mechanical/Rev3.0_GlassFront/renders/overview/, reused renders and drawing sheets,
and electronics_bom.json.

    python -B make_overview.py            # system Python 3.14 with reportlab, PyMuPDF, numpy, Pillow, matplotlib

Every printed string is registered with its source in overview_provenance.json; audit_overview.py checks the PDF.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.pdfgen import canvas

import ov_values as V
import ov_draw as D
import ov_section as S
from ov_draw import MM, PW, PH, ML, MR, CW, ACCENT, ACCENT_L, INK, GREY, GREY_L, RULE, PANEL, BODY

CT = V.Content()
C = CT.C
MV = CT.mv
G = V.master_geometry(CT.M)
REG = V.Registry()
CHECKS = []   # balloon end-point checks, written to overview_layout_checks.json
SECS = json.load(open(os.path.join(V.OVR, "sections.json")))
FOOT = C["meta"]["footer"]


def T(e):
    """content entry -> (text, src, mvals)"""
    if isinstance(e, str):
        t, used = CT.fill(e)
        return t, ("master" if used else "-"), used
    t, used = CT.fill(e["t"])
    src = e.get("src", "-")
    if used and "master" not in src:
        src = (src + ", master") if src != "-" else "master"
    return t, src, used


def ptext(pen, x, y, e, **kw):
    t, s, mv = T(e)
    return pen.text(x, y, t, s, mvals=mv, **kw)


def ppara(pen, x, ytop, w, e, **kw):
    t, s, mv = T(e)
    return pen.para(x, ytop, w, t, s, mvals=mv, **kw)


def caption(pen, x, ytop, w, e, max_lines=3):
    return ppara(pen, x, ytop, w, e, color=GREY, max_lines=max_lines)


def img(name, **kw):
    p = name if os.path.isabs(name) else os.path.join(V.OVR, name + ".png")
    return D.Img(p, **kw)


def ytop_content():
    return PH - 31 * MM


# =============================================================================================== page 1: cover
def p_cover(c, pen, n, N):
    D.page_frame(pen, "Overview", n, N, FOOT)
    m = C["meta"]
    # accent band on the left
    c.setFillColor(ACCENT); c.rect(0, 0, 8 * MM, PH, stroke=0, fill=1)
    pen.text(ML + 2 * MM, PH - 34 * MM, "Rev3.0 Oven Controller", "-", "SB", 13, ACCENT)
    pen.text(ML + 2 * MM, PH - 50 * MM, "Glass Front", "-", "SB", 34, INK)
    pen.para(ML + 2 * MM, PH - 55 * MM, 92 * MM, m["subtitle"], "-", "R", 12, GREY, max_lines=2, lead=1.25)
    # revision tile
    D.rrect(c, ML + 2 * MM, PH - 92 * MM, 70 * MM, 24 * MM, 3, fill=ACCENT_L)
    pen.text(ML + 7 * MM, PH - 78 * MM, MV["revision"][0], "master", "SB", 22, ACCENT, mvals={MV["revision"][0]: "revision"})
    pen.text(ML + 7 * MM, PH - 87 * MM, "design of record · " + m["date"], "§intro", "R", 10, INK)
    ppara(pen, ML + 2 * MM, PH - 100 * MM, 88 * MM, m["one_line"], size=11.5, lead=1.3)
    ppara(pen, ML + 2 * MM, PH - 133 * MM, 88 * MM, m["cover_note"], color=GREY, size=BODY)
    ppara(pen, ML + 2 * MM, PH - 168 * MM, 88 * MM, m["readers"], color=GREY_L, size=BODY)
    hero = img("hero_front")
    D.place(c, hero, 112 * MM, 22 * MM, 172 * MM, 150 * MM)
    pen.text(112 * MM + 86 * MM, 18 * MM, "Rendered from the GF-2.1 assembly CAD, display switched off (S4 variant).",
             "-", "R", BODY, GREY, "c")


# =============================================================================================== page 2: what it is
def rrpath(c, x0, y0, x1, y1, r):
    p = c.beginPath()
    p.roundRect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0), r)
    return p


def dim_h(c, pen, xa, xb, y, text, src, mvals=None, ext_from=None, above=True, size=BODY, col=INK):
    c.setStrokeColor(col); c.setLineWidth(0.5)
    c.line(xa, y, xb, y)
    for x, d in ((xa, 1), (xb, -1)):
        p = c.beginPath(); p.moveTo(x, y); p.lineTo(x + d * 4, y + 1.4); p.lineTo(x + d * 4, y - 1.4); p.close()
        c.setFillColor(col); c.drawPath(p, stroke=0, fill=1)
        if ext_from is not None:
            c.setLineWidth(0.3); c.line(x, ext_from, x, y + (2 if y > ext_from else -2)); c.setLineWidth(0.5)
    pen.text((xa + xb) / 2, y + (2.2 if above else -size - 1), text, src, "R", size, col, "c", mvals)


def dim_v(c, pen, ya, yb, x, text, src, mvals=None, ext_from=None, left=True, size=BODY, col=INK):
    c.setStrokeColor(col); c.setLineWidth(0.5)
    c.line(x, ya, x, yb)
    for y, d in ((ya, 1), (yb, -1)):
        p = c.beginPath(); p.moveTo(x, y); p.lineTo(x + 1.4, y + d * 4); p.lineTo(x - 1.4, y + d * 4); p.close()
        c.setFillColor(col); c.drawPath(p, stroke=0, fill=1)
        if ext_from is not None:
            c.setLineWidth(0.3); c.line(ext_from, y, x + (2 if x > ext_from else -2), y); c.setLineWidth(0.5)
    c.saveState()
    c.translate(x + (-2.5 if left else size + 1.5), (ya + yb) / 2)
    c.rotate(90)
    pen.text(0, 0, text, src, "R", size, col, "c", mvals)
    c.restoreState()


LIGHT = HexColor("#DCE1E6")


def front_view(c, pen, x, y, w, h):
    """vector front view to scale from the master plan rectangles (front view mirrors x: u = -(x - xc))"""
    gc = G["glass"]
    xc = (gc["x0"] + gc["x1"]) / 2
    yc = (gc["y0"] + gc["y1"]) / 2
    fl = G["flange"]
    span_u = (fl["x1"] - fl["x0"]) + 40
    span_v = (fl["y1"] - fl["y0"]) + 34
    s = min(w / span_u, h / span_v)
    cx, cy = x + w / 2, y + h / 2 - 1.5 * MM

    def P(xa, ya):
        return cx - (xa - xc) * s, cy + (yc - ya) * s

    def rr(r, R):
        x0, y0 = P(r["x0"], r["y0"]); x1, y1 = P(r["x1"], r["y1"])
        return rrpath(c, x0, y0, x1, y1, R * s)
    c.saveState()
    clip = c.beginPath(); clip.rect(x, y, w, h); c.clipPath(clip, stroke=0, fill=0)
    c.setFillColor(HexColor("#D3D7DB")); c.rect(x, y, w, h, stroke=0, fill=1)
    c.setDash(3, 2); c.setStrokeColor(GREY); c.setLineWidth(0.6)
    c.drawPath(rr(fl, G["flange_R"]), stroke=1, fill=0)
    c.setDash()
    c.setFillColor(HexColor("#0D0E10")); c.drawPath(rr(G["cut"], G["R_cut"]), stroke=0, fill=1)
    c.setFillColor(HexColor("#2A2C30")); c.drawPath(rr(G["lip_out"], G["lip_out"]["R"]), stroke=0, fill=1)
    c.setFillColor(HexColor("#0D0E10")); c.drawPath(rr(G["lip_in"], G["lip_in"]["R"]), stroke=0, fill=1)
    c.setFillColor(HexColor("#050506")); c.drawPath(rr(gc, G["R_glass"]), stroke=0, fill=1)
    c.setFillColor(HexColor("#2C3138")); c.drawPath(rr(G["print_window"], G["print_window"]["R"]), stroke=0, fill=1)
    lc = G["logo_centre"]; lw_, lh_ = G["logo_w"], G["logo_h"]
    lx0, ly0 = P(lc[0] - lw_ / 2, lc[1] - lh_ / 2); lx1, ly1 = P(lc[0] + lw_ / 2, lc[1] + lh_ / 2)
    c.setDash(2, 2); c.setStrokeColor(HexColor("#8C939B")); c.setLineWidth(0.5)
    c.rect(min(lx0, lx1), min(ly0, ly1), abs(lx1 - lx0), abs(ly1 - ly0), stroke=1, fill=0)
    c.setDash()
    pen.text((lx0 + lx1) / 2, (ly0 + ly1) / 2 - 3, "logo zone ≤ %s × %s" % (MV["logo_w"][0], MV["logo_h"][0]), "master",
             "R", BODY, HexColor("#AEB4BA"), "c", {MV["logo_w"][0]: MV["logo_w"][1], MV["logo_h"][0]: MV["logo_h"][1]})
    c.setDash(1.5, 1.5); c.setStrokeColor(GREY); c.setLineWidth(0.6)
    for f in G["positions"]:
        X, Y = P(f["x_abs"], f["y_abs_down"])
        c.circle(X, Y, 2.0 * MM, stroke=1, fill=0)
    c.setDash()
    c.restoreState()
    # labels in the top margin of the drawing, on the steel
    ytxt = y + h - 4.2 * MM
    f1 = [f for f in G["positions"] if f["front_view_u"] > 0 and f["front_view_v"] > 0][0]
    X, Y = P(f1["x_abs"], f1["y_abs_down"])
    D.leader_label(c, pen, X - 1.5 * MM, Y + 1.5 * MM, x + w - 3 * MM, ytxt, "hidden stud (S4), one at each corner",
                   "§2.3", "r")
    fxm, fym = P(xc + 60, fl["y0"])
    D.leader_label(c, pen, fxm, fym, x + 3 * MM, ytxt, "frame flange (dashed), hidden behind the sheet", "§0.1", "l")
    # dimensions outside the glass (dark ink on the steel)
    cut = G["cut"]; win = G["print_window"]
    cx0, cy0 = P(cut["x1"], cut["y1"]); cx1, cy1 = P(cut["x0"], cut["y0"])
    dim_h(c, pen, cx0, cx1, cy0 - 6.5 * MM, "visible module (cut-out) %s" % MV["cut_w"][0], "master",
          {MV["cut_w"][0]: MV["cut_w"][1]}, ext_from=cy0, above=False)
    dim_v(c, pen, cy0, cy1, cx1 + 6.5 * MM, MV["cut_h"][0], "master", {MV["cut_h"][0]: MV["cut_h"][1]}, ext_from=cx1,
          left=False)
    gx0, gy0 = P(gc["x1"], gc["y1"]); gx1, gy1 = P(gc["x0"], gc["y0"])
    dim_h(c, pen, gx0, gx1, cy1 + 5.0 * MM, "glass %s" % MV["glass_w"][0], "master", {MV["glass_w"][0]: MV["glass_w"][1]},
          ext_from=gy1)
    # dimensions inside the black border (light ink, never across the picture window)
    wx0, wy0 = P(win["x1"], win["y1"]); wx1, wy1 = P(win["x0"], win["y0"])
    dim_h(c, pen, wx0, wx1, (wy1 + gy1) / 2 - 1.2 * MM, "picture window %s" % MV["win_w"][0], "master",
          {MV["win_w"][0]: MV["win_w"][1]}, col=LIGHT)
    dim_v(c, pen, wy0, wy1, (gx0 + wx0) / 2 + 1.0 * MM, MV["win_h"][0], "master", {MV["win_h"][0]: MV["win_h"][1]},
          col=LIGHT)
    b = MV["border"][0]; bm = {b: MV["border"][1]}
    dim_h(c, pen, gx0, wx0, (wy0 + gy0) / 2 - 1.2 * MM, b, "master", bm, col=LIGHT)
    dim_h(c, pen, wx1, gx1, (wy0 + wy1) / 2, b, "master", bm, col=LIGHT)
    dim_v(c, pen, wy1, gy1, wx1 + 4.0 * MM, b, "master", bm, left=False, col=LIGHT)
    dim_v(c, pen, gy0, wy0, wx1 + 4.0 * MM, b, "master", bm, left=False, col=LIGHT)
    return s


def p_what(c, pen, n, N):
    W = C["what"]
    D.page_frame(pen, W["title"], n, N, FOOT)
    t, s_, mv = T(C["meta"]["one_line"])
    D.title(pen, W["title"])
    pen.text(ML, PH - 26.5 * MM, t, s_, "R", 10, GREY, mvals=mv)
    fx, fy, fw, fh = ML, 70 * MM, 150 * MM, 106 * MM
    front_view(c, pen, fx, fy, fw, fh)
    caption(pen, fx, fy - 1.5 * MM, fw, W["front_caption"], 2)
    caption(pen, fx, fy - 9.5 * MM, fw, W["place_caption"], 3)
    rx = 172 * MM; tw, th = 53 * MM, 23 * MM
    for i, f in enumerate(W["facts"]):
        col, row = i % 2, i // 2
        x = rx + col * (tw + 3 * MM); y = PH - 34 * MM - th - row * (th + 3 * MM)
        D.rrect(c, x, y, tw, th, 3, fill=PANEL)
        big, s1, m1 = T({"t": f["big"], "src": f["src"]})
        pen.text(x + 3.5 * MM, y + th - 7.6 * MM, big, s1, "SB", 16, ACCENT, mvals=m1)
        sm, s2, m2 = T({"t": f["small"], "src": f["src"]})
        pen.para(x + 3.5 * MM, y + th - 9.4 * MM, tw - 6 * MM, sm, s2, size=BODY, color=INK, max_lines=3, mvals=m2,
                 lead=1.15)
    ap = os.path.join(V.DRAWINGS, "GF_Appearance.png")
    k = 4960 / 2296
    s4 = D.Img(ap, crop=(int(98 * k), int(146 * k), int(940 * k), int(742 * k)), do_trim=False, max_px=1400)
    r4 = D.Img(ap, crop=(int(962 * k), int(146 * k), int(1805 * k), int(742 * k)), do_trim=False, max_px=1400)
    ty = 60 * MM; th2 = 34 * MM; tw2 = 53 * MM
    D.place(c, s4, rx, ty, tw2, th2, jpeg=True, frame=True)
    D.place(c, r4, rx + tw2 + 3 * MM, ty, tw2, th2, jpeg=True, frame=True)
    pen.text(rx, ty + th2 + 1.8 * MM, "S4 — hidden studs", "§2.3", "SB", BODY, INK)
    pen.text(rx + tw2 + 3 * MM, ty + th2 + 1.8 * MM, "R4 — visible rivets", "§2.3", "SB", BODY, INK)
    caption(pen, rx, ty - 1.5 * MM, 2 * tw2 + 3 * MM, W["variants_caption"], 2)
    by = 12 * MM; bh = 24 * MM
    pen.text(ML, by + bh + 3.5 * MM, W["why_title"], "-", "SB", 11, INK)
    bw = (CW - 3 * 4 * MM) / 4
    for i, wv in enumerate(W["why"]):
        x = ML + i * (bw + 4 * MM)
        D.rrect(c, x, by, bw, bh, 3, fill=ACCENT_L)
        pen.text(x + 3 * MM, by + bh - 6 * MM, wv["h"], wv["src"], "SB", 10, ACCENT)
        ppara(pen, x + 3 * MM, by + bh - 7.5 * MM, bw - 6 * MM, {"t": wv["t"], "src": wv["src"]}, max_lines=3, lead=1.18)


# =============================================================================================== page 3: exploded
def bom_name(no):
    for b in C["bom"]:
        if str(b["no"]) == str(no):
            return b["name"]
    return ""


def p_exploded(c, pen, n, N):
    TG = C["together"]
    D.page_frame(pen, TG["title"], n, N, FOOT)
    D.title(pen, TG["title"])
    ptext(pen, ML, PH - 26.5 * MM, TG["order_note"], font="R", size=10, color=GREY)
    ex = img("exploded", do_trim=False, max_px=3200)
    idb = D.IdBuffer("exploded", V.OVR)
    box = (ML, 43 * MM, CW, 128 * MM)
    m, (px, py, pw, ph) = D.place(c, ex, *box)
    k = pw / ex.im.width  # page pt per pixel
    nums = {b["key"]: b["no"] for b in C["bom"]}
    placed = []
    r_pt = 3.4 * MM
    r_px = r_pt / k
    H, Wd = idb.bg.shape
    for key, anc in idb.rec["anchors"].items():
        if key not in nums:
            continue
        # end every leader well inside a visible area of its own part (8 px in from any edge where the part is
        # big enough), and check that with the id buffer
        tgt = idb.interior(key, anc[0], anc[1], depth=8)
        if tgt is None:
            continue
        tx, ty = tgt
        ix, iy = int(round(tx)), int(round(ty))
        nb = idb.masks[key][iy - 2:iy + 3, ix - 2:ix + 3]
        if nb.size == 0 or not nb.all():
            raise RuntimeError("balloon %s: leader end is not on its own part" % key)
        CHECKS.append({"balloon": nums[key], "key": key, "end_px": [ix, iy], "on_own_part": True,
                       "inset_px": int(D.erode(idb.masks[key], 8)[iy, ix]) * 8 or int(D.erode(idb.masks[key], 3)[iy, ix]) * 3})
        best = None
        # search outward for a balloon centre on free background, preferring up/down from the target
        for dist in np.arange(70, 420, 14):
            for ang in (-90, 90, -70, -110, 70, 110, -50, -130, 50, 130, 0, 180, -30, -150, 30, 150):
                cx = tx + dist * math.cos(math.radians(ang))
                cy = ty + dist * math.sin(math.radians(ang))
                if not D.free_circle(idb.bg, cx, cy, r_px * 1.5):
                    continue
                if any((cx - a) ** 2 + (cy - b) ** 2 < (r_px * 3.0) ** 2 for a, b in placed):
                    continue
                best = (cx, cy)
                break
            if best:
                break
        if best is None:
            raise RuntimeError("no free place for balloon " + key)
        placed.append(best)
        bx, by = m(best[0], best[1]); tpx, tpy = m(tx, ty)
        D.balloon(c, pen, bx, by, r_pt, nums[key], "structure: BOM item number", tpx, tpy)
    # key along the bottom
    caption(pen, ML, 41 * MM, CW, TG["explode_caption"], 2)
    ky = 30 * MM
    items = [(b["no"], b["name"], b.get("name_src", "-")) for b in C["bom"] if b["key"] in idb.rec["anchors"]]
    colw = CW / 4
    for i, (no, nm, nsrc) in enumerate(items):
        col, row = i % 4, i // 4
        x = ML + col * colw; y = ky - row * 5.2 * MM
        c.setFillColor(ACCENT); c.circle(x + 2.2 * MM, y + 1.1 * MM, 2.2 * MM, stroke=0, fill=1)
        pen.text(x + 2.2 * MM, y - 0.4, str(no), "structure: BOM item number", "SB", 8.5 if no > 9 else 9, white, "c")
        pen.text(x + 6 * MM, y, nm, nsrc, "R", BODY, INK)
    caption(pen, ML, ky - 3 * 5.2 * MM + 1 * MM, CW, TG["not_shown"], 1)


# =============================================================================================== page 4: edge section
def p_edge(c, pen, n, N):
    E = C["edge"]; L = E["labels"]
    D.page_frame(pen, E["title"], n, N, FOOT)
    D.title(pen, E["title"])
    ppara(pen, ML, PH - 23.2 * MM, CW, E["caption"], color=GREY, max_lines=2, size=BODY)
    D.LEADERS.clear()
    sec = S.Section(SECS["side_edge_y66.83"], [-14.5, 30.0, -15.6, 3.2])
    bx, by, bw, bh = sec.fit(70 * MM, 104 * MM, 152 * MM, 70 * MM)
    sec.draw(c)
    gz = min(z for pl in sec.polys if pl["key"] == "glass" and pl["sub"] == "glass" for L_ in pl["loops"] for _, z in L_)
    _, Yf = sec.P(sec.win[0], gz)
    c.setStrokeColor(ACCENT); c.setLineWidth(0.9); c.setDash(4, 2); c.line(bx - 3 * MM, Yf, bx + bw + 3 * MM, Yf)
    c.setDash()
    # flush-plane texts under the glass, right of the joint, so the zoom connector (going down-left) never crosses them
    # the zoom-source rectangle on the main section (drawn further down) - known here so the texts can clear it
    cut0, gl0 = G["cut"], G["glass"]
    zh0 = cut0["x0"] - 1.4; zh1 = gl0["x0"] + 1.4
    zlo, zhi = gz - 2.1, gz + 1.9          # room under the flush plane for the dimensions, inside the zoom box
    a0 = sec.P(zh0, zlo); a1 = sec.P(zh1, zhi)
    t, s_, mv = T(E["callouts"]["glass_flush"])
    tw_ = D.sw(t, "SB")
    xt = max(sec.P(18.0, 0)[0], a1[0] + 1.5 * MM + tw_ / 2 + 1)   # left edge at least 1.5 mm right of the rectangle
    pen.text(xt, Yf - 5.0 * MM, t, s_, "SB", BODY, ACCENT, "c", mv)
    pen.text(xt, Yf - 9.2 * MM, "customer side ↓", "-", "R", BODY, GREY, "c")
    flush_box = (xt - tw_ / 2 - 1, Yf - 10.5 * MM, xt + tw_ / 2 + 1, Yf - 1.5 * MM)
    gap_ = 1.5 * MM
    rx0, ry0, rx1, ry1 = a0[0] - gap_, a0[1] - gap_, a1[0] + gap_, a1[1] + gap_
    if not (flush_box[0] >= rx1 or flush_box[2] <= rx0 or flush_box[1] >= ry1 or flush_box[3] <= ry0):
        raise ValueError("flush-plane texts come within 1.5 mm of the zoom-source rectangle")
    if flush_box[2] > bx + bw:
        raise ValueError("flush-plane texts run under the right-hand label column")
    left = [
        (sec.target("frame", (-6, -11.2)), [L["frame"]], "-"),
        (sec.target("tape", (-2, -12.9)), [L["tape"]], "-"),
        (sec.target("sheet", (-10, -13.9)), [L["sheet"]], "-"),
    ]
    right = [
        (sec.target("pcb", (25, 0.8), "board"), [L["pcb"]], "-"),
        (sec.target("formex", (25, -4.8)), [L["formex"]], "-"),
        (sec.target("panel", (25, -7.5), "lcm"), [L["panel"]], "-"),
        (sec.target("bead", (11, -10.9)), [L["bead"]], "-"),
        (sec.target("loca", (27, -11.27), depth_mm=0.05), [L["loca"]], "-"),
        (sec.target("glass", (28, -11.43), sub="print", depth_mm=0.004), [L["print"]], "-"),
        (sec.target("glass", (24, -13.0), sub="glass"), [L["glass"]], "-"),
    ]
    S.label_column(c, pen, left, "left", bx - 5 * MM, (by + 2 * MM, by + bh * 0.75))
    S.label_column(c, pen, right, "right", bx + bw + 5 * MM, (by, by + bh))
    lip = G["lip_out"]; lipi = G["lip_in"]; cut = G["cut"]; gl = G["glass"]
    zsec = S.Section(SECS["side_edge_y66.83"], [zh0, zh1, zlo, zhi])
    zb = zsec.fit(20 * MM, 38 * MM, 80 * MM, 48 * MM)
    zsec.draw(c, lw=0.5)
    c.setStrokeColor(ACCENT); c.setLineWidth(0.8); c.rect(*zb, stroke=1, fill=0)
    c.rect(a0[0], a0[1], a1[0] - a0[0], a1[1] - a0[1], stroke=1, fill=0)
    conn = (a0[0], a0[1], zb[0] + zb[2], zb[1] + zb[3])
    c.setDash(1, 2); c.line(*conn); c.setDash()
    pen.text(zb[0], zb[1] + zb[3] + 6.5 * MM, "zoom: the visible joint", "-", "SB", BODY, INK)
    t, s_, mv = T(E["callouts"]["sheet_t"])
    pen.text(zb[0], zb[1] + zb[3] + 2.2 * MM, t, s_, "R", BODY, INK, "l", mv)
    # dimension line just under the flush plane; texts below it, clear of the line and of the box edge
    yf = zsec.P(0, gz)[1]
    yb = yf - 3.0 * MM
    xs = [zsec.P(cut["x0"], 0)[0], zsec.P(lip["x0"], 0)[0], zsec.P(lipi["x0"], 0)[0], zsec.P(gl["x0"], 0)[0]]
    c.setStrokeColor(INK); c.setLineWidth(0.4)
    for xx in xs:
        c.line(xx, yb - 1.0 * MM, xx, yf)
    c.line(xs[0], yb, xs[3], yb)
    for xx in xs[1:3]:
        c.line(xx - 0.8 * MM, yb - 0.8 * MM, xx + 0.8 * MM, yb + 0.8 * MM)
    t1, s1, m1 = T(E["callouts"]["g1"]); t2, s2, m2 = T(E["callouts"]["lip"]); t3, s3, m3 = T(E["callouts"]["g2"])
    ylab = yb - 5.2 * MM
    pen.text(xs[1] - 0.5 * MM, ylab, t1, s1, "R", BODY, INK, "r", m1)           # g1: ends under its gap
    pen.text(xs[2] + 0.5 * MM, ylab, t3, s3, "R", BODY, INK, "l", m3)           # g2: starts under its gap
    pen.text((xs[1] + xs[2]) / 2, ylab - 4.4 * MM, t2, s2, "R", BODY, INK, "c", m2)
    if ylab - 4.4 * MM - 1.5 * MM < zb[1]:
        raise ValueError("zoom dimensions do not fit inside the zoom box")
    pen.text(zb[0] + 2 * MM, zsec.P(0, gz + 0.45)[1], "steel", "-", "SB", BODY, INK)
    pen.text(zb[0] + zb[2] - 2 * MM, zsec.P(0, gz + 1.25)[1], "glass", "-", "SB", BODY, INK, "r")
    caption(pen, zb[0], 33 * MM, 90 * MM, E["zoom_caption"], 2)
    # the connector must not cross any text or leader
    for seg in D.LEADERS:
        if D.segments_cross(conn, seg):
            raise ValueError("zoom connector crosses a leader")
    fx0, fy0, fx1, fy1 = flush_box
    for e in ((fx0, fy0, fx1, fy0), (fx0, fy1, fx1, fy1), (fx0, fy0, fx0, fy1), (fx1, fy0, fx1, fy1)):
        if D.segments_cross(conn, e):
            raise ValueError("zoom connector crosses the flush-plane texts")
    # corner fastener section (bottom right), with the weld base the CAD leaves out (dashed, illustration)
    csec = S.Section(SECS["corner_F1_y-5.83"], [-15.5, 9.0, -15.0, 3.2])
    cb = csec.fit(176 * MM, 30 * MM, 70 * MM, 54 * MM)
    csec.draw(c)
    stud = [np.array(pl["loops"][0]) for pl in csec.polys if pl["key"] == "stud"][0]
    sheet_top = max(np.array(pl["loops"][0])[:, 1].max() for pl in csec.polys if pl["key"] == "sheet")
    sc = (stud[:, 0].min() + stud[:, 0].max()) / 2
    WB = C["edge"]["weld_base"]
    r_ = float(WB["d"]) / 2
    hb = float(WB["h"])
    p0 = csec.P(sc - r_, sheet_top); p1 = csec.P(sc + r_, sheet_top + hb)
    c.setDash(2, 1.5); c.setStrokeColor(INK); c.setLineWidth(0.7); c.setFillColor(HexColor("#EFE2D3"))
    c.rect(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], stroke=1, fill=1)
    q0 = csec.P(stud[:, 0].min(), sheet_top + hb); q1 = csec.P(stud[:, 0].max(), stud[:, 1].min())
    if q1[1] > q0[1]:
        c.rect(q0[0], q0[1], q1[0] - q0[0], q1[1] - q0[1], stroke=1, fill=1)
    c.setDash()
    pen.text(cb[0], cb[1] + cb[3] + 2.2 * MM, "cut through corner fastener F1", "-", "SB", BODY, INK)
    # targets on the left-hand halves, so that no leader runs through the stud
    lab = [(csec.target("nut", (-5.5, -3.5)), [L["nut"]], "-"), (csec.target("washer", (-6.5, -6.9)), [L["washer"]], "-"),
           (csec.target("stud", (-2.9, -9.0)), [L["stud"]], "-"),
           (csec.target("frame", (-10.0, -9.8)), ["frame pad and tube"], "-"),
           ((p0[0] + 0.8 * MM, (p0[1] + p1[1]) / 2), [L["weld_base"]], "-"),
           (csec.target("sheet", (-12.0, -13.9)), [L["sheet"]], "-")]
    n0 = len(D.LEADERS)
    S.label_column(c, pen, lab, "left", cb[0] - 3 * MM, (cb[1] - 2 * MM, cb[1] + cb[3]))
    segs = D.LEADERS[n0:]
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if D.segments_cross(segs[i], segs[j]):
                raise ValueError("corner-section leaders cross")
    caption(pen, 128 * MM, 22 * MM, PW - MR - 128 * MM, E["corner_caption"], 3)


# =============================================================================================== page 5: bottom edge
def p_bottom(c, pen, n, N):
    B = C["bottom"]; L = B["labels"]
    D.page_frame(pen, "Bottom edge", n, N, FOOT)
    D.title(pen, B["title"])
    ppara(pen, ML, PH - 23.2 * MM, CW, B["section_caption"], color=GREY, max_lines=2, size=BODY)
    sec = S.Section(SECS["bottom_x60"], [113.0, 152.5, -15.5, 4.8])
    bx, by, bw, bh = sec.fit(62 * MM, 64 * MM, 120 * MM, 98 * MM)
    sec.draw(c)
    gz = min(z for pl in sec.polys if pl["key"] == "glass" and pl["sub"] == "glass" for L_ in pl["loops"] for _, z in L_)
    _, Yf = sec.P(0, gz)
    c.setStrokeColor(ACCENT); c.setLineWidth(0.9); c.setDash(4, 2); c.line(bx, Yf, bx + bw, Yf); c.setDash()
    slot = G["bend_gap_slot"]
    D.LEADERS.clear()
    left = [
        (sec.target("pcb", (114, 0.8), "board"), [L["pcb"]], "-"),
        (sec.target("formex", (115, -4.8)), [L["formex"]], "-"),
        (sec.target("panel", (115, -7.5), "lcm"), [L["panel"]], "-"),
        (sec.target("glass", (118, -13.0), sub="glass"), [L["glass"]], "-"),
    ]
    # the column ends at the PCB's height, so the PCB leader runs level and stays under the cable's top leg
    S.label_column(c, pen, left, "left", bx - 4 * MM, (by + 2 * MM, sec.P(0, 1.4)[1]))
    t_slot, s_slot, mv_slot = T(L["slot"]); t_bead, s_bead, mv_bead = T(L["bead"])
    # the cable's own label, above: its leader ends on the U-loop
    n_cable = len(D.LEADERS)
    S.label_column(c, pen, [(sec.target("panel", (137.2, -1.35), sub="tail", depth_mm=0.05), [L["tail"]], "-")], "top",
                   by + bh + 6 * MM, (bx + bw * 0.42, bx + bw * 0.80))
    S.label_column(c, pen, [(sec.target("frame", (149, 1.0)), [L["wall"]], "-")], "top", by + bh + 6 * MM,
                   (bx + bw * 0.84, bx + bw + 6 * MM))
    px, py = sec.P(142.4, -4.2)
    pen.text(px, py, "tail pocket", "-", "R", BODY, GREY, "c")
    pen.text(px, py - BODY * 1.2, "(open to the back)", "-", "R", BODY, GREY, "c")
    # everything at the bottom edge is labelled from below: the leaders come up through the glass, never through
    # the cable, and they keep the left-to-right order of their targets, so none crosses another
    sl_h = (slot["y0"] + slot["y1"]) / 2 + 0.6     # in the slot, between the folded cable and the bridge face
    bottom = [
        (sec.P(sl_h, -10.2), [t_slot], s_slot),
        (sec.target("frame", (122.75, -8.6)), [L["nose"]], "-"),
        (sec.target("bead", (125.6, -10.9)), [t_bead], s_bead),
        (sec.target("frame", (130.2, -9.2)), [L["bridge"]], "-"),
        (sec.target("tape", (138, -12.9)), [L["tape"]], "-"),
        (sec.target("sheet", (146, -13.9)), [L["sheet"]], "-"),
    ]
    S.label_column(c, pen, bottom, "bottom", by - 8 * MM, (bx - 6 * MM, bx + bw + 6 * MM))
    segs = list(D.LEADERS)
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if D.segments_cross(segs[i], segs[j]):
                raise ValueError("bottom-edge leaders %d and %d cross" % (i, j))
    for i, sg in enumerate(segs):
        if i != n_cable and S.poly_hits_segment(sec, sg, "panel", sub="tail", skip_end=0.0):
            raise ValueError("bottom-edge leader %d runs through the cable" % i)
    pen.text(bx - 2 * MM, Yf - 5.0 * MM, "customer side ↓", "-", "R", BODY, GREY, "r")
    # right column: Fusion renders (reused) with labels outside the pictures
    rx = 200 * MM; rw = PW - MR - rx
    tb = D.Img(os.path.join(V.RENDERS, "Fusion_GF21_bottom_edge_bridge_tails_back.png"), do_trim=False, max_px=1600)
    mb, rb = D.place(c, tb, rx, 128 * MM, rw, 48 * MM, align="t", jpeg=True)
    BL = B["back_labels"]
    items = [(mb(120, 640), [BL["ctp"]], "-"), (mb(395, 650), [BL["rib"]], "-"), (mb(900, 560), [BL["tft"]], "-")]
    S.label_column(c, pen, items, "bottom", rb[1] - 5.5 * MM, (rx, rx + rw))
    caption(pen, rx, rb[1] - 8 * MM, rw, B["back_caption"], 3)
    nb = D.Img(os.path.join(V.RENDERS, "Fusion_GF21_bottom_edge_bridge_nose_closeup.png"), do_trim=False,
               crop=(330, 260, 1600, 1200), max_px=1200)
    mn, rn = D.place(c, nb, rx, 50 * MM, rw * 0.58, 40 * MM, align="l", jpeg=True)
    NL = B["nose_labels"]
    nitems = [(mn(1235, 470), [NL["nose"]], "-"), (mn(830, 700), [NL["rib"]], "-"), (mn(560, 900), [NL["tail"]], "-")]
    S.label_column(c, pen, nitems, "right", rn[0] + rn[2] + 3 * MM, (rn[1], rn[1] + rn[3]))
    caption(pen, rx, 48.5 * MM, rw, B["nose_caption"], 2)
    # bottom budget bar
    ytop = 36 * MM
    t, s_, mv = T(B["budget_title"])
    pen.text(ML, ytop, t, s_, "SB", 10.5, INK, mvals=mv)
    parts = B["budget"][:3]
    tot = sum(float(p["w"]) for p in parts)
    x = ML; y = 20 * MM; hbar = 7 * MM; wbar = 165 * MM
    shades = [HexColor("#9EA2A8"), HexColor("#E38E22"), HexColor("#3B3F45")]
    lx = ML
    for p, sh in zip(parts, shades):
        wv = float(p["w"]) / tot * wbar
        c.setFillColor(sh); c.rect(x, y, wv, hbar, stroke=0, fill=1)
        pen.text(x + wv / 2, y + 2.3 * MM, p["w"], p["src"], "SB", 10, white, "c")
        x += wv
        c.setFillColor(sh); c.rect(lx, y - 5.6 * MM, 3 * MM, 3 * MM, stroke=0, fill=1)
        lw_ = pen.text(lx + 4.2 * MM, y - 5.2 * MM, p["t"], p["src"], "R", BODY, INK)
        lx += lw_ + 9 * MM
    last = B["budget"][3]
    pen.text(ML + wbar + 4 * MM, y + 2.3 * MM, "= " + last["w"] + " mm", last["src"], "SB", 11, ACCENT)
    pen.text(ML + wbar + 4 * MM, y - 2.6 * MM, last["t"], last["src"], "R", BODY, INK)
    ppara(pen, ML + wbar + 4 * MM, ytop + 3.2, PW - MR - (ML + wbar + 4 * MM), B["margin_note"], color=GREY, max_lines=3)


# =============================================================================================== BOM cards
def ill_draw(c, pen, kind, x, y, w, h):
    """simple honest schematic pictures for parts that have no solid in the exported CAD"""
    cx, cy = x + w / 2, y + h / 2
    X0, Y0, W0 = x, y, w
    c.setLineWidth(0.8); c.setStrokeColor(INK)
    if kind == "ill_screw":
        s = min(h / 15.0, w / 14.0)
        c.setFillColor(HexColor("#C9CDD2"))
        c.rect(cx - 2.6 * s, cy + 3 * s, 5.2 * s, 2.0 * s, stroke=1, fill=1)
        p = c.beginPath(); p.moveTo(cx - 1.45 * s, cy + 3 * s); p.lineTo(cx + 1.45 * s, cy + 3 * s)
        p.lineTo(cx + 1.45 * s, cy - 4.5 * s); p.lineTo(cx, cy - 6 * s); p.lineTo(cx - 1.45 * s, cy - 4.5 * s); p.close()
        c.drawPath(p, stroke=1, fill=1)
        for i in range(8):
            yy = cy + 2.4 * s - i * 0.95 * s
            c.line(cx - 1.45 * s, yy, cx + 1.45 * s, yy - 0.5 * s)
        pen.text(cx + 3.4 * s, cy + 3.5 * s, "ST2.9", "§9.4", "R", BODY, INK)
    elif kind == "ill_rivet":
        s = min(h / 21.0, w / 17.0)
        cy -= 1.0 * s
        c.setFillColor(HexColor("#9AA1A8"))
        c.rect(cx - 0.9 * s, cy - 7.5 * s, 1.8 * s, 15.5 * s, stroke=1, fill=1)   # mandrel
        c.setFillColor(HexColor("#C9CDD2"))
        c.rect(cx - 2.4 * s, cy - 6 * s, 4.8 * s, 8.4 * s, stroke=1, fill=1)     # body
        c.setFillColor(HexColor("#2A2C30"))
        c.roundRect(cx - 7 * s, cy + 2.4 * s, 14 * s, 1.6 * s, 0.8 * s, stroke=1, fill=1)  # head
        pen.text(cx, cy + 9.2 * s, "black head Ø14", "§8.7", "R", BODY, INK, "c")
        pen.text(cx + 3.0 * s, cy - 3.5 * s, "Ø4.8", "§8.7", "R", BODY, INK)
    elif kind == "ill_washer5":
        s = min(h / 22.0, w / 18.0)
        c.setFillColor(HexColor("#D3D6DA"))
        c.circle(cx, cy + 2 * s, 7.5 * s, stroke=1, fill=1)
        c.setFillColor(PANEL); c.circle(cx, cy + 2 * s, 2.7 * s, stroke=1, fill=1)
        pen.text(cx, cy - 8.3 * s, "Ø15 × 1.2", "§8.7", "R", BODY, INK, "c")
    elif kind == "ill_consumables":
        s = min(w / 44.0, h / 24.0)
        x0 = cx - 21 * s
        for i, (lab, col, src) in enumerate([("primer", "#E7E1C8", "§8.4"), ("Primer 94", "#E7E1C8", "§8.5"),
                                             ("IPA", "#DCE9EF", "§9.2")]):
            bx = x0 + i * 11.5 * s
            c.setFillColor(HexColor(col)); c.roundRect(bx, cy - 5 * s, 8 * s, 11 * s, 1.2 * s, stroke=1, fill=1)
            c.setFillColor(HexColor("#5A6168")); c.rect(bx + 2.5 * s, cy + 6 * s, 3 * s, 2 * s, stroke=1, fill=1)
            pen.text(bx + 4 * s, cy - 5 * s - (11 if i % 2 == 0 else 22), lab, src, "R", BODY, INK, "c")
        kx = x0 + 3 * 11.5 * s + 4.5 * s
        c.setFillColor(HexColor("#E9A93B")); c.circle(kx, cy + 1 * s, 4.5 * s, stroke=1, fill=1)
        c.setFillColor(PANEL); c.circle(kx, cy + 1 * s, 2 * s, stroke=1, fill=1)
        pen.text(kx, cy - 5 * s - 22, "Kapton", "§9.2", "R", BODY, INK, "c")
    elif kind == "ill_press":
        s = min(w / 62.0, h / 34.0)
        x = cx - 30 * s; w = 60 * s; y = cy - 12 * s
        c.setFillColor(HexColor("#E8E2D6")); c.rect(x, y + 2 * s, w, 3 * s, stroke=0, fill=1)
        pen.text(x, y + 2 * s - 11, "felt-covered table", "§9.5", "R", BODY, GREY)
        c.setFillColor(HexColor("#AEB5BD")); c.rect(x + 4 * s, y + 5 * s, w - 8 * s, 1.2 * s, stroke=1, fill=1)
        c.setFillColor(HexColor("#3B3F45")); c.rect(x + 12 * s, y + 6.2 * s, w - 24 * s, 6 * s, stroke=1, fill=1)
        c.setFillColor(HexColor("#C9CDD2"))
        c.rect(x + 8 * s, y + 13 * s, w - 16 * s, 2.4 * s, stroke=1, fill=1)
        for xx in (x + 10 * s, x + w - 10 * s):
            p = c.beginPath(); p.moveTo(xx, y + 22 * s); p.lineTo(xx, y + 15.8 * s); c.drawPath(p, stroke=1, fill=0)
            p = c.beginPath(); p.moveTo(xx - 1.5 * s, y + 17.5 * s); p.lineTo(xx, y + 15.6 * s); p.lineTo(xx + 1.5 * s, y + 17.5 * s)
            c.drawPath(p, stroke=1, fill=0)
        pen.text(cx, y + 23.5 * s, "≈ 0.8–1 kN on the tape band", "§9.5", "R", BODY, INK, "c")
        pen.text(cx, y + 8.4 * s, "module", "§9.5", "R", BODY, white, "c")
    pen.text(X0 + W0 - 1 * MM, Y0 - 1.5 * MM, "illustration", "-", "I", BODY, GREY, "r")


def drawing_crop(name):
    k = 3307 / 2296
    crops = {
        "crop_j1": ("GF_Jig_J1.png", (60, 140, 1010, 1060)),
        "crop_j2": ("GF_Jig_J2_p1.png", (85, 180, 1060, 1065)),
        "crop_j2tail": ("GF_Jig_J2_p2.png", (160, 230, 1440, 1010)),
        "crop_gauge": ("GF_TailFoldGauge.png", (1080, 160, 2140, 540)),
        "crop_bonding": ("GF_BondingAids.png", (80, 285, 1400, 1290)),
        "crop_glass_in": ("GF_Glass.png", (75, 250, 1250, 1062)),
    }
    if name == "crop_corner":
        ka = 4960 / 2296
        return D.Img(os.path.join(V.DRAWINGS, "GF_Appearance.png"),
                     crop=(int(1843 * ka), int(146 * ka), int(2226 * ka), int(531 * ka)), do_trim=False, max_px=1000)
    f, (a, b, cc, d) = crops[name]
    return D.Img(os.path.join(V.DRAWINGS, f), crop=(int(a * k), int(b * k), int(cc * k), int(d * k)), max_px=1700)


def part_image(c, pen, name, kind, x, y, w, h):
    if name.startswith("ill_"):
        ill_draw(c, pen, name, x, y, w, h)
        return
    if name == "part_frame_both":
        a = img("part_frame_front"); b = img("part_frame_back")
        D.place(c, a, x, y + h * 0.51, w, h * 0.49)
        D.place(c, b, x, y, w, h * 0.49)
        return
    if name.startswith("crop_"):
        D.place(c, drawing_crop(name), x, y, w, h, jpeg=False)
        return
    D.place(c, img(name), x, y, w, h)


def bom_card(c, pen, b, x, y, w, h):
    D.rrect(c, x, y, w, h, 3, stroke=RULE, fill=white)
    iw = 44 * MM
    c.setFillColor(PANEL); c.roundRect(x + 1.2, y + 1.2, iw, h - 2.4, 2.5, stroke=0, fill=1)
    part_image(c, pen, b["image"], b["image_kind"], x + 3 * MM, y + 11.5 * MM, iw - 5 * MM, h - 14 * MM)
    kind = {"render": "CAD render", "illustration": "illustration"}.get(b["image_kind"], b["image_kind"])
    note, nsrc, _ = T(b["image_note"]) if isinstance(b.get("image_note"), dict) else ("", "-", {})
    label = (kind + (": " + note if note else "")) if b["image_kind"] != "illustration" else note
    if label:
        pen.para(x + 2.5 * MM, y + 9.0 * MM, iw - 3 * MM, label, nsrc, size=BODY, color=GREY, max_lines=2, lead=1.12)
    tx = x + iw + 4 * MM; tw = w - iw - 6 * MM
    c.setFillColor(ACCENT); c.circle(tx + 3 * MM, y + h - 5.6 * MM, 3 * MM, stroke=0, fill=1)
    pen.text(tx + 3 * MM, y + h - 6.9 * MM, str(b["no"]), "structure: BOM item number", "SB", 10, white, "c")
    pen.para(tx + 8 * MM, y + h - 2.6 * MM, tw - 8 * MM, b["name"], b.get("name_src", "-"), "SB", 10.5, INK,
             max_lines=2, lead=1.1)
    nl = len(D.wrap(b["name"], tw - 8 * MM, "SB", 10.5))
    yy = y + h - (8.6 if nl == 1 else 12.6) * MM
    yy -= ppara(pen, tx, yy, tw, b["purpose"], color=ACCENT, max_lines=2, lead=1.12) + 0.8 * MM
    labels = C["bom_page"]["field_labels"]
    keys = ["qty", "material", "size", "make", "who", "process", "file", "cost"]
    lw_ = 22 * MM
    for lab, k in zip(labels, keys):
        t, s_, mv = T(b[k])
        lines = D.wrap(t, tw - lw_, "R", BODY)
        if len(lines) > 2:
            raise ValueError("field too long: %s %s" % (b["no"], t))
        pen.text(tx, yy - BODY, lab, "-", "R", BODY, GREY)
        for ln in lines:
            pen.text(tx + lw_, yy - BODY, ln, s_, "R", BODY, INK, mvals=mv)
            yy -= BODY * 1.13
        yy -= 0.35 * MM
    if yy < y + 1 * MM:
        raise ValueError("card overflow: %s (%.1f mm)" % (b["no"], (y + 1 * MM - yy) / MM))


def variant_panel(c, pen, x, y, w, h):
    VP = C["variant_panel"]
    D.rrect(c, x, y, w, h, 3, fill=ACCENT_L)
    pen.text(x + 4 * MM, y + h - 6.5 * MM, VP["title"], VP["src"], "SB", 11, ACCENT)
    iw = 62 * MM
    r4 = D.Img(os.path.join(V.RENDERS, "Fusion_Assembly_front_R4_closeup_F1.png"), do_trim=False,
               crop=(0, 150, 1600, 1200), max_px=1200)
    D.place(c, r4, x + 4 * MM, y + 13 * MM, iw, h - 23 * MM, align="l", jpeg=True)
    caption(pen, x + 4 * MM, y + 9.5 * MM, iw + 4 * MM, VP["img_caption"], 2)
    yy = y + h - 12 * MM
    tx = x + iw + 10 * MM
    for r in VP["rows"]:
        c.setFillColor(ACCENT); c.circle(tx - 3 * MM, yy - 3.0, 1.3, stroke=0, fill=1)
        yy -= ppara(pen, tx, yy, w - (tx - x) - 5 * MM, r, max_lines=2, lead=1.2) + 2.5 * MM


def p_bom(page_items, title_key):
    def f(c, pen, n, N):
        P = C["bom_page"]
        D.page_frame(pen, "Mechanical parts list", n, N, FOOT)
        D.title(pen, P[title_key])
        ptext(pen, ML, PH - 26.5 * MM, P["intro"], size=10, color=GREY)
        cw = (CW - 5 * MM) / 2; ch = 53.6 * MM
        for i, b in enumerate(page_items):
            col, row = i % 2, i // 2
            x = ML + col * (cw + 5 * MM)
            y = PH - 30.5 * MM - (row + 1) * ch - row * 2.5 * MM
            bom_card(c, pen, b, x, y, cw, ch)
        if len(page_items) <= 4:
            rows = (len(page_items) + 1) // 2
            ytop = PH - 30.5 * MM - rows * ch - rows * 2.5 * MM
            variant_panel(c, pen, ML, 13 * MM, CW, ytop - 13 * MM)
    return f


def tool_card(c, pen, t, x, y, w, h):
    D.rrect(c, x, y, w, h, 3, stroke=RULE, fill=white)
    iw = 54 * MM
    c.setFillColor(PANEL); c.roundRect(x + 1.2, y + 1.2, iw, h - 2.4, 2.5, stroke=0, fill=1)
    part_image(c, pen, t["image"], t["image_kind"], x + 2.5 * MM, y + 10.5 * MM, iw - 3.5 * MM, h - 13 * MM)
    if not t["image_kind"].startswith("illustration") or "(" in t["image_kind"]:
        pen.para(x + 2.5 * MM, y + 8.6 * MM, iw - 3 * MM, t["image_kind"], t.get("image_kind_src", "-"), size=BODY,
                 color=GREY, max_lines=2,
                 lead=1.12)
    tx = x + iw + 4 * MM; tw = w - iw - 6 * MM
    c.setFillColor(ACCENT); c.roundRect(tx, y + h - 9 * MM, 9 * MM, 6 * MM, 1.5, stroke=0, fill=1)
    pen.text(tx + 4.5 * MM, y + h - 7.1 * MM, t["no"], "structure: tool number", "SB", 10, white, "c")
    pen.para(tx + 11 * MM, y + h - 2.8 * MM, tw - 11 * MM, t["name"], t.get("name_src", "-"), "SB", 10.5, INK,
             max_lines=2, lead=1.1)
    yy = y + h - 12 * MM
    yy -= ppara(pen, tx, yy, tw, t["purpose"], color=ACCENT, max_lines=3, lead=1.15) + 1.2 * MM
    lw_ = 16 * MM
    for lab, k in (("What", "spec"), ("How many", "qty"), ("Who", "who"), ("Cost", "cost")):
        tt, s_, mv = T(t[k])
        lines = D.wrap(tt, tw - lw_, "R", BODY)
        pen.text(tx, yy - BODY, lab, "-", "R", BODY, GREY)
        for ln in lines:
            pen.text(tx + lw_, yy - BODY, ln, s_, "R", BODY, INK, mvals=mv)
            yy -= BODY * 1.13
        yy -= 0.4 * MM
    if yy < y + 0.5 * MM:
        raise ValueError("tool card overflow: %s (%.1f mm)" % (t["no"], (y + 0.5 * MM - yy) / MM))


def p_tools(c, pen, n, N):
    P = C["tools_page"]
    D.page_frame(pen, "Mechanical parts list", n, N, FOOT)
    D.title(pen, P["title"])
    ptext(pen, ML, PH - 26.5 * MM, P["intro"], size=10, color=GREY)
    cw = (CW - 5 * MM) / 2; ch = 53.6 * MM
    for i, t in enumerate(C["tools"]):
        col, row = i % 2, i // 2
        x = ML + col * (cw + 5 * MM)
        y = PH - 30.5 * MM - (row + 1) * ch - row * 2.5 * MM
        tool_card(c, pen, t, x, y, cw, ch)


def p_summary(c, pen, n, N):
    P = C["summary_page"]
    D.page_frame(pen, "Mechanical parts list", n, N, FOOT)
    D.title(pen, P["title"])
    cols = P["cols"]
    widths = [14 * MM, 70 * MM, 22 * MM, 36 * MM, 48 * MM, CW - 190 * MM]
    x0 = ML; y = PH - 32 * MM
    c.setFillColor(ACCENT); c.rect(x0, y - 6.2 * MM, CW, 6.8 * MM, stroke=0, fill=1)
    xx = x0
    for cn, wd in zip(cols, widths):
        pen.text(xx + 1.8 * MM, y - 4.3 * MM, cn, "-", "SB", BODY, white)
        xx += wd
    y -= 6.6 * MM
    names = {str(b["no"]): b["name"] for b in C["bom"]}
    nsrcs = {str(b["no"]): b.get("name_src", "-") for b in C["bom"]}
    names.update(P["names"])
    for i, r in enumerate(P["rows"]):
        no = r["no"]
        b = [bb for bb in C["bom"] if str(bb["no"]) == no]
        qsrc = T(b[0]["qty"])[1] if b else P["qty_src"].get(no, "-")
        ct, cs, cm = T(r["cost"])
        cells = [(no, "structure: BOM item number", "SB", None), (names[no], nsrcs.get(no, "-"), "SB", None),
                 (P["qty_col"][no], qsrc, "R", None), (P["make_col"][no], "-", "R", None),
                 (r["src_type"], "§11.1", "R", None), (ct, cs, "R", cm)]
        wrapped = [D.wrap(t, wd - 3.6 * MM, f, BODY) for (t, s_, f, m), wd in zip(cells, widths)]
        nl = max(len(wl) for wl in wrapped)
        rh = (nl * BODY * 1.15 + 3.4 * MM)
        if i % 2 == 0:
            c.setFillColor(PANEL); c.rect(x0, y - rh, CW, rh, stroke=0, fill=1)
        xx = x0
        for (t, s_, f, m), wl, wd in zip(cells, wrapped, widths):
            yy = y - 1.6 * MM - BODY
            for ln in wl:
                pen.text(xx + 1.8 * MM, yy, ln, s_, f, BODY, INK, mvals=m)
                yy -= BODY * 1.15
            xx += wd
        y -= rh
    c.setStrokeColor(RULE); c.line(x0, y, x0 + CW, y)
    ppara(pen, ML, y - 3 * MM, CW, P["note"], color=GREY, max_lines=2)
    # a strip of the product renders under the table: the parts at a glance
    keys = ["part_sheet", "part_tape", "part_glass", "part_loca", "part_panel", "part_bead", "part_formex",
            "part_frame_front", "part_pcb"]
    sy = 14 * MM; sh = max(14 * MM, y - 12 * MM - sy)
    sw_ = CW / len(keys)
    nos = {b["image"]: b["no"] for b in C["bom"]}
    nos["part_frame_front"] = nos.get("part_frame_both")
    for i, k in enumerate(keys):
        D.place(c, img(k), ML + i * sw_ + 1 * MM, sy + 5 * MM, sw_ - 2 * MM, sh - 5 * MM)
        bxx = ML + i * sw_ + sw_ / 2
        c.setFillColor(ACCENT); c.circle(bxx, sy + 1.8 * MM, 2.4 * MM, stroke=0, fill=1)
        pen.text(bxx, sy + 0.6 * MM, str(nos[k]), "structure: BOM item number", "SB", 9, white, "c")


# =============================================================================================== who makes what
def p_suppliers(c, pen, n, N):
    P = C["suppliers_page"]
    D.page_frame(pen, "How we manufacture it", n, N, FOOT)
    D.title(pen, P["title"])
    ppara(pen, ML, PH - 24 * MM, CW, P["intro"], size=10, color=GREY, max_lines=2)
    sup = P["suppliers"]
    colw = 98 * MM; bh = 13.6 * MM; gap = 1.6 * MM
    y0 = PH - 36 * MM
    ax0 = ML + colw + 1.5 * MM; ax1 = 176 * MM
    for i, s in enumerate(sup):
        y = y0 - (i + 1) * bh - i * gap
        D.rrect(c, ML, y, colw, bh, 2.5, stroke=RULE, fill=white)
        c.setFillColor(ACCENT); c.rect(ML, y, 1.6 * MM, bh, stroke=0, fill=1)
        pen.text(ML + 4 * MM, y + bh - 4.6 * MM, s["name"], s["src"], "SB", 10, INK)
        pen.text(ML + 4 * MM, y + bh - 8.6 * MM, s["what"], s["src"], "R", BODY, INK)
        pen.text(ML + 4 * MM, y + bh - 12.4 * MM, s["where"], s["src"], "R", BODY, GREY)
        lt, ls, lm = T(s["lead"])
        ay = y + 2.6 * MM
        c.setStrokeColor(GREY_L); c.setLineWidth(0.8); c.line(ax0, ay, ax1, ay)
        p = c.beginPath(); p.moveTo(ax1, ay); p.lineTo(ax1 - 2.4 * MM, ay + 1.2 * MM); p.lineTo(ax1 - 2.4 * MM, ay - 1.2 * MM)
        p.close(); c.setFillColor(GREY_L); c.drawPath(p, stroke=0, fill=1)
        lines = D.wrap(lt, ax1 - ax0 - 4 * MM, "R", BODY)
        if len(lines) > 2:
            raise ValueError("lead text too long: " + lt)
        yy = ay + 1.6 * MM + (len(lines) - 1) * BODY * 1.15
        for ln in lines:
            pen.text(ax0 + 2 * MM, yy, ln, ls, "R", BODY, ACCENT, mvals=lm)
            yy -= BODY * 1.15
    bx = 178 * MM; bw = 62 * MM; top = y0; bot = y0 - len(sup) * (bh + gap) + gap
    D.rrect(c, bx, bot, bw, top - bot, 4, fill=ACCENT_L)
    pen.text(bx + 4 * MM, top - 7 * MM, P["bench_title"], "-", "SB", 12, ACCENT)
    yy = top - 11 * MM
    step_h = (top - bot - 36 * MM) / len(P["bench"])
    for s in P["bench"]:
        D.rrect(c, bx + 4 * MM, yy - step_h + 2.2 * MM, bw - 8 * MM, step_h - 2.2 * MM, 2, fill=white)
        t, s_, mv = T(s)
        pen.text(bx + 7 * MM, yy - step_h / 2 - 0.2 * MM, t, s_, "R", BODY, INK, mvals=mv)
        yy -= step_h
    ppara(pen, bx + 4 * MM, bot + 22 * MM, bw - 8 * MM, P["bench_note"], color=INK, max_lines=4, lead=1.2)
    ox = 247 * MM; ow = PW - MR - ox
    ay = (top + bot) / 2
    c.setStrokeColor(ACCENT); c.setLineWidth(1.4); c.line(bx + bw + 1 * MM, ay, ox - 1 * MM, ay)
    p = c.beginPath(); p.moveTo(ox - 1 * MM, ay); p.lineTo(ox - 4 * MM, ay + 1.6 * MM); p.lineTo(ox - 4 * MM, ay - 1.6 * MM)
    p.close(); c.setFillColor(ACCENT); c.drawPath(p, stroke=0, fill=1)
    h = img("hero_front")
    D.place(c, h, ox, ay - 18 * MM, ow, 34 * MM)
    pen.para(ox, ay - 20 * MM, ow, P["out_title"], "-", "SB", 10, INK, anchor="c")
    ppara(pen, ox, ay - 30 * MM, ow, P["critical"], color=GREY, max_lines=6, lead=1.2)


# =============================================================================================== process
def proc_col(c, pen, s, x, y, w, h):
    L = C["process_page"]["labels"]
    D.rrect(c, x, y, w, h, 3, stroke=RULE, fill=white)
    c.setFillColor(ACCENT); c.circle(x + 6 * MM, y + h - 6.5 * MM, 4 * MM, stroke=0, fill=1)
    pen.text(x + 6 * MM, y + h - 8.2 * MM, s["no"], "structure: station number (§9.1)", "SB", 13, white, "c")
    pen.para(x + 12 * MM, y + h - 2.6 * MM, w - 14 * MM, s["title"], "-", "SB", 11, INK, max_lines=2, lead=1.1)
    # text block measured first; the picture takes the space that is left
    tmp = D.Pen(c, V.Registry())
    what = T(s["what"])[0]
    th = tmp.height(what, w - 5 * MM, "R", BODY, 1.2) + 1.5 * MM
    for k in ("time", "wait", "tools"):
        th += len(D.wrap(T(s[k])[0], w - 21 * MM, "R", BODY)) * BODY * 1.18 + 0.6 * MM
    rt = T(s["risk"])[0]
    rh = tmp.height(rt, w - 8 * MM, "R", BODY, 1.18) + 9 * MM
    ih = h - 13 * MM - 6.5 * MM - th - rh - 6 * MM
    ih = min(ih, 80 * MM)
    c.setFillColor(PANEL); c.rect(x + 1.5, y + h - 13 * MM - ih, w - 3, ih, stroke=0, fill=1)
    part_image(c, pen, s["image"], s["image_kind"], x + 2 * MM, y + h - 12.5 * MM - ih + 1 * MM, w - 4 * MM, ih - 2 * MM)
    kind = s["image_kind"] if s["image_kind"] != "render" else "CAD render"
    pen.text(x + 2.5 * MM, y + h - 13 * MM - ih - 4 * MM, kind, "-", "R", BODY, GREY)
    yy = y + h - 13 * MM - ih - 6.5 * MM
    yy -= ppara(pen, x + 2.5 * MM, yy, w - 5 * MM, s["what"], max_lines=6, lead=1.2) + 1.5 * MM
    for lab, k in ((L["time"], "time"), (L["wait"], "wait"), (L["tools"], "tools")):
        t, s_, mv = T(s[k])
        pen.text(x + 2.5 * MM, yy - BODY, lab, "-", "SB", BODY, GREY)
        for ln in D.wrap(t, w - 21 * MM, "R", BODY):
            pen.text(x + 19 * MM, yy - BODY, ln, s_, "R", BODY, INK, mvals=mv)
            yy -= BODY * 1.18
        yy -= 0.6 * MM
    t, s_, mv = T(s["risk"])
    D.rrect(c, x + 2 * MM, y + 2 * MM, w - 4 * MM, rh, 2, fill=ACCENT_L)
    pen.text(x + 4 * MM, y + 2 * MM + rh - 5 * MM, L["risk"], "-", "SB", BODY, ACCENT)
    pen.para(x + 4 * MM, y + 2 * MM + rh - 6.5 * MM, w - 8 * MM, t, s_, size=BODY, lead=1.18, mvals=mv)
    if yy < y + 2 * MM + rh:
        raise ValueError("process column overflow: station %s (%.1f mm)" % (s["no"], (y + rh + 2 * MM - yy) / MM))


def p_process(steps, title_key):
    def f(c, pen, n, N):
        P = C["process_page"]
        D.page_frame(pen, "How we manufacture it", n, N, FOOT)
        D.title(pen, P[title_key])
        ptext(pen, ML, PH - 26.5 * MM, P["intro"], size=10, color=GREY)
        w = (CW - 3 * 4 * MM) / 4
        for i, s in enumerate(steps):
            proc_col(c, pen, s, ML + i * (w + 4 * MM), 13 * MM, w, PH - 46 * MM)
    return f


# =============================================================================================== timeline + cost
def label_bg(c, x, y, w, size=BODY):
    c.setFillColor(white); c.rect(x - 0.8, y - size * 0.28, w + 1.6, size * 1.15, stroke=0, fill=1)


def p_plan(c, pen, n, N):
    P = C["plan_page"]
    D.page_frame(pen, "How we manufacture it", n, N, FOOT)
    D.title(pen, P["title"])
    gx, gy, gw, gh = ML, 70 * MM, 150 * MM, 100 * MM
    pen.text(gx, gy + gh + 3 * MM, P["gantt_title"], "-", "SB", 10.5, INK)
    tasks = P["tasks"]
    lab_w = 56 * MM
    ax0 = gx + lab_w; ax1 = gx + gw
    gate = [t for t in tasks if t["lane"] == "gate"]
    known = [float(t["max"]) + float(t["start"]) for t in gate if t["max"] and t["t"] != "Glass RFQ → samples"]
    freeze = max(known)
    glass = [t for t in tasks if t["t"] == "Glass RFQ → samples"][0]
    glass_end = (float(glass["start"]) + float(glass["min"]), float(glass["start"]) + float(glass["max"]))
    ends = []
    rows = []
    for t in tasks:
        st = t["start"]
        if st == "freeze":
            s0 = freeze
        elif st == "glass_samples":
            s0 = glass_end[0]
        elif st == "T1":
            mould = [q for q in tasks if q["t"].startswith("Aluminium mould")][0]
            s0 = freeze + float(mould["min"])
        else:
            s0 = float(st)
        mn = float(t["min"]) if t["min"] is not None else None
        mx = float(t["max"]) if t["max"] is not None else None
        rows.append((t, s0, mn, mx))
        if mx is not None:
            ends.append(s0 + mx + float(t.get("extra") or 0))
    wk_max = math.ceil(max(ends) + 1.5)
    sx = (ax1 - ax0) / wk_max
    rh = gh / (len(rows) + 1.5)
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    for wk in range(0, wk_max + 1):
        X = ax0 + wk * sx
        c.line(X, gy, X, gy + gh - rh * 0.5)
        pen.text(X, gy - 4 * MM, str(wk), "structure: week axis", "R", BODY, GREY, "c")
    pen.text(ax0 + (ax1 - ax0) / 2, gy - 8.5 * MM, "weeks", "-", "R", BODY, GREY, "c")
    XF = ax0 + freeze * sx
    c.setStrokeColor(INK); c.setLineWidth(1.0); c.line(XF, gy, XF, gy + gh - rh * 0.4)
    y = gy + gh - rh
    for t, s0, mn, mx in rows:
        yb = y - rh * 0.72
        pen.text(gx, yb + rh * 0.18, t["t"], t["src"], "R", BODY, INK)
        X0 = ax0 + s0 * sx
        if mn is None:
            c.setStrokeColor(ACCENT); c.setDash(1.5, 1.5); c.setLineWidth(0.7)
            c.setFillColor(white); c.rect(X0, yb, 2.2 * sx, rh * 0.6, stroke=1, fill=1); c.setDash()
            lab = "duration not stated"
            label_bg(c, X0 + 2.2 * sx + 1.5 * MM, yb + rh * 0.15, D.sw(lab, "I"))
            pen.text(X0 + 2.2 * sx + 1.5 * MM, yb + rh * 0.15, lab, t["src"], "I", BODY, GREY)
        else:
            c.setFillColor(ACCENT); c.rect(X0, yb, max(mn * sx, 1.2), rh * 0.6, stroke=0, fill=1)
            if mx > mn:
                c.setFillColor(HexColor("#9CCBCF")); c.rect(X0 + mn * sx, yb, (mx - mn) * sx, rh * 0.6, stroke=0, fill=1)
            ex = float(t.get("extra") or 0)
            if ex:
                c.setStrokeColor(ACCENT); c.setDash(1.5, 1.5); c.rect(X0 + mx * sx, yb, ex * sx, rh * 0.6, stroke=1, fill=0)
                c.setDash()
            rng = t.get("label") or ((t["min"] if t["min"] == t["max"] else "%s–%s" % (t["min"], t["max"])) + " wk")
            if ex:
                rng += " (+%s)" % t["extra"]
            lx = max(X0 + (mx + ex) * sx + 1.5 * MM, XF + 1.5 * MM) if X0 < XF else X0 + (mx + ex) * sx + 1.5 * MM
            label_bg(c, lx, yb + rh * 0.15, D.sw(rng))
            pen.text(lx, yb + rh * 0.15, rng, t["src"], "R", BODY, INK)
        y -= rh
    ft, fs, fm = T(P["freeze_label"])
    pen.text(XF + 1.5 * MM, gy + gh - rh * 0.25, ft, fs, "SB", BODY, INK, mvals=fm)
    ut, us, um = T(P["first_units"])
    pen.text(ax1, gy - 13 * MM, ut, us, "SB", BODY, ACCENT, "r", mvals=um)
    ppara(pen, gx, gy - 16 * MM, gw, P["gantt_note"], color=GREY, max_lines=3)
    # ---- cost (right)
    cx0 = 176 * MM; cw = PW - MR - cx0
    ptext(pen, cx0, gy + gh + 3 * MM, P["cost_title"], font="SB", size=10.5, color=INK)
    rows = P["cost_rows"]
    hi = max(float(r["high"].replace(",", "")) for r in rows)
    lab_w = 40 * MM
    bx0 = cx0 + lab_w; bw = cw - lab_w - 14 * MM
    rhh = 8.2 * MM
    yy = gy + gh - 2 * MM
    for r in rows:
        lo, li, hg = (float(r[k].replace(",", "")) for k in ("low", "likely", "high"))
        pen.text(cx0, yy - 3.6 * MM, r["t"], r["src"], "R", BODY, INK)
        sub = "%s – %s k" % ("{:g}".format(lo / 1000), "{:g}".format(hg / 1000))
        pen.text(cx0, yy - 7.2 * MM, sub, r["src"] + " (low – high)", "R", BODY, GREY)
        c.setFillColor(HexColor("#C7E2E4")); c.rect(bx0 + lo / hi * bw, yy - 6.4 * MM, (hg - lo) / hi * bw, 1.4 * MM,
                                                     stroke=0, fill=1)
        c.setFillColor(ACCENT if r["kind"] == "one-off" else HexColor("#4E9AA1"))
        c.rect(bx0, yy - 4.6 * MM, li / hi * bw, 3.4 * MM, stroke=0, fill=1)
        lab = "%s k" % ("{:g}".format(li / 1000))
        lx = bx0 + li / hi * bw + 1.2 * MM
        label_bg(c, lx, yy - 3.9 * MM, D.sw(lab, "SB"))
        pen.text(lx, yy - 3.9 * MM, lab, r["src"] + " (likely, k = 1,000 TRY)", "SB", BODY, INK)
        yy -= rhh
    yy -= 2 * MM
    c.setFillColor(ACCENT); c.rect(cx0, yy - 3 * MM, 3 * MM, 3 * MM, stroke=0, fill=1)
    pen.text(cx0 + 4.5 * MM, yy - 2.6 * MM, "one-off", "-", "R", BODY, INK)
    c.setFillColor(HexColor("#4E9AA1")); c.rect(cx0 + 22 * MM, yy - 3 * MM, 3 * MM, 3 * MM, stroke=0, fill=1)
    pen.text(cx0 + 26.5 * MM, yy - 2.6 * MM, "per unit, for 100 ovens", "§11.4", "R", BODY, INK)
    c.setFillColor(HexColor("#C7E2E4")); c.rect(cx0 + 66 * MM, yy - 2.2 * MM, 6 * MM, 1.6 * MM, stroke=0, fill=1)
    pen.text(cx0 + 73.5 * MM, yy - 2.6 * MM, "low – high", "-", "R", BODY, INK)
    ppara(pen, cx0, yy - 6 * MM, cw, P["cost_note"], color=GREY, max_lines=4, lead=1.2)
    tw = (CW - 2 * 4 * MM) / 3
    ty = 13 * MM; th = 19 * MM
    for i, tl in enumerate(P["cost_tiles"]):
        x = ML + i * (tw + 4 * MM)
        D.rrect(c, x, ty, tw, th, 3, fill=ACCENT_L)
        t, s_, mv = T({"t": tl["big"], "src": tl["src"]})
        pen.text(x + 4 * MM, ty + th - 8.5 * MM, t, s_, "SB", 17, ACCENT, mvals=mv)
        t, s_, mv = T({"t": tl["small"], "src": tl["src"]})
        pen.para(x + 4 * MM, ty + th - 10 * MM, tw - 8 * MM, t, s_, size=BODY, max_lines=2, lead=1.15, mvals=mv)


# =============================================================================================== gates + decisions
def checkbox(c, x, y, s, done=False):
    c.setStrokeColor(INK); c.setLineWidth(0.8); c.setFillColor(white)
    c.rect(x, y, s, s, stroke=1, fill=1)
    if done:
        c.setStrokeColor(ACCENT); c.setLineWidth(1.4)
        p = c.beginPath(); p.moveTo(x + s * 0.18, y + s * 0.5); p.lineTo(x + s * 0.42, y + s * 0.22)
        p.lineTo(x + s * 0.85, y + s * 0.82); c.drawPath(p, stroke=1, fill=0)


def p_gates(c, pen, n, N):
    P = C["gates_page"]
    D.page_frame(pen, "Before we order anything", n, N, FOOT)
    D.title(pen, P["title"])
    t, s_, mv = T(P["verified"])
    pen.text(ML, PH - 26.5 * MM, t, s_, "R", 10, GREY, mvals=mv)
    gx, gw = ML, 132 * MM
    pen.text(gx, PH - 34 * MM, P["gates_title"], "-", "SB", 11, INK)
    y = PH - 37 * MM
    gauge = drawing_crop("crop_gauge")
    tmp = D.Pen(c, V.Registry())
    for i, g in enumerate(P["gates"]):
        tw_ = gw - 13 * MM - (40 * MM if i == 1 else 0)
        dt_ = T(g["d"])[0]
        gh = tmp.height(dt_, tw_, "R", BODY, 1.15) + 15.5 * MM
        gh = max(gh, 24 * MM if i == 1 else 0)
        D.rrect(c, gx, y - gh, gw, gh - 1.5 * MM, 3, stroke=RULE, fill=white)
        checkbox(c, gx + 3 * MM, y - 8 * MM, 4.4 * MM)
        pen.text(gx + 10 * MM, y - 6.6 * MM, "%d  %s" % (i + 1, g["t"]), "structure: gate order (§11.2)", "SB", 10, INK)
        ppara(pen, gx + 10 * MM, y - 8.4 * MM, tw_, g["d"], max_lines=4, lead=1.15)
        dt, ds, dm = T(g["decides"])
        pen.text(gx + 10 * MM, y - gh + 3.6 * MM, "decides: " + dt, ds, "SB", BODY, ACCENT, mvals=dm)
        if i == 1:
            D.place(c, gauge, gx + gw - 42 * MM, y - gh + 2.5 * MM, 40 * MM, gh - 6 * MM)
        y -= gh
    y -= 3 * MM
    pen.text(gx, y - 4 * MM, P["mould_title"], "-", "SB", 11, INK)
    y -= 7 * MM
    for i, m_ in enumerate(P["mould"]):
        x = gx + (i % 2) * (gw / 2)
        yy = y - (i // 2) * 11 * MM
        D.rrect(c, x, yy - 10 * MM, gw / 2 - 2 * MM, 9.4 * MM, 2, fill=ACCENT_L)
        pen.text(x + 3 * MM, yy - 4.4 * MM, m_["t"], "-", "R", BODY, INK)
        t, s_, mv = T({"t": m_["v"], "src": m_["src"]})
        pen.text(x + 3 * MM, yy - 8.6 * MM, t, s_, "SB", BODY, ACCENT, mvals=mv)
    dx = 154 * MM; dw = PW - MR - dx
    pen.text(dx, PH - 34 * MM, P["dec_title"], "-", "SB", 11, INK)
    y = PH - 38 * MM
    rh = 5.55 * MM
    for i, d in enumerate(P["decisions"]):
        if i % 2 == 0:
            c.setFillColor(PANEL); c.rect(dx, y - rh, dw, rh, stroke=0, fill=1)
        checkbox(c, dx + 1.5 * MM, y - rh + 1.2 * MM, 3.2 * MM, done=not d["open"])
        pen.text(dx + 6.5 * MM, y - rh + 1.7 * MM, d["id"], d["src"], "SB", BODY, INK)
        pen.text(dx + 15 * MM, y - rh + 1.7 * MM, d["t"], d["src"], "R", BODY, INK)
        st = ("decided: " if not d["open"] else "open · rec.: ") + d["rec"]
        pen.text(dx + dw - 1.5 * MM, y - rh + 1.7 * MM, st, d["src"], "R", BODY, ACCENT if not d["open"] else GREY, "r")
        y -= rh
    y -= 4 * MM
    # not-verified box sized to its content
    hh = 9 * MM
    for u in P["unverified"]:
        hh += tmp.height(T(u)[0], dw - 9 * MM, "R", BODY, 1.17) + 0.8 * MM
    hh += 2 * MM + tmp.height(T(P["margins"])[0], dw - 6 * MM, "R", BODY, 1.17) + 3 * MM
    D.rrect(c, dx, y - hh, dw, hh, 3, stroke=ACCENT, fill=white, lw=1.0)
    pen.text(dx + 3 * MM, y - 5.5 * MM, P["unverified_title"], "-", "SB", 10.5, ACCENT)
    yy = y - 8 * MM
    for u in P["unverified"]:
        c.setFillColor(ACCENT); c.circle(dx + 4.5 * MM, yy - 2.6, 1.1, stroke=0, fill=1)
        yy -= ppara(pen, dx + 6.5 * MM, yy, dw - 9 * MM, u, max_lines=2, lead=1.17) + 0.8 * MM
    yy -= 0.5 * MM
    c.setStrokeColor(RULE); c.line(dx + 3 * MM, yy, dx + dw - 3 * MM, yy)
    ppara(pen, dx + 3 * MM, yy - 1.2 * MM, dw - 6 * MM, P["margins"], color=INK, max_lines=3, lead=1.17)


# =============================================================================================== electronics
# Part number and Maker are as wide as their longest unbreakable word (CX3225GB10000P0HPQCC, STMicroelectronics)
EW = [21 * MM, 7 * MM, 57 * MM, 56 * MM, 40 * MM, 29 * MM, 17 * MM, 15 * MM, 25 * MM]
ELEAD = 1.08
NBSP = chr(160)   # no-break space: joins a number to its unit while wrapping


def ewrap(t, w, refs=False):
    """wrap at spaces only, or after a hyphen inside a long word (Electro-Mechanics, SAT70AT40D21-33KN-CTP-V1);
    a word is never cut anywhere else - if one does not fit, the column is too narrow and the build stops"""
    if refs and "," in t and " " not in t:
        t = t.replace(",", ", ")      # reference lists only (C5,C8 -> C5, C8); part numbers stay verbatim
    # keep a number with its unit (7 A, 105 °C, 0.5 mm) on one line
    t = __import__("re").sub(r"(\d) (?=[A-Za-zµΩ°%])", lambda mo: mo.group(1) + NBSP, t)
    units = []
    for word in t.split(" "):
        if D.sw(word) <= w:
            units.append((word, True))
            continue
        pieces = [p_ for p_ in __import__("re").split(r"(?<=-)", word) if p_]
        for k, p_ in enumerate(pieces):
            if D.sw(p_) > w:
                raise ValueError("electronics table: '%s' does not fit a %.1f mm column" % (word, w / MM))
            units.append((p_, k == len(pieces) - 1))
    lines, cur, sep = [], "", True
    for u, ends_word in units:
        cand = (cur + (" " if sep else "") + u) if cur else u
        if D.sw(cand) <= w:
            cur = cand
        else:
            lines.append(cur)
            cur = u
        sep = ends_word
    lines.append(cur)
    return [l_.replace(NBSP, " ") for l_ in lines]


def elec_cells(l):
    price = V.fmt_price(l.get("unit_price_usd"))
    return [l["refs"] or "—", str(l["qty"]), l["part"] or "—", l["role"] or "—", l["mpn"] or "—",
            l["manufacturer"] or "—", l["supplier"] or "—", price, l["status"]]


def elec_rows(E):
    rows = []
    for g in E["groups"]:
        rows.append(("group", g))
        for l in g["lines"]:
            rows.append(("line", l))
    rows.append(("extra_head", None))
    for l in E["not_in_component_total"]:
        rows.append(("line", l))
    heights = []
    for kind, r in rows:
        if kind == "group":
            nl = len(D.wrap(r["what_it_does"], CW - 4 * MM, "R", BODY))
            heights.append(5.8 * MM + nl * BODY * ELEAD + 1.0 * MM)
        elif kind == "extra_head":
            heights.append(7.5 * MM)
        else:
            cells = elec_cells(r)
            nl = max(len(ewrap(t, w - 2.4 * MM, k == 0)) for k, (t, w) in enumerate(zip(cells[:8], EW[:8])))
            heights.append(max(nl * BODY * ELEAD + 1.1 * MM, 4.8 * MM))
    return rows, heights


def p_elec_factory(E):
    rows, heights = elec_rows(E)
    LEG = 21 * MM                                   # bottom reserve on a page that carries the status legend
    first_avail = (PH - 31 * MM - 52 * MM) - LEG - 6.6 * MM
    other_avail = (PH - 31 * MM) - 12.5 * MM - 6.6 * MM
    pages = []
    cur = []; avail = first_avail; used = 0
    for i, (r, h) in enumerate(zip(rows, heights)):
        need = h + (heights[i + 1] if r[0] in ("group", "extra_head") and i + 1 < len(heights) else 0)
        if used + need > avail and cur:
            pages.append(cur); cur = []; used = 0; avail = other_avail
        cur.append((r, h)); used += h
    if cur:
        pages.append(cur)
    # the last page carries the legend too: keep its rows clear of it
    last_avail = (PH - 31 * MM) - LEG - 6.6 * MM
    while len(pages) > 1 and sum(h for _, h in pages[-1]) > last_avail:
        spill = []
        while sum(h for _, h in pages[-1]) > last_avail:
            spill.insert(0, pages[-1].pop())
        pages.append(spill)
    return [_elec_page(E, chunk, pi == 0, pi == len(pages) - 1) for pi, chunk in enumerate(pages)]


def status_tag(c, pen, x, y, st):
    style = {"OK": (None, GREY), "SHORT": (ACCENT, white), "SUBSTITUTE": (None, ACCENT), "NOT_SOURCED": (INK, white)}
    fill, col = style.get(st, (None, INK))
    label = st.replace("_", " ")
    w = D.sw(label, "SB", BODY) + 1.8 * MM
    if fill is not None:
        c.setFillColor(fill); c.roundRect(x, y - 0.75 * MM, w, BODY + 0.85 * MM, 1.5, stroke=0, fill=1)
    elif st == "SUBSTITUTE":
        c.setStrokeColor(ACCENT); c.setLineWidth(0.6); c.roundRect(x, y - 0.75 * MM, w, BODY + 0.85 * MM, 1.5, stroke=1, fill=0)
    pen.text(x + 0.9 * MM, y + 0.2, label, "elec", "SB", BODY, col)
    return w


def _elec_page(E, chunk, first, last=False):
    P = C["elec_page"]

    def f(c, pen, n, N):
        D.page_frame(pen, "Electronics parts list", n, N, FOOT)
        D.title(pen, P["title"] if first else P["title2"])
        y = PH - 31 * MM
        if first:
            pen.text(ML, PH - 26.5 * MM, "Price basis: ", "-", "SB", 10, GREY)
            hh = pen.para(ML + D.sw("Price basis: ", "SB", 10), PH - 26.5 * MM + 10, CW - 30 * MM, E["price_basis"],
                          "elec", size=BODY, color=GREY, max_lines=2, lead=1.2)
            cy0 = PH - 33 * MM - hh
            pen.text(ML, cy0 - 4 * MM, P["chart_title"], "-", "SB", 10.5, INK)
            sums = [(g["title"], sum(l["line_usd_per_board"] or 0 for l in g["lines"])) for g in E["groups"]]
            mx = max(v for _, v in sums)
            bh = 4.0 * MM
            yy = cy0 - 6.5 * MM
            half = (len(sums) + 1) // 2
            for i, (tt, v) in enumerate(sums):
                col, row = i // half, i % half
                xo = col * (CW / 2 + 2 * MM)
                yb = yy - row * (bh + 1.4 * MM)
                pen.text(ML + xo, yb - bh + 1.0 * MM, tt, "elec", "R", BODY, INK)
                bwid = (CW / 2 - 66 * MM - 18 * MM)
                c.setFillColor(ACCENT); c.rect(ML + xo + 64 * MM, yb - bh, v / mx * bwid, bh - 0.6 * MM, stroke=0, fill=1)
                pen.text(ML + xo + 64 * MM + v / mx * bwid + 1.5 * MM, yb - bh + 1.0 * MM, "%.2f" % v,
                         "elec: sum of line_usd_per_board", "SB", BODY, INK)
            tot = E["totals"]
            t = ("Components per board: %.2f USD (%d lines, %d placements). Not included: display panel, bare PCB, "
                 "assembly, glass front (listed at the end)." % (tot["components_usd_per_board"], tot["lines"],
                                                               tot["placements"]))
            ylast = yy - half * (bh + 1.4 * MM) - 1.0 * MM
            pen.text(ML, ylast - 2 * MM, t, "elec", "SB", BODY, INK)
            y = ylast - 5 * MM
        c.setFillColor(ACCENT); c.rect(ML, y - 6.2 * MM, CW, 6.6 * MM, stroke=0, fill=1)
        xx = ML
        for cn, wd in zip(P["cols"], EW):
            pen.text(xx + 1.2 * MM, y - 4.3 * MM, cn, "-", "SB", BODY, white)
            xx += wd
        y -= 6.6 * MM
        for (kind, r), h in chunk:
            if kind == "group":
                c.setFillColor(ACCENT_L); c.rect(ML, y - h, CW, h, stroke=0, fill=1)
                s = sum(l["line_usd_per_board"] or 0 for l in r["lines"])
                pen.text(ML + 1.5 * MM, y - 4.6 * MM, r["title"], "elec", "SB", 10, ACCENT)
                pen.text(PW - MR - 1.5 * MM, y - 4.6 * MM, "%.2f USD per board" % s, "elec: sum of line_usd_per_board",
                         "SB", BODY, ACCENT, "r")
                pen.para(ML + 1.5 * MM, y - 5.3 * MM, CW - 4 * MM, r["what_it_does"], "elec", size=BODY, color=INK,
                         max_lines=3, lead=ELEAD)
            elif kind == "extra_head":
                pen.text(ML + 1.5 * MM, y - 5.4 * MM, P["extra_title"] + " (prices shown where the files have one)",
                         "-", "SB", 10, INK)
                c.setStrokeColor(RULE); c.line(ML, y - h + 0.5, ML + CW, y - h + 0.5)
            else:
                cells = elec_cells(r)
                xx = ML
                for k, (t, wd) in enumerate(zip(cells, EW)):
                    yy = y - 0.8 * MM - BODY
                    if k == 8:
                        status_tag(c, pen, xx + 1.0 * MM, yy, t)
                    elif k == 6 and r.get("url"):
                        lns = ewrap(t, wd - 2.4 * MM)
                        y_top = yy + BODY * 0.85
                        for ln in lns:
                            pen.text(xx + 1.2 * MM, yy, ln, "elec", "R", BODY, ACCENT)
                            c.setStrokeColor(ACCENT); c.setLineWidth(0.4)
                            c.line(xx + 1.2 * MM, yy - 1.0, xx + 1.2 * MM + D.sw(ln), yy - 1.0)
                            yy -= BODY * ELEAD
                        # one link annotation per supplier cell
                        c.linkURL(r["url"], (xx + 1.0 * MM, yy + BODY * ELEAD - BODY * 0.3,
                                             xx + 1.4 * MM + max(D.sw(l_) for l_ in lns), y_top), relative=0, thickness=0)
                    else:
                        for ln in ewrap(t, wd - 2.4 * MM, k == 0):
                            pen.text(xx + 1.2 * MM, yy, ln, "elec" if k != 7 else "elec: unit_price_usd", "R", BODY,
                                     INK, "l")
                            yy -= BODY * ELEAD
                    xx += wd
                c.setStrokeColor(RULE); c.setLineWidth(0.4); c.line(ML, y - h, ML + CW, y - h)
            y -= h
        if first or last:
            ppara(pen, ML, 19.5 * MM, CW, {"t": P["status_help"]["t"] + " Supplier names are links.",
                                           "src": "elec"}, color=GREY, max_lines=2, lead=1.15)
            if y < 19.5 * MM + 0.5 * MM:
                raise ValueError("electronics legend overlaps the table")
    return f


# =============================================================================================== files + glossary
def p_files(c, pen, n, N):
    P = C["files_page"]
    D.page_frame(pen, "Files and words", n, N, FOOT)
    D.title(pen, P["title"])
    x = ML; w = 128 * MM
    y = PH - 36 * MM
    for f in P["files"]:
        pen.text(x, y, f["t"], "-", "SB", 10, INK)
        pen.text(x, y - 4.6 * MM, f["p"], "structure: file path", "R", BODY, ACCENT)
        y -= 11.5 * MM
    ppara(pen, x, y + 1 * MM, w, P["rfq"], max_lines=3)
    # the drawing set as thumbnails
    sheets = [("GF-D01", "GF_Sheet_S4.png"), ("GF-D03", "GF_Sheet_R4.png"), ("GF-D10", "GF_Glass.png"),
              ("GF-D20", "GF_BondingAids.png"), ("GF-D21", "GF_TailFoldGauge.png"), ("GF-D30", "GF_Jig_J2_p1.png"),
              ("GF-D31", "GF_Jig_J1.png"), ("GF-D40", "GF_Appearance.png"), ("GF-D50", "GF_Frame_Inspection_p1.png")]
    ty = 16 * MM; tw = (w + 6 * MM) / 5; th = tw * 0.72
    pen.text(x, ty + 2 * th + 10 * MM, "The drawing set (one thumbnail per sheet)", "-", "SB", 10, INK)
    for i, (num, fn) in enumerate(sheets):
        col, row = i % 5, i // 5
        xx = x + col * tw; yy = ty + (1 - row) * (th + 5 * MM)
        im = D.Img(os.path.join(V.DRAWINGS, fn), do_trim=False, max_px=700)
        D.place(c, im, xx, yy, tw - 2 * MM, th, jpeg=True, frame=True)
        pen.text(xx, yy - 3.6 * MM, num, "structure: drawing number", "SB", BODY, INK)
    gx = 158 * MM; gw = PW - MR - gx
    pen.text(gx, PH - 34 * MM, P["glossary_title"], "-", "SB", 11, INK)
    y = PH - 38 * MM
    for g in P["glossary"]:
        D.rrect(c, gx, y - 12.2 * MM, gw, 11.4 * MM, 2, fill=PANEL)
        pen.text(gx + 3 * MM, y - 4.8 * MM, g["w"], g["src"], "SB", 10, ACCENT)
        ppara(pen, gx + 30 * MM, y - 1.6 * MM, gw - 33 * MM, {"t": g["d"], "src": g["src"]}, max_lines=2, lead=1.15)
        y -= 13.2 * MM


# =============================================================================================== main
def main():
    E = V.load_json(V.ELEC) if os.path.exists(V.ELEC) else None
    if E is None:
        raise SystemExit("electronics_bom.json missing: the fallback table is not built by this script")
    bom = C["bom"]
    pages = [p_cover, p_what, p_exploded, p_edge, p_bottom,
             p_bom(bom[0:6], "title"), p_bom(bom[6:12], "title2"), p_bom(bom[12:16], "title2"),
             p_tools, p_summary, p_suppliers,
             p_process(C["process"][0:4], "title"), p_process(C["process"][4:8], "title2"),
             p_plan, p_gates] + p_elec_factory(E) + [p_files]
    N = len(pages)
    c = canvas.Canvas(V.OUT_PDF, pagesize=(PW, PH), pageCompression=1, initialFontName=D.FN["R"],
                      initialFontSize=BODY)
    c.setTitle("Rev3.0 Oven Controller — Glass Front GF-2.1, visual overview")
    c.setSubject("What it is, what every piece is, how we manufacture it")
    c.setCreator("make_overview.py")
    c.setAuthor("")
    pen = D.Pen(c, REG)
    for i, f in enumerate(pages, 1):
        REG.page = i
        f(c, pen, i, N)
        c.showPage()
    c.save()
    REG.dump(os.path.join(V.HERE, "overview_provenance.json"))
    json.dump(CHECKS, open(os.path.join(V.HERE, "overview_layout_checks.json"), "w"), indent=1)
    print("wrote", V.OUT_PDF, N, "pages")


if __name__ == "__main__":
    main()
