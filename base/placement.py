#!/usr/bin/env python3
"""Where should the nodes go? Answered before anything is mounted.

base_station.py can only be as good as the geometry it is handed. This works out, for a candidate
node layout, how well a point source can be located ANYWHERE in the area -- and where it cannot be.

Two numbers, because they answer different questions and only one of them is DOP:

  dop  -- metres of position error per metre of range-difference error. Multiply by c * sigma_t
          for a real figure. It says how PRECISELY you locate, assuming nothing is wrong.

  dof  -- redundant equations. With N nodes, TDoA gives N-1 equations for 2 unknowns, so three
          nodes give dof 0: the fit is exact, the residual is ~0 BY CONSTRUCTION, and it cannot
          tell you the fit is wrong. DOP can look excellent at dof 0. Four nodes is where the
          residual solve_tdoa() prints begins to carry information.

WHAT THIS DOES NOT MODEL: whether a node can actually HEAR the event. DOP improves with baseline
extent, so this will happily tell you a node 2 km away is worth more than one in the middle of the
array -- geometrically true, and useless if the shot never clears that node's threshold. Treat the
ranking as "best geometry among sites that all detect", and decide detectability separately.

Coordinates match base_station.py: lat/lon in, local equirectangular metres inside.
Depends on numpy only.

    python3 base/placement.py --nodes "40.1,-75.2;40.1,-75.198;40.102,-75.198;40.102,-75.2"
    python3 base/placement.py --nodes ... --candidates "40.101,-75.199"
"""
import argparse
import math

import numpy as np

R_EARTH = 6_371_000.0

# Position error per metre of range-difference error, above which a layout is not worth mounting.
DOP_USABLE = 10.0


