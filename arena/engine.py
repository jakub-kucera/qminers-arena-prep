"""Replays a Day against a bot and simulates its fills.

Default rules follow IMC Prosperity and were checked fill-for-fill against jmerle's prosperity3bt:
  1. Every tick the bot sees the book and returns orders.
  2. If a product's orders could breach its position limit (all its buys, or all its sells,
     filling), every order for that product is cancelled.
  3. Each order trades against the visible book at the book's prices, best price first.
  4. What's left can fill against that tick's market trades, at the order's own price
     (see TradeMatching).
  5. Anything still unfilled is cancelled: no order rests into the next tick.

Resting mode (EngineConfig.resting) replaces rule 5 with an exchange where orders stay on the
book until they fill or the bot cancels them. Its queue model estimates fills for orders that
aren't in the recorded data:
  - A new order takes what it can from the visible book (rule 3). The rest rests, unless the
    order is ioc. It joins the back of the queue: the visible volume at its price is ahead of it.
  - Market trades at the order's price first use up the volume ahead of it, then fill it.
    Trades at a worse price fill it straight away (it would have traded first). Fills are at
    the order's price. TradeMatching worse / none turn off fills from trades at / at any price.
  - When a new snapshot shows the other side at or through a resting order's price, those
    orders would have hit it: it fills at its own price against that volume, and the bot sees
    the snapshot without it.
  - If the visible volume at the order's price drops below the volume counted ahead of it,
    orders ahead of it were cancelled, so it moves up. An emptied level puts it at the front.
  - The limit check (rule 2) counts resting orders, and only rejects that tick's new orders.
  - Your own orders never trade with each other.
Positions are valued at each tick's mark price.
"""

from __future__ import annotations

import io
import random
import time
import traceback
from collections import defaultdict
from contextlib import nullcontext, redirect_stdout
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Protocol

from arena.model import Book, Cancel, Day, Fill, MarketTrade, OpenOrder, Order, Tick


class TradeMatching(StrEnum):
    """Which market trades an order can fill against once the visible book is exhausted."""

    ALL = "all"  # trades at the order's price or worse (in resting mode, after the queue ahead)
    WORSE = "worse"  # only trades strictly worse than the order's price (more conservative)
    NONE = "none"  # none: fills come from the visible book only


@dataclass(frozen=True)
class EngineConfig:
    trade_matching: TradeMatching = TradeMatching.ALL
    resting: bool = False  # orders rest until filled or cancelled (see the module docstring)
    # Share of each book level and market trade available to us. Below 1 it approximates other
    # teams competing for the same liquidity: each unit is available with this probability.
    # The draws are seeded and don't depend on the bot's orders, so variants of a bot see the
    # same liquidity and can be compared fairly.
    fill_ratio: float = 1.0
    seed: int = 0
    capture_output: bool = True  # hide the bot's prints (their size is still measured)


class Bot(Protocol):
    def step(
        self,
        tick: Tick,
        positions: dict[str, int],
        own_fills: list[Fill],
        market_trades: dict[str, list[MarketTrade]],
        open_orders: list[OpenOrder],
    ) -> list[Order | Cancel]:
        """Returns this tick's new orders and cancels.

        own_fills are the fills since the last call, market_trades the previous tick's.
        open_orders are the bot's resting orders, always empty unless the engine is in resting mode.
        """
        ...


@dataclass
class DayResult:
    day: str
    products: list[str]
    limits: dict[str, int]
    timestamps: list[int] = field(default_factory=list)
    # Per product, one value per tick, recorded after that tick's fills.
    positions: dict[str, list[int]] = field(default_factory=dict)
    marks: dict[str, list[float]] = field(default_factory=dict)
    pnl: dict[str, list[float]] = field(default_factory=dict)
    best_bids: dict[str, list[float | None]] = field(default_factory=dict)  # None: that side was empty
    best_asks: dict[str, list[float | None]] = field(default_factory=dict)
    # (timestamp, order) for every order working during that tick, before its fills: placed then
    # (after the limit check), or resting from earlier.
    orders: list[tuple[int, OpenOrder]] = field(default_factory=list)
    cancels: list[tuple[int, int]] = field(default_factory=list)  # (timestamp, order id)
    fills: list[Fill] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)  # (timestamp, traceback or message)
    limit_breaches: list[tuple[int, str]] = field(default_factory=list)  # (timestamp, product)
    step_seconds: list[float] = field(default_factory=list)
    max_output_chars: int = 0


