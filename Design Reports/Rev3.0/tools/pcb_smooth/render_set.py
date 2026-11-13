"""Renders for review (system python with PyMuPDF): 3D top/bottom (kicad-cli pcb render), per-layer SVG exports and
150-dpi PNG crops of every region.  The SVG page is the board bounding box incl. the ears (round 3: local
x -9.3..174.3, y -10.3..108.3).  Usage: render_set.py board.kicad_pcb outdir"""
import subprocess, sys, os, fitz
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
src, out = sys.argv[1], sys.argv[2]
DPI = int(sys.argv[3]) if len(sys.argv) > 3 else 150
os.makedirs(out, exist_ok=True)
# page = board bounding box incl. the ears and half the 0.1 mm Edge.Cuts stroke.  Smoothing round: x 0..174.3,
# y -10.3..99; round 3 (ears on all four edges): x -9.3..174.3, y -10.3..108.3
BB = (-9.3 - 0.05, -10.3 - 0.05, 174.3 + 0.05, 108.3 + 0.05)
SETS = {
    "top": "F.Cu,F.SilkS,F.Mask,Edge.Cuts,User.Comments",
    "fcu": "F.Cu,Edge.Cuts",
    "bcu": "B.Cu,Edge.Cuts",
    "in1_gnd": "In1.Cu,Edge.Cuts",
    "in2_pwr": "In2.Cu,Edge.Cuts",
    "fb": "F.Cu,B.Cu,Edge.Cuts,F.SilkS",
}
REG = {   # local mm x0, y0, x1, y1 (round 3 hole names: H1..H9 clockwise from the top-left)
    "mains_band": (24, -10, 132, 58), "heater_stage": (88, 8, 132, 58), "mains_input_filter": (24, -10, 90, 36),
    "psu_corner": (126, -10, 173.5, 62), "esp32": (-1, 0, 46, 76), "ssd1963_bus": (22, 34, 82, 86),
    "rgb_ribbon": (64, 52, 150, 92), "j10": (118, 78, 160, 99.2), "j11": (30, 78, 60, 99.2), "j11_zoom": (31, 82, 49, 95.5),
    "lv_power": (66, 66, 106, 99.2), "thermocouple": (-1, 70, 42, 99.2), "relay_k1": (54, 26, 90, 62),
    "ear_H1": (2, -10.3, 18, 4), "ear_H2": (65, -10.3, 81, 4), "ear_H3": (146, -10.3, 162, 4),
    "ear_H4": (160, 2, 174.3, 18), "ear_H5": (160, 81, 174.3, 97), "ear_H6": (146, 95, 165, 108.3),
    "ear_H7": (-1, 95, 18, 108.3), "ear_H8": (-9.3, 81, 5, 97), "ear_H9": (-9.3, 2, 5, 18),
    "former_hole_4_4": (-1, -1, 12, 12), "former_hole_4_95": (-1, 87, 12, 100), "former_hole_97_95": (89, 87, 105, 100),
    "former_hole_160_95": (152, 87, 165, 100), "corner_bl": (-9.3, 85, 18, 108.3), "slot_u1_u5": (98, 46, 128, 58),
}
r = subprocess.run([CLI, "pcb", "render", "--side", "top", "--width", "2400", "--height", "1600", "--quality", "high",
                    "-o", os.path.join(out, "render3d_top.png"), src], capture_output=True, text=True)
print("render top", r.returncode, r.stderr.strip()[-200:])
r = subprocess.run([CLI, "pcb", "render", "--side", "bottom", "--width", "2400", "--height", "1600", "--quality", "high",
                    "-o", os.path.join(out, "render3d_bottom.png"), src], capture_output=True, text=True)
print("render bottom", r.returncode, r.stderr.strip()[-200:])
VIEWS = {"render3d_iso_front_bottom": ["--side", "top", "--rotate", "-60,0,-20", "--perspective", "--zoom", "0.85"],
         "render3d_iso_back": ["--side", "bottom", "--rotate", "-50,0,25", "--perspective", "--zoom", "0.85"],
         "render3d_side_front": ["--side", "front"], "render3d_side_right": ["--side", "right"]}
for vn, va in VIEWS.items():
    r = subprocess.run([CLI, "pcb", "render", "--width", "2400", "--height", "1600", "--quality", "high"] + va +
                       ["-o", os.path.join(out, vn + ".png"), src], capture_output=True, text=True)
    print(vn, r.returncode, r.stderr.strip()[-200:])
for name, layers in SETS.items():
    svg = os.path.join(out, "layer_%s.svg" % name)
    subprocess.run([CLI, "pcb", "export", "svg", "--layers", layers, "--mode-single", "--page-size-mode", "2",
                    "--exclude-drawing-sheet", "-o", svg, src], capture_output=True)
    doc = fitz.open(svg); page = doc[0]; rr = page.rect
    page.get_pixmap(dpi=60).save(os.path.join(out, "layer_%s_full.png" % name))
    if name not in ("top", "fb", "in1_gnd", "in2_pwr", "bcu"):
        continue
    for reg, (x0, y0, x1, y1) in REG.items():
        if name in ("in1_gnd", "in2_pwr", "bcu") and reg.startswith("ear"):
            continue
        fx = lambda x: rr.x0 + rr.width * (x - BB[0]) / (BB[2] - BB[0])
        fy = lambda y: rr.y0 + rr.height * (y - BB[1]) / (BB[3] - BB[1])
        clip = fitz.Rect(fx(x0), fy(y0), fx(x1), fy(y1))
        page.get_pixmap(dpi=DPI, clip=clip).save(os.path.join(out, "crop_%s_%s.png" % (reg, name)))
print("done", out)
