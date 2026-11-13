"""KiCad DRC (--severity-all) of the original and of the stage with the project's own rules (.kicad_pro from HEAD and
.kicad_dru beside each board), zones as saved, saved as drc/drc_orig.json and drc/drc_stage.json, and compared item
by item (type + every item's description and position): drc/drc_compare.json. Exit code 1 if the stage has any item
the original does not have. Optional: python refdes_drc.py --refill (adds --refill-zones to both runs).
python refdes_drc.py [--refill] [board.kicad_pcb]   (a board given: one DRC of that board only, printed)
"""
import json
import os
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import CLI, ORIG, ROOT, STAGE  # noqa: E402


def run(board, out):
    a = [CLI, "pcb", "drc", "--format", "json", "--severity-all", "-o", out]
    if "--refill" in sys.argv:
        a.append("--refill-zones")
    subprocess.run(a + [board], check=True, capture_output=True, text=True)
    return json.load(open(out, encoding="utf-8"))


def keys(rep):
    out = Counter()
    for sec in ("violations", "unconnected_items", "schematic_parity"):
        for v in rep.get(sec, []):
            items = tuple(sorted((i["description"], round(i["pos"]["x"], 3), round(i["pos"]["y"], 3))
                                 for i in v.get("items", [])))
            out[(sec, v["type"], v.get("severity"), items)] += 1
    return out


def summary(rep):
    return {"violations": dict(Counter(v["type"] for v in rep["violations"])),
            "violations_total": len(rep["violations"]), "unconnected": len(rep["unconnected_items"]),
            "parity": len(rep["schematic_parity"])}


def main():
    d = os.path.join(ROOT, "drc")
    os.makedirs(d, exist_ok=True)
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if args:
        r = run(args[0], os.path.join(d, "drc_board.json"))
        print(args[0], summary(r))
        for v in r["violations"]:
            print("  ", v["severity"], v["type"], " | ".join(i["description"] for i in v["items"]))
        return
    a = run(ORIG, os.path.join(d, "drc_orig.json"))
    b = run(STAGE, os.path.join(d, "drc_stage.json"))
    ka, kb = keys(a), keys(b)
    new = kb - ka
    gone = ka - kb
    res = {"orig": summary(a), "stage": summary(b),
           "new_in_stage": [{"section": k[0], "type": k[1], "items": k[3], "count": n} for k, n in new.items()],
           "gone_in_stage": [{"section": k[0], "type": k[1], "items": k[3], "count": n} for k, n in gone.items()]}
    json.dump(res, open(os.path.join(d, "drc_compare.json"), "w", encoding="utf-8"), indent=1)
    print("original:", res["orig"])
    print("stage:   ", res["stage"])
    print("new items in the stage: %d, items gone: %d" % (sum(new.values()), sum(gone.values())))
    for x in res["new_in_stage"][:20]:
        print("   NEW", x)
    sys.exit(1 if new else 0)


if __name__ == "__main__":
    main()
