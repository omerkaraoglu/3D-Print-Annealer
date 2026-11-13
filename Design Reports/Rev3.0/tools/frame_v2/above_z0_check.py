"""Item 3 verification, part 2: distance of all frame material above Z_PCB (scratchpad/cad/above_z0.json from
fusion/46) to the PCB outline polygon (v1_geometry.json, ears included). Volume inside 'outline + 1 mm' above
Z 0 = 0 exactly when every boundary point is outside the outline by more than 1.0 mm (the material above Z 0 is a
set of prisms whose boundary is sampled densely). Also reports the min distance per lump side."""
import json
import os
import sys

from shapely.geometry import Point, Polygon

SCR = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
       r"\scratchpad\cad")
d = json.load(open(os.path.join(SCR, "above_z0.json")))
g = json.load(open(os.path.join(SCR, "v1_geometry.json")))
poly = Polygon(g["outline_polys"][0])
grown = poly.buffer(1.0)
pts = [Point(p[0], p[1]) for p in d["points"] if p[2] > 1e-4]
inside = sum(1 for p in pts if grown.contains(p))
dmin = min(poly.exterior.distance(p) if not poly.contains(p) else -poly.exterior.distance(p) for p in pts)
left = [p for p in pts if p.x < 100]
right = [p for p in pts if p.x >= 100]
out = {"volume_above_Z0_mm3": d["volume_mm3"], "lumps": d["lumps"], "bbox_abs": d["bbox_abs"],
       "points": len(pts), "points_inside_outline_plus_1mm": inside,
       "min_distance_to_pcb_outline_mm": round(dmin, 3),
       "min_left_mm": round(min(poly.exterior.distance(p) for p in left), 3),
       "min_right_mm": round(min(poly.exterior.distance(p) for p in right), 3),
       "volume_inside_outline_plus_1mm_mm3": 0.0 if inside == 0 and dmin > 1.0 else None}
json.dump(out, open(os.path.join(SCR, "above_z0_check.json"), "w"), indent=1)
print(out)
