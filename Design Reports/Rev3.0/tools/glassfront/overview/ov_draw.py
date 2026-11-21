"""Drawing helpers for the GF-2.1 overview (reportlab canvas): fonts, colours, text, images, labels."""
import io
import json
import math
import os

import numpy as np
from PIL import Image
from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ------------------------------------------------------------------------------------------------ style
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
FONTS = {"R": "segoeui.ttf", "SB": "seguisb.ttf", "B": "segoeuib.ttf", "L": "segoeuil.ttf", "I": "segoeuii.ttf"}
FN = {}
for k, f in FONTS.items():
    name = "SegoeUI-" + k
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, f)))
    FN[k] = name

ACCENT = HexColor("#00707A")       # the one accent colour
ACCENT_L = HexColor("#E3F1F2")     # its light tint (backgrounds only)
INK = HexColor("#1D2125")
GREY = HexColor("#5A6168")
GREY_L = HexColor("#9AA1A8")
RULE = HexColor("#D5DADF")
PANEL = HexColor("#F4F6F7")

MM = 72.0 / 25.4
PW, PH = 297 * MM, 210 * MM
ML, MR = 15 * MM, 15 * MM
TOP = PH - 12 * MM
BOT = 11 * MM
CW = PW - ML - MR
BODY = 9.0          # minimum body size
SMALL = 9.0


def sw(text, font="R", size=BODY):
    return pdfmetrics.stringWidth(text, FN[font], size)


def wrap(text, width, font="R", size=BODY):
    """greedy word wrap; words longer than the width are split by character"""
    out = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        line = ""
        for w in words:
            cand = (line + " " + w) if line else w
            if sw(cand, font, size) <= width:
                line = cand
                continue
            if line:
                out.append(line)
            if sw(w, font, size) <= width:
                line = w
            else:
                piece = ""
                for ch in w:
                    if sw(piece + ch, font, size) > width and piece:
                        out.append(piece)
                        piece = ch
                    else:
                        piece += ch
                line = piece
        out.append(line)
    return out


class Pen:
    """text drawing that registers every string with its source"""

    def __init__(self, c, reg):
        self.c = c
        self.reg = reg

    def text(self, x, y, s, src="-", font="R", size=BODY, color=INK, anchor="l", mvals=None, url=None):
        c = self.c
        c.setFont(FN[font], size)
        c.setFillColor(color)
        w = sw(s, font, size)
        if anchor == "c":
            x0 = x - w / 2
        elif anchor == "r":
            x0 = x - w
        else:
            x0 = x
        c.drawString(x0, y, s)
        self.reg.add(s, src, mvals)
        if url:
            c.linkURL(url, (x0, y - size * 0.25, x0 + w, y + size * 0.85), relative=0, thickness=0)
        return w

    def para(self, x, ytop, width, s, src="-", font="R", size=BODY, color=INK, lead=1.28, max_lines=None,
             mvals=None, anchor="l"):
        """paragraph from the top edge; returns the height used"""
        lines = wrap(s, width, font, size)
        if max_lines and len(lines) > max_lines:
            raise ValueError("text needs %d lines > %d: %s" % (len(lines), max_lines, s[:80]))
        y = ytop - size
        for ln in lines:
            if anchor == "c":
                self.text(x + width / 2, y, ln, src, font, size, color, "c", mvals)
            else:
                self.text(x, y, ln, src, font, size, color, "l", mvals)
            y -= size * lead
        return len(lines) * size * lead

    def height(self, s, width, font="R", size=BODY, lead=1.28):
        return len(wrap(s, width, font, size)) * size * lead


# ------------------------------------------------------------------------------------------------ page frame
def page_frame(pen, section, n, N, footer_fmt, footer_src="structure: footer (revision, date, page n/N)"):
    c = pen.c
    c.setFillColor(white)
    c.rect(0, 0, PW, PH, stroke=0, fill=1)
    # header: section name (accent) left, document name right, thin rule
    pen.text(ML, PH - 8.2 * MM, section.upper(), "-", "SB", BODY, ACCENT)
    pen.text(PW - MR, PH - 8.2 * MM, "Rev3.0 Oven Controller · Glass Front", "-", "R", BODY, GREY, "r")
    c.setStrokeColor(RULE); c.setLineWidth(0.6)
    c.line(ML, PH - 10 * MM, PW - MR, PH - 10 * MM)
    # footer
    c.line(ML, 9.2 * MM, PW - MR, 9.2 * MM)
    pen.text(PW - MR, 5.6 * MM, footer_fmt.format(n=n, N=N), footer_src, "R", BODY, GREY, "r")


