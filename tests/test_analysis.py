import pytest

pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

import pandas as pd  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from arena import analysis, report  # noqa: E402
from arena.engine import run_day  # noqa: E402
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
    assert "markouts" in capsys.readouterr().out
    assert sorted(p.name for p in (results / "plots").iterdir()) == ["d0_X.png", "d0_markouts.png", "d0_pnl.png"]
