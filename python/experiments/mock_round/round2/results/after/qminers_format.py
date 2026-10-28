"""The Arena's format: the Halden Exchange (data/arena/round1/rules.md), registered as `--format qminers`.

Data layout (rules.md §2):
    <data>/products.json                 {"pip_value": 0.25, "step_ms": 500, "products": {"AURIC": {"tick": 1, "limit": 60}, ...}}
    <data>/sessions/<YYYY-MM-DD>.jsonl.gz one JSON line a step: {"n", "ts", "book": {sym: {"bid": [[px, lots], ...],
                                          "ask": [...]}}, "tape": [[sym, px, lots, "B"|"S"|"?"], ...]}
`--data` takes that folder or the round's folder above it (data/arena/round<N>/).

Units: prices are whole pips, so the engine's unit is one pip (`Day.info[p] = {"tick", "unit": 1}`): reports, fees
and `--metrics` are in pips, the portal's credits are pips × pip_value (0.25). Step n is engine timestamp n × 100.

Timing (rules.md §4): line n's tape printed between snapshots n − 1 and n. Orders resting after step n meet line
n + 1's tape, so the loader puts line n + 1's tape on engine tick n (the engine matches a tick's orders against
that tick's trades, and shows the bot the previous tick's): the bot sees line n's tape at step n, as on the
exchange. One difference left: a snapshot that crosses a resting order at step n spends that volume from line
n + 1's tape here, from line n's there, so we give slightly fewer trade fills than the exchange.

Bot API (rules.md §3): `class Strategy` with optional `on_start(config)` and `on_market(update) -> list` of
`("post"|"take", sym, qty, price, ref)`, `("pull", ref)`, `("pull_all"[, sym])`. Orders rest (RESTING); refs are
the bot's own, carried on `Order.tag`. The wrapper applies the exchange's per-action rules before the engine
sees an order: 10 actions a call (the rest dropped), pulls first, then each post or take checked alone (validity,
the per-order limit counting resting lots, 4 resting orders a product). A rejected action is the bot's bug: in
strict mode (validate, backtests) it raises, so the step's actions are discarded and the error is listed; with
`--no-strict` it is dropped as the exchange would, and counted in `rejected`.
"""

from __future__ import annotations

import ast
import datetime as dt
import gzip
import json
from pathlib import Path

from arena.botfile import BotFile
from arena.model import Book, Cancel, Day, MarketTrade, OpenOrder, Order, Tick

PROVIDED_MODULES: set[str] = set()  # their bot file imports nothing of theirs
RESTING = True  # posts rest until filled or pulled: the CLI runs as with --resting
SKELETON = False
ENTRY = ("Strategy", "on_market")
MAX_ACTIONS = 10
MAX_RESTING = 4
TAKER = "taker"  # the tape's aggressor, kept as the trade's buyer ("B") or seller ("S")
OPEN = dt.time(13, 30)  # the session's first snapshot, UTC

# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = Path(arg)
    for candidate in (path, path / "data"):
        if (candidate / "products.json").is_file() and (candidate / "sessions").is_dir():
            return candidate
    raise ValueError(f"not a Halden data folder (no products.json and sessions/): {path}")


def list_days(data_dir: Path) -> list[str]:
    return sorted(p.name.removesuffix(".jsonl.gz") for p in (data_dir / "sessions").glob("*.jsonl.gz"))


def load_days(data_dir: Path, specs: list[str]) -> list[Day]:
    """Each spec is a session's date (2026-05-11) or `all`."""
    available = list_days(data_dir)
    selected: list[str] = []
    for spec in specs:
        names = available if spec == "all" else [spec] if spec in available else []
        if not names:
            raise ValueError(f"no session {spec!r} in {data_dir}. Available: {', '.join(available)} (or all)")
        selected += [n for n in names if n not in selected]
    meta = json.loads((data_dir / "products.json").read_text())
    return [_load_session(data_dir / "sessions" / f"{name}.jsonl.gz", name, meta) for name in selected]


