"""Hand calculations for the Rev3.0 carrier frame (screw bosses, feet, shelf, frame beam, gasket).

Material values: PA6-GF30 heat-stabilised at 110 C (owner's enclosure memory, Battery Sentinel):
tensile 75-85 MPa, long-term compressive creep allowance 15-20 MPa, HDT ~200 C. The flame-retardant
(V-0, GWFI 960) grades are ~15 % weaker than the standard grade; the low end of each range is used.
Writes out/calc.json; build.py copies the table into the design document.
"""
import json
import math
import os

import frame as F

HERE = os.path.dirname(os.path.abspath(__file__))

SIG_T_110 = 75.0          # MPa tensile at 110 C (low end)
TAU_110 = 0.6 * SIG_T_110 # MPa shear
CREEP_ALLOW = 15.0        # MPa long-term compressive (low end of 15-20)
E_110 = 3500.0            # MPa, PA6-GF30 conditioned at 110 C (short term)
E_CREEP = 0.5 * E_110     # MPa, 1000 h creep modulus estimate
G = 9.81


def boss():
    d, dp, D = F.SCREW_D, F.PILOT_D, F.BOSS_OD
    L_screw = 9.5
    tip = 1.5                                   # C-point taper, not load bearing
    Le = L_screw - F.PCB_T - tip                # engaged length
    T = 0.40                                    # Nm installation (seating) torque, max
    T_drive = 0.20                              # Nm drive (thread-forming) torque, typical; verify on first articles
    K = 0.20                                    # torque coefficient
    F_cons = T / (K * d * 1e-3)                 # all torque into preload (conservative)
    F_real = (T - T_drive) / (K * d * 1e-3)
    A_bear = math.pi / 4 * (D ** 2 - F.CBORE_D ** 2)
    A_shear = math.pi * d * Le * 0.6            # 0.6 = formed-thread fill factor
    p = F_cons * math.tan(math.radians(30)) / (math.pi * d * Le)
    lame = (D ** 2 + d ** 2) / (D ** 2 - d ** 2)
    hoop = p * lame
    return {
        "screw": "ISO 7049-C / DIN 7981 ST2.9x9.5 A2 (alt. PT K30x10)", "pilot_mm": dp, "boss_od_mm": D,
        "od_over_d": D / d, "engaged_mm": round(Le, 2), "torque_install_Nm": T, "torque_drive_Nm": T_drive,
        "preload_cons_N": round(F_cons), "preload_real_N": round(F_real),
        "bearing_area_mm2": round(A_bear, 1), "bearing_cons_MPa": round(F_cons / A_bear, 1),
        "bearing_real_MPa": round(F_real / A_bear, 1), "creep_allow_MPa": CREEP_ALLOW,
        "thread_shear_cons_MPa": round(F_cons / A_shear, 1), "thread_shear_SF": round(TAU_110 / (F_cons / A_shear), 2),
        "hoop_cons_MPa": round(hoop, 1), "hoop_SF_short": round(SIG_T_110 / hoop, 1),
        "hoop_SF_longterm(0.4x)": round(0.4 * SIG_T_110 / hoop, 1)}


def feet(gasket_force_max):
    T, T_prev, d = 0.60, 0.20, 4.0                 # Nm total incl. the nyloc prevailing torque
    F_cons = T / (0.2 * d * 1e-3)
    F_real = (T - T_prev) / (0.2 * d * 1e-3)
    A = math.pi / 4 * (F.FOOT_OD ** 2 - F.FOOT_HOLE ** 2)   # DIN 9021 washer (OD 12) on the tube top
    n = len(F.FEET)
    return {"nut": "ISO 10511 (DIN 985) M4 nyloc + DIN 9021 M4 washer on FH-M4-15 stud", "torque_Nm": T,
            "preload_cons_N": round(F_cons), "preload_real_N": round(F_real),
            "bearing_area_mm2": round(A, 1), "bearing_cons_MPa": round(F_cons / A, 1),
            "bearing_real_MPa": round(F_real / A, 1),
            "gasket_share_per_foot_N": round(gasket_force_max / n, 1),
            "clamp_margin": round(F_real / (gasket_force_max / n), 1)}


