#!/usr/bin/env python3
"""
Acoustic node carrier — 2-layer CNC isolation-milled, UNPLATED holes.
REAL footprints: ESP32-S3 SuperMini (classic 2x9, nologo pinout) + INMP441 2x3
+ ATGM336H GPS + RYLR689 (1.27mm). MCP1700 LDO + 0805 ferrite/caps + 470uF buffer.
SuperMini pinout (confirmed from board image):
  LEFT col top->bot : TX RX G1 G2 G3 G4 G5 G6 G7
  RIGHT col top->bot: 5V GND 3V3 G13 G12 G11 G10 G9 G8
Left-col LoRa signals cross UNDER the module on the bottom layer (free area).
Outputs ./out: node_preview.png + Gerbers + node.drl. Uniform 0.47mm isolation floor.
"""
import os
OUT=os.path.join(os.path.dirname(__file__),'out'); os.makedirs(OUT,exist_ok=True)
VERSION='v2.2'                             # v2.2 = 3018-friendly: open all isolation to ~0.47mm
P=2.54; p127=1.27; ECW=15.24
BW,BH=56.0,53.0
TRACE=0.8; POW=1.4; PADD=1.8; SPAD=1.3; HOLE=1.0; M3=3.2; REG=3.0
CROSSW=0.3  # 3V3 column-crossing trace: thin so its isolation matches the LoRa web
ESPAD=1.3; ESPHOLE=0.8   # v2.2: ESP pads shrunk (ring 0.25 on 0.8 hole) so the 2.54
            # column opens a 1.24mm gap -> crossing isolation 0.47mm, matching the LoRa web
pads=[]; traces=[]; holes=[]; labels=[]
def padd(x,y,net,lab,lp,d=PADD,hole=HOLE): pads.append((x,y,net,lab,lp,d,hole))
def T(layer,w,*pts,lab=''): traces.append((layer,w,list(pts),lab))
def sig(layer,a,b,mx=None,lab=''):
    ax,ay=a;bx,by=b; mx=(ax+bx)/2 if mx is None else mx
    traces.append((layer,TRACE,[(ax,ay),(mx,ay),(mx,by),(bx,by)],lab))

# ---------- ESP32-S3 SuperMini (2x9), USB-C at BOTTOM edge (flash/test access) ----------
EX=25; EY=6                                   # EY = bottom (USB) end, near board bottom edge
espLn=['TX','RX','G1','G2','G3','G4','G5','G6','G7']
espRn=['5V','GND','3V3','G13','G12','G11','G10','G9','G8']
esp={}
# USB-down: TX/5V (the USB-end pins, i=0) sit at the bottom row -> y=EY+i*P
for i,n in enumerate(espLn): y=EY+i*P; padd(EX,y,n,n,'L',ESPAD,ESPHOLE); esp[n]=(EX,y)
for i,n in enumerate(espRn): y=EY+i*P; padd(EX+ECW,y,n,n,'R',ESPAD,ESPHOLE); esp[n]=(EX+ECW,y)
labels.append((EX+ECW/2,EY-3,'ESP32-S3 SuperMini (USB bottom)',1.05,0))

# ---------- INMP441 mic 2x3 : LEFT, by the ESP I2S pins (G4/G5/G6) ----------
mX=8; mY=19
# real INMP441 round module (Ø13.9): top row GND VDD SD ; bottom row L/R WS SCK.
# 3 pins/row at 2.54 mm, and the two rows are 7 mm apart.
MROW=7.0
for i,n in enumerate(['MGND','MVDD','MSD']): padd(mX+i*P,mY+MROW,n,n,'T'); esp[n]=(mX+i*P,mY+MROW)
for i,n in enumerate(['MLR','MWS','MSCK']):  padd(mX+i*P,mY,n,n,'B'); esp[n]=(mX+i*P,mY)
mic={'MVDD':esp['MVDD'],'MGND':esp['MGND'],'MSD':esp['MSD'],'MSCK':esp['MSCK'],'MWS':esp['MWS'],'MLR':esp['MLR']}
labels.append((mX+P,mY+P+3,'INMP441 (2x3)',1.0,0))

