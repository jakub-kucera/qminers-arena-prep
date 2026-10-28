"""The rehearsal round's portal: runs a bot file under public/rules.md and prints its score.

    uv run python private/evaluate.py BOT_FILE [--days public|hidden] [--session DATE] [--jobs N] [--json OUT]

Runs on the qminers_arena repo's engine (arena.engine.run_day, so run it with that repo's `uv run`):
resting mode, TradeMatching.ALL with the "prob" queue model (power 1), positions marked at the touch
(Mark.TOUCH: a long at the best bid, a short at the best ask), a taker fee of 1 pip a lot and no
maker fee. Engine prices are the data's integer pips; PnL is converted to credits (x pip_value).
The adapter below enforces the rules the engine doesn't know: the action format, 10 actions a
call, 4 resting orders a product, the per-order limit check, unique refs and the 50 ms budget.
"""

from __future__ import annotations

import argparse
import ast
import gzip
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena.botfile import BotFile
from arena.engine import EngineConfig, Mark, QueueModel, TradeMatching, run_day
from arena.model import Book, Cancel, Day, MarketTrade, Order, Tick

HERE = Path(__file__).resolve().parent
DATA = {"public": HERE.parent / "public" / "data", "hidden": HERE / "hidden_data"}
CONFIG = EngineConfig(
    resting=True, trade_matching=TradeMatching.ALL, queue=QueueModel.PROB, queue_power=1.0,
    mark=Mark.TOUCH, fee=1.0, maker_fee=0.0,
)
TAKER = "taker"
CALL_BUDGET = 0.050  # seconds per on_market call (rules section 6)
START_BUDGET = 2.0  # seconds for on_start
MAX_ACTIONS = 10
MAX_RESTING = 4

# ---------------------------------------------------------------------------- data


def meta(data_dir: Path) -> dict:
    return json.loads((data_dir / "products.json").read_text())


def sessions(data_dir: Path) -> list[str]:
    return sorted(p.name.removesuffix(".jsonl.gz") for p in (data_dir / "sessions").glob("*.jsonl.gz"))


def load_session(data_dir: Path, date: str) -> tuple[Day, list[str]]:
    m = meta(data_dir)
    products = sorted(m["products"])
    lines = []
    with gzip.open(data_dir / "sessions" / f"{date}.jsonl.gz", "rt", encoding="utf-8") as file:
        for raw in file:
            if raw.strip():
                lines.append(json.loads(raw))
    ticks, stamps = [], []
    for k, line in enumerate(lines):
        assert line["n"] == k, (line["n"], k)
        books = {
            sym: Book(tuple((p, v) for p, v in side["bid"]), tuple((p, v) for p, v in side["ask"]))
            for sym, side in line["book"].items()
        }
        # the tape of line k+1 printed between snapshots k and k+1: the engine's trades of tick k
        nxt = lines[k + 1]["tape"] if k + 1 < len(lines) else []
        trades: dict[str, list[MarketTrade]] = {}
        for sym, px, qty, agg in nxt:
            buyer, seller = (TAKER, "") if agg == "B" else ("", TAKER) if agg == "S" else ("", "")
            trades.setdefault(sym, []).append(MarketTrade(sym, px, qty, buyer, seller, k))
        ticks.append(Tick(k, books, trades, {}))
        stamps.append(line["ts"])
    info = {sym: {"tick_pips": m["products"][sym]["tick"], "date": date} for sym in products}
    limits = {sym: m["products"][sym]["limit"] for sym in products}
    return Day(date, products, limits, ticks, info), stamps


# ---------------------------------------------------------------------------- bot


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
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Strategy"), None)
    if cls is None:
        problems.append("no top-level class Strategy")
    elif not any(isinstance(n, ast.FunctionDef) and n.name == "on_market" for n in cls.body):
        problems.append("class Strategy has no method on_market(self, update)")
    return problems


def _int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


class Discarded(Exception):
    """A call whose actions the rules discard (over the time budget, or a bad return value)."""


