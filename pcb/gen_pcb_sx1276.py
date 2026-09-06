#!/usr/bin/env python3
"""
gen_pcb_sx1276.py — Acoustic node carrier v3.0, XL1276-P01 / SX1276 variant.
2-layer FR4, 56×53 mm, designed for JLCPCB manufacturing (or any fab).

Key changes vs v2.2 (RYLR689):
  • XL1276-P01 (SX1276) footprint — 16×16 mm, 2 mm pitch, Ra-01S-compatible pinout
  • 3 control signals vs 6: only NSS/SCK/MOSI/MISO/RST/DIO0 — no RFSW, no BUSY
  • GP7 + GP8 freed for future use (DS3231 RTC, status LED, etc.)
  • Gerbers include F_Mask / B_Mask / F_Silk for JLCPCB ordering

XL1276-P01 pinout assumed (Ra-01S / SX1276 standard, antenna at module top):
  Left col  (L1→L8, top first): ANT  GND  DIO5  DIO4  DIO3  DIO2  DIO1  DIO0
  Right col (R1→R8, top first): NC   VCC  NSS   SCK   MOSI  MISO  RST   GND

Outputs → ./out_sx1276/:
  node_sx1276-F_Cu.gtl   node_sx1276-B_Cu.gbl
  node_sx1276-F_Mask.gts node_sx1276-B_Mask.gbs
  node_sx1276-F_Silk.gto node_sx1276-Edge_Cuts.gko
  node_sx1276.drl        node_sx1276_preview.png

NOTE: After generating, open in KiCad / EasyEDA, add a B_Cu GND fill zone,
run DRC, and re-export gerbers before submitting to JLCPCB.
"""
import os, math
from collections import defaultdict

OUT = os.path.join(os.path.dirname(__file__), 'out_sx1276')
os.makedirs(OUT, exist_ok=True)

VERSION = 'v3.0-sx1276'
BW, BH  = 56.0, 53.0       # board width × height (mm) — same footprint as v2.2

# ---- JLCPCB 2-layer design rules ----
TRACE  = 0.4    # signal trace width (mm)
POW    = 0.8    # power rail
CROSSW = 0.2    # 3V3 column-crossing (narrow to thread the ESP header gap)
M3     = 3.2    # M3 mounting hole

# ---- Pad geometry ----
P      = 2.54          # 2.54 mm standard pitch
ESPAD  = 1.3;  ESPHOLE = 0.8    # ESP32-S3 Zero header pad / drill
THPAD  = 1.8;  THHOL   = 1.0   # generic through-hole pad
PWRPAD = 2.6                    # battery / bulk-cap terminal (large, wire gauge)
SMD    = 1.3                    # 0805 SMD pad (round, no drill)
SMD14  = 1.4                    # ferrite bead pad (JP1)
# XL1276-P01 castellation land — rectangular SMD, extends 1mm outside module edge
LORA_PW = 2.0   # pad depth (perpendicular to module edge, top-layer SMD)
LORA_PH = 1.4   # pad width along the 2mm pitch axis

ECW = 15.24     # ESP32-S3 Zero header width (6 × 2.54 mm between col centres)

# ---- Component anchor points ----
EX, EY  = 25.0, 6.0      # ESP32-S3 Zero: left-col TX at (EX, EY), USB end at BOTTOM
mX, mY  = 8.0,  19.0     # INMP441 mic: body centre-left
gX, gY  = 12.0, 49.0     # ATGM336H GPS: leftmost of the 5-pin header row
Lcx     = 36.0            # XL1276-P01 module centre X (matches RYLR689 position)
Lcy     = 37.0            # module centre Y (shifted up 2 mm from RYLR689 v2.2)
LHW     = 8.0             # half-width of 16 mm module

# ---- Data structures ----
pads   = []   # (x, y, net, label, pw, ph, hole)   hole=0 → SMD
traces = []   # (layer, w, [(x,y),...], label)
holes  = []   # (x, y, dia, label)
silk   = []   # ('rect'|'circle'|'text'|'line', *args)

