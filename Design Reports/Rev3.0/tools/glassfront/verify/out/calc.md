# Glass-front frame - calculations with section properties measured on the STEP

STEP: `Rev3.0_GlassFront_Frame.step` (2026-11-16 11:53:36, 1585816 bytes, sha256 d734683ac0c0058a)

Tags: [M] measured on the STEP, [C] calculated (grillage / formulae), [A] assumed.

Grillage: a copy of the concept's port (`grillage_port.py`); concept_calc.py is not imported or run. Validation against the GF-1.1 concept (S4, glass 3.0): [np.float64(0.1387), np.float64(0.0665), np.float64(0.0662), np.float64(0.0922), np.float64(0.0665)] vs [0.139, 0.067, 0.066, 0.092, 0.067] mm at 50 N -> ok.

## 1. Ring section properties [M]

| section | A mm2 | centroid Z | I mm4 | c mm | Z range |
|---|---|---|---|---|---|
| mid-top (x 80) | 120.8 | -8.913 | 1197 | 8.91 | -14.42 .. 0.00 |
| mid-top (x 103.85, no F5 at GF-2.0) | 120.8 | -8.913 | 1197 | 8.91 | -14.42 .. 0.00 |
| mid-side left (y 60) | 116.0 | -8.903 | 1194 | 8.90 | -14.42 .. 0.00 |
| mid-side right (y 60) | 123.0 | -8.918 | 1198 | 8.92 | -14.42 .. 0.00 |
| near the top-left corner (x 23, past the corner arc and the side shelf) | 121.4 | -8.889 | 1214 | 8.89 | -14.42 .. 0.00 |
| bottom bridge CTP compartment x 60: channel (bridge + flange plate + bottom wall) | 109.4 | -8.559 | 1894 | 12.61 | -14.42 .. 4.05 |
| bottom bridge CTP compartment x 60: bridge only (cut at the bottom-wall inner face y 147.7) | 71.8 | -10.668 | 120 | 3.75 | -14.42 .. -7.92 |
| bottom bridge TFT compartment x 103.85: channel (bridge + flange plate + bottom wall) | 109.4 | -8.559 | 1894 | 12.61 | -14.42 .. 4.05 |
| bottom bridge TFT compartment x 103.85: bridge only (cut at the bottom-wall inner face y 147.7) | 71.8 | -10.668 | 120 | 3.75 | -14.42 .. -7.92 |
| bottom bridge TFT wide part x 150: channel (bridge + flange plate + bottom wall) | 109.4 | -8.559 | 1894 | 12.61 | -14.42 .. 4.05 |
| bottom bridge TFT wide part x 150: bridge only (cut at the bottom-wall inner face y 147.7) | 71.8 | -10.668 | 120 | 3.75 | -14.42 .. -7.92 |
| bottom at the divider rib x 79.92: channel incl. the rib | 420.7 | -4.456 | 8823 | 9.96 | -14.42 .. 4.05 |
| bottom outside the tail span x 24 (corner cell, land 8.69) | 142.4 | -8.228 | 1700 | 8.23 | -14.42 .. 0.00 |
| corner apex: diagonal plane through F1 and the glass corner (incl. pad, tube, rib) | 229.0 | -8.016 | 2694 | 8.02 | -14.42 .. 0.00 |

Concept rectangles at glass 3.0 [C]: top 1233, left 1230, right 1234, bottom channel 2150, bottom bridge only 126 mm4; measured / concept: {'top': 0.971, 'left': 0.971, 'right': 0.971, 'channel': 0.881, 'bridge': 0.946}

## 2. Push (S4 / R4: 4 corner studs + VHB) [C]

