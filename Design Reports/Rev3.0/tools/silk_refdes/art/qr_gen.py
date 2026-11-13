"""Rev3.0 front silkscreen QR code, step 1 of 2 (system python): a QR code that opens the AnnealX product video.

Adapted from the Battery Sentinel Silkscreen-Art generator (silk_art_gen.py, qr_mask) and from art_gen.py here: the
QR is drawn as Battery Sentinel's: the LIGHT modules and the quiet zone are the printed (white) silk, the dark modules
are holes that show the solder mask; the white square has rounded outer corners (QR_CORNER_MM). The lowest QR version
that holds URL at error level M is used (segno), MODULE mm per module, QUIET modules of quiet zone on every side.

Placement by search on an obstacle raster (0.025 mm) of the REAL board (geom_now.json from refdes_geom.py on the
project file, plus the designator ink boxes of placement.json): the white square keeps >= 0.15 mm from every
solder-mask aperture, 0.15 mm from any other silk, 0.15 mm from every courtyard, 0.50 mm from the board edge, 0.30 mm
from holes, and stays out of the ESP32 antenna keep-out. Copper under the mask is no obstacle. The search looks in
REGION (the free strip left of J10 along the bottom edge) first and takes the free position nearest to ANCHOR; with
--anywhere the whole board is searched.

python qr_gen.py --map                       free-space map and the largest free squares (no URL needed)
python qr_gen.py <url> [--anywhere]          -> <WORK>/art/qr.json (+ qr_preview.png)
"""
import json
import os
import sys

import cv2
import numpy as np
import segno
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
from cfg import PLACEMENT, WORK  # noqa: E402
from refdes_place import Grid  # noqa: E402
from art_gen import RES, SIMPLIFY_MM, ANTENNA, trace  # noqa: E402

GEOM_NOW = os.path.join(WORK, "geom_now.json")        # geometry of the real board (refdes_geom.py)
OUT_DIR = os.path.join(WORK, "art")
OUT_JSON = os.path.join(OUT_DIR, "qr.json")

MODULE = 0.5                    # mm per module (20 px at RES 40). Battery Sentinel used 0.625; the pocket left of J10
                                # holds a 19.2 mm square at most, and the 37-module v3 code needs 0.5 mm to fit (18.5 mm)
QUIET = 4                       # modules of white quiet zone on every side (QR spec minimum)
QR_CORNER_MM = 1.8              # radius of the white square's rounded outer corners (Battery Sentinel: 1.8)
CLR = dict(mask=0.15, silk=0.15, cy=0.15, edge=0.50, hole=0.30, safety=0.03)
REGION = (20.0, 95.0, 140.0, 119.0)       # abs mm: bottom strip left of J10 (J10 at 155.65, 112.0)
ANCHOR = (131.0, 108.75)                  # preferred centre: 1.0 mm off the bottom edge (0.5 required), towards J10
STEP = 0.25                               # mm, position search grid


def qr_matrix(url):
    q = segno.make(url, error="m")        # lowest version for the URL at M; segno raises the level if it costs nothing
    return np.array(q.matrix, dtype=np.uint8), q.version, q.error


def qr_mask(m):
    """1 = dark module -> uint8 mask of the printed (white) area: light modules + quiet zone, corners rounded"""
    n = m.shape[0]
    cells = np.pad(m, QUIET, constant_values=0)
    light = (cells == 0).astype(np.uint8) * 255
    px = int(round(MODULE * RES))
    assert abs(px / RES - MODULE) < 1e-9, "MODULE must be a whole number of raster pixels"
    mask = np.kron(light, np.ones((px, px), dtype=np.uint8))
    r = int(round(QR_CORNER_MM * RES))
    rr = Image.new("L", (mask.shape[1], mask.shape[0]), 0)
    ImageDraw.Draw(rr).rounded_rectangle([0, 0, mask.shape[1] - 1, mask.shape[0] - 1], radius=r, fill=255)
    mask = np.where(np.array(rr) > 0, mask, 0).astype(np.uint8)
    return mask, (n + 2 * QUIET) * MODULE


