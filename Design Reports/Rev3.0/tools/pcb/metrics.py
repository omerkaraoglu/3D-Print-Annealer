"""Per-net routed length / via count from tracks.json (for the layout note)."""
import json, math, sys, collections
t = json.load(open(sys.argv[1]))
L = collections.defaultdict(float); V = collections.Counter(); LB = collections.defaultdict(float)
for x in t:
    if x["via"]: V[x["net"]] += 1
    else:
        d = math.hypot(x["x2"] - x["x1"], x["y2"] - x["y1"]); L[x["net"]] += d
        if x["layer"] == "B": LB[x["net"]] += d
def show(nets, title):
    print("== " + title)
    for n in nets:
        if n in L: print("  %-34s %6.1f mm  (B.Cu %5.1f)  vias %d" % (n, L[n], LB[n], V[n]))
bus = sorted(n for n in L if n.startswith("/Display/SSD_"))
lcd = sorted(n for n in L if n.startswith("LCD_"))
rgb = sorted(n for n in L if n.startswith("/Display/") and n[9] in "RGB" and n[10:].isdigit())
show(bus, "SSD1963 8080 bus (33R -> U10)"); show(lcd, "ESP32 -> 33R"); show(rgb, "RGB to FPC")
show(["/Display/PCLK", "/Display/HSYNC", "/Display/VSYNC", "/Display/DE", "I2C_SDA", "I2C_SCL"], "clocks / I2C")
TC = "/Thermocouple front end (K-type, ADS1115)/"
show([TC + "TC_P", TC + "TC_N", TC + "TCF_P", TC + "TCF_N"], "thermocouple")
show(["LINE", "NEUT", "LINE_FUSED", "LINE_FILT", "Net-(PS1-AC/L)", "Net-(PS1-AC/N)", "Net-(Q1-A1)", "Net-(Q1-A2)", "Net-(J4-Pin_1)"], "mains")
show(["+5V", "+3V3", "+1V2", "GND"], "power")
tot = sum(L.values()); print("total track length %.0f mm, vias %d, segments %d" % (tot, sum(V.values()), sum(1 for x in t if not x["via"])))
# bus pair totals (ESP32 pad -> resistor -> U10)
pairs = {"D%d" % i: ("LCD_D%d" % i, "/Display/SSD_D%d" % i) for i in range(8)}
pairs.update({"WR": ("LCD_WR", "/Display/SSD_WR"), "DC": ("LCD_DC", "/Display/SSD_DC"), "CS": ("LCD_CS", "/Display/SSD_CS"), "RST": ("LCD_RST", "/Display/SSD_RST")})
print("== bus end-to-end (ESP32 pin -> SSD1963 pin), limit 80 mm")
for k, (a, b) in pairs.items():
    print("  %-4s %5.1f mm  vias %d" % (k, L[a] + L[b], V[a] + V[b]))
