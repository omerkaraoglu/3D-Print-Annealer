"""GF-2.1 master params: addendum after the GF-2.1 verification hand-back (before drawings and document start).

  <venv>\\Scripts\\python.exe -B params_gf21_addendum.py            (writes the master + the numeric diff)
  <venv>\\Scripts\\python.exe -B params_gf21_addendum.py --dry-run  (diff only)

  1. cad_rules shut-off rule ('shut-off A/B'): the GF-2.1 figures measured by the verification (out/cadcheck.json
     mould.bridge.shut_off): parting points, rise / run, A ledge, stepped steel angles, max telescopic angle, straight knife edge;
  2. as_modelled_GF-2.1.pip_top_to_glass_mm: 0.50 = the clearance to the glass back (incl. its 0.02 print); the Fusion 0.52
     kept under its own name (to the glass substrate behind the print);
  3. stale GF-2.0 numbers stated as current: only cad_rules[15] found (28.6 / 29.6 / 3.23 ledge) - fixed by 1;
  4. open_findings.margins_note_GF-2.1: full-worst-case bend-zone margin, g_bend room to its limit, paid out of the bead margin.
Discipline: refuses a second run (change_log KEY), byte-exact writer check, previous master saved to
out/params_before_GF21_addendum.json, numeric diff to out/params_GF21_addendum_numeric_diff.json, assertion that no numeric
value changes outside the pip-to-glass entry and the new / log entries.
"""
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon as C
from params_gf20_post_verification_fix import sha, write_master, numeric_leaves

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PARAMS = C.GF_PARAMS
PARAMS_SHA_IN = "6bb527b0b0e15c83811a6eed5ae60ecb3f7692d80f9e0637f95993bb9c82abe8"
STEP_SHA = "d734683ac0c0058a863c4d079b511767ff84a41912745e2ebf592eb1e4e333d6"
BACKUP = os.path.join(OUT, "params_before_GF21_addendum.json")
DIFF = os.path.join(OUT, "params_GF21_addendum_numeric_diff.json")
DATE = "2026-11-16"
KEY = "independent_verification_GF-2.1_addendum_%s" % DATE
ALLOWED_NUMERIC = ("as_modelled_GF-2.1.pip_top_to_glass", "open_findings.margins_note", "change_log.")


