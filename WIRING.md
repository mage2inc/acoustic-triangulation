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

## Signals — RYLR689 (LLCC68) node  [see also node_config.h]

Radio changed from Ra-01 / SX1278 → **RYLR689 / LLCC68**. It's a bare SPI module
(not AT-command UART), so RadioLib drives it, but it needs 3 pins the SX1278
didn't: **BUSY** + the two antenna **RF-switch** lines (RFSW_V1/V2). It also runs
on a **32 MHz crystal, not a TCXO** → firmware passes `TCXO = 0.0` (a nonzero
value makes `begin()` fail — this was the #1 first-try trap).

```
INMP441 I²S:  BCLK=GP4   WS=GP5   SD=GP6                 (L/R -> GND, left ch)
RYLR689 SPI:  SCK=GP12   MISO=GP13  MOSI=GP11  NSS=GP10
              RST=GP7    DIO1=GP9   BUSY=GP3
              RFSW_V1=GP2   RFSW_V2=GP8*             (*link test; see crunch)
ATGM336H:     GPS_TX->GP1 (ESP RX)   PPS=GP8              (ESP->GPS TX unused)
```

RYLR689 module pins → ESP: `1,13,18=GND  2=VDD(3V3)  3=NRESET→GP7  4=MISO→GP13
5=MOSI→GP11  6=SCK→GP12  7=NSS→GP10  9=RFSW_V1→GP2  8=RFSW_V2  14=BUSY→GP3
15=DIO1→GP9  10=ANT→coil`. Leave DIO2/DIO3 (16/17) unconnected.

### Two-phase bring-up (breadboard)
**Phase 1 — radio-only link test** (`lora_tx_llcc` / `lora_rx_llcc`): mic + GPS
NOT connected, so the whole GP1–13 header is free. Wire the RYLR689 as above with
**RFSW_V2 → GP8**. Both boards identical. Expect RX lines with RSSI ≈ −30…−60 dBm
a few metres apart.

**Phase 2 — full node / 2-node sync** (`twonode_llcc`): add mic + GPS. Now
mic(3) + GPS(2) + RYLR689(9) = 14 signals vs 13 header pins. Reconcile:
- **Move the INMP441 `L/R` wire from GP3 to the GND rail** (it just needs to be
  low). That frees GP3 for **BUSY**.
- **GP8 is now PPS**, so RFSW_V2 moves to **GP44 (the "RX" header pin)**. The
  USB-CDC console frees UART0, so RX=GP44 / TX=GP43 are usable GPIO — 13 + 2 = 15
  pins for 14 signals. Build with `-D PIN_LORA_RFSW2=44`; GP43 (TX) stays spare.
  No solder pad, no extra part, real BUSY — the same two-GPIO RF-switch topology
  the **PCB** uses, so the breadboard is electrically identical to the final board.

---

## Signals — XL1276-P01 (SX1276) node  [manufactured PCB v3 / node_config.h default]

**3 fewer control pins** vs RYLR689: no BUSY, no RFSW_V1/V2. The SX1276 integrates
the antenna switch. GP7 and GP8 are now free (DS3231 RTC, status LED, etc.).

```
INMP441 I²S:     BCLK=GP4   WS=GP5   SD=GP6            (L/R → GND, left ch)
XL1276-P01 SPI:  SCK=GP11   MISO=GP13  MOSI=GP12  NSS=GP10
                 RST=GP44   DIO0=GP9
ATGM336H:        GPS_TX→GP1 (ESP RX)   PPS=GP2
```

XL1276-P01 module pins → ESP (Ra-01S-compatible pinout, antenna at module top):

| Module pin | Signal | ESP GPIO |
|---|---|---|
| Right col R2 | VCC (3.3 V) | 3V3 rail |
| Right col R3 | NSS / CS | GP10 |
| Right col R4 | SCK | GP11 |
| Right col R5 | MOSI | GP12 |
| Right col R6 | MISO | GP13 |
| Right col R7 | RST | GP44 (RX pin) |
| Right col R8 | GND | GND rail |
| Left col L1 | ANT | wire antenna (bundled) |
| Left col L8 | DIO0 | GP9 |
| Left col L2 | GND | GND rail |
| L3–L7 | DIO5–DIO1 | NC |
| Right col R1 | NC | — |

> **Verify the physical pinout on your specific XL1276-P01 batch** before
> soldering the first node. Ra-01S-compatible modules are common, but some
> sellers rotate or mirror the pin numbering. Use a multimeter to confirm
> VCC and GND before applying power.

### Breadboard bring-up (XL1276-P01)

**Phase 1 — radio link test** (`lora_tx` / `lora_rx`): wire only NSS, SCK,
MOSI, MISO, RST, DIO0, VCC, GND. No mic, no GPS. Expect RSSI ≈ −30…−60 dBm
at close range.

**Phase 2 — full node** (`stage4`): add mic + GPS. Pin budget:

| Group | Signals | GPIOs used |
|---|---|---|
| I²S mic | BCLK, WS, SD | GP4, GP5, GP6 |
| SPI radio | NSS, SCK, MOSI, MISO | GP10, GP11, GP12, GP13 |
| Radio control | RST, DIO0 | GP44, GP9 |
| GPS | GPS_TX, PPS | GP1, GP2 |
| **Total** | **10 signals** | **GP43 + GP3 + GP7 + GP8 spare** |

With the XL1276-P01 you have **4 spare GPIOs** on the S3-Zero vs 0 with the
RYLR689. The defaults in `node_config.h` already target this pinout — no build
flags needed.
