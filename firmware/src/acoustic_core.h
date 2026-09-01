// acoustic_core.h — corrected shared node core (timing-critical path)
//
// Fixes the review findings so cross-node timestamps are consistent to ~µs:
//  * I2S DMA-callback-anchored ring buffer  -> onset time is tied to the DMA
//    capture instant, NOT the loop read (C1). Constant DMA latency cancels.
//  * Continuous ring + backward-walk to a fixed fraction of peak (C2, M5) ->
//    onset localized across buffer boundaries, amplitude-independent.
//  * PPS clock paired on the NMEA time update, snapshot atomically, gated on a
//    healthy 1 Hz interval, invalidated when stale (C3, M4, M6).
//
// One .cpp includes this per PlatformIO env, so the static defs are fine.

#pragma once
#include <Arduino.h>
#include <driver/i2s_std.h>
#include <TinyGPSPlus.h>
#include <math.h>
#include "node_config.h"

// ======================= I2S ring buffer + time anchor =======================
#define RING_BITS 13
#define RING_SIZE (1u << RING_BITS)     // 8192 samples ≈ 0.5 s @ 16 kHz
#define RING_MASK (RING_SIZE - 1)

static int32_t           g_ring[RING_SIZE];
static volatile uint32_t g_head        = 0;   // total samples written (monotonic)
static volatile uint64_t g_anchor_us   = 0;   // esp_timer at last DMA-buffer completion
static volatile uint32_t g_anchor_head = 0;   // g_head at that latch
static volatile uint32_t g_anchor_seq  = 0;   // seqlock (odd = being written)
static i2s_chan_handle_t g_rx          = NULL;

// Capture task — pulls samples with i2s_channel_read() (the proven path; the
// on_recv ev->data copy picked up DMA-descriptor/address garbage as "samples").
// After each read, publish {time, head} under a seqlock. The read returns when
// the chunk has been captured, so esp_timer_get_time() here is the capture instant
// (last sample) + a ~constant driver latency that cancels in cross-node Δt.
static void i2s_capture_task(void*) {
  static int32_t buf[128];                      // 8 ms chunks -> tight time anchor
  size_t nbytes;
  for (;;) {
    if (i2s_channel_read(g_rx, buf, sizeof(buf), &nbytes, portMAX_DELAY) != ESP_OK) continue;
    uint32_t n = nbytes / sizeof(int32_t);
    uint32_t head = g_head;
    for (uint32_t i = 0; i < n; i++)
      g_ring[(head + i) & RING_MASK] = buf[i];
    __sync_synchronize();                        // publish ring writes before head/anchor
    g_anchor_seq  = g_anchor_seq + 1;           // -> odd (writing)
    g_anchor_us   = esp_timer_get_time();
    g_anchor_head = head + n;
    g_head        = head + n;
    __sync_synchronize();                        // anchor+head visible before seq goes even
    g_anchor_seq  = g_anchor_seq + 1;           // -> even (done)
  }
}

static void core_i2s_init() {
  i2s_chan_config_t cc = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
  cc.dma_desc_num  = 6;
  cc.dma_frame_num = 256;                       // ~16 ms per DMA buffer
  i2s_new_channel(&cc, NULL, &g_rx);
  i2s_std_config_t sc = {
    .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
    .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO),
    .gpio_cfg = { .mclk = I2S_GPIO_UNUSED, .bclk = (gpio_num_t)PIN_I2S_BCLK,
                  .ws = (gpio_num_t)PIN_I2S_WS, .dout = I2S_GPIO_UNUSED,
                  .din = (gpio_num_t)PIN_I2S_SD, .invert_flags = { false, false, false } },
  };
  sc.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;    // INMP441 L/R->GND = left
  ESP_ERROR_CHECK(i2s_channel_init_std_mode(g_rx, &sc));
  ESP_ERROR_CHECK(i2s_channel_enable(g_rx));
  // high priority, pinned to core 0 so capture never starves behind the app loop
  xTaskCreatePinnedToCore(i2s_capture_task, "i2scap", 4096, NULL, 20, NULL, 0);
}

// sample index (in g_head units) -> local esp_timer µs, via the DMA anchor
static uint64_t core_sample_to_local_us(uint32_t sample_idx) {
  uint64_t a_us; uint32_t a_head, s1, s2;
  do { s1 = g_anchor_seq; __sync_synchronize(); a_us = g_anchor_us; a_head = g_anchor_head;
       __sync_synchronize(); s2 = g_anchor_seq; }
  while ((s1 & 1u) || s1 != s2);                // retry if the writer was mid-update
  int32_t d = (int32_t)((uint32_t)sample_idx - (uint32_t)a_head);   // wrap-safe (74h counter)
  return (uint64_t)((int64_t)a_us + llround((double)d * (1000000.0 / SAMPLE_RATE)));
}

// ============================ GPS + PPS clock ================================
static TinyGPSPlus   g_gps;
static HardwareSerial g_gpsser(1);
static volatile uint64_t g_pps_us       = 0;
static volatile uint32_t g_pps_cnt      = 0;
static volatile uint32_t g_pps_interval = 0;

static IRAM_ATTR void core_pps_isr() {
  uint64_t now   = esp_timer_get_time();
  g_pps_interval = (uint32_t)(now - g_pps_us);
  g_pps_us       = now;
  g_pps_cnt      = g_pps_cnt + 1;
}