def _load_session(path: Path, name: str, meta: dict) -> Day:
    products = sorted(meta["products"])
    limits = {}
    for p in products:
        if "limit" not in meta["products"][p]:
            raise ValueError(f"{p}: no limit in products.json")
        limits[p] = int(meta["products"][p]["limit"])
    with gzip.open(path, "rt") as file:
        lines = [json.loads(line) for line in file]
    ticks = []
    for k, line in enumerate(lines):
        if line["n"] != k:
            raise ValueError(f"{path}: line {k + 1} has n {line['n']}, expected {k}")
        books = {}
        for sym, sides in line["book"].items():
            if sym not in limits:
                raise ValueError(f"{path}:{k + 1}: {sym!r} is not in products.json")
            bids = tuple(sorted(((int(px), int(v)) for px, v in sides.get("bid", []) if v > 0), reverse=True))
            asks = tuple(sorted((int(px), int(v)) for px, v in sides.get("ask", []) if v > 0))
            if bids or asks:
                books[sym] = Book(bids, asks)
        trades: dict[str, list[MarketTrade]] = {}
        for sym, px, lots, aggressor in lines[k + 1]["tape"] if k + 1 < len(lines) else ():  # printed before snapshot k + 1
            buyer, seller = (TAKER, "") if aggressor == "B" else ("", TAKER) if aggressor == "S" else ("", "")
            trades.setdefault(sym, []).append(MarketTrade(sym, int(px), int(lots), buyer, seller, k * 100))
        ticks.append(Tick(k * 100, books, trades, {}))  # no marks: the engine values at the mid (or --mark touch)
    info = {p: {"tick": float(meta["products"][p]["tick"]), "unit": 1.0} for p in products}
    return Day(name, products, limits, ticks, info)


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return HaldenBot(BotFile(path, {}, overrides, strict), strict, fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    cls, method = ENTRY
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            if any(isinstance(item, ast.FunctionDef) and item.name == method for item in node.body):
                return []
            return [f"class {cls} has no {method} method"]
    return [f"no top-level class {cls}"]


class HaldenBot:
    """Calls `Strategy().on_market(update)` once a step and applies the exchange's action rules."""

    max_state_chars = 0  # state lives on the Strategy instance, not in a string

    def __init__(self, bot_file: BotFile, strict: bool = True, fresh_each_tick: bool = False):
        self._file, self._strict, self._fresh = bot_file, strict, fresh_each_tick
        self._bot = getattr(bot_file.load(), ENTRY[0])()
        self._limits: dict[str, int] = {}
        self._ticks: dict[str, int] = {}
        self._date = "1970-01-01"
        self._used: set[int] = set()
        self.rejected: list[tuple[int, str]] = []

    def begin_day(self, day: Day) -> None:
        self._limits = day.limits
        self._ticks = {p: round(day.info.get(p, {}).get("tick", 1)) for p in day.products}
        self._date = day.name
        self._used = set()
        if hasattr(self._bot, "on_start"):
            self._bot.on_start({
                "session": day.name, "steps": len(day.ticks), "step_ms": 500, "pip_value": 0.25, "max_actions": MAX_ACTIONS,
                "products": {p: {"tick": self._ticks[p], "limit": day.limits[p], "max_resting": MAX_RESTING} for p in day.products},
            })

    def step(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        if self._fresh:  # keep the instance's state, lose module globals: the exchange keeps the instance
            module = self._file.load()
            bot = getattr(module, ENTRY[0]).__new__(getattr(module, ENTRY[0]))
            bot.__dict__ = self._bot.__dict__
            self._bot = bot
        n = tick.timestamp // 100
        start = dt.datetime.combine(dt.date.fromisoformat(self._date), OPEN)
        update = {
            "n": n,
            "ts": (start + dt.timedelta(milliseconds=500 * n)).isoformat(timespec="milliseconds") + "Z",
            "book": {p: _side_lists(tick.books.get(p)) for p in self._limits},
            "tape": [[t.product, int(t.price), t.quantity, "B" if t.buyer == TAKER else "S" if t.seller == TAKER else "?"]
                     for p in self._limits for t in market_trades.get(p, [])],
            "pos": {p: positions.get(p, 0) for p in self._limits},
            "fills": [[_ref(f.tag), f.product, f.quantity, int(f.price), "taker" if f.source == "book" else "maker"] for f in own_fills],
            "open": [[_ref(o.tag), o.product, o.quantity, int(o.price)] for o in open_orders],
        }
        returned = getattr(self._bot, ENTRY[1])(update)
        if returned is None:
            return []
        if not isinstance(returned, list):
            raise TypeError(f"on_market must return a list, not {type(returned).__name__}")
        if len(returned) > MAX_ACTIONS:
            self._reject(n, f"{len(returned)} actions: the exchange drops those after the {MAX_ACTIONS}th")
            returned = returned[:MAX_ACTIONS]
        return self._apply(n, returned, positions, open_orders)

    def _apply(self, n: int, actions: list, positions, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        by_ref = {_ref(o.tag): o for o in open_orders}
        pulled: set[int] = set()
        for action in actions:  # every pull first, wherever it is in the list
            if not isinstance(action, (tuple, list)) or not action:
                self._reject(n, f"not an action: {action!r}")
            elif action[0] == "pull" and len(action) == 2:
                if action[1] in by_ref:
                    pulled.add(by_ref[action[1]].id)
                else:
                    self._reject(n, f"pull {action[1]!r}: no such resting order")
            elif action[0] == "pull_all" and len(action) in (1, 2):
                pulled |= {o.id for o in open_orders if len(action) == 1 or o.product == action[1]}
        out: list[Order | Cancel] = [Cancel(i) for i in sorted(pulled)]
        live = [o for o in open_orders if o.id not in pulled]
        buys = {p: sum(o.quantity for o in live if o.product == p and o.quantity > 0) for p in self._limits}
        sells = {p: -sum(o.quantity for o in live if o.product == p and o.quantity < 0) for p in self._limits}
        count = {p: sum(1 for o in live if o.product == p) for p in self._limits}
        for action in actions:
            if not isinstance(action, (tuple, list)) or not action or action[0] in ("pull", "pull_all"):
                continue
            if action[0] not in ("post", "take") or len(action) != 5:
                self._reject(n, f"unknown action {action!r}")
                continue
            kind, sym, qty, price, ref = action
            if sym not in self._limits:
                self._reject(n, f"{action!r}: unknown symbol")
            elif not isinstance(qty, int) or isinstance(qty, bool) or qty == 0:
                self._reject(n, f"{action!r}: qty must be a non-zero int")
            elif not isinstance(price, int) or isinstance(price, bool) or price <= 0 or price % self._ticks[sym]:
                self._reject(n, f"{action!r}: price must be a positive int on the {self._ticks[sym]} tick grid")
            elif not isinstance(ref, int) or isinstance(ref, bool) or ref <= 0 or ref in self._used:
                self._reject(n, f"{action!r}: ref must be a positive int not used before")
            elif qty > 0 and positions.get(sym, 0) + buys[sym] + qty > self._limits[sym]:
                self._reject(n, f"{action!r}: over the {self._limits[sym]} limit (position {positions.get(sym, 0)}, resting buys {buys[sym]})")
            elif qty < 0 and positions.get(sym, 0) - sells[sym] + qty < -self._limits[sym]:
                self._reject(n, f"{action!r}: over the {self._limits[sym]} limit (position {positions.get(sym, 0)}, resting sells {sells[sym]})")
            elif kind == "post" and count[sym] >= MAX_RESTING:
                self._reject(n, f"{action!r}: {sym} already has {MAX_RESTING} orders resting")
            else:
                self._used.add(ref)
                if qty > 0:
                    buys[sym] += qty
                else:
                    sells[sym] -= qty
                if kind == "post":
                    count[sym] += 1
                out.append(Order(sym, price, qty, kind == "take", tag=str(ref)))
        return out

    def _reject(self, n: int, why: str) -> None:
        if self._strict:
            raise ValueError(f"step {n}: rejected by the exchange's rules: {why}")
        self.rejected.append((n, why))


def _side_lists(book: Book | None) -> dict[str, list[list[int]]]:
    if book is None:
        return {"bid": [], "ask": []}
    return {"bid": [[int(px), v] for px, v in book.bids], "ask": [[int(px), v] for px, v in book.asks]}


def _ref(tag: str) -> int | str:
    return int(tag) if tag.isdigit() else tag