def obstacles(grid):
    G = json.load(open(GEOM_NOW, encoding="utf-8"))
    PL = json.load(open(PLACEMENT, encoding="utf-8"))
    lay = {k: grid.new() for k in ("pad", "silk", "inside", "hole", "cy")}
    for fp in G["fps"]:
        grid.fill(lay["pad"], [rings for pd in fp["pads"] for rings in pd["poly"]])
        grid.fill(lay["silk"], [rings for s in fp["silk"] for rings in s])
        grid.fill(lay["cy"], fp["cy"])
    grid.fill(lay["silk"], [rings for s in G["silk"] for rings in s["poly"]])   # legend, maps, artwork
    d = ImageDraw.Draw(lay["silk"])
    for v in PL["refs"].values():                                              # designators (Reference fields)
        if v:
            (a, b), (c, e) = grid.px(v["rect"][0], v["rect"][1]), grid.px(v["rect"][2], v["rect"][3])
            d.rectangle([a, b, c, e], fill=1)
    grid.fill(lay["inside"], G["edge"]["outline"])
    d = ImageDraw.Draw(lay["hole"])
    for cx, cy, r, _ in G["edge"]["holes"]:
        (a, b), (c, e) = grid.px(cx - r, cy - r), grid.px(cx + r, cy + r)
        d.ellipse([a, b, c, e], fill=1, outline=1)
    arr = {k: np.array(v, dtype=bool) for k, v in lay.items()}
    arr["outside"] = ~arr.pop("inside")
    forb = np.zeros((grid.h, grid.w), bool)
    for k, c in (("pad", CLR["mask"]), ("silk", CLR["silk"]), ("cy", CLR["cy"]), ("outside", CLR["edge"]),
                 ("hole", CLR["hole"])):
        forb |= ndimage.distance_transform_edt(~arr[k]) * grid.res < c + CLR["safety"]
    i0, j0, i1, j1 = grid.idx(ANTENNA)
    forb[max(0, j0):j1, max(0, i0):i1] = True
    return forb, G


def free_positions(grid, S, side, region):
    """top-left corners (abs mm) on the STEP grid inside region where a side x side square is free"""
    X = np.arange(region[0], region[2] - side + 1e-9, STEP)
    Y = np.arange(region[1], region[3] - side + 1e-9, STEP)
    if not len(X) or not len(Y):
        return np.zeros(0), np.zeros(0)
    XX, YY = np.meshgrid(X, Y)
    XX, YY = XX.ravel(), YY.ravel()
    i0 = np.floor((XX - grid.x0) / grid.res).astype(int)
    j0 = np.floor((YY - grid.y0) / grid.res).astype(int)
    i1 = np.ceil((XX + side - grid.x0) / grid.res).astype(int)
    j1 = np.ceil((YY + side - grid.y0) / grid.res).astype(int)
    ok = (i0 >= 0) & (j0 >= 0) & (i1 <= grid.w) & (j1 <= grid.h)
    i0, j0 = np.clip(i0, 0, grid.w), np.clip(j0, 0, grid.h)
    i1, j1 = np.clip(i1, 0, grid.w), np.clip(j1, 0, grid.h)
    ok &= (S[j1, i1] - S[j0, i1] - S[j1, i0] + S[j0, i0]) == 0
    return XX[ok], YY[ok]


