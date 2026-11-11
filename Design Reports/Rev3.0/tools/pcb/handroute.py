"""Helper for hand-coded ("orderly") routing of the Rev3.0 board.

Coordinates: LOCAL board mm, origin = board top-left corner, x right, y down (board 164 x 99).
(KiCad file coordinates are local + 20 mm on both axes; this module converts.)

    from handroute import *
    R = Router("geom.json")                      # pad lookup
    x, y = R.pad("U10", "7")                    # local mm of a pad centre
    R.track("LCD_D0", "F", [(x, y), (x, y-1.0), (x-2, y-3)], w=0.25)   # polyline, segments must be 0/45/90 deg
    R.via("LCD_D0", 30.0, 50.0, d=0.6, drill=0.3)
    R.save("tracks_display.json")
    R.check("tracks_display.json", nets=["LCD_D0", ...])   # import on the placed board + DRC, prints violations touching your nets

Rules the DRC enforces (do not fight them, design to them):
  SELV default clearance 0.20 mm, track 0.25; Bus class (LCD_*, SSD_*, R/G/B[0-7], PCLK/HSYNC/VSYNC/DE) 0.15 mm clearance;
  inside the SSD1963 (U10) / ADS1115 (U20) escape boxes any copper may be 0.13 mm apart.
  Mains nets: 2.5 mm to other mains copper (1.0 mm within the L-chain LINE/LINE_FUSED/LINE_FILT/PS1-L and within NEUT/PS1-N),
  4.0 mm clearance and 6.4 mm creepage to anything SELV, 1.0 mm to the board edge. Fan-out areas q1_fanout/k1_pins/u1_pins/u5_pins: 0.5 mm.
  Vias: signal 0.6/0.3, power 0.9/0.45, mains 1.2/0.6. Copper to board edge 0.5 mm.
Widths: heater path (J3.1 -> F3 -> BTA12 A2/A1 -> heater pad R1.1 and NEUT J3.2 -> R1.2) 2.5 mm (neck to 1.6 mm at the TO-220 pins);
  other mains 1.0; +5V 1.0; +3V3 1.0 (plane on In2, stubs 0.25 at fine-pitch pads); +1V2 0.25-0.5; BUCK_SW/BL_SW/BL_VIN 1.0;
  VLED_P/N, TFT_VDD 0.6; thermocouple pair 0.3; everything else 0.25.
Planes: In1 = GND everywhere in the SELV region; In2 = +3V3 in the SELV region with a +5V island at x 108..140, y 64..98.
  F.Cu and B.Cu carry GND pours in the SELV region (thermal reliefs). A via to GND/3V3/5V anywhere inside those regions connects.
Keep-outs: no tracks/vias on F.Cu in the 1.8 mm corner squares of the U10 pad ring; no copper under the ESP32 antenna
  (x<7.6, y 36..64); no inner copper under L30 (101.5..109.5, 66.5..74.5) and L11 (103.5..109.5, 76..82); heatsink box
  (100.62..124.62, 24.3..36.3) F.Cu copper-free; the u10_escape/u20_escape/q1_fanout/k1_pins/u1_pins/u5_pins zones are named rule areas only; mains region has no inner copper; slots at (101.5..113.5, 50.6..51.8) and (113..125, 50.6..51.8).
"""
import json, math, subprocess, os, sys
OX, OY = 20.0, 20.0
SCR = os.path.dirname(os.path.abspath(__file__))
KIPY = r"C:/Program Files/KiCad/10.0/bin/python.exe"

