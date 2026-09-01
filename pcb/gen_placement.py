#!/usr/bin/env python3
"""Placement / assembly render — REAL module body sizes + overlap assertion.
Pulls pad coords from gen_pcb.py so placement == footprint."""
import runpy, os, itertools
ns=runpy.run_path(os.path.join(os.path.dirname(__file__),'gen_pcb.py'))
esp,mic,gps,lora=ns['esp'],ns['mic'],ns['gps'],ns['lora']
holes=ns['holes']; BW,BH=ns['BW'],ns['BH']; cap=ns['cap']; capn=ns['capn']; OUTLINE=ns['OUTLINE']

def centroid(d,keys=None):
    ks=keys or list(d); xs=[d[k][0] for k in ks]; ys=[d[k][1] for k in ks]
    return (sum(xs)/len(xs),sum(ys)/len(ys))

# REAL body footprints (w,h mm) centered on their pin cluster centroid
BODIES=[]  # (x0,y0,w,h,label,sub,color,pin1)
def add_body(cx,cy,w,h,label,sub,color,pin1):
    BODIES.append((cx-w/2,cy-h/2,w,h,label,sub,color,pin1))

ecx,ecy=centroid(esp,['TX','RX','G1','G2','G3','G4','G5','G6','G7','5V','GND','3V3','G13','G12','G11','G10','G9','G8'])
add_body(ecx,ecy,18.0,22.52,'ESP32-S3 SuperMini','22.52 x 18 mm · soldered flat (castellated)','#2e6da4',esp['TX'])
mcx,mcy=centroid(mic); add_body(mcx,mcy,13.9,13.9,'INMP441','I2S mic · Ø13.9 round','#6a4fb0',mic['MVDD'])
gcx,_=centroid(gps); gtop=gps['PVCC'][1]
add_body(gcx,gtop+6.0,17.0,16.0,'ATGM336H','GPS 1x5 · ANT end hangs off top','#1f8a70',gps['PVCC'])
lcx,lcy=centroid(lora); add_body(lcx,lcy,12.70,15.24,'RYLR689','LoRa 12.7×15.24 · 1.27mm','#b0562e',lora['LGND'])

# ---- overlap assertion (>=2mm required gap between bodies) ----
GAP=2.0
def rects_overlap(a,b):
    ax0,ay0,aw,ah=a[:4]; bx0,by0,bw,bh=b[:4]
    return not (ax0+aw+GAP<=bx0 or bx0+bw+GAP<=ax0 or ay0+ah+GAP<=by0 or by0+bh+GAP<=ay0)
bad=[(a[4],b[4]) for a,b in itertools.combinations(BODIES,2) if rects_overlap(a,b)]
if bad:
    print("BODY OVERLAP:",bad)
else:
    print("bodies OK — no overlaps (>=%gmm gaps)"%GAP)
# hole clearance: no body within (hole_r + 2mm) of a mount/dowel centre
def body_hits_hole(b,hx,hy,r):
    x0,y0,w,h=b[:4]
    cx=min(max(hx,x0),x0+w); cy=min(max(hy,y0),y0+h)   # closest point on rect
    return (cx-hx)**2+(cy-hy)**2 < r*r
hbad=[(b[4],k) for b in BODIES for hx,hy,d,k in holes if body_hits_hole(b,hx,hy,d/2+2.0)]
print("HOLE CLEARANCE:",hbad if hbad else "OK — no body within 2mm of any hole")

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyBboxPatch,Circle,FancyArrow,Polygon
fig,ax=plt.subplots(figsize=(15,8.6),dpi=150); ax.set_aspect('equal')
ax.add_patch(Polygon(OUTLINE,closed=True,fc='#0d5c2f',ec='k',lw=2.2,zorder=0,alpha=.10))
ax.add_patch(Polygon(OUTLINE,closed=True,fill=False,ec='k',lw=2.2,zorder=6))

def pins(coords,z=5):
    for (x,y) in coords:
        ax.add_patch(Circle((x,y),0.9,fc='#d4b106',ec='#5c4b00',lw=.4,zorder=z))
        ax.add_patch(Circle((x,y),0.5,fc='white',zorder=z+1))

for x0,y0,w,h,label,sub,color,pin1 in BODIES:
    if label.startswith('INMP441'):          # round mic module
        ax.add_patch(Circle((x0+w/2,y0+h/2),w/2,fc=color,ec='#222',lw=1.4,alpha=.92,zorder=3))
    else:
        ax.add_patch(FancyBboxPatch((x0,y0),w,h,boxstyle="round,pad=0.2,rounding_size=1",
                     fc=color,ec='#222',lw=1.4,alpha=.92,zorder=3))
    ax.text(x0+w/2,y0+h/2+1.1,label,ha='center',va='center',fontsize=8.3,weight='bold',color='white',zorder=5)
    ax.text(x0+w/2,y0+h/2-1.5,sub,ha='center',va='center',fontsize=5.8,color='#eee',zorder=5)
    ax.add_patch(Circle(pin1,0.75,fc='#ffe08a',ec='k',lw=.5,zorder=6))
    ax.text(pin1[0]-1.4,pin1[1],'1',ha='right',va='center',fontsize=5.5,color='white',weight='bold',zorder=6)