# ---------- ATGM336H GPS : TOP of the stack, header at top edge so the ANTENNA END
# HANGS OFF the top of the PCB (easy antenna access). Pins stay on-board. ----------
gX=12; gY=49
gps={}
# DORHEA ATGM336H real header is 5-pin: VCC GND TX RX PPS (RX unused = no-connect)
for i,n in enumerate(['PVCC','PGND','PTX','PRX','PPPS']): padd(gX+i*P,gY,n,n,'B'); gps[n]=(gX+i*P,gY)
labels.append((gX+2*P,gY-3,'ATGM336H GPS',1.0,0))

# ---------- RYLR689 : upper-RIGHT (by ESP SPI pins), ANT to TOP edge ----------
# rotated 90deg vs datasheet: the two pad rows run horizontally so the ANT-bearing
# edge faces the top of the board. Signal row (1-9) faces DOWN toward the ESP.
Lcx=36; Lcy=39
# RYLR689 is 1.27mm pitch with PLATED HOLES (solder wires/pins, as on the breadboard).
# v2.2: pad 0.8 / hole 0.5 -> web 0.47mm (was 0.37) with a healthy 0.15mm ring.
LSPAD,LHOLE=0.8,0.5
lora={}
# BOTTOM row = pins 1..9 (signal, faces ESP), left->right:
_Lbot=['LGND','LVDD','NRST','MISO','MOSI','SCK','NSS','RFV2','RFV1']
for i,n in enumerate(_Lbot): x=Lcx+(i-4)*p127; y=Lcy-ECW/2; padd(x,y,n,n,'B',LSPAD,LHOLE); lora[n]=(x,y)
# TOP row = pins 18,17,16,15,14,13,12,(11 absent),10 left->right, SAME columns.
# ANT (pin 10) far-RIGHT; pin 11 has NO pad (gap at col 8).
_Ltop=['LGN18','DIO3','DIO2','DIO1','BUSY','LGN13','APAD',None,'ANT']
for i,n in enumerate(_Ltop):
    if n is None: continue
    x=Lcx+(i-4)*p127; y=Lcy+ECW/2; padd(x,y,n,n,'T',LSPAD,LHOLE); lora[n]=(x,y)
labels.append((Lcx,Lcy-6*p127,'RYLR689 1.27mm (hole0.5/pad0.8)',1.0,0))

# ---- C1 : local decoupling AT LoRa VDD (10uF 0805 MLCC, TOP-mount SMD land) --------
# Pads land under LoRa VDD(pin2)/LGND(pin1); short TOP traces tie C1+->LVDD, C1-->LGND,
# which bridge to the 3V3 rail / GND pour through the soldered LoRa pins -> no via, no
# SPI crossing.  0805 land = round 1.3mm copper islands @2.0mm, hole=0 (milled, no drill).
# The series ferrite (L1) lives on JP1 (a via-in-pad 0805 land on the 3V3 crossing,
# below); C1 here is the local HF cap right at the LoRa VDD pins.
SMD=1.3
cap=(32.19,29.6); capn=(30.19,29.6)
padd(*cap,'3V3','C1','R',SMD,0); padd(*capn,'GND','','L',SMD,0)
labels.append((27.7,29.5,'C1 10uF',0.55,0))

# ---- POWER INPUT + LDO (bottom-left) : raw Li-ion (from CN3791 board) -> 3.3V -------
# U5 = MCP1700-3302E/TO (LDO, TO-92, ~110mV dropout @150mA -> holds 3.3V deep into the
# Li-ion curve). REAL TO-92 pinout, MARKED FACE / legs down:  pin1 GND | pin2 VIN |
# pin3 VOUT  -> pads GND | VIN | VOUT @2.54mm.  2nd source HT7333-A (identical pinout).
# Cin/Cout = 1uF 0805 MLCC (top-mount; tie to the LDO's own TH pads, which bridge down).
PWRPAD=2.6
ldo_g=(11.0,9.0); ldo_in=(13.54,9.0); ldo_out=(16.08,9.0)      # GND | VIN | VOUT (2.54)
padd(*ldo_g,'GND','G','T'); padd(*ldo_in,'BAT','VI','T'); padd(*ldo_out,'3V3','VO','T')
labels.append((13.54,11.4,'U5 MCP1700',0.55,0))
cinG=(11.54,5.0); cinP=(13.54,5.0)                             # Cin 1uF 0805 : VIN->GND
padd(*cinP,'BAT','Ci','R',SMD,0); padd(*cinG,'GND','','L',SMD,0)
coutP=(16.08,5.0); coutG=(18.08,5.0)                           # Cout 1uF 0805 : VOUT->GND
padd(*coutP,'3V3','Co','L',SMD,0); padd(*coutG,'GND','','R',SMD,0)
batp=(8.0,2.2); batn=(16.5,2.2)                                # raw-battery wire pads (+/-)
padd(*batp,'BAT','B+','L',PWRPAD); padd(*batn,'GND','B-','R',PWRPAD)
labels.append((22.5,2.4,'BATT 3.0-4.2V IN',0.52,0))

