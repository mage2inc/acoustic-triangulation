// Diagnostic: does acoustic_core's I2S ring actually capture live audio?
// Dumps ring stats + raw samples. If min/max/mean are frozen while you make
// noise, the DMA-callback capture is broken (stale buffer).
#include <Arduino.h>
#include "acoustic_core.h"

void setup() {
  Serial.begin(115200); delay(1200);
  node_pin_report();
  core_i2s_init();
  Serial.println("\n== acoustic_core I2S ring dump (make noise!) ==");
}

void loop() {
  delay(500);
  uint32_t h = g_head;
  int32_t mn = INT32_MAX, mx = INT32_MIN; int64_t sum = 0;
  for (int i = 1; i <= 512; i++) {
    int32_t v = g_ring[(h - i) & RING_MASK] >> 8;
    if (v < mn) mn = v; if (v > mx) mx = v; sum += v;
  }
  Serial.printf("head=%lu  min=%ld max=%ld mean=%ld  last6:",
                (unsigned long)h, (long)mn, (long)mx, (long)(sum / 512));
  for (int i = 6; i >= 1; i--) Serial.printf(" %ld", (long)(g_ring[(h - i) & RING_MASK] >> 8));
  Serial.println();
}
