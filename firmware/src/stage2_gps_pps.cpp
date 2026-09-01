// Stage 2 — GPS NMEA + PPS timestamp (the timing foundation)
//
// GOAL: prove the PPS pulse disciplines a microsecond clock. The critical line
// to watch is `interval` — once the GPS has a fix it must read ~1000000 us
// (±a few, that's your oscillator ppm). If it does, cross-node TDoA will work.
//
//   pio run -e stage2 -t upload -t monitor
//
// Needs SKY VIEW — run it near a window or outside; first fix can take minutes.
// Wiring: GPS VCC->3V3, GND->GND, GPS-TX->GP17, GPS-RX->GP18(opt), PPS->GP8

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
  GPSser.begin(9600, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);
  pinMode(PIN_PPS, INPUT);
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

  // Heartbeat while no PPS yet
  static uint32_t hb = 0;
  if (pps_count == 0 && millis() - hb > 2000) {
    hb = millis();
    Serial.printf("no PPS yet — sats=%d  NMEA_chars=%lu  (chars climbing = GPS UART wired OK; needs sky view for a fix)\n",
                  gps.satellites.value(), (unsigned long)gps.charsProcessed());
  }
}
