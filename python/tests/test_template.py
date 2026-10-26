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


def test_weighted_mid_leans_toward_the_thinner_side(bot):
    # 30 bid against 10 offered: I = 0.75, so 0.75 * 101 + 0.25 * 99.
    book = bot.Book([[99, 30], [97, 5]], [[101, 10]])
    assert bot.fair_value(book, params(bot, fair="weighted_mid"), {}) == 100.5
    assert bot.imbalance(book) == 0.5


def test_imbalance_moves_the_quotes_but_not_the_fair_value(bot):
    book = bot.Book([[96, 30]], [[104, 10]])  # wall mid 100, rho 0.5
    plain = bot.trade_product("X", book, 0, params(bot, fair="wall_mid"), {})
    tilted = bot.trade_product("X", book, 0, params(bot, fair="wall_mid", imbalance=4), {})
    assert plain.fair == tilted.fair == 100
    assert plain.quotes == [(97, 10), (103, -10)]  # one tick inside the walls, 3 from fair
    # Quoted around 100 + 4 * 0.5 = 102: the bid still steps in front of the wall, the ask can't
    # come within make_edge of 102, so it joins the wall at 104.
    assert tilted.quotes == [(97, 10), (104, -10)]


def test_an_untuned_product_quotes_around_the_market_makers_size(bot):
    # The default is sized_mid: a small order inside the walls doesn't move the fair value, and a
    # book with no level of wall_size falls back to the mid.
    walls = bot.Book([[101, 2], [98, 20]], [[104, 20]])
    assert bot.fair_value(walls, params(bot), {}) == 101.0
    assert bot.fair_value(bot.Book([[101, 2]], [[104, 3]]), params(bot), {}) == 102.5


def test_a_fixed_fair_gives_way_once_the_market_leaves_it(bot):
    p = params(bot, fair="fixed", fixed_fair=100, fixed_guard=5)
    assert bot.fair_value(bot.Book([[98, 20]], [[102, 20]]), p, {}) == 100
    assert bot.fair_value(bot.Book([[108, 20]], [[112, 20]]), p, {}) == 110.0


def test_a_large_order_far_from_the_touch_doesnt_trip_the_guard(bot):
    # A spoofer's 40-lot behind the walls moves the wall mid to 93.5, past the guard; the sized
    # mid (the first level with at least wall_size) stays at 100.
    p = params(bot, fair="fixed", fixed_fair=100, fixed_guard=5)
    assert bot.fair_value(bot.Book([[98, 20], [85, 40]], [[102, 20]]), p, {}) == 100


def test_the_loss_stop_trips_on_a_drawdown_from_the_high_and_resets_next_day(bot):
    p = params(bot, stop_loss=50)
    memory = {}
    assert not bot.loss_stop(100, 10, [(100, 10)], 0, p, memory)  # bought 10 at 100
    assert not bot.loss_stop(110, 10, [], 100, p, memory)  # +100, the high
    assert bot.loss_stop(104, 10, [], 200, p, memory)  # +40: 60 below the high
    assert bot.loss_stop(120, 10, [], 300, p, memory)  # stays stopped for the day
    assert not bot.loss_stop(120, 10, [], 0, p, memory)  # a new day: the carried position starts at 0


def test_a_stopped_product_only_flattens(bot):
    p = params(bot, fair="mid", stop_loss=10, make_edge=1)
    memory = {"stopped": True, "stop_t": 0}
    book = bot.Book([[99, 5]], [[103, 5]])
    plan = bot.trade_product("X", book, 4, p, memory, bot.Market({"X": book}, timestamp=100))
    assert plan.takes == [(99, -4)] and plan.quotes == []  # crosses the spread to sell what it holds


