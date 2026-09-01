# Acoustic Node Carrier — CNC Milling Guide

2-layer through-hole carrier for one node: **ESP32-S3-Zero + INMP441 mic +
ATGM336H GPS + RYLR689 LoRa**. Designed for **isolation milling on a hobby CNC**
with **unplated** holes and a **flip for the second side**.

Board: **84 × 58 mm**, matches the firmware net map (`node_config.h`).

## Files (`out/`)
| File | Layer |
|---|---|
| `node-F_Cu.gtl` | TOP copper (red in preview) |
| `node-B_Cu.gbl` | BOTTOM copper (blue) |
| `node-Edge_Cuts.gko` | board outline |
| `node.drl` | Excellon drill (all holes) |
| `node_preview.png` | labeled preview |

## ⚠ Verify before you cut copper
This is a **complete, correct netlist** and a milling-optimized layout, but it is
a **starting design generated programmatically** — treat it like a first draft:
1. **Footprints are 2.54 mm headers.** Confirm the **ESP32-S3-Zero** pad order/pitch
   and the **RYLR689** castellated pad layout against *your* actual parts and adjust
   pad positions if they differ. (The RYLR689 is a 16×16 mm castellated SMD module —
   you'll either solder it edge-on to pads or use a breakout.)
2. **Open the Gerbers in FlatCAM (or import to KiCad) and eyeball for same-layer
   crossings** before generating toolpaths. On a milled board two traces touching
   on one layer = a short. The router splits top/bottom, but verify — nudge any
   crossing to the other layer or reroute.
3. Run your CAM tool's isolation preview at your actual tool width.

## Milling parameters  (v2.1 — matches the current Gerbers/`node.drl`)
- **Isolation tool:** **fine V-bit, ~0.1 mm tip, 20–30°.** The board is a **uniform
  0.47 mm** isolation floor *everywhere* (set by the LoRa 1.27 mm pitch — no tighter
  spots). That is millable at **constant Z** on a small flattened blank — **no height
  map required.** Still: sharp V-bit, low spindle runout, and surface the spoilboard
  flat + stick the blank down fully so it's true to the machine.
- **Traces:** 0.8 mm signal · 1.4 mm power · **0.3 mm** at the single column crossing.
- **Drills (from `node.drl`, 4 tools):**
  - **0.5 mm** — LoRa module pads + JP1 ferrite via-in-pad
  - **0.8 mm** — ESP pads + BUSY via
  - **1.0 mm** — mic / GPS / LDO / battery / C2 leads
  - **3.2 mm** — M3 corner holes (×4; these also do the flip-registration)
- **Outline / notches / RF keepout:** **1.0–1.5 mm 2-flute flat end mill** — board edge,
  USB-C + ANT notches, and pocketing the RF-keepout rectangle. Leave tabs to hold it.

## Double-sided workflow (the flip) — M3 corner holes = registration
The **four M3 corner holes** double as registration (no separate dowels):
1. Drill all holes (incl. the four 3.2 mm corners) through the stock first.
2. Put two **M3 screws/dowel pins** through diagonal corners into your spoilboard.
3. Mill **bottom** copper (`B_Cu`). Lift, **flip about the vertical axis**, drop back
   onto the same two corner pins → orientation preserved. Mill **top** (`F_Cu`).
   - In CAM, mirror the top layer about the **Y axis** (vertical) so it matches the flip.
4. Cut the outline + notches last.

## Unplated holes — handling the few cross-layer nets
Holes are **not plated**, so a pin only connects to copper on the side you solder.
This layout is arranged so **most nets need only the bottom side**, and where a net
uses top copper it lands on a **component pad you can solder on top too**. Practical
rules at assembly:
- **Header/module pins that carry a top-layer trace:** solder them on **both** sides
  (or bend a tiny wire). The preview shows which pads have red (top) traces.
- **3V3 and GND:** soldered both sides at the module pads (they're the wide traces).
- There are **no blind vias** — every cross-layer point is at a solderable pad.

## Assembly order
0. **RF keepout (v2):** when generating the bottom isolation/pour, exclude the magenta
   keepout box at the antenna feed (`ANT`/`ANT_PAD` are the module's 50 Ω RF output) —
   leave that rectangle bare copper-free so the ground pour doesn't detune the antenna.
1. Mill both sides + drill + outline; deburr holes.
2. Solder the **RYLR689** first (tightest). Coil/uFL antenna to the **ANT** pad
   (never power it without an antenna).
3. Solder **ESP32-S3-Zero** (2 header rows), then **mic** and **GPS** headers.
4. Solder both-sides where the preview shows a top trace on a pin.
5. Confirm **L/R → GND** on the mic (left channel); **ANT**/**ANT_PAD** and their feed
   are clear of ground (the v2 keepout) — **ANT_PAD (pin 12) stays unconnected**.
6. Flash `twonode_llcc` (node 1) / `twonode_b_llcc` (node 2), verify per FIELD_TEST.md.

## Net map (what connects to what)
ESP32-S3-Zero →
```
GP1  ← GPS TX (NMEA)      GP7  → LoRa NRST        GP12 → LoRa SCK
GP2  → LoRa RFSW_V1       GP8  ← GPS PPS          GP13 → LoRa MISO
GP3  → LoRa BUSY          GP9  → LoRa DIO1        GP44 → LoRa RFSW_V2
GP4  → Mic SCK(BCLK)      GP10 → LoRa NSS         3V3  → mic/gps/lora VDD
GP5  → Mic WS            GP11 → LoRa MOSI         GND  → mic/gps/lora GND + mic L/R
GP6  → Mic SD             GP43 = spare (TX)       GP48 = onboard RGB (no wire)
```
GPS RX pin = **no-connect** (we only read the GPS). LoRa module GND on 3 pads → tie all to GND.

## BOM (per node)
| Ref | Part | Notes |
|---|---|---|
| U1 | ESP32-S3-Zero (S3FH4R2) | the MCU |
| U2 | INMP441 I²S mic | L/R→GND |
| U3 | ATGM336H GPS (w/ PPS) | active antenna for enclosed sites |
| U4 | RYLR689 (LLCC68, 915 MHz) | +915 coil/uFL antenna |
| — | 2.54 mm headers | per module |
| — | 2× 3.0 mm dowel pins | registration (reusable) |
| — | 4× M3 hardware | mounting |
| PCB | single-sided-clad? **use 2-layer clad** FR1/FR4 | FR1 mills cleaner than FR4 |

**Tip:** FR1 (paper-phenolic) or CEM machines much nicer than FR4 for isolation
milling (less fiberglass dust, cleaner edges). For 2 boards, panelize both on one
sheet with shared registration dowels.
