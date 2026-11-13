"""Render the front side of a board as PNG: silk white on a dark board, copper under mask dark green, exposed copper
(mask openings over copper) gold, bare laminate in mask openings tan, F.Fab outlines blue (no F.Fab texts), board
edge yellow.
Optionally the courtyards (F.CrtYd) as thin magenta lines (--courtyard, for review crops).

The layers are plotted by kicad-cli (SVG, F.Fab as PDF; black and white, one file per layer, page = absolute board mm),
rasterised by PyMuPDF and composited with numpy / Pillow.

python refdes_render.py <board.kicad_pcb> <out_dir> <prefix> [--courtyard] [--regions regions.json]
                         [--legends placement.json] [--ppmm N] [--no-board]
  whole board at 20 px/mm -> <out_dir>/<prefix>board.png
  every region {name: [x0, y0, x1, y1] absolute mm} at 60 px/mm -> <out_dir>/<prefix><name>.png
"""
import json
import os
import subprocess
import sys
import tempfile

import fitz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image

CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
LAYERS = ["F.Cu", "F.Mask", "F.SilkS", "F.Fab", "Edge.Cuts", "F.CrtYd"]
FILES = {"F.Cu": "F_Cu", "F.Mask": "F_Mask", "F.SilkS": "F_Silkscreen", "F.Fab": "F_Fab", "Edge.Cuts": "Edge_Cuts",
         "F.CrtYd": "F_Courtyard"}
PT = 72.0 / 25.4
PPMM_CROP = 60
from cfg import WINDOW as BOARD   # absolute mm, board outline plus a margin

COL = {"bg": (24, 24, 24), "board": (10, 52, 28), "cu": (36, 96, 52), "pad": (212, 170, 64), "bare": (150, 132, 92),
       "fab": (70, 120, 190), "crt": (215, 80, 200), "silk": (250, 250, 250), "edge": (240, 220, 40)}


def plot(board, tmp):
    # every layer except F.Fab as SVG (kicad-cli 10 PDF export draws stroke text about 3 % wider than the board
    # geometry, Gerber and SVG; found on the Rev3.0 title block), F.Fab as PDF with its texts left out
    # (--exclude-refdes / --exclude-value: the ${REFERENCE} copies and the values), outlines only
    other = [L for L in LAYERS if L != "F.Fab"]
    subprocess.run([CLI, "pcb", "export", "svg", "--mode-multi", "--black-and-white", "--exclude-drawing-sheet",
                    "--drill-shape-opt", "2", "--layers", ",".join(other), "-o", tmp + os.sep, board], check=True,
                   capture_output=True)
    subprocess.run([CLI, "pcb", "export", "pdf", "--mode-separate", "--black-and-white", "--exclude-refdes",
                    "--exclude-value", "--layers", "F.Fab", "-o", tmp + os.sep, board], check=True, capture_output=True)
    base = os.path.splitext(os.path.basename(board))[0]
    return {L: os.path.join(tmp, "%s-%s.%s" % (base, FILES[L], "pdf" if L == "F.Fab" else "svg")) for L in LAYERS}


def raster(pdf, box, ppmm):
    d = fitz.open(pdf)
    p = d[0]
    clip = fitz.Rect(box[0] * PT, box[1] * PT, box[2] * PT, box[3] * PT)
    pm = p.get_pixmap(matrix=fitz.Matrix(ppmm / PT, ppmm / PT), clip=clip, colorspace=fitz.csGRAY, alpha=False)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
    return 1.0 - a.astype(np.float32) / 255.0      # ink coverage 0..1


def compose(pdfs, box, ppmm, courtyard=False):
    lay = {L: raster(pdfs[L], box, ppmm) for L in pdfs}
    h, w = lay["F.Cu"].shape
    img = np.zeros((h, w, 3), np.float32)
    img[:] = COL["board"]

    def over(alpha, col, k=1.0):
        a = np.clip(alpha * k, 0, 1)[..., None]
        img[:] = img * (1 - a) + np.array(col, np.float32) * a

    cu, mask = lay["F.Cu"], lay["F.Mask"]
    over(cu, COL["cu"])
    over(mask * (1 - cu), COL["bare"])
    over(mask * cu, COL["pad"])
    over(lay["F.Fab"], COL["fab"], 0.8)
    if courtyard:
        over(lay["F.CrtYd"], COL["crt"], 0.6)
    over(lay["F.SilkS"], COL["silk"])
    over(lay["Edge.Cuts"], COL["edge"])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def main():
    board, out, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
    courtyard = "--courtyard" in sys.argv
    global PPMM_CROP
    if "--ppmm" in sys.argv:
        PPMM_CROP = float(sys.argv[sys.argv.index("--ppmm") + 1])
    regions = {}
    if "--regions" in sys.argv:
        regions = json.load(open(sys.argv[sys.argv.index("--regions") + 1], encoding="utf-8"))
    if "--legends" in sys.argv:          # one crop per legend block: block + its group + 2 mm
        pl = json.load(open(sys.argv[sys.argv.index("--legends") + 1], encoding="utf-8"))
        for b in pl["blocks"]:
            r, g = b["rect"], b["group_bbox"]
            regions["legend_%s_%s" % (b["name"], "-".join(b["members"][:3]) + ("-etc" if len(b["members"]) > 3 else ""))] = [
                round(min(r[0], g[0]) - 2, 2), round(min(r[1], g[1]) - 2, 2), round(max(r[2], g[2]) + 2, 2),
                round(max(r[3], g[3]) + 2, 2)]
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pdfs = plot(board, tmp)
        if "--no-board" not in sys.argv:
            compose(pdfs, BOARD, 20, courtyard).save(os.path.join(out, prefix + "board.png"))
            print("wrote", prefix + "board.png")
        for name, box in regions.items():
            compose(pdfs, box, PPMM_CROP, courtyard).save(os.path.join(out, prefix + name + ".png"))
            print("wrote", prefix + name + ".png")


if __name__ == "__main__":
    main()
