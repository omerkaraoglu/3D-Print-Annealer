"""Stage 5 (2026-11-23, owner's decision "put the earth connection on the board"): the single-point ground-to-earth bond
J5 on the Thermocouple sheet.

J5 = Connector:Conn_01x01_Pin (one pin, like the wire pads J3 / J4 = Connector:Conn_01x02_Pin on the root sheet), value
"PE bond", footprint Rev3:EarthBond_M3_Pad7.0mm_Drill3.2mm, in_bom no / in_pos_files no / on_board yes (board copper,
not a purchased part). Pin 1 on GND through a 5.08 mm stub to one GND symbol (#PWR0418, next free number of the sheet,
unique across the five sheet files). A four-line note under it, first line naming the group (house rulebook).

Why the Thermocouple sheet: the pad sits beside J20 on the board, the thermocouple front end is the circuit whose
behaviour depends on the bond (inputs 0.30-0.58 V, no 50 Hz ripple, needs an insulated-junction probe), and the sheet
has free room next to its input group; the root sheet's free room is far from the mains-input group of J3 / J4.

Placement (A3 sheet): J5 at (63.5, 182.88), pin end (68.58, 182.88), stub to the GND symbol at (73.66, 182.88); the
group sits 20 mm below the thermocouple-input note (last line y 160.02), left-aligned with it (x 55.88), and keeps
> 25 mm from the cold-junction group (x >= 180). Embedded library symbol copied verbatim from KiCad 10's
Connector.kicad_sym (no lib_symbol_mismatch).

    python -I stage5_j5.py <project_dir>      (edits Rev3_Thermocouple.kicad_sch in place: use a scratch copy)
"""
import os
import re
import sys
import uuid

SHEET = "Rev3_Thermocouple.kicad_sch"
KLIB = r"C:/Program Files/KiCad/10.0/share/kicad/symbols/Connector.kicad_sym"
INST = "/ea3996f2-7d6b-4a86-86ab-4ed62213f41f/3a0f6c2e-0001-4c3e-9b1e-000000000002"
NS = uuid.UUID("5e7a1c2d-0b3f-4e55-9a51-23f1d0e0b5c5")
_n = [0]


def U():
    _n[0] += 1
    return str(uuid.uuid5(NS, "J5-%d" % _n[0]))


X, Y = 63.5, 182.88          # J5 origin
PX = X + 5.08                # pin end
GX = PX + 5.08               # GND symbol
FIELDS = [
    ("Footprint", "Rev3:EarthBond_M3_Pad7.0mm_Drill3.2mm"),
    ("Datasheet", ""),
    ("Description", "Single-point bond of the low-voltage ground (GND) to the earthed oven chassis (PE): 7.0 mm plated pad "
                    "for an M3 screw, ring-lug lead to the chassis stud FH9 (board copper, not a purchased part)"),
]
NOTE = [
    "Ground-to-earth bond: J5 = single-point bond of the low-voltage ground (GND) to chassis earth (PE)",
    "M3 screw in the 7 mm plated pad by J20, ring-lug lead to the chassis stud FH9 (about 22 mm)",
    "Board copper, not a purchased part: not in the BOM or the position file (owner's decision 2026-11-23)",
    "Needs an insulated-junction probe TC1; TC inputs then 0.30-0.58 V, no 50 Hz ripple (spec 12.12.8)",
]
NOTE_X, NOTE_Y0 = 55.88, 193.04


def f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def eff(just=None, hide=False):
    h = "\t\t\t(hide yes)\n" if hide else ""
    j = "\t\t\t\t(justify %s)\n" % just if just else ""
    return (h + "\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n"
            "\t\t\t\t)\n" + j + "\t\t\t)\n")


def prop(name, val, x, y, just=None, hide=False):
    return '\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n%s\t\t)\n' % (name, val, f(x), f(y), eff(just, hide))


def lib_symbol():
    t = open(KLIB, encoding="utf-8").read().replace("\r\n", "\n")
    i = t.index('\t(symbol "Conn_01x01_Pin"\n')
    d = 0
    j = i + 1
    while True:
        c = t[j]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                break
        j += 1
    blk = t[i:j + 1].replace('(symbol "Conn_01x01_Pin"', '(symbol "Connector:Conn_01x01_Pin"', 1)
    return "\n".join("\t" + ln for ln in blk.split("\n")) + "\n"


