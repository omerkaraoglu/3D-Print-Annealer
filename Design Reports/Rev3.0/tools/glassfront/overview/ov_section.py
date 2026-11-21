"""Vector section figures from renders/overview/sections.json (planar cuts of the assembly STEP)."""
import math

import numpy as np
from matplotlib.path import Path as MPath
from reportlab.lib.colors import HexColor

import ov_draw as D

COL = {
    "frame": "#3B3F45", "glass": "#CFE2E8", "print": "#0B0B0C", "loca": "#8FD3EA", "formex": "#EFE3B8",
    "bead": "#C23B2C", "tape": "#F0B331", "sheet": "#AEB5BD", "stud": "#C99B6B", "washer": "#D3D6DA",
    "nut": "#B5BAC1", "tail": "#E38E22", "lcm": "#9EA2A8", "pu": "#2A2A2C", "sensor": "#B9D2DE",
    "cover": "#1E2024", "board": "#2E7D4F", "component": "#6E7378",
}


def colour_of(key, sub):
    if key == "glass":
        return COL["print"] if sub == "print" else COL["glass"]
    if key == "panel":
        for k in ("tail", "lcm", "pu", "sensor", "cover"):
            if sub.startswith(k):
                return COL[k]
        return COL["lcm"]
    if key == "pcb":
        return COL["board"] if sub == "board" else COL["component"]
    return COL.get(key, "#888888")


