"""Silkscreen reference designators for the Rev3.0 READARK filament dryer / annealer board: placement.
Adapted from the Battery Sentinel refdes round (rev C.29, reviewed 2026-10-15); method and parameters unchanged.

Whole chain, deterministic, always from the untouched copy orig/3dFilamentDryer.kicad_pcb (run_all.py runs it):
  1. refdes_geom.py (KiCad python): geometry of the labelled board (orig + the board legend of silk_labels.py)
  2. this script (python 3, numpy / scipy / Pillow / matplotlib)
       - obstacle raster (0.025 mm): F.Mask apertures + 0.15, library and board silk + 0.15, board edge + 0.30,
         holes + 0.30, every clearance plus a 0.03 mm raster safety margin; exact polygons for the courtyards
       - candidate positions per part: centred / offset outside each courtyard side, 0 and 90 deg, gaps -0.15..1.0
         mm, text styles S (0.8 / 0.7 / 0.10), C (0.8 / 0.6 / 0.10), L (1.0 / 1.0 / 0.15, large parts only)
       - ownership test per candidate (text bbox to own courtyard vs. every other courtyard)
       - optimisation: unary cost + row consistency penalties, no two designators closer than 0.25 mm
       - legend maps for the parts left without a clean label: a framed, uniformly scaled copy of the group in board
         orientation, each name centred at its part's scaled position, ICs / anchors as 0.1 mm outlines, frame
         aspect = group bbox aspect, leader + arrow to the group's bounding box
     -> work/placement.json
python refdes_place.py [--explain R1,R2] [--debug R1] [--debug-maps]
"""
import hashlib
import inspect
import json
import math
import os
import pickle
import re
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from cfg import GEOM, KPY, PLACEMENT, SKIP, WORK, WINDOW  # noqa: E402

BX0, BY0, BX1, BY1 = WINDOW                            # raster window (absolute mm)

P = dict(
    res=0.025, safety=0.03,
    clr_mask=0.15, clr_silk=0.15, clr_edge=0.30, clr_hole=0.30, clr_fid=1.00,
    clr_label=0.25,               # designator to designator (other parts)
    clr_block=0.50,               # designator to a legend block frame / leader (keeps blocks and labels apart)
    own_margin=0.30, own_margin_aligned=0.22, own_ratio=2.0, own_center=0.20, own_face_margin=0.45,
    own_slack_cost=2.0, own_slack_ref=1.0, own_cap=6.0,   # thin ownership margin: cost 2 per mm below 1 mm
    gaps=(-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00),
    off_step=0.10, centred_tol=0.10, max_off_steps=30,
    keep_per_key=25, keep_total=320,
    legend_cost=40.0,
    row_mismatch=2.5, row_misalign=0.8, row_ends=0.5, region_ang=0.1,
    prox_dist=0.60, prox_cost=1.5,  # designators of different parts closer than 0.6 mm read as one: soft cost
    group_gap=0.45,               # tight neighbours of an unplaceable part (courtyard to courtyard)
    block_radius=10.0, block_pad=0.25, block_line=0.10, block_cy_margin=0.10, displace_cost=0.5,
    leader_cross_cost=2.0, leader_min=0.6, arrow_len=0.45, arrow_deg=30.0,
    map_gap_label=0.35, map_gap_outline=0.25, map_s_min=0.30, map_s_max=2.0, map_style_cost=0.8, map_outline_scale=0.75,   # legend maps
)
STYLE_COST = {"L": 0.0, "S": 0.0, "C": 0.4}
STYLE_COST_LARGE = {"L": 0.0, "S": 0.6, "C": 1.0}
# large parts (1.0 x 1.0 / 0.15 allowed): connectors (J*), every part with a courtyard of 30 mm2 or more, and these
LARGE = {"U3", "U10", "U20", "U30", "U11", "U31", "U6"}
LARGE_AREA = 30.0


def natkey(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


# ------------------------------------------------------------------------------------------------ geometry helpers
def rect_dist(a, b):
    dx = max(0.0, b[0] - a[2], a[0] - b[2])
    dy = max(0.0, b[1] - a[3], a[1] - b[3])
    return math.hypot(dx, dy)


def _orient(p, q, r):
    return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])


def rect_poly_dist(r, V, path):
    """exact distance between an axis-aligned rect and a filled polygon (0 if they overlap)"""
    x0, y0, x1, y1 = r
    if np.any((V[:, 0] >= x0) & (V[:, 0] <= x1) & (V[:, 1] >= y0) & (V[:, 1] <= y1)):
        return 0.0
    if path.contains_point(((x0 + x1) / 2, (y0 + y1) / 2)):
        return 0.0
    A = V
    B = np.roll(V, -1, axis=0)
    C4 = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    if x1 > x0 or y1 > y0:
        for k in range(4):
            C, D = C4[k], C4[(k + 1) % 4]
            o1, o2 = _orient(A, B, C), _orient(A, B, D)
            o3, o4 = _orient(C, D, A), _orient(C, D, B)
            if np.any((o1 * o2 < 0) & (o3 * o4 < 0)):      # proper crossing (contact gives 0 below)
                return 0.0
    dx = np.maximum(0, np.maximum(x0 - V[:, 0], V[:, 0] - x1))
    dy = np.maximum(0, np.maximum(y0 - V[:, 1], V[:, 1] - y1))
    d = float(np.hypot(dx, dy).min())
    AB = B - A
    L2 = (AB ** 2).sum(1)
    L2 = np.where(L2 == 0, 1e-18, L2)
    for C in C4:
        t = np.clip(((C[0] - A[:, 0]) * AB[:, 0] + (C[1] - A[:, 1]) * AB[:, 1]) / L2, 0, 1)
        d = min(d, float(np.hypot(A[:, 0] + t * AB[:, 0] - C[0], A[:, 1] + t * AB[:, 1] - C[1]).min()))
    return d


class Courtyard:
    """courtyard of one footprint: fast path for axis-aligned rectangles, exact polygon distance otherwise"""

    def __init__(self, rings_list, bb):
        self.bb = bb
        self.polys = []
        self.is_rect = False
        if len(rings_list) == 1 and len(rings_list[0][0]) == 4:
            V = np.array(rings_list[0][0])
            xs, ys = sorted(set(np.round(V[:, 0], 4))), sorted(set(np.round(V[:, 1], 4)))
            self.is_rect = len(xs) == 2 and len(ys) == 2
        if not self.is_rect:
            for rings in rings_list:
                V = np.array(rings[0])
                self.polys.append((V, MPath(V)))

    def dist(self, r):
        if self.is_rect:
            return rect_dist(r, self.bb)
        return min(rect_poly_dist(r, V, path) for V, path in self.polys)


# ------------------------------------------------------------------------------------------------ raster
class Grid:
    def __init__(self):
        self.res = P["res"]
        self.x0, self.y0 = BX0, BY0
        self.w = int(math.ceil((BX1 - BX0) / self.res))
        self.h = int(math.ceil((BY1 - BY0) / self.res))

    def px(self, x, y):
        return ((x - self.x0) / self.res, (y - self.y0) / self.res)

    def new(self):
        return Image.new("1", (self.w, self.h), 0)

    def fill(self, img, rings_list):
        """fill polygons (outline minus holes); a polygon with holes is drawn on its own patch and OR-ed in, so its
        holes never erase what is already drawn (Battery Sentinel version drew holes straight into the layer)"""
        d = ImageDraw.Draw(img)
        for rings in rings_list:
            if len(rings[0]) < 2:
                continue
            outer = [self.px(x, y) for x, y in rings[0]]
            holes = [[self.px(x, y) for x, y in h] for h in rings[1:] if len(h) >= 3]
            if not holes:
                d.polygon(outer, fill=1, outline=1)
                continue
            x0 = int(math.floor(min(p[0] for p in outer))) - 1
            y0 = int(math.floor(min(p[1] for p in outer))) - 1
            x1 = int(math.ceil(max(p[0] for p in outer))) + 2
            y1 = int(math.ceil(max(p[1] for p in outer))) + 2
            patch = Image.new("1", (x1 - x0, y1 - y0), 0)
            pd = ImageDraw.Draw(patch)
            pd.polygon([(u - x0, v - y0) for u, v in outer], fill=1, outline=1)
            for h in holes:
                pd.polygon([(u - x0, v - y0) for u, v in h], fill=0, outline=1)
            img.paste(1, (x0, y0), mask=patch)

    def integral(self, arr):
        S = np.zeros((self.h + 1, self.w + 1), np.int32)
        S[1:, 1:] = np.cumsum(np.cumsum(arr, 0, dtype=np.int32), 1, dtype=np.int32)
        return S

    def idx(self, r):
        return (int(math.floor((r[0] - self.x0) / self.res)), int(math.floor((r[1] - self.y0) / self.res)),
                int(math.ceil((r[2] - self.x0) / self.res)), int(math.ceil((r[3] - self.y0) / self.res)))

    def count(self, S, r):
        i0, j0, i1, j1 = self.idx(r)
        if i0 < 0 or j0 < 0 or i1 > self.w or j1 > self.h:
            return 1 << 30
        return int(S[j1, i1] - S[j0, i1] - S[j1, i0] + S[j0, i0])


