"""Crop renders of a board (kicad-cli SVG of chosen layers -> PyMuPDF raster).  Local mm boxes; px/mm >= 30.
Usage: render_crops.py board.kicad_pcb outdir tag layers px_per_mm name=x0,y0,x1,y1 ..."""
import sys, os, subprocess, fitz, re
brd, out, tag, layers, ppm = sys.argv[1:6]
ppm = float(ppm)
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
svg = os.path.join(out, tag + ".svg")
subprocess.run([CLI, "pcb", "export", "svg", "--layers", layers, "--mode-single", "--exclude-drawing-sheet", "--page-size-mode", "2",
                "-o", svg, brd], capture_output=True, check=True)
doc = fitz.open(svg); page = doc[0]
txt = open(svg, encoding="utf-8").read(2000)
vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', txt).group(1).split()]
W = page.rect.width
k = W / vb[2]                     # points per mm
# board-area page: origin = board bounding box (abs 10.70, 9.70) -> local (-9.30, -10.30)
OX, OY = -9.30, -10.30
for arg in sys.argv[6:]:
    name, bx = arg.split("="); x0, y0, x1, y1 = map(float, bx.split(","))
    clip = fitz.Rect((x0 - OX) * k, (y0 - OY) * k, (x1 - OX) * k, (y1 - OY) * k)
    pix = page.get_pixmap(matrix=fitz.Matrix(ppm / k, ppm / k), clip=clip)
    fn = os.path.join(out, "%s_%s.png" % (tag, name)); pix.save(fn); print(fn, pix.width, pix.height)
