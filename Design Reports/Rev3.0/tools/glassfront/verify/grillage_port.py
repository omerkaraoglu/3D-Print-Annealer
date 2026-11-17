"""Grillage, ring-section and glass-impact model of the glass-front concept - a COPY (not an import) of the port in
Design Reports/Rev3.0/tools/glassfront/concept/concept_gf2_calc.py sec. 5 / 6, which is itself a port of concept_calc.py
sec. 7 / 8. Neither concept script is imported or run here: concept_calc.py rewrites the master params when imported, and
concept_gf2_calc.py writes its outputs into the concept folder. The copy is validated in calc_gf.py against the GF-1.1
concept numbers (S4 0.139 / 0.067 / 0.066 / 0.092 / 0.067 mm at 50 N) before it is used.

Model: glass strips on a frame ring (one beam section per edge), corner links, studs as springs, VHB as an elastic band;
panel / LOCA / PCB stiffness NOT counted; frame E 3500, glass E 70000. All globals are set by setup(G).
"""
import math

import numpy as np

E_G, NU_G, RHO_G = 70000.0, 0.22, 2.5e-3          # [A] concept sec. 9
E_F, NU_F = 3500.0, 0.35                           # [A] PA6-GF30, concept sec. 9
G_F = E_F / (2 * (1 + NU_F))
I_LINK = 2 * 109.8
CFG = {}


def setup(G):
    """read the constants the concept used from the params object (vcommon.GF)"""
    d = G.drv
    CFG.update(g2=float(d["g2"]), lip_w=float(d["lip_w"]), fl_beyond=float(d["flange_beyond_glass"]), fl_t=float(d["flange_t"]),
               t_gap=float(d["t_gap"]), tape_w=float(d["tape_w"]), fast_off=float(d["fast_off"]), pocket_clr=float(d["pocket_clr"]),
               seat_w=float(G.SEAT_W), seat_ring_w=float(d["seat_ring_w"]), tape_margin=float(d["tape_margin"]))
    CFG["D_fl"] = E_F * CFG["fl_t"] ** 3 / (12 * (1 - NU_F ** 2))
    s0 = CFG["g2"] + CFG["lip_w"] + CFG["seat_ring_w"] + CFG["tape_margin"]
    CFG["SH0"], CFG["SH1"] = band_shares(s0, s0 + CFG["tape_w"], CFG["fast_off"])


def section_props(rects):
    A = sum((r[1] - r[0]) * (r[3] - r[2]) for r in rects)
    zc = sum((r[1] - r[0]) * (r[3] - r[2]) * (r[2] + r[3]) / 2 for r in rects) / A
    I = sum((r[1] - r[0]) * (r[3] - r[2]) ** 3 / 12 + (r[1] - r[0]) * (r[3] - r[2]) * ((r[2] + r[3]) / 2 - zc) ** 2 for r in rects)
    J = sum(max(r[1] - r[0], r[3] - r[2]) * min(r[1] - r[0], r[3] - r[2]) ** 3 / 3 for r in rects)
    zmin, zmax = min(r[2] for r in rects), max(r[3] for r in rects)
    return dict(A=A, zc=zc, I=I, J=J, c=max(abs(zmin - zc), abs(zmax - zc)), rects=rects)