def pad(x, y, net, lab, pw, ph=None, hole=0):
    pads.append((x, y, net, lab, pw, ph if ph is not None else pw, hole))

def th(x, y, net, lab, pw=THPAD):    pad(x, y, net, lab, pw, pw, THHOL)
def esph(x, y, net, lab):            pad(x, y, net, lab, ESPAD, ESPAD, ESPHOLE)
def smd(x, y, net, lab, pw=SMD):     pad(x, y, net, lab, pw, pw, 0)

def T(layer, w, *pts, lab=''):
    traces.append((layer, w, list(pts), lab))

def seg(layer, a, b, mx=None, lab=''):
    """L-shaped route: a → (mx, a.y) → (mx, b.y) → b"""
    ax, ay = a; bx, by = b
    mx = (ax + bx) / 2 if mx is None else mx
    traces.append((layer, TRACE, [(ax,ay),(mx,ay),(mx,by),(bx,by)], lab))

# ==========================================================================
# ESP32-S3 Zero (2×9 header, USB-C at BOTTOM = lowest y)
# Left  col (TX..G7, i=0..8) at x=EX,    y=EY+i*P
# Right col (5V..G8, i=0..8) at x=EX+ECW, y=EY+i*P
# ==========================================================================
espLn = ['TX','RX','G1','G2','G3','G4','G5','G6','G7']
espRn = ['5V','GND','3V3','G13','G12','G11','G10','G9','G8']
esp   = {}

for i, n in enumerate(espLn):
    y = EY + i * P
    esph(EX, y, n, n)
    esp[n] = (EX, y)

for i, n in enumerate(espRn):
    y = EY + i * P
    esph(EX + ECW, y, n, n)
    esp[n] = (EX + ECW, y)

silk.append(('rect', EX-2.2, EY-2, EX+ECW+2.2, EY+8*P+2))
silk.append(('text', EX+ECW/2, EY-3.5, 'ESP32-S3 Zero', 1.05))

# ==========================================================================
# INMP441 mic — 2×3 header, 2.54 mm pitch
# Top row (y=mY+MROW): MGND  MVDD  MSD
# Bot row (y=mY):       MLR   MWS   MSCK
# ==========================================================================
MROW = 7.0
mic = {}
for i, n in enumerate(['MGND','MVDD','MSD']):
    esph(mX+i*P, mY+MROW, n, n); mic[n] = (mX+i*P, mY+MROW); esp[n] = mic[n]
for i, n in enumerate(['MLR','MWS','MSCK']):
    esph(mX+i*P, mY,      n, n); mic[n] = (mX+i*P, mY);      esp[n] = mic[n]
silk.append(('circle', mX+P, mY+MROW/2, 7.0))
silk.append(('text', mX+P, mY+MROW+3.5, 'INMP441', 1.0))

# ==========================================================================
# ATGM336H GPS — 5-pin header: VCC GND TX RX PPS
# ==========================================================================
gps = {}
for i, n in enumerate(['PVCC','PGND','PTX','PRX','PPPS']):
    esph(gX+i*P, gY, n, n); gps[n] = (gX+i*P, gY)
silk.append(('rect', gX-1.5, gY-1.5, gX+4*P+1.5, gY+1.5))
silk.append(('text', gX+2*P, gY+3.0, 'ATGM336H GPS', 1.0))

# ==========================================================================
# XL1276-P01 (SX1276) — 16×16 mm, castellation, 2 mm pitch, 8 per side.
# Antenna at TOP (high y). Pinout: Ra-01S compatible.
# Left  col x=Lcx-LHW: ANT GND DIO5 DIO4 DIO3 DIO2 DIO1 DIO0  (top→bot)
# Right col x=Lcx+LHW: NC  VCC NSS  SCK  MOSI MISO RST  GND   (top→bot)
# Y positions: Lcy+7, Lcy+5, Lcy+3, Lcy+1, Lcy-1, Lcy-3, Lcy-5, Lcy-7
# ==========================================================================
lora = {}
LPY  = [Lcy + 7 - 2*i for i in range(8)]   # top-to-bot y positions

