"""Stage 5 review renders: the J5 earth-bond area on the front and back copper with the neighbours labelled, and the
schematic region with J5.
    python stage5_render.py board.kicad_pcb sch.pdf check.json frame_v2_params.json outdir
Board: kicad-cli SVG (board-area page) of the chosen layers -> PyMuPDF raster 30 px/mm -> PIL labels. The page origin is
the Edge.Cuts bounding box (pcbnew), so the overlay is exact. Overlays (thin, labelled): front - the M3 ring-lug envelope
at the 150 deg tongue direction, the H8 PT-screw head (assumed dia 6.0), the direction to FH9, the removed vias;
back - the frame v2 / GF-2.1 support ribs 9 and 21 and the shelf window edge (frame documents, read only), the screw
head (dk 5.6, + 0.2 mm hole play). Not mirrored: the back is shown as seen through the board from the component side."""
import json
import math
import os
import re
import subprocess
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
KP = r"C:/Program Files/KiCad/10.0/bin/python.exe"
brd, schpdf, chkf, fpf, out = sys.argv[1:6]
os.makedirs(out, exist_ok=True)
CHK = json.load(open(chkf))
FP = json.load(open(fpf, encoding="utf-8"))
PPM = 30.0
BOX = (-9.3, 76.5, 25.7, 101.5)           # local mm crop (x0 >= board-area page origin -9.35)
bb = subprocess.run([KP, "-c", "import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); r=b.GetBoardEdgesBoundingBox(); "
                     "print(pcbnew.ToMM(r.GetLeft()), pcbnew.ToMM(r.GetTop()))", brd], capture_output=True, text=True).stdout.split()
OX, OY = float(bb[0]) - 20.0, float(bb[1]) - 20.0
try:
    F = ImageFont.truetype("arial.ttf", 17); FB = ImageFont.truetype("arialbd.ttf", 20); FS = ImageFont.truetype("arial.ttf", 14)
except OSError:
    F = FB = FS = ImageFont.load_default()


def raster(layers, tag):
    svg = os.path.join(out, tag + ".svg")
    subprocess.run([CLI, "pcb", "export", "svg", "--layers", layers, "--mode-single", "--exclude-drawing-sheet",
                    "--page-size-mode", "2", "-o", svg, brd], capture_output=True, check=True)
    doc = fitz.open(svg)
    page = doc[0]
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', open(svg, encoding="utf-8").read(3000)).group(1).split()]
    k = page.rect.width / vb[2]
    x0, y0, x1, y1 = BOX
    clip = fitz.Rect((x0 - OX) * k, (y0 - OY) * k, (x1 - OX) * k, (y1 - OY) * k)
    pix = page.get_pixmap(matrix=fitz.Matrix(PPM / k, PPM / k), clip=clip)
    png = os.path.join(out, tag + "_raw.png")
    pix.save(png)
    doc.close()
    os.remove(svg)
    im = Image.open(png).convert("RGB")
    os.remove(png)
    return im


def P(x, y):
    return ((x - BOX[0]) * PPM, (y - BOX[1]) * PPM)


def label(d, text, at, xy, col=(0, 0, 0), font=None):
    """text at xy (px, top-left), leader from the text box to the feature at 'at' (local mm)"""
    font = font or F
    tb = d.textbbox(xy, text, font=font)
    d.rectangle((tb[0] - 3, tb[1] - 2, tb[2] + 3, tb[3] + 2), fill=(255, 255, 255), outline=col)
    d.text(xy, text, fill=col, font=font)
    if at is not None:
        ax, ay = P(*at)
        bx = min(max(ax, tb[0] - 3), tb[2] + 3); by = min(max(ay, tb[1] - 2), tb[3] + 2)
        d.line((bx, by, ax, ay), fill=col, width=2)
        d.ellipse((ax - 3, ay - 3, ax + 3, ay + 3), fill=col)


def circle(d, c, r, col, w=2, dash=False):
    if not dash:
        x, y = P(*c); d.ellipse((x - r * PPM, y - r * PPM, x + r * PPM, y + r * PPM), outline=col, width=w)
        return
    for a in range(0, 360, 12):
        p0 = P(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
        p1 = P(c[0] + r * math.cos(math.radians(a + 7)), c[1] + r * math.sin(math.radians(a + 7)))
        d.line((p0, p1), fill=col, width=w)


def dashed(d, pts, col, w=2):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0); n = max(1, int(L / 0.6))
        for i in range(0, n, 2):
            a = P(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n); b = P(x0 + (x1 - x0) * min(i + 1, n) / n, y0 + (y1 - y0) * min(i + 1, n) / n)
            d.line((a, b), fill=col, width=w)