def gasket():
    o = (F.PX1 - F.PX0 - 2 * F.GASKET_OUT_INSET) * (F.PY1 - F.PY0 - 2 * F.GASKET_OUT_INSET)
    i = (F.VA[1] - F.VA[0] + 2 * F.GASKET_IN_MARGIN) * (F.VA[3] - F.VA[2] + 2 * F.GASKET_IN_MARGIN)
    A = o - i
    comp = F.GASKET_T * F.GASKET_COMP
    tol = math.sqrt(F.PANEL_T_TOL ** 2 + 0.10 ** 2 + 0.10 ** 2 + 0.05 ** 2)   # LCM, CTP stack, frame seat, sheet
    return {"area_mm2": round(A), "thickness_mm": F.GASKET_T, "compression_nom_mm": round(comp, 2),
            "compression_nom_pct": round(100 * F.GASKET_COMP), "stack_tol_rss_mm": round(tol, 2),
            "compression_range_pct": [round(100 * max(comp - tol, 0) / F.GASKET_T), round(100 * (comp + tol) / F.GASKET_T)],
            "pressure_nom_MPa": 0.07, "pressure_max_MPa": 0.25,
            "force_nom_N": round(A * 0.07), "force_max_N": round(A * 0.25)}


def shelf(gasket_force_max):
    per = 2 * ((F.PX1 - F.PX0) + (F.PY1 - F.PY0))
    q = gasket_force_max / per                     # N/mm along the panel border
    arm = F.POCKET_CLR + (F.SEAT_W - F.SHEET_INSET) / 2 + F.SHEET_INSET   # wall face -> load centroid
    t = F.SHELF_T
    sig = 6 * q * arm / t ** 2
    I = t ** 3 / 12
    defl = q * arm ** 3 / (3 * E_CREEP * I)
    A_bear = (F.SEAT_W - F.SHEET_INSET) * per
    return {"line_load_N_per_mm": round(q, 2), "lever_mm": round(arm, 2), "bending_MPa": round(sig, 2),
            "deflection_um": round(defl * 1000, 2), "seat_pressure_MPa": round(gasket_force_max / A_bear, 3)}


def frame_beam(gasket_force_max):
    """Top long side between two adjacent top feet, as a simply supported beam carrying its share of the
    gasket force (the gasket pushes the panel and thus the frame away from the sheet; the feet hold it).
    Section: outer wall (feet plane -> PCB plane) + shelf. Support ribs and the PCB are ignored (stiffer)."""
    rects = [  # (width along y, height along z, z centroid)
        (F.WALL, F.Z_PCB - F.Z_FRONT, (F.Z_PCB + F.Z_FRONT) / 2),
        (F.SEAT_W + F.POCKET_CLR, F.SHELF_T, (F.Z_SEAT + F.Z_SHELF_BACK) / 2)]
    A = sum(w * h for w, h, _ in rects)
    zc = sum(w * h * z for w, h, z in rects) / A
    I = sum(w * h ** 3 / 12 + w * h * (z - zc) ** 2 for w, h, z in rects)
    xs = sorted(x for x, y in F.FEET.values() if y < F.PY0)
    span = max(b - a for a, b in zip(xs, xs[1:]))
    share = (F.PX1 - F.PX0) / (2 * ((F.PX1 - F.PX0) + (F.PY1 - F.PY0)))
    out = {"section_A_mm2": round(A, 1), "I_mm4": round(I), "span_mm": round(span, 1)}
    for tag, Fg in (("nom", gasket_force_max * 0.07 / 0.25), ("max", gasket_force_max)):
        q = Fg * share / (F.PX1 - F.PX0)
        M = q * span ** 2 / 8
        c = max(abs(F.Z_FRONT - zc), abs(F.Z_PCB - zc))
        out[tag] = {"q_N_per_mm": round(q, 3), "bending_MPa": round(M * c / I, 2),
                    "lift_short_um": round(5 * q * span ** 4 / (384 * E_110 * I) * 1000, 1),
                    "lift_1000h_um": round(5 * q * span ** 4 / (384 * E_CREEP * I) * 1000, 1)}
    return out


def weight():
    m = {"PCB with SMD parts": 0.120, "panel (LCM + CTP)": 0.200, "heatsink SK 409 63.5 + Q1": 0.060,
         "PSU HLK-10M05": 0.050, "relay, fuses, chokes, caps": 0.060}
    tot = sum(m.values())
    g_shock = 10.0
    return {"masses_kg": m, "total_kg": round(tot, 3), "static_N": round(tot * G, 1),
            "shock_10g_per_M4_stud_N": round(tot * G * g_shock / len(F.FEET), 1),
            "shock_10g_per_PCB_screw_N": round((tot - 0.2) * G * g_shock / len(F.HOLES), 1)}


def run():
    g = gasket()
    res = {"boss": boss(), "gasket": g, "feet": feet(g["force_max_N"]), "shelf": shelf(g["force_max_N"]),
           "frame_beam": frame_beam(g["force_max_N"]), "weight": weight()}
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    json.dump(res, open(os.path.join(HERE, "out", "calc.json"), "w"), indent=1)
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
