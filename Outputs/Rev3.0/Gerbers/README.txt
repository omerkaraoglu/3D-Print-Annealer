OVEN CONTROLLER PCB Rev3.0 (3D Printer Filament Dryer & Print Annealer) - fabrication data
Exported 2026-11-23 with KiCad 10.0.1 (kicad-cli) from 3dFilamentDryer.kicad_pcb, git commit b2837d7
(board file md5 4bc77e6a2a4f801f22de27bd7fd16ce1). Design-rule check of that file: 0 violations, 0 unconnected.

FILES (Gerber X2, millimetres, 4.6 format; Excellon drill, millimetres, decimal)
  3dFilamentDryer-F_Cu.gtl          copper layer 1, top (components)
  3dFilamentDryer-GND.g1            copper layer 2, inner 1, ground plane
  3dFilamentDryer-PWR.g2            copper layer 3, inner 2, 3V3 power plane with +5 V island
  3dFilamentDryer-B_Cu.gbl          copper layer 4, bottom
  3dFilamentDryer-F_Mask.gts        solder mask, top
  3dFilamentDryer-B_Mask.gbs        solder mask, bottom
  3dFilamentDryer-F_Silkscreen.gto  legend, top
  3dFilamentDryer-B_Silkscreen.gbo  legend, bottom (designators BP1-BP18 of the bare landing pads)
  3dFilamentDryer-F_Paste.gtp       solder paste, top (stencil)
  3dFilamentDryer-B_Paste.gbp       solder paste, bottom - empty: no paste on the bottom side
  3dFilamentDryer-Edge_Cuts.gm1     board outline, including the routed creepage slot
  3dFilamentDryer-PTH.drl           plated holes, 726
  3dFilamentDryer-NPTH.drl          non-plated holes, 9 x 3.2 mm (mounting holes in the screw ears)
  3dFilamentDryer-PTH-drl_map.pdf, 3dFilamentDryer-NPTH-drl_map.pdf   drill maps
  3dFilamentDryer-drill_report.txt  drill table
  3dFilamentDryer-job.gbrjob        Gerber job file (layer order and stack-up)
  3dFilamentDryer-fab_notes.pdf     fabrication notes drawing (board layer Cmts.User, notes dated 2026-11-13)
  3dFilamentDryer.d356              IPC-D-356 netlist for electrical test

BOARD
  Size 164.0 x 99.0 mm body, 183.7 x 118.7 mm overall including the nine screw ears. Thickness 1.6 mm.
  4 layers, FR4 (Tg >= 150 C, UL 94 V-0), 35 um (1 oz) finished copper on all layers.
  Stack-up: F.Cu / prepreg 0.2 mm / inner 1 (GND) / core 1.0 mm / inner 2 (PWR) / prepreg 0.2 mm / B.Cu.
  Finish ENIG (stated as "final choice TBD" in the fabrication notes). Green solder mask both sides, white legend.
  Minimum track / clearance 0.15 / 0.15 mm; 0.13 mm clearance at the fine-pitch escapes of U10 and U20.
  Vias 0.6 / 0.3 mm and 0.9 / 0.45 mm, tented.
  Routed non-plated creepage slot 1.2 x 23.5 mm under U5 / U1: do not fill or plate.
  IPC-6012 / IPC-A-600 class 2, 100 % electrical test.

POINTS THE FABRICATION NOTES (2026-11-13) DO NOT STATE
  - Smallest drill is 0.2 mm: 12 plated holes under the ESP32 module U3 (thermal vias of the library footprint).
    All other vias are 0.3 mm or larger.
  - Legend is needed on BOTH sides; the notes say "white legend top".
  - The bottom side carries 18 bare (ENIG) ground landing pads BP1-BP18, 6.0 x 5.0 mm openings, and the bare seat
    of the earth-bond pad J5 (5.6 mm opening). They must stay free of solder mask.
  - J5 is one 3.2 mm PLATED hole at X27.0 Y-112.5 (the nine 3.2 mm mounting holes are non-plated).

ASSEMBLY DATA (not in this folder)
  Design Reports/Rev3.0/Rev3.0_CPL.csv   component placement
  Design Reports/Rev3.0/Rev3.0_BOM.csv   schematic bill of materials
  Design Reports/Rev3.0/Rev3.0_BOM_Ozdisan_100pcs.csv / .md   purchasing list with suppliers
