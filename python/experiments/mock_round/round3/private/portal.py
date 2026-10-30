"""The Kestrel Bourse portal (organiser side): evaluates a bot file and reports what the exchange's
submission page would.

    uv run python <ROUND>/private/portal.py upload BOT.py    # a team upload: the 3 public sessions, counts (max 3)
    uv run python <ROUND>/private/portal.py hidden BOT.py    # ORGANISER ONLY: the 2 hidden sessions, the final score
    uv run python <ROUND>/private/portal.py status           # uploads used
    uv run python <ROUND>/private/portal.py reset            # ORGANISER ONLY: uploads back to 0

Run from the qminers_arena repo root (it runs that repo's engine, arena.engine.run_day, so it needs
its `uv run`). The bot may be at any path. One evaluation runs at a time (a lock file in private/).

`upload` prints the submission's metrics as JSON on stdout, with the Arena portal's own field names,
and writes the results ZIP and metrics.json to <ROUND>/uploads/upload_<n>/ (the paths go to stderr
and into the JSON). A file rejected at upload (syntax, a non-stdlib import, no top-level step())
doesn't count.

The truth (private/ANSWER_KEY.md): TRUTH below. Prices in the engine are integer hundredths of a
point; a point is worth 2 credits a lot, so an engine unit is 0.02 credits (Day.info "unit"), which
the engine's fee and penalty conversion (price_units) and experiments.day.calibrate's --scale both read.
"""

from __future__ import annotations

import ast
import csv
import io
import json
import os
import statistics
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from arena.botfile import BotFile
from arena.engine import EngineConfig, Mark, QueueModel, TradeMatching, run_day
from arena.model import Book, Cancel, Day, MarketTrade, Order, Tick

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
DATA = {"public": ROUND / "public" / "data", "hidden": HERE / "hidden_data"}
STATE = HERE / "state.json"
LOCK = HERE / ".evaluation.lock"
UPLOADS = ROUND / "uploads"
MAX_UPLOADS = 3

POINT_VALUE = 2.0  # credits per point per lot
UNIT = POINT_VALUE / 100  # credits per engine unit (a hundredth of a point)
STEP_MS = 250
OPEN_MS = 10 * 3600 * 1000
MAX_ACTIONS = 6
MAX_RESTING = 3
STEP_BUDGET = 0.100  # seconds per step() call
SETUP_BUDGET = 2.0
LIMIT_PENALTY = 0.25  # credits per lot beyond the limit, per step
TAKER = "taker"

# The exchange's matching rules, the round's truth. Stated in rules.md: resting, fee_bps, maker_fee_bps,
# max_actions, max_resting, limit_penalty. NOT stated: trade_matching, queue, mark, delay.
TRUTH = EngineConfig(
    resting=True,
    trade_matching=TradeMatching.WORSE,
    queue=QueueModel.PROB,
    queue_power=1.0,
    mark=Mark.LAST,
    delay=1,
    fee_bps=2.0,
    maker_fee_bps=-0.5,
    max_actions=MAX_ACTIONS,
    max_resting=MAX_RESTING,
    limit_penalty=LIMIT_PENALTY,
)

# ---------------------------------------------------------------------------- data


def clock(n: int) -> str:
    ms = OPEN_MS + n * STEP_MS
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def step_of(text: str) -> int:
    h, m, s = text.split(":")
    ms = (int(h) * 3600 + int(m) * 60) * 1000 + round(float(s) * 1000)
    return (ms - OPEN_MS) // STEP_MS


def hundredths(text: str) -> int:
    return round(float(text) * 100)


def instruments(data_dir: Path) -> dict[str, dict]:
    with (data_dir / "instruments.csv").open() as f:
        return {
            r["symbol"]: {"tick": float(r["tick"]), "tick_units": hundredths(r["tick"]), "decimals": int(r["decimals"]),
                          "limit": int(r["limit"]), "description": r["description"]}
            for r in csv.DictReader(f)
        }


def sessions(data_dir: Path) -> list[str]:
    return sorted(p.name for p in data_dir.iterdir() if p.is_dir())


