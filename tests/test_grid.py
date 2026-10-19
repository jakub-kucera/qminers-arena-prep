import csv
import random
import statistics
import textwrap

import pytest

from arena import grid
from arena.engine import TradeMatching

# Buys `size` KELP at the 2032 ask on the first tick of each day; KELP is marked at 2030,
# so each day loses 2 per unit and the total over the two fixture days is -4 * size.
BOT = """
from datamodel import Order

PARAMS = {"size": 1, "unused": "x"}

class Trader:
    def run(self, state):
        if state.timestamp == 0:
            return {"KELP": [Order("KELP", 2032, PARAMS["size"])]}, 0, ""
        return {}, 0, ""
"""


@pytest.fixture
def bot(tmp_path):
    path = tmp_path / "bot.py"
    path.write_text(textwrap.dedent(BOT))
    return path


def run_main(capsys, bot, data_dir, *args):
    code = grid.main([str(bot), "1", "--data", str(data_dir), *args])
    return code, capsys.readouterr().out


@pytest.mark.parametrize(
    "text, values",
    [
        ("PARAMS.KELP.make_edge=1,2,3", [1, 2, 3]),
        ("PARAMS.KELP.make_edge=0..3", [0, 1, 2, 3]),
        ("PARAMS.KELP.smoothing=0..0.5..0.25", [0.0, 0.25, 0.5]),
        ("PARAMS.KELP.fair=mid,wall_mid", ["mid", "wall_mid"]),
        ("PARAMS.KELP.make_size=None,10", [None, 10]),
    ],
)
def test_parse_axis(text, values):
    axis = grid.parse_axis(text)
    assert axis.target == text.split("=")[0]
    assert axis.values == values


@pytest.mark.parametrize("text", ["PARAMS.X", "PARAMS.X=", "=1,2", "PARAMS.X=3..1", "PARAMS.X=1..a", "PARAMS.X=1,1"])
def test_parse_axis_rejects(text):
    with pytest.raises(ValueError):
        grid.parse_axis(text)


def test_neighborhood_mean_uses_one_step_along_each_axis():
    mode = TradeMatching.ALL
    outcomes = {}
    for i in range(3):
        for j in range(3):
            outcome = grid.Outcome((i, j), (i, j))
            outcome.day_pnl[mode] = {"d": float(10 * i + j)}
            outcomes[(i, j)] = outcome
    # (1, 1) = 11, neighbours 1, 21, 10, 12
    assert grid.neighborhood_mean(outcomes, (1, 1), (3, 3), mode) == pytest.approx((11 + 1 + 21 + 10 + 12) / 5)
    # corner (0, 0) = 0, neighbours 10 and 1
    assert grid.neighborhood_mean(outcomes, (0, 0), (3, 3), mode) == pytest.approx(11 / 3)


def _outcomes(day_pnls, failed=()):
    mode = TradeMatching.ALL
    outcomes = {}
    for i, pnls in enumerate(day_pnls):
        outcome = grid.Outcome((i,), (i,), limit_breaches=1 if i in failed else 0)
        outcome.day_pnl[mode] = dict(pnls)
        outcomes[(i,)] = outcome
    return outcomes


def test_each_day_is_scored_with_the_best_combination_on_the_other_days():
    # Combination 0 wins overall (5 against 4) only because of days d1 and d2.
    outcomes = _outcomes([{"d1": 10, "d2": 10, "d3": -15}, {"d1": 0, "d2": 0, "d3": 4}])
    picks = grid.leave_one_day_out(outcomes, TradeMatching.ALL)
    assert {day: pick.values for day, pick in picks.items()} == {"d1": (1,), "d2": (1,), "d3": (0,)}
    text = grid.format_held_out([grid.Axis("PARAMS.x", [0, 1])], [TradeMatching.ALL], outcomes, [(["d1", "d2"], ["X"])])
    assert "held out -15 against 5 for the best combination (-400%); 2 different settings chosen over 3 days" in text
    assert "! d1, d2 hold the same data for X" in text


