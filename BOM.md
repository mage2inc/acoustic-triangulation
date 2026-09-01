# Acoustic Triangulation — Price-Shopped BOM

> **RADIO: RYLR689 (Semtech LLCC68, 868/915 MHz).** Replaces the earlier Ra-01/
> SX1278 (433). It's a bare **SPI** LLCC68 (not an AT-command UART module), so it
> drops into the RadioLib firmware — but it needs **3 extra GPIO** vs the SX1278
> (BUSY + two RF-switch lines) and a **crystal, not a TCXO** (firmware TCXO=0.0).
> See node_config.h + WIRING.md. US ISM = **915 MHz**.

> **CURRENT PHASE: 2-node bench test.** Building **2** nodes (ESP32-S3 + INMP441 +
> ATGM336H + RYLR689) to validate the LoRa link and the make-or-break 2-node GPS
> time-sync (M2). If M2 holds, scale to the 5-node topology below **and spin a PCB**
> (which also ends the breadboard pin crunch the RYLR689 causes).

**Topology (target, after the test passes): 4 solar nodes (one per corner) + 1
office node (sensor + LoRa gateway + base, mains-powered) = 5 detection points.**
Prices = best-deal / AliExpress tier, USD, Aug 2026. Amazon/DigiKey ~1.5–2×.
Buy 1–2 spares of the cheap bits.

Battery = **Li-ion, 1S/parallel** (site doesn't freeze). **Never a LiPo pouch in
a hot box, never a USB power bank** (auto-off at ~58 mA). LiFePO4 = +~$5/node
upgrade for heat longevity.

Power note: the **5 W panel is right-sized** for continuous-GPS (~4.6 Wh/day) —
don't shrink it. Save instead on the **battery** (system tolerates a node
browning out and rejoining). Default below uses a **lean 1× 18650 (~1.5-day
autonomy)**; bump to 2–3 cells for more margin.

---

## Field node ×4 (solar, weatherproof, at corners)

| # | Item | Unit $ | Qty | Line $ |
|---|---|---|---|---|
| 1 | ESP32-S3-Zero (S3FH4R2, 2 MB PSRAM) | 4.50 | 4 | 18.00 |
| 2 | INMP441 I²S mic | 1.80 | 4 | 7.20 |
| 3 | **RYLR689** LLCC68 915 MHz **w/ spring antenna** | 9.00 | 4 | 36.00 |
| 4 | ATGM336H GPS (PPS + patch antenna) | 4.50 | 4 | 18.00 |
| 5 | 6 V 5 W solar panel | 8.00 | 4 | 32.00 |
| 6 | CN3791 1S Li-ion MPPT solar charger | 3.00 | 4 | 12.00 |
| 7 | 18650 cell ×1 (lean) + holder | 5.00 | 4 | 20.00 |
| 8 | Schottky diode + 220–470 µF cap (LDO-direct, no buck-boost) | 0.50 | 4 | 2.00 |
| 9 | IP65 ABS enclosure ~100×68×50 mm | 4.50 | 4 | 18.00 |
| 10 | Waterproof acoustic vent / PTFE membrane | 1.50 | 4 | 6.00 |
| 11 | Wire, JST, heat-shrink, pole mount | 5.00 | 4 | 20.00 |
| | **Field-node subtotal (lean power)** | | | **$189** |

Power chain: `6V solar → CN3791 → 18650 (1S) → Schottky → ESP32 5V pad → onboard LDO → 3V3` (no separate buck-boost; board takes 3.3–6 V in, USB-C coexists via the diode).
- **More autonomy:** 2× 18650 (+$4/node, ~3.5 days) or 3× (+$8/node, ~5 days).
- **Salvaged 18650s** (laptop/tool packs) → cells nearly free.
- **Mains-tap a corner** near existing power: a ~$5 weatherproof 5 V supply
  replaces items #5–8 (~−$18/node).
- **Cut draw (DS3231 holdover, design-doc Appendix A):** halves draw → a 2–3 W
  panel + 1 cell suffices; +$2 + firmware.

---

## Office node ×1 (mains: sensor + LoRa gateway + base)

Same sensor as a field node, minus solar/battery/weatherproofing, **USB-powered
from the Pi**. Receives the 4 field nodes over LoRa AND is a 5th detection point.