def latlon_to_m(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * R_EARTH * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R_EARTH
    return x, y


def dop(nodes_m, source_m):
    """Dilution of precision for point-source TDoA at `source_m`. Local metres.

    Formulated by marginalising the unknown emission time -- the projector (I - 11'/N) -- rather
    than differencing against a chosen reference node. Otherwise the answer depends on which node
    you call node 0, and a property of the geometry should not depend on the bookkeeping.
    """
    P = np.asarray(nodes_m, float)[:, :2]
    s = np.asarray(source_m, float)[:2]
    n = len(P)
    if n < 3:
        raise ValueError("need >= 3 nodes")
    d = s[None, :] - P
    r = np.linalg.norm(d, axis=1)
    dof = (n - 1) - 2
    if float(r.min()) < 1e-6:
        return {"dop": float("inf"), "dof": dof, "redundant": dof > 0, "singular": True}
    G = d / r[:, None]
    F = G.T @ (np.eye(n) - np.ones((n, n)) / n) @ G
    try:
        if abs(float(np.linalg.det(F))) < 1e-12:
            raise np.linalg.LinAlgError
        val = float(np.sqrt(np.trace(np.linalg.inv(F))))
    except np.linalg.LinAlgError:
        val = float("inf")          # collinear nodes, or the source on their baseline
    return {"dop": val, "dof": dof, "redundant": dof > 0, "singular": not math.isfinite(val)}


def dop_grid(nodes_m, bounds, step=10.0):
    x0, y0, x1, y1 = bounds
    xs = np.arange(x0, x1 + step * 0.5, step)
    ys = np.arange(y0, y1 + step * 0.5, step)
    g = np.empty((len(ys), len(xs)), float)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            g[j, i] = dop(nodes_m, (x, y))["dop"]
    finite = g[np.isfinite(g)]
    return {"grid": g, "xs": xs, "ys": ys,
            "median": float(np.median(finite)) if finite.size else float("inf"),
            "usable_frac": float(np.mean(g <= DOP_USABLE))}


def best_addition(nodes_m, candidates_m, bounds, step=20.0):
    """Rank candidate sites for the next node by median DOP with it added."""
    base = dop_grid(nodes_m, bounds, step)["median"]
    out = []
    for c in candidates_m:
        g = dop_grid(list(nodes_m) + [c], bounds, step)
        out.append({"position": (float(c[0]), float(c[1])), "median_dop": g["median"],
                    "gain": base - g["median"], "usable_frac": g["usable_frac"],
                    "dof": (len(nodes_m) + 1 - 1) - 2})
    out.sort(key=lambda r: r["median_dop"])
    return out


_RAMP = " .:-=+*#%"          # '@' is reserved for non-finite


def render(g, nodes_m, width=60):
    """ASCII map. ' ' is well-conditioned, '@' degenerate, 'N' a node. North up."""
    grid, xs, ys = g["grid"], g["xs"], g["ys"]
    st = max(1, len(xs) // width)
    sub, sx, sy = grid[::st, ::st], xs[::st], ys[::st]
    marks = {}
    for p in nodes_m:
        i = int(np.argmin(np.abs(sx - p[0])))
        j = int(np.argmin(np.abs(sy - p[1])))
        marks[(j, i)] = "N"
    lines = []
    for j in range(sub.shape[0] - 1, -1, -1):
        row = []
        for i in range(sub.shape[1]):
            if (j, i) in marks:
                row.append("N")
            elif not math.isfinite(sub[j, i]):
                row.append("@")
            else:
                f = (min(max(sub[j, i], 1.0), DOP_USABLE * 2.0) - 1.0) / (DOP_USABLE * 2.0 - 1.0)
                row.append(_RAMP[min(len(_RAMP) - 1, int(f * len(_RAMP)))])
        lines.append("".join(row))
    return "\n".join(lines)


def _parse_latlon(s):
    out = []
    for part in s.split(";"):
        part = part.strip()
        if part:
            a, b = part.split(",")
            out.append((float(a), float(b)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Node placement quality for TDoA multilateration.")
    ap.add_argument("--nodes", required=True, help='"lat,lon;lat,lon;..." (>=3)')
    ap.add_argument("--candidates", default="", help='sites for one more node, same format')
    ap.add_argument("--margin", type=float, default=100.0, help="box margin around nodes (m)")
    ap.add_argument("--step", type=float, default=5.0, help="grid step (m)")
    ap.add_argument("--sigma-us", type=float, default=1.0, help="per-node timing error (us)")
    ap.add_argument("--c", type=float, default=343.0, help="speed of sound (m/s)")
    a = ap.parse_args(argv)

    ll = _parse_latlon(a.nodes)
    if len(ll) < 3:
        print("need >= 3 nodes")
        return 2
    lat0, lon0 = ll[0]
    P = [latlon_to_m(la, lo, lat0, lon0) for la, lo in ll]
    A = np.asarray(P, float)
    b = (A[:, 0].min() - a.margin, A[:, 1].min() - a.margin,
         A[:, 0].max() + a.margin, A[:, 1].max() + a.margin)
    g = dop_grid(P, b, a.step)
    dof = (len(P) - 1) - 2

    print("nodes      %d    dof %d    %s" % (
        len(P), dof,
        "residual carries information" if dof > 0
        else "RESIDUAL IS ZERO BY CONSTRUCTION -- it cannot tell you the fit is wrong"))
    print("median DOP %.2f   -> %.0f mm of position error at %.1f us of timing error"
          % (g["median"], g["median"] * a.c * a.sigma_us * 1e-6 * 1000.0, a.sigma_us))
    print("usable     %.0f%% of the box at DOP <= %.0f" % (100 * g["usable_frac"], DOP_USABLE))
    print("           (geometry only -- a node still has to hear the event)")
    print()
    print(render(g, P))
    print("\n' '=good  '@'=degenerate  'N'=node   north up")

    if a.candidates:
        cand = [latlon_to_m(la, lo, lat0, lon0) for la, lo in _parse_latlon(a.candidates)]
        print("\ncandidates for the next node, best first:")
        for r in best_addition(P, cand, b, max(a.step, 20.0)):
            print("  (%8.1f,%8.1f) m   median DOP %6.2f (%+.2f)   dof %d"
                  % (r["position"][0], r["position"][1], r["median_dop"], -r["gain"], r["dof"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
