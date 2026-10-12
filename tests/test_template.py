import json
from pathlib import Path

import pytest

from arena.botfile import BotFile
from arena.engine import EngineConfig, run_day
from arena.formats import prosperity
from arena.formats import prosperity_datamodel as dm

TEMPLATE = Path(__file__).parents[1] / "bots" / "template.py"


@pytest.fixture
def bot():
    return BotFile(TEMPLATE, {"datamodel": dm}, strict=True).load()


def params(bot, **overrides):
    return {**bot.DEFAULTS, "limit": 10, **overrides}


def state(depths, trader_data="", position=None, open_orders=None):
    return dm.TradingState(
        trader_data, 0, {}, depths, {}, {}, position or {}, dm.Observation({}, {}), open_orders or {}
    )


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
    assert plan.takes == [(97, 4), (99, 1)]
    assert book.asks == [[97, 0], [99, 7], [100, 5]]


def test_clear_cuts_inventory_at_fair(bot):
    book = bot.Book([[100, 3], [99, 5]], [])
    plan = bot.Plan(position=2, limit=10)
    bot.clear(book, 100, params(bot, clear_edge=0), plan)
    assert plan.takes == [(100, -2)]


def test_clear_and_skew_work_toward_the_target(bot):
    book = bot.Book([[100, 3]], [[100, 9], [101, 9]])
    plan = bot.Plan(position=2, limit=10)
    bot.clear(book, 100, params(bot, clear_edge=0, target=6), plan)
    assert plan.takes == [(100, 4)]  # buys up to the target at fair, not down to zero
    plan = bot.Plan(position=6, limit=10)  # at target: no skew
    bot.make(bot.Book([[90, 5]], [[110, 5]]), 100, params(bot, make_edge=2, skew=4, target=6), plan)
    assert plan.quotes == [(91, 4), (109, -16)]  # one inside the 90/110 book
    plan = bot.Plan(position=-4, limit=10)  # a full limit below target: quotes move up 4
    bot.make(bot.Book([[90, 5]], [[110, 5]]), 100, params(bot, make_edge=2, skew=4, target=6), plan)
    assert plan.quotes == [(95, 14), (113, -6)]


def test_make_steps_inside_a_wide_book(bot):
    plan = bot.Plan(0, 10)
    bot.make(bot.Book([[95, 5]], [[105, 5]]), 100, params(bot, make_edge=2), plan)
    assert plan.quotes == [(96, 10), (104, -10)]


def test_make_keeps_its_edge_in_a_tight_book(bot):
    plan = bot.Plan(0, 10)
    bot.make(bot.Book([[99, 5]], [[101, 5]]), 100, params(bot, make_edge=2), plan)
    assert plan.quotes == [(98, 10), (102, -10)]


def test_skew_moves_quotes_against_inventory(bot):
    plan = bot.Plan(10, 10)  # long at the limit: no room to buy, room to sell 20
    bot.make(bot.Book([[90, 5]], [[110, 5]]), 100, params(bot, make_edge=2, skew=4), plan)
    assert plan.quotes == [(105, -20)]  # one inside the 110 ask, moved down 4


def test_skew_never_crosses_the_book(bot):
    plan = bot.Plan(-10, 10)  # short at the limit: quotes move up
    bot.make(bot.Book([[99, 5]], [[101, 5]]), 100, params(bot, make_edge=1, skew=5), plan)
    assert plan.quotes == [(100, 20)]  # would be 104, capped one below the 101 ask


def plan_with(bot, takes=(), quotes=()):
    plan = bot.Plan(0, 10)
    plan.takes, plan.quotes = list(takes), list(quotes)
    return plan


def test_execute_sends_everything_when_nothing_rests(bot):
    cancels, orders = bot.execute(plan_with(bot, takes=[(97, 4)], quotes=[(98, 6), (102, -10)]), [])
    assert cancels == []
    assert orders == [(97, 4, True), (98, 6, False), (102, -10, False)]


def test_execute_keeps_quotes_that_havent_moved_and_tops_them_up(bot):
    resting = [(1, 98, 4), (2, 103, -10)]  # the bid was partly filled, the ask is now 102
    cancels, orders = bot.execute(plan_with(bot, quotes=[(98, 6), (102, -10)]), resting)
    assert cancels == [2]
    assert orders == [(98, 2, False), (102, -10, False)]


def test_execute_replaces_a_resting_order_larger_than_its_quote(bot):
    # Keeping 8 when the plan wants 5 could breach the limit, so it goes to the back of the queue.
    cancels, orders = bot.execute(plan_with(bot, quotes=[(98, 5)]), [(1, 98, 8)])
    assert cancels == [1] and orders == [(98, 5, False)]


def test_execute_tells_a_bid_and_an_ask_at_one_price_apart(bot):
    cancels, orders = bot.execute(plan_with(bot, quotes=[(100, 3), (100, -3)]), [(1, 100, -3)])
    assert cancels == [] and orders == [(100, 3, False)]


def test_trader_cancels_with_ids_and_sends_takes_as_ioc(bot):
    depths = {"RAINFOREST_RESIN": depth([(9990, 5)], [(9995, 2), (10010, 5)])}
    resting = {"RAINFOREST_RESIN": [dm.OpenOrder(7, "RAINFOREST_RESIN", 9980, 3, 0)]}
    orders, _, _ = bot.Trader().run(state(depths, open_orders=resting))
    cancels = [o.order_id for o in orders["RAINFOREST_RESIN"] if isinstance(o, dm.Cancel)]
    new = [(o.price, o.quantity, o.ioc) for o in orders["RAINFOREST_RESIN"] if isinstance(o, dm.Order)]
    assert cancels == [7]
    assert new[0] == (9995, 2, True)  # took the cheap ask
    assert all(not ioc for _, _, ioc in new[1:])


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


def test_lenient_errors_cancel_the_products_resting_orders(capsys):
    lenient = BotFile(TEMPLATE, {"datamodel": dm}, strict=False).load()
    lenient.PARAMS["KELP"]["fair"] = "bogus"
    resting = {"KELP": [dm.OpenOrder(3, "KELP", 2029, 5, 0)]}
    orders, _, _ = lenient.Trader().run(state({"KELP": depth([(2029, 25)], [(2031, 25)])}, open_orders=resting))
    assert [o.order_id for o in orders["KELP"]] == [3]


@pytest.mark.parametrize("resting", [False, True])
def test_template_runs_cleanly_in_both_modes(data_dir, resting):
    days = prosperity.load_days(data_dir, ["1"])
    for day in days:
        result = run_day(day, prosperity.load_bot(TEMPLATE, {}, strict=True), EngineConfig(resting=resting))
        assert result.errors == [] and result.limit_breaches == []