class Router:
    def __init__(self, geom="geom.json", placed="rev3_placed.kicad_pcb"):
        self.placed = placed
        g = json.load(open(os.path.join(SCR, geom)))
        self.pads = {}; self.bynet = {}
        for p in g["pads"]:
            self.pads[(p["ref"], p["num"])] = p
            if p["net"]: self.bynet.setdefault(p["net"], []).append((p["ref"], p["num"]))
        self.items = []
    # ---- lookup ----
    def pad(self, ref, num):
        p = self.pads[(str(ref), str(num))]; return (p["x"] - OX, p["y"] - OY)
    def padinfo(self, ref, num):
        p = self.pads[(str(ref), str(num))]
        return {"x": p["x"] - OX, "y": p["y"] - OY, "net": p["net"], "layers": p["layers"], "tht": p["tht"], "w": p["w"], "h": p["h"]}
    def net_pads(self, net): return self.bynet.get(net, [])
    def pads_of(self, ref): return sorted([(k[1], v["net"], round(v["x"] - OX, 3), round(v["y"] - OY, 3)) for k, v in self.pads.items() if k[0] == ref], key=lambda t: (len(t[0]), t[0]))
    # ---- drawing ----
    def track(self, net, layer, pts, w=0.25, strict45=True):
        """polyline on layer 'F' or 'B'; consecutive points must differ by a 0/45/90 degree step when strict45"""
        assert layer in ("F", "B")
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            dx, dy = x2 - x1, y2 - y1
            if abs(dx) < 1e-6 and abs(dy) < 1e-6: continue
            if strict45 and not (abs(dx) < 1e-6 or abs(dy) < 1e-6 or abs(abs(dx) - abs(dy)) < 1e-6):
                raise ValueError("segment %s -> %s on %s is not 0/45/90 degrees" % ((x1, y1), (x2, y2), net))
            self.items.append({"via": False, "net": net, "layer": layer, "x1": x1 + OX, "y1": y1 + OY, "x2": x2 + OX, "y2": y2 + OY, "w": w})
    def via(self, net, x, y, d=0.6, drill=0.3):
        self.items.append({"via": True, "net": net, "x": x + OX, "y": y + OY, "d": d, "drill": drill})
    def save(self, fn):
        json.dump(self.items, open(os.path.join(SCR, fn), "w")); print("saved", fn, len(self.items), "items")
    # ---- checking ----
    def check(self, fn, nets=None, extra_json=(), out="check.kicad_pcb", show=40):
        """import this file (+ extra track files) on the placed board, run DRC, print violations (filtered to nets)"""
        merged = []
        for f in list(extra_json) + [fn]:
            merged += json.load(open(os.path.join(SCR, f)))
        mf = os.path.join(SCR, "_merged_" + os.path.basename(fn))
        json.dump(merged, open(mf, "w"))
        board = os.path.join(SCR, out)
        subprocess.run([KIPY, os.path.join(SCR, "import_tracks.py"), os.path.join(SCR, self.placed), mf, board], check=True, capture_output=True)
        r = subprocess.run([sys.executable, os.path.join(SCR, "drc_run.py"), board, "0"], capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[0] if r.stdout else r.stderr[-500:])
        d = json.load(open(os.path.splitext(board)[0] + "_drc.json", encoding="utf-8"))
        viol = d.get("violations", []); unc = d.get("unconnected_items", [])
        def touches(v):
            if nets is None: return True
            s = json.dumps(v)
            return any(("[%s]" % n) in s for n in nets)
        vv = [v for v in viol if touches(v)]; uu = [u for u in unc if touches(u)]
        print("violations touching your nets:", len(vv), " unconnected:", len(uu))
        for v in vv[:show]:
            its = [it.get("description", "")[:70] for it in v.get("items", [])][:2]
            pos = v.get("items", [{}])[0].get("pos", {})
            print("  %-16s %-70s %s @(%.1f,%.1f)" % (v["type"], v["description"][:70], its, pos.get("x", 0) - OX, pos.get("y", 0) - OY))
        for u in uu[:show]:
            print("  UNC", [it.get("description", "")[:60] for it in u.get("items", [])][:2])
        return vv, uu
    def render(self, board="check.kicad_pcb", png="check.png", x0=0, y0=0, x1=164, y1=99, dpi=300, layers="F.Cu,B.Cu,Edge.Cuts,F.CrtYd"):
        subprocess.run([sys.executable, os.path.join(SCR, "render.py"), os.path.join(SCR, board), os.path.join(SCR, png), layers, "200"], capture_output=True)
        subprocess.run([sys.executable, os.path.join(SCR, "crop.py"), os.path.join(SCR, png + ".svg"), os.path.join(SCR, png), str(x0), str(y0), str(x1), str(y1), str(dpi)], capture_output=True)
        return os.path.join(SCR, png)

if __name__ == "__main__":
    R = Router()
    ref = sys.argv[1] if len(sys.argv) > 1 else "U10"
    for t in R.pads_of(ref): print(t)
