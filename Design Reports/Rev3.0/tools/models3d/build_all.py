"""Rebuild every Rev3.0 3D model, the display's mechanical footprint, the model
fields in Rev3.pretty and models.json, then re-import every STEP as a check.

  <venv>\\Scripts\\python.exe build_all.py            (see README.md)

Steps:
  1. dump_pads.py with KiCad's Python (read-only) -> pads.json
  2. every part script (CadQuery)                   -> Rev3.3dshapes/*.step + .wrl, renders, out/*.json
  3. make_mech_footprint.py                         -> Rev3.pretty/TFT7_SAT070AT40D21_Mech.kicad_mod
  4. set_model_fields.py                            -> (model ...) in the Rev3.pretty footprints
  5. make_models_json.py                            -> models.json for the board editor
  6. STEP re-import: bounding box of the file vs the script's own bounding box
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_PY = os.environ.get("KICAD_PYTHON", r"C:\Program Files\KiCad\10.0\bin\python.exe")
PARTS = ["l_pcd0403.py", "l_sri0605b.py", "l_rc1415u.py", "l_lfu09v103.py", "c_c42p2105kbs.py",
         "hs_sk409.py", "fpc_connectors.py", "tb_dg127h.py", "fuse_reomax_r3_5a.py",
         "solderwire_stub.py", "tft7_sat070at40d21.py"]


def sh(cmd):
    print(">>", " ".join(os.path.basename(c) if i == 1 else c for i, c in enumerate(cmd)))
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode:
        sys.exit("FAILED: %s" % cmd)


def main():
    if os.path.exists(KICAD_PY):
        sh([KICAD_PY, os.path.join(HERE, "dump_pads.py")])
    else:
        print("KiCad Python not found - using the existing pads.json")
    for p in PARTS:
        sh([sys.executable, os.path.join(HERE, p)])
    for p in ("make_mech_footprint.py", "set_model_fields.py", "make_models_json.py"):
        sh([sys.executable, os.path.join(HERE, p)])

    import warnings
    warnings.filterwarnings("ignore")
    import cadquery as cq
    print("\n%-62s %-6s %-28s %s" % ("model", "pins", "bbox X / Y / Z (mm)", "STEP re-import"))
    bad = 0
    for f in sorted(glob.glob(os.path.join(HERE, "out", "*.json"))):
        r = json.load(open(f))
        b = r["bbox"]
        s = cq.importers.importStep(r["files"]["step"]).val().BoundingBox()
        d = max(abs(s.xmin - b["xmin"]), abs(s.xmax - b["xmax"]), abs(s.ymin - b["ymin"]),
                abs(s.ymax - b["ymax"]), abs(s.zmin - b["zmin"]), abs(s.zmax - b["zmax"]))
        pins = "-" if "verify" not in r else ("PASS" if r["verify"]["ok"] else "FAIL")
        bad += pins == "FAIL" or d > 0.05
        print("%-62s %-6s %6.2f..%-6.2f %6.2f..%-6.2f %5.2f..%-6.2f  %s" % (
            r["name"], pins, b["xmin"], b["xmax"], b["ymin"], b["ymax"], b["zmin"], b["zmax"],
            "ok" if d <= 0.05 else "MISMATCH %.3f" % d))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
