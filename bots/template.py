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

from datamodel import Cancel, Order, OrderDepth, TradingState

# The backtester sets this to True so bugs raise instead of being swallowed.
STRICT = False

DEFAULTS = {
    "limit": 50,  # position limit: must match the competition's
    "fair": "mid",  # "fixed", "mid" or "wall_mid" (see fair_value)
    "fixed_fair": None,  # used when fair is "fixed"
    "smoothing": 0.0,  # 0 uses each tick's fair as is; closer to 1 moves it more slowly
    "take_edge": 1,  # take book orders priced at least this much better than fair
    "clear_edge": 0,  # cut inventory at prices up to this much worse than fair
    "make_edge": 2,  # quote at least this far from fair
    "skew": 0.0,  # move quotes this far against inventory when at the full position limit
    "make_size": None,  # largest quote; None quotes all remaining room under the limit
}

PARAMS = {
    # IMC Prosperity 3, round 1
    "RAINFOREST_RESIN": {"limit": 50, "fair": "fixed", "fixed_fair": 10_000},
    "KELP": {"limit": 50, "fair": "wall_mid", "make_edge": 1},
    # IMC Prosperity 2, round 1
    "AMETHYSTS": {"limit": 20, "fair": "fixed", "fixed_fair": 10_000},
    "STARFRUIT": {"limit": 20, "fair": "wall_mid", "make_edge": 1},
    # IMC Prosperity 4, rounds 1-2 (untuned starting points)
    "ASH_COATED_OSMIUM": {"limit": 80, "fair": "wall_mid", "make_edge": 1},
    "INTARIAN_PEPPER_ROOT": {"limit": 80, "fair": "wall_mid", "make_edge": 1},
}


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


def trade_product(book: Book, position: int, p: dict, memory: dict) -> Plan:
    plan = Plan(position, p["limit"])
    fair = fair_value(book, p, memory)
    if fair is None:  # no price seen yet
        return plan
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
    """Cut inventory at (or close to) fair, freeing room under the limit for better trades later."""
    if plan.net > 0:
        for level in book.bids:
            if level[0] < fair - p["clear_edge"] or plan.net <= 0:
                break
            level[1] -= plan.sell(level[0], min(level[1], plan.net))
    elif plan.net < 0:
        for level in book.asks:
            if level[0] > fair + p["clear_edge"] or plan.net >= 0:
                break
            level[1] -= plan.buy(level[0], min(level[1], -plan.net))


def make(book: Book, fair: float, p: dict, plan: Plan) -> None:
    """Quote both sides around fair, then shift both quotes against inventory.

    Each quote sits make_edge from fair, or one tick inside the best remaining book quote if
    that's further out (no point quoting better than needed). skew then moves both quotes down
    when long and up when short, by up to skew ticks at the full limit, to work the position
    back toward zero. Quotes never cross the book.
    """
    best_bid = next((price for price, volume in book.bids if volume > 0), None)
    best_ask = next((price for price, volume in book.asks if volume > 0), None)

    bid = math.floor(fair - p["make_edge"])
    ask = math.ceil(fair + p["make_edge"])
    if best_bid is not None:
        bid = min(bid, best_bid + 1)
    if best_ask is not None:
        ask = max(ask, best_ask - 1)

    shift = round(p["skew"] * plan.net / plan.limit)
    bid, ask = bid - shift, ask - shift
    if best_ask is not None:
        bid = min(bid, best_ask - 1)
    if best_bid is not None:
        ask = max(ask, best_bid + 1)

    size = p["make_size"]
    plan.buy(bid, plan.buy_room if size is None else size, quote=True)
    plan.sell(ask, plan.sell_room if size is None else size, quote=True)


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
        for product, depth in state.order_depths.items():
            # Each product is isolated, so a bug in one doesn't stop the others trading.
            try:
                p = params_for(product)
                if p is None:
                    continue
                plan = trade_product(read_book(depth), state.position.get(product, 0), p, memory.setdefault(product, {}))
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
