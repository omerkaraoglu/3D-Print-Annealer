"""C40 - Faratronic C42P2105KBSC400, 1 uF 275 VAC X2 MKP box, P27.5.

Source: Faratronic MKP62 (C42) data sheet, "Dimensions (mm) - Miniature version
275Vac" table: 1.0 uF  W 32.0  H 18.0  T 9.0 (+-0.4)  P 27.5  d 0.8, part
C42P2105-BS (digit 11 'S' = miniature); copy at
pdf.direnc.net/upload/1uf-275vac-polyester-kondansator-datasheet.pdf.
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

W, H, T, P, d = 32.0, 18.0, 9.0, 27.5, 0.8


def build():
    m = Model("C_Rect_L32.0mm_W9.0mm_P27.50mm_X2_Faratronic_C42", "Rev3:C_Rect_L32.0mm_W9.0mm_P27.50mm_X2",
              "Faratronic C42P2105KBSC400 32 x 9 x 18 mm, P27.5")
    body = box(-W / 2, W / 2, -T / 2, T / 2, 0, H)
    body = fillet_edges(body, "|Z", 0.6)
    m.add("box", body, "film_grey")
    for num, sx in (("1", -1), ("2", 1)):
        m.pin(num, cyl(sx * P / 2, 0, -3.5, 0.5, d), "tin")
    return m


if __name__ == "__main__":
    run(build())
