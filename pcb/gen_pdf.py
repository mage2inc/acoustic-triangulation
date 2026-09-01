#!/usr/bin/env python3
"""Build node_report.pdf — inspection packet for the acoustic node carrier.
Pages: 1) summary+BOM+netmap  2) placement  3) routed copper  4) 1:1 FIT/DRILL
template (print at 100%, lay real parts on it) . Pulls geometry from gen_pcb.py."""
import runpy, os
HERE=os.path.dirname(__file__); OUT=os.path.join(HERE,'out')
ns=runpy.run_path(os.path.join(HERE,'gen_pcb.py'))
pads,holes,traces=ns['pads'],ns['holes'],ns['traces']
esp,mic,gps,lora=ns['esp'],ns['mic'],ns['gps'],ns['lora']
BW,BH,cap=ns['BW'],ns['BH'],ns['cap']
PADD,SPAD,HOLE,M3=ns['PADD'],ns['SPAD'],ns['HOLE'],ns['M3']

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle,FancyBboxPatch,Polygon
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg

def centroid(d,keys=None):
    ks=keys or list(d); return (sum(d[k][0] for k in ks)/len(ks),sum(d[k][1] for k in ks)/len(ks))
ecx,ecy=centroid(esp,['TX','RX','G1','G2','G3','G4','G5','G6','G7','5V','GND','3V3','G13','G12','G11','G10','G9','G8'])
mcx,mcy=centroid(mic); gcx,_=centroid(gps); gtop=gps['PVCC'][1]; lcx,lcy=centroid(lora)
BODIES=[(ecx,ecy,18.0,22.52,'ESP32-S3 SuperMini'),(mcx,mcy,13.9,13.9,'INMP441'),
        (gcx,gtop+6.0,17.0,16.0,'ATGM336H'),(lcx,lcy,12.70,15.24,'RYLR689')]

pp=PdfPages(os.path.join(OUT,'node_report.pdf'))

# ---------- PAGE 1 : summary / BOM / net map / fit-check method ----------
fig=plt.figure(figsize=(8.27,11.69)); fig.subplots_adjust(0,0,1,1); ax=fig.add_axes([0,0,1,1]); ax.axis('off')
cur=[0.972]
def L(s,size=8.3,b=False,c='#111',x=0.055,pre=0.0,lh=0.0158,url=None):  # running-cursor writer
    cur[0]-=pre
    ax.text(x,cur[0],s,fontsize=size,weight=('bold' if b else 'normal'),color=c,va='top',
            family='monospace',transform=ax.transAxes,url=url)
    cur[0]-=lh
def H(s,c='#1a5276'): L(s,10.5,True,c,pre=0.012,lh=0.019)         # section header

L(f'ACOUSTIC NODE CARRIER — INSPECTION PACKET   [{ns.get("VERSION","")}]',14.5,True,lh=0.021)
L(f'2-layer CNC isolation-milled · {BW:g} x {BH:g} mm · unplated holes · GND pour (bottom)',8,c='#555')
H('LAYER / ROUTING')
for s in ['RED  = top copper   (SPI bus, mic I2S, NRST, C1 decoupling AT LoRa VDD)',
          'BLUE = bottom copper (3V3 rails + JP1 ferrite + threaded crossing, PPPS) + POUR',
          'GRN  = 0 jumper wires!  BUSY = top->via->bottom copper; DIO1 = all bottom copper',
          '0 copper crossings + 0 trace-over-pad shorts (machine-verified DRC).',
          '3V3: LDO feeds mic/GPS with no crossing; JP1 ferrite, then ONE 0.4mm trace',
          '     threads the ESP RX<->G1 gap (0.32mm clr, ~matches the LoRa 0.37 floor).',
          'EDGE CUTS: cut the outline + USB-C plug notch (bottom) + coil-ant notch (top)',
          'RF KEEPOUT (v2): clear ALL bottom GND pour inside the magenta box at the ANT',
          '     feed (ANT/ANT_PAD are the 50ohm RF output) -- do not backfill copper there.']: L(s)
