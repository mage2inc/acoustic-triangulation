"""Placement metrics. Run: python3 -m pytest base/test_placement.py -q"""
import math

import numpy as np
import pytest

import placement as PL

SQUARE = [(0.0, 0.0), (200.0, 0.0), (200.0, 200.0), (0.0, 200.0)]


def test_dop_does_not_depend_on_which_node_is_first():
    """A geometry property must not depend on the reference node the maths happens to pick."""
    base = PL.dop(SQUARE, (100.0, 100.0))["dop"]
    for k in range(1, 4):
        assert PL.dop(SQUARE[k:] + SQUARE[:k], (100.0, 100.0))["dop"] == pytest.approx(base, rel=1e-9)


def test_three_nodes_locate_but_cannot_self_check():
    r = PL.dop(SQUARE[:3], (100.0, 100.0))
    assert r["dof"] == 0 and r["redundant"] is False
    assert math.isfinite(r["dop"]), "3 nodes still give a position -- that is the trap"
    assert PL.dop(SQUARE, (100.0, 100.0))["redundant"] is True


def test_collinear_nodes_are_singular_not_confident():
    line = [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0), (300.0, 0.0)]
    assert PL.dop(line, (150.0, 0.0))["singular"] is True


def test_a_source_inside_the_array_is_located_better_than_one_far_outside():
    assert PL.dop(SQUARE, (100.0, 100.0))["dop"] < PL.dop(SQUARE, (100.0, 5000.0))["dop"]


def test_a_distant_node_improves_dop_which_is_true_and_a_trap():
    """Counterintuitive but correct: TDoA likes long baselines, so geometry alone prefers a node
    far outside the array. It is a trap because DOP says nothing about whether that node can hear
    the event. Pinned so nobody 'fixes' the maths to match the intuition."""
    b = (-100.0, -100.0, 300.0, 300.0)
    mid = PL.dop_grid(SQUARE + [(100.0, 100.0)], b, step=50.0)["median"]
    far = PL.dop_grid(SQUARE + [(600.0, 600.0)], b, step=50.0)["median"]
    assert far < mid


def test_grid_and_ranking_run():
    b = (-100.0, -100.0, 300.0, 300.0)
    g = PL.dop_grid(SQUARE, b, step=50.0)
    assert math.isfinite(g["median"]) and 0.0 <= g["usable_frac"] <= 1.0
    ranked = PL.best_addition(SQUARE, [(100.0, 100.0), (600.0, 600.0)], b, step=50.0)
    assert [r["position"] for r in ranked] == [(600.0, 600.0), (100.0, 100.0)]
    assert all(r["dof"] == 2 for r in ranked)


def test_map_reserves_at_sign_for_degenerate_cells_only():
    """The legend says '@' means degenerate. It has to be true: a saturated but finite DOP must
    not render as '@', or the map quietly lies about which cells are unsolvable."""
    assert "@" not in PL._RAMP
    line = [(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)]          # collinear -> genuinely singular
    g = PL.dop_grid(line, (-50.0, -50.0, 250.0, 50.0), step=50.0)
    assert "@" in PL.render(g, line), "singular cells must still be marked"
    sq = PL.dop_grid(SQUARE, (0.0, 0.0, 200.0, 200.0), step=50.0)
    assert "@" not in PL.render(sq, SQUARE), "a well-conditioned square has no degenerate cells"


def test_cli(capsys):
    assert PL.main(["--nodes", "40.1,-75.2;40.1,-75.198;40.102,-75.198;40.102,-75.2",
                    "--step", "40"]) == 0
    assert "median DOP" in capsys.readouterr().out
