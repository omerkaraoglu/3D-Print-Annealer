"""Rev3.0 front silkscreen artwork, step 1 of 2 (system python): readark logo + Manrope text block.

Adapted from the Battery Sentinel Silkscreen-Art generator (silk_art_gen.py): the logo PNG and every text line are
rasterised at RES px/mm and traced with OpenCV into filled polygons (outline + holes) in board mm.

The block (logo, then the centred text lines under it) is placed by search on an obstacle raster (0.025 mm) of the
staged board: no ink box within 0.15 mm of a solder-mask aperture, 0.15 mm of any other silk (library silk, board
legend, designators, legend-map graphics), 0.15 mm of a courtyard, 1.0 mm of the board edge (0.5 required), 0.3 mm of a hole, and
nothing in the ESP32 antenna keep-out. The board title texts of the legend (title-0..3) are replaced by the artwork
and are not obstacles. Copper under the mask is no obstacle. The logo is made as wide as any free spot allows
(LOGO_WIDTHS, largest first); among the free spots of that size the one nearest to ANCHOR wins.

python art_gen.py [--map]          -> <WORK>/art/art.json (+ preview PNG; --map also writes the free-space map)
"""
import json
import math
import os
import sys
import uuid

import cv2
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from cfg import GEOM, LABELS, PLACEMENT, WORK  # noqa: E402
from refdes_place import Grid  # noqa: E402

ASSETS = os.path.join(HERE, "assets")
LOGO_PNG = os.path.join(ASSETS, "readark-logo-white.png")
FONT_TTF = os.path.join(ASSETS, "Manrope[wght].ttf")
OUT_DIR = os.path.join(WORK, "art")
OUT_JSON = os.path.join(OUT_DIR, "art.json")
NS = uuid.UUID("6b1f3c2e-9a57-4f0e-8d3b-5c1a2e7f9b40")

RES = 40.0                      # px per mm for the artwork raster
SIMPLIFY_MM = 0.012             # contour simplification tolerance
CLR = dict(mask=0.15, silk=0.15, cy=0.15, edge=1.00, hole=0.30, safety=0.03)   # edge: 0.5 required, 1.0 for looks
ANTENNA = (19.0, 56.0, 27.6, 84.0)          # ESP32 antenna keep-out rule area (all layers), abs mm
REPLACES = ["title-0", "title-1", "title-2", "title-3"]   # legend texts (labels.json names) the artwork replaces

DATE = "2026-11-13"
NAME = "OVEN CONTROLLER"          # board name, the first line; its cap height follows the logo width (2.5..3.5 mm)
NAME_WEIGHT = 700
TEXT_LINES = [   # (text, cap height mm, Manrope weight), under the name; weights chosen for >= 0.15 mm strokes
    ("PCB Rev3.0 · " + DATE, 1.2, 700),
    ("Designed by Ömer Karaoğlu · readark", 1.2, 700),
    ("230 V~ · 1 kW heater · 7\" touch · K-type TC", 1.1, 800),
]
LOGO_GAP = 1.0                  # mm between the logo and the name (ink to ink)
LINE_GAP = [0.8, 0.6, 0.5]      # mm between consecutive lines (ink box to ink box)
LOGO_WIDTHS = [w / 2 for w in range(80, 49, -1)]   # 40 .. 25 mm in 0.5 mm steps
ANCHOR = (167.0, 90.0)          # preferred block centre: the old title block, right of the RGB ribbon
STEP = 0.25                     # mm, position search grid


# ----------------------------------------------------------------- artwork rasters
def trace(mask, x0_mm, y0_mm):
    """binary mask (row 0 = top) -> [{outline, holes}] in mm, (x0, y0) = board position of the top-left pixel corner"""
    contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return []
    hier = hier[0]
    eps = SIMPLIFY_MM * RES

    def to_mm(c):
        c = cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(float)
        xs = x0_mm + (c[:, 0] + 0.5) / RES
        ys = y0_mm + (c[:, 1] + 0.5) / RES
        return [[round(float(x), 4), round(float(y), 4)] for x, y in zip(xs, ys)]

    shapes = []
    for i, c in enumerate(contours):
        if hier[i][3] != -1 or cv2.contourArea(c) < (0.02 * RES) ** 2:
            continue
        holes = []
        child = hier[i][2]
        while child != -1:
            if cv2.contourArea(contours[child]) >= (0.02 * RES) ** 2:
                holes.append(to_mm(contours[child]))
            child = hier[child][0]
        outline = to_mm(c)
        if len(outline) >= 3:
            shapes.append({"outline": outline, "holes": [h for h in holes if len(h) >= 3]})
    return shapes