def test_the_level_guard_waits_for_the_price_to_come_back(bot):
    p = params(bot, level=100, level_band=10, level_guard=3)
    memory = {}
    assert bot.level_target(115, p, memory) == -10
    assert bot.level_target(135, p, memory) == 0  # 3.5 bands away: the level is broken
    assert bot.level_target(125, p, memory) == 0  # back inside the guard but not within a band
    assert bot.level_target(105, p, memory) == 0  # within a band: the bet may start again
    assert bot.level_target(112, p, memory) == -10


def test_the_regime_guard_trips_when_volatility_jumps(bot):
    p = params(bot, vol_guard=3)
    memory = {}
    calm = [100 + (k % 2) for k in range(400)]
    assert not any(bot.regime_guard(f, p, memory) for f in calm)
    assert any(bot.regime_guard(100 + 20 * (k % 2), p, memory) for k in range(20))


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


def test_level_exit_flattens_when_the_price_jumps_past_the_level(bot):
    # Wall mids move in steps of 0.5 and levels are often means: the gap may never be exactly 0.
    p = params(bot, level=100.2, level_band=5, level_exit=0)
    memory = {}
    targets = [bot.level_target(fair, p, memory) for fair in (106, 100.5, 99.5, 98, 106)]
    assert targets == [-10, -10, 0, 0, -10]
    targets = [bot.level_target(fair, p, {}) for fair in (94, 100.5)]
    assert targets == [10, 0]  # long below the level: flat once back above it


def test_the_level_from_the_day_or_blended_with_it(bot):
    memory = {}
    assert [bot.estimate_level(f, params(bot, level="day"), memory) for f in (100, 104)] == [100, 102]
    memory = {}
    blend = params(bot, level=100, level_weight=2)  # the 100 counts as two ticks of the day's mean
    assert [bot.estimate_level(f, blend, memory) for f in (106, 106)] == [102, 103]
    assert bot.estimate_level(106, params(bot, level=100), {}) == 100  # no weight: it never moves


def test_jump_target_fades_jumps_once_enough_have_reversed(bot):
    p = params(bot, jump_min=50, jump_seen=2, jump_share=0.6)
    memory = {}
    fairs = (100, 200, 100, 105, 200, 100, 200)
    targets = [bot.jump_target(fair, p, memory) for fair in fairs]
    # Jumps at 200, 100, 200, 100, 200; the move to 105 is not one. From the third jump on, two
    # jumps have followed another and both reversed it: the full limit against each jump.
    assert targets == [0, 0, 0, 0, -10, 10, -10]


def test_jump_target_stays_flat_when_jumps_keep_going(bot):
    p = params(bot, jump_min=50, jump_seen=2, jump_share=0.6)
    memory = {}
    targets = [bot.jump_target(fair, p, memory) for fair in (100, 200, 300, 400, 300, 400, 500)]
    assert targets == [0] * 7  # at most half the jumps reversed the one before, under 60%


def test_jump_hold_flattens_after_that_many_ticks(bot):
    p = params(bot, jump_min=50, jump_seen=0, jump_share=0, jump_hold=2)
    memory = {}
    targets = [bot.jump_target(fair, p, memory) for fair in (100, 200, 200, 200, 100)]
    assert targets == [0, -10, -10, 0, 10]


def test_a_jump_target_crosses_up_to_jump_edge(bot):
    p = params(bot, fair="wall_mid", jump_min=50, jump_seen=0, jump_share=0, jump_edge=10, make_size=0)
    memory = {}
    bot.trade_product("X", bot.Book([[96, 10]], [[104, 10]]), 0, p, memory)
    plan = bot.trade_product("X", bot.Book([[196, 10]], [[204, 10]]), 0, p, memory)
    assert plan.takes == [(196, -10)]  # wall mid 200: sells at 4 below it, inside jump_edge
    plan = bot.trade_product("X", bot.Book([[195, 10]], [[205, 10]]), -10, p, memory)
    assert plan.takes == []  # no jump: target held, nothing to do
    flat = params(bot, fair="wall_mid", make_size=0)  # clear_edge 0 alone wouldn't cross
    assert bot.trade_product("X", bot.Book([[196, 10]], [[204, 10]]), 10, flat, {}).takes == []