// clock anchor (loop-owned): a PPS edge time and the UTC second it marks
static uint64_t g_clk_pps_us    = 0;
static uint32_t g_clk_utc_sod   = 0;
static uint32_t g_clk_stamp_ms  = 0;
static bool     g_clk_valid     = false;
static uint32_t g_last_svc_ms   = 0;

static inline bool core_clock_ready() { return g_clk_valid; }

// Call every loop: feed NMEA, and (on a fresh NMEA second) pair it with the PPS
// edge that just preceded it — snapshot atomically, accept only a healthy PPS.
// A loop stall > ~0.8 s could let a PPS fire between a sentence's second and our
// parse of it (off-by-one). Guard: if we detect we were stalled, still consume
// the sentence (clear the flag) but SKIP pairing until the next clean cycle —
// so a bad anchor is never latched (worst case: clock briefly goes stale).
static void core_gps_service() {
  uint32_t nowms  = millis();
  bool stalled    = (g_last_svc_ms != 0) && (nowms - g_last_svc_ms > 400);
  g_last_svc_ms   = nowms;

  while (g_gpsser.available()) g_gps.encode(g_gpsser.read());

  if (g_gps.time.isValid() && g_gps.time.isUpdated()) {
    uint32_t sod = (uint32_t)g_gps.time.hour() * 3600u     // reading clears isUpdated
                 + (uint32_t)g_gps.time.minute() * 60u
                 + (uint32_t)g_gps.time.second();
    uint32_t c1, c2; uint64_t pus; uint32_t iv;
    do { c1 = g_pps_cnt; pus = g_pps_us; iv = g_pps_interval; c2 = g_pps_cnt; }
    while (c1 != c2);                            // atomic snapshot of the ISR trio
    if (!stalled && c1 > 0 && iv > 999000 && iv < 1001000) {
      g_clk_pps_us   = pus;
      g_clk_utc_sod  = sod;
      g_clk_stamp_ms = nowms;
      g_clk_valid    = true;
    }
  }
  if (g_clk_valid && (nowms - g_clk_stamp_ms) > 2500) g_clk_valid = false; // stale
}

static uint32_t core_pps_interval() { return g_pps_interval; }
static uint32_t core_sats()         { return g_gps.satellites.value(); }

// local esp_timer µs -> GPS µs-of-day (both nodes use the same anchor scheme)
static uint64_t core_local_to_gps_us(uint64_t local_us) {
  int64_t since = (int64_t)local_us - (int64_t)g_clk_pps_us;
  int64_t sod   = (int64_t)g_clk_utc_sod;
  while (since >= 1000000) { since -= 1000000; sod++; }
  while (since < 0)        { since += 1000000; sod--; }
  sod %= 86400; if (sod < 0) sod += 86400;
  return (uint64_t)sod * 1000000ULL + (uint64_t)since;
}

// ============================ onset detection ===============================
static float    g_noise    = 8000.0f;
static uint32_t g_cursor   = 0;                 // samples processed
static uint32_t g_refr_ms  = 3000;              // also = startup settle: ignore the
                                                //   INMP441 DC-offset transient (~2-3s)

// Scan newly-arrived ring samples. On a trigger, find the local peak then walk
// BACK to the last sample below 20% of peak = the true onset edge (amplitude-
// independent). Returns true + fills the onset sample index and peak.
static bool core_detect_onset(uint32_t* onset_sample, int32_t* out_peak) {
  uint32_t head = g_head;
  // never read overwritten data: keep cursor within the ring window
  if (head - g_cursor > RING_SIZE - 512) g_cursor = head - (RING_SIZE - 512);

  const uint32_t WIN = (uint32_t)(0.005f * SAMPLE_RATE);   // 5 ms
  while (g_cursor < head) {
    int32_t s = g_ring[g_cursor & RING_MASK] >> 8;
    int32_t a = s < 0 ? -s : s;
    if ((float)a < g_noise * 7.0f)                          // adapt on any non-trigger sample
      g_noise = 0.9995f * g_noise + 0.0005f * (float)a;     // (avoids the 4x-8x dead-band)

    if ((int32_t)(millis() - g_refr_ms) > 0 && (float)a > g_noise * 8.0f && a > (int32_t)ONSET_ABS_MIN) {
      uint32_t wend = g_cursor + WIN; if (wend > head) wend = head;
      int32_t peak = a;
      for (uint32_t i = g_cursor; i < wend; i++) {
        int32_t v = g_ring[i & RING_MASK] >> 8; int32_t av = v < 0 ? -v : v;
        if (av > peak) peak = av;
      }
      float low = peak * 0.2f;
      uint32_t on = g_cursor;
      uint32_t floor_idx = (head > RING_SIZE) ? head - RING_SIZE + 1 : 0;
      for (uint32_t k = 0; k < WIN && on > floor_idx; k++) {
        int32_t v = g_ring[(on - 1) & RING_MASK] >> 8; int32_t av = v < 0 ? -v : v;
        if (av < low) break;
        on--;
      }
      *onset_sample = on; *out_peak = peak;
      g_refr_ms = millis() + 700;                            // ignore echoes
      g_cursor  = wend;
      return true;
    }
    g_cursor++;
  }
  return false;
}

// ============================ bring-up ======================================
static void core_begin() {
  core_i2s_init();
  g_gpsser.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  pinMode(PIN_PPS, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_PPS), core_pps_isr, RISING);
}
