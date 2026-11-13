"""Sheet builder: re-place the kept symbol instances, regenerate wires / labels / power symbols / junctions /
no-connects / notes from a layout script, check the drawn connectivity against the baseline netlist and write
the sheet (KiCad 10 format, CRLF).

Layout scripts use pins as "REF.NUM" strings and points as (x, y) tuples (mm, y down). The net of every pin
comes from the baseline netlist, so helpers never name nets: lab("R6.2") draws a stub and the label of R6.2's
baseline net (local or global as in the baseline), pw("C5.2") draws the power symbol of that pin's net.
"""
import copy
import os
import re
from collections import defaultdict

from core import (S, N, U, G, fmt, key, xf, find, first, dump, parse, Doc, LibSym, getprop, prop_node, on_seg,
                  sheet_clusters, PROJECT, NETPREFIX)

DIRS = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}
SUPPLY_DOWN = {"GND", "NEUT"}      # power symbols drawn pointing down (GND, and the mains return NEUT)


def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


def font():
    return [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]]]


class Builder:
    def __init__(self, sheet, path, target, pwr_base, flg_base):
        self.sheet = sheet
        self.doc = Doc(path, sheet)
        self.t = target
        self.placed = {}
        self.wires = []           # (a, b)
        self.labels = []          # (pt, kind, name, rot, shape)
        self.powers = []          # (pt, name, rot)
        self.ncs = []             # pt
        self.texts = []           # (x, y, s)
        self.rects = []           # (x1, y1, x2, y2, dashed)
        self.extra_syms = []      # extra symbol nodes (BOM items)
        self.pwr_n = pwr_base
        self.flg_n = flg_base
        self.used_pins = set()
        self.warn = []
        self.shapes = {}          # per-sheet global label shapes (input/output as seen from this sheet)

    # ------------------------------------------------------------------ placement
    def lib(self, ref):
        return self.doc.lib_of(ref)

    def place(self, ref, x, y, rot=0, mirror=None, f="R", hide_val=False, dx=None):
        """move symbol `ref` to (x, y, rot[, mirror]) and place Reference/Value by mode f:
        R / L: beside a vertical part (right / left), A / B: above / below a horizontal part, S: Ref above Value below,
        TL / TR / BL / BR: above/below the body corner (ICs), or a dict {"Reference": (x, y, just), "Value": ...}."""
        node = self.doc.symbols[ref]
        assert abs(snap(x) - x) < 1e-6 and abs(snap(y) - y) < 1e-6, (ref, x, y)
        at = first(node, "at")
        at[1], at[2] = N(x), N(y)
        if len(at) > 3:
            at[3] = N(rot)
        else:
            at.append(N(rot))
        for m in find(node, "mirror"):
            node.remove(m)
        if mirror:
            node.insert(node.index(at) + 1, [S("mirror"), S(mirror)])
        for fa in find(node, "fields_autoplaced"):
            node.remove(fa)
        self.placed[ref] = (x, y, rot, mirror)
        # pins on grid
        for num, p, o, pd in self.doc.pins_of(node):
            if abs(snap(p[0]) - p[0]) > 1e-3 or abs(snap(p[1]) - p[1]) > 1e-3:
                self.warn.append("%s.%s off grid at %s" % (ref, num, p))
        self.set_fields(ref, f, hide_val, dx)
        return self

    def body(self, ref):
        """sheet-coordinate bbox of the symbol body graphics (x1, y1, x2, y2)"""
        node = self.doc.symbols[ref]
        x, y, rot, mir, unit = self.doc.placement(node)
        lib = self.lib(ref)
        b = lib.body(unit)
        pts = [xf(px, py, rot, mir) for px, py in ((b[0], b[1]), (b[0], b[3]), (b[2], b[1]), (b[2], b[3]))]
        xs = [x + p[0] for p in pts]; ys = [y + p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def set_fields(self, ref, f, hide_val=False, dx=None):
        node = self.doc.symbols[ref]
        x, y, rot, mir = self.placed[ref]
        bx1, by1, bx2, by2 = self.body(ref)
        xc, yc = (bx1 + bx2) / 2, (by1 + by2) / 2
        w2, h2 = (bx2 - bx1) / 2, (by2 - by1) / 2
        if isinstance(f, dict):
            pos = f
        elif f in ("R", "L"):
            d = dx if dx is not None else (2.54 if w2 <= 1.1 else 3.81 if w2 <= 2.1 else snap(w2 + 1.9, 0.635))
            sx = 1 if f == "R" else -1
            just = "left" if f == "R" else "right"
            pos = {"Reference": (x + sx * d, y - 1.27, just), "Value": (x + sx * d, y + 1.27, just)}
        elif f in ("A", "B", "S"):
            d = dx if dx is not None else (2.54 if h2 <= 1.1 else 3.81 if h2 <= 2.1 else snap(h2 + 1.9, 0.635))
            if f == "A":
                pos = {"Reference": (x, y - d - 2.54, "center"), "Value": (x, y - d, "center")}
            elif f == "B":
                pos = {"Reference": (x, y + d, "center"), "Value": (x, y + d + 2.54, "center")}
            else:
                pos = {"Reference": (x, y - d, "center"), "Value": (x, y + d, "center")}
        elif f in ("TL", "TR", "BL", "BR"):
            d = dx if dx is not None else 1.905
            if f[0] == "T":
                ry, vy = by1 - d - 2.54, by1 - d
            else:
                ry, vy = by2 + d, by2 + d + 2.54
            if f[1] == "L":
                pos = {"Reference": (bx1, ry, "left"), "Value": (bx1, vy, "left")}
            else:
                pos = {"Reference": (bx2, ry, "right"), "Value": (bx2, vy, "right")}
        else:
            raise ValueError(f)
        fang = 90 if rot in (90, 270) else 0
        for p in find(node, "property"):
            name = p[1]
            if name in pos:
                fx, fy, just = pos[name]
                self._prop(p, fx, fy, fang, self._stored_just(just, rot, fang, mir),
                           hidden=(name == "Value" and hide_val))
            else:
                self._prop(p, x, y, fang, None, hidden=True)

    @staticmethod
    def _stored_just(just, rot, fang, mirror):
        if just in (None, "center"):
            return None
        inv = ((rot + fang) % 360) == 180
        if mirror == "y":
            inv = not inv                        # a mirrored symbol flips its stored justification on screen
        if inv:
            return {"left": "right", "right": "left"}[just]
        return just

    @staticmethod
    def _prop(p, x, y, ang, just, hidden):
        at = first(p, "at")
        at[1:] = [N(snap(x, 0.0001)), N(snap(y, 0.0001)), N(ang)]
        for h in [h for h in p if isinstance(h, list) and h and h[0] == "hide"]:
            p.remove(h)
        eff = first(p, "effects")
        for h in [h for h in eff if (isinstance(h, list) and h and h[0] in ("hide", "justify")) or h == S("hide")]:
            eff.remove(h)
        fnt = first(eff, "font")
        sz = first(fnt, "size")
        sz[1:] = [N(1.27), N(1.27)]
        for b in [b for b in fnt if isinstance(b, list) and b and b[0] in ("bold", "italic", "thickness")]:
            fnt.remove(b)
        if just:
            eff.append([S("justify"), S(just)])
        if hidden:
            p.insert(p.index(at) + 1, [S("hide"), S("yes")])

    def field_at(self, ref, name, x, y, just="left"):
        """override one field position after place()"""
        node = self.doc.symbols[ref]
        _, _, rot, mir = self.placed[ref]
        fang = 90 if rot in (90, 270) else 0
        self._prop(prop_node(node, name), x, y, fang, self._stored_just(just, rot, fang, mir), hidden=False)

    def hide_field(self, ref, name):
        p = prop_node(self.doc.symbols[ref], name)
        at = first(p, "at")
        if not any(isinstance(h, list) and h and h[0] == "hide" for h in p):
            p.insert(p.index(at) + 1, [S("hide"), S("yes")])

    def place_sheet(self, name, x, y, w=55.88, h=30.48):
        """move a hierarchical sheet symbol (no pins) and put Sheetname above / Sheetfile below it"""
        for sh in self.doc.sheets:
            pn = prop_node(sh, "Sheetname")
            if pn[2] != name:
                continue
            at = first(sh, "at"); sz = first(sh, "size")
            at[1:] = [N(x), N(y)]
            sz[1:] = [N(w), N(h)]
            for fa in find(sh, "fields_autoplaced"):
                sh.remove(fa)
            self._prop(pn, x, y - 1.27, 0, None, False)
            first(pn, "effects").append([S("justify"), S("left"), S("bottom")])
            pf = prop_node(sh, "Sheetfile")
            self._prop(pf, x, y + h + 1.27, 0, None, False)
            first(pf, "effects").append([S("justify"), S("left"), S("top")])
            self.sheet_boxes = getattr(self, "sheet_boxes", []) + [(x, y, x + w, y + h)]
            return
        raise KeyError(name)

    # ------------------------------------------------------------------ pins
    def pin(self, spec):
        ref, num = spec.rsplit(".", 1)
        node = self.doc.symbols[ref]
        assert ref in self.placed, "not placed: " + ref
        for n, p, o, pd in self.doc.pins_of(node):
            if n == num and not pd["hidden"]:
                return p, o
        for n, p, o, pd in self.doc.pins_of(node):
            if n == num:
                return p, o
        raise KeyError(spec)

    def P(self, spec):
        if isinstance(spec, str):
            return self.pin(spec)[0]
        return (round(spec[0], 4), round(spec[1], 4))

    def O(self, spec):
        return self.pin(spec)[1]

    def net(self, spec):
        ref, num = spec.rsplit(".", 1)
        return self.t.pin_net[(ref, num)]

    def off(self, spec, dx=0, dy=0):
        p = self.P(spec)
        return (round(p[0] + dx, 4), round(p[1] + dy, 4))

    # ------------------------------------------------------------------ drawing primitives
    def w(self, *pts):
        pts = [self.P(p) for p in pts]
        for a, b in zip(pts, pts[1:]):
            if key(a) == key(b):
                continue
            assert abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6, ("diagonal wire", a, b)
            for v in a + b:
                if abs(snap(v) - v) > 1e-3:
                    self.warn.append("wire off grid %s-%s" % (a, b))
            self.wires.append((a, b))
        for p in pts:
            pass
        return pts[-1]

    def wl(self, a, b, first="h"):
        """L-shaped connection a -> b; first = 'h' (horizontal leg first) or 'v'"""
        A, B = self.P(a), self.P(b)
        if abs(A[0] - B[0]) < 1e-6 or abs(A[1] - B[1]) < 1e-6:
            return self.w(A, B)
        c = (B[0], A[1]) if first == "h" else (A[0], B[1])
        return self.w(A, c, B)

    def stub(self, spec, L=G, d=None):
        p, o = self.pin(spec)
        if d:
            o = DIRS[d]
        e = (round(p[0] + o[0] * L, 4), round(p[1] + o[1] * L, 4))
        if L:
            self.w(p, e)
        return e

    def _dir_of(self, spec, d):
        if d:
            return DIRS[d]
        return self.O(spec)

    def lab_at(self, pt, d, net=None, spec=None, shape=None):
        """label for `net` (or the net of pin `spec`) at pt, text running in direction d (L/R/U/D)"""
        pt = self.P(pt)
        if net is None:
            net = self.net(spec)
        kind, name = self.t.kind(net, self.sheet)
        rot = {"R": 0, "U": 90, "L": 180, "D": 270}[d]
        if kind == "local":
            self.labels.append((pt, "label", name, rot, None))
        elif kind == "global":
            self.labels.append((pt, "global_label", name, rot, shape or self.shapes.get(name) or self.t.global_shapes[name]))
        else:
            raise ValueError("no label for %s (%s)" % (net, kind))
        return pt

    def lab(self, spec, L=5.08, d=None, shape=None):
        o = self._dir_of(spec, d)
        dd = {(-1, 0): "L", (1, 0): "R", (0, -1): "U", (0, 1): "D"}[tuple(o)]
        e = self.stub(spec, L, dd)
        return self.lab_at(e, dd, spec=spec, shape=shape)

    def ensure_lib(self, lid):
        """embed a library symbol that this sheet does not carry yet (copied from another backup sheet)"""
        if lid in self.doc.libs:
            return
        import os
        from core import FILES, BACKUP
        for fn in FILES.values():
            t = parse(open(os.path.join(BACKUP, fn), encoding="utf-8").read())
            for s in find(first(t, "lib_symbols"), "symbol"):
                if s[1] == lid:
                    first(self.doc.tree, "lib_symbols").append(s)
                    self.doc.libs[lid] = LibSym(s)
                    return
        raise KeyError(lid)

    def power(self, pt, name, rot=None):
        self.ensure_lib("power:" + name)
        pt = self.P(pt)
        if rot is None:
            rot = 180 if name == "NEUT" else 0
        self.powers.append((pt, name, rot))
        return pt

    def gnd(self, pt):
        return self.power(pt, "GND")

    def flag(self, pt):
        return self.power(pt, "PWR_FLAG")

    def pw(self, spec, L=G, d=None):
        """stub from the pin and the power symbol of its net at the end"""
        net = self.net(spec)
        kind, name = self.t.kind(net, self.sheet)
        assert kind == "power", (spec, net)
        o = self._dir_of(spec, d)
        dd = {(-1, 0): "L", (1, 0): "R", (0, -1): "U", (0, 1): "D"}[tuple(o)]
        e = self.stub(spec, L, dd)
        return self.power(e, name)

    def nc(self, spec):
        self.ncs.append(self.P(spec))

    def note(self, x, y, lines):
        """plain 1.27 mm text, left-bottom justified, one line per item, pitch 2.54 (first line at y)"""
        for i, s in enumerate(lines):
            self.texts.append((x, round(y + i * G, 4), s))

    def rect(self, x1, y1, x2, y2, dashed=True):
        self.rects.append((x1, y1, x2, y2, dashed))

    def translate(self, dx, dy):
        """shift everything drawn so far (symbols with their fields, wires, labels, power, NC, notes, frames)"""
        mv = lambda p: (round(p[0] + dx, 4), round(p[1] + dy, 4))
        for ref, (x, y, rot, mir) in list(self.placed.items()):
            node = self.doc.symbols[ref]
            at = first(node, "at")
            at[1], at[2] = N(x + dx), N(y + dy)
            for p in find(node, "property"):
                pa = first(p, "at")
                pa[1], pa[2] = N(float(pa[1]) + dx), N(float(pa[2]) + dy)
            self.placed[ref] = (round(x + dx, 4), round(y + dy, 4), rot, mir)
        self.wires = [(mv(a), mv(b)) for a, b in self.wires]
        self.labels = [(mv(p),) + tuple(r) for p, *r in self.labels]
        self.powers = [(mv(p),) + tuple(r) for p, *r in self.powers]
        self.ncs = [mv(p) for p in self.ncs]
        self.texts = [(x + dx, y + dy, t) for x, y, t in self.texts]
        self.rects = [(x1 + dx, y1 + dy, x2 + dx, y2 + dy, d) for x1, y1, x2, y2, d in self.rects]

    # ------------------------------------------------------------------ bulk helpers
    def auto(self, ref, nums=None, L=5.08, Lpwr=None, skip=()):
        """every listed (default: every visible, not yet used) pin of ref: NC flag / power symbol / label"""
        node = self.doc.symbols[ref]
        done = self.connected_pins()
        for n, p, o, pd in self.doc.pins_of(node):
            if pd["hidden"] or n in skip:
                continue
            if nums is not None and n not in nums:
                continue
            spec = "%s.%s" % (ref, n)
            if nums is None and spec in done:
                continue
            net = self.net(spec)
            kind, name = self.t.kind(net, self.sheet)
            if kind == "nc":
                self.nc(spec)
            elif kind == "power":
                self.pw(spec, Lpwr or L)
            elif kind in ("local", "global"):
                self.lab(spec, L)
            else:
                self.warn.append("auto: %s on auto net %s needs a wire" % (spec, net))

    def connected_pins(self):
        pts = set()
        for a, b in self.wires:
            pts.add(key(a)); pts.add(key(b))
        for p, *_ in self.labels:
            pts.add(key(p))
        for p, *_ in self.powers:
            pts.add(key(p))
        for p in self.ncs:
            pts.add(key(p))
        out = set()
        for ref in self.placed:
            for n, p, o, pd in self.doc.pins_of(self.doc.symbols[ref]):
                if key(p) in pts:
                    out.add("%s.%s" % (ref, n))
        return out

    # ------------------------------------------------------------------ finish: split, junctions, check
    def all_pins(self):
        out = []
        for ref in self.doc.symbols:
            if ref not in self.placed:
                continue
            for n, p, o, pd in self.doc.pins_of(self.doc.symbols[ref]):
                out.append((p, (ref, n), pd))
        return out

    def finish(self):
        assert set(self.placed) == set(self.doc.symbols), ("unplaced", sorted(set(self.doc.symbols) - set(self.placed)))
        # NC flags for single-pin unconnected nets that are not drawn yet (visible pins only)
        have = self.connected_pins()
        for p, (ref, n), pd in self.all_pins():
            net = self.t.pin_net.get((ref, n))
            if net and net.startswith("unconnected-") and not pd["hidden"] and "%s.%s" % (ref, n) not in have:
                self.ncs.append(p)
        # split wires at every connection point on their interior
        cpts = set()
        for a, b in self.wires:
            cpts.add(key(a)); cpts.add(key(b))
        for p, *_ in self.labels:
            cpts.add(key(p))
        for p, *_ in self.powers:
            cpts.add(key(p))
        for p, *_ in self.all_pins():
            cpts.add(key(p))
        out = []
        for a, b in self.wires:
            inner = [p for p in cpts if p != key(a) and p != key(b) and on_seg(p, a, b)]
            seq = sorted(inner, key=lambda p: abs(p[0] - a[0]) + abs(p[1] - a[1]))
            pts = [a] + seq + [b]
            for u, v in zip(pts, pts[1:]):
                out.append((u, v))
        # remove duplicate / overlapping collinear segments
        seen = set()
        uniq = []
        for a, b in out:
            k = tuple(sorted([key(a), key(b)]))
            if k in seen:
                self.warn.append("duplicate wire %s" % (k,))
                continue
            seen.add(k)
            uniq.append((a, b))
        self.wires = uniq
        for i, (a, b) in enumerate(self.wires):
            for c, d in self.wires[i + 1:]:
                if self._overlap(a, b, c, d):
                    self.warn.append("overlapping wires %s-%s / %s-%s" % (a, b, c, d))
        # junctions where >= 3 items meet
        cnt = defaultdict(int)
        for a, b in self.wires:
            cnt[key(a)] += 1; cnt[key(b)] += 1
        for p, *_ in self.powers:
            cnt[key(p)] += 1
        for p in {(key(p), rn[0]) for p, rn, pd in self.all_pins()}:
            cnt[p[0]] += 1
        self.junctions = [p for p, n in cnt.items() if n >= 3]
        # dangling wire ends (a wire end that touches nothing else)
        ends = defaultdict(int)
        for a, b in self.wires:
            ends[key(a)] += 1; ends[key(b)] += 1
        lab = {key(p) for p, *_ in self.labels}
        for p, n in ends.items():
            if n == 1 and cnt[p] == 1 and p not in lab:
                self.warn.append("dangling wire end at %s" % (p,))
        # wires through symbol bodies
        for ref in self.placed:
            bx1, by1, bx2, by2 = self.body(ref)
            for a, b in self.wires:
                if self._seg_hits_box(a, b, (bx1 + 0.3, by1 + 0.3, bx2 - 0.3, by2 - 0.3)):
                    self.warn.append("wire %s-%s crosses body of %s" % (a, b, ref))
        # pins of different symbols on the same point
        pp = defaultdict(list)
        for p, rn, pd in self.all_pins():
            if not pd["hidden"]:
                pp[key(p)].append(rn)
        for p, l in pp.items():
            if len({r for r, n in l}) > 1:
                self.warn.append("pins touching at %s: %s" % (p, l))
        return self.check()

    @staticmethod
    def _overlap(a, b, c, d):
        if abs(a[0] - b[0]) < 1e-6 and abs(c[0] - d[0]) < 1e-6 and abs(a[0] - c[0]) < 1e-6:
            lo1, hi1 = sorted([a[1], b[1]]); lo2, hi2 = sorted([c[1], d[1]])
            return min(hi1, hi2) - max(lo1, lo2) > 1e-6
        if abs(a[1] - b[1]) < 1e-6 and abs(c[1] - d[1]) < 1e-6 and abs(a[1] - c[1]) < 1e-6:
            lo1, hi1 = sorted([a[0], b[0]]); lo2, hi2 = sorted([c[0], d[0]])
            return min(hi1, hi2) - max(lo1, lo2) > 1e-6
        return False

    @staticmethod
    def _seg_hits_box(a, b, box):
        x1, y1, x2, y2 = box
        if x1 >= x2 or y1 >= y2:
            return False
        if abs(a[1] - b[1]) < 1e-6:
            lo, hi = sorted([a[0], b[0]])
            return y1 < a[1] < y2 and lo < x2 and hi > x1
        lo, hi = sorted([a[1], b[1]])
        return x1 < a[0] < x2 and lo < y2 and hi > y1

    def check(self):
        """sheet-level connectivity vs the baseline: no shorts, every drawn cluster carries the right name"""
        points = []
        for p, (ref, n), pd in self.all_pins():
            points.append((p, ("pin", ref, n)))
        for i, (p, kind, name, rot, shape) in enumerate(self.labels):
            points.append((p, (kind, name, i)))
        for i, (p, name, rot) in enumerate(self.powers):
            points.append((p, ("pwr", name, i)))
        cl, _ = sheet_clusters(self.wires, points, self.junctions)
        members = defaultdict(list)
        for tag, cid in cl.items():
            members[cid].append(tag)
        problems = []
        for cid, tags in members.items():
            pins = [(t[1], t[2]) for t in tags if t[0] == "pin"]
            nets = {self.t.pin_net.get(p, "?") for p in pins}
            names = set()
            for t in tags:
                if t[0] == "pwr" and t[1] != "PWR_FLAG":
                    names.add(t[1])
                elif t[0] == "global_label":
                    names.add(t[1])
                elif t[0] == "label":
                    names.add(NETPREFIX[self.sheet] + t[1])
            if len(nets) > 1:
                problems.append("SHORT %s: %s" % (sorted(nets), sorted(pins)))
            if len(names) > 1:
                problems.append("MULTI-NAME %s on %s" % (sorted(names), sorted(pins)))
            if nets and len(nets) == 1:
                net = next(iter(nets))
                if names and net not in names:
                    problems.append("WRONG NAME %s for net %s" % (sorted(names), net))
            if not pins and len(tags) == 1 and tags[0][0] in ("label", "global_label", "pwr"):
                problems.append("DANGLING %s at %s" % (tags[0], [p for p, t in points if t == tags[0]]))
        # each target net (restricted to this sheet) must be in one cluster or joined by names
        by_net = defaultdict(set)
        for tag, cid in cl.items():
            if tag[0] == "pin":
                by_net[self.t.pin_net[(tag[1], tag[2])]].add(cid)
        for net, cids in by_net.items():
            kind, name = self.t.kind(net, self.sheet)
            if kind in ("auto",) and len(cids) > 1:
                problems.append("SPLIT auto net %s into %d pieces" % (net, len(cids)))
            if kind in ("local", "global", "power"):
                for cid in cids:
                    tags = members[cid]
                    named = any(t[0] in ("label", "global_label") or (t[0] == "pwr" and t[1] != "PWR_FLAG") for t in tags)
                    pins = [t for t in tags if t[0] == "pin"]
                    if not named:
                        problems.append("UNNAMED piece of %s: %s" % (net, [(t[1], t[2]) for t in pins]))
            if kind == "nc":
                pass
        # open pins (no wire, label, power or NC): every visible pin must be touched
        have = self.connected_pins()
        ncset = {key(p) for p in self.ncs}
        for p, (ref, n), pd in self.all_pins():
            if pd["hidden"]:
                continue
            spec = "%s.%s" % (ref, n)
            if spec not in have and key(p) not in ncset:
                problems.append("OPEN pin %s (%s)" % (spec, self.t.pin_net.get((ref, n))))
        return problems

    # ------------------------------------------------------------------ output nodes
    def _power_node(self, pt, name, rot, inst_path):
        lid = "power:" + name
        lib = self.doc.libs[lid]
        if name == "PWR_FLAG":
            ref = "#FLG%04d" % self.flg_n; self.flg_n += 1
        else:
            ref = "#PWR%04d" % self.pwr_n; self.pwr_n += 1
        x, y = pt
        props = []
        for p in find(lib.node, "property"):
            pn, pv = p[1], p[2]
            if pn.startswith("ki_"):
                continue
            at = first(p, "at")
            if pn in ("Reference", "Value"):
                ox, oy = xf(float(at[1]), float(at[2]), rot, None)
                fx, fy = x + ox, y + oy
            else:
                fx, fy = x, y
            v = ref if pn == "Reference" else pv
            hidden = pn != "Value"
            node = [S("property"), pn, v, [S("at"), N(fx), N(fy), N(0)]]
            if hidden:
                node.append([S("hide"), S("yes")])
            node += [[S("show_name"), S("no")], [S("do_not_autoplace"), S("no")], font()]
            props.append(node)
        sym = [S("symbol"), [S("lib_id"), lid], [S("at"), N(x), N(y), N(rot)], [S("unit"), N(1)], [S("body_style"), N(1)],
               [S("exclude_from_sim"), S("no")], [S("in_bom"), S("yes")], [S("on_board"), S("yes")], [S("in_pos_files"), S("yes")],
               [S("dnp"), S("no")], [S("uuid"), U()]] + props
        sym.append([S("pin"), "1", [S("uuid"), U()]])
        sym.append([S("instances"), [S("project"), PROJECT, [S("path"), inst_path, [S("reference"), ref], [S("unit"), N(1)]]]])
        return sym

    def nodes(self):
        inst = self.doc.inst_path
        out = {"junction": [], "no_connect": [], "wire": [], "rectangle": [], "text": [], "label": [], "global_label": [],
               "symbol": [], "sheet": []}
        for p in self.junctions:
            out["junction"].append([S("junction"), [S("at"), N(p[0]), N(p[1])], [S("diameter"), N(0)],
                                    [S("color"), N(0), N(0), N(0), N(0)], [S("uuid"), U()]])
        for p in self.ncs:
            out["no_connect"].append([S("no_connect"), [S("at"), N(p[0]), N(p[1])], [S("uuid"), U()]])
        for a, b in self.wires:
            out["wire"].append([S("wire"), [S("pts"), [S("xy"), N(a[0]), N(a[1])], [S("xy"), N(b[0]), N(b[1])]],
                                [S("stroke"), [S("width"), N(0)], [S("type"), S("default")]], [S("uuid"), U()]])
        for x1, y1, x2, y2, dashed in self.rects:
            out["rectangle"].append([S("rectangle"), [S("start"), N(x1), N(y1)], [S("end"), N(x2), N(y2)],
                                     [S("stroke"), [S("width"), N(0)], [S("type"), S("dash" if dashed else "default")]],
                                     [S("fill"), [S("type"), S("none")]], [S("uuid"), U()]])
        for x, y, s in self.texts:
            out["text"].append([S("text"), s, [S("exclude_from_sim"), S("no")], [S("at"), N(x), N(y), N(0)],
                                [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]], [S("justify"), S("left"), S("bottom")]],
                                [S("uuid"), U()]])
        for p, kind, name, rot, shape in self.labels:
            if kind == "label":
                just = [S("left"), S("bottom")] if rot in (0, 90) else [S("right"), S("bottom")]
                out["label"].append([S("label"), name, [S("at"), N(p[0]), N(p[1]), N(rot)],
                                     [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]], [S("justify")] + just],
                                     [S("uuid"), U()]])
            else:
                just = S("left") if rot in (0, 90) else S("right")
                out["global_label"].append([S("global_label"), name, [S("shape"), S(shape)], [S("at"), N(p[0]), N(p[1]), N(rot)],
                                            [S("fields_autoplaced"), S("yes")],
                                            [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]], [S("justify"), just]],
                                            [S("uuid"), U()],
                                            [S("property"), "Intersheetrefs", "${INTERSHEET_REFS}", [S("at"), N(p[0]), N(p[1]), N(0)],
                                             [S("hide"), S("yes")], [S("show_name"), S("no")], [S("do_not_autoplace"), S("no")],
                                             [S("effects"), [S("font"), [S("size"), N(1.27), N(1.27)]], [S("justify"), just]]]])
        for ref, node in self.doc.symbols.items():
            out["symbol"].append(node)
        for p, name, rot in self.powers:
            out["symbol"].append(self._power_node(p, name, rot, inst))
        out["symbol"] += self.extra_syms
        out["sheet"] = self.doc.sheets
        return out

    def write(self, path, paper, title, comments, date="2026-11-13", rev="3.0", company="READARK"):
        tree = self.doc.tree
        nd = self.nodes()
        head = []
        for it in tree[1:]:
            if not isinstance(it, list):
                continue
            k = it[0]
            if k in ("version", "generator", "generator_version", "uuid"):
                head.append(it)
        tb = [S("title_block"), [S("title"), title], [S("date"), date], [S("rev"), rev], [S("company"), company]]
        for i, c in enumerate(comments, 1):
            tb.append([S("comment"), N(i), c])
        body = [S("kicad_sch")] + head + [[S("paper"), paper], tb, first(tree, "lib_symbols")]
        for k in ("junction", "no_connect", "wire", "rectangle", "text", "label", "global_label", "symbol", "sheet"):
            body += nd[k]
        si = first(tree, "sheet_instances")
        if si:
            body.append(si)
        body.append([S("embedded_fonts"), S("no")])
        txt = dump(body) + "\n"
        txt = txt.replace("\r\n", "\n").replace("\n", "\r\n")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(txt)
