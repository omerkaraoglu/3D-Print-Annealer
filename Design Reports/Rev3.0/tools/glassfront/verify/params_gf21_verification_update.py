"""GF-2.1 master params: the blocks owned by the independent verification, rewritten from the GF-2.1 verification run.

  <venv>\\Scripts\\python.exe -B params_gf21_verification_update.py            (writes the master + the numeric diff)
  <venv>\\Scripts\\python.exe -B params_gf21_verification_update.py --dry-run  (diff + preview only)

Input: the GF-2.1 master (sha256 PARAMS_SHA_IN, as written by the stage-5 Fusion agent) and the outputs of run_verify.py on
the GF-2.1 frame STEP (out/summary.json, fitcheck.json, calc.json, cadcheck.json; the script refuses outputs of another STEP
or another master). Nothing that drives the frame geometry is touched; the revision stays GF-2.1.

Rewritten (all numbers from the outputs, nothing typed in):
  * open_findings            GF-2.0 findings 1 / 2 re-judged at GF-2.1 against the unchanged rules (closed / open, margins);
  * tail_clearance_criteria  criteria unchanged; GF-2.1 results, the concept's full-worst-case intent judged, loop_clr results;
  * fold_test                one rule: gauge slot = g_bend, a 0.05-step feeler, 'tail outer surface within X of the panel
                             edge', budget and reserve, fail branch with the A1 land measured to the break edge (6.20);
  * checks (push / impact estimates, status), gaps g2 / g1 notes (temperature tables), bead adhesive note (shear at the
    GF-2.1 bead corner) - the estimates flagged 'to be re-verified at GF-2.1';
  * the bead -> break-edge notes flagged as CAD-side / derived (driving_parameters.land_break, plan_rectangles.pocket, and
    lands['bottom over the tail span'] which states the same numbers), in the wording the drawings toolchain parses;
  * to_be_reverified_at_GF-2.1: the items this verification covers marked;
  * change_log entry KEY.
Discipline: refuses a second run (change_log KEY), checks first that its writer reproduces the master byte for byte, keeps
the master as it was in out/params_before_GF21_verification_update.json, writes out/params_GF21_verification_numeric_diff.json.
concept/concept_calc.py is never imported or run.
"""
import json
import math
import os
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon as C
import tails_gf2 as TG
from params_gf20_post_verification_fix import sha, write_master, numeric_leaves, entry

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PARAMS = C.GF_PARAMS
PARAMS_SHA_IN = "91ed2723f0b3344d77a2cdbac692a876fcb2dfe3d0fdd72fe80a2617293a7724"
STEP_SHA = "d734683ac0c0058a863c4d079b511767ff84a41912745e2ebf592eb1e4e333d6"
BACKUP = os.path.join(OUT, "params_before_GF21_verification_update.json")
DIFF = os.path.join(OUT, "params_GF21_verification_numeric_diff.json")
DATE = "2026-11-16"
KEY = "independent_verification_GF-2.1_%s" % DATE
LANDS_KEY = "bottom over the tail span (x 38.9 .. 167.7)"
FEELER_STEP = 0.05


def r2(v):
    return round(float(v) + 1e-9, 2)


