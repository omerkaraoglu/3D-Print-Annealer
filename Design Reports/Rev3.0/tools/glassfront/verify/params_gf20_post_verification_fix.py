"""GF-2.0 master params: corrections after the independent verification (lead decisions 2026-11-16).

  <venv>\\Scripts\\python.exe -B params_gf20_post_verification_fix.py            (writes the master, the errata, the diff)
  <venv>\\Scripts\\python.exe -B params_gf20_post_verification_fix.py --dry-run  (diff only)

What it changes (notes, criteria, check results; the only geometry-related value is the logo-zone centre = print artwork,
not read by the frame or the Fusion model):
  * open_findings (new): 1 bend-zone clearance at the worst case, 2 bead inner edge to the land break;
  * tail_clearance_criteria (new): loop_clr for the loops / pocket, bend-zone criterion (>= 0.45 at the RSS panel position,
    > 0 at the worst case) with the corrected position tolerance incl. print-to-edge; carried_over loop_clr note;
  * g_bend note (budget with the position term 0.31 RSS), cad_rules shut-off rule (buildable stepped / telescopic form),
    cad_rules R0.5 shelf-end rounds (new rule), bend_gap_slot and pocket notes, gaps notes (verified tables), checks
    (push / impact verified with the measured section I, grillage not FEA), bead adhesive note, v2_superseded status,
    carried-over loop envelope notes (values kept: loop_tft_y1 drives tr_y1 in the Fusion parameter table), logo-zone centre,
    as_modelled_GF-2.0 (tail-to-PCB figures, pip top to glass), to_be_reverified entries verified, one change_log entry;
  * writes Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report_errata.json (corrections to the CAD reports);
  * writes out/params_fix_numeric_diff.json (every numeric leaf before / after) and keeps out/params_before_post_verification_fix.json.
Numbers come from the verification outputs (out/calc.json, out/fitcheck.json, out/cadcheck.json) and from a direct 3D
computation of the bend-zone cases (tails_gf2). concept/concept_calc.py is never imported or run.
"""
import hashlib
import json
import math
import os
import shutil
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon as C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PARAMS = C.GF_PARAMS
BACKUP = os.path.join(OUT, "params_before_post_verification_fix.json")
DIFF = os.path.join(OUT, "params_fix_numeric_diff.json")
ERRATA = os.path.join(C.GF_DIR, "Rev3.0_GlassFront_Frame_report_errata.json")
DATE = "2026-11-16"
KEY = "post_verification_corrections_%s" % DATE


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def write_master(d, path):
    """same format as the master: json indent 1, ASCII, CRLF line ends, trailing newline"""
    s = json.dumps(d, indent=1, ensure_ascii=True) + "\n"
    open(path, "wb").write(s.replace("\n", "\r\n").encode("ascii"))


def numeric_leaves(o, path=""):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            out.update(numeric_leaves(v, "%s.%s" % (path, k) if path else str(k)))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            nm = v.get("name") if isinstance(v, dict) and "name" in v else None
            out.update(numeric_leaves(v, "%s[%s]" % (path, nm if nm is not None else i)))
    elif isinstance(o, bool):
        pass
    elif isinstance(o, (int, float)):
        out[path] = o
    return out


def entry(lst, name):
    e = [x for x in lst if isinstance(x, dict) and x.get("name") == name]
    assert len(e) == 1, name
    return e[0]


def bend_zone_cases(G, rss, wc, ze_tol, t_tol, alt_wc):
    """direct 3D clearances of both tails to the bend zone (nose, pocket face, break) - the same functions the fit check uses"""
    import tails_gf2 as TG
    fr, _ = C.load_solid(C.GF_STEP)
    groups = TG.classify_frame_faces(fr, G)
    feats = ("bridge nose R1.5", "bridge pocket face y 122.0 (+ rib front)", "land break 0.3 x 45")
    bz = [f for k in feats for f in groups[k]]
    res = {}
    for n in ("TFT", "CTP"):
        T = TG.tail_data(G, n)
        def clr(dy, dz, t, P=None):
            if P is None:
                ze = T["Z_exit"] + dz
                rc = float(G.tail_R_in_min) + t / 2
                P = TG.route(T, y_edge=119.0 + dy, Ze=ze, rc1=rc, rc2=rc, Z_leg=max(T["Z_leg"], ze + 2 * rc))["pts"]
            sol = [s for _, s, _ in TG.tail_solids(G, n, P, t=t)]
            return TG.dist_min(bz, sol)[0]
        import numpy as np
        t0 = T["thickness"]
        res[n] = {"nominal": round(clr(0, 0, t0, np.array(T["centreline_yZ"])), 3),
                  "RSS": round(clr(rss, 0, t0), 3),
                  "WC": round(min(clr(wc, s * ze_tol, t0 + t_tol) for s in (-1, 1)), 3),
                  "WC_panel_only": round(clr(wc, 0, t0), 3),
                  "WC_print_0.1": round(min(clr(alt_wc, s * ze_tol, t0 + t_tol) for s in (-1, 1)), 3),
                  "WC_panel_only_print_0.1": round(clr(alt_wc, 0, t0), 3)}
        print("  bend zone", n, res[n], flush=True)
    return res


