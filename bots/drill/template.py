"""The template, with its ADAPTER rewritten for the drill format (arena/formats/drill.py).

The format drill (TODO.md): the same file as bots/template.py down to the end of EXECUTION,
except PARAMS. Only the imports, PARAMS and ADAPTER changed, which is the edit to make on the
day for the Arena's real API. tests/test_drill.py checks that DEFAULTS, STRATEGY and
EXECUTION still match bots/template.py word for word.

The drill exchange calls Bot.on_tick(api) once a step. Prices are decimals on each product's
tick grid; STRATEGY and EXECUTION work in whole ticks, so ADAPTER converts at the boundary.
Order ids are opaque strings, and orders rest until cancelled.
"""

from __future__ import annotations

import math
import traceback
from statistics import NormalDist

# The backtester sets this to True so bugs raise instead of being swallowed.
STRICT = False

DEFAULTS = {
    "limit": 50,  # position limit: must match the competition's
    "fair": "sized_mid",  # "fixed", "mid", "wall_mid", "outer_mid", "sized_mid" or "weighted_mid" (see fair_value)
    "fixed_fair": None,  # used when fair is "fixed"
    "fixed_guard": None,  # fair "fixed": use the sized mid instead while it is further than this from fixed_fair
    "wall_size": 15,  # sized_mid: the smallest level that counts as the market maker's quote
    "smoothing": 0.0,  # 0 uses each tick's fair as is; closer to 1 moves it more slowly
    # Take, clear and make around fair + imbalance * rho, rho = (Vb - Va)/(Vb + Va) at the best
    # levels: the linear micro-price. 0 turns it off. Fitted per product by experiments.imbalance.
    "imbalance": 0.0,
    "take_edge": 1,  # take book orders priced at least this much better than fair
    "clear_edge": 0,  # cut inventory at prices up to this much worse than fair
    "make_edge": 2,  # quote at least this far from fair
    "skew": 0.0,  # move quotes this far against inventory when at the full position limit
    "size_skew": 0.0,  # scale each quote by max(1 +/- size_skew * gap / limit, 0): the side that adds to the gap shrinks
    "target": 0,  # position to hold: clear and skew work inventory toward it (e.g. long with a steady drift)
    "make_size": None,  # largest quote; None quotes all remaining room under the limit
    # A price the product returns to (see level_target): a number from earlier days, or "day" for
    # the mean of the day so far. None turns it off. While on, it sets target instead.
    "level": None,
    "level_weight": None,  # with a number level: ticks it counts for against the day's mean; None: fixed
    "level_band": 20,  # hold the full limit against a move this far from the level
    "level_exit": None,  # flatten once back within this of the level; None: hold until the other band
    "level_guard": None,  # past this many level_bands from the level, drop the bet (target 0) until back within one band
    # Changepoint detection on a number level (see changepoint_level): the expected ticks between
    # shifts of the level, None for off. It needs the product's reversion to the level a tick and the
    # sd of its one-tick steps, measured on the download (experiments/sim_regimes.py shows how).
    "cpd_hazard": None,
    "cpd_reversion": None,
    "cpd_sd": None,
    "cpd_block": 50,  # ticks averaged into one observation
    "cpd_action": "level",  # "level": bet around the re-estimated level; "drop": keep the level, drop the bet once it has likely moved
    "cpd_threshold": 0.5,  # "drop": the chance that the level has moved since the open from which the bet is dropped for the day
    # A call option on another product (see follow_target): it takes that product's target as a
    # share of its own limit. None trades the product on its own.
    "follow": None,
    "strike": None,  # the call's strike
    "max_cost_per_delta": 20.0,  # stay flat when half the spread per unit of delta is above this
    # A basket of other products, {leg: weight} (see basket_target). Its spread, the basket's price
    # less the legs' weighted prices, is traded with the level settings, level being its usual value.
    "basket": None,
    "hedge_ratio": 0.0,  # the legs that hedge hold -weight * hedge_ratio per basket held
    "hedge": False,  # a basket leg: hold what the baskets it belongs to want against them
    # Fading jumps that snap back (see jump_target): a move of the fair value at least this big
    # is a jump. None turns it off. While on, it sets target instead.
    "jump_min": None,
    "jump_hold": None,  # ticks to hold against a jump; None: until the next jump
    "jump_edge": 10,  # clear_edge while the target is against a jump: worth paying, a jump is worth jump_min
    "jump_seen": 5,  # jumps seen today before trading on them
    "jump_share": 0.6,  # the least share of them that reversed the jump before
    # Following named traders (see copy_target): {name: weight}, positive to trade with that
    # name, negative to trade against it. None turns it off. While on, it sets target instead.
    "copy": None,
    "copy_hold": None,  # ticks to hold after a signal; None: until the next one
    "copy_edge": 5,  # clear_edge while the target follows a signal
    # Protection against a regime the parameters weren't tuned for (see loss_stop, regime_guard;
    # arena.stress tests them).
    "stop_loss": None,  # flatten and stop for the day once today's PnL is this far below its high; None: off
    "stop_edge": None,  # clear_edge while flattening after the stop; None: the book's spread, to reach the other side
    "vol_guard": None,  # fall back to plain market making while recent volatility is this many times the day's
}

