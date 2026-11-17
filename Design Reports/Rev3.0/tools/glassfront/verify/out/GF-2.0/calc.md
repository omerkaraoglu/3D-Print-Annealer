# Glass-front frame - calculations with section properties measured on the STEP

STEP: `Rev3.0_GlassFront_Frame.step` (2026-11-16 02:01:36, 1586957 bytes, sha256 7831768c26066dc0)

Tags: [M] measured on the STEP, [C] calculated (grillage / formulae), [A] assumed.

Grillage: a copy of the concept's port (`grillage_port.py`); concept_calc.py is not imported or run. Validation against the GF-1.1 concept (S4, glass 3.0): [np.float64(0.1387), np.float64(0.0665), np.float64(0.0662), np.float64(0.0922), np.float64(0.0665)] vs [0.139, 0.067, 0.066, 0.092, 0.067] mm at 50 N -> ok.

## 1. Ring section properties [M]

| section | A mm2 | centroid Z | I mm4 | c mm | Z range |
|---|---|---|---|---|---|
| mid-top (x 80) | 119.6 | -8.911 | 1196 | 8.91 | -14.42 .. 0.00 |
| mid-top (x 103.85, no F5 at GF-2.0) | 119.6 | -8.911 | 1196 | 8.91 | -14.42 .. 0.00 |
| mid-side left (y 60) | 114.8 | -8.900 | 1194 | 8.90 | -14.42 .. 0.00 |
| mid-side right (y 60) | 121.7 | -8.915 | 1198 | 8.91 | -14.42 .. 0.00 |
| near the top-left corner (x 23, past the corner arc and the side shelf) | 120.1 | -8.886 | 1213 | 8.89 | -14.42 .. 0.00 |
| bottom bridge CTP compartment x 60: channel (bridge + flange plate + bottom wall) | 110.0 | -8.585 | 1902 | 12.63 | -14.42 .. 4.05 |
| bottom bridge CTP compartment x 60: bridge only (cut at the bottom-wall inner face y 147.7) | 72.4 | -10.691 | 119 | 3.73 | -14.42 .. -7.92 |
| bottom bridge TFT compartment x 103.85: channel (bridge + flange plate + bottom wall) | 110.0 | -8.585 | 1902 | 12.63 | -14.42 .. 4.05 |
| bottom bridge TFT compartment x 103.85: bridge only (cut at the bottom-wall inner face y 147.7) | 72.4 | -10.691 | 119 | 3.73 | -14.42 .. -7.92 |
| bottom bridge TFT wide part x 150: channel (bridge + flange plate + bottom wall) | 110.0 | -8.585 | 1902 | 12.63 | -14.42 .. 4.05 |
| bottom bridge TFT wide part x 150: bridge only (cut at the bottom-wall inner face y 147.7) | 72.4 | -10.691 | 119 | 3.73 | -14.42 .. -7.92 |
| bottom at the divider rib x 79.92: channel incl. the rib | 424.1 | -4.477 | 8895 | 9.94 | -14.42 .. 4.05 |
| bottom outside the tail span x 24 (corner cell, land 8.19) | 142.4 | -8.245 | 1709 | 8.24 | -14.42 .. 0.00 |
| corner apex: diagonal plane through F1 and the glass corner (incl. pad, tube, rib) | 225.5 | -8.033 | 2659 | 8.03 | -14.42 .. 0.00 |

Concept rectangles at glass 3.0 [C]: top 1232, left 1229, right 1233, bottom channel 2160, bottom bridge only 124 mm4; measured / concept: {'top': 0.971, 'left': 0.971, 'right': 0.971, 'channel': 0.881, 'bridge': 0.953}

## 2. Push (S4 / R4: 4 corner studs + VHB) [C]

