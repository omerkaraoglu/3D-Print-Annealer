import fitz, sys
svg, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
dpi = int(sys.argv[7]) if len(sys.argv) > 7 else 500
doc = fitz.open(svg); page = doc[0]; r = page.rect
clip = fitz.Rect(r.x0 + r.width * x0 / 164, r.y0 + r.height * y0 / 99, r.x0 + r.width * x1 / 164, r.y0 + r.height * y1 / 99)
pix = page.get_pixmap(dpi=dpi, clip=clip); pix.save(out); print(out, pix.width, pix.height)
