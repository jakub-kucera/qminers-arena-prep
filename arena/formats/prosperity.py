"""IMC Prosperity format: semicolon-separated CSV data and a `Trader.run(state)` bot API.

Data layout (as in jmerle's backtesters):
    <data>/round<R>/prices_round_<R>_day_<D>.csv   book snapshots (3 levels a side) and mid price
    <data>/round<R>/trades_round_<R>_day_<D>.csv   market trades; Prosperity 2 adds _wn (with
                                                   trader names) and _nn (without) variants
Conversions (Prosperity 2 orchids, Prosperity 3 macarons) are not supported.
"""

from __future__ import annotations

import ast
import csv
import re
from collections import defaultdict
from pathlib import Path

from arena.botfile import BotFile
from arena.formats import prosperity_datamodel as dm
from arena.model import Book, Day, Fill, MarketTrade, Order, Tick

PROVIDED_MODULES = {"datamodel"}

_REFERENCES = Path(__file__).resolve().parents[2] / "references"
DATA_DIRS = {
    "p2": _REFERENCES / "prosperity2-backtester-jmerle" / "prosperity2bt" / "resources",
    "p3": _REFERENCES / "prosperity3-backtester-jmerle" / "prosperity3bt" / "resources",
}

LIMITS = {
    # Prosperity 2 (2024)
    "AMETHYSTS": 20,
    "STARFRUIT": 20,
    "ORCHIDS": 100,
    "CHOCOLATE": 250,
    "STRAWBERRIES": 350,
    "ROSES": 60,
    "GIFT_BASKET": 60,
    "COCONUT": 300,
    "COCONUT_COUPON": 600,
    # Prosperity 3 (2025)
    "RAINFOREST_RESIN": 50,
    "KELP": 50,
    "SQUID_INK": 50,
    "CROISSANTS": 250,
    "JAMS": 350,
    "DJEMBES": 60,
    "PICNIC_BASKET1": 60,
    "PICNIC_BASKET2": 100,
    "VOLCANIC_ROCK": 400,
    "VOLCANIC_ROCK_VOUCHER_9500": 200,
    "VOLCANIC_ROCK_VOUCHER_9750": 200,
    "VOLCANIC_ROCK_VOUCHER_10000": 200,
    "VOLCANIC_ROCK_VOUCHER_10250": 200,
    "VOLCANIC_ROCK_VOUCHER_10500": 200,
    "MAGNIFICENT_MACARONS": 75,
}

SUBMISSION = "SUBMISSION"  # how Prosperity names us in trades


# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = DATA_DIRS.get(arg, Path(arg))
    if not path.is_dir():
        hint = " (run references/clone.sh first)" if arg in DATA_DIRS else ""
        raise ValueError(f"data folder not found: {path}{hint}")
    return path


def list_days(data_dir: Path) -> list[tuple[int, int]]:
    pattern = re.compile(r"prices_round_(\d+)_day_(-?\d+)\.csv")
    days = []
    for path in data_dir.glob("round*/prices_round_*_day_*.csv"):
        if match := pattern.fullmatch(path.name):
            days.append((int(match[1]), int(match[2])))
    return sorted(days)


def parse_day_specs(specs: list[str], data_dir: Path) -> list[tuple[int, int]]:
    """`1` selects every day of round 1; `1-0` round 1 day 0; `1--1` round 1 day -1."""
    available = list_days(data_dir)
    selected: list[tuple[int, int]] = []
    for spec in specs:
        match = re.fullmatch(r"(\d+)(?:-(-?\d+))?", spec)
        if not match:
            raise ValueError(f"bad day {spec!r}: use ROUND or ROUND-DAY, e.g. 1, 1-0 or 1--1")
        round_num = int(match[1])
        days = [
            (r, d)
            for r, d in available
            if r == round_num and (match[2] is None or d == int(match[2]))
        ]
        if not days:
            listed = ", ".join(f"{r}-{d}" for r, d in available)
            raise ValueError(f"no data for {spec!r} in {data_dir}. Available: {listed}")
        selected.extend(day for day in days if day not in selected)
    return selected


def load_days(data_dir: Path, specs: list[str]) -> list[Day]:
    return [load_day(data_dir, r, d) for r, d in parse_day_specs(specs, data_dir)]