_L = ['LANT','LGND','LDIO5','LDIO4','LDIO3','LDIO2','LDIO1','LDIO0']
_R = ['LNC', 'LVCC','LNSS', 'LSCK', 'LMOSI','LMISO','LRST', 'LGND2']

for i, n in enumerate(_L):
    x = Lcx - LHW
    pad(x, LPY[i], n, n, LORA_PW, LORA_PH, 0)
    lora[n] = (x, LPY[i])

for i, n in enumerate(_R):
    x = Lcx + LHW
    pad(x, LPY[i], n, n, LORA_PW, LORA_PH, 0)
    lora[n] = (x, LPY[i])

silk.append(('rect', Lcx-LHW, Lcy-LHW, Lcx+LHW, Lcy+LHW))
silk.append(('text', Lcx, Lcy+2, 'XL1276-P01', 0.9))
silk.append(('text', Lcx, Lcy-1, 'SX1276  915MHz', 0.75))
# Antenna direction indicator
silk.append(('line', Lcx-LHW, Lcy+LHW+1, Lcx-LHW, Lcy+LHW+3))
silk.append(('text', Lcx-LHW+2, Lcy+LHW+2, 'ANT', 0.7))

# ==========================================================================
# Power supply — MCP1700-3302E/TO-92 LDO (same as v2.2)
# ==========================================================================
ldo_g   = (11.0, 9.0)
ldo_in  = (13.54, 9.0)
ldo_out = (16.08, 9.0)
th(*ldo_g,   'GND', 'G')
th(*ldo_in,  'BAT', 'VI')
th(*ldo_out, '3V3', 'VO')
silk.append(('text', 13.54, 11.2, 'U5 MCP1700', 0.7))

# Cin / Cout 1 uF 0805 on LDO
cinP  = (13.54, 5.0); cinG  = (11.54, 5.0)
coutP = (16.08, 5.0); coutG = (18.08, 5.0)
smd(*cinP,  'BAT', 'Ci+');  smd(*cinG,  'GND', 'Ci-')
smd(*coutP, '3V3', 'Co+');  smd(*coutG, 'GND', 'Co-')
silk.append(('text', 12.5, 3.0, 'Cin 1uF', 0.6))
silk.append(('text', 17.0, 3.0, 'Cout 1uF', 0.6))

# Battery input terminals
batp = (8.0, 2.2); batn = (16.5, 2.2)
pad(*batp, 'BAT', 'B+', PWRPAD, PWRPAD, THHOL)
pad(*batn, 'GND', 'B-', PWRPAD, PWRPAD, THHOL)
silk.append(('text', 12.0, 0.3, 'BATT IN 3.0-4.2V', 0.65))

# JP1 — 0805 ferrite bead on 3V3 rail (pre-ESP+LoRa side filter)
YX = 9.81    # y of 3V3 crossing (centre of RX/G1 gap at the left ESP col)
jp  = (19.5, YX); jpb = (21.5, YX)
smd(*jp,  '3V3', 'J1', SMD14)
smd(*jpb, '3V3', 'J2', SMD14)
silk.append(('text', 20.5, 11.2, 'L1 ferrite', 0.6))

# C1 — 10 uF 0805 local decoupling at LoRa VCC
# Placed just right of the LoRa right col, level with LVCC pad
c1p = (Lcx+LHW+2.2, lora['LVCC'][1])
c1n = (Lcx+LHW+4.0, lora['LVCC'][1])
smd(*c1p, '3V3', 'C1+')
smd(*c1n, 'GND', 'C1-')
silk.append(('text', Lcx+LHW+3.0, lora['LVCC'][1]+2.0, 'C1 10uF', 0.6))

# C2 — 470 uF low-ESR electrolytic bulk buffer for LoRa TX spikes
# Moved right to clear the RST routing lane at x=48
sc_p = (50.0, 18.0); sc_m = (50.0, 14.5)
pad(*sc_p, '3V3', 'C2+', PWRPAD, PWRPAD, THHOL)
pad(*sc_m, 'GND', 'C2-', PWRPAD, PWRPAD, THHOL)
silk.append(('text', 50.0, 20.5, 'C2\n470uF', 0.6))

