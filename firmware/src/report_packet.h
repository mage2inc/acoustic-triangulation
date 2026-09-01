#pragma once
#include <stdint.h>

// On-air detection report (LoRa payload). Same struct on node and base.
// 23 bytes packed. onset_gps_us is µs-of-day (UTC) — the value compared for TDoA.
struct __attribute__((packed)) Report {
  uint8_t  node_id;
  uint16_t seq;
  uint64_t onset_gps_us;   // microseconds of day (UTC)
  int32_t  lat_1e7;        // self-located position, degrees × 1e7
  int32_t  lon_1e7;
  int32_t  peak;           // peak amplitude
};