def test_held_out_days_skip_failed_combinations_and_single_days():
    outcomes = _outcomes([{"d1": 9, "d2": 9}, {"d1": 1, "d2": 1}], failed={0})
    assert {pick.values for pick in grid.leave_one_day_out(outcomes, TradeMatching.ALL).values()} == {(1,)}
    assert grid.leave_one_day_out(_outcomes([{"d1": 1}]), TradeMatching.ALL) == {}


def test_repeated_days_are_found_per_product_without_counterparty_names():
    from arena.model import Book, Day, MarketTrade, Tick

    def day(name, buyer, price=100, extra=False):
        books = {"X": Book(((price - 1, 5),), ((price + 1, 5),))}
        if extra:  # a later round adds a product, but X's data is reused
            books["Y"] = Book(((50, 1),), ((52, 1),))
        tick = Tick(0, books, {"X": [MarketTrade("X", price, 2, buyer)]}, {})
        return Day(name, sorted(books), {p: 10 for p in books}, [tick])

    days = [day("a", ""), day("b", "Mark 22", extra=True), day("c", "", price=101)]
    assert grid.repeated_days(days) == [(["a", "b"], ["X"])]


@pytest.mark.parametrize("jobs", ["1", "2"])
def test_grid_ranks_combinations_and_writes_csv(capsys, bot, data_dir, tmp_path, jobs):
    out = tmp_path / "grid.csv"
    code, text = run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1..3", "--modes", "all,worse", "--jobs", jobs, "--out", str(out))
    assert code == 0
    assert "baseline (bot as is): pnl(all) -4" in text
    assert "best by pnl      size=1  (-4)" in text
    assert "all measures agree" in text
    assert "held out -4 against -4 for the best combination (+0%); 1 different settings chosen over 2 days" in text

    rows = list(csv.DictReader(out.open()))
    assert [row["PARAMS.size"] for row in rows] == ["1", "2", "3"]
    assert [float(row["pnl_all"]) for row in rows] == [-4, -8, -12]
    assert [float(row["nbhd_all"]) for row in rows] == [-6, -8, -10]
    assert float(rows[0]["pnl_worse_r1d0"]) == -2
    assert float(rows[2]["pnl_all_KELP"]) == -12


def test_typos_fail_before_the_grid_runs(capsys, tmp_path, data_dir):
    path = tmp_path / "bot.py"
    path.write_text(TEMPLATE_LIKE)
    with pytest.raises(SystemExit):
        grid.main([str(path), "1", "--data", str(data_dir), "--grid", "PARAMS.KELP.make_egde=1,2"])
    assert "unknown params for KELP: make_egde" in capsys.readouterr().err


def test_the_same_target_cant_be_set_twice(capsys, bot, data_dir):
    with pytest.raises(SystemExit):
        grid.main([str(bot), "1", "--data", str(data_dir), "--grid", "PARAMS.size=1,2", "--set", "PARAMS.size=3"])
    assert "set more than once" in capsys.readouterr().err


# A bot that validates its parameter names, like bots/template.py does.
TEMPLATE_LIKE = textwrap.dedent(
    """
    PARAMS = {"KELP": {"make_edge": 1}}

    class Trader:
        def run(self, state):
            unknown = set(PARAMS["KELP"]) - {"make_edge"}
            if unknown:
                raise ValueError(f"unknown params for KELP: {', '.join(sorted(unknown))}")
            return {}, 0, ""
    """
)


def test_grid_runs_against_rivals(capsys, bot, data_dir):
    code, text = run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1,2", "--vs", str(bot), "--jobs", "1")
    assert code == 0
    assert "each against bot#2 in the same market" in text


def test_neighbourhood_mean_leaves_out_failed_neighbours():
    outcomes = _outcomes([{"d": 10}, {"d": 20}, {"d": 900}], failed=(2,))
    assert grid.neighborhood_mean(outcomes, (1,), (3,), TradeMatching.ALL) == pytest.approx((20 + 10) / 2)


