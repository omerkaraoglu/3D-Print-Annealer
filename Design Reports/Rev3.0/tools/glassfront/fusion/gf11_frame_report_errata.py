"""Stage 3, lead round 4: errata for the VERIFIED Frame report (the report itself is not rewritten). Writes
Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_Frame_report_errata.json with the stale entries and the values measured
on the model (scan_gf11_cb74.json = 20_scan on the v13 frame; round3_hardware.json / docinfo_asm.json for the S8 shim).
Usage: python gf11_frame_report_errata.py"""
import hashlib
import json
import os

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront")
FR = os.path.join(MECH, "Rev3.0_GlassFront_Frame_report.json")
OUT = os.path.join(MECH, "Rev3.0_GlassFront_Frame_report_errata.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"


def main():
    rep = json.load(open(FR, encoding="utf-8"))
    scan = json.load(open(os.path.join(SCR, "scan_gf11_cb74.json")))
    hw = json.load(open(os.path.join(SCR, "gf11", "round3_hardware.json")))
    pv = {p["name"]: p for p in json.load(open(os.path.join(SCR, "docinfo_asm.json")))["user_parameters"]}
    roots = scan["unfilleted_concave_roots"]
    tp = sorted([r for r in roots if r["group"] == "tail pocket"], key=lambda r: r["mid_abs"][0])
    sb = sorted([r for r in roots if r["group"] == "shelf back"], key=lambda r: r["mid_abs"][0])
    sic = rep["sharp_inside_corners"]

    def idx(prefix):
        return next(i for i, c in enumerate(sic) if c["corner"].startswith(prefix))
    i_l, i_r = idx("tail-pocket corner left"), idx("tail-pocket corner right")
    i_sl, i_sr = idx("shelf back / bottom pocket wall, left"), idx("shelf back / bottom pocket wall, right")

    def seg(r):
        x0 = r["mid_abs"][0] - r["len_mm"] / 2
        return "y %.2f, x %.2f..%.2f" % (r["mid_abs"][1], x0, x0 + r["len_mm"])
    ch = rep["stage3_GF-1.1"]["changes"]
    i7 = next(i for i, c in enumerate(ch) if c["item"].startswith("7"))
    s8 = hw["S8"]["F5"]
    sid, sod = pv["spacer_id"]["value"], pv["spacer_od"]["value"]
    errata = [
        {"path": "sharp_inside_corners[%d].where_abs" % i_l, "reads": sic[i_l]["where_abs"],
         "correct": [round(v, 3) for v in tp[0]["mid_abs"][:2]], "z": tp[0]["z"],
         "why": "GF-1.1 item 4: tail-pocket side walls moved out 0.3 (the entry is the GF-1.0 position)"},
        {"path": "sharp_inside_corners[%d].where_abs" % i_r, "reads": sic[i_r]["where_abs"],
         "correct": [round(v, 3) for v in tp[1]["mid_abs"][:2]], "z": tp[1]["z"], "why": "as above"},
        {"path": "sharp_inside_corners[%d].where_abs" % i_sl, "reads": sic[i_sl]["where_abs"], "correct": seg(sb[0]),
         "why": "the shelf-back segment ends at the moved tail-pocket wall"},
        {"path": "sharp_inside_corners[%d].where_abs" % i_sr, "reads": sic[i_sr]["where_abs"], "correct": seg(sb[1]),
         "why": "as above"},
        {"path": "stage3_GF-1.1.changes[%d] (item 7: S8 spacer)" % i7,
         "reads": {"built": ch[i7]["built"], "parameters": ch[i7].get("parameters"), "numbers": ch[i7].get("numbers")},
         "correct": {"built": "DIN 988 %g x %g x 1.0 shim (spacer_id %g / spacer_od %g; lead round 3, first GF-1.1 build "
                              "6 x 12) on the stud between sheet and flange at F5-F8; bodies 'Spacer DIN 988 7x13x1.0 Fk'"
                              % (sid, sod, sid, sod),
                     "numbers": {"radial_clearance_to_flange_5.5": round((sid - 5.5) / 2, 3),
                                 "radial_clearance_to_flange_5.7": round((sid - 5.7) / 2, 3),
                                 "radial_clearance_to_envelope_5.8": round((sid - 5.8) / 2, 3),
                                 "contact_on_flange_front_mm2": s8["contact_on_flange_front_mm2"],
                                 "contact_on_sheet_mm2": s8["contact_on_sheet_mm2"]}},
         "why": "lead round 3 changed the S8 shim (hardware only, frame unchanged)"}]
    out = {"about": "Errata to Rev3.0_GlassFront_Frame_report.json, which stays byte-identical to the version written with "
                    "the independently verified frame STEP (sha256 47742d2f...). Correct values measured on the model "
                    "(v13 frame geometry = v14 document).",
           "frame_report_sha256": hashlib.sha256(open(FR, "rb").read()).hexdigest(),
           "sources": {"corners": "20_scan on the v13 frame (scan_gf11_cb74.json, unfilleted concave roots)",
                       "S8": "64_gf11_round3_hardware.py (round3_hardware.json) and the v14 user parameters"},
           "errata": errata}
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("written", OUT)
    for e in errata:
        print(e["path"], "|", str(e["reads"])[:80], "->", str(e["correct"])[:120])


if __name__ == "__main__":
    main()
