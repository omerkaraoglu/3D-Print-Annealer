# Carrier frame v2 - hand calculations

| check | value | limit | ok |
|---|---|---|---|
| PCB boss bearing (cons / real) | 16.3 / 8.2 MPa | 15 | True |
| PCB boss thread shear SF | 2.28 | > 2 | True |
| PCB boss hoop SF short / long | 8.4 / 3.4 | > 2 | True |
| gasket force nom / max | 165 / 591 N | - | - |
| stud tube bearing (cons / real), area 59.4 mm2 | 12.6 / 8.4 MPa | 15 | True |
| stud clamp margin over the gasket share | 8.5 x | > 2 | True |
| flange a_plate_OD_lever_offset (hole FH9, F 64 N) | total 46.0 / sustained 42.6 MPa | 37.5 / 15 | False |
| flange b_plate_plus_rib (hole FH9, F 64 N) | total 23.5 / sustained 21.7 MPa | 37.5 / 15 | False |
| flange c_realistic_lever_from_tube_face (hole FH9, F 64 N) | total 10.2 / sustained 9.5 MPa | 37.5 / 15 | True |
| flange d_T_section_measured_rib (hole FH9, F 64 N) | total 23.5 / sustained 6.2 MPa | 37.5 / 15 | True |
| beam section I (analytic) | 713 mm4 (v1 309, x2.31) | - | - |
| longest top run FH1-FH2, span 60.0 | lift 1000 h nom 44.0 um (full-q bound 42.3) | 90 um | True |
| longest bottom run FH8-FH7, span 68.5 | lift 1000 h nom 71.8 um (full-q bound 71.8) | 90 um | True |
| longest left run FH10-FH9, span 58.0 | lift 1000 h nom 38.4 um (full-q bound 36.9) | 90 um | True |
| longest right run FH4-FH5, span 58.0 | lift 1000 h nom 38.4 um (full-q bound 36.9) | 90 um | True |
| thermal (from the datum (both pegs slotted along the peg line: held across it, self-centred along it)): worst stud displacement | 0.398 mm (avail. 0.125 round) | - | not covered: FH6, FH8 |
| thermal: peg-to-peg growth (slots P1+P2 3.20 x 3.90) | 0.645 mm, 0.323 per peg (play 0.325) | - | True |
| thermal + frame x-float +-0.25 along the peg line | - | - | not covered: FH1, FH2, FH3, FH4, FH5, FH6, FH7, FH8, FH9, FH10 |
| 10 g shock per stud / PCB screw | 4.8 / 3.2 N | - | - |

## Runs (corners count as supports; uniform q)

| edge | from | to | span | loaded | I meas. | lift nom 1000 h full q | partial (verdict) | lift max 1000 h full q | bending max |
|---|---|---|---|---|---|---|---|---|---|
| top | corner | FH1 | 26.2 | 23.5 | 685.1 | 1.5 | 1.6 | 5.5 | 1.00 |
| top | FH1 | FH2 | 60.0 | 60.0 | 685.1 | 42.3 | 44.0 | 151.0 | 5.23 |
| top | FH2 | FH3 | 58.5 | 58.5 | 685.1 | 38.2 | 39.7 | 136.4 | 4.97 |
| top | FH3 | corner | 25.7 | 22.9 | 685.1 | 1.4 | 1.4 | 5.1 | 0.96 |
| bottom | corner | FH8 | 16.7 | 14.0 | 558.0 | 0.3 | 0.3 | 0.9 | 0.41 |
| bottom | FH8 | FH7 | 68.5 | 68.5 | 1269.5 | 71.8 | 71.8 | 256.4 | 6.82 |
| bottom | FH7 | FH6 | 68.5 | 68.5 | 1269.5 | 71.8 | 71.8 | 256.4 | 6.82 |
| bottom | FH6 | corner | 16.7 | 13.9 | 558.0 | 0.3 | 0.3 | 0.9 | 0.40 |
| left | corner | FH10 | 24.2 | 21.5 | 685.1 | 1.1 | 1.1 | 4.0 | 0.85 |
| left | FH10 | FH9 | 58.0 | 58.0 | 685.1 | 36.9 | 38.4 | 131.8 | 4.89 |
| left | FH9 | corner | 55.2 | 20.5 | 558.0 | 30.3 | 11.8 | 108.1 | 4.43 |
| right | corner | FH4 | 24.2 | 21.5 | 685.1 | 1.1 | 1.1 | 4.0 | 0.85 |
| right | FH4 | FH5 | 58.0 | 58.0 | 685.1 | 36.9 | 38.4 | 131.8 | 4.89 |
| right | FH5 | corner | 55.2 | 20.5 | 558.0 | 30.3 | 11.8 | 108.1 | 4.43 |

## Thermal (dT 60 K, from the datum (both pegs slotted along the peg line: held across it, self-centred along it))

| hole | dx | dy | 70/70 | 30/70 | 70/30 | slot |
|---|---|---|---|---|---|---|
| FH1 | -59.0 | -60.8 | 0.295 | 0.221 | 0.215 | - |
| FH2 | 1.0 | -60.8 | 0.211 | 0.211 | 0.066 | - |
| FH3 | 59.5 | -60.8 | 0.296 | 0.221 | 0.217 | - |
| FH4 | 92.7 | -29.0 | 0.338 | 0.142 | 0.324 | - |
| FH5 | 92.7 | 29.0 | 0.338 | 0.142 | 0.324 | - |
| FH6 | 68.5 | 91.7 | 0.398 | 0.328 | 0.258 | 5.05 |
| FH7 | 0.0 | 91.7 | 0.319 | 0.319 | 0.099 | - |
| FH8 | -68.5 | 91.7 | 0.398 | 0.328 | 0.258 | 5.05 |
| FH9 | -92.7 | 29.0 | 0.338 | 0.142 | 0.324 | - |
| FH10 | -92.7 | -29.0 | 0.338 | 0.142 | 0.324 | - |
