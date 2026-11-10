import uuid, re, os
LIB=r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/ComponentsLibrary/User Created/Rev3/Rev3.pretty"
def U(): return str(uuid.uuid4())
def text(kind,s,x,y,layer,size=1.0,th=0.15):
    return f'\t(fp_text {kind} "{s}" (at {x} {y}) (layer "{layer}") (uuid "{U()}") (effects (font (size {size} {size}) (thickness {th}))))\n'
def line(x1,y1,x2,y2,layer,w):
    return f'\t(fp_line (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{U()}"))\n'
def rect(x1,y1,x2,y2,layer,w):
    return f'\t(fp_rect (start {x1:.3f} {y1:.3f}) (end {x2:.3f} {y2:.3f}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{U()}"))\n'
def circle(cx,cy,r,layer,w):
    return f'\t(fp_circle (center {cx:.3f} {cy:.3f}) (end {cx+r:.3f} {cy:.3f}) (stroke (width {w}) (type solid)) (fill no) (layer "{layer}") (uuid "{U()}"))\n'
def smdpad(num,x,y,sx,sy,shape="roundrect",rr=0.25):
    s=f'\t(pad "{num}" smd {shape} (at {x:.3f} {y:.3f}) (size {sx:.3f} {sy:.3f}) (layers "F.Cu" "F.Paste" "F.Mask")'
    if shape=="roundrect": s+=f' (roundrect_rratio {rr})'
    return s+f' (uuid "{U()}"))\n'
def thtpad(num,x,y,d,drill,shape="circle"):
    s=f'\t(pad "{num}" thru_hole {shape} (at {x:.3f} {y:.3f}) (size {d:.3f} {d:.3f}) (drill {drill:.3f}) (layers "*.Cu" "*.Mask")'
    if shape=="roundrect": s+=' (roundrect_rratio 0.25)'
    return s+f' (remove_unused_layers no) (uuid "{U()}"))\n'
def header(name,descr,tags,attr):
    return (f'(footprint "{name}"\n\t(version 20240108)\n\t(generator "pcbnew")\n\t(generator_version "8.0")\n'
            f'\t(layer "F.Cu")\n\t(descr "{descr}")\n\t(tags "{tags}")\n\t(attr {attr})\n')
def write(name,body):
    open(os.path.join(LIB,name+".kicad_mod"),"w",encoding="utf-8").write(body+")\n")
    print("wrote",name)

# ---------- Connfly DS1020-09-xxVBT1A ----------
def connfly(N):
    name=f"Connfly_DS1020-09-{N:02d}VBT1A_1x{N:02d}_P0.5mm_Horizontal"
    D=5.75 if N>=35 else 5.2
    W=0.5*N+5.6
    ysig=-D/2            # signal pad centre: 0.9 mm outside, 0.9 mm inside the rear body edge
    yanc=-D/2+1.9        # anchor pad: top edge 1.2 mm below the signal pad top edge (Connfly drawing: 4.40 overall, 3.20 anchor)
    xanc=(N-1)/4+0.7+1.25
    s=header(name,f"Connfly DS1020-09-{N:02d}VBT1A, 0.5 mm pitch {N}-pin FPC/FFC connector, right-angle SMT, lower (PCB-side) contact, flip lock; land pattern from Connfly drawing C-DS1020-09-XXXXX-E (pads 0.30x1.80 on 0.50 pitch, anchors 2.50x3.20); body 0.5N+5.6 x {D} mm","connector fpc ffc 0.5mm connfly","smd")
    s+=text("reference","REF**",0,-D/2-2.4,"F.SilkS")
    s+=text("value",name,0,D/2+1.6,"F.Fab")
    s+=text("user","${REFERENCE}",0,0.6,"F.Fab",0.8,0.12)
    for i in range(N):
        x=-(N-1)/4+0.5*i
        s+=smdpad(str(i+1),x,ysig,0.3,1.8,"roundrect",0.25)
    s+=smdpad("MP",-xanc,yanc,2.5,3.2,"rect")
    s+=smdpad("MP", xanc,yanc,2.5,3.2,"rect")
    s+=rect(-W/2,-D/2,W/2,D/2,"F.Fab",0.1)
    s+=line(-W/2+1,D/2,-W/2,D/2-1,"F.Fab",0.1)
    s+=line(-W/2-0.1,D/2+0.1,W/2+0.1,D/2+0.1,"F.SilkS",0.12)
    s+=line(-W/2-0.1,D/2+0.1,-W/2-0.1,yanc+1.6+0.3,"F.SilkS",0.12)
    s+=line(W/2+0.1,D/2+0.1,W/2+0.1,yanc+1.6+0.3,"F.SilkS",0.12)
    x1=-(N-1)/4
    s+=line(x1-0.45,ysig-0.9-0.3,x1-0.45,ysig-0.9-0.3-0.8,"F.SilkS",0.15)
    cx=max(W/2,xanc+1.25)+0.5
    cy1=ysig-0.9-0.5; cy2=D/2+0.5
    s+=rect(-cx,cy1,cx,cy2,"F.CrtYd",0.05)
    write(name,s)
connfly(40); connfly(6)

