# Acoustic Triangulation — Node Firmware Design

Two-tier (lazy) firmware for a solar-powered sensor node in a distributed
loud-noise/gunshot triangulation network. Nodes detect a loud transient,
precisely timestamp its **onset** against GPS PPS, classify it, and send a tiny
report over LoRa. The base station collects reports from ≥3 nodes and solves
for the source location (TDoA multilateration) on a Leaflet/OSM map.

**Design targets**
- Sub-meter localization on a 52 m × 155 m property.
- Runs continuously on solar; average current near the low-power floor.
- Rejects false alarms (thunder, car doors, dogs) via classification.

---

## 1. Hardware per node

| Block | Part | Interface | Notes |
|---|---|---|---|
| MCU | ESP32-S3 (N16R8, 16 MB flash / 8 MB PSRAM) | — | dual-core; wake-to-classify |
| Mic | INMP441 (I²S MEMS) | I²S | continuous DMA capture |
| Radio | Ra-01 / SX1278 (433 MHz LoRa) | SPI + DIO0 IRQ | tiny report packets |
| Time/pos | ATGM336H (GPS+BDS timing) | UART (NMEA) + **PPS** | PPS is the whole ballgame |
| Power | 5–6 W panel + 2× 18650 + CN3791/TP4056 | — | see power notes |

### Pin map — Waveshare ESP32-S3-Zero
**The map is `firmware/src/node_config.h`, not this document.** It moved twice
(SX1278 → RYLR689, then again for the carrier PCB), and the copy that used to sit
here survived both — long enough to point PPS at a pin the radio driver had taken
as an output. Every sketch prints the map it was compiled with at boot; wire from
that. This section keeps only the *constraints* that choose the pins:

- Avoid strapping pins, the USB D± pair, and the onboard WS2812.
- USB-CDC console frees UART0, so both UART0 pins are usable GPIO.
- **PPS must be interrupt-capable, non-strapping, and driven by nothing but the
  GPS** — it is the whole timebase. A PPS sharing a GPIO with any output the
  firmware drives is a build error (`static_assert` in node_config.h), because the
  symptom — no edges, clock never ready, node silently never transmits — is
  indistinguishable from a GPS that has no fix.
- All signals are 3.3 V — no level shifting.

Power: the radio and ATGM336H run on **3V3** (Ra-01 is NOT 5 V tolerant); the board
5V pad feeds the regulator from the solar/battery supply.

---

## 2. The crux: GPS-PPS timekeeping

Everything depends on all nodes sharing one clock to < ~1 ms. We get that from
the GPS **PPS** (pulse-per-second) edge, which is aligned across all GPS
receivers on Earth to < 1 µs. We never use LoRa for timing.

### Clock model
Maintain a mapping between the **local high-res timer** (`esp_timer`, 1 µs, or the
CPU cycle counter) and **GPS UTC**:

- On every **PPS rising edge** (hardware ISR), latch the local timer:
  `t_pps_local = now_us()`. The NMEA sentence that follows tells you which UTC
  second that PPS marked → keep `utc_at_pps`.
- Measure `ticks_between_pps = t_pps_local[n] - t_pps_local[n-1]`. Nominal is
  1 000 000 µs; the deviation is your local oscillator error (ppm). Use it to
  scale interpolation (optional but improves accuracy / holdover).

### Sample → GPS time
I²S samples arrive via DMA at a fixed rate `Fs` (e.g., 16 kHz). To timestamp a
specific **sample index**:

- On each DMA "buffer complete" ISR, latch `now_us()` and the running
  `sample_count`. This anchors `sample_index ↔ local_time`.
- For any sample: `local_time = anchor_time + (sample_index - anchor_index)/Fs`.
- Then convert local_time → GPS time via the PPS mapping:
  `T_gps = utc_at_pps + (local_time - t_pps_local) * (1e6 / ticks_between_pps)`.

**Achievable precision:** limited by `Fs` (16 kHz = 62.5 µs/sample; interpolate
the threshold crossing for sub-sample), ISR jitter (~µs), and PPS jitter (~µs).
Realistically **~50–200 µs → ~2–7 cm of ranging error**. Timing is *not* your
accuracy limiter; node geometry and echoes are.