# stop_loss is about 3 times the product's largest intraday drawdown on the days it was tuned on
# (arena.stress prints it), so it never fires there: it caps a day the regime changes (IDEAS.md,
# "Stress: what a regime change costs").
# Prices in PARAMS are in each product's ticks (ALPHA: 0.05, BETA: 0.01, GAMMA: 0.25), and the
# limit comes from api.max_position, so it can't drift from the exchange's. Set from
# arena.diagnose on the drill data, as ON_THE_DAY.md says to (TODO.md, the format drill).
PARAMS = {
    # wall mid filters the mid's noise
    "ALPHA": {"fair": "wall_mid", "make_edge": 1},
    # wall mid nearly fixed at 100.00 = 10,000 ticks of 0.01
    "BETA": {"fair": "fixed", "fixed_fair": 10_000},
    # jumps past half the spread on 15% of ticks, and orders rest here: take only
    "GAMMA": {"fair": "wall_mid", "make_size": 0},
}


# ------------------------------------------------------------------------------ STRATEGY


class Book:
    """Visible order book. Levels are [price, volume] with volume > 0, best price first.

    take and clear reduce level volumes as they trade, so later steps see what's left.
    """

    def __init__(self, bids: list[list[int]], asks: list[list[int]]):
        self.bids = bids
        self.asks = asks

    def copy(self) -> Book:
        return Book([level[:] for level in self.bids], [level[:] for level in self.asks])


class Plan:
    """One product's orders for this tick, keeping all of them inside the position limit.

    Orders can all fill in the same tick, so the room to buy ignores planned sells and vice versa.
    The room is the full room under the limit: EXECUTION cancels any resting order the plan
    doesn't keep, and cancels free their room before new orders are checked.
    """

    def __init__(self, position: int, limit: int):
        self.position = position
        self.limit = limit
        self.bought = 0
        self.sold = 0
        self.takes: list[tuple[int, int]] = []  # (price, signed quantity) trading with the book now
        self.quotes: list[tuple[int, int]] = []  # (price, signed quantity) waiting to be hit
        # What the strategy decided, for the products traded after this one (see Market).
        self.fair: float | None = None
        self.target = 0
        self.legs: dict[str, float] = {}  # a basket's wish for each leg that hedges it

    @property
    def net(self) -> int:
        """Position if every planned order fills."""
        return self.position + self.bought - self.sold

    @property
    def buy_room(self) -> int:
        return self.limit - self.position - self.bought

    @property
    def sell_room(self) -> int:
        return self.limit + self.position - self.sold

    def buy(self, price: int, quantity: int, quote: bool = False) -> int:
        quantity = min(quantity, self.buy_room)
        if quantity > 0:
            (self.quotes if quote else self.takes).append((price, quantity))
            self.bought += quantity
        return max(quantity, 0)

    def sell(self, price: int, quantity: int, quote: bool = False) -> int:
        quantity = min(quantity, self.sell_room)
        if quantity > 0:
            (self.quotes if quote else self.takes).append((price, -quantity))
            self.sold += quantity
        return max(quantity, 0)


class Market:
    """What one product's strategy sees of the others this tick: every book, before anyone trades,
    the other traders' trades since the last tick as (buyer, seller, quantity), and the plans of
    the products traded so far. Trader.run trades a product that follows or hedges another after
    it, so one level of dependency works."""

    def __init__(
        self,
        books: dict[str, Book],
        trades: dict[str, list[tuple[str, str, int]]] | None = None,
        fills: dict[str, list[tuple[float, int]]] | None = None,
        timestamp: int = 0,
    ):
        self.books = books
        self.trades = trades or {}
        self.fills = fills or {}  # our own fills since the last tick, as (price, signed quantity)
        self.timestamp = timestamp
        self.plans: dict[str, Plan] = {}


