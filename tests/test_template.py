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


def test_outer_and_sized_mids(bot):
    # A rival's large bid far below the market maker's 20-lot wall at 96.
    book = bot.Book([[99, 2], [96, 20], [80, 40]], [[102, 2], [104, 20]])
    fair = lambda **kw: bot.fair_value(book, params(bot, **kw), {})
    assert fair(fair="wall_mid") == 92  # (80 + 104) / 2: the largest level is the rival's
    assert fair(fair="outer_mid") == 92  # the outermost level is the rival's too
    assert fair(fair="sized_mid", wall_size=15) == 100  # (96 + 104) / 2: stops at the first 15+
    assert fair(fair="sized_mid", wall_size=50) == 100.5  # nothing that large: the best levels


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


def test_level_target_holds_the_full_limit_until_the_other_band(bot):
    p = params(bot, level=100, level_band=5)
    memory = {}
    targets = [bot.level_target(fair, p, memory) for fair in (102, 106, 101, 96, 94, 100, 104)]
    assert targets == [0, -10, -10, -10, 10, 10, 10]


def test_level_exit_flattens_near_the_level(bot):
    p = params(bot, level=100, level_band=5, level_exit=1)
    memory = {}
    targets = [bot.level_target(fair, p, memory) for fair in (106, 103, 100.5, 103, 94)]
    assert targets == [-10, -10, 0, 0, 10]  # flat from the level until a band is reached again


def test_the_level_from_the_day_or_blended_with_it(bot):
    memory = {}
    assert [bot.estimate_level(f, params(bot, level="day"), memory) for f in (100, 104)] == [100, 102]
    memory = {}
    blend = params(bot, level=100, level_weight=2)  # the 100 counts as two ticks of the day's mean
    assert [bot.estimate_level(f, blend, memory) for f in (106, 106)] == [102, 103]
    assert bot.estimate_level(106, params(bot, level=100), {}) == 100  # no weight: it never moves


def test_a_price_far_above_the_level_sells_toward_a_short_target(bot):
    book = bot.Book([[109, 4], [108, 9]], [[111, 4]])
    p = params(bot, fair="wall_mid", level=100, level_band=5, clear_edge=2)
    plan = bot.trade_product(book, 0, p, {})
    assert plan.takes == [(109, -4), (108, -6)]  # wall mid 109.5: sells down to -10 within 2 of it


def test_black_scholes_in_total_variance(bot):
    # S = K = 100, sigma 0.2 for a year: w = 0.04, the textbook at-the-money call of 7.97.
    assert bot.call_price(100, 100, 0.04) == pytest.approx(7.9656, abs=1e-4)
    assert bot.call_delta(100, 100, 0.04) == pytest.approx(0.5398, abs=1e-4)
    assert bot.implied_variance(bot.call_price(105, 100, 0.01), 105, 100) == pytest.approx(0.01, rel=1e-6)
    assert bot.implied_variance(5, 105, 100) == 0  # no time value: delta 1
    assert bot.call_delta(105, 100, 0) == 1 and bot.call_delta(95, 100, 0) == 0


def test_a_call_follows_the_underlyings_target_as_a_share_of_its_limit(bot):
    underlying = bot.Plan(position=0, limit=200)
    underlying.fair, underlying.target = 100.0, -200
    book = bot.Book([[7, 50]], [[8, 50]])  # a call struck at 100 worth 7.5: delta about 0.5
    p = params(bot, limit=300, follow="U", strike=100, max_cost_per_delta=5)
    memory = {}
    assert bot.follow_target(book, 7.5, p, memory, underlying) == -300
    assert bot.follow_target(book, 7.5, p, memory, None) == -300  # underlying missing: keeps its target
    wide = bot.Book([[3, 50]], [[12, 50]])  # half the spread is 4.5: 9 a unit of delta
    assert bot.follow_target(wide, 7.5, p, {}, underlying) == 0


def test_followers_trade_after_the_product_they_follow(bot, monkeypatch):
    monkeypatch.setattr(bot, "PARAMS", {
        "C": {"limit": 10, "fair": "mid", "follow": "U", "strike": 100, "clear_edge": 5, "make_size": 0},
        "U": {"limit": 10, "fair": "mid", "level": 90, "level_band": 5, "clear_edge": 1},
    })
    depths = {"C": depth([(10, 20)], [(12, 20)]), "U": depth([(109, 20)], [(111, 20)])}
    orders, _, _ = bot.Trader().run(state(depths))
    # U is 20 above its level: both go short, and C sells into its bid within clear_edge.
    assert [(o.price, o.quantity) for o in orders["C"]] == [(10, -10)]
    assert [(o.price, o.quantity) for o in orders["U"] if o.quantity < 0][0] == (109, -10)


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


def test_size_skew_shrinks_the_quote_that_adds_to_the_gap(bot):
    book = bot.Book([[90, 5]], [[110, 5]])
    plan = bot.Plan(position=5, limit=10)  # long half the limit
    bot.make(book, 100, params(bot, make_edge=2, make_size=4, size_skew=1), plan)
    assert plan.quotes == [(91, 2), (109, -6)]  # bid 4 x 0.5, ask 4 x 1.5
    plan = bot.Plan(position=-5, limit=10)  # short: the bid grows but stays within the room
    bot.make(book, 100, params(bot, make_edge=2, size_skew=1), plan)
    assert plan.quotes == [(91, 15), (109, -2)]  # ask: room 5 x 0.5
    plan = bot.Plan(position=6, limit=10)  # at target: sizes unchanged
    bot.make(book, 100, params(bot, make_edge=2, make_size=4, size_skew=3, target=6), plan)
    assert plan.quotes == [(91, 4), (109, -4)]
    plan = bot.Plan(position=5, limit=10)  # a factor below zero quotes nothing on that side
    bot.make(book, 100, params(bot, make_edge=2, make_size=4, size_skew=3), plan)
    assert plan.quotes == [(109, -10)]


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