# M3 corner mounting holes
for hx, hy in [(4,4),(BW-4,4),(4,BH-4),(BW-4,BH-4)]:
    holes.append((hx, hy, M3, 'M3'))

# ==========================================================================
# ROUTING
# ==========================================================================

V3 = esp['3V3'];  GN = esp['GND']

# ---- SPI bus — TOP layer, staggered columns between ESP right col & LoRa ----
# ESP right col x=40.24; LoRa right col x=44.  Route via mx values 40.8..42.6
# so the 4 vertical segments don't overlap (0.6 mm spacing ≥ 0.2 mm clearance).
#   G13 → LMISO   G12 → LMOSI   G11 → LSCK   G10 → LNSS
for gpin, lpin, mx in [('G13','LMISO',40.8),('G12','LMOSI',41.4),
                        ('G11','LSCK', 42.0),('G10','LNSS', 42.6)]:
    seg('top', esp[gpin], lora[lpin], mx=mx, lab=lpin)

# ---- RST — TOP layer, routes right past ESP then up alongside board edge ----
# RX/GP44 at (25, 8.54).  LRST at (44, 30) [right col, 7th from top = Lcy-7=30].
# Drops to y=7 to avoid the GND pad at (40.24, 8.54), then swings wide right.
T('top', TRACE,
  esp['RX'],
  (EX, 7.0),
  (48.0, 7.0),
  (48.0, lora['LRST'][1]),
  lora['LRST'],
  lab='RST')

# ---- DIO0 — BOTTOM layer from G9 TH pad (both-layer via the plated hole) ----
# G9 at (40.24, 23.78).  LDIO0 at (28, 30).
# Route: right past LoRa, down to clear-zone, left under module, up to DIO0.
T('bot', TRACE,
  esp['G9'],
  (45.0, esp['G9'][1]),
  (45.0, 28.5),
  (26.0, 28.5),
  (26.0, lora['LDIO0'][1]),
  lora['LDIO0'],
  lab='DIO0')

# ---- Mic I2S — TOP layer (G4→MSCK, G5→MWS, G6→MSD) ----
seg('top', esp['G4'], mic['MSCK'], mx=14.0,  lab='MSCK')
seg('top', esp['G5'], mic['MWS'],  mx=12.0,  lab='MWS')
seg('top', esp['G6'], mic['MSD'],  mx=20.0,  lab='MSD')

# ---- GPS TX — TOP layer, left edge then up ----
T('top', TRACE,
  esp['G1'], (2.0, esp['G1'][1]), (2.0, 47.0), gps['PTX'],
  lab='GPS_TX')

# ---- GPS PPS — BOTTOM layer from G2 TH pad ----
# Route at x=21 (not x=23 which conflicts with RST bottom leg if any)
T('bot', TRACE,
  esp['G2'], (21.0, esp['G2'][1]), (21.0, 47.0), gps['PPPS'],
  lab='PPS')

# ---- POWER — BOTTOM layer (GND = copper pour added in KiCad/EasyEDA) ----

# Left rail: LDO out → GPS VCC (up the left side)
T('bot', POW,
  ldo_out,
  (ldo_out[0], 14.0), (5.0, 14.0), (5.0, 47.0), gps['PVCC'],
  lab='3V3-left')

# Mic VDD tap from left rail
T('bot', TRACE, (5.0, mY+MROW-2), mic['MVDD'], lab='3V3-mic')

# LDO out → ferrite JP1 (pre-ferrite segment)
T('bot', POW, ldo_out, (ldo_out[0], YX), jp, lab='3V3-jp')

# JP1 post-ferrite → narrow crossing through ESP left-col gap → ESP 3V3 + LoRa VCC
T('bot', CROSSW, jpb,
  (40.24, YX), V3,
  lab='3V3-cross')

# LoRa VCC tap from the 3V3 corridor (branch from crossing)
T('bot', TRACE, (Lcx+LHW-0.5, YX), (Lcx+LHW-0.5, lora['LVCC'][1]), lora['LVCC'], lab='3V3-lora')