| bottom | glass | I | load point | w 50 N mm | lip line 50 N | bottom edge 50 N | glass 250 N MPa | SF | ring 250 N | stud 250 N |
|---|---|---|---|---|---|---|---|---|---|---|
| channel | 1.1 | concept | window centre | 1.2264 | 0.1440 | 0.1385 | 411.7 | 0.61 | 8.2 | -22 |
| channel | 1.1 | concept | glass top edge, mid | 0.1257 | 0.1257 | 0.0125 | 72.5 | 3.45 | 20.9 | -3 |
| channel | 1.1 | concept | glass side edge, mid | 0.1197 | 0.1197 | 0.0209 | 73.1 | 3.42 | 21.6 | -1 |
| channel | 1.1 | concept | bottom border over the bend gap | 0.3115 | 0.1523 | 0.1523 | 302.6 | 0.83 | 17.8 | -7 |
| channel | 1.1 | concept | glass bottom edge, mid | 0.1121 | 0.1121 | 0.1121 | 60.9 | 4.11 | 19.0 | -3 |
| channel | 1.1 | concept | bottom edge over the CTP tail (x 58) | 0.1031 | 0.1031 | 0.1031 | 60.5 | 4.13 | 20.3 | 0 |
| channel | 1.1 | meas. | window centre | 1.2281 | 0.1444 | 0.1400 | 411.7 | 0.61 | 8.4 | -23 |
| channel | 1.1 | meas. | glass top edge, mid | 0.1264 | 0.1264 | 0.0126 | 73.1 | 3.42 | 21.3 | -3 |
| channel | 1.1 | meas. | glass side edge, mid | 0.1204 | 0.1204 | 0.0211 | 73.7 | 3.39 | 22.0 | -1 |
| channel | 1.1 | meas. | bottom border over the bend gap | 0.3148 | 0.1552 | 0.1552 | 303.4 | 0.82 | 19.1 | -7 |
| channel | 1.1 | meas. | glass bottom edge, mid | 0.1147 | 0.1147 | 0.1147 | 63.0 | 3.97 | 20.8 | -3 |
| channel | 1.1 | meas. | bottom edge over the CTP tail (x 58) | 0.1063 | 0.1063 | 0.1063 | 63.0 | 3.97 | 22.0 | -1 |
| channel | 2.0 | concept | window centre | 0.3204 | 0.0670 | 0.0649 | 137.1 | 1.82 | 3.8 | -16 |
| channel | 2.0 | concept | glass top edge, mid | 0.0848 | 0.0848 | 0.0097 | 38.8 | 6.44 | 15.5 | -3 |
| channel | 2.0 | concept | glass side edge, mid | 0.0844 | 0.0844 | 0.0150 | 40.6 | 6.15 | 16.1 | -1 |
| channel | 2.0 | concept | bottom border over the bend gap | 0.1217 | 0.0835 | 0.0835 | 112.1 | 2.23 | 11.0 | -6 |
| channel | 2.0 | concept | glass bottom edge, mid | 0.0772 | 0.0772 | 0.0772 | 31.3 | 7.99 | 14.9 | -3 |
| channel | 2.0 | concept | bottom edge over the CTP tail (x 58) | 0.0734 | 0.0734 | 0.0734 | 30.9 | 8.09 | 16.0 | 5 |
| channel | 2.0 | meas. | window centre | 0.3209 | 0.0671 | 0.0654 | 137.1 | 1.82 | 3.9 | -16 |
| channel | 2.0 | meas. | glass top edge, mid | 0.0852 | 0.0852 | 0.0098 | 39.5 | 6.33 | 15.8 | -3 |
| channel | 2.0 | meas. | glass side edge, mid | 0.0848 | 0.0848 | 0.0151 | 41.3 | 6.06 | 16.4 | -1 |
| channel | 2.0 | meas. | bottom border over the bend gap | 0.1230 | 0.0849 | 0.0849 | 112.1 | 2.23 | 11.8 | -6 |
| channel | 2.0 | meas. | glass bottom edge, mid | 0.0787 | 0.0787 | 0.0787 | 32.4 | 7.71 | 16.2 | -3 |
| channel | 2.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0753 | 0.0753 | 0.0753 | 32.1 | 7.78 | 17.3 | 4 |
| channel | 3.0 | concept | window centre | 0.1220 | 0.0396 | 0.0387 | 62.9 | 1.91 | 2.3 | -12 |
| channel | 3.0 | concept | glass top edge, mid | 0.0658 | 0.0658 | 0.0076 | 39.1 | 3.07 | 11.0 | -4 |
| channel | 3.0 | concept | glass side edge, mid | 0.0646 | 0.0646 | 0.0131 | 41.5 | 2.89 | 11.6 | 1 |
| channel | 3.0 | concept | bottom border over the bend gap | 0.0692 | 0.0597 | 0.0597 | 50.1 | 2.40 | 7.7 | -6 |
| channel | 3.0 | concept | glass bottom edge, mid | 0.0619 | 0.0619 | 0.0619 | 29.4 | 4.08 | 11.5 | -4 |
| channel | 3.0 | concept | bottom edge over the CTP tail (x 58) | 0.0579 | 0.0579 | 0.0579 | 31.4 | 3.82 | 12.3 | 14 |
| channel | 3.0 | meas. | window centre | 0.1222 | 0.0397 | 0.0390 | 62.9 | 1.91 | 2.4 | -12 |
| channel | 3.0 | meas. | glass top edge, mid | 0.0660 | 0.0660 | 0.0077 | 39.6 | 3.03 | 11.2 | -4 |
| channel | 3.0 | meas. | glass side edge, mid | 0.0649 | 0.0649 | 0.0132 | 42.0 | 2.86 | 11.9 | 1 |
| channel | 3.0 | meas. | bottom border over the bend gap | 0.0698 | 0.0605 | 0.0605 | 49.9 | 2.41 | 8.3 | -6 |
| channel | 3.0 | meas. | glass bottom edge, mid | 0.0628 | 0.0628 | 0.0628 | 31.4 | 3.82 | 12.6 | -4 |
| channel | 3.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0591 | 0.0591 | 0.0591 | 33.5 | 3.58 | 13.4 | 12 |
| channel | 4.0 | concept | window centre | 0.0649 | 0.0297 | 0.0292 | 35.6 | 3.37 | 1.7 | -8 |
| channel | 4.0 | concept | glass top edge, mid | 0.0538 | 0.0538 | 0.0071 | 34.8 | 3.45 | 7.7 | -3 |
| channel | 4.0 | concept | glass side edge, mid | 0.0504 | 0.0504 | 0.0133 | 36.9 | 3.25 | 8.2 | 11 |
| channel | 4.0 | concept | bottom border over the bend gap | 0.0503 | 0.0482 | 0.0482 | 30.3 | 3.97 | 5.7 | -3 |
| channel | 4.0 | concept | glass bottom edge, mid | 0.0518 | 0.0518 | 0.0518 | 28.4 | 4.23 | 8.7 | -2 |
| channel | 4.0 | concept | bottom edge over the CTP tail (x 58) | 0.0472 | 0.0472 | 0.0472 | 29.8 | 4.03 | 9.2 | 23 |
| channel | 4.0 | meas. | window centre | 0.0651 | 0.0298 | 0.0294 | 35.6 | 3.37 | 1.8 | -8 |
| channel | 4.0 | meas. | glass top edge, mid | 0.0540 | 0.0540 | 0.0071 | 35.2 | 3.41 | 7.8 | -3 |
| channel | 4.0 | meas. | glass side edge, mid | 0.0505 | 0.0505 | 0.0133 | 37.3 | 3.22 | 8.3 | 11 |
| channel | 4.0 | meas. | bottom border over the bend gap | 0.0507 | 0.0487 | 0.0487 | 30.7 | 3.91 | 5.9 | -4 |
| channel | 4.0 | meas. | glass bottom edge, mid | 0.0524 | 0.0524 | 0.0524 | 30.0 | 4.01 | 9.2 | -2 |
| channel | 4.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0479 | 0.0479 | 0.0479 | 31.4 | 3.82 | 9.7 | 22 |
| bridge | 1.1 | concept | window centre | 1.2529 | 0.1652 | 0.1652 | 412.2 | 0.61 | 6.9 | -20 |
| bridge | 1.1 | concept | glass top edge, mid | 0.1259 | 0.1259 | 0.0142 | 72.4 | 3.45 | 20.9 | -3 |
| bridge | 1.1 | concept | glass side edge, mid | 0.1206 | 0.1206 | 0.0274 | 73.4 | 3.40 | 21.5 | -0 |
| bridge | 1.1 | concept | bottom border over the bend gap | 0.3953 | 0.2298 | 0.2298 | 315.9 | 0.79 | 25.7 | -7 |
| bridge | 1.1 | concept | glass bottom edge, mid | 0.1927 | 0.1927 | 0.1927 | 163.3 | 1.53 | 40.9 | -3 |
| bridge | 1.1 | concept | bottom edge over the CTP tail (x 58) | 0.1830 | 0.1830 | 0.1830 | 163.9 | 1.53 | 41.0 | -1 |
| bridge | 1.1 | meas. | window centre | 1.2533 | 0.1653 | 0.1653 | 412.2 | 0.61 | 6.9 | -20 |
| bridge | 1.1 | meas. | glass top edge, mid | 0.1266 | 0.1266 | 0.0142 | 73.0 | 3.43 | 21.3 | -3 |
| bridge | 1.1 | meas. | glass side edge, mid | 0.1212 | 0.1212 | 0.0274 | 74.0 | 3.38 | 21.9 | -0 |
| bridge | 1.1 | meas. | bottom border over the bend gap | 0.3959 | 0.2306 | 0.2306 | 315.7 | 0.79 | 26.1 | -7 |
| bridge | 1.1 | meas. | glass bottom edge, mid | 0.1936 | 0.1936 | 0.1936 | 165.1 | 1.51 | 41.7 | -3 |
| bridge | 1.1 | meas. | bottom edge over the CTP tail (x 58) | 0.1839 | 0.1839 | 0.1839 | 165.7 | 1.51 | 41.8 | -1 |
| bridge | 2.0 | concept | window centre | 0.3252 | 0.0716 | 0.0716 | 137.1 | 1.82 | 3.1 | -16 |
| bridge | 2.0 | concept | glass top edge, mid | 0.0849 | 0.0849 | 0.0104 | 38.8 | 6.44 | 15.5 | -3 |
| bridge | 2.0 | concept | glass side edge, mid | 0.0846 | 0.0846 | 0.0177 | 40.6 | 6.15 | 16.2 | -1 |
| bridge | 2.0 | concept | bottom border over the bend gap | 0.1440 | 0.1096 | 0.1096 | 106.7 | 2.34 | 10.4 | -6 |
| bridge | 2.0 | concept | glass bottom edge, mid | 0.1107 | 0.1107 | 0.1107 | 123.6 | 2.02 | 20.2 | -3 |
| bridge | 2.0 | concept | bottom edge over the CTP tail (x 58) | 0.1086 | 0.1086 | 0.1086 | 125.3 | 2.00 | 20.4 | -1 |
| bridge | 2.0 | meas. | window centre | 0.3254 | 0.0717 | 0.0717 | 137.1 | 1.82 | 3.1 | -16 |
| bridge | 2.0 | meas. | glass top edge, mid | 0.0853 | 0.0853 | 0.0104 | 39.5 | 6.32 | 15.8 | -3 |
| bridge | 2.0 | meas. | glass side edge, mid | 0.0850 | 0.0850 | 0.0177 | 41.3 | 6.06 | 16.4 | -1 |
| bridge | 2.0 | meas. | bottom border over the bend gap | 0.1441 | 0.1098 | 0.1098 | 106.6 | 2.34 | 10.5 | -6 |
| bridge | 2.0 | meas. | glass bottom edge, mid | 0.1110 | 0.1110 | 0.1110 | 125.1 | 2.00 | 20.4 | -3 |
| bridge | 2.0 | meas. | bottom edge over the CTP tail (x 58) | 0.1089 | 0.1089 | 0.1089 | 126.7 | 1.97 | 20.7 | -1 |
| bridge | 3.0 | concept | window centre | 0.1236 | 0.0413 | 0.0413 | 62.9 | 1.91 | 1.9 | -12 |
| bridge | 3.0 | concept | glass top edge, mid | 0.0659 | 0.0659 | 0.0080 | 39.1 | 3.07 | 11.0 | -4 |
| bridge | 3.0 | concept | glass side edge, mid | 0.0648 | 0.0648 | 0.0145 | 41.4 | 2.90 | 11.6 | 0 |
| bridge | 3.0 | concept | bottom border over the bend gap | 0.0772 | 0.0698 | 0.0698 | 56.1 | 2.14 | 4.9 | -6 |
| bridge | 3.0 | concept | glass bottom edge, mid | 0.0755 | 0.0755 | 0.0755 | 82.1 | 1.46 | 9.7 | -4 |
| bridge | 3.0 | concept | bottom edge over the CTP tail (x 58) | 0.0736 | 0.0736 | 0.0736 | 84.7 | 1.42 | 10.0 | 3 |
| bridge | 3.0 | meas. | window centre | 0.1236 | 0.0414 | 0.0414 | 62.9 | 1.91 | 1.9 | -12 |
| bridge | 3.0 | meas. | glass top edge, mid | 0.0661 | 0.0661 | 0.0080 | 39.6 | 3.03 | 11.2 | -4 |
| bridge | 3.0 | meas. | glass side edge, mid | 0.0650 | 0.0650 | 0.0145 | 42.0 | 2.86 | 11.8 | 0 |
| bridge | 3.0 | meas. | bottom border over the bend gap | 0.0772 | 0.0698 | 0.0698 | 56.2 | 2.13 | 4.9 | -6 |
| bridge | 3.0 | meas. | glass bottom edge, mid | 0.0755 | 0.0755 | 0.0755 | 82.7 | 1.45 | 9.8 | -4 |
| bridge | 3.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0737 | 0.0737 | 0.0737 | 85.3 | 1.41 | 10.1 | 3 |
| bridge | 4.0 | concept | window centre | 0.0657 | 0.0307 | 0.0307 | 35.6 | 3.38 | 1.3 | -8 |
| bridge | 4.0 | concept | glass top edge, mid | 0.0539 | 0.0539 | 0.0074 | 34.8 | 3.45 | 7.7 | -3 |
| bridge | 4.0 | concept | glass side edge, mid | 0.0505 | 0.0505 | 0.0140 | 36.9 | 3.25 | 8.2 | 11 |
| bridge | 4.0 | concept | bottom border over the bend gap | 0.0540 | 0.0529 | 0.0529 | 36.4 | 3.30 | 2.8 | -5 |
| bridge | 4.0 | concept | glass bottom edge, mid | 0.0580 | 0.0580 | 0.0580 | 56.5 | 2.12 | 5.4 | -3 |
| bridge | 4.0 | concept | bottom edge over the CTP tail (x 58) | 0.0546 | 0.0546 | 0.0546 | 58.5 | 2.05 | 5.6 | 16 |
| bridge | 4.0 | meas. | window centre | 0.0658 | 0.0307 | 0.0307 | 35.6 | 3.38 | 1.3 | -8 |
| bridge | 4.0 | meas. | glass top edge, mid | 0.0540 | 0.0540 | 0.0074 | 35.2 | 3.41 | 7.8 | -3 |
| bridge | 4.0 | meas. | glass side edge, mid | 0.0506 | 0.0506 | 0.0140 | 37.3 | 3.22 | 8.3 | 11 |
| bridge | 4.0 | meas. | bottom border over the bend gap | 0.0541 | 0.0529 | 0.0529 | 36.5 | 3.29 | 2.9 | -5 |
| bridge | 4.0 | meas. | glass bottom edge, mid | 0.0580 | 0.0580 | 0.0580 | 56.8 | 2.11 | 5.5 | -3 |
| bridge | 4.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0546 | 0.0546 | 0.0546 | 58.8 | 2.04 | 5.6 | 16 |