def load_session(data_dir: Path, date: str, steps: int = 6000) -> Day:
    """Rebuilds every step's book from the level-by-level updates; a print stamped t is a trade of tick t."""
    inst = instruments(data_dir)
    symbols = sorted(inst)
    levels = {(s, side): [None, None, None] for s in symbols for side in ("bid", "ask")}
    updates: dict[int, list] = {}
    with (data_dir / date / "book.csv").open() as f:
        for r in csv.DictReader(f):
            updates.setdefault(step_of(r["clock"]), []).append(r)
    prints: dict[int, dict[str, list[MarketTrade]]] = {}
    with (data_dir / date / "prints.csv").open() as f:
        for r in csv.DictReader(f):
            n = step_of(r["clock"])
            buyer, seller = (TAKER, "") if r["aggressor"] == "BUY" else ("", TAKER) if r["aggressor"] == "SELL" else ("", "")
            prints.setdefault(n, {}).setdefault(r["symbol"], []).append(
                MarketTrade(r["symbol"], hundredths(r["price"]), int(r["size"]), buyer, seller, n))
    ticks = []
    for n in range(steps):
        for r in updates.get(n, []):
            size = int(r["size"])
            levels[(r["symbol"], r["side"])][int(r["level"]) - 1] = None if size == 0 else (hundredths(r["price"]), size)
        books = {
            s: Book(tuple(l for l in levels[(s, "bid")] if l), tuple(l for l in levels[(s, "ask")] if l)) for s in symbols
        }
        ticks.append(Tick(n, books, prints.get(n, {}), {}))
    info = {s: {"tick": inst[s]["tick"], "unit": UNIT, "tick_units": inst[s]["tick_units"], "decimals": inst[s]["decimals"]}
            for s in symbols}
    return Day(date, symbols, {s: inst[s]["limit"] for s in symbols}, ticks, info)


# ---------------------------------------------------------------------------- bot