# ---- C2 : bulk BUFFER on the 3V3 rail for LoRa TX current spikes -------------------
# 470uF 10V LOW-ESR aluminium electrolytic. NOT a supercap -- a coin supercap's
# 30-120 ohm ESR would drop 4-9V on the ~120mA TX pulse and collapse the rail; a
# low-ESR e-cap (ESR <0.1 ohm) sources it flat. Radial ~8mm body, 3.5mm lead pitch.
sc_p=(47.0,18.0); sc_m=(47.0,14.5)             # + to 3V3, - to GND  (var names kept)
padd(*sc_p,'3V3','C2+','R',PWRPAD); padd(*sc_m,'GND','C2-','R',PWRPAD)
labels.append((47.0,20.5,'C2 470uF buffer',0.55,0))

# ---- JP1 : 0805 SMD ferrite (L1) on the 3V3 CROSSING rail --------------------------
# Sits on the crossing BEFORE it threads the ESP column, so it isolates the noisy
# ESP+LoRa side (post-JP1) from the quiet mic/GPS+LDO side (pre-JP1). It's an 0805 land
# with VIA-IN-PAD (0.6mm hole): the 3V3 rail feeds each pad's BOTTOM annulus, the bead
# mounts on TOP, and a solder-fill bridges top<->bottom. Bridge the two pads instead to
# bypass the bead (0-ohm). Open area between the LDO and the column.
JPP=1.4
jp=(19.5,9.81); jpb=(21.5,9.81)                        # 0805 pitch (2.0mm)
padd(*jp,'3V3','J1','L',JPP,0.5); padd(*jpb,'3V3','J2','R',JPP,0.5)   # 0.5 via = LoRa tool
labels.append((20.5,11.4,'L1 ferrite 0805',0.48,0))

# ---- part bodies (real sizes) for the body-collision DRC : keep >=0.6mm between them
part_bodies=[('C1',(cap[0]+capn[0])/2,29.6,2.0,1.25),('U5 LDO',ldo_in[0],9.0,5.2,4.8),
    ('JP1',(jp[0]+jpb[0])/2,9.81,2.2,1.5),
    ('Cin',(cinP[0]+cinG[0])/2,5.0,2.0,1.25),('Cout',(coutP[0]+coutG[0])/2,5.0,2.0,1.25),
    ('C2 e-cap',47.0,16.25,8.5,8.5),('ESP',32.62,16.16,18.0,22.52),
    ('mic',10.54,22.5,13.9,13.9),('LoRa',36.0,39.0,12.70,15.24)]

# ================= ROUTING (ESP soldered flat: each pad = both-side via) =========
# Layer plan: SPI bus + mic (short, local) on TOP; the left-column LoRa-control and
# power rails run on BOTTOM through the free x26-39 corridor BETWEEN the ESP columns
# (no pins there) and under the module.
V3=esp['3V3']; GN=esp['GND']

# Firmware is repinned so the LoRa NEAR row (SPI + RF-switch) all comes off the ESP
# RIGHT column in pad order -> nests cleanly on TOP, zero jumpers. Only BUSY + DIO1
# (the module's FAR row, antenna edge) need a flying wire.
# --- SPI + RF-switch : ESP right col (G8..G13) -> LoRa near row (TOP, nested) ---
sig('top',esp['G13'],lora['MISO'],mx=lora['MISO'][0],lab='MISO')   # G13 -> MISO
sig('top',esp['G12'],lora['MOSI'],mx=lora['MOSI'][0],lab='MOSI')   # G12 -> MOSI
sig('top',esp['G11'],lora['SCK'], mx=lora['SCK'][0], lab='SCK')    # G11 -> SCK
sig('top',esp['G10'],lora['NSS'], mx=lora['NSS'][0], lab='NSS')    # G10 -> NSS
# RF-switch pads sit tight against G8/G9; assign each ESP pin to its OUTER pad so no
# trace passes through the other pin. (Firmware RFSW1/RFSW2 swapped to match: 9/8.)
T('top',TRACE,esp['G8'],(lora['RFV2'][0],esp['G8'][1]),lora['RFV2'],lab='RFV2')  # G8 -> RFV2 (left, clean)
T('top',TRACE,esp['G9'],(41.7,esp['G9'][1]),(41.7,31.0),lora['RFV1'],lab='RFV1') # G9 -> RFV1 (swing right of G8)

