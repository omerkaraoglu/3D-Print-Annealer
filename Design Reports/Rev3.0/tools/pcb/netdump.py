import re,sys
from sx import *
d=parse(open(sys.argv[1] if len(sys.argv)>1 else 'rev3.net',encoding='utf-8').read())
comps=find(first(d,'components'),'comp')
print("components",len(comps))
rows=[]
for c in comps:
    ref=first(c,'ref')[1]; val=first(c,'value')[1]
    fp=first(c,'footprint'); fp=fp[1] if fp else ''
    rows.append((ref,val,fp))
def key(r):
    m=re.match(r'([A-Za-z]+)(\d+)',r[0]); return (m.group(1),int(m.group(2))) if m else (r[0],0)
for r in sorted(rows,key=key): print("%-6s %-28s %s"%r)
nets=find(first(d,'nets'),'net')
print("nets",len(nets))
for n in nets:
    name=first(n,'name')[1]
    nodes=find(n,'node')
    pins=["%s.%s"%(first(x,'ref')[1],first(x,'pin')[1]) for x in nodes]
    print("%-22s %3d  %s"%(name,len(pins)," ".join(pins)))
