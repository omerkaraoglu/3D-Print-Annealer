"""Offline analysis of the Fusion fit-check output (scratchpad/cad/fit_frame_board.json from fusion/34, and
fit_parts.json from fusion/35): maps every board body to its KiCad reference (footprint id + nearest position,
from the v1 board_geom.json), lists the closest bodies, panel parts, tails, overlaps. Prints + writes
fit_summary.json next to the inputs."""
import json
import math
import os
import sys

SCR = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
       r"\scratchpad\cad")
GEOM = (r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame\out"
        r"\board_geom.json")
PANEL = {"lcm_0": "LCM", "pu_tape_1": "PU tape", "sensor_2": "CTP sensor", "cover_print_3": "cover glass (print)",
         "cover_va_4": "cover glass (VA)", "tft_tail_5": "TFT tail", "tft_fingers_6": "TFT fingers",
         "ctp_tail_7": "CTP tail", "ctp_fingers_8": "CTP fingers"}


def ref_of(path, bbox, fps):
    seg = path.split("+")
    model = seg[2].rsplit(":", 1)[0] if len(seg) > 2 else seg[-1].rsplit(":", 1)[0]   # footprint-level model
    for k, v in PANEL.items():
        if k in path:
            return "DS1", v
    if model.endswith("_PCB"):
        return "PCB", "board solid (core, z 0.08..1.55)"
    cx, cy = (bbox[0] + bbox[1]) / 2, (bbox[2] + bbox[3]) / 2
    cands = [f for f in fps if f["fpid"].split(":")[-1] == model] or fps
    best = min(cands, key=lambda f: math.hypot(f["x"] - cx, f["y"] - cy))
    return best["ref"], best["fpid"].split(":")[-1]


def main():
    fps = json.load(open(GEOM))["fps"]
    res = json.load(open(os.path.join(SCR, "fit_frame_board.json")))["results"]
    rows = []
    for r in res:
        ref, part = ref_of(r["path"], r["bbox"], fps)
        rows.append(dict(r, ref=ref, part=part, zmin=r["bbox"][4]))
    rows.sort(key=lambda r: r["d_mm"])
    comps = [r for r in rows if r["ref"] not in ("PCB", "DS1")]
    pcb = [r for r in rows if r["ref"] == "PCB"]
    ds1 = [r for r in rows if r["ref"] == "DS1"]
    inter = [r for r in rows if r.get("overlap_mm3", 0) and r["overlap_mm3"] > 1e-4]
    out = {"n_bodies": len(rows), "pcb_solid": pcb, "closest_components_15": comps[:15],
           "panel_parts": ds1, "intersections": inter,
           "n_component_bodies": len(comps), "components_min_mm": comps[0]["d_mm"] if comps else None}
    json.dump(out, open(os.path.join(SCR, "fit_summary.json"), "w"), indent=1)
    print("PCB:", [(r["d_mm"], r.get("overlap_mm3"), r["p_frame"]) for r in pcb])
    print("components: %d bodies, min %.3f" % (len(comps), comps[0]["d_mm"]))
    for r in comps[:18]:
        print("  %-6s %-42s d %6.3f  zmin %7.3f  at frame %s" % (r["ref"], r["part"][:42], r["d_mm"], r["zmin"],
                                                                   r["p_frame"]))
    for r in ds1:
        print("  DS1 %-20s d %6.3f overlap %s at frame %s" % (r["part"], r["d_mm"], r.get("overlap_mm3"),
                                                            r["p_frame"]))
    print("intersections:", [(r["ref"], r["part"], r["overlap_mm3"]) for r in inter])


if __name__ == "__main__":
    main()


LEADS = ["PS1", "HS1", "L40", "L1", "F1", "F3", "J20", "C40", "K1", "U1", "U5", "Q1"]


def parts():
    fps = json.load(open(GEOM))["fps"]
    d = json.load(open(os.path.join(SCR, "fit_parts.json")))
    sv = []
    for r in d["sheet_vs_board"]:
        ref, part = ref_of(r["path"], r["bbox"], fps)
        sv.append(dict(r, ref=ref, part=part))
    by_ref = {}
    for r in sv:
        if r["ref"] not in by_ref or r["d_mm"] < by_ref[r["ref"]]["d_mm"]:
            by_ref[r["ref"]] = r
    lead = {k: by_ref.get(k) for k in LEADS}
    acc = []
    for a in d["tool_access"]:
        n = a["nearest"]
        if n:
            ref, part = ref_of(n["path"], n["bbox"], fps)
            near3 = []
            for r in a.get("within_3mm", []):
                rf, pt = ref_of(r["path"], r["bbox"], fps)
                near3.append({"ref": rf, "part": pt, "d_mm": r["d_mm"], "overlap_mm3": r.get("overlap_mm3")})
            acc.append({"hole": a["hole"], "d_mm": n["d_mm"], "ref": ref, "part": part, "at": n["p_body"],
                        "bodies_checked_incl_DS1": a.get("n_checked"), "within_3mm": near3})
        else:
            acc.append({"hole": a["hole"], "d_mm": None, "ref": None, "part": "nothing within 25 mm (XY)"})
    out = {k: v for k, v in d.items() if k.endswith("frame")}
    out["lead_tips_vs_formex_sheet"] = {k: (None if v is None else {"d_mm": v["d_mm"], "part": v["part"],
                                                                   "zmin": v["bbox"][4],
                                                                   "overlap_mm3": v.get("overlap_mm3")})
                                        for k, v in lead.items()}
    out["sheet_closest_10"] = [{"ref": r["ref"], "part": r["part"], "d_mm": r["d_mm"], "zmin": r["bbox"][4]}
                               for r in sorted(by_ref.values(), key=lambda r: r["d_mm"])[:10]]
    out["tool_access"] = acc
    out["socket_vs_frame_wall_and_bosses"] = d.get("socket_vs_frame_wall")
    out["frame_volume_in_assembly_cm3"] = d.get("frame_volume_cm3")
    json.dump(out, open(os.path.join(SCR, "fit_parts_summary.json"), "w"), indent=1)
    for k, v in out["lead_tips_vs_formex_sheet"].items():
        print("lead %-5s %s" % (k, v))
    print("sheet closest:", [(r["ref"], r["d_mm"]) for r in out["sheet_closest_10"]])
    for a in acc:
        print("tool", a)


if __name__ == "__main__" and "--parts" in sys.argv:
    parts()