def check_source(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        return [f"cannot parse: {exc}"]
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
    if not any(isinstance(n, ast.FunctionDef) and n.name == "step" for n in tree.body):
        problems.append("no top-level function step(ctx, view)")
    return problems


class LazyCancel(Cancel):
    """A cancel by client id, resolved to the engine's order id when it reaches the exchange (after any delay)."""

    def __init__(self, resolve, cid: str):
        object.__setattr__(self, "_resolve", resolve)
        object.__setattr__(self, "cid", cid)

    @property
    def order_id(self) -> int:  # type: ignore[override]
        return self._resolve(self.cid)

    def __repr__(self) -> str:
        return f"LazyCancel({self.cid!r})"

    def __eq__(self, other) -> bool:
        return self is other

    def __hash__(self) -> int:
        return id(self)


class Discarded(Exception):
    pass


class KestrelBot:
    """Adapts a setup(ctx) / step(ctx, view) bot file to the engine's Bot protocol."""

    def __init__(self, bot_path: Path, clocks: list[str]):
        self._file = BotFile(bot_path, {}, strict=False)
        self.rejects: list[tuple[int, str]] = []
        self.slow = 0
        self.tif: dict[str, str] = {}

    def begin_day(self, day: Day) -> None:
        self._mod = self._file.load()
        self._day = day
        self._units = {s: day.info[s]["tick_units"] for s in day.products}
        self._dec = {s: day.info[s]["decimals"] for s in day.products}
        self._ids: dict[str, int] = {}  # client id -> engine order id, once the exchange has it
        self._cids: set[str] = set()
        self.ctx = SimpleNamespace(
            session=day.name, steps=len(day.ticks), step_ms=STEP_MS, point_value=POINT_VALUE,
            max_actions=MAX_ACTIONS, max_resting=MAX_RESTING,
            instruments={s: {"tick": day.info[s]["tick"], "decimals": self._dec[s], "limit": day.limits[s]} for s in day.products},
        )
        if hasattr(self._mod, "setup"):
            start = time.perf_counter()
            try:
                self._mod.setup(self.ctx)
            except Exception as exc:
                self.rejects.append((-1, f"setup raised {type(exc).__name__}: {exc}"))
            if time.perf_counter() - start > SETUP_BUDGET:
                self.rejects.append((-1, "setup took over 2 s"))

    def _px(self, units: float) -> float:
        return round(units / 100, 2)

    def _resolve(self, cid: str) -> int:
        return self._ids.get(cid, -1)

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        for o in open_orders:
            self._ids[o.tag] = o.id
        for f in own_fills:
            self._ids.setdefault(f.tag, f.order_id)
        view = {
            "step": tick.timestamp,
            "clock": clock(tick.timestamp),
            "book": {s: {"bid": [(self._px(p), v) for p, v in b.bids], "ask": [(self._px(p), v) for p, v in b.asks]}
                     for s, b in tick.books.items()},
            "prints": [{"symbol": s, "price": self._px(t.price), "size": t.quantity,
                        "aggressor": "BUY" if t.buyer == TAKER else "SELL" if t.seller == TAKER else ""}
                       for s in sorted(market_trades) for t in market_trades[s]],
            "position": dict(positions),
            "executions": [{"cid": f.tag, "symbol": f.product, "side": "BUY" if f.quantity > 0 else "SELL",
                            "price": self._px(f.price), "size": abs(f.quantity),
                            "liquidity": "TAKER" if f.source == "book" else "MAKER"} for f in own_fills],
            "working": [{"cid": o.tag, "symbol": o.product, "side": "BUY" if o.quantity > 0 else "SELL",
                         "price": self._px(o.price), "remaining": abs(o.quantity)} for o in open_orders],
        }
        start = time.perf_counter()
        actions = self._mod.step(self.ctx, view)
        elapsed = time.perf_counter() - start
        if elapsed > STEP_BUDGET:
            self.slow += 1
            raise Discarded(f"step() took {elapsed * 1000:.1f} ms, over {STEP_BUDGET * 1000:.0f} ms: its actions were discarded")
        return self._convert(tick.timestamp, actions)

    def _convert(self, n: int, actions):
        if actions is None:
            return []
        if not isinstance(actions, list):
            raise Discarded(f"step() must return a list, got {type(actions).__name__}")
        if len(actions) > MAX_ACTIONS:
            self.rejects.append((n, f"{len(actions)} actions: the ones after the first {MAX_ACTIONS} were dropped"))
            actions = actions[:MAX_ACTIONS]
        out = []
        for a in actions:
            problem = self._check(a)
            if problem:
                self.rejects.append((n, problem))
                continue
            if a["type"] == "cancel":
                out.append(LazyCancel(self._resolve, a["cid"]))
                continue
            sym, cid = a["symbol"], a["cid"]
            qty = int(a["size"]) if a["side"] == "BUY" else -int(a["size"])
            self._cids.add(cid)
            tif = a.get("tif", "GTC")
            self.tif[cid] = tif
            out.append(Order(sym, hundredths(str(a["price"])), qty, tif == "IOC", tag=cid))
        return out

    def _check(self, a) -> str | None:
        if not isinstance(a, dict) or a.get("type") not in ("limit", "cancel"):
            return f"bad action {a!r}: a dict with type 'limit' or 'cancel'"
        cid = a.get("cid")
        if not isinstance(cid, str) or not 0 < len(cid) <= 32:
            return f"bad cid {cid!r}: a string of 1-32 characters"
        if a["type"] == "cancel":
            return None if cid in self._cids else f"cancel {cid!r}: no order with that cid"
        if cid in self._cids:
            return f"limit {cid!r}: cid already used this session"
        sym = a.get("symbol")
        if sym not in self._units:
            return f"limit {cid!r}: unknown symbol {sym!r}"
        if a.get("side") not in ("BUY", "SELL"):
            return f"limit {cid!r}: side must be 'BUY' or 'SELL'"
        size = a.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            return f"limit {cid!r}: size must be a positive int, got {size!r}"
        if a.get("tif", "GTC") not in ("GTC", "IOC"):
            return f"limit {cid!r}: tif must be 'GTC' or 'IOC'"
        px = a.get("price")
        try:
            value = float(px) if isinstance(px, (int, float, str)) and not isinstance(px, bool) else None
        except ValueError:
            value = None
        if value is None or value <= 0:
            return f"limit {cid!r}: price must be a positive number or decimal string, got {px!r}"
        units = value * 100
        if abs(units - round(units)) > 1e-6 or round(units) % self._units[sym]:
            return f"limit {cid!r}: price {px!r} is not on {sym}'s tick grid ({self._day.info[sym]['tick']})"
        return None


# ---------------------------------------------------------------------------- running


def run_session(bot_path: str, data_dir: str, date: str):
    day = load_session(Path(data_dir), date)
    bot = KestrelBot(Path(bot_path), [])

    class Guarded:  # a Discarded step loses its actions, as an exception would, but is reported as such
        def begin_day(self, d):
            bot.begin_day(d)

        def step(self, *a):
            try:
                return bot.step(*a)
            except Discarded as exc:
                bot.rejects.append((a[0].timestamp, str(exc)))
                return []

    result = run_day(day, Guarded(), TRUTH)
    return result, bot.rejects, bot.slow, bot.tif


def _translate(msg: str) -> str:
    last = msg.strip().splitlines()[-1]
    if msg.startswith("Traceback"):
        return f"ERROR step() raised {last}: its actions were discarded"
    if last.startswith("resting cap:"):
        words = last.split()
        return f"{words[2]} new {words[6]} orders refused: {MAX_RESTING} orders already working on it"
    if last.startswith("action cap:"):
        return f"actions over the {MAX_ACTIONS}-action limit dropped"
    if last.startswith("cancel for order"):
        return "cancel ignored: the order is not open on the exchange"
    return last


def evaluate(bot: Path, which: str):
    data_dir = DATA[which]
    dates = sessions(data_dir)
    with ProcessPoolExecutor(len(dates)) as pool:
        runs = list(pool.map(run_session, [str(bot)] * len(dates), [str(data_dir)] * len(dates), dates))
    return dates, runs


def metrics(results) -> dict:
    """The portal's figures, in credits, the way experiments.day.calibrate reads them (figures()):
    score = the sessions' sum; fills = fills; pnlSe = the per-session reading (stdev of the session PnLs x sqrt(n));
    markPrice = the last session's mark of the product if one traded, else the mean over the traded ones."""
    from experiments.day.calibrate import figures

    ours = figures(results, UNIT, LIMIT_PENALTY)
    last = results[-1]
    traded = sorted({p for r in results for p in r.products if any(f.product == p for f in r.fills) or any(r.positions[p])})
    marks = [last.marks[p][-1] * UNIT for p in traded]
    out = {
        "score": ours["score"][0],
        "fills": int(ours["fills"][0]),
        "tradedVolume": int(ours["tradedVolume"][0]),
        "inventory": int(ours["inventory"][0]),
        "cash": ours["cash"][0],
        "markPrice": statistics.fmean(marks) if marks else None,
        "breachPenalty": ours["breachPenalty"][0],
        "pnlSe": ours["pnlSe"][2],
        "absInventoryQ50": ours["absInventoryQ50"][0],
        "absInventoryQ68": ours["absInventoryQ68"][0],
        "absInventoryQ95": ours["absInventoryQ95"][0],
        "absInventoryQ997": ours["absInventoryQ997"][0],
    }
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}