def j5_symbol():
    s = ('\t(symbol\n\t\t(lib_id "Connector:Conn_01x01_Pin")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n'
         '\t\t(exclude_from_sim no)\n\t\t(in_bom no)\n\t\t(on_board yes)\n\t\t(in_pos_files no)\n\t\t(dnp no)\n'
         '\t\t(uuid "%s")\n' % (f(X), f(Y), U()))
    s += prop("Reference", "J5", X - 2.54, Y - 1.27, just="right")
    s += prop("Value", "PE bond", X - 2.54, Y + 1.27, just="right")
    for k, v in FIELDS:
        s += prop(k, v, X, Y, hide=True)
    s += '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n' % U()
    s += ('\t\t(instances\n\t\t\t(project "3dFilamentDryer"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "J5")\n'
          '\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % INST)
    return s


def gnd_symbol(ref):
    s = ('\t(symbol\n\t\t(lib_id "power:GND")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n'
         '\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n'
         '\t\t(uuid "%s")\n' % (f(GX), f(Y), U()))
    s += prop("Reference", ref, GX, Y + 6.35, hide=True)
    s += prop("Value", "GND", GX, Y + 3.81)
    s += prop("Footprint", "", GX, Y, hide=True)
    s += prop("Datasheet", "", GX, Y, hide=True)
    s += prop("Description", 'Power symbol creates a global label with name \\"GND\\" , ground', GX, Y, hide=True)
    s += '\t\t(pin "1"\n\t\t\t(uuid "%s")\n\t\t)\n' % U()
    s += ('\t\t(instances\n\t\t\t(project "3dFilamentDryer"\n\t\t\t\t(path "%s"\n\t\t\t\t\t(reference "%s")\n'
          '\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (INST, ref))
    return s


def wire(a, b):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s)\n\t\t\t(xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)\n' % (f(a[0]), f(a[1]), f(b[0]), f(b[1]), U()))


def text(s, x, y):
    return ('\t(text "%s"\n\t\t(exclude_from_sim no)\n\t\t(at %s %s 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
            '\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n' % (s, f(x), f(y), U()))


def main(proj):
    p = os.path.join(proj, SHEET)
    t = open(p, encoding="utf-8", newline="").read()
    crlf = "\r\n" in t
    t = t.replace("\r\n", "\n")
    assert '(reference "J5")' not in t and '"Connector:Conn_01x01_Pin"' not in t
    used = set()
    for fn in os.listdir(proj):
        if fn.endswith(".kicad_sch"):
            used |= set(re.findall(r'\(reference "(#PWR\d+)"\)', open(os.path.join(proj, fn), encoding="utf-8").read()))
    ref = "#PWR0418"
    assert ref not in used, ref
    # 1 embedded library symbol, alphabetically first in lib_symbols (before Connector:Screw_Terminal_01x02)
    k = t.index("\t(lib_symbols\n") + len("\t(lib_symbols\n")
    assert t[k:].startswith('\t\t(symbol "Connector:Screw_Terminal_01x02"')
    t = t[:k] + lib_symbol() + t[k:]
    # 2 wires (with the other wires), symbols and texts (before sheet_instances / embedded_fonts at the end)
    k = t.index("\n\t(wire\n") + 1
    t = t[:k] + wire((PX, Y), (GX, Y)) + t[k:]
    k = t.index("\n\t(text ") + 1
    t = t[:k] + "".join(text(s, NOTE_X, NOTE_Y0 + 2.54 * n) for n, s in enumerate(NOTE)) + t[k:]
    k = t.index("\n\t(symbol\n") + 1
    t = t[:k] + j5_symbol() + gnd_symbol(ref) + t[k:]
    if crlf:
        t = t.replace("\n", "\r\n")
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("J5 'PE bond' at (%s, %s) on %s, GND %s at (%s, %s), note %d lines" % (f(X), f(Y), SHEET, ref, f(GX), f(Y), len(NOTE)))


if __name__ == "__main__":
    main(sys.argv[1])