def build_obstacles(G, grid):
    lay = {k: grid.new() for k in ("pad", "fid", "silk", "inside", "hole", "cy")}
    for fp in G["fps"]:
        key = "fid" if fp["ref"].startswith("FID") else "pad"
        grid.fill(lay[key], [rings for pd in fp["pads"] for rings in pd["poly"]])
        grid.fill(lay["silk"], [rings for s in fp["silk"] for rings in s])
        grid.fill(lay["cy"], fp["cy"])
    grid.fill(lay["silk"], [rings for s in G["silk"] for rings in s["poly"]])
    grid.fill(lay["inside"], G["edge"]["outline"])
    d = ImageDraw.Draw(lay["hole"])
    for cx, cy, r, _ in G["edge"]["holes"]:
        (a, b), (c, e) = grid.px(cx - r, cy - r), grid.px(cx + r, cy + r)
        d.ellipse([a, b, c, e], fill=1, outline=1)
    arr = {k: np.array(v, dtype=bool) for k, v in lay.items()}
    arr["outside"] = ~arr.pop("inside")
    clr = {"pad": P["clr_mask"], "fid": P["clr_fid"], "silk": P["clr_silk"], "outside": P["clr_edge"],
           "hole": P["clr_hole"]}
    forb = np.zeros((grid.h, grid.w), bool)
    for k, c in clr.items():
        if arr[k].any():
            dist = ndimage.distance_transform_edt(~arr[k]) * grid.res
            forb |= dist < c + P["safety"]
            del dist
    dist = ndimage.distance_transform_edt(~arr["cy"]) * grid.res
    cyforb = dist < P["block_cy_margin"]
    del dist
    return forb, cyforb


# ------------------------------------------------------------------------------------------------ parts
class Part:
    def __init__(self, rec):
        self.ref = rec["ref"]
        self.rec = rec
        bb = rec["cybb"]
        if bb is None:                                   # no courtyard (L1): pads + library silk bbox
            xs = [v for pd in rec["pads"] for v in (pd["bb"][0], pd["bb"][2])]
            ys = [v for pd in rec["pads"] for v in (pd["bb"][1], pd["bb"][3])]
            for s in rec["silk"]:
                for rings in s:
                    xs += [q[0] for q in rings[0]]
                    ys += [q[1] for q in rings[0]]
            bb = [min(xs), min(ys), max(xs), max(ys)]
            rec["cy"] = [[[[bb[0], bb[1]], [bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]]]]]
        self.bb = bb
        self.cyd = Courtyard(rec["cy"], bb)
        self.W, self.H = bb[2] - bb[0], bb[3] - bb[1]
        self.cx, self.cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        self.large = self.ref in LARGE or self.ref.startswith("J") or self.W * self.H >= LARGE_AREA
        self.small = self.W * self.H <= 16.0 and max(self.W, self.H) <= 5.0 and not self.large
        self.square = max(self.W, self.H) / max(min(self.W, self.H), 1e-6) < 1.2
        self.long_h = self.W >= self.H


class Cand:
    __slots__ = ("ref", "style", "ang", "side", "gap", "off", "rect", "pos", "cost", "cls", "d_own", "d_oth", "line",
                 "key", "idx")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def facing(side, r, qb):
    """qb lies beyond the label's outer edge (seen from its own part) and overlaps it sideways"""
    if side in "TB":
        ov = min(qb[2], r[2]) - max(qb[0], r[0])
        return ov > 0 and (qb[3] <= r[1] + 0.05 if side == "T" else qb[1] >= r[3] - 0.05)
    ov = min(qb[3], r[3]) - max(qb[1], r[1])
    return ov > 0 and (qb[2] <= r[0] + 0.05 if side == "L" else qb[0] >= r[2] - 0.05)


def gen_candidates(part, G, grid, forbS, neigh, extra_rects=(), stats=None):
    ink = G["ink"][part.ref]
    x0, y0, x1, y1 = part.bb
    styles = ["L", "S", "C"] if part.large else ["S", "C"]
    scost = STYLE_COST_LARGE if part.large else STYLE_COST
    out = []
    for st in styles:
        for ang in (0, 90):
            ib = ink[st][str(ang)]
            tw, th = ib[2] - ib[0], ib[3] - ib[1]
            for side in "TBLR":
                hs = side in "TB"
                parallel = (ang == 0) == hs
                side_len = part.W if hs else part.H
                is_long = part.square or (hs == part.long_h)
                n = min(int(max(0.0, side_len / 2) / P["off_step"] + 1e-9), P["max_off_steps"])
                offs = [0.0] + [s * k * P["off_step"] for k in range(1, n + 1) for s in (-1, 1)]
                for g in P["gaps"]:
                    for off in offs:
                        if side == "T":
                            r = (part.cx + off - tw / 2, y0 - g - th, part.cx + off + tw / 2, y0 - g)
                        elif side == "B":
                            r = (part.cx + off - tw / 2, y1 + g, part.cx + off + tw / 2, y1 + g + th)
                        elif side == "L":
                            r = (x0 - g - tw, part.cy + off - th / 2, x0 - g, part.cy + off + th / 2)
                        else:
                            r = (x1 + g, part.cy + off - th / 2, x1 + g + tw, part.cy + off + th / 2)
                        if grid.count(forbS, r):
                            if stats is not None:
                                stats["clearance"] += 1
                            continue
                        if any(rect_dist(r, e) < P["clr_block"] for e in extra_rects):
                            continue
                        d_own = part.cyd.dist(r)
                        # a centred label that stays within its own side reads as that part's even with a slightly
                        # smaller margin (column / row continuation); anything else needs the full margin
                        fits = abs(off) <= P["centred_tol"] + 1e-9 and (tw if hs else th) <= side_len + 1e-9
                        margin = P["own_margin_aligned"] if fits else P["own_margin"]
                        lim = max(d_own + margin, P["own_ratio"] * d_own, 0.05)
                        d_oth = P["own_cap"]
                        bad = False
                        # a part facing the label across the gap (beyond its outer edge, overlapping it sideways)
                        # needs a wider margin: a label half way between two parts belongs to neither
                        flim = d_own + P["own_face_margin"]
                        for q in neigh:
                            rd = rect_dist(r, q.bb)
                            if rd >= d_oth and rd >= flim:
                                continue
                            dq = q.cyd.dist(r)
                            if dq < d_oth:
                                d_oth = dq
                                if d_oth < lim:
                                    bad = True
                                    break
                            if dq < flim and facing(side, r, q.bb):
                                bad = True
                                break
                        if bad:
                            if stats is not None:
                                stats["ownership"] += 1
                                k = (side, ang, st)
                                if k not in stats["best_own"] or stats["best_own"][k][0] < d_oth - d_own:
                                    stats["best_own"][k] = (round(d_oth - d_own, 3), g, off, round(d_own, 3))
                            continue
                        c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
                        cr = (c[0], c[1], c[0], c[1])
                        dc_own = part.cyd.dist(cr)
                        dc_oth = min([q.cyd.dist(cr) for q in neigh if rect_dist(cr, q.bb) < dc_own + 3.0] or [9.9])
                        if dc_oth < dc_own + P["own_center"]:
                            if stats is not None:
                                stats["centre"] += 1
                            continue
                        # orientation / side: (long side, parallel) best; then end labels along the part axis
                        # (short side) and text parallel to a short side (penalised by its overhang); text across a
                        # long side last
                        aligned = parallel if part.square else ((ang == 0) == part.long_h)
                        overhang = max(0.0, (tw if hs else th) - side_len)
                        if is_long and parallel:
                            cost = 0.0
                        elif not is_long and aligned:
                            cost = 1.0
                        elif not is_long:
                            cost = 1.0 + 1.5 * overhang
                        else:
                            cost = 2.2
                        cost += 0.15 if ang == 90 else 0.0
                        cost += {"T": 0.0, "B": 0.05, "L": 0.10, "R": 0.15}[side]
                        cost += 0.8 * abs(g - 0.05) + (0.3 if g < 0 else 0.0)
                        centred = abs(off) <= P["centred_tol"] + 1e-9
                        cost += 0.3 * abs(off) / P["off_step"] if centred else 1.5 + abs(off)
                        cost += scost[st]
                        cost += P["own_slack_cost"] * max(0.0, P["own_slack_ref"] - (d_oth - d_own))
                        cls = 3 if not centred else (1 if (parallel and is_long) else 2)
                        if not centred and abs(off) > side_len / 2 + 1e-9:
                            continue
                        line = (r[1] + r[3]) / 2 if hs else (r[0] + r[2]) / 2
                        out.append(Cand(ref=part.ref, style=st, ang=ang, side=side, gap=g, off=off, rect=r,
                                        pos=(r[0] - ib[0], r[1] - ib[1]), cost=cost, cls=cls, d_own=d_own,
                                        d_oth=d_oth, line=line, key=(side, ang, st), idx=-1))
    # prune: best per key, then best overall
    out.sort(key=lambda c: (c.cost, c.gap, abs(c.off), c.off))
    keep, per = [], defaultdict(int)
    for c in out:
        if per[c.key] < P["keep_per_key"]:
            keep.append(c)
            per[c.key] += 1
    kid = set(map(id, keep))
    rest = [c for c in out if id(c) not in kid][: max(0, P["keep_total"] - len(keep))]
    keep = sorted(keep + rest, key=lambda c: (c.cost, c.gap, abs(c.off), c.off))
    for i, c in enumerate(keep):
        c.idx = i
    return keep


