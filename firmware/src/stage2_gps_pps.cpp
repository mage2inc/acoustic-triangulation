// Stage 2 — GPS NMEA + PPS timestamp (the timing foundation)
//
// GOAL: prove the PPS pulse disciplines a microsecond clock. The critical line
// to watch is `interval` — once the GPS has a fix it must read ~1000000 us
// (±a few, that's your oscillator ppm). If it does, cross-node TDoA will work.
//
//   pio run -e stage2 -t upload -t monitor
//
// Needs SKY VIEW — run it near a window or outside; first fix can take minutes.
// Wiring: GPS VCC->3V3, GND->GND, GPS-TX->GPS_RX pin, PPS->PPS pin. The GPIO
// numbers are in node_config.h and this sketch PRINTS them at boot — wire from
// that print, never from a doc.

#include <Arduino.h>
#include <TinyGPSPlus.h>
#include "node_config.h"

TinyGPSPlus gps;
HardwareSerial GPSser(1);

// --- PPS interrupt: latch a microsecond timestamp on each 1 Hz edge ---
volatile uint64_t pps_local_us = 0;    // esp_timer us at the last PPS edge
volatile uint32_t pps_interval = 0;    // us between the last two edges (~1e6)
volatile uint32_t pps_count    = 0;

void IRAM_ATTR pps_isr() {
  uint64_t now = esp_timer_get_time();          // 1 us systimer, ISR-safe
  pps_interval = (uint32_t)(now - pps_local_us);
  pps_local_us = now;
  pps_count = pps_count + 1;
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n== Stage 2: GPS NMEA + PPS timestamp ==");
  node_pin_report();
  GPSser.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  // PULLDOWN, not bare INPUT: a floating RISING-edge pin counts noise and looks
  // like a live PPS at a junk rate. Pulled down, unwired == 0 edges, which we can
  // name. Assumes a push-pull PPS output (see acoustic_core.h for the caveat).
  pinMode(PIN_PPS, INPUT_PULLDOWN);
  attachInterrupt(digitalPinToInterrupt(PIN_PPS), pps_isr, RISING);
  Serial.println("Waiting for satellites (needs sky view)...");
}

void loop() {
  while (GPSser.available()) gps.encode(GPSser.read());

  // Print once per PPS edge
  static uint32_t last = 0;
  if (pps_count != last) {
    last = pps_count;
    noInterrupts();
    uint64_t t  = pps_local_us;
    uint32_t iv = pps_interval;
    uint32_t c  = pps_count;
    interrupts();

    Serial.printf("PPS #%-4u  interval=%7u us (want ~1000000)  local_us=%llu  ",
                  c, iv, (unsigned long long)t);
    if (gps.time.isValid())
      Serial.printf("UTC=%02d:%02d:%02d  ", gps.time.hour(), gps.time.minute(),
                    gps.time.second());
    Serial.printf("fix=%d sats=%d\n",
                  (int)gps.location.isValid(), gps.satellites.value());
  }

  // Heartbeat while no PPS yet. The old version of this line blamed sky view for
  // everything, which is exactly how a mis-wired PPS pin hides for a week: a dead
  // pin and a cold GPS look identical unless somebody names the pin.
  static uint32_t hb = 0;
  static bool verdict_printed = false;
  if (pps_count == 0 && millis() - hb > 2000) {
    hb = millis();
    Serial.printf("PPS pin GPIO%d: 0 edges in %lu s | NMEA chars=%lu sats=%u\n",
                  (int)PIN_PPS, (unsigned long)(millis() / 1000UL),
                  (unsigned long)gps.charsProcessed(), (unsigned)gps.satellites.value());
    if (!verdict_printed && millis() > 30000UL) {
      verdict_printed = true;
      if (gps.charsProcessed() <= 100)
        Serial.println("^^ no NMEA either — the GPS UART is not wired (check GPS_RX in the "
                       "boot map above), or the module has no power.");
      else if (gps.location.isValid())
        Serial.printf("^^ the GPS has a FIX and GPIO%d has still seen nothing in 30 s. "
                      "That is the wire, not the sky: unwired, on a different GPIO than "
                      "the boot map above, or held by another driver.\n", (int)PIN_PPS);
      else
        Serial.printf("^^ GPS is talking but has no fix yet, so PPS may legitimately be "
                      "absent — OR GPIO%d is the wrong pin. Check it against the boot map "
                      "now instead of waiting out an hour of sky.\n", (int)PIN_PPS);
    }
  }

  // Edges are not health: a floating or externally-driven pin also counts.
  static uint32_t bad_iv_at = 0;
  if (pps_count > 1 && (pps_interval < 999000 || pps_interval > 1001000) &&
      millis() - bad_iv_at > 5000) {
    bad_iv_at = millis();
    Serial.printf("!! PPS pin GPIO%d is toggling at interval=%u us, not ~1000000 — that is "
                  "not a GPS 1PPS. Noise on a floating input or another driver.\n",
                  (int)PIN_PPS, pps_interval);
  }
}