def scalebar(d, im):
    x, y = 20, im.height - 30
    d.rectangle((x - 4, y - 22, x + 5 * PPM + 6, y + 8), fill=(255, 255, 255))
    d.line((x, y, x + 5 * PPM, y), fill=(0, 0, 0), width=3)
    d.text((x, y - 20), "5 mm", fill=(0, 0, 0), font=FS)


def title(d, im, s):
    tb = d.textbbox((10, 6), s, font=FB)
    d.rectangle((4, 2, tb[2] + 8, tb[3] + 6), fill=(255, 255, 255))
    d.text((10, 6), s, fill=(0, 0, 0), font=FB)


J = CHK["j5"]; cx, cy = J["pos"]
BLUE, RED, GRN, MAG, ORG = (0, 60, 200), (190, 0, 0), (0, 120, 0), (150, 0, 150), (210, 110, 0)
# ---- front
im = raster("F.Cu,F.Mask,F.SilkS,F.CrtYd,Edge.Cuts", "s5front")
d = ImageDraw.Draw(im)
th = math.radians(150)
ring_r, tw, L = 3.2, 5.2, 17.0
u = (math.cos(th), math.sin(th)); n_ = (-u[1], u[0])
a0 = math.degrees(math.asin(tw / 2 / ring_r))
arc = [(cx + ring_r * math.cos(th + math.radians(a)), cy + ring_r * math.sin(th + math.radians(a))) for a in range(int(a0), int(360 - a0) + 1, 6)]
tongue = [(cx + u[0] * L + n_[0] * tw / 2 * s, cy + u[1] * L + n_[1] * tw / 2 * s) for s in (-1, 1)]
outline = [(cx + u[0] * math.sqrt(ring_r ** 2 - (tw / 2) ** 2) + n_[0] * tw / 2, cy + u[1] * math.sqrt(ring_r ** 2 - (tw / 2) ** 2) + n_[1] * tw / 2),
           tongue[1], tongue[0],
           (cx + u[0] * math.sqrt(ring_r ** 2 - (tw / 2) ** 2) - n_[0] * tw / 2, cy + u[1] * math.sqrt(ring_r ** 2 - (tw / 2) ** 2) - n_[1] * tw / 2)]
dashed(d, outline, ORG, 3)
dashed(d, arc, ORG, 3)
circle(d, (-4.8, 89.0), 3.0, MAG, 2, dash=True)
F9 = CHK["frame"]["FH9 (local)"]
ax, ay = cx + (F9[0] - cx) * 0.55, cy + (F9[1] - cy) * 0.55
d.line((P(cx, cy), P(ax, ay)), fill=GRN, width=2)
for vx, vy in ((6.0, 91.5), (10.5, 91.5)):
    x, y = P(vx, vy); d.line((x - 6, y - 6, x + 6, y + 6), fill=RED, width=3); d.line((x - 6, y + 6, x + 6, y - 6), fill=RED, width=3)