# C1 → LoRa VCC (TOP layer, short stub)
T('top', TRACE, c1p, lora['LVCC'], lab='3V3-c1')

# C2 buffer → ESP 3V3 (TOP layer power rail)
T('top', POW, sc_p, (sc_p[0], V3[1]), V3, lab='3V3-c2')

# LDO cap wiring (TOP, very short)
T('top', TRACE, cinP,  ldo_in,  lab='BAT-cin')
T('top', TRACE, cinG,  ldo_g,   lab='GND-cin')
T('top', TRACE, coutP, ldo_out, lab='3V3-cout')
T('top', TRACE, coutG, (coutG[0], 3.8), (ldo_g[0], 3.8), ldo_g, lab='GND-cout')

# Battery + → LDO VIN (BOTTOM layer)
T('bot', POW, batp, (ldo_in[0], batp[1]), ldo_in, lab='BAT-in')

# GND reference list (these tie to the B_Cu GND pour — add in KiCad)
gnd_pads = [GN, mic['MGND'], mic['MLR'], gps['PGND'],
            lora['LGND'], lora['LGND2'], c1n, batn, ldo_g, cinG, coutG, sc_m]

# ==========================================================================
# BOARD OUTLINE (same rounded-corner algorithm as v2.2)
# USB-C access notch at BOTTOM, no top notch (XL1276-P01 wire antenna exits freely)
# ==========================================================================
usb_cx = EX + ECW / 2; usb_w = 13.0; usb_d = 5.5
ux0, ux1 = usb_cx - usb_w/2, usb_cx + usb_w/2
_RAW = [(0,0),(ux0,0),(ux0,usb_d),(ux1,usb_d),(ux1,0),
        (BW,0),(BW,BH),(0,BH),(0,0)]

def fillet(poly, r, segs=6):
    pts = poly[:-1] if poly[0] == poly[-1] else list(poly)
    n = len(pts); out = []
    for i in range(n):
        p0=pts[(i-1)%n]; p1=pts[i]; p2=pts[(i+1)%n]
        v1=(p0[0]-p1[0],p0[1]-p1[1]); v2=(p2[0]-p1[0],p2[1]-p1[1])
        l1=math.hypot(*v1); l2=math.hypot(*v2); rr=min(r,l1/2,l2/2)
        if rr < 1e-6: out.append(p1); continue
        u1=(v1[0]/l1,v1[1]/l1); u2=(v2[0]/l2,v2[1]/l2)
        t1=(p1[0]+u1[0]*rr,p1[1]+u1[1]*rr); t2=(p1[0]+u2[0]*rr,p1[1]+u2[1]*rr)
        c=(t1[0]+t2[0]-p1[0],t1[1]+t2[1]-p1[1])
        a1=math.atan2(t1[1]-c[1],t1[0]-c[0]); a2=math.atan2(t2[1]-c[1],t2[0]-c[0])
        da=a2-a1
        while da >  math.pi: da -= 2*math.pi
        while da < -math.pi: da += 2*math.pi
        for k in range(segs+1):
            a=a1+da*k/segs; out.append((c[0]+rr*math.cos(a),c[1]+rr*math.sin(a)))
    out.append(out[0]); return out

OUTLINE = fillet(_RAW, 2.0)

# ==========================================================================
# PREVIEW PNG
# ==========================================================================
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from matplotlib.patches import Polygon as MplPoly

fig, ax = plt.subplots(figsize=(15, 9), dpi=140)
ax.set_aspect('equal')

# Board (GND pour = light blue field)
ax.add_patch(MplPoly(OUTLINE, closed=True, fc='#dbe7f2', ec='k', lw=2.5, zorder=0))
ax.add_patch(MplPoly(OUTLINE, closed=True, fill=False, ec='k', lw=2.5, zorder=10))

# RF keepout annotation near LoRa antenna
ax.text(Lcx-LHW+1, Lcy+LHW+1, 'no GND pour\nnear ANT pad',
        ha='left', va='bottom', fontsize=4.5, color='#c0007a', style='italic', zorder=9)

