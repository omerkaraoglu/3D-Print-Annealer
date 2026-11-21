"""Stage 2 back-side overview: kicad-cli SVG of the back layers, mirrored (seen from the back, as the panel sees it),
rasterised with PyMuPDF, then annotated with PIL: pad numbers BPn (large), the shelf window (dashed), the LV boundary,
the reserved earth-bond ring-lug circle (not placed), J10 / J11 outlines.
Usage: s2_render.py board plan.json out.png px_per_mm [lug=x,y]"""
import sys, os, subprocess, re, json
import fitz
from PIL import Image, ImageDraw, ImageFont
brd, planf, outp, ppm = sys.argv[1:5]
ppm = float(ppm)
lug = None
for a in sys.argv[5:]:
    if a.startswith("lug="): lug = tuple(map(float, a[4:].split(",")))
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
svg = outp[:-4] + ".svg"
subprocess.run([CLI, "pcb", "export", "svg", "--layers", "B.Cu,B.Mask,B.Silkscreen,Edge.Cuts", "--mode-single", "--mirror",
                "--exclude-drawing-sheet", "--page-size-mode", "2", "-o", svg, brd], capture_output=True, check=True)
doc = fitz.open(svg); page = doc[0]
txt = open(svg, encoding="utf-8").read(2000)
vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', txt).group(1).split()]
k = page.rect.width / vb[2]
pix = page.get_pixmap(matrix=fitz.Matrix(ppm / k, ppm / k))
img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img); img = bg
# board-area page spans local x -9.30 .. 174.30 (183.6 mm), y -10.30 .. 108.30; mirrored: X = (174.30 - x)
X0, X1, Y0 = -9.30, 174.30, -10.30
def P(x, y):
    return ((X1 - x) * ppm, (y - Y0) * ppm)
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype("arialbd.ttf", int(3.2 * ppm)); fs = ImageFont.truetype("arial.ttf", int(1.8 * ppm))
except OSError:
    f = fs = ImageFont.load_default()
def rect(x0, y0, x1, y1, col, w=2, dash=False):
    a, b = P(x1, y0), P(x0, y1)
    if not dash:
        d.rectangle([a[0], a[1], b[0], b[1]], outline=col, width=w); return
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for (p, q) in zip(pts, pts[1:]):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) / 2.0) or 1
        for i in range(0, n, 2):
            s = (p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n); e = (p[0] + (q[0] - p[0]) * (i + 1) / n, p[1] + (q[1] - p[1]) * (i + 1) / n)
            d.line([P(*s), P(*e)], fill=col, width=w)
rect(2.62, 1.6, 162.32, 96.4, (0, 0, 0), 2, dash=True)
LV = [(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (61.5, 56.0), (61.5, 45.0), (77.0, 45.0), (77.0, 56.0), (96.0, 56.0), (96.0, 54.8),
      (126.0, 54.8), (130.0, 55.5), (130.0, 40.0), (163.5, 40.0)]
d.line([P(*p) for p in LV], fill=(200, 0, 200), width=3)
plan = json.load(open(planf))
for p in plan["pads"]:
    x, y = P(p["x"], p["y"])
    d.text((x, y), p["ref"][2:], fill=(220, 0, 0), font=f, anchor="mm", stroke_width=2, stroke_fill=(255, 255, 255))
for ref, (x0, y0, x1, y1) in (("J10 (front side)", (122.18, 87.05, 149.12, 95.4)), ("J11 (front side)", (34.7, 88.55, 45.33, 94.97))):
    rect(x0, y0, x1, y1, (0, 120, 255), 2)
    a = P((x0 + x1) / 2, y0 - 1.6); d.text(a, ref, fill=(0, 90, 220), font=fs, anchor="mm")
if lug:
    a, b = P(lug[0] + 3.5, lug[1] - 3.5), P(lug[0] - 3.5, lug[1] + 3.5)
    d.ellipse([a[0], a[1], b[0], b[1]], outline=(0, 150, 0), width=3)
    c = P(lug[0], lug[1] + 5.2); d.text(c, "E (reserved, not placed)", fill=(0, 130, 0), font=fs, anchor="mm")
c = P(82, 104.5)
d.text(c, "Back side (B.Cu / B.Mask / B.SilkS), seen from the back - mirrored. Red = landing pad BPn; dashed = shelf window; "
          "magenta = Cmts.User mains boundary (mains band above)", fill=(0, 0, 0), font=fs, anchor="mm")
img.save(outp); print(outp, img.size)
