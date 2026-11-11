"""Fischer SK 409 63,5 STC heatsink (45 x 12.7 profile, 63.5 mm tall, two solder pins 35.5 mm apart). Origin = plate centre
on the board; +y = the side the TO-220 sits on. TO-220 (KiCad TO-220-3_Vertical, pads at its y=0, tab back face at y=-3.2)
goes at (x_hs - 2.54, y_hs + 4.7) rot 0 so its back face lies on the plate face (y = +1.5)."""
import uuid, os
LIB=r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/ComponentsLibrary/User Created/Rev3/Rev3.pretty"
def U(): return str(uuid.uuid4())
def text(kind,s,x,y,layer,size=1.0,th=0.15):
    return f'\t(fp_text {kind} "{s}" (at {x} {y}) (layer "{layer}") (uuid "{U()}") (effects (font (size {size} {size}) (thickness {th}))))\n'
def line(x1,y1,x2,y2,layer,w):
    return f'\t(fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{U()}"))\n'
def rect(x1,y1,x2,y2,layer,w):
    return f'\t(fp_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{U()}"))\n'
def thtpad(num,x,y,d,drill):
    return f'\t(pad "{num}" thru_hole circle (at {x:.3f} {y:.3f}) (size {d:.3f} {d:.3f}) (drill {drill:.3f}) (layers "*.Cu" "*.Mask") (remove_unused_layers no) (uuid "{U()}"))\n'
def keepout(name,pts):
    p=" ".join(f"(xy {x:.3f} {y:.3f})" for x,y in pts)
    return (f'\t(zone (net 0) (net_name "") (layers "F.Cu") (uuid "{U()}") (name "{name}") (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.25) (filled_areas_thickness no)\n'
            f'\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed) (copperpour not_allowed) (footprints allowed))\n'
            f'\t\t(fill (thermal_gap 0.5) (thermal_bridge_width 0.5)) (polygon (pts {p})))\n')
name="Heatsink_Fischer_SK409_63.5_STC"
s=(f'(footprint "{name}"\n\t(version 20240108)\n\t(generator "pcbnew")\n\t(generator_version "8.0")\n\t(layer "F.Cu")\n'
   f'\t(descr "Fischer Elektronik SK 409 63,5 STC: extruded PCB heatsink 45 x 12.7 mm profile, 63.5 mm length standing on two solder pins (dia 2.3 max, 35.5 mm apart), 5.6 K/W (80 K rise), TO-220 clip/screw mounted on the 3 mm plate (hole P 18.3 mm above the board). Origin = plate centre, TO-220 side +y: place TO-220-3_Vertical at (x-2.54, y+4.7) rot 0.")\n'
   f'\t(tags "heatsink fischer sk409 to-220")\n\t(attr through_hole)\n')
s+=text("reference","REF**",0,-8.5,"F.SilkS")+text("value",name,0,8.5,"F.Fab")
s+=thtpad(1,-17.75,0,4.2,2.8)+thtpad(2,17.75,0,4.2,2.8)
# fab: plate, fin blocks, TO-220 position
s+=rect(-22.5,-1.5,22.5,1.5,"F.Fab",0.1)
s+=rect(-22.5,-6.35,-13.1,6.35,"F.Fab",0.1)+rect(13.1,-6.35,22.5,6.35,"F.Fab",0.1)
s+=rect(-5.0,1.5,5.0,6.0,"F.Fab",0.1)+text("user","TO-220",0,3.75,"F.Fab",0.8,0.12)
# silk: outer envelope (open where the triac leads are)
for (x1,y1,x2,y2) in [(-22.75,-6.6,-12.9,-6.6),(-22.75,6.6,-12.9,6.6),(12.9,-6.6,22.75,-6.6),(12.9,6.6,22.75,6.6),
                      (-22.75,-6.6,-22.75,6.6),(22.75,-6.6,22.75,6.6),(-12.9,-6.6,-12.9,-1.75),(-12.9,1.75,-12.9,6.6),
                      (12.9,-6.6,12.9,-1.75),(12.9,1.75,12.9,6.6),(-12.9,-1.75,12.9,-1.75)]:
    s+=line(x1,y1,x2,y2,"F.SilkS",0.12)
s+=rect(-23.0,-6.85,23.0,6.85,"F.CrtYd",0.05)
# no copper (tracks/vias/pour) under the fins and the plate on F.Cu
s+=keepout("fins_left",[(-22.75,-6.6),(-12.9,-6.6),(-12.9,6.6),(-22.75,6.6)])
s+=keepout("fins_right",[(12.9,-6.6),(22.75,-6.6),(22.75,6.6),(12.9,6.6)])
s+=keepout("plate",[(-13.0,-1.75),(13.0,-1.75),(13.0,1.75),(-13.0,1.75)])
open(os.path.join(LIB,name+".kicad_mod"),"w",encoding="utf-8").write(s+")\n"); print("wrote",name)
