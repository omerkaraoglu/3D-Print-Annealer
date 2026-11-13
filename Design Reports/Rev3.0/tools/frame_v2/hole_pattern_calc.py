"""Rev3.0 carrier frame v2 - stud-hole pattern rules + gasket-lift hand calculation.

Run:  python hole_pattern_calc.py [--json out.json]
Reads the board outline from v1_geometry.json (path below, or env FRAME_V1_GEOM).

All plan coordinates are KiCad absolute (x, y-down), as in pcbnew.

Rules checked per hole (brief section 3):
  * >= 15 mm from the nearest flange corner, measured along the edge from the start of the corner arc
  * v2.1 (coordinator 2026-11-13): >= 6.5 mm from every point of the PCB outline (ears included) and
    >= 11.0 mm from each ear-hole centre H1..H9 (dia 12 socket beside the board); v2.0 used 11.0 / 15.5
  * clear of the tail-loop plan envelopes + 1.5 mm
  * top edge: adjacent holes <= 60 mm apart
Lift calc: each run between adjacent holes (walking round the stud line, corners unfolded) is a simply
supported beam with the section wall (2.5 x 11.02) + flange (14 x 2.5) + shelf (b_shelf x 2.5), I about
its own horizontal centroidal axis. Load = gasket line load q = F / (2 x (164.9 + 100)) applied where the
glass edge runs alongside the run (exact partial load, numerical double integration) and, as a second
model, the run's gasket share spread uniformly (q x loaded length / run length). The bottom glass edge is
projected onto the bottom stud line (conservative: in reality it is carried by the ribs into the PCB).
Criterion (owner): 1000 h lift at NOMINAL gasket force <= 100 um and <= 0.3 x gasket compression (90 um).
Decision basis: the EXACT partial-load result. For straight runs (both holes on one side) it equals the
brief's uniform model; for corner runs (unfolded L) the uniform smearing moves the load from the ends of the
run (where the glass edge actually is, next to the supports) to mid-span and overstates the lift 1.6-1.9x;
it is reported as an upper bound only.
Pattern search v2.0 (socket rule 11 / 15.5): 8 holes best 219 um. v2.1 (socket rule 6.5 / 11.0): 8 holes best
178 um exact (T2 R2 L2 B2), so 10 holes; the symmetric 10-hole pattern passes BOTH models (71.6 um).
"""
import json
import math
import os
import sys

import numpy as np

GEOM = os.environ.get("FRAME_V1_GEOM", r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142"
                      r"\62ff0a1a-4475-4c41-9c45-d7dae40b64a5\scratchpad\cad\v1_geometry.json")

# ---------------------------------------------------------------- parameters (mirror the Fusion user parameters)
WALL, FLANGE_T, SHELF_T = 2.5, 2.5, 2.5
FLANGE_W = 14.0            # flange width (top, right, bottom)
FLANGE_W_L = 14.0          # v2.1: symmetric again (coordinator: socket rule is 6.5 / 11.0)
FLANGE_R = 12.0
STUD_OFFSET = 7.5          # hole centre from the wall outer face at Z_FRONT (top, right, bottom)
STUD_OFFSET_L = 7.5        # v2.1: symmetric (left board edge x 20.0 -> 10.23 >= 6.5)
OUTER = (17.27, 187.67, 16.25, 153.70)      # body outline at Z_FRONT, x0 x1 y0 y1 (abs, y down)
PANEL = (20.02, 184.92, 19.00, 119.00)
Z_FRONT, Z_PCB, Z_SEAT, Z_SHELF_BACK = -11.02, 0.0, -4.6, -2.1
SHELF_W_REAL = 2.6 + 0.25  # seat_w + pocket_clr (as v1 calc.py; v1 I = 309 mm4 without flange)
SHELF_W_BRIEF = 5.1        # value quoted in the brief
HOLES_PCB = {"H1": (30.0, 14.2), "H2": (93.0, 14.2), "H3": (174.0, 14.2), "H4": (189.8, 30.0),
             "H5": (189.8, 109.0), "H6": (175.0, 123.8), "H7": (30.0, 123.8), "H8": (15.2, 109.0),
             "H9": (15.2, 30.0)}
