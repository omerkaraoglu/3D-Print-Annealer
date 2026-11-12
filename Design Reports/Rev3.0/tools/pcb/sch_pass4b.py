"""Pass 4b: regroup the 33R arrays RN1..RN7 in SSD1963 pin order (the order the lines leave U10: B2 B3 | R0..R7 G0..G7 B0 |
DE PCLK HSYNC VSYNC | B1 B4..B7, see display_lane_decision.md) so the arrays sit at the driver's exits (source termination).
Only the label texts around the arrays change (positions from sch_pass4.py)."""
import re
DISP = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/Rev3_Display.kicad_sch"
s = open(DISP, encoding="utf-8").read()
NEW = [["B2", "B3", "R0", "R1"], ["R2", "R3", "R4", "R5"], ["R6", "R7", "G0", "G1"], ["G2", "G3", "G4", "G5"],
       ["G6", "G7", "B0", "DE"], ["PCLK", "HSYNC", "VSYNC", "B1"], ["B4", "B5", "B6", "B7"]]
XOFF = [-5.08, -2.54, 0.0, 2.54]
for k, nets in enumerate(NEW):
    X, Y = 254.0, 66.04 + 19.05 * k
    for xo, net in zip(XOFF, nets):
        for yy, suffix in ((round(Y + 7.62, 2), "_T"), (round(Y - 7.62, 2), "")):
            pat = r'\(label "[A-Z0-9]+%s"\n\t\t\(at %s %s ' % (suffix, round(X + xo, 2), yy)
            n = len(re.findall(pat, s)); assert n == 1, (k, net, suffix, n)
            s = re.sub(pat, '(label "%s%s"\n\t\t(at %s %s ' % (net, suffix, round(X + xo, 2), yy), s)
# descriptions: note the grouping
s = s.replace("series termination of the RGB/sync lines at the SSD1963 (EMC pass 4)", "series termination of the RGB/sync lines at the SSD1963, grouped in SSD1963 pin order (EMC pass 4)")
open(DISP, "w", encoding="utf-8").write(s); print("arrays regrouped")
