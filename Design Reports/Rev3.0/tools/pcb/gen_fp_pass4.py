"""Pass-4 footprints (top-side FPC connectors, upper contact) into Rev3.pretty, built with the pass-1 helpers of gen_footprints.py.
Pad numbering is MIRRORED relative to the connector's physical terminal numbering: with the panel tail hanging straight down past
the flush bottom edges and folded once around the PCB's bottom edge onto the top side, the panel's conductor 1 lands on the
terminal that is physically "pin N" of an upper-contact connector. Keeping the schematic symbol in panel pin numbers (pin k =
panel conductor k) therefore needs pad "1" at the +x end (entry side facing -y / the board edge when placed with rot 0).
- Connfly DS1020-09-40VBT1B: same land pattern as the VBT1A drawing C-DS1020-09-XXXXX-E used in pass 1 (pads 0.30 x 1.80 on
  0.50, anchors 2.50 x 3.20); the A/B versions share the housing -> ASSUMED same land pattern, to be confirmed on the Connfly
  drawing's product-code legend before fabrication.
- KLS L-KLS1-242D-1.2-06-T-U-R: KLS drawing KLS1-242D-1.2 (2018-03-10, pages 1 upper / 2 lower contact, identical PCB layout):
  pads 0.30 x 1.25 on 0.50 pitch, anchors 2.00 x 2.45 with their top edge 2.00 below the signal-pad top edge and centred 2.54
  outside the end pads; body 0.50(N+1)+5.5 wide, 4.10 deep, 1.2 high; FPC 0.30 mm, reinforcement >= 3.20 mm."""
import sys, os, importlib.util
TOOLS = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb"
spec = importlib.util.spec_from_file_location("gen_footprints", os.path.join(TOOLS, "gen_footprints.py"))
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)          # also regenerates the pass-1 footprints (same output)
header, smdpad, rect, line, text, write = g.header, g.smdpad, g.rect, g.line, g.text, g.write

def connfly_B(N):
    name = f"Connfly_DS1020-09-{N:02d}VBT1B_1x{N:02d}_P0.5mm_Horizontal_TopSide"
    D = 5.75 if N >= 35 else 5.2
    W = 0.5 * N + 5.6
    ysig = -D / 2
    yanc = -D / 2 + 1.9
    xanc = (N - 1) / 4 + 0.7 + 1.25
    s = header(name, f"Connfly DS1020-09-{N:02d}VBT1B, 0.5 mm pitch {N}-pin FPC connector, right-angle SMT, UPPER contact, flip lock; land pattern as the VBT1A drawing C-DS1020-09-XXXXX-E (pads 0.30x1.80 on 0.50 pitch, anchors 2.50x3.20) - assumed shared by the B version; pad numbers mirrored (pad 1 at +x) so the panel-numbered symbol fits the top-side wrap-around tail; body 0.5N+5.6 x {D} mm", "connector fpc ffc 0.5mm connfly upper contact", "smd")
    s += text("reference", "REF**", 0, -D / 2 - 2.4, "F.SilkS")
    s += text("value", name, 0, D / 2 + 1.6, "F.Fab")
    s += text("user", "${REFERENCE}", 0, 0.6, "F.Fab", 0.8, 0.12)
    for i in range(N):
        x = (N - 1) / 4 - 0.5 * i                     # mirrored: pad 1 at +x
        s += smdpad(str(i + 1), x, ysig, 0.3, 1.8, "roundrect", 0.25)
    s += smdpad("MP", -xanc, yanc, 2.5, 3.2, "rect")
    s += smdpad("MP", xanc, yanc, 2.5, 3.2, "rect")
    s += rect(-W / 2, -D / 2, W / 2, D / 2, "F.Fab", 0.1)
    s += line(W / 2 - 1, D / 2, W / 2, D / 2 - 1, "F.Fab", 0.1)           # pin-1 corner chamfer at +x
    s += line(-W / 2 - 0.1, D / 2 + 0.1, W / 2 + 0.1, D / 2 + 0.1, "F.SilkS", 0.12)
    s += line(-W / 2 - 0.1, D / 2 + 0.1, -W / 2 - 0.1, yanc + 1.6 + 0.3, "F.SilkS", 0.12)
    s += line(W / 2 + 0.1, D / 2 + 0.1, W / 2 + 0.1, yanc + 1.6 + 0.3, "F.SilkS", 0.12)
    x1 = (N - 1) / 4
    s += line(x1 + 0.45, ysig - 0.9 - 0.3, x1 + 0.45, ysig - 0.9 - 0.3 - 0.8, "F.SilkS", 0.15)   # pin-1 mark at +x
    cx = max(W / 2, xanc + 1.25) + 0.5
    s += rect(-cx, ysig - 0.9 - 0.5, cx, D / 2 + 0.5, "F.CrtYd", 0.05)
    write(name, s)