H('BILL OF MATERIALS  (per node; blue rows are clickable -> Amazon)')
AMZ='https://www.amazon.com/dp/'
for r,p,asin in [
    ('U1','ESP32-S3 SuperMini - soldered FLAT via castellations (not socketed)','B0F6YJL9NM'),
    ('U2','INMP441 I2S mic - O13.9 round, 2x3 @ 2.54, rows 7mm apart','B09BB1F4C8'),
    ('U3','ATGM336H GPS (1x5) - hangs off TOP edge  [confirm PPS pad on listing]','B0DFYM7FPS'),
    ('U4','REYAX RYLR689 LoRa (LLCC68 SPI, 915MHz, 1.27mm castellated), 2pk','B0BNVKQ9JD'),
    ('U5','MCP1700-3302E/TO LDO 3V3 TO-92 (1 GND|2 VIN|3 VOUT)  2nd:HT7333-A','B091C4NGTR'),
    ('C1','10uF 25V MLCC 0805 at LoRa VDD (top-mount, ties to LVDD/LGND)','B07P77YXS7'),
    ('Cin','1uF + 10uF 0805 MLCC assortment kit (Cin/Cout, 1uF each)','B06XDG3WQX'),
    ('C2','470uF 10V/16V LOW-ESR electrolytic (Nichicon PM) = TX-spike buffer','B00RH8DB40'),
    ('L1','ferrite bead 0805 ~600ohm@100MHz (TDK MPZ2012S601) on JP1 3V3 crossing','B0B8MN84RJ'),
    ('V1','1 via (BUSY). JP1=0805 via-in-pad: solder-bridge to rail; bridge pads=bypass',None),
    ('BAT','18650 holder (2-wire) + your CN3791 charger -> BATT-IN pads (3.0-4.2V)','B08Q399339'),
    ('HW','4x M3 standoff/screw kit   +   2-layer FR1/FR4 clad stock','B01HDR72Q2')]:
    L(f'  {r:4} {p}',c=('#1a5276' if asin else '#111'),url=(AMZ+asin if asin else None))
L('  2nd-source LDO: HT7333-A 20pk (TO-92, same pinout)',7.6,c='#1a5276',url=AMZ+'B07KX5YL6Y')
L('  L1 isolates ESP+LoRa HF noise from the mic/GPS supply (~20-40dB, 50-300MHz). It',7.4,c='#555')
L('  does NOT fix TX droop (C2 does) or radiated GPS<->LoRa antenna coupling. Optional:',7.4,c='#555')
L('  a solder bridge across the pads bypasses it (0-ohm) if it ever causes trouble.',7.4,c='#555')
L('  NOTE: coin SUPERCAPS rejected -- 30-120ohm ESR drops 4-9V on the 120mA TX pulse;',7.4,c='#922b21')
L('  a 470uF low-ESR e-cap (<0.1ohm) sources it flat.',7.4,c='#922b21')
H('NET MAP  (matches firmware node_config.h)')
for s in ['GP4  Mic BCLK   GP5  Mic WS    GP6  Mic SD     (I2S, L/R->GND = left)',
          'GP13 MISO  GP12 MOSI  GP11 SCK  GP10 NSS       (SPI, ESP right column)',
          'GP8  RFSW_V2    GP9  RFSW_V1   (RF switch; each pin to its outer pad)',
          'GP7  BUSY (copper+via)   GP3 DIO1 (copper)   GP44 NRST (top)',
          'GP1  GPS TX(in) GP2  GPS PPS   (GPS RX = no-connect)',
          '3V3 -> mic/gps/lora VDD (C1 at LoRa VDD)  GND pour -> all grounds']: L('  '+s)
H('>> HOW TO CHECK PARTS FIT  (before cutting copper) <<','#922b21')
for s in ['1. Print PAGE 4 at 100% / "actual size" (NOT fit-to-page). Then caliper the',
          '   50 mm scale bar — it MUST read 50.0 mm. Re-print if off.',
          '2. Set each real module on its pad group: pin pitch lands in the holes, the',
          '   body outline (dashed) has clearance, antenna/USB edges point the right way.',
          '3. Caliper-verify the footprints assumed vs your actual parts:',
          '     ESP SuperMini 2.54 pitch, rows 15.24, body 22.52x18',
          '     RYLR689 body 12.70x15.24, pads 1.27 pitch, rows 15.24 <- finest',
          '     ATGM336H 1x5 @ 2.54   ·   INMP441 Ø13.9 round, 2x3 @ 2.54, rows 7mm',
          '4. DRILL-ONLY test cut on scrap; dry-fit ALL parts + standoffs; THEN mill.',
          '5. Optional: mill one board first, populate + verify before making the 2nd.']: L(s)
