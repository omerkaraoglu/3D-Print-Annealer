"""K1 relay swap (owner's decision 2026-11-21): SRD-type SPDT (Tianbo HJR-3FF-S-Z-4/05VDC) -> TE Connectivity Schrack
RZ03-1A4-D005 (1 form A, 16 A, AgNi 90/10, 5 V 60 ohm 420 mW coil, 5000 Vrms / >= 10 mm clearance and creepage
coil-contact, reinforced), second source on the same footprint Hongfa HF115FD/005-1H3A(335).

Symbol: project symbol Rev3:Relay_SPST-NO_11-14 = KiCad Relay:Relay_SPST-NO with the contact pins numbered as in the
datasheets (TE RZ p.3 "PCB layout / terminal assignment", EN 50005): A1 / A2 coil, 11 common, 14 NO. Footprint: the
unmodified KiCad Relay_THT:Relay_SPST_Schrack-RT1-16A-FormA_RM5mm, whose pads are already A1 / A2 / 11 (x2) / 14 (x2):
symbol, footprint and datasheet use one numbering, so no Rev3 footprint copy is needed.

The new symbol is placed at K1's position and rotation (482.6, 393.7, 180 deg); its four pins land on the old pins'
wire ends: 11 -> old COM (LINE_FUSED), 14 -> old NO (J4 pin 1), A2 -> old coil pin on +5V, A1 -> old coil pin at
Q4 / D5 (the RZ and HF115FD coils are not polarised). The old NC pin's no-connect flag is removed; the instance UUID
is kept (the board footprint keeps its link). Fields: Value, Footprint, Datasheet (Ozdisan page), Description, MPN,
Manufacturer, plus "MPN2" / "Manufacturer2" for the second source. The fan-control note is rewritten.

    python -I k1_relay.py <project_dir> <Rev3.kicad_sym>       (edits both in place: use scratch copies)"""
import os
import re
import sys
import uuid

KICAD_SYM = r"C:/Program Files/KiCad/10.0/share/kicad/symbols/Relay.kicad_sym"
NEW = "Relay_SPST-NO_11-14"
FP = "Relay_THT:Relay_SPST_Schrack-RT1-16A-FormA_RM5mm"
DESC_LIB = ("Relay SPST-NO, EN 50005 terminal numbers: coil A1 / A2, common 11, NO 14 (TE Schrack RZ / RT1 form A, "
            "Hongfa HF115FD ...-1H)")
FIELDS = {
    "Value": "RZ03-1A4-D005",
    "Footprint": FP,
    "Datasheet": "https://www.ozdisan.com/p/genel-tip-roleler-403/te-connectivity-rz03-1a4-d005-1211236",
    "Description": ("Power relay 1 form A 16 A 250 VAC, AgNi 90/10, 5 VDC coil 60 ohm 420 mW, 5000 Vrms and >= 10/10 mm "
                    "coil-contact (reinforced), RTII flux proof, -40..85 C (TE Schrack RZ03-1A4-D005, 1-1415899-3); "
                    "second source Hongfa HF115FD/005-1H3A(335), same footprint"),
    "MPN": "RZ03-1A4-D005",
    "Manufacturer": "TE Connectivity",
}
EXTRA = {"MPN2": "HF115FD/005-1H3A(335)", "Manufacturer2": "Hongfa"}
NOTE_OLD = ["K1 HJR-3FF-S-Z-4/05VDC (Tianbo; SRD-05 footprint and pinout, SPDT 7 A): COM = LINE_FUSED (after F3 only:",
            "the oven fan needs no filter and its current stays out of L40); NO -> J4 fan lead pads (the fan returns to NEUT), NC unused"]
NOTE_NEW = [
    "K1 TE RZ03-1A4-D005 (alt. Hongfa HF115FD/005-1H3A(335)), 1 form A 16 A, 5 kV / 10 mm reinforced coil-contact: 11 = LINE_FUSED",
    "(after F3 only: the oven fan needs no filter and its current stays out of L40); 14 (NO) -> J4 fan lead pads (fan returns to NEUT)",
    "Coil 60 R +-10 %: 83 mA / 0.42 W at 5 V, worst 97 mA / 0.51 W (5.25 V, 54 R); Q4 IB ~2.4 mA, forced beta ~40: saturated",
    "Pick-up (hot coil, datasheet graph): 0.90 Urtd = 4.5 V at 60 C, 0.95 Urtd = 4.75 V at 85 C -> restart guaranteed to 60 C ambient",
]