def trade_product(product: str, book: Book, position: int, p: dict, memory: dict, market: Market | None = None) -> Plan:
    """Fair value -> take -> clear -> make, on a copy of the book: market.books stays untouched."""
    plan = Plan(position, p["limit"])
    market = market or Market({product: book})
    fair = fair_value(book, p, memory)
    if fair is None:  # no price seen yet
        return plan
    if p["stop_loss"] is not None and loss_stop(fair, position, market.fills.get(product, []), market.timestamp, p, memory):
        edge = p["stop_edge"] if p["stop_edge"] is not None else (book.asks[0][0] - book.bids[0][0] if book.bids and book.asks else 0)
        p = {**p, "target": 0, "take_edge": math.inf, "make_size": 0, "clear_edge": edge}
    elif p["vol_guard"] is not None and regime_guard(fair, p, memory):
        pass  # plain market making toward the static target
    elif p["basket"] is not None:
        p = {**p, "target": basket_target(fair, p, memory, market, plan)}
    elif p["level"] is not None:
        p = {**p, "target": level_target(fair, p, memory)}
    elif p["copy"] is not None:
        target = copy_target(market.trades.get(product, []), p, memory)
        p = {**p, "target": target, "clear_edge": p["copy_edge"] if target else p["clear_edge"]}
    elif p["jump_min"] is not None:
        target = jump_target(fair, p, memory)
        p = {**p, "target": target, "clear_edge": p["jump_edge"] if target else p["clear_edge"]}
    elif p["follow"] is not None:
        p = {**p, "target": follow_target(book, fair, p, memory, market.plans.get(p["follow"]))}
    elif p["hedge"]:
        p = {**p, "target": hedge_target(product, p, market)}
    plan.fair, plan.target = fair, p["target"]
    if p["imbalance"] and book.bids and book.asks:
        fair += p["imbalance"] * imbalance(book)
    book = book.copy()  # take and clear use up its levels
    take(book, fair, p, plan)
    clear(book, fair, p, plan)
    make(book, fair, p, plan)
    return plan


def fair_value(book: Book, p: dict, memory: dict) -> float | None:
    if p["fair"] == "fixed":
        if p["fixed_guard"] is not None:
            # A fixed value that the market has left (a level shift, a trend) is no longer the value.
            # The sized mid, not the wall mid: a rival's large order far from the touch would move
            # the wall mid past the guard (IDEAS.md, "Adversarial rivals"). Where a side has no
            # level of wall_size it uses the best one, so the guard doesn't flicker off in a trend.
            market = mid(_sized(book.bids, p["wall_size"]), _sized(book.asks, p["wall_size"]))
            if market is not None and abs(market - p["fixed_fair"]) > p["fixed_guard"]:
                return market
        return p["fixed_fair"]
    fair = price(book, p)
    previous = memory.get("fair")
    if fair is None:  # one side of the book is empty: keep the last value
        return previous
    if previous is not None and p["smoothing"]:
        fair = p["smoothing"] * previous + (1 - p["smoothing"]) * fair
    memory["fair"] = fair
    return fair


def price(book: Book, p: dict) -> float | None:
    """The book's price by p's fair-value method, before smoothing. None if a side is empty."""
    method = p["fair"]
    if method == "fixed":
        return p["fixed_fair"]
    if method == "mid":
        fair = mid(book.bids, book.asks)
    elif method == "wall_mid":
        # Market-making bots quote the largest size at stable prices. The midpoint of those
        # "walls" is much less noisy than the plain mid, which small orders keep moving.
        fair = mid(_wall(book.bids), _wall(book.asks))
    elif method == "outer_mid":
        # The outermost bid and ask, where the market maker usually sits (Frankfurt Hedgehogs).
        fair = mid(book.bids[-1:], book.asks[-1:])
    elif method == "sized_mid":
        # The first level from the top with at least wall_size. Unlike the largest or outermost
        # level, a large order far from the touch can't move it, so it holds up when other
        # traders' resting orders share the book (IDEAS.md, wall-mid definitions).
        fair = mid(_sized(book.bids, p["wall_size"]), _sized(book.asks, p["wall_size"]))
    elif method == "weighted_mid":
        # The best prices weighted by the other side's volume, I*ask + (1-I)*bid with I = Vb/(Vb+Va):
        # what most teams call the micro-price (Stoikov's is between it and the mid).
        if not book.bids or not book.asks:
            return None
        share = book.bids[0][1] / (book.bids[0][1] + book.asks[0][1])
        fair = share * book.asks[0][0] + (1 - share) * book.bids[0][0]
    else:
        raise ValueError(f"unknown fair value method {method!r}")
    return fair