LOOPS = {"CTP": (40.7, 75.8, 137.4), "TFT": (84.0, 165.9, 146.2)}   # x0, x1, y_max (abs)
LOOP_Y0 = 119.0
LOOP_CLR = 1.5
F_NOM, F_MAX = 165.0, 591.0
E_SHORT, E_1000H = 3500.0, 1750.0
GASKET_COMP_MM = 0.30
LIFT_MAX_UM = min(100.0, 0.3 * GASKET_COMP_MM * 1000)     # 90 um
OUTLINE_MIN, EAR_MIN = 6.5, 11.0   # v2.1 socket rule (keys keep their v2.0 names ok_outline_11 / ok_ear_15_5)

XL = OUTER[0] - STUD_OFFSET_L
XR = OUTER[1] + STUD_OFFSET
YT = OUTER[2] - STUD_OFFSET
YB = OUTER[3] + STUD_OFFSET
FL = (OUTER[0] - FLANGE_W_L, OUTER[1] + FLANGE_W, OUTER[2] - FLANGE_W, OUTER[3] + FLANGE_W)

# ---------------------------------------------------------------- chosen pattern (name: (x, y) abs)
PATTERN = {   # v2.1 final (coordinator 2026-11-13): FH1/FH2 and the side holes shifted so the dia-12 socket keeps
    # >= 1.5 mm from the PCB screw bosses that stand outside the wall; FH1..FH10 clockwise (component side view)
    "FH1": (43.5, YT), "FH2": (103.5, YT), "FH3": (162.0, YT),
    "FH4": (XR, 40.5), "FH5": (XR, 98.5),
    "FH6": (171.0, YB), "FH7": (102.5, YB), "FH8": (34.0, YB),
    "FH9": (XL, 98.5), "FH10": (XL, 40.5),
}


def section_I(shelf_w, flange_w=FLANGE_W):
    rects = [(WALL, Z_PCB - Z_FRONT, (Z_PCB + Z_FRONT) / 2),
             (flange_w, FLANGE_T, Z_FRONT + FLANGE_T / 2),
             (shelf_w, SHELF_T, (Z_SEAT + Z_SHELF_BACK) / 2)]
    A = sum(w * h for w, h, _ in rects)
    zc = sum(w * h * z for w, h, z in rects) / A
    I = sum(w * h ** 3 / 12 + w * h * (z - zc) ** 2 for w, h, z in rects)
    return A, zc, I


def loop_s(x, y):
    """position along the stud line loop (start top-left corner, clockwise in the y-down plan)"""
    Lt, Ls = XR - XL, YB - YT
    if abs(y - YT) < 1e-6:
        return x - XL
    if abs(x - XR) < 1e-6:
        return Lt + (y - YT)
    if abs(y - YB) < 1e-6:
        return Lt + Ls + (XR - x)
    if abs(x - XL) < 1e-6:
        return 2 * Lt + Ls + (YB - y)
    raise ValueError("hole not on the stud line: %r" % ((x, y),))


def loaded_ranges(include_bottom=True):
    Lt, Ls = XR - XL, YB - YT
    r = [(PANEL[0] - XL, PANEL[1] - XL),                                  # top edge
         (Lt + PANEL[2] - YT, Lt + PANEL[3] - YT),                        # right edge
         (2 * Lt + Ls + YB - PANEL[3], 2 * Lt + Ls + YB - PANEL[2])]      # left edge
    if include_bottom:
        r.append((Lt + Ls + XR - PANEL[1], Lt + Ls + XR - PANEL[0]))
    return r


def ss_partial_lift(L, segs, q, EI, n=2001):
    """max deflection of a simply supported beam (0..L) with uniform load q on the sub-segments segs"""
    x = np.linspace(0, L, n)
    w = np.zeros(n)
    for a, b in segs:
        w[(x >= a) & (x <= b)] = q
    W = np.trapezoid(w, x)
    Ra = np.trapezoid(w * (L - x), x) / L if W > 0 else 0.0
    V = Ra - np.concatenate([[0], np.cumsum((w[1:] + w[:-1]) / 2 * np.diff(x))])
    M = np.concatenate([[0], np.cumsum((V[1:] + V[:-1]) / 2 * np.diff(x))])
    k = M / EI
    th = np.concatenate([[0], np.cumsum((k[1:] + k[:-1]) / 2 * np.diff(x))])
    v = np.concatenate([[0], np.cumsum((th[1:] + th[:-1]) / 2 * np.diff(x))])
    v = v - x / L * v[-1]                       # enforce v(L) = 0
    return float(np.max(np.abs(v))), float(np.max(np.abs(M)))


