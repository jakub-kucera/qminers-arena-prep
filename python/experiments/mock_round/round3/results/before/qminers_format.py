"""The Arena's round-1 format: the Kestrel Bourse's Technical Rules (data/arena/round1/rules.md).

Copied from drill.py's pattern and rewritten to the rules. Data layout (rules §2):
    <data>/instruments.csv              symbol,description,tick,decimals,limit
    <data>/<YYYY-MM-DD>/book.csv        clock,symbol,side,level,price,size: a row when a level changed since the
                                        previous step (size 0, empty price: the level is empty); up to 3 levels a side
    <data>/<YYYY-MM-DD>/prints.csv      clock,symbol,price,size,aggressor (BUY, SELL or empty): trades after the
                                        book at `clock` was published and before the next step

Unlike Prosperity:
- **Decimal prices in points, a tick per instrument** (BRAM 0.5, OPHIR 0.01, TALC 0.05). The engine's unit is
  the finest the decimals allow (0.01 points), so reports are in hundredths of a point: × 0.02 for credits
  (1 point = 2 credits a lot).
- **Step n of 6,000 is engine timestamp n × 1,000,000 // 6,000**; the wrapper hands the bot the step number and clock.
- **A print at clock n traded after book n**, so it goes on tick n as it is (the engine's orders at tick n meet
  tick n's trades, and the bot sees them at tick n + 1, "since your previous call").
- **The API** (§3): module-level `setup(ctx)` (optional) and `step(ctx, view) -> list` of action dicts
  ({"type": "limit", "cid", "symbol", "side", "price", "size", "tif"} or {"type": "cancel", "cid"}). The file is
  imported fresh per session and `ctx` lives all session, so state lives on `ctx`.
- **The exchange's checks are applied here** (§3), before the engine sees the orders: at most 6 actions a step
  (cancels included; the rest dropped), cancels first, then each new order on its own: valid fields, a fresh cid,
  and at most 3 working orders per instrument (IOC doesn't count). A rejected action is dropped; in strict mode it
  raises instead, so arena.validate reports it.
- **Orders rest** (RESTING). Limits are charged, not enforced, and fills pay fees: run every tool with
  `--limit-penalty 0.125 --fee-bps 2 --maker-fee-bps -0.5` (0.25 credits a lot a step = 0.125 points).
"""

from __future__ import annotations

import ast
import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace

from arena.botfile import BotFile
from arena.model import Book, Cancel, Day, MarketTrade, OpenOrder, Order, Tick

PROVIDED_MODULES: set[str] = set()
RESTING = True  # orders rest until cancelled: the CLI runs this format as with --resting
SKELETON = False
ENTRY = (None, "step")  # module-level step(ctx, view)
TAKER = "taker"  # the trade's aggressor, shown as its buyer or seller
MAX_ACTIONS = 6
MAX_RESTING = 3
STEP_MS = 250
POINT_VALUE = 2.0
LATENCY = 1  # steps between a call and its actions reaching the exchange: fitted to the first upload (QminersBot.step)
# The engine settings every arena.* tool uses on this format unless a flag says otherwise (arena.cli.setup). Fees and
# the penalty are the rules' (§4: 2 bps taker, 0.5 bp maker rebate, 0.25 credits = 0.125 points a lot a step); the
# matching and the mark were fitted to upload 1 (data/arena/round1/HANDOVER.md, "Fill model and mark"): under worse
# and last, its fills, volume, end position, penalty, cash, score and pnlSe matched the portal's to the cent.
ENGINE = {"trade_matching": "worse", "mark": "last", "limit_penalty": 0.125, "fee_bps": 2.0, "maker_fee_bps": -0.5}

# ---------------------------------------------------------------------------- data


def resolve_data_dir(arg: str) -> Path:
    path = Path(arg)
    for candidate in (path, path / "data"):
        if (candidate / "instruments.csv").is_file():
            return candidate
    raise ValueError(f"not a qminers data folder (no instruments.csv): {path}")


