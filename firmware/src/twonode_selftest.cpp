// twonode_selftest — the make-or-break (M2) with only TWO radios.
//
// Flash BOTH boards with this (one as NODE_ID 1, the other as 2). Each board is
// node AND base: it timestamps the clap, LoRa-broadcasts its onset time, receives
// the other board's, and prints Δt + the implied Δdistance. Both boards should
// report the same |Δt| (opposite sign), and it should track the geometry:
//     Δdist ≈ (my distance to clap) − (their distance to clap).
//
//   Board A:  pio run -e twonode   -t upload -t monitor     (NODE_ID=1)
//   Board B:  pio run -e twonode_b -t upload -t monitor     (NODE_ID=2)
//
// TEST: place the two nodes a known distance apart, get a GPS fix on both, then
// clap much closer to one than the other and check the Δdist ≈ the real difference.

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include "acoustic_core.h"
#include "report_packet.h"

#include "lora_radio.h"
volatile bool rxFlag = false;
void IRAM_ATTR onRx() { rxFlag = true; }

// self-location
static double  lat_acc = 0, lon_acc = 0;
static uint32_t loc_n = 0;
static bool     pos_locked = false;
static int32_t  node_lat = 0, node_lon = 0;
static uint16_t seq = 0;

// most-recent onsets for pairing
static uint64_t my_onset = 0;    static uint32_t my_onset_ms = 0;
static uint64_t other_onset = 0; static uint8_t other_id = 0; static uint32_t other_ms = 0;
static uint16_t last_other_seq = 0xFFFF; static uint8_t last_other_id = 0;   // dedup repeated reports

// scheduled (non-blocking) TX so we stay in RX except during the brief send
static bool     tx_pending = false;
static uint32_t tx_at = 0;
static Report   tx_rpt;

// ---- onboard WS2812 status LED (GP21, no header pin) ----------------------
//  solid RED     radio init failed (dead — check wiring)
//  blink RED     no GPS fix yet (sats = 0)
//  blink YELLOW  acquiring GPS / averaging position (has sats, not locked)
//  solid GREEN   position locked + clock ready  -> READY, clap now
//  BLUE flash    local clap/onset detected
//  CYAN flash    received the other node's report over LoRa
//  MAGENTA flash PAIR — Δt computed between the two nodes
#ifndef PIN_RGB
#define PIN_RGB 48                  // onboard RGB confirmed on GPIO48 (this board)
#endif
static bool     g_radio_ok = false;
static uint32_t led_flash_until = 0;
static uint8_t  fr, fg, fb;
// This board's LED is RGB-order, but the core drives WS2812 as GRB -> swap R/G.
static inline void led_show(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(PIN_RGB, g, r, b); }
static inline void led_flash(uint8_t r, uint8_t g, uint8_t b, uint16_t ms) {
  fr = r; fg = g; fb = b; led_flash_until = millis() + ms;
}
static void led_service(bool pos_locked, bool clk_ok, uint32_t sats) {
  uint32_t now = millis();
  if ((int32_t)(led_flash_until - now) > 0) { led_show(fr, fg, fb); return; }  // active flash
  bool on = (now / 400) & 1;                                   // 400 ms blink phase
  if (!g_radio_ok)                 led_show(30, 0, 0);         // solid RED
  else if (pos_locked && clk_ok)   led_show(0, 30, 0);         // solid GREEN — ready
  else if (!pos_locked && sats == 0) led_show(on ? 30 : 0, 0, 0);          // blink RED
  else                             led_show(on ? 28 : 0, on ? 18 : 0, 0);  // blink YELLOW
}

static int64_t wrap_us(int64_t dt) {
  const int64_t D = 86400000000LL;      // µs per day
  if (dt >  D / 2) dt -= D;
  if (dt < -D / 2) dt += D;
  return dt;
}

