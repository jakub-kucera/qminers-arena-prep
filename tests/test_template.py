import json
from pathlib import Path

import pytest

from arena.botfile import BotFile
from arena.formats import prosperity_datamodel as dm

TEMPLATE = Path(__file__).parents[1] / "bots" / "template.py"


@pytest.fixture
def bot():
    return BotFile(TEMPLATE, {"datamodel": dm}, strict=True).load()


def params(bot, **overrides):
    return {**bot.DEFAULTS, "limit": 10, **overrides}


def state(depths, trader_data="", position=None):
    return dm.TradingState(trader_data, 0, {}, depths, {}, {}, position or {}, dm.Observation({}, {}))


def depth(bids, asks):
    d = dm.OrderDepth()
    d.buy_orders = dict(bids)
    d.sell_orders = {price: -volume for price, volume in asks}
    return d


def test_wall_mid_uses_the_largest_level_on_each_side(bot):
    book = bot.Book([[99, 1], [98, 20]], [[101, 2], [103, 20]])
    assert bot.fair_value(book, params(bot, fair="wall_mid"), {}) == 100.5


def test_fair_keeps_its_last_value_when_a_side_is_empty(bot):
    assert bot.fair_value(bot.Book([[99, 1]], []), params(bot, fair="mid"), {"fair": 100.0}) == 100.0


def test_smoothing_blends_with_the_previous_fair(bot):
    book = bot.Book([[109, 1]], [[111, 1]])
    assert bot.fair_value(book, params(bot, fair="mid", smoothing=0.5), {"fair": 100.0}) == 105.0


def test_take_buys_cheap_asks_up_to_the_room_left(bot):
    book = bot.Book([], [[97, 4], [99, 8], [100, 5]])
    plan = bot.Plan(position=5, limit=10)
    bot.take(book, 100, params(bot, take_edge=1), plan)
    assert plan.orders == [(97, 4), (99, 1)]
    assert book.asks == [[97, 0], [99, 7], [100, 5]]


def test_clear_cuts_inventory_at_fair(bot):
    book = bot.Book([[100, 3], [99, 5]], [])
    plan = bot.Plan(position=2, limit=10)
    bot.clear(book, 100, params(bot, clear_edge=0), plan)
    assert plan.orders == [(100, -2)]


def test_make_steps_inside_a_wide_book(bot):
    plan = bot.Plan(0, 10)
    bot.make(bot.Book([[95, 5]], [[105, 5]]), 100, params(bot, make_edge=2), plan)
    assert plan.orders == [(96, 10), (104, -10)]


def test_make_keeps_its_edge_in_a_tight_book(bot):
    plan = bot.Plan(0, 10)
    bot.make(bot.Book([[99, 5]], [[101, 5]]), 100, params(bot, make_edge=2), plan)
    assert plan.orders == [(98, 10), (102, -10)]


def test_skew_moves_quotes_against_inventory(bot):
    plan = bot.Plan(10, 10)  # long at the limit: no room to buy, room to sell 20
    bot.make(bot.Book([[90, 5]], [[110, 5]]), 100, params(bot, make_edge=2, skew=4), plan)
    assert plan.orders == [(105, -20)]  # one inside the 110 ask, moved down 4


def test_skew_never_crosses_the_book(bot):
    plan = bot.Plan(-10, 10)  # short at the limit: quotes move up
    bot.make(bot.Book([[99, 5]], [[101, 5]]), 100, params(bot, make_edge=1, skew=5), plan)
    assert plan.orders == [(100, 20)]  # would be 104, capped one below the 101 ask


def test_unknown_params_are_rejected(bot):
    bot.PARAMS["KELP"] = {"make_egde": 1}
    with pytest.raises(ValueError, match="make_egde"):
        bot.params_for("KELP")


def test_trader_trades_listed_products_and_keeps_memory_in_trader_data(bot):
    depths = {"KELP": depth([(2029, 25)], [(2031, 25)]), "UNLISTED": depth([(9, 1)], [(11, 1)])}
    orders, conversions, trader_data = bot.Trader().run(state(depths))
    assert set(orders) == {"KELP"} and conversions == 0
    assert json.loads(trader_data)["KELP"]["fair"] == 2030
    assert all(isinstance(o.price, int) and isinstance(o.quantity, int) for o in orders["KELP"])


def test_one_broken_product_doesnt_stop_the_others(capsys):
    lenient = BotFile(TEMPLATE, {"datamodel": dm}, strict=False).load()
    lenient.PARAMS["KELP"]["fair"] = "bogus"
    depths = {"KELP": depth([(2029, 25)], [(2031, 25)]), "RAINFOREST_RESIN": depth([(9996, 2)], [(10004, 2)])}
    orders, _, _ = lenient.Trader().run(state(depths))
    assert set(orders) == {"RAINFOREST_RESIN"}
    assert "bogus" in capsys.readouterr().out