def main(argv):
    dry = "--dry-run" in argv
    raw = json.load(open(PARAMS, encoding="utf8"))
    if KEY in raw.get("change_log", {}):
        print("already applied (change_log has %s) - restore %s first to re-run" % (KEY, BACKUP))
        return 1
    sha_old = sha(PARAMS)
    assert sha_old == PARAMS_SHA_IN, "the master is not the GF-2.1 file this update was written for (%s)" % sha_old
    probe = os.path.join(OUT, "_params_format_probe.json")
    write_master(raw, probe)
    same = open(probe, "rb").read() == open(PARAMS, "rb").read()
    os.remove(probe)
    assert same, "write_master does not reproduce the master format - nothing written"
    before = json.loads(json.dumps(raw))
    G = C.GF(PARAMS)
    summ = json.load(open(os.path.join(OUT, "summary.json")))
    fit = json.load(open(os.path.join(OUT, "fitcheck.json")))
    calc = json.load(open(os.path.join(OUT, "calc.json")))
    cad = json.load(open(os.path.join(OUT, "cadcheck.json")))
    assert summ["inputs"]["frame"]["sha256"] == STEP_SHA == C.file_id(C.GF_STEP)["sha256"], "outputs / STEP mismatch"
    assert summ["inputs"]["params"]["sha256"] == sha_old, "outputs were made with another master"
    rev = str(G.revision).split(" ")[0]
    assert rev == "GF-2.1"
    stamp = "VERIFIED %s (independent verification GF-2.1, tools/glassfront/verify, frame STEP sha256 %s)" % (DATE, STEP_SHA[:16])
    counts = summ["counts"]
    changes = []

    def chg(path, old, new, why):
        changes.append({"path": path, "old": old, "new": new, "reason": why})

    # ================================================================ numbers from the outputs
    bz = fit["tails"]["bend_zone"]                         # per tail: nominal / RSS / WC / WC_panel_only / WC_print_0.1
    cases = fit["tails"]["cases"]
    bc = TG.bend_zone_criterion(G)
    k_wc = [c for c in cases if c.startswith("bend-zone WC: ")]
    def bmin(case, n):
        fb = cases[case][n]["frame_by_class"]
        return min(fb[k]["min"] for k in TG.BEND_KEYS if k in fb)
    wc_sides = {n: {c.split("exit Z ")[-1].split(",")[0]: round(bmin(c, n), 4) for c in k_wc} for n in ("TFT", "CTP")}
    nom = cases["nominal (params polylines)"]
    loop = {n: min((v["min"], k) for k, v in nom[n]["frame_by_class"].items() if k not in TG.BEND_KEYS) for n in ("TFT", "CTP")}
    bzc = calc["bend_zone_criterion"]
    gb = bzc["g_bend_budget"]
    need = bzc["g_bend_needed_for_concept_0.45_at_WC"]
    slope = {n: need[n]["slope_per_mm"] for n in need}
    lp = fit["bead_to_break_land_plane"]                   # x -> bead_to_break_edge_on_land_plane
    b_plane = min(v["bead_to_break_edge_on_land_plane"] for v in lp.values())
    b_probe = min(fit["bead_to_pocket"]["bottom over the bridge, CTP x 60"], fit["bead_to_pocket"]["bottom over the bridge, TFT x 130"])
    b_face = min(fit["bead_to_pocket_plane_bridge"])
    bpm = float(G.bead_pocket_min)
    bezel = G.PANEL[3] - G.PRINT[3]
    land_rule = G.bead_edge + G.bead_w + bpm + G.land_break   # A1 measured to the break edge on the land plane
    land_b = next(x for x in raw["lands"] if x["name"] == LANDS_KEY)["value"]
    tcc = raw["tail_clearance_criteria"]["bend_zone"]
    rss, wcp = bc["rss"], bc["wc"]
    clr = bc["min_at_RSS"]
    intent = 0.45
    ctp_wc = bz["CTP"]["WC"]
    worst_tail = min(("TFT", "CTP"), key=lambda n: bz[n]["WC"])
    # ================================================================ 1. open findings
    of_old = raw["open_findings"]
    f1_closed = min(bz[n]["WC"] for n in bz) >= intent - 1e-4
    f2_closed = b_plane >= bpm - 1e-4 and b_probe >= bpm - 1e-4
    f1 = {"status": ("CLOSED at GF-2.1 (border 19.0, g_bend 3.23)" if f1_closed else "OPEN at GF-2.1") +
                    " - judged %s by the independent verification on frame STEP sha256 %s" % (DATE, STEP_SHA[:16]),
          "rule": "concept intent >= %.2f tail -> bend zone (R1.5 nose, pocket face, land break) at the full worst case (panel +%.2f, "
                  "exit Z +-%.1f, tail %.2f); the params criterion (tail_clearance_criteria.bend_zone) is >= %.2f at the RSS position and "
                  "> 0 at the worst case" % (intent, wcp, bc["exit_Z_tol"], G.tail_t + bc["tail_t_tol"], clr),
          "measured_GF-2.1_mm": {n: {"nominal": bz[n]["nominal"], "RSS": bz[n]["RSS"], "panel_WC_only": bz[n]["WC_panel_only"],
                                     "full_WC": bz[n]["WC"], "full_WC_by_exit_side": wc_sides[n], "full_WC_print_to_edge_0.1": bz[n]["WC_print_0.1"],
                                     "closest_feature": bz[n]["feature"]} for n in ("TFT", "CTP")},
          "result": "%s full worst case %.4f vs %.2f: margin %+.4f (%s; exit Z at its lower limit -%.1f governs)%s; TFT %.3f (margin %+.3f)" % (
              worst_tail, bz[worst_tail]["WC"], intent, bz[worst_tail]["WC"] - intent, "PASS" if f1_closed else "FAIL", bc["exit_Z_tol"],
              ("; THIN: the margin equals %.3f mm of g_bend at the measured slope %.2f per mm (g_bend %.3f would give exactly %.2f), and "
               "a tail %.3f larger than assumed (straight + radius + thickness) uses it up; measurement resolution about +-0.001 (tail "
               "polyline chords)" % ((bz[worst_tail]["WC"] - intent) / slope[worst_tail], slope[worst_tail],
                                     need[worst_tail]["g_bend_for_0.45_at_WC_all_contributors"], intent,
                                     (bz[worst_tail]["WC"] - intent) / slope[worst_tail])
               if 0 <= bz[worst_tail]["WC"] - intent < 0.05 else ""),
              bz["TFT"]["WC"], bz["TFT"]["WC"] - intent),
          "g_bend_at_exactly_0.45_full_WC": need[worst_tail]["g_bend_for_0.45_at_WC_all_contributors"],
          "GF-2.0": {"measured_mm": of_old["1_bend_zone_clearance_worst_case"]["measured_mm"],
                     "status": of_old["1_bend_zone_clearance_worst_case"]["status"]},
          "source": "tools/glassfront/verify/out/fitcheck.json (tails.bend_zone, tails.cases), calc.json (bend_zone_criterion)"}
    f2 = {"status": ("CLOSED at GF-2.1 (border 19.0, g_bend 3.23)" if f2_closed else "OPEN at GF-2.1") +
                    " - judged %s by the independent verification on frame STEP sha256 %s" % (DATE, STEP_SHA[:16]),
          "rule": "A1 bead_pocket_min %.1f: bead inner edge -> the edge of the %.1f x 45 land break (where the flat land ends)" % (bpm, G.land_break),
          "measured_GF-2.1_mm": {"on_the_land_plane_x60_x130": [v["bead_to_break_edge_on_land_plane"] for v in lp.values()],
                                 "at_Z_LAND+0.01_x60_x130": [fit["bead_to_pocket"]["bottom over the bridge, CTP x 60"],
                                                             fit["bead_to_pocket"]["bottom over the bridge, TFT x 130"]],
                                 "to_the_pocket_face_plane_x60_x130": [round(v, 4) for v in fit["bead_to_pocket_plane_bridge"]],
                                 "break_edge_y_on_land_plane": [v["break_edge_y_on_land_plane"] for v in lp.values()],
                                 "break_face_slope_dy_dz": [v["break_slope_dy_per_dz"] for v in lp.values()]},
          "result": "%.3f on the land plane (%.3f at Z_LAND + 0.01) vs %.1f: margin %+.3f (%s); %.3f to the pocket-face plane" % (
              b_plane, b_probe, bpm, b_plane - bpm, "PASS" if f2_closed else "FAIL", b_face),
          "GF-2.0": {"at_Z_LAND+0.01": of_old["2_bead_to_land_break"]["finding"].split(" from the edge")[0].split()[-1],
                     "status": of_old["2_bead_to_land_break"]["status"]},
          "source": "tools/glassfront/verify/out/fitcheck.json (bead_to_break_land_plane, bead_to_pocket, bead_to_pocket_plane_bridge)"}
    new_of = {"about": "findings of the independent verification. GF-2.0 findings 1 and 2 (verification 2026-11-16 on frame STEP sha256 "
                       "7831768c...) re-judged at GF-2.1 against the unchanged rules: GF-2.1 verification %s on frame STEP sha256 %s, "
                       "%d PASS / %d FAIL / %d INFO (tools/glassfront/verify/out/summary.json)" % (
                           DATE, STEP_SHA[:16], counts["PASS"], counts["FAIL"], counts["INFO"]),
              "1_bend_zone_clearance_worst_case": f1, "2_bead_to_land_break": f2}
    fails = [r for r in summ["table"] if r["verdict"] == "FAIL"]
    new_of["new_at_GF-2.1"] = ("none: no FAIL in the GF-2.1 verification" if not fails else
                               ["%s %s: %s (required %s)" % (r["id"], r["check"], r["measured"], r["required"]) for r in fails])
    chg("open_findings", "GF-2.0 block (+ status_GF-2.1 note)", "rewritten for GF-2.1", "findings re-judged at GF-2.1")
    raw["open_findings"] = new_of
    # ================================================================ 2. tail clearance criteria
    t_old = raw["tail_clearance_criteria"]
    t_new = {"about": "criteria for the FPC tails (set 2026-11-16, unchanged at GF-2.1): loop_clr (carried over from v1/v2) applies to "
                      "the loops and the tail pocket, not to the bend zone, which the tail passes at less than 1.5 by design and is laid "
                      "over after cure",
             "loop_clr": dict(t_old["loop_clr"], **{"results_GF-2.1_nominal_mm": {n: {"min": loop[n][0], "feature": loop[n][1]} for n in loop},
                                                    "verdict_GF-2.1": "met (TFT %.3f, CTP %.3f >= %.1f)" % (loop["TFT"][0], loop["CTP"][0],
                                                                                                         t_old["loop_clr"]["value_mm"])}),
             "bend_zone": {k: v for k, v in tcc.items() if not k.startswith(("results_", "verdict_"))}}
    bzn = t_new["bend_zone"]
    bzn["features"] = ["bridge nose R%.1f" % G.bend_nose_R, "bridge pocket face y %.2f (+ rib front)" % G.BRIDGE[2],
                       "land break %.1f x 45" % G.land_break]
    bzn["concept_intent"] = (">= %.2f at the full worst case (concept_gf2.md 2.1 clearance held at the worst case; not a params criterion "
                             "at GF-2.0, judged as GF-2.0 open finding 1)" % intent)
    bzn["results_GF-2.1"] = {n: {"nominal": bz[n]["nominal"], "at_RSS": bz[n]["RSS"], "at_panel_WC_only": bz[n]["WC_panel_only"],
                                 "at_WC": bz[n]["WC"], "at_WC_print_to_edge_0.1": bz[n]["WC_print_0.1"]} for n in ("TFT", "CTP")}
    ok_rss = all(bz[n]["RSS"] >= clr - 1e-4 for n in bz)
    ok_wc = all(bz[n]["WC"] > bc["min_at_WC"] for n in bz)
    bzn["verdict_GF-2.1"] = "criterion %s (TFT %.3f / %.3f, CTP %.3f / %.3f at RSS / WC); concept intent %s (CTP full WC %.3f, margin %+.3f)" % (
        "met" if ok_rss and ok_wc else "NOT met", bz["TFT"]["RSS"], bz["TFT"]["WC"], bz["CTP"]["RSS"], bz["CTP"]["WC"],
        "met" if f1_closed else "NOT met", ctp_wc, ctp_wc - intent)
    bzn["results_GF-2.0"] = {k: v for k, v in tcc.items() if k.startswith("results_")}
    chg("tail_clearance_criteria", "GF-2.0 results (+ status_GF-2.1 note)", "GF-2.1 results, verdicts", "re-evaluated at GF-2.1")
    raw["tail_clearance_criteria"] = t_new
    # ================================================================ 3. fold test (one rule)
    slot = float(G.g_bend)
    l0, rin, tt = G.tail_straight_l0, G.tail_R_in_min, G.tail_t
    d_assumed = l0 + rin + tt
    d_budget = slot - clr - rss                             # largest tail extent the budget allows in this slot
    f_exact = slot - d_budget                               # = clearance + RSS position term
    feeler = math.ceil(f_exact / FEELER_STEP - 1e-9) * FEELER_STEP
    X = slot - feeler
    assert d_assumed <= X + 1e-9, "the assumed tail would fail the gauge"
    g_lim = G.border - bezel - land_rule                    # border holds while the needed gap <= this
    need_X = X + clr + rss
    sl_ctp = slope["CTP"]
    d_intent = d_assumed + (ctp_wc - intent) / sl_ctp       # tail extent at which the CTP full-WC clearance reaches the intent
    d_rss3d = d_assumed + min((bz[n]["RSS"] - clr) / slope[n] for n in bz)
    d_wc3d = d_assumed + min(bz[n]["WC"] / slope[n] for n in bz)
    fold = {
        "about": "real-panel fold test on the GF-D21 tail fold gauge (concept_gf2.md 2.4): the pass line read by the drawings and the "
                 "design document. GF-2.1 values (verified %s): the gauge slot is g_bend, so the GF-2.0 gauge (3.00) is not valid for "
                 "GF-2.1" % DATE,
        "gauge_slot_mm": round(slot, 2),
        "gauge_slot_note": "panel edge face -> gauge face = g_bend (%.2f at GF-2.1), R%.1f nose as the bridge" % (slot, G.bend_nose_R),
        "feeler_mm": round(feeler, 2),
        "tail_outer_surface_limit_from_panel_edge_mm": round(X, 2),
        "exact_feeler_for_the_budget_mm": round(f_exact, 3),
        "needed_gap_at_the_limit_mm": round(need_X, 3),
        "reserve_to_g_bend_mm": round(slot - need_X, 3),
        "border_limit_needed_gap_mm": round(g_lim, 3),
        "A1_land_to_the_break_edge_mm": round(land_rule, 2),
        "rule": "panel held at its nominal position by the gauge, each tail folded over the gauge nose: a %.2f feeler passes between the "
                "tail's outer surface and the gauge face / nose over the whole tail width, i.e. the tail's outer surface lies within %.2f of "
                "the panel edge; record the largest feeler that passes (0.05 steps)" % (feeler, X),
        "basis": "budget (g_bend note): needed gap = tail extent + clearance %.2f + panel position %.2f RSS; with the gap = the slot %.2f the "
                 "tail may extend %.3f, i.e. feeler %.3f exactly; %.2f is the next 0.05-step leaf at or above it (safe side)" % (
                     clr, rss, slot, d_budget, f_exact, feeler),
        "assumed_tail_mm": round(d_assumed, 2),
        "assumed_tail_note": "straight tail_straight_l0 %.1f + inner radius tail_R_in_min %.1f + thickness tail_t %.2f = %.2f -> passes with "
                             "%.2f to spare (gap %.2f at the assumed tail)" % (l0, rin, tt, d_assumed, X - d_assumed, slot - d_assumed),
        "pass": "border %.1f holds by the budget: needed gap <= %.2f + %.2f + %.2f = %.3f <= g_bend %.2f (reserve %.3f) <= limit %.2f (border "
                "%.1f - bezel %.2f - land %.2f; reserve %.3f). Measured in 3D (GF-2.1) a tail up to %.2f keeps >= %.2f at the RSS position "
                "and up to %.2f keeps > 0 at the full worst case (slopes TFT %.2f / CTP %.2f per mm); the concept's full-worst-case %.2f "
                "holds only up to %.3f (CTP margin %.3f at GF-2.1), so passing does NOT guarantee that intent - no 0.05-step feeler can, "
                "because the assumed tail (%.2f) must pass" % (
                    G.border, X, clr, rss, need_X, slot, slot - need_X, g_lim, G.border, bezel, land_rule, g_lim - need_X,
                    d_rss3d, clr, d_wc3d, slope["TFT"], slope["CTP"], intent, d_intent, ctp_wc - intent, d_assumed),
        "fail": "measured tail extent d = gauge slot %.2f - largest passing feeler; needed gap g = d + %.2f + %.2f; border = bezel %.2f + g + "
                "land %.2f, where the land is bead_edge %.1f + bead_w %.1f + bead_pocket_min %.1f measured to the break edge + land_break "
                "%.1f (A1 is measured to the break edge on the land plane). Border %.1f holds while g <= %.2f (g_bend raised to g); "
                "above that border = %.2f + g + %.2f (e.g. 19.5 covers g <= %.2f)" % (
                    slot, clr, rss, bezel, land_rule, G.bead_edge, G.bead_w, bpm, G.land_break, G.border, g_lim, bezel, land_rule,
                    19.5 - bezel - land_rule),
        "land_note": "GF-2.0 used a land of %.1f (A1 to the pocket face); the rule is measured to the break edge, so the land is %.2f (%.1f + "
                     "the %.1f break): at GF-2.0 that limit was %.2f < the modelled 3.00, consistent with the GF-2.0 bead FAIL (0.79 on the "
                     "land plane)" % (land_rule - G.land_break, land_rule, land_rule - G.land_break, G.land_break,
                                      18.5 - bezel - land_rule),
        "references": "driving_parameters.g_bend note (budget), tail_clearance_criteria.bend_zone, open_findings 1",
        "date": DATE}
    chg("fold_test", "GF-2.0 rule (slot 3.00, feeler 0.70, 2.30)", "GF-2.1 rule (slot %.2f, feeler %.2f, %.2f)" % (slot, feeler, X),
        "re-derived at GF-2.1 from the budget and the measured clearances")
    raw["fold_test"] = fold
    # ================================================================ 4. estimates flagged 'to be re-verified at GF-2.1'
    rows = calc["grillage"]["rows"]
    def w50(bottom, lp_):
        return next(x["w_50N_mm"] for x in rows if x["bottom"] == bottom and x["glass_t"] == 3.0 and x["I_source"].startswith("measured")
                    and x["load_point"] == lp_)
    lps = {"window centre": "window centre", "glass top edge, mid": "glass top edge, mid", "glass side edge, mid": "glass side edge, mid",
           "bottom border over the bend gap": "bottom border over the bend gap", "glass bottom edge, mid": "glass bottom edge, mid",
           "bottom edge over CTP tail (x 58)": "bottom edge over the CTP tail (x 58)"}
    ck = raw["checks"]
    pc = ck["push_50N_glass3.0_concept_estimate_mm"]
    old = pc["status"]
    pc["status"] = ("concept values at border 18.5; checked at GF-2.1 (%s) with the section I measured on the GF-2.1 STEP -> "
                    "verified_GF-2.1_measured_I (still the concept grillage, not FEA)" % DATE)
    gmax = {t: max(x["glass_250N_MPa"] for x in rows if x["glass_t"] == t and x["I_source"].startswith("measured") and x["bottom"] == "channel")
            for t in sorted({x["glass_t"] for x in rows})}
    pc["verified_GF-2.1_measured_I"] = {
        "S4/R4 channel": {k: w50("channel", v) for k, v in lps.items()},
        "S4/R4 bridge-only bound": {k: w50("bridge", v) for k, v in lps.items()},
        "glass_250N_max_MPa_channel": {"%.1f" % t: v for t, v in gmax.items()},
        "measured_I_mm4": {"top": calc["sections"]["mid-top (x 80)"]["I_mm4"], "sides": calc["sections"]["mid-side left (y 60)"]["I_mm4"],
                           "bottom channel": calc["sections"]["bottom bridge CTP compartment x 60: channel (bridge + flange plate + bottom wall)"]["I_mm4"],
                           "bottom bridge only": calc["sections"]["bottom bridge CTP compartment x 60: bridge only (cut at the bottom-wall inner face y %.1f)"
                                                                  % G.TAIL[3]]["I_mm4"]}}
    chg("checks.push_50N_glass3.0_concept_estimate_mm", old, pc["status"], "GF-2.1 values added")
    ic = ck["impact_0p5J_SF_concept_estimate"]
    old = ic["status"]
    imp = calc["impact_0p5J"]
    ic["status"] = "concept values at border 18.5; checked at GF-2.1 (%s) with the measured section I -> verified_GF-2.1_measured_I (estimates; impact still to be tested)" % DATE
    ic["verified_GF-2.1_measured_I"] = {t: {"window_centre": imp["channel %s" % t]["window_centre"]["SF"],
                                            "bottom_border_whole_border_free": imp["channel %s" % t]["bend_gap_strip_whole_border_free"]["SF"],
                                            "bottom_border_strip_only": imp["channel %s" % t]["bend_gap_strip_only"]["SF"],
                                            "bridge_only_bound": [imp["bridge %s" % t]["window_centre"]["SF"],
                                                                  imp["bridge %s" % t]["bend_gap_strip_whole_border_free"]["SF"],
                                                                  imp["bridge %s" % t]["bend_gap_strip_only"]["SF"]]}
                                        for t in ("1.1", "2.0", "3.0", "4.0")}
    chg("checks.impact_0p5J_SF_concept_estimate", old, ic["status"], "GF-2.1 values added")
    old = ck.get("status_GF-2.1")
    ck["status_GF-2.1"] = "push / impact estimates re-checked at GF-2.1 with the measured section I (%s): see verified_GF-2.1_measured_I" % stamp
    chg("checks.status_GF-2.1", old, ck["status_GF-2.1"], "verified")
    gt = calc["gaps_table"]
    def g(tag, t, case, k):
        return gt[tag][t][case][k]
    hot50, hot70 = "+70 C frame/glass, +50 C sheet, 50 ppm", "+70 C frame/glass, +50 C sheet, 70 ppm"
    k1 = "glass +0.1/side, R nominal (requested +-0.1, R +0.2/-0)"
    k2 = "glass +0.2/side, R nominal (R +0.2/-0 callout)"
    k3 = "glass +0.2/side and R -0.2 (size + radius tolerances)"
    e2 = entry(raw["gaps"], "g2_glass_lip")
    old = e2["note"]
    e2["note"] = ("20 C nominal (STEP, 0.32 behind the flush plane: sides %.3f, corner diagonal %.3f). GF-2.1 over temperature (verified "
                  "%s, nominal sides): -20 C %.3f (50 ppm) / %.3f (70 ppm); +70 C %.3f (50 ppm) / %.3f (70 ppm). Tolerance cases at -20 C, "
                  "70 ppm (sides / corner min; negative = the glass touches the lip): glass +0.1/side %.3f / %.3f; glass +0.2/side, R nominal "
                  "%.3f / %.3f; glass +0.2/side and R -0.2 %.3f / %.3f. It can touch at -20 C with 70 ppm WC (as GF-1.1 / GF-2.0)" % (
                      g("g2", "20 C", "nominal", "sides_min"), g("g2", "20 C", "nominal", "diagonal"), DATE,
                      g("g2", "-20 C, 50 ppm", "nominal", "sides_min"), g("g2", "-20 C, 70 ppm", "nominal", "sides_min"),
                      g("g2", hot50, "nominal", "sides_min"), g("g2", hot70, "nominal", "sides_min"),
                      g("g2", "-20 C, 70 ppm", k1, "sides_min"), g("g2", "-20 C, 70 ppm", k1, "corners_min"),
                      g("g2", "-20 C, 70 ppm", k2, "sides_min"), g("g2", "-20 C, 70 ppm", k2, "corners_min"),
                      g("g2", "-20 C, 70 ppm", k3, "sides_min"), g("g2", "-20 C, 70 ppm", k3, "corners_min")))
    chg("gaps[g2_glass_lip].note", old, e2["note"], "temperature values verified at GF-2.1")
    e1 = entry(raw["gaps"], "g1_lip_sheet")
    old = e1["note"]
    cm = "cut-out -0.1/side, R nominal (R +0/-0.2 callout), lip +0.04"
    e1["note"] = ("20 C nominal (STEP, 0.32 behind the flush plane: sides %.3f, corner diagonal %.3f; 0.4175 as designed at the flush "
                  "plane). GF-2.1 over temperature (verified %s, nominal sides): +70 C frame / +50 C sheet %.3f (50 ppm) / %.3f (70 ppm); "
                  "-20 C %.3f (50 ppm) / %.3f (70 ppm). Tolerance case hot, 70 ppm, cut-out -0.1/side with R nominal and lip +0.04 (sides / "
                  "corner min; negative = the sheet edge touches the lip): %.3f / %.3f. It can touch hot with 70 ppm WC (as GF-1.1 / GF-2.0)" % (
                      g("g1", "20 C", "nominal", "sides_min"), g("g1", "20 C", "nominal", "diagonal"), DATE,
                      g("g1", hot50, "nominal", "sides_min"), g("g1", hot70, "nominal", "sides_min"),
                      g("g1", "-20 C, 50 ppm", "nominal", "sides_min"), g("g1", "-20 C, 70 ppm", "nominal", "sides_min"),
                      g("g1", hot70, cm, "sides_min"), g("g1", hot70, cm, "corners_min")))
    chg("gaps[g1_lip_sheet].note", old, e1["note"], "temperature values verified at GF-2.1")
    ad = entry(raw["bead"], "adhesive")
    old = ad["note"]
    sh = {s["case"]: s for s in calc["bead"]["shear"]}["bound + 0.3 % moisture, +70 C"]
    import re
    m = re.search(r"bound case with moisture swelling about [\d.]+ at the thinnest bond line 0\.73 \(GF-2\.0 bead corner r [\d.]+; GF-1\.1 0\.68 at r 111\.7\)", old)
    assert m, old
    ad["note"] = old.replace(m.group(0), "bound case with moisture swelling about %.2f at the thinnest bond line 0.73 (GF-2.1 bead corner r %.1f; "
                                         "GF-2.0 %.2f at r %.1f; GF-1.1 0.68 at r 111.7)" % (
                                             sh["d_mm"], calc["bead"]["r_bead_corner_mm"],
                                             calc["previous_release"]["bead_shear_bound_moisture_d_mm"], calc["previous_release"]["r_bead_corner_mm"]))
    chg("bead[adhesive].note", old, ad["note"], "GF-2.1 bead corner radius")
    # ---- bead -> break edge notes (flagged CAD-side / derived), in the wording the drawings toolchain parses
    lpx = list(lp.values())[0]
    on_plane = lpx["bead_to_break_edge_on_land_plane"]
    flat = land_b - G.land_break
    d = entry(raw["driving_parameters"], "land_break")
    old = d["note"]
    d["note"] = ("GF-2.1: 45 deg break on the land front-inner edge (land x bridge pocket face) over the tail span, so the edge cannot snag "
                 "a tail when the frame is lowered in J2; the flat land then starts %.1f behind the pocket face (bead inner edge %.2f from "
                 "the break edge, measured where the land ends at Z_LAND + 0.01 as in the pocket note - %.2f on the land plane itself - and "
                 "%.2f from the pocket-face plane; >= bead_pocket_min %.1f, verified %s; GF-2.0: 0.80 / 0.79 / 1.09)" % (
                     G.land_break, b_probe, on_plane, b_face, bpm, DATE))
    chg("driving_parameters[land_break].note", old, d["note"], "CAD-side values replaced by the verified ones")
    ln = next(x for x in raw["lands"] if x["name"] == LANDS_KEY)
    old = ln["note"]
    ln["note"] = ("GF-2.1: bead_to_pocket %.2f is to the bridge pocket face y %.2f at Z_LAND; the land_break %.1f x 45 deg leaves %.2f of flat "
                  "land, bead inner edge %.2f from the break edge (measured where the land ends, Z_LAND + 0.01; %.2f on the land plane itself), "
                  "which meets the %.1f rule (A1; GF-2.0: 0.80, open_findings 2, closed at GF-2.1; verified %s)" % (
                      b_face, G.BRIDGE[2], G.land_break, flat, b_probe, on_plane, bpm, DATE))
    chg("lands[%s].note" % LANDS_KEY, old, ln["note"], "same CAD-side numbers as the land_break note, verified")
    bd = fit["bead_to_pocket"]
    r = entry(raw["plan_rectangles"], "pocket")
    old = r["note"]
    r["note"] = ("clearance pocket = panel + pocket_clr; defined at Z_SEAT with 1 deg draft (opening to the front): 0.10 larger per side at "
                 "the land (measured x0 19.119 at Z_LAND vs 19.22 here). The land widths and bead_to_pocket values in 'lands' apply at Z_SEAT. "
                 "Where the land ends (Z_LAND + 0.01) the bead-to-pocket margins are (GF-2.1, verified %s): abs left %.2f, abs right %.2f, "
                 "top %.2f, bottom outside the tail span %.2f; the smallest is over the bridge: %.2f to the edge of the %.1f x 45 land break "
                 "(%.2f to the pocket-face plane, which is defined at the land) - open_findings 2, closed at GF-2.1. GF-2.0: 5.61 / 8.37 / "
                 "7.53 / 3.19 and 0.80 / 1.09" % (DATE, bd["left"], bd["right"], bd["top"], bd["bottom outside the tail span x 24"],
                                                   b_probe, G.land_break, b_face))
    chg("plan_rectangles.pocket.note", old, r["note"], "derived values replaced by the verified ones")
    # ---- to_be_reverified_at_GF-2.1
    tbr = raw["to_be_reverified_at_GF-2.1"]
    res_txt = {
        "the independent verification": (stamp, "%d PASS / %d FAIL / %d INFO; open_findings 1 / 2 %s / %s; tail_clearance_criteria and "
                                                "fold_test rewritten (gauge slot %.2f, feeler %.2f)" % (
                                                    counts["PASS"], counts["FAIL"], counts["INFO"], "closed" if f1_closed else "OPEN",
                                                    "closed" if f2_closed else "OPEN", slot, feeler)),
        "concept push / impact estimates": (stamp, "checks.*.verified_GF-2.1_measured_I and the gaps notes (GF-2.1 temperature and "
                                                   "tolerance values); the design document tables are not updated by this"),
        "fasteners d_* values": (stamp.replace("VERIFIED", "VERIFIED IN PART"),
                                 "logo zone: logo_centre y %.2f gives 1.25 to the window and 2.75 to the glass edge for the 15-high zone "
                                 "(params arithmetic); F1-F4 positions, slots, counterbores, pads and stud / rivet / washer seats verified "
                                 "on the STEP; the d_* clearances to the board were not re-measured" % raw["logo_zone"][0]["value"][1])}
    old = list(tbr)
    new = []
    for t in tbr:
        k = next((k for k in res_txt if t.startswith(k)), None)
        new.append("%s: %s -> %s" % (res_txt[k][0], t, res_txt[k][1]) if k else t)
    raw["to_be_reverified_at_GF-2.1"] = new
    chg("to_be_reverified_at_GF-2.1", old, new, "items covered by the GF-2.1 verification marked")
    # ================================================================ change log
    raw["change_log"][KEY] = {
        "date": DATE, "by": "independent verification agent (tools/glassfront/verify/params_gf21_verification_update.py)",
        "summary": "GF-2.1 independent verification on frame STEP sha256 %s: %d PASS / %d FAIL / %d INFO. Rewritten: open_findings (1 %s, "
                   "2 %s), tail_clearance_criteria (GF-2.1 results), fold_test (slot %.2f, feeler %.2f, tail within %.2f), push / impact "
                   "estimates, g2 / g1 temperature notes, bead adhesive note, the bead -> break-edge notes (land_break, lands, pocket), "
                   "to_be_reverified_at_GF-2.1. No geometry value changed; revision stays GF-2.1" % (
                       STEP_SHA, counts["PASS"], counts["FAIL"], counts["INFO"], "closed" if f1_closed else "OPEN",
                       "closed" if f2_closed else "OPEN", slot, feeler, X),
        "params_sha256_before": sha_old, "changes": changes}
    # ================================================================ diff, write
    a, b = numeric_leaves(before), numeric_leaves(json.loads(json.dumps(raw)))
    diff = {"changed": {k: [a[k], b[k]] for k in sorted(set(a) & set(b)) if a[k] != b[k]},
            "removed": {k: a[k] for k in sorted(set(a) - set(b))},
            "added": {k: b[k] for k in sorted(set(b) - set(a))}, "count_before": len(a), "count_after": len(b)}
    print("numeric leaves before %d after %d; changed %d, removed %d, added %d" % (len(a), len(b), len(diff["changed"]),
                                                                                 len(diff["removed"]), len(diff["added"])))
    geo = [k for k in list(diff["changed"]) + list(diff["removed"]) if not k.startswith(("open_findings", "tail_clearance_criteria",
                                                                                         "fold_test", "checks.", "change_log"))]
    assert not geo, ("numeric values outside the owned blocks would change", geo)
    for k, v in diff["changed"].items():
        print("  CHANGED %s: %s -> %s" % (k, v[0], v[1]))
    for k, v in diff["removed"].items():
        print("  REMOVED %s: %s" % (k, v))
    print("fold_test:", json.dumps(fold, indent=1))
    if dry:
        os.makedirs(C.TMP, exist_ok=True)
        pv = os.path.join(C.TMP, "params_gf21_preview.json")
        json.dump({k: raw[k] for k in ("open_findings", "tail_clearance_criteria", "fold_test")} | {"changes": changes}, open(pv, "w"), indent=1)
        print("dry run - nothing written to the master; preview", pv)
        return 0
    if not os.path.exists(BACKUP):
        shutil.copyfile(PARAMS, BACKUP)
    write_master(raw, PARAMS)
    sha_new = sha(PARAMS)
    diff["params_sha256_before"], diff["params_sha256_after"] = sha_old, sha_new
    C.dump(diff, DIFF)
    print("params sha256 %s -> %s" % (sha_old, sha_new))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
