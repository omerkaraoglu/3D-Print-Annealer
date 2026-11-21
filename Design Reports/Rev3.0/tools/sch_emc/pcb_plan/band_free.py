import sys, json, numpy as np
G = json.load(open("geo.json"))
poly = [(45.5,20.5),(45.5,55.5),(72,55.5),(72,58.8),(78,59.81),(78,76),(116,76),(116,74.8),(146,74.8),(150,75.5),(150,60),(183.5,60),(183.5,20.5)]
R = 0.25
xs = np.arange(45.5, 183.5, R); ys = np.arange(20.5, 76, R)
X, Y = np.meshgrid(xs + R/2, ys + R/2)
from matplotlib.path import Path
inband = Path(poly).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
occ = np.zeros_like(inband)
def mark_box(x0, y0, x1, y1, m):
    occ[(X >= x0 - m) & (X <= x1 + m) & (Y >= y0 - m) & (Y <= y1 + m)] = True
fps = {}
for r, (x0, y0, x1, y1) in G["fps"].items():
    if r.startswith("DS") or r.startswith("H"):
        if r == "HS1": mark_box(x0, y0, x1, y1, 1.0)
        continue
    mark_box(x0, y0, x1, y1, 1.0)
    fps[r] = (x0, y0, x1, y1)
for t in G["tracks"]:
    if True:
        sx, sy, ex, ey, w = t[:5]
        if not (min(sy, ey) < 77 and max(sx, ex) > 45): continue
        n = int(max(abs(ex - sx), abs(ey - sy)) / R) + 2
        for k in range(n + 1):
            px = sx + (ex - sx) * k / n; py = sy + (ey - sy) * k / n
            m = w / 2 + 2.5
            occ[(abs(X - px) <= m) & (abs(Y - py) <= m)] = True
# board edge 1 mm
occ[Y < 20.0 + 1.0] = True
free = inband & ~occ
print("band area %.0f mm2, free (>=1 mm from courtyards, >=2.5 mm from tracks, >=1 mm from the top edge) %.0f mm2" % (inband.sum() * R * R, free.sum() * R * R))
# largest free rectangle (histogram method)
H = np.zeros(free.shape[1], int); best = (0, None)
for i in range(free.shape[0]):
    H = np.where(free[i], H + 1, 0)
    st = []
    for j in range(len(H) + 1):
        h = H[j] if j < len(H) else 0
        s0 = j
        while st and st[-1][1] >= h:
            s0, hh = st.pop(); a = hh * (j - s0)
            if a > best[0]: best = (a, (xs[s0], ys[i - hh + 1], xs[j - 1] + R, ys[i] + R))
        st.append((s0, h))
print("largest free rectangle %.0f mm2: x %.1f-%.1f, y %.1f-%.1f" % (best[0] * R * R, best[1][0], best[1][2], best[1][1], best[1][3]))
np.save("band_free.npy", free)
json.dump(dict(xs0=45.5, ys0=20.5, R=R), open("band_free.json", "w"))
# connected free regions >= 50 mm2
from scipy import ndimage
lab, nlab = ndimage.label(free)
sizes = ndimage.sum(free, lab, range(1, nlab + 1)) * R * R
for k in np.argsort(-sizes)[:8]:
    m = lab == k + 1; yy, xx = np.where(m)
    print("free region %.0f mm2 bbox x %.1f-%.1f y %.1f-%.1f" % (sizes[k], xs[xx.min()], xs[xx.max()] + R, ys[yy.min()], ys[yy.max()] + R))