> Keep the I²S DMA ring buffer running even in the low-power tier, so the
> onset sample already exists in memory when the threshold trips.

---

## 3. Audio ring buffer

A continuous circular buffer of recent audio in RAM.

- 16 kHz × 16-bit × 1.0 s = **32 KB** (trivial; with PSRAM keep several seconds).
- Purpose: **pre-trigger history.** The energy threshold trips slightly *after*
  the true onset; the pre-roll lets you look back and find the real onset edge.
- Window captured per event: ~50 ms pre-trigger + ~250 ms post-trigger.

```
      ring buffer (circular, always filling via DMA)
  ...[....pre-roll....][ONSET][....decay....].... write ptr ->
                         ^ found by looking back from trigger point
```

---

## 4. Two-tier state machine (the "lazy" design)

```
        ┌──────────────────────────────────────────────┐
        │  STATE_LISTEN  (CPU 80 MHz, low power)         │
        │  • I²S DMA -> ring buffer (always)             │
        │  • PPS ISR keeps clock disciplined             │
        │  • per-DMA-buffer: cheap energy/peak check     │
        │  • LoRa idle (sleep or RX)                     │
        └───────────────┬──────────────────────────────┘
                        │ energy > THRESHOLD
                        v
        ┌──────────────────────────────────────────────┐
        │  STATE_EVENT   (CPU 240 MHz, brief burst)      │
        │  1. snapshot ring-buffer window                │
        │  2. find precise onset sample (rising edge)    │
        │  3. T_onset = sample->GPS time  (Sec.2)        │
        │  4. classify window (Sec.5)                    │
        │  5. if of-interest: build + TX LoRa report     │
        │  6. refractory dead-time (~700 ms) to ignore   │
        │     echoes, then -> STATE_LISTEN               │
        └──────────────────────────────────────────────┘
```

Because loud events are rare (seconds/day), you sit in STATE_LISTEN ~99.9 % of
the time → average current ≈ the low tier, while STATE_EVENT gives you full
S3-class classification only when it matters.

> **Power reality:** this shaves the *CPU* portion. GPS (~30–50 mA continuous)
> is the dominant draw and is unchanged — it sets the floor.

---

## 5. Onset detection & classification

### Onset (timing-critical)
- Trigger: short-window RMS/energy over a sliding ~2–5 ms window exceeds an
  adaptive threshold (threshold = k × rolling noise floor).
- Precise onset: from the trigger point, walk **backward** in the ring buffer to
  the last sample below a lower fraction of the peak → that's the onset edge.
  Optionally linear-interpolate the exact crossing for sub-sample time.

### Classification (false-alarm rejection)
Compute cheap features over the captured window and score impulsive-vs-not:

| Feature | Gunshot-like | Rejects |
|---|---|---|
| Rise time (10→90 % of peak) | very short (< 1–2 ms) | slow → thunder, engine |
| Total duration | short (tens of ms + echoes) | long → rumble, music |
| Peak amplitude | high | low → distant/ambient |
| Spectral flatness / centroid | broadband, high | tonal → alarms, voices |
| Zero-crossing rate | high | low → thuds |
| (optional) crest factor | high | compressed sounds |

Start with a simple weighted-threshold rule; upgrade to a tiny TinyML model
later if needed. Emit a `class` id + `confidence`.

---

## 6. LoRa transmit — collision avoidance (important)

Every node hears the same gunshot within ~450 ms, so **all nodes want to
transmit at nearly the same instant** → LoRa collisions that could wipe out the
event. Two rules fix this:

1. **The timestamp is in the payload, not the RX time** — so *when* the packet
   arrives at the base doesn't matter. We can freely delay/jitter TX.
2. **Per-node staggered backoff:** after capturing `T_onset`, wait
   `backoff = node_id × 60 ms + small_random` before transmitting. Nodes'
   packets are then spread out and don't collide. Optionally listen-before-talk.

Also: 2–3 quick repeats per report (LoRa is lossy), deduped at the base by
`(node_id, seq)`.

