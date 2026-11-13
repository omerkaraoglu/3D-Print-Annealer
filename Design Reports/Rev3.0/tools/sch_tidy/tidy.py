"""Driver of the 2026-11-13 schematic tidy round.

    python -I tidy.py <out_dir> <Rev3.kicad_sym path> [sheet ...]

Builds every listed sheet (default: all five) from the untouched backup copies in sch_tidy_backup/ (never from
the files it overwrites), applies the part substitutions / BOM fields (fields.py), runs the per-sheet layout
script (lay_*.py), checks the drawn connectivity against the baseline netlist and writes the sheet into
<out_dir>. Sheets not listed are copied unchanged from the backup. The project library gets Rev3:BOM_Item.
Writes <out_dir>/tidy_regions.json (group regions for the crop renders) and prints the per-sheet checks.
"""
import importlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import FILES, BASELINE, BACKUP, Target, RENAME  # noqa: E402
from builder import Builder  # noqa: E402
import fields  # noqa: E402
import bomitem  # noqa: E402
import libfix  # noqa: E402

MODULES = {"root": "lay_root", "Display": "lay_display", "Thermocouple": "lay_thermo", "Power": "lay_power",
           "InputFilter": "lay_filter"}
BASES = {"root": 101, "Display": 201, "Thermocouple": 401, "Power": 501, "InputFilter": 601}
PROJECT_TITLE = "3D Printer Filament Dryer & Print Annealer"
AUTHOR = "M. Ömer Karaoğlu"


def main(out, libpath, sheets):
    target = Target(os.path.join(BASELINE, "baseline.xml"), BASELINE, RENAME)
    os.makedirs(out, exist_ok=True)
    regions = {}
    builders = {}
    for sh in sheets:
        builders[sh] = Builder(sh, os.path.join(BACKUP, FILES[sh]), target, BASES[sh], BASES[sh])
    log, table = fields.apply({sh: b.doc for sh, b in builders.items()})
    for line in log:
        print("  fields:", line)
    bomitem.update_library(libpath)
    print("  library: %d footprint defaults aligned with the embedded copies" % libfix.fix_library(libpath))
    print("  library: SSD1963 top pins moved:", libfix.fix_ssd1963_library(libpath))
    if "Display" in builders:
        print("  Display: embedded SSD1963 top pins moved:", libfix.fix_ssd1963_embedded(builders["Display"].doc))
    if "root" in builders:
        print("  root: J2 embedded symbol replaced by the library copy:", libfix.fix_root_j2(builders["root"].doc))
    total = 0
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
        b.write(dst, meta["paper"], PROJECT_TITLE + " - " + meta["name"], [meta["c1"], meta["c2"], AUTHOR])
        regions[sh] = meta.get("regions", [])
        print("%s: %d symbols, %d wires, %d labels, %d power, %d junctions, %d NC, %d texts -> %s" % (
            sh, len(b.doc.symbols), len(b.wires), len(b.labels), len(b.powers), len(b.junctions), len(b.ncs), len(b.texts), dst))
    old = {}
    rp = os.path.join(os.environ.get("TIDY_OUT", out), "tidy_regions.json")
    if os.path.exists(rp):
        old = json.load(open(rp))
    old.update(regions)
    json.dump(old, open(rp, "w"), indent=1)
    print("sheet-level problems:", total)
    return total


if __name__ == "__main__":
    out, lib = sys.argv[1], sys.argv[2]
    sh = sys.argv[3:] or list(FILES)
    sys.exit(1 if main(out, lib, sh) else 0)