def test_copy_target_trades_the_named_traders_way(bot):
    p = params(bot, copy={"Olivia": 1, "Pablo": -0.5})
    memory = {}
    assert bot.copy_target([("Caesar", "Paris", 5)], p, memory) == 0  # no name in copy: no signal
    assert bot.copy_target([("Olivia", "Paris", 15)], p, memory) == 10  # she buys: the full limit long
    assert bot.copy_target([], p, memory) == 10  # held until the next signal
    assert bot.copy_target([("Pablo", "Caesar", 3)], p, memory) == -5  # against Pablo, at his weight
    assert bot.copy_target([("Pablo", "Olivia", 3)], p, memory) == -10  # both say sell: capped at the limit


def test_copy_hold_flattens_after_that_many_ticks(bot):
    p = params(bot, copy={"Olivia": 1}, copy_hold=2)
    memory = {}
    targets = [bot.copy_target(trades, p, memory) for trades in ([("Paris", "Olivia", 1)], [], [], [])]
    assert targets == [-10, -10, 0, 0]


def test_copy_reads_the_counterparty_of_our_own_fills(bot, monkeypatch):
    # When our order fills against her trade, it leaves the market trades and is only in own_trades.
    monkeypatch.setattr(bot, "PARAMS", {"X": {"limit": 10, "fair": "fixed", "fixed_fair": 100, "copy": {"Olivia": 1}, "make_size": 0}})
    depths = {"X": depth([(99, 20)], [(101, 20)])}
    own = {"X": [dm.Trade("X", 101, 2, "Olivia", "SUBMISSION")]}
    s = dm.TradingState("", 0, {}, depths, own, {}, {"X": -2}, dm.Observation({}, {}))
    orders, _, _ = bot.Trader().run(s)
    assert [(o.price, o.quantity) for o in orders["X"]] == [(101, 12)]  # she bought from us: go long


def test_a_price_far_above_the_level_sells_toward_a_short_target(bot):
    book = bot.Book([[109, 4], [108, 9]], [[111, 4]])
    p = params(bot, fair="wall_mid", level=100, level_band=5, clear_edge=2)
    plan = bot.trade_product("X", book, 0, p, {})
    assert plan.takes == [(109, -4), (108, -6)]  # wall mid 109.5: sells down to -10 within 2 of it


def test_a_basket_prices_its_legs_from_the_books_as_sent(bot):
    # The leg trades first and takes its 30-lot wall; the basket must still see the wall at 101.
    leg_p = params(bot, limit=250, fair="fixed", fixed_fair=100)
    basket_p = params(bot, limit=100, fair="wall_mid", basket={"LEG": 4}, level=0, level_band=1000, make_size=0)
    market = bot.Market({"LEG": bot.Book([[101, 30], [100, 5]], [[103, 10]]), "BASKET": bot.Book([[399, 20]], [[401, 20]])})
    market.plans["LEG"] = bot.trade_product("LEG", market.books["LEG"], 0, leg_p, {}, market)
    assert market.plans["LEG"].takes == [(101, -30)]
    assert market.books["LEG"].bids == [[101, 30], [100, 5]]  # untouched
    memory = {}
    bot.trade_product("BASKET", market.books["BASKET"], 0, basket_p, memory, market)
    assert memory["level_sum"] == 400 - 4 * 102  # the spread against the leg's wall mid of 102


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



