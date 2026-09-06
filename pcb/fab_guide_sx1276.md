# JLCPCB Fabrication Guide — Acoustic Node Carrier v3.0-sx1276

Board: **56 × 53 mm**, 2-layer FR4, XL1276-P01 / SX1276 variant.

---

## Step 1 — Finish the PCB in KiCad (required before ordering)

The script `gen_pcb_sx1276.py` produces the copper traces and pad footprints but
**does not generate the GND fill** (requires a polygon-pour tool). Do this once:

1. **Import gerbers into KiCad**
   `File → Import → Gerber` → select all files in `out_sx1276/`

2. **Add B_Cu GND fill zone**
   - Switch to B_Cu layer
   - `Place → Add Rule Area` → check "Copper fill", net = GND
   - Draw zone outline around the full board
   - `Edit → Fill All Zones` (shortcut `B`)

3. **RF keepout near ANT pad**
   - The XL1276-P01 ANT pad (left col, top) is at upper-left of the module
   - Add a B_Cu keepout rectangle (~10 × 10 mm) around the ANT pad and the
     area above the module where the wire antenna will sit
   - This prevents the GND pour from adding shunt capacitance to the antenna feed

4. **Run DRC**
   `Inspect → Design Rules Checker → Run DRC`
   Fix any clearance violations. Common issues:
   - 3V3 crossing trace (CROSSW = 0.2 mm) may be tight — JLCPCB min is 0.1 mm, fine
   - Verify XL1276-P01 pads are not flagged as overlapping module body

5. **Re-export gerbers**
   `File → Plot → Gerber` — use default KiCad layer mapping
   `File → Fabrication Outputs → Drill Files`
   Zip the exported files.

---

## Step 2 — JLCPCB Quote (15 units)

Go to **[jlcpcb.com](https://jlcpcb.com)** → "Order Now" → upload the zip.

### Recommended settings for 15 pcs

| Option | Value |
|---|---|
| Layers | **2** |
| Dimensions | Auto-detected (56 × 53 mm) |
| PCB Qty | **15** (JLCPCB supports any qty ≥ 5) |
| PCB Thickness | **1.6 mm** |
| PCB Color | **Green** (cheapest; any color same price at this qty) |
| Silkscreen | White (default) |
| Surface Finish | **HASL (with lead)** — cheapest, fine for TH solder joints |
|  | ENIG (+$15 for the order) if you want cleaner SMD pad finish |
| Copper Weight | **1 oz** |
| Min Hole Size | 0.8 mm (ESP/mic/GPS headers) — well within JLCPCB 0.2 mm min |
| Min Track/Spacing | 0.4 / 0.2 mm — standard tier |

> **HASL vs ENIG:** HASL is fine for all TH pads and the SMD castellation pads.
> ENIG gives a flatter surface that's easier to inspect after soldering the XL1276-P01.
> Pick ENIG if you're sharing boards with a friend who's less experienced soldering.

### Estimated pricing (Sep 2026)

| Item | Cost |
|---|---|
| 15 × PCB (56×53 mm, 2-layer, HASL, green) | **$13–18** |
| DHL Express shipping to US (~5–7 days) | **$22–28** |
| **Total for 15 boards** | **~$35–46** |
| Per-board cost | **~$2.30–3.10** |

> JLCPCB sometimes runs promotions: new-account first order ~$2 for 5 pcs.
> For 15 units there's no promo, but the price is stable. Verify at checkout —
> the calculator on the site is real-time.

> **Economy shipping** (JLCPCB Global Standard, ~15–25 days): ~$7–12 shipping,
> total ~$20–30 for 15 boards. Fine if you're not in a rush.

---

## Step 3 — Pre-order checklist

- [ ] GND pour added and filled in KiCad
- [ ] RF keepout set around ANT pad
- [ ] DRC passes with 0 errors
- [ ] Preview gerbers in [JLCPCB Gerber Viewer](https://gerber-viewer.jlcpcb.com/) — verify pad positions
- [ ] XL1276-P01 modules in hand — **measure the castellation pitch** with calipers
      before committing. Confirm 2 mm pitch and 16 × 16 mm body.
      If pitch differs, adjust `LORA_PW`/`LORA_PH` in `gen_pcb_sx1276.py` and regenerate.
- [ ] Confirm the exact pinout of your batch (VCC / GND / DIO0 position) with a multimeter

---

## Step 4 — Soldering order (recommended)

1. **SMD passives first** (C1, Cin, Cout, L1) — hardest to reach after modules
2. **U5 LDO** (MCP1700 TO-92) + battery terminals
3. **XL1276-P01** — solder castellation pads, inspect under magnification
4. **ESP32-S3-Zero** — insert into header pins, solder from below
5. **INMP441 + ATGM336H** — header pins, straightforward
6. **C2 electrolytic** — polarity: + to 3V3, − to GND (labelled on silkscreen)

**First power-on:** before inserting the ESP, apply 3.3 V to the board rails
and verify current draw < 15 mA (GPS + LoRa idle, no ESP). Then insert ESP and
proceed with `pio run -e lora_tx -t upload -t monitor`.

---

## Layer-to-filename reference (for JLCPCB upload)

| File | Content | JLCPCB auto-detected? |
|---|---|---|
| `node_sx1276-F_Cu.gtl` | Front copper | ✅ |
| `node_sx1276-B_Cu.gbl` | Back copper (+ GND pour from KiCad) | ✅ |
| `node_sx1276-F_Mask.gts` | Front soldermask openings | ✅ |
| `node_sx1276-B_Mask.gbs` | Back soldermask openings | ✅ |
| `node_sx1276-F_Silk.gto` | Front silkscreen | ✅ |
| `node_sx1276-Edge_Cuts.gko` | Board outline | ✅ |
| `node_sx1276.drl` | Drill file (Excellon, metric) | ✅ |

JLCPCB's auto-detection recognizes standard KiCad extensions. If it asks you to
manually assign layers, match the table above.

---

## Design notes

### Why no B_Cu silkscreen?
Component labels are on F_Cu silkscreen only — the bottom is the GND pour,
no room for text.

### C2 position
The 470 µF bulk capacitor is at upper-right (x≈50 mm) to clear the RST routing
lane. Use a standard **8 mm body, 3.5 mm lead pitch** radial cap. The PCB pad
spacing matches 3.5 mm exactly.

### XL1276-P01 antenna clearance
The wire antenna solders to the ANT castellation pad at the top of the left column.
The antenna wire can exit through a small hole in the enclosure lid or through the
acoustic vent grommet. The PCB has ~8 mm of board real-estate above the module
before the GPS header — route the antenna up and over the board edge.

### Power chain reminder
```
Solar (6V) → CN3791 MPPT → 18650 (1S) → Schottky 1N5822 → ESP32 5V pad
                                                                    │
                                                          MCP1700 LDO → 3.3V rail
                                                                    │
                                                     XL1276-P01 · INMP441 · GPS
```
The Schottky diode is **off-board** (between the CN3791 BAT+ and the ESP 5V pad
solder wire). It is NOT on the PCB — solder it inline on the power wire.
