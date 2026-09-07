# Node Wiring

## Power (field node: solar + 18650 + CN3791, LDO-direct — no buck-boost)

Use the ESP32-S3's own input pad (accepts 3.3–6 V) + onboard LDO. No separate
regulator.

```
 6V panel ─► CN3791(IN) ──MPPT──► CN3791(BAT) ═╦═ 18650 (+protection)
                                               ║
                                        [Schottky diode]
                                               ║
                                     ESP32-S3 "5V" pad ─► onboard LDO ─► 3V3 out
                                               │                          │
                                               └── USB-C (coexists) ──┐    ├─► RYLR689 (+bulk cap)
                                                                      │    ├─► INMP441
                                                                      │    └─► ATGM336H
```

The CN3791 **BAT** terminals ARE the battery rail — cell + load both tap there.

| From | To |
|---|---|
| Solar + | CN3791 IN+ |
| Solar − | CN3791 IN− |
| CN3791 BAT+ | 18650 + (via protection) |
| CN3791 BAT− | 18650 − |
| CN3791 BAT+ → **Schottky diode** → | ESP32 **5V** pad |
| CN3791 BAT− | ESP32 **GND** |
| ESP32 **3V3 out** | RYLR689 3.3V, INMP441 VDD, ATGM336H VCC |
| GND rail | RYLR689 GND, INMP441 GND **+ L/R**, ATGM336H GND |
| **220–470 µF cap** | across 3V3–GND near the RYLR689 (TX spike) |

**Gotchas**
1. **Series Schottky** (BAT+ → 5V pad) lets USB-C + battery coexist — flash over
   USB anytime, no back-feed into the cell.
2. **Bulk cap on 3V3 near RYLR689** for the ~120 mA LoRa-TX transient.
3. Match CN3791 MPPT set-point to the 6 V panel (MPP ~5 V); many ship for 9/12 V.
4. INMP441 `L/R` → GND (left channel; silent if floating).
5. Protected cell or a 1S protection board between cell and BAT; set low-voltage
   cutoff ~3.2–3.3 V (LDO sags below that — fine, ~90 % of cell used).
6. *(Optional)* add a buck-boost back only if you want a rock-stable 3.3 V to the
   very bottom of the cell.

Office node: no solar/charger/battery — powered from the Pi's USB-C (5 V → onboard
LDO → 3V3). Everything else identical.

## Signals — RYLR689 (LLCC68) node

Radio changed from Ra-01 / SX1278 → **RYLR689 / LLCC68**. It's a bare SPI module
(not AT-command UART), so RadioLib drives it, but it needs 3 pins the SX1278
didn't: **BUSY** + the two antenna **RF-switch** lines (RFSW_V1/V2). It also runs
on a **32 MHz crystal, not a TCXO** → firmware passes `TCXO = 0.0` (a nonzero
value makes `begin()` fail — this was the #1 first-try trap).

**The GPIO numbers are deliberately not in this file.** They live in
`firmware/src/node_config.h`, and every sketch prints the map it was *actually
compiled with* in its first lines of serial output:

```
== pins compiled in ==  node=1  radio=LLCC68/RYLR689 (SX126x)  915.0 MHz
   I2S_BCLK    GPIO..
   ...                 (every signal, then a CONFLICT line if two share a pin)
```

Flash, read that, wire to that. A pin number typed into a document is a claim
about what the build looked like when somebody typed it. This file used to name a
PPS pin that the firmware had since handed to RFSW_V2 — a pin RadioLib **drives**.
Wired that way, the GPS PPS fights an ESP output: zero edges, `core_clock_ready()`
never true, the node never transmits, and the console blames the sky. The build
now refuses to compile a PPS/RF-switch collision, and the firmware now says
`PPS pin GPIOn: 0 edges in 30 s` instead of "no PPS yet".

RYLR689 module pin → signal: `1,13,18=GND  2=VDD(3V3)  3=NRESET  4=MISO  5=MOSI
6=SCK  7=NSS  9=RFSW_V1  8=RFSW_V2  14=BUSY  15=DIO1  10=ANT→coil`. Leave
DIO2/DIO3 (16/17) unconnected. Each signal's ESP pin comes from the boot print.

### Two-phase bring-up (breadboard)
**Phase 1 — radio-only link test** (`lora_tx_llcc` / `lora_rx_llcc`): mic + GPS
NOT connected, so the whole header is free. Wire the radio per the boot print;
both boards identical. Expect RX lines with RSSI ≈ −30…−60 dBm a few metres apart.

**Phase 2 — full node / 2-node sync** (`twonode_llcc`): add mic + GPS. That is
14 wired signals, and they all fit with no build-flag override — the USB-CDC
console (`ARDUINO_USB_CDC_ON_BOOT=1`) frees UART0, so both of its pins are usable
GPIO and one is left spare. Reconcile only one thing:
- **INMP441 `L/R` goes to the GND rail**, not to a GPIO — it only needs to be low.

If some signal looks like it needs a pin that is already taken, edit
`node_config.h` and reflash. The boot print and the build's static asserts decide
what is true; this paragraph does not.