# --- NRST : now on GP44(RX) -> LoRa near-row pad, TOP copper (left of the SPI) ---
sig('top',esp['RX'],lora['NRST'],mx=lora['NRST'][0],lab='NRST')

# --- FAR-ROW SIGNALS as BOTTOM COPPER (through-hole pads), entering the under-module
#     space from OPPOSITE sides so they never cross -> ZERO jumpers. ---
# DIO1 (GP3, above the 3V3 rail): up the corridor, under the module from the LEFT.
T('bot',TRACE,esp['G3'],(28,esp['G3'][1]),(28,33),(lora['DIO1'][0],33),lora['DIO1'],lab='DIO1')
# BUSY (GP7): TOP copper over the ESP (crossing OVER DIO1's bottom trace is fine -
# different layer), one VIA down on the right, then BOTTOM under the module, entering
# from the RIGHT so it never crosses DIO1. No flying wire; the layer change is a via.
busvia=(42,35); padd(*busvia,'BUSY','v','R',1.4,0.8)
T('top',TRACE,esp['G7'],(25,35),busvia,lab='BUSY')
T('bot',TRACE,busvia,(42,44),(lora['BUSY'][0],44),lora['BUSY'],lab='BUSY')

# --- mic I2S : ESP left col -> mic (TOP, short, pad-own-x) ---
sig('top',esp['G4'],mic['MSCK'],mx=mic['MSCK'][0],lab='MSCK')
sig('top',esp['G5'],mic['MWS'], mx=mic['MWS'][0], lab='MWS')
sig('top',esp['G6'],mic['MSD'], mx=mic['MSD'][0], lab='MSD')

# --- GPS : PTX(G1) TOP, routed AROUND the far-left edge (below the mic, then up the
#     left side) so it never runs under the ESP or across the mic I2S traces.
#     PPS(G2) on BOTTOM (G2 pad = hand-via).
T('top',TRACE,esp['G1'],(2,esp['G1'][1]),(2,44),(gps['PTX'][0],44),gps['PTX'],lab='PTX')
T('bot',TRACE,esp['G2'],(23,esp['G2'][1]),(23,gps['PPPS'][1]-3),gps['PPPS'],lab='PPPS')

# --- POWER ---
# GND = BOTTOM-LAYER POUR (leave the background copper; every GND pad ties to it).
# On a milled board you simply don't clear the field copper -> no GND traces to route,
# no GND crossings. GND pads: ESP GND, mic MGND+MLR, gps PGND, LoRa LGND/LGN2/LGN3,
# cap C-.  (Isolation-mill a moat around every non-GND pad/trace.)
gnd_pads=[GN,mic['MGND'],mic['MLR'],gps['PGND'],lora['LGND'],lora['LGN18'],lora['LGN13'],
          capn,batn,ldo_g,cinG,coutG,sc_m]

