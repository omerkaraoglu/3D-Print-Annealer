# Carrier frame v1 - hand calculations

| check | value | limit | ok |
|---|---|---|---|
| PCB boss bearing (cons / real) | 16.3 / 8.2 MPa | 15 | True |
| PCB boss thread shear SF | 2.28 | > 2 | True |
| PCB boss hoop SF short / long | 8.4 / 3.4 | > 2 | True |
| gasket force nom / max | 165 / 591 N | - | - |
| stud tube bearing (cons / real), area 53.9 mm2 | 13.9 / 9.3 MPa | 15 | True |
| stud clamp margin over the gasket share | 6.8 x | > 2 | True |
| flange a_plate_OD_lever_offset (hole F4, F 80 N) | total 49.0 / sustained 45.3 MPa | 37.5 / 15 | False |
| flange c_realistic_lever_from_tube_face (hole F4, F 80 N) | total 8.3 / sustained 7.7 MPa | 37.5 / 15 | True |
| beam section I (analytic) | 309 mm4 (v1 309, x1.00) | - | - |
| longest top run F2-F3, span 59.6 | lift 1000 h nom 102.4 um (full-q bound 94.9) | 90 um | False |
| longest bottom run F7-F6, span 149.0 | lift 1000 h nom 3708.2 um (full-q bound 3708.2) | 90 um | False |
| longest left run F8-F7, span 70.0 | lift 1000 h nom 158.9 um (full-q bound 180.6) | 90 um | False |
| longest right run F5-F6, span 70.0 | lift 1000 h nom 158.9 um (full-q bound 180.6) | 90 um | False |
| thermal (from the pegs' midpoint (all pegs round)): worst stud displacement | 0.561 mm (avail. 0.125 round) | - | not covered: F1, F2, F3, F4, F5, F6, F7, F8 |
| thermal: peg-to-peg growth (two round holes dia 3.20) | 0.487 mm, 0.487 per peg (play 0.200) | - | False |
| 10 g shock per stud / PCB screw | 6.0 / 3.2 N | - | - |

## Runs (corners count as supports; uniform q)

| edge | from | to | span | loaded | I meas. | lift nom 1000 h full q | partial (verdict) | lift max 1000 h full q | bending max |
|---|---|---|---|---|---|---|---|---|---|
| top | F1 | F2 | 55.4 | 52.7 | 286.3 | 71.0 | 76.2 | 253.7 | 8.26 |
| top | F2 | F3 | 59.6 | 59.6 | 286.3 | 94.9 | 102.4 | 339.0 | 9.55 |
| top | F3 | F4 | 55.4 | 52.6 | 286.3 | 70.7 | 75.8 | 252.6 | 8.24 |
| bottom | corner | F7 | 10.7 | 8.0 | 372.2 | 0.1 | 0.1 | 0.4 | 0.31 |
| bottom | F7 | F6 | 149.0 | 149.0 | 635.0 | 3708.2 | 3708.2 | 13243.5 | 59.67 |
| bottom | F6 | corner | 10.7 | 7.9 | 372.2 | 0.1 | 0.1 | 0.3 | 0.31 |
| left | F1 | F8 | 52.8 | 50.0 | 286.3 | 58.3 | 62.4 | 208.0 | 7.48 |
| left | F8 | F7 | 70.0 | 50.0 | 286.3 | 180.6 | 158.9 | 645.1 | 13.17 |
| left | F7 | corner | 14.7 | 0.0 | 367.2 | 0.4 | 0.0 | 1.3 | 0.58 |
| right | F4 | F5 | 52.8 | 50.0 | 286.3 | 58.3 | 62.4 | 208.0 | 7.48 |
| right | F5 | F6 | 70.0 | 50.0 | 286.3 | 180.6 | 158.9 | 645.1 | 13.17 |
| right | F6 | corner | 14.7 | 0.0 | 367.2 | 0.4 | 0.0 | 1.3 | 0.58 |

## Thermal (dT 60 K, from the pegs' midpoint (all pegs round))

| hole | dx | dy | 70/70 | 30/70 | 70/30 | slot |
|---|---|---|---|---|---|---|
| F1 | -89.5 | -134.0 | 0.561 | 0.476 | 0.343 | 5.37 |
| F2 | -29.8 | -134.0 | 0.478 | 0.467 | 0.178 | 5.21 |
| F3 | 29.8 | -134.0 | 0.478 | 0.467 | 0.178 | 5.21 |
| F4 | 89.5 | -134.0 | 0.561 | 0.476 | 0.343 | 5.37 |
| F5 | 89.9 | -77.0 | 0.412 | 0.285 | 0.324 | 5.07 |
| F6 | 74.5 | -7.0 | 0.260 | 0.084 | 0.259 | 4.77 |
| F7 | -74.5 | -7.0 | 0.260 | 0.084 | 0.259 | 4.77 |
| F8 | -89.9 | -77.0 | 0.412 | 0.285 | 0.324 | 5.07 |
