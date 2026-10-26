"""The Arena's format, as its Technical Rules describe it (data/arena/round1/rules.md).

Data layout (`--data` is the folder holding instruments.csv):
    <data>/instruments.csv          symbol,tick_size,position_limit,currency
    <data>/<YYYY-MM-DD>/depth.csv   seq,time,symbol,side,level,price,size   (one row per level)
    <data>/<YYYY-MM-DD>/prints.csv  seq,time,symbol,price,size,aggressor     (BUY, SELL or empty)

Day specs: a session's date, its 0-based index among the folder's sessions, a range `0..2`, or `all`.

Engine mapping:
- **Prices are integer cents** (PRICE_UNIT) for every product, so they compare exactly and PnL is
  in cents; `Day.info` gives each product's tick and the unit.
- **Timestamps are seq × 100**, so a 10,000-step session spans 0..999,900 as a Prosperity day.
- **Prints between snapshots seq and seq + 1 are tick seq's trades**: orders placed at seq can
  fill against them, and the bot sees them at seq + 1 (rules §2, §4.4). The aggressor is kept as
  the trade's buyer or seller, TAKER.
- **Orders rest** (GTC by default, RESTING); a print fills a resting order only when strictly
  through its price, so the rules' fill model is `--resting --match-trades worse`.

The bot API (rules §3): a module-level `trade(snapshot, memory) -> list[dict]` and an optional
`init(session) -> dict`. `memory` is stored as JSON after each successful call and handed back as a
copy; a call that raises keeps the old memory. Invalid actions are rejected one by one, as the
exchange does; in strict mode they raise instead, so the validator sees them.
"""

from __future__ import annotations

import ast
import csv
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from arena.botfile import BotFile
from arena.model import Book, Cancel, Day, MarketTrade, OpenOrder, Order, Tick

PROVIDED_MODULES: set[str] = set()
RESTING = True
TAKER = "taker"
PRICE_UNIT = Decimal("0.01")
STEP_TIME = 100  # engine timestamp per seq
MAX_ACTIONS = 50
MAX_MEMORY_CHARS = 100_000
MAX_ID_CHARS = 32

# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = Path(arg)
    if (path / "data" / "instruments.csv").is_file():
        path = path / "data"
    if not (path / "instruments.csv").is_file():
        raise ValueError(f"not an Arena data folder (no instruments.csv): {path}")
    return path


def list_sessions(data_dir: Path) -> list[str]:
    return sorted(p.name for p in data_dir.iterdir() if p.is_dir() and (p / "depth.csv").is_file())


def load_days(data_dir: Path, specs: list[str]) -> list[Day]:
    available = list_sessions(data_dir)
    selected: list[str] = []
    for spec in specs:
        if spec == "all":
            names = available
        elif spec in available:
            names = [spec]
        elif match := re.fullmatch(r"(\d+)(?:\.\.(\d+))?", spec):
            low, high = int(match[1]), int(match[2] or match[1])
            names = available[low : high + 1]
        else:
            names = []
        if not names:
            raise ValueError(f"no session {spec!r} in {data_dir}. Available: {', '.join(available)} (or 0..{len(available) - 1}, all)")
        selected += [n for n in names if n not in selected]
    instruments = _instruments(data_dir)
    return [_load_session(data_dir / name, name, instruments) for name in selected]


def _instruments(data_dir: Path) -> dict[str, tuple[Decimal, int]]:
    out = {}
    with (data_dir / "instruments.csv").open() as file:
        for row in csv.DictReader(file):
            tick = Decimal(row["tick_size"])
            if tick % PRICE_UNIT:
                raise ValueError(f"{row['symbol']}: tick {tick} is not a multiple of the price unit {PRICE_UNIT}")
            if not row.get("position_limit"):
                raise ValueError(f"{row['symbol']}: no position limit")
            out[row["symbol"]] = (tick, int(row["position_limit"]))
    return out


def _units(px: str, tick: Decimal, where: str) -> int:
    try:
        price = Decimal(px)
    except InvalidOperation:
        raise ValueError(f"{where}: bad price {px!r}") from None
    if price % tick:
        raise ValueError(f"{where}: price {px} is off the {tick} tick grid")
    return int(price / PRICE_UNIT)