def imbalance(book: Book) -> float:
    """(Vb - Va)/(Vb + Va) at the best bid and ask, in [-1, 1]."""
    bid, ask = book.bids[0][1], book.asks[0][1]
    return (bid - ask) / (bid + ask)


def mid(bids: list[list[int]], asks: list[list[int]]) -> float | None:
    if not bids or not asks:
        return None
    return (bids[0][0] + asks[0][0]) / 2


def _wall(levels: list[list[int]]) -> list[list[int]]:
    """The level with the most volume, as a one-level list (empty if there are no levels)."""
    return [max(levels, key=lambda level: level[1])] if levels else []


def _sized(levels: list[list[int]], size: int) -> list[list[int]]:
    """The first level from the top with at least `size`, else the best level, as a one-level list."""
    return next(([level] for level in levels if level[1] >= size), levels[:1])


def level_target(fair: float, p: dict, memory: dict) -> int:
    """The position to hold when the product returns to a level: short above it, long below.

    Beyond level_band from the level, the target is the full limit against the move. Inside the
    band it keeps its last value, so the position isn't traded back and forth on every tick (each
    trade toward the target can cost half the spread), until the price reaches the other band or,
    with level_exit, comes back within level_exit of the level or goes past it. (Past it counts
    because prices jump: a gap of exactly 0 may never be seen.) On P4 Hydrogel and Velvetfruit a
    level taken from the other days made 1.7 times as much as the day's own mean (IDEAS.md).
    """
    gap = fair - estimate_level(fair, p, memory)
    held = memory.get("held", 0)
    exit_within = p["level_exit"]
    if p["level_guard"] is not None:
        # The level may have moved: past level_guard bands, stop betting on it until the price is
        # back within one band (not just inside the guard, or it trades in and out at the guard).
        if abs(gap) > p["level_guard"] * p["level_band"]:
            memory["broken"] = True
        elif abs(gap) < p["level_band"]:
            memory.pop("broken", None)
    if p["cpd_hazard"] is not None and p["cpd_action"] == "drop" and memory.get("cp_moved", 0) > p["cpd_threshold"]:
        memory["broken"] = True  # the level has likely moved: no bet on it for the rest of the day
    if memory.get("broken"):
        held = 0
    elif gap >= p["level_band"]:
        held = -p["limit"]
    elif gap <= -p["level_band"]:
        held = p["limit"]
    elif exit_within is not None and ((held < 0 and gap <= exit_within) or (held > 0 and gap >= -exit_within)):
        held = 0
    memory["held"] = held
    return held


def loss_stop(fair: float, position: int, fills: list[tuple[float, int]], timestamp: int, p: dict, memory: dict) -> bool:
    """True once today's PnL on this product has fallen stop_loss below its high: then the product
    only flattens (crossing up to stop_edge) until the day ends.

    PnL is cash from our fills plus the position at fair. A timestamp lower than the last one is a
    new day: the stop resets, and a position carried over starts at zero PnL.
    """
    if timestamp < memory.get("stop_t", -1):
        memory.pop("stopped", None)
        memory["cash"], memory["peak"] = -position * fair, 0.0
    memory["stop_t"] = timestamp
    memory["cash"] = memory.get("cash", 0.0) - sum(price * quantity for price, quantity in fills)
    pnl = memory["cash"] + position * fair
    memory["peak"] = max(memory.get("peak", 0.0), pnl)
    if memory["peak"] - pnl > p["stop_loss"]:
        memory["stopped"] = True
    return memory.get("stopped", False)


def regime_guard(fair: float, p: dict, memory: dict) -> bool:
    """True while the fair value's recent volatility is vol_guard times its volatility over the day.

    Exponential averages of squared one-tick changes, over about 20 and 1,000 ticks, after 200
    ticks of warm-up. While it holds, the product drops its target bets (level, jump, copy, basket,
    follow) and makes markets around its static target. A rough stand-in for a changepoint detector
    (Adams & MacKay, references/wiki/sources/online-changepoint-detection.md).
    """
    last = memory.get("vg_last")
    memory["vg_last"] = fair
    if last is None:
        return False
    change = (fair - last) ** 2
    memory["vg_fast"] = 0.95 * memory.get("vg_fast", change) + 0.05 * change
    memory["vg_slow"] = 0.999 * memory.get("vg_slow", change) + 0.001 * change
    memory["vg_n"] = memory.get("vg_n", 0) + 1
    return memory["vg_n"] >= 200 and memory["vg_fast"] > p["vol_guard"] ** 2 * max(memory["vg_slow"], 1e-9)


