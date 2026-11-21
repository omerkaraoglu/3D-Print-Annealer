"""EMC-fix schematic rounds (2026-11-21), built on the 2026-11-13 tidy tooling (builder + layout scripts + checks).

    python -I prepare_base.py                      # once: pre-round sheets from git + baseline netlist/ERC (work area)
    set EMC_ROUND=1 | 2                            # 1 = phase 1 as written 2026-11-21; 2 (default) = + U5 MOC3083, R4 0603
    python -I emc_round.py <out_dir> [--repro]     # --repro: no changes at all (reproduces the pre-round drawing)
    python -I checks.py <project_dir> netlist erc pdf collide render bom ids

Builds the root and Display sheets from the pre-round copies against the pre-round netlist; Thermocouple, Power and
InputFilter are copied unchanged. newparts.apply() adds C9, D6, RV3 (root), C134, C135 (Display), removes RV2 and, in
round 2, swaps U5 to Relay_SolidState:MOC3083M and R4 to 0603; fields.py sets values / MPNs from bom_ozdisan_input.json
(update_bom_json.py <json> 1|2 makes the round's JSON). Both rounds were checked to reproduce the files (geomdiff.py: 0)."""
import importlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import FILES, BASELINE, BACKUP, Target, RENAME  # noqa: E402
from builder import Builder  # noqa: E402
import fields  # noqa: E402

MODULES = {"root": "lay_root", "Display": "lay_display"}
BASES = {"root": 101, "Display": 201, "Thermocouple": 401, "Power": 501, "InputFilter": 601}
PROJECT_TITLE = "3D Printer Filament Dryer & Print Annealer"
AUTHOR = "M. Ömer Karaoğlu"


def main(out, repro):
    os.environ["EMC_REPRO"] = "1" if repro else ""
    target = Target(os.path.join(BASELINE, "baseline.xml"), BASELINE, RENAME)
    os.makedirs(out, exist_ok=True)
    builders = {sh: Builder(sh, os.path.join(BACKUP, FILES[sh]), target, BASES[sh], BASES[sh]) for sh in MODULES}
    if not repro:
        import newparts
        for line in newparts.apply(builders, target):
            print("  parts:", line)
    log, table = fields.apply({sh: b.doc for sh, b in builders.items()}, repro=repro)
    for line in log:
        print("  fields:", line)
    total = 0
    regions = {}
    for sh in FILES:
        dst = os.path.join(out, FILES[sh])
        if sh not in builders:
            shutil.copyfile(os.path.join(BACKUP, FILES[sh]), dst)
            continue
        b = builders[sh]
        mod = importlib.import_module(MODULES[sh])
        meta = mod.build(b, table)
        if meta.get("shift"):
            dx, dy = meta["shift"]
            b.translate(dx, dy)
            meta["regions"] = [(n, x0 + dx, y0 + dy, x1 + dx, y1 + dy) for n, x0, y0, x1, y1 in meta.get("regions", [])]
        problems = b.finish()
        for w in b.warn:
            print("  [%s] warn: %s" % (sh, w))
        for p in problems:
            print("  [%s] PROBLEM: %s" % (sh, p))
        total += len(problems)
        b.write(dst, meta["paper"], PROJECT_TITLE + " - " + meta["name"], [meta["c1"], meta["c2"], AUTHOR],
                date=meta.get("date", "2026-11-13"))
        regions[sh] = meta.get("regions", [])
        print("%s: %d symbols, %d wires, %d labels, %d power, %d junctions, %d NC, %d texts -> %s" % (
            sh, len(b.doc.symbols), len(b.wires), len(b.labels), len(b.powers), len(b.junctions), len(b.ncs), len(b.texts), dst))
    json.dump(regions, open(os.path.join(os.environ.get("TIDY_OUT", out), "tidy_regions.json"), "w"), indent=1)
    print("sheet-level problems:", total)
    return total


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1], "--repro" in sys.argv) else 0)