def runs(pattern, I, include_bottom=True):
    Lt, Ls = XR - XL, YB - YT
    per = 2 * (Lt + Ls)
    items = sorted(((loop_s(*p), n) for n, p in pattern.items()))
    lr = loaded_ranges(include_bottom)
    q_nom = F_NOM / (2 * ((PANEL[1] - PANEL[0]) + (PANEL[3] - PANEL[2])))
    q_max = F_MAX / (2 * ((PANEL[1] - PANEL[0]) + (PANEL[3] - PANEL[2])))
    _, zc, _ = section_I(SHELF_W_REAL)
    c = max(abs(Z_FRONT - zc), abs(Z_PCB - zc))
    out = []
    for i, (s0, n0) in enumerate(items):
        s1, n1 = items[(i + 1) % len(items)]
        if s1 <= s0:
            s1 += per
        L = s1 - s0
        segs = []
        for a, b in lr:
            for off in (0.0, per):
                aa, bb = max(a + off, s0), min(b + off, s1)
                if bb > aa:
                    segs.append((aa - s0, bb - s0))
        loaded = sum(b - a for a, b in segs)
        corner = any(abs(s - k) < 1e-6 or s0 < k < s1 for k in (Lt, Lt + Ls, 2 * Lt + Ls, per, per + Lt)
                     for s in ())
        crosses = [k for k in (0.0, Lt, Lt + Ls, 2 * Lt + Ls, per, per + Lt) if s0 < k < s1]
        row = {"from": n0, "to": n1, "span_mm": round(L, 2), "loaded_mm": round(loaded, 2),
               "turns_corner": bool(crosses)}
        for tag, q in (("nom", q_nom), ("max", q_max)):
            for et, E in (("short", E_SHORT), ("1000h", E_1000H)):
                v, M = ss_partial_lift(L, segs, q, E * I)
                row["lift_%s_%s_um" % (tag, et)] = round(v * 1000, 1)
                qeff = q * loaded / L
                row["lift_%s_%s_uniform_um" % (tag, et)] = round(5 * qeff * L ** 4 / (384 * E * I) * 1000, 1)
            row["bending_%s_MPa" % tag] = round(M * c / I, 2)
        out.append(row)
    return out, q_nom, q_max


def outline_points():
    d = json.load(open(GEOM))
    pts = [p for poly in d["outline_polys"] for p in poly]
    # densify: the polygon has long straight edges
    dens = []
    for poly in d["outline_polys"]:
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            k = max(1, int(L / 0.05))
            for j in range(k):
                t = j / k
                dens.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return dens


def corner_distance(x, y):
    """distance along the edge from the hole to the start of the nearest flange corner arc"""
    x0, x1, y0, y1 = FL
    r = FLANGE_R
    if abs(y - YT) < 1e-6 or abs(y - YB) < 1e-6:
        return min(x - (x0 + r), (x1 - r) - x)
    return min(y - (y0 + r), (y1 - r) - y)


def check(pattern):
    pts = np.array(outline_points())
    rows = []
    for n, (x, y) in pattern.items():
        d_out = float(np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y)))
        ears = sorted((math.hypot(x - hx, y - hy), h) for h, (hx, hy) in HOLES_PCB.items())
        loop_d = []
        for ln, (lx0, lx1, ly1) in LOOPS.items():
            dx = max(lx0 - x, 0, x - lx1)
            dy = max(LOOP_Y0 - y, 0, y - ly1)
            loop_d.append(math.hypot(dx, dy))
        rows.append({"name": n, "x": round(x, 3), "y": round(y, 3), "Y_model": round(-y, 3),
                     "d_pcb_outline_mm": round(d_out, 2), "nearest_ear": ears[0][1],
                     "d_nearest_ear_centre_mm": round(ears[0][0], 2),
                     "d_corner_arc_start_mm": round(corner_distance(x, y), 2),
                     "d_tail_loop_env_mm": round(min(loop_d), 2),
                     "ok_outline_11": d_out >= OUTLINE_MIN - 1e-9, "ok_ear_15_5": ears[0][0] >= EAR_MIN - 1e-9,
                     "ok_corner_15": corner_distance(x, y) >= 15.0 - 1e-9,
                     "ok_loops_1_5": min(loop_d) >= LOOP_CLR})
    top = sorted(x for x, y in pattern.values() if abs(y - YT) < 1e-6)
    top_spans = [round(b - a, 2) for a, b in zip(top, top[1:])]
    return rows, top_spans