def list_sessions(data_dir: Path) -> list[str]:
    return sorted(p.name for p in data_dir.iterdir() if re.fullmatch(r"\d{4}-\d\d-\d\d", p.name) and (p / "book.csv").is_file())


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
    instruments = _instruments(data_dir)
    return [_load_session(data_dir / name, name, instruments) for name in selected]


def _instruments(data_dir: Path) -> dict[str, dict]:
    out = {}
    with (data_dir / "instruments.csv").open(newline="") as file:
        for row in csv.DictReader(file):
            if not row.get("tick") or not row.get("limit"):
                raise ValueError(f"{row.get('symbol')}: instruments.csv gives no tick or limit")
            out[row["symbol"]] = {"tick": Decimal(row["tick"]), "decimals": int(row["decimals"]), "limit": int(row["limit"])}
    return out


def _step(clock: str, where: str) -> int:
    match = re.fullmatch(r"(\d\d):(\d\d):(\d\d)\.(\d{3})", clock)
    if not match:
        raise ValueError(f"{where}: bad clock {clock!r}")
    h, m, s, ms = map(int, match.groups())
    elapsed = ((h - 10) * 3600 + m * 60 + s) * 1000 + ms
    if elapsed % STEP_MS:
        raise ValueError(f"{where}: clock {clock} is not on the {STEP_MS} ms step grid")
    return elapsed // STEP_MS


