"""In1 anti-pad web rule helpers for route_display.py (display region, pass 2b).
Rule (EMI rule 2 / IPC-2221C 9.1.4.1): every non-GND via keeps its pad on In1 and the GND plane keeps 0.25 mm around it;
the plane web between two anti-pads must stay >= 0.25 mm.  => centre pitch >= r1 + r2 + 0.25 with r = d/2 + 0.25 (non-GND)
or d/2 (GND).  0.6 vias: 1.35 non-GND/non-GND, 1.10 GND/non-GND.  Local board mm."""
import math, json, os
from handroute import SCR, OX, OY
WEB = 0.25
def rad(net, d): return d / 2 + (0.25 if net != "GND" else 0.0)

class Web:
    """web check of a candidate via against the vias already drawn by R plus the other regions' vias"""
    def __init__(self, R, extra=(), margin=0.01):
        self.R = R; self.margin = margin; self.others = []
        for fn in extra:
            fp = os.path.join(SCR, fn)
            if os.path.exists(fp):
                self.others += [(t["x"] - OX, t["y"] - OY, t["net"], t["d"]) for t in json.load(open(fp)) if t["via"]]
    def vias(self):
        return self.others + [(t["x"] - OX, t["y"] - OY, t["net"], t["d"]) for t in self.R.items if t["via"]]
    def ok(self, net, x, y, d=0.6, ignore=None):
        for vx, vy, n, vd in self.vias():
            if net == "GND" and n == "GND": continue
            if ignore and ignore(vx, vy, n): continue
            if math.hypot(vx - x, vy - y) < rad(net, d) + rad(n, vd) + WEB + self.margin - 1e-9: return False
        return True

def gap(k1, k2):
    """minimum lane-to-lane distance (along a U10 side) between lane kinds: 'v+3V3' / 'vGND' (row-A vias), 's' (1V2 stub
    passing the via row), 'b' (B.Cu lane passing the via row)"""
    if k1[0] == "v" and k2[0] == "v":
        n1, n2 = k1[1:], k2[1:]
        if n1 == "GND" and n2 == "GND": return 0.8
        if n1 == "GND" or n2 == "GND": return 1.11
        return 1.36
    if k1[0] == "v" or k2[0] == "v": return 0.6 if "B" in (k1 + k2) else 0.56
    return 0.4

def solve_lanes(targets, kinds, lo, hi, slo=None, shi=None):
    """LP: lane positions t (ordered as given) minimising sum |t - target| subject to the pairwise lane gaps, vias in
    [lo, hi], stubs in [slo, shi].  Returns list or None."""
    from scipy.optimize import linprog
    n = len(targets); import numpy as np
    # variables: t_0..t_{n-1}, u_0..u_{n-1} (|t - target| <= u)
    c = np.r_[np.zeros(n), np.ones(n)]
    A, b = [], []
    for i in range(n):
        for j in range(i + 1, n):
            g = gap(kinds[i], kinds[j])
            if j > i + 1:            # only needed when the chained adjacent gaps do not already imply it
                if sum(gap(kinds[k], kinds[k + 1]) for k in range(i, j)) >= g - 1e-9: continue
            row = np.zeros(2 * n); row[i] = 1; row[j] = -1; A.append(row); b.append(-g)
        row = np.zeros(2 * n); row[i] = 1; row[n + i] = -1; A.append(row); b.append(targets[i])
        row = np.zeros(2 * n); row[i] = -1; row[n + i] = -1; A.append(row); b.append(-targets[i])
    bounds = []
    for i in range(n):
        if kinds[i][0] == "v": bounds.append((lo, hi))
        else: bounds.append((slo if slo is not None else lo, shi if shi is not None else hi))
    bounds += [(0, None)] * n
    r = linprog(c, A_ub=np.array(A), b_ub=np.array(b), bounds=bounds, method="highs")
    if not r.success: return None
    return [round(v, 3) for v in r.x[:n]]
