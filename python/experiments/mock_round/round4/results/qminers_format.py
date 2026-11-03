"""The Arena's format: the Varde Exchange, round 1 (data/arena/round1/rules.md; the 2026-11-03 rehearsal).

Written from the skeleton (snapshots.py) by ON_THE_DAY.md, "The format swap, step by step".

Data layout (rules §Data):
    <data>/session_<n>.jsonl   one line per step, 5,000 steps:
        {"t": step, "book": {SYM: {"bids": [[px, vol], ...], "asks": [...]}},
         "prints": [{"sym", "px", "qty", "aggressor": "buy" | "sell"}]}
    The book is up to 3 levels a side, best first, before the step's trading; the prints are the trades
    between other participants *during* that step.

Units: prices are integer cents on a 5-cent tick for every product (rules §Products); the engine's unit is
the cent, so `Day.info[p] = {"tick": 0.05, "unit": 0.01}` (euros) and reports, `--fee` and calibrate's
figures are in euros through `credits_per_unit` (0.01 × CREDITS 1). The limits are the rules' (LIMITS).
Timestamps: step n of N becomes n × 1,000,000 // N (200 a step for 5,000), so flatten_from keeps its scale;
the bot is handed the step itself as `t`.

The trades: a step's prints are the trades during it, and the bot at step n sees step n − 1's (rules
§Your bot): the engine's convention (it hands the bot the previous tick's trades and matches its orders
against this tick's), so line n's prints go on tick n, unshifted.

The API (rules §Your bot): `class Strategy: __init__(self, limits)` and `on_tick(self, state) -> list`
of action dicts, `{"type": "limit", "sym", "px", "qty"}` or `{"type": "cancel", "id"}`, at most 10 a step
(the rest ignored). The exchange's ids are the engine's order ids. A fresh Strategy per session; its
state lives on the instance.

What the engine models of their rules (ENGINE): orders rest (RESTING); a resting order fills from prints
at or through its price (`trade_matching` all) with nothing ahead of it but our own older orders (the
rules name no queue behind the shown volume: `queue` front); the limit rule counts resting orders and
rejects all the step's new orders for the product (the engine's resting-mode rule 2); 0.1 cent a lot
traded (`fee` 0.001 €). Not modelled: the 0.5-cent fee an order placed (the wrapper counts orders in
`orders_placed` and the bot's `cash` pays it; take it off a backtest's PnL by hand), and the engine's
fills of a resting order by a later book that crosses it, which the rules don't have.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from arena.botfile import BotFile
from arena.model import Book, Cancel, Day, MarketTrade, OpenOrder, Order, Tick

PROVIDED_MODULES: set[str] = set()  # standard library only, no SDK (rules §Your bot)
RESTING = True  # orders rest until filled or cancelled (rules §Matching): the CLI runs as with --resting
CREDITS = 1.0  # the unit (0.01) is already in euros, the portal's currency
# The engine settings the rules fix (rules §Matching, §Limits); calibrate refines them after the first upload.
ENGINE: dict = {"trade_matching": "all", "queue": "front", "fee": 0.001, "max_actions": 10, "mark": "mid"}
SKELETON = False
LIMITS = {"LUMEN": 40, "QUILL": 60, "SORREL": 30}  # rules §Products
TICK_CENTS = 5  # rules §Products: every price a multiple of 5 cents
MAX_ACTIONS = 10  # rules §Your bot: the rest are ignored
ORDER_FEE = 0.005  # euros an order placed (rules §Limits); not charged by the engine
LOT_FEE = 0.001  # euros a lot traded (rules §Limits); ENGINE's fee
TAKER = "taker"  # the print's aggressor, shown as its buyer or seller
ENTRY = ("Strategy", "on_tick")

# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = Path(arg)
    for candidate in (path, path / "data"):
        if list_sessions(candidate):
            return candidate
    raise ValueError(f"not a Varde data folder (no session_<n>.jsonl): {path}")


def list_sessions(data_dir: Path) -> list[int]:
    if not data_dir.is_dir():
        return []
    return sorted(int(m[1]) for p in data_dir.glob("session_*.jsonl") if (m := re.fullmatch(r"session_(\d+)\.jsonl", p.name)))


def load_days(data_dir: Path, specs: list[str]) -> list[Day]:
    """Each spec is `all`, a session number (1, 2, 3) or a range like 1..2."""
    available = list_sessions(data_dir)
    selected: list[int] = []
    for spec in specs:
        if spec == "all":
            numbers = available
        elif match := re.fullmatch(r"s?(\d+)(?:\.\.(\d+))?", spec):
            low, high = int(match[1]), int(match[2] or match[1])
            numbers = [n for n in available if low <= n <= high]
        else:
            raise ValueError(f"bad session {spec!r}: use all, a number or a range like 1..2")
        if not numbers:
            raise ValueError(f"no session {spec!r} in {data_dir}. Available: {', '.join(map(str, available))} (or all)")
        selected += [n for n in numbers if n not in selected]
    return [_load_session(data_dir / f"session_{n}.jsonl", f"s{n}") for n in selected]


def _load_session(path: Path, name: str) -> Day:
    with path.open() as file:
        lines = [json.loads(line) for line in file if line.strip()]
    steps = len(lines)
    ticks: list[Tick] = []
    seen: set[str] = set()
    for k, line in enumerate(lines):
        where = f"{path}:{k + 1}"
        if int(line["t"]) != k:
            raise ValueError(f"{where}: step {line['t']}, expected {k}")
        timestamp = k * 1_000_000 // steps
        books = {}
        for sym, side in line["book"].items():
            _known(sym, where)
            seen.add(sym)
            bids = tuple((_cents(p, where), int(v)) for p, v in side.get("bids") or [] if int(v) > 0)
            asks = tuple((_cents(p, where), int(v)) for p, v in side.get("asks") or [] if int(v) > 0)
            books[sym] = Book(tuple(sorted(bids, reverse=True)), tuple(sorted(asks)))
        trades: dict[str, list[MarketTrade]] = {}
        for pr in line.get("prints") or []:
            sym = pr["sym"]
            _known(sym, where)
            buyer, seller = (TAKER, "") if pr["aggressor"] == "buy" else ("", TAKER) if pr["aggressor"] == "sell" else ("", "")
            trades.setdefault(sym, []).append(MarketTrade(sym, _cents(pr["px"], where), int(pr["qty"]), buyer, seller, timestamp))
        ticks.append(Tick(timestamp, books, trades, {}))  # no marks: the engine values at the mid
    products = sorted(seen)
    info = {p: {"tick": TICK_CENTS / 100, "unit": 0.01, "steps": steps} for p in products}
    return Day(name, products, {p: LIMITS[p] for p in products}, ticks, info)


def _known(sym: str, where: str) -> None:
    if sym not in LIMITS:
        raise ValueError(f"{where}: {sym!r} has no limit in LIMITS (rules §Products)")


def _cents(px, where: str) -> int:
    if not isinstance(px, int) or px % TICK_CENTS:
        raise ValueError(f"{where}: price {px!r} is not an integer multiple of {TICK_CENTS} cents")
    return px


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return VardeBot(BotFile(path, {}, overrides, strict), strict, fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    cls, method = ENTRY
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls:
            if any(isinstance(item, ast.FunctionDef) and item.name == method for item in node.body):
                return []
            return [f"class {cls} has no {method} method"]
    return [f"no top-level class {cls}"]


class VardeBot:
    """Calls `Strategy(limits).on_tick(state)` once a step and applies the exchange's checks to its actions."""

    max_state_chars = 0  # state lives on the Strategy instance, not in a string

    def __init__(self, bot_file: BotFile, strict: bool = True, fresh_each_tick: bool = False):
        self._file, self._strict, self._fresh = bot_file, strict, fresh_each_tick
        # Loaded at once: the tools read PARAMS from the module this registers (arena.cli.bot_module).
        self._bot = bot_file.load().Strategy(dict(LIMITS))
        self._day: Day | None = None
        self.rejected: list[tuple[int, str]] = []
        self.orders_placed = 0

    def begin_day(self, day: Day) -> None:
        """A fresh Strategy per session (assumed: the rules call one object for the whole session)."""
        self._day = day
        self._steps = len(day.ticks)
        self._cash = 0.0
        self._bot = self._file.load().Strategy(dict(day.limits))

    def step(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        if self._fresh:
            # The official state is the instance: move it into a freshly loaded module, so only state
            # kept outside it (module globals) is lost, which is what the validator checks for.
            module = self._file.load()
            bot = module.Strategy.__new__(module.Strategy)
            bot.__dict__ = self._bot.__dict__
            self._bot = bot
        day = self._day
        for f in own_fills:
            self._cash -= f.quantity * f.price * 0.01 + LOT_FEE * abs(f.quantity)
        step = tick.timestamp * self._steps // 1_000_000
        if step * 1_000_000 // self._steps != tick.timestamp:
            step += 1  # the inverse of n × 1,000,000 // N
        state = {
            "t": step,
            "book": {p: {"bids": [[int(px), v] for px, v in b.bids], "asks": [[int(px), v] for px, v in b.asks]} for p, b in tick.books.items()},
            "prints": [
                {"sym": t.product, "px": int(t.price), "qty": t.quantity, "aggressor": "buy" if t.buyer == TAKER else "sell"}
                for p in day.products for t in market_trades.get(p, [])
            ],
            "position": {p: positions.get(p, 0) for p in day.products},
            "orders": [{"id": o.id, "sym": o.product, "px": int(o.price), "qty": o.quantity} for o in open_orders],
            "fills": [{"id": f.order_id, "sym": f.product, "px": int(f.price), "qty": f.quantity} for f in own_fills],
            "cash": round(self._cash, 6),
        }
        actions = self._bot.on_tick(state)
        if actions is None:
            return []
        if not isinstance(actions, list):
            raise TypeError(f"on_tick returned {type(actions).__name__}, not a list: the step's actions are dropped")
        return self._apply(actions, step, open_orders)

    def _apply(self, actions: list, step: int, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        """Rules §Your bot and §Matching: the first 10 actions, cancels before new orders."""
        problems: list[str] = []
        if len(actions) > MAX_ACTIONS:
            problems.append(f"{len(actions)} actions: the {len(actions) - MAX_ACTIONS} past {MAX_ACTIONS} are ignored")
        resting = {o.id for o in open_orders}
        cancels: list[Cancel] = []
        orders: list[Order] = []
        for action in actions[:MAX_ACTIONS]:
            kind = action.get("type") if isinstance(action, dict) else None
            if kind == "cancel":
                if action.get("id") in resting:
                    cancels.append(Cancel(action["id"]))
                    resting.discard(action["id"])
                else:
                    problems.append(f"cancel {action.get('id')!r}: no such resting order")
            elif kind == "limit":
                sym, px, qty = action.get("sym"), action.get("px"), action.get("qty")
                if sym not in self._day.limits:
                    problems.append(f"{action!r}: unknown symbol")
                elif not _is_int(px) or px <= 0 or px % TICK_CENTS or not _is_int(qty) or qty == 0:
                    problems.append(f"{action!r}: needs an int px > 0 on the {TICK_CENTS}-cent grid and a non-zero int qty")
                else:
                    orders.append(Order(sym, px, qty))
                    self.orders_placed += 1
                    self._cash -= ORDER_FEE
            else:
                problems.append(f"not an action: {action!r}")
        if problems:
            self.rejected += [(step, text) for text in problems]
            if self._strict:
                raise ValueError(f"step {step}: rejected by the exchange's rules: " + "; ".join(problems))
        return [*cancels, *orders]


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)
