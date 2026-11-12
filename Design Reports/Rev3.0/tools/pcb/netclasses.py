"""Net classes + DRC rules for Rev3.0 (IPC-2221B spacing, IPC-2152 widths). Writes the .kicad_pro net settings and the .kicad_dru."""
import json, sys, re
PRO = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/3dFilamentDryer.kicad_pro"
DRU = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/3dFilamentDryer.kicad_dru"

MAINS = ["LINE", "LINE_FUSED", "LINE_FILT", "PSU_L", "NEUT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "Net-(Q1-A1)", "Net-(Q1-A2)",
         "Net-(Q1-G)", "Net-(C4-Pad1)", "Net-(R3-Pad1)", "Net-(J4-Pin_1)", "/ZCD_L", "/ZCD_N"]   # pass 4: H11AA1 replaces the 4N28 + D1-D4 bridge
HEATER = ["LINE", "LINE_FUSED", "LINE_FILT", "Net-(Q1-A1)", "Net-(Q1-A2)"]   # pass 3: the LC filter is in the heater path                       # 5.7 A heater path -> 2.5 mm (IPC-2152, 1 oz, 20 K rise at 85 C)
POWER = ["+5V", "+3V3", "/Power/BUCK_SW", "/Display/BL_VIN", "/Display/BL_SW", "/Display/BL_DAMP", "/Display/VLED_P", "/Display/VLED_N", "/Display/TFT_VDD"]
P1V2 = ["+1V2"]
TC = ["/Thermocouple front end (K-type, ADS1115)/TC_P", "/Thermocouple front end (K-type, ADS1115)/TC_N",
      "/Thermocouple front end (K-type, ADS1115)/TCF_P", "/Thermocouple front end (K-type, ADS1115)/TCF_N"]

def cls(name, clearance, track, via, drill, color="rgba(0, 0, 0, 0.000)", prio=0):
    return {"bus_width": 12, "clearance": clearance, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "diff_pair_width": 0.25,
            "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1, "name": name, "pcb_color": color, "priority": prio,
            "schematic_color": "rgba(0, 0, 0, 0.000)", "track_width": track, "tuning_profile": "", "via_diameter": via, "via_drill": drill, "wire_width": 6}

p = json.load(open(PRO, encoding="utf-8"))
ns = p["net_settings"]
ns["classes"] = [
    cls("Default", 0.2, 0.25, 0.6, 0.3, prio=2147483647),
    cls("Mains", 2.5, 1.0, 1.2, 0.6, "rgba(255, 0, 0, 0.500)", 0),          # IPC-2221B B2, 301-500 Vpk: 2.5 mm between mains conductors
    cls("MainsHeater", 2.5, 2.5, 1.2, 0.6, "rgba(255, 80, 0, 0.500)", 1),
    cls("Power", 0.2, 1.0, 0.9, 0.45, "rgba(0, 120, 255, 0.500)", 2),
    cls("P1V2", 0.2, 0.6, 0.6, 0.3, "rgba(0, 200, 120, 0.500)", 3),
    cls("TC", 0.25, 0.3, 0.6, 0.3, "rgba(200, 0, 200, 0.500)", 4),
    cls("Bus", 0.15, 0.25, 0.6, 0.3, "rgba(255, 200, 0, 0.500)", 5),
]
pat = []
for n in HEATER: pat.append({"netclass": "MainsHeater", "pattern": n})
for n in MAINS:
    if n not in HEATER: pat.append({"netclass": "Mains", "pattern": n})
for n in ("unconnected-(K1-Pad4)", "unconnected-(U1-NC-Pad3)", "unconnected-(U5-NC-Pad5)"): pat.append({"netclass": "Mains", "pattern": n})
for n in POWER: pat.append({"netclass": "Power", "pattern": n})
for n in P1V2: pat.append({"netclass": "P1V2", "pattern": n})
for n in TC: pat.append({"netclass": "TC", "pattern": n})
pat.append({"netclass": "Bus", "pattern": "LCD_*"}); pat.append({"netclass": "Bus", "pattern": "/Display/SSD_*"})
for g in ("R", "G", "B"):
    pat.append({"netclass": "Bus", "pattern": "/Display/%s[0-7]" % g})
