"""Board-level silkscreen legend of the Rev3.0 board (functional labels, pin / polarity marks, title block, mains
warning) and the fabrication notes on Cmts.User, in the style of the Battery Sentinel silk.py pass.

python silk_labels.py <geom.json of the untouched board> <labels.json>

- Every label of labels_def.LABELS is placed at the free spot nearest to its first target that has one: no ink within
  0.25 mm of a solder-mask aperture, 0.5 mm of any silk that stays (library outlines, polarity marks), 0.5 mm of the
  board edge or a hole, 0.3 mm of another legend text of its own cluster and 0.5 mm of any other legend text
  (each clearance plus the 0.03 mm raster safety margin).
- Blocks (title, mains warning) are centred lines placed as one unit; they also keep 0.3 mm from every courtyard and
  0.2 mm from F.Cu tracks (legibility; tented vias are no obstacle), and the mains warning stays inside the Cmts.User mains outline
  (1 mm inside).
- The old board texts listed in labels_def.OLD_TEXTS are removed (they are not obstacles here).
Footprint Reference fields are not obstacles: the designators are placed afterwards around this legend.
"""
import json
import math
import os
import sys

import numpy as np
from matplotlib.path import Path as MPath
from PIL import ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labels_def as LD  # noqa: E402
from refdes_place import Grid, rect_dist  # noqa: E402

C = dict(pad=0.25, silk=0.50, edge=0.50, hole=0.50, cluster=0.30, other=0.50, block_cy=0.30, block_trk=0.20,
         safety=0.03, step=0.05, mains_inset=1.0)


def build(G, grid):
    lay = {k: grid.new() for k in ("pad", "silk", "inside", "hole", "cy", "trk")}
    for fp in G["fps"]:
        grid.fill(lay["pad"], [rings for pd in fp["pads"] for rings in pd["poly"]])
        grid.fill(lay["silk"], [rings for s in fp["silk"] for rings in s])
        grid.fill(lay["cy"], fp["cy"])
    grid.fill(lay["silk"], [rings for s in G["silk"] if s.get("uuid") not in LD.OLD_TEXTS for rings in s["poly"]])
    grid.fill(lay["inside"], G["edge"]["outline"])
    grid.fill(lay["trk"], G["tracks"])
    d = ImageDraw.Draw(lay["hole"])
    for cx, cy, r, _ in G["edge"]["holes"]:
        (a, b), (c, e) = grid.px(cx - r, cy - r), grid.px(cx + r, cy + r)
        d.ellipse([a, b, c, e], fill=1, outline=1)
    arr = {k: np.array(v, dtype=bool) for k, v in lay.items()}
    arr["outside"] = ~arr.pop("inside")
    forb = np.zeros((grid.h, grid.w), bool)
    for k, c in (("pad", C["pad"]), ("silk", C["silk"]), ("outside", C["edge"]), ("hole", C["hole"])):
        forb |= ndimage.distance_transform_edt(~arr[k]) * grid.res < c + C["safety"]
    fblk = forb.copy()
    fblk |= ndimage.distance_transform_edt(~arr["cy"]) * grid.res < C["block_cy"] + C["safety"]
    fblk |= ndimage.distance_transform_edt(~arr["trk"]) * grid.res < C["block_trk"] + C["safety"]
    return grid.integral(forb), grid.integral(fblk)


def mains_path(G):
    """closed polygon of the Cmts.User mains outline (open chain from the top edge back to the top edge)"""
    segs = [tuple(map(tuple, s)) for s in G["mains_outline"]]
    pts = {}
    for a, b in segs:
        for p in (a, b):
            k = (round(p[0], 2), round(p[1], 2))
            pts[k] = pts.get(k, 0) + 1
    ends = sorted([k for k, n in pts.items() if n == 1])
    start = ends[0]
    chain, cur, left = [start], start, list(segs)
    while left:
        for s in left:
            a, b = (round(s[0][0], 2), round(s[0][1], 2)), (round(s[1][0], 2), round(s[1][1], 2))
            if a == cur or b == cur:
                cur = b if a == cur else a
                chain.append(cur)
                left.remove(s)
                break
        else:
            break
    return MPath(np.array(chain + [chain[0]]))


def spots(target, R, step):
    tx, ty, _ = target
    n = int(R / step)
    k = np.arange(-n, n + 1) * step
    X, Y = np.meshgrid(tx + k, ty + k)
    X, Y = X.ravel(), Y.ravel()
    d = np.hypot(X - tx, Y - ty)
    ok = d <= R + 1e-9
    o = np.lexsort((X[ok], Y[ok], d[ok]))
    return X[ok][o], Y[ok][o]


def free(grid, S, rects):
    """rects: (n, 4) absolute mm -> bool mask of rects with no forbidden pixel"""
    i0 = np.floor((rects[:, 0] - grid.x0) / grid.res).astype(int)
    j0 = np.floor((rects[:, 1] - grid.y0) / grid.res).astype(int)
    i1 = np.ceil((rects[:, 2] - grid.x0) / grid.res).astype(int)
    j1 = np.ceil((rects[:, 3] - grid.y0) / grid.res).astype(int)
    inb = (i0 >= 0) & (j0 >= 0) & (i1 <= grid.w) & (j1 <= grid.h)
    i0, j0, i1, j1 = [np.clip(v, 0, m) for v, m in ((i0, grid.w), (j0, grid.h), (i1, grid.w), (j1, grid.h))]
    cnt = S[j1, i1] - S[j0, i1] - S[j1, i0] + S[j0, i0]
    return inb & (cnt == 0)