static void try_pair() {
  if (my_onset_ms == 0 || other_ms == 0) return;
  if (millis() - my_onset_ms > 1500 || millis() - other_ms > 1500) return;  // both fresh
  int64_t dt = wrap_us((int64_t)my_onset - (int64_t)other_onset);
  if (dt < -700000 || dt > 700000) return;                                  // same event
  double dd = (double)dt * 1e-6 * 343.0;
  Serial.printf(">>> PAIR me(%d)-node%d  dt=%lld us  Δdist=%+.2f m  "
                "(want ≈ my_dist − their_dist to the clap)\n",
                NODE_ID, other_id, (long long)dt, dd);
  led_flash(30, 0, 30, 700);                    // MAGENTA — pair success
  my_onset_ms = 0; other_ms = 0;                // CONSUME: each onset pairs once (no dup/cross-event reuse)
}

#ifdef BENCH_SHARED
#include "esp_timer.h"
#define BENCH_PPS_OUT 43                        // node1 drives 1Hz here -> wire to BOTH nodes' GP8
static void bench_pps_cb(void*) { static bool s = false; s = !s; digitalWrite(BENCH_PPS_OUT, s ? HIGH : LOW); }
static void bench_shared_clock() {              // discipline to the shared PPS wire; utc fixed=0
  static uint32_t last = 0; uint32_t c1, c2; uint64_t pus;
  do { c1 = g_pps_cnt; pus = g_pps_us; c2 = g_pps_cnt; } while (c1 != c2);
  if (c1 > 0 && c1 != last) { last = c1; g_clk_pps_us = pus; g_clk_utc_sod = 0; g_clk_valid = true; }
}
#endif

void setup() {
  Serial.begin(115200);
  delay(400);
  led_show(0, 0, 20);                           // dim BLUE = booting
  Serial.printf("\n== 2-node self-test (node %d) ==\n", NODE_ID);
  core_begin();
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int st = lora_begin();
  if (st != RADIOLIB_ERR_NONE) {
    Serial.printf("LoRa init FAIL %d\n", st);
    while (1) { led_show(30, 0, 0); delay(1000); }   // solid RED = radio dead
  }
  g_radio_ok = true;
  radio.setPacketReceivedAction(onRx);
  radio.startReceive();
#ifdef BENCH_SYNC
  g_clk_valid = true; pos_locked = true;             // fake the GPS lock (no sky needed)
  node_lat = 301132776; node_lon = -975791107;       // last real field fix
  Serial.println("BENCH_SYNC: faking GPS lock. onset=esp_timer (boards NOT time-synced),");
  Serial.println("  so this validates the LoRa EXCHANGE only: want 'rx node=<other>' + valid");
  Serial.println("  onset (NOT node=0/garbage). dt will be meaningless (no shared clock).");
#endif
#ifdef BENCH_SHARED
  pos_locked = true; node_lat = 301132776; node_lon = -975791107;
  pinMode(BENCH_PPS_OUT, OUTPUT); digitalWrite(BENCH_PPS_OUT, LOW);
  if (NODE_ID == 1) {                                // node1 is the shared-PPS source
    const esp_timer_create_args_t a = { .callback = bench_pps_cb, .arg = NULL,
      .dispatch_method = ESP_TIMER_TASK, .name = "bpps", .skip_unhandled_events = false };
    esp_timer_handle_t h; esp_timer_create(&a, &h); esp_timer_start_periodic(h, 500000);
    Serial.println("BENCH_SHARED: node1 driving 1Hz on GP43 -> wire GP43 to BOTH nodes' GP8.");
  }
  Serial.println("BENCH_SHARED: shared-PPS common timebase -> dt should TRACK clap position.");
#endif
  Serial.println("ready — get a GPS fix on both (LED green), then clap between them.");
}

