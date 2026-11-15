"""Stage 3, lead round 3 (bookkeeping, frame frozen): amend the GF-1.1 master params in place (same revision; new block
change_log.round_3; key names kept). Measured values come from gf11\\round3_hardware.json (64),
gf11\\extreme_stud_tape.json + extreme_stud_5p9x1p5.json (63) and the washer-offset bearing computed from
sections_asm.json (tube-top section, gf_asm_offline.poly_at). Backup: stage2_dumps\\params_GF-1.1_round2.json.
Refuses if change_log.round_3 exists. Usage: python gf11_params_round3.py"""
import json
import math
import os
import shutil
import sys

from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gf_asm_offline as G  # noqa: E402

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
BACKUP = os.path.join(SCR, "stage2_dumps", "params_GF-1.1_round2.json")
HW = json.load(open(os.path.join(SCR, "gf11", "round3_hardware.json")))
EX57 = json.load(open(os.path.join(SCR, "gf11", "extreme_stud_tape.json")))
EX59 = json.load(open(os.path.join(SCR, "gf11", "extreme_stud_5p9x1p5.json")))


def entry(lst, name):
    for e in lst:
        if e.get("name") == name:
            return e
    raise KeyError(name)


def worst(ex, f, k):
    s = ex["studs"][f]
    return min(v[k]["d_mm"] for n, v in s.items() if isinstance(v, dict) and k in v and v[k] and n != "centred")


def bearing_offsets(raw):
    d = G.load("sections_asm.json")
    p = d["params"]
    ax = {f["name"]: f["slot_axis"] for f in raw["fasteners"]["positions"]}
    rec = next(r for r in d["levels"].values() if r.get("tube_top_level"))
    fr = G.poly_at(rec["Frame GF"])
    x, y = p["fasteners"]["F1"]
    ux, uy = ax["F1"]
    out = {}
    for lab, (a, b) in (("centred", (0, 0)), ("0.6 along", (0.6 * ux, 0.6 * uy)), ("0.7 across", (-0.7 * uy, 0.7 * ux)),
                        ("1.5 along (slot end)", (1.5 * ux, 1.5 * uy))):
        out[lab] = {}
        for nm, od, idd in (("M4", p["w4"][0], p["w4"][1]), ("M5", p["w5"][0], p["w5"][1])):
            c = Point(x + a, y + b)
            ann = c.buffer(od / 2, quad_segs=128).difference(c.buffer(idd / 2, quad_segs=128))
            out[lab][nm] = round(ann.intersection(fr).area, 1)
    return out


