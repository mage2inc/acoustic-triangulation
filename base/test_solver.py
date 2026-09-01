#!/usr/bin/env python3
"""
Validate the TDoA multilateration WITHOUT hardware: place 4 nodes at the corners
of a 52x155 m lot, pick random sources, synthesize the true arrival times (+ 100us
PPS-class timing jitter), and check the solver recovers the source.

Run:  python3 test_solver.py
"""
import numpy as np
from base_station import solve_tdoa, latlon_to_m, m_to_latlon, C_SOUND

lat0, lon0 = 40.0, -75.0
W, L = 52.0, 155.0                      # lot width x length (m)
nodes_m = [(0, 0), (W, 0), (0, L), (W, L)]          # 4 corners
nodes = [m_to_latlon(x, y, lat0, lon0) for x, y in nodes_m]

def run(timing_jitter_us, pos_err_m, trials=1000, seed=1):
    rng = np.random.default_rng(seed)
    errs = []
    for _ in range(trials):
        sx, sy = rng.uniform(0, W), rng.uniform(0, L)      # true source
        emit = rng.uniform(0, 1000)                        # unknown emission time
        times_us = []
        for (nx, ny) in nodes_m:
            d = np.hypot(sx - nx, sy - ny)
            t = emit + d / C_SOUND + rng.normal(0, timing_jitter_us * 1e-6)
            times_us.append(t * 1e6)
        # solver sees node positions with GPS-class error
        solver_nodes = [m_to_latlon(x + rng.normal(0, pos_err_m),
                                    y + rng.normal(0, pos_err_m), lat0, lon0)
                        for x, y in nodes_m]
        slat, slon, rms = solve_tdoa(solver_nodes, times_us)
        rx, ry = latlon_to_m(slat, slon, lat0, lon0)
        errs.append(np.hypot(rx - sx, ry - sy))
    e = np.array(errs)
    return e.mean(), np.median(e), np.percentile(e, 90)

print("Solver validation on a 52x155 m, 4-corner array:\n")
print(f"{'timing jitter':>14} {'node pos err':>13} {'mean':>7} {'median':>7} {'p90':>7}")
for tj, pe in [(100, 0.0), (100, 1.0), (100, 2.5), (300, 2.5)]:
    m, med, p90 = run(tj, pe)
    print(f"{tj:>11} us {pe:>10.1f} m {m:>6.2f}m {med:>6.2f}m {p90:>6.2f}m")

# hard pass criterion: ideal timing + perfect positions must be ~sub-meter
m, med, p90 = run(100, 0.0)
assert med < 1.0, f"solver median error {med:.2f} m too high with clean inputs"
print("\nPASS: solver recovers the source (sub-meter with clean inputs;\n"
      "node GPS position error dominates real-world accuracy, as expected).")