def test_grid_exits_1_when_every_combination_fails(capsys, data_dir, tmp_path):
    path = tmp_path / "bot.py"
    path.write_text(
        textwrap.dedent(
            """
            from datamodel import Order

            PARAMS = {"size": 1}

            class Trader:
                def run(self, state):
                    return {"KELP": [Order("KELP", 1, 1000 * PARAMS["size"])]}, 0, ""
            """
        )
    )
    code, text = run_main(capsys, path, data_dir, "--grid", "PARAMS.size=1,2", "--jobs", "1")
    assert code == 1 and "every combination failed" in text


def test_blocks_are_an_even_number_over_the_days_and_sum_to_the_day():
    assert [grid.blocks_per_day(days) for days in (1, 2, 3, 6, 7)] == [16, 8, 6, 3, 4]
    assert grid.block_pnl([1, 2, 3, 4, 5, 6], 3) == [2, 2, 2]
    assert sum(grid.block_pnl([0, -1, 4, 2, 7], 2)) == 7
    assert grid.block_pnl([1, 2], 3) == []


def test_cscv_finds_no_information_in_noise_and_finds_a_planted_edge():
    import random

    def matrix(seed, edge):
        rng = random.Random(seed)
        columns = [[rng.gauss(0, 1) for _ in range(12)] for _ in range(20)]
        columns[3] = [x + edge for x in columns[3]]
        return columns

    noise = [grid.cscv(matrix(seed, 0)) for seed in range(10)]
    assert 0.35 < sum(r.pbo for r in noise) / 10 < 0.65  # the pick is a coin flip out of sample
    assert 0.4 < sum(r.rank for r in noise) / 10 < 0.6
    planted = [grid.cscv(matrix(seed, 1.5)) for seed in range(10)]
    assert sum(r.pbo for r in planted) / 10 < 0.1
    assert planted[0].splits == planted[0].of == 924  # C(12, 6), all of them


def test_cscv_samples_the_halvings_when_there_are_many():
    columns = [[float(i == j) for i in range(20)] for j in range(3)]
    result = grid.cscv(columns, max_splits=500)
    assert (result.splits, result.of) == (500, 184_756)


def test_deflated_sharpe_ratio_reproduces_the_papers_example():
    # Bailey and Lopez de Prado, p. 9-10: annualised SR 2.5 over 1,250 days, 100 trials with an
    # annualised SR variance of 1/2, skew -3, kurtosis 10: SR0 0.1132 a day, DSR 0.9004.
    sharpe = 2.5 / 250**0.5
    sharpe0 = grid.expected_max_sharpe(0.5 / 250, 100)
    assert sharpe0 == pytest.approx(0.1132, abs=1e-4)
    assert grid.deflated_sharpe(sharpe, sharpe0, 1250, -3, 10) == pytest.approx(0.9004, abs=1e-4)
    assert grid.deflated_sharpe(sharpe, grid.expected_max_sharpe(0.5 / 250, 46), 1250, -3, 10) == pytest.approx(0.9505, abs=1e-4)
    assert grid.expected_max_sharpe(1.0, 1) == 0.0


def test_independent_trials_discount_correlated_cells():
    assert grid.independent_trials([[1, 2, 3], [2, 4, 6], [3, 6, 9]]) == pytest.approx(1)
    assert grid.independent_trials([[1, -1, 1, -1], [1, 1, -1, -1]]) == pytest.approx(2)
    assert grid.independent_trials([[1, 1, 1], [1, 2, 3]]) == 2  # a constant cell has no correlation


def test_grid_reports_trials_and_overfitting(capsys, bot, data_dir):
    code, text = run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1..3", "--modes", "all,worse")
    assert code == 0
    assert "overfitting: 3 cells × 2 modes = 6 trials on 2 days" in text


def test_omega_is_the_plain_variance_without_blocks():
    d = [1.0, -2.0, 0.5, 3.0, -1.0]
    assert grid.omega2(d, 1.0) == pytest.approx(statistics.pvariance(d))


def _gains(seed, cells, n, edge=0.0, planted=3):
    rng = random.Random(seed)
    columns = [[rng.gauss(0, 1) for _ in range(n)] for _ in range(cells)]
    columns[planted] = [x + edge for x in columns[planted]]
    return columns