label(d, "J5: GND, pad 7.0 / drill 3.2, solid", (cx + 2.4, cy - 2.4), (P(12.6, 0)[0], P(0, 78.6)[1]), BLUE, FB)
label(d, "J5 designator", (5.9, 97.6), (P(15.5, 0)[0], P(0, 98.6)[1]), BLUE)
label(d, "earth mark (IEC 60417-5017)", (12.3, 93.4), (P(15.0, 0)[0], P(0, 93.2)[1]), BLUE)
label(d, "J20 TC_N pad: 2.64 mm copper to copper", (6.5, 86.4), (P(-9.0, 0)[0], P(0, 78.4)[1]), (0, 0, 0))
label(d, "J20 courtyard: 0.39 mm", (3.5, 88.17), (P(-9.0, 0)[0], P(0, 80.2)[1]), (0, 0, 0))
label(d, "D221 (TC_N / GND)", (13.0, 87.6), (P(15.4, 0)[0], P(0, 86.2)[1]), (0, 0, 0))
label(d, "R223", (17.5, 89.5), (P(19.4, 0)[0], P(0, 90.5)[1]), (0, 0, 0))
label(d, "H8 (NPTH, PT screw head dia 6 assumed)", (-4.8, 92.0), (P(-9.0, 0)[0], P(0, 95.4)[1]), MAG)
label(d, "H7 (NPTH)", (10.0, 100.5), (P(15.4, 0)[0], P(0, 100.3)[1]), MAG)
label(d, "M3 ring lug 6.4 / barrel 5.2 x 17 at 150 deg", (cx - 8.5, cy + 4.3), (P(-9.0, 0)[0], P(0, 97.4)[1]), ORG)
label(d, "direction to FH9 (22.2 mm)", (ax, ay), (P(-9.0, 0)[0], P(0, 82.4)[1]), GRN)
label(d, "x = GND vias removed", None, (P(15.5, 0)[0], P(0, 95.6)[1]), RED, FS)
title(d, im, "J5 front (F.Cu, mask, silk, courtyards) - lug side; local mm, mains copper 68.5 mm away")
scalebar(d, im)
im.save(os.path.join(out, "stage5_J5_front.png"))
# ---- back
im = raster("B.Cu,B.Mask,B.SilkS,B.CrtYd,Edge.Cuts", "s5back")
d = ImageDraw.Draw(im)
ribs = {r["rib"]: r for r in FP["support_ribs"]["per_rib"]}
for n in (9, 21):
    r = ribs[n]; x0, y0, x1, y1 = r["x0"] - 20, r["y0"] - 20, r["x1"] - 20, r["y1"] - 20
    dashed(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], MAG, 3)
dashed(d, [(2.62, 78.0), (2.62, 96.4), (24.0, 96.4)], GRN, 2)
circle(d, (cx, cy), 3.0, ORG, 2, dash=True)
fr = CHK["frame"]
label(d, "J5 on B.Cu: copper 7.0, bare 5.6 (screw-head side)", (cx + 2.5, cy - 2.5), (P(4.0, 0)[0], P(0, 78.6)[1]), BLUE, FB)
label(d, "screw head dk 5.6 + 0.2 play (no washer on B)", (cx - 2.0, cy + 2.0), (P(-9.0, 0)[0], P(0, 99.0)[1]), ORG)
label(d, "rib 9: bare area %.2f, head %.2f mm" % (fr["B bare area (mask opening)"][0][0], fr["screw head dk 5.6 + 0.2 radial hole play"][0][0]),
      (8.0, 97.2), (P(11.0, 0)[0], P(0, 99.0)[1]), MAG)
label(d, "rib 21: bare area %.2f, head %.2f mm" % (fr["B bare area (mask opening)"][1][0], fr["screw head dk 5.6 + 0.2 radial hole play"][1][0]),
      (1.0, 91.0), (P(-9.0, 0)[0], P(0, 86.0)[1]), MAG)
label(d, "shelf window edge (shelf at Z -2.10 outside)", (2.62, 84.0), (P(-9.0, 0)[0], P(0, 82.6)[1]), GRN)
label(d, "BP16 (GND): copper 1.50, bare area 2.50 mm", (13.0, 90.0), (P(11.0, 0)[0], P(0, 85.6)[1]), (0, 0, 0))
label(d, "J20 pads (TC_P / TC_N): 2.64 mm", (7.6, 80.4), (P(11.0, 0)[0], P(0, 81.0)[1]), (0, 0, 0))
title(d, im, "J5 back (B.Cu, mask, silk, courtyards) seen through from the front; ribs dashed; bare 5.6")
scalebar(d, im)
im.save(os.path.join(out, "stage5_J5_back.png"))
# ---- schematic: Thermocouple sheet (page 3), region around J20 and J5
doc = fitz.open(schpdf)
page = doc[2]
k = 72 / 25.4
clip = fitz.Rect(45 * k, 85 * k, 232 * k, 210 * k)
pix = page.get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72), clip=clip)
p = os.path.join(out, "stage5_J5_schematic.png")
pix.save(p)
print("written", os.path.join(out, "stage5_J5_front.png"), os.path.join(out, "stage5_J5_back.png"), p, "origin", OX, OY)