| bottom | glass | I | load point | w 50 N mm | lip line 50 N | bottom edge 50 N | glass 250 N MPa | SF | ring 250 N | stud 250 N |
|---|---|---|---|---|---|---|---|---|---|---|
| channel | 1.1 | concept | window centre | 1.2424 | 0.1443 | 0.1391 | 411.6 | 0.61 | 8.1 | -22 |
| channel | 1.1 | concept | glass top edge, mid | 0.1257 | 0.1257 | 0.0124 | 72.2 | 3.46 | 20.9 | -3 |
| channel | 1.1 | concept | glass side edge, mid | 0.1198 | 0.1198 | 0.0207 | 72.9 | 3.43 | 21.5 | -1 |
| channel | 1.1 | concept | bottom border over the bend gap | 0.2556 | 0.1457 | 0.1457 | 278.2 | 0.90 | 18.3 | -6 |
| channel | 1.1 | concept | glass bottom edge, mid | 0.1123 | 0.1123 | 0.1123 | 61.4 | 4.07 | 19.0 | -3 |
| channel | 1.1 | concept | bottom edge over the CTP tail (x 58) | 0.1034 | 0.1034 | 0.1034 | 61.2 | 4.08 | 20.3 | -0 |
| channel | 1.1 | meas. | window centre | 1.2440 | 0.1447 | 0.1406 | 411.6 | 0.61 | 8.4 | -23 |
| channel | 1.1 | meas. | glass top edge, mid | 0.1264 | 0.1264 | 0.0125 | 72.9 | 3.43 | 21.3 | -3 |
| channel | 1.1 | meas. | glass side edge, mid | 0.1205 | 0.1205 | 0.0209 | 73.5 | 3.40 | 21.9 | -1 |
| channel | 1.1 | meas. | bottom border over the bend gap | 0.2589 | 0.1486 | 0.1486 | 279.2 | 0.90 | 19.8 | -6 |
| channel | 1.1 | meas. | glass bottom edge, mid | 0.1149 | 0.1149 | 0.1149 | 63.6 | 3.93 | 20.8 | -3 |
| channel | 1.1 | meas. | bottom edge over the CTP tail (x 58) | 0.1066 | 0.1066 | 0.1066 | 63.8 | 3.92 | 22.0 | -1 |
| channel | 2.0 | concept | window centre | 0.3243 | 0.0671 | 0.0651 | 137.0 | 1.82 | 3.8 | -16 |
| channel | 2.0 | concept | glass top edge, mid | 0.0848 | 0.0848 | 0.0097 | 38.8 | 6.44 | 15.5 | -3 |
| channel | 2.0 | concept | glass side edge, mid | 0.0844 | 0.0844 | 0.0148 | 40.5 | 6.17 | 16.1 | -1 |
| channel | 2.0 | concept | bottom border over the bend gap | 0.1092 | 0.0828 | 0.0828 | 107.4 | 2.33 | 11.8 | -6 |
| channel | 2.0 | concept | glass bottom edge, mid | 0.0772 | 0.0772 | 0.0772 | 31.4 | 7.96 | 14.9 | -3 |
| channel | 2.0 | concept | bottom edge over the CTP tail (x 58) | 0.0735 | 0.0735 | 0.0735 | 31.0 | 8.05 | 16.0 | 5 |
| channel | 2.0 | meas. | window centre | 0.3247 | 0.0672 | 0.0656 | 137.0 | 1.82 | 3.9 | -16 |
| channel | 2.0 | meas. | glass top edge, mid | 0.0852 | 0.0852 | 0.0097 | 39.5 | 6.33 | 15.8 | -3 |
| channel | 2.0 | meas. | glass side edge, mid | 0.0848 | 0.0848 | 0.0150 | 41.2 | 6.07 | 16.4 | -1 |
| channel | 2.0 | meas. | bottom border over the bend gap | 0.1106 | 0.0842 | 0.0842 | 107.5 | 2.33 | 12.6 | -6 |
| channel | 2.0 | meas. | glass bottom edge, mid | 0.0788 | 0.0788 | 0.0788 | 32.5 | 7.69 | 16.2 | -3 |
| channel | 2.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0755 | 0.0755 | 0.0755 | 32.3 | 7.74 | 17.3 | 3 |
| channel | 3.0 | concept | window centre | 0.1233 | 0.0396 | 0.0387 | 62.9 | 1.91 | 2.3 | -12 |
| channel | 3.0 | concept | glass top edge, mid | 0.0658 | 0.0658 | 0.0075 | 39.0 | 3.07 | 11.0 | -4 |
| channel | 3.0 | concept | glass side edge, mid | 0.0648 | 0.0648 | 0.0129 | 41.4 | 2.90 | 11.6 | 1 |
| channel | 3.0 | concept | bottom border over the bend gap | 0.0665 | 0.0604 | 0.0604 | 48.4 | 2.48 | 8.3 | -6 |
| channel | 3.0 | concept | glass bottom edge, mid | 0.0619 | 0.0619 | 0.0619 | 29.5 | 4.07 | 11.6 | -4 |
| channel | 3.0 | concept | bottom edge over the CTP tail (x 58) | 0.0580 | 0.0580 | 0.0580 | 31.6 | 3.80 | 12.4 | 13 |
| channel | 3.0 | meas. | window centre | 0.1235 | 0.0397 | 0.0390 | 62.9 | 1.91 | 2.4 | -12 |
| channel | 3.0 | meas. | glass top edge, mid | 0.0660 | 0.0660 | 0.0076 | 39.6 | 3.03 | 11.2 | -4 |
| channel | 3.0 | meas. | glass side edge, mid | 0.0650 | 0.0650 | 0.0130 | 41.9 | 2.86 | 11.8 | 0 |
| channel | 3.0 | meas. | bottom border over the bend gap | 0.0672 | 0.0612 | 0.0612 | 48.2 | 2.49 | 9.0 | -6 |
| channel | 3.0 | meas. | glass bottom edge, mid | 0.0628 | 0.0628 | 0.0628 | 31.6 | 3.80 | 12.6 | -4 |
| channel | 3.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0592 | 0.0592 | 0.0592 | 33.7 | 3.56 | 13.5 | 12 |
| channel | 4.0 | concept | window centre | 0.0655 | 0.0297 | 0.0292 | 35.6 | 3.37 | 1.7 | -8 |
| channel | 4.0 | concept | glass top edge, mid | 0.0539 | 0.0539 | 0.0070 | 34.8 | 3.45 | 7.7 | -3 |
| channel | 4.0 | concept | glass side edge, mid | 0.0505 | 0.0505 | 0.0131 | 36.9 | 3.26 | 8.2 | 11 |
| channel | 4.0 | concept | bottom border over the bend gap | 0.0501 | 0.0491 | 0.0491 | 29.3 | 4.10 | 6.2 | -3 |
| channel | 4.0 | concept | glass bottom edge, mid | 0.0519 | 0.0519 | 0.0519 | 28.6 | 4.20 | 8.8 | -2 |
| channel | 4.0 | concept | bottom edge over the CTP tail (x 58) | 0.0473 | 0.0473 | 0.0473 | 30.0 | 4.00 | 9.2 | 23 |
| channel | 4.0 | meas. | window centre | 0.0656 | 0.0297 | 0.0293 | 35.6 | 3.37 | 1.8 | -8 |
| channel | 4.0 | meas. | glass top edge, mid | 0.0540 | 0.0540 | 0.0071 | 35.1 | 3.42 | 7.8 | -3 |
| channel | 4.0 | meas. | glass side edge, mid | 0.0506 | 0.0506 | 0.0132 | 37.2 | 3.22 | 8.3 | 11 |
| channel | 4.0 | meas. | bottom border over the bend gap | 0.0505 | 0.0496 | 0.0496 | 29.9 | 4.02 | 6.4 | -4 |
| channel | 4.0 | meas. | glass bottom edge, mid | 0.0524 | 0.0524 | 0.0524 | 30.2 | 3.97 | 9.3 | -3 |
| channel | 4.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0480 | 0.0480 | 0.0480 | 31.7 | 3.79 | 9.7 | 22 |
| bridge | 1.1 | concept | window centre | 1.2682 | 0.1654 | 0.1654 | 412.0 | 0.61 | 6.8 | -20 |
| bridge | 1.1 | concept | glass top edge, mid | 0.1259 | 0.1259 | 0.0140 | 72.1 | 3.47 | 20.9 | -3 |
| bridge | 1.1 | concept | glass side edge, mid | 0.1206 | 0.1206 | 0.0272 | 73.2 | 3.42 | 21.5 | -0 |
| bridge | 1.1 | concept | bottom border over the bend gap | 0.3405 | 0.2252 | 0.2252 | 301.1 | 0.83 | 29.1 | -6 |
| bridge | 1.1 | concept | glass bottom edge, mid | 0.1926 | 0.1926 | 0.1926 | 167.7 | 1.49 | 40.8 | -3 |
| bridge | 1.1 | concept | bottom edge over the CTP tail (x 58) | 0.1829 | 0.1829 | 0.1829 | 168.4 | 1.48 | 40.8 | -1 |
| bridge | 1.1 | meas. | window centre | 1.2687 | 0.1656 | 0.1656 | 412.0 | 0.61 | 6.9 | -20 |
| bridge | 1.1 | meas. | glass top edge, mid | 0.1266 | 0.1266 | 0.0141 | 72.7 | 3.44 | 21.3 | -3 |
| bridge | 1.1 | meas. | glass side edge, mid | 0.1213 | 0.1213 | 0.0272 | 73.8 | 3.39 | 21.9 | -0 |
| bridge | 1.1 | meas. | bottom border over the bend gap | 0.3413 | 0.2261 | 0.2261 | 301.0 | 0.83 | 29.6 | -6 |
| bridge | 1.1 | meas. | glass bottom edge, mid | 0.1937 | 0.1937 | 0.1937 | 169.9 | 1.47 | 41.7 | -3 |
| bridge | 1.1 | meas. | bottom edge over the CTP tail (x 58) | 0.1840 | 0.1840 | 0.1840 | 170.6 | 1.47 | 41.8 | -1 |
| bridge | 2.0 | concept | window centre | 0.3290 | 0.0717 | 0.0717 | 137.1 | 1.82 | 3.1 | -16 |
| bridge | 2.0 | concept | glass top edge, mid | 0.0849 | 0.0849 | 0.0103 | 38.8 | 6.44 | 15.5 | -3 |
| bridge | 2.0 | concept | glass side edge, mid | 0.0847 | 0.0847 | 0.0175 | 40.5 | 6.17 | 16.1 | -1 |
| bridge | 2.0 | concept | bottom border over the bend gap | 0.1336 | 0.1105 | 0.1105 | 103.8 | 2.41 | 12.1 | -6 |
| bridge | 2.0 | concept | glass bottom edge, mid | 0.1108 | 0.1108 | 0.1108 | 125.4 | 1.99 | 20.5 | -3 |
| bridge | 2.0 | concept | bottom edge over the CTP tail (x 58) | 0.1087 | 0.1087 | 0.1087 | 127.2 | 1.97 | 20.8 | -1 |
| bridge | 2.0 | meas. | window centre | 0.3292 | 0.0717 | 0.0717 | 137.1 | 1.82 | 3.1 | -16 |
| bridge | 2.0 | meas. | glass top edge, mid | 0.0853 | 0.0853 | 0.0103 | 39.5 | 6.33 | 15.8 | -3 |
| bridge | 2.0 | meas. | glass side edge, mid | 0.0851 | 0.0851 | 0.0175 | 41.2 | 6.07 | 16.4 | -1 |
| bridge | 2.0 | meas. | bottom border over the bend gap | 0.1338 | 0.1107 | 0.1107 | 103.8 | 2.41 | 12.2 | -6 |
| bridge | 2.0 | meas. | glass bottom edge, mid | 0.1111 | 0.1111 | 0.1111 | 127.3 | 1.96 | 20.8 | -3 |
| bridge | 2.0 | meas. | bottom edge over the CTP tail (x 58) | 0.1090 | 0.1090 | 0.1090 | 129.0 | 1.94 | 21.1 | -1 |
| bridge | 3.0 | concept | window centre | 0.1248 | 0.0413 | 0.0413 | 62.9 | 1.91 | 1.8 | -13 |
| bridge | 3.0 | concept | glass top edge, mid | 0.0659 | 0.0659 | 0.0079 | 39.0 | 3.07 | 11.0 | -4 |
| bridge | 3.0 | concept | glass side edge, mid | 0.0649 | 0.0649 | 0.0143 | 41.3 | 2.90 | 11.6 | 0 |
| bridge | 3.0 | concept | bottom border over the bend gap | 0.0755 | 0.0711 | 0.0711 | 56.8 | 2.11 | 5.7 | -6 |
| bridge | 3.0 | concept | glass bottom edge, mid | 0.0755 | 0.0755 | 0.0755 | 84.6 | 1.42 | 10.0 | -4 |
| bridge | 3.0 | concept | bottom edge over the CTP tail (x 58) | 0.0737 | 0.0737 | 0.0737 | 87.2 | 1.38 | 10.3 | 3 |
| bridge | 3.0 | meas. | window centre | 0.1249 | 0.0413 | 0.0413 | 62.9 | 1.91 | 1.9 | -13 |
| bridge | 3.0 | meas. | glass top edge, mid | 0.0661 | 0.0661 | 0.0079 | 39.6 | 3.03 | 11.2 | -4 |
| bridge | 3.0 | meas. | glass side edge, mid | 0.0651 | 0.0651 | 0.0143 | 41.9 | 2.87 | 11.8 | -0 |
| bridge | 3.0 | meas. | bottom border over the bend gap | 0.0755 | 0.0712 | 0.0712 | 56.9 | 2.11 | 5.8 | -6 |
| bridge | 3.0 | meas. | glass bottom edge, mid | 0.0757 | 0.0757 | 0.0757 | 85.4 | 1.40 | 10.2 | -4 |
| bridge | 3.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0738 | 0.0738 | 0.0738 | 88.1 | 1.36 | 10.5 | 3 |
| bridge | 4.0 | concept | window centre | 0.0663 | 0.0306 | 0.0306 | 35.6 | 3.37 | 1.3 | -8 |
| bridge | 4.0 | concept | glass top edge, mid | 0.0539 | 0.0539 | 0.0073 | 34.8 | 3.45 | 7.7 | -3 |
| bridge | 4.0 | concept | glass side edge, mid | 0.0506 | 0.0506 | 0.0139 | 36.8 | 3.26 | 8.2 | 11 |
| bridge | 4.0 | concept | bottom border over the bend gap | 0.0542 | 0.0541 | 0.0541 | 37.4 | 3.21 | 3.3 | -4 |
| bridge | 4.0 | concept | glass bottom edge, mid | 0.0581 | 0.0581 | 0.0581 | 58.5 | 2.05 | 5.6 | -3 |
| bridge | 4.0 | concept | bottom edge over the CTP tail (x 58) | 0.0547 | 0.0547 | 0.0547 | 60.5 | 1.98 | 5.8 | 16 |
| bridge | 4.0 | meas. | window centre | 0.0663 | 0.0306 | 0.0306 | 35.6 | 3.37 | 1.3 | -8 |
| bridge | 4.0 | meas. | glass top edge, mid | 0.0540 | 0.0540 | 0.0074 | 35.1 | 3.41 | 7.8 | -3 |
| bridge | 4.0 | meas. | glass side edge, mid | 0.0508 | 0.0508 | 0.0139 | 37.2 | 3.23 | 8.3 | 11 |
| bridge | 4.0 | meas. | bottom border over the bend gap | 0.0543 | 0.0541 | 0.0541 | 37.5 | 3.20 | 3.3 | -4 |
| bridge | 4.0 | meas. | glass bottom edge, mid | 0.0581 | 0.0581 | 0.0581 | 58.9 | 2.04 | 5.7 | -3 |
| bridge | 4.0 | meas. | bottom edge over the CTP tail (x 58) | 0.0547 | 0.0547 | 0.0547 | 61.0 | 1.97 | 5.9 | 16 |

