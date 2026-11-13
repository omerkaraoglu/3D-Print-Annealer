"""J10 / J11 (and the unused lower-contact variants) - 0.5 mm FPC connectors.

Connfly DS1020-09 series, drawing C-DS1020-09-XXXXX-E rev E (2024-06-26),
via LCSC C94919 (DS1020-09-15VBT1B):
  body length 0.5*N + 5.6, depth D = 5.2 (N 4..34) / 5.75 (N 35..60),
  height 2.0 +-0.15, FPC slot 0.5*N + 0.56, terminals 0.5 pitch,
  land pattern pads 0.30 x 1.80, fitting nails 2.50 x 3.20 (pad set as in the footprints).
  V = ivory housing, B = black actuator (cover), T1 = tin, A/B = lower/upper contact.
KLS L-KLS1-242D-1.2-06-T-U-R (KLS drawing KLS1-242D-1.2 as transcribed in the
footprint): body 9.0 x 4.1, H 1.2, pads 0.30 x 1.25, anchors 2.00 x 2.45 at
2.54 outside the end pads.  ESTIMATED: actuator split and anchor shape.
Frame: terminal row at the footprint's -y edge (model +Y), FPC entry at the
footprint's +y edge (model -Y); 'pin1_plus_x' follows the TopSide footprints,
whose pad numbers are mirrored (panel order).
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def fpc(name, footprint, n, length, depth, height, pad_len, anchor_xy, anchor_wh, pin1_plus_x, descr,
        slot_w=None):
    m = Model(name, footprint, descr)
    hd = depth / 2
    yb = hd                                  # terminal edge (model +Y)
    housing = box(-length / 2, length / 2, -hd, hd, 0, height * 0.55)
    housing = housing.union(box(-length / 2, -length / 2 + 1.6, -hd, hd, 0, height))
    housing = housing.union(box(length / 2 - 1.6, length / 2, -hd, hd, 0, height))
    housing = housing.union(box(-length / 2, length / 2, hd - 1.2, hd, 0, height))
    sw = slot_w or (0.5 * n + 0.56)
    slot = box(-sw / 2, sw / 2, -hd - 0.1, hd - 1.4, height * 0.25, height * 0.45)
    m.add("housing", housing.cut(slot), "ivory")
    m.add("actuator", box(-length / 2 + 1.7, length / 2 - 1.7, -hd, hd - 1.3, height * 0.55, height), "black")
    pitch = 0.5
    for i in range(n):
        k = i if not pin1_plus_x else (n - 1 - i)
        x = (k - (n - 1) / 2) * pitch
        m.pin(str(i + 1), box(x - 0.1, x + 0.1, yb - pad_len / 2 + 0.1, yb + pad_len / 2 - 0.1, 0, 0.12), "tin")
    ax, ay = anchor_xy
    aw, ah = anchor_wh
    for sx in (-1, 1):
        m.pin("MP", box(sx * ax - aw * 0.3, sx * ax + aw * 0.3, -ay - ah * 0.35, -ay + ah * 0.35, 0, 0.15), "tin")
        xe = sx * length / 2
        m.add("nail_side", box(min(xe, sx * (ax + aw * 0.3)), max(xe, sx * (ax + aw * 0.3)),
                               -ay - ah * 0.35, -ay + ah * 0.35, 0, 0.15), "tin")
    return m


def build_all():
    N = 40
    return [
        fpc("Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide",
            "Rev3:Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide",
            N, 0.5 * N + 5.6, 5.75, 2.0, 1.8, (11.7, -0.975), (2.5, 3.2), True,
            "Connfly DS1020-09-40VBT1B 25.6 x 5.75 x 2.0, upper contact, pads in panel order"),
        fpc("Connfly_DS1020-09-40VBT1A_1x40_P0.5mm_Horizontal",
            "Rev3:Connfly_DS1020-09-40VBT1A_1x40_P0.5mm_Horizontal",
            N, 0.5 * N + 5.6, 5.75, 2.0, 1.8, (11.7, -0.975), (2.5, 3.2), False,
            "Connfly DS1020-09-40VBT1A 25.6 x 5.75 x 2.0, lower contact"),
        fpc("Connfly_DS1020-09-06VBT1A_1x06_P0.5mm_Horizontal",
            "Rev3:Connfly_DS1020-09-06VBT1A_1x06_P0.5mm_Horizontal",
            6, 0.5 * 6 + 5.6, 5.2, 2.0, 1.8, (3.2, -0.7), (2.5, 3.2), False,
            "Connfly DS1020-09-06VBT1A 8.6 x 5.2 x 2.0, lower contact"),
        fpc("KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide",
            "Rev3:KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide",
            6, 9.0, 4.1, 1.2, 1.25, (3.79, 0.55), (2.0, 2.45), True,
            "KLS L-KLS1-242D-1.2-06-T-U-R 9.0 x 4.1 x 1.2, upper contact, pads in panel order", slot_w=3.6),
    ]


if __name__ == "__main__":
    for m in build_all():
        run(m)
