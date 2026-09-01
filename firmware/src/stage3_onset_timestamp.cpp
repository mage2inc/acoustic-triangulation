// Stage 3 — onset detection + GPS-disciplined timestamp (single-node core)
//
// Uses acoustic_core.h (DMA-anchored ring buffer + robust PPS clock). On a clap
// it prints the onset time as GPS µs-of-day — the value compared across nodes.
//
//   pio run -e stage3 -t upload -t monitor
//
// Needs sky view for the GPS fix. Watch: after a fix, claps print a timestamp;
// two nodes' timestamps for the same clap differ only by propagation delay.

#include <Arduino.h>
#include "acoustic_core.h"

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n== Stage 3: onset + GPS timestamp (corrected core) ==");
  core_begin();
  Serial.println("Waiting for GPS fix (sky view), then clap.");
}

void loop() {
  core_gps_service();

  uint32_t onset; int32_t peak;
  if (core_detect_onset(&onset, &peak)) {
    if (core_clock_ready()) {
      uint64_t gps_us = core_local_to_gps_us(core_sample_to_local_us(onset));
      Serial.printf(">> ONSET node=%d peak=%d gps_us_of_day=%llu (%02u:%02u:%02u.%06u)\n",
                    NODE_ID, peak, (unsigned long long)gps_us,
                    (unsigned)(gps_us / 3600000000ULL % 24),
                    (unsigned)(gps_us / 60000000ULL % 60),
                    (unsigned)(gps_us / 1000000ULL % 60),
                    (unsigned)(gps_us % 1000000ULL));
    } else {
      Serial.printf(">> onset peak=%d (no GPS clock yet; sats=%u)\n", peak, core_sats());
    }
  }

  // periodic clock health line
  static uint32_t t = 0;
  if (millis() - t > 3000) {
    t = millis();
    Serial.printf("[clock ready=%d  pps_interval=%u us  sats=%u]\n",
                  (int)core_clock_ready(), core_pps_interval(), core_sats());
  }
}