L('pages: 2 = placement (assembly)   3 = routed copper   4 = 1:1 fit/drill template',8,c='#555',pre=0.012)
pp.savefig(fig); plt.close(fig)

# ---------- PAGES 2 & 3 : the PNGs ----------
for png,cap_txt in [('node_placement.png','PAGE 2 — COMPONENT PLACEMENT (assembly, top view)'),
                    ('node_preview.png','PAGE 3 — ROUTED COPPER (red=top, blue=bottom, green=jumper)')]:
    p=os.path.join(OUT,png)
    if not os.path.exists(p): continue
    fig=plt.figure(figsize=(11.69,8.27)); ax=fig.add_axes([0.02,0.02,0.96,0.93]); ax.axis('off')
    ax.imshow(mpimg.imread(p)); fig.text(0.5,0.97,cap_txt,ha='center',fontsize=12,weight='bold')
    pp.savefig(fig); plt.close(fig)

# ---------- PAGE 4 : 1:1 FIT / DRILL TEMPLATE (exact scale) ----------
mgn=20.0                                   # mm margin around the board for scale bar/notes
Win=(BW+2*mgn)/25.4; Hin=(BH+2*mgn)/25.4
fig=plt.figure(figsize=(Win,Hin))
ax=fig.add_axes([mgn/(BW+2*mgn), mgn/(BH+2*mgn), BW/(BW+2*mgn), BH/(BH+2*mgn)])
ax.set_xlim(0,BW); ax.set_ylim(0,BH); ax.set_aspect('equal'); ax.axis('off')
ax.add_patch(Polygon(ns['OUTLINE'],closed=True,fill=False,ec='k',lw=1.2))   # real outline + notches
for x0c,y0c,w,h,nm in BODIES:                                   # module body outlines (dashed)
    if nm=='INMP441':
        ax.add_patch(Circle((x0c,y0c),w/2,fill=False,ec='#888',lw=0.7,ls=(0,(4,3))))
    else:
        ax.add_patch(Rectangle((x0c-w/2,y0c-h/2),w,h,fill=False,ec='#888',lw=0.7,ls=(0,(4,3))))
    ax.text(x0c,y0c,nm,ha='center',va='center',fontsize=4.5,color='#888')
for px,py,net,lab,lp,d,hole in pads:                            # pads at REAL diameter + hole
    ax.add_patch(Circle((px,py),d/2,fill=False,ec='#000',lw=0.5))
    ax.add_patch(Circle((px,py),hole/2,fill=True,fc='#000'))
for hx,hy,d,k in holes:
    ax.add_patch(Circle((hx,hy),d/2,fill=False,ec='#000',lw=1.0))
    ax.add_patch(Circle((hx,hy),0.4,fc='#000'))
# scale bar (must measure 50.0 mm when printed at 100%)
sb0=1.0
ax.plot([sb0,sb0+50],[-6,-6],color='#c00',lw=1.5,clip_on=False)
for xx in (sb0,sb0+50): ax.plot([xx,xx],[-6.9,-5.1],color='#c00',lw=1.5,clip_on=False)
ax.text(sb0+25,-9.5,'50.0 mm  — PRINT AT 100%; this MUST measure 50 mm with calipers',
        ha='center',fontsize=6,color='#c00',weight='bold',clip_on=False)
ax.text(BW/2,BH+6,'PAGE 4 — 1:1 FIT / DRILL TEMPLATE  (solid dots = drill points, dashed = module bodies)',
        ha='center',fontsize=6.5,weight='bold',clip_on=False)
pp.savefig(fig); plt.close(fig)

pp.close(); print('wrote',os.path.join(OUT,'node_report.pdf'))
