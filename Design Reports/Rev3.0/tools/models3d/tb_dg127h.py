"""J20 - DEGSON DG127H-5.08-02P-14-00A(H) screw terminal block (tall 'H' body).

Source: DEGSON customer drawing DG127H-5.08-C01 rev T1 (2020-06-23),
"DG127H-5.08-XXP-1Y-00A(H)", downloaded from degson.com (product 10040002252):
  height 19.10 above the board, depth 8.60, width 5.08 x N, pins 1.00 x 0.60,
  3.50 +-0.30 below the board, pin row 4.05 from the rear face, end pins
  2.54 from the body ends, PCB holes dia 1.40, M3 screws from the top,
  wire entry on the front face.
This settles the open question: the 19.1 mm "profile height" on Ozdisan is the
DG127H body height; the 10.0 mm / 8.1 mm figures belong to the low DG127.
Footprint frame: pin 1 at the origin, pin 2 at x 5.08; the front (wire entry)
faces footprint +y (= model -Y), i.e. the board's left edge with J20 at -90 deg.
ESTIMATED: the front chamfer, cage-opening size and screw recess positions
(read off the drawing at its 2.5:1 scale).
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

N, P = 2, 5.08
H, DEPTH, REAR = 19.10, 8.60, 4.05
PIN_W, PIN_T, PIN_L = 1.00, 0.60, 3.50


def build():
    m = Model("TerminalBlock_DEGSON_DG127H-5.08-02P", "Rev3:TerminalBlock_DEGSON_DG127H-5.08-02P",
              "DEGSON DG127H-5.08-02P 10.16 x 8.60 x 19.10 mm")
    x0, x1 = -P / 2, P * (N - 1) + P / 2
    yf, yr = -(DEPTH - REAR), REAR          # front (wire entry) at -Y, rear at +Y
    body = box(x0, x1, yf, yr, 0, H)
    # front-top chamfer (drawing: front face vertical to ~15.5, then slopes back ~1.3)
    cut = (cq.Workplane("YZ").polyline([(yf - 0.01, 15.5), (yf - 0.01, H + 0.01), (yf + 1.3, H + 0.01)]).close()
           .extrude(x1 - x0 + 2).translate((x0 - 1, 0, 0)))
    body = body.cut(cut)
    for i in range(N):
        xc = i * P
        body = body.cut(box(xc - 1.8, xc + 1.8, yf - 0.1, yf + 4.5, 9.5, 14.3))       # wire entry
        body = body.cut(cyl(xc, 0.0, H - 2.5, H + 0.1, 3.6))                          # screw recess
    m.add("housing", body, "green")
    for i in range(N):
        xc = i * P
        m.add("screw", cyl(xc, 0.0, H - 2.5, H - 0.6, 3.0), "steel")
        m.add("cage", box(xc - 1.6, xc + 1.6, yf + 0.6, yf + 4.4, 9.6, 9.9), "tin")
        m.pin(str(i + 1), box(xc - PIN_W / 2, xc + PIN_W / 2, -PIN_T / 2, PIN_T / 2, -PIN_L, 0.2), "tin")
    return m


if __name__ == "__main__":
    run(build(), render_views=("iso", "top", "side"))
