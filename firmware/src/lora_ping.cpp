// LoRa ping test — proves the RYLR689 (LLCC68) link, isolated from GPS/mic.
// One board flashed as TX, the other as RX (or watch TX on an SDR at 915 MHz).
//
//   pio run -e lora_tx_llcc -t upload     (board A: sends "ping N" every 1s)
//   pio run -e lora_rx_llcc -t upload     (board B: prints received + RSSI)
//
// Status is reprinted every second (incl. the init code) so a serial reader that
// attaches after boot still sees whether the radio came up — the ESP32-S3 native
// USB port re-enumerates on reset and eats one-shot boot prints.
//
// Wiring (RYLR689): NSS/SCK/MISO/MOSI/RST/DIO1/BUSY/RFSW_V1/RFSW_V2 per the pin
// map this sketch prints at boot (node_config.h is the only pin map). Plus
// 3.3V/GND and the ANT coil — never TX bare!

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include "node_config.h"

#include "lora_radio.h"

int g_init = -999;

void setup() {
  Serial.begin(115200);
  delay(1800);                                 // let HWCDC enumerate + host attach
  for (int i = 0; i < 3; i++) { Serial.printf("BOOT %d (pre-radio)\n", i); delay(150); }
  node_pin_report();
  Serial.println("SPI.begin ...");
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_NSS);
  Serial.println("lora_begin() ... (if this is the last line, radio.begin hung -> BUSY/SPI wiring)");
  g_init = lora_begin();
#ifdef LORA_TX
  Serial.printf("\n== LoRa PING TX ==  freq=%.1f init=%d\n", LORA_FREQ, g_init);
#else
  Serial.printf("\n== LoRa PING RX ==  freq=%.1f init=%d\n", LORA_FREQ, g_init);
#endif
  if (g_init != RADIOLIB_ERR_NONE)
    Serial.println("LoRa init FAILED — check SPI wiring / BUSY / RFSW / 3.3V against the pin map above");
  else
    Serial.println("LoRa ready.");
}

#ifdef LORA_TX
void loop() {
  static uint32_t n = 0;
  if (g_init != RADIOLIB_ERR_NONE) {           // radio didn't come up
    Serial.printf("TX idle — init=%d (radio FAIL, fix wiring)\n", g_init);
    delay(1000); return;
  }
  char msg[24];
  snprintf(msg, sizeof(msg), "ping %lu", (unsigned long)n++);
  int st = radio.transmit(msg);
  Serial.printf("init=%d  TX '%s' -> %s\n", g_init, msg,
                st == RADIOLIB_ERR_NONE ? "ok" : "ERR");
  delay(1000);
}
#else
void loop() {
  static uint32_t last = 0;
  if (millis() - last > 1000) {                // heartbeat so a late reader sees status
    last = millis();
    Serial.printf("init=%d  %s  RX waiting for TX...\n", g_init,
                  g_init == RADIOLIB_ERR_NONE ? "OK" : "RADIO FAIL");
  }
  if (g_init != RADIOLIB_ERR_NONE) { delay(200); return; }
  String s;
  int st = radio.receive(s);                    // blocks until a packet or timeout
  if (st == RADIOLIB_ERR_NONE)
    Serial.printf("RX '%s'  RSSI %.1f dBm  SNR %.1f dB\n",
                  s.c_str(), radio.getRSSI(), radio.getSNR());
  else if (st != RADIOLIB_ERR_RX_TIMEOUT)
    Serial.printf("RX err %d\n", st);
}
#endif