one ring section per edge; J and the corner links as the concept; glass characteristic strength per glass_t from the params (1.1/2.0 CS 250 MPa, 3.0/4.0 tempered 120 MPa); no panel / LOCA / PCB credit

## 3. 0.5 J impact (concept method, estimates) [C]

| bottom bound / glass | glass g | window centre SF | bend-gap strip, whole border free SF | strip only SF |
|---|---|---|---|---|
| channel 1.1 | 64 | 1.07 | 0.81 | 1.41 |
| channel 2.0 | 116 | 1.81 | 1.67 | 3.09 |
| channel 3.0 | 174 | 1.21 | 1.39 | 2.78 |
| channel 4.0 | 233 | 1.58 | 2.15 | 4.65 |
| bridge 1.1 | 64 | 1.08 | 0.90 | 1.56 |
| bridge 2.0 | 116 | 1.83 | 1.80 | 3.32 |
| bridge 3.0 | 174 | 1.22 | 1.46 | 2.91 |
| bridge 4.0 | 233 | 1.58 | 2.22 | 4.79 |

## 4. Bead [C]

- area 2386.6 mm2 (params 2386.6; GF-1.1 2486.7); dead load 3.67 N -> 1.54 kPa; 250 N pull 0.105 MPa mean
- bead corner radius from the glass centre 109.18 (GF-1.1 111.7)