# ------------------------------------------------------------------------------------------------ rows
def row_pairs(parts):
    """row-mates: small parts of similar size (or medium parts of the same footprint), aligned, side by side
    (dir 'x') or stacked (dir 'y'), nothing in between"""
    sm = [p for p in parts if p.small or p.W * p.H <= 40.0 or p.ref.startswith("J")]
    pairs = []
    for i, a in enumerate(sm):
        for b in sm[i + 1:]:
            same_fp = a.rec["fpid"] == b.rec["fpid"] and a.rec["ang"] % 180 == b.rec["ang"] % 180
            if not ((a.small and b.small) or same_fp):
                continue
            if abs(a.W - b.W) > 0.5 or abs(a.H - b.H) > 0.5:
                continue
            maxgap = 1.5 if (a.small and b.small) else max(1.5, 1.2 * min(a.W, a.H))
            for d in ("x", "y"):
                if d == "x":
                    al = abs(a.cy - b.cy)
                    gap = max(b.bb[0] - a.bb[2], a.bb[0] - b.bb[2])
                else:
                    al = abs(a.cx - b.cx)
                    gap = max(b.bb[1] - a.bb[3], a.bb[1] - b.bb[3])
                if al > 0.25 or gap < -0.05 or gap > maxgap:
                    continue
                # nothing in between
                if d == "x":
                    lo, hi = sorted((a.cx, b.cx))
                    mid = [q for q in sm if q not in (a, b) and lo < q.cx < hi and abs(q.cy - a.cy) < 1.0]
                else:
                    lo, hi = sorted((a.cy, b.cy))
                    mid = [q for q in sm if q not in (a, b) and lo < q.cy < hi and abs(q.cx - a.cx) < 1.0]
                if mid:
                    continue
                first, second = (a, b) if (a.cx < b.cx if d == "x" else a.cy < b.cy) else (b, a)
                pairs.append((first.ref, second.ref, d))
    return pairs


def near_pairs(parts, rowp):
    """parts close to each other (courtyards within 2 mm) that are not row-mates: soft same-orientation pairs"""
    have = {(a, b) for a, b, d in rowp} | {(b, a) for a, b, d in rowp}
    out = []
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if (a.ref, b.ref) in have or rect_dist(a.bb, b.bb) > 2.0:
                continue
            out.append((a.ref, b.ref, "n"))
    return out


def pair_pen(ca, cb, d):
    """ca: label of the left / upper part, cb: of the right / lower part"""
    if ca is None or cb is None:
        return 0.0
    if d == "n":
        return P["region_ang"] if ca.ang != cb.ang else 0.0
    along = "TB" if d == "x" else "LR"         # sides that keep the row reading the same way
    ends = "LR" if d == "x" else "TB"
    a_al, b_al = ca.side in along, cb.side in along
    if a_al and b_al:
        if ca.key != cb.key:
            return P["row_mismatch"]
        return 0.0 if abs(ca.line - cb.line) <= 0.03 else P["row_misalign"]
    if not a_al and not b_al:
        outward = ca.side == ends[0] and cb.side == ends[1]
        same = ca.side == cb.side
        return 0.0 if ((outward or same) and ca.ang == cb.ang and ca.style == cb.style) else P["row_ends"] + 1.0
    return P["row_mismatch"]