def main():
    A, zc, I = section_I(SHELF_W_REAL)
    A2, zc2, I2 = section_I(SHELF_W_BRIEF)
    A0, zc0, I0 = section_I(SHELF_W_REAL, flange_w=0.0)
    rows, top_spans = check(PATTERN)
    rr, q_nom, q_max = runs(PATTERN, I)
    rr_nb, _, _ = runs(PATTERN, I, include_bottom=False)
    worst = max(r["lift_nom_1000h_um"] for r in rr)                     # decision basis (exact partial load)
    worst_unif = max(r["lift_nom_1000h_uniform_um"] for r in rr)        # upper bound (smeared share)
    worst_straight_unif = max(r["lift_nom_1000h_uniform_um"] for r in rr if not r["turns_corner"])
    res = {
        "stud_lines_abs": {"left_x": XL, "right_x": XR, "top_y": YT, "bottom_y": YB},
        "flange_outline_abs": FL,
        "section": {"I_mm4_shelf_2.85": round(I, 1), "zc_mm": round(zc, 3), "A_mm2": round(A, 2),
                    "I_mm4_shelf_5.1_brief": round(I2, 1), "I_mm4_without_flange_v1": round(I0, 1)},
        "q_nom_N_per_mm": round(q_nom, 4), "q_max_N_per_mm": round(q_max, 4),
        "criterion_lift_1000h_nom_um": LIFT_MAX_UM,
        "holes": rows, "top_spans_mm": top_spans,
        "runs": rr, "runs_bottom_edge_not_projected": rr_nb,
        "worst_lift_nom_1000h_um": worst, "worst_lift_nom_1000h_uniform_upper_bound_um": worst_unif,
        "worst_straight_run_uniform_um": worst_straight_unif, "pass": worst <= LIFT_MAX_UM and all(
            r["ok_outline_11"] and r["ok_ear_15_5"] and r["ok_corner_15"] and r["ok_loops_1_5"] for r in rows)
        and all(s <= 60.0 for s in top_spans),
    }
    if "--json" in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
    print("section I = %.1f mm4 (shelf 2.85), %.1f (shelf 5.1), v1 without flange %.1f" % (I, I2, I0))
    print("q nom %.4f N/mm, max %.4f N/mm" % (q_nom, q_max))
    for r in rows:
        print("%-5s x %7.2f y %7.2f  outline %6.2f  ear %s %6.2f  corner %6.2f  loops %6.2f  %s" % (
            r["name"], r["x"], r["y"], r["d_pcb_outline_mm"], r["nearest_ear"], r["d_nearest_ear_centre_mm"],
            r["d_corner_arc_start_mm"], r["d_tail_loop_env_mm"],
            "OK" if r["ok_outline_11"] and r["ok_ear_15_5"] and r["ok_corner_15"] and r["ok_loops_1_5"] else "FAIL"))
    print("top spans", top_spans)
    for r in rr:
        print("%-5s -> %-5s span %6.1f loaded %6.1f corner %d | nom 1000h %6.1f (unif %6.1f) | max 1000h %6.1f | "
              "nom short %5.1f | sig nom %.2f max %.2f" % (
                  r["from"], r["to"], r["span_mm"], r["loaded_mm"], r["turns_corner"], r["lift_nom_1000h_um"],
                  r["lift_nom_1000h_uniform_um"], r["lift_max_1000h_um"], r["lift_nom_short_um"],
                  r["bending_nom_MPa"], r["bending_max_MPa"]))
    print("worst nominal 1000 h lift %.1f um exact (limit %.0f) -> %s; uniform-smeared upper bound %.1f, "
          "straight runs (brief model) %.1f" % (worst, LIFT_MAX_UM, res["pass"], worst_unif, worst_straight_unif))
    return res


if __name__ == "__main__":
    main()


# ------------------------------------------------------------------------------------------------ v2.2 additions
DATUM = ((XL + XR) / 2.0, 69.5)          # datum_x = midpoint of the side pegs P1 (XL, 69.5) / P2 (XR, 69.5)
PEGS_V22 = {"P1": (XL, 69.5), "P2": (XR, 69.5)}
STUD_HOLE, STUD_SLOT, STUD_D = 4.5, 0.8, 4.0
ALPHA_REL, DT = 58e-6, 60.0              # 70 ppm/K transverse PA6-GF30 - 12 ppm/K steel, dT 60 K