| case | d mm | ext. at t 0.73 | ext. at t 1.0 | allow class 50 t 0.73 | allow class 25 t 1.0 |
|---|---|---|---|---|---|
| design 50 ppm/K, +70 C | 0.224 | 4.6 % | 2.5 % | 0.816 | 0.750 |
| bound 70 ppm/K, +70 C | 0.333 | 9.9 % | 5.4 % | 0.816 | 0.750 |
| design 50 ppm/K, -20 C | 0.179 | 3.0 % | 1.6 % | 0.816 | 0.750 |
| bound 70 ppm/K, -20 C | 0.266 | 6.5 % | 3.5 % | 0.816 | 0.750 |
| design + 0.1 % moisture, +70 C | 0.333 | 9.9 % | 5.4 % | 0.816 | 0.750 |
| bound + 0.3 % moisture, +70 C | 0.661 | 34.9 % | 19.8 % | 0.816 | 0.750 |

## 5. Gaps (STEP lip, params glass / cut-out; sides / corner min / diagonal) [M + C]

| g2 | nominal | glass +0.1/side, R nominal (requested +-0.1, R +0.2/-0) | glass profile +0.2 (offset outline) | glass +0.2/side and R -0.2 (size + radius tolerances) | glass nominal size, R -0.2 | glass +0.2/side, R nominal (R +0.2/-0 callout) |
|---|---||---|---||---|---||---|---||---|---||---|---|
| 20 C | 0.394 / 0.395 / 0.497 | 0.294 / 0.295 / 0.356 | 0.194 / 0.195 / 0.297 | 0.191 / 0.131 / 0.132 | 0.394 / 0.394 / 0.414 | 0.194 / 0.194 / 0.214 |
| -20 C, 50 ppm | 0.238 / 0.238 / 0.320 | 0.138 / 0.137 / 0.178 | 0.038 / 0.038 / 0.120 | 0.034 / -0.049 / -0.046 | 0.238 / 0.228 / 0.237 | 0.038 / 0.028 / 0.037 |
| +70 C frame/glass, +50 C sheet, 50 ppm | 0.520 / 0.520 / 0.718 | 0.420 / 0.420 / 0.577 | 0.320 / 0.320 / 0.519 | 0.316 / 0.316 / 0.354 | 0.520 / 0.520 / 0.636 | 0.320 / 0.320 / 0.436 |
| -20 C, 70 ppm | 0.162 / 0.161 / 0.233 | 0.062 / 0.059 / 0.092 | -0.038 / -0.040 / 0.033 | -0.042 / -0.138 / -0.133 | 0.162 / 0.140 / 0.151 | -0.038 / -0.060 / -0.050 |
| +70 C frame/glass, +50 C sheet, 70 ppm | 0.581 / 0.581 / 0.826 | 0.481 / 0.481 / 0.685 | 0.382 / 0.382 / 0.627 | 0.378 / 0.378 / 0.462 | 0.581 / 0.581 / 0.744 | 0.382 / 0.382 / 0.544 |