# ------------------------------------------------------------------------------------------------ solver
class Solver:
    CELL = 2.0

    def __init__(self, parts, cands, pairs):
        self.parts = parts
        self.cands = cands
        self.choice = {p.ref: None for p in parts}
        self.grid = defaultdict(set)
        self.mates = defaultdict(list)          # ref -> [(other, dir, i_am_first)]
        for a, b, d in pairs:
            if a in cands and b in cands:
                self.mates[a].append((b, d, True))
                self.mates[b].append((a, d, False))
        self.order = sorted(cands, key=lambda r: (len(cands[r]), natkey(r)))
        self.rowmate = {(a, b) for a, b, d in pairs if d != "n"} | {(b, a) for a, b, d in pairs if d != "n"}

    def _cells(self, r):
        c = max([P["clr_label"], P["prox_dist"]] + list(REVIEW_PAIRS.values()))
        for i in range(int(math.floor((r[0] - c) / self.CELL)), int(math.floor((r[2] + c) / self.CELL)) + 1):
            for j in range(int(math.floor((r[1] - c) / self.CELL)), int(math.floor((r[3] + c) / self.CELL)) + 1):
                yield (i, j)

    def put(self, ref, c):
        old = self.choice[ref]
        if old is not None:
            for k in self._cells(old.rect):
                self.grid[k].discard(ref)
        self.choice[ref] = c
        if c is not None:
            for k in self._cells(c.rect):
                self.grid[k].add(ref)

    def conflicts(self, ref, r, ignore=()):
        out = set()
        for k in self._cells(r):
            for q in self.grid.get(k, ()):
                if q != ref and q not in ignore and q not in out:
                    lim = REVIEW_PAIRS.get((ref, q), REVIEW_PAIRS.get((q, ref), P["clr_label"]))
                    if rect_dist(r, self.choice[q].rect) < lim:
                        out.add(q)
        return out

    def unary(self, ref, c):
        return P["legend_cost"] if c is None else c.cost

    def prox_pair(self, a, ca, b, cb):
        if ca is None or cb is None:
            return 0.0
        d = rect_dist(ca.rect, cb.rect)
        if d >= P["prox_dist"]:
            return 0.0
        if (a, b) in self.rowmate and ca.key == cb.key:
            return 0.0
        return P["prox_cost"] * (P["prox_dist"] - d) / (P["prox_dist"] - P["clr_label"])

    def near_labels(self, ref, r):
        out = set()
        for k in self._cells(r):
            for q in self.grid.get(k, ()):
                if q != ref:
                    out.add(q)
        return sorted(out, key=natkey)

    def prox(self, ref, c, skip=()):
        if c is None:
            return 0.0
        return sum(self.prox_pair(ref, c, q, self.choice[q]) for q in self.near_labels(ref, c.rect) if q not in skip)

    def pen(self, ref, c, other, d, first, oc=None):
        oc = self.choice[other] if oc is None else oc
        return pair_pen(c, oc, d) if first else pair_pen(oc, c, d)

    def set_cost(self, S):
        """cost of the parts in S plus every row pair and proximity pair touching S (current choices)"""
        tot = 0.0
        seen = set()
        for a in S:
            tot += self.unary(a, self.choice[a])
            ca = self.choice[a]
            if ca is not None:
                for q in self.near_labels(a, ca.rect):
                    if q in S and natkey(q) < natkey(a):
                        continue
                    tot += self.prox_pair(a, ca, q, self.choice[q])
            for b, d, first in self.mates[a]:
                key = (a, b) if first else (b, a)
                if key in seen:
                    continue
                seen.add(key)
                tot += self.pen(a, self.choice[a], b, d, first)
        return tot

    def best_free(self, ref, ignore=(), exclude_rects=()):
        best, bc = None, None
        for c in self.cands[ref]:
            if self.conflicts(ref, c.rect, ignore):
                continue
            if any(rect_dist(c.rect, e) < P["clr_label"] for e in exclude_rects):
                continue
            v = c.cost + sum(self.pen(ref, c, b, d, f) for b, d, f in self.mates[ref]) + self.prox(ref, c)
            if bc is None or v < bc - 1e-12:
                best, bc = c, v
        return best

    def greedy(self):
        for ref in self.order:
            self.put(ref, self.best_free(ref))

    def try_move(self, ref, c):
        """move ref to c, relocating up to two conflicting labels; keep if the cost drops"""
        Q = self.conflicts(ref, c.rect)
        if len(Q) > 2:
            return False
        S = {ref} | Q
        before = self.set_cost(S)
        saved = {a: self.choice[a] for a in S}
        self.put(ref, c)
        for q in sorted(Q, key=natkey):
            self.put(q, None)
        for q in sorted(Q, key=natkey):
            self.put(q, self.best_free(q))
        after = self.set_cost(S)
        if after < before - 1e-9:
            return True
        for a in S:
            self.put(a, None)
        for a, v in saved.items():
            self.put(a, v)
        return False

    def local(self, ref, c):
        return self.unary(ref, c) + sum(self.pen(ref, c, b, d, f) for b, d, f in self.mates[ref]) + self.prox(ref, c)

    def improve(self, passes=12):
        for it in range(passes):
            changed = 0
            for ref in self.order:
                cur = self.choice[ref]
                vcur = self.local(ref, cur)
                for c in self.cands[ref]:
                    if c is cur or self.local(ref, c) >= vcur - 1e-9:
                        continue
                    if self.try_move(ref, c):
                        changed += 1
                        cur = self.choice[ref]
                        vcur = self.local(ref, cur)
            changed += self.row_moves()
            if not changed:
                break
        return it

    def components(self, d):
        adj = defaultdict(set)
        for a in self.mates:
            for b, dd, f in self.mates[a]:
                if dd == d:
                    adj[a].add(b)
        seen, comps = set(), []
        for a in sorted(adj, key=natkey):
            if a in seen:
                continue
            st, comp = [a], []
            seen.add(a)
            while st:
                x = st.pop()
                comp.append(x)
                for y in adj[x]:
                    if y not in seen:
                        seen.add(y)
                        st.append(y)
            comps.append(sorted(comp, key=natkey))
        return comps

    def row_moves(self):
        changed = 0
        for d in ("x", "y"):
            along = "TB" if d == "x" else "LR"
            for comp in self.components(d):
                keys = sorted({c.key for r in comp for c in self.cands[r] if c.side in along})
                for key in keys:
                    gaps = None
                    for r in comp:
                        gs = {c.gap for c in self.cands[r] if c.key == key and abs(c.off) <= P["centred_tol"] + 1e-9}
                        gaps = gs if gaps is None else gaps & gs
                    glist = sorted(gaps) if gaps else [None]
                    for g in glist[:3]:
                        assign = {}
                        for r in comp:
                            pool = [c for c in self.cands[r] if c.key == key and (g is None or c.gap == g)]
                            if not pool:
                                break
                            assign[r] = min(pool, key=lambda c: (c.cost, abs(c.off)))
                        if len(assign) != len(comp):
                            continue
                        if all(self.choice[r] is assign[r] for r in comp):
                            continue
                        # members must not conflict with each other
                        ok = True
                        rs = list(assign.items())
                        for i in range(len(rs)):
                            for j in range(i + 1, len(rs)):
                                if rect_dist(rs[i][1].rect, rs[j][1].rect) < P["clr_label"]:
                                    ok = False
                        if not ok:
                            continue
                        Q = set()
                        for r, c in assign.items():
                            Q |= self.conflicts(r, c.rect, ignore=comp)
                        if len(Q) > 3:
                            continue
                        S = set(comp) | Q
                        before = self.set_cost(S)
                        saved = {a: self.choice[a] for a in S}
                        for a in S:
                            self.put(a, None)
                        for r, c in assign.items():
                            self.put(r, c)
                        for q in sorted(Q, key=natkey):
                            self.put(q, self.best_free(q))
                        after = self.set_cost(S)
                        if after < before - 1e-9:
                            changed += 1
                        else:
                            for a in S:
                                self.put(a, None)
                            for a, v in saved.items():
                                self.put(a, v)
        return changed

    def total(self):
        return self.set_cost(set(self.choice))


# ------------------------------------------------------------------------------------------------ legend maps
# Design review 2026-10-15: every legend block is a scaled map of its group, one uniform scale, in the board's own
# orientation (never a list). Each member's designator is centred at the member's scaled position. ICs among the
# members are drawn as 0.1 mm outlines with their name inside (or beside). The group's directly labelled anchor parts
# are drawn as outlines with their name as a new board text, so the map is recognised at once. The frame has the
# aspect ratio of the group's bounding box, and the leader points at that bounding box, not at one member.
REVIEW_GROUPS = []          # Rev3.0 first pass: no review yet, every map is found automatically
OPTIONAL_ANCHORS = {}
OUTLINE_PREFIX = ("U", "IC")
# Review 2026-10-15: the direct labels of the reviewed result stay exactly where they were, except these
REVIEWED = os.path.join(WORK, "reviewed_placement.json")
REVIEW_UNPIN = set()
REVIEW_PAIRS = {}


def pin_reviewed(allc):
    """every part that had a direct label in the reviewed result keeps exactly that candidate"""
    if not os.path.exists(REVIEWED):
        print("no reviewed placement: nothing pinned")
        return allc
    rv = json.load(open(REVIEWED, encoding="utf-8"))["refs"]
    in_review = {m for g in REVIEW_GROUPS for m in g["members"]}
    out, n = {}, 0
    for r, lst in allc.items():
        v = rv.get(r)
        if v and v["cls"] != 4 and r not in REVIEW_UNPIN and r not in in_review:
            same = [c for c in lst if max(abs(a - b) for a, b in zip(c.rect, v["rect"])) < 1e-3 and c.ang == v["ang"]
                    and c.style == v["style"]]
            assert same, "reviewed label of %s not among its candidates" % r
            out[r] = same[:1]
            n += 1
        else:
            out[r] = lst
    print("pinned to the reviewed position: %d designators; free: %s" % (
        n, " ".join(sorted((r for r in allc if len(out[r]) != 1 or r in REVIEW_UNPIN), key=natkey))))
    return out
MODE_COST = {"part": 0.0, "0": 0.3, "90": 1.5}    # names oriented like their parts read most like the board


def body_box(part):
    """the part's body (F.Fab outline bbox) when it lies within the courtyard, else the courtyard"""
    fb = part.rec.get("fabbb")
    bb = part.bb
    if fb and fb[0] >= bb[0] - 0.01 and fb[1] >= bb[1] - 0.01 and fb[2] <= bb[2] + 0.01 and fb[3] <= bb[3] + 0.01:
        return fb
    return bb