def results_zip(dates, runs, path: Path, data_dir: Path) -> None:
    inst = instruments(data_dir)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for date, (result, rejects, slow, tif) in zip(dates, runs):
            fmt = lambda sym, units: f"{units / 100:.{inst[sym]['decimals']}f}"
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["ts", "symbol", "px", "qty", "side", "client_id", "liquidity"])
            for f in result.fills:
                w.writerow([clock(f.timestamp), f.product, fmt(f.product, f.price), abs(f.quantity),
                            "BUY" if f.quantity > 0 else "SELL", f.tag, "TAKER" if f.source == "book" else "MAKER"])
            z.writestr(f"executions_{date}.csv", buf.getvalue())
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["ts", "event", "client_id", "symbol", "side", "px", "qty", "tif"])
            seen, by_id, events = set(), {}, []
            for ts, o in result.orders:
                if o.id not in seen:
                    seen.add(o.id)
                    by_id[o.id] = o
                    events.append((ts, 0, ["NEW", o.tag, o.product, "BUY" if o.quantity > 0 else "SELL",
                                           fmt(o.product, o.price), abs(o.quantity), tif.get(o.tag, "GTC")]))
            for ts, oid in result.cancels:
                o = by_id.get(oid)
                if o is not None:
                    events.append((ts, 1, ["CANCEL", o.tag, o.product, "BUY" if o.quantity > 0 else "SELL",
                                           fmt(o.product, o.price), "", ""]))
            for ts, _, row in sorted(events, key=lambda e: (e[0], e[1])):
                w.writerow([clock(ts), *row])
            z.writestr(f"orders_{date}.csv", buf.getvalue())
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["ts", "symbol", "position", "pnl"])
            for k in range(0, len(result.timestamps), 40):
                for sym in result.products:
                    w.writerow([clock(result.timestamps[k]), sym, result.positions[sym][k], f"{result.pnl[sym][k] * UNIT:.2f}"])
            k = len(result.timestamps) - 1
            for sym in result.products:
                w.writerow([clock(result.timestamps[k]), sym, result.positions[sym][k], f"{result.pnl[sym][k] * UNIT:.2f}"])
            z.writestr(f"pnl_{date}.csv", buf.getvalue())
            lines = [f"session {date}: {len(result.fills)} fills, {len(rejects)} rejected actions, "
                     f"{len(result.errors)} exchange messages, {slow} slow steps"]
            lines += [f"{'setup' if n < 0 else clock(n)} REJECTED {msg}" for n, msg in rejects]
            lines += [f"{clock(ts)} EXCHANGE {_translate(msg)}" for ts, msg in result.errors]
            z.writestr(f"log_{date}.txt", "\n".join(lines) + "\n")