def slot_axes(pattern):
    """radial slot axis per hole (unit vector, abs KiCad x / y-down) from the datum + thermal travel table.
    Case 'datum': frame grows about the datum (coordinator's assumption).
    Case 'P1 fixed': P1 round / P2 slotted along X in the sheet -> the frame grows about P1 (x) and y 69.5."""
    out = []
    travel = STUD_SLOT / 2 + (STUD_HOLE - STUD_D) / 2      # 0.4 + 0.25
    across = (STUD_HOLE - STUD_D) / 2                      # 0.25
    for n, (x, y) in pattern.items():
        dx, dy = x - DATUM[0], y - DATUM[1]
        r = math.hypot(dx, dy)
        u = (dx / r, dy / r)
        mov = r * ALPHA_REL * DT
        mx, my = (x - PEGS_V22["P1"][0]) * ALPHA_REL * DT, (y - PEGS_V22["P1"][1]) * ALPHA_REL * DT
        along = mx * u[0] + my * u[1]
        acr = abs(mx * u[1] - my * u[0])
        out.append({"name": n, "x": x, "y": y, "slot_axis": [round(u[0], 6), round(u[1], 6)],
                    "slot_axis_deg": round(math.degrees(math.atan2(dy, dx)), 3),
                    "r_from_datum_mm": round(r, 2), "move_datum_case_mm": round(mov, 3),
                    "travel_available_mm": travel, "across_clearance_mm": across,
                    "ok_datum_case": mov <= travel,
                    "move_P1_fixed_along_mm": round(along, 3), "move_P1_fixed_across_mm": round(acr, 3),
                    "ok_P1_fixed": abs(along) <= travel and acr <= across})
    peg_growth = (PEGS_V22["P2"][0] - PEGS_V22["P1"][0]) * ALPHA_REL * DT
    return out, peg_growth


def stud_bending(rib_h, F, lever=7.5, b=10.0, t=2.5, rib_t=1.5):
    """T-section at the stud: flange strip b x t + radial rib rib_t x rib_h on top, bending about the combined
    centroid, moment F x lever (coordinator's model)"""
    a1, z1 = b * t, t / 2
    a2, z2 = rib_t * rib_h, t + rib_h / 2
    zc = (a1 * z1 + a2 * z2) / (a1 + a2)
    I = b * t ** 3 / 12 + a1 * (z1 - zc) ** 2 + rib_t * rib_h ** 3 / 12 + a2 * (z2 - zc) ** 2
    c = max(zc, t + rib_h - zc)
    return {"rib_h_mm": rib_h, "F_N": F, "zc_mm": round(zc, 3), "I_mm4": round(I, 1), "c_mm": round(c, 3),
            "sigma_MPa": round(F * lever * c / I, 1)}


if __name__ == "__main__" and "--v22" in sys.argv:
    rows, pg = slot_axes(PATTERN)
    bend = {"v2.2_rib_5mm_worst": stud_bending(5.0, 64), "v2.2_rib_5mm_nominal": stud_bending(5.0, 18),
            "v2.1_rib_2.5mm_worst": stud_bending(2.5, 64), "v2.1_rib_2.5mm_nominal": stud_bending(2.5, 18)}
    res = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hole_pattern_result.json")))
    res["datum_abs"] = DATUM
    res["pegs_v22_abs"] = PEGS_V22
    res["slot_axes_thermal"] = rows
    res["peg_to_peg_growth_mm"] = round(pg, 3)
    res["stud_bending"] = bend
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hole_pattern_result.json"), "w"),
              indent=1)
    print("datum", DATUM, "peg-to-peg growth %.3f mm" % pg)
    for r in rows:
        print("%-5s r %6.2f deg %8.3f u (%7.4f %7.4f) | datum case %.3f/%.2f %s | P1 fixed along %.3f across %.3f %s" % (
            r["name"], r["r_from_datum_mm"], r["slot_axis_deg"], r["slot_axis"][0], r["slot_axis"][1],
            r["move_datum_case_mm"], r["travel_available_mm"], "ok" if r["ok_datum_case"] else "NO",
            r["move_P1_fixed_along_mm"], r["move_P1_fixed_across_mm"], "ok" if r["ok_P1_fixed"] else "NO"))
    for k, v in bend.items():
        print(k, v)