def _rect_at(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def map_layout(members, anchors, parts, G, mode, style):
    """smallest uniform scale s at which every name of the map is >= 0.25 mm from every other name and >= 0.25 mm
    (line centre) from every outline it does not belong to, outlines >= 0.25 mm apart. Returns the layout relative to
    the frame's top-left corner, or None."""
    members = sorted(members, key=natkey)
    anchors = sorted(anchors, key=natkey)
    allp = members + anchors
    gbb = (min(parts[x].bb[0] for x in allp), min(parts[x].bb[1] for x in allp),
           max(parts[x].bb[2] for x in allp), max(parts[x].bb[3] for x in allp))
    W0, H0 = gbb[2] - gbb[0], gbb[3] - gbb[1]
    outl = [x for x in allp if x in anchors or x.startswith(OUTLINE_PREFIX)]

    def ang_of(m):
        if m in anchors:
            return 0
        if mode == "0":
            return 0
        if mode == "90":
            return 90
        return 90 if parts[m].H > 1.2 * parts[m].W else 0

    ink = {}
    for x in allp:
        a = ang_of(x)
        st = "C" if x in anchors else style
        ink[x] = (G["ink"][x][st][str(a)], a, st)
    gl, go = P["map_gap_label"], P["map_gap_outline"]
    for s in np.arange(P["map_s_min"], P["map_s_max"] + 1e-9, 0.01):
        s = round(float(s), 3)

        def sc(x, y):
            return ((x - gbb[0]) * s, (y - gbb[1]) * s)

        boxes = {}
        for x in outl:
            b = body_box(parts[x])
            (a0, b0), (a1, b1) = sc(b[0], b[1]), sc(b[2], b[3])
            k = (1 - P["map_outline_scale"]) / 2          # outline drawn at 75 % of the scaled body, same centre
            boxes[x] = (a0 + (a1 - a0) * k, b0 + (b1 - b0) * k, a1 - (a1 - a0) * k, b1 - (b1 - b0) * k)
        ok = all(rect_dist(boxes[a], boxes[b]) >= gl for i, a in enumerate(outl) for b in outl[i + 1:])
        if not ok:
            continue
        labels = {}
        for m in members:
            if m in outl:
                continue
            ib = ink[m][0]
            c = sc(parts[m].cx, parts[m].cy)
            labels[m] = _rect_at(c[0], c[1], ib[2] - ib[0], ib[3] - ib[1])
        names = list(labels)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if rect_dist(labels[a], labels[b]) < gl:
                    ok = False
                    break
            if not ok:
                break
            if any(rect_dist(labels[a], boxes[o]) < go for o in outl):
                ok = False
                break
        if not ok:
            continue
        for x in outl:                     # outline names: inside, else below / above / right / left
            ib = ink[x][0]
            w, h = ib[2] - ib[0], ib[3] - ib[1]
            bx = boxes[x]
            cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
            opts = []
            if w + 2 * go <= bx[2] - bx[0] and h + 2 * go <= bx[3] - bx[1]:
                opts.append(_rect_at(cx, cy, w, h))
            opts += [_rect_at(cx, bx[3] + go + h / 2, w, h), _rect_at(cx, bx[1] - go - h / 2, w, h),
                     _rect_at(bx[2] + go + w / 2, cy, w, h), _rect_at(bx[0] - go - w / 2, cy, w, h)]
            chosen = None
            for r in opts:
                if any(rect_dist(r, labels[q]) < gl for q in labels):
                    continue
                if any(rect_dist(r, boxes[o]) < go for o in outl if o != x):
                    continue
                if r is not opts[0] or not (w + 2 * go <= bx[2] - bx[0] and h + 2 * go <= bx[3] - bx[1]):
                    if rect_dist(r, bx) < go - 1e-9:
                        continue
                chosen = r
                break
            if chosen is None:
                ok = False
                break
            labels[x] = chosen
        if not ok:
            continue
        # frame: content + pad, then grown to the group's aspect ratio
        xs = [v for r in list(labels.values()) + list(boxes.values()) for v in (r[0], r[2])] + [0.0, W0 * s]
        ys = [v for r in list(labels.values()) + list(boxes.values()) for v in (r[1], r[3])] + [0.0, H0 * s]
        pad = P["block_pad"]
        fx0, fy0, fx1, fy1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
        w, h = fx1 - fx0, fy1 - fy0
        A = W0 / H0
        if w / h < A:
            dw = h * A - w
            fx0, fx1 = fx0 - dw / 2, fx1 + dw / 2
        else:
            dh = w / A - h
            fy0, fy1 = fy0 - dh / 2, fy1 + dh / 2

        def rel(r):
            return (r[0] - fx0, r[1] - fy0, r[2] - fx0, r[3] - fy0)

        return {"W": fx1 - fx0, "H": fy1 - fy0, "s": s, "gbb": gbb, "mode": mode, "style": style,
                "labels": {k: {"rect": rel(r), "ang": ink[k][1], "style": ink[k][2], "ib": ink[k][0],
                               "anchor": k in anchors} for k, r in labels.items()},
                "outlines": {k: rel(r) for k, r in boxes.items()}}
    return None


def seg_poly(a, b, w):
    """thin rectangle polygon around segment a-b, half width w/2"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    ex, ey = dx / L * w / 2, dy / L * w / 2
    return [(a[0] - ex + nx, a[1] - ey + ny), (b[0] + ex + nx, b[1] + ey + ny), (b[0] + ex - nx, b[1] + ey - ny),
            (a[0] - ex - nx, a[1] - ey - ny)]


def segs_clear(segs, grid, forb, cyforb_arr, allowed_cy, label_rects, block_rects):
    """leader segments: no forbidden pixel (mask / silk / edge clearances), clear of labels and other blocks;
    'cross' if they pass over a courtyard outside the group"""
    xs = [v for a, b in segs for v in (a[0], b[0])]
    ys = [v for a, b in segs for v in (a[1], b[1])]
    i0, j0, i1, j1 = grid.idx((min(xs) - 0.2, min(ys) - 0.2, max(xs) + 0.2, max(ys) + 0.2))
    if i0 < 0 or j0 < 0 or i1 > grid.w or j1 > grid.h:
        return False
    img = Image.new("1", (i1 - i0, j1 - j0), 0)
    d = ImageDraw.Draw(img)
    for a, b in segs:
        d.polygon([(u - i0, v - j0) for u, v in (grid.px(x, y) for x, y in seg_poly(a, b, P["block_line"]))],
                  fill=1, outline=1)
    m = np.array(img, dtype=bool)
    if (m & forb[j0:j1, i0:i1]).any():
        return False
    crosses = bool((m & cyforb_arr[j0:j1, i0:i1] & ~allowed_cy[j0:j1, i0:i1]).any())
    for a, b in segs:
        sb = (min(a[0], b[0]) - 0.05, min(a[1], b[1]) - 0.05, max(a[0], b[0]) + 0.05, max(a[1], b[1]) + 0.05)
        for r in label_rects:
            if rect_dist(sb, r) < P["clr_label"] and seg_rect_dist(a, b, r) < P["clr_label"] + 0.05:
                return False
        for r in block_rects:
            if rect_dist(sb, r) < P["clr_block"]:
                return False
    return "cross" if crosses else "clear"


def seg_rect_dist(a, b, r):
    V = np.array([a, b], float)
    path = MPath(np.array([a, b, b, a], float))
    return rect_poly_dist(r, V, path)


def _arrow(a, tip):
    L = math.hypot(tip[0] - a[0], tip[1] - a[1]) or 1e-9
    d = ((tip[0] - a[0]) / L, (tip[1] - a[1]) / L)
    ang = math.atan2(-d[1], -d[0])
    segs = [(a, tip)]
    for s_ in (-1, 1):
        aa = ang + s_ * math.radians(P["arrow_deg"])
        segs.append((tip, (tip[0] + P["arrow_len"] * math.cos(aa), tip[1] + P["arrow_len"] * math.sin(aa))))
    return segs, L


def _clip_to_box(a, c, box):
    """point where the segment a -> c (c inside box) enters the box"""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        p = (a[0] + (c[0] - a[0]) * mid, a[1] + (c[1] - a[1]) * mid)
        if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]:
            hi = mid
        else:
            lo = mid
    return (a[0] + (c[0] - a[0]) * hi, a[1] + (c[1] - a[1]) * hi)


def bbox_leaders(fr, gbb):
    """leaders from the frame to the nearest edge of the group's bounding box (perpendicular where the two overlap
    in x or y, else corner to corner and towards the box centre), arrow tip on the box edge or up to 0.6 mm short"""
    fx0, fy0, fx1, fy1 = fr
    gx0, gy0, gx1, gy1 = gbb
    gc = ((gx0 + gx1) / 2, (gy0 + gy1) / 2)
    pairs = []
    ovx = min(fx1, gx1) - max(fx0, gx0)
    ovy = min(fy1, gy1) - max(fy0, gy0)
    if ovx > 0.3:
        lo, hi = max(fx0, gx0) + 0.15, min(fx1, gx1) - 0.15
        for t in (0.5, 0.35, 0.65, 0.2, 0.8):
            x = lo + (hi - lo) * t
            pairs.append(((x, fy1), (x, gy0)) if fy1 <= gy0 else ((x, fy0), (x, gy1)))
    elif ovy > 0.3:
        lo, hi = max(fy0, gy0) + 0.15, min(fy1, gy1) - 0.15
        for t in (0.5, 0.35, 0.65, 0.2, 0.8):
            y = lo + (hi - lo) * t
            pairs.append(((fx1, y), (gx0, y)) if fx1 <= gx0 else ((fx0, y), (gx1, y)))
    else:
        ax = fx1 if fx1 <= gx0 else fx0
        ay = fy1 if fy1 <= gy0 else fy0
        pairs.append(((ax, ay), (gx0 if fx1 <= gx0 else gx1, gy0 if fy1 <= gy0 else gy1)))
        pairs.append(((ax, ay), _clip_to_box((ax, ay), gc, gbb)))
    out = []
    for a, b in pairs:
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        for stop in (0.0, 0.2, 0.4, 0.6):
            tip = (b[0] - d[0] * stop, b[1] - d[1] * stop)
            if L - stop >= P["leader_min"]:
                out.append(_arrow(a, tip))
    return out


def place_frame(lay, members, parts, grid, forbS, forb, cyS, cyforb, blocks, radius, displace):
    """nearest free spot for the frame (no forbidden pixel, no courtyard, >= 0.5 mm from other blocks, designators
    in the way only if they can move), with a clear leader to the group's bounding box"""
    W, H, gbb = lay["W"], lay["H"], lay["gbb"]
    R = radius
    hw = P["block_line"] / 2
    res = grid.res
    mp = [parts[m] for m in lay["labels"]] + [parts[m] for m in lay["outlines"]]
    allowed = grid.new()
    grid.fill(allowed, [rings for p in mp for rings in p.rec["cy"]])
    allowed = ndimage.binary_dilation(np.array(allowed, dtype=bool), iterations=int(P["block_cy_margin"] / res) + 2)
    wpx = int(math.ceil((W + 2 * hw) / res)) + 1
    hpx = int(math.ceil((H + 2 * hw) / res)) + 1
    I, J = np.meshgrid(np.arange(int(math.floor((gbb[0] - R - W - grid.x0) / res)), int(math.ceil((gbb[2] + R - grid.x0) / res)) + 1, 4),
                       np.arange(int(math.floor((gbb[1] - R - H - grid.y0) / res)), int(math.ceil((gbb[3] + R - grid.y0) / res)) + 1, 4))
    I, J = I.ravel(), J.ravel()
    ok = (I >= 0) & (J >= 0) & (I + wpx <= grid.w) & (J + hpx <= grid.h)
    I, J = I[ok], J[ok]

    def cnt(S):
        return S[J + hpx, I + wpx] - S[J, I + wpx] - S[J + hpx, I] + S[J, I]

    ok = (cnt(forbS) == 0) & (cnt(cyS) == 0)
    I, J = I[ok], J[ok]
    bx = grid.x0 + I * res + hw
    by = grid.y0 + J * res + hw
    dist = np.hypot(np.maximum(0, np.maximum(gbb[0] - (bx + W), bx - gbb[2])),
                    np.maximum(0, np.maximum(gbb[1] - (by + H), by - gbb[3])))
    ok = (dist <= R) & (dist >= P["leader_min"])
    bx, by, dist = bx[ok], by[ok], dist[ok]
    BR = np.array([b["outer"] for b in blocks], float).reshape(-1, 4)
    found = []
    for k in np.lexsort((bx, by, dist)):
        d0 = float(dist[k])
        if found and d0 > min(f[1] for f in found) + 0.5:
            break
        x, y = float(bx[k]), float(by[k])
        r = (x, y, x + W, y + H)
        ro = (x - hw, y - hw, x + W + hw, y + H + hw)
        if len(BR):
            ddx = np.maximum(0, np.maximum(BR[:, 0] - ro[2], ro[0] - BR[:, 2]))
            ddy = np.maximum(0, np.maximum(BR[:, 1] - ro[3], ro[1] - BR[:, 3]))
            if (np.hypot(ddx, ddy) < 0.5).any():
                continue
        best = None
        for segs, L in bbox_leaders(r, gbb):
            lk = segs_clear(segs, grid, forb, cyforb, allowed, [], [b["outer"] for b in blocks])
            if not lk:
                continue
            pen = displace(ro, segs)
            if pen is None:
                continue
            sc_ = d0 + 0.3 * L + (P["leader_cross_cost"] if lk == "cross" else 0.0) + pen
            if best is None or sc_ < best[0]:
                best = (sc_, segs, lk)
            if lk == "clear":
                break
        if best is None:
            continue
        found.append((best[0] + 0.03 * W * H + MODE_COST[lay["mode"]], d0, y, x, r, ro, best[1], best[2]))
        if len(found) >= 30:
            break
    if not found:
        return None
    score, d0, y, x, r, ro, segs, lk = min(found, key=lambda f: (f[0], f[1], f[2], f[3]))
    texts, atexts = {}, []
    for k, L in lay["labels"].items():
        rr = (x + L["rect"][0], y + L["rect"][1], x + L["rect"][2], y + L["rect"][3])
        e = {"rect": rr, "pos": (rr[0] - L["ib"][0], rr[1] - L["ib"][1]), "ang": L["ang"], "style": L["style"]}
        if L["anchor"]:
            e["text"] = k
            atexts.append(e)
        else:
            texts[k] = e
    outlines = {k: (x + o[0], y + o[1], x + o[2], y + o[3]) for k, o in lay["outlines"].items()}
    return {"members": sorted(members, key=natkey), "anchors": sorted([k for k in lay["outlines"] if k not in members], key=natkey),
            "rect": r, "outer": ro, "segs": segs, "texts": texts, "atexts": atexts, "outlines": outlines,
            "dist": d0, "gbb": gbb, "leader": lk, "score": score, "s": lay["s"], "mode": lay["mode"],
            "style": lay["style"]}