| # | Item | Unit $ | Qty | Line $ |
|---|---|---|---|---|
| H1 | ESP32-S3-Zero | 4.50 | 1 | 4.50 |
| H2 | INMP441 I²S mic | 1.80 | 1 | 1.80 |
| H3 | **RYLR689** LLCC68 915 MHz w/ spring antenna | 9.00 | 1 | 9.00 |
| H4 | ATGM336H GPS + **active external GPS antenna** | 8.50 | 1 | 8.50 |
| H5 | Small case + USB-C cable (Pi powers it) | 4.50 | 1 | 4.50 |
| | **Office-node subtotal** | | | **~$28** |

> **Office node needs GPS sky-view for PPS** — indoors gets no fix. Route the
> active GPS antenna to a window/roof, or mount the node on an exterior wall.

---

## Base compute + bench-dev

| # | Item | Unit $ | Qty | Line $ |
|---|---|---|---|---|
| B1 | Raspberry Pi (on hand) — solver + Leaflet map | 0 | 1 | 0 |
| B2 | microSD 16 GB+ | 6 | 1 | 6 |
| D1 | ESP32-S3-DevKitC-1 (headered, prototyping) | 8 | 1 | 8 |

> No separate LoRa dongle — the **office node IS the gateway** (its Ra-01 hears
> the field nodes; forwards them + its own detections to the Pi over USB).

---

## Totals

| Group | Cost |
|---|---|
| 4 field nodes (lean power) | $189 |
| 1 office node | $28 |
| Base (Pi on hand) + microSD | $6 |
| Bench-dev kit | $8 |
| **Project total** | **~$231** (+ Pi if not on hand) |

**2-node test build (current):** 2× [ESP32-S3-Zero $4.50 + INMP441 $1.80 +
ATGM336H $4.50 + RYLR689 $9.00] ≈ **$40** (parts on hand). No power/enclosure yet.

Add-ons: +$4–8/node for bigger battery; −$18/node per corner you can mains-tap;
+$20 total for LiFePO4 field cells.

---

## Data flow
```
[Corner node 1..4]  --LoRa 915-->  [Office node ESP32]  --USB-->  [Pi]
     (solar sensor)                 (gateway + 5th sensor)      (solver + Leaflet map)
```

## Ordering gotchas
- **RYLR689 with bundled coil antenna** — **solder the coil to the ANT pad
  (pin 10) before ANY TX**; keying the +22 dBm PA into an open can damage it.
- **RYLR689 is a bare SPI LLCC68** (good — uses RadioLib), NOT the AT-command
  UART type. Needs BUSY + RFSW_V1/RFSW_V2 wired, and TCXO=0.0 (it has a crystal).
- **ATGM336H must have the PPS pin** broken out — confirm on the listing.
- **Office node = active external GPS antenna**; field nodes = patch antenna at
  top of enclosure (sky view).
- **Acoustic vent** (#10) so the sealed box doesn't muffle the mic.
- **Li-ion:** genuine cells, wire **1S/parallel**, add a 1S protection board or
  use protected cells. Bare pack — **not** a USB power bank.

## Buy links (verify variant/price at order)
- [ESP32-S3-Zero](https://www.amazon.com/Development-Bluetooth-ESP32-S3FH4R2-XYGStudy-ESP32-S3-Zero/dp/B0CN8KMKHJ) (cheaper on AliExpress) ·
  [INMP441 ~$1.61](https://www.aliexpress.com/item/32962426410.html) ·
  [ATGM336H ~$2.66](https://www.aliexpress.com/item/33034354199.html)
- [RYLR689 (LLCC68 915 MHz, SPI)](https://www.amazon.com/RYLR689-Wireless-Include-Antenna-Interface/dp/B0BNVKQ9JD) ·
  [6 V 5 W panel](https://www.waveshare.com/solar-panel-6v-5w.htm) ·
  [CN3791 charger](https://www.icstation.com/cn3791-charging-mppt-solar-power-panels-lithium-battery-charging-module-p-15791.html) ·
  [IP65 box](https://www.aliexpress.us/item/3256811371680313.html)

*Prices verified Aug 2026 (AliExpress/Waveshare/Amazon); treat as ±30%.*
