"""J3 (mains), R1 (heater), J4 (fan) - wire ends soldered into the board.

KiCad 10 ships no 3D models for Connector_Wire:SolderWire-* (the referenced
.step files are missing from the library). These stand-in models show the
stripped conductor in the hole and 12 mm of insulated wire rising from the
board so the space the wires take is visible.
Dimensions from the footprint names: 1.5 mm2 (D 1.7 conductor, OD 3.9, P 7.8),
0.75 mm2 (D 1.25, OD 3.5, P 7.0).  Wire colours brown/blue (IEC L/N).
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *


def stub(name, fp, d, od, p):
    m = Model(name, "Connector_Wire:" + fp, "solder-wire stub %.2f / OD %.1f, P%.1f" % (d, od, p))
    for num, x, col in (("1", 0.0, "copper"), ("2", p, "copper")):
        m.pin(num, cyl(x, 0, -2.0, 1.0, d * 0.95), col)
        m.add("insulation", cyl(x, 0, 1.0, 13.0, od), "wire_red" if num == "1" else "wire_blue")
    return m


def build_all():
    return [stub("SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm_stub", "SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm",
                 1.7, 3.9, 7.8),
            stub("SolderWire-0.75sqmm_1x02_P7mm_D1.25mm_OD3.5mm_stub", "SolderWire-0.75sqmm_1x02_P7mm_D1.25mm_OD3.5mm",
                 1.25, 3.5, 7.0)]


if __name__ == "__main__":
    for m in build_all():
        run(m)
