"""Stage 3 follow-up (lead round 2): amend the GF-1.1 master params in place (same revision, no new revision):
counterbore 7.2 x 8.8 -> 7.4 x 9.0 (slot + 1.0 per side). Updates fasteners.counterbore (cb_w, cb_l, pad contact area,
new entries for the extreme-stud margins and the tape area over the F5-F8 openings), the matching cad_rules line,
as_modelled_GF-1.1 and the change_log entry of item '1 + amendment' (old value kept in its note). Backup of the
pre-round-2 file: %TEMP%\\rev3_glassfront\\stage2_dumps\\params_GF-1.1_round1.json. Values from
gf11\\as_modelled.json (57) and gf11\\extreme_stud_tape.json (63). Refuses if cb_w is already 7.4.
Usage: python gf11_params_round2.py"""
import json
import os
import shutil

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
P = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
BACKUP = os.path.join(SCR, "stage2_dumps", "params_GF-1.1_round1.json")
AM = json.load(open(os.path.join(SCR, "gf11", "as_modelled.json")))
EX = json.load(open(os.path.join(SCR, "gf11", "extreme_stud_tape.json")))


def entry(lst, name):
    for e in lst:
        if e.get("name") == name:
            return e
    raise KeyError(name)


def main():
    raw = json.load(open(P, encoding="utf-8"))
    if not str(raw.get("revision", "")).startswith("GF-1.1"):
        raise SystemExit("not GF-1.1")
    cb = raw["fasteners"]["counterbore"]
    if abs(entry(cb, "cb_w")["value"] - 7.4) < 1e-9:
        raise SystemExit("already 7.4 x 9.0")
    if not os.path.exists(BACKUP):
        shutil.copyfile(P, BACKUP)
    e = entry(cb, "cb_w")
    e["value"], e["note"] = 7.4, ("stadium width at the opening (Z_SHEET_BACK), coaxial with the slot = slot_w + 2 x 1.0 "
                                  "(lead round 2; first GF-1.1 build 7.2 = slot + 0.9)")
    e = entry(cb, "cb_l")
    e["value"], e["note"] = 9.0, ("stadium length at the opening, along the slot axis = slot_l + 2 x 1.0 (lead round 2; "
                                  "first GF-1.1 build 8.8)")
    e = entry(cb, "pad_contact_area_F1-F4")
    e["value"] = AM["pad_contact_area_mm2"]
    e["note"] = ("pad hard-stop face left round the counterbore (as modelled), annulus %.2f along / %.2f across the slot "
                 "(>= 3.0)" % (AM["pad_annulus_min"], AM["pad_annulus_across"]))
    s1, s5 = EX["studs"]["F1"], EX["studs"]["F5"]

    def worst(s, k):
        return min(v[k]["d_mm"] for n, v in s.items() if isinstance(v, dict) and k in v and v[k])
    cb.append({"name": "flange_clearance_extreme_stud", "value": {
        "F1-F4": {"to_wall": worst(s1, "flange_to_wall"), "to_floor_round": worst(s1, "flange_to_floor_round"),
                  "to_floor": worst(s1, "flange_to_floor")},
        "F5-F8": {"to_wall": worst(s5, "flange_to_wall"), "to_floor_round": worst(s5, "flange_to_floor_round"),
                  "to_floor": worst(s5, "flange_to_floor")}}, "unit": "mm",
        "note": "weld flange dia 5.7 x 1.4 (worst case), stud shank against the slot wall / slot end (modelled, measured "
                "face to face); ~0.15 at the opening, the minimum is at the flange top edge (1 deg draft + R0.3 round)"})
    tape = EX["tape_F5-F8"]
    cb.append({"name": "tape_over_opening_F5-F8_S4", "value": tape["F5"]["over_air_mm2"], "unit": "mm2",
               "note": "VHB strip area over the counterbore opening at each of F5-F8 (S4 variant; GF-1.0 slot %.2f); "
                       "4 positions %.1f of 7903 mm2 tape, %.1f more than GF-1.0" %
                       (tape["reference_at_flange_front"]["slot_5.4x7.0_GF-1.0_mm2"],
                        4 * tape["F5"]["over_air_mm2"], tape["lost_vs_GF-1.0_total_mm2"])})
    h6 = raw["corner_cell_H6"]
    if not any(e.get("name") == "h6_v_round" for e in h6):
        h6.append({"name": "h6_v_round", "value": 0.5, "unit": "mm",
                   "note": "the V where the H6 boss crosses the R2.5 corner arc is rounded by the R0.5 cell root fillet "
                           "(rolling ball, Z -7.44..0, sphere corner at the floor); left at R0.5 in round 2 (a larger "
                           "radius needs the edge split out of the 81-edge cell fillet = two features)"})
    cr = raw["cad_rules"]
    for i, s in enumerate(cr):
        if s.startswith("GF-1.1: fastener counterbores 7.2 x 8.8"):
            cr[i] = s.replace("7.2 x 8.8 stadium", "7.4 x 9.0 stadium (slot + 1.0 per side)")
    am = raw["as_modelled_GF-1.1"]
    am["frame_volume_cm3"], am["frame_mass_g_at_1.36"] = AM["frame_volume_cm3"], AM["frame_mass_g"]
    am["max_inscribed_sphere_mm"] = AM.get("max_sphere_dia") or am["max_inscribed_sphere_mm"]
    for c in raw["change_log"]["changes"]:
        if c["item"] == "1 + amendment":
            c["new"] = "added (7.4 x 9.0, floors 1.6 / 2.0, R0.3, 1 deg)"
            c["note"] = ("lead round 2 (2026-11-15): 7.2 x 8.8 (slot + 0.9) -> 7.4 x 9.0 (slot + 1.0 per side) for "
                         "weld-flash margin; same revision")
        if c["path"] == "as_modelled_GF-1.1":
            c["new"] = "%.2f cm3 / %.1f g" % (AM["frame_volume_cm3"], AM["frame_mass_g"])
    raw["change_log"]["round_2"] = {"date": "2026-11-15", "what": "counterbore 7.4 x 9.0 (+ measured extreme-stud "
                                                                  "clearances, tape over the F5-F8 openings, note on "
                                                                  "the H6 V round); no other geometry changed",
                                    "by": "gf11_params_round2.py"}
    json.dump(raw, open(P, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.load(open(P, encoding="utf-8"))
    print("written", P)


if __name__ == "__main__":
    main()