def estimate_level(fair: float, p: dict, memory: dict) -> float:
    """The level: the configured one, the mean of the day so far, or a blend of the two.

    With level_weight, a number level counts as that many ticks of the day's mean, so a day that
    settles elsewhere slowly moves it.
    """
    memory["level_sum"] = memory.get("level_sum", 0.0) + fair
    memory["level_n"] = memory.get("level_n", 0) + 1
    if p["level"] == "day":
        return memory["level_sum"] / memory["level_n"]
    if p["cpd_hazard"] is not None:
        return changepoint_level(fair, p, memory)
    if p["level_weight"] is None:
        return p["level"]
    return (p["level"] * p["level_weight"] + memory["level_sum"]) / (p["level_weight"] + memory["level_n"])


def changepoint_level(fair: float, p: dict, memory: dict) -> float:
    """The level, re-estimated when it shifts: online changepoint detection (Adams & MacKay 2007).

    The fair value is averaged over blocks of cpd_block ticks. For a product that returns to its
    level mu at rate theta a tick, consecutive block means follow x_k = mu + phi (x_{k-1} - mu) + e
    with phi = exp(-theta B), so z_k = (x_k - phi x_{k-1}) / (1 - phi) is an independent, noisy
    observation of mu. Each run length r (blocks since the last shift) keeps a Gaussian posterior
    for mu. A shift happens with chance B / cpd_hazard per block; a new run's mu starts near the
    latest block mean. The level used is the posterior mean of mu over all run lengths: the
    configured level until the evidence moves it, the new one soon after a shift.
    """
    memory["cp_sum"] = memory.get("cp_sum", 0.0) + fair
    memory["cp_n"] = memory.get("cp_n", 0) + 1
    if memory["cp_n"] < p["cpd_block"]:
        return memory.get("cp_level", p["level"]) if p["cpd_action"] == "level" else p["level"]
    x = memory.pop("cp_sum") / memory.pop("cp_n")
    block, theta, sd = p["cpd_block"], p["cpd_reversion"], p["cpd_sd"]
    phi = math.exp(-theta * block)
    stationary = sd * sd / (2 * theta)  # the variance of the price around its level
    noise = stationary * (1 - phi * phi) / (1 - phi) ** 2  # the variance of one observation z of mu
    runs = memory.get("cp_runs") or [[1.0, p["level"], stationary / 4, 0]]  # [chance, mean, variance, first block]
    last = memory.get("cp_last")
    memory["cp_last"] = x
    memory["cp_k"] = k = memory.get("cp_k", 0) + 1
    if last is not None:
        z = (x - phi * last) / (1 - phi)
        hazard = min(block / p["cpd_hazard"], 1.0)
        grown, shifted = [], 0.0
        for chance, mean, var, first in runs:
            spread = var + noise
            likelihood = math.exp(-((z - mean) ** 2) / (2 * spread)) / math.sqrt(spread)
            grown.append([chance * likelihood * (1 - hazard), (mean / var + z / noise) / (1 / var + 1 / noise), 1 / (1 / var + 1 / noise), first])
            shifted += chance * likelihood * hazard
        runs = [[shifted, x, stationary, k]] + grown
        total = sum(r[0] for r in runs) or 1.0
        runs = sorted(([c / total, m, v, f] for c, m, v, f in runs if c / total > 1e-6), reverse=True)[:40]
    memory["cp_runs"] = runs
    memory["cp_moved"] = 1 - sum(c for c, _, _, first in runs if first == 0)  # chance it shifted since the open
    memory["cp_level"] = sum(c * m for c, m, _, _ in runs) / sum(c for c, _, _, _ in runs)
    return memory["cp_level"] if p["cpd_action"] == "level" else p["level"]


def jump_target(fair: float, p: dict, memory: dict) -> int:
    """The position to hold when the price jumps and snaps back: the full limit against the last jump.

    A move of the fair value by at least jump_min is a jump. Once jump_seen jumps have followed
    another today, and at least jump_share of those went the opposite way, each jump sets the
    target to the full limit against it, held for jump_hold ticks or until the next jump. Before
    that, or when too few reverse, the target is 0. The share is measured on the day itself, so
    the rule can run on every product: in P4 round 5's data the jumps came on one product and day
    (ROBOT_DISHES, steps of 100, 87% reversed), and a team reports them on another one live. On
    every round 5 product it added 501k over three days to plain market making, its worst day
    +4k; fading every jump instead lost 184k on one day (IDEAS.md).
    """
    last, memory["jump_last"] = memory.get("jump_last"), fair
    held, age = memory.get("held", 0), memory.get("jump_age", 0) + 1
    if last is not None and abs(fair - last) >= p["jump_min"]:
        sign = 1 if fair > last else -1
        if memory.get("jump_sign"):
            memory["jump_n"] = memory.get("jump_n", 0) + 1
            memory["jump_rev"] = memory.get("jump_rev", 0) + (sign != memory["jump_sign"])
        memory["jump_sign"] = sign
        n, reversed_ = memory.get("jump_n", 0), memory.get("jump_rev", 0)
        held = -sign * p["limit"] if n >= p["jump_seen"] and reversed_ >= p["jump_share"] * n else 0
        age = 0
    elif p["jump_hold"] is not None and age >= p["jump_hold"]:
        held = 0
    memory["held"], memory["jump_age"] = held, age
    return held