def main(argv):
    dry = "--dry-run" in argv
    raw = json.load(open(PARAMS, encoding="utf8"))
    if KEY in raw.get("change_log", {}):
        print("already applied (change_log has %s) - restore %s first to re-run" % (KEY, BACKUP))
        return 1
    sha_old = sha(PARAMS)
    # the writer must reproduce the master byte for byte before anything is changed
    probe = os.path.join(OUT, "_params_format_probe.json")
    write_master(raw, probe)
    same = open(probe, "rb").read() == open(PARAMS, "rb").read()
    os.remove(probe)
    assert same, "write_master does not reproduce the master format - nothing written"
    before = json.loads(json.dumps(raw))
    G = C.GF(PARAMS)
    calc = json.load(open(os.path.join(OUT, "calc.json")))
    fit = json.load(open(os.path.join(OUT, "fitcheck.json")))
    cad = json.load(open(os.path.join(OUT, "cadcheck.json")))
    summ = json.load(open(os.path.join(OUT, "summary.json")))
    step_sha = summ["inputs"]["frame"]["sha256"]
    assert step_sha == C.file_id(C.GF_STEP)["sha256"], "the frame STEP changed since the verification run"
    vstamp = "VERIFIED %s (independent verification, tools/glassfront/verify, frame STEP sha256 %s)" % (DATE, step_sha[:16])
    changes = []

    def chg(path, old, new, reason):
        changes.append({"path": path, "old": old, "new": new, "reason": reason})

    # ------------------------------------------------------------------ numbers
    contrib = {"panel outline vs AA (panel DS)": 0.2, "J1: AA aligned to the print window": 0.1,
               "print window vs glass edge (drawing_tolerances.print print-to-edge +-0.2)": 0.2,
               "J2: glass centred in the recess (graded shims)": 0.05, "frame: bridge face (B core) vs recess wall (A core), core shift [A]": 0.05}
    rss = math.sqrt(sum(v * v for v in contrib.values()))
    wc = sum(contrib.values())
    alt_wc = wc - 0.1
    ze_tol, t_tol = 0.3, 0.05
    print("bend-zone cases (direct 3D) ...", flush=True)
    bz = bend_zone_cases(G, rss, wc, ze_tol, t_tol, alt_wc)
    l0, rin, tt = float(G.tail_straight_l0), float(G.tail_R_in_min), float(G.tail_t)
    bezel = G.PANEL[3] - G.PRINT[3]
    land_min = G.bead_edge + G.bead_w + float(G.bead_pocket_min)
    g_max = G.border - bezel - land_min
    budget = l0 + rin + tt + 0.45 + rss
    slope = (bz["CTP"]["RSS"] - bz["CTP"]["WC_panel_only"]) / (wc - rss)
    g_need_all = G.g_bend + (0.45 - bz["CTP"]["WC"]) / slope
    g_need_panel = G.g_bend + max(0.0, (0.45 - bz["CTP"]["WC_panel_only"]) / slope)
    g19_land = 19.0 - bezel - round(g_need_all, 2)
    g19_brk = g19_land - G.land_break - (G.bead_edge + G.bead_w)
    b19_land = 19.0 - bezel - 3.21
    bead_brk_19 = b19_land - G.land_break - (G.bead_edge + G.bead_w)
    brk_max_185 = (G.GLASS[3] - G.bead_edge - G.bead_w) - G.BRIDGE[2] - float(G.bead_pocket_min)
    bd = fit["bead_to_pocket"]
    # ------------------------------------------------------------------ 1. open findings + criteria (new blocks)
    raw["open_findings"] = {
        "about": "findings of the independent verification %s that stay open until the owner decides (with the real-panel fold test, "
                 "concept_gf2.md 2.4); the frame (STEP sha256 %s) and border 18.5 are unchanged" % (DATE, step_sha[:16]),
        "1_bend_zone_clearance_worst_case": {
            "status": "OPEN (owner decision); the params criterion (tail_clearance_criteria.bend_zone) is MET",
            "finding": "the concept intended 0.45 tail -> bridge clearance at the worst case; with the panel position tolerance corrected to "
                       "include print-to-edge +-0.2 (RSS %.3f / WC %.2f instead of 0.25 / 0.35) the CTP tail keeps %.3f at the worst case "
                       "(panel +%.2f, exit Z +-%.1f, tail %.2f) and %.3f with the panel position alone" % (
                           rss, wc, bz["CTP"]["WC"], wc, ze_tol, tt + t_tol, bz["CTP"]["WC_panel_only"]),
            "measured_mm": {n: dict(v, feature="bridge nose R1.5") for n, v in bz.items()},
            "criterion": ">= 0.45 at the RSS panel position, > 0 at the worst case: TFT %.3f / %.3f, CTP %.3f / %.3f -> met" % (
                bz["TFT"]["RSS"], bz["TFT"]["WC"], bz["CTP"]["RSS"], bz["CTP"]["WC"]),
            "fixes": "g_bend about %.2f restores 0.45 at the full worst case (needs border 19.0: bottom land %.2f, bead to the break %.2f, "
                     "which also closes finding 2); g_bend about %.2f would do it for the panel position alone (within border 18.5, "
                     "limit %.2f); print-to-edge +-0.1 gives %.3f with the panel position alone but only %.3f with the exit height and "
                     "the tail thickness at their limits (slope about %.2f clearance per mm of g_bend, from the RSS and WC cases)" % (
                         g_need_all, g19_land, g19_brk, g_need_panel, g_max, bz["CTP"]["WC_panel_only_print_0.1"],
                         bz["CTP"]["WC_print_0.1"], slope),
            "source": "tools/glassfront/verify/out/fitcheck.json (tails.bend_zone), calc.json (bend_zone_criterion)"},
        "2_bead_to_land_break": {
            "status": "OPEN, FAIL (A1 bead_pocket_min 1.0, measured where the land ends as at GF-1.1)",
            "finding": "over the bridge the bead inner edge is %.3f from the edge of the 0.3 x 45 land break (x 60 and x 130, Z_LAND + 0.01); "
                       "to the bridge pocket-face plane it is %.3f" % (bd["bottom over the bridge, CTP x 60"], fit["bead_to_pocket_plane_bridge"][0]),
            "fixes": "border 19.0 with g_bend 3.21: bottom land %.2f (9.51 + 3.21 + %.2f = 19.00), bead to the break edge %.2f; or, at border "
                     "18.5, land_break <= %.2f (0.10 gives %.2f)" % (b19_land, b19_land, bead_brk_19, brk_max_185, 1.09 - 0.10),
            "source": "tools/glassfront/verify/out/fitcheck.json (bead_to_pocket, bead_to_pocket_plane_bridge)"}}
    chg("open_findings", None, "added (items 1, 2)", "independent verification %s" % DATE)
    raw["tail_clearance_criteria"] = {
        "about": "lead decision %s after the independent verification: loop_clr (carried over from v1/v2) applies to the loops and the "
                 "tail pocket, not to the bend zone, which the tail passes at less than 1.5 by design and is laid over after cure" % DATE,
        "loop_clr": {"value_mm": 1.5, "applies_to": "U-loops and the tail-pocket side walls, divider rib, bottom wall, flange plate, land-plate "
                     "back and slot ends (nominal route)", "source": "carried_over_from_v2.loop_clr"},
        "bend_zone": {"features": ["bridge nose R1.5", "bridge pocket face y 122.0 (+ rib front)", "land break 0.3 x 45"],
                      "clearance_min_at_RSS_mm": 0.45, "clearance_min_at_WC_mm": 0.0,
                      "criterion": "clearance >= 0.45 with the panel at its RSS position tolerance, and > 0 (no forced contact) at the worst case "
                                   "(panel at its WC position, exit height at either limit, tail at its upper thickness)",
                      "panel_position_contributors_mm": contrib, "panel_position_RSS_mm": round(rss, 3), "panel_position_WC_mm": round(wc, 2),
                      "exit_Z_tol_mm": ze_tol, "tail_t_tol_mm": t_tol, "alternative_panel_position_WC_with_print_0.1_mm": round(alt_wc, 2),
                      "concept_values_superseded": "panel position 0.25 RSS / 0.35 WC (concept_gf2.md 2.1, without print-to-edge)",
                      "results_%s" % DATE: {n: {"nominal": v["nominal"], "at_RSS": v["RSS"], "at_WC": v["WC"]} for n, v in bz.items()},
                      "verdict_%s" % DATE: "met (TFT %.3f >= 0.45 / %.3f > 0; CTP %.3f >= 0.45 / %.3f > 0)" % (
                          bz["TFT"]["RSS"], bz["TFT"]["WC"], bz["CTP"]["RSS"], bz["CTP"]["WC"])}}
    chg("tail_clearance_criteria", None, "added (loop_clr scope, bend-zone criterion)", "lead decision on verification item 1")
    # ------------------------------------------------------------------ 2. g_bend note
    e = entry(raw["driving_parameters"], "g_bend")
    old = e["note"]
    assert "panel position 0.25 (concept_gf2.md 2.1)" in old
    e["note"] = ("DRIVING (GF-2.0): bend gap = panel bottom edge (y 119.00) -> bridge pocket face over the tail span. Budget (concept_gf2.md "
                 "2.1, position term corrected %s): straight 0.5 + R_in 1.5 + tail 0.30 + clearance 0.45 + panel position %.2f RSS (AA->outline "
                 "0.2, J1 0.1, print-to-edge 0.2, J2 0.05, core shift 0.05; WC %.2f) = %.2f; border 18.5 holds while g_bend <= %.2f (bezel %.2f + "
                 "land %.1f) -> reserve %.2f to that limit. The modelled 3.00 is %.2f below the budget sum; the measured bend-zone clearance "
                 "still meets tail_clearance_criteria.bend_zone (CTP %.3f at the RSS position, the closest point is the R1.5 nose, not the flat "
                 "face). Bridge face at y = panel_y1 + g_bend at Z_LAND, 1 deg widening to the back. A double-sided tail (R3.6) would need "
                 "%.2f and border %.1f" % (DATE, rss, wc, budget, g_max, bezel, land_min, g_max - budget, budget - G.g_bend,
                                           bz["CTP"]["RSS"], 0.5 + 3.6 + 0.3 + 0.45 + rss, bezel + (0.5 + 3.6 + 0.3 + 0.45 + rss) + land_min))
    import re
    m = re.search(r"clearance ([\d.]+) \+ panel position ([\d.]+)", e["note"])
    m2 = re.search(r"double-sided tail \(R([\d.]+)\) would need ([\d.]+) and border ([\d.]+)", e["note"])
    assert m and m2 and m.group(2) == "%.2f" % rss, "g_bend note must stay readable for the drawings toolchain (make_tailgauge, selfcheck)"
    chg("driving_parameters.g_bend.note", old, e["note"], "item 1: position term 0.25 -> 0.31 RSS, reserve to the border-18.5 limit")
    # ------------------------------------------------------------------ 3. cad_rules: shut-off, R0.5 rounds
    rules = raw["cad_rules"]
    so = [i for i, r in enumerate(rules) if "shut-off A/B" in r]
    assert len(so) == 1
    so_b = cad["mould"]["bridge"]["shut_off"][0]
    pb, pf = so_b["PB_chamfer_top_yZ"], so_b["PF_shelf_corner_yZ"]
    k_st = next(k for k in so_b if k.startswith("option_stepped"))
    old = rules[so[0]]
    rules[so[0]] = ("GF-2.0: bridge = land plate + step wall + flange plate over the tail span; nose R bend_nose_R on the land-plate back x "
                    "pocket face (B side), land_break 0.3 x 45 deg on the land x pocket face (A side); slot faces 1 deg; the bend-gap slot is "
                    "the only through-opening at the bottom. Its shut-off A/B is NOT a flat face at Z_LAND: the parting runs on the bridge side "
                    "at the top of the land break (y %.3f, Z_LAND + land_break = %.2f) and on the front side at the shelf corner (y %.2f, "
                    "Z_SEAT %.2f), so it rises %.2f over the %.2f slot width. Buildable form: an A-side ledge %.1f x %.1f across the slot at "
                    "the break level, then a telescopic shut-off face along y %.1f rising to Z_SEAT, >= 3 deg on that face (no part face below "
                    "Z_SEAT there; up to %.1f deg fits in the slot); steel angles B %.0f deg / A %.0f deg at the break top, no knife edge (a "
                    "straight shut-off from the break top to the shelf corner leaves a %.1f deg B-steel knife edge; a flat shut-off at Z_LAND "
                    "makes the break an undercut for B with a 45 deg knife edge). Toolmaker to state the final shut-off design; no flash "
                    "allowed on it (verified %s)" % (pb[0], pb[1], pf[0], pf[1], so_b["rise_mm"], so_b["run_mm"], so_b["run_mm"], G.land_break,
                                                     pf[0], so_b["max_shutoff_angle_from_pull_deg"], so_b[k_st]["B_steel_at_PB_deg"],
                                                     so_b[k_st]["A_steel_at_PB_deg"], so_b["option_straight_PF_PB"]["B_steel_wedge_at_PB_deg"], DATE))
    chg("cad_rules[%d]" % so[0], old, rules[so[0]], "item 3: shut-off rewritten to the buildable stepped / telescopic form")
    r05 = ("GF-2.0: R0.5 vertical rounds in the two inside corners shelf end (y 119.0) x tail-pocket side walls (x 38.9 / 167.7) between "
           "Z_SEAT and Z_SHELF_BACK (kept; added at GF-2.0, sharp at GF-1.1; found by the independent verification %s, 0.29 mm3)" % DATE)
    rules.append(r05)
    chg("cad_rules (+1)", None, r05, "item 4: R0.5 shelf-end rounds kept and listed")
    # ------------------------------------------------------------------ 4. plan_rectangles notes
    r = entry(raw["plan_rectangles"], "bend_gap_slot")
    old = r["note"]
    r["note"] = ("GF-2.0: bend-gap slot over the tail span, x 38.9 .. 167.7. Back face = bridge pocket face y 122.00 at Z_LAND, 1 deg wider to "
                 "the back, 0.3 x 45 break at the land. Front: the shelf end over the tail span, y 119.0 at Z_SEAT, from Z_SEAT to the shelf "
                 "back; below Z_SEAT there is no frame face at y 119 - the slot is open to the clearance pocket (the former '119.10 at Z_LAND' "
                 "was an extrapolation). Open from the land (glass back) to the tail pocket; shut-off see cad_rules (stepped / telescopic, "
                 "parting at the break top and at the shelf corner) (verified %s)" % DATE)
    chg("plan_rectangles.bend_gap_slot.note", old, r["note"], "item 3")
    r = entry(raw["plan_rectangles"], "pocket")
    old = r["note"]
    assert "at the land the minimum bead-to-pocket is 1.11" in old
    r["note"] = ("clearance pocket = panel + pocket_clr; defined at Z_SEAT with 1 deg draft (opening to the front): 0.10 larger per side at "
                 "the land (measured x0 19.119 at Z_LAND vs 19.22 here). The land widths and bead_to_pocket values in 'lands' apply at Z_SEAT. "
                 "Where the land ends (Z_LAND + 0.01) the bead-to-pocket margins are (GF-2.0, verified %s): abs left %.2f, abs right %.2f, "
                 "top %.2f, bottom outside the tail span %.2f; the smallest is over the bridge: %.2f to the edge of the 0.3 x 45 land break "
                 "(%.2f to the pocket-face plane, which is defined at the land) - open_findings 2. The GF-1.1 values 1.11 / 3.87 / 3.03 / 1.40 "
                 "no longer apply" % (DATE, bd["left"], bd["right"], bd["top"], bd["bottom outside the tail span x 24"],
                                      bd["bottom over the bridge, CTP x 60"], fit["bead_to_pocket_plane_bridge"][0]))
    chg("plan_rectangles.pocket.note", old, r["note"], "GF-1.1 values replaced by the verified GF-2.0 margins")
    # ------------------------------------------------------------------ 5. gaps notes
    gt = calc["gaps_table"]
    def g(tag, t, case, k):
        return gt[tag][t][case][k]
    e2 = entry(raw["gaps"], "g2_glass_lip")
    old = e2["note"]
    hot50, hot70 = "+70 C frame/glass, +50 C sheet, 50 ppm", "+70 C frame/glass, +50 C sheet, 70 ppm"
    k1 = "glass +0.1/side, R nominal (requested +-0.1, R +0.2/-0)"
    k2 = "glass +0.2/side, R nominal (R +0.2/-0 callout)"
    k3 = "glass +0.2/side and R -0.2 (size + radius tolerances)"
    e2["note"] = ("20 C nominal (STEP, 0.32 behind the flush plane: sides %.3f, corner diagonal %.3f). GF-2.0 over temperature (verified "
                  "%s, nominal sides): -20 C %.3f (50 ppm) / %.3f (70 ppm); +70 C %.3f (50 ppm) / %.3f (70 ppm). Tolerance cases at -20 C, "
                  "70 ppm (sides / corner min; negative = the glass touches the lip): glass +0.1/side %.3f / %.3f; glass +0.2/side, R nominal "
                  "%.3f / %.3f; glass +0.2/side and R -0.2 %.3f / %.3f. As at GF-1.1 it can touch at -20 C with 70 ppm WC" % (
                      g("g2", "20 C", "nominal", "sides_min"), g("g2", "20 C", "nominal", "diagonal"), DATE,
                      g("g2", "-20 C, 50 ppm", "nominal", "sides_min"), g("g2", "-20 C, 70 ppm", "nominal", "sides_min"),
                      g("g2", hot50, "nominal", "sides_min"), g("g2", hot70, "nominal", "sides_min"),
                      g("g2", "-20 C, 70 ppm", k1, "sides_min"), g("g2", "-20 C, 70 ppm", k1, "corners_min"),
                      g("g2", "-20 C, 70 ppm", k2, "sides_min"), g("g2", "-20 C, 70 ppm", k2, "corners_min"),
                      g("g2", "-20 C, 70 ppm", k3, "sides_min"), g("g2", "-20 C, 70 ppm", k3, "corners_min")))
    chg("gaps[g2_glass_lip].note", old, e2["note"], "temperature values verified at GF-2.0")
    e1 = entry(raw["gaps"], "g1_lip_sheet")
    old = e1["note"]
    cm = "cut-out -0.1/side, R nominal (R +0/-0.2 callout), lip +0.04"
    e1["note"] = ("20 C nominal (STEP, 0.32 behind the flush plane: sides %.3f, corner diagonal %.3f; 0.4175 as designed at the flush "
                  "plane). GF-2.0 over temperature (verified %s, nominal sides): +70 C frame / +50 C sheet %.3f (50 ppm) / %.3f (70 ppm); "
                  "-20 C %.3f (50 ppm) / %.3f (70 ppm). Tolerance case hot, 70 ppm, cut-out -0.1/side with R nominal and lip +0.04 (sides / "
                  "corner min; negative = the sheet edge touches the lip): %.3f / %.3f. As at GF-1.1 it can touch hot with 70 ppm WC" % (
                      g("g1", "20 C", "nominal", "sides_min"), g("g1", "20 C", "nominal", "diagonal"), DATE,
                      g("g1", hot50, "nominal", "sides_min"), g("g1", hot70, "nominal", "sides_min"),
                      g("g1", "-20 C, 50 ppm", "nominal", "sides_min"), g("g1", "-20 C, 70 ppm", "nominal", "sides_min"),
                      g("g1", hot70, cm, "sides_min"), g("g1", hot70, cm, "corners_min")))
    chg("gaps[g1_lip_sheet].note", old, e1["note"], "temperature values verified at GF-2.0")
    # ------------------------------------------------------------------ 6. checks (push / impact), bead note
    rows = calc["grillage"]["rows"]
    def w50(bottom, lp):
        return next(x["w_50N_mm"] for x in rows if x["bottom"] == bottom and x["glass_t"] == 3.0 and x["I_source"].startswith("measured") and x["load_point"] == lp)
    pc = raw["checks"]["push_50N_glass3.0_concept_estimate_mm"]
    old = pc["status"]
    lps = {"window centre": "window centre", "glass top edge, mid": "glass top edge, mid", "glass side edge, mid": "glass side edge, mid",
           "bottom border over the bend gap": "bottom border over the bend gap", "glass bottom edge, mid": "glass bottom edge, mid",
           "bottom edge over CTP tail (x 58)": "bottom edge over the CTP tail (x 58)"}
    pc["status"] = "checked %s with the section I measured on the STEP (tools/glassfront/verify/calc_gf.py) - still the concept grillage, not FEA" % DATE
    pc["verified_%s_measured_I" % DATE] = {"S4/R4 channel": {k: w50("channel", v) for k, v in lps.items()},
                                           "S4/R4 bridge-only bound": {k: w50("bridge", v) for k, v in lps.items()},
                                           "measured_I_mm4": {"top": calc["sections"]["mid-top (x 80)"]["I_mm4"],
                                                              "sides": calc["sections"]["mid-side left (y 60)"]["I_mm4"],
                                                              "bottom channel": calc["sections"]["bottom bridge CTP compartment x 60: channel (bridge + flange plate + bottom wall)"]["I_mm4"],
                                                              "bottom bridge only": calc["sections"]["bottom bridge CTP compartment x 60: bridge only (cut at the bottom-wall inner face y 147.7)"]["I_mm4"]}}
    chg("checks.push_50N_glass3.0_concept_estimate_mm", old, pc["status"], "verified with the measured section I (values added)")
    ic = raw["checks"]["impact_0p5J_SF_concept_estimate"]
    old = ic["status"]
    imp = calc["impact_0p5J"]
    ic["status"] = "checked %s with the measured section I (concept method, estimates; impact still to be tested)" % DATE
    ic["verified_%s_measured_I" % DATE] = {t: {"window_centre": imp["channel %s" % t]["window_centre"]["SF"],
                                                "bottom_border_whole_border_free": imp["channel %s" % t]["bend_gap_strip_whole_border_free"]["SF"],
                                                "bottom_border_strip_only": imp["channel %s" % t]["bend_gap_strip_only"]["SF"],
                                                "bridge_only_bound": [imp["bridge %s" % t]["window_centre"]["SF"], imp["bridge %s" % t]["bend_gap_strip_whole_border_free"]["SF"],
                                                                      imp["bridge %s" % t]["bend_gap_strip_only"]["SF"]]} for t in ("1.1", "2.0", "3.0", "4.0")}
    chg("checks.impact_0p5J_SF_concept_estimate", old, ic["status"], "verified with the measured section I (values added)")
    ad = entry(raw["bead"], "adhesive")
    old = ad["note"]
    sh = {s["case"]: s for s in calc["bead"]["shear"]}["bound + 0.3 % moisture, +70 C"]
    assert "bound case with moisture swelling about 0.68 at the thinnest bond line 0.73" in old
    ad["note"] = old.replace("bound case with moisture swelling about 0.68 at the thinnest bond line 0.73",
                             "bound case with moisture swelling about %.2f at the thinnest bond line 0.73 (GF-2.0 bead corner r %.1f; GF-1.1 0.68 at r 111.7)" % (
                                 sh["d_mm"], calc["bead"]["r_bead_corner_mm"]))
    chg("bead[adhesive].note", old, ad["note"], "GF-2.0 bead corner radius")
    # ------------------------------------------------------------------ 7. v2_superseded, carried-over loop notes
    vs = entry(raw["v2_superseded"], "Z_FRONT / flange / studs FH1-FH10 / pegs")
    old = vs["status"]
    assert "F1-F8" in old
    vs["status"] = old.replace("F1-F8", "F1-F4 (GF-2.0)")
    chg("v2_superseded[Z_FRONT / flange / studs FH1-FH10 / pegs].status", old, vs["status"], "S8 withdrawn")
    co = raw["carried_over_from_v2"]
    lc = entry(co, "loop_clr")
    old = lc["note"]
    lc["note"] = old + ("; GF-2.0 (%s): applies to the U-loops and the tail-pocket walls, divider rib, bottom wall and flange plate, NOT to the "
                        "bend zone (nose, pocket face, break) - see tail_clearance_criteria" % DATE)
    chg("carried_over_from_v2[loop_clr].note", old, lc["note"], "item 1: loop_clr scope")
    for nm, route in (("loop_tft_y1", "TFT"), ("loop_ctp_y1", "CTP")):
        e = entry(co, nm)
        old = e["note"]
        why = ("it drives tr_y1 = loop_tft_y1 + trough_R (147.70, the tail-pocket bottom face) in the Fusion parameter table" if route == "TFT"
               else "it is a user parameter of the Fusion table next to loop_tft_y1, which drives tr_y1")
        e["note"] = old + ("; value kept (v2 panel-model envelope; %s); the GF-2.0 bent-back route puts the %s loop bottom (outer surface) at "
                           "%.2f (tail_route.%s.loop_bottom_outer, verified %s)" % (why, route, G.raw["tail_route"][route]["loop_bottom_outer"],
                                                                                   route, DATE))
        chg("carried_over_from_v2[%s].note" % nm, old, e["note"], "GF-2.0 loop position recorded (value kept, frame-driving)")
    # ------------------------------------------------------------------ 8. logo zone
    lz = raw["logo_zone"]
    c = entry(lz, "logo_centre")
    h = float(entry(lz, "logo_h")["value"])
    y_lo, y_hi = G.PRINT[3] + 1.0, G.GLASS[3] - 2.5
    assert abs((y_hi - y_lo) - h) < 1e-6, (y_lo, y_hi, h)
    new_c = [c["value"][0], round((y_lo + y_hi) / 2, 2)]
    old = (list(c["value"]), c["note"])
    c["value"] = new_c
    c["note"] = ("zone centred between window y1 + 1.0 (%.2f) and glass y1 - 2.5 (%.2f): the 15-high zone is exactly 1.0 from the window and "
                 "2.5 from the glass edge (corrected %s; 118.74 left only 1.75 to the glass edge)" % (y_lo, y_hi, DATE))
    chg("logo_zone[logo_centre]", old, [new_c, c["note"]], "item 6: print artwork only (not in the frame)")
    # ------------------------------------------------------------------ 9. as_modelled_GF-2.0
    am = raw["as_modelled_GF-2.0"]
    old = am["pip_top_to_glass_mm"]
    am["pip_top_to_glass_mm"] = [0.5]
    am["pip_top_to_glass_note"] = ("pip tops Z -10.92 to the glass back Z_GLASS_BACK -11.42 = 0.50 (verified %s). The Fusion check's 0.52 "
                                   "is to the glass body; the 0.02 black print layer modelled on its back is 0.50 from the frame "
                                   "(Assembly report, frame vs 'Glass print')" % DATE)
    chg("as_modelled_GF-2.0.pip_top_to_glass_mm", old, am["pip_top_to_glass_mm"], "item 5")
    ce = fit["connector_entry"]
    tails = fit["tails"]["cases"]["nominal (params polylines)"]
    def opening(ref):
        b = ce[ref]["opening_probe"][2]
        return b.get("free_band_at_tail_Z") or (b.get("all_free_bands") or [None])[0]
    seat = 1.635
    for nm, n, ref in (("TFT tail GF-2.0 (bent back)", "TFT", "J10"), ("CTP tail GF-2.0 (bent back)", "CTP", "J11")):
        tc = am["tail_clearances_mm"][nm]
        old = tc.get("PCB")
        ob = opening(ref)
        T = G.raw["tail_route"][n]
        z_bot_centre = (ob[0] + ob[1]) / 2 - T["thickness"] / 2 if ob else None
        tc["PCB"] = {"to_PCB_body_model_top_1.55": round(tails[n]["pcb_body"]["min"], 3),
                     "to_component_seating_plane_%.3f" % seat: round(tails[n]["pcb_body"]["min"] - (seat - 1.55), 3),
                     "if_return_leg_at_connector_model_opening_centre": round(z_bot_centre - seat, 3) if ob else None,
                     "connector_model_opening_Z": ob, "connector_model_overlap_mm3": ce[ref]["overlap_my_tail_mm3"],
                     "note": "the former 0.0 was the overlap of the tail end with the %s connector model, a model artefact: the tail at "
                             "Z_return %.2f occupies Z %.2f..%.2f, the model's free opening is Z %.3f..%.3f (%.2f high); the DS1 panel model's "
                             "own tail bodies overlap the same connector model at GF-1.1 as well (%s mm3). Clearances above are to the "
                             "PCB body model top (1.55) and to the component seating plane (1.635, the connector model's underside). "
                             "Z_return has to come from the connector datasheet (verified %s)" % (
                                 ref, T["Z_return"], T["Z_return"] - T["thickness"] / 2, T["Z_return"] + T["thickness"] / 2, ob[0], ob[1],
                                 ob[1] - ob[0], " + ".join("%s %.3f" % (k.rsplit("_", 1)[0], v) for k, v in
                                                          ce[ref]["overlap_DS1_own_bodies_unmoved_GF11_mm3"].items()), DATE)}
        chg("as_modelled_GF-2.0.tail_clearances_mm.%s.PCB" % nm, old, tc["PCB"], "item 5")
    # ------------------------------------------------------------------ 10. to_be_reverified
    tbr = raw["to_be_reverified_at_GF-2.0"]
    thick = cad["mould"]["thick"]["max_sphere_dia"]
    res_txt = {
        "lands, bead_area": "bead_area %.1f (params %.1f), tape area %.1f (GF-1.1 7903.0); lands, bead-to-pocket and the 8 pips at the params "
                            "positions and levels (spec / fit check); strip lengths not measured separately" % (
                                calc["bead"]["area_mm2"], calc["bead"]["params_bead_area"], fit["tape"]["area_mm2"]),
        "fasteners.positions": "F1-F4 positions, slot axes, counterbores, tube coring and pads checked against the params (spec check); "
                               "nothing moulded at F5-F8; stud envelope and rivet / washer seats in fitcheck.json; the d_* clearances to the "
                               "board outline, ear holes, wire corridor and bosses were not re-measured",
        "checks.push_50N_*": "push / impact checked with the section I measured on the STEP (checks.*.verified_%s_measured_I, still the "
                             "concept grillage, not FEA); the chin case is gone" % DATE,
        "gaps over temperature": "GF-2.0 values in the gaps notes; the design document 7.4 tables are not updated by this",
        "as_modelled_GF-1.1 volume": "GF-2.0 frame volume %.3f cm3, max inscribed sphere dia %.2f; GF-2.0 verification %s: 111 PASS / 3 FAIL / "
                                     "56 INFO before these corrections (verify/out/summary.json); the GF-D01..D50 drawings are not part of it" % (
                                         summ["inputs"]["frame"]["volume_mm3"] / 1000.0, thick, DATE),
        "cad_rules[8]": "replaced by the GF-2.0 tail-pocket rule in cad_rules; nothing is moulded at F5-F8 (checked on the STEP)",
        "tail checks:": "GF-2.0 tails rebuilt from tail_route; criteria in tail_clearance_criteria; the split model is not used",
        "the verification toolchain": "toolchain reads the GF-2.0 file (F1-F4, bridge, tails, bend zone)",
        "plan_points.chin_border": "chin gone (border 18.5 on all sides); logo zone 100 x 15 at logo_centre y %.2f (1.0 from the window, "
                                   "2.5 from the glass edge)" % new_c[1],
    }
    partial = ("lands, bead_area", "fasteners.positions", "gaps over temperature", "as_modelled_GF-1.1 volume")
    new_tbr = []
    for t in tbr:
        k = next((k for k in res_txt if t.startswith(k)), None)
        if k:
            new_tbr.append("%s: %s -> %s" % (vstamp.replace("VERIFIED", "VERIFIED IN PART") if k in partial else vstamp, t, res_txt[k]))
        else:
            new_tbr.append(t)
    chg("to_be_reverified_at_GF-2.0", list(tbr), new_tbr, "entries verified by the independent verification marked")
    raw["to_be_reverified_at_GF-2.0"] = new_tbr
    # ------------------------------------------------------------------ 11. change log entry
    raw["change_log"][KEY] = {
        "date": DATE, "by": "independent verification agent (tools/glassfront/verify/params_gf20_post_verification_fix.py)",
        "summary": "notes, criteria and check results corrected after the independent verification of the GF-2.0 frame STEP (sha256 %s); "
                   "no geometry-driving value changed except the logo-zone centre (print artwork only, not in the frame); revision stays "
                   "GF-2.0; new blocks open_findings and tail_clearance_criteria; R0.5 shelf-end rounds (already in the STEP) listed in "
                   "cad_rules" % step_sha,
        "params_sha256_before": sha_old, "changes": changes}
    after = raw
    # ------------------------------------------------------------------ numeric diff
    a, b = numeric_leaves(before), numeric_leaves(after)
    diff = {"changed": {k: [a[k], b[k]] for k in sorted(set(a) & set(b)) if a[k] != b[k]},
            "removed": {k: a[k] for k in sorted(set(a) - set(b))},
            "added": {k: b[k] for k in sorted(set(b) - set(a))},
            "count_before": len(a), "count_after": len(b)}
    print("numeric leaves before %d after %d; changed %d, removed %d, added %d" % (len(a), len(b), len(diff["changed"]), len(diff["removed"]), len(diff["added"])))
    for k, v in diff["changed"].items():
        print("  CHANGED %s: %s -> %s" % (k, v[0], v[1]))
    for k, v in diff["removed"].items():
        print("  REMOVED %s: %s" % (k, v))
    blocks = {}
    for k in diff["added"]:
        bk = k.split(".")[0] if not k.startswith("checks.") else ".".join(k.split(".")[:2])
        blocks[bk] = blocks.get(bk, 0) + 1
    print("  ADDED numeric leaves by block:", blocks)
    for k, v in diff["added"].items():
        if k.startswith("as_modelled"):
            print("  ADDED %s: %s" % (k, v))
    if dry:
        os.makedirs(C.TMP, exist_ok=True)
        pv = os.path.join(C.TMP, "params_fix_preview.json")
        json.dump({k: raw[k] for k in ("open_findings", "tail_clearance_criteria")} | {"changes": changes}, open(pv, "w"), indent=1)
        print("dry run - nothing written to the master; preview", pv)
        return 0
    if not os.path.exists(BACKUP):
        shutil.copyfile(PARAMS, BACKUP)
    write_master(after, PARAMS)
    sha_new = sha(PARAMS)
    diff["params_sha256_before"], diff["params_sha256_after"] = sha_old, sha_new
    C.dump(diff, DIFF)
    # ------------------------------------------------------------------ errata for the CAD reports
    frep = json.load(open(os.path.join(C.GF_DIR, "Rev3.0_GlassFront_Frame_report.json"), encoding="utf8"))
    arep = json.load(open(os.path.join(C.GF_DIR, "Rev3.0_GlassFront_Assembly_report.json"), encoding="utf8"))
    fam = frep["as_modelled"] if "as_modelled" in frep else {}
    ss = fit["stud_seat"]
    k58 = next(k for k in ss if k.startswith("dia 5.8") and "slot limits" in k)
    errata = {
        "about": "Errata to Rev3.0_GlassFront_Frame_report.json and Rev3.0_GlassFront_Assembly_report.json (GF-2.0, Fusion document version 18): "
                 "statements corrected by the independent verification %s (tools/glassfront/verify). The reports themselves are not edited." % DATE,
        "frame_step_sha256": step_sha,
        "params_sha256_quoted_in_the_reports": frep.get("master_params", {}).get("sha256"),
        "params_sha256_before_corrections": sha_old, "params_sha256_after_corrections": sha_new,
        "params_change": "change_log.%s (notes, criteria, check results; logo-zone centre; no frame-driving value changed)" % KEY,
        "items": [
            {"report": "Frame_report", "where": "sharp_inside_corners[5]",
             "report_value": next((x for x in frep.get("sharp_inside_corners", []) if "shelf end" in x), None),
             "verified": "the two inside corners shelf end (y 119.0) x tail-pocket side walls (x 38.9 / 167.7) carry R0.5 vertical rounds between "
                         "Z_SEAT and Z_SHELF_BACK in the GF-2.0 STEP (GF-1.1: sharp); 0.29 mm3; now listed in cad_rules",
             "source": "verify/out/cadcheck.json (carryover_vs_GF11.regions)"},
            {"report": "Frame_report", "where": "moulding_notes.slot_shut_off",
             "report_value": frep.get("moulding_notes", {}).get("slot_shut_off"),
             "verified": "parting on the bridge side at the break top (y %.3f, Z %.2f) and on the front side at the shelf corner (y %.2f, Z %.2f): "
                         "the shut-off rises %.2f over %.2f; buildable as an A ledge %.1f x %.1f plus a telescopic face along y 119.0 (>= 3 deg), "
                         "steel B %.0f / A %.0f deg; see cad_rules" % (pb[0], pb[1], pf[0], pf[1], so_b["rise_mm"], so_b["run_mm"], so_b["run_mm"],
                                                                     G.land_break, so_b[k_st]["B_steel_at_PB_deg"], so_b[k_st]["A_steel_at_PB_deg"]),
             "source": "verify/out/cadcheck.json (mould.bridge.shut_off)"},
            {"report": "Assembly_report", "where": "checks.3_flush_and_gaps.pips_to_glass[*].to_glass_mm",
             "report_value": 0.52, "verified": 0.50, "note": "Z_PIP_TOP -10.92 to Z_GLASS_BACK -11.42",
             "source": "verify/out/fitcheck.json (row 'pip tops -> glass back')"},
            {"report": "Frame/Assembly reports, params as_modelled_GF-2.0", "where": "tail_clearances_mm.*.PCB",
             "report_value": 0.0,
             "verified": {n: {"to_PCB_body_model": round(tails[n]["pcb_body"]["min"], 3),
                              "to_component_seating_plane": round(tails[n]["pcb_body"]["min"] - (seat - 1.55), 3)} for n in ("TFT", "CTP")},
             "note": "0.0 is the overlap of the tail end with the J10 / J11 models (%.3f / %.3f mm3), a model artefact that also exists at GF-1.1 "
                     "with the DS1 model's own tail bodies (%s / %s mm3)" % (ce["J10"]["overlap_my_tail_mm3"], ce["J11"]["overlap_my_tail_mm3"],
                                                                         ce["J10"]["overlap_DS1_own_bodies_unmoved_GF11_mm3"], ce["J11"]["overlap_DS1_own_bodies_unmoved_GF11_mm3"]),
             "source": "verify/out/fitcheck.json (tails.cases.nominal, connector_entry)"},
            {"report": "Assembly_report (and params as_modelled_GF-2.0.tail_clearances_mm.*.frame_by_class)",
             "where": "checks.5_tails.per_tail.*.frame_by_class",
             "report_value": {n: {k: v["d_mm"] for k, v in arep["checks"]["5_tails"]["per_tail"]["%s tail GF-2.0 (bent back)" % n]["frame_by_class"].items()}
                              for n in ("TFT", "CTP")},
             "verified": {n: {k: v["min"] for k, v in tails[n]["frame_by_class"].items()} for n in ("TFT", "CTP")},
             "note": "the overall minima agree (TFT 1.524, CTP 0.946, both to the R1.5 nose). The grouping differs: the report's 'bridge pocket "
                     "face / land break' value is measured to the break top edge (y 122.005, Z -10.12), i.e. the break alone - the flat pocket "
                     "face is closer (TFT 1.851, CTP 1.055); its 'flange plate (pocket floor)' TFT 5.17 is measured to pip P4 on the land "
                     "(Z -10.42), the flange plate itself is 4.67; its 'bridge floor (land-plate back)' 2.671 / 2.672 equals the step face "
                     "y 130.89 here, the land-plate back is 2.385 / 2.219. Under the GF-2.0 criteria (tail_clearance_criteria) every class "
                     "outside the bend zone is >= 1.5 nominal",
             "source": "verify/out/fitcheck.json (tails.cases['nominal (params polylines)'].*.frame_by_class)"},
            {"report": "params as_modelled_GF-2.0.fasteners (quoted by the reports)", "where": "flange_env_min_extreme",
             "report_value": {"params as_modelled_GF-2.0.fasteners.flange_env_min_extreme": 0.0544,
                              "Assembly_report checks.7_fasteners.F.F1.stud_extreme['+along (to glass)'].flange_env_d_mm":
                                  arep["checks"]["7_fasteners"]["F"]["F1"]["stud_extreme"]["+along (to glass)"]["flange_env_d_mm"]},
             "verified": {"wall": ss[k58]["min"]["wall"], "floor_round": ss[k58]["min"]["floor round"], "floor": ss[k58]["min"]["floor"],
                          "shank_to_frame": ss[k58]["min"]["any"]},
             "note": "envelope dia 5.8 x 1.4 with the shank at the slot limits (7 positions per stud): the extreme is at F3, end + across "
                     "(floor round), not at F1 along; all > 0, no overlap",
             "source": "verify/out/fitcheck.json (stud_seat)"}],
        "written_by": "tools/glassfront/verify/params_gf20_post_verification_fix.py", "date": DATE}
    json.dump(errata, open(ERRATA, "w", encoding="utf8"), indent=1)
    print("params sha256 %s -> %s" % (sha_old, sha_new))
    print("errata", ERRATA)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