def load_day(data_dir: Path, round_num: int, day_num: int) -> Day:
    folder = data_dir / f"round{round_num}"
    books: dict[int, dict[str, Book]] = defaultdict(dict)
    marks: dict[int, dict[str, float]] = defaultdict(dict)
    with (folder / f"prices_round_{round_num}_day_{day_num}.csv").open(newline="") as file:
        rows = csv.reader(file, delimiter=";")
        next(rows)
        for row in rows:
            timestamp, product = int(row[1]), row[2]
            books[timestamp][product] = Book(
                bids=tuple(sorted(_levels(row, 3), reverse=True)),
                asks=tuple(sorted(_levels(row, 9))),
            )
            if row[15]:
                marks[timestamp][product] = float(row[15])

    trades: dict[int, dict[str, list[MarketTrade]]] = defaultdict(lambda: defaultdict(list))
    trades_path = _trades_file(folder, round_num, day_num)
    if trades_path:
        with trades_path.open(newline="") as file:
            rows = csv.reader(file, delimiter=";")
            next(rows)
            for row in rows:
                timestamp, product = int(row[0]), row[3]
                trades[timestamp][product].append(
                    MarketTrade(product, int(float(row[5])), int(row[6]), row[1], row[2], timestamp)
                )

    products = sorted({product for snapshot in books.values() for product in snapshot})
    unknown = [product for product in products if product not in LIMITS]
    if unknown:
        raise ValueError(f"no position limit known for {', '.join(unknown)}: add it to LIMITS")

    ticks = [
        Tick(timestamp, books[timestamp], dict(trades.get(timestamp, {})), marks[timestamp])
        for timestamp in sorted(books)
    ]
    return Day(f"r{round_num}d{day_num}", products, {p: LIMITS[p] for p in products}, ticks)


def _levels(row: list[str], start: int) -> list[tuple[int, int]]:
    """Up to three (price, volume) column pairs starting at column `start`."""
    levels = []
    for i in range(start, start + 6, 2):
        if not row[i]:
            break
        levels.append((int(float(row[i])), int(float(row[i + 1]))))
    return levels


def _trades_file(folder: Path, round_num: int, day_num: int) -> Path | None:
    stem = f"trades_round_{round_num}_day_{day_num}"
    for name in (f"{stem}_wn.csv", f"{stem}.csv", f"{stem}_nn.csv"):
        if (folder / name).exists():
            return folder / name
    return None


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return ProsperityBot(BotFile(path, {"datamodel": dm}, overrides, strict), fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Trader":
            if any(isinstance(item, ast.FunctionDef) and item.name == "run" for item in node.body):
                return []
            return ["class Trader has no run method"]
    return ["no top-level class Trader"]


class ProsperityBot:
    """Calls `Trader().run(state)` and converts between Prosperity's types and the engine's."""

    def __init__(self, bot_file: BotFile, fresh_each_tick: bool = False):
        self._bot_file = bot_file
        self._fresh_each_tick = fresh_each_tick
        self._trader = None if fresh_each_tick else bot_file.load().Trader()
        self._trader_data = ""
        self.max_state_chars = 0  # largest traderData returned

    def step(self, tick, positions, own_fills, market_trades) -> list[Order]:
        trader = self._bot_file.load().Trader() if self._fresh_each_tick else self._trader
        state = dm.TradingState(
            traderData=self._trader_data,
            timestamp=tick.timestamp,
            listings={product: dm.Listing(product, product, 1) for product in tick.books},
            order_depths={product: _order_depth(book) for product, book in tick.books.items()},
            own_trades=_own_trades(own_fills),
            market_trades={
                product: [dm.Trade(product, t.price, t.quantity, t.buyer, t.seller, t.timestamp) for t in trades]
                for product, trades in market_trades.items()
            },
            position={product: qty for product, qty in positions.items() if qty != 0},
            observations=dm.Observation({}, {}),
        )

        result = trader.run(state)
        if not (isinstance(result, tuple) and len(result) == 3):
            raise TypeError("Trader.run must return (orders, conversions, traderData)")
        orders, _conversions, trader_data = result
        if not isinstance(orders, dict):
            raise TypeError(f"orders must be a dict of symbol -> list[Order], got {type(orders).__name__}")
        if not isinstance(trader_data, str):
            raise TypeError(f"traderData must be a str, got {type(trader_data).__name__}")

        self._trader_data = trader_data
        self.max_state_chars = max(self.max_state_chars, len(trader_data))
        return _engine_orders(orders)


def _order_depth(book: Book) -> dm.OrderDepth:
    depth = dm.OrderDepth()
    depth.buy_orders = {price: volume for price, volume in book.bids}
    depth.sell_orders = {price: -volume for price, volume in book.asks}
    return depth


def _own_trades(fills: list[Fill]) -> dict[str, list[dm.Trade]]:
    trades: dict[str, list[dm.Trade]] = defaultdict(list)
    for fill in fills:
        buyer, seller = (SUBMISSION, fill.counterparty) if fill.quantity > 0 else (fill.counterparty, SUBMISSION)
        trades[fill.product].append(
            dm.Trade(fill.product, fill.price, abs(fill.quantity), buyer, seller, fill.timestamp)
        )
    return dict(trades)


def _engine_orders(orders: dict) -> list[Order]:
    converted = []
    for symbol, product_orders in orders.items():
        for order in product_orders:
            if not (
                isinstance(order.symbol, str)
                and isinstance(order.price, int)
                and isinstance(order.quantity, int)
            ):
                raise TypeError(
                    f"order {order!r}: symbol must be a str, price and quantity ints "
                    f"(got {type(order.price).__name__} price, {type(order.quantity).__name__} quantity)"
                )
            if order.symbol != symbol:
                raise ValueError(f"order {order!r} is listed under {symbol!r}")
            converted.append(Order(order.symbol, order.price, order.quantity))
    return converted
