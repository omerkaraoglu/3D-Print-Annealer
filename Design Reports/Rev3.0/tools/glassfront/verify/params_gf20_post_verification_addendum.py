"""GF-2.0 master params: addendum to the post-verification corrections (lead decisions 2026-11-16, after the drawings and
the design document were regenerated from the corrected master). Notes and one new block only; no geometry value changes.

  <venv>\\Scripts\\python.exe -B params_gf20_post_verification_addendum.py            (writes the master, errata sha, diff)
  <venv>\\Scripts\\python.exe -B params_gf20_post_verification_addendum.py --dry-run  (diff + preview only)

The four points:
  1. land_break note and lands['bottom over the tail span ...'] note: bead -> break edge 0.80 (measured where the land ends,
     Z_LAND + 0.01, as the pocket note and open_findings 2), 1.09 to the pocket-face plane; the lands note no longer calls 1.09
     'the governing bead_to_pocket, >= bead_pocket_min' (to the face 1.09 passes, to the break edge 0.80 fails: open finding 2);
  2. open_findings 2: the border-19.0 fix quoted as the common fix of findings 1 and 2 (g_bend 3.23, land 6.26, bead to the
     break 1.06), land_break <= 0.09 kept as the alternative at border 18.5;
  3. to_be_reverified_at_GF-2.0: the drawings item marked done (GF-2.0 set regenerated and self-checked 2026-11-16);
  4. new block fold_test (GF-D21 pass line: gauge slot 3.00, feeler 0.70 = tail outer surface within 2.30 of the panel edge).
It refuses to run twice (change_log key), checks first that its writer reproduces the master byte for byte, keeps the
master as it was in out/params_before_post_verification_addendum.json, writes out/params_addendum_numeric_diff.json and adds
the new params sha256 to the errata file. concept/concept_calc.py is never imported or run.
"""
import json
import math
import os
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon as C
from params_gf20_post_verification_fix import sha, write_master, numeric_leaves, entry, ERRATA, KEY as KEY_FIX

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PARAMS = C.GF_PARAMS
BACKUP = os.path.join(OUT, "params_before_post_verification_addendum.json")
DIFF = os.path.join(OUT, "params_addendum_numeric_diff.json")
DATE = "2026-11-16"
KEY = "post_verification_addendum_%s" % DATE
LANDS_KEY = "bottom over the tail span (x 38.9 .. 167.7)"