# --- C1 (0805) at LoRa VDD : tie to LVDD/LGND (bridge to rail/pour via the LoRa pins)
T('top',TRACE,cap,lora['LVDD'],lab='3V3')        # C1+ -> LoRa VDD
T('top',TRACE,capn,lora['LGND'],lab='GND')       # C1- -> LoRa LGND
# 3V3 DISTRIBUTION. LDO (bottom-left) = source. The ESP LEFT pin column is a wall
# (1.04mm gaps even with shrunk pads), so the net splits: LEFT (mic/gps) fed with NO
# crossing; RIGHT (ESP 3V3, LoRa VDD, C2 buffer) fed by ONE 0.4mm trace threading the
# RX<->G1 gap at its centre (y=YX), then fanning out in the pin-free corridor.
YX=9.81                                       # centre of the RX(8.54)/G1(11.08) gap
T('bot',POW,ldo_out,(ldo_out[0],13),(5,13),(5,44),(gps['PVCC'][0],44),gps['PVCC'],lab='3V3')  # LEFT rail (up-over LDO)
T('bot',POW,(5,24),(mic['MVDD'][0],24),mic['MVDD'],lab='3V3')            # mic VDD from below
T('bot',POW,ldo_out,(ldo_out[0],YX),jp,lab='3V3')                       # LDO OUT -> JP1a (pre-ferrite)
T('bot',CROSSW,jpb,(26,YX),(38,YX),(38,V3[1]),V3,lab='3V3')            # JP1b -> thread column -> ESP 3V3
T('bot',TRACE,(lora['LVDD'][0],YX),lora['LVDD'],lab='3V3')              # corridor riser -> LoRa VDD (post-ferrite)
T('top',POW,sc_p,(sc_p[0],V3[1]),V3,lab='3V3')                          # C2+ buffer -> ESP 3V3
# LDO caps + battery : short TOP traces to the LDO's TH pads (they bridge to bottom).
T('top',TRACE,cinP,ldo_in,lab='BAT')                                    # Cin+ -> VIN
T('top',TRACE,cinG,ldo_g,lab='GND')                                     # Cin- -> LDO GND
T('top',TRACE,coutP,ldo_out,lab='3V3')                                  # Cout+ -> VOUT
T('top',TRACE,coutG,(coutG[0],3.6),(ldo_g[0],3.6),ldo_g,lab='GND')      # Cout- -> LDO GND (below)
T('bot',POW,batp,(ldo_in[0],batp[1]),ldo_in,lab='BAT')                  # BAT+ -> VIN

# ---------- 80s retrowave logo : decorative TOP copper, in the clear area above mic --
import math as _m
LOGOW=0.35
def _LG(a,b): traces.append(('logo',LOGOW,[a,b],'logo'))
_cx,_cy,_r=12.5,39.0,2.9                                    # the "sun"
_pc=[(_cx+_r*_m.cos(t),_cy+_r*_m.sin(t)) for t in [i*2*_m.pi/26 for i in range(27)]]
for _i in range(26): _LG(_pc[_i],_pc[_i+1])                # sun ring
for _yy in [_cy-0.4,_cy-1.1,_cy-1.8,_cy-2.5]:              # sun slats (retrowave bars)
    _h=_m.sqrt(max(0.0,_r*_r-(_yy-_cy)**2)); _LG((_cx-_h,_yy),(_cx+_h,_yy))
_g=_cy-_r-0.5                                               # grid just below the sun
for _dx in [-4.4,-2.6,-1.1,1.1,2.6,4.4]:                   # perspective lines -> vanishing pt
    _LG((_cx+_dx,_g-4.0),(_cx+_dx*0.18,_g))
for _j,_yy in enumerate([_g,_g-1.15,_g-2.5,_g-4.0]):       # grid rows (widen downward)
    _w=1.7+_j*1.15; _LG((_cx-_w,_yy),(_cx+_w,_yy))

ANT_NOTCH_FLOOR=BH-3.5                                        # coil-antenna clearance notch
T('top',1.0,lora['ANT'],(lora['ANT'][0],ANT_NOTCH_FLOOR-0.5),lab='ANT')   # ANT -> notch base
# RF KEEPOUT (v2): pull the GND pour BACK from the antenna feed. ANT(pin10) + ANT_PAD
# (pin12) are the module's 50-ohm RF output; a tight ground pour beside them adds shunt
# capacitance and detunes the antenna. Clear ALL bottom copper in this rectangle (keep
# LGND pin13 at x37.27 grounded -> left edge starts right of it). No GND pad lies inside.
ant_keepout=(37.9,44.3,42.9,ANT_NOTCH_FLOOR)                  # (x0,y0,x1,y1) bottom-layer

# ---------- board OUTLINE (Edge_Cuts) with clearance notches ----------
usbx=EX+ECW/2; usb_w=13.0; usb_d=5.5                 # USB-C plug notch, bottom edge
ux0,ux1=usbx-usb_w/2, usbx+usb_w/2
antx=lora['ANT'][0]; ant_w=9.0; ant_d=BH-ANT_NOTCH_FLOOR   # coil-antenna notch, top edge
axL,axR=antx-ant_w/2, antx+ant_w/2
_RAW_OUTLINE=[(0,0),(ux0,0),(ux0,usb_d),(ux1,usb_d),(ux1,0),(BW,0),(BW,BH),
              (axR,BH),(axR,BH-ant_d),(axL,BH-ant_d),(axL,BH),(0,BH),(0,0)]
