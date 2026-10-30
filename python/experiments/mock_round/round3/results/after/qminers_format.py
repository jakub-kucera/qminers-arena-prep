"""The Arena's format, as the rehearsal's round 1 ("Kestrel Bourse", data/arena/round1/rules.md) defines it.

Filled in by ON_THE_DAY.md, "The format swap, step by step" (2026-10-30). The loader half takes book changes,
as drill.py's does, but level-indexed; the wrapper half calls module-level functions with an object kept all
session, as no earlier format did.

Data layout (rules.md, section 2):
    <data>/instruments.csv            symbol,description,tick,decimals,limit
    <data>/<YYYY-MM-DD>/book.csv      clock,symbol,side,level,price,size
                                      a row only when that level (1..3 a side) changed since the previous
                                      step; size 0 with an empty price empties the level
    <data>/<YYYY-MM-DD>/prints.csv    clock,symbol,price,size,aggressor (BUY, SELL or empty)
`<data>` is the round's folder (data/arena/round<N>/) or its `data/` subfolder.

Units: prices in the engine are whole units of 1 / PRICE_SCALE points (0.01, the finest tick); `Day.info`
gives each product's tick, that unit and its decimals. One point is 2 credits a lot (POINT_VALUE): the
engine's money is in points, the portal's in credits. Step n of a session's 6,000 is timestamp
n * 1,000,000 // 6,000. Prints at a step's clock are trades after that step's book was published, so they
are the tick's own trades: our orders sent at step n meet them, and the bot sees them at step n + 1.

Bot API (rules.md, section 3): module-level `setup(ctx)` (optional) and `step(ctx, view) -> list` of action
dicts ({"type": "limit", "cid", "symbol", "side", "price", "size", "tif"} or {"type": "cancel", "cid"}).
The module is imported fresh for every session and `ctx` lives the whole session; nothing else is kept.
"""

from __future__ import annotations

import ast
import csv
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace

from arena.botfile import BotFile
from arena.model import Book, Cancel, Day, MarketTrade, OpenOrder, Order, Tick

PROVIDED_MODULES: set[str] = set()  # their bot file imports nothing of theirs
RESTING = True  # GTC orders rest until filled or cancelled (rules.md, section 3)
# The settings their rules fix (rules.md, sections 3 and 4): taker 2 bps, maker rebate 0.5 bps; a breach is
# charged 0.25 credits a lot a step (0.125 points), not rejected; 6 actions a step, 3 orders working a product.
# Fitted to upload 1 (2026-10-30 13:02, experiments.day.calibrate --scale 0.02 --vary delay=0,1; 0.0% off on all
# 12 portal figures): trade_matching "worse", delay 1 (orders reach the exchange a step late: the orders CSV
# stamps step 0's at 10:00:00.250), mark "last" (mid 0.9% off, touch 3.9%), no depletion (14.9% off). The queue
# model (back, prob, front) can't be told apart under "worse": left at the engine's default, "back".
ENGINE: dict = {"trade_matching": "worse", "mark": "last", "delay": 1, "fee_bps": 2.0, "maker_fee_bps": -0.5, "limit_penalty": 0.125,
                "max_actions": 6, "max_resting": 3}
SKELETON = False
FILES = {"instruments": "instruments.csv", "book": "book.csv", "prints": "prints.csv"}
PRICE_SCALE = 100  # engine units a point
POINT_VALUE = 2.0  # credits a point a lot
STEPS = 6000
STEP_MS = 250
OPEN_MS = 10 * 3600 * 1000  # 10:00:00.000
MAX_ACTIONS, MAX_RESTING = 6, 3
ENTRY = (None, "step")
TAKER = "taker"  # the print's aggressor, shown as its buyer or seller
LEVELS = 3

# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = Path(arg)
    for candidate in (path, path / "data"):
        if (candidate / FILES["instruments"]).is_file():
            return candidate
    raise ValueError(f"not a qminers data folder (no {FILES['instruments']} in it or in its data/): {path}")


def list_days(data_dir: Path) -> list[str]:
    return sorted(p.name for p in data_dir.iterdir() if p.is_dir() and (p / FILES["book"]).is_file())


def load_days(data_dir: Path, specs: list[str]) -> list[Day]:
    """Each spec is a session's date (2026-09-14), its index in date order (0, 1, ...), or `all`."""
    available = list_days(data_dir)
    selected: list[str] = []
    for spec in specs:
        if spec == "all":
            names = available
        elif spec in available:
            names = [spec]
        elif re.fullmatch(r"\d+", spec) and int(spec) < len(available):
            names = [available[int(spec)]]
        else:
            names = []
        if not names:
            raise ValueError(f"no session {spec!r} in {data_dir}. Available: {', '.join(available)} (or an index, or all)")
        selected += [n for n in names if n not in selected]
    instruments = _instruments(data_dir)
    return [_load_day(data_dir / name, name, instruments) for name in selected]


