"""Tiny drafting library on matplotlib: an A3 (or any) sheet in paper millimetres, views at a true scale,
ISO-style linear / radius dimensions, leaders, tables, note blocks, a title block, and a layout checker
(text-text overlaps, text outside the frame, text crossing registered geometry).

Paper coordinates: x right, y up, mm, origin at the lower-left sheet corner. A View maps model (u, v) mm to paper.
"""
import math
import textwrap

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["hatch.linewidth"] = 0.4
matplotlib.rcParams["path.simplify"] = False

MM_PER_PT = 25.4 / 72.0
THICK, THIN, XTHIN = 0.5, 0.25, 0.18          # line widths, mm (ISO 128: 0.5 / 0.25)
ARROW_L, ARROW_W = 2.2, 0.75                   # arrowhead length / full width, mm


def lw(mm):
    return mm / MM_PER_PT


def char_w(fs):
    """average DejaVu Sans character width, mm"""
    return 0.585 * fs * MM_PER_PT


ALL_SHEETS = []              # every Sheet made in this process (make_all indexes them and scans their texts)


class Sheet:
    def __init__(self, W=420.0, H=297.0, margin=10.0):
        ALL_SHEETS.append(self)
        self.dwg, self.title, self.rev = None, None, None
        self.W, self.H, self.m = W, H, margin
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(0, H)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self.texts = []          # [(artist, allow_geom)]
        self.segs = []           # [np.array (k, 4)]
        self.issues = []

    # ------------------------------------------------------------------ primitives (paper mm)
    def T(self, x, y, s, fs=7.0, ha="left", va="baseline", rot=0.0, color="k", weight="normal", family=None,
          check=True, allow_geom=False, z=6, style="normal", bg=None):
        kw = dict(fontsize=fs, ha=ha, va=va, rotation=rot, color=color, fontweight=weight, zorder=z, fontstyle=style)
        if family:
            kw["family"] = family
        if bg:
            kw["bbox"] = dict(boxstyle="square,pad=0.15", fc=bg, ec="none")
        t = self.ax.text(x, y, s, **kw)
        if check:
            self.texts.append((t, allow_geom))
        return t

    def L(self, xs, ys, w=THIN, c="k", ls="-", geom=True, z=3, dashes=None):
        kw = dict(lw=lw(w), color=c, ls=ls, zorder=z, solid_capstyle="butt")
        if dashes:
            kw["dashes"] = dashes
        self.ax.plot(xs, ys, **kw)
        if geom and len(xs) > 1:
            a = np.column_stack([xs[:-1], ys[:-1], xs[1:], ys[1:]]).astype(float)
            self.segs.append(a)

    def poly(self, pts, closed=True, fc="none", ec="k", w=THIN, hatch=None, z=2, geom=True, ls="-", alpha=1.0):
        pts = np.asarray(pts, float)
        p = Polygon(pts, closed=closed, fc=fc, ec=ec, lw=lw(w), hatch=hatch, zorder=z, ls=ls, alpha=alpha)
        self.ax.add_patch(p)
        if geom and ec != "none":
            q = np.vstack([pts, pts[:1]]) if closed else pts
            self.segs.append(np.column_stack([q[:-1, 0], q[:-1, 1], q[1:, 0], q[1:, 1]]))
        return p

    def circle(self, x, y, r, fc="none", ec="k", w=THIN, z=3, geom=True, ls="-"):
        self.ax.add_patch(Circle((x, y), r, fc=fc, ec=ec, lw=lw(w), zorder=z, ls=ls))
        if geom and ec != "none":
            a = np.linspace(0, 2 * np.pi, 49)
            q = np.column_stack([x + r * np.cos(a), y + r * np.sin(a)])
            self.segs.append(np.column_stack([q[:-1, 0], q[:-1, 1], q[1:, 0], q[1:, 1]]))

    def arrow(self, x, y, ang, c="k", L=ARROW_L, W=ARROW_W):
        """filled arrowhead with its tip at (x, y), pointing in direction ang (rad)"""
        ux, uy = math.cos(ang), math.sin(ang)
        bx, by = x - L * ux, y - L * uy
        nx, ny = -uy * W / 2, ux * W / 2
        self.ax.add_patch(Polygon([(x, y), (bx + nx, by + ny), (bx - nx, by - ny)], closed=True, fc=c, ec=c,
                                  lw=0.2, zorder=5))

    # ------------------------------------------------------------------ dimensions (paper mm)
    def dim_h(self, xa, ya, xb, yb, yd, text, fs=7.0, c="k", text_at=None, ha="center", arrows="in", ext=True,
              gap=0.8, over=1.5):
        """horizontal dimension between feature points (xa, ya) and (xb, yb); dimension line at y = yd"""
        if xa > xb:
            xa, ya, xb, yb = xb, yb, xa, ya
        if ext:
            for x, y in ((xa, ya), (xb, yb)):
                s = 1 if yd > y else -1
                if abs(yd - y) > gap:
                    self.L([x, x], [y + s * gap, yd + s * over], w=XTHIN, c=c)
        if arrows == "in":
            self.L([xa, xb], [yd, yd], w=XTHIN, c=c)
            self.arrow(xa, yd, math.pi, c)
            self.arrow(xb, yd, 0.0, c)
        else:
            self.L([xa - 5, xb + 5], [yd, yd], w=XTHIN, c=c)
            self.arrow(xa, yd, 0.0, c)
            self.arrow(xb, yd, math.pi, c)
        if text is not None:
            if text_at is None:
                self.T((xa + xb) / 2, yd + 0.6, text, fs=fs, ha="center", va="bottom", color=c)
            else:
                self.T(text_at[0], text_at[1], text, fs=fs, ha=ha, va="bottom", color=c)

    def dim_v(self, xa, ya, xb, yb, xd, text, fs=7.0, c="k", text_at=None, arrows="in", ext=True, gap=0.8,
              over=1.5, side="left"):
        """vertical dimension between (xa, ya) and (xb, yb); dimension line at x = xd; text rotated 90 deg"""
        if ya > yb:
            xa, ya, xb, yb = xb, yb, xa, ya
        if ext:
            for x, y in ((xa, ya), (xb, yb)):
                s = 1 if xd > x else -1
                if abs(xd - x) > gap:
                    self.L([x + s * gap, xd + s * over], [y, y], w=XTHIN, c=c)
        if arrows == "in":
            self.L([xd, xd], [ya, yb], w=XTHIN, c=c)
            self.arrow(xd, ya, -math.pi / 2, c)
            self.arrow(xd, yb, math.pi / 2, c)
        else:
            self.L([xd, xd], [ya - 5, yb + 5], w=XTHIN, c=c)
            self.arrow(xd, ya, math.pi / 2, c)
            self.arrow(xd, yb, -math.pi / 2, c)
        if text is not None:
            if text_at is None:
                if side == "left":
                    self.T(xd - 0.6, (ya + yb) / 2, text, fs=fs, ha="right", va="center", rot=90, color=c)
                else:
                    self.T(xd + 0.6, (ya + yb) / 2, text, fs=fs, ha="left", va="center", rot=90, color=c)
            else:
                self.T(text_at[0], text_at[1], text, fs=fs, ha="left", va="center", color=c)

    def leader(self, px, py, tx, ty, text, fs=7.0, c="k", ha="left", va="center", head="arrow", shoulder=2.0,
               allow_geom=False, color_text=None, weight="normal"):
        """leader from the text anchor (tx, ty) to the point (px, py)"""
        sgn = 1 if ha == "left" else -1
        sx = tx - sgn * shoulder
        self.L([px, sx, tx - sgn * 0.3], [py, ty, ty], w=XTHIN, c=c)
        if head == "arrow":
            self.arrow(px, py, math.atan2(py - ty, px - sx), c)
        elif head == "dot":
            self.ax.add_patch(Circle((px, py), 0.45, fc=c, ec="none", zorder=5))
        if text:
            self.T(tx, ty, text, fs=fs, ha=ha, va=va, color=color_text or c, allow_geom=allow_geom, weight=weight)

    def radius(self, cx, cy, r, ang_deg, text, L=8.0, fs=7.0, c="k", shoulder=3.0, inside=False):
        """radius leader with the arrow on the arc; inside=True runs the leader towards the centre side"""
        a = math.radians(ang_deg)
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        d = -1.0 if inside else 1.0
        ex, ey = px + d * L * math.cos(a), py + d * L * math.sin(a)
        sgn = 1 if d * math.cos(a) >= 0 else -1
        self.L([px, ex, ex + sgn * shoulder], [py, ey, ey], w=XTHIN, c=c)
        self.arrow(px, py, a + (math.pi if not inside else 0.0), c)
        self.T(ex + sgn * (shoulder + 0.5), ey, text, fs=fs, ha="left" if sgn > 0 else "right", va="center", color=c)

    # ------------------------------------------------------------------ blocks
    def wrap(self, s, width_mm, fs):
        n = max(int(width_mm / char_w(fs)), 10)
        return textwrap.wrap(s, n, break_long_words=False, break_on_hyphens=False) or [""]

    def notes(self, x, y, width, items, fs=6.5, lh=None, head=None, head_fs=None, numbered=True, gap=0.6,
              color="k", indent=None):
        """numbered note list starting at the top-left (x, y); returns the y below the last line"""
        lh = lh or fs * MM_PER_PT * 1.28
        if indent is None:
            indent = 3.6 if len(items) < 10 else 4.9
        if head:
            self.T(x, y - (head_fs or fs + 1) * MM_PER_PT, head, fs=head_fs or fs + 1, weight="bold", color=color)
            y -= (head_fs or fs + 1) * MM_PER_PT * 1.5
        for i, it in enumerate(items):
            lab = ("%d." % (i + 1)) if numbered else "-"
            lines = self.wrap(it, width - indent, fs)
            for k, ln in enumerate(lines):
                y -= lh
                if k == 0:
                    self.T(x, y, lab, fs=fs, color=color)
                self.T(x + indent, y, ln, fs=fs, color=color)
            y -= gap
        return y

    def table(self, x, y, cols, rows, fs=6.5, lh=None, head_bold=True, rule=True, color="k", widths=None):
        """simple table; cols = list of column x offsets (mm); rows[0] = header; returns y below"""
        lh = lh or fs * MM_PER_PT * 1.45
        x_end = x + (widths if widths else cols[-1] + 30)
        for i, row in enumerate(rows):
            y -= lh
            for cx, cell in zip(cols, row):
                self.T(x + cx, y + 0.25 * lh * 0.5, str(cell), fs=fs, weight="bold" if (i == 0 and head_bold) else
                       "normal", color=color)
            if rule and (i == 0 or i == len(rows) - 1):
                yr = y - (0.2 if i == 0 else 0.35) * lh
                self.L([x, x_end], [yr, yr], w=XTHIN, c=color, geom=False)
        return y - 0.4 * lh

    def table_wrapped(self, x, y, widths, rows, fs=6.2, head_fs=None, color="k", bold_rows=(), pad=1.2):
        """table with word-wrapped cells; widths = column widths (mm); rows[0] = header; rules between rows"""
        lh = fs * MM_PER_PT * 1.3
        xs = [x]
        for w in widths:
            xs.append(xs[-1] + w)
        self.L([xs[0], xs[-1]], [y, y], w=THIN, c=color, geom=False)
        for i, row in enumerate(rows):
            f = (head_fs or fs) if i == 0 else fs
            cells = [self.wrap(str(c), w - pad, f) for c, w in zip(row, widths)]
            nl = max(len(c) for c in cells)
            for k in range(nl):
                yy = y - (k + 1) * lh
                for j, c in enumerate(cells):
                    if k < len(c):
                        self.T(xs[j] + pad / 2, yy + 0.15 * lh, c[k], fs=f, color=color,
                               weight="bold" if (i == 0 or i in bold_rows) else "normal")
            y -= nl * lh + 0.8
            self.L([xs[0], xs[-1]], [y + 0.35, y + 0.35], w=THIN if i == 0 or i == len(rows) - 1 else XTHIN,
                   c=color, geom=False)
        return y

    def frame(self, zones=True):
        m = self.m
        self.L([m, self.W - m, self.W - m, m, m], [m, m, self.H - m, self.H - m, m], w=THICK, geom=False)
        self.L([0.5, self.W - 0.5, self.W - 0.5, 0.5, 0.5], [0.5, 0.5, self.H - 0.5, self.H - 0.5, 0.5],
               w=XTHIN, c="0.6", geom=False)
        if zones:   # centring marks
            for x, y, dx, dy in ((self.W / 2, m, 0, -m + 1), (self.W / 2, self.H - m, 0, m - 1),
                                 (m, self.H / 2, -m + 1, 0), (self.W - m, self.H / 2, m - 1, 0)):
                self.L([x, x + dx], [y, y + dy], w=THICK, geom=False)

    def title_block(self, fields, w=180.0, h=36.0):
        """ISO 7200-like title block at the lower-right corner; fields: dict"""
        self.dwg, self.title, self.rev = fields.get("dwg"), fields.get("title"), fields.get("rev")
        x1, y0 = self.W - self.m, self.m
        x0, y1 = x1 - w, y0 + h
        self.L([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], w=THICK, geom=False)
        r2, r3 = y0 + 15.0, y0 + 7.5
        for yy in (r2, r3):
            self.L([x0, x1], [yy, yy], w=XTHIN, geom=False)
        cA, cB, cC = x0 + w * 0.36, x0 + w * 0.60, x0 + w * 0.80
        self.L([cA, cA], [y0, r2], w=XTHIN, geom=False)
        self.L([cB, cB], [y0, r2], w=XTHIN, geom=False)
        self.L([cC, cC], [y0, r2], w=XTHIN, geom=False)

        def cell(xx, yy, lab, val, fsv=7.0, bold=False):
            self.T(xx + 1.0, yy + 4.6, lab, fs=4.8, color="0.35")
            self.T(xx + 1.0, yy + 1.2, val, fs=fsv, weight="bold" if bold else "normal")

        self.T(x0 + 2, y1 - 5.0, fields.get("title", ""), fs=9.5, weight="bold", va="baseline")
        yy = y1 - 9.6
        for key, fs, col in (("subtitle", 6.6, "k"), ("source", 5.6, "0.25"), ("project", 5.8, "k")):
            lines = self.wrap(fields.get(key, ""), w - 4, fs)
            assert len(lines) <= 2, ("title-block %s longer than two lines" % key, fields.get(key))
            for ln in lines:
                self.T(x0 + 2, yy, ln, fs=fs, color=col)
                yy -= fs * MM_PER_PT * 1.3
        if fields.get("change"):
            ych = r2 + 1.6
            chl = self.wrap(fields["change"], w - 4, 5.6)
            assert len(chl) <= 2, ("change note longer than two lines", fields["change"])
            for ln in reversed(chl):
                self.T(x0 + 2, ych, ln, fs=5.6, color="#8a1c1c")
                ych += 5.6 * MM_PER_PT * 1.3
        cell(x0, r3, "drawing no.", fields.get("dwg", ""), bold=True)
        cell(cA, r3, "revision", fields.get("rev", ""), bold=True)
        cell(cB, r3, "scale", fields.get("scale", ""))
        cell(cC, r3, "sheet / units", fields.get("size", "A3  mm"))
        cell(x0, y0, "date", fields.get("date", ""))
        cell(cA, y0, "drawn (script)", fields.get("drawn", ""), fsv=5.4)
        cell(cB, y0, "checked", fields.get("checked", "________"))
        cell(cC, y0, "approved", fields.get("approved", "________"))
        return (x0, y0, x1, y1)

    # ------------------------------------------------------------------ checks + output
    def check_layout(self, ignore_pairs=()):
        """text boxes in paper mm; reports overlaps, out-of-frame text, text crossing geometry"""
        self.fig.canvas.draw()
        r = self.fig.canvas.get_renderer()
        inv = self.ax.transData.inverted()
        boxes = []
        for t, ag in self.texts:
            if not t.get_text().strip():
                continue
            bb = t.get_window_extent(r)
            (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
            boxes.append((x0, y0, x1, y1, t.get_text().replace("\n", " ")[:48], ag))
        issues = []
        pad = 0.12
        for i in range(len(boxes)):
            a = boxes[i]
            if a[0] < self.m - 0.01 or a[2] > self.W - self.m + 0.01 or a[1] < self.m - 0.01 or a[3] > self.H - self.m + 0.01:
                issues.append("text outside the frame: %r" % a[4])
            for j in range(i + 1, len(boxes)):
                b = boxes[j]
                if (min(a[2], b[2]) - max(a[0], b[0]) > pad) and (min(a[3], b[3]) - max(a[1], b[1]) > pad):
                    if (a[4], b[4]) in ignore_pairs or (b[4], a[4]) in ignore_pairs:
                        continue
                    issues.append("text overlap: %r / %r" % (a[4], b[4]))
        segs = np.vstack(self.segs) if self.segs else np.zeros((0, 4))
        for b in boxes:
            if b[5]:
                continue
            x0, y0, x1, y1 = b[0] + 0.25, b[1] + 0.25, b[2] - 0.25, b[3] - 0.25
            if x1 <= x0 or y1 <= y0 or len(segs) == 0:
                continue
            if _segs_hit_box(segs, x0, y0, x1, y1):
                issues.append("text crosses geometry: %r" % b[4])
        self.issues = issues
        self.boxes = boxes
        return issues

    def all_text(self):
        """every string drawn on the sheet (also the unchecked ones), in drawing order"""
        return [t.get_text() for t in self.ax.texts if t.get_text().strip()]

    def save(self, pdf=None, png=None, dpi=200, pdf_image_dpi=300):
        if pdf:
            self.fig.savefig(pdf, dpi=pdf_image_dpi)     # dpi only affects embedded raster images
        if png:
            self.fig.savefig(png, dpi=dpi)
        plt.close(self.fig)


def clip_poly(pts, x0, x1, y0, y1):
    """Sutherland-Hodgman clip of a closed polygon (any shape) by the axis-aligned box x0..x1, y0..y1 (the box is
    convex, so the result is exact; a concave subject may keep zero-width edges on the box boundary)"""
    def clip(P, inside, inter):
        out = []
        for i in range(len(P)):
            a, b = P[i - 1], P[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(inter(a, b))
                out.append(b)
            elif ia:
                out.append(inter(a, b))
        return out
    ix = lambda x: (lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])))
    iy = lambda y: (lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y))
    P = [tuple(p) for p in pts]
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)),
                          (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        if not P:
            break
        P = clip(P, inside, inter)
    return P


def _segs_hit_box(segs, x0, y0, x1, y1):
    """True if any segment intersects the axis-aligned box (Liang-Barsky, vectorised)"""
    px, py = segs[:, 0], segs[:, 1]
    dx, dy = segs[:, 2] - px, segs[:, 3] - py
    t0 = np.zeros(len(segs))
    t1 = np.ones(len(segs))
    ok = np.ones(len(segs), bool)
    for p, q in ((-dx, px - x0), (dx, x1 - px), (-dy, py - y0), (dy, y1 - py)):
        par = np.abs(p) < 1e-12
        ok &= ~(par & (q < 0))
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.where(par, 0.0, q / np.where(par, 1.0, p))
        neg = (~par) & (p < 0)
        pos = (~par) & (p > 0)
        t0 = np.where(neg, np.maximum(t0, r), t0)
        t1 = np.where(pos, np.minimum(t1, r), t1)
    return bool(np.any(ok & (t0 <= t1)))


class View:
    """model (u, v) mm -> paper mm: x = ox + s * (+-u), y = oy + s * v"""

    def __init__(self, sh: Sheet, ox, oy, scale, mirror=False):
        self.sh, self.ox, self.oy, self.s, self.mx = sh, ox, oy, scale, (-1.0 if mirror else 1.0)

    def P(self, u, v):
        return (self.ox + self.s * self.mx * u, self.oy + self.s * v)

    def Pa(self, pts):
        a = np.asarray(pts, float)
        return np.column_stack([self.ox + self.s * self.mx * a[:, 0], self.oy + self.s * a[:, 1]])

    def line(self, pts, **kw):
        q = self.Pa(pts)
        self.sh.L(q[:, 0], q[:, 1], **kw)

    def poly(self, pts, **kw):
        return self.sh.poly(self.Pa(pts), **kw)

    def rrect(self, r, **kw):
        return self.sh.poly(self.Pa(r.boundary(n_arc=24, step=2.0)), **kw)

    def circle(self, u, v, rad, **kw):
        x, y = self.P(u, v)
        self.sh.circle(x, y, rad * self.s, **kw)

    def cross(self, u, v, a_paper=2.0, w=XTHIN, c="k", geom=False):
        x, y = self.P(u, v)
        self.sh.L([x - a_paper, x + a_paper], [y, y], w=w, c=c, geom=geom)
        self.sh.L([x, x], [y - a_paper, y + a_paper], w=w, c=c, geom=geom)

    def centreline(self, p0, p1, c="k", w=XTHIN):
        q = self.Pa([p0, p1])
        self.sh.L(q[:, 0], q[:, 1], w=w, c=c, geom=False, dashes=(12, 2.5, 2, 2.5))
