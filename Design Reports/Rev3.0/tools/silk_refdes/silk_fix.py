"""Silk-only fixes of footprint instances on the board (owner request after the review of 2026-11-13), applied to the
staged board after refdes_apply.py; the KiCad libraries are not touched.

1. U5, U1 (DIP-6): the body side that crosses the 1.2 x 23.5 mm creepage slot (abs y 70.6..71.8, x 121.5..145.0)
   is split so its ink stays >= 0.30 mm from the slot edge (line centre at y <= 70.23 / >= 72.17, 0.12 mm stroke).
   The notch arc (pin-1 end) lies wholly inside that band (y 70.19..72.19) and is removed; a filled pin-1 triangle
   (0.4 x 0.5 mm, like KiCad's SMD pin-1 marks) is added next to pad 1 instead, outside the body outline.
2. J20: the pin-1 corner mark (an L of 0.15 mm lines beyond the body's top-right corner) ran over D220's outline and
   its pad 1: the horizontal leg is cut back to abs x 31.08 (ink >= 0.17 mm from D220's silk), the vertical leg, which
   lies between D220's outline and its pad, is removed. J20's body outline is unchanged.
3. .kicad_dru: Q1 sits on the HS1 plate by design (q1_on_heatsink_courtyard); the narrow rule DRU_RULE (F.SilkS to
   F.SilkS between Q1 and HS1 only, clearance 0, severity ignore) is inserted right after that rule in the copy
   beside <out>.
New items get uuid5 uuids (same namespace as refdes_apply.py), so reruns give the same file.
python silk_fix.py <in.kicad_pcb> <out.kicad_pcb>     (the .kicad_dru beside <out> is rewritten from orig/)
"""
import json
import math
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import GEOM, NAME, ORIG_DIR  # noqa: E402
from refdes_apply import NS, fmt, to_local  # noqa: E402

SLOT_LO, SLOT_HI = 70.23, 72.17          # keep line centres outside this band (slot y 70.6..71.8, +0.30 + 0.06 stroke)

SPLITS = [   # (ref, uuid, axis, keep-out band): an axis-parallel line split into the parts outside the band
    ("U5", "304f2721-3f9b-4c9d-9d2f-64b4fc8046f6", 1, (SLOT_LO, SLOT_HI)),
    ("U1", "3956b94b-e26b-436b-8957-5d6d1852da49", 1, (SLOT_LO, SLOT_HI)),
]
REMOVE = [
    ("U5", "bc108818-c86e-4328-b707-c49cb39374b6"),     # notch arc inside the slot band
    ("U1", "73ee4e64-7874-4891-b4b3-d1ac80337cee"),     # notch arc inside the slot band
    ("J20", "31555753-bc0e-431b-ae56-70dd9a09ce64"),    # pin-1 L, vertical leg over D220 pad 1
]
CLIPS = [    # (ref, uuid, axis, abs value): the end with the larger coordinate is moved back to it
    ("J20", "2996c8ee-bcdf-4e67-83ed-6878a4fdcfd3", 0, 31.08),   # pin-1 L, horizontal leg: stop short of D220
]
TRIANGLES = [  # (ref, name, abs points): pin-1 marks replacing the DIP notches
    ("U5", "U5-pin1", [(123.80, 75.00), (123.40, 74.75), (123.40, 75.25)]),
    ("U1", "U1-pin1", [(142.70, 67.38), (143.10, 67.13), (143.10, 67.63)]),
]


DRU_AFTER = "(rule \"q1_on_heatsink_courtyard\""
DRU_RULE = """# Q1's TO-220 outline lies on the HS1 plate outline by design (same case as the courtyard rule above): silk to silk
# between these two footprints only. A clearance of 0 alone does not do it (KiCad still reports touching silk as
# silk_overlap, and an unrestricted silk rule also starts checking silk against F.Fab / F.Courtyard), hence the layer
# condition and the ignore, as in q1_on_heatsink_courtyard.
(rule "q1_on_heatsink_silk"
   (constraint silk_clearance (min 0mm))
   (severity ignore)
   (condition "A.Layer == 'F.SilkS' && B.Layer == 'F.SilkS' && ((A.memberOfFootprint('Q1') && B.memberOfFootprint('HS1')) || (A.memberOfFootprint('HS1') && B.memberOfFootprint('Q1')))"))
"""


