# Same-layer crossing checker: flags intersecting segments on the same layer,
# reporting the NET LABELS involved so routing can be fixed net-by-net.
import runpy, itertools
ns=runpy.run_path("gen_pcb.py")
traces=ns['traces']
def segs(pts): return [(pts[i],pts[i+1]) for i in range(len(pts)-1)]
def ccw(A,B,C): return (C[1]-A[1])*(B[0]-A[0])>(B[1]-A[1])*(C[0]-A[0])
def inter(s,t):
    A,B=s;C,D=t
    for p in (A,B):
        for q in (C,D):
            if abs(p[0]-q[0])<1e-6 and abs(p[1]-q[1])<1e-6: return False
    return ccw(A,C,D)!=ccw(B,C,D) and ccw(A,B,C)!=ccw(A,B,D)
S={'top':[],'bot':[]}
jmp=set()
for lay,w,pts,lab in traces:
    if lay in ('jmp','logo'): jmp.add(lab); continue      # flying wire: cannot short
    for s in segs(pts): S[lay].append((s,lab))
pairs=set()
for lay in ('top','bot'):
    for (s,la),(t,lb) in itertools.combinations(S[lay],2):
        if la==lb: continue                       # same net can touch itself
        if inter(s,t): pairs.add((lay,tuple(sorted((la or '?',lb or '?')))))
for lay,(a,b) in sorted(pairs):
    print(f"  {lay} CROSS: {a} X {b}")
print(f"total copper crossing net-pairs: {len(pairs)}")
if jmp: print(f"jumper wires ({len(jmp)}): {', '.join(sorted(jmp))}")