one ring section per edge; J and the corner links as the concept; glass characteristic strength per glass_t from the params (1.1/2.0 CS 250 MPa, 3.0/4.0 tempered 120 MPa); no panel / LOCA / PCB credit

## 3. 0.5 J impact (concept method, estimates) [C]

| bottom bound / glass | glass g | window centre SF | bend-gap strip, whole border free SF | strip only SF |
|---|---|---|---|---|
| channel 1.1 | 65 | 1.07 | 0.74 | 1.23 |
| channel 2.0 | 118 | 1.82 | 1.58 | 2.77 |
| channel 3.0 | 177 | 1.22 | 1.35 | 2.53 |
| channel 4.0 | 236 | 1.58 | 2.12 | 4.26 |
| bridge 1.1 | 65 | 1.08 | 0.83 | 1.38 |
| bridge 2.0 | 118 | 1.83 | 1.72 | 3.01 |
| bridge 3.0 | 177 | 1.22 | 1.43 | 2.67 |
| bridge 4.0 | 236 | 1.59 | 2.20 | 4.40 |

## 4. Bead [C]

- area 2402.6 mm2 (params 2402.6; GF-2.0 2386.6); dead load 3.70 N -> 1.54 kPa; 250 N pull 0.104 MPa mean
- bead corner radius from the glass centre 109.87 (GF-2.0 109.18)

