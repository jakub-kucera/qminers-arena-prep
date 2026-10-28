"""The Arena's round-1 format (the Halden Exchange's Technical Rules, data/arena/round1/rules.md).

Copied from drill.py and rewritten to the rules. Data layout (rules §2):
    <data>/products.json                   pip_value, step_ms, and per product: tick, limit
    <data>/sessions/<YYYY-MM-DD>.jsonl.gz  one line per 500 ms step:
        {"n": 17, "ts": "...", "book": {"AURIC": {"bid": [[3179, 21], ...], "ask": [...]}, ...},
         "tape": [["AURIC", 3182, 2, "B"], ...]}   trades since the previous line; aggressor B/S/?

Unlike Prosperity:
- **Prices are integer pips** for every product; VANTA's tick is 4 pips. The engine's unit is
  the pip (Day.info's `unit` 1), so reports are in pips: × pip_value (0.25) for credits.
- **Line n+1's tape goes on tick n:** the rules fill orders placed at step n from the trades
  printed before snapshot n+1 (§4 step 6), and the bot at step n sees line n's tape (§3), which
  is the engine's "previous tick's trades".
- **The API** (§3): `Strategy()` constructed fresh per session, `on_start(config)` once, then
  `on_market(update) -> list` of action tuples: ("post", sym, qty, price, ref), ("take", ...) IOC,
  ("pull", ref), ("pull_all",) / ("pull_all", sym). State lives on the instance.
- **The exchange's checks are applied here** (§3, §4), before the engine sees the orders: at most
  10 actions a call (the rest dropped), pulls first, then each post or take on its own: validity,
  the per-order limit (position + resting and accepted lots on that side + q), and at most 4
  resting posts a product. A rejected action is dropped; in strict mode it raises instead, so
  arena.validate reports it (the step's actions are then lost, which their exchange wouldn't do).
- **Orders rest** (RESTING). Their queue splits cancels pro-rata: run with `--queue prob`.
  Taker fills pay 1 pip a lot, makers nothing: `--fee 1 --maker-fee 0`. Scored at the touch of
  the final snapshot: `--mark touch`.
"""

from __future__ import annotations

import ast
import gzip
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from arena.botfile import BotFile
from arena.model import Book, Cancel, Day, MarketTrade, OpenOrder, Order, Tick

PROVIDED_MODULES: set[str] = set()
RESTING = True  # orders rest until pulled: the CLI runs this format as with --resting
TAKER = "taker"  # the trade's aggressor, shown as its buyer or seller
MAX_ACTIONS = 10
MAX_RESTING = 4

# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = Path(arg)
    for candidate in (path, path / "data"):
        if (candidate / "products.json").is_file() and (candidate / "sessions").is_dir():
            return candidate
    raise ValueError(f"not a qminers data folder (no products.json and sessions/): {path}")


def list_sessions(data_dir: Path) -> list[str]:
    return sorted(m[1] for p in (data_dir / "sessions").glob("*.jsonl.gz") if (m := re.fullmatch(r"(\d{4}-\d\d-\d\d)\.jsonl\.gz", p.name)))


def load_days(data_dir: Path, specs: list[str]) -> list[Day]:
    """Each spec is `all`, a session's date, its index in date order (0, 1, ...) or a range like 0..1."""
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
            raise ValueError(f"bad session {spec!r}: use all, a date, an index or a range like 0..1")
        if not names:
            raise ValueError(f"no session {spec!r} in {data_dir}. Available: {', '.join(available)}")
        selected += [n for n in names if n not in selected]
    meta = json.loads((data_dir / "products.json").read_text())
    return [_load_session(data_dir / "sessions" / f"{name}.jsonl.gz", name, meta) for name in selected]