def place_map(members, anchors, parts, G, grid, forbS, forb, cyS, cyforb, blocks, radius, displace):
    """both text styles and all three orientation modes; 0.8 x 0.6 carries a small penalty, so it is used when it
    gives a smaller or nearer map (shrink the text before enlarging the frame)"""
    best = None
    for style in ("S", "C"):
        for mode in ("part", "0", "90"):
            lay = map_layout(members, anchors, parts, G, mode, style)
            if lay is None:
                continue
            b = place_frame(lay, members, parts, grid, forbS, forb, cyS, cyforb, blocks, radius, displace)
            if "--debug-maps" in sys.argv:
                print("    map", members[:3], anchors, style, mode, "s=%.2f %.2fx%.2f" % (lay["s"], lay["W"], lay["H"]),
                      "->", None if b is None else "at %.2f,%.2f dist %.2f score %.2f %s" % (
                          b["rect"][0], b["rect"][1], b["dist"], b["score"], b["leader"]))
            if b is not None:
                b["score"] += P["map_style_cost"] if style == "C" else 0.0
                if best is None or b["score"] < best["score"]:
                    best = b
    if best is not None:
        return best
    return None


def make_displace(S, cands, group):
    """cost of moving the designators a block (frame + leader) would sit on: each one needs another candidate that
    is clear of the block and of every other designator; None if one of them has none"""
    chosen = [(r, c) for r, c in sorted(S.choice.items(), key=lambda rc: natkey(rc[0])) if c is not None and r not in group]
    LRr = np.array([c.rect for r, c in chosen], float).reshape(-1, 4)
    cb = P["clr_block"]

    def near(rect, ro, segs):
        if rect_dist(rect, ro) < cb:
            return True
        for a, e in segs:
            sb = (min(a[0], e[0]), min(a[1], e[1]), max(a[0], e[0]), max(a[1], e[1]))
            if rect_dist(sb, rect) < cb + 0.05 and seg_rect_dist(a, e, rect) < cb + 0.05:
                return True
        return False

    def f(ro, segs):
        xs = [ro[0], ro[2]] + [v for a, e in segs for v in (a[0], e[0])]
        ys = [ro[1], ro[3]] + [v for a, e in segs for v in (a[1], e[1])]
        bx = (min(xs) - cb - 0.1, min(ys) - cb - 0.1, max(xs) + cb + 0.1, max(ys) + cb + 0.1)
        if not len(LRr):
            return 0.0
        hit = np.where((LRr[:, 0] < bx[2]) & (LRr[:, 2] > bx[0]) & (LRr[:, 1] < bx[3]) & (LRr[:, 3] > bx[1]))[0]
        tot = 0.0
        for i in hit:
            r, c = chosen[i]
            if not near(c.rect, ro, segs):
                continue
            alt = None
            for c2 in cands[r]:
                if c2 is c or near(c2.rect, ro, segs) or S.conflicts(r, c2.rect):
                    continue
                alt = c2
                break
            if alt is None:
                return None
            tot += P["displace_cost"] + max(0.0, alt.cost - c.cost)
        return tot
    return f