| case | d mm | ext. at t 0.73 | ext. at t 1.0 | allow class 50 t 0.73 | allow class 25 t 1.0 |
|---|---|---|---|---|---|
| design 50 ppm/K, +70 C | 0.225 | 4.7 % | 2.5 % | 0.816 | 0.750 |
| bound 70 ppm/K, +70 C | 0.335 | 10.0 % | 5.5 % | 0.816 | 0.750 |
| design 50 ppm/K, -20 C | 0.180 | 3.0 % | 1.6 % | 0.816 | 0.750 |
| bound 70 ppm/K, -20 C | 0.268 | 6.5 % | 3.5 % | 0.816 | 0.750 |
| design + 0.1 % moisture, +70 C | 0.335 | 10.0 % | 5.5 % | 0.816 | 0.750 |
| bound + 0.3 % moisture, +70 C | 0.665 | 35.2 % | 20.1 % | 0.816 | 0.750 |

## 5. Gaps (STEP lip, params glass / cut-out; sides / corner min / diagonal) [M + C]

| g2 | nominal | glass +0.1/side, R nominal (requested +-0.1, R +0.2/-0) | glass profile +0.2 (offset outline) | glass +0.2/side and R -0.2 (size + radius tolerances) | glass nominal size, R -0.2 | glass +0.2/side, R nominal (R +0.2/-0 callout) |
|---|---||---|---||---|---||---|---||---|---||---|---|
| 20 C | 0.394 / 0.395 / 0.497 | 0.294 / 0.295 / 0.356 | 0.194 / 0.195 / 0.297 | 0.191 / 0.131 / 0.132 | 0.394 / 0.394 / 0.414 | 0.194 / 0.194 / 0.214 |
| -20 C, 50 ppm | 0.237 / 0.237 / 0.319 | 0.137 / 0.137 / 0.177 | 0.037 / 0.037 / 0.119 | 0.033 / -0.050 / -0.047 | 0.237 / 0.227 / 0.236 | 0.037 / 0.027 / 0.036 |
| +70 C frame/glass, +50 C sheet, 50 ppm | 0.521 / 0.521 / 0.720 | 0.421 / 0.421 / 0.579 | 0.321 / 0.321 / 0.520 | 0.318 / 0.318 / 0.355 | 0.521 / 0.521 / 0.637 | 0.321 / 0.321 / 0.438 |
| -20 C, 70 ppm | 0.161 / 0.160 / 0.232 | 0.061 / 0.058 / 0.090 | -0.040 / -0.041 / 0.031 | -0.043 / -0.139 / -0.135 | 0.161 / 0.138 / 0.149 | -0.040 / -0.062 / -0.052 |
| +70 C frame/glass, +50 C sheet, 70 ppm | 0.582 / 0.583 / 0.828 | 0.483 / 0.483 / 0.687 | 0.383 / 0.383 / 0.629 | 0.379 / 0.379 / 0.464 | 0.582 / 0.583 / 0.746 | 0.383 / 0.383 / 0.547 |

