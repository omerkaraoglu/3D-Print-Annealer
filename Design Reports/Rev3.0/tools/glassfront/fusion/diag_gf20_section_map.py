"""diag_gf20_section_map - READ-ONLY: ASCII section maps of the frame body by point containment.
Module globals (set by the runner): SECTIONS = [("x", value, (u0, u1, du), (z0, z1, dz)), ("y", value, ...)],
OUTNAME. Plane 'x' = section at abs x (columns = abs y); 'y' = section at abs y (columns = abs x).
'#' inside, '.' outside, '+' on the boundary. Writes %TEMP%\\rev3_glassfront\\gf20\\<OUTNAME>."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

SECTIONS = globals().get("SECTIONS") or [("x", 79.92, (117.0, 151.0, 0.25), (-15.0, 5.0, 0.25))]
OUTNAME = globals().get("OUTNAME") or "section_map.txt"
CH = {adsk.fusion.PointContainment.PointInsidePointContainment: "#",
      adsk.fusion.PointContainment.PointOutsidePointContainment: ".",
      adsk.fusion.PointContainment.PointOnPointContainment: "+"}


def frange(a, b, s):
    n = int(round((b - a) / s))
    return [a + k * s for k in range(n + 1)]


def run(_context: str):
    L.check_doc()
    b = L.body()
    lines = []
    for ax, val, (u0, u1, du), (z0, z1, dz) in SECTIONS:
        us = frange(u0, u1, du)
        zs = frange(z0, z1, dz)
        lines.append("=== section %s = %.3f ; columns %s %.2f..%.2f step %.2f ; rows Z %.2f..%.2f step %.2f (top row = "
                     "max Z)" % (ax, val, "y" if ax == "x" else "x", u0, u1, du, z0, z1, dz))
        for z in reversed(zs):
            row = []
            for u in us:
                if ax == "x":
                    p = adsk.core.Point3D.create(val / 10.0, -u / 10.0, z / 10.0)
                else:
                    p = adsk.core.Point3D.create(u / 10.0, -val / 10.0, z / 10.0)
                row.append(CH.get(b.pointContainment(p), "?"))
            lines.append("%7.2f %s" % (z, "".join(row)))
        lines.append("")
    p = os.path.join(L.SCR, "gf20", OUTNAME)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(p)