# Traces
layer_col = {'top': '#c0392b', 'bot': '#1f6dad'}
for layer, w, pts, lab in traces:
    col = layer_col.get(layer, '#888')
    ax.plot([p[0] for p in pts], [p[1] for p in pts],
            color=col, lw=w*2.2, solid_capstyle='round', alpha=0.9, zorder=3)
    if lab:
        mx = (pts[0][0]+pts[-1][0])/2; my = (pts[0][1]+pts[-1][1])/2
        ax.text(mx, my, lab, fontsize=3.8, color=col, ha='center', va='bottom', zorder=9,
                alpha=0.75)

# Pads
for px, py, net, lab, pw, ph, hole in pads:
    fc = '#f4d03f'; ec = '#7d6608'
    ax.add_patch(Rectangle((px-pw/2, py-ph/2), pw, ph,
                            fc=fc, ec=ec, lw=0.4, zorder=5))
    if hole > 0:
        ax.add_patch(Circle((px, py), hole/2, fc='white', zorder=6))
    if lab:
        ax.text(px, py, lab, ha='center', va='center', fontsize=4.0, zorder=8)

# GND pour tie indicators
for gp in gnd_pads:
    ax.add_patch(Circle(gp, 1.4, fill=False, ec='#1f6dad', lw=0.8,
                        ls=(0,(1,1)), zorder=4))

# Holes
for hx, hy, hd, hl in holes:
    ax.add_patch(Circle((hx,hy), hd/2, fill=False, ec='#444', lw=2, zorder=7))
    ax.text(hx, hy, hl, ha='center', va='center', fontsize=4.5, color='#444', zorder=8)

# Silk
for item in silk:
    t = item[0]
    if t == 'rect':
        _, x0,y0,x1,y1 = item
        ax.add_patch(Rectangle((x0,y0), x1-x0, y1-y0,
                               fill=False, ec='#d4ac0d', lw=0.9, ls=':', zorder=8))
    elif t == 'circle':
        _, cx,cy,r = item
        ax.add_patch(Circle((cx,cy), r, fill=False, ec='#d4ac0d', lw=0.9, ls=':', zorder=8))
    elif t == 'text':
        _, tx,ty,txt,sz = item
        ax.text(tx, ty, txt, ha='center', va='center',
                fontsize=sz*4.0, weight='bold', color='#333', zorder=9)
    elif t == 'line':
        _, x1,y1,x2,y2 = item
        ax.plot([x1,x2],[y1,y2], color='#d4ac0d', lw=0.9, zorder=8)

ax.text(BW/2, BH+4.0,
        f'ACOUSTIC NODE CARRIER · XL1276-P01 / SX1276 · 2-layer FR4 · {BW:g}×{BH:g} mm · {VERSION}',
        ha='center', fontsize=12, weight='bold')
ax.text(BW/2, BH+2.0,
        'RED=F_Cu  BLUE=B_Cu  GOLD=pads  dotted circle=GND pour tie  '
        '·  Add B_Cu GND fill in KiCad before ordering',
        ha='center', fontsize=7.5)
ax.set_xlim(-6, BW+10); ax.set_ylim(-6, BH+7); ax.axis('off')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'node_sx1276_preview.png'), bbox_inches='tight', facecolor='white')
plt.close()
print('Preview saved.')

# ==========================================================================
# GERBER EXPORT  (RS-274X, metric, 4-decimal integer format)
# ==========================================================================
def co(v): return '%d' % round(v * 10000)

