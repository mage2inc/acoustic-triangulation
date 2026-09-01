#!/usr/bin/env python3
"""Two-panel view: TOP copper vs BOTTOM copper, so each milled side is clear.
Both panels are top-view (X-ray); the bottom is mirrored about the vertical axis
for the actual second-side mill. Output: out/node_sides.png"""
import runpy, os
HERE=os.path.dirname(__file__); ns=runpy.run_path(os.path.join(HERE,'gen_pcb.py'))
pads,holes,traces=ns['pads'],ns['holes'],ns['traces']
esp,mic,gps,lora=ns['esp'],ns['mic'],ns['gps'],ns['lora']
BW,BH,HOLE=ns['BW'],ns['BH'],ns['HOLE']; gnd_pads=ns['gnd_pads']

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle

fig,axes=plt.subplots(1,2,figsize=(17,9),dpi=140)

from matplotlib.patches import Polygon
OUTLINE=ns['OUTLINE']
def draw(ax,side):
    ax.set_aspect('equal')
    fcc='#dbe7f2' if side=='bot' else '#faf6f0'
    ax.add_patch(Polygon(OUTLINE,closed=True,fc=fcc,ec='k',lw=2,zorder=0))
    ax.add_patch(Polygon(OUTLINE,closed=True,fill=False,ec='k',lw=2,zorder=9))
    if side=='bot':                                   # RF keepout: clear the GND pour here
        kx0,ky0,kx1,ky1=ns['ant_keepout']
        ax.add_patch(Rectangle((kx0,ky0),kx1-kx0,ky1-ky0,fc='white',ec='#c0007a',lw=1.4,ls=(0,(4,2)),zorder=3,hatch='xx'))
        ax.text((kx0+kx1)/2,ky0-0.8,'RF keepout\n(no pour)',ha='center',va='top',fontsize=6,color='#c0007a',weight='bold',zorder=8)
    # traces for this side (jumpers ride on the TOP side)
    for layer,w,pts,lab in traces:
        show = (layer==side) or (side=='top' and layer=='jmp')
        if not show: continue
        if layer=='top': col,ls,z='#c0392b','-',4
        elif layer=='bot': col,ls,z='#1f6dad','-',4
        else: col,ls,z='#1e8449','--',6           # jumper
        ax.plot([p[0] for p in pts],[p[1] for p in pts],color=col,ls=ls,
                lw=w*2.4,solid_capstyle='round',zorder=z,alpha=.95)
        if lab:
            mx,my=pts[len(pts)//2]
            ax.text(mx,my+0.6,lab,fontsize=4.6,color=col,ha='center',va='bottom',zorder=8)
    # pads (holes go through both sides) + GND ties on the bottom
    for px,py,net,lab,lp,d,hole in pads:
        ax.add_patch(Circle((px,py),d/2,color='#f4d03f',ec='#7d6608',lw=.4,zorder=5))
        ax.add_patch(Circle((px,py),hole/2,color='white',zorder=6))
    if side=='bot':
        for gp in gnd_pads:
            ax.add_patch(Circle(gp,1.5,fill=False,ec='#1f6dad',lw=1.1,ls=(0,(1,1)),zorder=7))
    for hx,hy,d,k in holes:
        ax.add_patch(Circle((hx,hy),d/2,fill=False,ec='#444',lw=1.8,zorder=7))
    ax.set_xlim(-3,BW+3); ax.set_ylim(-3,BH+7); ax.axis('off')

draw(axes[0],'top'); draw(axes[1],'bot')
axes[0].set_title('TOP copper  (red)  +  jumper wires (green)',fontsize=13,weight='bold',color='#c0392b')
axes[1].set_title('BOTTOM copper  (blue)  +  GND pour field',fontsize=13,weight='bold',color='#1f6dad')
axes[0].text(BW/2,BH+3.5,'SPI+RF-switch bus, mic I2S, GPS-TX, 3V3->cap->LoRa VDD, ANT · BUSY/DIO1 = jumpers',
             ha='center',fontsize=8,color='#555')
axes[1].text(BW/2,BH+3.5,'NRST, GPS-PPS, 3V3 rail · dotted rings = pads tied to the GND pour · '
             'MIRROR L-R to mill side 2',ha='center',fontsize=8,color='#555')
fig.suptitle('ACOUSTIC NODE CARRIER — the two copper sides (top-view / X-ray)',fontsize=15,weight='bold',y=0.98)
plt.tight_layout(rect=[0,0,1,0.96])
out=os.path.join(HERE,'out','node_sides.png')
plt.savefig(out,bbox_inches='tight',facecolor='white'); print('wrote',out)