def main(argv):
    dry = "--dry-run" in argv
    raw = json.load(open(PARAMS, encoding="utf8"))
    if KEY in raw.get("change_log", {}):
        print("already applied (change_log has %s) - restore %s first to re-run" % (KEY, BACKUP))
        return 1
    sha_old = sha(PARAMS)
    assert sha_old == PARAMS_SHA_IN, "the master is not the file this addendum was written for (%s)" % sha_old
    probe = os.path.join(OUT, "_params_format_probe.json")
    write_master(raw, probe)
    same = open(probe, "rb").read() == open(PARAMS, "rb").read()
    os.remove(probe)
    assert same, "write_master does not reproduce the master format - nothing written"
    before = json.loads(json.dumps(raw))
    assert C.file_id(C.GF_STEP)["sha256"] == STEP_SHA
    cad = json.load(open(os.path.join(OUT, "cadcheck.json")))
    fit = json.load(open(os.path.join(OUT, "fitcheck.json")))
    calc = json.load(open(os.path.join(OUT, "calc.json")))
    assert cad["step"]["sha256"] == STEP_SHA
    G = C.GF(PARAMS)
    changes = []

    def chg(path, old, new, why):
        changes.append({"path": path, "old": old, "new": new, "reason": why})

    # ---------------------------------------------------------------- 1. shut-off rule
    so = cad["mould"]["bridge"]["shut_off"]
    assert len(so) == 2 and so[0]["PB_chamfer_top_yZ"] == so[1]["PB_chamfer_top_yZ"] and so[0]["run_mm"] == so[1]["run_mm"]
    s = so[0]
    k_st = next(k for k in s if k.startswith("option_stepped"))
    pb, pf = s["PB_chamfer_top_yZ"], s["PF_shelf_corner_yZ"]
    rules = raw["cad_rules"]
    i = [j for j, r in enumerate(rules) if "shut-off A/B" in r]
    assert len(i) == 1
    i = i[0]
    old = rules[i]
    rules[i] = ("GF-2.1: bridge = land plate + step wall + flange plate over the tail span; nose R bend_nose_R on the land-plate back x "
                "pocket face (B side), land_break %.1f x 45 deg on the land x pocket face (A side); slot faces 1 deg; the bend-gap slot is "
                "the only through-opening at the bottom. Its shut-off A/B is NOT a flat face at Z_LAND: the parting runs on the bridge side "
                "at the top of the land break (y %.3f, Z_LAND + land_break = %.2f) and on the front side at the shelf corner (y %.2f, "
                "Z_SEAT %.2f), so it rises %.2f over the %.3f slot width. Buildable form: an A-side ledge %.3f x %.1f across the slot at "
                "the break level, then a telescopic shut-off face along y %.2f rising to Z_SEAT, >= 3 deg on that face (no part face below "
                "Z_SEAT there; up to %.1f deg fits in the slot); stepped steel angles B %.0f deg / A %.0f deg at the break top, no knife "
                "edge (a straight shut-off from the break top to the shelf corner would leave a %.1f deg B-steel knife edge; a flat "
                "shut-off at Z_LAND makes the break an undercut for B with a 45 deg knife edge). Toolmaker to state the final shut-off "
                "design; no flash allowed on it (verified %s on GF-2.1, frame STEP sha256 %s, x 60 and x 130)" % (
                    G.land_break, pb[0], pb[1], pf[0], pf[1], s["rise_mm"], s["run_mm"], s[k_st]["A_ledge_mm"][0], s[k_st]["A_ledge_mm"][1],
                    pf[0], s["max_shutoff_angle_from_pull_deg"], s[k_st]["B_steel_at_PB_deg"], s[k_st]["A_steel_at_PB_deg"],
                    s["option_straight_PF_PB"]["B_steel_wedge_at_PB_deg"], DATE, STEP_SHA[:16]))
    assert sum("shut-off A/B" in r for r in rules) == 1 and sum("vent witness on the lip top" in r for r in rules) == 1
    chg("cad_rules[%d]" % i, old, rules[i], "GF-2.1 shut-off figures (28.6 -> %.1f, 29.6 -> %.1f, ledge 3.23 -> %.3f)" % (
        s["max_shutoff_angle_from_pull_deg"], s["option_straight_PF_PB"]["B_steel_wedge_at_PB_deg"], s[k_st]["A_ledge_mm"][0]))
    # ---------------------------------------------------------------- 2. pip to glass
    am = raw["as_modelled_GF-2.1"]
    pr = next(r for r in fit["rows"] if r["check"].startswith("pip tops -> glass back"))
    assert pr["measured"].startswith("0.500")
    old = am["pip_top_to_glass_mm"]
    assert old == [0.52]
    keys = list(am)
    new_am = {}
    for k in keys:
        if k == "pip_top_to_glass_mm":
            new_am[k] = [0.5]
            new_am["pip_top_to_glass_note"] = (
                "0.50 = clearance from the 8 pip tops (Z_PIP_TOP %.2f) to the glass back including its 0.02 black print (Z_GLASS_BACK "
                "%.2f), verified %s on the GF-2.1 STEP; the Fusion check's 0.52 is measured to the glass substrate behind the 0.02 "
                "print layer (pip_top_to_glass_substrate_mm), not the clearance" % (G.L["Z_PIP_TOP"], G.L["Z_GLASS_BACK"], DATE))
            new_am["pip_top_to_glass_substrate_mm"] = old
        elif k in ("pip_top_to_glass_note", "pip_top_to_glass_substrate_mm"):
            continue
        else:
            new_am[k] = am[k]
    raw["as_modelled_GF-2.1"] = new_am
    chg("as_modelled_GF-2.1.pip_top_to_glass_mm", old, [0.5], "clearance to the glass back incl. the print; 0.52 kept as "
                                                              "pip_top_to_glass_substrate_mm")
    # ---------------------------------------------------------------- 4. margins note
    of = raw["open_findings"]
    wc = of["1_bend_zone_clearance_worst_case"]["measured_GF-2.1_mm"]["CTP"]["full_WC"]
    bp = min(of["2_bead_to_land_break"]["measured_GF-2.1_mm"]["on_the_land_plane_x60_x130"])
    gb = calc["bend_zone_criterion"]["g_bend_budget"]
    room = gb["limit_for_border"] - G.g_bend
    bead_m = bp - float(G.bead_pocket_min)
    assert abs(room - 0.06) < 1e-6 and abs(bead_m - 0.06) < 1e-6, (room, bead_m)
    note = ("GF-2.1 (verified %s): the full-worst-case bend-zone margin is %+.3f mm (CTP %.4f against 0.45; exit Z at its lower limit "
            "governs), and g_bend has %.2f mm of room to its limit %.2f (border %.1f - bezel %.2f - land %.2f measured to the break edge), "
            "which would be paid for one-to-one out of the %.3f bead margin (bead -> break edge %.3f on the land plane against "
            "bead_pocket_min %.1f). No rebuild for this; the real-panel fold test (fold_test) is the gate" % (
                DATE, wc - 0.45, wc, room, gb["limit_for_border"], gb["border"], gb["bezel"], gb["land_min"], bead_m, bp,
                float(G.bead_pocket_min)))
    new_of = {}
    for k, v in of.items():
        new_of[k] = v
        if k == "about":
            new_of["margins_note_GF-2.1"] = note
    raw["open_findings"] = new_of
    chg("open_findings.margins_note_GF-2.1", None, note, "lead request: margins stated plainly")
    # ---------------------------------------------------------------- change log, diff, write
    raw["change_log"][KEY] = {
        "date": DATE, "by": "independent verification agent (tools/glassfront/verify/params_gf21_addendum.py)",
        "summary": "addendum after the GF-2.1 verification hand-back: cad_rules shut-off rule at the GF-2.1 figures; pip-to-glass "
                   "0.50 (clearance) with the Fusion 0.52 named as to the glass substrate; open_findings margins note. The search for "
                   "GF-2.0 numbers stated as current found only the shut-off rule. No geometry value changed; revision stays GF-2.1",
        "params_sha256_before": sha_old, "changes": changes}
    a, b = numeric_leaves(before), numeric_leaves(json.loads(json.dumps(raw)))
    diff = {"changed": {k: [a[k], b[k]] for k in sorted(set(a) & set(b)) if a[k] != b[k]},
            "removed": {k: a[k] for k in sorted(set(a) - set(b))},
            "added": {k: b[k] for k in sorted(set(b) - set(a))}, "count_before": len(a), "count_after": len(b)}
    bad = [k for k in list(diff["changed"]) + list(diff["removed"]) + list(diff["added"]) if not k.startswith(ALLOWED_NUMERIC)]
    assert not bad, ("numeric values outside the allowed entries would change", bad)
    for t, d in (("CHANGED", diff["changed"]), ("REMOVED", diff["removed"]), ("ADDED", diff["added"])):
        for k, v in d.items():
            print("  %s %s: %s" % (t, k, v))
    print("rule:", rules[i])
    print("note:", note)
    if dry:
        print("dry run - nothing written")
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