| g1 | nominal | cut-out profile -0.1, lip +0.04 | cut-out -0.1/side and R +0.1, lip +0.04 | cut-out -0.1/side, R nominal (R +0/-0.2 callout), lip +0.04 |
|---|---||---|---||---|---||---|---|
| 20 C | 0.412 / 0.418 / 0.516 | 0.272 / 0.278 / 0.376 | 0.272 / 0.273 / 0.293 | 0.272 / 0.275 / 0.335 |
| -20 C, 50 ppm | 0.508 / 0.513 / 0.683 | 0.367 / 0.373 / 0.543 | 0.367 / 0.369 / 0.460 | 0.367 / 0.371 / 0.502 |
| +70 C frame/glass, +50 C sheet, 50 ppm | 0.204 / 0.209 / 0.281 | 0.064 / 0.070 / 0.141 | 0.064 / 0.048 / 0.058 | 0.064 / 0.067 / 0.100 |
| -20 C, 70 ppm | 0.558 / 0.564 / 0.771 | 0.418 / 0.423 / 0.631 | 0.418 / 0.419 / 0.548 | 0.418 / 0.421 / 0.589 |
| +70 C frame/glass, +50 C sheet, 70 ppm | 0.107 / 0.112 / 0.171 | -0.033 / -0.028 / 0.031 | -0.033 / -0.064 / -0.051 | -0.033 / -0.034 / -0.010 |