### Packet format (~20 bytes — MOBILE nodes send their own position)
```
byte  field
0     node_id                (1)
1-2   seq                    (2)   for dedupe / repeats
3-7   onset_time_us          (5)   40-bit: µs-of-hour (or since GPS epoch tick)
8-11  latitude               (4)   int32, 1e-7 deg  (~1 cm resolution)
12-15 longitude              (4)   int32, 1e-7 deg
16-17 peak_amp               (2)
18    class_id               (1)
19    confidence             (1)
+ LoRa hardware CRC
```
> **Nodes are static during operation but self-locating.** At deploy each node
> takes a GPS position lock and **averages it while stationary** (pulls error to
> ~1–2 m), stores it, and includes it in every report. So nodes are plug-and-play
> and handle redeployment automatically — no manual survey, no base lookup table.
> GPS keeps running afterward purely for PPS timing.

**LoRa params:** 433 MHz, SF7–SF9 / 125 kHz (short range, low airtime), CRC on,
explicit header.

---

## 7. Concurrency layout (dual-core)

```
Core 0 (real-time, never blocks):
  • I²S DMA buffer-done ISR: latch time anchor, run energy check,
    set event flag on trigger
  • PPS ISR: latch t_pps_local, update clock mapping

Core 1 (app):
  • GPS UART / NMEA parse -> utc_at_pps, node health
  • on event flag: snapshot window, onset, classify, backoff, LoRa TX
  • status LED / housekeeping
```

Keep ISRs tiny (latch + flag). Do all heavy work (classify, TX) on Core 1.

---

## 8. Main-loop pseudocode

```c
void setup() {
  clock_set(80_MHz);
  i2s_start_dma(Fs=16000, ring_buffer);      // runs forever
  attach_isr(PPS_PIN, on_pps_edge);          // Core 0
  attach_i2s_done_isr(on_dma_buffer);        // Core 0
  gps_uart_begin();                          // Core 1
  lora_begin(433E6, SF8, 125E3);
  state = LISTEN;
}

// ---- Core 0 ISRs ----
void on_pps_edge() {
  uint64_t t = now_us();
  ticks_between_pps = t - t_pps_local;
  t_pps_local = t;
  pps_seen = true;                            // NMEA parser fills utc_at_pps
}

void on_dma_buffer(int16_t* buf, int n) {
  anchor_time = now_us(); anchor_index = (sample_count += n);
  float e = energy(buf, n);
  noise_floor = 0.999f*noise_floor + 0.001f*e;    // slow adaptive
  if (state == LISTEN && e > K * noise_floor) {
    trigger_index = sample_count;
    event_flag = true;                            // hand to Core 1
  }
}

// ---- Core 1 ----
void loop() {
  gps_service();                              // parse NMEA -> utc_at_pps
  if (event_flag && state == LISTEN) {
    state = EVENT; clock_set(240_MHz);
    Window w = snapshot_ring(trigger_index, PRE=50ms, POST=250ms);
    size_t onset = find_onset(w);
    uint64_t T_onset = sample_to_gps_time(onset);   // Sec.2
    Class c = classify(w);                          // Sec.5
    if (c.of_interest) {
      delay(node_id*60 + rand()%40);                // Sec.6 backoff
      lora_send(pack(node_id, seq++, T_onset, w.peak, c));
    }
    delay(REFRACTORY_700ms);                        // ignore echoes
    clock_set(80_MHz); state = LISTEN; event_flag = false;
  }
}
```

---

## 9. Base station (outline — separate doc later)

Runs on a Raspberry Pi + one Ra-01 gateway.

1. **Ingest**: receive LoRa reports, dedupe `(node_id, seq)`.
2. **Correlate**: group reports whose `onset_time_us` fall within ~450 ms
   (max propagation across the property) into one *event*.
3. **Solve**: TDoA multilateration using the **GPS-averaged node positions each
   node self-reports** + onset times. Least-squares / Levenberg–Marquardt seeded
   by a coarse grid search; output lat/lon + residual. Need ≥3 nodes; 4+ rejects
   the mirror ambiguity. Accuracy bounded by node position error: ~**2–5 m** with
   GPS averaging (or sub-meter if you also tape-survey and hardcode positions).