pins(list(esp.values())); pins(list(mic.values())); pins(list(gps.values()))
for (x,y) in lora.values():                 # LoRa 1.27mm pads: 0.9 dia / 0.6 hole (small)
    ax.add_patch(Circle((x,y),0.45,fc='#d4b106',ec='#5c4b00',lw=.3,zorder=5))
    ax.add_patch(Circle((x,y),0.3,fc='white',zorder=6))

# power section: battery pads -> LDO (TO-92) + Cin/Cout (0805) -> C2 buffer e-cap
g=lambda k: ns[k]; PWRPAD=ns['PWRPAD']
batp,batn=g('batp'),g('batn'); ldo_in,ldo_g,ldo_out=g('ldo_in'),g('ldo_g'),g('ldo_out')
cinP,cinG,coutP,coutG=g('cinP'),g('cinG'),g('coutP'),g('coutG'); sc_p,sc_m=g('sc_p'),g('sc_m')
def bigpad(p,l,col='#5c4b00'):
    ax.add_patch(Circle((p[0],p[1]),PWRPAD/2,fc='#d4b106',ec=col,lw=.6,zorder=5))
    ax.add_patch(Circle((p[0],p[1]),0.5,fc='white',zorder=6))
    if l: ax.text(p[0]+1.9,p[1],l,ha='left',va='center',fontsize=7,weight='bold',color=col,zorder=7)
def smallpad(p):                                        # TO-92 lead (through-hole)
    ax.add_patch(Circle((p[0],p[1]),0.9,fc='#d4b106',ec='#5c4b00',lw=.5,zorder=5))
    ax.add_patch(Circle((p[0],p[1]),0.5,fc='white',zorder=6))
def smd(p):                                             # 0805 SMD land (no hole)
    ax.add_patch(Rectangle((p[0]-0.65,p[1]-0.7),1.3,1.4,fc='#c8a415',ec='#5c4b00',lw=.4,zorder=5))
# TO-92 body (semicircle-ish) behind the 3 leads
ax.add_patch(Circle((ldo_in[0],ldo_in[1]+0.4),2.3,fc='#333',ec='#111',lw=1,alpha=.85,zorder=3))
for p,l in [(ldo_g,'G'),(ldo_in,'VI'),(ldo_out,'VO')]:
    smallpad(p); ax.text(p[0],p[1]+2.6,l,ha='center',va='bottom',fontsize=5,color='#333',zorder=7)
ax.text(ldo_in[0],ldo_in[1]-2.6,'U5 MCP1700  (GND|VIN|VOUT)',ha='center',va='top',fontsize=5.2,weight='bold',color='#333',zorder=7)
for p in (cinP,cinG,coutP,coutG): smd(p)
ax.text((cinP[0]+cinG[0])/2,cinP[1]-1.4,'Cin 1µF',ha='center',va='top',fontsize=4.4,color='#666',zorder=7)
ax.text((coutP[0]+coutG[0])/2,coutP[1]-1.4,'Cout 1µF',ha='center',va='top',fontsize=4.4,color='#666',zorder=7)
bigpad(batp,'+BAT'); bigpad(batn,'−')
ax.add_patch(Circle(((sc_p[0]+sc_m[0])/2,(sc_p[1]+sc_m[1])/2),4.25,fc='#3a4a6b',ec='#1a2440',lw=1.2,alpha=.85,zorder=3))
bigpad(sc_p,'+'); bigpad(sc_m,'−')
ax.text((sc_p[0]+sc_m[0])/2,sc_p[1]+5.0,'C2 470µF e-cap',ha='center',fontsize=5.8,weight='bold',color='#1a2440',zorder=7)
ax.annotate('raw battery IN (3.0–4.2V) from CN3791 →\non-board LDO makes safe 3.3V',
            (batp[0],batp[1]-1.2),(batp[0]+1,-7),ha='center',va='top',
            fontsize=6.2,color='#7a5c00',weight='bold',arrowprops=dict(arrowstyle='->',color='#7a5c00',lw=1.1))
ax.annotate('470µF LOW-ESR e-cap on 3V3 rail —\nsources the LoRa TX pulse (a supercap\ncan\'t: 30–120Ω ESR)',
            (sc_p[0]+2.5,(sc_p[1]+sc_m[1])/2),(sc_p[0]+6,(sc_p[1]+sc_m[1])/2),ha='left',va='center',fontsize=6.0,color='#1a2440',
            weight='bold',arrowprops=dict(arrowstyle='->',color='#1a2440',lw=1.1))
# JP1 : 0805 SMD ferrite (L1) on the 3V3 crossing (isolates ESP+LoRa from mic/GPS)
jpv,jpbv=g('jp'),g('jpb')
smallpad(jpv); smallpad(jpbv)                    # via-in-pad: hole shown white
ax.add_patch(FancyBboxPatch(((jpv[0]+jpbv[0])/2-1.05,jpv[1]-0.7),2.1,1.4,
             boxstyle="round,pad=0.03,rounding_size=.3",fc='#555',ec='#222',lw=.8,zorder=5))