def write_dru(out):
    src = open(os.path.join(ORIG_DIR, NAME + ".kicad_dru"), encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in src else "\n"
    k = src.index(DRU_AFTER)
    # right after the q1 rule's last line
    end_q1 = src.index(nl, src.index("(condition ", k)) + len(nl)
    dst = src[:end_q1] + DRU_RULE.replace("\n", nl) + src[end_q1:]
    open(os.path.join(os.path.dirname(out), NAME + ".kicad_dru"), "w", encoding="utf-8", newline="").write(dst)


def from_local(lx, ly, fx, fy, ang):
    t = math.radians(ang)
    return fx + lx * math.cos(t) + ly * math.sin(t), fy - lx * math.sin(t) + ly * math.cos(t)


def block(t, u):
    """span of the fp_* block holding (uuid u)"""
    k = t.index('(uuid "%s")' % u)
    s = t.rindex("\t\t(fp_", 0, k)
    e = t.index("\n\t\t)", k) + len("\n\t\t)")
    return s, e


def xy(b, key):
    m = re.search(r"\(%s (-?[\d.]+) (-?[\d.]+)\)" % key, b)
    return float(m.group(1)), float(m.group(2))


def main():
    src, out = sys.argv[1], sys.argv[2]
    t = open(src, encoding="utf-8", newline="").read()
    NL = "\r\n" if "\r\n" in t else "\n"
    fps = {f["ref"]: f for f in json.load(open(GEOM, encoding="utf-8"))["fps"]}
    log = []
    for ref, u, ax, (lo, hi) in SPLITS:
        f = fps[ref]
        s, e = block(t, u)
        b = t[s:e]
        assert b.startswith("\t\t(fp_line") and '(layer "F.SilkS")' in b
        ls, le = xy(b, "start"), xy(b, "end")
        A = from_local(*ls, *f["pos"], f["ang"])
        B = from_local(*le, *f["pos"], f["ang"])
        if A[ax] > B[ax]:
            A, B, ls, le = B, A, le, ls

        def at(v):            # local point on the line where the absolute coordinate ax equals v
            r = (v - A[ax]) / (B[ax] - A[ax])
            return (ls[0] + r * (le[0] - ls[0]), ls[1] + r * (le[1] - ls[1]))
        p_lo, p_hi = at(lo), at(hi)
        b1 = re.sub(r"\(start [^)]*\)", "(start %s %s)" % (fmt(ls[0]), fmt(ls[1])), b, count=1)
        b1 = re.sub(r"\(end [^)]*\)", "(end %s %s)" % (fmt(p_lo[0]), fmt(p_lo[1])), b1, count=1)
        b2 = re.sub(r"\(start [^)]*\)", "(start %s %s)" % (fmt(p_hi[0]), fmt(p_hi[1])), b, count=1)
        b2 = re.sub(r"\(end [^)]*\)", "(end %s %s)" % (fmt(le[0]), fmt(le[1])), b2, count=1)
        b2 = b2.replace('(uuid "%s")' % u, '(uuid "%s")' % uuid.uuid5(NS, "silkfix-%s-split" % u))
        t = t[:s] + b1 + NL + b2 + t[e:]
        log.append("%s: line %s split at abs %s %.2f / %.2f" % (ref, u[:8], "xy"[ax], lo, hi))
    for ref, u in REMOVE:
        s, e = block(t, u)
        assert '(layer "F.SilkS")' in t[s:e]
        s2 = t.rindex(NL, 0, s)                   # drop the line break before the block too
        t = t[:s2] + t[e:]
        log.append("%s: %s removed" % (ref, u[:8]))
    for ref, u, ax, v in CLIPS:
        f = fps[ref]
        s, e = block(t, u)
        b = t[s:e]
        ls, le = xy(b, "start"), xy(b, "end")
        A = from_local(*ls, *f["pos"], f["ang"])
        B = from_local(*le, *f["pos"], f["ang"])
        key = "end" if B[ax] > A[ax] else "start"        # the end beyond v (towards D220) is moved back to v
        P0, P1, l0, l1 = (A, B, ls, le) if key == "end" else (B, A, le, ls)
        r = (v - P0[ax]) / (P1[ax] - P0[ax])
        p = (l0[0] + r * (l1[0] - l0[0]), l0[1] + r * (l1[1] - l0[1]))
        b = re.sub(r"\(%s [^)]*\)" % key, "(%s %s %s)" % (key, fmt(p[0]), fmt(p[1])), b, count=1)
        t = t[:s] + b + t[e:]
        log.append("%s: line %s %s moved to abs %s %.2f" % (ref, u[:8], key, "xy"[ax], v))
    for ref, name, pts in TRIANGLES:
        f = fps[ref]
        loc = [to_local(x, y, f["pos"][0], f["pos"][1], f["ang"]) for x, y in pts]
        u = uuid.uuid5(NS, "silkfix-" + name)
        poly = NL.join(["\t\t(fp_poly", "\t\t\t(pts",
                        "\t\t\t\t" + " ".join("(xy %s %s)" % (fmt(a), fmt(b)) for a, b in loc), "\t\t\t)",
                        "\t\t\t(stroke", "\t\t\t\t(width 0.1)", "\t\t\t\t(type solid)", "\t\t\t)", "\t\t\t(fill yes)",
                        '\t\t\t(layer "F.SilkS")', '\t\t\t(uuid "%s")' % u, "\t\t)"])
        # after the footprint's last F.SilkS graphic (the first split / kept outline line of that footprint)
        m = re.search(r'\(property "Reference" "%s"' % ref, t)
        fs = t.rindex("\n\t(footprint ", 0, m.start())
        fe = t.index("\n\t)", m.start())
        last = None
        for mm in re.finditer(r'\t\t\(fp_(line|arc|poly|rect|circle)', t[fs:fe]):
            s, e = block(t, re.search(r'\(uuid "([^"]+)"\)', t[fs + mm.start():]).group(1))
            if '(layer "F.SilkS")' in t[s:e]:
                last = e
        t = t[:last] + NL + poly + t[last:]
        log.append("%s: pin-1 triangle added at abs %s" % (ref, pts[0]))
    assert t.count("(") == t.count(")")
    open(out, "w", encoding="utf-8", newline="").write(t)
    write_dru(out)
    log.append("kicad_dru: rule q1_on_heatsink_silk inserted after q1_on_heatsink_courtyard")
    print("\n".join(log))


if __name__ == "__main__":
    main()