def main(argv):
    dry = "--dry-run" in argv
    raw = json.load(open(PARAMS, encoding="utf8"))
    cl = raw.get("change_log", {})
    assert KEY_FIX in cl, "the post-verification fix must be applied first"
    if KEY in cl:
        print("already applied (change_log has %s) - restore %s first to re-run" % (KEY, BACKUP))
        return 1
    sha_old = sha(PARAMS)
    probe = os.path.join(OUT, "_params_format_probe.json")
    write_master(raw, probe)
    same = open(probe, "rb").read() == open(PARAMS, "rb").read()
    os.remove(probe)
    assert same, "write_master does not reproduce the master format - nothing written"
    before = json.loads(json.dumps(raw))
    G = C.GF(PARAMS)
    fit = json.load(open(os.path.join(OUT, "fitcheck.json")))
    step_sha = C.file_id(C.GF_STEP)["sha256"]
    assert step_sha.startswith("7831768c"), "the frame STEP changed"
    changes = []

    def chg(path, old, new, point):
        changes.append({"point": point, "path": path, "old": old, "new": new})

    # ---------------------------------------------------------------- numbers (from the params and the fit check)
    bd = fit["bead_to_pocket"]
    to_brk = bd["bottom over the bridge, CTP x 60"]                     # 0.800 at Z_LAND + 0.01
    to_face = fit["bead_to_pocket_plane_bridge"][0]                     # 1.090
    bead_in = G.bead_edge + G.bead_w                                   # 4.9 inside the glass edge
    land_b = next(x for x in raw["lands"] if x["name"] == LANDS_KEY)["value"]   # 5.99
    flat = land_b - G.land_break                                        # 5.69
    on_plane = land_b - bead_in - G.land_break                          # 0.79 exactly on the land plane
    assert abs(to_brk - 0.80) < 1e-3 and abs(to_face - 1.09) < 1e-3 and abs(on_plane - 0.79) < 1e-6, (to_brk, to_face, on_plane)
    bezel = G.PANEL[3] - G.PRINT[3]                                     # 9.51
    land_min = bead_in + G.bead_pocket_min                              # 5.9
    tc = raw["tail_clearance_criteria"]["bend_zone"]
    rss = tc["panel_position_RSS_mm"]                                   # 0.308
    clr = tc["clearance_min_at_RSS_mm"]                                 # 0.45
    g_lim = G.border - bezel - land_min                                 # 3.09
    # ---------------------------------------------------------------- 1. 0.79 -> 0.80 (measured), 1.09 to the face
    d = entry(raw["driving_parameters"], "land_break")
    old = d["note"]
    assert "(bead inner edge 0.79 from the break edge, 1.09 from the face)" in old
    d["note"] = old.replace("(bead inner edge 0.79 from the break edge, 1.09 from the face)",
                            "(bead inner edge %.2f from the break edge, measured where the land ends at Z_LAND + 0.01 as in the pocket "
                            "note - %.2f on the land plane itself - and %.2f from the pocket-face plane; the %.2f fails bead_pocket_min "
                            "%.1f: open_findings 2_bead_to_land_break)" % (to_brk, on_plane, to_face, to_brk, G.bead_pocket_min))
    chg("driving_parameters[land_break].note", old, d["note"], 1)
    ln = next(x for x in raw["lands"] if x["name"] == LANDS_KEY)
    old = ln["note"]
    assert "(the governing bead_to_pocket, >= bead_pocket_min 1.0)" in old and "bead inner edge 0.79 from the break edge" in old
    ln["note"] = ("GF-2.0: bead_to_pocket %.2f is to the bridge pocket face y 122.00 at Z_LAND (passes bead_pocket_min %.1f to the face "
                  "plane); the land_break 0.3 x 45 deg leaves %.2f of flat land, bead inner edge %.2f from the break edge (measured where "
                  "the land ends, Z_LAND + 0.01; %.2f on the land plane itself), which fails the %.1f rule - see "
                  "open_findings 2_bead_to_land_break" % (to_face, G.bead_pocket_min, flat, to_brk, on_plane, G.bead_pocket_min))
    assert ">= bead_pocket_min" not in ln["note"]
    chg("lands[%s].note" % LANDS_KEY, old, ln["note"], 1)
    # ---------------------------------------------------------------- 2. open finding 2: the common fix
    f2 = raw["open_findings"]["2_bead_to_land_break"]
    f1 = raw["open_findings"]["1_bend_zone_clearance_worst_case"]
    g_fix = 3.23
    assert ("g_bend about %.2f restores 0.45 at the full worst case" % g_fix) in f1["fixes"], f1["fixes"]
    land19 = round(19.0 - bezel - g_fix, 2)
    brk19 = round(land19 - G.land_break - bead_in, 2)
    assert abs(bezel + g_fix + land19 - 19.0) < 1e-9 and abs(land19 - 6.26) < 1e-9 and abs(brk19 - 1.06) < 1e-9, (land19, brk19)
    brk_max = round(to_face - G.bead_pocket_min, 2)                     # 0.09
    old = f2["fixes"]
    f2["fixes"] = ("border 19.0 with g_bend %.2f - the one fix that closes both findings (item 1: 0.45 at the full worst case): bottom "
                   "land %.2f (%.2f + %.2f + %.2f = %.2f), bead to the break edge %.2f; or, at border 18.5, land_break <= %.2f (0.10 gives "
                   "%.2f). Land-plane values; the Z_LAND + 0.01 probe of the finding reads 0.01 more on the 45 deg break" % (
                       g_fix, land19, bezel, g_fix, land19, bezel + g_fix + land19, brk19, brk_max, to_face - 0.10))
    chg("open_findings.2_bead_to_land_break.fixes", old, f2["fixes"], 2)
    # ---------------------------------------------------------------- 3. drawings item done
    tbr = raw["to_be_reverified_at_GF-2.0"]
    item = "drawings GF-D01..D50 (Mechanical/Rev3.0_GlassFront/drawings are GF-1.1)"
    assert tbr.count(item) == 1
    rep = json.load(open(os.path.join(C.GF_DIR, "drawings", "drawings_report.json"), encoding="utf8"))
    assert rep["master"]["revision"] == "GF-2.0" and rep["generated"].startswith(DATE), rep["master"]
    new_item = ("DONE %s (tools/glassfront/drawings, frame STEP sha256 %s): %s -> the folder holds the GF-2.0 set, regenerated from "
                "the corrected master (params sha256 %s) and self-checked %s (drawings/drawings_report.json); the GF-1.1 set is in "
                "archive/GF-1.1/drawings/" % (DATE, step_sha[:16], item, rep["master"]["sha256"][:16], rep["generated"].replace("T", " ")))
    old = list(tbr)
    tbr[tbr.index(item)] = new_item
    chg("to_be_reverified_at_GF-2.0[%d]" % tbr.index(new_item), item, new_item, 3)
    # ---------------------------------------------------------------- 4. fold test
    l0, rin, tt = G.tail_straight_l0, G.tail_R_in_min, G.tail_t
    slot = 3.0
    lim = l0 + rin + tt                                                  # 2.30
    feeler = round(slot - lim, 2)                                        # 0.70
    need = lim + clr + rss                                               # 3.058
    d_exact = g_lim - clr - rss                                          # 2.332
    f_exact = slot - d_exact                                             # 0.668
    # the lead's arithmetic
    assert abs(slot - 2.30 - 0.70) < 1e-9 and abs(lim - 2.30) < 1e-9 and abs(feeler - 0.70) < 1e-9
    assert abs(round(3.09 - 0.45 - 0.31, 2) - 2.33) < 1e-9 and abs(round(3.00 - 2.33, 2) - 0.67) < 1e-9
    assert abs(round(d_exact, 2) - 2.33) < 1e-9 and abs(round(f_exact, 2) - 0.67) < 1e-9 and abs(round(need, 2) - 3.06) < 1e-9
    raw["fold_test"] = {
        "about": "real-panel fold test on the GF-D21 tail fold gauge (concept_gf2.md 2.4): the pass line, lead decision %s; the one "
                 "source for the drawings and the design document. It supersedes the concept pass line (tail surface within 2.55 of "
                 "the panel edge, 0.45 feeler in the 3.00 slot) and the 0.76 feeler / 2.24 conversion of the GF-2.0 drawing set" % DATE,
        "gauge_slot_mm": slot,
        "gauge_slot_note": "GF-D21 slot = panel edge face -> gauge face, 3.00 (the GF-2.0 g_bend); the gauge stays 3.00",
        "feeler_mm": feeler,
        "tail_outer_surface_limit_from_panel_edge_mm": round(lim, 2),
        "limit_basis": "assumed straight tail_straight_l0 %.1f + inner radius tail_R_in_min %.1f + thickness tail_t %.2f = %.2f = gauge "
                       "slot %.2f - feeler %.2f" % (l0, rin, tt, lim, slot, feeler),
        "check": "panel held at its nominal position by the gauge, each tail folded over the gauge nose: the %.2f feeler passes between "
                 "the tail's outer surface and the gauge face / nose over the whole tail width (tail outer surface within %.2f of the "
                 "panel edge); record the largest feeler that passes" % (feeler, lim),
        "pass": "the tail needs no more room than assumed and border %.1f holds by the budget: needed gap = %.2f + clearance %.2f + panel "
                "position %.2f RSS = %.2f <= limit %.2f (g_bend note); the rebuild then sets g_bend to the needed value" % (
                    G.border, lim, clr, rss, need, g_lim),
        "fail": "border 19.0 or more, decided from the measured values with the same budget formula: needed gap = measured tail extent "
                "(panel edge -> tail outer surface) + %.2f + %.2f, border = bezel %.2f + needed gap + land %.1f (bead_edge %.1f + bead_w "
                "%.1f + bead_pocket_min %.1f)" % (clr, rss, bezel, land_min, G.bead_edge, G.bead_w, G.bead_pocket_min),
        "exact_feeler_for_the_limit_mm": round(f_exact, 2),
        "feeler_note": "the feeler that corresponds exactly to the border-%.1f limit is %.2f - (%.2f - %.2f - %.2f) = %.2f - %.2f = %.2f "
                       "(unrounded %.3f / %.3f); %.2f is the nearest standard feeler leaf at or above it, i.e. on the safe side (it "
                       "accepts a tail up to %.2f, the exact limit is %.2f; a 0.65 leaf is numerically nearer but would accept up to "
                       "%.2f)" % (G.border, slot, g_lim, clr, rss, slot, d_exact, f_exact, d_exact, f_exact, feeler, lim, d_exact, slot - 0.65),
        "references": "driving_parameters.g_bend note (budget), tail_clearance_criteria.bend_zone, open_findings 1",
        "date": DATE}
    chg("fold_test", None, "added", 4)
    # ---------------------------------------------------------------- change log
    raw["change_log"][KEY] = {
        "date": DATE, "by": "independent verification agent (tools/glassfront/verify/params_gf20_post_verification_addendum.py)",
        "summary": "addendum to %s after the drawings and the design document were regenerated from the corrected master: (1) "
                   "land_break and lands notes give the bead -> break edge as 0.80 measured (1.09 to the pocket-face plane) and no longer "
                   "call 1.09 the governing bead_to_pocket; (2) open_findings 2 quotes the common border-19.0 fix 3.23 / 6.26 / 1.06; (3) "
                   "the drawings item of to_be_reverified_at_GF-2.0 marked done; (4) new block fold_test (gauge slot 3.00, feeler 0.70, "
                   "tail within 2.30 of the panel edge). No geometry value changed; frame STEP sha256 %s; revision stays GF-2.0" % (
                       KEY_FIX, step_sha),
        "params_sha256_before": sha_old, "changes": changes}
    # ---------------------------------------------------------------- numeric diff
    a, b = numeric_leaves(before), numeric_leaves(raw)
    diff = {"changed": {k: [a[k], b[k]] for k in sorted(set(a) & set(b)) if a[k] != b[k]},
            "removed": {k: a[k] for k in sorted(set(a) - set(b))},
            "added": {k: b[k] for k in sorted(set(b) - set(a))},
            "count_before": len(a), "count_after": len(b)}
    print("numeric leaves before %d after %d; changed %d, removed %d, added %d" % (
        len(a), len(b), len(diff["changed"]), len(diff["removed"]), len(diff["added"])))
    for k, v in diff["changed"].items():
        print("  CHANGED %s: %s -> %s" % (k, v[0], v[1]))
    for k, v in diff["removed"].items():
        print("  REMOVED %s: %s" % (k, v))
    for k, v in diff["added"].items():
        print("  ADDED %s: %s" % (k, v))
    if dry:
        os.makedirs(C.TMP, exist_ok=True)
        pv = os.path.join(C.TMP, "params_addendum_preview.json")
        json.dump({"fold_test": raw["fold_test"], "changes": changes}, open(pv, "w"), indent=1)
        print("dry run - nothing written to the master; preview", pv)
        return 0
    if not os.path.exists(BACKUP):
        shutil.copyfile(PARAMS, BACKUP)
    write_master(raw, PARAMS)
    sha_new = sha(PARAMS)
    diff["params_sha256_before"], diff["params_sha256_after"] = sha_old, sha_new
    C.dump(diff, DIFF)
    # ---------------------------------------------------------------- errata: newest params sha
    er = json.load(open(ERRATA, encoding="utf8"))
    assert er.get("params_sha256_after_corrections") == sha_old, "errata sha record does not end with the current master"
    er["params_sha256_after_addendum"] = sha_new
    er["params_sha256_history"] = [
        {"sha256": er["params_sha256_before_corrections"], "what": "GF-2.0 as written by the Fusion stage (quoted by the reports)"},
        {"sha256": sha_old, "what": "after change_log.%s" % KEY_FIX},
        {"sha256": sha_new, "what": "after change_log.%s (notes, open_findings 2 fix numbers, to_be_reverified, fold_test)" % KEY}]
    er["params_change"] = er["params_change"] + "; then change_log.%s" % KEY
    json.dump(er, open(ERRATA, "w", encoding="utf8"), indent=1)
    print("params sha256 %s -> %s" % (sha_old, sha_new))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
