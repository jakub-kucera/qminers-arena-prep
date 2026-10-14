import pytest

from arena.model import Book, Day, MarketTrade, Tick
from arena.stress import perturb


def flat_day(n=10):
    """A product at 100 with walls at 98 / 102 and a small order inside, one trade each tick."""
    ticks = [
        Tick(t * 100, {"X": Book(((99, 2), (98, 20)), ((102, 20),))}, {"X": [MarketTrade("X", 102, 1)]}, {"X": 100.5})
        for t in range(n)
    ]
    return Day("d", ["X"], {"X": 10}, ticks)


def prices(day):
    return [t.books["X"].asks[0][0] for t in day.ticks]


def test_a_shift_moves_book_trades_and_mark_together_from_mid_day():
    shifted = perturb(flat_day(), "shift_up")
    # The median spread is 3 (99 to 102), so the shift is 5 x 3 = 15 from tick 5 on.
    assert prices(shifted) == [102] * 5 + [117] * 5
    assert shifted.ticks[7].trades["X"][0].price == 117 and shifted.ticks[7].marks["X"] == 115.5
    assert shifted.ticks[7].books["X"].bids == ((114, 2), (113, 20))


def test_trends_and_spikes():
    assert prices(perturb(flat_day(), "trend_down"))[-1] == 102 - 30
    spike = perturb(flat_day(400), "spike_up")
    assert prices(spike)[199] == 102 and prices(spike)[200] == 117 and prices(spike)[300] == 102


def test_no_wall_removes_the_largest_level_in_the_middle_fifth():
    day = perturb(flat_day(), "no_wall")
    assert day.ticks[4].books["X"].bids == ((99, 2),)
    assert day.ticks[4].books["X"].asks == ((102, 20),)  # a lone level is kept
    assert day.ticks[0].books["X"].bids == ((99, 2), (98, 20))


def test_vol2_doubles_the_distance_from_the_first_wall_mid():
    day = flat_day(3)
    moved = Tick(200, {"X": Book(((102, 20),), ((106, 20),))}, {}, {})
    day = Day("d", ["X"], {"X": 10}, day.ticks[:2] + [moved])
    assert perturb(day, "vol2").ticks[2].books["X"].asks == ((110, 20),)


def test_unknown_perturbation():
    with pytest.raises(ValueError, match="unknown perturbation"):
        perturb(flat_day(), "nope")