def test_spa_and_stepm_find_no_edge_in_noise_and_find_a_planted_one():
    nulls = [grid.spa(_gains(seed, 15, 200), 0.1, 300, seed) for seed in range(10)]
    assert 0.2 < statistics.fmean(p["c"] for p in nulls) < 0.8
    assert all(p["l"] <= p["c"] <= p["u"] for p in nulls)
    assert sum(len(grid.stepm(_gains(seed, 15, 200), 0.1, 300)) for seed in range(10)) <= 1
    planted = _gains(0, 15, 200, edge=0.4)
    assert grid.spa(planted, 0.1, 300)["c"] < 0.01
    assert grid.stepm(planted, 0.1, 300) == [3]


def test_spa_is_not_hidden_by_poor_cells():
    # Hansen's point: adding clearly worse cells shouldn't sink a real gain under the consistent p.
    good = _gains(1, 5, 200, edge=0.2, planted=0)
    poor = [[x - 1.0 for x in column] for column in _gains(2, 40, 200)]
    with_poor = grid.spa(good + poor, 0.1, 300)
    assert with_poor["c"] <= grid.spa(good, 0.1, 300)["c"] + 0.02
    assert with_poor["c"] <= with_poor["u"]


def _outcome(index, fine, pnl):
    o = grid.Outcome(index, index)
    for mode, value in pnl.items():
        o.fine_pnl[mode] = fine
        o.day_pnl[mode] = {"d": value}
    return o


def test_snooping_names_the_cells_and_checks_them_under_the_other_modes():
    all_, worse = TradeMatching.ALL, TradeMatching.WORSE
    axes = [grid.Axis("PARAMS.edge", [0, 1, 2])]
    columns = _gains(3, 3, 100, edge=0.5, planted=1)
    baseline = _outcome((), [0.0] * 100, {all_: 0.0, worse: 0.0})
    outcomes = {(k,): _outcome((k,), columns[k], {all_: sum(columns[k]), worse: -1.0}) for k in range(3)}
    text = grid.format_snooping(axes, baseline, outcomes, [all_, worse], dsr=0.5)
    assert "100 blocks of 100 ticks, 3 distinct cells" in text
    assert "StepM at 5%: 1 cells beat the bot as is: edge=1" in text
    assert "SPA finds a gain the DSR doesn't" in text
    assert "under worse: 0 of StepM's 1 cells beat the bot as is" in text
    assert "only beat the bot as is under all" in text
    assert "pick: the bot as is" in text
    outcomes[(1,)].day_pnl[worse] = {"d": 1.0}
    text = grid.format_snooping(axes, baseline, outcomes, [all_, worse], dsr=0.5)
    assert "pick: edge=1 (all +" in text and "worse +1)" in text


def test_snooping_skips_short_days(capsys, bot, data_dir):
    code, text = run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1..3")
    assert "SPA, StepM: skipped" in text


def test_grid_runs_a_permutation_test(capsys, bot, data_dir):
    code, text = run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1..3", "--permute", "3", "--jobs", "1")
    assert code == 0
    assert "permutation test: the whole grid on 3 copies of the days, their ticks shuffled in runs of 1" in text
    assert "best cell's PnL:" in text and "lift of the best cell over the median one:" in text
    assert "(smallest possible 0.250)" in text


def test_axis_products_are_the_products_the_axes_set():
    axes = [grid.Axis("PARAMS.KELP.make_edge", [1]), grid.Axis("PARAMS.KELP.take_edge", [1])]
    assert grid.axis_products(axes, ["KELP", "RESIN"]) == ["KELP"]
    assert grid.axis_products([grid.Axis("PARAMS.size", [1])], ["KELP", "RESIN"]) == ["KELP", "RESIN"]
    assert grid.axis_products([grid.Axis("DEFAULTS.make_edge", [1])], ["KELP"]) == ["KELP"]


def test_permute_needs_sensible_arguments(capsys, bot, data_dir):
    with pytest.raises(SystemExit):
        run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1,2", "--permute-block", "0")