def logo_mask(width_mm):
    a = np.array(Image.open(LOGO_PNG).convert("RGBA"))[..., 3]
    ys, xs = np.where(a > 40)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w_px = int(round(width_mm * RES))
    h_px = int(round(width_mm * a.shape[0] / a.shape[1] * RES))
    alpha = Image.fromarray(a).resize((w_px, h_px), Image.LANCZOS)
    return (np.array(alpha) >= 128).astype(np.uint8) * 255


def text_mask(text, cap_mm, weight):
    """mask cropped to the ink, plus the baseline row (px from the top of the crop)"""
    meta = TTFont(FONT_TTF)
    cap_ratio = meta["OS/2"].sCapHeight / meta["head"].unitsPerEm
    font = ImageFont.truetype(FONT_TTF, size=int(round(cap_mm * RES / cap_ratio)))
    font.set_variation_by_axes([weight])
    l, t, r, b = font.getbbox(text, anchor="ls")
    pad = 4
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=255, anchor="ls")
    m = (np.array(im) >= 128).astype(np.uint8) * 255
    ys, xs = np.where(m > 0)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return m, (pad - t) - ys.min()


def stroke_min(mask):
    """thinnest printed feature (mm): twice the largest inscribed distance along the skeleton's thinnest parts is
    approximated by the 2nd percentile of 2 x distance-to-background over the medial pixels"""
    d = ndimage.distance_transform_edt(mask > 0)
    med = (d >= ndimage.maximum_filter(d, size=3)) & (d > 0)
    return float(np.percentile(2 * d[med], 2)) / RES


def name_cap(W):
    """cap height of the name so that it is as wide as the logo, within 2.5..3.5 mm"""
    m, _ = text_mask(NAME, 3.0, NAME_WEIGHT)
    return round(min(3.5, max(2.5, 3.0 * W / (m.shape[1] / RES))), 2)


def lines(W):
    return [(NAME, name_cap(W), NAME_WEIGHT)] + TEXT_LINES


def layout(W):
    """the block for a logo of width W: list of (name, mask, x_off, y_off) relative to the block's top centre"""
    parts = []
    lm = logo_mask(W)
    parts.append(("logo", lm, -lm.shape[1] / RES / 2, 0.0))
    y = lm.shape[0] / RES + LOGO_GAP
    for k, (text, cap, wt) in enumerate(lines(W)):
        m, base = text_mask(text, cap, wt)
        if k:
            y += LINE_GAP[k - 1]
        parts.append(("line%d" % k, m, -m.shape[1] / RES / 2, y))
        y += m.shape[0] / RES
    return parts