def kls_242D(N):
    name = f"KLS_L-KLS1-242D-1.2-{N:02d}-T-U-R_1x{N:02d}_P0.5mm_Horizontal_TopSide"
    W = 0.5 * (N + 1) + 5.5
    D = 4.10
    ysig = -D / 2                                   # signal pads at the rear edge, body extends toward +y (FPC entry at +y)
    yanc = ysig - 0.625 + 2.0 + 2.45 / 2            # anchor top edge 2.00 below the signal-pad top edge
    xanc = (N - 1) / 4 + 2.54
    s = header(name, f"KLS L-KLS1-242D-1.2-{N:02d}-T-U-R, 0.5 mm pitch {N}-pin FPC connector, SMT, H 1.2 mm, UPPER contact, ZIF; KLS drawing KLS1-242D-1.2: pads 0.30x1.25 on 0.50, anchors 2.00x2.45 at 2.54 outside the end pads, body {W:.1f} x {D} mm; pad numbers mirrored (pad 1 at +x) for the top-side wrap-around tail", "connector fpc ffc 0.5mm kls upper contact", "smd")
    s += text("reference", "REF**", 0, ysig - 2.2, "F.SilkS")
    s += text("value", name, 0, D / 2 + 1.6, "F.Fab")
    s += text("user", "${REFERENCE}", 0, 0.6, "F.Fab", 0.8, 0.12)
    for i in range(N):
        x = (N - 1) / 4 - 0.5 * i
        s += smdpad(str(i + 1), x, ysig, 0.3, 1.25, "roundrect", 0.25)
    s += smdpad("MP", -xanc, yanc, 2.0, 2.45, "rect")
    s += smdpad("MP", xanc, yanc, 2.0, 2.45, "rect")
    s += rect(-W / 2, -D / 2, W / 2, D / 2, "F.Fab", 0.1)
    s += line(W / 2 - 1, D / 2, W / 2, D / 2 - 1, "F.Fab", 0.1)
    s += line(-W / 2 - 0.1, D / 2 + 0.1, W / 2 + 0.1, D / 2 + 0.1, "F.SilkS", 0.12)
    s += line(-W / 2 - 0.1, D / 2 + 0.1, -W / 2 - 0.1, yanc + 2.45 / 2 + 0.3, "F.SilkS", 0.12)
    s += line(W / 2 + 0.1, D / 2 + 0.1, W / 2 + 0.1, yanc + 2.45 / 2 + 0.3, "F.SilkS", 0.12)
    x1 = (N - 1) / 4
    s += line(x1 + 0.45, ysig - 0.625 - 0.3, x1 + 0.45, ysig - 0.625 - 0.3 - 0.8, "F.SilkS", 0.15)
    cx = max(W / 2, xanc + 1.0) + 0.5
    s += rect(-cx, ysig - 0.625 - 0.5, cx, D / 2 + 0.5, "F.CrtYd", 0.05)
    write(name, s)

connfly_B(40); kls_242D(6); print("pass-4 connector footprints written")
