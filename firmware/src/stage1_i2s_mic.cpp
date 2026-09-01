// Stage 1 — INMP441 I2S mic level meter (ESP32-S3, Arduino core 3.x / i2s_std)
//
// GOAL: prove the mic captures clean audio. Flash it, open the monitor, and
// tap/clap/whistle near the mic — the RMS/peak numbers and the bar should jump.
//
//   pio run -e stage1 -t upload -t monitor
//
// Wiring: INMP441 VDD->3V3, GND->GND, L/R->GND, SCK->GP4, WS->GP5, SD->GP6

#include <Arduino.h>
#include <driver/i2s_std.h>
#include <math.h>
#include "node_config.h"

static i2s_chan_handle_t rx_chan = NULL;
static int32_t samples[256];

static void mic_init() {
  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
  i2s_new_channel(&chan_cfg, NULL, &rx_chan);          // RX only (NULL tx handle)

  i2s_std_config_t std_cfg = {
    .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
    .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,
                                                    I2S_SLOT_MODE_MONO),
    .gpio_cfg = {
      .mclk = I2S_GPIO_UNUSED,
      .bclk = (gpio_num_t)PIN_I2S_BCLK,
      .ws   = (gpio_num_t)PIN_I2S_WS,
      .dout = I2S_GPIO_UNUSED,
      .din  = (gpio_num_t)PIN_I2S_SD,
      .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
    },
  };
  // INMP441 with L/R tied low drives the LEFT slot
  std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;

  ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_chan, &std_cfg));
  ESP_ERROR_CHECK(i2s_channel_enable(rx_chan));
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n== Stage 1: INMP441 I2S mic level meter ==");
  mic_init();
  Serial.println("Tap/clap the mic — bar should move.");
}

void loop() {
  size_t bytes_read = 0;
  if (i2s_channel_read(rx_chan, samples, sizeof(samples), &bytes_read, 100) != ESP_OK)
    return;
  int n = bytes_read / sizeof(int32_t);
  if (n == 0) return;

  int64_t sumsq = 0;
  int32_t peak = 0;
  for (int i = 0; i < n; i++) {
    int32_t s = samples[i] >> 8;         // INMP441: 24-bit signed in top of 32-bit slot
    sumsq += (int64_t)s * s;
    int32_t a = s < 0 ? -s : s;
    if (a > peak) peak = a;
  }

  static uint32_t t = 0;
  if (millis() - t > 150) {              // ~7 updates/sec
    t = millis();
    float rms = sqrtf((float)(sumsq / n));
    int bar = (int)(40.0f * rms / 400000.0f);
    if (bar > 40) bar = 40;
    Serial.printf("RMS %9.0f  peak %9d  |", rms, peak);
    for (int i = 0; i < bar; i++) Serial.print('#');
    Serial.println();
  }
}
