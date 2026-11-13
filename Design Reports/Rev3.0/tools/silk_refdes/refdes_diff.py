"""Diff check: staged board against the untouched original, on the s-expression structure (python 3).

python refdes_diff.py [orig.kicad_pcb] [stage.kicad_pcb] [placement.json]

Allowed differences, and nothing else:
  A. inside a footprint: its (property "Reference" ...) block, and in it only (at ...), (layer ...), (hide ...) and
     (effects ...) (font size / thickness, justification); the property's name, text and uuid unchanged;
  B. new top-level gr_rect / gr_line / gr_text items whose uuids are the legend-map graphics of placement.json
     (F.SilkS) or the board legend / fabrication notes of labels.json (F.SilkS / Cmts.User);
  C. the old board texts listed in labels.json "delete" removed;
  D. in U1, U5, J20 (silk_fix.py) F.SilkS fp_line / fp_arc / fp_poly items split, cut, removed or added.
Every other top-level item (header, setup, nets, footprints, board graphics, tracks, vias, zones, ...) must be
byte-identical and in the same order. Writes work/diff.json, exit code 1 on any other difference.
"""
import json
import os
import re
import sys
import uuid
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import LABELS, ORIG, PLACEMENT, STAGE, WORK  # noqa: E402

NS = uuid.UUID("6b1f3c2e-9a57-4f0e-8d3b-5c1a2e7f9b40")
SILK_FIX_REFS = {"U1", "U5", "J20"}     # footprints whose library silk silk_fix.py edits


def children(t, s, e):
    """spans (start, end) of the direct child lists of the list t[s:e] (s at its '(')"""
    out = []
    i = s + 1
    depth = 0
    start = None
    instr = False
    while i < e - 1:
        c = t[i]
        if instr:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            if depth == 0:
                start = i
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                out.append((start, i + 1))
        i += 1
    return out


def head(x):
    m = re.match(r'\((\S+)(?:\s+"([^"]*)")?', x)
    return m.group(1), m.group(2)


def uuid_of(x):
    m = re.search(r'\(uuid "([^"]+)"\)', x)
    return m.group(1) if m else None


def own_uuid(t, sp):
    for a, b in children(t, *sp):
        x = t[a:b]
        if x.startswith("(uuid "):
            return uuid_of(x)
    return None