@dataclass
class _Live:
    """An accepted order inside the engine."""

    id: int
    product: str
    price: float
    quantity: int  # left to fill, signed
    timestamp: int
    ahead: int = 0  # resting mode: volume queued in front of it at its price

    def view(self) -> OpenOrder:
        return OpenOrder(self.id, self.product, self.price, self.quantity, self.timestamp)


def run_day(day: Day, bot: Bot, config: EngineConfig = EngineConfig()) -> DayResult:
    result = DayResult(
        day.name,
        day.products,
        day.limits,
        positions={product: [] for product in day.products},
        marks={product: [] for product in day.products},
        pnl={product: [] for product in day.products},
        best_bids={product: [] for product in day.products},
        best_asks={product: [] for product in day.products},
    )
    rng = random.Random(config.seed)
    position = dict.fromkeys(day.products, 0)
    cash = dict.fromkeys(day.products, 0.0)
    mark = dict.fromkeys(day.products, 0.0)
    unseen_fills: list[Fill] = []  # fills the bot hasn't been shown yet
    market_trades: dict[str, list[MarketTrade]] = {}
    resting: list[_Live] = []
    next_id = 1

    def settle(fills: list[Fill]) -> None:
        for fill in fills:
            position[fill.product] += fill.quantity
            cash[fill.product] -= fill.price * fill.quantity
        result.fills.extend(fills)

    for tick in day.ticks:
        books, trades = _liquidity(tick, config.fill_ratio, rng)
        if resting:
            crossed, taken = _cross(resting, books, tick.timestamp)
            _requeue(resting, tick.books)
            tick = _without(tick, taken)
            resting = [order for order in resting if order.quantity]
            settle(crossed)
            unseen_fills = unseen_fills + crossed

        actions = _call_bot(bot, tick, position, unseen_fills, market_trades, [o.view() for o in resting], config, result)
        orders, resting = _cancel(actions, resting, config.resting, tick.timestamp, result)
        orders = _within_limits(orders, position, resting, day.limits, tick.timestamp, result)
        placed = [_Live(next_id + i, o.product, o.price, o.quantity, tick.timestamp) for i, o in enumerate(orders)]
        next_id += len(placed)
        result.orders.extend((tick.timestamp, order.view()) for order in resting + placed)

        if config.resting:
            fills = []
            for order, live in zip(orders, placed):
                fills += _take_book(live, books, tick.timestamp)
                if live.quantity and not order.ioc:
                    live.ahead = _volume_at(live, tick.books)
                    resting.append(live)
            fills += _fill_resting(resting, trades, config.trade_matching, tick.timestamp)
            resting = [order for order in resting if order.quantity]
        else:
            fills = [
                fill
                for order in placed
                for fill in _take_book(order, books, tick.timestamp)
                + _take_trades(order, trades, config.trade_matching, tick.timestamp)
            ]
        market_trades = _remaining_trades(trades)
        settle(fills)
        unseen_fills = fills

        result.timestamps.append(tick.timestamp)
        for product in day.products:
            mark[product] = _mark(tick, product, mark[product])
            result.positions[product].append(position[product])
            result.marks[product].append(mark[product])
            result.pnl[product].append(cash[product] + position[product] * mark[product])
            book = tick.books.get(product)
            result.best_bids[product].append(book.bids[0][0] if book and book.bids else None)
            result.best_asks[product].append(book.asks[0][0] if book and book.asks else None)

    return result


def _call_bot(bot, tick, position, own_fills, market_trades, open_orders, config, result) -> list[Order | Cancel]:
    output = io.StringIO()
    start = time.perf_counter()
    try:
        with redirect_stdout(output) if config.capture_output else nullcontext():
            actions = bot.step(tick, dict(position), own_fills, market_trades, open_orders)
    except Exception:
        actions = []
        result.errors.append((tick.timestamp, traceback.format_exc()))
    result.step_seconds.append(time.perf_counter() - start)
    result.max_output_chars = max(result.max_output_chars, len(output.getvalue()))
    return actions


def _cancel(actions, resting: list[_Live], resting_mode: bool, timestamp, result) -> tuple[list[Order], list[_Live]]:
    """Applies the cancels. Returns the new orders and the orders still resting."""
    cancelled = set()
    live_ids = {order.id for order in resting}
    for action in actions:
        if not isinstance(action, Cancel):
            continue
        if action.order_id in live_ids - cancelled:
            cancelled.add(action.order_id)
            result.cancels.append((timestamp, action.order_id))
        else:
            hint = "" if resting_mode else " (orders only rest in resting mode)"
            result.errors.append((timestamp, f"cancel for order {action.order_id}, which isn't open{hint}"))
    orders = [action for action in actions if not isinstance(action, Cancel)]
    return orders, [order for order in resting if order.id not in cancelled]