void loop() {
#if defined(BENCH_SHARED)
  bench_shared_clock();                          // discipline to the shared fake-PPS wire
#elif !defined(BENCH_SYNC)
  core_gps_service();

  if (!pos_locked && g_gps.location.isUpdated() && g_gps.location.isValid()) {
    lat_acc += g_gps.location.lat(); lon_acc += g_gps.location.lng(); loc_n++;
    if (loc_n >= 60) {
      node_lat = (int32_t)llround(lat_acc / loc_n * 1e7);
      node_lon = (int32_t)llround(lon_acc / loc_n * 1e7);
      pos_locked = true;
      Serial.printf("pos locked %.7f,%.7f\n", lat_acc / loc_n, lon_acc / loc_n);
    }
  }
#endif

#ifdef BENCH_AUTO
  // autonomous LoRa-exchange stress: synthesize an onset every ~1s (no mic needed)
  static uint32_t last_fake = 1000;
  if (millis() - last_fake > 1000) {
    last_fake = millis();
    my_onset = (uint64_t)esp_timer_get_time();
    my_onset_ms = millis();
    tx_rpt.node_id = NODE_ID; tx_rpt.seq = seq++; tx_rpt.onset_gps_us = my_onset;
    tx_rpt.lat_1e7 = node_lat; tx_rpt.lon_1e7 = node_lon; tx_rpt.peak = 9999;
    tx_pending = true; tx_at = millis() + NODE_ID * 300;
    Serial.printf("onset node=%d peak=9999 onset_us=%llu (auto seq=%u)\n",
                  NODE_ID, (unsigned long long)my_onset, (unsigned)tx_rpt.seq);
    try_pair();
  }
#endif

  // own onset -> record + schedule a staggered TX (stay in RX meanwhile)
  uint32_t onset; int32_t peak;
  if (core_detect_onset(&onset, &peak)) {
    led_flash(0, 0, 45, 150);                    // BLUE — mic triggered (works pre-GPS)
    if (core_clock_ready()) {                    // only timestamp + TX once GPS clock is up
#ifdef BENCH_SYNC
      my_onset    = (uint64_t)esp_timer_get_time();   // per-board local time (unsynced) — exchange test
#else
      my_onset    = core_local_to_gps_us(core_sample_to_local_us(onset));
#endif
      my_onset_ms = millis();
      tx_rpt.node_id = NODE_ID; tx_rpt.seq = seq++; tx_rpt.onset_gps_us = my_onset;
      tx_rpt.lat_1e7 = node_lat; tx_rpt.lon_1e7 = node_lon; tx_rpt.peak = peak;
      tx_pending = true; tx_at = millis() + NODE_ID * 300;    // stagger > airtime (~150ms) so TXs don't overlap
      Serial.printf("onset node=%d peak=%d onset_us=%llu (tx in %dms)\n",
                    NODE_ID, peak, (unsigned long long)my_onset, NODE_ID * 300);
      try_pair();
    }
  }

  // receive the other board's report FIRST — so a real packet is handled before
  // the blocking TX below (whose post-TX rxFlag clear would otherwise drop it).
  if (rxFlag) {
    rxFlag = false;
    Report r;
    int st = radio.readData((uint8_t*)&r, sizeof(Report));
    radio.startReceive();
    if (st == RADIOLIB_ERR_NONE && r.node_id != NODE_ID &&
        !(r.node_id == last_other_id && r.seq == last_other_seq)) {   // skip duplicate repeats
      last_other_id = r.node_id; last_other_seq = r.seq;
      other_onset = r.onset_gps_us; other_id = r.node_id; other_ms = millis();
      Serial.printf("rx node=%d onset_us=%llu rssi=%.0f\n",
                    r.node_id, (unsigned long long)r.onset_gps_us, radio.getRSSI());
      led_flash(0, 30, 25, 120);                 // CYAN — got the other node's report
      try_pair();
    }
  }

  // fire the scheduled TX, then immediately return to RX
  if (tx_pending && (int32_t)(millis() - tx_at) >= 0) {
    tx_pending = false;
    radio.transmit((uint8_t*)&tx_rpt, sizeof(tx_rpt));
    radio.startReceive();
    rxFlag = false;                     // swallow only our own TxDone edge (real RX handled above)
    try_pair();
  }

  uint32_t sats = g_gps.satellites.isValid() ? g_gps.satellites.value() : 0;
  led_service(pos_locked, core_clock_ready(), sats);
}
