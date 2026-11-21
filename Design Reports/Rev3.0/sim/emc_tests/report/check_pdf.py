"""Mechanical checks of Rev3.0_EMC_Test_Simulation_Results.pdf (read-only):
  1. text-collision check: no two text lines from different labels overlap (PyMuPDF line boxes, shrunk by 15 % of their
     height top and bottom and 0.4 pt left and right to remove font-ascender padding);
  2. margin check: every text line inside [36, W-36] x [20, H-12] pt;
  3. font size: every span >= 7.95 pt.
Optional: --png renders every page at 115 dpi into the folder given after it.
Run: python -X utf8 check_pdf.py [--png DIR]
"""
import os, sys
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.abspath(os.path.join(HERE, "..", "..", "..", "Rev3.0_EMC_Test_Simulation_Results.pdf"))


def lines_of(page):
    out = []
    d = page.get_text("dict")
    for b in d["blocks"]:
        if b.get("type") != 0:
            continue
        for ln in b["lines"]:
            txt = "".join(s["text"] for s in ln["spans"]).strip()
            if not txt:
                continue
            r = fitz.Rect(ln["bbox"])
            sizes = [s["size"] for s in ln["spans"] if s["text"].strip()]
            out.append((r, txt, min(sizes) if sizes else 99))
    return out


def shrink(r):
    h = r.height; w = r.width
    if w >= h:   # horizontal text
        return fitz.Rect(r.x0 + 0.4, r.y0 + 0.15 * h, r.x1 - 0.4, r.y1 - 0.15 * h)
    return fitz.Rect(r.x0 + 0.15 * w, r.y0 + 0.4, r.x1 - 0.15 * w, r.y1 - 0.4)


def main():
    doc = fitz.open(PDF)
    W, H = doc[0].rect.width, doc[0].rect.height
    collisions, margins, small = [], [], []
    nlines = 0
    for pno, page in enumerate(doc, 1):
        L = lines_of(page)
        nlines += len(L)
        for i in range(len(L)):
            ri = shrink(L[i][0])
            if L[i][0].x0 < 36 or L[i][0].x1 > W - 36 or L[i][0].y0 < 20 or L[i][0].y1 > H - 12:
                margins.append((pno, L[i][1][:50], tuple(round(v, 1) for v in L[i][0])))
            if L[i][2] < 7.95:
                small.append((pno, L[i][1][:50], round(L[i][2], 2)))
            for j in range(i + 1, len(L)):
                rj = shrink(L[j][0])
                inter = ri & rj
                if inter.is_valid and not inter.is_empty and inter.width > 0.3 and inter.height > 0.3:
                    collisions.append((pno, L[i][1][:40], L[j][1][:40], round(inter.width, 1), round(inter.height, 1)))
    print("pages %d, text lines %d" % (len(doc), nlines))
    print("collisions: %d" % len(collisions))
    for c in collisions:
        print("  p%d  [%s] x [%s]  overlap %.1f x %.1f pt" % c)
    print("outside margins: %d" % len(margins))
    for m in margins:
        print("  p%d  [%s] %s" % m)
    print("spans below 8 pt: %d" % len(small))
    for s in small[:40]:
        print("  p%d  [%s] %.2f pt" % s)
    if "--png" in sys.argv:
        out = sys.argv[sys.argv.index("--png") + 1]
        os.makedirs(out, exist_ok=True)
        for pno, page in enumerate(doc, 1):
            page.get_pixmap(dpi=115).save(os.path.join(out, "page_%02d.png" % pno))
        print("rendered %d pages to %s" % (len(doc), out))


if __name__ == "__main__":
    main()
