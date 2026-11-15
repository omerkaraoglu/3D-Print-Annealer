"""Regenerate the whole GF drawing set, render DXF previews, run the self-checks and write drawings_report.json.

  <venv>/Scripts/python.exe make_all.py
"""
import datetime
import hashlib
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import OUT_DIR, PARAMS_PATH, CHOICES_PATH, dxf_preview, Choices, Params
import make_sheet
import make_glass
import make_bonding
import make_jigs
import make_appearance
import make_frame
import selfcheck


def _np(o):
    if hasattr(o, "item"):
        return o.item()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _stud_envelope():
    """weld-stud requirement as drawn on GF-D01 / GF-D02, re-read from the master at the end of the run"""
    P = Params()
    rx = r"must lie within dia ([\d.]+) x ([\d.]+) high"
    return {"flange_envelope_dia": P.num("fasteners.hardware", rx, 1, name="stud"),
            "flange_envelope_height": P.num("fasteners.hardware", rx, 2, name="stud"),
            "axis_to_cut_out_tol": P.val("drawing_tolerances.sheet", "stud_position_tol"),
            "template_means": P.num("drawing_tolerances.sheet", r"with \+-([\d.]+) accuracy is the recommended means",
                                    name="stud_position_tol"),
            "perpendicularity_deg_P": Choices()("stud_perpendicularity_deg"),
            "read_from": "params fasteners.hardware[stud].note + drawing_tolerances.sheet.stud_position_tol"}


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    prev = os.path.join(OUT_DIR, "previews")
    os.makedirs(prev, exist_ok=True)
    master_hash_before = sha256(PARAMS_PATH)
    R = {}
    R["sheet"] = make_sheet.run()
    R["glass"] = make_glass.run()
    R["bonding"] = make_bonding.make()
    R["jigs"] = make_jigs.run()
    R["appearance"] = make_appearance.make()
    R["frame"] = make_frame.make()          # last: reads the params and the frame STEP at the end of the run
    # DXF previews rendered by ezdxf itself (independent of the matplotlib sheets)
    previews = []
    for f in sorted(os.listdir(OUT_DIR)):
        if f.lower().endswith(".dxf"):
            png = os.path.join(prev, f[:-4] + "_dxf.png")
            dxf_preview(os.path.join(OUT_DIR, f), png)
            previews.append(png)
    checks = selfcheck.run()
    master_hash_after = sha256(PARAMS_PATH)

    files = []

    def add(paths, what, by, res, extra=None):
        for p in paths:
            e = {"file": os.path.relpath(p, OUT_DIR).replace("\\", "/"), "what": what, "generated_by": by,
                 "bytes": os.path.getsize(p), "params_used": res.get("params_used", []),
                 "choices_used": sorted(res.get("choices_used", {}).keys()),
                 "layout_issues": res.get("layout_issues", [])}
            n = os.path.basename(p)
            if n in checks["dxf"]:
                e["checks"] = checks["dxf"][n]
            if n in checks["pdf"]:
                e["pdf"] = checks["pdf"][n]
            if extra:
                e.update(extra)
            files.append(e)

    for v, r in R["sheet"].items():
        add(r["files"], "oven front sheet cut-out, variant %s (DXF 1:1 front view + A3 drawing)" % v,
            "make_sheet.py", r, {"hole_table": r["hole_table"]})
    g = R["glass"]
    add(g["files"][:3], "cover glass: DXF (front view) + A3 drawing", "make_glass.py", g)
    add(g["files"][3:], "print artwork 1:1 vector PDF, seen from the printed face (mirrored)", "make_glass.py", g,
        {"artwork": g["artwork"]})
    add(R["bonding"]["files"], "bonding and assembly aids (frame front plan 1:1)", "make_bonding.py", R["bonding"],
        {"bead_path_mm": R["bonding"]["bead_path_mm"], "bead_volume_ml": R["bonding"]["bead_volume_ml"]})
    add(R["jigs"]["J2"]["files"], "jig J2 flush plate", "make_jigs.py", R["jigs"]["J2"])
    add(R["jigs"]["J1"]["files"], "jig J1 optical-bonding alignment fixture", "make_jigs.py", R["jigs"]["J1"])
    add(R["appearance"]["files"], "appearance sheet (colour, to scale)", "make_appearance.py", R["appearance"])
    fr = R["frame"]
    add(fr["files"], "frame inspection drawing GF-D50 (2 pages) for the mould RFQ", "make_frame.py", fr,
        {"step": fr["step"], "counterbore_params": fr["counterbore_params"],
         "counterbore_measured_on_step": fr["counterbore_measured"], "step_vs_master": fr["step_vs_master"]})
    for p in previews + [os.path.join(prev, "GF_Glass_Print_1to1_preview.png")]:
        files.append({"file": os.path.relpath(p, OUT_DIR).replace("\\", "/"), "what": "preview for checking only",
                      "generated_by": "make_all.py (ezdxf drawing add-on) / make_glass.py", "bytes": os.path.getsize(p)})

    C = Choices()
    layout_total = sum(len(f.get("layout_issues", [])) for f in files)
    report = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "master": {"path": PARAMS_PATH, "revision": Params().revision, "sha256": master_hash_before,
                   "unchanged_by_this_run": master_hash_before == master_hash_after},
        "drafting_choices": {"path": CHOICES_PATH, "items": C.raw["items"]},
        "python": sys.executable,
        "runtime_s": round(time.time() - t0, 1),
        "summary": {
            "dxf_all_ok": checks["dxf_all_ok"],
            "geometry_all_ok": checks["geometry_all_ok"],
            "mirroring_ok": checks["mirroring"]["ok"],
            "frame_step": R["frame"]["step"],
            "frame_counterbore": {"params": R["frame"]["counterbore_params"],
                                  "measured_on_step": R["frame"]["counterbore_measured"]},
            "frame_step_vs_master_all_ok": all(r["ok"] for r in R["frame"]["step_vs_master"]),
            "layout_issues_total": layout_total,
            "stud_envelope_drawn": _stud_envelope(),
            "pdf_pages": {k: v["pages"] for k, v in checks["pdf"].items()},
            "visual_review": "every PNG (and crops of it) looked at by the drafter after the last change; PNGs are "
                             "rendered from the same matplotlib figure as the PDF (Agg vs PDF backend, no PDF "
                             "rasteriser in the venv); DXFs additionally rendered by ezdxf into previews/",
        },
        "files": files,
        "self_checks": checks,
        "brand_logo_folder": g["brand_logo_folder"],
    }
    path = os.path.join(OUT_DIR, "drawings_report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False, default=_np)
    print("report:", path)
    print(json.dumps(report["summary"], indent=1, default=_np))
    return report


if __name__ == "__main__":
    main()
