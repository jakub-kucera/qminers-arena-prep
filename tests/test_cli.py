from pathlib import Path

from arena import backtest
from arena.cli import Requote, participant_names
from arena.engine import EngineConfig, run_market
from arena.model import Book, Day, Order, Tick
from tests.test_grid import BOT


def test_participant_names_number_repeated_files():
    names = participant_names(Path("bots/template.py"), [Path("x/template.py"), Path("other.py"), Path("template.py")])
    assert names == ["template", "template#2", "other", "template#3"]


def test_backtest_reports_rivals(capsys, tmp_path, data_dir):
    path = tmp_path / "bot.py"
    path.write_text(BOT)
    code = backtest.main([str(path), "1", "--data", str(data_dir), "--vs", str(path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "vs bot#2: pnl" in out
    assert "rivals: bot#2" in out


class _NeverCancels:
    """A bot written for orders that live one tick: the same bid every tick, never a cancel."""

    def __init__(self):
        self.seen_open = []

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        self.seen_open.append(list(open_orders))
        return [Order("X", 90, 1)]


def test_requote_cancels_a_rivals_resting_orders_every_tick():
    d = Day("d", ["X"], {"X": 2}, [Tick(t, {"X": Book(((89, 5),), ((111, 5),))}, {}, {}) for t in range(0, 500, 100)])
    plain, wrapped = _NeverCancels(), _NeverCancels()
    (piled,) = run_market(d, [("rival", plain)], EngineConfig(resting=True))
    (requoted,) = run_market(d, [("rival", Requote(wrapped))], EngineConfig(resting=True))
    assert piled.limit_breaches  # the bids pile up past the limit of 2
    assert not requoted.limit_breaches and len(requoted.cancels) == 4
    assert all(seen == [] for seen in wrapped.seen_open)  # it never sees its own resting orders