def ring_rects(Zl, land, kind="side", s_fl_end=None, beam=None):
    """concept ring_section (kind 'side'); 'bridge' = no pocket wall / shelf (bend gap); beam = (s_in, s_out) adds the bottom wall"""
    g2, lip_w = CFG["g2"], CFG["lip_w"]
    s_pf = -land
    zfb = Zl["Z_STEPWALL_BACK"] if abs(Zl["Z_LANDPLATE_BACK"] - Zl["Z_FLANGE_BACK"]) < 0.5 else Zl["Z_FLANGE_BACK"]
    s_end = CFG["fl_beyond"] if s_fl_end is None else s_fl_end
    R_ = [(g2, g2 + lip_w, Zl["Z_GLASS_FRONT"], Zl["Z_SHEET_BACK"]),
          (g2, g2 + 2.5, Zl["Z_SHEET_BACK"], Zl["Z_STEPWALL_BACK"]),
          (g2 + 2.5, s_end, Zl["Z_FLANGE_FRONT"], zfb),
          (s_pf, g2, Zl["Z_LAND"], Zl["Z_LANDPLATE_BACK"])]
    if kind == "side":
        R_ += [(s_pf, s_pf + 2.5, Zl["Z_LANDPLATE_BACK"], 0.0),
               (s_pf - (CFG["seat_w"] + CFG["pocket_clr"]), s_pf, Zl["Z_SEAT"], Zl["Z_SHELF_BACK"])]
    if beam is not None:
        R_ = [r for r in R_ if r[0] != g2 + 2.5] + [(g2 + 2.5, beam[0], Zl["Z_FLANGE_FRONT"], zfb),
                                                    (beam[0], beam[1], Zl["Z_FLANGE_FRONT"], Zl["Z_TROUGH_TOP"])]
    return R_


def band_shares(a, b, Lf):
    a1, b1 = min(a, Lf), min(b, Lf)
    s0 = (b1 - b1 ** 2 / (2 * Lf)) - (a1 - a1 ** 2 / (2 * Lf))
    return s0, (b - a) - s0


def beam_k(EI, GJ, Lx):
    k = np.zeros((6, 6))
    b = np.array([[12, 6 * Lx, -12, 6 * Lx], [6 * Lx, 4 * Lx * Lx, -6 * Lx, 2 * Lx * Lx], [-12, -6 * Lx, 12, -6 * Lx], [6 * Lx, 2 * Lx * Lx, -6 * Lx, 4 * Lx * Lx]])
    idx = [0, 1, 3, 4]
    k[np.ix_(idx, idx)] = EI / Lx ** 3 * b
    k[2, 2] = k[5, 5] = GJ / Lx
    k[2, 5] = k[5, 2] = -GJ / Lx
    return k


def tmat(c, s):
    T = np.zeros((6, 6))
    for o in (0, 3):
        T[o, o] = 1.0
        T[o + 1, o + 1], T[o + 1, o + 2] = c, s
        T[o + 2, o + 1], T[o + 2, o + 2] = -s, c
    return T