def _within_limits(orders, position, resting, limits, timestamp, result) -> list[Order]:
    """Drops orders for unknown products, and every new order for a product that could breach its limit.

    Resting orders count towards the limit. They always fit, as fills move the position and
    shrink the order by the same amount.
    """
    buys: dict[str, int] = defaultdict(int)
    sells: dict[str, int] = defaultdict(int)
    traded = set()
    for order in orders:
        if order.product not in limits:
            result.errors.append((timestamp, f"order for unknown product {order.product!r}"))
        elif order.quantity:
            traded.add(order.product)
            if order.quantity > 0:
                buys[order.product] += order.quantity
            else:
                sells[order.product] -= order.quantity
    for order in resting:
        if order.quantity > 0:
            buys[order.product] += order.quantity
        else:
            sells[order.product] -= order.quantity

    breached = {
        product
        for product in traded
        if position[product] + buys[product] > limits[product]
        or position[product] - sells[product] < -limits[product]
    }
    result.limit_breaches.extend((timestamp, product) for product in sorted(breached))
    return [
        order
        for order in orders
        if order.product in limits and order.quantity != 0 and order.product not in breached
    ]


def _liquidity(tick: Tick, fill_ratio: float, rng: random.Random):
    """Mutable copies of what this tick's orders can trade against.

    Books become [price, volume] levels. Market trades become
    [trade, available volume, left for our buys, left for our sells]: our buy takes the
    trade's seller, our sell takes its buyer.
    """

    def available(volume: int) -> int:
        return volume if fill_ratio >= 1 else rng.binomialvariate(volume, fill_ratio)

    books = {}
    for product in sorted(tick.books):
        book = tick.books[product]
        books[product] = (
            [[price, available(volume)] for price, volume in book.bids],
            [[price, available(volume)] for price, volume in book.asks],
        )

    trades = {}
    for product in sorted(tick.trades):
        entries = []
        for trade in tick.trades[product]:
            volume = available(trade.quantity)
            entries.append([trade, volume, volume, volume])
        trades[product] = entries

    return books, trades


def _take_book(order: _Live, books, timestamp: int) -> list[Fill]:
    """Trades the order against the visible book at the book's prices, best first."""
    buying = order.quantity > 0
    sign = 1 if buying else -1
    fills = []
    bids, asks = books.get(order.product, ([], []))
    for level in asks if buying else bids:
        price, volume = level
        if (price > order.price) if buying else (price < order.price):
            break
        take = min(abs(order.quantity), volume)
        if take == 0:
            continue
        level[1] -= take
        order.quantity -= sign * take
        fills.append(Fill(timestamp, order.product, price, sign * take, "book", "", order.id))
        if order.quantity == 0:
            break
    return fills


def _take_trades(order: _Live, trades, matching: TradeMatching, timestamp: int) -> list[Fill]:
    """Fills what's left of the order against market trades at its price or worse, at its own price."""
    if matching is TradeMatching.NONE or order.quantity == 0:
        return []
    buying = order.quantity > 0
    sign = 1 if buying else -1
    side = 2 if buying else 3
    fills = []
    for entry in trades.get(order.product, []):
        trade = entry[0]
        better = trade.price < order.price if buying else trade.price > order.price
        if not (better or (trade.price == order.price and matching is TradeMatching.ALL)):
            continue
        take = min(abs(order.quantity), entry[side])
        if take == 0:
            continue
        entry[side] -= take
        order.quantity -= sign * take
        counterparty = trade.seller if buying else trade.buyer
        fills.append(Fill(timestamp, order.product, order.price, sign * take, "trade", counterparty, order.id))
        if order.quantity == 0:
            break
    return fills


def _remaining_trades(trades) -> dict[str, list[MarketTrade]]:
    """Market trades as the bot sees them next tick: minus the volume our orders took over."""
    remaining = {}
    for product, entries in trades.items():
        left = [
            replace(trade, quantity=trade.quantity - (available - min(for_buys, for_sells)))
            for trade, available, for_buys, for_sells in entries
        ]
        remaining[product] = [trade for trade in left if trade.quantity > 0]
    return remaining


def _mark(tick: Tick, product: str, last: float) -> float:
    if product in tick.marks:
        return tick.marks[product]
    book = tick.books.get(product)
    mid = book.mid if book else None
    return last if mid is None else mid


# ---------------------------------------------------------------------------- resting mode


def _priority(orders: list[_Live], buying: bool) -> list[_Live]:
    """Price-time priority: best price first, then the oldest."""
    side = [order for order in orders if (order.quantity > 0) == buying]
    return sorted(side, key=lambda order: (-order.price if buying else order.price, order.id))