def main():
    orig = sys.argv[1] if len(sys.argv) > 1 else ORIG
    stage = sys.argv[2] if len(sys.argv) > 2 else STAGE
    plf = sys.argv[3] if len(sys.argv) > 3 else PLACEMENT
    PL = json.load(open(plf, encoding="utf-8"))
    LB = json.load(open(LABELS, encoding="utf-8"))
    want_gfx = {str(uuid.uuid5(NS, g["name"])): g for g in PL["graphics"]}
    art_file = os.path.join(WORK, "art", "art.json")
    ART = json.load(open(art_file, encoding="utf-8")) if os.path.exists(art_file) else {"replaces": [], "items": []}
    want_gfx.update({str(uuid.uuid5(NS, g["name"])): g for g in LB["texts"] if g["name"] not in ART["replaces"]})
    art_uuids = set()
    for it in ART["items"]:                  # front artwork gr_poly (art/art_apply.py)
        for n in range(2000):
            art_uuids.add(str(uuid.uuid5(NS, "art-%s-%d" % (it["name"], n))))
    qr_file = os.path.join(WORK, "art", "qr.json")
    QR = json.load(open(qr_file, encoding="utf-8")) if os.path.exists(qr_file) else {"items": []}
    qr_uuids = set()
    for it in QR["items"]:                   # QR code gr_poly (art/qr_apply.py)
        for n in range(2000):
            qr_uuids.add(str(uuid.uuid5(NS, "qr-%s-%d" % (it["name"], n))))
    art_uuids |= qr_uuids
    want_gfx.update({u: {"layer": "F.SilkS"} for u in art_uuids})
    deleted = set()
    A = open(orig, encoding="utf-8", newline="").read()
    B = open(stage, encoding="utf-8", newline="").read()
    ra, rb = A.index("(kicad_pcb"), B.index("(kicad_pcb")
    assert A[:ra] == B[:rb]
    ca = children(A, ra, len(A.rstrip()))
    cb = children(B, rb, len(B.rstrip()))
    bad, stats = [], Counter()
    ref_changes = Counter()
    seen_gfx = set()
    i = j = 0
    while i < len(ca) or j < len(cb):
        xa = A[ca[i][0]:ca[i][1]] if i < len(ca) else None
        xb = B[cb[j][0]:cb[j][1]] if j < len(cb) else None
        if xa is not None and xa == xb:
            stats["identical top-level items"] += 1
            i += 1
            j += 1
            continue
        if xa is not None and head(xa)[0] == "gr_text" and own_uuid(A, ca[i]) in LB["delete"]:
            deleted.add(own_uuid(A, ca[i]))
            stats["old board texts removed"] += 1
            i += 1
            continue
        if xb is not None and head(xb)[0] in ("gr_rect", "gr_line", "gr_text", "gr_poly") and \
                own_uuid(B, cb[j]) in want_gfx and \
                (xa is None or own_uuid(A, ca[i]) != own_uuid(B, cb[j])):
            u = own_uuid(B, cb[j])
            lay = want_gfx[u].get("layer", "F.SilkS")
            if '(layer "%s")' % lay not in xb or lay not in ("F.SilkS", "Cmts.User"):
                bad.append(("new graphic not on its layer", u))
            stats["new %s items%s" % (lay, " (QR gr_poly)" if u in qr_uuids else
                                      (" (artwork gr_poly)" if u in art_uuids else ""))] += 1
            if u in seen_gfx:
                bad.append(("duplicate new graphic", u))
            seen_gfx.add(u)
            j += 1
            continue
        if xa is not None and xb is not None and head(xa)[0] == "footprint" == head(xb)[0] and \
                own_uuid(A, ca[i]) == own_uuid(B, cb[j]):
            fa, fb = children(A, *ca[i]), children(B, *cb[j])
            ta = [A[s:e] for s, e in fa]
            tb = [B[s:e] for s, e in fb]
            # the footprint's own header (library id) must be the same
            if A[ca[i][0]:fa[0][0]] != B[cb[j][0]:fb[0][0]]:
                bad.append(("footprint header changed", own_uuid(A, ca[i])))
            fref = re.search(r'\(property "Reference" "([^"]+)"', A[ca[i][0]:ca[i][1]]).group(1)
            if fref in SILK_FIX_REFS:
                # silk_fix.py: F.SilkS fp_line / fp_arc / fp_poly of this footprint may be split, cut, removed or
                # added; everything else must stay, in order
                def silk(x):
                    return head(x)[0] in ("fp_line", "fp_arc", "fp_poly") and '(layer "F.SilkS")' in x
                ra = [x for x in ta if not silk(x)]
                rb = [x for x in tb if not silk(x)]
                ga = [x for x in ta if silk(x)]
                gb = [x for x in tb if silk(x)]
                stats["footprints with fixed library silk (silk_fix.py)"] += 1
                stats["  library silk items removed / changed"] += len([x for x in ga if x not in gb])
                stats["  library silk items added / changed"] += len([x for x in gb if x not in ga])
                ta, tb = ra, rb
                fa = [sp for sp in fa if not silk(A[sp[0]:sp[1]])]
                fb = [sp for sp in fb if not silk(B[sp[0]:sp[1]])]
            if len(ta) != len(tb):
                bad.append(("footprint child count changed", own_uuid(A, ca[i])))
            ref = None
            for xa2, xb2, sa, sb in zip(ta, tb, fa, fb):
                if xa2 == xb2:
                    continue
                ha, hb = head(xa2), head(xb2)
                if not (ha[0] == hb[0] == "property" and ha[1] == hb[1] == "Reference"):
                    bad.append(("footprint item changed", ha, own_uuid(A, ca[i])))
                    continue
                ref = re.match(r'\(property "Reference" "([^"]*)"', xa2).group(1)
                if re.match(r'\(property "Reference" "([^"]*)"', xb2).group(1) != ref:
                    bad.append(("reference text changed", ref))
                ka = {head(A[s:e])[0]: A[s:e] for s, e in children(A, *sa)}
                kb = {head(B[s:e])[0]: B[s:e] for s, e in children(B, *sb)}
                for k in sorted(set(ka) | set(kb)):
                    if ka.get(k) == kb.get(k):
                        continue
                    if k in ("at", "layer", "hide", "effects"):
                        ref_changes[k] += 1
                    else:
                        bad.append(("Reference property item changed", ref, k))
                if ka.get("uuid") != kb.get("uuid"):
                    bad.append(("Reference uuid changed", ref))
            stats["footprints with only the Reference changed"] += 1
            i += 1
            j += 1
            continue
        bad.append(("unexpected difference", head(xa) if xa else None, head(xb) if xb else None,
                    (own_uuid(A, ca[i]) if xa else None)))
        i += 1
        j += 1
        if len(bad) > 50:
            break
    if deleted != set(LB["delete"]):
        bad.append(("old texts not removed", sorted(set(LB["delete"]) - deleted)))
    missing = set(want_gfx) - seen_gfx - art_uuids
    if ART["items"] and not (seen_gfx & art_uuids):
        bad.append(("front artwork missing",))
    if QR["items"] and not (seen_gfx & qr_uuids):
        bad.append(("QR code missing",))
    if missing:
        bad.append(("legend graphics missing from the stage", sorted(missing)))
    tail_a = A[ca[-1][1]:] if ca else ""
    tail_b = B[cb[-1][1]:] if cb else ""
    if tail_a != tail_b:
        bad.append(("file tail changed",))
    res = {"orig": orig, "stage": stage, "top_level_items": {"orig": len(ca), "stage": len(cb)},
           "stats": dict(stats), "reference_property_items_changed": dict(ref_changes),
           "violations": [list(map(str, b)) for b in bad]}
    json.dump(res, open(os.path.join(WORK, "diff.json"), "w", encoding="utf-8"), indent=1)
    print("top-level items: orig %d, stage %d" % (len(ca), len(cb)))
    for k, v in stats.items():
        print("  %-46s %d" % (k, v))
    print("  Reference property items changed:", dict(ref_changes))
    print("other differences: %d" % len(bad))
    for b in bad[:20]:
        print("   ", b)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