def main():
    G = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    grid = Grid()
    S, SB = build(G, grid)
    ink = G["label_ink"]
    placed = []          # (name, cluster, rect)
    texts, missed = [], []

    def clear_of_placed(r, cluster):
        for n, cl, pr in placed:
            lim = C["cluster"] if (cluster and cl == cluster) else C["other"]
            if rect_dist(r, pr) < lim:
                return False
        return True

    for L in LD.LABELS:
        ib = ink[L["name"]]
        got = None
        for tg in L["targets"]:
            X, Y = spots(tg, tg[2], C["step"])
            R = np.stack([X + ib[0], Y + ib[1], X + ib[2], Y + ib[3]], 1)
            ok = free(grid, S, R)
            for k in np.nonzero(ok)[0]:
                r = tuple(float(v) for v in R[k])
                if clear_of_placed(r, L.get("cluster")):
                    got = (float(X[k]), float(Y[k]), r, tg)
                    break
            if got:
                break
        if not got:
            missed.append(L["name"])
            continue
        x, y, r, tg = got
        placed.append((L["name"], L.get("cluster"), r))
        h, w, t = L["size"]
        texts.append({"name": "label-" + L["name"], "text": L["text"], "pos": [round(x, 4), round(y, 4)],
                      "ang": L["ang"], "h": h, "w": w, "t": t, "layer": "F.SilkS", "rect": [round(v, 4) for v in r],
                      "shift": round(math.hypot(x - tg[0], y - tg[1]), 3), "target": list(tg)})

    mp = mains_path(G)
    for B in LD.BLOCKS:
        # line offsets: centred lines stacked with B["gap"] between ink boxes
        inks = [ink["%s.%d" % (B["name"], k)] for k in range(len(B["lines"]))]
        ys, y = [], 0.0
        for k, ib in enumerate(inks):
            if k:
                y += inks[k - 1][3] + B["gap"] - ib[1]
            ys.append(y)
        mid = (ys[0] + inks[0][1] + ys[-1] + inks[-1][3]) / 2
        ys = [v - mid for v in ys]
        got = None
        for tg in B["targets"]:
            X, Y = spots(tg, tg[2], 0.1)
            ok = np.ones(len(X), bool)
            for ib, dy in zip(inks, ys):
                R = np.stack([X + ib[0], Y + dy + ib[1], X + ib[2], Y + dy + ib[3]], 1)
                ok &= free(grid, SB, R)
            for k in np.nonzero(ok)[0]:
                rs = [(X[k] + ib[0], Y[k] + dy + ib[1], X[k] + ib[2], Y[k] + dy + ib[3]) for ib, dy in zip(inks, ys)]
                if not all(clear_of_placed(r, None) for r in rs):
                    continue
                if B.get("region") == "mains":
                    m = C["mains_inset"]
                    cs = [(r[0] - m, r[1] - m) for r in rs] + [(r[2] + m, r[1] - m) for r in rs] + \
                         [(r[0] - m, r[3] + m) for r in rs] + [(r[2] + m, r[3] + m) for r in rs]
                    if not all(mp.contains_point(c) for c in cs):
                        continue
                got = (float(X[k]), float(Y[k]), rs, tg)
                break
            if got:
                break
        if not got:
            missed.append(B["name"])
            continue
        x, y, rs, tg = got
        for k, ((txt, sz), dy, r) in enumerate(zip(B["lines"], ys, rs)):
            placed.append(("%s.%d" % (B["name"], k), None, r))
            texts.append({"name": "%s-%d" % (B["name"], k), "text": txt, "pos": [round(x, 4), round(y + dy, 4)],
                          "ang": 0, "h": sz[0], "w": sz[1], "t": sz[2], "layer": "F.SilkS",
                          "rect": [round(float(v), 4) for v in r], "shift": round(math.hypot(x - tg[0], y - tg[1]), 3),
                          "target": list(tg)})
    for k, line in enumerate(LD.FAB_NOTES):
        texts.append({"name": "fabnote-%d" % k, "text": line, "pos": [LD.FAB_X, round(LD.FAB_Y + k * LD.FAB_DY, 4)],
                      "ang": 0, "h": 1.0, "w": 1.0, "t": 0.12, "layer": "Cmts.User", "justify": "left"})
    json.dump({"params": C, "delete": LD.OLD_TEXTS, "texts": texts, "missed": missed}, open(out, "w", encoding="utf-8"),
              indent=1)
    for t in texts:
        if t["layer"] == "F.SilkS":
            print("  %-12s %-28s at %7.2f %7.2f  (%.2f mm from its target)" % (t["name"], t["text"], t["pos"][0],
                                                                              t["pos"][1], t["shift"]))
    print("legend texts %d, fabrication note lines %d, not placed: %s" % (
        sum(t["layer"] == "F.SilkS" for t in texts), len(LD.FAB_NOTES), missed or "none"))
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
