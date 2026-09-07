# Acoustic Triangulation — BOM (SX1276 / XL1276-P01 variant, v3 manufactured PCB)

> ⚠️ **UNTESTED VARIANT** — PCB gerbers are generated and verified for correctness,
> but no boards have been ordered or soldered yet. Use [BOM.md](../BOM.md) (RYLR689 v2)
> if you need a working node today. This file tracks the v3 SX1276 variant for future production.

> **Radio: XL1276-P01 (Semtech SX1276, 915 MHz, SPI).** Simpler wiring than RYLR689:
> only NSS/SCK/MOSI/MISO/RST/DIO0 — no RF-switch lines, no BUSY pin. GP7 + GP8 freed.
> Firmware default in `node_config.h` — **no build flags needed**.

> **PCB: v3.0-sx1276 manufactured board** (56×53 mm, 2-layer FR4, JLCPCB).
> Replaces hand-wiring. See [`pcb/fab_guide_sx1276.md`](pcb/fab_guide_sx1276.md)
> for ordering instructions, Gerber checklist, and pricing.

Prices = AliExpress/Amazon best-deal tier, USD, Sep 2026. Buy 1–2 spares on cheap parts.

---

## On-board components (soldered to the PCB — per node)

| # | Item | Footprint | Unit $ | Qty/node | Line $ |
|---|---|---|---|---|---|
| U1 | ESP32-S3-Zero (S3FH4R2, 4 MB flash 2 MB PSRAM) | 2×9 2.54mm TH header | 4.50 | 1 | 4.50 |
| U2 | XL1276-P01 SX1276 915 MHz LoRa module | 16×16mm SMD castellation | 12.00 | 1 | 12.00 |
| U3 | INMP441 I²S MEMS mic module | 2×3 2.54mm TH header | 1.80 | 1 | 1.80 |
| U4 | ATGM336H GPS module (PPS pin required) | 1×5 2.54mm TH header | 4.50 | 1 | 4.50 |
| U5 | MCP1700-3302E/TO-92 LDO (or HT7333-A) | TO-92 TH | 0.30 | 1 | 0.30 |
| C1 | 10 µF 16V MLCC 0805 (local LoRa VCC decoupling) | 0805 SMD | 0.05 | 1 | 0.05 |
| C2 | 470 µF 10V low-ESR electrolytic, radial 8mm | TH 3.5mm pitch | 0.40 | 1 | 0.40 |
| Cin | 1 µF 25V MLCC 0805 (LDO input cap) | 0805 SMD | 0.03 | 1 | 0.03 |
| Cout | 1 µF 25V MLCC 0805 (LDO output cap) | 0805 SMD | 0.03 | 1 | 0.03 |
| L1 | 600 Ω @ 100 MHz ferrite bead 0805 (e.g. BLM21PG601SN1) | 0805 SMD | 0.05 | 1 | 0.05 |
| J1 | 2-pin screw terminal or solder pads for battery | TH 2.54mm (B+ B−) | 0.15 | 1 | 0.15 |
| — | PCB (v3.0-sx1276, JLCPCB 2-layer FR4) | — | ~1.80 | 1 | 1.80 |
| | **Per-node board subtotal** | | | | **~$25.60** |

> **XL1276-P01 pinout:** Footprint uses the ACTUAL verified pinout from the XL1276-D01
> datasheet — NOT Ra-01S-compatible. Left col: ANT GND GND DIO1 DIO2 DIO3 DIO4 DIO5.
> Right col: GND VCC DIO0 RST SCK MISO MOSI NSS (top→bot). DIO0 is on the right column.
> **Verify VCC and GND with a multimeter before first power-on.**
> If pitch differs from 2 mm, adjust `LORA_PW`/`LORA_PH` and regenerate.

---

## Field node ×4 (solar, weatherproof)