| g1 | nominal | cut-out profile -0.1, lip +0.04 | cut-out -0.1/side and R +0.1, lip +0.04 | cut-out -0.1/side, R nominal (R +0/-0.2 callout), lip +0.04 |
|---|---||---|---||---|---||---|---|
| 20 C | 0.412 / 0.418 / 0.516 | 0.272 / 0.278 / 0.376 | 0.272 / 0.273 / 0.293 | 0.272 / 0.275 / 0.335 |
| -20 C, 50 ppm | 0.508 / 0.514 / 0.684 | 0.368 / 0.374 / 0.544 | 0.368 / 0.369 / 0.461 | 0.368 / 0.372 / 0.503 |
| +70 C frame/glass, +50 C sheet, 50 ppm | 0.203 / 0.208 / 0.279 | 0.063 / 0.068 / 0.139 | 0.063 / 0.047 / 0.057 | 0.063 / 0.066 / 0.098 |
| -20 C, 70 ppm | 0.559 / 0.565 / 0.773 | 0.419 / 0.425 / 0.633 | 0.419 / 0.420 / 0.550 | 0.419 / 0.422 / 0.591 |
| +70 C frame/glass, +50 C sheet, 70 ppm | 0.106 / 0.110 / 0.169 | -0.034 / -0.030 / 0.029 | -0.034 / -0.066 / -0.054 | -0.034 / -0.036 / -0.012 |

