// Stage 5 — base receiver + 2-node sync check (M2, the make-or-break)
//
// Receives Reports over LoRa, prints each as a parseable line (for the Pi in
// Stage 6), and when two nodes report the SAME event prints their Δt and the
// implied distance difference (Δt × 343 m/s).
//
//   pio run -e stage5 -t upload -t monitor
//
// M2 TEST: 2 nodes a known distance apart, clap between them, check
// Δt ≈ (dist_to_A − dist_to_B) / 343 m/s.

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include "node_config.h"
#include "report_packet.h"

#include "lora_radio.h"

volatile bool rxFlag = false;
void IRAM_ATTR onRx() { rxFlag = true; }

#define NREC 16
static Report   recent[NREC];
static uint32_t rec_ms[NREC];
static int      rec_i = 0;

#define USPERDAY   86400000000LL
#define PAIR_US    600000LL        // same-event onset window (µs)
#define PAIR_AGE   3000            // and reports must arrive within 3 s (ms)

static uint16_t last_seq_node[64];
static bool     seen_node[64];

static int64_t wrap_us(int64_t dt) {                 // handle µs-of-day midnight wrap
  if (dt >  USPERDAY / 2) dt -= USPERDAY;
  if (dt < -USPERDAY / 2) dt += USPERDAY;
  return dt;
}

static void consider_pair(const Report& r, uint32_t now_ms) {
  for (int k = 0; k < NREC; k++) {
    if (rec_ms[k] == 0) continue;
    if (now_ms - rec_ms[k] > PAIR_AGE) continue;     // must be recent arrivals
    const Report& o = recent[k];
    if (o.node_id == r.node_id) continue;
    int64_t dt = wrap_us((int64_t)r.onset_gps_us - (int64_t)o.onset_gps_us);
    if (dt < -PAIR_US || dt > PAIR_US) continue;     // same event only
    double dd = (double)dt * 1e-6 * 343.0;
    Serial.printf("   PAIR nodes %d/%d  dt=%lld us  -> Δdist=%.2f m\n",
                  r.node_id, o.node_id, (long long)dt, dd);
  }
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n== Stage 5: base receiver + sync check ==");
  node_pin_report();
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  int st = lora_begin();
  if (st != RADIOLIB_ERR_NONE) { Serial.printf("LoRa init FAILED %d\n", st); while (1) delay(1000); }
  radio.setPacketReceivedAction(onRx);
  radio.startReceive();
  Serial.println("Listening for node reports...");
}

void loop() {
  if (!rxFlag) return;
  rxFlag = false;

  Report r;
  int st = radio.readData((uint8_t*)&r, sizeof(Report));
  float rssi = radio.getRSSI();          // cache BEFORE re-arming (last-packet RSSI)
  radio.startReceive();
  if (st != RADIOLIB_ERR_NONE) return;
  if (r.node_id >= 64) return;

  // dedupe repeats of the same (node_id, seq)
  if (seen_node[r.node_id] && last_seq_node[r.node_id] == r.seq) return;
  seen_node[r.node_id] = true; last_seq_node[r.node_id] = r.seq;

  uint32_t now_ms = millis();
  Serial.printf("RPT node=%d seq=%u onset_us=%llu lat=%d lon=%d peak=%d rssi=%.1f\n",
                r.node_id, r.seq, (unsigned long long)r.onset_gps_us,
                r.lat_1e7, r.lon_1e7, r.peak, rssi);

  consider_pair(r, now_ms);
  recent[rec_i] = r; rec_ms[rec_i] = now_ms; rec_i = (rec_i + 1) % NREC;
}
