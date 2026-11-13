"""Rev3.0 front silkscreen artwork, step 2 of 2 (KiCad python), after art_gen.py.

Text patch of a staged board (CRLF kept, nothing re-serialised):
  - the legend texts the artwork replaces (art.json "replaces": the four title-block gr_text lines) are removed;
  - every artwork shape (outline + holes) is fractured into KiCad's single-outline form and appended as a filled
    gr_poly on F.SilkS (stroke 0) before the file tail; uuids are uuid5 of "art-<item>-<n>", so reruns give the
    same file.
The solder-mask colour is not touched (Battery Sentinel's script also turned it black; not wanted here).
"C:/Program Files/KiCad/10.0/bin/python.exe" art_apply.py <in.kicad_pcb> <out.kicad_pcb>
"""
import json
import os
import sys
import uuid

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from cfg import WORK  # noqa: E402

ART_JSON = os.path.join(WORK, "art", "art.json")
NS = uuid.UUID("6b1f3c2e-9a57-4f0e-8d3b-5c1a2e7f9b40")
mm = pcbnew.FromMM


def chain(pts):
    return pcbnew.SHAPE_LINE_CHAIN([pcbnew.VECTOR2I(mm(x), mm(y)) for x, y in pts], True)


def fractured(shape):
    ps = pcbnew.SHAPE_POLY_SET()
    ps.AddOutline(chain(shape["outline"]))
    for h in shape["holes"]:
        ps.AddHole(chain(h))
    ps.Fracture()
    out = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        out.append([(pcbnew.ToMM(o.CPoint(k).x), pcbnew.ToMM(o.CPoint(k).y)) for k in range(o.PointCount())])
    return out


def gr_poly(pts, u, nl):
    rows, row = [], []
    for x, y in pts:
        row.append("(xy %.4f %.4f)" % (x, y))
        if len(row) == 6:
            rows.append("\t\t\t" + " ".join(row))
            row = []
    if row:
        rows.append("\t\t\t" + " ".join(row))
    return nl.join(["\t(gr_poly", "\t\t(pts"] + rows + ["\t\t)", "\t\t(stroke", "\t\t\t(width 0)", "\t\t\t(type solid)",
                                                        "\t\t)", "\t\t(fill yes)", '\t\t(layer "F.SilkS")',
                                                        '\t\t(uuid "%s")' % u, "\t)"])


def main(src, out):
    art = json.load(open(ART_JSON, encoding="utf-8"))
    t = open(src, encoding="utf-8", newline="").read()
    nl = "\r\n"
    assert nl in t
    removed = 0
    for name in art["replaces"]:
        u = str(uuid.uuid5(NS, name))
        k = t.index('(uuid "%s")' % u)
        s = t.rindex(nl + "\t(gr_text ", 0, k)
        e = t.index(nl + "\t)", k) + len(nl + "\t)")
        assert t[s:e].count("(gr_text ") == 1
        t = t[:s] + t[e:]
        removed += 1
    blocks = []
    for it in art["items"]:
        n = 0
        for sh in it["shapes"]:
            for outline in fractured(sh):
                blocks.append(gr_poly(outline, uuid.uuid5(NS, "art-%s-%d" % (it["name"], n)), nl))
                n += 1
        it["gr_poly"] = n
    tail = "\t(embedded_fonts no)" + nl + ")" + nl
    assert t.endswith(tail), "unexpected board file tail"
    t = t[:-len(tail)] + nl.join(blocks) + nl + tail
    assert t.count("(") == t.count(")")
    open(out, "w", encoding="utf-8", newline="").write(t)
    b = pcbnew.LoadBoard(out)
    npoly = sum(1 for d in b.GetDrawings() if d.GetClass() == "PCB_SHAPE" and d.GetShape() == pcbnew.SHAPE_T_POLY
                and d.GetLayer() == pcbnew.F_SilkS)
    print("title texts removed: %d, artwork gr_poly added: %d (%s), reloaded: %d F.SilkS polygons -> %s" % (
        removed, len(blocks), ", ".join("%s %d" % (i["name"], i["gr_poly"]) for i in art["items"]), npoly, out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
