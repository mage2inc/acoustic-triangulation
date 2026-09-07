# HANDOFF — Acoustic Triangulation (portable/uConsole continuation)

Self-contained project. Read `PROJECT_MEMORY.md` first (full context), then
`POC.md` (plan) and `firmware/README.md` (build).

## Where we are (hardware bring-up, verified on a MacBook)
- Board CONFIRMED: ESP32-S3, 4MB flash / 2MB PSRAM (S3FH4R2). `/dev/cu.usbmodem2101` on the Mac.
- Toolchain: PlatformIO + **pioarduino platform** (core 3.x) — set in `firmware/platformio.ini`.
  Also fixed: **4MB flash override** (board_upload.flash_size=4MB, partitions=default.csv).
- Pin map lives in ONE place: `firmware/src/node_config.h`. Don't copy it into notes —
  every sketch prints the map it was compiled with (`== pins compiled in ==`) in its
  first serial lines. Wire from that print. (This line used to carry its own copy of
  the map, naming a PPS pin the firmware had since handed to the LoRa RF-switch.
  That is the bug this note replaced.)
- Stage 1 (mic): PASS — RMS/peak jump with sound.
- Stage 2 (GPS): GPS UART WIRED OK (NMEA chars climbing). sats=0 INDOORS (no fix yet).
  TRAP: that reading was taken while the docs named one PPS pin and the firmware
  watched another, so "no PPS" here proves nothing about the sky. Re-take it against
  the boot pin map before drawing any conclusion from it.

## NEXT STEP (needs sky view — that's why we're going portable)
1. Plug the ESP32 into the uConsole. `pip install platformio` if needed.
2. `cd firmware && pio run -e stage2 -t upload -t monitor`  (port may be /dev/ttyACM0)
3. Check the boot pin map against the board FIRST — if the PPS line is on a pin the
   radio drives, nothing below will ever work and it will look like a cold GPS.
4. Take it OUTSIDE / by a window. Wait for `sats` to climb, get a fix, then PPS starts:
   confirm **`interval` locks to ~1000000 us**. That proves the PPS wire + the
   synchronized clock. If instead you get `PPS pin GPIOn: 0 edges in 30 s` while the
   NMEA char count climbs, the GPS is fine and the PPS wire is not — stop and fix
   the wire; more sky view will not help.
5. Then `pio run -e stage3 -t upload -t monitor`, clap -> prints a GPS-referenced timestamp = **M1 DONE**.
6. M2 (make-or-break): 2 nodes on stage4 + a base on stage5, clap between them,
   verify base prints `dt ~ Δdistance/343`.

## Notes for the uConsole
- Serial port is likely /dev/ttyACM0 (not cu.usbmodem). Add `--upload-port /dev/ttyACM0` or set `upload_port`/`monitor_port` in platformio.ini.
- First `pio run` downloads the toolchain (~few min).
- Base solver already validated (base/test_solver.py: 0.04m clean, ~2.8m realistic).
