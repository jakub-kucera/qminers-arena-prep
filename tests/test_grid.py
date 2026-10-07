import csv
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


@pytest.mark.parametrize("jobs", ["1", "2"])
def test_grid_ranks_combinations_and_writes_csv(capsys, bot, data_dir, tmp_path, jobs):
    out = tmp_path / "grid.csv"
    code, text = run_main(capsys, bot, data_dir, "--grid", "PARAMS.size=1..3", "--modes", "all,worse", "--jobs", jobs, "--out", str(out))
    assert code == 0
    assert "baseline (bot as is): pnl(all) -4" in text
    assert "best by pnl      size=1  (-4)" in text
    assert "all measures agree" in text

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
