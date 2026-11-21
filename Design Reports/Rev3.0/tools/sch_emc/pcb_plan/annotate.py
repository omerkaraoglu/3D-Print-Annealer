"""Annotated board image for the phase-2 PCB change plan (abs board coordinates, mm)."""
import json, numpy as np
from PIL import Image, ImageDraw, ImageFont
im = Image.open("pcbimg/board.png").convert("RGB")
S = 1446 / 183.5912; OX, OY = 10.70, 9.70
big = 2
im = im.resize((im.width * big, im.height * big)); S *= big
ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
try:
    f = ImageFont.truetype("arial.ttf", 22); fs = ImageFont.truetype("arial.ttf", 18)
except Exception:
    f = fs = ImageFont.load_default()
P = lambda x, y: ((x - OX) * S, (y - OY) * S)
def box(x0, y0, x1, y1, col, w=4):
    d.rectangle([P(x0, y0), P(x1, y1)], outline=col, width=w)
def txt(x, y, s, col, font=None):
    xy = P(x, y); d.text(xy, s, fill=col, font=font or f, stroke_width=3, stroke_fill=(255, 255, 255, 255))
def line(pts, col, w=5):
    d.line([P(*p) for p in pts], fill=col, width=w)
# free space in the mains band (after RV3 / D6 are placed: see text)
free = np.load("band_free.npy"); R = 0.25
yy, xx = np.where(free)
for y, x in zip(yy, xx):
    d.rectangle([P(45.5 + x * R, 20.5 + y * R), P(45.5 + (x + 1) * R, 20.5 + (y + 1) * R)], fill=(0, 200, 0, 70))
RED, BLU, ORG, MAG, GRY = (220, 0, 0, 255), (0, 70, 220, 255), (230, 120, 0, 255), (170, 0, 170, 255), (90, 90, 90, 255)
# D6 replaces RV2
box(112.4, 29.55, 130.84, 35.45, RED); txt(112.4, 26.0, "D6 1.5KE440CA (DO-201AD, P15.24) replaces RV2", RED)
box(117.97, 30.98, 130.53, 35.42, GRY, 2)
txt(131.5, 30.5, "move PSU_L track >= 1 mm east", RED, fs)
# RV3
box(50.0, 21.75, 66.0, 27.25, RED); txt(47.0, 13.0, "RV3 TVR14431 (as RV1), pads (54.25/61.75, 24.5)", RED)
line([(82.4, 23.5), (82.4, 28.25), (61.75, 28.25), (61.75, 24.5)], ORG, 4)
txt(64.0, 28.6, "LINE_FUSED branch 1.0 mm B.Cu", ORG, fs)
line([(54.25, 24.5), (53.25, 33.0)], ORG, 4); txt(46.5, 29.5, "NEUT to C40.2", ORG, fs)
# U5 pending
box(123.35, 66.31, 131.62, 76.08, MAG); txt(108.0, 77.2, "U5: pending owner decision (same DIP-6)", MAG, fs)
# C9 / C5 at U6
box(137.55, 82.1, 140.45, 83.1, BLU, 3); txt(128.0, 84.0, "C9 1 nF at U6.2", BLU, fs)
box(142.17, 78.1, 145.03, 79.1, BLU, 3); txt(144.0, 75.6, "C5 moved to U6.5", BLU, fs)
line([(29.27, 81.4), (60, 81.4)], BLU, 2); txt(30.0, 77.5, "C5 today (113 mm from U6) -> move", BLU, fs)
# J10 via field and the two caps
box(132.5, 82.3, 139.5, 105.0, GRY, 2); txt(118.0, 106.0, "J10 re-sort vias", GRY, fs)
for (x, y) in ((130.6, 99.0), (141.0, 99.0)):
    box(x - 1.0, y - 0.6, x + 1.0, y + 0.6, BLU, 3)
txt(141.8, 99.5, "C134 / C135 100 nF +5V-GND", BLU, fs)
# RN arrays: value only
box(126.58, 82.88, 128.62, 97.42, GRY, 2); txt(113.0, 88.0, "RN1-RN7 value only", GRY, fs)
txt(46.0, 60.5, "green = free in the mains band (>= 1 mm from courtyards, >= 2.5 mm from tracks)", (0, 120, 0, 255), fs)
im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
crop = im.crop((int(P(40, 8)[0]), int(P(40, 8)[1]), int(P(190, 120)[0]), int(P(190, 120)[1])))
crop.save("pcb_change_plan.png"); print(crop.size)