def test_a_smile_call_is_priced_off_its_underlying_plus_its_usual_offset(bot):
    import math
    # S = K = 100 at one year (expiry 365 days, timestamp 0): m = 0, so the smile gives c = 0.2,
    # w = 0.04 and Black-Scholes 7.9656. The call's own mid is 9: its offset starts at 1.0344.
    p = params(bot, fair="mid", smile=(1.0, 0.5, 0.2), underlying="U", strike=100, expiry=365, smile_window=3, hedge_ratio=1)
    market, memory = bot.Market({"U": bot.Book([[99, 5]], [[101, 5]])}), {}
    book = bot.Book([[8, 5]], [[10, 5]])
    assert bot.smile_fair(book, p, memory, market) == pytest.approx(9.0)  # the first tick: model plus its own offset
    assert memory["delta"] == pytest.approx(0.5398, abs=1e-4)
    # The underlying moves to 110 and the call doesn't: the fair follows the model with the old
    # offset, then the offset moves halfway (EMA over 3 ticks) toward the new one.
    market.books["U"] = bot.Book([[109, 5]], [[111, 5]])
    m = math.log(100 / 110)
    model = bot.call_price(110, 100, (m * m + 0.5 * m + 0.2) ** 2)
    assert bot.smile_fair(book, p, memory, market) == pytest.approx(model + 1.0344, abs=1e-4)
    assert memory["offset"] == pytest.approx((1.0344 + 9 - model) / 2, abs=1e-4)
    del market.books["U"]  # no underlying price: keep the last fair
    assert bot.smile_fair(book, p, memory, market) == pytest.approx(model + 1.0344, abs=1e-4)
    # trade_product asks the underlying for minus delta times the position held.
    plan = bot.trade_product("C", book, 4, p, memory, bot.Market({"U": bot.Book([[109, 5]], [[111, 5]])}))
    assert plan.legs == {"U": pytest.approx(-4 * memory["delta"])}

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


def test_a_basket_trades_its_spread_as_a_level_and_asks_its_legs_to_hedge(bot):
    market = bot.Market({"A": bot.Book([[49, 5]], [[51, 5]]), "B": bot.Book([[1, 5]], [[3, 5]])})
    p = params(bot, fair="mid", basket={"A": 2, "B": 1}, level=10, level_band=5, hedge_ratio=0.5)
    plan, memory = bot.Plan(0, 10), {}
    # spread = 120 - (2 * 50 + 2) = 18, 8 above its level: the basket goes short.
    assert bot.basket_target(120, p, memory, market, plan) == -10
    assert plan.legs == {"A": 10, "B": 5}  # -weight * 0.5 * -10
    del market.books["B"]  # a leg without a price: the last target stands
    assert bot.basket_target(100, p, memory, market, bot.Plan(0, 10)) == -10


def test_a_leg_sums_what_its_baskets_want_within_its_limit(bot):
    market = bot.Market({})
    market.plans = {"X": bot.Plan(0, 10), "Y": bot.Plan(0, 10)}
    market.plans["X"].legs, market.plans["Y"].legs = {"A": 10.0}, {"A": 7.0, "B": -3.0}
    assert bot.hedge_target("A", params(bot, limit=15), market) == 15
    assert bot.hedge_target("B", params(bot, limit=15), market) == -3


def test_hedging_legs_trade_after_their_basket(bot, monkeypatch):
    monkeypatch.setattr(bot, "PARAMS", {
        "A": {"limit": 20, "fair": "mid", "hedge": True, "clear_edge": 1, "make_size": 0},
        "K": {"limit": 10, "fair": "mid", "basket": {"A": 2}, "level": 0, "level_band": 5, "hedge_ratio": 1, "clear_edge": 1},
    })
    depths = {"A": depth([(49, 30)], [(51, 30)]), "K": depth([(109, 20)], [(111, 20)])}
    orders, _, _ = bot.Trader().run(state(depths))
    # K's spread is 110 - 100 = 10 above its level: K sells 10, A buys 20 (2 per basket, at its limit).
    assert [(o.price, o.quantity) for o in orders["K"] if o.quantity < 0][0] == (109, -10)
    assert [(o.price, o.quantity) for o in orders["A"]] == [(51, 20)]


