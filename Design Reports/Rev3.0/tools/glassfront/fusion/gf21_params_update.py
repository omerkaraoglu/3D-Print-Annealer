"""Stage 5: master parameter file GF-2.0 -> GF-2.1 (Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json).
Owner decision 2026-11-16 (lead): border 19.0 on all four sides, released as GF-2.1, to close the two open findings of
the independent GF-2.0 verification (115 PASS / 1 FAIL): CTP tail -> bridge nose 0.239 at the full worst case (intent
>= 0.45) and bead inner edge 0.80 from the land-break edge (rule >= 1.0).
Split (confirmed CAD-side by Fusion script 86 before building): g_bend 3.23 = the smallest 0.01 step that gives 0.45
at the full worst case by the verification's method (0.239 + 0.93..0.95 x (g_bend - 3.00)); bottom land
19.0 - 9.51 - 3.23 = 6.26; bead inner edge -> break edge 6.26 - 4.9 - 0.3 = 1.06 on the land plane.
Every dependent value is re-derived by the GF-2.0 rules (glass = print window +- border, same offsets, F1-F4 = glass
corners + 11, flange = glass + 21 / bottom wall, pips on the bead centre line at +-1/4, logo zone centred between
window + 1.0 and glass edge - 2.5, VHB strips 1.0 short of the pads, fastener d_* values by the concept 4a rules from
frame_v2/out/board_geom.json, read only). The print window, the panel / PCB / connector side, the tail route and the
tail assumptions are unchanged. The verification's blocks open_findings, tail_clearance_criteria and fold_test keep
their criteria and figures; they only get a 'status_GF-2.1' note.
Writer discipline: the file is read as bytes and must be reproduced byte for byte by the writer (indent 1,
ensure_ascii False, trailing newline, CRLF) before anything is changed; the written file is re-read and checked the
same way. Never imports or runs concept/concept_calc.py.

Usage (python -B):
  gf21_params_update.py --stage design     GF-2.0 -> GF-2.1 (refuses unless the file is GF-2.0); backup of the GF-2.0
                                           file in %TEMP%\\rev3_glassfront\\gf21\\params_GF-2.0.json
  gf21_params_update.py --stage measured   (re)writes as_modelled_GF-2.1 and the measured values from the stage-5 dumps
                                           in %TEMP%\\rev3_glassfront\\gf21 (refuses unless GF-2.1)"""
