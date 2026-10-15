import textwrap

import pytest

from arena.botfile import OverrideError, parse_override
from arena.formats import prosperity
from arena.model import Book, Cancel, Fill, MarketTrade, OpenOrder, Order, Tick
from tests.conftest import PRICES


def write_bot(tmp_path, body):
    path = tmp_path / "bot.py"
    path.write_text(textwrap.dedent(body))
    return path


def test_load_day_builds_sorted_books_trades_and_marks(data_dir):
    day = prosperity.load_day(data_dir, 1, 0)
    assert day.name == "r1d0"
    assert day.products == ["KELP", "RAINFOREST_RESIN"]
    assert day.limits == {"KELP": 50, "RAINFOREST_RESIN": 50}
    first = day.ticks[0]
    assert first.books["KELP"] == Book(bids=((2028, 1), (2026, 20)), asks=((2032, 20),))
    assert first.books["RAINFOREST_RESIN"].asks == ()
    assert first.marks["RAINFOREST_RESIN"] == 9998.0
    assert day.ticks[1].trades["KELP"] == [MarketTrade("KELP", 2030, 3, "Olivia", "", 100)]


def test_day_specs(data_dir):
    assert prosperity.parse_day_specs(["1"], data_dir) == [(1, -1), (1, 0)]
    assert prosperity.parse_day_specs(["1--1", "1"], data_dir) == [(1, -1), (1, 0)]
    with pytest.raises(ValueError, match="no data"):
        prosperity.parse_day_specs(["2"], data_dir)
    with pytest.raises(ValueError, match="bad day"):
        prosperity.parse_day_specs(["one"], data_dir)


def test_unknown_product_needs_a_limit(data_dir):
    path = data_dir / "round1" / "prices_round_1_day_0.csv"
    path.write_text(PRICES.replace("KELP", "MYSTERY"))
    with pytest.raises(ValueError, match="MYSTERY"):
        prosperity.load_day(data_dir, 1, 0)


def test_an_empty_book_has_no_mark(data_dir):
    path = data_dir / "round1" / "prices_round_1_day_0.csv"
    path.write_text(path.read_text() + "0;200;KELP;;;;;;;;;;;;;0.0;0.0\n")
    day = prosperity.load_day(data_dir, 1, 0)
    tick = next(tick for tick in day.ticks if tick.timestamp == 200)
    assert tick.books["KELP"] == Book()
    assert "KELP" not in tick.marks


@pytest.mark.parametrize("alias", sorted(prosperity.DATA_DIRS))
def test_every_product_in_the_cloned_data_has_a_limit(alias):
    data_dir = prosperity.DATA_DIRS[alias]
    if not data_dir.is_dir():
        pytest.skip(f"{alias} data missing: run references/clone.sh")
    products = set()
    for path in data_dir.glob("round*/prices_round_*_day_*.csv"):
        with path.open() as file:
            next(file)
            products |= {line.split(";", 3)[2] for line in file}
    assert products
    assert sorted(products - set(prosperity.LIMITS)) == []


def test_bot_gets_a_prosperity_state_and_its_orders_are_converted(tmp_path):
    path = write_bot(
        tmp_path,
        """
        from datamodel import Order

        class Trader:
            def run(self, state):
                depth = state.order_depths["X"]
                assert depth.buy_orders == {99: 4} and depth.sell_orders == {101: -6}
                assert state.position == {"X": 3}
                assert [(t.price, t.quantity, t.buyer) for t in state.own_trades["X"]] == [(101, 3, "SUBMISSION")]
                assert [(t.price, t.quantity) for t in state.market_trades["X"]] == [(100, 2)]
                return {"X": [Order("X", 100, -1)]}, 0, state.traderData + "!"
        """,
    )
    bot = prosperity.load_bot(path, {}, strict=True)
    tick = Tick(100, {"X": Book(bids=((99, 4),), asks=((101, 6),))}, {}, {})
    own_fills = [Fill(0, "X", 101, 3, "book")]
    market_trades = {"X": [MarketTrade("X", 100, 2, timestamp=0)]}
    orders = bot.step(tick, {"X": 3}, own_fills, market_trades, [])
    assert [(o.product, o.price, o.quantity) for o in orders] == [("X", 100, -1)]
    bot.step(tick, {"X": 3}, own_fills, market_trades, [])
    assert bot.max_state_chars == 2


def test_resting_extensions_open_orders_cancels_and_ioc(tmp_path):
    path = write_bot(
        tmp_path,
        """
        from datamodel import Cancel, Order

        class Trader:
            def run(self, state):
                (order,) = state.open_orders["X"]
                assert (order.id, order.price, order.quantity, order.timestamp) == (4, 100, -2, 0)
                return {"X": [Cancel(order.id), Order("X", 101, -2, ioc=True)]}, 0, ""
        """,
    )
    bot = prosperity.load_bot(path, {}, strict=True)
    tick = Tick(100, {"X": Book(bids=((99, 4),), asks=((101, 6),))}, {}, {})
    actions = bot.step(tick, {}, [], {}, [OpenOrder(4, "X", 100, -2, 0)])
    assert actions == [Cancel(4), Order("X", 101, -2, ioc=True)]


