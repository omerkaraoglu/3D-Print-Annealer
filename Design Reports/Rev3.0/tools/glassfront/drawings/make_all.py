"""Regenerate the whole GF drawing set (current master revision), render DXF previews, remove withdrawn outputs (only if the archive
holds an identical copy), run the self-checks and write drawings_report.json.

  <venv>/Scripts/python.exe make_all.py
"""
import datetime
import filecmp
import hashlib
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gf_common import (OUT_DIR, PARAMS_PATH, CHOICES_PATH, REPO, dxf_preview, Choices, Params, rev_note,
                       s8_withdrawn_rev)
import gf_draft
import make_sheet
import make_glass
import make_bonding
import make_jigs
import make_appearance
import make_tailgauge
import make_frame
import selfcheck

ARCHIVE = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront", "archive", "GF-1.1", "drawings")
WITHDRAWN = {"GF-D02": {"variant": "S8", "files": ["GF_Sheet_S8.dxf", "GF_Sheet_S8.pdf", "GF_Sheet_S8.png",
                                                   "previews/GF_Sheet_S8_dxf.png"],
                        "reason": "master sheet_variants.S8_withdrawn: 'WITHDRAWN at GF-2.0 (lead decision 3)'; "
                                  "nothing is moulded at F5-F8"}}
RENAMED = {"GF_Jig_J2.png": "GF-D30 is two sheets at GF-2.0: GF_Jig_J2_p1.png (plate) + GF_Jig_J2_p2.png "
                            "(tail handling)"}


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
    """weld-stud requirement as drawn on GF-D01, re-read from the master at the end of the run"""
    P = Params()
    rx = r"must lie within dia ([\d.]+) x ([\d.]+) high"
    return {"flange_envelope_dia": P.num("fasteners.hardware", rx, 1, name="stud"),
            "flange_envelope_height": P.num("fasteners.hardware", rx, 2, name="stud"),
            "axis_to_cut_out_tol": P.val("drawing_tolerances.sheet", "stud_position_tol"),
            "template_means": P.num("drawing_tolerances.sheet", r"with \+-([\d.]+) accuracy is the recommended means",
                                    name="stud_position_tol"),
            "perpendicularity_deg_P": Choices()("stud_perpendicularity_deg"),
            "read_from": "params fasteners.hardware[stud].note + drawing_tolerances.sheet.stud_position_tol"}


