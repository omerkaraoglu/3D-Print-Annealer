"""Post-process the routed board file: insert the 4-layer stackup block and title block, save as the project board."""
import sys, re
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
stackup = '''		(stackup
			(layer "F.SilkS"
				(type "Top Silk Screen")
			)
			(layer "F.Paste"
				(type "Top Solder Paste")
			)
			(layer "F.Mask"
				(type "Top Solder Mask")
				(color "Green")
				(thickness 0.01)
			)
			(layer "F.Cu"
				(type "copper")
				(thickness 0.035)
			)
			(layer "dielectric 1"
				(type "prepreg")
				(thickness 0.2)
				(material "FR4")
				(epsilon_r 4.4)
				(loss_tangent 0.02)
			)
			(layer "In1.Cu"
				(type "copper")
				(thickness 0.035)
			)
			(layer "dielectric 2"
				(type "core")
				(thickness 1.0)
				(material "FR4")
				(epsilon_r 4.5)
				(loss_tangent 0.02)
			)
			(layer "In2.Cu"
				(type "copper")
				(thickness 0.035)
			)
			(layer "dielectric 3"
				(type "prepreg")
				(thickness 0.2)
				(material "FR4")
				(epsilon_r 4.4)
				(loss_tangent 0.02)
			)
			(layer "B.Cu"
				(type "copper")
				(thickness 0.035)
			)
			(layer "B.Mask"
				(type "Bottom Solder Mask")
				(color "Green")
				(thickness 0.01)
			)
			(layer "B.Paste"
				(type "Bottom Solder Paste")
			)
			(layer "B.SilkS"
				(type "Bottom Silk Screen")
			)
			(copper_finish "ENIG")
			(dielectric_constraints no)
		)
'''
if "(stackup" in s:
    s = re.sub(r"\t\t\(stackup.*?\n\t\t\)\n", stackup, s, count=1, flags=re.S)
else:
    s = s.replace("\t(setup\n", "\t(setup\n" + stackup, 1)
s = re.sub(r"\(general\s*\(thickness [0-9.]+\)", "(general\n\t\t(thickness 1.6)", s, count=1)
# title block
tb = '''	(title_block
		(title "READARK 3D Printer Filament Dryer / Annealer - Controller")
		(date "2026-11-10")
		(rev "3.0")
		(company "READARK")
		(comment 1 "4-layer: F.Cu sig / In1 GND / In2 3V3(+5V island) / B.Cu sig, 1.6 mm FR4, 35 um Cu, ENIG")
		(comment 2 "Mains 230 VAC section above the dashed line (Cmts.User); 6.4 mm creepage/clearance to SELV; slots under U1/U5")
	)
'''
if "(title_block" not in s:
    s = s.replace('\t(paper "A4")\n', '\t(paper "A3")\n' + tb, 1)
open(dst, "w", encoding="utf-8").write(s)
print("finalized ->", dst)