def lib_symbol(prefix=""):
    t = open(KICAD_SYM, encoding="utf-8").read()
    i = t.index('\t(symbol "Relay_SPST-NO"')
    j = t.index('\n\t(symbol "', i + 10)
    blk = t[i:j].rstrip()
    blk = blk.replace('(symbol "Relay_SPST-NO_', '(symbol "%s_' % NEW)          # unit sub-symbols first
    blk = blk.replace('(symbol "Relay_SPST-NO"', '(symbol "%s%s"' % (prefix, NEW), 1)
    n = blk.count('(number "13"')
    assert n == 1, n
    blk = blk.replace('(number "13"', '(number "11"')
    blk = blk.replace('(property "Value" "Relay_SPST-NO"', '(property "Value" "%s"' % NEW)
    blk = re.sub(r'\(property "Footprint" ""', '(property "Footprint" "%s"' % FP, blk, count=1)
    blk = blk.replace('"Relay SPST, normally open, EN50005"', '"%s"' % DESC_LIB)
    return blk


def indent(blk, n):
    return "\n".join(("\t" * n + l[1:]) if l.startswith("\t") else l for l in blk.split("\n"))


def prop(name, value, at, hide=True):
    return ('\t\t(property "%s" "%s"\n\t\t\t(at %s)\n%s\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n'
            '\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
            % (name, value, at, "\t\t\t(hide yes)\n" if hide else ""))


def main(proj, symlib):
    sch = os.path.join(proj, "3dFilamentDryer.kicad_sch")
    t = open(sch, encoding="utf-8", newline="").read()
    crlf = "\r\n" in t
    t = t.replace("\r\n", "\n")
    # 1 embedded library symbol: add Rev3:..., drop Relay:SANYOU_SRD_Form_C (K1 was its only user)
    assert t.count('(lib_id "Relay:SANYOU_SRD_Form_C")') == 1
    i = t.index('\t\t(symbol "Relay:SANYOU_SRD_Form_C"')
    j = t.index("\n\t\t)\n", i) + 4
    t = t[:i] + indent(lib_symbol("Rev3:"), 2) + "\n" + t[j:]
    # 2 the instance
    k = t.index('(lib_id "Relay:SANYOU_SRD_Form_C")')
    s = t.rindex("\n\t(symbol\n", 0, k)
    e = t.index("\n\t)\n", k) + 3
    inst = t[s:e]
    assert '(uuid "81bb48ac-068e-47b1-882b-e54ca8f0ed2c")' in inst
    inst = inst.replace('(lib_id "Relay:SANYOU_SRD_Form_C")', '(lib_id "Rev3:%s")' % NEW)
    for name, val in FIELDS.items():
        inst, n = re.subn(r'(\(property "%s" )"[^"]*"' % name, lambda m: m.group(1) + '"%s"' % val, inst)
        assert n == 1, name
    pos = inst.index("\t\t(pin ")
    extra = "".join(prop(n, v, "482.6 393.7 0") for n, v in EXTRA.items())
    inst = inst[:pos] + extra + inst[pos:]
    p0 = inst.index("\t\t(pin "); p1 = inst.index("\t\t(instances")
    pins = "".join('\t\t(pin "%s"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, uuid.uuid4()) for n in ("A1", "A2", "11", "14"))
    inst = inst[:p0] + pins + inst[p1:]
    t = t[:s] + inst + t[e:]
    # 3 no-connect on the old NC pin
    m = re.search(r'\n\t\(no_connect\n\t\t\(at 480\.06 401\.32\)\n\t\t\(uuid "[^"]+"\)\n\t\)', t)
    assert m, "NC flag"
    t = t[:m.start()] + t[m.end():]
    # 4 the note
    blocks = []
    for line in NOTE_OLD:
        a = t.index('(text "%s"' % line)
        s = a - 2; assert t[s:a] == "\n\t"; e = t.index("\n\t)\n", a) + 3
        blocks.append((s, e))
    tmpl = t[blocks[0][0]:blocks[0][1]]
    y0 = float(re.search(r"\(at 440\.69 ([\d.]+) 0\)", tmpl).group(1))
    new = ""
    for n, line in enumerate(NOTE_NEW):
        b = re.sub(r'\(text "[^"]*"', lambda m: '(text "%s"' % line, tmpl, count=1)
        b = re.sub(r"\(at 440\.69 [\d.]+ 0\)", "(at 440.69 %.2f 0)" % (y0 + 2.54 * n), b, count=1)
        b = re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid4(), b)
        new += b
    (s1, e1), (s2, e2) = blocks
    assert e1 <= s2
    t = t[:s1] + new + t[e1:s2] + t[e2:]
    if crlf:
        t = t.replace("\n", "\r\n")
    open(sch, "w", encoding="utf-8", newline="").write(t)
    # 5 the project symbol library
    L = open(symlib, encoding="utf-8", newline="").read()
    lcr = "\r\n" in L
    L = L.replace("\r\n", "\n")
    if '(symbol "%s"' % NEW not in L:
        cut = L.rstrip().rindex(")")
        L = L[:cut].rstrip("\n") + "\n" + lib_symbol() + "\n)\n"
    if lcr:
        L = L.replace("\n", "\r\n")
    open(symlib, "w", encoding="utf-8", newline="").write(L)
    print("K1 -> Rev3:%s / %s; NC flag removed; note %d lines" % (NEW, FIELDS["Value"], len(NOTE_NEW)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
