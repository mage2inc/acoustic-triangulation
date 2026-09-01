# Node firmware

ESP32-S3 node firmware for the acoustic triangulation array, built in testable
stages (see `../POC.md` for the milestone plan). Arduino framework via
**PlatformIO**.

## Toolchain
- Install PlatformIO (VS Code extension or `pip install platformio`).
- Board target: `esp32-s3-devkitc-1` (works for the DevKitC-1 *and* the
  ESP32-S3-Zero — same chip). Serial is native USB (CDC).

## Build & flash one stage
```
pio run -e stage1 -t upload -t monitor      # I2S mic level meter
pio run -e stage2 -t upload -t monitor      # GPS + PPS timestamp
```
(Each stage is one file selected by `build_src_filter` in `platformio.ini`.)

## Stages
| Stage | File | Proves | Pass criteria |
|---|---|---|---|
| 1 | `stage1_i2s_mic.cpp` | mic captures audio | tap/clap moves the RMS bar |
| 2 | `stage2_gps_pps.cpp` | PPS disciplines a µs clock | `interval` ≈ **1000000 µs** after fix |
| 3 | *(next)* | onset → GPS-time timestamp | clap prints a precise UTC-referenced µs |
| 4 | *(next)* | LoRa report | base prints the packet |
| 5 | *(next)* | **2-node PPS sync (M2)** | Δt ≈ Δdistance ÷ 343 m/s |
| 6 | *(Pi)* | multilaterate + Leaflet map | dot lands within a few m |

## Pin map
All pins in `src/node_config.h`. Set `NODE_ID` per node (1..5).

## Notes
- **Stage 2 needs sky view** — first GPS fix can take minutes; PPS typically
  starts after the first fix.
- If Stage 1 reads flat/zero: check `L/R`→GND and the SD/BCLK/WS wiring; the
  INMP441 drives the LEFT slot.
- Libs (`RadioLib`, `TinyGPSPlus`) auto-install on first build.