def make_groups(U, parts, neigh, rowp, fixed):
    """legend groups for the parts in U: each part with the aligned small parts it stands in a row / stack with
    (closure over the row-mate graph, at most 6, else its direct row-mates); groups that share a part, or whose
    unplaceable parts touch (courtyards within group_gap), merge; a part standing alone gets its nearest tight
    small neighbours (at most 3) as context"""
    adj = defaultdict(set)
    for a, b, d in rowp:
        adj[a].add(b)
        adj[b].add(a)

    def closure(u):
        comp, st = {u}, [u]
        while st:
            x = st.pop()
            for y in sorted(adj[x], key=natkey):
                if y not in comp and y not in fixed:
                    comp.add(y)
                    st.append(y)
        if len(comp) > 6:
            comp = {u} | {y for y in adj[u] if y not in fixed}
        return comp

    def tight(a, b):
        return parts[a].cyd.dist(parts[b].bb) <= P["group_gap"]

    def merge(gs):
        changed = True
        while changed:
            changed = False
            for i in range(len(gs)):
                for j in range(i + 1, len(gs)):
                    A, B = gs[i], gs[j]
                    if A["members"] & B["members"] or any(tight(a, b) for a in A["failing"] for b in B["failing"]):
                        A["members"] |= B["members"]
                        A["failing"] |= B["failing"]
                        gs.pop(j)
                        changed = True
                        break
                if changed:
                    break
        return gs

    gs = merge([{"members": closure(u), "failing": {u}, "block": None, "anchors": []} for u in sorted(U, key=natkey)])
    for g in gs:
        if len(g["members"]) == 1:
            u = next(iter(g["members"]))
            near = sorted((parts[u].cyd.dist(q.bb), natkey(q.ref), q.ref) for q in neigh[u]
                          if q.small and q.ref not in fixed and parts[u].cyd.dist(q.bb) <= P["group_gap"])
            g["members"] |= {r for _, _, r in near[:3]}
    return merge(gs)


# ------------------------------------------------------------------------------------------------ main
# parts mounted on another part (courtyard inside the other's): the carrier is not an "other part" for its label
OWN_EXEMPT = {"Q1": {"HS1"}}      # BTA24 on the heatsink plate (q1_on_heatsink_courtyard rule)


def neighbours(parts, p, rad=6.0):
    return [q for q in parts if q is not p and rect_dist(p.bb, q.bb) < rad and q.ref not in OWN_EXEMPT.get(p.ref, ())]


CAND_KEYS = ("res", "safety", "clr_mask", "clr_silk", "clr_edge", "clr_hole", "clr_fid", "own_margin",
             "own_margin_aligned", "own_ratio", "own_center", "own_face_margin", "own_slack_cost", "own_slack_ref", "own_cap", "gaps", "off_step", "centred_tol",
             "max_off_steps", "keep_per_key", "keep_total")


def candidates_cached(parts_l, G, grid, forbS0, neigh):
    """candidate generation is the slow step (about 2 min): cached on the geometry, the parameters and the code"""
    h = hashlib.sha1(open(GEOM, "rb").read())
    h.update(json.dumps({k: P[k] for k in CAND_KEYS}, sort_keys=True).encode())
    for f in (gen_candidates, facing, Courtyard, rect_poly_dist, build_obstacles, Part, Grid):
        h.update(inspect.getsource(f).encode())
    h.update((json.dumps(sorted(LARGE)) + json.dumps(STYLE_COST) + json.dumps(STYLE_COST_LARGE) + str(LARGE_AREA) +
              json.dumps({k: sorted(v) for k, v in OWN_EXEMPT.items()}, sort_keys=True)).encode())
    key = h.hexdigest()
    cache = os.path.join(WORK, "cands_cache.pkl")
    if os.path.exists(cache):
        k, allc = pickle.load(open(cache, "rb"))
        if k == key:
            print("candidates from cache")
            return allc
    t0 = time.time()
    allc = {p.ref: gen_candidates(p, G, grid, forbS0, neigh[p.ref]) for p in parts_l}
    print("candidate generation %.0f s" % (time.time() - t0))
    pickle.dump((key, allc), open(cache, "wb"))
    return allc


def filter_cands(allc, fixed, blocks):
    """drop the candidates of the parts in blocks, and every candidate closer than clr_block to a block frame or
    to a leader segment (true segment distance, not its bounding box)"""
    BO = np.array([b["outer"] for b in blocks], float).reshape(-1, 4)
    segs = [(a, c) for b in blocks for a, c in b["segs"]]
    cands = {}
    for r in allc:
        if r in fixed:
            continue
        lst = []
        for c in allc[r]:
            if len(BO):
                ddx = np.maximum(0, np.maximum(BO[:, 0] - c.rect[2], c.rect[0] - BO[:, 2]))
                ddy = np.maximum(0, np.maximum(BO[:, 1] - c.rect[3], c.rect[1] - BO[:, 3]))
                if (np.hypot(ddx, ddy) < P["clr_block"]).any():
                    continue
            bad = False
            for a, e in segs:
                sb = (min(a[0], e[0]), min(a[1], e[1]), max(a[0], e[0]), max(a[1], e[1]))
                if rect_dist(sb, c.rect) < P["clr_block"] + 0.05 and seg_rect_dist(a, e, c.rect) < P["clr_block"] + 0.05:
                    bad = True
                    break
            if not bad:
                lst.append(c)
        cands[r] = lst
    return cands


