"""Rev3.0 front silkscreen QR code, step 2 of 2 (KiCad python), after qr_gen.py.

Text patch of a board (CRLF kept, nothing re-serialised): every QR shape of qr.json (white outline + dark-module
holes) is fractured into KiCad's single-outline form (art_apply.fractured) and appended as a filled gr_poly on
F.SilkS (stroke 0) before the file tail; uuids are uuid5 of "qr-<item>-<n>", so reruns give the same file. Nothing
is removed. A board that already carries the QR (same uuids) is refused. The output is written to a temporary file
beside the target and moved into place (os.replace), so a concurrent reader never sees a half-written board.
"C:/Program Files/KiCad/10.0/bin/python.exe" qr_apply.py <in.kicad_pcb> <out.kicad_pcb>
"""
import json
import os
import sys
import uuid

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from cfg import WORK  # noqa: E402
from art_apply import NS, fractured, gr_poly  # noqa: E402

QR_JSON = os.path.join(WORK, "art", "qr.json")


def main(src, out):
    Q = json.load(open(QR_JSON, encoding="utf-8"))
    t = open(src, encoding="utf-8", newline="").read()
    nl = "\r\n"
    assert nl in t
    blocks, uuids = [], []
    for it in Q["items"]:
        n = 0
        for sh in it["shapes"]:
            for outline in fractured(sh):
                u = uuid.uuid5(NS, "qr-%s-%d" % (it["name"], n))
                blocks.append(gr_poly(outline, u, nl))
                uuids.append(str(u))
                n += 1
        it["gr_poly"] = n
    assert not any('(uuid "%s")' % u in t for u in uuids), "this board already carries the QR code"
    tail = "\t(embedded_fonts no)" + nl + ")" + nl
    assert t.endswith(tail), "unexpected board file tail"
    t = t[:-len(tail)] + nl.join(blocks) + nl + tail
    assert t.count("(") == t.count(")")
    tmp = out + ".qr_tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    os.replace(tmp, out)
    b = pcbnew.LoadBoard(out)
    mine = [d for d in b.GetDrawings() if d.m_Uuid.AsString() in set(uuids)]
    ok = all(d.GetClass() == "PCB_SHAPE" and d.GetShape() == pcbnew.SHAPE_T_POLY and d.GetLayer() == pcbnew.F_SilkS
             and d.IsAnyFill() for d in mine)
    print("QR v%d-%s %s: %d gr_poly appended on F.SilkS (%s), reloaded: %d found, filled F.SilkS polygons: %s -> %s" % (
        Q["version"], Q["error_level"], Q["url"], len(blocks),
        ", ".join("%s %d" % (i["name"], i["gr_poly"]) for i in Q["items"]), len(mine), ok, out))
    assert len(mine) == len(blocks) and ok


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
