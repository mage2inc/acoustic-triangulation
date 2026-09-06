# Power Budget — Acoustic Triangulation Nodes

## Field node current draw (continuous, 3.3 V rail)

| Subsystem | Mode | Current |
|---|---|---|
| ESP32-S3 (dual-core @ 80 MHz, STATE_LISTEN) | always-on | ~25 mA |
| ATGM336H GPS (lock acquired, PPS running) | always-on | ~28–35 mA |
| INMP441 MEMS mic (I²S DMA, always capturing) | always-on | ~1.4 mA |
| RYLR689 LoRa (idle / Tx burst avg ~0.1% duty) | mostly sleep | ~1–2 mA |
| **Total (typical)** | | **~58 mA** |

> **GPS is the dominant draw** — it stays on 100% of the time because it provides
> both the position AND the PPS timebase. Duty-cycling it saves ~15 mA average
> but requires a DS3231 TCXO holdover and adds firmware complexity (see Appendix A).

During `STATE_EVENT` (onset detected, classify + LoRa Tx):
- CPU briefly runs @ 240 MHz → +~50 mA for ~100–300 ms
- LoRa Tx @ +20 dBm → +~120 mA for ~50 ms
- Both are short bursts; average impact on daily energy is negligible (<0.5%)

**Average draw used for sizing: 58 mA @ 3.3 V = ~0.19 W**

---

## Daily energy

```
58 mA × 3.3 V × 24 h = 4.6 Wh/day
```

---

## Solar panel sizing

A 5 W / 6 V panel in a mid-latitude location with ~4 peak-sun-hours/day delivers:

```
5 W × 4 h × ~0.85 (MPPT efficiency) = ~17 Wh/day harvested
```

vs. **4.6 Wh/day needed** → **3.7× margin**. Covers cloudy stretches and charging
the battery simultaneously. Don't downsize the panel — the GPS is not negotiable.

| Panel | Cost | Verdict |
|---|---|---|
| 6 V 5 W (110 × 136 mm) | ~$8 | ✅ right-sized, use this |
| 6 V 2 W | ~$4 | ❌ marginal even in full sun |
| 12 V 10 W | ~$15 | overkill, also needs a different charger |

> **"10 W" panel gotcha:** a panel labeled 10 W doing 12 V × 0.166 A is really
> ~2 W. Always check Vop × Iop (the operating point), not the label.

---

## Battery sizing

| Config | Capacity | Autonomy (no sun) | Notes |
|---|---|---|---|
| 1× 18650 (2 500 mAh) | ~8.3 Wh | **~1.5 days** | lean / default BOM |
| 2× 18650 (5 000 mAh) | ~16.5 Wh | **~3.5 days** | +$4/node, recommended |
| 3× 18650 (7 500 mAh) | ~24.8 Wh | **~5 days** | +$8/node, comfortable margin |
| 1× 32700 LiFePO₄ (6 000 mAh) | ~19.8 Wh | **~4.2 days** | +$5/node, safer in hot enclosures |

Autonomy formula: `capacity_Wh / 4.6 Wh/day`

**Recommendation:** 2× 18650 in parallel (or 1× 32700 LiFePO₄ if the enclosure
gets hot). The system tolerates a node browning out and rejoining — a missed
detection just reduces fix quality slightly.

> ❌ **Never use a USB power bank.** They auto-cutoff at low draw (~58 mA triggers
> most power banks' "no load" protection). Use bare Li-ion cells with a 1S
> protection board, or protected cells.

---

## Power chain

```
6 V solar panel
    │
    ▼
CN3791 MPPT charger  ──── charges ──── 18650 cell (1S)
    │                                       │
    └─── (direct path when sun > load) ─────┘
                                            │
                                        Schottky diode
                                            │
                                    ESP32-S3-Zero 5V pad
                                            │
                                     onboard AMS1117 LDO
                                            │
                                           3V3 ──► GPS, mic, LoRa, ESP32
```

No separate buck-boost needed — the ESP32-S3-Zero's onboard LDO accepts 3.3–6 V
on the 5V pad and regulates to 3.3 V. The Schottky diode prevents USB-C and the
solar supply from fighting when you plug in for debugging.

---

## Appendix A: Low-power variant (DS3231 holdover)

Halves average current by duty-cycling the GPS. Only worthwhile on battery-only
or heavily shaded nodes.

### How it works

1. Node acquires GPS lock, pairs PPS, then gates off the GPS module.
2. A DS3231 TCXO RTC (±2 ppm) takes over as the time reference.
3. GPS wakes every ~3 minutes for a 2–5 s re-discipline pulse, then sleeps again.

### Error budget during holdover

```
Holdover gap: 3 min = 180 s
DS3231 drift: ±2 ppm
Max timing error: 180 s × 2×10⁻⁶ = 360 µs
Distance error: 360 µs × 343 m/s = ~0.12 m
```

Sub-meter — GPS position error (2–5 m) still dominates. The holdover approach is
timing-safe.

### Power savings

| Subsystem | Always-on | With holdover |
|---|---|---|
| GPS | ~30 mA | ~2 mA avg (30 mA × 5 s / 180 s) |
| DS3231 | 0 | ~0.2 mA |
| **Total** | **~58 mA** | **~30 mA** |

~48% reduction. Daily energy drops from 4.6 Wh to ~2.4 Wh → a 2 W panel and
1× 18650 are sufficient.

### Cost

| Part | ~$ |
|---|---|
| DS3231 RTC module (32 kHz + coin cell backup) | $1.50 |
| CR2032 coin cell | $0.50 |
| **Per node add-on** | **~$2** |

### When to use it

- Battery-only nodes (no solar) ✅
- Heavily shaded nodes where the 5 W panel can't fully recharge ✅
- Nodes that need to last a week between maintenance visits ✅
- Solar nodes in a sunny location ❌ (already power-positive, not worth the complexity)