# radius every 90-deg corner (outer + notch), arc approximated by short segments
import math
def fillet(poly,r,segs=6):
    pts=poly[:-1] if poly[0]==poly[-1] else list(poly)
    n=len(pts); out=[]
    for i in range(n):
        p0=pts[(i-1)%n]; p1=pts[i]; p2=pts[(i+1)%n]
        v1=(p0[0]-p1[0],p0[1]-p1[1]); v2=(p2[0]-p1[0],p2[1]-p1[1])
        l1=math.hypot(*v1); l2=math.hypot(*v2); rr=min(r,l1/2,l2/2)
        if rr<1e-6: out.append(p1); continue
        u1=(v1[0]/l1,v1[1]/l1); u2=(v2[0]/l2,v2[1]/l2)
        t1=(p1[0]+u1[0]*rr,p1[1]+u1[1]*rr); t2=(p1[0]+u2[0]*rr,p1[1]+u2[1]*rr)
        c=(t1[0]+t2[0]-p1[0],t1[1]+t2[1]-p1[1])            # arc centre (exact for 90-deg)
        a1=math.atan2(t1[1]-c[1],t1[0]-c[0]); a2=math.atan2(t2[1]-c[1],t2[0]-c[0])
        da=a2-a1
        while da> math.pi: da-=2*math.pi
        while da<-math.pi: da+=2*math.pi
        for k in range(segs+1):
            a=a1+da*k/segs; out.append((c[0]+rr*math.cos(a),c[1]+rr*math.sin(a)))
    out.append(out[0]); return out
OUTLINE=fillet(_RAW_OUTLINE,2.0)

# ---------- holes ----------
# 4 corner M3 holes ONLY — they double as flip-registration (drill first, pin 2 diagonally)
holes+=[(4,4,M3,'M3'),(BW-4,4,M3,'M3'),(4,BH-4,M3,'M3'),(BW-4,BH-4,M3,'M3')]

# ================= RENDER =================
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle,Polygon
fig,ax=plt.subplots(figsize=(15,8.5),dpi=140); ax.set_aspect('equal')
ax.add_patch(Polygon(OUTLINE,closed=True,fc='#dbe7f2',ec='k',lw=2.5,zorder=0))   # GND pour + outline
ax.add_patch(Polygon(OUTLINE,closed=True,fill=False,ec='k',lw=2.5,zorder=10))
kx0,ky0,kx1,ky1=ant_keepout                                                      # RF keepout: no pour
ax.add_patch(Rectangle((kx0,ky0),kx1-kx0,ky1-ky0,fc='white',ec='#c0007a',lw=1.2,ls=(0,(4,2)),zorder=2,hatch='xx'))
ax.text((kx0+kx1)/2,ky0-1.0,'RF keepout\n(no GND pour)',ha='center',va='top',fontsize=5.2,color='#c0007a',weight='bold',zorder=8)
for gp in gnd_pads: ax.add_patch(Circle(gp,1.4,fill=False,ec='#1f6dad',lw=1.0,ls=(0,(1,1)),zorder=6))  # ties to pour
def box(x0,y0,x1,y1): ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='#999',lw=.8,ls=':'))
box(EX-2.2,EY-2,EX+ECW+2.2,EY+8*P+2)
ax.add_patch(Circle((mX+P,mY+MROW/2),13.9/2,fill=False,ec='#999',lw=.8,ls=':'))   # round mic Ø13.9
box(gX-1.6,gY-1.6,gX+4*P+1.6,gY+1.6); box(Lcx-6.35-1,Lcy-7.62-1,Lcx+6.35+1,Lcy+7.62+1)  # LoRa 12.70x15.24
for layer,w,pts,lab in traces:
    col={'top':'#c0392b','bot':'#1f6dad','jmp':'#1e8449','logo':'#e08a2b'}[layer]
    ax.plot([p[0] for p in pts],[p[1] for p in pts],color=col,ls=('--' if layer=='jmp' else '-'),
            lw=w*2.2,solid_capstyle='round',alpha=.9,zorder=(9 if layer in('jmp','logo') else 3))
for px,py,net,lab,lp,d,hole in pads:
    ax.add_patch(Circle((px,py),d/2,color='#f4d03f',ec='#7d6608',lw=.4,zorder=5))
    ax.add_patch(Circle((px,py),hole/2,color='white',zorder=6))
    off={'L':(-2.5,0),'R':(2.5,0),'T':(0,2.3),'B':(0,-2.3)}[lp]
    ax.text(px+off[0],py+off[1],lab,ha='center',va='center',fontsize=5.4,zorder=8)
