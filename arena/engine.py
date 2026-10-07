"""Replays a Day against a bot and simulates its fills.

The rules follow IMC Prosperity and were checked fill-for-fill against jmerle's prosperity3bt:
  1. Every tick the bot sees the book and returns orders.
  2. If a product's orders could breach its position limit (all its buys, or all its sells,
     filling), every order for that product is cancelled.
  3. Each order trades against the visible book at the book's prices, best price first.
  4. What's left can fill against that tick's market trades, at the order's own price
     (see TradeMatching).
  5. Anything still unfilled is cancelled: no order rests into the next tick.
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

from arena.model import Day, Fill, MarketTrade, Order, Tick


class TradeMatching(StrEnum):
    """Which market trades an order can fill against once the visible book is exhausted."""

    ALL = "all"  # trades at the order's price or worse
    WORSE = "worse"  # only trades strictly worse than the order's price (more conservative)
    NONE = "none"  # none: fills come from the visible book only


@dataclass(frozen=True)
class EngineConfig:
    trade_matching: TradeMatching = TradeMatching.ALL
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
    ) -> list[Order]:
        """Returns this tick's orders. own_fills and market_trades are from the previous tick."""
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
    fills: list[Fill] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)  # (timestamp, traceback or message)
    limit_breaches: list[tuple[int, str]] = field(default_factory=list)  # (timestamp, product)
    step_seconds: list[float] = field(default_factory=list)
    max_output_chars: int = 0


def run_day(day: Day, bot: Bot, config: EngineConfig = EngineConfig()) -> DayResult:
    result = DayResult(
        day.name,
        day.products,
        day.limits,
        positions={product: [] for product in day.products},
        marks={product: [] for product in day.products},
        pnl={product: [] for product in day.products},
    )
    rng = random.Random(config.seed)
    position = dict.fromkeys(day.products, 0)
    cash = dict.fromkeys(day.products, 0.0)
    mark = dict.fromkeys(day.products, 0.0)
    own_fills: list[Fill] = []
    market_trades: dict[str, list[MarketTrade]] = {}

    for tick in day.ticks:
        orders = _call_bot(bot, tick, position, own_fills, market_trades, config, result)
        orders = _within_limits(orders, position, day.limits, tick.timestamp, result)
        books, trades = _liquidity(tick, config.fill_ratio, rng)
        own_fills = [
            fill
            for order in orders
            for fill in _match(order, books, trades, config.trade_matching, tick.timestamp)
        ]
        market_trades = _remaining_trades(trades)

        for fill in own_fills:
            position[fill.product] += fill.quantity
            cash[fill.product] -= fill.price * fill.quantity
        result.fills.extend(own_fills)

        result.timestamps.append(tick.timestamp)
        for product in day.products:
            mark[product] = _mark(tick, product, mark[product])
            result.positions[product].append(position[product])
            result.marks[product].append(mark[product])
            result.pnl[product].append(cash[product] + position[product] * mark[product])

    return result


def _call_bot(bot, tick, position, own_fills, market_trades, config, result) -> list[Order]:
    output = io.StringIO()
    start = time.perf_counter()
    try:
        with redirect_stdout(output) if config.capture_output else nullcontext():
            orders = bot.step(tick, dict(position), own_fills, market_trades)
    except Exception:
        orders = []
        result.errors.append((tick.timestamp, traceback.format_exc()))
    result.step_seconds.append(time.perf_counter() - start)
    result.max_output_chars = max(result.max_output_chars, len(output.getvalue()))
    return orders


def _within_limits(orders, position, limits, timestamp, result) -> list[Order]:
    """Drops orders for unknown products, and every order for a product that could breach its limit."""
    buys: dict[str, int] = defaultdict(int)
    sells: dict[str, int] = defaultdict(int)
    for order in orders:
        if order.product not in limits:
            result.errors.append((timestamp, f"order for unknown product {order.product!r}"))
        elif order.quantity > 0:
            buys[order.product] += order.quantity
        elif order.quantity < 0:
            sells[order.product] -= order.quantity

    breached = {
        product
        for product in buys.keys() | sells.keys()
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


def _match(order: Order, books, trades, matching: TradeMatching, timestamp: int) -> list[Fill]:
    buying = order.quantity > 0
    sign = 1 if buying else -1
    left = abs(order.quantity)
    fills = []

    bids, asks = books.get(order.product, ([], []))
    for level in asks if buying else bids:  # best price first
        price, volume = level
        if (price > order.price) if buying else (price < order.price):
            break
        take = min(left, volume)
        if take == 0:
            continue
        level[1] -= take
        left -= take
        fills.append(Fill(timestamp, order.product, price, sign * take, "book"))
        if left == 0:
            return fills

    if matching is TradeMatching.NONE:
        return fills

    side = 2 if buying else 3
    for entry in trades.get(order.product, []):
        trade = entry[0]
        better = trade.price < order.price if buying else trade.price > order.price
        if not (better or (trade.price == order.price and matching is TradeMatching.ALL)):
            continue
        take = min(left, entry[side])
        if take == 0:
            continue
        entry[side] -= take
        left -= take
        counterparty = trade.seller if buying else trade.buyer
        fills.append(Fill(timestamp, order.product, order.price, sign * take, "trade", counterparty))
        if left == 0:
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