# ---------- Core Master SRI0605B ----------
name="L_CoreMaster_SRI0605B"
s=header(name,"Core Master SRI0605B shielded SMD power inductor, 6.6x6.2x5.0 mm max; pad layout from Core Master PAD and RELIABILITY and PACKING FOR SRI (L 7.0, G 2.5, H 1.8)","inductor smd shielded coremaster sri0605b","smd")
s+=text("reference","REF**",0,-4.4,"F.SilkS"); s+=text("value",name,0,4.4,"F.Fab"); s+=text("user","${REFERENCE}",0,0,"F.Fab",0.8,0.12)
s+=smdpad("1",-2.375,0,2.25,1.8,"roundrect",0.2); s+=smdpad("2",2.375,0,2.25,1.8,"roundrect",0.2)
s+=rect(-3.3,-3.1,3.3,3.1,"F.Fab",0.1); s+=circle(0,0,2.9,"F.Fab",0.1)
for sx in (-1,1):
    s+=line(-3.4,sx*3.2,3.4,sx*3.2,"F.SilkS",0.12)
    s+=line(sx*3.4,-3.2,sx*3.4,-1.2,"F.SilkS",0.12); s+=line(sx*3.4,3.2,sx*3.4,1.2,"F.SilkS",0.12)
s+=rect(-3.8,-3.6,3.8,3.6,"F.CrtYd",0.05)
write(name,s)

# ---------- Viking PCD0403 ----------
name="L_Viking_PCD0403"
s=header(name,"Viking PCD0403 unshielded SMD power inductor 4.5x4.0x3.0 mm; pads 1.75x4.5 on 3.25 mm pitch (LCSC/EasyEDA land pattern IND-SMD_L4.5-W4.0_PCD0403)","inductor smd viking pcd0403","smd")
s+=text("reference","REF**",0,-3.3,"F.SilkS"); s+=text("value",name,0,3.3,"F.Fab"); s+=text("user","${REFERENCE}",0,0,"F.Fab",0.6,0.1)
s+=smdpad("1",-1.625,0,1.75,4.5,"roundrect",0.2); s+=smdpad("2",1.625,0,1.75,4.5,"roundrect",0.2)
s+=rect(-2.0,-2.25,2.0,2.25,"F.Fab",0.1)
s+=line(-2.1,-2.35,2.1,-2.35,"F.SilkS",0.12); s+=line(-2.1,2.35,2.1,2.35,"F.SilkS",0.12)
s+=rect(-2.75,-2.5,2.75,2.5,"F.CrtYd",0.05)
write(name,s)

# ---------- DEGSON DG127H-5.08-02P ----------
name="TerminalBlock_DEGSON_DG127H-5.08-02P"
s=header(name,"DEGSON DG127H-5.08-02P-14-00AH screw terminal block, 2 poles, 5.08 mm pitch, 12 A / 300 V, 26-14 AWG, horizontal wire entry (Ozdisan listing); land pattern: 1.3 mm drill / 2.6 mm pad (IPC-2222 level B for 1.0 mm square pins), body envelope 10.2 x 9.8 mm taken from the Phoenix MKDS 1,5/2-5.08 placeholder - verify against the DEGSON drawing","terminal block screw degson dg127h 5.08","through_hole")
s+=text("reference","REF**",2.54,-6.6,"F.SilkS"); s+=text("value",name,2.54,6.6,"F.Fab"); s+=text("user","${REFERENCE}",2.54,0,"F.Fab",0.8,0.12)
s+=thtpad("1",0,0,2.6,1.3,"roundrect"); s+=thtpad("2",5.08,0,2.6,1.3,"circle")
s+=rect(-2.54,-4.3,7.62,5.5,"F.Fab",0.1); s+=line(-2.54,2.9,7.62,2.9,"F.Fab",0.1)
s+=rect(-2.65,-4.41,7.73,5.61,"F.SilkS",0.12); s+=line(-2.65,2.9,7.73,2.9,"F.SilkS",0.12)
s+=line(-2.65,-4.41,-2.65,-5.2,"F.SilkS",0.15); s+=line(-2.65,-5.2,-1.6,-5.2,"F.SilkS",0.15)
s+=rect(-3.04,-4.8,8.12,6.0,"F.CrtYd",0.05)
write(name,s)

# ---------- LFU09V-103 copied from the Rev2.1 board ----------
src=open(r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/3dFilamentDryer_Rev2.1.kicad_pcb",encoding="utf-8").read()
i=src.index('(footprint "Inductor_THT:LFU09V-103"')
depth=0; j=i
while True:
    c=src[j]
    if c=='(': depth+=1
    elif c==')':
        depth-=1
        if depth==0: break
    j+=1
fp=src[i:j+1]
fp=fp.replace('(footprint "Inductor_THT:LFU09V-103"','(footprint "LFU09V-103"',1)
fp=re.sub(r'\n\t\t\(at [^\n]*\)\n','\n',fp,count=1)
fp=re.sub(r'\n\t\t\(path "[^"]*"\)','',fp)
fp=re.sub(r'\n\t\t\(sheetname "[^"]*"\)','',fp); fp=re.sub(r'\n\t\t\(sheetfile "[^"]*"\)','',fp)
fp=re.sub(r'\(net \d+ "[^"]*"\)\s*','',fp)
fp=re.sub(r'\n\s*\(pintype "[^"]*"\)','',fp); fp=re.sub(r'\n\s*\(pinfunction "[^"]*"\)','',fp)
fp=re.sub(r'\(uuid "[^"]*"\)',lambda m:f'(uuid "{U()}")',fp)
fp="\n".join(l[1:] if l.startswith("\t\t") else l for l in fp.split("\n"))
fp=fp.replace('(footprint "LFU09V-103"','(footprint "LFU09V-103"\n\t(version 20240108)',1) if '(version' not in fp else fp
open(os.path.join(LIB,"LFU09V-103.kicad_mod"),"w",encoding="utf-8").write(fp+"\n")
print("wrote LFU09V-103")
