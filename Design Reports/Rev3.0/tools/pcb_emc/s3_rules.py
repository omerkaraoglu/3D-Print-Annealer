"""Stage 3 rule-file edits: no relay exception left (K1 = TE RZ, 5 kV / 10 mm reinforced, coil 17.8 mm from the contacts).
.kicad_pro: netclass pattern 'unconnected-(K1-Pad4)' removed (the form-A relay has no NC pin).
.kicad_dru: the K1 exclusion group (LINE / LINE_FUSED / K1-Pad4 vs +5V / Net-(D5-A)) removed from mains_to_selv_clearance
and _creepage; K1 removed from same_footprint_pads(_creepage); the k1_pins terms removed from fanout_areas(_creepage);
rules relay_coil_clearance / relay_coil_creepage deleted.  Usage: s3_rules.py in_dir out_dir"""
import os, re, sys
src, dst = sys.argv[1:3]
p = open(os.path.join(src, "3dFilamentDryer.kicad_pro"), encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in p else "\n"
blk = '      {' + nl + '        "netclass": "Mains",' + nl + '        "pattern": "unconnected-(K1-Pad4)"' + nl + '      },' + nl
assert p.count(blk) == 1
p = p.replace(blk, "")
open(os.path.join(dst, "3dFilamentDryer.kicad_pro"), "w", encoding="utf-8", newline="").write(p)
d = open(os.path.join(src, "3dFilamentDryer.kicad_dru"), encoding="utf-8", newline="").read()
excl = (" && !((A.NetName == 'LINE' && (B.NetName == '+5V' || B.NetName == 'Net-(D5-A)')) || (B.NetName == 'LINE' && (A.NetName == '+5V' || A.NetName == 'Net-(D5-A)'))"
        " || (A.NetName == 'LINE_FUSED' && (B.NetName == '+5V' || B.NetName == 'Net-(D5-A)')) || (B.NetName == 'LINE_FUSED' && (A.NetName == '+5V' || A.NetName == 'Net-(D5-A)'))"
        " || (A.NetName == 'unconnected-(K1-Pad4)' && (B.NetName == '+5V' || B.NetName == 'Net-(D5-A)')) || (B.NetName == 'unconnected-(K1-Pad4)' && (A.NetName == '+5V' || A.NetName == 'Net-(D5-A)')))")
assert d.count(excl) == 2, d.count(excl)
d = d.replace(excl, "")
k1 = " || (A.memberOfFootprint('K1') && B.memberOfFootprint('K1'))"
assert d.count(k1) == 2; d = d.replace(k1, "")
for t in (" || (A.insideArea('k1_pins') && B.insideArea('k1_pins'))", "(A.insideArea('k1_pins') && B.insideArea('k1_pins')) || "):
    assert d.count(t) == 1, (t, d.count(t)); d = d.replace(t, "")
m = re.search(r"# relay SRD-05VDC[^\n]*\n\(rule \"relay_coil_clearance\"[\s\S]*?\n\(rule \"relay_coil_creepage\"[\s\S]*?\"\)\)\r?\n", d)
assert m; d = d[:m.start()] + d[m.end():]
d = d.replace("# component-inherent pin spacing (TO-220, DIP-6, relay, wire pads)", "# component-inherent pin spacing (TO-220, DIP-6, wire pads)")
d = d.replace("# fan-out areas next to the TO-220 triac, the relay and the optocouplers", "# fan-out areas next to the TO-220 triac and the optocouplers")
assert "K1" not in d and "k1_pins" not in d and "relay_coil" not in d
open(os.path.join(dst, "3dFilamentDryer.kicad_dru"), "w", encoding="utf-8", newline="").write(d)
print("rules written to", dst)
