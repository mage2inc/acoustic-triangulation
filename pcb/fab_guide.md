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

## Milling parameters
- **Isolation tool:** 0.1–0.2 mm 30–60° V-bit, *or* a 0.8 mm flat end mill.
- **Traces:** 0.8 mm signal, 1.4 mm power (3V3/GND). **Clearance ≥ 0.6 mm** — safe
  for the above tools with one isolation pass (two passes if you want more copper
  removed near the pads).
- **Drills (from `node.drl`):**
  - **1.0 mm** — all header/module pins
  - **3.2 mm** — M3 mounting (×4 corners)
  - **3.0 mm** — registration dowels (×2, top & bottom centerline)
- **Outline:** 1.5–2 mm end mill, tabs to hold the board.

## Double-sided workflow (the flip) — registration dowels
The two **3.0 mm REG holes** sit on the vertical centerline (top & bottom). Use them
to keep top/bottom aligned:
1. Drill the two REG holes **first** (and the pin/mount holes) through the stock.
2. Press two **3.0 mm dowel pins** into your spoilboard at the matching spots.
3. Mill **bottom** copper (`B_Cu`). Lift, **flip about the vertical axis**, drop
   back onto the same two dowels → orientation preserved. Mill **top** (`F_Cu`).
   - In CAM, mirror the top layer about the **Y axis** (vertical) so it matches the flip.
4. Then cut the outline.

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
1. Mill both sides + drill + outline; deburr holes.
2. Solder the **RYLR689** first (tightest). Coil/uFL antenna to the **ANT** pad
   (never power it without an antenna).
3. Solder **ESP32-S3-Zero** (2 header rows), then **mic** and **GPS** headers.
4. Solder both-sides where the preview shows a top trace on a pin.
5. Confirm **L/R → GND** on the mic (left channel), **ANT** stub is clear of ground.
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
