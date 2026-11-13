"""Write a staged board: text patch of orig/3dFilamentDryer.kicad_pcb (CRLF kept, nothing re-serialised).

Changes exactly these things:
  - every placed footprint's (property "Reference" ...) block: (at x y angle) in footprint coordinates,
    (layer "F.SilkS"), no (hide yes), font size / thickness, no (justify ...) (= centre / centre, not mirrored);
    footprints without a placement (H1-H9, DS1) are left as they are (reference hidden);
  - the old board texts listed in labels.json "delete" are removed;
  - new board-level items, inserted after the last existing board graphic, uuids derived from their names (uuid5) so
    every run gives the same file: the board legend and fabrication notes of labels.json (gr_text on F.SilkS /
    Cmts.User) and the legend-map graphics of placement.json (gr_rect / gr_line / gr_text on F.SilkS).
python refdes_apply.py <labels.json> <placement.json | -> <out.kicad_pcb>
"""
import json
import math
import os
import re
import shutil
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import GEOM, NAME, ORIG, ORIG_DIR  # noqa: E402

NS = uuid.UUID("6b1f3c2e-9a57-4f0e-8d3b-5c1a2e7f9b40")
NL = "\r\n"


def fmt(v):
    s = ("%.6f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def to_local(x, y, fx, fy, ang):
    t = math.radians(ang)
    dx, dy = x - fx, y - fy
    return dx * math.cos(t) - dy * math.sin(t), dx * math.sin(t) + dy * math.cos(t)


def patch_reference(block, ref, pl, fp):
    """block: the text of one (property "Reference" ...) s-expression (lines joined by CRLF)"""
    lines = block.split(NL)
    head = lines[0]
    assert head.strip() == '(property "Reference" "%s"' % ref, head
    ind = re.match(r"\t*", head).group(0)
    lx, ly = to_local(pl["x"], pl["y"], fp["pos"][0], fp["pos"][1], fp["ang"])
    out = [head]
    out.append(ind + "\t(at %s %s %s)" % (fmt(lx), fmt(ly), fmt(pl["ang"])))
    out.append(ind + '\t(layer "F.SilkS")')
    uu = [x for x in lines if x.strip().startswith("(uuid ")]
    assert len(uu) == 1, ref
    out.append(uu[0])
    for x in lines[1:]:
        s = x.strip()
        if s.startswith("(at ") or s.startswith("(layer ") or s.startswith("(uuid ") or s == "(hide yes)":
            continue
        if s.startswith("(unlocked") or s.startswith("(knockout"):
            out.append(x)
    out += [ind + "\t(effects", ind + "\t\t(font", ind + "\t\t\t(size %s %s)" % (fmt(pl["h"]), fmt(pl["w"])),
            ind + "\t\t\t(thickness %s)" % fmt(pl["t"]), ind + "\t\t)", ind + "\t)", ind + ")"]
    return NL.join(out)


def check_block_shape(block):
    """the original Reference block may only hold at / layer / hide / uuid / effects(font(size, thickness), justify)"""
    allowed = {"(property", "(at", "(layer", "(uuid", "(effects", "(font", "(size", "(thickness", "(justify",
               "(hide", ")", "(unlocked", "(knockout"}
    for x in block.split(NL):
        tok = x.strip().split(" ")[0]
        assert tok in allowed, "unexpected token in Reference block: %r" % x


def gr_item(g):
    u = uuid.uuid5(NS, g["name"])
    if g["kind"] == "rect":
        body = ["\t(gr_rect", "\t\t(start %s %s)" % (fmt(g["start"][0]), fmt(g["start"][1])),
                "\t\t(end %s %s)" % (fmt(g["end"][0]), fmt(g["end"][1])), "\t\t(stroke", "\t\t\t(width %s)" % fmt(g["width"]),
                "\t\t\t(type solid)", "\t\t)", "\t\t(fill no)", '\t\t(layer "F.SilkS")', '\t\t(uuid "%s")' % u, "\t)"]
    elif g["kind"] == "text":
        body = ['\t(gr_text "%s"' % g["text"], "\t\t(at %s %s %s)" % (fmt(g["pos"][0]), fmt(g["pos"][1]), fmt(g["ang"])),
                '\t\t(layer "%s")' % g.get("layer", "F.SilkS"), '\t\t(uuid "%s")' % u, "\t\t(effects", "\t\t\t(font",
                "\t\t\t\t(size %s %s)" % (fmt(g["h"]), fmt(g["w"])), "\t\t\t\t(thickness %s)" % fmt(g["t"]), "\t\t\t)"]
        if g.get("justify"):
            body.append("\t\t\t(justify %s)" % g["justify"])
        body += ["\t\t)", "\t)"]
    else:
        body = ["\t(gr_line", "\t\t(start %s %s)" % (fmt(g["start"][0]), fmt(g["start"][1])),
                "\t\t(end %s %s)" % (fmt(g["end"][0]), fmt(g["end"][1])), "\t\t(stroke", "\t\t\t(width %s)" % fmt(g["width"]),
                "\t\t\t(type solid)", "\t\t)", '\t\t(layer "F.SilkS")', '\t\t(uuid "%s")' % u, "\t)"]
    return NL.join(body)


def load_graphics(labels, PL):
    """every new board item, in file order: legend + notes first, then the legend-map graphics"""
    out = []
    for x in labels["texts"]:
        g = dict(x)
        g["kind"] = "text"
        out.append(g)
    if PL:
        out += PL["graphics"]
    return out


def main():
    labels = json.load(open(sys.argv[1], encoding="utf-8"))
    PL = json.load(open(sys.argv[2], encoding="utf-8")) if sys.argv[2] != "-" else None
    out = sys.argv[3]
    fps = {f["ref"]: f for f in json.load(open(GEOM, encoding="utf-8"))["fps"]} if PL else {}
    t = open(ORIG, encoding="utf-8", newline="").read()
    assert NL in t
    pieces, pos, done = [], 0, 0
    if PL:
        for m in re.finditer(r'\n(\t+)\(property "Reference" "([^"]+)"\r', t):
            ref = m.group(2)
            ind = m.group(1)
            s = m.start() + 1
            e = t.index("\n" + ind + ")\r\n", s) + len("\n" + ind + ")")
            block = t[s:e]
            pl = PL["refs"].get(ref)
            if pl is None:
                continue
            check_block_shape(block)
            pieces.append(t[pos:s])
            pieces.append(patch_reference(block, ref, pl, fps[ref]))
            pos = e
            done += 1
    pieces.append(t[pos:])
    t2 = "".join(pieces)
    removed = 0
    for u in labels["delete"]:                       # the old board texts
        k = t2.index('(uuid "%s")' % u)
        s = t2.rindex("\r\n\t(gr_text ", 0, k)
        e = t2.index("\r\n\t)", k) + len("\r\n\t)")
        assert t2[s:e].count("(gr_text ") == 1
        t2 = t2[:s] + t2[e:]
        removed += 1
    last = None                                      # new items after the last top-level gr_* item
    for m in re.finditer(r"\r\n\t\(gr_[a-z]+", t2):
        last = m
    assert last is not None
    end = t2.index("\r\n\t)\r\n", last.start()) + len("\r\n\t)")
    gfx = load_graphics(labels, PL)
    if gfx:
        t2 = t2[:end] + NL + NL.join(gr_item(g) for g in gfx) + t2[end:]
    assert t2.count("(") == t2.count(")")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="").write(t2)
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copyfile(os.path.join(ORIG_DIR, NAME + ext), os.path.join(os.path.dirname(out), NAME + ext))
    print("references patched: %d, old texts removed: %d, items added: %d -> %s" % (done, removed, len(gfx), out))


if __name__ == "__main__":
    main()
