"""The pin map has exactly one home: firmware/src/node_config.h.

These tests enforce that, and nothing else. They do NOT check the copper, the
solder, or what is physically plugged into a board -- only that the firmware's
pin table is self-consistent and that no document has grown a second, stale copy
of it. That second copy is what this suite exists for: PPS was documented on the
GPIO the LoRa RF-switch drives, so the GPS pulse never arrived, the clock never
went ready, the node silently never transmitted, and the console called it "no
satellites".
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE_CONFIG = ROOT / "firmware" / "src" / "node_config.h"

# Files that are allowed to talk about wiring but NOT to name a GPIO number.
NUMBER_FREE_DOCS = [
    "WIRING.md",
    "HANDOFF.md",
    "NODE_FIRMWARE_DESIGN.md",
    "pcb/fab_guide.md",
    "firmware/README.md",
]

# The one place outside node_config.h that must carry literal pin numbers: you
# cannot solder from a pointer. So it is checked for agreement instead of banned.
FAB_NETMAP = ROOT / "pcb" / "gen_pdf.py"


def pins():
    """Every `#define PIN_x <n>` in node_config.h, name -> gpio."""
    src = NODE_CONFIG.read_text(encoding="utf-8")
    return {m[1]: int(m[2]) for m in re.finditer(r"^#define\s+(PIN_\w+)\s+(\d+)", src, re.M)}


# One GPIO can legitimately appear twice across radio families (DIO0 is SX127x
# only, RFSW1 is SX126x only) -- they are never compiled together.
SX127X = ["PIN_I2S_BCLK", "PIN_I2S_WS", "PIN_I2S_SD", "PIN_GPS_RX", "PIN_GPS_TX",
          "PIN_PPS", "PIN_LORA_SCK", "PIN_LORA_MISO", "PIN_LORA_MOSI",
          "PIN_LORA_NSS", "PIN_LORA_RST", "PIN_RGB", "PIN_LORA_DIO0"]
SX126X = ["PIN_I2S_BCLK", "PIN_I2S_WS", "PIN_I2S_SD", "PIN_GPS_RX", "PIN_GPS_TX",
          "PIN_PPS", "PIN_LORA_SCK", "PIN_LORA_MISO", "PIN_LORA_MOSI",
          "PIN_LORA_NSS", "PIN_LORA_RST", "PIN_RGB", "PIN_LORA_DIO1",
          "PIN_LORA_BUSY", "PIN_LORA_RFSW1", "PIN_LORA_RFSW2"]

# Pins the FIRMWARE drives. A GPS output tied to any of these is a short.
DRIVEN_BY_US = ["PIN_LORA_SCK", "PIN_LORA_MOSI", "PIN_LORA_NSS", "PIN_LORA_RST",
                "PIN_LORA_RFSW1", "PIN_LORA_RFSW2", "PIN_I2S_BCLK", "PIN_I2S_WS",
                "PIN_RGB"]


@pytest.mark.parametrize("family,names", [("SX127x", SX127X), ("SX126x", SX126X)])
def test_no_two_signals_share_a_gpio(family, names):
    p = pins()
    used = {}
    for n in names:
        assert n in p, f"{n} missing from node_config.h"
        used.setdefault(p[n], []).append(n)
    clashes = {gpio: who for gpio, who in used.items() if len(who) > 1}
    assert not clashes, f"{family} build has two signals on one GPIO: {clashes}"


def test_pps_is_not_on_a_pin_the_firmware_drives():
    """The live bug. Symptom is 'no satellites', cause is a pin fight."""
    p = pins()
    for n in DRIVEN_BY_US:
        assert p["PIN_PPS"] != p[n], (
            f"PPS shares GPIO{p['PIN_PPS']} with {n}, which the firmware drives as an "
            "output: zero PPS edges, clock never ready, node never transmits")


def test_boot_report_lists_every_pin():
    """A dump that misses a pin is worse than no dump -- it reads as complete."""
    src = NODE_CONFIG.read_text(encoding="utf-8")
    table = src[src.index("NODE_PINS[]"):src.index("static inline void node_pin_report")]
    for name in pins():
        assert name in table, f"{name} is defined but never printed at boot"


@pytest.mark.parametrize("rel", NUMBER_FREE_DOCS)
def test_docs_do_not_carry_a_second_pin_map(rel):
    """Docs describe the wiring; node_config.h defines it. A GPIO number in prose
    is a claim about the past, and this project has already lost bring-up time to
    one. Point at the boot print instead."""
    text = (ROOT / rel).read_text(encoding="utf-8")
    hits = re.findall(r"\bGP(?:IO)?\d+\b", text)
    assert not hits, f"{rel} names GPIOs {sorted(set(hits))} -- point at node_config.h"


def test_sketch_comments_do_not_carry_a_second_pin_map():
    """Same rule inside firmware/src: only node_config.h names numbers."""
    bad = {}
    for f in sorted((ROOT / "firmware" / "src").glob("*.*")):
        if f.name == "node_config.h":
            continue
        hits = re.findall(r"\bGP(?:IO)?\d+\b", f.read_text(encoding="utf-8"))
        if hits:
            bad[f.name] = sorted(set(hits))
    assert not bad, f"hardcoded pin numbers outside node_config.h: {bad}"


def test_fab_netmap_agrees_with_node_config():
    """The fab drawing must print literal numbers, so it gets checked, not banned.
    Does not verify the copper -- only that the drawing and the firmware agree."""
    p = pins()
    src = FAB_NETMAP.read_text(encoding="utf-8")
    drawn = {int(n) for n in re.findall(r"\bGP(\d+)\b", src)}
    # the drawing omits the two pins that carry no wire to a part
    expected = {p[n] for n in SX126X} - {p["PIN_GPS_TX"], p["PIN_RGB"]}
    assert drawn == expected, f"fab net map draws {sorted(drawn)}, build has {sorted(expected)}"
    for gpio, label in [(p["PIN_PPS"], "GPS PPS"), (p["PIN_LORA_RFSW2"], "RFSW_V2"),
                        (p["PIN_LORA_BUSY"], "BUSY"), (p["PIN_LORA_RST"], "NRST")]:
        assert re.search(rf"GP{gpio}\s+{label}", src), \
            f"fab net map does not put {label} on GP{gpio}"