for hx,hy,d,k in holes:
    c='#1e8449' if k=='REG' else '#444'; ax.add_patch(Circle((hx,hy),d/2,fill=False,ec=c,lw=2,zorder=7))
    ax.text(hx,hy,k,ha='center',va='center',fontsize=5,color=c,zorder=8)
for lx,ly,txt,sz,rot in labels: ax.text(lx,ly,txt,ha='center',va='center',fontsize=sz*4.3,weight='bold',color='#333',zorder=8)
ax.text(BW/2,BH+3.5,f'ACOUSTIC NODE CARRIER · 2-layer milled · {BW:g}x{BH:g} mm · {VERSION}',ha='center',fontsize=13,weight='bold')
ax.text(BW/2,BH+1.5,'RED=top copper   BLUE=bottom copper   GREEN dashed=jumper wire   light-blue field=GND pour   ·   0 copper crossings',ha='center',fontsize=8)
ax.set_xlim(-6,BW+8); ax.set_ylim(-6,BH+6); ax.axis('off')
plt.tight_layout(); plt.savefig(os.path.join(OUT,'node_preview.png'),bbox_inches='tight',facecolor='white')

# ================= GERBER + DRILL =================
def co(v): return '%d'%round(v*10000)
def gerber(fn,layer):
    L=['%FSLAX34Y34*%','%MOMM*%','%LPD*%',f'%ADD10C,{TRACE:.4f}*%',f'%ADD11C,{POW:.4f}*%',
       f'%ADD12C,{1.0:.4f}*%',f'%ADD20C,{PADD:.4f}*%',f'%ADD21C,{SPAD:.4f}*%',
       f'%ADD22C,{PWRPAD:.4f}*%',f'%ADD23C,{LSPAD:.4f}*%',f'%ADD24C,{LOGOW:.4f}*%',
       f'%ADD25C,{CROSSW:.4f}*%']
    for px,py,net,lab,lp,d,hole in pads:
        ap='D22*' if d==PWRPAD else ('D23*' if d==LSPAD else ('D21*' if d==SPAD else 'D20*'))
        L.append(ap); L.append('X%sY%sD03*'%(co(px),co(py)))
    for lay,w,pts,lab in traces:
        if lay!=layer and not(layer=='top' and lay=='logo'): continue   # logo -> top copper
        L.append('D24*' if w==LOGOW else ('D25*' if w==CROSSW else ('D11*' if w>=POW else ('D12*' if w==1.0 else 'D10*'))))
        L.append('X%sY%sD02*'%(co(pts[0][0]),co(pts[0][1])))
        for x,y in pts[1:]: L.append('X%sY%sD01*'%(co(x),co(y)))
    L.append('M02*'); open(os.path.join(OUT,fn),'w').write('\n'.join(L))
gerber('node-F_Cu.gtl','top'); gerber('node-B_Cu.gbl','bot')
oc=['%FSLAX34Y34*%','%MOMM*%','%ADD10C,0.2000*%','D10*','X%sY%sD02*'%(co(OUTLINE[0][0]),co(OUTLINE[0][1]))]
for x,y in OUTLINE[1:]: oc.append('X%sY%sD01*'%(co(x),co(y)))
oc.append('M02*'); open(os.path.join(OUT,'node-Edge_Cuts.gko'),'w').write('\n'.join(oc))
from collections import defaultdict
g=defaultdict(list)
for px,py,net,lab,lp,d,hole in pads:
    if hole>0: g[hole].append((px,py))          # hole==0 -> SMD land (no drill)
for hx,hy,d,k in holes: g[d].append((hx,hy))
L=['M48','METRIC,TZ']
for i,d in enumerate(sorted(g),1): L.append('T%02dC%.3f'%(i,d))
L.append('%')
for i,d in enumerate(sorted(g),1):
    L.append('T%02d'%i)
    for x,y in g[d]: L.append('X%.3fY%.3f'%(x,y))
L.append('M30'); open(os.path.join(OUT,'node.drl'),'w').write('\n'.join(L))
print('OK pads=%d traces=%d board=%gx%g'%(len(pads),len(traces),BW,BH))
