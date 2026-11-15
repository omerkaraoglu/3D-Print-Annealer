"""Stage 3, lead round 3 follow-up (params only, GF-1.1 kept): weld-stud specification tightened instead of the frozen
frame. Replaces the 'dia 5.9 x 1.5' limit in fasteners.hardware.stud.note by the lead's decision (flange incl. weld
collar / flash within dia 5.8 x 1.4 after welding; stud axis within +-0.3 of nominal relative to the cut-out) with the
clearances measured by 63 at dia 5.8 x 1.4 at the extreme stud positions (gf11\\extreme_stud_5p8x1p4.json) and the
5.9 x 1.5 / 5.7 x 1.4 results as the reason; adds the change to change_log.round_3. Refuses a second run.
Usage: python gf11_params_round3_stud.py"""
import json
import os

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront\gf11"


def worst(ex, f, k):
    s = ex["studs"][f]
    return min(v[k]["d_mm"] for n, v in s.items() if isinstance(v, dict) and "offset_mm" in v and v.get(k))


def main():
    raw = json.load(open(P, encoding="utf-8"))
    r3 = raw["change_log"]["round_3"]
    if "stud_envelope_decision" in r3:
        raise SystemExit("already applied")
    e58 = json.load(open(os.path.join(SCR, "extreme_stud_5p8x1p4.json")))
    e59 = json.load(open(os.path.join(SCR, "extreme_stud_5p9x1p5.json")))
    e57 = json.load(open(os.path.join(SCR, "extreme_stud_tape.json")))
    m = {f: {k: worst(e58, f, "flange_to_" + k) for k in ("wall", "floor_round", "floor")} for f in ("F1", "F5")}
    ov58 = max(v.get("stud_frame_overlap_mm3") or 0 for f in ("F1", "F5") for v in e58["studs"][f].values()
               if isinstance(v, dict))
    if min(m["F1"]["wall"], m["F1"]["floor_round"], m["F5"]["wall"]) < 0.03 or ov58 > 0:
        raise SystemExit("5.8 x 1.4 does not clear by 0.03: %s" % m)
    ov59 = max(v.get("stud_frame_overlap_mm3") or 0 for v in e59["studs"]["F1"].values() if isinstance(v, dict))
    st = next(h for h in raw["fasteners"]["hardware"] if h["name"] == "stud")
    old = st["note"]
    st["note"] = (
        "S4: F1-F4; S8: F1-F8. ISO 13918 PT M4 weld flange dia 5.3-5.7 x 0.7-1.4 sits in the fastener counterbore "
        "(GF-1.1). After welding, the stud flange INCLUDING weld collar and flash must lie within dia 5.8 x 1.4 high, and "
        "the stud axis must be within +-0.3 of its nominal position relative to the cut-out. Measured with the dia 5.8 x "
        "1.4 envelope and the stud against the slot wall / slot end (worst position, modelled): F1-F4 %.3f to the "
        "counterbore wall, %.3f to the R0.3 floor round, %.2f to the floor; F5-F8 %.3f / %.3f / %.2f; no overlap. Reason "
        "(frame frozen, so the stud spec is tightened): a dia 5.9 x 1.5 envelope touches the F1-F4 floor round with the "
        "stud against the slot wall (overlap <= %.4f mm3, ~0.04 deep); a clean dia 5.7 x 1.4 flange clears by %.2f (wall "
        "%.3f, floor round %.3f, floor %.2f)." %
        (m["F1"]["wall"], m["F1"]["floor_round"], m["F1"]["floor"], m["F5"]["wall"], m["F5"]["floor_round"],
         m["F5"]["floor"], ov59, min(worst(e57, "F1", "flange_to_wall"), worst(e57, "F1", "flange_to_floor_round")),
         worst(e57, "F1", "flange_to_wall"), worst(e57, "F1", "flange_to_floor_round"),
         worst(e57, "F1", "flange_to_floor")))
    r3["changes"].append({"item": "C5 (lead decision)", "path": "fasteners.hardware.stud.note", "old": old,
                          "new": st["note"], "note": "envelope dia 5.9 x 1.5 -> dia 5.8 x 1.4 + stud axis +-0.3"})
    r3["stud_envelope_decision"] = {
        "envelope": "dia 5.8 x 1.4 (flange incl. weld collar / flash, after welding)",
        "stud_axis_position": "+-0.3 of nominal relative to the cut-out",
        "measured_min_clearance_mm (63, stud at its extreme positions)": m,
        "rejected": "dia 5.9 x 1.5 (touches the F1-F4 floor round, overlap <= %.4f mm3)" % ov59}
    json.dump(raw, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.load(open(P, encoding="utf-8"))
    print("written", P, m)


if __name__ == "__main__":
    main()