def copy_target(trades: list[tuple[str, str, int]], p: dict, memory: dict) -> int:
    """The position to hold when some traders know where the price is going: up to the full limit their way.

    Each trade since the last tick adds the buyer's weight in copy and takes away the seller's.
    A non-zero sum, capped at 1 either way, sets the target to that share of the limit, held for
    copy_hold ticks or until the next signal: a weight of 0.5 leaves half the room to market making. On P3 round 5, Olivia bought at or near the day's low and sold at
    or near its high on all 19 of her trades (Kelp, Squid Ink, Croissants) (IDEAS.md).
    """
    signal = sum(p["copy"].get(buyer, 0) - p["copy"].get(seller, 0) for buyer, seller, _ in trades)
    held, age = memory.get("held", 0), memory.get("copy_age", 0) + 1
    if signal:
        held, age = round(max(-1.0, min(1.0, signal)) * p["limit"]), 0
    elif p["copy_hold"] is not None and age >= p["copy_hold"]:
        held = 0
    memory["held"], memory["copy_age"] = held, age
    return held


def follow_target(book: Book, fair: float, p: dict, memory: dict, underlying: Plan | None) -> int:
    """A call option's target: the underlying's target as a share of the option's own limit.

    Each unit then adds its delta to the underlying's view, so the options are extra room for the
    same bet: on P4 the vouchers' implied volatility was flat within a day, and the teams' voucher
    PnL was almost exactly delta times the underlying's move (IDEAS.md). A strike stays flat when
    crossing its spread costs more than max_cost_per_delta per unit of delta, in the underlying's
    price units: deep in-the-money calls have a delta of 1 but a much wider spread. Delta comes
    from the option's own price, so no expiry date is needed. If the underlying wasn't traded
    this tick, the last target is kept.
    """
    if underlying is None or underlying.fair is None or not book.bids or not book.asks:
        return memory.get("held", 0)
    s, k = underlying.fair, p["strike"]
    delta = call_delta(s, k, implied_variance(fair, s, k))
    half_spread = (book.asks[0][0] - book.bids[0][0]) / 2
    cost = half_spread / delta if delta > 1e-6 else 1e9
    # Averaged over about 20 ticks, so a spread that widens for a tick doesn't flip the strike.
    cost = memory["cost"] = cost if "cost" not in memory else 0.95 * memory["cost"] + 0.05 * cost
    if cost > p["max_cost_per_delta"]:
        held = 0
    else:
        held = round(underlying.target / underlying.limit * p["limit"])
    memory["held"] = held
    return held


# Black-Scholes for a call with no interest, in terms of the total variance w = sigma^2 * T to
# expiry. Price and delta depend on sigma and T only through w, so w can be implied from the
# option's own price without knowing the expiry.
_NORMAL = NormalDist()


def call_price(s: float, k: float, w: float) -> float:
    if w <= 0:
        return max(s - k, 0.0)
    d1 = (math.log(s / k) + w / 2) / math.sqrt(w)
    return s * _NORMAL.cdf(d1) - k * _NORMAL.cdf(d1 - math.sqrt(w))


def call_delta(s: float, k: float, w: float) -> float:
    if w <= 0:
        return 1.0 if s > k else 0.0
    return _NORMAL.cdf((math.log(s / k) + w / 2) / math.sqrt(w))


def implied_variance(price: float, s: float, k: float) -> float:
    """The w at which call_price matches price: 0 at or below intrinsic value (bisection)."""
    if price <= max(s - k, 0.0):
        return 0.0
    lo, hi = 0.0, 4.0  # w = 4 is a volatility of 200% for a year
    for _ in range(50):
        mid_w = (lo + hi) / 2
        if call_price(s, k, mid_w) < price:
            lo = mid_w
        else:
            hi = mid_w
    return (lo + hi) / 2


