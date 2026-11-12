"""Footprint for the Core Master RC1415U radial inductor (L40, pass 3): Core Master spec HX8817022 for RC1415U-101K gives
A 16.5 max (dia), B 17.0 max (height), C 15 +/-3 (lead length), D 1.0 ref (lead dia), E 7.5 ref (pitch).
Derived from the pass-1 L_Radial_D22.5mm_P9.00mm file (same structure): pads +/-3.75, drill 1.3, pad 2.4 mm (mains THT: drill + 1.1)."""
import re, uuid
LIB = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/ComponentsLibrary/User Created/Rev3/Rev3.pretty/"
s = open(LIB + "L_Radial_D22.5mm_P9.00mm.kicad_mod", encoding="utf-8").read()
s = s.replace('(footprint "L_Radial_D22.5mm_P9.00mm"', '(footprint "L_Radial_CoreMaster_RC1415U"')
s = s.replace('Radial inductor D22.5 mm, pitch 9.00 mm (ozdisan IND-120UH-THT); pad/drill sized for 0.8 mm leads',
              'Radial inductor Core Master RC1415U (D16.5 x H17 mm, pitch 7.5 mm, leads 1.0 mm; spec HX8817022 for RC1415U-101K 100 uH 5 A); drill 1.3, pad 2.4')
for old, new in (("-13.5", "-10.5"), ("13.5", "10.5")):
    s = s.replace("(at 0 %s)" % old, "(at 0 %s)" % new)
s = s.replace("(end 11.25 0)", "(end 8.25 0)").replace("(end 11.75 0)", "(end 8.75 0)")
s = s.replace("(at -4.5 0)", "(at -3.75 0)").replace("(at 4.5 0)", "(at 3.75 0)")
s = s.replace("(size 2.2 2.2)", "(size 2.4 2.4)").replace("(drill 1.2)", "(drill 1.3)")
s = re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda m: '(uuid "%s")' % uuid.uuid4(), s)
assert s.count("8.25") >= 1 and s.count("3.75") >= 2 and "(drill 1.3)" in s, "template changed"
open(LIB + "L_Radial_CoreMaster_RC1415U.kicad_mod", "w", encoding="utf-8").write(s); print("footprint written")
