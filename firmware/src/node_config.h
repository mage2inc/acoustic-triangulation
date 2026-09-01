#pragma once
#include <stdint.h>

// ---- Node identity (change per node: 1..5) ----
// Overridable per-board via a build flag (-D NODE_ID=2), e.g. the twonode_b env.
#ifndef NODE_ID
#define NODE_ID        1
#endif

// ---- Audio ----
#define SAMPLE_RATE    16000        // Hz (onset timing + basic classify)
// Onset must clear BOTH an adaptive 8x-noise-floor gate AND this absolute floor,
// so a very quiet room can't drop the floor low enough to trigger on nothing.
// Units = |sample| after >>8 (24-bit). A close clap ~ several million; ambient
// well under this. Lower it if distant real events are being missed.
#ifndef ONSET_ABS_MIN
#define ONSET_ABS_MIN  120000
#endif

// ============================================================
//  Pin map — ESP32-S3-Zero  (avoids strapping / USB / LED pins)
//  See NODE_FIRMWARE_DESIGN.md
// ============================================================

// I2S mic (INMP441)   —  L/R pin tied to GND (left channel)
#define PIN_I2S_BCLK   4
#define PIN_I2S_WS     5
#define PIN_I2S_SD     6

// SPI to the LoRa (shared by all radio modules).  Pin ORDER matches the RYLR689
// carrier-PCB pad layout: MISO/MOSI/SCK/NSS come out of the ESP right-hand header
// column in the same left-to-right order as the module pads, so the SPI bus routes
// with ZERO jumpers.  (MOSI<->SCK swapped vs the old breadboard map for this.)
#define PIN_LORA_SCK   11           // was 12
#define PIN_LORA_MISO  13
#define PIN_LORA_MOSI  12           // was 11
#define PIN_LORA_NSS   10
#define PIN_LORA_RST   44           // was 7 (NRST -> GP44 so GP7 can carry BUSY as copper)
#define PIN_LORA_DIO0  9            // SX127x-only (SX1276 fleet); unused on SX126x/PCB

// GPS (ATGM336H)  — we only READ it (GPS TX -> ESP, plus PPS)
#define PIN_GPS_RX     1            // ESP32 RX  <-  GPS TX (NMEA in)
#define PIN_GPS_TX     43           // unused spare (GPS RX pin left open)
#define PIN_PPS        2            // was 8  (GP8 freed for the LoRa RF-switch)

// ---- LoRa MODULE select (pick ONE; every board in a test must match) ----
//   XL1276-P01 -> SX1276  (SX127x, DIO0)         [default, 915, the fleet part]
//   RYLR689    -> LLCC68  (SX126x, DIO1 + BUSY)  [915, for the A/B comparison]
//   433 test   -> SX1278  (SX127x, DIO0)         [433 only]
// Override per build with -D LORA_MOD_LLCC68 etc, or just edit these three lines:
#if !defined(LORA_MOD_SX1276) && !defined(LORA_MOD_LLCC68) && !defined(LORA_MOD_SX1278_433)
  #define LORA_MOD_SX1276           // default
#endif

#if defined(LORA_MOD_LLCC68)
  #define LORA_FAMILY_SX126X        // uses DIO1 + BUSY; radio class in lora_radio.h
  #define LORA_FREQ   915.0f
  #define LORA_TCXO_V 0.0f          // RYLR689 has a 32 MHz CRYSTAL, not a TCXO -> 0.0
  #define LORA_RFSW_MANUAL          // RYLR689 breaks out RFSW_V1/V2: host must drive them
#elif defined(LORA_MOD_SX1278_433)
  #define LORA_CHIP  SX1278
  #define LORA_FREQ  433.0f
#else
  #define LORA_CHIP  SX1276
  #define LORA_FREQ  915.0f
#endif

// ---- SX126x-only pins (LLCC68 / RYLR689 — the carrier PCB) -----------------
// Repinned for the carrier PCB so the module's NEAR row (the SPI + RF-switch pads
// that face the ESP) all land on the ESP RIGHT header column -> clean 2-layer
// copper, zero jumpers. Only the two signals on the module's FAR row (BUSY, DIO1)
// need a short flying wire, because they sit on the antenna edge, physically
// opposite the ESP. RF-switch MUST be driven or the radio can't TX or RX.
//   RFSW_V1 -> GP9   RFSW_V2 -> GP8   (module pins 9/8, ESP right column; each ESP
//   NRST    -> GP7   (module left-end pad, clean)
//   FAR-row signals routed as BOTTOM COPPER (LoRa pads are through-holes), each
//   entering the under-module space from OPPOSITE sides so they never cross ->
//   ZERO jumper wires. Pins chosen for that: DIO1 from the left, BUSY from the right.
//   DIO1 -> GP3  (left col, above the 3V3 rail -> under module from the LEFT)
//   BUSY -> GP7  (top of left col        -> around the right -> from the RIGHT)
//   NRST -> GP44 (moved here; routes as top copper to the near-row pad)
#define PIN_LORA_DIO1   3
#ifndef PIN_LORA_BUSY
#define PIN_LORA_BUSY   7           // was 44
#endif
#define PIN_LORA_RFSW1  9           // RFSW_V1 (module pin 9) -> ESP GP9 (routes to outer RFV1 pad)
#ifndef PIN_LORA_RFSW2
#define PIN_LORA_RFSW2  8           // RFSW_V2 (module pin 8) -> ESP GP8 (clean, inner RFV2 pad)
#endif
#ifndef LORA_TCXO_V
#define LORA_TCXO_V     0.0f        // (only the SX126x path reads this)
#endif

// ---- FULL NODE (mic + GPS + RYLR689) = 14 signal pins ----------------------
// USB-CDC console (ARDUINO_USB_CDC_ON_BOOT=1) frees UART0, so GP44(RX) is a usable
// GPIO (here = DIO1) and GP43(TX) is spare. Pin budget, per ESP header column:
//   RIGHT col GP8..13 (6) = RFSW_V2, RFSW_V1, NSS, SCK, MOSI, MISO  (LoRa near row)
//   LEFT  col GP1..7,44   = GPS TX(1), PPS(2), DIO1(3), I2S(4/5/6), NRST(7), BUSY(44)
// 14 signals on 14 pins; GP43 spare. Matches pcb/gen_pcb.py exactly.

// ---- LoRa radio params (both ends must match) ----
#define LORA_BW        125.0f       // kHz
#define LORA_SF        9            // spreading factor
#define LORA_CR        7            // coding rate 4/7
#define LORA_SYNCWORD  0x12
#define LORA_POWER     17           // dBm (SX1278 PA_BOOST, max 20)
#define LORA_PREAMBLE  8