class Section:
    def __init__(self, sec, window=None):
        self.sec = sec
        self.win = window or sec["window"]
        self.polys = sec["polys"]

    def fit(self, x, y, w, h):
        h0, h1, z0, z1 = self.win
        self.s = min(w / (h1 - h0), h / (z1 - z0))
        self.ox = x + (w - (h1 - h0) * self.s) / 2
        self.oy = y + (h - (z1 - z0) * self.s) / 2
        self.box = (self.ox, self.oy, (h1 - h0) * self.s, (z1 - z0) * self.s)
        return self.box

    def P(self, hh, zz):
        return self.ox + (hh - self.win[0]) * self.s, self.oy + (zz - self.win[2]) * self.s

    def draw(self, c, order=None, edge="#1D2125", lw=0.35):
        c.saveState()
        bx, by, bw, bh = self.box
        p = c.beginPath(); p.rect(bx, by, bw, bh)
        c.clipPath(p, stroke=0, fill=0)
        # paint big bodies first, thin ones last so they stay visible
        def area(pl):
            L = np.array(pl["loops"][0])
            return abs(np.sum(L[:, 0] * np.roll(L[:, 1], -1) - np.roll(L[:, 0], -1) * L[:, 1])) / 2
        for pl in sorted(self.polys, key=lambda q: -area(q)):
            col = HexColor(colour_of(pl["key"], pl["sub"]))
            path = c.beginPath()
            for L in pl["loops"]:
                for i, (hh, zz) in enumerate(L):
                    X, Y = self.P(hh, zz)
                    if i == 0:
                        path.moveTo(X, Y)
                    else:
                        path.lineTo(X, Y)
                path.close()
            c.setFillColor(col); c.setStrokeColor(HexColor(edge)); c.setLineWidth(lw)
            c.drawPath(path, stroke=1, fill=1, fillMode=0)  # even-odd: holes stay open
        c.restoreState()

    def target(self, key, near, sub=None, depth_mm=None):
        """an interior point (page coords) of the key's polygons closest to `near` (h, z), at least depth inside"""
        best = None
        h0, h1, z0, z1 = self.win
        for pl in self.polys:
            if pl["key"] != key or (sub and not pl["sub"].startswith(sub)):
                continue
            L = np.array(pl["loops"][0])
            path = MPath(L)
            xs = np.linspace(max(L[:, 0].min(), h0), min(L[:, 0].max(), h1), 120)
            zs = np.linspace(max(L[:, 1].min(), z0), min(L[:, 1].max(), z1), 80)
            G = np.array([(a, b) for a in xs for b in zs])
            if len(G) == 0:
                continue
            ins = path.contains_points(G)
            for H in pl["loops"][1:]:
                ins &= ~MPath(np.array(H)).contains_points(G)
            G = G[ins]
            if len(G) == 0:
                continue
            # depth: distance to the outline (densified vertices)
            V = np.vstack([np.array(l) for l in pl["loops"]])
            dmin = np.sqrt(((G[:, None, :] - V[None, ::max(1, len(V) // 400), :]) ** 2).sum(axis=2)).min(axis=1)
            need = depth_mm if depth_mm is not None else min(0.25, 0.4 * dmin.max())
            ok = dmin >= need * 0.999
            if not ok.any():
                ok = dmin >= dmin.max() * 0.8
            G2 = G[ok]
            d = ((G2 - np.array(near)) ** 2).sum(axis=1)
            i = int(np.argmin(d))
            if best is None or d[i] < best[0]:
                best = (d[i], tuple(G2[i]))
        if best is None:
            raise KeyError("no polygon for %s/%s" % (key, sub))
        return self.P(*best[1])


def poly_hits_segment(sec, seg, key, sub=None, skip_end=2.0):
    """True if the leader segment (page coords) runs through a polygon of key/sub, ignoring the last skip_end pt
    (the dot end, which may sit on the part it names)"""
    import numpy as np
    x1, y1, x2, y2 = seg
    L = max(1e-6, ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
    n = max(2, int(L / 0.5))
    ts = np.linspace(0, 1 - skip_end / L, n) if L > skip_end else np.array([0.0])
    pts = np.column_stack([x1 + (x2 - x1) * ts, y1 + (y2 - y1) * ts])
    # page -> model
    H = (pts[:, 0] - sec.ox) / sec.s + sec.win[0]
    Z = (pts[:, 1] - sec.oy) / sec.s + sec.win[2]
    M = np.column_stack([H, Z])
    for pl in sec.polys:
        if pl["key"] != key or (sub and not pl["sub"].startswith(sub)):
            continue
        ins = MPath(np.array(pl["loops"][0])).contains_points(M)
        if ins.any():
            return True
    return False


def label_column(c, pen, items, side, x_or_y, span, size=D.BODY, gap=None):
    """items: [(target(x, y), [lines], src)]; side 'left'/'right': labels stacked at x = x_or_y between span
    (y_lo, y_hi), sorted by target y; side 'top'/'bottom': labels in a row at y = x_or_y, sorted by target x"""
    if not items:
        return
    if side in ("left", "right"):
        items = sorted(items, key=lambda t: -t[0][1])
        y_hi, y_lo = span[1], span[0]
        hs = [len(t[1]) * size * 1.25 for t in items]
        free = (y_hi - y_lo) - sum(hs)
        g = free / max(1, len(items) - 1) if len(items) > 1 else 0
        g = min(g, gap) if gap else g
        total = sum(hs) + g * (len(items) - 1)
        y = (y_hi + y_lo) / 2 + total / 2
        for (tgt, lines, src), hh in zip(items, hs):
            ly = y - size
            D.leader_label(c, pen, tgt[0], tgt[1], x_or_y, ly, lines, src, "r" if side == "left" else "l", size)
            y -= hh + g
    else:
        items = sorted(items, key=lambda t: t[0][0])
        x_lo, x_hi = span
        ws = [max(D.sw(l, "R", size) for l in t[1]) for t in items]
        free = (x_hi - x_lo) - sum(ws)
        g = free / max(1, len(items) - 1) if len(items) > 1 else 0
        x = x_lo if len(items) > 1 else (x_lo + x_hi - ws[0]) / 2
        for (tgt, lines, src), ww in zip(items, ws):
            nl = len(lines)
            ly = x_or_y + (nl - 1) * size * 1.25 if side == "top" else x_or_y
            # leader starts at the label's centre-bottom (top row) or centre-top (bottom row)
            cx = x + ww / 2
            c.setStrokeColor(D.INK); c.setLineWidth(0.6)
            if side == "top":
                seg = (cx, x_or_y - size * 0.45, tgt[0], tgt[1])
            else:
                seg = (cx, ly + size * 1.1, tgt[0], tgt[1])
            c.line(*seg)
            D.LEADERS.append(seg)
            c.setFillColor(D.INK); c.circle(tgt[0], tgt[1], 1.2, stroke=0, fill=1)
            yy = ly
            for l in lines:
                pen.text(cx, yy, l, src, "R", size, D.INK, "c")
                yy -= size * 1.25
            x += ww + g