def aperture_table(pads, traces, extra_rounds=()):
    """Collect all needed apertures, return (table_lines, ap_map).
    ap_map: (shape, *dims) → d-code int.
    """
    ap_map = {}; d_next = [10]; lines = []

    def reg(shape, *dims):
        key = (shape,) + tuple(round(d,4) for d in dims)
        if key not in ap_map:
            ap_map[key] = d_next[0]; d_next[0] += 1
        return ap_map[key]

    for px,py,net,lab,pw,ph,hole in pads:
        if hole > 0:
            reg('C', pw)      # TH pad: circular aperture (HASL ring)
        else:
            reg('R', pw, ph)  # SMD: rectangular
    for r in extra_rounds:
        reg('C', r)
    for layer,w,pts,lab in traces:
        reg('C', w)

    # Build header lines
    for key, dc in sorted(ap_map.items(), key=lambda x: x[1]):
        sh = key[0]; dims = key[1:]
        if sh == 'C': lines.append(f'%ADD{dc}C,{dims[0]:.4f}*%')
        elif sh == 'R': lines.append(f'%ADD{dc}R,{dims[0]:.4f}X{dims[1]:.4f}*%')
    return lines, ap_map

def write_copper(fn, layer_name, pads, traces, ap_lines, ap_map):
    co2 = co
    hdr = ['%FSLAX34Y34*%','%MOMM*%'] + ap_lines + ['%LPD*%']
    body = []
    # Flash all pads (TH pads appear on both layers — that's correct for FR4)
    for px,py,net,lab,pw,ph,hole in pads:
        key = ('C', round(pw,4)) if hole > 0 else ('R', round(pw,4), round(ph,4))
        body.append(f'D{ap_map[key]}*')
        body.append(f'X{co2(px)}Y{co2(py)}D03*')
    # Draw traces on this layer
    for layer,w,pts,lab in traces:
        if layer != layer_name: continue
        key = ('C', round(w,4))
        body.append(f'D{ap_map[key]}*')
        body.append(f'X{co2(pts[0][0])}Y{co2(pts[0][1])}D02*')
        for x,y in pts[1:]: body.append(f'X{co2(x)}Y{co2(y)}D01*')
    body.append('M02*')
    open(os.path.join(OUT, fn),'w').write('\n'.join(hdr + body))

def write_mask(fn, pads):
    """Soldermask gerber: openings (positive = where soldermask is removed)."""
    # Collect unique pad apertures
    ap_map2 = {}; d2 = [10]; ap_lines2 = []
    def reg2(shape, *dims):
        # enlarge pad by 0.1 mm (standard mask expansion)
        if shape == 'C': key = ('C', round(dims[0]+0.1,4))
        else:            key = ('R', round(dims[0]+0.1,4), round(dims[1]+0.1,4))
        if key not in ap_map2:
            ap_map2[key] = d2[0]; d2[0] += 1
        return ap_map2[key]
    for px,py,net,lab,pw,ph,hole in pads:
        if hole > 0: reg2('C', pw)
        else:        reg2('R', pw, ph)
    for key, dc in sorted(ap_map2.items(), key=lambda x: x[1]):
        sh=key[0]; dims=key[1:]
        if sh=='C': ap_lines2.append(f'%ADD{dc}C,{dims[0]:.4f}*%')
        else:       ap_lines2.append(f'%ADD{dc}R,{dims[0]:.4f}X{dims[1]:.4f}*%')
    hdr = ['%FSLAX34Y34*%','%MOMM*%'] + ap_lines2 + ['%LPD*%']
    body = []
    for px,py,net,lab,pw,ph,hole in pads:
        if hole > 0: key = ('C', round(pw+0.1,4))
        else:        key = ('R', round(pw+0.1,4), round(ph+0.1,4))
        body.append(f'D{ap_map2[key]}*')
        body.append(f'X{co(px)}Y{co(py)}D03*')
    body.append('M02*')
    open(os.path.join(OUT, fn),'w').write('\n'.join(hdr + body))

