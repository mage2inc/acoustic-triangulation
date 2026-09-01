#!/usr/bin/env python3
"""
Base station (Stage 6) — runs on the Raspberry Pi.

Reads Report lines from the base/office ESP32 over USB serial (the lines Stage 5
prints: "RPT node=.. seq=.. onset_us=.. lat=.. lon=.. peak=.. rssi=.."),
correlates reports of the same event, multilaterates the source via TDoA, and
serves a live Leaflet/OpenStreetMap page.

Run:  python3 base_station.py --port /dev/ttyACM0
Deps: numpy scipy pyserial flask   (pip install -r requirements.txt)
"""
import argparse, re, threading, time, math
from collections import deque
import numpy as np
from scipy.optimize import least_squares

C_SOUND = 343.0          # m/s (adjust for temperature: 331 + 0.6*Tc)
EVENT_WINDOW_US = 600_000  # reports within this span = same event (~max propagation)

# ----------------------------------------------------------------------------
# Geo helpers (local equirectangular around a reference)
# ----------------------------------------------------------------------------
R_EARTH = 6_371_000.0

def latlon_to_m(lat, lon, lat0, lon0):
    x = math.radians(lon - lon0) * R_EARTH * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R_EARTH
    return x, y

def m_to_latlon(x, y, lat0, lon0):
    lat = lat0 + math.degrees(y / R_EARTH)
    lon = lon0 + math.degrees(x / (R_EARTH * math.cos(math.radians(lat0))))
    return lat, lon

# ----------------------------------------------------------------------------
# TDoA multilateration
#   nodes: list of (lat, lon);  times_us: onset µs (same order); >=3 required
#   returns (lat, lon, residual_rms_m)
# ----------------------------------------------------------------------------
def solve_tdoa(nodes, times_us, c=C_SOUND):
    n = len(nodes)
    if n < 3:
        return None
    lat0 = sum(a for a, _ in nodes) / n
    lon0 = sum(b for _, b in nodes) / n
    P = np.array([latlon_to_m(a, b, lat0, lon0) for a, b in nodes])   # (n,2) meters
    t = np.array(times_us, dtype=float) * 1e-6                        # seconds
    ref = int(np.argmin(t))                                          # earliest arrival
    obs = c * (t - t[ref])            # observed range-differences, METERS (well-scaled)

    def resid(s):
        d = np.sqrt(((P - s) ** 2).sum(axis=1))                      # source->node dists
        return (d - d[ref]) - obs                                   # residual in meters

    # grid-search seed over the node bounding box (+margin) to dodge local minima,
    # then Levenberg-Marquardt refine. (Residuals in meters => solver converges.)
    xmin, ymin = P.min(axis=0)
    xmax, ymax = P.max(axis=0)
    mx = 0.5 * (xmax - xmin) + 10.0
    my = 0.5 * (ymax - ymin) + 10.0
    gx = np.linspace(xmin - mx, xmax + mx, 30)
    gy = np.linspace(ymin - my, ymax + my, 30)
    best, best_cost = P.mean(axis=0), 1e18
    for x in gx:
        for y in gy:
            r = resid(np.array([x, y]))
            cost = float((r * r).sum())
            if cost < best_cost:
                best_cost, best = cost, (x, y)

    res = least_squares(resid, np.array(best, dtype=float), method="lm")
    lat, lon = m_to_latlon(res.x[0], res.x[1], lat0, lon0)
    rms_m = float(np.sqrt(np.mean(res.fun ** 2)))                   # residual already meters
    return lat, lon, rms_m

