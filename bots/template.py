"""Single-file trading bot: market making around a fair value.

The competition runs one file, so everything lives here, top to bottom:

  PARAMS     per-product settings. Products not listed are not traded.
  STRATEGY   format-agnostic logic: fair value -> take -> clear -> make.
  EXECUTION  format-agnostic order management: turns the plan into cancels and new orders.
  ADAPTER    the only code that knows the competition's data and order format.
  Trader     the entry point the competition calls every tick.

Works whether or not unfilled orders rest between ticks. Where they're cancelled every tick
(IMC Prosperity), every planned order is sent each tick. Where they rest (the backtester's
--resting), quotes that haven't moved are left alone to keep their place in the queue.

Written against the IMC Prosperity format as a stand-in, plus the backtester's resting-order
extensions (state.open_orders, Cancel, Order(..., ioc=True)). Once the real format is known,
rewrite ADAPTER and the datamodel import, and leave STRATEGY and EXECUTION alone.
Uses only the standard library so it runs wherever it is submitted.
"""

from __future__ import annotations

import json
import math
import traceback
from statistics import NormalDist

from datamodel import Cancel, Order, OrderDepth, TradingState

# The backtester sets this to True so bugs raise instead of being swallowed.
STRICT = False

DEFAULTS = {
    "limit": 50,  # position limit: must match the competition's
    "fair": "mid",  # "fixed", "mid", "wall_mid", "outer_mid" or "sized_mid" (see fair_value)
    "fixed_fair": None,  # used when fair is "fixed"
    "wall_size": 15,  # sized_mid: the smallest level that counts as the market maker's quote
    "smoothing": 0.0,  # 0 uses each tick's fair as is; closer to 1 moves it more slowly
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
    # A call option on another product (see follow_target): it takes that product's target as a
    # share of its own limit. None trades the product on its own.
    "follow": None,
    "strike": None,  # the call's strike
    "max_cost_per_delta": 20.0,  # stay flat when half the spread per unit of delta is above this
}

PARAMS = {
    # IMC Prosperity 3, round 1
    "RAINFOREST_RESIN": {"limit": 50, "fair": "fixed", "fixed_fair": 10_000},
    "KELP": {"limit": 50, "fair": "wall_mid", "make_edge": 1},
    # IMC Prosperity 2, round 1
    "AMETHYSTS": {"limit": 20, "fair": "fixed", "fixed_fair": 10_000},
    "STARFRUIT": {"limit": 20, "fair": "wall_mid", "make_edge": 1},
    # IMC Prosperity 4, rounds 1-2. Pepper Root rises about 1,000 a day, so it holds a long target
    # (grid over target and skew on rounds 1-2, IDEAS.md); Osmium is untuned.
    "ASH_COATED_OSMIUM": {"limit": 80, "fair": "wall_mid", "make_edge": 1},
    "INTARIAN_PEPPER_ROOT": {"limit": 80, "fair": "wall_mid", "make_edge": 1, "target": 80, "skew": 20},
    # IMC Prosperity 4, rounds 3-4. Both return to a level that held across days (IDEAS.md).
    "HYDROGEL_PACK": {"limit": 200, "fair": "wall_mid", "make_edge": 1, "level": 9994, "level_band": 30, "level_exit": 0, "clear_edge": 8},
    "VELVETFRUIT_EXTRACT": {"limit": 200, "fair": "wall_mid", "make_edge": 1, "level": 5247, "level_band": 30, "clear_edge": 2},
}
# Its vouchers are calls on it: extra room for the same bet. They only trade toward the target (no
# takes or quotes of their own), crossing up to clear_edge, about half each one's spread.
for _strike, _clear_edge in ((4000, 11), (4500, 8), (5000, 3), (5100, 2), (5200, 2), (5300, 1), (5400, 1), (5500, 1)):
    PARAMS[f"VEV_{_strike}"] = {"limit": 300, "fair": "wall_mid", "follow": "VELVETFRUIT_EXTRACT", "strike": _strike,
                                "clear_edge": _clear_edge, "take_edge": 10**6, "make_size": 0}


# ------------------------------------------------------------------------------ STRATEGY


class Book:
    """Visible order book. Levels are [price, volume] with volume > 0, best price first.

    take and clear reduce level volumes as they trade, so later steps see what's left.
    """

    def __init__(self, bids: list[list[int]], asks: list[list[int]]):
        self.bids = bids
        self.asks = asks


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
        # What the strategy decided, for products that follow this one (see Trader.run).
        self.fair: float | None = None
        self.target = 0

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


def trade_product(book: Book, position: int, p: dict, memory: dict, market: dict | None = None) -> Plan:
    """market holds this tick's plans of the products traded so far, for a product that follows one."""
    plan = Plan(position, p["limit"])
    fair = fair_value(book, p, memory)
    if fair is None:  # no price seen yet
        return plan
    if p["level"] is not None:
        p = {**p, "target": level_target(fair, p, memory)}
    elif p["follow"] is not None:
        p = {**p, "target": follow_target(book, fair, p, memory, (market or {}).get(p["follow"]))}
    plan.fair, plan.target = fair, p["target"]
    take(book, fair, p, plan)
    clear(book, fair, p, plan)
    make(book, fair, p, plan)
    return plan


