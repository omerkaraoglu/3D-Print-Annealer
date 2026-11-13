"""L1 - Core Master LFU09V-103 common-mode choke (10 mH, UU9.8 core, vertical).

Sources: Core Master spec for LFU09V-103 (DWG TD1241102, UU9.8 core + 2+2 pin
bobbin, ~150 turns 0.2 mm - quoted via web search, the PDF on the Ozdisan CDN
could not be downloaded); pin grid 7.0 x 8.0 mm from the footprint (UU9.8
standard).  The envelope is ESTIMATED from the UU9.8 vertical family:
Delta LFU09V outline 16.5 / 11.0 / 16.0 max, Coilmaster UU9.8LF 17 x 12 x 17,
footprint silk 13.5 x 17.  Model envelope 12.0 x 16.5 x 17.0 (conservative
height), pins 0.6 mm (Coilmaster E 0.6), 3.5 mm below the board.
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

W, L, H = 12.0, 16.5, 17.0       # x, y, z
PIN_D = 0.6
BASE = 3.0
CORE_T = 2.6                     # ferrite bar thickness (z) and width


def build():
    m = Model("LFU09V-103", "Rev3:LFU09V-103", "Core Master LFU09V-103 UU9.8 vertical CMC (envelope estimated)")
    m.add("base", box(-W / 2, W / 2, -L / 2, L / 2, 0.3, 0.3 + BASE), "black")
    zc0, zc1 = 0.3 + BASE, H - CORE_T
    for sy in (-1, 1):
        m.add("coil", cyl(0, sy * 4.0, zc0, zc1, 7.8), "copper")
        m.add("leg", box(-1.6, 1.6, sy * 4.0 - 1.6, sy * 4.0 + 1.6, zc1 - 0.2, H), "ferrite")
    m.add("core_top", box(-2.4, 2.4, -L / 2 + 0.6, L / 2 - 0.6, zc1, H), "ferrite")
    # pins: footprint pads 1 (-3.5,+4), 2 (+3.5,+4), 3 (+3.5,-4), 4 (-3.5,-4)  (KiCad y-down)
    for num, (x, y) in {"1": (-3.5, 4), "2": (3.5, 4), "3": (3.5, -4), "4": (-3.5, -4)}.items():
        m.pin(num, cyl(x, -y, -3.5, 0.6, PIN_D), "tin")
    return m


if __name__ == "__main__":
    run(build())
