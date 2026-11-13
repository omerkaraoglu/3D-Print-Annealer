"""Write Rev3.pretty/TFT7_SAT070AT40D21_Mech.kicad_mod (no pads, mechanical only).

Library frame = the panel's FRONT view (KiCad y down), origin = outline centre.
The footprint is meant for the PCB's B side (flip left/right in KiCad): the
flip mirrors x, so the board view then shows the panel's BACK view, which is
what the PCB top side looks at.  Dwgs.User: outline, active area, cover-glass
view area, tail-loop envelopes below the bottom edge; Cmts.User: notes.
Attributes: board_only (not in schematic), exclude_from_pos_files,
exclude_from_bom, allow_missing_courtyard.
Run with the CadQuery venv (imports the panel constants from the model script).
"""
import itertools, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tft7_sat070at40d21 as t

LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    r"..\..\..\..\KiCad\ComponentsLibrary\User Created\Rev3\Rev3.pretty"))
NAME = "TFT7_SAT070AT40D21_Mech"
MODEL = t.MODEL_PATH_FMT % "TFT7_SAT070AT40D21"


_COUNTER = itertools.count()


def u():
    """Deterministic UUIDs so that re-running the script does not churn the file."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "%s/%d" % (NAME, next(_COUNTER))))


def rect(x0, y0, x1, y1, layer, w=0.1):
    return ('\t(fp_rect (start %.3f %.3f) (end %.3f %.3f) (stroke (width %.2f) (type solid)) (fill no) '
            '(layer "%s") (uuid "%s"))\n' % (x0, y0, x1, y1, w, layer, u()))


def text(s, x, y, layer, size=1.0):
    return ('\t(fp_text user "%s" (at %.3f %.3f 0) (layer "%s") (uuid "%s") '
            '(effects (font (size %.2f %.2f) (thickness %.2f)) (justify left)))\n'
            % (s, x, y, layer, u(), size, size, size * 0.15))


def fv(r):
    """front-view rect (left, top, w, h) -> footprint coords (y down)."""
    l, tp, w, h = r
    return (-t.L_OUT / 2 + l, -t.H_OUT / 2 + tp, -t.L_OUT / 2 + l + w, -t.H_OUT / 2 + tp + h)


def main():
    m = t.build()            # also yields the solved tail geometry
    hx, hy = t.L_OUT / 2, t.H_OUT / 2
    s = []
    s.append('(footprint "%s"\n\t(version 20240108)\n\t(generator "pcbnew")\n\t(generator_version "8.0")\n'
             '\t(layer "F.Cu")\n' % NAME)
    s.append('\t(descr "SATOZ SAT070AT40D21Y0-35100T071KN 7in 800x480 TFT + GT911 CTP, mechanical only (no pads). '
             'Library view = panel FRONT view, origin = 164.9 x 100 outline centre; place on B.Cu (flip left/right) '
             'with the panel back on the PCB back. Outline 164.90 x 100.00, LCM 3.34 + CTP 1.98 = 5.32 thick; '
             'A.A. 154.08 x 85.92 (4.03 / 4.87 from left / top); cover VA 155.08 x 86.92 (3.53 left, 8.85 bottom). '
             'Tails: TFT 40p 67.65 long, fingers 19.02..39.52 from the left end; CTP 6p 50 long, fingers 40 from the right end '
             '(front view). Sources: SAT spec V.2 sheet 16/18, Fannal CT0476-V2.0")\n')
    s.append('\t(tags "display TFT 7inch mechanical")\n')
    s.append('\t(property "Reference" "DS1" (at 0 %.2f 0) (layer "F.SilkS") (hide yes) (uuid "%s") '
             '(effects (font (size 1 1) (thickness 0.15))))\n' % (-hy - 2, u()))
    s.append('\t(property "Value" "SAT070AT40D21_Mech" (at 0 %.2f 0) (layer "F.Fab") (uuid "%s") '
             '(effects (font (size 1 1) (thickness 0.15))))\n' % (-hy - 4, u()))
    s.append('\t(property "Datasheet" "Datasheets/SAT070AT40D21Y0-35100T071KN (7in TFT + GT911 CTP).pdf" (at 0 0 0) '
             '(layer "F.Fab") (hide yes) (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))\n' % u())
    s.append('\t(property "Description" "7in TFT panel envelope for the frame design (not a BOM item)" (at 0 0 0) '
             '(layer "F.Fab") (hide yes) (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))\n' % u())
    s.append('\t(attr board_only exclude_from_pos_files exclude_from_bom allow_missing_courtyard)\n')
    s.append(rect(-hx, -hy, hx, hy, "Dwgs.User", 0.15))
    s.append(rect(*fv(t.AA), "Dwgs.User", 0.1))
    s.append(rect(*fv(t.VA), "Dwgs.User", 0.05))
    # tail loop envelopes (below the bottom edge; front-view X, y down)
    for name, tail in (("tft", t.TFT_TAIL), ("ctp", t.CTP_TAIL)):
        g = m.geo[name]
        xs = [t.u_to_X(tail, v) for sg in tail["segs"] for v in sg[2:]]
        s.append(rect(min(xs), hy, max(xs), hy + g["loop_bottom_below_board_edge"] + t.TAIL_T, "Dwgs.User", 0.1))
        fx = g["finger_centre_X"]
        half = 10.25 if name == "tft" else 1.75
        s.append(rect(fx - half, hy - 1.0, fx + half, hy, "Dwgs.User", 0.1))
    s.append(text("SAT070AT40D21 outline 164.90 x 100.00 (front view; place on B side)", -hx + 2, -hy + 2, "Cmts.User"))
    s.append(text("A.A. 154.08 x 85.92", -hx + 6, -hy + 7, "Cmts.User"))
    s.append(text("TFT tail loop: %.1f below edge" % m.geo["tft"]["loop_bottom_below_board_edge"],
                  t.u_to_X(t.TFT_TAIL, 20), hy + 3, "Cmts.User", 0.8))
    s.append(text("CTP tail loop: %.1f below edge" % m.geo["ctp"]["loop_bottom_below_board_edge"],
                  t.u_to_X(t.CTP_TAIL, 55), hy + 3, "Cmts.User", 0.8))
    s.append('\t(model "%s"\n\t\t(offset (xyz 0 0 0))\n\t\t(scale (xyz 1 1 1))\n\t\t(rotate (xyz 0 0 0))\n\t)\n' % MODEL)
    s.append(')\n')
    p = os.path.join(LIB, NAME + ".kicad_mod")
    open(p, "w", encoding="utf-8", newline="\n").write("".join(s))
    print("wrote", p)


if __name__ == "__main__":
    main()