ax.annotate('L1: 0805 ferrite bead on 3V3 (via-in-pad,\nsolder-bridge to rail) — isolates ESP+LoRa\nfrom mic/GPS. Bridge pads to bypass.',
            ((jpv[0]+jpbv[0])/2,jpv[1]-0.8),((jpv[0]+jpbv[0])/2+1,jpv[1]-7.8),ha='center',va='top',
            fontsize=5.6,color='#444',weight='bold',arrowprops=dict(arrowstyle='->',color='#444',lw=1.0))

# ESP USB edge — points DOWN to the bottom board edge (flash / serial access)
eb=[b for b in BODIES if b[4].startswith('ESP32')][0]
ax.add_patch(FancyArrow(eb[0]+eb[2]/2,eb[1]-0.3,0,-1.8,width=.25,head_width=1.3,head_length=.8,fc='#2e6da4',ec='none',zorder=7))
ax.text(eb[0]+eb[2]/2,eb[1]-3.2,'USB-C edge + bottom plug NOTCH\n(flash/serial here)',ha='center',va='top',fontsize=6.2,color='#2e6da4',weight='bold')

# C1 (10µF 0805) decoupling at the LoRa VDD, in the ESP<->LoRa gap
ax.add_patch(Rectangle((capn[0]-0.65,capn[1]-0.7),(cap[0]-capn[0])+1.3,1.4,fc='#c8a415',ec='#5c4b00',lw=.5,zorder=4))
ax.annotate('C1 10µF (0805) at LoRa VDD',((cap[0]+capn[0])/2,capn[1]-0.9),
            (capn[0]-8,capn[1]-4.5),ha='center',va='top',fontsize=5.2,color='#555',
            arrowprops=dict(arrowstyle='->',color='#555',lw=.8),zorder=6)

# LoRa coil antenna -> solders at ANT pad, sticks up through the TOP notch
antfloor=BH-ns['ant_d']
ax.plot([lora['ANT'][0],lora['ANT'][0]],[lora['ANT'][1],antfloor],color='#b0562e',lw=1.8,zorder=8)
ax.annotate('LoRa coil antenna solders here &\nsticks up through the top NOTCH',
            (lora['ANT'][0],antfloor),(lora['ANT'][0]+5.5,BH-1),ha='left',va='center',
            fontsize=6.2,color='#b0562e',weight='bold',arrowprops=dict(arrowstyle='->',color='#b0562e',lw=1.2))

# mounting + registration
for hx,hy,d,k in holes:
    if k=='M3':
        ax.add_patch(Circle((hx,hy),d/2,fill=False,ec='#111',lw=2,zorder=7))
        ax.add_patch(Circle((hx,hy),d/2+1.4,fill=False,ec='#111',lw=.6,ls=':',zorder=7))
        ax.text(hx,hy-4.6,'M3',ha='center',fontsize=6,zorder=7)
    else:
        ax.add_patch(Circle((hx,hy),d/2,fill=False,ec='#1e8449',lw=2.2,zorder=7))
        ax.text(hx-5.5,hy,'REG Ø3',ha='right',va='center',fontsize=5.8,color='#1e8449',zorder=7)

ax.annotate('',(0,-3),(BW,-3),arrowprops=dict(arrowstyle='<->',color='#444'))
ax.text(BW/2,-5,f'{BW:g} mm',ha='center',fontsize=8,color='#444')
ax.annotate('',(-3,0),(-3,BH),arrowprops=dict(arrowstyle='<->',color='#444'))
ax.text(-5.5,BH/2,f'{BH:g} mm',va='center',rotation=90,fontsize=8,color='#444')
ax.text(BW/2,BH+19,'ACOUSTIC NODE CARRIER — COMPONENT PLACEMENT (top view)',ha='center',fontsize=13,weight='bold')
ax.text(BW/2,BH+16.2,'bodies to scale · yellow = through-holes (unplated) · pin 1 marked · ESP soldered flat',
        ha='center',fontsize=8.2,color='#333')
# GPS overhang callout: the module's antenna end crosses the top board edge
gcx2,_=centroid(gps)
ax.plot([gcx2-9,gcx2+9],[BH,BH],color='#1f8a70',lw=1.6,ls=(0,(5,3)),zorder=8)  # board top edge under GPS
ax.annotate('GPS antenna end HANGS OFF top edge\n(pins on-board · easy antenna access)',
            (gcx2-8,BH),(gcx2-13,BH+9),ha='right',va='center',fontsize=6.4,color='#1f8a70',weight='bold',
            arrowprops=dict(arrowstyle='->',color='#1f8a70',lw=1.2))
ax.set_xlim(-9,BW+7); ax.set_ylim(-13,BH+22); ax.axis('off')
plt.tight_layout()
out=os.path.join(os.path.dirname(__file__),'out','node_placement.png')
plt.savefig(out,bbox_inches='tight',facecolor='white'); print('wrote',out)