import copy
import hashlib
import json
import math
import os
import shutil
import sys

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
BOARD = os.path.join(REPO, "Design Reports", "Rev3.0", "tools", "frame_v2", "out", "board_geom.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront\gf21"
BACKUP = os.path.join(SCR, "params_GF-2.0.json")
GF20_SHA = "7439b098325a09f4e31bd242b7db6372c30ae9c2bf0aa7c53e3b7003608b6082"
DATE = "2026-11-16"
BORDER, G_BEND = 19.0, 3.23
RV = "to be re-verified at GF-2.1"
REV = ("GF-2.1 (2026-11-16: GF-2.0 with border 19.0 on all four sides and g_bend 3.23 (bottom land 6.26), to close the "
       "two open findings of the independent GF-2.0 verification; see change_log)")


# ------------------------------------------------------------------------------------------------ byte-exact writer
def dumps(raw):
    return (json.dumps(raw, indent=1, ensure_ascii=False) + "\n").replace("\n", "\r\n").encode("utf-8")


def load_checked():
    b = open(P, "rb").read()
    raw = json.loads(b.decode("utf-8"))
    if dumps(raw) != b:
        raise SystemExit("writer check failed: the file is not reproduced byte for byte - refusing to write")
    return raw, b


def write_checked(raw):
    out = dumps(raw)
    tmp = P + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    back = open(tmp, "rb").read()
    if dumps(json.loads(back.decode("utf-8"))) != back:
        raise SystemExit("written file does not round-trip")
    os.replace(tmp, P)
    return hashlib.sha256(out).hexdigest()


def entry(lst, name):
    for e in lst:
        if e.get("name") == name:
            return e
    raise KeyError(name)


def r2(v):
    return round(v + 0.0, 2)


# ------------------------------------------------------------------------------------------------ geometry rules
def geometry(raw):
    rect = {r["name"]: r for r in raw["plan_rectangles"]}
    W = tuple(rect["print_window"][k] for k in ("x0", "x1", "y0", "y1"))
    co = {p["name"]: p["value"] for p in raw["carried_over_from_v2"]}
    dp = {p["name"]: p["value"] for p in raw["driving_parameters"]}
    GL = (W[0] - BORDER, W[1] + BORDER, W[2] - BORDER, W[3] + BORDER)
    ring = lambda off: tuple(r2(v) for v in (GL[0] - off, GL[1] + off, GL[2] - off, GL[3] + off))
    g2, lip_w, g1, srw = dp["g2"], dp["lip_w"], dp["g1"], dp["seat_ring_w"]
    G = {"glass": ring(0.0), "lip_in": ring(g2), "lip_out": ring(g2 + lip_w), "seat_ring_out": ring(g2 + lip_w + srw),
         "cut": ring(g2 + lip_w + g1), "tape_in": ring(srw + g2 + lip_w + dp["tape_margin"]),
         "tape_out": ring(srw + g2 + lip_w + dp["tape_margin"] + dp["tape_w"]), "fastener_line": ring(dp["fast_off"])}
    fl = list(ring(dp["flange_beyond_glass"]))
    fl[3] = max(fl[3], 150.235)                               # flange_y1_bottom: bottom-wall face at the flange front
    G["flange"] = tuple(fl)
    G["gc"] = ((GL[0] + GL[1]) / 2, (GL[2] + GL[3]) / 2)
    G["GL"] = GL
    G["bend_y1"] = co["panel_y1"] + G_BEND
    G["step_back_y"] = r2(GL[3] + g2 + lip_w + srw)        # glass + s_ring = step-wall back at the flange back
    gW, gH = GL[1] - GL[0], GL[3] - GL[2]
    s = dp["bead_edge"] + dp["bead_w"] / 2
    G["pips"] = [(GL[0] + gW / 4, GL[2] + s), (GL[0] + gW / 4, GL[3] - s), (GL[0] + 3 * gW / 4, GL[2] + s),
                 (GL[0] + 3 * gW / 4, GL[3] - s), (GL[0] + s, GL[2] + gH / 4), (GL[1] - s, GL[2] + gH / 4),
                 (GL[0] + s, GL[2] + 3 * gH / 4), (GL[1] - s, GL[2] + 3 * gH / 4)]
    pocket = tuple(rect["pocket"][k] for k in ("x0", "x1", "y0", "y1"))
    bead_in = dp["bead_edge"] + dp["bead_w"]
    G["lands"] = {"abs left": pocket[0] - GL[0], "abs right": GL[1] - pocket[1], "top": pocket[2] - GL[2],
                  "bottom_span": GL[3] - G["bend_y1"], "bottom_outside": GL[3] - pocket[3]}
    G["bead_to_pocket"] = {k: v - bead_in for k, v in G["lands"].items()}
    G["bead_to_break"] = GL[3] - bead_in - G["bend_y1"] - dp["land_break"]
    G["logo_cy"] = ((W[3] + 1.0) + (GL[3] - 2.5)) / 2
    F = G["fastener_line"]
    pad = dp["pad_d"]
    G["strips"] = {"top_bottom": r2((F[1] - pad / 2 - dp["tape_margin"]) - (F[0] + pad / 2 + dp["tape_margin"])),
                   "sides": r2((F[3] - pad / 2 - dp["tape_margin"]) - (F[2] + pad / 2 + dp["tape_margin"]))}
    # fasteners, concept 4a rules (concept_gf2_calc.py 'fasteners', re-implemented; board geometry read only)
    brd = json.load(open(BOARD, encoding="utf-8"))
    outline = brd["outline"][0]
    fps = {f["ref"]: f for f in brd["fps"]}
    J20, J2 = fps["J20"]["crtyd"], fps["J2"]["crtyd"]
    corr = [(-1e3, J20[2], J20[1] - 2.0, J20[3] + 2.0), (-1e3, J2[2], J2[1] - 2.0, J2[3] + 2.0)]
    holes = {"H%d" % i: (co["h%d_x" % i], co["h%d_y" % i]) for i in range(1, 10)}
    loops = [(co["loop_ctp_x0"], co["loop_ctp_x1"], co["panel_y1"], co["loop_ctp_y1"]),
             (co["loop_tft_x0"], co["loop_tft_x1"], co["panel_y1"], co["loop_tft_y1"])]
    tp = rect["tail_pocket"]
    tailpocket = (tp["x0"], tp["x1"], co["panel_y1"], tp["y1"])

    def seg_d(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy or 1e-12)))
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    def poly_d(p, pts):
        return min(seg_d(p, pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))

    def rect_d(p, r):
        return math.hypot(max(r[0] - p[0], 0.0, p[0] - r[1]), max(r[2] - p[1], 0.0, p[1] - r[3]))

    def rrect_d(p, r, R):
        return rect_d(p, (r[0] + R, r[1] - R, r[2] + R, r[3] - R)) - R

    def rrect_inner_d(p, r, R):
        """exact distance from a point inside a rounded rectangle to its boundary"""
        x, y = p
        best = min(x - r[0], r[1] - x, y - r[2], r[3] - y)
        for cx, cy in ((r[0] + R, r[2] + R), (r[1] - R, r[2] + R), (r[1] - R, r[3] - R), (r[0] + R, r[3] - R)):
            inx = (x < cx) if cx == r[0] + R else (x > cx)
            iny = (y < cy) if cy == r[2] + R else (y > cy)
            if inx and iny:
                best = min(best, R - math.hypot(x - cx, y - cy))
        return best

    rows = []
    gc = G["gc"]
    for n, (x, y) in (("F1", (F[0], F[2])), ("F2", (F[1], F[2])), ("F3", (F[1], F[3])), ("F4", (F[0], F[3]))):
        ux, uy = gc[0] - x, gc[1] - y
        L_ = math.hypot(ux, uy)
        hn, hd = min(((h, math.hypot(x - hx, y - hy)) for h, (hx, hy) in holes.items()), key=lambda t: t[1])
        rows.append({"name": n, "x_abs": r2(x), "y_abs_down": r2(y),
                     "slot_axis": [round(ux / L_, 4), round(uy / L_, 4)],
                     "slot_axis_deg": round(math.degrees(math.atan2(uy, ux)), 3), "r_from_glass_centre": round(L_, 3),
                     "d_board_outline_incl_ears": round(poly_d((x, y), outline), 4), "nearest_ear_hole": hn,
                     "d_ear_hole": round(hd, 4), "d_J20_J2_wire_corridor": round(min(rect_d((x, y), r) for r in corr), 4),
                     "d_tail_pocket_or_loops": round(min([rect_d((x, y), r) for r in loops] +
                                                         [rect_d((x, y), tailpocket)]), 4),
                     "d_pcb_boss_edge_from_tube": round(hd - pad / 2 - 4.0, 4),
                     "d_cut_out_edge": round(rrect_d((x, y), G["cut"], dp["R_cut"]), 4),
                     "d_tube_edge_to_flange_edge": round(rrect_inner_d((x, y), G["flange"], dp["flange_R"]) - pad / 2, 4),
                     "front_view_u": r2(-(x - gc[0])), "front_view_v": r2(gc[1] - y)})
    G["fasteners"] = rows
    return G


