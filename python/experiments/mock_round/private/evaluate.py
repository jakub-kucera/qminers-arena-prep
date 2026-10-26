"""Private evaluation harness for the mock round: runs a bot file under public/rules.md.

    uv run python evaluate.py BOT_FILE [--days public|hidden] [--session DATE] [--jobs N]

Uses the repo's engine (arena.engine.run_day) in resting mode with TradeMatching.WORSE, the queue
model "back", and the mark at the mid (Mark.MID with no data marks). Prices inside the engine are
integer multiples of each instrument's tick; PnL is converted back to credits for the report.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
from pathlib import Path

from arena.botfile import BotFile
from arena.engine import EngineConfig, TradeMatching, run_day
from arena.model import Book, Cancel, Day, MarketTrade, Order, Tick

HERE = Path(__file__).resolve().parent
DATA = {"public": HERE.parent / "public" / "data", "hidden": HERE / "hidden_data"}
CONFIG = EngineConfig(resting=True, trade_matching=TradeMatching.WORSE)
TAKER = "taker"
STEP_TIMEOUT = 0.100  # seconds per call, rules section 7
MEMORY_CHARS = 100_000
MAX_ACTIONS = 50
OPEN_MS, STEP_MS = 9 * 3600 * 1000, 400

# ---------------------------------------------------------------------------- data


def instruments(data_dir: Path) -> dict[str, tuple[Decimal, int]]:
    with (data_dir / "instruments.csv").open() as file:
        return {row["symbol"]: (Decimal(row["tick_size"]), int(row["position_limit"])) for row in csv.DictReader(file)}


def sessions(data_dir: Path) -> list[str]:
    return sorted(p.name for p in data_dir.iterdir() if p.is_dir() and (p / "depth.csv").is_file())


def units(price: str, tick: Decimal) -> int:
    value = Decimal(price) / tick
    if value != value.to_integral_value():
        raise ValueError(f"price {price} off the {tick} grid")
    return int(value)


def load_session(data_dir: Path, date: str) -> Day:
    inst = instruments(data_dir)
    levels: dict[int, dict[str, dict[str, list]]] = defaultdict(lambda: defaultdict(lambda: {"BID": [], "ASK": []}))
    with (data_dir / date / "depth.csv").open() as file:
        for row in csv.DictReader(file):
            sym = row["symbol"]
            levels[int(row["seq"])][sym][row["side"]].append((int(row["level"]), units(row["price"], inst[sym][0]), int(row["size"])))
    prints: dict[int, dict[str, list[MarketTrade]]] = defaultdict(lambda: defaultdict(list))
    with (data_dir / date / "prints.csv").open() as file:
        for row in csv.DictReader(file):
            sym, seq = row["symbol"], int(row["seq"])
            buyer, seller = (TAKER, "") if row["aggressor"] == "BUY" else ("", TAKER) if row["aggressor"] == "SELL" else ("", "")
            prints[seq][sym].append(MarketTrade(sym, units(row["price"], inst[sym][0]), int(row["size"]), buyer, seller, seq))
    last = max(levels) if levels else -1
    ticks = []
    for seq in range(last + 1):
        books = {
            sym: Book(tuple((p, v) for _, p, v in sorted(s["BID"])), tuple((p, v) for _, p, v in sorted(s["ASK"])))
            for sym, s in levels.get(seq, {}).items()
        }
        ticks.append(Tick(seq, books, dict(prints.get(seq, {})), {}))  # no marks: valued at the mid
    info = {sym: {"tick": tick, "date": date} for sym, (tick, _) in inst.items()}
    return Day(date, sorted(inst), {sym: lim for sym, (_, lim) in inst.items()}, ticks, info)


# ---------------------------------------------------------------------------- bot


class StepRejected(Exception):
    """A call that the rules discard: timeout or bad memory. The engine records it as an error."""


def check_source(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    problems = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] if node.level == 0 else ["<relative import>"]
        for name in names:
            if name.split(".")[0] not in sys.stdlib_module_names:
                problems.append(f"line {node.lineno}: import of {name!r} is not standard library")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "trade" for n in tree.body):
        problems.append("no top-level function trade(snapshot, memory)")
    return problems


def _px(units_: int | float, tick: Decimal) -> float:
    return float(Decimal(int(units_)) * tick)


class ArenaBot:
    """Adapts a `trade(snapshot, memory)` bot file to the engine's Bot protocol."""

    def __init__(self, bot_file: BotFile):
        self._file = bot_file
        self.rejects: list[tuple[int, str]] = []
        self.timeouts = 0

    def begin_day(self, day: Day) -> None:
        self._module = self._file.load()
        self._ticks = {sym: info["tick"] for sym, info in day.info.items()}
        self._limits = dict(day.limits)
        self._used_ids: set[str] = set()
        self._auto = 0
        session = {
            "date": next(iter(day.info.values()))["date"],
            "instruments": {sym: {"tick_size": float(t), "position_limit": self._limits[sym]} for sym, t in self._ticks.items()},
        }
        self._memory_json = "{}"
        if hasattr(self._module, "init"):
            try:
                start = time.perf_counter()
                memory = self._module.init(session)
                if time.perf_counter() - start > STEP_TIMEOUT:
                    raise StepRejected("init took longer than 100 ms")
                self._memory_json = self._dump(memory if memory is not None else {})
            except Exception as exc:  # init errors leave memory at {}
                self.rejects.append((-1, f"init failed: {type(exc).__name__}: {exc}"))

    @staticmethod
    def _dump(memory) -> str:
        if not isinstance(memory, dict):
            raise StepRejected(f"memory must be a dict, got {type(memory).__name__}")
        try:
            text = json.dumps(memory)
        except (TypeError, ValueError) as exc:
            raise StepRejected(f"memory is not JSON-serialisable: {exc}") from None
        if len(text) > MEMORY_CHARS:
            raise StepRejected(f"memory is {len(text)} characters, over {MEMORY_CHARS}")
        return text

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        t = self._ticks
        snapshot = {
            "seq": tick.timestamp,
            "time": _clock(tick.timestamp),
            "books": {
                sym: {"bids": [[_px(p, t[sym]), v] for p, v in b.bids], "asks": [[_px(p, t[sym]), v] for p, v in b.asks]}
                for sym, b in tick.books.items()
            },
            "prints": {
                sym: [
                    {"price": _px(tr.price, t[sym]), "size": tr.quantity,
                     "aggressor": "BUY" if tr.buyer == TAKER else "SELL" if tr.seller == TAKER else ""}
                    for tr in trades
                ]
                for sym, trades in market_trades.items() if trades
            },
            "positions": dict(positions),
            "fills": [
                {"id": f.tag, "symbol": f.product, "side": "BUY" if f.quantity > 0 else "SELL",
                 "price": _px(f.price, t[f.product]), "size": abs(f.quantity)}
                for f in own_fills
            ],
            "orders": [
                {"id": o.tag, "symbol": o.product, "side": "BUY" if o.quantity > 0 else "SELL",
                 "price": _px(o.price, t[o.product]), "remaining": abs(o.quantity)}
                for o in open_orders
            ],
        }
        memory = json.loads(self._memory_json)
        start = time.perf_counter()
        actions = self._module.trade(snapshot, memory)
        elapsed = time.perf_counter() - start
        if elapsed > STEP_TIMEOUT:
            self.timeouts += 1
            raise StepRejected(f"trade took {elapsed * 1000:.0f} ms, over 100 ms: actions discarded")
        new_memory = self._dump(memory)
        out = self._convert(tick.timestamp, actions, open_orders)
        self._memory_json = new_memory
        return out

    def _convert(self, seq: int, actions, open_orders):
        if actions is None:
            return []
        if not isinstance(actions, list):
            raise StepRejected(f"trade must return a list, got {type(actions).__name__}")
        if len(actions) > MAX_ACTIONS:
            self.rejects.append((seq, f"{len(actions)} actions: only the first {MAX_ACTIONS} kept"))
            actions = actions[:MAX_ACTIONS]
        resting = {o.tag: o.id for o in open_orders}
        cancelled: set[str] = set()
        out = []
        for action in actions:
            problem = None
            if not isinstance(action, dict):
                problem = "action is not a dict"
            elif action.get("action") == "cancel":
                oid = action.get("id")
                if oid in resting and oid not in cancelled:
                    cancelled.add(oid)
                    out.append(Cancel(resting[oid]))
                else:
                    problem = f"cancel {oid!r}: not resting"
            elif action.get("action") == "new":
                problem = self._new(action, out)
            else:
                problem = f"unknown action {action.get('action')!r}"
            if problem:
                self.rejects.append((seq, problem))
        return out

    def _new(self, a: dict, out: list) -> str | None:
        sym, side, price, size = a.get("symbol"), a.get("side"), a.get("price"), a.get("size")
        tif = a.get("tif", "GTC")
        if sym not in self._ticks:
            return f"unknown symbol {sym!r}"
        if side not in ("BUY", "SELL"):
            return f"{sym}: bad side {side!r}"
        if tif not in ("GTC", "IOC"):
            return f"{sym}: bad tif {tif!r}"
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            return f"{sym}: size must be a positive int, got {size!r}"
        if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
            return f"{sym}: bad price {price!r}"
        tick = float(self._ticks[sym])
        u = price / tick
        if abs(u - round(u)) > 1e-6:
            return f"{sym}: price {price} is off the {self._ticks[sym]} tick grid"
        oid = a.get("id")
        if oid is None:
            self._auto += 1
            oid = f"x{self._auto}"
        elif not isinstance(oid, str) or not oid or len(oid) > 32:
            return f"{sym}: bad id {oid!r}"
        if oid in self._used_ids:
            return f"{sym}: duplicate id {oid!r}"
        self._used_ids.add(oid)
        out.append(Order(sym, round(u), size if side == "BUY" else -size, tif == "IOC", tag=oid))
        return None


