"""76 - stage 4 (GF-2.0), READ-ONLY: runs 20_scan.py verbatim with TAG = module global TAG (default 'gf20'):
sliver rule, draft / undercut classification of every face, thin strips < 1.0, unfilleted-root census.
Output %TEMP%\\rev3_glassfront\\scan_<TAG>.json (20's own dump)."""
import os

P20 = os.path.join(r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion",
                   "20_scan.py")
TAG = globals().get("TAG") or "gf20"


def run(_context: str):
    src = open(P20, encoding="utf-8").read().replace('TAG = "final"', 'TAG = "%s"' % TAG)
    ns = {"__name__": "gf_20", "__file__": P20}
    exec(compile(src, P20, "exec"), ns)
    ns["run"](_context)