def basket_target(fair: float, p: dict, memory: dict, market: Market, plan: Plan) -> int:
    """A basket's target: level_target on its spread, the basket's price less its legs' weighted prices.

    level is the spread's usual value, the premium. A family whose prices sum to a constant is a
    basket too: one member, the others as legs of weight -1, level the constant. Each leg that
    hedges is asked for -weight * hedge_ratio times the target (plan.legs). Legs are priced by the
    basket's fair method; if one has no price this tick, the last target is kept.
    """
    legs = [price(market.books[leg], p) if leg in market.books else None for leg in p["basket"]]
    if None in legs:
        target = memory.get("held", 0)
    else:
        spread = fair - sum(weight * leg for weight, leg in zip(p["basket"].values(), legs))
        target = level_target(spread, p, memory)
    plan.legs = {leg: -weight * p["hedge_ratio"] * target for leg, weight in p["basket"].items()}
    return target


def hedge_target(product: str, p: dict, market: Market) -> int:
    """A basket leg's target: what the baskets it belongs to want held against them, within the limit."""
    wanted = sum(plan.legs.get(product, 0.0) for plan in market.plans.values())
    return max(-p["limit"], min(p["limit"], round(wanted)))


def take(book: Book, fair: float, p: dict, plan: Plan) -> None:
    """Trade against book orders priced at least take_edge better than fair."""
    for level in book.asks:
        if level[0] > fair - p["take_edge"]:
            break
        level[1] -= plan.buy(level[0], level[1])
    for level in book.bids:
        if level[0] < fair + p["take_edge"]:
            break
        level[1] -= plan.sell(level[0], level[1])


def clear(book: Book, fair: float, p: dict, plan: Plan) -> None:
    """Trade inventory back to target at (or close to) fair, freeing room for better trades later."""
    target = p["target"]
    if plan.net > target:
        for level in book.bids:
            if level[0] < fair - p["clear_edge"] or plan.net <= target:
                break
            level[1] -= plan.sell(level[0], min(level[1], plan.net - target))
    elif plan.net < target:
        for level in book.asks:
            if level[0] > fair + p["clear_edge"] or plan.net >= target:
                break
            level[1] -= plan.buy(level[0], min(level[1], target - plan.net))


def make(book: Book, fair: float, p: dict, plan: Plan) -> None:
    """Quote both sides around fair, then shift both quotes against inventory.

    Each quote sits make_edge from fair, or one tick inside the best remaining book quote if
    that's further out (no point quoting better than needed). skew then moves both quotes down
    when above target and up when below, by up to skew ticks a full limit away, to work the
    position back toward target. Quotes never cross the book, and the bid stays below the ask:
    if they meet, the side that would add to inventory steps back (the bid, at or above target).

    size_skew works through size instead (Bouchaud et al. 2018, eq. 17.4): with gap the distance
    above target as a share of the limit, the bid is scaled by max(1 - size_skew * gap, 0) and the
    ask by max(1 + size_skew * gap, 0), within the room left.
    """
    best_bid = next((price for price, volume in book.bids if volume > 0), None)
    best_ask = next((price for price, volume in book.asks if volume > 0), None)

    bid = math.floor(fair - p["make_edge"])
    ask = math.ceil(fair + p["make_edge"])
    if best_bid is not None:
        bid = min(bid, best_bid + 1)
    if best_ask is not None:
        ask = max(ask, best_ask - 1)

    shift = round(p["skew"] * (plan.net - p["target"]) / plan.limit)
    bid, ask = bid - shift, ask - shift
    if best_ask is not None:
        bid = min(bid, best_ask - 1)
    if best_bid is not None:
        ask = max(ask, best_bid + 1)
    if bid >= ask:  # a narrow book and a skew can bring them together: move the side that adds to inventory
        if plan.net >= p["target"]:
            bid = ask - 1
        else:
            ask = bid + 1

    size = p["make_size"]
    gap = p["size_skew"] * (plan.net - p["target"]) / plan.limit
    plan.buy(bid, _scaled(plan.buy_room if size is None else size, 1 - gap), quote=True)
    plan.sell(ask, _scaled(plan.sell_room if size is None else size, 1 + gap), quote=True)


def _scaled(size: int, factor: float) -> int:
    return int(size * max(factor, 0.0))


# ------------------------------------------------------------------------------ EXECUTION