def fair_value(book: Book, p: dict, memory: dict) -> float | None:
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
    else:
        raise ValueError(f"unknown fair value method {method!r}")

    previous = memory.get("fair")
    if fair is None:  # one side of the book is empty: keep the last value
        return previous
    if previous is not None and p["smoothing"]:
        fair = p["smoothing"] * previous + (1 - p["smoothing"]) * fair
    memory["fair"] = fair
    return fair


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
    with level_exit, comes back within level_exit of the level. On P4 Hydrogel and Velvetfruit a
    level taken from the other days made 1.7 times as much as the day's own mean (IDEAS.md).
    """
    gap = fair - estimate_level(fair, p, memory)
    held = memory.get("held", 0)
    if gap >= p["level_band"]:
        held = -p["limit"]
    elif gap <= -p["level_band"]:
        held = p["limit"]
    elif p["level_exit"] is not None and abs(gap) <= p["level_exit"]:
        held = 0
    memory["held"] = held
    return held


def estimate_level(fair: float, p: dict, memory: dict) -> float:
    """The level: the configured one, the mean of the day so far, or a blend of the two.

    With level_weight, a number level counts as that many ticks of the day's mean, so a day that
    settles elsewhere slowly moves it.
    """
    memory["level_sum"] = memory.get("level_sum", 0.0) + fair
    memory["level_n"] = memory.get("level_n", 0) + 1
    if p["level"] == "day":
        return memory["level_sum"] / memory["level_n"]
    if p["level_weight"] is None:
        return p["level"]
    return (p["level"] * p["level_weight"] + memory["level_sum"]) / (p["level_weight"] + memory["level_n"])


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
    position back toward target. Quotes never cross the book.

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

    size = p["make_size"]
    gap = p["size_skew"] * (plan.net - p["target"]) / plan.limit
    plan.buy(bid, _scaled(plan.buy_room if size is None else size, 1 - gap), quote=True)
    plan.sell(ask, _scaled(plan.sell_room if size is None else size, 1 + gap), quote=True)


def _scaled(size: int, factor: float) -> int:
    return int(size * max(factor, 0.0))


# ------------------------------------------------------------------------------ EXECUTION


def execute(plan: Plan, resting: list[tuple[int, int, int]]) -> tuple[list[int], list[tuple[int, int, bool]]]:
    """Turns the plan into (order ids to cancel, new orders as (price, signed quantity, ioc)).

    resting holds the product's resting orders as (id, price, signed quantity left), and is
    always empty where orders don't rest. A resting order is kept, with its place in the queue,
    while a quote on its side and at its price still wants at least its size. The quote then
    only sends the difference. Every other resting order is cancelled. Takes go out as
    immediate-or-cancel, so whatever the book can't fill never rests at a crossing price.
    """
    wanted: dict[tuple[bool, int], int] = {}  # (buying, price) -> signed quantity still to send
    for price, quantity in plan.quotes:
        key = (quantity > 0, price)
        wanted[key] = wanted.get(key, 0) + quantity
    cancels = []
    for order_id, price, quantity in sorted(resting):  # oldest first, as the queue has them
        key = (quantity > 0, price)
        if abs(quantity) <= abs(wanted.get(key, 0)):
            wanted[key] -= quantity
        else:
            cancels.append(order_id)
    orders = [(price, quantity, True) for price, quantity in plan.takes]
    orders += [(price, quantity, False) for (_, price), quantity in wanted.items() if quantity]
    return cancels, orders


# ------------------------------------------------------------------------------ ADAPTER


def read_book(depth: OrderDepth) -> Book:
    bids = [[price, volume] for price, volume in sorted(depth.buy_orders.items(), reverse=True)]
    asks = [[price, -volume] for price, volume in sorted(depth.sell_orders.items())]
    return Book(bids, asks)


def load_memory(trader_data: str) -> dict:
    try:
        memory = json.loads(trader_data) if trader_data else {}
    except ValueError:
        return {}
    return memory if isinstance(memory, dict) else {}


def params_for(product: str) -> dict | None:
    if product not in PARAMS:
        return None
    unknown = set(PARAMS[product]) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown params for {product}: {', '.join(sorted(unknown))}")
    return {**DEFAULTS, **PARAMS[product]}


def read_resting(state: TradingState, product: str) -> list[tuple[int, int, int]]:
    return [(order.id, order.price, order.quantity) for order in state.open_orders.get(product, [])]


class Trader:
    def run(self, state: TradingState):
        memory = load_memory(state.traderData)
        orders: dict[str, list[Order | Cancel]] = {}
        market: dict[str, Plan] = {}  # this tick's plans, for the products that follow one
        # Products that follow another go last, so they see its plan.
        products = sorted(state.order_depths, key=lambda product: PARAMS.get(product, {}).get("follow") is not None)
        for product in products:
            # Each product is isolated, so a bug in one doesn't stop the others trading.
            try:
                p = params_for(product)
                if p is None:
                    continue
                book = read_book(state.order_depths[product])
                plan = trade_product(book, state.position.get(product, 0), p, memory.setdefault(product, {}), market)
                market[product] = plan
                cancels, new = execute(plan, read_resting(state, product))
            except Exception:
                if STRICT:
                    raise
                print(f"{state.timestamp} {product}: {traceback.format_exc()}")
                # Don't leave stale quotes resting while this product is broken.
                stale = [Cancel(order.id) for order in state.open_orders.get(product, [])]
                if stale:
                    orders[product] = stale
                continue
            orders[product] = [Cancel(order_id) for order_id in cancels] + [
                Order(product, int(price), int(quantity), ioc=ioc) for price, quantity, ioc in new
            ]
        return orders, 0, json.dumps(memory)
