import pytest

pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from arena import analysis, report  # noqa: E402
from arena.engine import EngineConfig, run_day  # noqa: E402
from arena.model import Book, Day, MarketTrade, Order, Tick  # noqa: E402
from tests.test_engine import ScriptedBot  # noqa: E402

MARKS = [100, 100, 102, 103, 104, 104]


@pytest.fixture
def results(tmp_path):
    """One day of X: buy 2 by taking the 101 ask at tick 1, and get a resting bid filled at 99 at tick 3."""
    ticks = []
    for i, mark in enumerate(MARKS):
        asks = ((101, 5),) if i == 1 else ((mark + 1, 5),)
        trades = {"X": [MarketTrade("X", 98, 1, timestamp=i)]} if i == 3 else {}
        ticks.append(Tick(i, {"X": Book(bids=((mark - 1, 5),), asks=asks)}, trades, {"X": float(mark)}))
    day = Day("d0", ["X"], {"X": 10}, ticks)
    bot = ScriptedBot({1: [Order("X", 101, 2)], 3: [Order("X", 99, 1)]})
    report.write_csvs(run_day(day, bot), tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def light_theme():
    yield
    analysis.set_theme("light")


def test_load_run(results):
    assert analysis.days_in(results) == ["d0"]
    run = analysis.load_run(results, "d0")
    assert run.products == ["X"]
    assert list(run.colors) == ["X"]
    assert len(run.orders) == 2
    assert run.series("X", 2, 4).index.tolist() == [2, 3, 4]


def test_fill_summary_measures_edge_against_the_arrival_mid(results):
    table = analysis.fill_summary(analysis.load_run(results, "d0"))
    took, passive = table.loc[("X", "took")], table.loc[("X", "passive")]
    assert (took["fills"], took["volume"], took["bought"]) == (1, 2, 2)
    assert took["edge"] == pytest.approx(100 - 101)  # mid before tick 1 was 100
    assert passive["edge"] == pytest.approx(102 - 99)  # mid before tick 3 was 102


def test_markouts_by_horizon(results):
    table = analysis.markouts(analysis.load_run(results, "d0"), horizons=(1, 2, 5))
    assert table.loc[("X", "took"), 1] == pytest.approx(102 - 101)  # bought at tick 1, tick 2 marks 102
    assert table.loc[("X", "took"), 2] == pytest.approx(103 - 101)
    assert pd.isna(table.loc[("X", "took"), 5])  # past the end of the day
    assert table.loc[("X", "passive"), 1] == pytest.approx(104 - 99)


def test_pnl_split_adds_up_to_the_pnl(results):
    split = analysis.pnl_split(analysis.load_run(results, "d0")).loc["X"]
    assert split["capture_took"] == pytest.approx(2 * (100 - 101))  # bought 2 at 101, marked 100 that tick
    assert split["capture_passive"] == pytest.approx(103 - 99)
    assert split["carry"] == pytest.approx(2 * 2 + 2 * 1 + 3 * 1)  # positions 2, 2, 3 into ticks 2, 3, 4
    assert split["end_gap"] == 0
    assert split[["capture_took", "capture_passive", "carry", "end_gap"]].sum() == pytest.approx(split["pnl"])


@pytest.fixture
def walled(tmp_path):
    """Large quotes at 95 and 107 under a moving touch: the wall mid stays at 101 while the mark moves.

    The bot buys 2 at the 101 ask at tick 1. Market trades: a buy at the ask (tick 2), a sell at the
    bid (tick 3) and one inside the spread (tick 4).
    """
    trades = {2: 103, 3: 102, 4: 104}
    ticks = []
    for i, mark in enumerate(MARKS):
        book = Book(bids=((mark - 1, 5), (95, 20)), asks=((mark + 1, 5), (107, 20)))
        printed = {"X": [MarketTrade("X", trades[i], 1, timestamp=i)]} if i in trades else {}
        ticks.append(Tick(i, {"X": book}, printed, {"X": float(mark)}))
    day = Day("d0", ["X"], {"X": 10}, ticks)
    report.write_csvs(run_day(day, ScriptedBot({1: [Order("X", 101, 2)]})), tmp_path)
    return analysis.load_run(tmp_path, "d0")


def test_measures_against_the_wall_mid(walled):
    assert walled.timeline["wall_mid"].tolist() == [101.0] * len(MARKS)
    assert analysis.fill_summary(walled, "wall_mid").loc[("X", "took"), "edge"] == pytest.approx(0)  # 101 against 101
    assert analysis.markouts(walled, (1,), "wall_mid").loc[("X", "took"), 1] == pytest.approx(0)
    assert analysis.markouts(walled, (1,)).loc[("X", "took"), 1] == pytest.approx(102 - 101)
    split = analysis.pnl_split(walled, "wall_mid").loc["X"]
    assert (split["capture_took"], split["carry"]) == (0, 0)
    assert split["end_gap"] == pytest.approx(2 * (104 - 101))  # the mark ends 3 above the wall mid
    assert split["pnl"] == pytest.approx(2 * (104 - 101))


def test_trade_impact(walled):
    table = analysis.trade_impact(walled, horizons=(1, 2))
    mark, wall = table.loc[("X", "mark")], table.loc[("X", "wall_mid")]
    assert (mark["trades"], mark["inside"]) == (2, 1)
    assert mark["taker_edge"] == pytest.approx(((102 - 103) - (103 - 102)) / 2)  # paid 1 on each side
    assert mark[1] == pytest.approx(((103 - 102) - (104 - 103)) / 2)
    assert mark[2] == pytest.approx(((104 - 102) - (104 - 103)) / 2)
    assert wall["taker_edge"] == pytest.approx(((101 - 103) - (101 - 102)) / 2)
    assert (wall[1], wall[2]) == (0, 0)
    assert analysis.trade_impact([walled, walled], horizons=(1,)).loc[("X", "mark"), "trades"] == 4


def test_wall_mid_needs_csvs_that_have_it(results):
    run = analysis.load_run(results, "d0")
    run.timeline = run.timeline.drop(columns="wall_mid")
    with pytest.raises(ValueError, match="run the backtest again"):
        analysis.markouts(run, reference="wall_mid")
    with pytest.raises(ValueError, match="reference must be"):
        analysis.fill_summary(run, "micro_price")


def test_charts_render(results, tmp_path):
    run = analysis.load_run(results, "d0")
    for fig in (
        analysis.plot_pnl(run),
        analysis.plot_product(run, "X"),
        analysis.plot_product(run, "X", start=1, end=4, quotes=True),
        analysis.plot_markouts(run, horizons=(1, 2)),
    ):
        assert isinstance(fig, Figure)
        fig.savefig(tmp_path / "chart.png")
    with pytest.raises(ValueError):
        analysis.plot_product(run, "X", start=100, end=200)


def test_grid_charts_and_dark_theme(tmp_path):
    analysis.set_theme("dark")
    two_axes = pd.DataFrame(
        {"PARAMS.a": [1, 1, 2, 2], "PARAMS.b": [0, 1, 0, 1], "pnl_all": [5.0, -3.0, 8.0, 1.0], "nbhd_all": [1.0, 2.0, 3.0, 4.0]}
    )
    assert analysis.grid_axes(two_axes) == ["PARAMS.a", "PARAMS.b"]
    analysis.plot_grid(two_axes).savefig(tmp_path / "heatmap.png")
    analysis.plot_grid(two_axes.query("`PARAMS.b` == 0").drop(columns="PARAMS.b")).savefig(tmp_path / "line.png")
    with pytest.raises(ValueError):
        analysis.set_theme("sepia")


def test_cli_writes_charts(results, capsys):
    assert analysis.main([str(results)]) == 0
    out = capsys.readouterr().out
    assert "markouts" in out and "pnl split" in out and "market trades" in out
    assert sorted(p.name for p in (results / "plots").iterdir()) == ["d0_X.png", "d0_markouts.png", "d0_pnl.png"]


def test_crossed_resting_fills_count_as_passive(tmp_path):
    ticks = [
        Tick(0, {"X": Book(bids=((98, 5),), asks=((102, 5),))}, {}, {"X": 100.0}),
        Tick(1, {"X": Book(bids=((97, 5),), asks=((99, 5),))}, {}, {"X": 98.0}),
        Tick(2, {"X": Book(bids=((97, 5),), asks=((99, 5),))}, {}, {"X": 98.0}),
    ]
    day = Day("d0", ["X"], {"X": 10}, ticks)
    result = run_day(day, ScriptedBot({0: [Order("X", 100, 2)]}), EngineConfig(resting=True))
    report.write_csvs(result, tmp_path)
    table = analysis.fill_summary(analysis.load_run(tmp_path, "d0"))
    assert table.loc[("X", "passive"), "bought"] == 2
    assert table.loc[("X", "passive"), "edge"] == pytest.approx(100 - 100)  # arrival mid 100, filled at 100