def execute(plan: Plan, resting: list[tuple[int, int, int]]) -> tuple[list[int], list[tuple[int, int, bool]]]:
    """Turns the plan into (order ids to cancel, new orders as (price, signed quantity, ioc)).

    resting holds the product's resting orders as (id, price, signed quantity left), oldest
    first (ADAPTER's job: ids needn't sort by age), and is always empty where orders don't rest. A resting order is kept, with its place in the queue,
    while a quote on its side and at its price still wants at least its size. The quote then
    only sends the difference. Every other resting order is cancelled. Takes go out as
    immediate-or-cancel, so whatever the book can't fill never rests at a crossing price.
    """
    wanted: dict[tuple[bool, int], int] = {}  # (buying, price) -> signed quantity still to send
    for price, quantity in plan.quotes:
        key = (quantity > 0, price)
        wanted[key] = wanted.get(key, 0) + quantity
    cancels = []
    for order_id, price, quantity in resting:  # oldest first, as the queue has them
        key = (quantity > 0, price)
        if abs(quantity) <= abs(wanted.get(key, 0)):
            wanted[key] -= quantity
        else:
            cancels.append(order_id)
    orders = [(price, quantity, True) for price, quantity in plan.takes]
    orders += [(price, quantity, False) for (_, price), quantity in wanted.items() if quantity]
    return cancels, orders


# ------------------------------------------------------------------------------ ADAPTER
# The drill exchange (arena/formats/drill_exchange.py). Everything below converts between its
# decimal prices and the whole ticks STRATEGY and EXECUTION use.


def to_ticks(api, symbol: str, price: float) -> int:
    return round(price / api.tick_size(symbol))


def to_price(api, symbol: str, ticks: int) -> float:
    return round(ticks * api.tick_size(symbol), 10)


def read_book(api, symbol: str) -> Book | None:
    book = api.book(symbol)
    if book is None:
        return None
    side = lambda levels: [[to_ticks(api, symbol, level.price), level.size] for level in levels]
    return Book(side(book.bids), side(book.asks))


def params_for(api, product: str) -> dict | None:
    if product not in PARAMS:
        return None
    unknown = set(PARAMS[product]) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown params for {product}: {', '.join(sorted(unknown))}")
    return {**DEFAULTS, **PARAMS[product], "limit": api.max_position(product)}


def read_trades(api) -> dict[str, list[tuple[str, str, int]]]:
    """Trades this step as (buyer, seller, quantity). The drill names no traders, so `copy` can't work."""
    return {symbol: [("", "", trade.size) for trade in api.trades(symbol)] for symbol in api.symbols()}


def read_fills(api, fills) -> dict[str, list[tuple[float, int]]]:
    """Our fills since the last step, by product, as (price in ticks, signed quantity)."""
    out: dict[str, list[tuple[float, int]]] = {}
    for fill in fills:
        out.setdefault(fill.symbol, []).append((to_ticks(api, fill.symbol, fill.price), fill.size))
    return out


def read_resting(api, product: str) -> list[tuple[str, int, int]]:
    """The product's resting orders, oldest first (api.orders keeps that order; the ids don't)."""
    return [(order.order_id, to_ticks(api, product, order.price), order.size) for order in api.orders(product)]


def _depends(p: dict) -> bool:
    return p.get("follow") is not None or bool(p.get("hedge"))


class Bot:
    def __init__(self):
        self.memory: dict = {}  # the instance lives all session, so state stays on it

    def on_tick(self, api) -> None:
        books = {}
        for symbol in api.symbols():
            book = read_book(api, symbol)
            if book is not None:
                books[symbol] = book
        market = Market(books, read_trades(api), read_fills(api, api.fills()), api.time)
        # Products that follow or hedge another go last, so they see its plan.
        products = sorted(market.books, key=lambda product: _depends(PARAMS.get(product, {})))
        for product in products:
            # Each product is isolated, so a bug in one doesn't stop the others trading.
            try:
                p = params_for(api, product)
                if p is None:
                    continue
                plan = trade_product(product, market.books[product], api.position(product), p, self.memory.setdefault(product, {}), market)
                market.plans[product] = plan
                cancels, new = execute(plan, read_resting(api, product))
                for order_id in cancels:
                    api.cancel(order_id)
                for price, quantity, ioc in new:
                    send = api.buy if quantity > 0 else api.sell
                    send(product, to_price(api, product, int(price)), abs(int(quantity)), ioc=ioc)
            except Exception:
                if STRICT:
                    raise
                print(f"{api.time} {product}: {traceback.format_exc()}")
                # Don't leave stale quotes resting while this product is broken.
                try:
                    for order in api.orders(product):
                        api.cancel(order.order_id)
                except Exception:
                    pass