# ----------------------------------------------------------------------------
# State (shared with web thread)
# ----------------------------------------------------------------------------
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.nodes = {}          # node_id -> {lat, lon, n}  (position, averaged)
        self.buffer = deque(maxlen=200)   # recent reports for correlation
        self.events = deque(maxlen=100)   # solved events

    def add_node_pos(self, nid, lat, lon):
        if lat == 0 and lon == 0:
            return
        with self.lock:
            nd = self.nodes.setdefault(nid, {"lat": lat, "lon": lon, "n": 0})
            nd["n"] += 1
            k = nd["n"]
            nd["lat"] += (lat - nd["lat"]) / k     # running average
            nd["lon"] += (lon - nd["lon"]) / k

    def add_report(self, rpt):
        with self.lock:
            self.buffer.append(rpt)
            grp = [r for r in self.buffer
                   if abs(r["onset_us"] - rpt["onset_us"]) <= EVENT_WINDOW_US]
            by_node = {}
            for r in grp:                          # one (latest) per node
                by_node[r["node_id"]] = r
            if len(by_node) < 3:
                return
            nodes, times = [], []
            for r in by_node.values():
                pos = self.nodes.get(r["node_id"])
                if not pos:
                    return
                nodes.append((pos["lat"], pos["lon"]))
                times.append(r["onset_us"])
        sol = solve_tdoa(nodes, times)
        if sol:
            lat, lon, rms = sol
            with self.lock:
                self.events.append({
                    "lat": lat, "lon": lon, "rms_m": rms,
                    "n_nodes": len(nodes), "t": time.time(),
                })
            print(f"[EVENT] {lat:.6f},{lon:.6f}  residual={rms:.1f} m  ({len(nodes)} nodes)")

    def snapshot(self):
        with self.lock:
            return {
                "nodes": [{"id": k, "lat": v["lat"], "lon": v["lon"]}
                          for k, v in self.nodes.items()],
                "events": list(self.events)[-20:],
            }

STATE = State()

# ----------------------------------------------------------------------------
# Serial reader
# ----------------------------------------------------------------------------
RPT_RE = re.compile(
    r"RPT node=(\d+) seq=(\d+) onset_us=(\d+) lat=(-?\d+) lon=(-?\d+) peak=(-?\d+)")

def serial_loop(port, baud):
    import serial
    while True:
        try:
            with serial.Serial(port, baud, timeout=1) as ser:
                print(f"[serial] connected {port} @ {baud}")
                for raw in ser:
                    line = raw.decode(errors="replace").strip()
                    m = RPT_RE.search(line)
                    if not m:
                        continue
                    nid, seq, onset, lat_i, lon_i, peak = (int(x) for x in m.groups())
                    lat, lon = lat_i / 1e7, lon_i / 1e7
                    STATE.add_node_pos(nid, lat, lon)
                    STATE.add_report({"node_id": nid, "seq": seq,
                                      "onset_us": onset, "peak": peak})
        except Exception as e:
            print(f"[serial] {e}; retry in 3s")
            time.sleep(3)

# ----------------------------------------------------------------------------
# Web (Flask + Leaflet)
# ----------------------------------------------------------------------------
MAP_HTML = """<!doctype html><html><head><meta charset=utf-8>
<title>Acoustic Triangulation</title>
<link rel=stylesheet href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{height:100%;margin:0}</style></head><body>
<div id=map></div><script>
var map=L.map('map'); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
 {maxZoom:19,attribution:'OSM'}).addTo(map);
var nodeLayer=L.layerGroup().addTo(map), evLayer=L.layerGroup().addTo(map), fitted=false;
async function tick(){
 let s=await (await fetch('/api/state')).json();
 nodeLayer.clearLayers(); evLayer.clearLayers(); let pts=[];
 for(const n of s.nodes){L.circleMarker([n.lat,n.lon],{radius:7,color:'#1565c0',
   fillColor:'#42a5f5',fillOpacity:1}).bindTooltip('node '+n.id,{permanent:true}).addTo(nodeLayer);
   pts.push([n.lat,n.lon]);}
 for(const e of s.events){L.circle([e.lat,e.lon],{radius:Math.max(e.rms_m,3),
   color:'#c62828',fillColor:'#ef5350',fillOpacity:.4}).bindPopup(
   'source ±'+e.rms_m.toFixed(1)+'m ('+e.n_nodes+' nodes)').addTo(evLayer);
   pts.push([e.lat,e.lon]);}
 if(!fitted && pts.length){map.fitBounds(pts,{padding:[40,40],maxZoom:19});fitted=true;}
}
setInterval(tick,1000); tick();
</script></body></html>"""

def run_web(host, port):
    from flask import Flask, jsonify, Response
    app = Flask(__name__)
    app.route("/")(lambda: Response(MAP_HTML, mimetype="text/html"))
    app.route("/api/state")(lambda: jsonify(STATE.snapshot()))
    app.run(host=host, port=port, threaded=True)

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0", help="base ESP32 serial port")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--web-host", default="0.0.0.0")
    ap.add_argument("--web-port", type=int, default=8080)
    a = ap.parse_args()
    threading.Thread(target=serial_loop, args=(a.port, a.baud), daemon=True).start()
    print(f"[web] http://localhost:{a.web_port}")
    run_web(a.web_host, a.web_port)