def title(pen, s, src="-", sub=None, sub_src="-"):
    pen.text(ML, PH - 20.5 * MM, s, src, "SB", 19, INK)
    if sub:
        pen.text(ML, PH - 26.5 * MM, sub, sub_src, "R", 10, GREY)


# ------------------------------------------------------------------------------------------------ images
def trim(im, bg=(255, 255, 255), tol=6, pad=8):
    a = np.asarray(im.convert("RGB")).astype(int)
    d = np.abs(a - np.array(bg)).max(axis=2) > tol
    ys, xs = np.where(d)
    if len(xs) == 0:
        return im, (0, 0)
    x0, x1 = max(0, xs.min() - pad), min(im.width, xs.max() + pad + 1)
    y0, y1 = max(0, ys.min() - pad), min(im.height, ys.max() + pad + 1)
    return im.crop((x0, y0, x1, y1)), (x0, y0)


class Img:
    """an image prepared for placement: PIL image + offset of its crop in the source pixels"""

    def __init__(self, path, crop=None, do_trim=True, bg=(255, 255, 255), max_px=2400, pad=8):
        im = Image.open(path).convert("RGB")
        ox, oy = 0, 0
        if crop:
            im = im.crop(crop)
            ox, oy = crop[0], crop[1]
        if do_trim:
            im, (tx, ty) = trim(im, bg, pad=pad)
            ox += tx; oy += ty
        self.scale_src = 1.0
        if max(im.size) > max_px:
            s = max_px / max(im.size)
            im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
            self.scale_src = s
        self.im = im
        self.off = (ox, oy)
        self.path = path

    @property
    def aspect(self):
        return self.im.width / self.im.height

    def reader(self, jpeg=False):
        buf = io.BytesIO()
        if jpeg:
            self.im.save(buf, "JPEG", quality=90, optimize=True)
        else:
            self.im.save(buf, "PNG", optimize=True)
        buf.seek(0)
        return ImageReader(buf)


def place(c, img, x, y, w, h, align="c", jpeg=False, frame=False):
    """fit img into the box (x, y bottom-left, w, h); returns a mapper src-pixel -> page point and the rect"""
    a = img.aspect
    if w / h > a:
        pw, ph = h * a, h
    else:
        pw, ph = w, w / a
    if align == "c":
        px, py = x + (w - pw) / 2, y + (h - ph) / 2
    elif align == "l":
        px, py = x, y + (h - ph) / 2
    elif align == "t":
        px, py = x + (w - pw) / 2, y + h - ph
    else:
        px, py = x + (w - pw) / 2, y
    c.drawImage(img.reader(jpeg), px, py, pw, ph)
    if frame:
        c.setStrokeColor(RULE); c.setLineWidth(0.5); c.rect(px, py, pw, ph, stroke=1, fill=0)
    k = pw / img.im.width

    def m(sx, sy):
        """source-image pixel (before crop/trim/resize) -> page point"""
        ix = (sx - img.off[0]) * img.scale_src
        iy = (sy - img.off[1]) * img.scale_src
        return px + ix * k, py + ph - iy * k
    return m, (px, py, pw, ph)


# ------------------------------------------------------------------------------------------------ balloons from an id buffer
class IdBuffer:
    def __init__(self, render_name, ovr):
        rec = json.load(open(os.path.join(ovr, render_name + ".json")))
        self.rec = rec
        a = np.asarray(Image.open(os.path.join(ovr, render_name + "_id.png")).convert("RGB")).astype(int)
        self.a = a
        self.bg = (np.abs(a - 255).max(axis=2) <= 2)
        self.masks = {k: (np.abs(a - np.array(c)).max(axis=2) <= 2) for k, c in rec["keys"].items()}

    def nearest(self, key, px, py):
        m = self.masks[key]
        ys, xs = np.where(m)
        if len(xs) == 0:
            return None
        d = (xs - px) ** 2 + (ys - py) ** 2
        i = int(np.argmin(d))
        return float(xs[i]), float(ys[i])

    def interior(self, key, px, py, depth=6):
        """a visible pixel of the key near (px, py) that lies at least `depth` px inside its region"""
        e = erode(self.masks[key], depth)
        ys, xs = np.where(e)
        if len(xs) == 0:
            return self.nearest(key, px, py)
        d = (xs - px) ** 2 + (ys - py) ** 2
        i = int(np.argmin(d))
        return float(xs[i]), float(ys[i])