# ----------------------------------------------------------------- obstacle raster of the staged board
def obstacles(grid):
    G = json.load(open(GEOM, encoding="utf-8"))
    PL = json.load(open(PLACEMENT, encoding="utf-8"))
    LB = json.load(open(LABELS, encoding="utf-8"))
    skip = {str(uuid.uuid5(NS, n)) for n in REPLACES}
    lay = {k: grid.new() for k in ("pad", "silk", "inside", "hole", "cy")}
    for fp in G["fps"]:
        grid.fill(lay["pad"], [rings for pd in fp["pads"] for rings in pd["poly"]])
        grid.fill(lay["silk"], [rings for s in fp["silk"] for rings in s])
        grid.fill(lay["cy"], fp["cy"])
    grid.fill(lay["silk"], [rings for s in G["silk"] if s.get("uuid") not in skip for rings in s["poly"]])
    rects = [v["rect"] for v in PL["refs"].values() if v]
    for g in PL["graphics"]:
        if g["kind"] == "text":
            rects.append(g["rect"])
        else:
            (x0, y0), (x1, y1) = g["start"], g["end"]
            rects.append([min(x0, x1) - 0.05, min(y0, y1) - 0.05, max(x0, x1) + 0.05, max(y0, y1) + 0.05])
    d = ImageDraw.Draw(lay["silk"])
    for r in rects:
        (a, b), (c, e) = grid.px(r[0], r[1]), grid.px(r[2], r[3])
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
    return forb, LB


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    grid = Grid()
    forb, LB = obstacles(grid)
    S = grid.integral(forb)
    if "--map" in sys.argv:
        Image.fromarray((~forb[::4, ::4]).astype(np.uint8) * 255).save(os.path.join(OUT_DIR, "free_map.png"))
    best = None
    for W in LOGO_WIDTHS:
        parts = layout(W)
        rel = [(n, x, y, x + m.shape[1] / RES, y + m.shape[0] / RES) for n, m, x, y in parts]
        bx0 = min(r[1] for r in rel)
        bx1 = max(r[3] for r in rel)
        by1 = max(r[4] for r in rel)
        # candidate block origins (top centre) on the search grid
        X = np.arange(grid.x0 - bx0, grid.x0 + grid.w * grid.res - bx1, STEP)
        Y = np.arange(grid.y0, grid.y0 + grid.h * grid.res - by1, STEP)
        XX, YY = np.meshgrid(X, Y)
        XX, YY = XX.ravel(), YY.ravel()
        ok = np.ones(len(XX), bool)
        for n, a, b, c, d in rel:
            i0 = np.floor((XX + a - grid.x0) / grid.res).astype(int)
            j0 = np.floor((YY + b - grid.y0) / grid.res).astype(int)
            i1 = np.ceil((XX + c - grid.x0) / grid.res).astype(int)
            j1 = np.ceil((YY + d - grid.y0) / grid.res).astype(int)
            good = (i0 >= 0) & (j0 >= 0) & (i1 <= grid.w) & (j1 <= grid.h)
            i0, j0 = np.clip(i0, 0, grid.w), np.clip(j0, 0, grid.h)
            i1, j1 = np.clip(i1, 0, grid.w), np.clip(j1, 0, grid.h)
            ok &= good & ((S[j1, i1] - S[j0, i1] - S[j1, i0] + S[j0, i0]) == 0)
        if ok.any():
            cx, cy = XX[ok], YY[ok] + by1 / 2
            k = int(np.argmin(np.hypot(cx - ANCHOR[0], cy - ANCHOR[1])))
            best = (W, float(XX[ok][k]), float(YY[ok][k]), parts, rel, int(ok.sum()))
            break
    if best is None:
        raise SystemExit("no free spot for the artwork")
    W, ox, oy, parts, rel, nfree = best
    items = []
    for (n, m, x, y), r in zip(parts, rel):
        shapes = trace(m, ox + x, oy + y)
        items.append({"name": n, "layer": "F.SilkS", "shapes": shapes,
                      "bbox": [round(ox + r[1], 3), round(oy + r[2], 3), round(ox + r[3], 3), round(oy + r[4], 3)],
                      "min_feature_mm": round(stroke_min(m), 3)})
    texts = [{"text": t, "cap_mm": c, "weight": w} for t, c, w in lines(W)]
    bb = [min(i["bbox"][0] for i in items), min(i["bbox"][1] for i in items), max(i["bbox"][2] for i in items),
          max(i["bbox"][3] for i in items)]
    json.dump({"logo_width": W, "origin_top_centre": [round(ox, 3), round(oy, 3)], "bbox": bb, "lines": texts,
               "replaces": REPLACES, "clearances": CLR, "free_positions_at_this_width": nfree, "items": items},
              open(OUT_JSON, "w", encoding="utf-8"))
    print("logo width %.1f mm, block %.2f x %.2f mm at x %.2f..%.2f y %.2f..%.2f (%d free positions at this size)" % (
        W, bb[2] - bb[0], bb[3] - bb[1], bb[0], bb[2], bb[1], bb[3], nfree))
    for it in items:
        print("  %-6s bbox %s  polys %d  thinnest feature %.3f mm" % (it["name"], it["bbox"], len(it["shapes"]),
                                                                    it["min_feature_mm"]))
    # preview, 20 px/mm
    s = 20
    pv = Image.new("L", (int((bb[2] - bb[0]) * s) + 20, int((bb[3] - bb[1]) * s) + 20), 30)
    d = ImageDraw.Draw(pv)
    for it in items:
        for sh in it["shapes"]:
            d.polygon([((x - bb[0]) * s + 10, (y - bb[1]) * s + 10) for x, y in sh["outline"]], fill=255)
            for h in sh["holes"]:
                d.polygon([((x - bb[0]) * s + 10, (y - bb[1]) * s + 10) for x, y in h], fill=30)
    pv.save(os.path.join(OUT_DIR, "art_preview.png"))


if __name__ == "__main__":
    main()
