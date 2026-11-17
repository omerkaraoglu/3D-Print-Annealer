# Glass-front frame - numbers the concept relies on, measured on the STEP

STEP: `Rev3.0_GlassFront_Frame.step` (2026-11-15 17:29:54, 1747323 bytes, sha256 47742d2f5ad0235d)

## Ring section properties (I about the in-plane axis along the edge, through the section centroid)

Concept 5.4 grillage: concept.md quotes I = 1174 mm4 (first-draft value); concept_calc.py with the GF-1.0 parameters computes I = 1222 mm4 (A 104.6 mm2, centroid Z -8.82, c 8.82) on the glass edge for glass 3.0 - that is the value its grillage uses and the reference below.

| section | A mm2 | centroid Z | I mm4 | I / concept | c mm | Z range |
|---|---|---|---|---|---|---|
| mid-top (x 80) | 108.3 | -8.884 | 1190 | 0.97 | 8.88 | -14.42 .. 0.00 |
| mid-top through F5 (x 103.85) | 106.8 | -8.390 | 1053 | 0.86 | 8.39 | -14.42 .. 0.00 |
| mid-side left (y 60) | 103.5 | -8.871 | 1187 | 0.97 | 8.87 | -14.42 .. 0.00 |
| mid-side right (y 60) | 110.5 | -8.889 | 1191 | 0.97 | 8.89 | -14.42 .. 0.00 |
| mid-bottom over the tail pocket (x 80), beam + land plate + flange | 103.2 | -8.493 | 1878 | 1.54 | 12.54 | -14.42 .. 4.05 |
| mid-bottom (x 80) incl. the free shelf strip | 109.6 | -8.194 | 2040 | 1.67 | 12.24 | -14.42 .. 4.05 |
| near the top-left corner (x 23, past the corner arc and the side shelf) | 108.9 | -8.857 | 1206 | 0.99 | 8.86 | -14.42 .. 0.00 |
| bottom beside the tail pocket, corner cell (x 25) | 196.3 | -8.475 | 1753 | 1.44 | 8.47 | -14.42 .. 0.00 |
| corner apex: diagonal plane through F1 and the glass corner (incl. pad, tube, rib) | 166.6 | -8.395 | 2034 | 1.66 | 8.39 | -14.42 .. 0.00 |

## Push grillage (concept_calc.grillage, S4/R4 + VHB, glass 3.0) with the measured I

| run | load point | w @ 5 N um | w @ 50 N mm | lip line @ 50 N mm | glass @ 250 N MPa | ring @ 250 N MPa | stud @ 250 N |
|---|---|---|---|---|---|---|---|
| concept (I 1222) | window centre | 13.9 | 0.1387 | 0.0451 | 64.1 | 2.2 | -14 |
| concept (I 1222) | glass top edge, mid | 6.7 | 0.0665 | 0.0665 | 39.3 | 11.0 | -4 |
| concept (I 1222) | glass side edge, mid | 6.6 | 0.0662 | 0.0662 | 40.4 | 11.3 | -2 |
| concept (I 1222) | chin centre (over tail pocket) | 9.2 | 0.0922 | 0.0597 | 56.5 | 4.5 | -9 |
| concept (I 1222) | glass bottom edge, mid | 6.7 | 0.0665 | 0.0665 | 39.4 | 11.0 | -4 |
| measured min of mid-top / F5 slot / mid-side / near corner (I 1053) | window centre | 13.9 | 0.1391 | 0.0454 | 64.1 | 2.3 | -14 |
| measured min of mid-top / F5 slot / mid-side / near corner (I 1053) | glass top edge, mid | 6.7 | 0.0675 | 0.0675 | 42.1 | 11.9 | -4 |
| measured min of mid-top / F5 slot / mid-side / near corner (I 1053) | glass side edge, mid | 6.7 | 0.0672 | 0.0672 | 43.2 | 12.1 | -3 |
| measured min of mid-top / F5 slot / mid-side / near corner (I 1053) | chin centre (over tail pocket) | 9.3 | 0.0926 | 0.0603 | 56.4 | 4.7 | -9 |
| measured min of mid-top / F5 slot / mid-side / near corner (I 1053) | glass bottom edge, mid | 6.8 | 0.0675 | 0.0675 | 42.2 | 11.9 | -4 |
| measured mid-top (x 80) (I 1190) | window centre | 13.9 | 0.1388 | 0.0452 | 64.1 | 2.2 | -14 |
| measured mid-top (x 80) (I 1190) | glass top edge, mid | 6.7 | 0.0667 | 0.0667 | 39.8 | 11.2 | -4 |
| measured mid-top (x 80) (I 1190) | glass side edge, mid | 6.6 | 0.0664 | 0.0664 | 40.9 | 11.5 | -2 |
| measured mid-top (x 80) (I 1190) | chin centre (over tail pocket) | 9.2 | 0.0922 | 0.0598 | 56.5 | 4.5 | -9 |
| measured mid-top (x 80) (I 1190) | glass bottom edge, mid | 6.7 | 0.0667 | 0.0667 | 39.9 | 11.2 | -4 |
| measured mid-side left (y 60) (I 1187) | window centre | 13.9 | 0.1388 | 0.0452 | 64.1 | 2.2 | -14 |
| measured mid-side left (y 60) (I 1187) | glass top edge, mid | 6.7 | 0.0667 | 0.0667 | 39.9 | 11.2 | -4 |
| measured mid-side left (y 60) (I 1187) | glass side edge, mid | 6.6 | 0.0664 | 0.0664 | 40.9 | 11.5 | -2 |
| measured mid-side left (y 60) (I 1187) | chin centre (over tail pocket) | 9.2 | 0.0923 | 0.0598 | 56.5 | 4.5 | -9 |
| measured mid-side left (y 60) (I 1187) | glass bottom edge, mid | 6.7 | 0.0667 | 0.0667 | 39.9 | 11.2 | -4 |

only I (and the outer-fibre distance c) of the ring replaced; J, the corner links, VHB and E as the concept

## Bead and land

- bead ring 0.9..4.9 inside the glass edge (R6.25 glass corners): **2486.7 mm2** (concept 2510)
- 8 pips inside the bead line: 14.14 mm2 of pip footprint
- land face on the STEP (Z_LAND): 5404.0 mm2

## Volume and mass

- STEP volume **82.188 cm3**, mass **111.8 g** at 1.36 g/cm3 (concept estimate ~70 cm3 / ~95 g; v2 55.06 cm3 / 74.9 g)
