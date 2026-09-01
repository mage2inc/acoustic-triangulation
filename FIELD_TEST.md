# PPS Δt Field Test — the make-or-break

Goal: prove two nodes agree on time to sub-millisecond via GPS-PPS, by clapping
between them and checking the measured Δdistance matches the real geometry.

## What you need
- Both nodes on USB battery packs.
- A spot **outdoors with open sky** (a window is not enough — the GPS needs sky).
- A tape measure (or a known distance/landmarks).
- A sharp loud sound: a hard hand-clap is fine at bench-to-~40 ft; two boards
  smacked together carries farther.
- Laptop only if you want the numbers (LEDs alone give go/no-go). If you bring it,
  read **one** node's serial — each node reports the full Δt.

## LED = the whole state (no laptop needed to run it)
| LED | meaning |
|---|---|
| **RED blink** | no GPS fix yet (waiting for satellites) |
| **YELLOW blink** | has satellites, still locking (averaging position + PPS) |
| **GREEN solid** | **locked + clock ready — GO** |
| BLUE flash | this node heard a sound |
| CYAN flash | heard the other node's report over LoRa |
| **MAGENTA flash** | **PAIR — Δt computed between the two nodes** |

## Procedure

### 1. Place first, then power (important)
Each node **averages its position over the first ~60 GPS fixes** and freezes it.
So put both nodes at their **final spots first**, then power them and let them
lock. If you move a node after it locks, its reported position is stale.
- Set them a **measured distance apart** — e.g. **10 m (33 ft)**. Write it down.
- Keep them stationary and clear of your body/metal (sky view).

### 2. Wait for GREEN on both
Cold start: **~1–5 minutes** (needs a fix, then 60 fixes ≈ 60 s to lock, plus
PPS). Watch: red-blink → yellow-blink → **solid green**. Both must be green.

### 3. Test A — clock sanity (do this first)
Clap **at the exact midpoint** between the two nodes (equal distance to each).
- Expect **dt ≈ 0**, **Δdist ≈ 0** (within a few tenths of a meter).
- A large constant offset here = a clock-sync problem, not geometry.

### 4. Test B — geometry
Clap **right next to node A** (say 1 m from A).
- Expect **Δdist ≈ −(A-to-B distance)** — A hears it almost immediately, B hears
  it ~(A-B distance) later. With 10 m spacing: Δdist ≈ −9 m (from A's line).
- Then clap next to **node B** → same magnitude, **opposite sign**.

### 5. Repeat & judge
Clap each position **5+ times**. What you're looking for:
- **Test A** dt stays small and near zero (≈ within ±300 µs → <0.1 m).
- **Test B** Δdist tracks the real geometry within ~**0.5–2 m**.
- **Repeatable** across claps (consistency = timing precision).

If A is near-zero and B tracks geometry repeatably → **the GPS-PPS sync works,
sub-meter, and you're clear to build the PCB.**

## Reading the numbers (laptop)
Plug a node in and:
```
pio run -e twonode_llcc   -t monitor      # node A already flashed; just monitor
# (or -e twonode_b_llcc for node B)
```
Watch for lines like:
```
onset node=1 peak=... onset_us=...
rx node=2 onset_us=... rssi=...
>>> PAIR me(1)-node2  dt=-26100 us  Δdist=-8.95 m  (want ≈ my_dist − their_dist)
```
- `dt` = microseconds. `Δdist = dt × 343 m/s` (already computed in the line).
- Each node prints its own PAIR line (opposite signs) — reading one is enough.
- MAGENTA flash on the LED == a PAIR line just printed.

## Reading it on the uConsole (Kali/Linux) instead of the Mac
Connect the uConsole to **node A (NODE_ID 1)** — it powers *and* reads that node,
so node B just needs a battery pack. The ESP32-S3 enumerates as `/dev/ttyACM*`:
```bash
ls /dev/ttyACM*                 # usually /dev/ttyACM0
screen /dev/ttyACM0 115200      # quit: Ctrl-A then K   (or: minicom -D /dev/ttyACM0 -b 115200)
# no screen? ->  stty -F /dev/ttyACM0 115200 && cat /dev/ttyACM0
```
Read-only, so no PlatformIO needed. The `PAIR` line prints on every clap — keep it
open and clap. (Optional: the uConsole SDR can watch 915 MHz to confirm packets.)

## If it misbehaves
- **Never reaches green:** not enough sky, or GPS still cold — give it longer /
  move to clearer sky. Yellow-blink = it's trying (has sats, not locked).
- **Blue flashes but never CYAN/MAGENTA:** the two aren't hearing each other over
  LoRa (range/antenna) or the claps land >700 ms apart (clap once, sharply).
- **Δt wildly off / not repeatable:** note it and send me the serial — could be
  PPS wiring on one node or a fix that hasn't settled.
- **`pio monitor` throws a termios error:** that was my headless environment; on
  your real terminal it works. If not, tell me and I'll read it remotely.

## After it passes
Design the PCB (two-GPIO RF switch, real BUSY, GPIO48 RGB, mic L/R→GND baked in),
then scale to the 5-node layout.