class HaldenBot:
    """Adapts a `class Strategy` bot file to the engine's Bot protocol."""

    def __init__(self, bot_file: BotFile, stamps: list[str], pip_value: float):
        self._file = bot_file
        self._stamps = stamps
        self._pip = pip_value
        self.rejects: list[tuple[int, str]] = []
        self.slow = 0

    def begin_day(self, day: Day) -> None:
        module = self._file.load()
        self._ticks = {sym: info["tick_pips"] for sym, info in day.info.items()}
        self._limits = dict(day.limits)
        self._refs: set[int] = set()
        config = {
            "session": day.name,
            "steps": len(day.ticks),
            "step_ms": 500,
            "pip_value": self._pip,
            "products": {sym: {"tick": self._ticks[sym], "limit": self._limits[sym], "max_resting": MAX_RESTING} for sym in day.products},
            "max_actions": MAX_ACTIONS,
        }
        self._strategy = module.Strategy()
        if hasattr(self._strategy, "on_start"):
            try:
                start = time.perf_counter()
                self._strategy.on_start(config)
                if time.perf_counter() - start > START_BUDGET:
                    self.rejects.append((-1, "on_start took over 2 s"))
            except Exception as exc:
                self.rejects.append((-1, f"on_start raised {type(exc).__name__}: {exc}"))

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        update = {
            "n": tick.timestamp,
            "ts": self._stamps[tick.timestamp],
            "book": {sym: {"bid": [list(l) for l in b.bids], "ask": [list(l) for l in b.asks]} for sym, b in tick.books.items()},
            "tape": [
                [sym, tr.price, tr.quantity, "B" if tr.buyer == TAKER else "S" if tr.seller == TAKER else "?"]
                for sym in sorted(market_trades) for tr in market_trades[sym]
            ],
            "pos": dict(positions),
            "fills": [[int(f.tag), f.product, f.quantity, f.price, "taker" if f.source == "book" else "maker"] for f in own_fills],
            "open": [[int(o.tag), o.product, o.quantity, o.price] for o in open_orders],
        }
        start = time.perf_counter()
        actions = self._strategy.on_market(update)
        elapsed = time.perf_counter() - start
        if elapsed > CALL_BUDGET:
            self.slow += 1
            raise Discarded(f"on_market took {elapsed * 1000:.1f} ms, over 50 ms: actions discarded")
        return self._convert(tick.timestamp, actions, positions, open_orders)

    def _reject(self, n: int, msg: str) -> None:
        self.rejects.append((n, msg))

    def _convert(self, n: int, actions, positions, open_orders):
        if actions is None:
            return []
        if not isinstance(actions, (list, tuple)):
            raise Discarded(f"on_market must return a list, got {type(actions).__name__}")
        actions = list(actions)
        if len(actions) > MAX_ACTIONS:
            self._reject(n, f"{len(actions)} actions: those after the first {MAX_ACTIONS} dropped")
            actions = actions[:MAX_ACTIONS]
        by_ref = {int(o.tag): o for o in open_orders}
        pulled: set[int] = set()
        out: list = []
        news = []
        for a in actions:
            if not isinstance(a, (tuple, list)) or not a or not isinstance(a[0], str):
                self._reject(n, f"bad action {a!r}")
                continue
            kind = a[0]
            if kind == "pull":
                ref = a[1] if len(a) == 2 else None
                if ref in by_ref and ref not in pulled:
                    pulled.add(ref)
                    out.append(Cancel(by_ref[ref].id))
                else:
                    self._reject(n, f"pull {ref!r}: no such resting order")
            elif kind == "pull_all":
                sym = a[1] if len(a) > 1 else None
                if len(a) > 2 or (sym is not None and sym not in self._limits):
                    self._reject(n, f"bad pull_all {a!r}")
                    continue
                for ref, o in by_ref.items():
                    if (sym is None or o.product == sym) and ref not in pulled:
                        pulled.add(ref)
                        out.append(Cancel(o.id))
            elif kind in ("post", "take"):
                news.append(a)
            else:
                self._reject(n, f"unknown action {kind!r}")
        # pulls first, then the new orders in the order given, each checked on its own
        left = [o for ref, o in by_ref.items() if ref not in pulled]
        buys = {s: sum(o.quantity for o in left if o.product == s and o.quantity > 0) for s in self._limits}
        sells = {s: -sum(o.quantity for o in left if o.product == s and o.quantity < 0) for s in self._limits}
        count = {s: sum(1 for o in left if o.product == s) for s in self._limits}
        for a in news:
            problem = self._check(a)
            if problem:
                self._reject(n, problem)
                continue
            kind, sym, qty, px, ref = a
            pos, lim = positions.get(sym, 0), self._limits[sym]
            if qty > 0 and pos + buys[sym] + qty > lim:
                self._reject(n, f"{kind} {ref}: {sym} buys would reach {pos + buys[sym] + qty} > limit {lim}")
                continue
            if qty < 0 and pos - sells[sym] + qty < -lim:
                self._reject(n, f"{kind} {ref}: {sym} sells would reach {pos - sells[sym] + qty} < -{lim}")
                continue
            if kind == "post" and count[sym] >= MAX_RESTING:
                self._reject(n, f"post {ref}: {sym} already has {MAX_RESTING} resting orders")
                continue
            self._refs.add(ref)
            if qty > 0:
                buys[sym] += qty
            else:
                sells[sym] -= qty
            if kind == "post":
                count[sym] += 1
            out.append(Order(sym, px, qty, kind == "take", tag=str(ref)))
        return out

    def _check(self, a) -> str | None:
        if len(a) != 5:
            return f"{a[0]} needs 5 fields (kind, symbol, qty, price, ref): {a!r}"
        kind, sym, qty, px, ref = a
        if sym not in self._limits:
            return f"{kind}: unknown symbol {sym!r}"
        if not _int(qty) or qty == 0:
            return f"{kind} {sym}: qty must be a non-zero int, got {qty!r}"
        if not _int(px) or px <= 0 or px % self._ticks[sym]:
            return f"{kind} {sym}: price {px!r} is not a positive multiple of {self._ticks[sym]} pips"
        if not _int(ref) or ref <= 0:
            return f"{kind} {sym}: ref must be a positive int, got {ref!r}"
        if ref in self._refs:
            return f"{kind} {sym}: ref {ref} already used this session"
        return None