def _cross(resting: list[_Live], books, timestamp: int):
    """Fills resting orders that the new snapshot's other side reaches, at the resting price.

    Returns the fills and the volume taken from each level, as {(product, buying, price): volume}.
    """
    fills = []
    taken: dict[tuple[str, bool, float], int] = defaultdict(int)
    for product in sorted({order.product for order in resting}):
        bids, asks = books.get(product, ([], []))
        for buying, levels in ((True, asks), (False, bids)):
            sign = 1 if buying else -1
            for order in _priority([o for o in resting if o.product == product], buying):
                for level in levels:
                    price, volume = level
                    if (price > order.price) if buying else (price < order.price):
                        break
                    take = min(abs(order.quantity), volume)
                    if take == 0:
                        continue
                    level[1] -= take
                    order.quantity -= sign * take
                    taken[(product, buying, price)] += take
                    fills.append(Fill(timestamp, product, order.price, sign * take, "cross", "", order.id))
                    if order.quantity == 0:
                        break
    return fills, taken


def _without(tick: Tick, taken) -> Tick:
    """The tick as the bot sees it: without the levels resting orders just traded with."""
    if not taken:
        return tick
    books = dict(tick.books)
    for product in {product for product, _, _ in taken}:
        book = books[product]
        books[product] = Book(
            bids=_minus(book.bids, [taken.get((product, False, price), 0) for price, _ in book.bids]),
            asks=_minus(book.asks, [taken.get((product, True, price), 0) for price, _ in book.asks]),
        )
    return replace(tick, books=books)


def _minus(levels, used) -> tuple:
    return tuple((price, volume - u) for (price, volume), u in zip(levels, used) if volume > u)


def _volume_at(order: _Live, books: dict[str, Book]) -> int:
    """Visible volume at the order's price on its own side: what's queued in front of a new order."""
    book = books.get(order.product)
    levels = (book.bids if order.quantity > 0 else book.asks) if book else ()
    return next((volume for price, volume in levels if price == order.price), 0)


def _requeue(resting: list[_Live], books: dict[str, Book]) -> None:
    """Moves resting orders up their queue when the new snapshot shows less volume in front of them."""
    for order in resting:
        book = books.get(order.product)
        if not book:
            continue
        buying = order.quantity > 0
        levels = book.bids if buying else book.asks
        if not levels or ((order.price > levels[0][0]) if buying else (order.price < levels[0][0])):
            order.ahead = 0  # nothing visible at its price or better: it's at the front
            continue
        volume = next((volume for price, volume in levels if price == order.price), None)
        if volume is not None:
            order.ahead = min(order.ahead, volume)
        elif (order.price > levels[-1][0]) if buying else (order.price < levels[-1][0]):
            order.ahead = 0  # its level is inside the visible depth but empty
        # else: below the visible depth, so nothing is known: keep the estimate


def _fill_resting(resting: list[_Live], trades, matching: TradeMatching, timestamp: int) -> list[Fill]:
    """Fills resting orders against this tick's market trades, in price-time priority."""
    if matching is TradeMatching.NONE:
        return []
    fills = []
    for product, entries in trades.items():
        mine = [order for order in resting if order.product == product]
        buys, sells = _priority(mine, True), _priority(mine, False)
        for entry in entries:
            entry[2] = _fill_queue(buys, entry[0], entry[2], True, matching, timestamp, fills)
            entry[3] = _fill_queue(sells, entry[0], entry[3], False, matching, timestamp, fills)
    return fills


def _fill_queue(queue: list[_Live], trade: MarketTrade, left: int, buying: bool, matching, timestamp, fills) -> int:
    """Fills one side's resting orders from a market trade. Returns the trade volume left over."""
    sign = 1 if buying else -1
    for order in queue:
        if left == 0:
            break
        size = abs(order.quantity)
        if size == 0:
            continue
        if (order.price > trade.price) if buying else (order.price < trade.price):
            take = min(left, size)  # the trade went through its price, so it would have filled first
            order.ahead = 0
        elif order.price == trade.price and matching is TradeMatching.ALL:
            # The trade reaches the queue at this price after our better-priced orders took their
            # share. The volume ahead of this order goes first; our earlier orders here already
            # took theirs from `left`.
            take = max(0, min(size, left - order.ahead))
            order.ahead = max(0, order.ahead - left)
        else:
            break
        if take:
            order.quantity -= sign * take
            left -= take
            counterparty = trade.seller if buying else trade.buyer
            fills.append(Fill(timestamp, trade.product, order.price, sign * take, "trade", counterparty, order.id))
    return left