def _load_session(path: Path, name: str, instruments: dict[str, dict]) -> Day:
    unit = Decimal(1).scaleb(-max(spec["decimals"] for spec in instruments.values()))
    rows: dict[int, list[dict]] = {}
    with (path / "book.csv").open(newline="") as file:
        for line_no, row in enumerate(csv.DictReader(file), 2):
            rows.setdefault(_step(row["clock"], f"{path}/book.csv:{line_no}"), []).append(row)
    trades: dict[int, dict[str, list[MarketTrade]]] = {}
    prints = path / "prints.csv"
    if prints.is_file():
        with prints.open(newline="") as file:
            for line_no, row in enumerate(csv.DictReader(file), 2):
                where = f"{prints}:{line_no}"
                n, sym = _step(row["clock"], where), row["symbol"]
                if sym not in instruments:
                    raise ValueError(f"{where}: {sym!r} is not in instruments.csv")
                aggressor = row.get("aggressor") or ""
                buyer, seller = (TAKER, "") if aggressor == "BUY" else ("", TAKER) if aggressor == "SELL" else ("", "")
                price = _units(row["price"], unit, instruments[sym]["tick"], where)
                trades.setdefault(n, {}).setdefault(sym, []).append(MarketTrade(sym, price, int(row["size"]), buyer, seller, n))
    steps = max([*rows, *trades]) + 1
    levels: dict[str, dict[str, dict[int, tuple[int, int]]]] = {sym: {"bid": {}, "ask": {}} for sym in instruments}
    ticks: list[Tick] = []
    for n in range(steps):
        for row in rows.get(n, []):
            where = f"{path}/book.csv, step {n}"
            sym, side, level = row["symbol"], row["side"], int(row["level"])
            if sym not in instruments:
                raise ValueError(f"{where}: {sym!r} is not in instruments.csv")
            if side not in ("bid", "ask"):
                raise ValueError(f"{where}: bad side {side!r}")
            size = int(row["size"] or 0)
            if size and row["price"]:
                levels[sym][side][level] = (_units(row["price"], unit, instruments[sym]["tick"], where), size)
            else:
                levels[sym][side].pop(level, None)
        books = {}
        for sym, sides in levels.items():
            bids = tuple(sorted(sides["bid"].values(), reverse=True))
            asks = tuple(sorted(sides["ask"].values()))
            if bids or asks:
                books[sym] = Book(bids, asks)
        ticks.append(Tick(n * 1_000_000 // steps, books, trades.get(n, {}), {}))  # no marks: the engine values at the mid
    info = {sym: {"tick": float(spec["tick"]), "unit": float(unit), "decimals": spec["decimals"]} for sym, spec in instruments.items()}
    return Day(name, sorted(instruments), {sym: spec["limit"] for sym, spec in instruments.items()}, ticks, info)


def _units(px: str, unit: Decimal, tick: Decimal, where: str) -> int:
    try:
        price = Decimal(px)
    except InvalidOperation:
        raise ValueError(f"{where}: bad price {px!r}") from None
    if price % tick:
        raise ValueError(f"{where}: price {px} is off the {tick} tick grid")
    return int(price / unit)


# ---------------------------------------------------------------------------- bot


def load_bot(path: Path, overrides: dict[str, object], strict: bool, fresh_each_tick: bool = False):
    return QminersBot(BotFile(path, {}, overrides, strict), strict, fresh_each_tick)


def check_source(tree: ast.Module) -> list[str]:
    found = any(isinstance(node, ast.FunctionDef) and node.name == "step" for node in tree.body)
    return [] if found else ["no top-level function step"]


class QminersBot:
    """Calls the module's `step(ctx, view)` once a step and applies the exchange's checks to its actions."""

    max_state_chars = 0  # state lives on ctx, not in a string

    def __init__(self, bot_file: BotFile, strict: bool = True, fresh_each_tick: bool = False):
        self._file = bot_file
        self._strict = strict
        self._fresh = fresh_each_tick
        # Loaded at once, as drill.py does: the tools read PARAMS from the module this registers
        # (arena.cli.bot_module), and a bad file should fail here. begin_day loads it again per session.
        self._module = bot_file.load()
        self._day: Day | None = None
        self.rejected: list[tuple[int, str]] = []

    def begin_day(self, day: Day) -> None:
        """A fresh import per session (§1), a new ctx, then setup(ctx)."""
        self._day = day
        self._queued: list = []
        self._index = {tick.timestamp: n for n, tick in enumerate(day.ticks)}
        self._used: set[str] = set()
        self._module = self._file.load()
        self._ctx = SimpleNamespace(
            session=day.name, steps=len(day.ticks), step_ms=STEP_MS, point_value=POINT_VALUE, max_actions=MAX_ACTIONS,
            max_resting=MAX_RESTING,
            instruments={p: {"tick": day.info[p]["tick"], "decimals": day.info[p]["decimals"], "limit": day.limits[p]} for p in day.products},
        )
        if hasattr(self._module, "setup"):
            self._module.setup(self._ctx)

    def step(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        """LATENCY: the actions the bot returns at step n reach the exchange at step n + 1, after the bot's view of
        n + 1 was taken (the first upload's orders file stamps each NEW and CANCEL a step after the call that sent
        it, and refused posts the bot's view couldn't foresee). So each step returns the previous call's actions,
        checked against the orders working now, and keeps this call's for the next step."""
        n = self._index.get(tick.timestamp, 0)
        actions = self._call(tick, positions, own_fills, market_trades, open_orders)
        if not LATENCY:
            return self._apply(actions, n, open_orders)
        queued, self._queued = getattr(self, "_queued", []), actions
        return self._apply(queued, n, open_orders)

    def _call(self, tick: Tick, positions, own_fills, market_trades, open_orders: list[OpenOrder]) -> list:
        if self._fresh:  # their engine keeps ctx all session: reloading the module checks nothing else is needed
            self._module = self._file.load()
        day = self._day
        n = self._index.get(tick.timestamp, 0)
        ms = n * STEP_MS
        view = {
            "step": n,
            "clock": f"{10 + ms // 3_600_000:02d}:{ms // 60_000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}",
            "book": {
                p: {"bid": [(self._px(p, x), v) for x, v in b.bids], "ask": [(self._px(p, x), v) for x, v in b.asks]}
                for p in day.products
                for b in [tick.books.get(p, Book())]
            },
            "prints": [
                {"symbol": t.product, "price": self._px(t.product, t.price), "size": t.quantity,
                 "aggressor": "BUY" if t.buyer == TAKER else "SELL" if t.seller == TAKER else ""}
                for p in day.products
                for t in market_trades.get(p, [])
            ],
            "position": {p: positions.get(p, 0) for p in day.products},
            "executions": [
                {"cid": f.tag, "symbol": f.product, "side": "BUY" if f.quantity > 0 else "SELL", "price": self._px(f.product, f.price),
                 "size": abs(f.quantity), "liquidity": "TAKER" if f.source == "book" else "MAKER"}
                for f in own_fills
            ],
            "working": [
                {"cid": o.tag, "symbol": o.product, "side": "BUY" if o.quantity > 0 else "SELL", "price": self._px(o.product, o.price),
                 "remaining": abs(o.quantity)}
                for o in open_orders
            ],
        }
        try:
            actions = self._module.step(self._ctx, view)
            if actions is not None and not isinstance(actions, list):
                raise TypeError(f"step returned {type(actions).__name__}, not a list: the step's actions are discarded")
        except Exception as error:  # §6: that step's actions are discarded, the session goes on
            if self._strict:
                raise
            self.rejected.append((n, f"step raised {error!r}: its actions discarded"))
            return []
        return (actions or [])[:MAX_ACTIONS]

    def _apply(self, actions: list, n: int, open_orders: list[OpenOrder]) -> list[Order | Cancel]:
        """§3: cancels first, then each new order in list order, checked on its own."""
        day = self._day
        problems: list[str] = []
        by_cid = {o.tag: o for o in open_orders}
        cancelled: list[str] = []
        for action in actions:
            if not isinstance(action, dict):
                problems.append(f"not an action: {action!r}")
            elif action.get("type") == "cancel":
                cid = action.get("cid")
                if cid in by_cid:
                    if cid not in cancelled:
                        cancelled.append(cid)
                elif cid not in self._used:
                    problems.append(f"cancel {cid!r}: a cid never sent")
            elif action.get("type") != "limit":
                problems.append(f"unknown action type {action.get('type')!r}")
        working = {p: sum(1 for cid, o in by_cid.items() if o.product == p and cid not in cancelled) for p in day.products}
        out: list[Order | Cancel] = [Cancel(by_cid[cid].id) for cid in cancelled]
        for action in actions:
            if not isinstance(action, dict) or action.get("type") != "limit":
                continue
            cid, sym, side, size, tif = action.get("cid"), action.get("symbol"), action.get("side"), action.get("size"), action.get("tif", "GTC")
            if not isinstance(cid, str) or not 1 <= len(cid) <= 32:
                problems.append(f"{action!r}: cid must be a string of 1-32 characters")
                continue
            if cid in self._used:
                problems.append(f"{action!r}: cid {cid} used before")
                continue
            if sym not in day.limits or side not in ("BUY", "SELL") or tif not in ("GTC", "IOC"):
                problems.append(f"{action!r}: bad symbol, side or tif")
                continue
            if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
                problems.append(f"{action!r}: size must be a positive int")
                continue
            price = self._units(sym, action.get("price"))
            if price is None:
                problems.append(f"{action!r}: price must be positive and on {sym}'s {day.info[sym]['tick']} grid")
                continue
            if tif == "GTC" and working[sym] >= MAX_RESTING:
                problems.append(f"{action!r}: {sym} already has {MAX_RESTING} orders working")
                continue
            self._used.add(cid)
            if tif == "GTC":
                working[sym] += 1
            out.append(Order(sym, price, size if side == "BUY" else -size, tif == "IOC", tag=cid))
        if problems:
            self.rejected += [(n, text) for text in problems]
            if self._strict:
                raise ValueError(f"step {n}: rejected by the exchange's rules: " + "; ".join(problems))
        return out

    def _px(self, product: str, units: float) -> float:
        meta = self._day.info[product]
        return round(units * meta["unit"], meta["decimals"])

    def _units(self, product: str, price) -> int | None:
        meta = self._day.info[product]
        try:
            value = Decimal(str(price))
        except (InvalidOperation, ValueError):
            return None
        tick, unit = Decimal(str(meta["tick"])), Decimal(str(meta["unit"]))
        if value <= 0 or value % tick:
            return None
        return int(value / unit)