# ---------------------------------------------------------------------------- running


def run_session(bot_path: str, data_dir: str, date: str) -> dict:
    day, stamps = load_session(Path(data_dir), date)
    pip = meta(Path(data_dir))["pip_value"]
    bot = HaldenBot(BotFile(Path(bot_path), {}, strict=False), stamps, pip)
    result = run_day(day, bot, CONFIG)
    per = {}
    for sym in day.products:
        fills = [f for f in result.fills if f.product == sym]
        per[sym] = {
            "pnl": (result.pnl[sym][-1] if result.pnl[sym] else 0.0) * pip,
            "fills": len(fills),
            "taker_lots": sum(abs(f.quantity) for f in fills if f.source == "book"),
            "volume": sum(abs(f.quantity) for f in fills),
            "end_position": result.positions[sym][-1] if result.positions[sym] else 0,
            "breaches": sum(1 for _, p in result.limit_breaches if p == sym),
        }
    return {
        "date": date,
        "products": per,
        "errors": [(ts, msg.strip().splitlines()[-1]) for ts, msg in result.errors],
        "rejects": bot.rejects,
        "slow": bot.slow,
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
    print(f"SCORE: {total:,.2f} credits\n")
    header = f"{'session':<12}" + "".join(f"{p:>12}" for p in products) + f"{'total':>12}"
    print("PnL per product and session (credits, fees in, positions at the touch)\n" + header)
    for r in results:
        row = [r["products"][p]["pnl"] for p in products]
        print(f"{r['date']:<12}" + "".join(f"{v:>12,.2f}" for v in row) + f"{sum(row):>12,.2f}")
    sums = [sum(r["products"][p]["pnl"] for r in results) for p in products]
    print(f"{'all':<12}" + "".join(f"{v:>12,.2f}" for v in sums) + f"{sum(sums):>12,.2f}\n")
    print("fills (count / lots / taker lots), end position")
    for r in results:
        cells = [f"{p} {r['products'][p]['fills']}/{r['products'][p]['volume']}/{r['products'][p]['taker_lots']} pos {r['products'][p]['end_position']:+d}" for p in products]
        print(f"{r['date']:<12}" + " | ".join(cells))
    print()
    for r in results:
        breaches = sum(r["products"][p]["breaches"] for p in products)
        print(
            f"{r['date']}: errors {len(r['errors'])}, rejected actions {len(r['rejects'])}, slow calls {r['slow']}, "
            f"engine breaches {breaches}, call time mean {r['step_ms_mean']:.2f} ms max {r['step_ms_max']:.1f} ms"
        )
        for ts, msg in r["errors"][:3]:
            print(f"    error at n={ts}: {msg}")
        for ts, msg in r["rejects"][:3]:
            print(f"    rejected at n={ts}: {msg}")
    print(f"\nran in {time.time() - start:.1f} s")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