def _clock(seq: int) -> str:
    ms = OPEN_MS + seq * STEP_MS
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


# ---------------------------------------------------------------------------- running


def run_session(bot_path: str, data_dir: str, date: str) -> dict:
    day = load_session(Path(data_dir), date)
    bot = ArenaBot(BotFile(Path(bot_path), {}, strict=False))
    result = run_day(day, bot, CONFIG)
    ticks = {sym: info["tick"] for sym, info in day.info.items()}
    per = {}
    for sym in day.products:
        fills = [f for f in result.fills if f.product == sym]
        per[sym] = {
            "pnl": float(Decimal(str(result.pnl[sym][-1])) * ticks[sym]) if result.pnl[sym] else 0.0,
            "fills": len(fills),
            "volume": sum(abs(f.quantity) for f in fills),
            "end_position": result.positions[sym][-1] if result.positions[sym] else 0,
            "breaches": sum(1 for _, p in result.limit_breaches if p == sym),
        }
    return {
        "date": date,
        "products": per,
        "errors": [(ts, msg.strip().splitlines()[-1]) for ts, msg in result.errors],
        "rejects": bot.rejects,
        "timeouts": bot.timeouts,
        "step_ms_mean": 1000 * sum(result.step_seconds) / max(1, len(result.step_seconds)),
        "step_ms_max": 1000 * max(result.step_seconds, default=0.0),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bot")
    parser.add_argument("--days", choices=sorted(DATA), default="public")
    parser.add_argument("--session", action="append", help="only this date (repeatable)")
    parser.add_argument("--jobs", type=int, default=0, help="worker processes (default: one per session)")
    parser.add_argument("--json", help="also write the per-session results here")
    args = parser.parse_args(argv)

    bot_path = Path(args.bot).resolve()
    problems = check_source(bot_path)
    if problems:
        print("REJECTED at upload:\n  " + "\n  ".join(problems))
        return 2
    data_dir = DATA[args.days]
    dates = args.session or sessions(data_dir)
    start = time.time()
    jobs = args.jobs or len(dates)
    if jobs == 1:
        results = [run_session(str(bot_path), str(data_dir), d) for d in dates]
    else:
        with ProcessPoolExecutor(jobs) as pool:
            results = list(pool.map(run_session, [str(bot_path)] * len(dates), [str(data_dir)] * len(dates), dates))

    products = sorted(results[0]["products"])
    total = sum(r["products"][p]["pnl"] for r in results for p in products)
    print(f"bot: {bot_path}\ndays: {args.days} ({', '.join(dates)})\n")
    print(f"TOTAL PnL: {total:,.2f} CR\n")
    header = f"{'session':<12}" + "".join(f"{p:>14}" for p in products) + f"{'total':>14}"
    print("PnL per instrument and session (CR)\n" + header)
    for r in results:
        row = [r["products"][p]["pnl"] for p in products]
        print(f"{r['date']:<12}" + "".join(f"{v:>14,.2f}" for v in row) + f"{sum(row):>14,.2f}")
    sums = [sum(r["products"][p]["pnl"] for r in results) for p in products]
    print(f"{'all':<12}" + "".join(f"{v:>14,.2f}" for v in sums) + f"{sum(sums):>14,.2f}\n")
    print("fills (count / lots), end position, breaches")
    for r in results:
        cells = [f"{r['products'][p]['fills']}/{r['products'][p]['volume']} pos {r['products'][p]['end_position']:+d} br {r['products'][p]['breaches']}" for p in products]
        print(f"{r['date']:<12}" + " | ".join(f"{p} {c}" for p, c in zip(products, cells)))
    print()
    for r in results:
        print(
            f"{r['date']}: errors {len(r['errors'])}, rejected actions {len(r['rejects'])}, timeouts {r['timeouts']}, "
            f"step time mean {r['step_ms_mean']:.2f} ms max {r['step_ms_max']:.1f} ms"
        )
        for ts, msg in r["errors"][:3]:
            print(f"    error at seq {ts}: {msg}")
        for ts, msg in r["rejects"][:3]:
            print(f"    rejected at seq {ts}: {msg}")
    print(f"\nran in {time.time() - start:.1f} s")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