Formula (nominal per side) GF-2.0 vs GF-1.1: {"50 ppm/K, -20 C": {"GF-2.0 g2 / g1": [0.2438, 0.4951], "GF-1.1 g2 / g1": [0.2512, 0.5114], "change g2 / g1": [-0.0074, -0.0163]}, "50 ppm/K, +70 C frame / +50 C sheet": {"GF-2.0 g2 / g1": [0.5254, 0.1932], "GF-1.1 g2 / g1": [0.5474, 0.2028], "change g2 / g1": [-0.022, -0.0096]}, "70 ppm/K, -20 C": {"GF-2.0 g2 / g1": [0.1676, 0.5451], "GF-1.1 g2 / g1": [0.1786, 0.5701], "change g2 / g1": [-0.011, -0.025]}, "70 ppm/K, +70 C frame / +50 C sheet": {"GF-2.0 g2 / g1": [0.5865, 0.0966], "GF-1.1 g2 / g1": [0.6193, 0.1107], "change g2 / g1": [-0.0328, -0.0141]}}

## 6. Tape and fasteners [C]

- tape 7603.2 mm2 (GF-1.1 7903); module 7.63 N -> 1.00 kPa; 250 N -> 32.9 kPa; thermal shear [28.9, 42.5] % of the 1.0 gap (50 / 70 ppm)
- studs at r 128.43: radial move [0.244, 0.372] mm (50 / 70 ppm, +70 / +50 C) vs float 1.20; stud reaction at 250 N max 12 N; M4 washer at 500 N [6.2, 7.6] MPa