Formula (nominal per side), this release vs GF-2.0: {"50 ppm/K, -20 C": {"GF-2.1 g2 / g1": [0.243, 0.4959], "GF-2.0 g2 / g1": [0.2438, 0.4951], "change g2 / g1": [-0.0008, 0.0008]}, "50 ppm/K, +70 C frame / +50 C sheet": {"GF-2.1 g2 / g1": [0.5264, 0.1921], "GF-2.0 g2 / g1": [0.5254, 0.1932], "change g2 / g1": [0.001, -0.0011]}, "70 ppm/K, -20 C": {"GF-2.1 g2 / g1": [0.1664, 0.5463], "GF-2.0 g2 / g1": [0.1676, 0.5451], "change g2 / g1": [-0.0012, 0.0012]}, "70 ppm/K, +70 C frame / +50 C sheet": {"GF-2.1 g2 / g1": [0.5881, 0.095], "GF-2.0 g2 / g1": [0.5865, 0.0966], "change g2 / g1": [0.0016, -0.0016]}}

## 6. Tape and fasteners [C]

- tape 7651.2 mm2 (GF-2.0 7603.2); module 7.66 N -> 1.00 kPa; 250 N -> 32.7 kPa; thermal shear [29.1, 42.7] % of the 1.0 gap (50 / 70 ppm)
- studs at r 129.12: radial move [0.245, 0.374] mm (50 / 70 ppm, +70 / +50 C) vs float 1.20; stud reaction at 250 N max 12 N; M4 washer at 500 N [6.2, 7.6] MPa