def _ou_path(seed, shift=0.0, at=3000, n=6000, level=10_000.0):
    import random

    rng, x, out = random.Random(seed), level, []
    for k in range(n):
        if k == at:
            level, x = level + shift, x + shift
        x += 0.002 * (level - x) + 2.0 * rng.gauss(0, 1)
        out.append(x)
    return out


def test_changepoint_level_moves_to_a_shifted_level_and_stays_put_without_one(bot):
    p = params(bot, level=10_000, cpd_hazard=10_000, cpd_reversion=0.002, cpd_sd=2.0)
    for shift, low, high in ((0, 9_980, 10_020), (100, 10_070, 10_130)):
        memory = {}
        levels = [bot.estimate_level(x, p, memory) for x in _ou_path(4, shift)]
        assert levels[2_999] == pytest.approx(10_000, abs=20)  # before any shift
        assert low <= levels[-1] <= high
    memory = {}
    drop = params(bot, level=10_000, cpd_hazard=10_000, cpd_reversion=0.002, cpd_sd=2.0, cpd_action="drop")
    assert {bot.estimate_level(x, drop, memory) for x in _ou_path(4, 100)} == {10_000}  # the level stays put


def test_the_drop_action_ends_the_level_bet_once_the_level_has_likely_moved(bot):
    p = params(bot, level=10_000, level_band=30, cpd_hazard=10_000, cpd_reversion=0.002, cpd_sd=2.0, cpd_action="drop")
    memory = {}
    targets = [bot.level_target(x, p, memory) for x in _ou_path(4, 100)]
    assert memory["cp_moved"] > 0.5 and memory["broken"]
    assert targets[-1] == 0 and min(targets[3_000:]) == -10  # it was short the shift, then dropped the bet


def test_flattening_before_the_close_only_reduces_the_position(bot):
    book = bot.Book([[99, 5]], [[101, 5]])
    trade = lambda timestamp, **kw: bot.trade_product("X", book, 4, params(bot, fair="mid", flatten_from=900, **kw), {}, bot.Market({"X": book}, timestamp=timestamp))
    before = trade(800)
    assert len(before.quotes) == 2  # both sides, as usual
    at_fair = trade(900, flatten_edge=0)
    assert at_fair.takes == [] and at_fair.quotes == [(102, -4)]  # only the ask, sized to the position
    crossing = trade(950)  # by default it crosses up to the spread, to reach the other side
    assert crossing.takes == [(99, -4)] and crossing.quotes == []


def test_make_steps_inside_a_wide_book(bot):
    plan = bot.Plan(0, 10)
    bot.make(bot.Book([[95, 5]], [[105, 5]]), 100, params(bot, make_edge=2), plan)
    assert plan.quotes == [(96, 10), (104, -10)]


def test_make_inside_steps_further_into_a_wide_book_and_none_quotes_at_the_edge(bot):
    book = bot.Book([[95, 5]], [[105, 5]])
    quotes = lambda **kw: (plan := bot.Plan(0, 10), bot.make(book, 100, params(bot, make_edge=2, **kw), plan))[0].quotes
    assert quotes() == quotes(make_inside=1) == [(96, 10), (104, -10)]  # the default: one tick inside
    assert quotes(make_inside=3) == [(98, 10), (102, -10)]  # three ticks in, as far as make_edge allows
    assert quotes(make_inside=4) == quotes(make_inside=None) == [(98, 10), (102, -10)]  # never nearer fair than make_edge
    tight = bot.Book([[99, 5]], [[101, 5]])
    plan = bot.Plan(0, 10)
    bot.make(tight, 100, params(bot, make_edge=0, make_inside=None), plan)
    assert plan.quotes == [(99, 10), (100, -10)]  # both at fair would meet: the bid steps back, as make's other quotes do


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


