"""RV3 moved across the K1 contact (owner's decision 2026-11-21, after the surge re-simulation with the RZ relay):
LINE_FUSED (K1 pin 11) to Net-(J4-Pin_1) (K1 pin 14) instead of LINE_FUSED to NEUT; part TVR14431KSU15Y -> Thinking
TVR10471KSY (10 mm, 300 V ac class, V1mA 470 V +-10 %, 2500 A 8/20 us, 70 J), footprint RV_Disc_D12mm_W5.8mm_P7.5mm.

Drawing: the symbol (same UUID) leaves the mains-input group (111.76, 88.9) and stands vertically at (469.9, 392.43) between
the LINE_FUSED wire (y 381.0, pin 1) and the fan wire (y 403.86, pin 2) left of K1, with two junctions; the old stubs and
their junctions go, the split wires are merged again. K1's Reference / Value move above-left of the relay (they sat
where RV3 now stands). The mains-input note loses its RV3 line (the lines below move up one pitch); the fan-relay note
gets two RV3 lines.
    python -I rv3_contact.py <project_dir>          (edits 3dFilamentDryer.kicad_sch in place: use a scratch copy)"""
import os
import re
import sys
import uuid

FIELDS = {
    "Value": "TVR10471KSY",
    "Footprint": "Varistor:RV_Disc_D12mm_W5.8mm_P7.5mm",
    "Datasheet": "https://www.ozdisan.com/p/varistorler-863/thinking-tvr10471ksy-351283",
    "Description": ("VARISTOR DISC 10MM 470V 2.5KA 300VAC 385VDC THT (Thinking TVR10471KSY: V1mA 470 V +-10 %, Vc 775 V @ 25 A, "
                    "2500 A 8/20 us, 70 J 10/1000 us, -40..85 C, UL 1449/1414, VDE, CQC): across the fan-relay K1 contact "
                    "(LINE_FUSED - fan), keeps the open contact below its 1000 Vrms rating in the surge tests (EMC fix 2026-11-21)"),
    "MPN": "TVR10471KSY",
    "Manufacturer": "Thinking",
}
NOTE_RV3 = "RV3 TVR14431KSU15Y (same part) across LINE_FUSED-NEUT: protects the fan relay K1's open contact in a 1 kV surge (1162 V -> 773 V)"
FAN_NEW = [
    "RV3 TVR10471KSY (10 mm, 300 V ac class MOV) across the K1 contact 11-14: keeps the open contact below its 1000 Vrms rating in the surges (596-703 V) and clamps the fan turn-off spike (<= 626 V)",
    "With K1 open RV3 leaks into the fan (below about 0.1 mA peak at 253 V ac, catalog curve, 25 C); a short-circuited disc makes the fan run permanently (the fan limits the current, F3 does not clear)",
]


def wire(a, b):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s)\n\t\t\t(xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)\n' % (a[0], a[1], b[0], b[1], uuid.uuid4()))


def junction(p):
    return ('\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "%s")\n\t)\n' % (p[0], p[1], uuid.uuid4()))


def find_wire(t, a, b):
    pat = r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\)\n\t\t\t\(xy %s %s\)\n[\s\S]*?\n\t\)' % tuple(re.escape(v) for v in (a[0], a[1], b[0], b[1]))
    m = re.search(pat, t)
    if not m:
        pat = r'\n\t\(wire\n\t\t\(pts\n\t\t\t\(xy %s %s\)\n\t\t\t\(xy %s %s\)\n[\s\S]*?\n\t\)' % tuple(re.escape(v) for v in (b[0], b[1], a[0], a[1]))
        m = re.search(pat, t)
    assert m, ("wire", a, b)
    return m


def drop_wire(t, a, b):
    m = find_wire(t, a, b)
    return t[:m.start()] + t[m.end():]


def drop_junction(t, p):
    m = re.search(r'\n\t\(junction\n\t\t\(at %s %s\)\n[\s\S]*?\n\t\)' % (re.escape(p[0]), re.escape(p[1])), t)
    assert m, ("junction", p)
    return t[:m.start()] + t[m.end():]


def text_block(t, s):
    a = t.index('(text "%s"' % s)
    st = a - 2; assert t[st:a] == "\n\t"
    return st, t.index("\n\t)\n", a) + 3