## 7. Bend zone (nose, pocket face, break): criterion and measured clearances [M + C + A]

Criterion (params `tail_clearance_criteria.bend_zone`, lead decision 2026-11-16): >= 0.45 with the panel at its RSS position (+0.308), > 0.0 at the worst case (panel +0.60, exit Z +-0.3, tail +0.05). Panel position contributors: {'panel outline vs AA (DS, concept 0.2)': 0.2, 'J1: AA aligned to the print window (concept 0.1)': 0.1, "print window vs glass edge (params drawing_tolerances.print 'print-to-edge +-0.2')": 0.2, 'J2: glass centred in the recess (graded shims, design doc 9.3)': 0.05, 'frame: bridge face (B core) vs recess wall (A core), core shift [A]': 0.05}.

| tail | nominal | panel at RSS | WC (all) | WC (panel position only) | WC with print-to-edge +-0.1 | feature |
|---|---|---|---|---|---|---|
| TFT | 1.524 | 1.271 | 0.824 | 1.037 | 0.906 | bridge nose R1.5 |
| CTP | 0.946 | 0.654 | 0.239 | 0.382 | 0.334 | bridge nose R1.5 |

g_bend budget (concept form): l0 0.50 + R_in 1.50 + t 0.30 + clearance 0.45 + panel position RSS 0.308 = **3.058** (modelled 3.00); border 18.5 holds up to g_bend 3.090 (bezel 9.51 + land 5.9) -> reserve **0.032** (with the concept's 0.25: 0.090).

g_bend that would give the concept's 0.45 at the worst case: {"TFT": {"slope_per_mm": 0.8, "g_bend_for_0.45_at_WC_all_contributors": 3.0, "g_bend_for_0.45_at_WC_panel_position_only": 3.0}, "CTP": {"slope_per_mm": 0.933, "g_bend_for_0.45_at_WC_all_contributors": 3.226, "g_bend_for_0.45_at_WC_panel_position_only": 3.073}}

## 7b. Bend-gap tolerance stack, linear estimate from the panel +0.35 case [C + A]

- TFT: nominal 1.524 to the bridge; sensitivity 0.82 per mm of panel shift; panel position WC 0.60 / RSS 0.31 (concept 0.35 / 0.25); exit Z +-0.3 costs 0.159 -> clearance WC 0.822, RSS 1.221 (concept budget 1.187)
- CTP: nominal 0.946 to the bridge; sensitivity 0.94 per mm of panel shift; panel position WC 0.60 / RSS 0.31 (concept 0.35 / 0.25); exit Z +-0.3 costs 0.088 -> clearance WC 0.241, RSS 0.638 (concept budget 0.565)

## 8. Volume and mass [M]

- STEP volume **83.481 cm3**, mass **113.5 g** at 1.36 g/cm3 (params as modelled 83.4819; GF-1.1 82.188 cm3 / 111.8 g; v2 55.06 cm3 / 74.9 g)