@pytest.mark.parametrize("position, expected", [(0, [(99, 10), (100, -10)]), (-5, [(100, 15), (101, -5)])])
def test_bid_stays_below_the_ask(bot, position, expected):
    # A two-tick book and make_edge 0 put both quotes at 100. At or above target the bid steps
    # back; below it the ask does.
    plan = bot.Plan(position=position, limit=10)
    bot.make(bot.Book([[99, 5]], [[101, 5]]), 100, params(bot, make_edge=0), plan)
    assert plan.quotes == expected


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
    depths = {"RAINFOREST_RESIN": depth([(9990, 20)], [(9995, 2), (10010, 20)])}
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


def test_an_order_the_exchange_rejects_only_stops_its_own_product(capsys):
    """Building the exchange's orders is part of each product's isolated step: an Order that raises,
    as one without our `ioc` extension would, loses only that product's orders."""
    lenient = BotFile(TEMPLATE, {"datamodel": dm}, strict=False).load()

    def picky(symbol, price, quantity, ioc=False):
        if symbol == "KELP":
            raise TypeError("Order() got an unexpected keyword argument 'ioc'")
        return dm.Order(symbol, price, quantity, ioc)

    lenient.Order = picky
    depths = {"KELP": depth([(2029, 25)], [(2031, 25)]), "RAINFOREST_RESIN": depth([(9996, 2)], [(10004, 2)])}
    orders, _, _ = lenient.Trader().run(state(depths))
    assert set(orders) == {"RAINFOREST_RESIN"} and orders["RAINFOREST_RESIN"]
    assert "unexpected keyword argument 'ioc'" in capsys.readouterr().out


def test_a_broken_product_prints_each_error_once(capsys):
    """A product broken all day would print a traceback every tick; it prints again only when the error changes."""
    lenient = BotFile(TEMPLATE, {"datamodel": dm}, strict=False).load()
    lenient.PARAMS["KELP"]["fair"] = "bogus"
    data = ""
    for n in range(3):
        _, _, data = lenient.Trader().run(state({"KELP": depth([(2029, 25)], [(2031, 25)])}, trader_data=data))
    assert capsys.readouterr().out.count("Traceback") == 1
    lenient.PARAMS["KELP"]["fair"] = "other"
    lenient.Trader().run(state({"KELP": depth([(2029, 25)], [(2031, 25)])}, trader_data=data))
    assert capsys.readouterr().out.count("Traceback") == 1


def test_lenient_errors_cancel_the_products_resting_orders(capsys):
    lenient = BotFile(TEMPLATE, {"datamodel": dm}, strict=False).load()
    lenient.PARAMS["KELP"]["fair"] = "bogus"
    resting = {"KELP": [dm.OpenOrder(3, "KELP", 2029, 5, 0)]}
    orders, _, _ = lenient.Trader().run(state({"KELP": depth([(2029, 25)], [(2031, 25)])}, open_orders=resting))
    assert [o.order_id for o in orders["KELP"]] == [3]


def test_a_state_without_the_resting_extensions_still_trades(capsys):
    # A state from an exchange without open_orders: the broken product's handler must not raise.
    lenient = BotFile(TEMPLATE, {"datamodel": dm}, strict=False).load()
    lenient.PARAMS["KELP"]["fair"] = "bogus"
    plain = state({"KELP": depth([(2029, 25)], [(2031, 25)]), "RAINFOREST_RESIN": depth([(9996, 2)], [(10004, 2)])})
    del plain.open_orders
    orders, _, _ = lenient.Trader().run(plain)
    assert set(orders) == {"RAINFOREST_RESIN"}
    assert "bogus" in capsys.readouterr().out


@pytest.mark.parametrize("resting", [False, True])
def test_template_runs_cleanly_in_both_modes(data_dir, resting):
    days = prosperity.load_days(data_dir, ["1"])
    for day in days:
        result = run_day(day, prosperity.load_bot(TEMPLATE, {}, strict=True), EngineConfig(resting=resting))
        assert result.errors == [] and result.limit_breaches == []
