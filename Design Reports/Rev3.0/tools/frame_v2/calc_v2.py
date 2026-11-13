"""Hand calculations for the carrier frame v2 (v1 calc.py adapted to the flange + stud bosses).

  <venv>/Scripts/python.exe calc_v2.py [--v1] [--frame f.step] [--params p.json]

Material: PA6-GF30 heat-stabilised, FR (V-0 / GWFI 960) - owner's values, low end at 110 C (FR grades ~15 %
weaker than the standard grade): tensile 75 MPa, long-term compressive creep allowance 15 MPa,
E 3500 MPa short term / 1750 MPa at 1000 h. CLTE 30 ppm/K along the flow, 70 ppm/K transverse; steel 12.

  1. PCB screw bosses (unchanged from v1)
  2. gasket force and compression tolerance (unchanged)
  3. STUD BOSSES: bearing under the DIN 9021 dia-12 washer on the tube top ring (OD STUD_OD / ID STUD_HOLE_D;
     the area measured on the STEP is used when cadcheck found the tube top), clamp margin per stud
  4. FLANGE bending at a stud boss: cantilever from the clamped tube to the wall, load = per-hole share of the
     worst gasket force + 10 g shock; (a) lever = stud offset, plate width = tube OD (brief, conservative);
     (b) as (a) with the radial rib (T-section); (c) lever = offset - OD/2 (bending at the tube face, the washer
     area does not bend), plate width = OD + 2 x lever (45 deg spread)
  5. BEAM LIFT per straight run between adjacent holes along each edge, corners counted as supports (brief).
     Section wall (WALL x (Z_PCB - Z_FRONT)) + flange (FLANGE_W x FLANGE_T, outside the wall) + shelf
     ((POCKET_CLR + SEAT_W) x SHELF_T, inside the wall), I about the combined centroid; v1 (no flange) gives
     309 mm4. Also measured on the STEP section at each run's midpoint (+-3, +-6 mm, min: avoids ribs).
     Info: corner overhangs as cantilevers, and runs walked round the corners (corner not a support).
  6. THERMAL mismatch frame vs steel sheet over the hole pattern (dT 60 K), from the locating pegs' midpoint
     (else the pattern centroid); vs the stud clearance (dia STUD_HOLE_D - M4) less the position tolerance
  7. weight and 10 g shock per stud / PCB screw
Output: out/calc.json, out/calc.md
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cadquery as cq

import common_v2 as C

SIG_T_110 = 75.0            # MPa tensile at 110 C (low end, FR grade)
TAU_110 = 0.6 * SIG_T_110   # MPa shear
CREEP_ALLOW = 15.0          # MPa long-term compressive / sustained allowance (low end of 15-20)
E_110 = 3500.0              # MPa short term
E_CREEP = 1750.0            # MPa at 1000 h
CLTE_FLOW, CLTE_TRANS, CLTE_STEEL = 30e-6, 70e-6, 12e-6     # 1/K
DT = 60.0                   # K, frame and sheet heated together from assembly temperature
G = 9.81
G_SHOCK = 10.0
WASHER_OD = 12.0            # DIN 9021 M4
M4_D = 4.0
POS_TOL = math.hypot(0.10, 0.075)   # frame hole position +-0.10 (ISO 20457 TG5 on 200 mm is larger, tool-held
                                    # +-0.1 assumed) and PEM stud +-0.075: RSS
PEG_HOLE_CLR = C.PEG_HOLE_CLR
GASKET_P_NOM, GASKET_P_MAX = 0.07, 0.25     # MPa closed-cell silicone sponge at 30 % / high compression case
SPAN_MIN = 0.5              # runs shorter than this are ignored
SECTION_SHIFTS = (0.0, -3.0, 3.0, -6.0, 6.0)   # mm: measured section taken at the run midpoint + these (min)


def boss(D):
    d, dp, Dd = D.SCREW_D, D.PILOT_D, D.BOSS_OD
    L_screw, tip = 9.5, 1.5                       # ST2.9 x 9.5; C-point taper not load bearing
    Le = L_screw - D.PCB_T - tip
    T, T_drive, K = 0.40, 0.20, 0.20              # Nm seating, Nm drive (typical), torque coefficient
    F_cons = T / (K * d * 1e-3)
    F_real = (T - T_drive) / (K * d * 1e-3)
    A_bear = math.pi / 4 * (Dd ** 2 - D.CBORE_D ** 2)
    A_shear = math.pi * d * Le * 0.6              # 0.6 = formed-thread fill factor
    p = F_cons * math.tan(math.radians(30)) / (math.pi * d * Le)
    lame = (Dd ** 2 + d ** 2) / (Dd ** 2 - d ** 2)
    hoop = p * lame
    return {"screw": "ISO 7049-C / DIN 7981 ST2.9x9.5 A2 (alt. PT K30x10)", "pilot_mm": dp, "boss_od_mm": Dd,
            "od_over_d": round(Dd / d, 3), "engaged_mm": round(Le, 2), "torque_install_Nm": T,
            "torque_drive_Nm": T_drive, "preload_cons_N": round(F_cons), "preload_real_N": round(F_real),
            "bearing_area_mm2": round(A_bear, 1), "bearing_cons_MPa": round(F_cons / A_bear, 1),
            "bearing_real_MPa": round(F_real / A_bear, 1), "creep_allow_MPa": CREEP_ALLOW,
            "thread_shear_cons_MPa": round(F_cons / A_shear, 1),
            "thread_shear_SF": round(TAU_110 / (F_cons / A_shear), 2),
            "hoop_cons_MPa": round(hoop, 1), "hoop_SF_short": round(SIG_T_110 / hoop, 1),
            "hoop_SF_longterm(0.4x)": round(0.4 * SIG_T_110 / hoop, 1)}


def gasket(D):
    o = (D.PX1 - D.PX0 - 2 * D.GASKET_OUT_INSET) * (D.PY1 - D.PY0 - 2 * D.GASKET_OUT_INSET)
    i = (D.VA[1] - D.VA[0] + 2 * D.GASKET_IN_MARGIN) * (D.VA[3] - D.VA[2] + 2 * D.GASKET_IN_MARGIN)
    A = o - i
    comp = D.GASKET_T * D.GASKET_COMP
    tol = math.sqrt(D.PANEL_T_TOL ** 2 + 0.10 ** 2 + 0.10 ** 2 + 0.05 ** 2)   # LCM, CTP stack, frame seat, sheet
    return {"area_mm2": round(A), "thickness_mm": D.GASKET_T, "compression_nom_mm": round(comp, 2),
            "compression_nom_pct": round(100 * D.GASKET_COMP), "stack_tol_rss_mm": round(tol, 2),
            "compression_range_pct": [round(100 * max(comp - tol, 0) / D.GASKET_T),
                                      round(100 * (comp + tol) / D.GASKET_T)],
            "pressure_nom_MPa": GASKET_P_NOM, "pressure_max_MPa": GASKET_P_MAX,
            "force_nom_N": round(A * GASKET_P_NOM), "force_max_N": round(A * GASKET_P_MAX),
            "lift_limit_um": round(min(100.0, 0.3 * comp * 1000), 1)}


def weight(D):
    m = {"PCB with SMD parts": 0.120, "panel (LCM + CTP)": 0.200, "heatsink SK 409 63.5 + Q1": 0.060,
         "PSU HLK-10M05": 0.050, "relay, fuses, chokes, caps": 0.060}
    tot = sum(m.values())
    return {"masses_kg": m, "total_kg": round(tot, 3), "static_N": round(tot * G, 1),
            "shock_10g_per_M4_stud_N": round(tot * G * G_SHOCK / len(D.STUDS), 1),
            "shock_10g_per_PCB_screw_N": round((tot - m["panel (LCM + CTP)"]) * G * G_SHOCK / len(D.HOLES), 1)}


def studs(D, g, feat=None):
    T, T_prev = 0.60, 0.20                       # Nm total incl. the nyloc prevailing torque
    F_cons = T / (0.2 * M4_D * 1e-3)
    F_real = (T - T_prev) / (0.2 * M4_D * 1e-3)
    sl = max((s["len"] for s in D.SLOTS.values()), default=D.STUD_HOLE_D)       # stadium slot: extra rectangle
    A_nom = math.pi / 4 * (min(D.STUD_OD, WASHER_OD) ** 2 - D.STUD_HOLE_D ** 2) - (sl - D.STUD_HOLE_D) * D.STUD_HOLE_D
    A_meas = None
    if feat:
        a = [s["washer_bearing_area_mm2"] for s in feat.get("studs", []) if "washer_bearing_area_mm2" in s]
        A_meas = min(a) if a else None
    A = A_meas or A_nom
    n = len(D.STUDS)
    return {"nut": "ISO 10511 (DIN 985) M4 nyloc + DIN 9021 M4 washer on PEM FH-M4-18 stud", "n_studs": n,
            "torque_Nm": T, "preload_cons_N": round(F_cons), "preload_real_N": round(F_real),
            "tube_od_mm": D.STUD_OD, "hole_mm": D.STUD_HOLE_D,
            "bearing_area_nominal_mm2": round(A_nom, 1),
            "bearing_area_measured_mm2": round(A_meas, 1) if A_meas else None,
            "bearing_cons_MPa": round(F_cons / A, 1), "bearing_real_MPa": round(F_real / A, 1),
            "creep_allow_MPa": CREEP_ALLOW, "bearing_ok": F_real / A <= CREEP_ALLOW,
            "gasket_share_per_stud_N": round(g["force_max_N"] / n, 1),
            "clamp_margin": round(F_real / (g["force_max_N"] / n), 1)}


def hole_offset(D, x, y):
    """distance from the hole centre to the body outline OUTER (abs); 0 if inside the body"""
    x0, x1, y0, y1 = D.OUTER
    dx = max(x0 - x, 0, x - x1)
    dy = max(y0 - y, 0, y - y1)
    return math.hypot(dx, dy)


def section(rects):
    A = sum(w * h for w, h, _ in rects)
    zc = sum(w * h * z for w, h, z in rects) / A
    I = sum(w * h ** 3 / 12 + w * h * (z - zc) ** 2 for w, h, z in rects)
    return A, zc, I


def rib_height(frame, D, name, n=9):
    """height of the radial stud rib above the flange back, measured on the STEP: vertical probe lines along the
    line from the hole towards the body outline (the rib's centreline), clear of the tube and wall root fillets;
    -> (median, min, max) or None if there is no room / no rib"""
    import numpy as np
    x, y = D.STUDS[name]
    x0, x1, y0, y1 = D.OUTER
    px, py = min(max(x, x0), x1), min(max(y, y0), y1)
    d = math.hypot(px - x, py - y)
    r0, r1 = D.STUD_OD / 2 + 0.6, d - 0.6                  # 0.6: past the R0.5 root fillets
    if d < 1e-6 or r1 <= r0 or D.Z_FLANGE_BACK is None:
        return None
    ux, uy = (px - x) / d, (py - y) / d
    hs = []
    for t in np.linspace(r0, r1, n):
        sx, sy = x + ux * t, y + uy * t
        e = cq.Edge.makeLine(cq.Vector(sx, -sy, D.Z_FLANGE_BACK - 0.3), cq.Vector(sx, -sy, D.Z_FLANGE_BACK + 30))
        segs = [q.BoundingBox() for q in C.common_shape(frame, e).Edges()]
        top = max((b.zmax for b in segs if b.zmin <= D.Z_FLANGE_BACK + 0.05), default=None)
        hs.append(max(top - D.Z_FLANGE_BACK, 0.0) if top is not None else 0.0)
    return float(np.median(hs)), float(min(hs)), float(max(hs))


def flange(D, g, wt, frame=None):
    n = len(D.STUDS)
    F_gas = g["force_max_N"] / n
    F_shock = wt["total_kg"] * G * G_SHOCK / n
    F = F_gas + F_shock
    t = D.FLANGE_T
    rows = []
    for name, (x, y) in D.STUDS.items():
        rows.append((hole_offset(D, x, y), name))
    lever, worst = max(rows)
    od = D.STUD_OD
    out = {"load_gasket_max_per_stud_N": round(F_gas, 1), "load_shock_10g_per_stud_N": round(F_shock, 1),
           "load_total_N": round(F, 1), "plate_t_mm": t, "worst_hole": worst, "lever_mm": round(lever, 2),
           "stud_offset_param": D.STUD_OFFSET,
           "offsets": {nm: round(o, 2) for o, nm in sorted(rows, key=lambda r: r[1])}}
    cases = {}
    # (a) plate, width = tube OD, lever = offset
    b = od
    M = F * lever
    Ms = F_gas * lever
    cases["a_plate_OD_lever_offset"] = {"b_mm": b, "lever_mm": round(lever, 2), "M_Nmm": round(M, 1),
                                        "sigma_total_MPa": round(6 * M / (b * t * t), 1),
                                        "sigma_sustained_MPa": round(6 * Ms / (b * t * t), 1)}
    # (b) T-section: plate b = OD + radial rib STUD_RIB_T x h_rib on the back face
    if D.STUD_RIB_T > 0 and D.Z_STUD_TOP is not None:
        h = D.Z_STUD_TOP - D.Z_FLANGE_BACK
        A, zc, I = section([(b, t, t / 2), (D.STUD_RIB_T, h, t + h / 2)])
        c_front, c_back = zc, t + h - zc
        cases["b_plate_plus_rib"] = {"b_mm": b, "rib_t_mm": D.STUD_RIB_T, "rib_h_mm": round(h, 2), "I_mm4": round(I, 1),
                                     "sigma_front_total_MPa": round(M * c_front / I, 1),
                                     "sigma_rib_top_total_MPa": round(M * c_back / I, 1),
                                     "sigma_sustained_max_MPa": round(Ms * max(c_front, c_back) / I, 1)}
    # (c) lever from the tube face, 45 deg spread
    lr = max(lever - od / 2, 0.0)
    br = od + 2 * lr
    Mr, Mrs = F * lr, F_gas * lr
    cases["c_realistic_lever_from_tube_face"] = {"b_mm": round(br, 2), "lever_mm": round(lr, 2),
                                                 "sigma_total_MPa": round(6 * Mr / (br * t * t), 1) if lr > 0 else 0.0,
                                                 "sigma_sustained_MPa": round(6 * Mrs / (br * t * t), 1) if lr > 0 else 0.0}
    # (d) T-section with the rib height measured on the STEP: strip STUD_OD x FLANGE_T + rib STUD_RIB_T x h, lever =
    #     stud offset; worst (gasket max + 10 g) and nominal (gasket nominal + 1 g static) per hole
    if frame is not None and D.STUD_RIB_T > 0:
        rh = rib_height(frame, D, worst)
        out["rib_height_measured_mm"] = [round(v, 3) for v in rh] if rh else None
        if rh and rh[0] > 0.1:
            h = rh[0]
            A, zc, I = section([(b, t, t / 2), (D.STUD_RIB_T, h, t + h / 2)])
            c_front, c_back = zc, t + h - zc
            F_nom = g["force_nom_N"] / n + wt["total_kg"] * G / n
            Mw, Mn = F * lever, F_nom * lever
            cases["d_T_section_measured_rib"] = {
                "b_mm": b, "rib_t_mm": D.STUD_RIB_T, "rib_h_mm": round(h, 2), "I_mm4": round(I, 1),
                "zc_from_front_mm": round(zc, 3), "lever_mm": round(lever, 2),
                "F_worst_N": round(F, 1), "F_nominal_N": round(F_nom, 1),
                "sigma_front_total_MPa": round(Mw * c_front / I, 1), "sigma_rib_top_total_MPa": round(Mw * c_back / I, 1),
                "sigma_nominal_max_MPa": round(Mn * max(c_front, c_back) / I, 1),
                "sigma_sustained_max_MPa": round(Mn * max(c_front, c_back) / I, 1),
                "note": "sustained = nominal gasket (0.07 MPa) + 1 g static; total = worst gasket (0.25 MPa) + 10 g"}
    for k, c in cases.items():
        st = c.get("sigma_total_MPa", max(c.get("sigma_front_total_MPa", 0), c.get("sigma_rib_top_total_MPa", 0)))
        ss = c.get("sigma_sustained_MPa", c.get("sigma_sustained_max_MPa", 0))
        c["SF_tensile"] = round(SIG_T_110 / st, 1) if st > 0 else None
        c["sustained_vs_creep_allow"] = round(ss / CREEP_ALLOW, 2)
        c["ok"] = (st == 0) or (st <= SIG_T_110 / 2 and ss <= CREEP_ALLOW)
    out["cases"] = cases
    out["criterion"] = "total (gasket max + 10 g) <= %.1f MPa (SF 2 on %.0f) and sustained (gasket max) <= %.0f MPa" % (
        SIG_T_110 / 2, SIG_T_110, CREEP_ALLOW)
    return out


# ------------------------------------------------------------------------------------------- beam runs
def edges_of(D, x, y):
    """top / bottom / left / right edge(s) a stud supports (common_v2.Design.edges_of)"""
    return D.edges_of(x, y)


def ss_partial_lift(L, segs, q, EI, n=2001):
    """max deflection and moment of a simply supported beam 0..L with uniform load q on the sub-segments segs"""
    import numpy as np
    x = np.linspace(0, L, n)
    w = np.zeros(n)
    for a, b in segs:
        w[(x >= a) & (x <= b)] = q
    dx = np.diff(x)
    cum = lambda f: np.concatenate([[0], np.cumsum((f[1:] + f[:-1]) / 2 * dx)])
    W = cum(w)[-1]
    Ra = cum(w * (L - x))[-1] / L if W > 0 else 0.0
    V = Ra - cum(w)
    M = cum(V)
    v = cum(cum(M / EI))
    v = v - x / L * v[-1]
    return float(np.max(np.abs(v))), float(np.max(np.abs(M)))


def analytic_section(D, side=None):
    sh = D.POCKET_CLR + D.SEAT_W                    # shelf projection inside the wall's inner face
    fw = D.FLANGE_W_SIDE.get(side, D.FLANGE_W) if side else D.FLANGE_W
    rects = [(D.WALL, D.Z_PCB - D.Z_FRONT, (D.Z_PCB + D.Z_FRONT) / 2),
             (sh, D.SHELF_T, (D.Z_SEAT + D.Z_SHELF_BACK) / 2)]
    if fw > 0:
        rects.append((fw, D.FLANGE_T, D.Z_FRONT + D.FLANGE_T / 2))
    A, zc, I = section(rects)
    c = max(abs(D.Z_FRONT - zc), abs(D.Z_PCB - zc))
    return {"rects_w_h_zc": [[round(v, 3) for v in r] for r in rects], "A_mm2": round(A, 2), "zc": round(zc, 3),
            "I_mm4": round(I, 1), "c_mm": round(c, 3), "shelf_w_used": round(sh, 3), "flange_w_used": fw,
            "note": "shelf width = POCKET_CLR + SEAT_W inside the wall (the brief's 5.1 = WALL + SEAT_W would count "
                    "the wall's 2.5 x 2.5 corner twice)"}


def measured_I(D, frame, edge, s):
    """I (mm4) about the horizontal centroidal axis of the real section at position s along `edge`"""
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    x0, x1, y0, y1 = D.OUTER
    band_in = D.WALL + D.POCKET_CLR + D.SEAT_W + 0.5          # wall + shelf to just past the window edge
    out = 30.0                                                # everything outside the wall (flange, tubes)
    best = None
    for sh in SECTION_SHIFTS:
        p = s + sh
        if edge in ("top", "bottom"):
            sec = C.plane_section(frame, "x", p)
            ya, yb = (y0 - out, y0 + band_in) if edge == "top" else (y1 - band_in, y1 + out)
            clip = C.box(p - 1, p + 1, -yb, -ya, -100, 100)
            idx = 2                                               # Iyy: section in a plane x = const
        else:
            sec = C.plane_section(frame, "y", -p)
            xa, xb = (x0 - out, x0 + band_in) if edge == "left" else (x1 - band_in, x1 + out)
            clip = C.box(xa, xb, -p - 1, -p + 1, -100, 100)
            idx = 1                                               # Ixx: section in a plane y = const
        if sec is None:
            continue
        part = C.common_shape(sec, clip)
        if not part.Faces():
            continue
        gp = GProp_GProps()
        BRepGProp.SurfaceProperties_s(part.wrapped, gp)
        I = gp.MatrixOfInertia().Value(idx, idx)
        if best is None or I < best[0]:
            best = (I, gp.Mass(), p)
    return best


def beam(D, g, frame=None):
    sec = analytic_section(D)
    I, c = sec["I_mm4"], sec["c_mm"]
    q_max = g["force_max_N"] / (2 * ((D.PX1 - D.PX0) + (D.PY1 - D.PY0)))      # N/mm along the glass edge
    q_nom = q_max * GASKET_P_NOM / GASKET_P_MAX
    x0, x1, y0, y1 = D.OUTER
    corner = {"top": (x0, x1), "bottom": (x0, x1), "left": (y0, y1), "right": (y0, y1)}
    on = {k: [] for k in corner}
    for n, (x, y) in D.STUDS.items():
        for e in edges_of(D, x, y):
            on[e].append((x if e in ("top", "bottom") else y, n))
    runs = []
    for e, (c0, c1) in corner.items():
        sup = [(c0, "corner")] + sorted((min(max(v, c0), c1), n) for v, n in on[e]) + [(c1, "corner")]
        for (a, na), (b, nb) in zip(sup, sup[1:]):
            L = b - a
            if L < SPAN_MIN:
                continue
            r = {"edge": e, "from": na, "to": nb, "span_mm": round(L, 2)}
            secs = analytic_section(D, e)
            Iuse, c = secs["I_mm4"], secs["c_mm"]
            r["I_analytic_mm4"] = Iuse
            if frame is not None:
                m = measured_I(D, frame, e, (a + b) / 2)
                if m:
                    r["I_measured_mm4"] = round(m[0], 1)
                    r["A_measured_mm2"] = round(m[1], 1)
                    r["section_at"] = round(m[2], 2)
            g0, g1 = (D.PX0, D.PX1) if e in ("top", "bottom") else (D.PY0, D.PY1)     # glass edge alongside
            segs = [(max(g0, a) - a, min(g1, b) - a)] if min(g1, b) > max(g0, a) else []
            r["loaded_mm"] = round(sum(y - x for x, y in segs), 2)
            Ims = r.get("I_measured_mm4")
            for tag, q in (("nom", q_nom), ("max", q_max)):
                M = q * L ** 2 / 8
                vp, Mp = ss_partial_lift(L, segs, q, E_CREEP * Iuse)
                r[tag] = {"bending_MPa": round(M * c / Iuse, 2),
                          "lift_short_um": round(5 * q * L ** 4 / (384 * E_110 * Iuse) * 1000, 1),
                          "lift_1000h_um": round(5 * q * L ** 4 / (384 * E_CREEP * Iuse) * 1000, 1),
                          "lift_1000h_partial_um": round(vp * 1000, 1)}
                if Ims:
                    r[tag]["lift_1000h_measuredI_um"] = round(5 * q * L ** 4 / (384 * E_CREEP * Ims) * 1000, 1)
                    r[tag]["lift_1000h_partial_measuredI_um"] = round(vp * Iuse / Ims * 1000, 1)
            r["verdict_lift_1000h_nom_um"] = max(r["nom"]["lift_1000h_partial_um"],
                                                 r["nom"].get("lift_1000h_partial_measuredI_um", 0))
            runs.append(r)
    # corner overhangs: corner to the nearest hole on each adjacent edge, as a cantilever (info)
    over = []
    for e, (c0, c1) in corner.items():
        vals = sorted(min(max(v, c0), c1) for v, n in on[e])
        for cc, side in ((c0, "start"), (c1, "end")):
            a = min((abs(v - cc) for v in vals), default=c1 - c0)
            over.append({"edge": e, "corner": side, "overhang_mm": round(a, 2),
                         "cantilever_lift_1000h_nom_um": round(q_nom * a ** 4 / (8 * E_CREEP * I) * 1000, 1)})
    # runs walked round the stud line (corner NOT a support), consecutive holes by angle about the body centre
    xc, yc = (x0 + x1) / 2, (y0 + y1) / 2
    ring = sorted(D.STUDS.items(), key=lambda kv: math.atan2(kv[1][1] - yc, kv[1][0] - xc))
    walk = []
    for (na, (xa, ya)), (nb, (xb, yb)) in zip(ring, ring[1:] + ring[:1]):
        L = abs(xb - xa) + abs(yb - ya) if set(edges_of(D, xa, ya)) != set(edges_of(D, xb, yb)) else \
            math.hypot(xb - xa, yb - ya)
        walk.append({"from": na, "to": nb, "path_mm": round(L, 2),
                     "lift_1000h_nom_um": round(5 * q_nom * L ** 4 / (384 * E_CREEP * I) * 1000, 1)})
    worst = max(runs, key=lambda r: r["verdict_lift_1000h_nom_um"]) if runs else None
    lim = g["lift_limit_um"]
    per_edge = {}
    for r in runs:
        if r["edge"] not in per_edge or r["span_mm"] > per_edge[r["edge"]]["span_mm"]:
            per_edge[r["edge"]] = {"from": r["from"], "to": r["to"], "span_mm": r["span_mm"],
                                   "lift_1000h_nom_full_q_um": r["nom"]["lift_1000h_um"],
                                   "verdict_lift_1000h_nom_um": r["verdict_lift_1000h_nom_um"]}
    return {"section": sec, "I_analytic_by_side_mm4": {sd: analytic_section(D, sd)["I_mm4"] for sd in corner},
            "q_nom_N_per_mm": round(q_nom, 4), "q_max_N_per_mm": round(q_max, 4),
            "load_note": "gasket line load q = F / glass perimeter. 'lift_1000h_um' = q over the whole run (upper bound, "
                         "v1 method); 'partial' = q only where the glass edge runs alongside (verdict, with the smaller of "
                         "the analytic and measured I). The bottom edge's load is projected onto the bottom stud line "
                         "(conservative: it reaches it through the tail-pocket / cell walls)",
            "I_v1_reference_mm4": 309, "I_ratio_vs_v1": round(I / 309.0, 2),
            "runs": runs, "longest_run_per_edge": per_edge, "worst_run": worst,
            "lift_limit_1000h_nom_um": lim,
            "worst_lift_1000h_nom_um": worst["verdict_lift_1000h_nom_um"] if worst else None,
            "ok": (worst["verdict_lift_1000h_nom_um"] <= lim) if worst else True,
            "corner_overhangs": over, "walk_round_corners": walk,
            "walk_worst_lift_1000h_nom_um": max((w["lift_1000h_nom_um"] for w in walk), default=None)}


# ------------------------------------------------------------------------------------------- thermal
THERMAL_CASES = {"transverse_both (70/70)": (CLTE_TRANS, CLTE_TRANS), "flow_along_x (30/70)": (CLTE_FLOW, CLTE_TRANS),
                 "flow_along_y (70/30)": (CLTE_TRANS, CLTE_FLOW)}


def thermal_rows(D, ref, shift=(0.0, 0.0)):
    """per stud: movement relative to the sheet from the point `ref` (abs) for the three CLTE cases, plus a rigid
    `shift` of the frame (abs, e.g. its float along the peg line); for a slot split along / across its axis, each
    against its own play"""
    clr = (D.STUD_HOLE_D - M4_D) / 2
    avail = clr - POS_TOL
    rows = []
    for n, (x, y) in D.STUDS.items():
        dx, dy = x - ref[0], y - ref[1]
        r = {"hole": n, "dx_mm": round(dx, 1), "dy_mm": round(dy, 1)}
        vs = {}
        for k, (ax, ay) in THERMAL_CASES.items():
            vs[k] = ((ax - CLTE_STEEL) * DT * dx + shift[0], (ay - CLTE_STEEL) * DT * dy + shift[1])
            r[k] = round(math.hypot(*vs[k]), 3)
        r["worst_mm"] = max(r[k] for k in THERMAL_CASES)
        sl = D.SLOTS.get(n)
        if sl:
            ux, uy = sl["axis"]
            av_al = (sl["len"] - M4_D) / 2 - POS_TOL
            av_ac = (sl["w"] - M4_D) / 2 - POS_TOL
            al = max(abs(vx * ux + vy * uy) for vx, vy in vs.values())
            ac = max(abs(-vx * uy + vy * ux) for vx, vy in vs.values())
            rr = math.hypot(dx, dy)
            r["existing_slot"] = {"len": sl["len"], "axis": [round(ux, 4), round(uy, 4)],
                                  "axis_deg_abs": round(math.degrees(math.atan2(uy, ux)), 2),
                                  "radial_misalignment_deg": round(math.degrees(math.acos(min(1.0, abs(ux * dx + uy * dy)
                                                                                          / rr))), 2) if rr > 1e-6 else None,
                                  "along_mm": round(al, 3), "across_mm": round(ac, 3),
                                  "avail_along": round(av_al, 3), "avail_across": round(av_ac, 3)}
            r["slot"] = al > av_al or ac > av_ac
        else:
            r["slot"] = r["worst_mm"] > avail
        r["slot_length_mm"] = round(D.STUD_HOLE_D + 2 * max(r["worst_mm"] - avail, 0), 2) if r["slot"] else None
        r["slot_direction_deg_abs"] = round(math.degrees(math.atan2(dy, dx)), 1) if r["slot"] else None
        rows.append(r)
    return rows, avail


def thermal(D):
    """frame vs steel sheet from the point where the frame is actually held (round peg if the other peg is a slot);
    with a declared DATUM elsewhere the same table from the datum is reported too (radial slots assume it)"""
    ref_name, ref = D.thermal_fixed_point()
    rows, avail = thermal_rows(D, ref)
    xs = [p[0] for p in D.STUDS.values()]
    ys = [p[1] for p in D.STUDS.values()]
    res = {"dT_K": DT, "clte_frame_flow_transverse_steel_ppmK": [CLTE_FLOW * 1e6, CLTE_TRANS * 1e6, CLTE_STEEL * 1e6],
           "reference": ref_name, "reference_abs": [round(ref[0], 2), round(ref[1], 2)],
           "pattern_extent_mm": [round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)],
           "clearance_per_side_mm": (D.STUD_HOLE_D - M4_D) / 2, "position_tol_rss_mm": round(POS_TOL, 3),
           "available_mm": round(avail, 3), "holes": rows,
           "holes_to_slot": [r["hole"] for r in rows if r["slot"]],
           "restrained_stress_MPa": {"short": round(E_110 * (CLTE_TRANS - CLTE_STEEL) * DT, 1),
                                     "1000h": round(E_CREEP * (CLTE_TRANS - CLTE_STEEL) * DT, 1)}}
    ps_all = D.PEG_SLOTS
    if len(D.PEGS) == 2 and all(ps_all.get(n) for n in D.PEGS):
        # both pegs slotted along their line: the frame floats along it, located only by the studs' across-slot
        # clearance -> worst case = rigid offset of +-that clearance along the peg line on top of the growth (the
        # expansion-centre shift itself is negligible: dalpha x dT x 0.25 < 0.001 mm)
        u = next(iter(ps_all.values()))["axis"]
        off = min(((s["w"] - M4_D) / 2 for s in D.SLOTS.values()), default=(D.STUD_HOLE_D - M4_D) / 2)
        worst = {}
        for sg in (1, -1):
            orow, _ = thermal_rows(D, ref, (sg * off * u[0], sg * off * u[1]))
            for r in orow:
                w = worst.get(r["hole"])
                key = r.get("existing_slot", {})
                cand = (key.get("across_mm", r["worst_mm"]), key.get("along_mm", 0.0), r["slot"])
                if w is None or cand[0] > w[0]:
                    worst[r["hole"]] = cand
        res["x_float_offset_case"] = {
            "offset_mm": off, "axis": u,
            "holes": {n: {"across_mm": round(v[0], 3), "along_mm": round(v[1], 3), "not_covered": v[2]}
                      for n, v in worst.items()},
            "holes_not_covered": [n for n, v in worst.items() if v[2]],
            "note": "frame offset by +-%.2f along the peg line (studs' across-slot clearance) + thermal growth" % off}
    if D.DATUM is not None and math.hypot(D.DATUM[0] - ref[0], D.DATUM[1] - ref[1]) > 0.5:
        drows, _ = thermal_rows(D, D.DATUM)
        res["from_declared_datum"] = {
            "datum_abs": [round(D.DATUM[0], 2), round(D.DATUM[1], 2)], "holes": drows,
            "holes_to_slot": [r["hole"] for r in drows if r["slot"]],
            "note": "the slots point radially from the declared datum, but the frame is held at the %s (%.2f, %.2f): "
                    "the frame grows from there, so the verdict uses the fixed point" % (ref_name, ref[0], ref[1])}
    if len(D.PEGS) == 2:
        (n1, p1), (n2, p2) = sorted(D.PEGS.items())
        Lp = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        ex, ey = (p2[0] - p1[0]) / Lp, (p2[1] - p1[1]) / Lp
        grow = {k: round(math.hypot((ax - CLTE_STEEL) * DT * Lp * ex, (ay - CLTE_STEEL) * DT * Lp * ey), 3)
                for k, (ax, ay) in THERMAL_CASES.items()}
        ps = D.PEG_SLOTS
        hole = D.PEG_D + PEG_HOLE_CLR
        slotted = [n for n, v in ps.items() if v]
        both = len(slotted) == 2
        if slotted:
            sl = ps[slotted[0]]
            play = (sl["len"] - D.PEG_D) / 2 - POS_TOL       # centred at assembly, either way
            what = ("slots %s %.2f x %.2f" % ("+".join(sorted(slotted)), hole, sl["len"]) if both else
                    "round %s + slot %s %.2f x %.2f" % ([n for n in ps if n not in slotted][0], slotted[0], hole,
                                                         sl["len"]))
        else:
            play = PEG_HOLE_CLR                             # two round holes: both radial clearances together
            what = "two round holes dia %.2f" % hole
        gmax = max(grow.values())
        per_peg = gmax / 2 if both else gmax                 # both slotted: each peg takes half (self-centred)
        res["pegs"] = {"spacing_mm": round(Lp, 2), "growth_by_case_mm": grow, "growth_mm": gmax,
                       "sheet_holes": what, "play_mm": round(play, 3), "clearance_total_mm": round(play, 3),
                       "movement_per_peg_mm": round(per_peg, 3),
                       "one_peg_hole_must_be_slot": (not slotted) and gmax > play,
                       "ok": per_peg <= play,
                       "slot_length_needed_mm": round(D.PEG_D + 2 * (per_peg + POS_TOL), 2)}
        if both and "x_float_offset_case" in res:
            off = res["x_float_offset_case"]["offset_mm"]
            res["pegs"]["with_x_float_mm"] = round(per_peg + off, 3)
            res["pegs"]["ok_with_x_float"] = per_peg + off <= (sl["len"] - D.PEG_D) / 2
    return res


def table_md(r):
    L = ["# Carrier frame %s - hand calculations" % r["tag"], ""]
    b, s, f, bm, th, w, g = r["boss"], r["studs"], r["flange"], r["beam"], r["thermal"], r["weight"], r["gasket"]
    L += ["| check | value | limit | ok |", "|---|---|---|---|",
          "| PCB boss bearing (cons / real) | %.1f / %.1f MPa | %.0f | %s |" % (b["bearing_cons_MPa"], b["bearing_real_MPa"],
                                                                         CREEP_ALLOW, b["bearing_real_MPa"] <= CREEP_ALLOW),
          "| PCB boss thread shear SF | %.2f | > 2 | %s |" % (b["thread_shear_SF"], b["thread_shear_SF"] > 2),
          "| PCB boss hoop SF short / long | %.1f / %.1f | > 2 | %s |" % (b["hoop_SF_short"], b["hoop_SF_longterm(0.4x)"],
                                                                        b["hoop_SF_longterm(0.4x)"] > 2),
          "| gasket force nom / max | %d / %d N | - | - |" % (g["force_nom_N"], g["force_max_N"]),
          "| stud tube bearing (cons / real), area %.1f mm2 | %.1f / %.1f MPa | %.0f | %s |" % (
              s["bearing_area_measured_mm2"] or s["bearing_area_nominal_mm2"], s["bearing_cons_MPa"],
              s["bearing_real_MPa"], CREEP_ALLOW, s["bearing_ok"]),
          "| stud clamp margin over the gasket share | %.1f x | > 2 | %s |" % (s["clamp_margin"], s["clamp_margin"] > 2)]
    for k, c in f["cases"].items():
        st = c.get("sigma_total_MPa", max(c.get("sigma_front_total_MPa", 0), c.get("sigma_rib_top_total_MPa", 0)))
        ss = c.get("sigma_sustained_MPa", c.get("sigma_sustained_max_MPa", 0))
        L.append("| flange %s (hole %s, F %.0f N) | total %.1f / sustained %.1f MPa | %.1f / %.0f | %s |" % (
            k, f["worst_hole"], f["load_total_N"], st, ss, SIG_T_110 / 2, CREEP_ALLOW, c["ok"]))
    sec = bm["section"]
    L.append("| beam section I (analytic) | %.0f mm4 (v1 309, x%.2f) | - | - |" % (sec["I_mm4"], bm["I_ratio_vs_v1"]))
    if bm["worst_run"]:
        wr = bm["worst_run"]
        for e, pe in bm["longest_run_per_edge"].items():
            L.append("| longest %s run %s-%s, span %.1f | lift 1000 h nom %.1f um (full-q bound %.1f) | %.0f um | %s |" % (
                e, pe["from"], pe["to"], pe["span_mm"], pe["verdict_lift_1000h_nom_um"], pe["lift_1000h_nom_full_q_um"],
                bm["lift_limit_1000h_nom_um"], pe["verdict_lift_1000h_nom_um"] <= bm["lift_limit_1000h_nom_um"]))
    L.append("| thermal (from the %s): worst stud displacement | %.3f mm (avail. %.3f round) | - | not covered: %s |" % (
        th["reference"], max(h["worst_mm"] for h in th["holes"]), th["available_mm"],
        ", ".join(th["holes_to_slot"]) or "none"))
    if "from_declared_datum" in th:
        L.append("| thermal (from the declared datum %s) | - | - | not covered: %s |" % (
            th["from_declared_datum"]["datum_abs"], ", ".join(th["from_declared_datum"]["holes_to_slot"]) or "none"))
    if "pegs" in th:
        L.append("| thermal: peg-to-peg growth (%s) | %.3f mm, %.3f per peg (play %.3f) | - | %s |" % (
            th["pegs"]["sheet_holes"], th["pegs"]["growth_mm"], th["pegs"]["movement_per_peg_mm"],
            th["pegs"]["play_mm"], th["pegs"]["ok"]))
    if "x_float_offset_case" in th:
        xo = th["x_float_offset_case"]
        L.append("| thermal + frame x-float +-%.2f along the peg line | - | - | not covered: %s |" % (
            xo["offset_mm"], ", ".join(xo["holes_not_covered"]) or "none"))
    L.append("| 10 g shock per stud / PCB screw | %.1f / %.1f N | - | - |" % (w["shock_10g_per_M4_stud_N"],
                                                                         w["shock_10g_per_PCB_screw_N"]))
    L += ["", "## Runs (corners count as supports; uniform q)", "",
          "| edge | from | to | span | loaded | I meas. | lift nom 1000 h full q | partial (verdict) | lift max 1000 h full q | bending max |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for rr in bm["runs"]:
        L.append("| %s | %s | %s | %.1f | %.1f | %s | %.1f | %.1f | %.1f | %.2f |" % (
            rr["edge"], rr["from"], rr["to"], rr["span_mm"], rr["loaded_mm"], rr.get("I_measured_mm4", "-"),
            rr["nom"]["lift_1000h_um"], rr["verdict_lift_1000h_nom_um"], rr["max"]["lift_1000h_um"],
            rr["max"]["bending_MPa"]))
    L += ["", "## Thermal (dT %.0f K, from the %s)" % (th["dT_K"], th["reference"]), "",
          "| hole | dx | dy | 70/70 | 30/70 | 70/30 | slot |", "|---|---|---|---|---|---|---|"]
    for h in th["holes"]:
        L.append("| %s | %.1f | %.1f | %.3f | %.3f | %.3f | %s |" % (
            h["hole"], h["dx_mm"], h["dy_mm"], h["transverse_both (70/70)"], h["flow_along_x (30/70)"],
            h["flow_along_y (70/30)"], h["slot_length_mm"] or "-"))
    return "\n".join(L) + "\n"


def run(ctx, feat=None, log=C.log):
    D = ctx.D
    g = gasket(D)
    w = weight(D)
    log("[calc] boss, studs, flange, beam (measured sections on the STEP), thermal")
    res = {"tag": ctx.tag, "material": {"tensile_110C_MPa": SIG_T_110, "creep_allow_MPa": CREEP_ALLOW,
                                        "E_short_MPa": E_110, "E_1000h_MPa": E_CREEP},
           "boss": boss(D), "gasket": g, "studs": studs(D, g, feat), "flange": flange(D, g, w, ctx.frame),
           "beam": beam(D, g, ctx.frame), "thermal": thermal(D), "weight": w}
    C.dump(res, ctx.out("calc.json"))
    md = table_md(res)
    open(ctx.out("calc.md"), "w", encoding="utf8").write(md)
    log(md.split("\n## Runs")[0])
    return res


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    feat = None
    p = ctx.out("cadcheck.json")
    if os.path.exists(p):
        feat = json.load(open(p)).get("features")
    run(ctx, feat)