# ------------------------------------------------------------------------------------------------ design stage
def design(raw, b):
    if not str(raw.get("revision", "")).startswith("GF-2.0"):
        raise SystemExit("not GF-2.0 - the design stage runs once")
    if hashlib.sha256(b).hexdigest() != GF20_SHA:
        raise SystemExit("the GF-2.0 file is not the expected one (sha256 7439b098...)")
    os.makedirs(SCR, exist_ok=True)
    if not os.path.exists(BACKUP):
        shutil.copyfile(P, BACKUP)
    G = geometry(raw)
    log = []

    def chg(path, old, new, reason):
        log.append({"path": path, "old": old, "new": new, "reason": reason})

    old = raw["revision"]
    raw["revision"] = REV
    chg("revision", old, REV, "new revision (owner decision, border 19.0)")
    old = raw["status"]
    raw["status"] = ("frozen for CAD 2026-11-15 (GF-1.0), GF-1.1 2026-11-15, GF-2.0 2026-11-16, GF-2.1 2026-11-16 (stage 5 "
                     "Fusion rebuild, document 'Rev3.0 GlassFront'); border 19.0 / g_bend 3.23 still gated by the real-panel "
                     "fold test (fold_test)")
    chg("status", old, raw["status"], "")
    raw["about"] += " GF-2.1 (stage 5) edited by Design Reports/Rev3.0/tools/glassfront/fusion/gf21_params_update.py."
    dp = raw["driving_parameters"]
    e = entry(dp, "border")
    chg("driving_parameters.border.value", e["value"], BORDER, "owner decision: closes both open findings of the GF-2.0 "
        "verification together with g_bend 3.23 (open_findings 1 and 2)")
    e["value"] = BORDER
    e["note"] = ("window edge -> glass edge on ALL FOUR sides (GF-2.1; GF-2.0 18.5; GF-1.1 14.0 + chin 44.51). The one driving "
                 "value of the glass outline. Bottom budget: bezel 9.51 + g_bend 3.23 + land 6.26 = 19.00")
    e = entry(dp, "g_bend")
    chg("driving_parameters.g_bend.value", e["value"], G_BEND, "smallest 0.01 step with tail -> bridge-nose clearance >= "
        "0.45 at the full worst case of tail_clearance_criteria.bend_zone (GF-2.0: CTP 0.239 at 3.00; ~0.93-0.95 per mm)")
    e["value"] = G_BEND
    e["note"] = ("DRIVING (GF-2.1): bend gap = panel bottom edge (y 119.00) -> bridge pocket face over the tail span, bridge "
                 "face at y = panel_y1 + g_bend = 122.23 at Z_LAND, 1 deg widening to the back. 3.23 = the GF-2.0 3.00 + "
                 "0.23 so that the CTP tail keeps >= 0.45 to the R1.5 nose with the panel at its WC position 0.60, the "
                 "exit height at its limit and the tail at 0.35 (verification method; GF-2.0 0.239). The tail "
                 "assumptions are unchanged (straight 0.5 + R_in 1.5 + tail 0.30, single layer): the 0.23 is clearance "
                 "between the tail and the nose. Budget at border 19.0: bezel 9.51 + 3.23 + land 6.26 (bead_edge 0.9 + "
                 "bead_w 4.0 + 1.06 to the 0.3 land break) = 19.00")
    e = entry(dp, "land_break")
    e["note"] = ("GF-2.1: 45 deg break on the land front-inner edge (land x bridge pocket face) over the tail span, so the edge "
                 "cannot snag a tail when the frame is lowered in J2; the flat land starts 0.3 behind the pocket face. Bead "
                 "inner edge -> break edge 1.06 on the land plane (1.07 at Z_LAND + 0.01), -> pocket-face plane 1.36 "
                 "(CAD-side, %s)" % RV)
    e = entry(dp, "flange_y1_bottom")
    e["note"] = e["note"].replace("GF-2.0:", "GF-2.0 / GF-2.1:").replace("(glass + 21 = 148.99 would cut the wall)",
                                                                         "(glass + 21 = 149.49 at GF-2.1 would cut the wall)")
    chg("driving_parameters.land_break.note / flange_y1_bottom.note", None, "GF-2.1 values", "")

    rect = {r["name"]: r for r in raw["plan_rectangles"]}
    for n in ("glass", "lip_in", "lip_out", "seat_ring_out", "cut", "tape_in", "tape_out", "fastener_line", "flange"):
        r = rect[n]
        new = list(G[n])
        chg("plan_rectangles.%s" % n, [r["x0"], r["x1"], r["y0"], r["y1"]], new,
            "border 19.0, same offsets / rules as GF-2.0")
        r["x0"], r["x1"], r["y0"], r["y1"] = new
    gl, fl, cu = G["glass"], G["flange"], G["cut"]
    rect["glass"]["note"] = ("glass outline, +-0.1 requested (+-0.2 fallback); %.2f x %.2f; GF-2.1: print window +- border 19.0 "
                             "(y1 = print window y1 + border, derived)" % (gl[1] - gl[0], gl[3] - gl[2]))
    rect["cut"]["note"] = "SHEET CUT-OUT, laser, +-0.1, R 7.55 (+0/-0.2); %.2f x %.2f (GF-2.1)" % (cu[1] - cu[0], cu[3] - cu[2])
    fl3 = G["fastener_line"][3]
    rect["flange"]["note"] = ("flange outline at the flange front (parting line). Top / sides = glass + 21, corner radius "
                              "flange_R centred on F1 / F2; bottom edge y 150.235 = flange_y1_bottom (the bottom wall's outer "
                              "face continued, 150.20 at Z_LAND), bottom corners R10 centred 10 inside the corner (%.3f below "
                              "F3 / F4). %.2f x %.3f (GF-2.1)" % (fl[3] - 10 - fl3, fl[1] - fl[0], fl[3] - fl[2]))
    by, sw = G["bend_y1"], G["step_back_y"]
    L_ = G["bead_to_pocket"]
    rect["pocket"]["note"] = ("clearance pocket = panel + pocket_clr; defined at Z_SEAT with 1 deg draft (opening to the front): "
                              "0.10 larger per side at the land (measured x0 19.119 at Z_LAND vs 19.22 here). The land widths "
                              "and bead_to_pocket values in 'lands' apply at Z_SEAT. GF-2.1 (derived, %s): where the land ends "
                              "(Z_LAND + 0.01) the bead-to-pocket margins are abs left %.2f, abs right %.2f, top %.2f, bottom "
                              "outside the tail span %.2f; over the bridge 1.07 to the edge of the 0.3 x 45 land break (1.36 "
                              "to the pocket-face plane). GF-2.0 (verified): 5.61 / 8.37 / 7.53 / 3.19 and 0.80 / 1.09"
                              % (RV, L_["abs left"] - 0.10, L_["abs right"] - 0.10, L_["top"] - 0.10, L_["bottom_outside"] - 0.10))
    rect["tail_pocket"]["note"] = rect["tail_pocket"]["note"].replace("GF-2.0:", "GF-2.0 / GF-2.1:").replace(
        "bend_y1 122.00", "bend_y1 %.2f" % by).replace("(y 122.00 .. 130.89)", "(y %.2f .. %.2f)" % (by, sw)).replace(
        "(Z_FLOOR_LOW, y 130.89 .. 147.70)", "(Z_FLOOR_LOW, y %.2f .. 147.70)" % sw)
    r = rect["bend_gap_slot"]
    chg("plan_rectangles.bend_gap_slot.y1", r["y1"], r2(by), "g_bend 3.23")
    r["y1"] = r2(by)
    r["note"] = r["note"].replace("GF-2.0:", "GF-2.1:").replace("y 122.00 at Z_LAND", "y %.2f at Z_LAND" % by)
    r = rect["bridge"]
    chg("plan_rectangles.bridge.y0 / y1", [r["y0"], r["y1"]], [r2(by), sw], "g_bend 3.23, border 19.0")
    r["y0"], r["y1"] = r2(by), sw
    r["note"] = ("GF-2.1: land plate (land y %.2f .. %.2f at Z_LAND, back Z_LANDPLATE_BACK) + step wall (%.2f .. %.2f) + flange "
                 "plate over the tail span; nose R bend_nose_R on its back-inner edge, land_break 0.3 x 45 deg on its "
                 "front-inner edge" % (by, G["lip_in"][3], G["lip_in"][3], sw))
    r = rect["divider_rib"]
    chg("plan_rectangles.divider_rib.y0", r["y0"], r2(by), "front face coplanar with the bridge pocket face")
    r["y0"] = r2(by)
    r["note"] = r["note"].replace("GF-2.0:", "GF-2.0 / GF-2.1:")

    pp = raw["plan_points"]
    e = entry(pp, "borders_all_four")
    chg("plan_points.borders_all_four", e["value"], BORDER, "")
    e["value"], e["note"] = BORDER, "window edge -> glass edge, all four sides (GF-2.1)"
    old_l = copy.deepcopy(raw["lands"])
    vals = {"abs left (front-view right)": "abs left", "abs right (front-view left)": "abs right", "top": "top",
            "bottom over the tail span (x 38.9 .. 167.7)": "bottom_span", "bottom outside the tail span": "bottom_outside"}
    for e in raw["lands"]:
        k = vals[e["name"]]
        e["value"], e["bead_to_pocket"] = r2(G["lands"][k]), r2(G["bead_to_pocket"][k])
    entry(raw["lands"], "bottom over the tail span (x 38.9 .. 167.7)")["note"] = (
        "GF-2.1: to the bridge pocket face y %.2f at Z_LAND: bead_to_pocket %.2f to the face plane; the land_break 0.3 x 45 "
        "deg leaves %.2f of flat land and the bead inner edge %.2f from the break edge on the land plane (1.07 at Z_LAND + "
        "0.01) >= bead_pocket_min 1.0 (GF-2.0: 0.80, open_findings 2)" % (by, G["bead_to_pocket"]["bottom_span"],
                                                                         G["lands"]["bottom_span"] - 0.3, G["bead_to_break"]))
    entry(raw["lands"], "bottom outside the tail span")["note"] = "GF-2.1: to the clearance-pocket wall y 119.80 (at Z_SEAT)"
    chg("lands", [(x["name"], x["value"], x["bead_to_pocket"]) for x in old_l],
        [(x["name"], x["value"], x["bead_to_pocket"]) for x in raw["lands"]], "border 19.0, g_bend 3.23")
    for k, (x, y) in enumerate(G["pips"], 1):
        e = entry(raw["pips"], "pip%d" % k)
        new = [r2(x), r2(y)]
        chg("pips.pip%d" % k, e["value"], new, "same rule (bead centre line, +-1/4 of each side)")
        e["value"] = new
        e["note"] = e["note"].replace("GF-2.0: on the 5.99 bottom land over the bridge",
                                      "GF-2.1: on the 6.26 bottom land over the bridge")
    e = entry(raw["bead"], "bead_area")
    e["value"], e["note"] = RV + " (measured stage)", "as modelled at GF-2.1 (4.0 band, pip holes NOT subtracted, as GF-1.1 / GF-2.0)"
    fa = raw["fasteners"]
    old_f = [(f["name"], f["x_abs"], f["y_abs_down"]) for f in fa["positions"]]
    for f in fa["positions"]:
        new = next(x for x in G["fasteners"] if x["name"] == f["name"])
        for k, v in new.items():
            f[k] = v
    fa["positions_note"] = ("GF-2.1: F1-F4 only (S8 dropped at GF-2.0; nothing moulded at F5-F8), at the glass corners + 11; d_* "
                            "values re-derived by gf21_params_update.py with the concept 4a rules (board outline, ear holes, "
                            "J20 / J2 corridors from frame_v2/out/board_geom.json, loops, tail pocket, cut-out R7.55, flange "
                            "R10); d_cut_out_edge %s" % RV)
    chg("fasteners.positions", old_f, [(f["name"], f["x_abs"], f["y_abs_down"]) for f in fa["positions"]],
        "glass corners + 11 at border 19.0; d_* re-derived")
    lz = raw["logo_zone"]
    e = entry(lz, "logo_centre")
    chg("logo_zone.logo_centre", e["value"], [103.85, r2(G["logo_cy"])], "zone centred between window y1 + 1.0 and glass y1 "
        "- 2.5 (the verification's GF-2.0 rule)")
    e["value"] = [103.85, r2(G["logo_cy"])]
    e["note"] = ("GF-2.1: zone centred between window y1 + 1.0 (110.49) and glass y1 - 2.5 (%.2f): the 15-high zone is %.2f "
                 "from the window and %.2f from the glass edge (GF-2.0 117.99)" % (G["GL"][3] - 2.5, G["logo_cy"] - 7.5 - 109.49,
                                                                                  G["GL"][3] - (G["logo_cy"] + 7.5)))
    tg = raw["tape_and_gasket"]
    e = entry(tg, "strip_lengths")
    chg("tape_and_gasket.strip_lengths", e["value"], G["strips"], "new glass")
    e["value"] = G["strips"]
    e["note"] = "strips end 1.0 before the corner pads; area 12 x 2 x (%.2f + %.2f) = %.1f mm2 (GF-2.0 7603.2)" % (
        G["strips"]["top_bottom"], G["strips"]["sides"], 24 * (G["strips"]["top_bottom"] + G["strips"]["sides"]))
    e = entry(raw["sheet_variants"]["common"], "cut_out")
    chg("sheet_variants.common.cut_out", e["value"], list(G["cut"]), "")
    e["value"] = list(G["cut"])
    rules = raw["cad_rules"]
    for i, r in enumerate(rules):
        if r.startswith("GF-2.0: bridge = land plate"):
            new = (r.replace("GF-2.0: bridge", "GF-2.0 / GF-2.1: bridge")
                   .replace("(y 122.005, Z_LAND + land_break = -10.12)", "(GF-2.1: y %.3f, Z_LAND + land_break = -10.12)" % (by + 0.005))
                   .replace("so it rises 5.52 over the 3.00 slot width", "so it rises 5.52 over the slot width (GF-2.1: %.2f)" % G_BEND)
                   .replace("an A-side ledge 3.0 x 0.3 across the slot", "an A-side ledge %.2f x 0.3 across the slot" % G_BEND))
            chg("cad_rules[%d]" % i, r, new, "slot width / break position follow g_bend 3.23 (the verified shut-off "
                "description itself is unchanged; angles %s)" % RV)
            rules[i] = new
    e = entry(raw["corner_cell_H6"], "h6_jog_y")
    e["note"] = e["note"].replace("(y 130.89)", "(y 130.89 at GF-2.0, %.2f at GF-2.1)" % sw)
    raw["tail_route"]["note"] += (" GF-2.1: unchanged (tail assumptions unchanged; the extra 0.23 of g_bend is clearance between "
                                  "the tail and the bridge nose)")
    raw["checks"]["status_GF-2.1"] = ("the concept estimates (push / impact) were made at border 18.5 / glass 190.48 x 122.32: %s "
                                      "(glass 191.48 x 123.32)" % RV)
    for k in ("open_findings", "tail_clearance_criteria", "fold_test"):
        raw[k]["status_GF-2.1"] = ("GF-2.1 (border 19.0, g_bend 3.23, bridge face y 122.23): the GF-2.0 figures in this block "
                                   "are SUPERSEDED and are to be re-evaluated by the independent verification at GF-2.1, which "
                                   "will rewrite this block; criteria unchanged. CAD-side figures of the rebuild: "
                                   "as_modelled_GF-2.1")
    raw["as_modelled_GF-2.0"]["status"] = "GF-2.0 (Fusion version 18) values; superseded by as_modelled_GF-2.1"
    raw["to_be_reverified_at_GF-2.1"] = [
        "the independent verification (frame STEP, params, fit) incl. open_findings 1 / 2, tail_clearance_criteria.bend_zone "
        "results and the fold_test numbers (gauge slot / feeler) at g_bend 3.23",
        "drawings GF-D01..D50 (Mechanical/Rev3.0_GlassFront/drawings hold the GF-2.0 set; archived in archive/GF-2.0)",
        "design document Rev3.0_GlassFront_Design.md (GF-2.0; archived as archive/GF-2.0/Rev3.0_GlassFront_Design_GF-2.0.md)",
        "concept push / impact estimates (checks), gap tables over temperature (glass 1.0 wider in x and y)",
        "fasteners d_* values (re-derived by rule, not measured), logo zone placement on the print artwork"]
    prev = raw.pop("change_log")
    raw["change_log"] = {"from": "GF-2.0", "to": "GF-2.1", "date": DATE,
                         "by": "stage 5 Fusion agent (Design Reports/Rev3.0/tools/glassfront/fusion/gf21_params_update.py)",
                         "decision": "owner (via the lead) 2026-11-16: border 19.0, release as GF-2.1, after the independent "
                                     "GF-2.0 verification 115 PASS / 1 FAIL with two open findings",
                         "split": {"border": BORDER, "bezel": 9.51, "g_bend": G_BEND, "bottom_land": r2(G["lands"]["bottom_span"]),
                                   "bead_to_break_land_plane": r2(G["bead_to_break"]),
                                   "derivation": "g_bend = smallest 0.01 step with CTP tail -> nose >= 0.45 at the full worst "
                                                 "case: 0.239 + ~0.93..0.95 x (g - 3.00) >= 0.45 -> 3.23 (3.22 gives ~0.44); "
                                                 "confirmed CAD-side by Fusion script 86 (gf21/bend_zone_probe.json); land = "
                                                 "19.0 - 9.51 - 3.23 = 6.26 -> bead to break 1.06 >= 1.0"},
                         "params_sha256_before": GF20_SHA, "changes": log, "previous_revisions": {"GF-2.0": prev}}
    return raw


