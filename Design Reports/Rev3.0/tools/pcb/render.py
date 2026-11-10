import subprocess, sys, fitz, os
src = sys.argv[1]; out = sys.argv[2]; layers = sys.argv[3] if len(sys.argv) > 3 else "F.Cu,B.Cu,F.SilkS,F.CrtYd,B.CrtYd,Edge.Cuts,Cmts.User"
svg = out + ".svg"
subprocess.run([r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", svg, src], check=True)
doc = fitz.open(svg); pix = doc[0].get_pixmap(dpi=int(sys.argv[4]) if len(sys.argv) > 4 else 150); pix.save(out)
print("rendered", out, pix.width, pix.height)
