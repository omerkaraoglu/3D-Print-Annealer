"""32 - stage 2, Part A: the full stage-1 flex test (90_flex_test.py verbatim, TAG 'partA' -> flex_partA.json):
glass_t 2.0 / 4.0 / 1.1, t_sheet 0.8 / 1.5, t_opt 1.0, back to the defaults (checked by 90)."""
import os

GF = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion"


def run(_context: str):
    p = os.path.join(GF, "90_flex_test.py")
    ns = {"__name__": "gf_script", "__file__": p}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    ns["TAG"] = "partA"
    ns["run"](_context)
