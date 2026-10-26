"""The format skeletons (python/arena/formats/snapshots.py, orderlog.py): starting points for the
day's format, each loading its layout and running a bot through the engine."""

import json
import textwrap

import pytest

from arena.engine import EngineConfig, run_day
from arena.formats import FORMATS, orderlog, snapshots


def write(folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(textwrap.dedent(text).lstrip())
    return folder


BOOK = """
    timestamp,product,bid_price_1,bid_volume_1,bid_price_2,bid_volume_2,ask_price_1,ask_volume_1,ask_price_2,ask_volume_2
    0,GOLD,99.90,5,99.80,10,100.10,4,,
    0,SILVER,20.05,3,,,20.15,3,,
    100,GOLD,99.95,5,,,100.05,2,100.10,8
    100,SILVER,20.05,3,,,20.15,3,,
"""
TRADES = """
    timestamp,product,price,quantity,buyer,seller
    100,GOLD,100.05,1,,
"""


def test_snapshots_load_decimal_prices_as_whole_units(tmp_path):
    data = write(tmp_path, {"limits.json": json.dumps({"GOLD": 20, "SILVER": 10}), "d1_book.csv": BOOK, "d1_trades.csv": TRADES})
    (day,) = snapshots.load_days(snapshots.resolve_data_dir(str(data)), ["all"])
    assert day.products == ["GOLD", "SILVER"] and day.limits == {"GOLD": 20, "SILVER": 10}
    first = day.ticks[0].books["GOLD"]
    assert first.bids == ((9990, 5), (9980, 10)) and first.asks == ((10010, 4),)
    assert day.info["GOLD"] == {"tick": 0.05, "unit": 0.01} and day.info["SILVER"]["tick"] == 0.1
    assert [(t.price, t.quantity) for t in day.ticks[1].trades["GOLD"]] == [(10005, 1)]
    with pytest.raises(ValueError, match="no day 'd9'"):
        snapshots.load_days(data, ["d9"])


def test_snapshots_run_a_strategy_in_decimal_prices(tmp_path):
    data = write(tmp_path, {"limits.json": json.dumps({"GOLD": 20, "SILVER": 10}), "d1_book.csv": BOOK})
    bot_path = write(tmp_path / "bot", {"bot.py": """
        from api import Order

        class Strategy:
            def __init__(self):
                self.seen = []

            def on_tick(self, state):
                self.seen.append(state.books["GOLD"].asks[0])
                if state.timestamp == 100:
                    return [Order("GOLD", 100.05, 1), Order("GOLD", 2001 * 0.05, 1)]  # the best ask, the second with a float's error
                return []
    """}) / "bot.py"
    (day,) = snapshots.load_days(data, ["d1"])
    bot = snapshots.load_bot(bot_path, {}, strict=True)
    result = run_day(day, bot, EngineConfig())
    assert [(f.price, f.quantity) for f in result.fills] == [(10005, 1), (10005, 1)]
    assert bot._bot.seen == [(100.1, 4), (100.05, 2)] and not result.errors


def test_snapshots_reject_what_the_api_doesnt_take(tmp_path):
    data = write(tmp_path, {"limits.json": json.dumps({"GOLD": 20, "SILVER": 10}), "d1_book.csv": BOOK})
    bot_path = write(tmp_path / "bot", {"bot.py": """
        from api import Order

        class Strategy:
            def on_tick(self, state):
                return [Order("GOLD", 100.051, 1)]  # finer than a cent
    """}) / "bot.py"
    (day,) = snapshots.load_days(data, ["d1"])
    result = run_day(day, snapshots.load_bot(bot_path, {}, strict=True), EngineConfig())
    assert result.errors and "finer than 1/100" in result.errors[0][1]
    import ast
    assert snapshots.check_source(ast.parse("class Strategy:\n    def on_tick(self, state): return []")) == []
    assert snapshots.check_source(ast.parse("class Bot: pass")) == ["no top-level class Strategy"]


EVENTS = """
    timestamp,event,order_id,product,side,price,quantity
    0,add,a1,GOLD,buy,99.90,5
    0,add,a2,GOLD,buy,99.90,3
    0,add,b1,GOLD,sell,100.10,4
    100,execute,b1,,,,1
    100,modify,a2,,,,1
    100,add,b2,GOLD,sell,100.05,2
    200,delete,a1,,,,
    200,trade,,GOLD,sell,99.90,1
"""


def test_an_order_log_rebuilds_the_book_each_step(tmp_path):
    data = write(tmp_path, {"limits.json": json.dumps({"GOLD": 20}), "d1.csv": EVENTS})
    (day,) = orderlog.load_days(orderlog.resolve_data_dir(str(data)), ["all"])
    books = [t.books["GOLD"] for t in day.ticks]
    assert books[0].bids == ((9990, 8),) and books[0].asks == ((10010, 4),)
    assert books[1].bids == ((9990, 6),) and books[1].asks == ((10005, 2), (10010, 3))
    assert books[2].bids == ((9990, 1),)
    (executed,) = day.ticks[1].trades["GOLD"]
    assert (executed.price, executed.quantity, executed.buyer) == (10010, 1, orderlog.TAKER)  # it hit the resting sell
    (traded,) = day.ticks[2].trades["GOLD"]
    assert (traded.price, traded.seller) == (9990, orderlog.TAKER)
    assert day.info["GOLD"]["unit"] == 0.01 and FORMATS["orderlog"] is orderlog


def test_an_order_log_rejects_unknown_orders_and_events(tmp_path):
    for line, message in (("0,delete,zz,,,,", "unknown order 'zz'"), ("0,cross,x,GOLD,buy,1,1", "unknown event 'cross'"),
                          ("0,add,x,GOLD,long,1,1", "side 'long'")):
        data = write(tmp_path / message[:5].replace(" ", ""), {"limits.json": json.dumps({"GOLD": 20}),
                                                                "d1.csv": "timestamp,event,order_id,product,side,price,quantity\n" + line + "\n"})
        with pytest.raises(ValueError, match=message):
            orderlog.load_days(data, ["d1"])


def test_the_snapshot_example_reproduces_prosperitys_books(tmp_path):
    pytest.importorskip("arena.formats.prosperity")
    from arena.formats import prosperity

    try:
        source = prosperity.resolve_data_dir("p3")
    except ValueError:
        pytest.skip("needs references/ (references/clone.sh)")
    snapshots.write_example(tmp_path, "p3", 1, ticks=50)
    (ours,) = snapshots.load_days(tmp_path, ["r1dm2"])
    (theirs,) = prosperity.load_days(source, ["1--2"])
    for a, b in zip(ours.ticks, theirs.ticks[:50]):
        for product, book in b.books.items():
            assert a.books[product].bids == tuple((p * 10, v) for p, v in book.bids)  # prices / 10, in cents


def test_snapshots_can_call_a_module_level_function(tmp_path, monkeypatch):
    data = write(tmp_path, {"limits.json": json.dumps({"GOLD": 20, "SILVER": 10}), "d1_book.csv": BOOK})
    bot_path = write(tmp_path / "bot", {"bot.py": """
        from api import Order

        def trade(state):
            return [Order("GOLD", 100.05, 2)] if state.timestamp == 100 else []
    """}) / "bot.py"
    monkeypatch.setattr(snapshots, "ENTRY", (None, "trade"))
    (day,) = snapshots.load_days(data, ["d1"])
    result = run_day(day, snapshots.load_bot(bot_path, {}, strict=True), EngineConfig())
    assert [(f.price, f.quantity) for f in result.fills] == [(10005, 2)]
    import ast
    assert snapshots.check_source(ast.parse("def trade(state): return []")) == []
    assert snapshots.check_source(ast.parse("class Strategy: pass")) == ["no top-level function trade"]
