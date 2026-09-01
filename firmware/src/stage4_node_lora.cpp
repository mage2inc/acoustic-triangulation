// Stage 4 — full field node: mic + GPS/PPS + onset + timestamp + LoRa report
//
// The real node firmware. Uses acoustic_core.h for the corrected timing path.
// On a loud transient it self-locates (averaged GPS), timestamps the onset, and
// LoRa-transmits a Report. Pair with Stage 5 (base) on another board.
//
//   pio run -e stage4 -t upload -t monitor      (set NODE_ID per node!)

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include "acoustic_core.h"
#include "report_packet.h"

#include "lora_radio.h"

// self-location: average valid fixes while static, then lock
static double  lat_acc = 0, lon_acc = 0;
static uint32_t loc_n = 0;
static bool     pos_locked = false;
static int32_t  node_lat_1e7 = 0, node_lon_1e7 = 0;
static uint16_t seq = 0;

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.printf("\n== Stage 4: field node %d (corrected core + LoRa) ==\n", NODE_ID);
  core_begin();
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int st = lora_begin();
  if (st != RADIOLIB_ERR_NONE)
    Serial.printf("LoRa init FAILED code %d — check wiring/antenna\n", st);
  else
    Serial.println("LoRa ready. Waiting for GPS fix, then clap.");
}

void loop() {
  core_gps_service();

  // self-locate: average the first 60 valid fixes, then lock
  if (!pos_locked && g_gps.location.isUpdated() && g_gps.location.isValid()) {
    lat_acc += g_gps.location.lat(); lon_acc += g_gps.location.lng(); loc_n++;
    if (loc_n >= 60) {
      node_lat_1e7 = (int32_t)llround(lat_acc / loc_n * 1e7);
      node_lon_1e7 = (int32_t)llround(lon_acc / loc_n * 1e7);
      pos_locked = true;
      Serial.printf("position locked: %.7f, %.7f\n", lat_acc / loc_n, lon_acc / loc_n);
    }
  }

  uint32_t onset; int32_t peak;
  if (core_detect_onset(&onset, &peak) && core_clock_ready()) {
    Report r;
    r.node_id      = NODE_ID;
    r.seq          = seq++;
    r.onset_gps_us = core_local_to_gps_us(core_sample_to_local_us(onset));
    r.lat_1e7      = node_lat_1e7;
    r.lon_1e7      = node_lon_1e7;
    r.peak         = peak;

    delay(NODE_ID * 60);                        // staggered backoff (timestamp is in payload)
    int st = radio.transmit((uint8_t*)&r, sizeof(r));
    Serial.printf(">> TX node=%d seq=%u onset_us=%llu peak=%d tx=%s\n",
                  r.node_id, r.seq, (unsigned long long)r.onset_gps_us, peak,
                  st == RADIOLIB_ERR_NONE ? "ok" : "ERR");
  }
}
