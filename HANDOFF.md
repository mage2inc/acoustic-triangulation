# HANDOFF — Acoustic Triangulation (portable/uConsole continuation)

Self-contained project. Read `PROJECT_MEMORY.md` first (full context), then
`POC.md` (plan) and `firmware/README.md` (build).

## Where we are (hardware bring-up, verified on a MacBook)
- Board CONFIRMED: ESP32-S3, 4MB flash / 2MB PSRAM (S3FH4R2). `/dev/cu.usbmodem2101` on the Mac.
- Toolchain: PlatformIO + **pioarduino platform** (core 3.x) — set in `firmware/platformio.ini`.
  Also fixed: **4MB flash override** (board_upload.flash_size=4MB, partitions=default.csv).
- Pin map moved to the GP1..13 breadboard header (this board's GP14+/GP17/18 are solder pads).
  See `firmware/src/node_config.h`: I2S 4/5/6, GPS TX->GP1 / PPS->GP8, LoRa 12/13/11/10/9/RST=7.
- Stage 1 (mic): PASS — RMS/peak jump with sound.
- Stage 2 (GPS): GPS UART WIRED OK (NMEA chars climbing). sats=0 INDOORS (no fix yet).

## NEXT STEP (needs sky view — that's why we're going portable)
1. Plug the ESP32 into the uConsole. `pip install platformio` if needed.
2. `cd firmware && pio run -e stage2 -t upload -t monitor`  (port may be /dev/ttyACM0)
3. Take it OUTSIDE / by a window. Wait for `sats` to climb, get a fix, then PPS starts:
   confirm **`interval` locks to ~1000000 us**. That proves PPS/GP8 + the synchronized clock.
4. Then `pio run -e stage3 -t upload -t monitor`, clap -> prints a GPS-referenced timestamp = **M1 DONE**.
5. M2 (make-or-break): 2 nodes on stage4 + a base on stage5, clap between them,
   verify base prints `dt ~ Δdistance/343`.

## Notes for the uConsole
- Serial port is likely /dev/ttyACM0 (not cu.usbmodem). Add `--upload-port /dev/ttyACM0` or set `upload_port`/`monitor_port` in platformio.ini.
- First `pio run` downloads the toolchain (~few min).
- Base solver already validated (base/test_solver.py: 0.04m clean, ~2.8m realistic).