| # | Item | Unit $ | Qty | Line $ |
|---|---|---|---|---|
| — | PCB + on-board components (above) | 25.60 | 4 | 102.40 |
| P1 | 6 V 5 W solar panel (110×136 mm) | 8.00 | 4 | 32.00 |
| P2 | CN3791 1S Li-ion MPPT solar charger module | 3.00 | 4 | 12.00 |
| P3 | 18650 Li-ion cell ×1 + holder (lean) | 5.00 | 4 | 20.00 |
| P4 | 1N5822 Schottky diode (solar/USB coexist) | 0.15 | 4 | 0.60 |
| E1 | IP65 ABS enclosure ~100×68×50 mm | 4.50 | 4 | 18.00 |
| E2 | Acoustic vent / PTFE membrane | 1.50 | 4 | 6.00 |
| E3 | M3 nylon standoffs ×4 (mount PCB in box) | 0.50 | 4 | 2.00 |
| E4 | Wire, JST, heat-shrink, pole mount | 5.00 | 4 | 20.00 |
| | **Field-node subtotal (lean power)** | | | **~$213** |

Battery options: 2× 18650 (+$4/node, ~3.5-day autonomy) · 3× (+$8/node, ~5 days)
· 1× 32700 LiFePO₄ (+$5/node, safer in hot enclosures, ~4.2 days)

---

## Office node ×1 (mains, USB-powered from Pi)

| # | Item | Unit $ | Qty | Line $ |
|---|---|---|---|---|
| — | PCB + on-board components | 25.60 | 1 | 25.60 |
| H1 | Active external GPS antenna (SMA, 3V, 28 dB) | 4.50 | 1 | 4.50 |
| H2 | Small enclosure + USB-C cable | 4.50 | 1 | 4.50 |
| | **Office-node subtotal** | | | **~$35** |

---

## Base compute + bench-dev

| # | Item | Unit $ | Qty | Line $ |
|---|---|---|---|---|
| B1 | Raspberry Pi (on hand) | 0 | 1 | 0 |
| B2 | microSD 16 GB+ | 6.00 | 1 | 6.00 |
| D1 | ESP32-S3-DevKitC-1 (bench / extra node dev) | 8.00 | 1 | 8.00 |

---

## Totals

| Group | v2 (RYLR689 breadboard) | v3 (SX1276 manufactured PCB) |
|---|---|---|
| 4 field nodes | $189 | **$213** |
| 1 office node | $28 | **$35** |
| Base + bench | $14 | $14 |
| **Total** | **~$231** | **~$262** |

The ~$31 increase buys: manufactured PCBs (no hand-wiring, 5 boards), XL1276-P01
modules (2-3× pricier than RYLR689), and 4 free GPIOs per node.

---

## 15-unit batch (for sharing with a friend)

| Item | 15× qty | Estimated $ |
|---|---|---|
| XL1276-P01 modules | 15 | ~$90–120 (AliExpress ~$6–8 ea) |
| ESP32-S3-Zero | 15 | ~$45–60 |
| INMP441 mic | 15 | ~$15–25 |
| ATGM336H GPS | 15 | ~$35–50 |
| PCB (15 pcs JLCPCB) | 15 | ~$17–28 incl. shipping |
| Passives (U5, C1/C2, L1, etc.) | 15 sets | ~$20 |
| **15-board electronics subtotal** | | **~$220–280** |

Solar/enclosure/battery ordered separately per deployment. See
[`pcb/fab_guide_sx1276.md`](pcb/fab_guide_sx1276.md) for the exact JLCPCB quote
procedure and shipping options.

---

## Buy links (verify variant/price at order)

- **XL1276-P01** (SX1276, 915 MHz): [Amazon JESSINIE B0BXDNFZ2B](https://www.amazon.com/dp/B0BXDNFZ2B) ~$12 · AliExpress "XL1276-P01" ~$5–8
- **ESP32-S3-Zero**: [AliExpress "ESP32-S3-Zero"](https://www.aliexpress.com/item/1005007088521314.html) ~$4.50
- **INMP441**: [AliExpress ~$1.61](https://www.aliexpress.com/item/32962426410.html)
- **ATGM336H** (with PPS pin): [AliExpress ~$2.66](https://www.aliexpress.com/item/33034354199.html)
- **MCP1700-3302E**: Mouser / DigiKey ~$0.30
- **470 µF low-ESR 10V radial**: DigiKey / LCSC
- **6 V 5 W solar**: [Waveshare](https://www.waveshare.com/solar-panel-6v-5w.htm)
- **CN3791 MPPT**: [ICStation](https://www.icstation.com/cn3791-charging-mppt-solar-power-panels-lithium-battery-charging-module-p-15791.html)

*Prices verified Sep 2026; treat as ±30%.*
