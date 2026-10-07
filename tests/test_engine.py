import pytest

from arena.engine import EngineConfig, TradeMatching, run_day
from arena.model import Book, Day, Fill, MarketTrade, Order, Tick


class ScriptedBot:
    """Sends preset orders per timestamp and records what the engine showed it."""

    def __init__(self, script=None, error_at=None):
        self.script = script or {}
        self.error_at = error_at
        self.seen = []

    def step(self, tick, positions, own_fills, market_trades):
        self.seen.append((positions, own_fills, market_trades))
        if tick.timestamp == self.error_at:
            raise RuntimeError("boom")
        return self.script.get(tick.timestamp, [])


def tick(timestamp, bids=(), asks=(), trades=(), mark=None, product="X"):
    return Tick(
        timestamp,
        {product: Book(tuple(bids), tuple(asks))},
        {product: list(trades)} if trades else {},
        {product: mark} if mark is not None else {},
    )


def day(*ticks, limits=None):
    limits = limits or {"X": 10}
    return Day("test", sorted(limits), limits, list(ticks))


def fills(result):
    return [(f.price, f.quantity, f.source) for f in result.fills]


def test_buy_walks_the_book_at_the_book_prices():
    d = day(tick(0, asks=[(101, 2), (102, 5), (103, 9)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 102, 4)]}))
    assert fills(result) == [(101, 2, "book"), (102, 2, "book")]


def test_sell_walks_the_bids_best_first():
    d = day(tick(0, bids=[(99, 1), (98, 5)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 98, -3)]}))
    assert fills(result) == [(99, -1, "book"), (98, -2, "book")]


def test_orders_in_one_tick_share_the_book():
    d = day(tick(0, asks=[(101, 3)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 101, 2), Order("X", 101, 2)]}))
    assert fills(result) == [(101, 2, "book"), (101, 1, "book")]


def test_leftover_fills_against_market_trades_at_the_order_price():
    trade = MarketTrade("X", 99, 5, buyer="B", seller="S")
    d = day(tick(0, asks=[(105, 10)], trades=[trade]))
    result = run_day(d, ScriptedBot({0: [Order("X", 100, 3)]}))
    assert result.fills == [Fill(0, "X", 100, 3, "trade", "S")]


@pytest.mark.parametrize(
    "matching, filled", [(TradeMatching.ALL, 3), (TradeMatching.WORSE, 0), (TradeMatching.NONE, 0)]
)
def test_trade_matching_at_the_same_price(matching, filled):
    d = day(tick(0, trades=[MarketTrade("X", 100, 5)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 100, 3)]}), EngineConfig(trade_matching=matching))
    assert sum(f.quantity for f in result.fills) == filled


def test_market_trade_volume_is_used_up():
    d = day(tick(0, trades=[MarketTrade("X", 99, 4)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 100, 3), Order("X", 100, 3)]}))
    assert [f.quantity for f in result.fills] == [3, 1]


def test_orders_never_rest_into_the_next_tick():
    d = day(tick(0, asks=[(105, 5)]), tick(1, asks=[(100, 5)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 100, 3)]}))
    assert result.fills == []


def test_possible_limit_breach_cancels_every_order_for_that_product():
    d = day(tick(0, asks=[(101, 20)]), limits={"X": 10})
    # Each buy alone fits, but both together could take the position to 12.
    result = run_day(d, ScriptedBot({0: [Order("X", 101, 6), Order("X", 90, 6)]}))
    assert result.fills == []
    assert result.limit_breaches == [(0, "X")]


def test_breach_on_one_product_leaves_others_trading():
    d = Day(
        "test",
        ["X", "Y"],
        {"X": 1, "Y": 1},
        [Tick(0, {"X": Book(asks=((10, 5),)), "Y": Book(asks=((20, 5),))}, {}, {})],
    )
    result = run_day(d, ScriptedBot({0: [Order("X", 10, 2), Order("Y", 20, 1)]}))
    assert [(f.product, f.quantity) for f in result.fills] == [("Y", 1)]


def test_pnl_values_position_at_the_mark():
    d = day(tick(0, asks=[(101, 5)], mark=100), tick(1, mark=104))
    result = run_day(d, ScriptedBot({0: [Order("X", 101, 2)]}))
    assert result.positions["X"] == [2, 2]
    assert result.pnl["X"] == [-2, 6]


def test_mark_falls_back_to_the_book_mid():
    d = day(tick(0, bids=[(98, 1)], asks=[(101, 5)]), tick(1))
    result = run_day(d, ScriptedBot({0: [Order("X", 101, 1)]}))
    assert result.marks["X"] == [99.5, 99.5]


def test_bot_errors_are_recorded_and_the_run_continues():
    d = day(tick(0, asks=[(101, 5)]), tick(1, asks=[(101, 5)]))
    result = run_day(d, ScriptedBot({1: [Order("X", 101, 1)]}, error_at=0))
    assert len(result.errors) == 1 and "boom" in result.errors[0][1]
    assert len(result.fills) == 1


def test_orders_for_unknown_products_are_errors():
    d = day(tick(0, asks=[(101, 5)]))
    result = run_day(d, ScriptedBot({0: [Order("NOPE", 101, 1)]}))
    assert result.fills == [] and "NOPE" in result.errors[0][1]


def test_bot_sees_its_fills_and_the_leftover_market_trades_next_tick():
    d = day(tick(0, trades=[MarketTrade("X", 99, 5, timestamp=0)]), tick(1))
    bot = ScriptedBot({0: [Order("X", 100, 2)]})
    run_day(d, bot)
    positions, own_fills, market_trades = bot.seen[1]
    assert positions == {"X": 2}
    assert own_fills == [Fill(0, "X", 100, 2, "trade", "")]
    assert [t.quantity for t in market_trades["X"]] == [3]


def test_fill_ratio_zero_blocks_every_fill():
    d = day(tick(0, asks=[(101, 5)], trades=[MarketTrade("X", 99, 5)]))
    result = run_day(d, ScriptedBot({0: [Order("X", 101, 5)]}), EngineConfig(fill_ratio=0.0))
    assert result.fills == []


def test_fill_ratio_draws_repeat_with_the_same_seed():
    ticks = [tick(t, asks=[(101, 50)]) for t in range(50)]
    script = {t: [Order("X", 101, 1)] for t in range(50)}
    config = EngineConfig(fill_ratio=0.5, seed=7)
    first = run_day(day(*ticks, limits={"X": 100}), ScriptedBot(script), config)
    second = run_day(day(*ticks, limits={"X": 100}), ScriptedBot(script), config)
    assert first.fills == second.fills
    assert 0 < len(first.fills) <= 50