def largest_square(grid, S, region):
    """largest free square (side mm, top-left) inside region, bisection on the side in 0.125 mm steps"""
    lo, hi = 0.0, min(region[2] - region[0], region[3] - region[1])
    best = None
    while hi - lo > 0.125:
        mid = (lo + hi) / 2
        xs, ys = free_positions(grid, S, mid, region)
        if len(xs):
            lo, best = mid, (mid, xs, ys)
        else:
            hi = mid
    return best


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    grid = Grid()
    forb, G = obstacles(grid)
    S = grid.integral(forb)
    board = [grid.x0, grid.y0, grid.x0 + grid.w * grid.res, grid.y0 + grid.h * grid.res]
    if "--map" in sys.argv:
        Image.fromarray((~forb[::4, ::4]).astype(np.uint8) * 255).save(os.path.join(OUT_DIR, "qr_free_map.png"))
        for name, reg in (("REGION (bottom strip left of J10)", REGION), ("whole board", board)):
            b = largest_square(grid, S, reg)
            if b is None:
                print("%s: no free square" % name)
                continue
            side, xs, ys = b
            print("%s: largest free square %.2f mm, %d positions, x %.2f..%.2f y %.2f..%.2f (top-left corners)" % (
                name, side, len(xs), xs.min(), xs.max(), ys.min(), ys.max()))
        # how the free strip is shaped: for a few square sizes, the x span of free top-left corners in REGION
        for side in (12.0, 16.0, 18.0, 20.0, 20.625, 23.125, 25.0):
            xs, ys = free_positions(grid, S, side, REGION)
            if len(xs):
                print("  square %6.3f mm: %5d positions, x %.2f..%.2f y %.2f..%.2f" % (side, len(xs), xs.min(), xs.max(),
                                                                                  ys.min(), ys.max()))
            else:
                print("  square %6.3f mm: none" % side)
        return
    url = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    m, ver, ec = qr_matrix(url)
    mask, side = qr_mask(m)
    region = board if "--anywhere" in sys.argv else REGION
    xs, ys = free_positions(grid, S, side, region)
    if not len(xs):
        b = largest_square(grid, S, region)
        raise SystemExit("QR v%d (%d modules, %.3f mm with quiet zone) does not fit in the region; largest free square "
                         "there is %.2f mm" % (ver, m.shape[0], side, b[0] if b else 0))
    cx, cy = xs + side / 2, ys + side / 2
    print("free top-left corners for a %.3f mm square: x %.2f..%.2f y %.2f..%.2f" % (side, xs.min(), xs.max(), ys.min(), ys.max()))
    k = int(np.argmin(np.hypot(cx - ANCHOR[0], cy - ANCHOR[1])))
    x0, y0 = float(xs[k]), float(ys[k])
    shapes = trace(mask, x0, y0)
    bbox = [round(x0, 3), round(y0, 3), round(x0 + side, 3), round(y0 + side, 3)]
    item = {"name": "qr", "layer": "F.SilkS", "shapes": shapes, "bbox": bbox}
    json.dump({"url": url, "version": ver, "error_level": ec, "modules": int(m.shape[0]), "module_mm": MODULE,
               "quiet_modules": QUIET, "corner_mm": QR_CORNER_MM, "size_mm": round(side, 3), "bbox": bbox,
               "centre": [round(x0 + side / 2, 3), round(y0 + side / 2, 3)], "clearances": CLR,
               "free_positions": int(len(xs)), "matrix": m.tolist(), "items": [item]},
              open(OUT_JSON, "w", encoding="utf-8"))
    print("QR v%d-%s, %dx%d modules of %.3f mm, white square %.3f mm (quiet zone %d), corners R%.1f" % (
        ver, ec, m.shape[0], m.shape[0], MODULE, side, QUIET, QR_CORNER_MM))
    print("placed at x %.3f..%.3f y %.3f..%.3f (centre %.3f, %.3f), %d free positions in the region, %d polygons, %d holes" % (
        bbox[0], bbox[2], bbox[1], bbox[3], x0 + side / 2, y0 + side / 2, len(xs), len(shapes),
        sum(len(s["holes"]) for s in shapes)))
    s = 20
    pv = Image.new("L", (int(side * s) + 20, int(side * s) + 20), 30)
    d = ImageDraw.Draw(pv)
    for sh in shapes:
        d.polygon([((x - x0) * s + 10, (y - y0) * s + 10) for x, y in sh["outline"]], fill=255)
        for h in sh["holes"]:
            d.polygon([((x - x0) * s + 10, (y - y0) * s + 10) for x, y in h], fill=30)
    pv.save(os.path.join(OUT_DIR, "qr_preview.png"))
    print("wrote", OUT_JSON, "and qr_preview.png")


if __name__ == "__main__":
    main()