def _instruments(data_dir: Path) -> dict[str, dict]:
    out = {}
    with (data_dir / FILES["instruments"]).open(newline="") as file:
        for row in csv.DictReader(file):
            tick = Decimal(row["tick"])
            if (tick * PRICE_SCALE) % 1:
                raise ValueError(f"{row['symbol']}: tick {tick} is finer than 1/{PRICE_SCALE}: raise PRICE_SCALE")
            out[row["symbol"]] = {"tick": tick, "decimals": int(row["decimals"]), "limit": int(row["limit"])}
    if not out:
        raise ValueError(f"{data_dir / FILES['instruments']}: no instruments")
    return out


def step_of(clock: str, where: str) -> int:
    match = re.fullmatch(r"(\d\d):(\d\d):(\d\d)\.(\d\d\d)", clock)
    if not match:
        raise ValueError(f"{where}: bad clock {clock!r}")
    h, m, s, ms = map(int, match.groups())
    elapsed = (h * 3600 + m * 60 + s) * 1000 + ms - OPEN_MS
    if elapsed % STEP_MS or not 0 <= elapsed // STEP_MS < STEPS:
        raise ValueError(f"{where}: clock {clock} is not a step of the session")
    return elapsed // STEP_MS


def timestamp_of(step: int) -> int:
    return step * 1_000_000 // STEPS


def clock_of(step: int) -> str:
    ms = OPEN_MS + step * STEP_MS
    return f"{ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def _load_day(path: Path, name: str, instruments: dict[str, dict]) -> Day:
    changes: dict[int, list[tuple[str, str, int, int | None, int]]] = defaultdict(list)
    where_book = path / FILES["book"]
    with where_book.open(newline="") as file:
        for line_no, row in enumerate(csv.DictReader(file), 2):
            where = f"{where_book}:{line_no}"
            sym = row["symbol"]
            if sym not in instruments:
                raise ValueError(f"{where}: {sym!r} is not in {FILES['instruments']}")
            if row["side"] not in ("bid", "ask"):
                raise ValueError(f"{where}: bad side {row['side']!r}")
            level, size = int(row["level"]), int(row["size"])
            if not 1 <= level <= LEVELS:
                raise ValueError(f"{where}: level {level} outside 1..{LEVELS}")
            price = _units(row["price"], instruments[sym]["tick"], where) if size else None
            changes[step_of(row["clock"], where)].append((sym, row["side"], level, price, size))
    trades: dict[int, dict[str, list[MarketTrade]]] = defaultdict(lambda: defaultdict(list))
    where_prints = path / FILES["prints"]
    if where_prints.is_file():
        with where_prints.open(newline="") as file:
            for line_no, row in enumerate(csv.DictReader(file), 2):
                where = f"{where_prints}:{line_no}"
                n, sym = step_of(row["clock"], where), row["symbol"]
                if sym not in instruments:
                    raise ValueError(f"{where}: {sym!r} is not in {FILES['instruments']}")
                aggressor = row["aggressor"]
                buyer, seller = (TAKER, "") if aggressor == "BUY" else ("", TAKER) if aggressor == "SELL" else ("", "")
                trades[n][sym].append(MarketTrade(sym, _units(row["price"], instruments[sym]["tick"], where), int(row["size"]), buyer, seller, timestamp_of(n)))
    levels = {sym: {"bid": [None] * LEVELS, "ask": [None] * LEVELS} for sym in instruments}
    ticks = []
    for n in range(STEPS):
        for sym, side, level, price, size in changes.get(n, ()):
            levels[sym][side][level - 1] = (price, size) if size else None
        books = {}
        for sym, sides in levels.items():
            bids = tuple(sorted((lv for lv in sides["bid"] if lv), reverse=True))
            asks = tuple(sorted(lv for lv in sides["ask"] if lv))
            if bids or asks:
                books[sym] = Book(bids, asks)
        ticks.append(Tick(timestamp_of(n), books, {s: list(ts) for s, ts in trades.get(n, {}).items()}, {}))  # no marks: the engine's mark
    info = {sym: {"tick": float(spec["tick"]), "unit": 1 / PRICE_SCALE, "decimals": spec["decimals"]} for sym, spec in instruments.items()}
    return Day(name, sorted(instruments), {sym: spec["limit"] for sym, spec in instruments.items()}, ticks, info)