4. **Serve**: Leaflet + OpenStreetMap web page (WebSocket live) showing nodes,
   the computed source, and an error circle. Log every event to SQLite.

---

## 10. Tuning knobs & open items

- **Fs**: 16 kHz is plenty for onset timing + basic classify; 8 kHz saves power,
  32 kHz sharpens timing. Trade against CPU/power.
- **K (threshold)** and **noise-floor time constant**: field-tune to your
  ambient; too low = constant wakes (burns the lazy savings), too high = misses.
- **Refractory time**: long enough to swallow echoes off house/trees, short
  enough not to miss a real second event.
- **Node survey**: measure each node's lat/lon once (tape-measure to a local
  grid, or average a GPS fix for minutes). Store in the base's table. This is
  what turns ~3 m GPS error into cm-level position → sub-meter fixes.
- **Node layout**: stagger across the 52 m width; never colinear.
- **Power**: verify average current on the bench, then size panel/battery for
  worst-case cloudy days (target ≥2–3 days autonomy). GPS is the floor —
  consider GPS duty-cycling + a TCXO holdover only if you must go lower.
- **LoRa duty cycle / region**: mind 433 MHz regional limits; reports are tiny
  so this is easy to stay under.

---

---

## Appendix A — Low-Power Variant (GPS duty-cycle + DS3231 holdover)

**Optional.** The default design runs GPS continuously (~30 mA = half the node
budget). This variant nearly halves node draw for nodes that need it. **Skip it
for solar nodes** (already power-positive); use it only for:
- battery-only nodes (no solar) — halving draw ~doubles runtime,
- heavily shaded sites where the 5 W panel can't keep up,
- shrinking to a smaller panel/battery to cut cost/size.

### Idea
A bare ESP32 crystal drifts too fast — and drifts with *outdoor temperature* —
so you can't coast without GPS. Add a **DS3231 (TCXO RTC, ±2 ppm, temperature-
stable)**. Then you can turn the GPS OFF and hold time on the TCXO between brief
re-syncs.

### Added hardware
- **DS3231 + AT24C32 module** (~$2, I²C). TCXO holdover + EEPROM for node
  config/ID/optional surveyed position.
- **High-side P-MOSFET** (or the GPS module's standby pin) to gate GPS power.

### Extra pins
Needs 3–4 more GPIO (I²C SDA/SCL, optional 32 kHz reference in, GPS-enable MOSFET
gate). **Not allocated here** — the full node already uses nearly the whole header,
so anyone building this variant assigns them in `node_config.h`, where the collision
checks live, and reads the boot pin map back.

### How it works
1. **Sync phase (GPS on):** get position fix (average once, store in EEPROM) +
   discipline the ESP32 high-res timer against PPS; measure the TCXO's exact
   offset. Establish `timer_ticks ↔ GPS_time` and the ppm correction.
2. **Holdover phase (GPS off):** run the ESP32 fast timer, corrected by the
   DS3231 32.768 kHz TCXO reference (temperature-stable). Onset timestamps use
   this held timebase. Coast for the re-sync interval.
3. **Re-sync:** every ~2–3 min pulse GPS on (~2 s hot-start), re-lock PPS,
   re-measure the timer offset, GPS off again.

### Budget & timing
- GPS: ~30 mA continuous → **~1 mA average** (~1.6 % duty) + ~0.2 mA DS3231.
- **Node ~58 mA → ~28 mA** (roughly halved).
- Timing: ±2 ppm over a 3-min holdover → worst-case ~0.7 ms cross-node relative
  drift → **~0.25 m ranging error** — inside the 2–5 m target. Tighten the
  re-sync interval if you want margin.

### Cost / risk
Real firmware complexity: holdover discipline math, GPS on/off sequencing, and
you MUST field-validate cross-node timing holds (compare a known common event).
Not worth it unless power-starved. Keep the DS3231 as a stocked option.

---

*Status: design. Next: exact BOM w/ links, then implement node firmware
(I²S + PPS timestamp first, then classify, then LoRa), then the base solver+map.*
