s=open(r'C:/Program Files/KiCad/10.0/share/kicad/symbols/Mechanical.kicad_sym',encoding='utf-8').read()
i=s.index('(symbol "Heatsink_Pad_2Pin"'); depth=0; q=False; j=i
while True:
    c=s[j]
    if c=='"' and s[j-1]!=chr(92): q=not q
    elif not q:
        if c=='(': depth+=1
        elif c==')':
            depth-=1
            if depth==0: break
    j+=1
blk=s[i:j+1]; open('heatsink_sym.txt','w',encoding='utf-8').write(blk); print(len(blk), repr(blk[-80:]))