## 7. Bend zone (nose, pocket face, break): criterion and measured clearances [M + C + A]

Criterion (params `tail_clearance_criteria.bend_zone`): >= 0.45 with the panel at its RSS position (+0.308), > 0.0 at the worst case (panel +0.60, exit Z +-0.3, tail +0.05); the concept's intent: >= 0.45 at the full worst case. Panel position contributors: {'panel outline vs AA (DS, concept 0.2)': 0.2, 'J1: AA aligned to the print window (concept 0.1)': 0.1, "print window vs glass edge (params drawing_tolerances.print 'print-to-edge +-0.2')": 0.2, 'J2: glass centred in the recess (graded shims, design doc 9.3)': 0.05, 'frame: bridge face (B core) vs recess wall (A core), core shift [A]': 0.05}.

| tail | nominal | panel at RSS | WC (all) | WC (panel position only) | WC with print-to-edge +-0.1 | feature |
|---|---|---|---|---|---|---|
| TFT | 1.718 | 1.459 | 1.014 | 1.220 | 1.098 | bridge nose R1.5 |
| CTP | 1.164 | 0.871 | 0.459 | 0.597 | 0.554 | bridge nose R1.5 |

g_bend budget (concept form): l0 0.50 + R_in 1.50 + t 0.30 + clearance 0.45 + panel position RSS 0.308 = **3.058** (modelled 3.23, +0.172); border 19.0 holds up to g_bend 3.290 (bezel 9.51 + land 6.20 = bead_edge 0.9 + bead_w 4.0 + bead_pocket_min 1.0 to the break edge + land_break 0.30 (the GF-2.0 budget used 5.9, i.e. A1 to the pocket face)) -> reserve of the budget **0.232**, of the modelled g_bend 0.060 (with the land to the face, as at GF-2.0: limit 3.590).

g_bend at which the bend-zone clearance would be exactly 0.45 (linear, slope from the RSS / panel-WC cases): {"TFT": {"slope_per_mm": 0.818, "g_bend_for_0.45_at_WC_all_contributors": 2.541, "g_bend_for_0.45_at_WC_panel_position_only": 2.288, "g_bend_for_0.45_at_RSS": 1.996}, "CTP": {"slope_per_mm": 0.941, "g_bend_for_0.45_at_WC_all_contributors": 3.221, "g_bend_for_0.45_at_WC_panel_position_only": 3.074, "g_bend_for_0.45_at_RSS": 2.782}}

## 7b. Bend-gap tolerance stack, linear estimate from the panel +0.35 case [C + A]

- TFT: nominal 1.718 to the bridge; sensitivity 0.84 per mm of panel shift; panel position WC 0.60 / RSS 0.31 (concept 0.35 / 0.25); exit Z +-0.3 costs 0.154 -> clearance WC 1.011, RSS 1.413 (concept budget 1.375)
- CTP: nominal 1.164 to the bridge; sensitivity 0.95 per mm of panel shift; panel position WC 0.60 / RSS 0.31 (concept 0.35 / 0.25); exit Z +-0.3 costs 0.084 -> clearance WC 0.460, RSS 0.856 (concept budget 0.782)

## 8. Volume and mass [M]

- STEP volume **84.128 cm3**, mass **114.4 g** at 1.36 g/cm3 (params as modelled 84.1288; GF-2.0 83.481 cm3 / 113.5 g; v2 55.06 cm3 / 74.9 g)