# ------------------------------------------------------------------------------------------------ measured stage
def measured(raw):
    if not str(raw.get("revision", "")).startswith("GF-2.1"):
        raise SystemExit("run --stage design first")
    J = lambda n: json.load(open(os.path.join(SCR, n), encoding="utf-8")) if os.path.exists(os.path.join(SCR, n)) else None
    fr, fp, ft, fx = J("as_modelled_frame.json"), J("fit_parts.json"), J("fit_tails.json"), J("fasteners.json")
    th, ex, fl, bz = J("thickness_final/thickness_check.json"), J("export.json"), J("flex_final.json"), J("bend_zone_final.json")
    am = {"source": "Fusion document 'Rev3.0 GlassFront' (GF-2.1), stage-5 scripts 86-9x and gf20_thickness_check.py on the "
                    "exported frame STEP; dumps in %TEMP%\\rev3_glassfront\\gf21; CAD-side values, not the independent "
                    "verification"}
    if ex:
        p = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_Frame.step")
        am["frame_step"] = dict(ex["files"]["Rev3.0_GlassFront_Frame.step"],
                                sha256=hashlib.sha256(open(p, "rb").read()).hexdigest(),
                                fusion_version=(J("docinfo.json") or {}).get("version"))
    if fr:
        f = fr["frame"]
        am.update({"frame_volume_cm3": f["volume_cm3"], "frame_mass_g_at_1.36": f["mass_g_at_1.36"], "faces": f["faces"],
                   "edges": f["edges"], "bodies": 1, "lumps": f["lumps"], "bbox_abs": f["bbox_abs"],
                   "pad_hard_stop_faces_mm2": fr["pad_hard_stop_faces_mm2"], "pips": fr["pips"]})
    if fp:
        band = fp["bead"]["faces_at_Z_LAND_mm2"][-1]
        am["bead_area_mm2"] = {"band_without_subtracting_pips": round(band + 8 * math.pi * 0.75 ** 2, 1),
                               "face_as_modelled_with_8_pip_holes": band}
        am["tape_area_mm2"] = fp["tape"]["total_area_mm2"]
        am["strip_end_to_pad_mm"] = sorted({t["to_pad_mm"] for t in fp["tape"]["strips"]})
        g2, g1 = fp["g2_glass_edge_to_lip"]["gaps"], fp["g1_cutout_to_lip"]["gaps"]
        am["g2_mm"] = {"side_at_flush-0.5": min(g2[k][sorted(g2[k], key=float)[-2]] for k in ("left", "right", "top", "bottom")),
                       "corner_at_flush-0.5": min(g2[k][sorted(g2[k], key=float)[-2]] for k in g2 if k.startswith("corner")),
                       "all": g2}
        am["g1_mm"] = {"all": g1}
        am["pip_top_to_glass_mm"] = sorted({q["to_glass_mm"] for q in fp["pips"]})
    if bz:
        am["bend_zone_CAD_side"] = bz
    if ft:
        am["tail_clearances_mm"] = {nm: {"frame_min": e["frame_overall"]["d_mm"],
                                         "frame_by_class": {k: v["d_mm"] for k, v in e["frame_by_class"].items()},
                                         "glass_print": e["parts"]["glass print"]["d_mm"], "glass": e["parts"]["glass"]["d_mm"],
                                         "bead": e["parts"]["bead"]["d_mm"], "optical_bond": e["parts"]["optical bond"]["d_mm"],
                                         "Formex": e["parts"]["Formex sheet"]["d_mm"]} for nm, e in ft["tails"].items()}
    if fx:
        am["fasteners"] = fx["summary"]
    if th:
        am["max_inscribed_sphere_mm"] = th["max_sphere_dia"]
        am["thick_spots_over_5.0"] = len(th["spots_over_5.0"])
        am["thickest_spots"] = th["top5"]
        am["thin_walls_lt_1.2"] = [{"plane": w.get("plane"), "width_max": w.get("width_max"), "at": w.get("at"),
                                    "length": w.get("length")} for w in th.get("thin", {}).get("thin_walls", [])]
        am["thin_extra_probes_lt_1.2"] = th.get("thin_extra_walls", [])
    if fl:
        am["flex_test"] = [{"case": r["case"], "healthy": r["healthy"], "bodies": r["bodies_in_component"],
                            "lumps": r["lumps"], "volume_cm3": r["volume_cm3"], "faces": r["faces"]} for r in fl]
    raw["as_modelled_GF-2.1"] = am
    if fp:
        e = entry(raw["bead"], "bead_area")
        e["value"] = am["bead_area_mm2"]["band_without_subtracting_pips"]
    for e in raw["fasteners"]["tube_coring"]:
        if e["name"] == "max_inscribed_sphere" and th:
            e["value"] = th["max_sphere_dia"]
            e["note"] = "whole frame at GF-2.1, verification toolchain method (voxel 0.2, 3D EDT) on the exported STEP; limit 5.0"
    raw["change_log"]["measured_values"] = {"date": DATE, "written_by": "gf21_params_update.py --stage measured",
                                            "paths": ["as_modelled_GF-2.1", "bead.bead_area",
                                                      "fasteners.tube_coring.max_inscribed_sphere"]}
    return raw


def main():
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else None
    raw, b = load_checked()
    if stage == "design":
        raw = design(raw, b)
    elif stage == "measured":
        raw = measured(raw)
    else:
        raise SystemExit(__doc__)
    h = write_checked(raw)
    print("written", P, "stage", stage, "sha256", h)


if __name__ == "__main__":
    main()