for n in ("PCLK", "HSYNC", "VSYNC", "DE"): pat.append({"netclass": "Bus", "pattern": "/Display/" + n})
# pass 4: SSD1963-side halves of the RGB/sync lines (before the series resistor arrays)
for g in "RGB": pat.append({"netclass": "Bus", "pattern": "/Display/%s[0-7]_T" % g})
for n in ("PCLK", "HSYNC", "VSYNC", "DE"): pat.append({"netclass": "Bus", "pattern": "/Display/" + n + "_T"})
ns["netclass_patterns"] = pat
ns["netclass_assignments"] = None
r = p["board"]["design_settings"]["rules"]
r.update({"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3,
          "min_copper_edge_clearance": 0.5, "min_hole_clearance": 0.25, "min_hole_to_hole": 0.5, "min_via_annular_width": 0.1, "min_through_hole_diameter": 0.2,
          "min_connection": 0.0, "solder_mask_to_copper_clearance": 0.0})
p["board"]["design_settings"]["track_widths"] = [0.0, 0.25, 0.3, 0.5, 0.6, 1.0, 1.5, 2.5]
p["board"]["design_settings"]["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.9, "drill": 0.45}, {"diameter": 1.2, "drill": 0.6}]
sev = p["board"]["design_settings"]["rule_severities"]
sev["creepage"] = "error"; sev["courtyards_overlap"] = "error"; sev["silk_over_copper"] = "warning"; sev["silk_overlap"] = "warning"
sev["copper_sliver"] = "warning"; sev["isolated_copper"] = "warning"; sev["footprint_type_mismatch"] = "ignore"; sev["starved_thermal"] = "warning"
sev["lib_footprint_mismatch"] = "ignore"; sev["lib_footprint_issues"] = "ignore"
json.dump(p, open(PRO, "w", encoding="utf-8"), indent=2)
print("project net classes written")

# component-inherent exceptions (the SRD-05 relay: coil pins 6.3 mm from the COM contact; the relay carries the reinforced insulation)
K1NETS = lambda A: "(%s.NetName == 'LINE' || %s.NetName == 'LINE_FILT' || %s.NetName == '+5V' || %s.NetName == 'Net-(D5-A)' || %s.NetName == 'Net-(J4-Pin_1)')" % (A, A, A, A, A)   # pass 3: K1 COM is on LINE_FILT
COILN = lambda A: "(%s.NetName == '+5V' || %s.NetName == 'Net-(D5-A)')" % (A, A)
EXC = "(A.NetName == 'LINE' && %s) || (B.NetName == 'LINE' && %s) || (A.NetName == 'LINE_FILT' && %s) || (B.NetName == 'LINE_FILT' && %s) || (A.NetName == 'unconnected-(K1-Pad4)' && %s) || (B.NetName == 'unconnected-(K1-Pad4)' && %s)" % (COILN('B'), COILN('A'), COILN('B'), COILN('A'), COILN('B'), COILN('A'))
# HS1 solder pins (unconnected nets) by net name: creepage rules see nets, not footprints
HSN = lambda X: "%s.NetName == 'unconnected-(HS1-Pad1)' || %s.NetName == 'unconnected-(HS1-Pad2)'" % (X, X)
mainsc = lambda A: "%s.NetClass == 'Mains' || %s.NetClass == 'MainsHeater'" % (A, A)
notmains = lambda A: "%s.NetClass != 'Mains' && %s.NetClass != 'MainsHeater'" % (A, A)
dru = f"""(version 1)
# Rev3.0 isolation rules. IPC-2221B table 6-1 (B2, uncoated external, 301-500 V peak): 2.5 mm between mains conductors;
# reinforced insulation mains <-> SELV (IEC 62368-1, 250 Vrms, PD2, material group IIIb): 6.4 mm creepage (surface, slots count)
# and 4.0 mm clearance through air (requirement 3.0 mm for 2.5 kV transient, reinforced).
(rule "mains_to_selv_clearance"
   (constraint clearance (min 4.0mm))
   (condition "((({mainsc('A')}) && ({notmains('B')})) || (({mainsc('B')}) && ({notmains('A')}))) && !({EXC})"))
(rule "mains_to_selv_creepage"
   (constraint creepage (min 6.4mm))
   (condition "((({mainsc('A')}) && ({notmains('B')})) || (({mainsc('B')}) && ({notmains('A')}))) && !({EXC}) && !({HSN('A')} || {HSN('B')})"))
(rule "mains_to_edge"
   (constraint edge_clearance (min 1.0mm))
   (condition "{mainsc('A')}"))
# functional insulation inside the mains section: 2.5 mm (IPC-2221B B2 for 325 Vpk)
(rule "mains_mains"
   (constraint clearance (min 2.5mm))
   (condition "({mainsc('A')}) && ({mainsc('B')})"))
# nodes that sit at the same potential (fuse / choke / filter chain on L, and on N): 1.0 mm functional
(rule "mains_L_group"
   (constraint clearance (min 1.0mm))
   (condition "(A.NetName == 'LINE' && B.NetName == 'LINE_FUSED') || (A.NetName == 'LINE' && B.NetName == 'LINE_FILT') || (A.NetName == 'LINE' && B.NetName == 'PSU_L') || (A.NetName == 'LINE' && B.NetName == 'Net-(PS1-AC/L)') || (A.NetName == 'LINE_FUSED' && B.NetName == 'LINE') || (A.NetName == 'LINE_FUSED' && B.NetName == 'LINE_FILT') || (A.NetName == 'LINE_FUSED' && B.NetName == 'PSU_L') || (A.NetName == 'LINE_FUSED' && B.NetName == 'Net-(PS1-AC/L)') || (A.NetName == 'LINE_FILT' && B.NetName == 'LINE') || (A.NetName == 'LINE_FILT' && B.NetName == 'LINE_FUSED') || (A.NetName == 'LINE_FILT' && B.NetName == 'PSU_L') || (A.NetName == 'LINE_FILT' && B.NetName == 'Net-(PS1-AC/L)') || (A.NetName == 'PSU_L' && B.NetName == 'LINE') || (A.NetName == 'PSU_L' && B.NetName == 'LINE_FUSED') || (A.NetName == 'PSU_L' && B.NetName == 'LINE_FILT') || (A.NetName == 'PSU_L' && B.NetName == 'Net-(PS1-AC/L)') || (A.NetName == 'Net-(PS1-AC/L)' && B.NetName == 'LINE') || (A.NetName == 'Net-(PS1-AC/L)' && B.NetName == 'LINE_FUSED') || (A.NetName == 'Net-(PS1-AC/L)' && B.NetName == 'LINE_FILT') || (A.NetName == 'Net-(PS1-AC/L)' && B.NetName == 'PSU_L')"))
(rule "mains_N_group"
   (constraint clearance (min 1.0mm))
   (condition "(A.NetName == 'NEUT' && B.NetName == 'Net-(PS1-AC/N)') || (B.NetName == 'NEUT' && A.NetName == 'Net-(PS1-AC/N)')"))
# the gate resistor pad next to the floating NC pin 3 of the 4N28 (no working voltage between them)
(rule "gate_vs_u1_nc"
   (constraint clearance (min 0.5mm))
   (condition "(A.NetName == 'Net-(Q1-G)' && B.NetName == 'unconnected-(U1-NC-Pad3)') || (B.NetName == 'Net-(Q1-G)' && A.NetName == 'unconnected-(U1-NC-Pad3)')"))
# ZCD bridge DC side: the two nodes differ by one LED drop
(rule "zcd_dc_pair"
   (constraint clearance (min 0.5mm))
   (condition "(A.NetName == '/ZCD_L' && B.NetName == '/ZCD_N') || (B.NetName == '/ZCD_L' && A.NetName == '/ZCD_N')"))
# component-inherent pin spacing (TO-220, DIP-6, relay, wire pads): pad to pad inside one footprint
(rule "same_footprint_pads"
   (constraint clearance (min 0.4mm))
   (condition "(A.memberOfFootprint('Q1') && B.memberOfFootprint('Q1')) || (A.memberOfFootprint('U1') && B.memberOfFootprint('U1')) || (A.memberOfFootprint('U5') && B.memberOfFootprint('U5')) || (A.memberOfFootprint('K1') && B.memberOfFootprint('K1'))"))
(rule "same_footprint_pads_creepage"
   (constraint creepage (min 0.4mm))
   (condition "(A.memberOfFootprint('U1') && B.memberOfFootprint('U1')) || (A.memberOfFootprint('U5') && B.memberOfFootprint('U5')) || (A.memberOfFootprint('K1') && B.memberOfFootprint('K1'))"))
# triac pins at 2.54 mm pitch: the triac's own three nets next to its own pads
(rule "triac_pins"
   (constraint clearance (min 0.4mm))
   (condition "(A.memberOfFootprint('Q1') && (B.NetName == 'Net-(Q1-A1)' || B.NetName == 'Net-(Q1-A2)' || B.NetName == 'Net-(Q1-G)')) || (B.memberOfFootprint('Q1') && (A.NetName == 'Net-(Q1-A1)' || A.NetName == 'Net-(Q1-A2)' || A.NetName == 'Net-(Q1-G)'))"))
# fan-out areas next to the TO-220 triac, the relay and the optocouplers: component-inherent pin pitch
(rule "fanout_areas"
   (constraint clearance (min 0.5mm))
   (condition "A.Type != 'Zone' && B.Type != 'Zone' && ((A.insideArea('q1_fanout') && B.insideArea('q1_fanout')) || (A.insideArea('k1_pins') && B.insideArea('k1_pins')) || (A.insideArea('u1_pins') && B.insideArea('u1_pins')) || (A.insideArea('u5_pins') && B.insideArea('u5_pins')))"))
(rule "fanout_areas_creepage"
   (constraint creepage (min 0.5mm))
   (condition "(A.insideArea('k1_pins') && B.insideArea('k1_pins')) || (A.insideArea('u1_pins') && B.insideArea('u1_pins')) || (A.insideArea('u5_pins') && B.insideArea('u5_pins'))"))
# relay SRD-05VDC: coil pins are 6.3 mm from the COM contact by construction (relay carries the reinforced insulation)
(rule "relay_coil_clearance"
   (constraint clearance (min 0.8mm))
   (condition "(A.memberOfFootprint('K1') && (B.NetName == '+5V' || B.NetName == 'Net-(D5-A)')) || (B.memberOfFootprint('K1') && (A.NetName == '+5V' || A.NetName == 'Net-(D5-A)'))"))
(rule "relay_coil_creepage"
   (constraint creepage (min 0.8mm))
   (condition "(A.memberOfFootprint('K1') && (B.NetName == '+5V' || B.NetName == 'Net-(D5-A)')) || (B.memberOfFootprint('K1') && (A.NetName == '+5V' || A.NetName == 'Net-(D5-A)'))"))
# optocoupler LED-side / output-side pins: pads of U1 and U5 against their own nets (slots under the packages give the creepage)
(rule "opto_pins"
   (constraint clearance (min 0.4mm))
   (condition "(A.memberOfFootprint('U5') && (B.NetName == '/TRIG' || B.NetName == 'Net-(R4-Pad2)' || B.NetName == 'GND' || B.NetName == 'Net-(Q1-G)' || B.NetName == 'Net-(R3-Pad1)')) || (B.memberOfFootprint('U5') && (A.NetName == '/TRIG' || A.NetName == 'Net-(R4-Pad2)' || A.NetName == 'GND' || A.NetName == 'Net-(Q1-G)' || A.NetName == 'Net-(R3-Pad1)')) || (A.memberOfFootprint('U1') && (B.NetName == 'Net-(R8-Pad2)' || B.NetName == 'GND' || B.NetName == 'Net-(D1-A)' || B.NetName == 'Net-(D2-K)')) || (B.memberOfFootprint('U1') && (A.NetName == 'Net-(R8-Pad2)' || A.NetName == 'GND' || A.NetName == 'Net-(D1-A)' || A.NetName == 'Net-(D2-K)'))"))
# fine pitch escapes: SSD1963 (0.4 mm) and ADS1115 (0.5 mm) pads
(rule "fine_pitch_escape"
   (constraint clearance (min 0.13mm))
   (condition "A.memberOfFootprint('U10') || B.memberOfFootprint('U10') || A.memberOfFootprint('U20') || B.memberOfFootprint('U20') || (A.insideArea('u10_escape') && B.insideArea('u10_escape')) || (A.insideArea('u20_escape') && B.insideArea('u20_escape'))"))
# HS1 (Fischer SK 409 heatsink, floating metal on the insulated BTA24 tab): its solder pins are treated as mains-potential conductors
# (triac insulation = one level): 2.5 mm to any mains copper, 6.4 mm to any SELV copper; the triac's own leads are 15 mm away.
(rule "heatsink_pins_vs_mains"
   (constraint clearance (min 2.5mm))
   (condition "(A.memberOfFootprint('HS1') && ({mainsc('B')})) || (B.memberOfFootprint('HS1') && ({mainsc('A')}))"))
(rule "heatsink_pins_vs_selv"
   (constraint clearance (min 6.4mm))
   (condition "(A.memberOfFootprint('HS1') && {notmains('B')} && B.NetName != '') || (B.memberOfFootprint('HS1') && {notmains('A')} && A.NetName != '')"))
# creepage counterparts: KiCad evaluates creepage per net pair (memberOfFootprint is ignored) and a later creepage rule cannot
# relax an earlier one, so the HS1 pin nets are excluded from mains_to_selv_creepage above and get their own creepage rules.
(rule "heatsink_pins_vs_mains_creepage"
   (constraint creepage (min 2.5mm))
   (condition "(({HSN('A')}) && ({mainsc('B')})) || (({HSN('B')}) && ({mainsc('A')}))"))
# Q1 (BTA24) is mounted on the HS1 plate by design: its courtyard lies inside the heatsink's courtyard.
(rule "q1_on_heatsink_courtyard"
   (constraint courtyard_clearance (min 0mm))
   (severity ignore)
   (condition "(A.Reference == 'Q1' && B.Reference == 'HS1') || (A.Reference == 'HS1' && B.Reference == 'Q1')"))
# keep-out areas as explicit rules: kicad-cli 10 DRC does not report tracks/vias inside rule areas flagged "no tracks/vias"
# (found in pass 4 by the power agent; zone fills do honour them). Pads/footprints in the washer rings are caught by courtyards.
(rule "keepout_washer"
   (constraint disallow track via)
   (condition "A.intersectsArea('M3 washer keep-out')"))
(rule "keepout_inductors_inner"
   (constraint disallow track via)
   (condition "A.intersectsArea('no inner Cu under inductor')"))
(rule "keepout_antenna"
   (constraint disallow track via)
   (condition "A.intersectsArea('antenna keepout')"))
(rule "keepout_mains_inner"
   (constraint disallow track via)
   (condition "A.intersectsArea('mains: no inner copper')"))
(rule "keepout_heatsink"
   (constraint disallow track via)
   (condition "A.intersectsArea('fins_left') || A.intersectsArea('fins_right') || A.intersectsArea('plate')"))
(rule "keepout_u10_corner"
   (constraint disallow track via)
   (condition "A.intersectsArea('U10 corner')"))
(rule "heatsink_pins_vs_selv_creepage"
   (constraint creepage (min 6.4mm))
   (condition "(({HSN('A')}) && {notmains('B')} && B.NetName != '') || (({HSN('B')}) && {notmains('A')} && A.NetName != '')"))
"""
open(DRU, "w", encoding="utf-8").write(dru)
print("dru written")