def remove_withdrawn():
    """delete withdrawn / renamed outputs from drawings/ - only where the GF-1.1 archive holds an identical copy"""
    out = {}
    names = [f for d in WITHDRAWN.values() for f in d["files"]] + list(RENAMED)
    for rel in names:
        p, a = os.path.join(OUT_DIR, rel), os.path.join(ARCHIVE, rel)
        if not os.path.exists(p):
            out[rel] = ("absent from drawings/ (removed by an earlier run of this script); GF-1.1 copy in "
                        "archive/GF-1.1/drawings/" if os.path.exists(a) else "absent; NOT in the archive")
        elif os.path.exists(a) and filecmp.cmp(p, a, shallow=False):
            os.remove(p)
            out[rel] = "removed from drawings/; identical copy kept in archive/GF-1.1/drawings/"
        else:
            out[rel] = "KEPT: no identical archive copy"
    return out


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    prev = os.path.join(OUT_DIR, "previews")
    os.makedirs(prev, exist_ok=True)
    master_hash_before = sha256(PARAMS_PATH)
    removed = remove_withdrawn()
    R = {}
    R["sheet"] = make_sheet.run()
    R["glass"] = make_glass.run()
    R["bonding"] = make_bonding.make()
    R["tailgauge"] = make_tailgauge.make()
    R["jigs"] = make_jigs.run()
    R["appearance"] = make_appearance.make()
    R["frame"] = make_frame.make()          # last: reads the params and the frame STEP at the end of the run
    previews = []
    for f in sorted(os.listdir(OUT_DIR)):
        if f.lower().endswith(".dxf"):
            png = os.path.join(prev, f[:-4] + "_dxf.png")
            dxf_preview(os.path.join(OUT_DIR, f), png)
            previews.append(png)
    checks = selfcheck.run()
    checks["stale_text"] = selfcheck.stale_text_scan(gf_draft.ALL_SHEETS)
    master_hash_after = sha256(PARAMS_PATH)

    files = []

    def add(paths, what, by, res, extra=None):
        for p in paths:
            e = {"file": os.path.relpath(p, OUT_DIR).replace("\\", "/"), "what": what, "generated_by": by,
                 "bytes": os.path.getsize(p), "layout_issues": res.get("layout_issues", [])}
            n_ = os.path.basename(p)
            if n_ in checks["dxf"]:
                e["checks"] = checks["dxf"][n_]
            if n_ in checks["pdf"]:
                e["pdf"] = checks["pdf"][n_]
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
    add(R["tailgauge"]["files"], "tail fold gauge and fold test (real-panel gate)", "make_tailgauge.py",
        R["tailgauge"], {"gauge": R["tailgauge"]["gauge"]})
    add(R["jigs"]["J2"]["files"], "jig J2 flush plate (sheet 1) + FPC tail handling (sheet 2)", "make_jigs.py",
        R["jigs"]["J2"], {"tail_handling": R["jigs"]["J2"]["tail_handling"]})
    add(R["jigs"]["J1"]["files"], "jig J1 optical-bonding alignment fixture", "make_jigs.py", R["jigs"]["J1"])
    add(R["appearance"]["files"], "appearance sheet (colour, to scale)", "make_appearance.py", R["appearance"])
    fr = R["frame"]
    add(fr["files"], "frame inspection drawing GF-D50 (2 pages) for the mould RFQ", "make_frame.py", fr,
        {"step": fr["step"], "counterbore_params": fr["counterbore_params"],
         "counterbore_measured_on_step": fr["counterbore_measured"], "step_vs_master": fr["step_vs_master"]})
    for p in previews + [os.path.join(prev, "GF_Glass_Print_1to1_preview.png")]:
        files.append({"file": os.path.relpath(p, OUT_DIR).replace("\\", "/"), "what": "preview for checking only",
                      "generated_by": "make_all.py (ezdxf drawing add-on) / make_glass.py", "bytes": os.path.getsize(p)})

    # ---- per drawing: number, title, revision, files, source values used, self-check result
    res_by_dwg = {"GF-D01": R["sheet"]["S4"], "GF-D03": R["sheet"]["R4"], "GF-D10": g, "GF-D11": g,
                  "GF-D20": R["bonding"], "GF-D21": R["tailgauge"], "GF-D30": R["jigs"]["J2"],
                  "GF-D31": R["jigs"]["J1"], "GF-D40": R["appearance"], "GF-D50": fr}
    files_by_dwg = {"GF-D01": R["sheet"]["S4"]["files"], "GF-D03": R["sheet"]["R4"]["files"],
                    "GF-D10": g["files"][:3], "GF-D11": g["files"][3:] + [os.path.join(prev,
                                                                                 "GF_Glass_Print_1to1_preview.png")],
                    "GF-D20": R["bonding"]["files"], "GF-D21": R["tailgauge"]["files"],
                    "GF-D30": R["jigs"]["J2"]["files"], "GF-D31": R["jigs"]["J1"]["files"],
                    "GF-D40": R["appearance"]["files"], "GF-D50": fr["files"]}
    sheets = {}
    for sh in gf_draft.ALL_SHEETS:
        sheets.setdefault(sh.dwg, []).append(sh)
    P0 = Params()
    drawings = {}
    for dwg in sorted(files_by_dwg):
        r = res_by_dwg[dwg]
        shs = sheets.get(dwg, [])
        fl = [os.path.relpath(p, OUT_DIR).replace("\\", "/") for p in files_by_dwg[dwg]]
        dxf_ok = [checks["dxf"][os.path.basename(p)]["ok"] for p in files_by_dwg[dwg]
                  if os.path.basename(p) in checks["dxf"]]
        pdfs = {os.path.basename(p): checks["pdf"][os.path.basename(p)]["pages"] for p in files_by_dwg[dwg]
                if os.path.basename(p) in checks["pdf"]}
        st = [checks["stale_text"]["sheets"]["%s %s" % (s.dwg, s.title)]["stale_hits"] for s in shs]
        lay = [i for s in shs for i in s.issues]
        # every sheet of the drawing must cite the params file by its sha256 (master_ref in the title block / header)
        cites = [any(master_hash_before[:16] in t for t in s.all_text()) for s in shs]
        drawings[dwg] = {
            "number": dwg,
            "title": " / ".join(s.title for s in shs) if shs else "GF-D11 PRINT ARTWORK 1:1 (A4, mirrored)",
            "revision": (shs[0].rev if shs else P0.revision), "revision_note": rev_note(P0),
            "params_sha256": master_hash_before, "sheets_cite_params_sha": cites,
            "files": fl, "pdf_pages": pdfs,
            "source_values_used": r.get("params_used", {}),
            "drafting_choices_used": sorted(r.get("choices_used", {}).keys()),
            "self_check": {"layout_issues": lay, "dxf_ok": all(dxf_ok) if dxf_ok else None,
                           "stale_text_hits": sum(len(x) for x in st), "cites_params_sha": bool(cites) and all(cites),
                           "ok": not lay and (all(dxf_ok) if dxf_ok else True) and not any(st) and bool(cites) and
                           all(cites)},
        }
    drawings["GF-D02"] = {"number": "GF-D02", "title": "OVEN FRONT SHEET - CUT-OUT S8", "revision": "GF-1.1 (last)",
                          "status": "WITHDRAWN at %s (still withdrawn at %s)" % (s8_withdrawn_rev(P0), P0.revision), "reason": WITHDRAWN["GF-D02"]["reason"],
                          "files": {k: removed.get(k) for k in WITHDRAWN["GF-D02"]["files"]},
                          "archived_in": os.path.relpath(ARCHIVE, REPO).replace("\\", "/")}

    C = Choices()
    layout_total = sum(len(d["self_check"]["layout_issues"]) for d in drawings.values() if "self_check" in d)
    report = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "master": {"path": PARAMS_PATH, "revision": P0.revision, "sha256": master_hash_before,
                   "unchanged_by_this_run": master_hash_before == master_hash_after},
        "revision_note": rev_note(P0),
        "drafting_choices": {"path": CHOICES_PATH, "items": C.raw["items"]},
        "python": sys.executable,
        "runtime_s": round(time.time() - t0, 1),
        "summary": {
            "drawings": {k: {"title": v.get("title"), "revision": v.get("revision"),
                             "status": v.get("status", "issued"), "self_check_ok": v.get("self_check", {}).get("ok")}
                         for k, v in sorted(drawings.items())},
            "dxf_all_ok": checks["dxf_all_ok"],
            "geometry_all_ok": checks["geometry_all_ok"],
            "mirroring_ok": checks["mirroring"]["ok"],
            "stale_text_ok": checks["stale_text"]["ok"],
            "params_sha256": master_hash_before,
            "all_sheets_cite_params_sha": all(d.get("self_check", {}).get("cites_params_sha", True)
                                              for d in drawings.values()),
            "frame_step": R["frame"]["step"],
            "frame_counterbore": {"params": R["frame"]["counterbore_params"],
                                  "measured_on_step": R["frame"]["counterbore_measured"]},
            "frame_step_vs_master_all_ok": all(r["ok"] for r in R["frame"]["step_vs_master"]),
            "frame_step_vs_master_checks": len(R["frame"]["step_vs_master"]),
            "layout_issues_total": layout_total,
            "stud_envelope_drawn": _stud_envelope(),
            "pdf_pages": {k: v["pages"] for k, v in checks["pdf"].items()},
            "withdrawn_and_renamed": removed,
            "visual_review": "every PNG (and crops of it) looked at by the drafter after the last change; PNGs are "
                             "rendered from the same matplotlib figure as the PDF (Agg vs PDF backend); DXFs "
                             "additionally rendered by ezdxf into previews/",
        },
        "drawings": drawings,
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