def _units(text: str, tick: Decimal, where: str) -> int:
    try:
        price = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{where}: bad price {text!r}") from None
    if price <= 0 or price % tick:
        raise ValueError(f"{where}: price {text} is not a positive multiple of the {tick} tick")
    return int(price * PRICE_SCALE)


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return ArenaBot(BotFile(path, {}, overrides, strict), fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    if any(isinstance(node, ast.FunctionDef) and node.name == "step" for node in tree.body):
        return []
    return ["no top-level function step"]


class ArenaBot:
    """Calls the bot file's `step(ctx, view)` once a step and turns its action dicts into engine orders.

    The module is loaded afresh for every session (begin_day) and `ctx` lives the session, so the state their
    exchange keeps is exactly what survives here; `fresh_each_tick` changes nothing (no state is lost between
    steps of a session). Actions follow rules.md, section 3: the first MAX_ACTIONS in list order, cancels before
    new orders; a malformed action, a repeated cid or a cancel of a cid never sent raises (their exchange drops
    it and logs it; ours stops the step, so a bug shows in the backtest).
    """

    max_state_chars = 0  # state lives on ctx, not in a string

    def __init__(self, bot_file: BotFile, fresh_each_tick: bool = False):
        self._file = bot_file
        self._module = bot_file.load()
        self._day: Day | None = None

    def begin_day(self, day: Day) -> None:
        self._day = day
        self._module = self._file.load()  # imported fresh for every session
        self._steps = {t.timestamp: n for n, t in enumerate(day.ticks)}
        self._used: set[str] = set()
        self._last_trades: dict[str, list[MarketTrade]] = {}
        self.ctx = SimpleNamespace(
            session=day.name, steps=len(day.ticks), step_ms=STEP_MS, point_value=POINT_VALUE, max_actions=MAX_ACTIONS,
            max_resting=MAX_RESTING,
            instruments={p: {"tick": day.info[p]["tick"], "decimals": day.info[p]["decimals"], "limit": day.limits[p]} for p in day.products},
        )
        setup = getattr(self._module, "setup", None)
        if setup is not None:
            setup(self.ctx)

    def step(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        day = self._day
        n = self._steps.get(tick.timestamp, 0)
        book = {p: {"bid": [(_price(x), v) for x, v in b.bids], "ask": [(_price(x), v) for x, v in b.asks]} for p, b in tick.books.items()}
        prints = [
            {"symbol": p, "price": _price(t.price), "size": t.quantity, "aggressor": "BUY" if t.buyer == TAKER else "SELL" if t.seller == TAKER else ""}
            for p in sorted(market_trades) for t in market_trades[p]
        ]
        executions = [
            {"cid": f.tag, "symbol": f.product, "side": "BUY" if f.quantity > 0 else "SELL", "price": _price(f.price), "size": abs(f.quantity),
             "liquidity": "TAKER" if f.source == "book" else "MAKER"}
            for f in own_fills
        ]
        working = [
            {"cid": o.tag, "symbol": o.product, "side": "BUY" if o.quantity > 0 else "SELL", "price": _price(o.price), "remaining": abs(o.quantity)}
            for o in open_orders
        ]
        view = {
            "step": n, "clock": clock_of(n), "book": book, "prints": prints,
            "position": {p: positions.get(p, 0) for p in day.products}, "executions": executions, "working": working,
        }
        returned = self._module.step(self.ctx, view)
        if returned is None:
            return []
        if not isinstance(returned, list):
            raise TypeError(f"step must return a list of action dicts, not {type(returned).__name__}")
        actions = returned[:MAX_ACTIONS]  # actions after the 6th are dropped (rules.md, section 3)
        live = {o.tag: o.id for o in open_orders}
        cancels: list[Cancel] = []
        orders: list[Order] = []
        sent: set[str] = set()
        for action in actions:
            kind = action.get("type") if isinstance(action, dict) else None
            if kind == "cancel":
                cid = action.get("cid")
                if cid in live:
                    cancels.append(Cancel(live.pop(cid)))
                elif cid not in self._used:
                    raise ValueError(f"cancel {cid!r}: a cid never sent")
            elif kind == "limit":
                orders.append(self._order(action, sent))
            else:
                raise ValueError(f"bad action {action!r}: type must be 'limit' or 'cancel'")
        return [*cancels, *orders]

    def _order(self, action: dict, sent: set[str]) -> Order:
        cid, sym, side, size = action.get("cid"), action.get("symbol"), action.get("side"), action.get("size")
        if not isinstance(cid, str) or not 1 <= len(cid) <= 32:
            raise ValueError(f"bad cid {cid!r}: a string of 1-32 characters")
        if cid in self._used or cid in sent:
            raise ValueError(f"cid {cid!r} repeats one used earlier in the session")
        if sym not in self._day.limits:
            raise ValueError(f"unknown symbol {sym!r}")
        if side not in ("BUY", "SELL"):
            raise ValueError(f"{sym}: side must be BUY or SELL, not {side!r}")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"{sym}: size must be a positive int, not {size!r}")
        tif = action.get("tif", "GTC")
        if tif not in ("GTC", "IOC"):
            raise ValueError(f"{sym}: tif must be GTC or IOC, not {tif!r}")
        units = _units(str(action.get("price")), Decimal(str(self._day.info[sym]["tick"])), f"{sym} order {cid}")
        sent.add(cid)
        self._used.add(cid)
        return Order(sym, units, size if side == "BUY" else -size, tif == "IOC", tag=cid)


def _price(units: float) -> float:
    return round(units / PRICE_SCALE, 10)
