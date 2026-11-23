"""Stage 5 (2026-11-23, owner's decision "put the earth connection on the board"): footprint of the single-point
ground-to-earth bond J5, written into Rev3.pretty.

  Rev3:EarthBond_M3_Pad7.0mm_Drill3.2mm
  - one plated through-hole pad "1", circle 7.0 mm on every copper layer (F.Cu / In1 / In2 / B.Cu), drill 3.2 mm, no paste;
    solder mask: front opening = pad + the board's 0.05 mm pad-to-mask clearance (dia 7.1, lug seat); back opening
    dia 5.6 only (screw-head seat), so that the bare back copper keeps the frame document's 1.0 mm from the support-rib
    contact faces (rib 9: 1.11 mm, rib 21: 1.64 mm nominal, >= 1.06 / 1.59 with +-0.05 mm mask registration; frame v2 / GF-2.1 section 1.2). KiCad 10.0.1 stores the solder-mask
    margin per pad, not per side (the padstack's per-side mask properties are neither written in the file nor wrapped in
    pcbnew python), so the pad carries F.Mask only and the back opening is a filled 5.6 mm B.Mask circle in the footprint;
    zone connection solid (zone_connect 2): the pad carries surge / ESD current (about 16 A peak for nanoseconds in the
    earthed-chassis simulations), so no thermal spokes. The In2 (3V3 plane) copper ring stays (remove_unused_layers
    no): the 3V3 plane therefore clears the whole 7.0 mm pad by its zone clearance (anti-pad 7.5 mm), not only the drill.
  - F.CrtYd circle 8.0 mm: lug side (component side). Envelope of the M3 ring-lug ring (<= 6.4 mm), the DIN 125 M3 washer
    (7.0 mm) and the M3 nut (6.0 mm across corners), + 0.5 mm (IPC-7351 courtyard excess, level B).
  - B.CrtYd circle 7.5 mm: screw-head side (frame side). Pad copper 7.0 mm + 0.25 mm; the head (pan / button head,
    ISO 7045 M3, dk <= 5.6 mm, no washer on this side; with 0.2 mm radial hole play its edge reaches r 3.0) stays inside it, so the
    courtyard is not reduced. The head is drawn on B.Fab.
  - F.SilkS: the IEC 60417-5017 earth symbol east of the pad (stem + three bars 2.0 / 1.3 / 0.6 mm, 0.15 mm lines),
    0.75 mm outside the mask opening; the reference is placed on the board by the silk_refdes method (stage5.py).
  - attributes through_hole, exclude_from_pos_files, exclude_from_bom: it is board copper, not a purchased part
    (the symbol J5 on the Thermocouple sheet carries in_bom no / in_pos_files no).

    python stage5_footprint.py <Rev3.pretty dir>
"""
import os
import sys
import uuid

NAME = "EarthBond_M3_Pad7.0mm_Drill3.2mm"
NS = uuid.UUID("5e7a1c2d-0b3f-4e55-9a51-23f1d0e0b005")
_n = [0]


def U():
    _n[0] += 1
    return str(uuid.uuid5(NS, "%s-%d" % (NAME, _n[0])))


def circle(r, layer, w):
    return ('\t(fp_circle (center 0 0) (end %s 0) (stroke (width %s) (type solid)) (fill no) (layer "%s") (uuid "%s"))\n'
            % (r, w, layer, U()))


def line(x0, y0, x1, y1, layer, w):
    return ('\t(fp_line (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (layer "%s") (uuid "%s"))\n'
            % (x0, y0, x1, y1, w, layer, U()))


# earth symbol (IEC 60417-5017), F.SilkS, relative to the pad centre: stem top (5.3, 0.1), bars at y 0.9 / 1.35 / 1.8
EX, EY = 5.3, 0.1
EARTH = [(EX, EY, EX, EY + 0.8), (EX - 1.0, EY + 0.8, EX + 1.0, EY + 0.8), (EX - 0.65, EY + 1.25, EX + 0.65, EY + 1.25),
         (EX - 0.3, EY + 1.7, EX + 0.3, EY + 1.7)]


def build():
    d = ("Single-point bond of the low-voltage ground (GND) to the earthed oven chassis (PE), Rev3.0 stage 5 (2026-11-23). "
         "Plated hole 3.2 mm for an M3 screw, copper pad 7.0 mm on all copper layers, solder mask open dia 7.1 on the front "
         "(lug seat) and dia 5.6 on the back (screw-head seat; keeps 1.0 mm to the frame support ribs), solid "
         "zone connection (surge / ESD current, no thermal spokes). Lug side = F (component side): M3 ring lug directly on the "
         "pad, DIN 125 washer, locking means, M3 nut; screw head on B (ISO 7045 M3 pan head dk <= 5.6, height <= 2.4, no washer "
         "on B). Ring-lug lead to the chassis stud FH9. Board copper: not a BOM item, not in position files.")
    s = '(footprint "%s"\n' % NAME
    s += '\t(version 20240108)\n\t(generator "pcbnew")\n\t(generator_version "8.0")\n\t(layer "F.Cu")\n'
    s += '\t(descr "%s")\n' % d
    s += '\t(tags "earth ground PE chassis bond M3 ring lug screw EMC ESD surge")\n'
    s += ('\t(property "Reference" "J**" (at 0 -5.0 0) (layer "F.SilkS") (uuid "%s") '
          '(effects (font (size 1 1) (thickness 0.15))))\n' % U())
    s += ('\t(property "Value" "PE bond" (at 0 5.0 0) (layer "F.Fab") (hide yes) (uuid "%s") '
          '(effects (font (size 1 1) (thickness 0.15))))\n' % U())
    s += '\t(attr through_hole exclude_from_pos_files exclude_from_bom)\n'
    s += circle(3.5, "F.Fab", 0.1)          # washer 7.0
    s += circle(1.6, "F.Fab", 0.1)          # hole
    s += circle(2.8, "B.Fab", 0.1)          # screw head dk 5.6
    s += circle(4.0, "F.CrtYd", 0.05)
    s += circle(3.75, "B.CrtYd", 0.05)
    s += ('\t(fp_circle (center 0 0) (end 2.8 0) (stroke (width 0) (type solid)) (fill solid) (layer "B.Mask") (uuid "%s"))\n'
          % U())                            # back mask opening dia 5.6 (screw-head seat)
    for x0, y0, x1, y1 in EARTH:
        s += line(round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3), "F.SilkS", 0.15)
    s += ('\t(fp_text user "${REFERENCE}" (at 0 -4.6 0) (layer "F.Fab") (uuid "%s") '
          '(effects (font (size 0.8 0.8) (thickness 0.12))))\n' % U())
    s += ('\t(pad "1" thru_hole circle (at 0 0) (size 7.0 7.0) (drill 3.2) (layers "*.Cu" "F.Mask") '
          '(remove_unused_layers no) (zone_connect 2) (uuid "%s"))\n' % U())
    s += '\t(embedded_fonts no)\n)\n'
    return s


if __name__ == "__main__":
    lib = sys.argv[1]
    p = os.path.join(lib, NAME + ".kicad_mod")
    open(p, "w", encoding="utf-8", newline="\n").write(build())
    print("written", p)
