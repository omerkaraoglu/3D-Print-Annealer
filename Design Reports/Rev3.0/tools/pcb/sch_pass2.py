"""Schematic edits for layout pass 2: Q1 -> BTA24-800CWRG, R1 = 1 kW heater, add HS1 (SK 409 63,5 STC) with NC pins."""
import re, uuid
F=r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer/3dFilamentDryer.kicad_sch"
s=open(F,encoding="utf-8").read()
def rep(old,new,ref):
    global s
    a=s.index(f'(property "Reference" "{ref}"'); b=s.index("(instances",a); blk=s[a:b]
    assert blk.count(old)==1,(ref,old,blk.count(old)); s=s[:a]+blk.replace(old,new)+s[b:]
rep('(property "Value" "BTA12-600BW"', '(property "Value" "BTA24-800CWRG"','Q1')
rep('(property "Datasheet" "https://www.st.com/resource/en/datasheet/bta16.pdf"', '(property "Datasheet" "https://www.ozdisan.com/p/discrete-triyaklar-420/stm-bta24-800cwrg-360751"','Q1')
rep('(property "Description" "16A RMS, 600V Off-State Voltage, 50mA Sensitivity, Snubberless, Insulated, Triac, TO-220"',
    '(property "Description" "Triac 25 A RMS, 800 V, IGT 35 mA (CW), Snubberless, insulated TO-220AB (2500 V RMS), Rth(j-c) 1.7 K/W; 1 kW heater = 4.35 A RMS -> 3.7 W, on HS1"','Q1')
rep('(property "Heatsink Needed" "5.6°C/W"', '(property "Heatsink Needed" "HS1 Fischer SK 409 63,5 STC (5.6 K/W)"','Q1')
rep('(property "Value" "Heater 1300W"', '(property "Value" "Heater 1kW"','R1')
rep('(property "Description" "Resistive heater (500W safe, 550W fuse 100%)"', '(property "Description" "Resistive heater 1 kW at 230 V (4.35 A RMS), fused by F3 8 A, switched by Q1"','R1')
# HS1 symbol
lib=open("heatsink_sym.txt",encoding="utf-8").read().replace('(symbol "Heatsink_Pad_2Pin"','(symbol "Mechanical:Heatsink_Pad_2Pin"',1)
assert '(symbol "Mechanical:Heatsink_Pad_2Pin"' not in s
i=s.index("(lib_symbols")+len("(lib_symbols"); s=s[:i]+"\n\t\t"+lib.replace("\n","\n\t")+s[i:]
ats=[(float(a),float(b)) for a,b in re.findall(r'\(at (-?[\d\.]+) (-?[\d\.]+)',s)]
for X,Y in [(330.2,261.62),(355.6,261.62),(304.8,261.62),(381.0,261.62),(381.0,228.6),(254.0,261.62)]:
    if not [t for t in ats if abs(t[0]-X)<16 and abs(t[1]-Y)<16]: break
else: raise SystemExit('no free spot')
print('HS1 at',X,Y)
def prop(n,v,dy,hide):
    return (f'\t\t(property "{n}" "{v}"\n\t\t\t(at {X} {Y+dy} 0)\n'+("\t\t\t(hide yes)\n" if hide else "")+
            f'\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
sym=(f'\t(symbol\n\t\t(lib_id "Mechanical:Heatsink_Pad_2Pin")\n\t\t(at {X} {Y} 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim yes)\n'
     f'\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "{uuid.uuid4()}")\n'
     +prop("Reference","HS1",-7.62,False)+prop("Value","SK 409 63,5 STC",-5.08,False)
     +prop("Footprint","Rev3:Heatsink_Fischer_SK409_63.5_STC",5.08,True)
     +prop("Datasheet","https://www.digikey.com/en/products/detail/fischer-elektronik/SK-409-63-5-STC-TO-220/25833367",7.62,True)
     +prop("Description","Heatsink for Q1: Fischer SK 409 63,5 STC, 45 x 12.7 x 63.5 mm, 5.6 K/W (natural convection, 80 K rise), two solder pins, TO-220 clip/screw mount; DigiKey 5496-SK40963,5STCTO220-ND",10.16,True)
     +prop("MPN","SK 409 63,5 STC TO 220",12.7,True)+prop("Manufacturer","Fischer Elektronik",15.24,True)
     +f'\t\t(pin "1"\n\t\t\t(uuid "{uuid.uuid4()}")\n\t\t)\n\t\t(pin "2"\n\t\t\t(uuid "{uuid.uuid4()}")\n\t\t)\n'
     f'\t\t(instances\n\t\t\t(project "3dFilamentDryer"\n\t\t\t\t(path "/ea3996f2-7d6b-4a86-86ab-4ed62213f41f"\n\t\t\t\t\t(reference "HS1")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n')
nc="".join(f'\t(no_connect\n\t\t(at {X+dx} {Y+2.54})\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n' for dx in (-2.54,2.54))
j=s.index("\t(sheet_instances"); s=s[:j]+sym+nc+s[j:]
open(F,"w",encoding="utf-8").write(s); print("schematic written")
