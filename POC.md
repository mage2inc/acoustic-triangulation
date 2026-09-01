# Proof-of-Concept Plan (USB-powered, no solar/battery)

Validate the *risky* parts — GPS-PPS time-sync and TDoA — before investing in
the power hardware. POC kits become the real nodes later (just add the power
stack). Nothing wasted.

## POC BOM (per node, USB-powered)
| Item | ~$ |
|---|---|
| ESP32-S3-Zero | 4.50 |
| INMP441 I²S mic | 1.80 |
| Ra-01 SX1278 w/ spring antenna | 4.50 |
| ATGM336H GPS (PPS + antenna) | 4.50 |
| USB-C cable | 1.50 |
| **Per node** | **~$17** |

**Dropped for POC:** solar panel, CN3791, 18650 + holder, Schottky/cap
(buck-boost already dropped), enclosure, acoustic vent.

**Power during test:** USB wall adapter + outdoor extension, or a power bank with
an always-on/low-current mode (plain power banks auto-off at ~58 mA). GPS needs
sky-view → nodes at windows / outside during tests.

## Cost
4 node kits (~$68) + ESP32-S3-DevKitC-1 (~$8) + Pi/microSD (on hand) ≈ **~$76**
vs ~$209 full build. Power hardware deferred until M2 passes.

## Milestones
1. **M1 — 1 node (bench).** I²S capture → onset detect → GPS lock → PPS timestamp
   → LoRa packet to base. Proves the node pipeline end to end. *(1 kit + DevKit)*
2. **M2 — 2 nodes (make-or-break).** Known separation; clap/bang; verify both
   timestamp the SAME event and Δt ≈ (Δdistance ÷ 343 m/s). **If PPS sync holds
   here, the project works.** *(2 kits)*
3. **M3 — 4 nodes at corners.** Full triangulation + Leaflet map; check fixes land
   within a few meters of the real source. *(4 kits)*

## After POC
Once M2/M3 pass, add per node: 12 V ~5–6 W panel + CN3791 (matched to panel V) +
3× 18650 (parallel) + Schottky + cap + IP65 box + acoustic vent. See BOM.md.

## Build order for firmware (do M1 first)
1. I²S continuous capture into a ring buffer (verify clean audio).
2. GPS NMEA parse + **PPS interrupt → discipline µs timer** (the crux).
3. Onset detect + sample→GPS-time timestamp.
4. LoRa packet {node_id, onset_us, lat, lon, amp} → base.
5. Base: collect, correlate, multilaterate, Leaflet map.