def erode(m, k):
    """binary erosion with a (2k+1) square, numpy only"""
    e = m.copy()
    for _ in range(k):
        n = e.copy()
        n[1:, :] &= e[:-1, :]; n[:-1, :] &= e[1:, :]
        n[:, 1:] &= e[:, :-1]; n[:, :-1] &= e[:, 1:]
        e = n
    return e


def free_circle(bg, cx, cy, r):
    h, w = bg.shape
    x0, x1 = int(cx - r), int(cx + r) + 1
    y0, y1 = int(cy - r), int(cy + r) + 1
    if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
        return False
    yy, xx = np.mgrid[y0:y1, x0:x1]
    inside = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    return bool(bg[y0:y1, x0:x1][inside].all())


def balloon(c, pen, x, y, r, label, src="-", tx=None, ty=None, fill=ACCENT):
    if tx is not None:
        c.setStrokeColor(INK); c.setLineWidth(0.7)
        ang = math.atan2(ty - y, tx - x)
        c.line(x + r * math.cos(ang), y + r * math.sin(ang), tx, ty)
        c.setFillColor(INK); c.circle(tx, ty, 1.3, stroke=0, fill=1)
    c.setFillColor(fill); c.setStrokeColor(white); c.setLineWidth(0.8)
    c.circle(x, y, r, stroke=1, fill=1)
    pen.text(x, y - 3.4, str(label), src, "SB", 10, white, "c")


LEADERS = []   # every leader segment drawn since the last reset (for the crossing checks)


def segments_cross(a, b):
    """True if two segments properly intersect (shared end points do not count)"""
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    def orient(ax, ay, bx, by, cx, cy):
        return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d1 = orient(x3, y3, x4, y4, x1, y1); d2 = orient(x3, y3, x4, y4, x2, y2)
    d3 = orient(x1, y1, x2, y2, x3, y3); d4 = orient(x1, y1, x2, y2, x4, y4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def leader_label(c, pen, tx, ty, lx, ly, lines, src="-", anchor="l", size=BODY, color=INK, font="R", dot=True,
                 mvals=None):
    """label text at (lx, ly) baseline of the first line, leader from the label edge to the target (tx, ty)"""
    c.setStrokeColor(INK); c.setLineWidth(0.6)
    if isinstance(lines, str):
        lines = [lines]
    w = max(sw(l, font, size) for l in lines)
    x0 = lx if anchor == "l" else (lx - w if anchor == "r" else lx - w / 2)
    x1 = x0 + w
    # attach the leader at the side of the text that faces the target, so it never runs through the text
    if tx >= x1:
        ex = x1 + 2
    elif tx <= x0:
        ex = x0 - 2
    else:
        ex = min(max(tx, x0), x1)
    ey = ly + size * 0.35
    if x0 < tx < x1:
        ey = ly - size * 0.35 if ty < ly else ly + size * 1.0
    c.line(ex, ey, tx, ty)
    LEADERS.append((ex, ey, tx, ty))
    if dot:
        c.setFillColor(INK); c.circle(tx, ty, 1.2, stroke=0, fill=1)
    y = ly
    for l in lines:
        pen.text(lx, y, l, src, font, size, color, anchor, mvals)
        y -= size * 1.25
    return w


def rrect(c, x, y, w, h, r, stroke=None, fill=None, lw=0.6):
    c.setLineWidth(lw)
    if stroke is not None:
        c.setStrokeColor(stroke)
    if fill is not None:
        c.setFillColor(fill)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke is not None else 0, fill=1 if fill is not None else 0)