def _load_session(folder: Path, name: str, instruments: dict[str, tuple[Decimal, int]]) -> Day:
    levels: dict[int, dict[str, dict[str, list[tuple[int, int, int]]]]] = defaultdict(lambda: defaultdict(lambda: {"BID": [], "ASK": []}))
    last_seq = -1
    with (folder / "depth.csv").open() as file:
        for line_no, row in enumerate(csv.DictReader(file), 2):
            sym = row["symbol"]
            if sym not in instruments:
                raise ValueError(f"{folder}/depth.csv:{line_no}: {sym!r} is not in instruments.csv")
            seq = int(row["seq"])
            last_seq = max(last_seq, seq)
            price = _units(row["price"], instruments[sym][0], f"{folder}/depth.csv:{line_no}")
            levels[seq][sym][row["side"]].append((int(row["level"]), price, int(row["size"])))
    trades: dict[int, dict[str, list[MarketTrade]]] = defaultdict(lambda: defaultdict(list))
    prints = folder / "prints.csv"
    if prints.is_file():
        with prints.open() as file:
            for line_no, row in enumerate(csv.DictReader(file), 2):
                sym, seq = row["symbol"], int(row["seq"])
                if sym not in instruments:
                    raise ValueError(f"{prints}:{line_no}: {sym!r} is not in instruments.csv")
                price = _units(row["price"], instruments[sym][0], f"{prints}:{line_no}")
                aggressor = row.get("aggressor", "")
                buyer, seller = (TAKER, "") if aggressor == "BUY" else ("", TAKER) if aggressor == "SELL" else ("", "")
                trades[seq][sym].append(MarketTrade(sym, price, int(row["size"]), buyer, seller, seq * STEP_TIME))
    ticks = []
    for seq in range(last_seq + 1):
        books = {}
        for sym, sides in levels.get(seq, {}).items():
            bids = tuple((p, v) for _, p, v in sorted(sides["BID"]))
            asks = tuple((p, v) for _, p, v in sorted(sides["ASK"]))
            if bids or asks:
                books[sym] = Book(bids, asks)
        ticks.append(Tick(seq * STEP_TIME, books, dict(trades.get(seq, {})), {}))  # no marks: the engine values at the mid
    info = {sym: {"tick": float(tick), "unit": float(PRICE_UNIT)} for sym, (tick, _) in instruments.items()}
    return Day(name, sorted(instruments), {sym: limit for sym, (_, limit) in instruments.items()}, ticks, info)


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return QminersBot(BotFile(path, {}, overrides, strict), strict, fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    return [] if "trade" in names else ["no top-level function trade(snapshot, memory)"]


class InvalidAction(ValueError):
    pass


class QminersBot:
    """Calls the bot's `trade(snapshot, memory)` once a step and turns its actions into engine orders."""

    def __init__(self, bot_file: BotFile, strict: bool, fresh_each_tick: bool = False):
        self._file = bot_file
        self._strict = strict
        self._fresh = fresh_each_tick
        self._module = bot_file.load()
        self._info: dict[str, dict] = {}
        self._limits: dict[str, int] = {}
        self._memory = "{}"
        self._used_ids: set[str] = set()
        self._auto = 0
        self.max_state_chars = 0
        self.rejected: list[str] = []

    def begin_day(self, day: Day) -> None:
        self._info, self._limits = day.info, day.limits
        session = {
            "date": day.name,
            "instruments": {sym: {"tick_size": self._info[sym]["tick"], "position_limit": day.limits[sym]} for sym in day.products},
        }
        init = getattr(self._module, "init", None)
        memory = init(session) if callable(init) else {}
        self._store({} if memory is None else memory)

    def _store(self, memory) -> None:
        text = json.dumps(memory)
        if len(text) > MAX_MEMORY_CHARS:
            raise ValueError(f"memory is {len(text):,} characters serialised, over {MAX_MEMORY_CHARS:,}")
        self.max_state_chars = max(self.max_state_chars, len(text))
        self._memory = text

    def step(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        if self._fresh:
            self._module = self._file.load()
        snapshot = self._snapshot(tick, positions, own_fills, market_trades, open_orders)
        memory = json.loads(self._memory)
        actions = self._module.trade(snapshot, memory)
        out = self._actions(actions, open_orders)  # raises in strict mode: then the old memory stays
        self._store(memory)
        return out

    # The snapshot: prices back to the exchange's decimals.
    def _px(self, sym: str, units: float) -> float:
        return round(units * self._info[sym]["unit"], 10)

    def _snapshot(self, tick, positions, own_fills, market_trades, open_orders) -> dict:
        books = {}
        for sym in self._limits:
            book = tick.books.get(sym, Book())
            books[sym] = {"bids": [[self._px(sym, p), v] for p, v in book.bids], "asks": [[self._px(sym, p), v] for p, v in book.asks]}
        prints = {}
        for sym, trades in market_trades.items():
            if trades:
                prints[sym] = [
                    {"price": self._px(sym, t.price), "size": t.quantity, "aggressor": "BUY" if t.buyer == TAKER else "SELL" if t.seller == TAKER else ""}
                    for t in trades
                ]
        return {
            "seq": tick.timestamp // STEP_TIME,
            "time": _clock(tick.timestamp // STEP_TIME),
            "books": books,
            "prints": prints,
            "positions": {sym: positions.get(sym, 0) for sym in self._limits},
            "fills": [
                {"id": f.tag, "symbol": f.product, "side": "BUY" if f.quantity > 0 else "SELL", "price": self._px(f.product, f.price), "size": abs(f.quantity)}
                for f in own_fills
            ],
            "orders": [
                {"id": o.tag, "symbol": o.product, "side": "BUY" if o.quantity > 0 else "SELL", "price": self._px(o.product, o.price), "remaining": abs(o.quantity)}
                for o in open_orders
            ],
        }

    def _reject(self, message: str) -> None:
        if self._strict:
            raise InvalidAction(message)
        self.rejected.append(message)

    def _actions(self, actions, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        if not isinstance(actions, list):
            raise TypeError(f"trade must return a list of actions, not {type(actions).__name__}")
        if len(actions) > MAX_ACTIONS:
            self._reject(f"{len(actions)} actions in one step, over {MAX_ACTIONS}")
            actions = actions[:MAX_ACTIONS]  # assumed: the rules don't say what happens to the rest
        resting = {o.tag: o for o in open_orders}
        cancels: list[Cancel] = []
        new: list[Order] = []
        for action in actions:
            if not isinstance(action, dict):
                self._reject(f"action is not a dict: {action!r}")
                continue
            kind = action.get("action")
            if kind == "cancel":
                order = resting.pop(action.get("id"), None)
                if order is None:
                    self._reject(f"cancel {action.get('id')!r}: not resting")
                    continue
                cancels.append(Cancel(order.id))
            elif kind == "new":
                order = self._new(action)
                if order is not None:
                    new.append(order)
            else:
                self._reject(f"unknown action {kind!r}")
        return [*cancels, *new]

    def _new(self, action: dict) -> Order | None:
        sym, side, size = action.get("symbol"), action.get("side"), action.get("size")
        if sym not in self._limits:
            return self._reject(f"unknown symbol {sym!r}")
        if side not in ("BUY", "SELL"):
            return self._reject(f"{sym}: side {side!r}")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            return self._reject(f"{sym}: size {size!r} is not a positive int")
        tif = action.get("tif", "GTC")
        if tif not in ("GTC", "IOC"):
            return self._reject(f"{sym}: tif {tif!r}")
        price = action.get("price")
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
            return self._reject(f"{sym}: price {price!r}")
        meta = self._info[sym]
        units = price / meta["unit"]
        step = round(meta["tick"] / meta["unit"])
        if abs(units - round(units)) > 1e-6 or round(units) % step:
            return self._reject(f"{sym}: price {price} is off its {meta['tick']} tick grid")
        order_id = action.get("id")
        if order_id is None:
            self._auto += 1
            order_id = f"auto{self._auto}"
        elif not isinstance(order_id, str) or len(order_id) > MAX_ID_CHARS:
            return self._reject(f"{sym}: id {order_id!r} is not a string of at most {MAX_ID_CHARS} characters")
        if order_id in self._used_ids:
            return self._reject(f"{sym}: duplicate id {order_id!r}")
        self._used_ids.add(order_id)
        quantity = size if side == "BUY" else -size
        return Order(sym, round(units), quantity, tif == "IOC", tag=order_id)


def _clock(seq: int) -> str:
    ms = seq * 400
    seconds, ms = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{9 + hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"
