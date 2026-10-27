"""experiments.search_methods' searches, on a planted landscape instead of backtests."""

import itertools
import random

import pytest

from experiments import search_methods as sm


def planted(sizes=(6, 6, 6, 6), peak=(4, 1, 3, 2), dead=3):
    """A bowl with its top at `peak`, the last axis (`dead`) changing nothing; two pieces a cell (one
    day under each mode), the second a little lower, so the objective is the second."""
    space = sm.Space.__new__(sm.Space)
    space.product, space.names = "X", [f"a{i}" for i in range(len(sizes))]
    space.values, space.sizes = [list(range(n)) for n in sizes], list(sizes)
    space.total, space.base, space.committed = 1, (0,) * len(sizes), None
    for n in sizes:
        space.total *= n
    value = lambda c: 100.0 - sum((c[i] - peak[i]) ** 2 for i in range(len(sizes)) if i != dead)
    calls = []

    def pieces(wanted):
        calls.append(len(wanted))
        return {(c, k): value(c) - k for c, k in wanted}

    return space, pieces, value, calls


def test_a_search_is_charged_its_backtests_and_stops_at_the_budget():
    space, pieces, value, calls = planted()
    s = sm.Search(space, pieces, 2, 1, 10)
    with pytest.raises(sm.Spent):
        s.whole(space.draw(random.Random(0), 30))
    assert s.spent == 20 and sum(calls) == 20 and len(s.seen) == 10
    assert s.best() == max(s.seen, key=lambda c: s.seen[c]) and s.seen[s.best()] == value(s.best()) - 1


def test_halving_starts_from_as_many_cells_as_the_budget_pays_for():
    n = sm.halving_start(10_000, 6, 100)
    space, pieces, value, calls = planted()
    space.total = 10_000
    alive, cost = n, 0
    for k in range(6):
        cost += alive
        alive = max(1, -(-alive // 2)) if k < 5 else alive
    assert cost <= 600 < cost + 6 * 2  # one more start cell would go over
    space, pieces, value, calls = planted()
    s = sm.Search(space, pieces, 2, 1, 40)
    sm.search_halving(s, random.Random(1))
    assert s.spent <= 80 and s.best() is not None


@pytest.mark.parametrize("method", ["coord", "tpe", "gp"])
def test_the_model_based_searches_find_a_planted_top_in_a_few_percent_of_the_cells(method):
    space, pieces, value, calls = planted()
    picks = sm.run_method(method, space, pieces, 2, 1, (60, 120), seed=3)
    top = max(value(c) for c in itertools.product(*(range(n) for n in space.sizes)))
    assert value(picks[120]) == top  # 120 of 1,296 cells
    assert value(picks[60]) >= top - 2


def test_random_search_is_the_benchmark_they_beat():
    space, pieces, value, calls = planted()
    found = [value(sm.run_method("random", space, pieces, 2, 1, (60,), seed)[60]) for seed in range(5)]
    assert min(found) < 100  # the top is 1 of 1,296 cells (6 with the dead axis): 60 random draws mostly miss it


def test_the_gp_fits_its_length_scales_and_predicts_between_the_points():
    xs = [[x / 10, y / 10] for x in range(0, 11, 2) for y in range(0, 11, 5)]
    f = lambda p: 3.0 * p[0] - p[0] ** 2  # the second coordinate changes nothing
    gp = sm.fit_gp(xs, [f(p) for p in xs], [0.4, 0.4])
    assert gp.scales[1] > gp.scales[0]  # the dead axis gets the longer length scale
    mean, sd = gp.predict([0.5, 0.3])
    assert abs(mean - f([0.5, 0.3])) < 0.05 and sd < 0.2