def main():
    os.makedirs(WORK, exist_ok=True)
    G = json.load(open(GEOM, encoding="utf-8"))
    grid = Grid()
    forb, cyforb = build_obstacles(G, grid)
    forbS0 = grid.integral(forb)
    cyS = grid.integral(cyforb)
    parts_l = sorted([Part(r) for r in G["fps"]], key=lambda p: natkey(p.ref))
    parts = {p.ref: p for p in parts_l}
    neigh = {p.ref: neighbours(parts_l, p) for p in parts_l}
    rowp = row_pairs(parts_l)
    pairs = rowp + near_pairs(parts_l, rowp)
    print("parts %d, row pairs %d, near pairs %d" % (len(parts_l), len(rowp), len(pairs) - len(rowp)))

    if "--explain" in sys.argv:
        for ref in sys.argv[sys.argv.index("--explain") + 1].split(","):
            st = {"clearance": 0, "ownership": 0, "centre": 0, "best_own": {}}
            cs = gen_candidates(parts[ref], G, grid, forbS0, neigh[ref], stats=st)
            print(ref, "bb", [round(v, 2) for v in parts[ref].bb], "cands", len(cs),
                  {k: v for k, v in st.items() if k != "best_own"})
            for k, v in sorted(st["best_own"].items()):
                print("   best ownership slack", k, v)
            for c in cs[:5]:
                print("   ", c.side, c.ang, c.style, c.gap, c.off, round(c.cost, 2), round(c.d_own, 2), round(c.d_oth, 2))
        return
    allc = candidates_cached([p for p in parts_l if p.ref not in SKIP], G, grid, forbS0, neigh)
    allc = pin_reviewed(allc)
    print("candidates: %d total, parts without any: %s" % (sum(len(v) for v in allc.values()),
                                                          [r for r, v in allc.items() if not v]))
    groups = [{"members": set(g["members"]), "failing": set(g["members"]), "anchors": list(g["anchors"]),
               "block": None, "review": True} for g in REVIEW_GROUPS]
    for it in range(8):
        blocks = [g["block"] for g in groups if g["block"]]
        fixed = {m for g in groups if g["block"] is not False for m in g["members"]}
        cands = filter_cands(allc, fixed, blocks)
        S = Solver([parts[r] for r in cands], cands, pairs)
        S.greedy()
        n = S.improve()
        un = sorted([r for r, c in S.choice.items() if c is None], key=natkey)
        print("iteration %d: %d passes, cost %.1f, unplaced %d %s" % (it, n + 1, S.total(), len(un), un))
        if un:
            new = make_groups(un, parts, neigh, rowp, fixed)
            for ng in new:                     # touching an existing group: merge, that map is rebuilt
                for g in groups:
                    if g["members"] & ng["members"] or any(parts[a].cyd.dist(parts[b].bb) <= P["group_gap"]
                                                           for a in g["failing"] for b in ng["failing"]):
                        g["members"] |= ng["members"]
                        g["failing"] |= ng["failing"]
                        g["block"] = None
                        break
                else:
                    groups.append(ng)
        pending = [g for g in groups if g["block"] is None]
        if not pending:
            break
        for g in pending:
            others = [h["block"] for h in groups if h["block"]]
            mem = sorted(g["members"], key=natkey)
            opt = sorted({a for m in mem for a in OPTIONAL_ANCHORS.get(m, []) if a not in g["members"]}, key=natkey)
            tries = []
            for rad in (P["block_radius"], 15.0):
                if opt:
                    tries.append((g["anchors"] + opt, rad))
                tries.append((g["anchors"], rad))
            b = None
            for anc, rad in tries:
                b = place_map(mem, anc, parts, G, grid, forbS0, forb, cyS, cyforb, others, rad,
                              make_displace(S, cands, set(mem)))
                if b is not None:
                    break
            if b is None:
                print("  no map position for", mem)
                g["block"] = False
                continue
            g["block"] = b
            print("  map at (%.2f, %.2f) %.2f x %.2f, scale %.2f, text %s/%s, %.2f mm from the group, leader %s: %s"
                  " | anchors %s" % (b["rect"][0], b["rect"][1], b["rect"][2] - b["rect"][0], b["rect"][3] - b["rect"][1],
                                     b["s"], b["style"], b["mode"], b["dist"], b["leader"], " ".join(b["members"]),
                                     " ".join(b["anchors"]) or "-"))
    if "--debug" in sys.argv:
        for ref in sys.argv[sys.argv.index("--debug") + 1].split(","):
            if ref not in S.cands:
                print(ref, "in a block")
                continue
            cur = S.choice[ref]
            print(ref, "chosen", cur and (cur.side, cur.ang, cur.style, cur.gap, cur.off, round(cur.cost, 2)),
                  "local %.2f" % S.local(ref, cur))
            for c in S.cands[ref][:12]:
                print("   ", c.side, c.ang, c.style, c.gap, round(c.off, 2), "cost %.2f local %.2f" % (c.cost, S.local(ref, c)),
                      "conflicts", sorted(S.conflicts(ref, c.rect)))
    blocks = sorted([g["block"] for g in groups if g["block"]], key=lambda b: (round(b["gbb"][1]), round(b["gbb"][0])))
    in_block = {}
    for i, b in enumerate(blocks):
        b["name"] = "LEG%d" % (i + 1)
        for m in b["members"]:
            in_block[m] = b["name"]
    write_placement(G, parts, S, blocks, in_block)


def seg_boxes(b):
    out = []
    for a, c in b["segs"]:
        out.append((min(a[0], c[0]) - 0.05, min(a[1], c[1]) - 0.05, max(a[0], c[0]) + 0.05, max(a[1], c[1]) + 0.05))
    return out


def write_placement(G, parts, S, blocks, in_block):
    st = G["styles"]
    refs = {}
    for r, p in parts.items():
        if r in SKIP:
            refs[r] = None
            continue
        if r in in_block:
            b = [x for x in blocks if x["name"] == in_block[r]][0]
            t = b["texts"][r]
            h, w, th = st[t["style"]]
            refs[r] = {"x": round(t["pos"][0], 4), "y": round(t["pos"][1], 4), "ang": t["ang"], "style": t["style"],
                       "h": h, "w": w, "t": th, "cls": 4, "block": b["name"], "rect": [round(v, 4) for v in t["rect"]]}
            continue
        c = S.choice.get(r)
        if c is None:
            refs[r] = None
            continue
        h, w, th = st[c.style]
        refs[r] = {"x": round(c.pos[0], 4), "y": round(c.pos[1], 4), "ang": c.ang, "style": c.style, "h": h, "w": w,
                   "t": th, "cls": c.cls, "side": c.side, "gap": c.gap, "off": round(c.off, 3),
                   "d_own": round(c.d_own, 3), "d_oth": round(c.d_oth, 3), "rect": [round(v, 4) for v in c.rect]}
    gfx = []
    R4 = lambda v: round(v, 4)  # noqa: E731
    for b in blocks:
        r = b["rect"]
        gfx.append({"kind": "rect", "start": [R4(r[0]), R4(r[1])], "end": [R4(r[2]), R4(r[3])],
                    "width": P["block_line"], "name": b["name"] + "-frame"})
        for k, o in sorted(b["outlines"].items(), key=lambda kv: natkey(kv[0])):
            gfx.append({"kind": "rect", "start": [R4(o[0]), R4(o[1])], "end": [R4(o[2]), R4(o[3])],
                        "width": P["block_line"], "name": "%s-outline-%s" % (b["name"], k)})
        for t in b["atexts"]:
            h, w, th = st[t["style"]]
            gfx.append({"kind": "text", "text": t["text"], "pos": [R4(t["pos"][0]), R4(t["pos"][1])], "ang": t["ang"],
                        "h": h, "w": w, "t": th, "rect": [R4(v) for v in t["rect"]],
                        "name": "%s-anchor-%s" % (b["name"], t["text"])})
        for k, (a, c) in enumerate(b["segs"]):
            gfx.append({"kind": "line", "start": [R4(a[0]), R4(a[1])], "end": [R4(c[0]), R4(c[1])],
                        "width": P["block_line"], "name": "%s-leader%d" % (b["name"], k)})
    out = {"params": P, "large": sorted(LARGE), "refs": refs, "graphics": gfx,
           "blocks": [{"name": b["name"], "members": b["members"], "anchors": b["anchors"],
                       "rect": [R4(v) for v in b["rect"]], "scale": b["s"], "text_style": b["style"],
                       "text_mode": b["mode"], "dist": round(b["dist"], 3), "leader": b["leader"],
                       "group_bbox": [round(v, 3) for v in b["gbb"]]} for b in blocks]}
    json.dump(out, open(PLACEMENT, "w", encoding="utf-8"), indent=1)
    from collections import Counter
    print("classes:", dict(Counter((v or {}).get("cls") for v in refs.values())))
    print("unplaced:", [r for r, v in refs.items() if v is None])


if __name__ == "__main__":
    main()