def main():
    raw = json.load(open(P, encoding="utf-8"))
    if not str(raw.get("revision", "")).startswith("GF-1.1"):
        raise SystemExit("not GF-1.1")
    if "round_3" in raw.get("change_log", {}):
        raise SystemExit("round 3 already applied")
    if not os.path.exists(BACKUP):
        shutil.copyfile(P, BACKUP)
    log = []

    def chg(item, path, old, new, note=""):
        log.append({"item": item, "path": path, "old": old, "new": new, "note": note})

    dt = raw["drawing_tolerances"]
    # 1 glass corner radius tolerance
    e = entry(dt["glass"], "corner_R")
    old = [e["value"], e["note"]]
    e["value"] = 6.25
    e["note"] = ("+0.2/-0 (one-sided). With independent outline +-0.2 and radius +-0.2 a large glass with a small radius "
                 "puts the corner closer to the lip than the sides; the one-sided tolerance keeps the corner at or more "
                 "open than nominal (GF-1.1 round 3; was the stale 6.0 +-0.5)")
    chg("C1", "drawing_tolerances.glass.corner_R", old, [6.25, "+0.2/-0"])
    # 2 sheet cut-out corner radius tolerance
    sh = dt["sheet"]
    i = next(k for k, x in enumerate(sh) if x["name"] == "cut_out_tol")
    sh.insert(i + 1, {"name": "cut_out_corner_R", "value": 7.55, "unit": "mm",
                      "note": "+0/-0.2 (one-sided: a smaller radius opens the corner gap g1; GF-1.1 round 3)"})
    chg("C2", "drawing_tolerances.sheet.cut_out_corner_R", None, [7.55, "+0/-0.2"], "added")
    # 3 d_cut_out_edge recomputed from the model (64: stud axis at the sheet front -> nearest cut-out face)
    dce = HW["d_cut_out_edge"]
    for f in raw["fasteners"]["positions"]:
        new = round(dce[f["name"]][0], 4)
        if abs(f["d_cut_out_edge"] - new) > 1e-6:
            chg("C3", "fasteners.positions.%s.d_cut_out_edge" % f["name"], f["d_cut_out_edge"], new,
                "measured on the model: axis to the %s" % dce[f["name"]][1])
        f["d_cut_out_edge"] = new
        if f["name"] in ("F5", "F6", "F7", "F8") and "DIN 9021 M4" in f.get("front_pad", ""):
            o = f["front_pad"]
            f["front_pad"] = "none moulded; S8 adds a 1.0 shim (DIN 988 7 x 13 x 1.0) as hard stop"
            chg("B", "fasteners.positions.%s.front_pad" % f["name"], o, f["front_pad"])
    r4 = raw["sheet_variants"]["R4"]
    d14 = HW["R4"]["F1"]
    old = [r4["value"], r4["note"]]
    r4["value"] = ("4 holes at F1-F4: dia 5.2 +0.1/0 (dia 4.8 LARGE-FLANGE blind rivet, DIN 7337 large-flange type, "
                   "head dia 14 'K14', tri-fold / bulb; GESIPA 5.1-5.4); VHB strips; heads ~1.5-2.0 proud")
    r4["note"] = ("edge distance axis -> cut-out %.2f (to the R7.55 corner arc, >= 2d); dia-14 head edge %.2f from the "
                  "cut-out corner arc; pad face under the head %.1f mm2 per position (a dia-10 head would keep only %.1f "
                  "after the 7.4 x 9.0 counterbore)" % (d14["axis_to_cut_out_edge"],
                                                        d14["head_edge_to_cut_out_corner_measured"]["d_mm"],
                                                        d14["pad_face_under_head_dia14_mm2"],
                                                        d14["pad_face_under_head_dia10_mm2 (old head)"]))
    chg("A + C3", "sheet_variants.R4.value / note", old, [r4["value"], r4["note"]])
    hw = raw["fasteners"]["hardware"]
    rv = entry(hw, "rivet")
    old = [rv["value"], rv["note"]]
    rv["value"] = ("dia 4.8 LARGE-FLANGE blind rivet set from the front (DIN 7337 large-flange type, head dia 14 'K14', "
                   "modelled head height 1.6 with an R1.4 edge), tri-fold / bulb Al/Al, black head; sheet hole dia 5.2 "
                   "+0.1/0; grip 8.2 (8.3 at glass 1.1); backing washer DIN 9021 M5 (15 x 1.2) on the tube top")
    rv["note"] = ("R4 (GF-1.1 round 3: the dia-10 head kept only %.1f mm2 of pad face after the counterbore; dia 14: "
                  "%.1f mm2)" % (d14["pad_face_under_head_dia10_mm2 (old head)"], d14["pad_face_under_head_dia14_mm2"]))
    chg("A", "fasteners.hardware.rivet", old, [rv["value"], rv["note"]])
    # B S8 shim
    sp = entry(hw, "spacer_S8")
    s8 = HW["S8"]["F5"]
    near = s8["nearest_vertical_frame_faces_in_gap_layer"]
    old = [sp["value"], sp["note"]]
    sp["value"] = ("DIN 988 7 x 13 x 1.0 shim on the stud between sheet and flange at F5-F8 (bore 7.0: 0.65 radial over a "
                   "5.7 flange, 0.55 over a 5.9 weld collar)")
    sp["note"] = ("hard stop where no pad is moulded; bears %.1f mm2 on the flange front (the counterbore opening 7.365 x "
                  "8.965 takes the rest of the %.1f mm2 annulus) and %.1f on the sheet; OD edge %.2f from the seat ring "
                  "(step wall front) and %.2f from the flange edge; takes 13 mm of the 12-wide gasket / tape band (s %.1f "
                  "- %.1f vs band s 3.9 - 15.9) at each position" %
                  (s8["contact_on_flange_front_mm2"], s8["annulus_mm2"], s8["contact_on_sheet_mm2"], near[0]["d_mm"],
                   next(r["d_mm"] for r in near if r["z"][1] > -12.0), HW["S8"]["band"]["shim_s_range"][0],
                   HW["S8"]["band"]["shim_s_range"][1]))
    chg("B", "fasteners.hardware.spacer_S8", old, [sp["value"], sp["note"]])
    # 5 weld stud note
    st = entry(hw, "stud")
    old = st["note"]
    st["note"] = ("S4: F1-F4; S8: F1-F8. ISO 13918 PT M4 weld flange dia 5.3-5.7 x 0.7-1.4 sits in the fastener "
                  "counterbore (GF-1.1). The flange INCLUDING weld collar / flash must stay within dia 5.9 x 1.5 high. "
                  "Measured worst case with a clean dia 5.7 x 1.4 flange and the stud against the slot wall / end: "
                  "%.2f to the counterbore wall, %.2f to the floor round, %.2f to the floor at F1-F4 (F5-F8 %.2f / %.2f "
                  "/ %.2f). The full 5.9 x 1.5 envelope clears when the stud is centred (%.2f to the round) but at "
                  "F1-F4 its top edge touches the R0.3 floor round when the stud is pressed against the slot wall "
                  "(modelled overlap <= %.4f mm3, ~0.04 deep; wall %.3f, floor %.2f); F5-F8 clear (wall %.3f)" %
                  (worst(EX57, "F1", "flange_to_wall"), worst(EX57, "F1", "flange_to_floor_round"),
                   worst(EX57, "F1", "flange_to_floor"), worst(EX57, "F5", "flange_to_wall"),
                   worst(EX57, "F5", "flange_to_floor_round"), worst(EX57, "F5", "flange_to_floor"),
                   EX59["studs"]["F1"]["centred"]["floor_round"]["d_mm"],
                   max(v.get("stud_frame_overlap_mm3") or 0 for v in EX59["studs"]["F1"].values() if isinstance(v, dict)),
                   worst(EX59, "F1", "flange_to_wall"), worst(EX59, "F1", "flange_to_floor"),
                   worst(EX59, "F5", "flange_to_wall")))
    chg("C5", "fasteners.hardware.stud.note", old, st["note"])
    # 6 washer bearing
    bo = bearing_offsets(raw)
    wn = entry(hw, "washer_nut")
    old = wn["note"]
    wn["note"] = ("bearing on the tube top (DIN 9021 M4): %.1f mm2 centred, %.1f at 0.6 off-centre along the slot, %.1f "
                  "at 0.7 across, %.1f at the slot end (500 N -> %.1f / %.1f MPa); off-centre the washer overhangs the "
                  "coring groove (r 6.2-7.5) on one side - 80 mm2 holds only near the centre" %
                  (bo["centred"]["M4"], bo["0.6 along"]["M4"], bo["0.7 across"]["M4"], bo["1.5 along (slot end)"]["M4"],
                   500 / bo["centred"]["M4"], 500 / bo["1.5 along (slot end)"]["M4"]))
    chg("C6", "fasteners.hardware.washer_nut.note", old, wn["note"])
    for e in raw["fasteners"]["tube_coring"]:
        if "12.4" in e.get("note", "") and e["name"] == "core_r_in":
            e["note"] = "groove inner radius at the tube top (washer seat dia 12.4; bearing see hardware.washer_nut)"
    # 7 M5 washer does not bridge the groove
    cr = raw["cad_rules"]
    for k, s in enumerate(cr):
        if "bridges the groove" in s:
            o = s
            cr[k] = s.replace("the M5 rivet washer bridges the groove.",
                              "the M5 rivet backing washer (dia 15) does NOT bridge the groove when centred: its edge "
                              "lands on the groove's outer edge (r 7.5) and it bears ~%.0f mm2 on the dia-12.4 seat "
                              "inside the groove (%.0f-%.0f off-centre)." %
                              (bo["centred"]["M5"], bo["0.6 along"]["M5"], bo["1.5 along (slot end)"]["M5"]))
            chg("C7", "cad_rules[%d]" % k, o, cr[k])
    # 8 counterbore reference plane
    cb = raw["fasteners"]["counterbore"]
    t = math.tan(math.radians(1.0))
    wf, lf = 7.4 - 2 * 1.0 * t, 9.0 - 2 * 1.0 * t
    for nm in ("cb_w", "cb_l"):
        e = entry(cb, nm)
        o = e["note"]
        e["note"] = (o + "; reference plane Z_SHEET_BACK (F1-F4: the pad face). At F5-F8 there is no pad and the "
                         "counterbore opens at the flange front (1.0 deeper), where it measures %.3f x %.3f (1 deg "
                         "draft)" % (wf, lf))
        chg("C8", "fasteners.counterbore.%s.note" % nm, o, e["note"])
    # 9 clearance pocket reference level
    pk = HW["pocket"]
    rect = {r["name"]: r for r in raw["plan_rectangles"]}
    o = rect["pocket"]["note"]
    rect["pocket"]["note"] = (o + "; defined at Z_SEAT with 1 deg draft (opening to the front): 0.10 larger per side at "
                                  "the land (measured x0 %.3f at Z_LAND vs %.2f here). The land widths and bead_to_pocket "
                                  "values in 'lands' apply at Z_SEAT; at the land the minimum bead-to-pocket is %.2f "
                                  "(abs left; right %.2f, top %.2f; the bottom 1.40 is to the tail-pocket bottom face, "
                                  "which is defined at the land)" %
                                  (pk["at_land_Z+0.01"][0], rect["pocket"]["x0"],
                                   *pk["bead_to_pocket_at_land [left, right, top]"]))
    chg("C9", "plan_rectangles.pocket.note", o, rect["pocket"]["note"])
    for ln in raw["lands"]:
        if not ln["name"].startswith("bottom") and "Z_SEAT" not in ln["note"]:
            o = ln["note"]
            ln["note"] = o + " (at Z_SEAT; 0.10 less at the land, see plan_rectangles.pocket)"
            chg("C9", "lands.%s.note" % ln["name"], o, ln["note"])
    # 10 Formex outline
    fx = HW["formex"]
    raw["plan_rectangles"].append({
        "name": "formex", "x0": fx["x0"], "x1": fx["x1"], "y0": fx["y0"], "y1": fx["y1"], "R": fx["corner_R"][0],
        "unit": "mm", "z": fx["z"], "status": "carried over from v2",
        "note": "Formex insulating sheet as modelled in the assembly: panel outline - sheet_inset 0.5 per side, R1, "
                "Z_FORMEX_FRONT -5.0 .. Z_SEAT -4.6 (sheet_t 0.4) at every glass_t, PSA-bonded to the shelf; carried "
                "over from v2"})
    chg("C10", "plan_rectangles.formex", None, [fx["x0"], fx["x1"], fx["y0"], fx["y1"], fx["corner_R"][0], fx["z"]],
        "added")
    # 11 venting / exclusion zones
    vent = ("GF-1.1 round 3 (moulding): the lip top, the lip faces, the seat ring, the pads (F1-F4 hard-stop faces) and "
            "the land are exclusion zones for gates, ejector marks and parting lines; vent witness on the lip top is "
            "allowed only if flush within 0.02 (toolmaker to propose); this supersedes 'vents at the lip top every ~50 "
            "mm' in the concept text (concept.md).")
    cr.append(vent)
    dt["frame"].append({"name": "vent_witness_lip_top", "value": 0.02, "unit": "mm",
                        "note": "flush within 0.02 if any vent witness is on the lip top (toolmaker to propose); gates, "
                                "ejector marks and parting lines not on the lip top / lip faces / seat ring / pads / land"})
    chg("C11", "cad_rules (+1), drawing_tolerances.frame.vent_witness_lip_top", None, vent, "added")
    # 4 as-modelled volume / mass (already the 7.4 x 9.0 build since round 2)
    am = raw["as_modelled_GF-1.1"]
    if abs(am["frame_volume_cm3"] - 82.188) > 1e-6 or abs(am["frame_mass_g_at_1.36"] - 111.8) > 1e-6:
        o = [am["frame_volume_cm3"], am["frame_mass_g_at_1.36"]]
        am["frame_volume_cm3"], am["frame_mass_g_at_1.36"] = 82.188, 111.8
        chg("C4", "as_modelled_GF-1.1", o, [82.188, 111.8])
    am["note"] = ("measured on the GF-1.1 Fusion model (document 'Rev3.0 GlassFront', counterbore 7.4 x 9.0, v13 = the "
                  "verified frame STEP sha256 47742d2f...); GF-1.0 model 84.0 cm3 / 114 g")
    raw["change_log"]["round_3"] = {
        "date": "2026-11-15", "by": "gf11_params_round3.py",
        "what": "bookkeeping after the independent re-verification (84 pass / 0 fail) and the drawings review; frame "
                "geometry frozen and unchanged; hardware bodies R4 (dia-14 large-flange rivet head) and S8 (DIN 988 7 x "
                "13 x 1.0) updated in the assembly",
        "item_C4": "as_modelled_GF-1.1 already showed the 7.4 x 9.0 build (82.188 cm3 / 111.8 g) since round 2; note "
                   "updated only",
        "washer_bearing_offsets_mm2": bo, "changes": log}
    json.dump(raw, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.load(open(P, encoding="utf-8"))
    print("written", P, len(log), "changes")


if __name__ == "__main__":
    main()
