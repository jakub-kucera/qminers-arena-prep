import statistics

from arena import backtest, report
from arena.engine import DayResult, EngineConfig, run_day
from arena.model import Order
from tests.test_engine import ScriptedBot, day, tick
from tests.test_grid import BOT


def test_the_portal_metrics_add_up_to_the_pnl():
    d = day(tick(0, asks=[(101, 20)], mark=100), tick(1, mark=100), tick(2, bids=[(99, 20)], mark=100), limits={"X": 10})
    script = {0: [Order("X", 101, 6), Order("X", 101, 6)], 2: [Order("X", 99, -12)]}
    result = run_day(d, ScriptedBot(script), EngineConfig(limit_penalty=2.5))
    (row,) = [line.split() for line in report.format_metrics(result, 2.5).splitlines() if line.strip().startswith("X ")]
    se = statistics.stdev([-17, -5, -12]) * 3**0.5  # the PnL's changes: -17, -22, -34
    # fills (orders), volume, position, cash, mark, penalty, s.e. ticks, s.e. blocks, quantiles, pnl
    assert row == ["X", "3", "(3)", "24", "0", "-24.00", "100.00", "10.00", f"{se:.2f}", "-", "12", "/", "12", "/", "12", "/", "12",
                   "-34.00"]  # cash -24 (bought 12 at 101, sold at 99) - penalty 10 = pnl -34


def test_the_portal_metrics_without_a_penalty_and_with_two_products():
    d = day(tick(0, asks=[(101, 5)], mark=100), tick(1, bids=[(102, 5)], mark=103))
    result = run_day(d, ScriptedBot({0: [Order("X", 101, 2)]}))
    text = report.format_metrics(result)
    assert "penalty" in text and "total" not in text  # one product: no total row
    (row,) = [line.split() for line in text.splitlines() if line.strip().startswith("X ")]
    assert row[1:8] == ["1", "(1)", "2", "2", "-202.00", "103.00", "0.00"] and row[-1] == "4.00"
    assert report.format_metrics(run_day(d, ScriptedBot())) == "  portal metrics: no trades"


def test_the_standard_errors_and_quantiles():
    assert report._quantiles([4, 1, 3, 2], (0.5, 0.25, 1.0)) == [2.5, 1.75, 4]  # as numpy.quantile
    pnl = [float(k % 2) for k in range(1, 41)]  # changes +1, -1, ...: every block of two sums to 0
    ticks, blocks = report._standard_errors(pnl)
    assert ticks == f"{statistics.stdev([1, -1] * 20) * 40**0.5:,.2f}" and blocks == "0.00"
    assert report._standard_errors([5.0]) == ["-", "-"]


def test_two_products_get_a_total_row():
    result = DayResult("d", ["A", "B"], {"A": 10, "B": 10}, timestamps=[0, 1], positions={"A": [1, 2], "B": [0, -1]},
                       marks={"A": [10.0, 11.0], "B": [5.0, 5.0]}, pnl={"A": [0.0, 1.0], "B": [0.0, 0.5]})
    (total,) = [line.split() for line in report.format_metrics(result).splitlines() if line.strip().startswith("total")]
    # no fills recorded: 0 (0); cash A 1 - 22, B 0.5 + 5
    assert total[1:4] == ["0", "(0)", "0"] and total[5] == "-15.50" and total[-1] == "1.50"


def test_the_portal_metrics_total_sums_the_days():
    first = DayResult("d0", ["X"], {"X": 10}, timestamps=[0, 1], positions={"X": [1, 2]},
                      marks={"X": [10.0, 11.0]}, pnl={"X": [0.0, 1.0]})
    second = DayResult("d1", ["X"], {"X": 10}, timestamps=[0, 1], positions={"X": [3, 4]},
                       marks={"X": [12.0, 13.0]}, pnl={"X": [0.0, 2.0]})
    text = report.format_metrics_total([first, second])
    (row,) = [line.split() for line in text.splitlines() if line.strip().startswith("X ")]
    # cash: day 0 1 - 2 x 11 = -21; day 1 2 - 4 x 13 = -50
    assert row[1:8] == ["0", "(0)", "0", "4", "-71.00", "13.00", "0.00"] and row[-1] == "3.00"
    assert "s.e. days" in text and "days: 2" in text and "sum 3.00" in text and "mean 1.50" in text
    empty = DayResult("d", ["X"], {"X": 1}, positions={"X": []}, marks={"X": []}, pnl={"X": []})
    assert report.format_metrics_total([empty]) == "  portal metrics over 1 day: no trades"


def test_backtest_prints_the_portal_metrics_on_request(capsys, tmp_path, data_dir):
    path = tmp_path / "bot.py"
    path.write_text(BOT)
    assert backtest.main([str(path), "1", "--data", str(data_dir)]) == 0
    assert "portal metrics" not in capsys.readouterr().out
    assert backtest.main([str(path), "1", "--data", str(data_dir), "--metrics"]) == 0
    out = capsys.readouterr().out
    assert "portal metrics (--metrics):" in out
    assert "portal metrics over 2 days" in out
