import importlib, sys
import adsk.core, adsk.fusion
sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

# 04b - rename the sketches/features of 04 (the 04 run raised in show_iso AFTER its features were built;
# Fusion kept them). Sketches get a ' sketch' suffix, features the plain name.
def run(_context: str):
    L.check_doc()
    r = L.root()
    for nm in ('Tail wall block', 'Corner cells', 'Body outline', 'Flange outline'):
        sk = r.sketches.itemByName(nm)
        if sk is not None:
            sk.name = nm + ' sketch'
    tl = L.des().timeline
    for i in range(tl.count):
        it = tl.item(i)
        if it.name in ('Tail wall block (1)', 'Corner cells (1)'):
            it.entity.name = it.name.replace(' (1)', '')
    n, bad = L.timeline_health()
    L.log('04b renamed; timeline %d, unhealthy %s; %s' % (n, bad, L.body_stats()))
    print(n, bad, L.body_stats(), [tl.item(i).name for i in range(tl.count)])