def _load_session(path: Path, name: str, meta: dict) -> Day:
    products = meta["products"]
    for sym, spec in products.items():
        if "tick" not in spec or "limit" not in spec:
            raise ValueError(f"{sym}: products.json gives no tick or limit")
    with gzip.open(path, "rt") as file:
        lines = [json.loads(line) for line in file if line.strip()]
    ticks: list[Tick] = []
    for k, line in enumerate(lines):
        if line["n"] != k:
            raise ValueError(f"{path}: line {k + 1} has n {line['n']}")
        books = {}
        for sym, side in line["book"].items():
            if sym not in products:
                raise ValueError(f"{path}:{k + 1}: {sym!r} is not in products.json")
            books[sym] = Book(tuple((int(p), int(v)) for p, v in side["bid"]), tuple((int(p), int(v)) for p, v in side["ask"]))
        # Line n+1's tape printed between snapshots n and n+1: it fills the orders placed at step n.
        trades: dict[str, list[MarketTrade]] = {}
        for sym, price, lots, aggressor in lines[k + 1]["tape"] if k + 1 < len(lines) else []:
            if int(price) % products[sym]["tick"]:
                raise ValueError(f"{path}:{k + 2}: {sym} trade at {price}, off its tick")
            buyer, seller = (TAKER, "") if aggressor == "B" else ("", TAKER) if aggressor == "S" else ("", "")
            trades.setdefault(sym, []).append(MarketTrade(sym, int(price), int(lots), buyer, seller, k))
        ticks.append(Tick(k, books, trades, {}))  # no marks: the engine values at the mid (or --mark touch)
    info = {
        sym: {"tick": float(spec["tick"]), "unit": 1.0, "pip_value": meta.get("pip_value", 1.0), "step_ms": meta.get("step_ms", 500)}
        for sym, spec in products.items()
    }
    return Day(name, sorted(products), {sym: int(spec["limit"]) for sym, spec in products.items()}, ticks, info)


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return QminersBot(BotFile(path, {}, overrides, strict), strict, fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Strategy":
            if any(isinstance(item, ast.FunctionDef) and item.name == "on_market" for item in node.body):
                return []
            return ["class Strategy has no on_market method"]
    return ["no top-level class Strategy"]


class QminersBot:
    """Calls `Strategy().on_market(update)` once a step and applies the exchange's checks to its actions."""

    max_state_chars = 0  # state lives on the Strategy instance, not in a string

    def __init__(self, bot_file: BotFile, strict: bool = True, fresh_each_tick: bool = False):
        self._file = bot_file
        self._strict = strict
        self._fresh = fresh_each_tick
        # Loaded at once, as drill.py does: the tools read PARAMS from the module this registers
        # (arena.cli.bot_module), and a bad file should fail here. begin_day loads it again per session.
        self._bot = bot_file.load().Strategy()
        self._day: Day | None = None
        self.rejected: list[tuple[int, str]] = []

    def begin_day(self, day: Day) -> None:
        """A fresh import and a fresh Strategy per session (§1), then on_start(config)."""
        self._day = day
        self._used_refs: set[int] = set()
        self._start = datetime.fromisoformat(f"{day.name}T13:30:00+00:00") if re.fullmatch(r"\d{4}-\d\d-\d\d", day.name) else None
        self._bot = self._file.load().Strategy()
        if hasattr(self._bot, "on_start"):
            first = next(iter(day.info.values()), {})
            config = {
                "session": day.name,
                "steps": len(day.ticks),
                "step_ms": first.get("step_ms", 500),
                "pip_value": first.get("pip_value", 1.0),
                "max_actions": MAX_ACTIONS,
                "products": {p: {"tick": int(day.info[p]["tick"]), "limit": day.limits[p], "max_resting": MAX_RESTING} for p in day.products},
            }
            self._bot.on_start(config)

    def step(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        if self._fresh:
            # The official state is the instance: move it into a freshly loaded module, so only state
            # kept outside it (module globals) is lost, which is what the validator checks for.
            module = self._file.load()
            bot = module.Strategy.__new__(module.Strategy)
            bot.__dict__ = self._bot.__dict__
            self._bot = bot
        day = self._day
        update = {
            "n": tick.timestamp,
            "ts": self._ts(tick.timestamp),
            "book": {
                p: {"bid": [[int(px), v] for px, v in b.bids], "ask": [[int(px), v] for px, v in b.asks]}
                for p in day.products
                for b in [tick.books.get(p, Book())]
            },
            "tape": [
                [t.product, int(t.price), t.quantity, "B" if t.buyer == TAKER else "S" if t.seller == TAKER else "?"]
                for p in day.products
                for t in market_trades.get(p, [])
            ],
            "pos": {p: positions.get(p, 0) for p in day.products},
            "fills": [[int(f.tag), f.product, f.quantity, int(f.price), "taker" if f.source == "book" else "maker"] for f in own_fills],
            "open": [[int(o.tag), o.product, o.quantity, int(o.price)] for o in open_orders],
        }
        actions = self._bot.on_market(update)
        if actions is None:
            return []
        if not isinstance(actions, list):
            raise TypeError(f"on_market returned {type(actions).__name__}, not a list: the step's actions are discarded")
        return self._apply(actions[:MAX_ACTIONS], tick.timestamp, positions, open_orders)

    def _apply(self, actions: list, n: int, positions, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        """The rules' §4 steps 3-4: pulls first, then each post and take checked on its own."""
        day = self._day
        problems: list[str] = []
        by_ref = {int(o.tag): o for o in open_orders}
        pulled: set[int] = set()
        for action in actions:
            if not isinstance(action, (tuple, list)) or not action:
                problems.append(f"not an action: {action!r}")
            elif action[0] == "pull":
                ref = action[1] if len(action) == 2 else None
                if ref in by_ref:
                    pulled.add(ref)
                else:
                    problems.append(f"pull {ref!r}: no such resting order")
            elif action[0] == "pull_all":
                if len(action) == 2 and action[1] not in day.limits:
                    problems.append(f"pull_all {action[1]!r}: unknown symbol")
                pulled |= {ref for ref, o in by_ref.items() if len(action) == 1 or o.product == action[1]}
            elif action[0] not in ("post", "take"):
                problems.append(f"unknown action {action[0]!r}")
        resting = [o for ref, o in by_ref.items() if ref not in pulled]
        buys = {p: sum(o.quantity for o in resting if o.product == p and o.quantity > 0) for p in day.products}
        sells = {p: -sum(o.quantity for o in resting if o.product == p and o.quantity < 0) for p in day.products}
        posts = {p: sum(1 for o in resting if o.product == p) for p in day.products}
        out: list[Order | Cancel] = [Cancel(by_ref[ref].id) for ref in sorted(pulled, key=lambda r: list(by_ref).index(r))]
        for action in actions:
            if not isinstance(action, (tuple, list)) or not action or action[0] not in ("post", "take"):
                continue
            if len(action) != 5:
                problems.append(f"{action!r}: a post or take has 5 fields")
                continue
            kind, sym, qty, price, ref = action
            if sym not in day.limits:
                problems.append(f"{action!r}: unknown symbol")
                continue
            tick = int(day.info[sym]["tick"])
            if not _is_int(qty) or qty == 0 or not _is_int(price) or price <= 0 or price % tick or not _is_int(ref) or ref <= 0:
                problems.append(f"{action!r}: needs a non-zero int qty, a positive int price on the {tick} grid and a positive int ref")
                continue
            if ref in self._used_refs:
                problems.append(f"{action!r}: ref {ref} used before")
                continue
            position = positions.get(sym, 0)
            if qty > 0 and position + buys[sym] + qty > day.limits[sym] or qty < 0 and position - sells[sym] + qty < -day.limits[sym]:
                problems.append(f"{action!r}: over the {day.limits[sym]} limit (position {position}, resting buys {buys[sym]}, sells {sells[sym]})")
                continue
            if kind == "post" and posts[sym] >= MAX_RESTING:
                problems.append(f"{action!r}: {sym} already has {MAX_RESTING} orders resting")
                continue
            self._used_refs.add(ref)
            if qty > 0:
                buys[sym] += qty
            else:
                sells[sym] -= qty
            if kind == "post":
                posts[sym] += 1
            out.append(Order(sym, price, qty, kind == "take", tag=str(ref)))
        if problems:
            self.rejected += [(n, text) for text in problems]
            if self._strict:
                raise ValueError(f"step {n}: rejected by the exchange's rules: " + "; ".join(problems))
        return out

    def _ts(self, n: int) -> str:
        if self._start is None:
            return str(n)
        step_ms = next(iter(self._day.info.values()), {}).get("step_ms", 500)
        return (self._start + timedelta(milliseconds=n * step_ms)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)
