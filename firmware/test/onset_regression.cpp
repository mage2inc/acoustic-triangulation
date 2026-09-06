// Onset-detector regression test -- runs core_detect_onset on the host, no board.
//
// It tests the REAL detector: build.sh slices the onset-detection section straight
// out of firmware/src/acoustic_core.h, so this cannot drift from what ships. (A test
// that carries its own copy of the logic proves nothing about the code you flash.)
//
//   cd firmware/test && ./build.sh && ./det_new
//
// The cadences are not invented. They are what live fire actually looked like in
// dama-hear's docs/validation-full-captures.md: strings of 19 rounds over 9.4 s
// (522 ms apart) and bursts at ~700 rpm (85.7 ms apart). A detector that reports
// fewer rounds than were fired is not "filtering echoes", it is losing data.

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cmath>
#include <vector>
#include <random>
#include <string>

#define SAMPLE_RATE    16000
#define ONSET_ABS_MIN  120000
#define RING_SIZE      65536
#define RING_MASK      (RING_SIZE - 1)

static int32_t  g_ring[RING_SIZE];
static uint32_t g_head   = 0;
static uint32_t g_now_ms = 0;
static uint32_t millis() { return g_now_ms; }

#include FRAGFILE

static void reset_detector() {
  g_noise = 8000.0f; g_cursor = 0; g_refr_ms = 3000;
#ifdef NEWVER
  g_env = 0.0f; g_armed = true; g_disarm_ms = 0; g_rearm_at = 0.0f;
#endif
  g_head = 0; g_now_ms = 0;
  for (int i = 0; i < RING_SIZE; i++) g_ring[i] = 0;
}

// Feed a signal (amplitudes in the post->>8 domain) and count detections.
static std::vector<double> run(const std::vector<int32_t>& sig) {
  reset_detector();
  std::vector<double> onsets;
  const uint32_t BLK = 128;
  for (size_t s = 0; s < sig.size(); s += BLK) {
    uint32_t n = (uint32_t)std::min((size_t)BLK, sig.size() - s);
    for (uint32_t i = 0; i < n; i++) g_ring[(g_head + i) & RING_MASK] = sig[s + i] << 8;
    g_head += n;
    g_now_ms = (uint32_t)((uint64_t)g_head * 1000ULL / SAMPLE_RATE);
    uint32_t on; int32_t pk;
    while (core_detect_onset(&on, &pk)) onsets.push_back((double)on / SAMPLE_RATE);
  }
  return onsets;
}

static std::mt19937 rng(12345);
static void add_quiet(std::vector<int32_t>& v, double secs, double amp = 2000.0) {
  std::normal_distribution<double> d(0.0, amp);
  for (int i = 0; i < (int)(secs * SAMPLE_RATE); i++) v.push_back((int32_t)d(rng));
}
// one round: sharp onset, then an exponential tail of length tail_s
static void add_round(std::vector<int32_t>& v, double at_s, double tail_s,
                      double peak = 2.0e6) {
  size_t at = (size_t)(at_s * SAMPLE_RATE);
  while (v.size() < at + 1) v.push_back(0);
  for (int i = 0; i < 8; i++) {                                   // ~0.5 ms rise/impulse
    size_t k = at + i; if (k >= v.size()) v.push_back(0);
    v[k] += (int32_t)(peak * std::sin(3.14159 * i / 7.0));
  }
  int L = (int)(tail_s * SAMPLE_RATE);
  std::normal_distribution<double> d(0.0, 1.0);
  for (int i = 0; i < L; i++) {
    size_t k = at + 8 + i; while (k >= v.size()) v.push_back(0);
    v[k] += (int32_t)(peak * 0.45 * std::exp(-i / (0.035 * SAMPLE_RATE)) * d(rng));
  }
}

static void report(const char* name, const std::vector<double>& got, int expect) {
  printf("  %-42s got %3d   expect %3d   %s\n", name, (int)got.size(), expect,
         ((int)got.size() == expect) ? "ok" : "MISMATCH");
}

int main() {
#ifdef NEWVER
  printf("== PATCHED (Schmitt re-arm) ==\n");
#else
  printf("== ORIGINAL (700 ms refractory) ==\n");
#endif
  { // A: one shot, long tail
    std::vector<int32_t> v; add_quiet(v, 3.5);
    add_round(v, 4.0, 0.30); add_quiet(v, 0.0);
    while (v.size() < (size_t)(6.0 * SAMPLE_RATE)) v.push_back((int32_t)(std::normal_distribution<double>(0,2000)(rng)));
    report("A  one shot, 300 ms tail", run(v), 1);
  }
  { // B: 700 rpm burst, 5 rounds at 85.7 ms
    std::vector<int32_t> v; add_quiet(v, 3.5);
    for (int k = 0; k < 5; k++) add_round(v, 4.0 + k * 0.0857, 0.03);
    while (v.size() < (size_t)(6.5 * SAMPLE_RATE)) v.push_back((int32_t)(std::normal_distribution<double>(0,2000)(rng)));
    report("B  700 rpm burst, 5 rounds @ 85.7 ms", run(v), 5);
  }
  { // C: the measured string -- 19 rounds over 9.4 s (522 ms apart)
    std::vector<int32_t> v; add_quiet(v, 3.5);
    for (int k = 0; k < 19; k++) add_round(v, 4.0 + k * 0.522, 0.05);
    while (v.size() < (size_t)(16.0 * SAMPLE_RATE)) v.push_back((int32_t)(std::normal_distribution<double>(0,2000)(rng)));
    report("C  measured string, 19 rounds @ 522 ms", run(v), 19);
  }
  { // E: noisy site -- a loud tail and a loud echo, where nothing else covers.
    // This does NOT demonstrate the latched re-arm level: it passes with the level latched and
    // with it drifting. Kept because high-noise behaviour was otherwise untested, and labelled
    // so nobody later reads a passing E as evidence the latch does something.
    std::vector<int32_t> v; add_quiet(v, 3.5, 25000.0);
    size_t at = (size_t)(4.0 * SAMPLE_RATE);
    while (v.size() < at) v.push_back((int32_t)(std::normal_distribution<double>(0,25000)(rng)));
    for (int i = 0; i < 8; i++) v.push_back((int32_t)(2.0e6 * std::sin(3.14159 * i / 7.0)));
    std::normal_distribution<double> pl(0.0, 60000.0);
    for (int i = 0; i < (int)(0.120 * SAMPLE_RATE); i++) {      // flat tail ~60k for 120 ms
      double e = pl(rng); v.push_back((int32_t)(e < 0 ? -e : e));
    }
    size_t echo = at + 8 + (size_t)(0.040 * SAMPLE_RATE);        // loud echo at 40 ms
    for (int i = 0; i < 8; i++) v[echo + i] += (int32_t)(3.0e5 * std::sin(3.14159 * i / 7.0));
    add_quiet(v, 1.5, 25000.0);
    report("E  noisy site, shot + echo at 40 ms", run(v), 1);
  }
  { // D: quiet only -- false alarms
    std::vector<int32_t> v; add_quiet(v, 30.0);
    report("D  30 s quiet (false alarms)", run(v), 0);
  }
  return 0;
}
