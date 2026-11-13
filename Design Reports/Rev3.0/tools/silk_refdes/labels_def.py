"""Board-level silkscreen legend of the Rev3.0 board (data only, no imports: read by the KiCad-python geometry export
for the ink boxes and by silk_labels.py for the placement).

Every label: name, text, (height, width, stroke) mm, angle, and a list of targets (x, y absolute mm, search radius mm):
the label goes to the free spot nearest to the first target that has one (pads + 0.25, silk + 0.5, edge / holes
+ 0.5, other new legend + 0.3 within its cluster / 0.5 otherwise). Blocks (title, mains warning) are several centred
lines placed as one unit, never over a courtyard or an F.Cu track / via.
Old board texts replaced by this legend (uuids): see OLD_TEXTS.
"""
F = (1.0, 1.0, 0.15)      # functional label
PIN = (1.0, 1.0, 0.15)    # pin / polarity mark

LABELS = [
    # mains band, wire pads on the top edge: the row right under the pads carries the designator (centred) and the
    # pin marks (under each pad), the function goes one row lower
    {"name": "J3_L", "text": "L", "size": PIN, "ang": 0, "cluster": "J3", "targets": [(107.0, 26.35, 0.6)]},
    {"name": "J3_N", "text": "N", "size": PIN, "ang": 0, "cluster": "J3", "targets": [(114.8, 26.35, 0.6)]},
    {"name": "J3_fn", "text": "MAINS IN", "size": F, "ang": 0, "cluster": "J3", "targets": [(110.9, 28.25, 1.5)]},
    {"name": "R1_fn", "text": "HEATER", "size": F, "ang": 0, "cluster": "R1", "targets": [(124.1, 28.25, 1.5)]},
    {"name": "J4_fn", "text": "FAN", "size": F, "ang": 0, "cluster": "J4", "targets": [(73.4, 23.5, 0.3), (73.4, 28.25, 1.5)]},  # between the two wire pads
    # FTDI programming header J2 (pin 1 = GND at the top)
    {"name": "J2_fn", "text": "FTDI", "size": F, "ang": 0, "cluster": "J2", "targets": [(24.5, 26.0, 2.0)]},
    {"name": "J2_p1", "text": "GND", "size": PIN, "ang": 0, "cluster": "J2", "targets": [(28.6, 30.5, 1.2), (21.4, 30.5, 1.0)]},
    {"name": "J2_p6", "text": "3V3", "size": PIN, "ang": 0, "cluster": "J2", "targets": [(28.6, 43.2, 1.2)]},
    # thermocouple terminal J20 (pin 1 TC+ at the top)
    {"name": "J20_fn", "text": "K-TYPE TC", "size": F, "ang": 0, "cluster": "J20", "targets": [(25.2, 94.6, 2.5)]},
    {"name": "J20_p", "text": "+", "size": PIN, "ang": 0, "cluster": "J20", "targets": [(23.3, 100.0, 1.2), (26.5, 96.2, 1.0)]},
    {"name": "J20_n", "text": "-", "size": PIN, "ang": 0, "cluster": "J20", "targets": [(23.3, 105.08, 1.2), (26.5, 109.0, 1.2)]},
    # FPC connectors at the bottom edge (tails come in from below)
    {"name": "J10_fn", "text": "TFT", "size": F, "ang": 0, "cluster": "J10", "targets": [(155.65, 116.4, 2.5)]},
    {"name": "J11_fn", "text": "TOUCH", "size": F, "ang": 0, "cluster": "J11", "targets": [(60.0, 116.4, 2.5)]},
]

BLOCKS = [
    {"name": "title", "lines": [("3D Printer Filament Dryer", (1.2, 1.2, 0.18)), ("& Print Annealer", (1.2, 1.2, 0.18)),
                                ("PCB Rev3.0  2026-11-13", (1.0, 1.0, 0.15)), ("readark", (1.5, 1.5, 0.22))],
     "gap": 0.6, "targets": [(168.5, 90.0, 14.0), (172.0, 100.0, 20.0), (40.0, 75.0, 20.0)]},
    {"name": "mains", "lines": [("230 V~ MAINS", (1.5, 1.5, 0.22)), ("HAZARDOUS VOLTAGE", (1.0, 1.0, 0.15))],
     "gap": 0.5, "targets": [(58.0, 52.0, 6.0), (95.0, 45.0, 8.0), (110.0, 70.0, 8.0)],
     "region": "mains"},
]

# board texts of the previous rounds, replaced by the legend above (mislabelled: "MAINS IN" sat at J4, "FAN" at J3,
# "HEATER" at PS1)
OLD_TEXTS = {
    "323db84b-0615-41b4-84af-da2a46173555": "MAINS IN",
    "68a54482-5593-4356-9470-c175acd6ad1e": "FAN",
    "f326fd7a-f76c-410c-934f-2fab53a83456": "HEATER",
    "4c2ee409-1ac2-450d-9c9f-a03adf0a43b3": "K-TYPE TC",
    "892bb6d6-f2d1-4bc1-b128-bb558627e0e1": "READARK DRYER / ANNEALER",
    "db4a5cef-f27f-46b3-bd9e-9bc95f28fd8e": "Rev3.0  2026",
}

FAB_X, FAB_Y, FAB_DY = 200.0, 20.0, 1.6     # Cmts.User notes right of the board (absolute mm), 1.0 mm / 0.12 stroke
FAB_NOTES = [
    "FABRICATION NOTES - 3D PRINTER FILAMENT DRYER & PRINT ANNEALER, PCB REV3.0 (2026-11-13)",
    "1. Outline 164.0 x 99.0 mm body, 183.7 x 118.7 mm overall incl. the nine screw ears; R3 corners. Thickness 1.6 mm.",
    "2. 4 layers, 1.6 mm FR4 (Tg >= 150 C, UL 94 V-0), 35 um (1 oz) finished copper on all layers:",
    "   F.Cu / prepreg 0.2 mm / In1 (GND) / core 1.0 mm / In2 (3V3, +5V island) / prepreg 0.2 mm / B.Cu.",
    "3. Finish: ENIG per the board stackup (final choice TBD). Green LPI solder mask both sides, white legend top.",
    "4. Minimum track / clearance 0.15 / 0.15 mm (fine-pitch escapes at U10 / U20 0.13 mm clearance).",
    "5. Vias 0.6 / 0.3 mm (signal, stitching) and 0.9 / 0.45 mm (power), tented both sides, no via-in-pad.",
    "6. 9 x M3 mounting holes, NPTH dia. 3.2 mm, in the screw ears. All other holes plated.",
    "7. Creepage slot under U5 / U1: routed, non-plated, 1.2 x 23.5 mm, round ends. Do not fill or plate.",
    "8. Mains area (top band, Cmts.User outline): no inner-layer copper; keep the 6.4 mm mains-SELV spacing.",
    "9. Fabricate and accept per IPC-6012 / IPC-A-600 class 2. 100 % electrical test.",
]