def main(proj):
    p = os.path.join(proj, "3dFilamentDryer.kicad_sch")
    t = open(p, encoding="utf-8", newline="").read()
    crlf = "\r\n" in t
    t = t.replace("\r\n", "\n")
    # 1 the RV3 instance: move, fields
    i = t.index('(property "Reference" "RV3"')
    s = t.rindex("\n\t(symbol\n", 0, i); e = t.index("\n\t)\n", i) + 3
    blk = t[s:e]
    assert "(at 111.76 88.9 0)" in blk
    dx, dy = 469.9 - 111.76, 392.43 - 88.9
    def mv(m):
        x, y = float(m.group(1)) + dx, float(m.group(2)) + dy
        return "(at %s %s %s)" % (("%.2f" % x).rstrip("0").rstrip("."), ("%.2f" % y).rstrip("0").rstrip("."), m.group(3))
    blk = re.sub(r"\(at ([-\d.]+) ([-\d.]+) (\d+)\)", mv, blk)
    # reference / value to the left of the body, right-justified
    blk = re.sub(r'(\(property "Reference" "RV3"\n\t\t\t\(at )[-\d.]+ [-\d.]+ 0\)', r'\g<1>467.36 391.16 0)', blk)
    blk = re.sub(r'(\(property "Value" "[^"]*"\n\t\t\t\(at )[-\d.]+ [-\d.]+ 0\)', r'\g<1>467.36 393.7 0)', blk)
    for prop in ("Reference", "Value"):
        k = blk.index('(property "%s"' % prop); k2 = blk.index("\n\t\t)\n", k)
        sub = blk[k:k2]
        sub = re.sub(r"\(justify left\)", "(justify right)", sub) if "(justify" in sub else sub.replace("\t\t\t\t)\n\t\t\t)", "\t\t\t\t)\n\t\t\t\t(justify right)\n\t\t\t)", 1)
        blk = blk[:k] + sub + blk[k2:]
    for name, val in FIELDS.items():
        blk, n = re.subn(r'(\(property "%s" )"[^"]*"' % name, lambda m: m.group(1) + '"%s"' % val, blk)
        assert n == 1, name
    t = t[:s] + blk + t[e:]
    # 2 old wiring in the mains-input group
    t = drop_wire(t, ("111.76", "76.2"), ("111.76", "85.09"))
    t = drop_wire(t, ("111.76", "92.71"), ("111.76", "101.6"))
    t = drop_junction(t, ("111.76", "76.2")); t = drop_junction(t, ("111.76", "101.6"))
    t = drop_wire(t, ("105.41", "76.2"), ("111.76", "76.2")); t = drop_wire(t, ("111.76", "76.2"), ("119.38", "76.2"))
    t = drop_wire(t, ("83.82", "101.6"), ("111.76", "101.6")); t = drop_wire(t, ("111.76", "101.6"), ("165.1", "101.6"))
    add = wire(("105.41", "76.2"), ("119.38", "76.2")) + wire(("83.82", "101.6"), ("165.1", "101.6"))
    # 3 new wiring in the fan-relay group
    add += wire(("469.9", "381"), ("469.9", "388.62")) + wire(("469.9", "396.24"), ("469.9", "403.86"))
    add += junction(("469.9", "381")) + junction(("469.9", "403.86"))
    k = t.index("\n\t(wire\n"); t = t[:k + 1] + add + t[k + 1:]
    # 4 K1 fields above-left of the relay
    t = t.replace('(property "Reference" "K1"\n\t\t\t(at 469.9 392.43 0)', '(property "Reference" "K1"\n\t\t\t(at 467.36 384.81 0)', 1)
    t = t.replace('(property "Value" "RZ03-1A4-D005"\n\t\t\t(at 469.9 394.97 0)', '(property "Value" "RZ03-1A4-D005"\n\t\t\t(at 467.36 387.35 0)', 1)
    assert "(at 467.36 384.81 0)" in t and "(at 467.36 387.35 0)" in t
    # 5 notes
    st, en = text_block(t, NOTE_RV3)
    t = t[:st] + t[en:]
    for old, new in (("38.1 129.54 0", "38.1 127 0"), ("38.1 132.08 0", "38.1 129.54 0")):
        n = t.count("(at %s)" % old); assert n == 1, (old, n)
        t = t.replace("(at %s)" % old, "(at %s)" % new)
    st, en = text_block(t, "Pick-up (hot coil, datasheet graph): 0.90 Urtd = 4.5 V at 60 C, 0.95 Urtd = 4.75 V at 85 C -> restart guaranteed to 60 C ambient")
    tmpl = t[st:en]; new = ""
    for n, line in enumerate(FAN_NEW):
        b = re.sub(r'\(text "[^"]*"', lambda m: '(text "%s"' % line, tmpl, count=1)
        b = b.replace("(at 440.69 459.74 0)", "(at 440.69 %.2f 0)" % (459.74 + 2.54 * (n + 1)))
        b = re.sub(r'\(uuid "[^"]+"\)', '(uuid "%s")' % uuid.uuid4(), b)
        new += b
    t = t[:en] + new + t[en:]
    if crlf:
        t = t.replace("\n", "\r\n")
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("RV3 -> (469.9, 392.43) across K1 11-14, %s; notes updated" % FIELDS["Value"])


if __name__ == "__main__":
    main(sys.argv[1])