@pytest.mark.parametrize(
    "returned, error",
    [
        ('{"X": [Order("X", 100.5, 1)]}, 0, ""', TypeError),
        ('{"X": [Order("Y", 100, 1)]}, 0, ""', ValueError),
        ('{"X": []}, 0, None', TypeError),
        ('{"X": []}', TypeError),
    ],
)
def test_malformed_output_raises(tmp_path, returned, error):
    path = write_bot(
        tmp_path,
        f"""
        from datamodel import Order

        class Trader:
            def run(self, state):
                return {returned}
        """,
    )
    bot = prosperity.load_bot(path, {}, strict=True)
    with pytest.raises(error):
        bot.step(Tick(0, {"X": Book()}, {}, {}), {}, [], {}, [])


def test_fresh_each_tick_forgets_instance_state(tmp_path):
    path = write_bot(
        tmp_path,
        """
        class Trader:
            calls = 0

            def run(self, state):
                Trader.calls += 1
                return {}, 0, str(Trader.calls)
        """,
    )
    tick = Tick(0, {}, {}, {})
    kept = prosperity.load_bot(path, {}, strict=True)
    fresh = prosperity.load_bot(path, {}, strict=True, fresh_each_tick=True)
    for bot in (kept, fresh):
        bot.step(tick, {}, [], {}, [])
        bot.step(tick, {}, [], {}, [])
    assert kept._trader_data == "2"
    assert fresh._trader_data == "1"


def test_overrides_and_strict_flag(tmp_path):
    path = write_bot(
        tmp_path,
        """
        STRICT = False
        PARAMS = {"X": {"edge": 1}}

        class Trader:
            def run(self, state):
                return {}, 0, f"{STRICT} {PARAMS['X']}"
        """,
    )
    overrides = dict([parse_override("PARAMS.X.edge=2"), parse_override("PARAMS.X.mode=wall")])
    bot = prosperity.load_bot(path, overrides, strict=True)
    bot.step(Tick(0, {}, {}, {}), {}, [], {}, [])
    assert bot._trader_data == "True {'edge': 2, 'mode': 'wall'}"

    with pytest.raises(OverrideError, match="no global"):
        prosperity.load_bot(path, dict([parse_override("PARAM.X.edge=2")]), strict=True)
    with pytest.raises(ValueError, match="PATH=VALUE"):
        parse_override("PARAMS.X.edge")
    with pytest.raises(ValueError, match="not a Python literal"):
        parse_override("PARAMS.X={'take_edge': 10**6}")  # an expression would otherwise arrive as a string


def test_an_override_never_changes_the_value_it_was_given(tmp_path):
    # The grid adds each combination's values to the same --set dicts, load after load.
    path = write_bot(
        tmp_path,
        """
        PARAMS = {}

        class Trader:
            def run(self, state):
                return {}, 0, str(PARAMS)
        """,
    )
    whole = parse_override("PARAMS.X={'edge': 1}")
    prosperity.load_bot(path, dict([whole, parse_override("PARAMS.X.edge=2")]), strict=True)
    bot = prosperity.load_bot(path, dict([whole]), strict=True)
    bot.step(Tick(0, {}, {}, {}), {}, [], {}, [])
    assert bot._trader_data == "{'X': {'edge': 1}}"


def test_check_source():
    import ast

    assert prosperity.check_source(ast.parse("class Trader:\n    def run(self, state): pass")) == []
    assert prosperity.check_source(ast.parse("class Trader:\n    pass")) == ["class Trader has no run method"]
    assert prosperity.check_source(ast.parse("x = 1")) == ["no top-level class Trader"]


def test_set_paths_must_go_through_dicts(tmp_path):
    path = write_bot(
        tmp_path,
        """
        PARAMS = {"X": {"edge": 1}, "a": {"a": 0}}

        class Trader:
            def run(self, state):
                return {}, 0, str(PARAMS["a"])
        """,
    )
    with pytest.raises(OverrideError, match="PARAMS.X.edge is not a dict"):
        prosperity.load_bot(path, dict([parse_override("PARAMS.X.edge.y=2")]), strict=True)
    bot = prosperity.load_bot(path, dict([parse_override("PARAMS.a.a=5")]), strict=True)  # a key repeated
    bot.step(Tick(0, {}, {}, {}), {}, [], {}, [])
    assert bot._trader_data == "{'a': 5}"
