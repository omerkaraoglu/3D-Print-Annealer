"""Shared helpers for the smoothing round (KiCad python). Local mm = absolute mm - 20."""
import pcbnew, math
O = 20.0
mm = pcbnew.ToMM
def V(x, y):  # local mm -> VECTOR2I absolute
    return pcbnew.VECTOR2I(pcbnew.FromMM(x + O), pcbnew.FromMM(y + O))
def L(v):  # VECTOR2I -> local (x, y) mm
    return (mm(v.x) - O, mm(v.y) - O)
def close(a, b, tol=0.005):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol
def find_tracks(b, net, p, q=None, layer=None):
    out = []
    for t in list(b.Tracks()):
        if t.GetClass() != 'PCB_TRACK' or t.GetNetname() != net: continue
        if layer is not None and t.GetLayer() != layer: continue
        s, e = L(t.GetStart()), L(t.GetEnd())
        if q is None:
            if close(s, p) or close(e, p): out.append(t)
        elif (close(s, p) and close(e, q)) or (close(s, q) and close(e, p)):
            out.append(t)
    return out
def add_track(b, net, layer, pts, w):
    ni = b.FindNet(net)
    made = []
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetStart(V(*a)); t.SetEnd(V(*c)); t.SetWidth(pcbnew.FromMM(w)); t.SetLayer(layer); t.SetNet(ni)
        b.Add(t); made.append(t)
    return made
def connectivity_signature(b):
    """net -> sorted list of pad ids, plus per-net island count via connectivity."""
    b.BuildConnectivity()
    sig = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            sig.setdefault(p.GetNetname(), []).append("%s.%s" % (fp.GetReference(), p.GetNumber()))
    return {k: sorted(v) for k, v in sig.items()}