def _state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"uploads": 0, "history": []}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("upload", "hidden", "status", "reset"):
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "status":
        s = _state()
        print(f"uploads used: {s['uploads']} of {MAX_UPLOADS}")
        return 0
    if cmd == "reset":
        STATE.write_text(json.dumps({"uploads": 0, "history": []}, indent=1) + "\n")
        print("uploads reset to 0")
        return 0
    if len(argv) != 2:
        print(f"usage: portal.py {cmd} BOT.py")
        return 2
    bot = Path(argv[1]).resolve()
    print("Kestrel Bourse portal: one evaluation at a time.", file=sys.stderr)
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print("one evaluation at a time: another evaluation is running, try again when it has finished", file=sys.stderr)
        return 3
    try:
        os.close(fd)
        problems = check_source(bot)
        if problems:
            print(json.dumps({"status": "REJECTED", "reasons": problems, "counted": False}, indent=1))
            return 2
        state = _state()
        if cmd == "upload" and state["uploads"] >= MAX_UPLOADS:
            print(json.dumps({"status": "REFUSED", "reasons": [f"all {MAX_UPLOADS} uploads for this round are used"]}, indent=1))
            return 4
        start = time.time()
        dates, runs = evaluate(bot, "public" if cmd == "upload" else "hidden")
        m = metrics([r for r, *_ in runs])
        if cmd == "upload":
            state["uploads"] += 1
            n = state["uploads"]
            state["history"].append({"upload": n, "bot": str(bot), "score": m["score"], "at": time.strftime("%Y-%m-%d %H:%M:%S")})
            STATE.write_text(json.dumps(state, indent=1) + "\n")
            out = UPLOADS / f"upload_{n}"
            label = f"upload {n} of {MAX_UPLOADS}"
        else:
            out = HERE / "hidden_runs" / bot.stem
            label = "hidden sessions (organiser)"
        out.mkdir(parents=True, exist_ok=True)
        zpath = out / f"results_{out.name}.zip"
        results_zip(dates, runs, zpath, DATA["public" if cmd == "upload" else "hidden"])
        doc = {"status": "COMPLETED", "submission": label, "sessions": dates, "metrics": m,
               "resultsZip": str(zpath), "seconds": round(time.time() - start, 1)}
        (out / "metrics.json").write_text(json.dumps(doc, indent=1) + "\n")
        print(json.dumps(doc, indent=1))
        print(f"results ZIP: {zpath}\nmetrics: {out / 'metrics.json'}", file=sys.stderr)
        return 0
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