def grillage(GLr, FLr, SECE, t_g, supports, vhb=False, line_q=0.0, loads=(), extra_ys=(), E_vhb=1.0, extra_xs=(), tab=None, ribs=()):
    """concept grillage (copied); SECE = {'top','bottom','left','right'} ring sections"""
    D_fl, SH0, SH1, t_gap, tape_w = CFG["D_fl"], CFG["SH0"], CFG["SH1"], CFG["t_gap"], CFG["tape_w"]
    gx0, gx1, gy0, gy1 = GLr
    gW_, gH_ = gx1 - gx0, gy1 - gy0
    D_g = E_G * t_g ** 3 / (12 * (1 - NU_G ** 2))
    fx0, fx1, fy0, fy1 = FLr
    xs = sorted({fx0, fx1, gx0, gx1} | {gx0 + gW_ * i / 16 for i in range(17)} | set(extra_xs) | (set(tab[:2]) if tab else set()))
    ys = sorted({fy0, fy1, gy0, gy1} | {gy0 + gH_ * i / 12 for i in range(13)} | set(extra_ys) | ({tab[2]} if tab else set()))
    xs = [x for i, x in enumerate(xs) if i == 0 or x - xs[i - 1] > 1.5]
    ys = [y for i, y in enumerate(ys) if i == 0 or y - ys[i - 1] > 1.5]
    assert gy1 in ys and gy0 in ys and gx0 in xs and gx1 in xs
    nx, ny = len(xs), len(ys)
    nid = lambda ix, iy: ix * ny + iy
    n = 3 * nx * ny
    K = np.zeros((n, n))
    elems = []

    def add_el(p, q, EI_g, EI_r, GJ, edge):
        (x1, y1), (x2, y2) = (xs[p // ny], ys[p % ny]), (xs[q // ny], ys[q % ny])
        Ln = math.hypot(x2 - x1, y2 - y1); c, s = (x2 - x1) / Ln, (y2 - y1) / Ln
        kl = beam_k(EI_g + EI_r, GJ, Ln); T = tmat(c, s)
        kg = T.T @ kl @ T
        dofs = [3 * p, 3 * p + 1, 3 * p + 2, 3 * q, 3 * q + 1, 3 * q + 2]
        K[np.ix_(dofs, dofs)] += kg
        elems.append((dofs, kl, T, EI_g, EI_r, edge))

    def trib(lines, i):
        lo = lines[i] - (lines[i] - lines[i - 1]) / 2 if i > 0 else lines[i]
        hi = lines[i] + (lines[i + 1] - lines[i]) / 2 if i < len(lines) - 1 else lines[i]
        return lo, hi

    for ix in range(nx):
        for iy in range(ny):
            for horiz in (True, False):
                if (horiz and ix == nx - 1) or ((not horiz) and iy == ny - 1):
                    continue
                p = nid(ix, iy); q = nid(ix + 1, iy) if horiz else nid(ix, iy + 1)
                if horiz:
                    xm, ym = (xs[ix] + xs[ix + 1]) / 2, ys[iy]; lo, hi = trib(ys, iy); ins = gx0 - 1e-9 <= xm <= gx1 + 1e-9
                    glo, ghi = gy0, gy1
                    edge = "top" if abs(ym - gy0) < 1e-6 else "bottom" if abs(ym - gy1) < 1e-6 else None
                else:
                    xm, ym = xs[ix], (ys[iy] + ys[iy + 1]) / 2; lo, hi = trib(xs, ix); ins = gy0 - 1e-9 <= ym <= gy1 + 1e-9
                    glo, ghi = gx0, gx1
                    edge = "left" if abs(xm - gx0) < 1e-6 else "right" if abs(xm - gx1) < 1e-6 else None
                if tab:
                    tx0, tx1, _ = tab
                    if horiz:
                        in_tab = xs[ix] >= tx0 - 1e-6 and xs[ix + 1] <= tx1 + 1e-6
                        if ys[iy] > fy1 + 1e-6 and not in_tab:
                            continue
                        if abs(ys[iy] - fy1) < 1e-6 and not in_tab:
                            hi = fy1
                    elif ys[iy + 1] > fy1 + 1e-6:
                        if not (tx0 - 1e-6 <= xs[ix] <= tx1 + 1e-6):
                            continue
                        lo, hi = max(lo, tx0), min(hi, tx1)
                bg = max(0.0, min(hi, ghi) - max(lo, glo)) if ins else 0.0
                bf = (hi - lo) - bg
                se = SECE[edge] if (ins and edge) else None
                EI_r = E_F * se["I"] if se else 0.0
                GJ = D_g * (1 - NU_G) * bg + D_fl * (1 - NU_F) * bf + (G_F * se["J"] if se else 0.0)
                if not horiz:
                    for rx, ry0, ry1, rEI, rGJ in ribs:
                        if abs(xm - rx) < 1e-6 and ry0 - 1e-6 <= ym <= ry1 + 1e-6:
                            EI_r += rEI; GJ += rGJ
                add_el(p, q, D_g * bg, EI_r + D_fl * bf, GJ, edge if se else None)
    for (cx, cy), (gxc, gyc) in zip(((fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)), ((gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1))):
        p = nid(xs.index(cx), ys.index(cy)); q = nid(xs.index(gxc), ys.index(gyc))
        add_el(min(p, q), max(p, q), 0.0, E_F * I_LINK, G_F * 60.0, None)
    sup = []
    for (sx, sy) in supports:
        ix = min(range(nx), key=lambda i: abs(xs[i] - sx)); iy = min(range(ny), key=lambda i: abs(ys[i] - sy))
        p = nid(ix, iy); sup.append(p); K[3 * p, 3 * p] += 2.0e4
    band = {}
    for ix in range(nx):
        for iy in range(ny):
            x, y = xs[ix], ys[iy]; lx = trib(xs, ix); ly = trib(ys, iy); w0 = w1 = 0.0
            if abs(y - fy0) < 1e-6 or abs(y - fy1) < 1e-6:
                w1 += SH1 * (lx[1] - lx[0])
            if abs(x - fx0) < 1e-6 or abs(x - fx1) < 1e-6:
                w1 += SH1 * (ly[1] - ly[0])
            if (abs(y - gy0) < 1e-6 or abs(y - gy1) < 1e-6) and gx0 - 1e-6 <= x <= gx1 + 1e-6:
                w0 += SH0 * (min(lx[1], gx1) - max(lx[0], gx0))
            if (abs(x - gx0) < 1e-6 or abs(x - gx1) < 1e-6) and gy0 - 1e-6 <= y <= gy1 + 1e-6:
                w0 += SH0 * (min(ly[1], gy1) - max(ly[0], gy0))
            if w0 + w1 > 0:
                band[nid(ix, iy)] = w0 + w1
    if vhb:
        for p, a in band.items():
            K[3 * p, 3 * p] += E_vhb / t_gap * a
    rhs, lp = [], []
    for (lx_, ly_) in loads:
        ix = min(range(nx), key=lambda i: abs(xs[i] - lx_)); iy = min(range(ny), key=lambda i: abs(ys[i] - ly_))
        f = np.zeros(n); f[3 * nid(ix, iy)] = 1.0; rhs.append(f); lp.append(nid(ix, iy))
    if line_q:
        f = np.zeros(n)
        for p, a in band.items():
            f[3 * p] = line_q / tape_w * a
        rhs.append(f); lp.append(None)
    dz = np.nonzero(np.abs(np.diag(K)) < 1e-12)[0]
    K[dz, dz] = 1.0
    U = np.linalg.solve(K, np.array(rhs).T).T
    perim = [nid(ix, iy) for ix in range(nx) for iy in range(ny)
             if ((abs(ys[iy] - gy0) < 1e-6 or abs(ys[iy] - gy1) < 1e-6) and gx0 - 1e-6 <= xs[ix] <= gx1 + 1e-6)
             or ((abs(xs[ix] - gx0) < 1e-6 or abs(xs[ix] - gx1) < 1e-6) and gy0 - 1e-6 <= ys[iy] <= gy1 + 1e-6)]
    perim_bot = [nid(ix, ys.index(gy1)) for ix in range(nx) if gx0 - 1e-6 <= xs[ix] <= gx1 + 1e-6]
    res = []
    for p_l, u in zip(lp, U):
        Mg = 0.0; sr = 0.0
        for dofs, kl, T, EIg, EIr, edge in elems:
            fl_ = kl @ (T @ u[dofs])
            Mx = max(abs(fl_[1]), abs(fl_[4])); tot = EIg + EIr
            if EIg > 0:
                Mg = max(Mg, Mx * D_g / tot)
            if edge:
                se = SECE[edge]
                sr = max(sr, Mx * (E_F * se["I"]) / tot * se["c"] / se["I"])
        res.append(dict(w=u[3 * p_l] if p_l is not None else None, w_perim=max(u[3 * p] for p in perim), w_bottom=max(u[3 * p] for p in perim_bot),
                        sig_g=6 * Mg / t_g ** 2, sig_r=sr, R=max(2.0e4 * u[3 * p] for p in sup)))
    return res


def sig_point(Pn, t, r0, a):
    """concept sec. 8: plate stress under a point load P on a loaded circle r0, support radius a"""
    rp = math.sqrt(1.6 * r0 ** 2 + t ** 2) - 0.675 * t if r0 < 0.5 * t else r0
    return 3 * Pn / (2 * math.pi * t ** 2) * ((1 + NU_G) * math.log(a / rp) + 1)


def impact(k, m_move, t, a):
    """concept sec. 8: 0.5 J steel ball (0.25 kg) on the glass; 'mass' = energy absorbed by the mass ratio, 'bound' = all 0.5 J"""
    E_def = 0.5 * m_move / (0.25 + m_move)
    res = {}
    for lab, E in (("bound", 0.5), ("mass", E_def)):
        F = math.sqrt(2 * E * k * 1000)
        ah = (3 * F * 10 / (4 * 3400)) ** (1 / 3)
        res[lab] = (F, sig_point(F, t, ah, a), E)
    return res