def write_silk(fn, silk_items, pads):
    """Front silkscreen: component outlines + labels. Pads cleared automatically by fab."""
    lines = ['%FSLAX34Y34*%','%MOMM*%','%LPD*%',
             '%ADD10C,0.1500*%',   # thin outline line
             '%ADD11C,0.1000*%']   # thinner line
    def mk_circle(cx, cy, r, n=24):
        return [(cx+r*math.cos(2*math.pi*i/n), cy+r*math.sin(2*math.pi*i/n))
                for i in range(n+1)]
    for item in silk_items:
        t = item[0]
        if t == 'rect':
            _,x0,y0,x1,y1 = item
            pts = [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
            lines.append('D10*')
            lines.append(f'X{co(pts[0][0])}Y{co(pts[0][1])}D02*')
            for x,y in pts[1:]: lines.append(f'X{co(x)}Y{co(y)}D01*')
        elif t == 'circle':
            _,cx,cy,r = item
            pts = mk_circle(cx,cy,r)
            lines.append('D10*')
            lines.append(f'X{co(pts[0][0])}Y{co(pts[0][1])}D02*')
            for x,y in pts[1:]: lines.append(f'X{co(x)}Y{co(y)}D01*')
        elif t == 'line':
            _,x1,y1,x2,y2 = item
            lines.append('D11*')
            lines.append(f'X{co(x1)}Y{co(y1)}D02*')
            lines.append(f'X{co(x2)}Y{co(y2)}D01*')
        # 'text' entries are visible only in the PNG preview; proper silk text
        # requires Gerber text macros — add in KiCad during the DRC/pour step.
    lines.append('M02*')
    open(os.path.join(OUT, fn),'w').write('\n'.join(lines))

def write_outline(fn, outline):
    lines = ['%FSLAX34Y34*%','%MOMM*%','%ADD10C,0.1000*%','D10*',
             f'X{co(outline[0][0])}Y{co(outline[0][1])}D02*']
    for x,y in outline[1:]: lines.append(f'X{co(x)}Y{co(y)}D01*')
    lines.append('M02*')
    open(os.path.join(OUT, fn),'w').write('\n'.join(lines))

def write_drill(fn, pads, holes):
    g = defaultdict(list)
    for px,py,net,lab,pw,ph,hole in pads:
        if hole > 0: g[hole].append((px,py))
    for hx,hy,hd,hl in holes: g[hd].append((hx,hy))
    lines = ['M48','METRIC,TZ']
    for i,d in enumerate(sorted(g), 1): lines.append(f'T{i:02d}C{d:.3f}')
    lines.append('%')
    for i,d in enumerate(sorted(g), 1):
        lines.append(f'T{i:02d}')
        for x,y in g[d]: lines.append(f'X{x:.3f}Y{y:.3f}')
    lines.append('M30')
    open(os.path.join(OUT, fn),'w').write('\n'.join(lines))

# --- Build shared aperture table ---
ap_lines, ap_map = aperture_table(pads, traces)

# --- Write all layers ---
write_copper('node_sx1276-F_Cu.gtl',      'top', pads, traces, ap_lines, ap_map)
write_copper('node_sx1276-B_Cu.gbl',      'bot', pads, traces, ap_lines, ap_map)
write_mask  ('node_sx1276-F_Mask.gts', pads)
write_mask  ('node_sx1276-B_Mask.gbs', pads)
write_silk  ('node_sx1276-F_Silk.gto', silk, pads)
write_outline('node_sx1276-Edge_Cuts.gko', OUTLINE)
write_drill ('node_sx1276.drl',        pads, holes)

# --- Summary ---
drill_count = sum(1 for _,_,_,_,pw,ph,h in pads if h>0) + len(holes)
print(f'Gerbers → {OUT}/')
print(f'Board  : {BW}×{BH} mm  ({VERSION})')
print(f'Pads   : {len(pads)}  ({sum(1 for p in pads if p[6]>0)} TH + {sum(1 for p in pads if p[6]==0)} SMD)')
print(f'Traces : {len(traces)}  Holes: {drill_count}')
print()
print('NEXT STEPS:')
print('  1. Import gerbers into KiCad (File > Import > Gerber) or EasyEDA')
print('  2. Add B_Cu GND fill zone over full board')
print('  3. Clear GND pour from ANT pad area (RF keepout)')
print('  4. Run DRC — fix any clearance violations')
print('  5. Re-export gerbers + drill → zip → upload to jlcpcb.com')
print('  6. Verify XL1276-P01 pad pitch on your actual module before committing to fab')
