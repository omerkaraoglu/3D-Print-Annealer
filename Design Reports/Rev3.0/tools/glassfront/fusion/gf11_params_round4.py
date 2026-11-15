"""Stage 3, lead round 4 (bookkeeping only; frame and Fusion geometry frozen): amend the GF-1.1 master params in place
(same revision, new block change_log.round_4, key names kept): bead adhesive class, corner seal count (counted in the
assembly: gf11\\strip_ends.json), S8 shim radial over the dia-5.8 envelope, stud position requirement, graded jig /
mounting shims + glass outline tolerance wording, material / UL card note. Backup: stage2_dumps\\params_GF-1.1_round3.json.
Refuses if change_log.round_4 exists. Usage: python gf11_params_round4.py"""
import json
import math
import os
import shutil

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
BACKUP = os.path.join(SCR, "stage2_dumps", "params_GF-1.1_round3.json")
SE = json.load(open(os.path.join(SCR, "gf11", "strip_ends.json")))


def entry(lst, name):
    for e in lst:
        if e.get("name") == name:
            return e
    raise KeyError(name)


def main():
    raw = json.load(open(P, encoding="utf-8"))
    if not str(raw.get("revision", "")).startswith("GF-1.1"):
        raise SystemExit("not GF-1.1")
    if "round_4" in raw.get("change_log", {}):
        raise SystemExit("round 4 already applied")
    if not os.path.exists(BACKUP):
        shutil.copyfile(P, BACKUP)
    log = []

    def chg(item, path, old, new, note=""):
        log.append({"item": item, "path": path, "old": old, "new": new, "note": note})

    # 1 bead adhesive
    e = entry(raw["bead"], "adhesive")
    old = [e["value"], e["note"]]
    s05 = 1.0 * math.sqrt(2 * 0.5 + 0.25)
    s025 = 1.0 * math.sqrt(2 * 0.25 + 0.0625)
    e["value"] = ("black elastic 2-C (or 1-C) neutral silicone or MS polymer, low-modulus, movement capability >= +-50 % "
                  "(ASTM C920 Class 50 or maker-declared; ISO 11600 stops at class 25) for the 1.0 bead; primer on PA and "
                  "print. With a class-25 product the bead must be 1.5 thick, which changes t_bond and must be decided "
                  "before the tool is cut (the model is not rebuilt or verified at 1.5)")
    e["note"] = ("R1/R2. Shear: allowable displacement t * sqrt(2e + e^2) = %.2f at e 0.5 and %.2f at e 0.25 for t 1.0; "
                 "bound case with moisture swelling about 0.68 at the thinnest bond line 0.73 (allowable %.2f at class "
                 "50)" % (s05, s025, 0.73 * s05))
    chg("1", "bead.adhesive", old, [e["value"], e["note"]])
    tb = entry(raw["driving_parameters"], "t_bond")
    o = tb["note"]
    tb["note"] = o + " (1.0 needs a +-50 % adhesive; class 25 would need 1.5 = a t_bond change before the tool is cut, " \
                     "see bead.adhesive)"
    chg("1", "driving_parameters.t_bond.note", o, tb["note"])
    # 2 corner seal: counted in the assembly
    n_strips, n_ends = SE["strips"], SE["strip_ends"]
    per = {k: len(v) for k, v in SE["ends_per_corner"].items()}
    gaps = sorted(set(r["end_to_pad_min_mm"] for r in SE["rows"]))
    cs = entry(raw["tape_and_gasket"], "corner_seal")
    old = [cs["value"], cs["note"]]
    cs["value"] = ("dab of the bead adhesive over the %d strip-end gaps: %d straight strips have %d ends, %s at each of the "
                   "4 corner pads F1-F4, each strip end %.1f before its pad (counted / measured in the assembly)" %
                   (n_ends, n_strips, n_ends, "2" if set(per.values()) == {2} else per, gaps[0]))
    cs["note"] = "closes the leak path (S4 / R4)"
    chg("2", "tape_and_gasket.corner_seal", old, [cs["value"], cs["note"]])
    # 3 S8 shim radial over the 5.8 envelope
    sp = entry(raw["fasteners"]["hardware"], "spacer_S8")
    old = sp["value"]
    sp["value"] = sp["value"].replace("0.55 over a 5.9 weld collar",
                                      "0.60 over the dia-5.8 flange + collar envelope (see stud)")
    chg("3", "fasteners.hardware.spacer_S8.value", old, sp["value"])
    # 4 stud position requirement
    sh = raw["drawing_tolerances"]["sheet"]
    e = entry(sh, "stud_position_tol")
    old = [e["value"], e["note"]]
    e["value"] = 0.3
    e["note"] = ("+- stud axis relative to its nominal position on the cut-out: the REQUIREMENT (the counterbore clearances "
                 "were checked for it); a weld template that locates on the cut-out with +-0.2 accuracy is the recommended "
                 "means, not the requirement")
    chg("4", "drawing_tolerances.sheet.stud_position_tol", old, [e["value"], e["note"]])
    s4 = raw["sheet_variants"]["S4"]
    o = s4["value"]
    s4["value"] = o.replace("(template +-0.2)", "(stud axis +-0.3 to the cut-out; weld template +-0.2 recommended)")
    chg("4", "sheet_variants.S4.value", o, s4["value"])
    # 5 jig / mounting shims, glass outline tolerance wording
    gl = raw["drawing_tolerances"]["glass"]
    e = entry(gl, "outline_tol")
    old = [e["value"], e["note"]]
    e["value"] = 0.1
    e["note"] = ("+- REQUESTED from the supplier (precision CNC; R2); +-0.2 is the accepted fallback. The graded J2 "
                 "centring shims (jig_and_mounting_shims) cover the fallback; a single 0.30 J2 shim only enters at about "
                 "+-0.1")
    chg("5", "drawing_tolerances.glass.outline_tol", old, [e["value"], e["note"]],
        "value = the tolerance requested on the glass drawing; fallback +-0.2 in the note")
    raw["jig_and_mounting_shims"] = [
        {"name": "J2_glass_centring_shims", "value": [0.15, 0.2, 0.25, 0.3], "unit": "mm",
         "note": "graded set in g2 (glass edge -> lip inner face) in jig J2; use the thickest size that enters on all four "
                 "sides. A single 0.30 shim only enters when the glass outline is within about +-0.1"},
        {"name": "sheet_mounting_shims", "value": [0.2, 0.25, 0.3], "unit": "mm",
         "note": "graded set in g1 (sheet cut-out edge -> lip outer face) when the sheet is mounted; use the thickest size "
                 "that enters on all four sides. A single 0.30 shim has zero play at cut-out -0.1"},
        {"name": "shim_rule", "value": "use the thickest size that enters on all four sides", "unit": "-",
         "note": "GF-1.1 round 4"}]
    chg("5", "jig_and_mounting_shims", None, raw["jig_and_mounting_shims"], "added")
    # 6 material / UL card
    raw["material"] = [
        {"name": "frame_material", "value": "PA6-GF30, black (frame v2 material)", "unit": "-",
         "note": "carried over from v2 (wall note: PA6-GF30)"},
        {"name": "UL_card", "value": "the UL yellow card must list V-0 and the glow-wire ratings (GWFI / GWIT) at <= 1.0 mm, "
                                     "not only at 1.5 mm", "unit": "-",
         "note": "thinnest walls: lip 1.0, H6 tail wall 1.1 at Z_PCB (GF-1.1 round 4)"}]
    chg("6", "material", None, raw["material"], "added")
    raw["change_log"]["round_4"] = {
        "date": "2026-11-15", "by": "gf11_params_round4.py",
        "what": "bookkeeping after the design-document review; frame and Fusion geometry frozen, no Fusion change",
        "corner_seal_count_source": "assembly (VHB tape strips: %d bodies, %d end faces, %s)" % (n_strips, n_ends, per),
        "changes": log}
    json.dump(raw, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.load(open(P, encoding="utf-8"))
    print("written", P, len(log), "changes")


if __name__ == "__main__":
    main()
