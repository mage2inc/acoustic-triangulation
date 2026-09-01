#!/usr/bin/env python3
"""Full DRC for the node carrier — catches what check_cross.py CANNOT: a trace
running OVER a pad it isn't connected to (a copper short), plus pad/pad, pad/hole,
trace/trace clearances and outline containment. Run after every gen_pcb.py edit.
  $ python3 drc.py            # prints a PASS/FAIL line per check
Exit code 0 = all pass, 1 = any fail. check_cross.py stays as the crossing view."""
import runpy, itertools, math, sys
ns=runpy.run_path('gen_pcb.py')
pads,holes,traces,OUT,esp=ns['pads'],ns['holes'],ns['traces'],ns['OUTLINE'],ns['esp']
CLR=0.25                                        # min copper-copper clearance we hold
def d2seg(px,py,a,b):
    ax,ay=a;bx,by=b;dx,dy=bx-ax,by-ay
    if dx==dy==0:return math.hypot(px-ax,py-ay)
    t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(px-(ax+t*dx),py-(ay+t*dy))
fails=[]
def rep(name,ok,detail=''):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{'  '+detail if detail else ''}")
    if not ok: fails.append(name)

# real net of a pad: an ESP header pin carries its routed SIGNAL, not its pin name
espset={(round(esp[k][0],2),round(esp[k][1],2)):k for k in esp}
pinnet={}
for lay,w,pts,lab in traces:
    for e in (pts[0],pts[-1]):
        k=espset.get((round(e[0],2),round(e[1],2)))
        if k and lab: pinnet.setdefault(k,lab)
def padnet(x,y,n):
    k=espset.get((round(x,2),round(y,2))); return pinnet.get(k,n) if k else n
POWER={'3V3','GND','CVDD','BAT'}

# 1. trace OVER a foreign pad  (the class the crossing-checker is blind to)
sh=[]
for lay,w,pts,lab in traces:
    if lay not in('top','bot'):continue
    ep={(round(pts[0][0],2),round(pts[0][1],2)),(round(pts[-1][0],2),round(pts[-1][1],2))}
    for x,y,n,l,p,d,h in pads:
        pn=padnet(x,y,n)
        if (round(x,2),round(y,2)) in ep or lab==pn or (lab in POWER and pn in POWER):continue
        g=min(d2seg(x,y,pts[i],pts[i+1]) for i in range(len(pts)-1))-d/2-w/2
        if g< -0.05: sh.append(f"{lab}({lay}) over {l or n} {-g:.2f}mm")
rep("trace-over-pad shorts",not sh,f"{len(sh)}: "+"; ".join(sh[:6]) if sh else "0")

# 2. pad <-> pad (different net)
pp=[f"{l1 or n1}/{l2 or n2} {g:.2f}" for (x1,y1,n1,l1,p1,d1,h1),(x2,y2,n2,l2,p2,d2,h2)
    in itertools.combinations(pads,2)
    if n1!=n2 and (g:=math.hypot(x1-x2,y1-y2)-d1/2-d2/2)<CLR]
rep("pad-pad clearance",not pp,f"min-violations: {pp[:5]}" if pp else "ok")

# 3. pad <-> mount hole
ph=[f"{l or n} {g:.2f}" for x,y,n,l,p,d,h in pads for hx,hy,hd,k in holes
    if (g:=math.hypot(x-hx,y-hy)-d/2-hd/2)<CLR]
rep("pad-mounthole clearance",not ph,str(ph) if ph else "ok")

# 4. trace <-> trace, same layer, different net (parallel proximity + crossings)
def s2s(a,b,c,d):return min(d2seg(a[0],a[1],c,d),d2seg(b[0],b[1],c,d),d2seg(c[0],c[1],a,b),d2seg(d[0],d[1],a,b))
seg={'top':[],'bot':[]}
for lay,w,pts,lab in traces:
    if lay in seg:
        for i in range(len(pts)-1): seg[lay].append((pts[i],pts[i+1],w,lab))
tt=[]
for lay in seg:
    for (a,b,w1,l1),(c,d,w2,l2) in itertools.combinations(seg[lay],2):
        if l1==l2:continue
        if (g:=s2s(a,b,c,d)-w1/2-w2/2)<CLR-0.05: tt.append(f"{lay}:{l1}/{l2} {g:.2f}")
rep("trace-trace clearance",not tt,str(tt[:5]) if tt else "ok")

# 5. everything inside the outline
def inside(x,y,P):
    c=False;j=len(P)-1
    for i in range(len(P)):
        xi,yi=P[i];xj,yj=P[j]
        if((yi>y)!=(yj>y)) and (x<(xj-xi)*(y-yi)/(yj-yi+1e-12)+xi):c=not c
        j=i
    return c
oc=[l or n for x,y,n,l,p,d,h in pads if not inside(x,y,OUT)]+\
   [lab for lay,w,pts,lab in traces for (x,y) in pts if not inside(x,y,OUT)]
rep("outline containment",not oc,str(set(oc)) if oc else "ok")

# 6. part-body collisions (real footprint bodies must not touch; margin for variation)
BM=0.6
bodies=ns.get('part_bodies',[])
bc=[]
for i in range(len(bodies)):
    for j in range(i+1,len(bodies)):
        n1,x1,y1,w1,h1=bodies[i]; n2,x2,y2,w2,h2=bodies[j]
        gx=abs(x1-x2)-(w1+w2)/2; gy=abs(y1-y2)-(h1+h2)/2
        gap=max(gx,gy)                              # boxes overlap iff BOTH gaps<0
        if gap<BM: bc.append(f"{n1}<->{n2} {gap:.2f}")
rep("part-body clearance",not bc,f">= {BM}mm: "+"; ".join(bc) if bc else "ok")

# 7. RF keepout must not strand a ground pad (only ANT/ANT_PAD may sit inside)
k=ns.get('ant_keepout')
if k:
    gset=set((round(p[0],2),round(p[1],2)) for p in ns['gnd_pads'])
    stranded=[l or n for x,y,n,l,p,d,h in pads
              if k[0]<=x<=k[2] and k[1]<=y<=k[3] and (round(x,2),round(y,2)) in gset]
    rep("RF-keepout no stranded GND",not stranded,str(stranded) if stranded else "ok (only ANT/ANT_PAD inside)")

print(f"\nDRC: {'ALL PASS' if not fails else 'FAIL -> '+', '.join(fails)}")
sys.exit(1 if fails else 0)
