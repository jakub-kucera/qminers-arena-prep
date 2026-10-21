"""The Rust port (rust/) from Python: building it, exporting days for it, and running backtests on it.

rust/ ports arena/engine.py and some bots, each with its Python twin listed in rust/twins.json
(rust/README.md has the table of what is in which language). This module is the bridge:

  export_day    a Day as rust/src/support/dayfile.rs reads it (the format plug-ins stay in Python)
  write_day     a reference to a Prosperity day's own CSVs instead, which Rust reads itself
                (rust/src/arena/formats/prosperity.rs), when the day came from them; else export_day
  bot_spec      a twin bot for Rust: its kind, and its Python file's globals after any --set
                overrides, so the Rust bot reads the same settings (the template's DEFAULTS and
                PARAMS, a rival's constants)
  prepare       --engine rust's checks: bots with a twin for the format, a built binary
  run_days      `arena-rs run`: participants in one market on each day, on threads, back as Python
                DayResults (arena.backtest --engine rust)
  run_batch     `arena-rs batch`: many backtests on every core, each returning what arena.grid's
                Piece holds (arena.grid, arena.compare, arena.stress --engine rust)
  run_sim       `arena-rs sim`: arena.sim's market (rust/src/arena/sim.rs) on a range of seeds, with twin
                bots in it, read back as arena.sim.SimDay (arena.sim --engine rust)
  cscv, mean_correlation, snooping
                arena/stats.py's statistics that grow with a grid's cells, in rust/src/arena/stats.rs
                (arena.grid --engine rust): the same results to the bit
  read_day, read_results
                a day and DayResults as Rust wrote them, back as Python's own types, so the reports
                and CSVs work unchanged
  stale_twins   the twins whose Python file changed since the Rust port was last checked against it

Standard library only, like the rest of arena/ outside analysis.py. Nothing here is needed unless
a tool is asked for the Rust engine.
"""

from __future__ import annotations

import dataclasses
import functools
import hashlib
import itertools
import json
import shutil
import subprocess
import weakref
from collections import defaultdict
from dataclasses import fields
from pathlib import Path

from arena.botfile import BotFile
from arena.engine import DayResult, EngineConfig, TradeMatching
from arena.formats import prosperity
from arena.model import Book, Day, Fill, MarketTrade, OpenOrder, Tick

ROOT = Path(__file__).resolve().parent.parent
RUST = ROOT / "rust"
BINARY = RUST / "target" / "release" / "arena-rs"
TWINS = RUST / "twins.json"


def build() -> None:
    """Builds the release binary (cargo skips it when nothing changed)."""
    if shutil.which("cargo") is None:
        raise RuntimeError("the Rust engine needs cargo (brew install rust), see rust/README.md")
    subprocess.run(["cargo", "build", "--release", "--quiet", "--manifest-path", str(RUST / "Cargo.toml")], check=True)


# ---------------------------------------------------------------------------- twins


def twins() -> dict[str, dict]:
    """rust/twins.json: each Python file with a Rust port, by its path from the repo root."""
    return json.loads(TWINS.read_text())


@functools.lru_cache(maxsize=None)
def _kinds() -> dict[str, str]:
    return {path: twin["kind"] for path, twin in twins().items() if "kind" in twin}


@functools.lru_cache(maxsize=None)
def _formats() -> dict[str, str]:
    """Per kind: the format its Python twin is written for (default prosperity)."""
    return {twin["kind"]: twin.get("format", "prosperity") for twin in twins().values() if "kind" in twin}


def format_of(path: Path) -> str:
    """The format plug-in a twinned bot file runs under."""
    return _formats()[kind_of(path)]


@functools.lru_cache(maxsize=None)
def _reads_settings() -> dict[str, bool]:
    """Per kind: whether the Rust bot reads its settings from the Python file's globals (the zoo's don't)."""
    return {twin["kind"]: twin.get("settings", True) for twin in twins().values() if "kind" in twin}


def file_hash(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def stale_twins() -> list[str]:
    """The twins whose Python file isn't the one their Rust port was last checked against."""
    return [path for path, twin in twins().items() if file_hash(path) != twin["sha256"]]


def record_hashes() -> None:
    """Writes each twin's current hash: run only after the parity check passed (experiments/rust_bench.py --record)."""
    table = twins()
    for path, twin in table.items():
        twin["sha256"] = file_hash(path)
    TWINS.write_text(json.dumps(table, indent=2) + "\n")


def kind_of(path: Path) -> str:
    """The Rust bot kind of a bot file, or a ValueError naming the bots that have one."""
    try:
        relative = Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        relative = str(path)
    kinds = _kinds()
    if relative not in kinds:
        raise ValueError(f"{path} has no Rust twin (bots with one: {', '.join(kinds)})")
    return kinds[relative]


# ---------------------------------------------------------------------------- bots


def _jsonable(value) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_jsonable(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _jsonable(v) for k, v in value.items())
    return False


@functools.lru_cache(maxsize=None)
def _bot_file(path: Path) -> BotFile:
    from arena.formats import drill_exchange

    return BotFile(path, {"datamodel": prosperity.dm, "exchange": drill_exchange}, strict=False)


def bot_globals(path: Path, overrides: dict[str, object]) -> dict:
    """The bot file's upper-case globals that JSON can hold, after the overrides: what its Rust
    twin reads its settings from."""
    module = _bot_file(Path(path).resolve()).load(overrides)
    return {name: value for name, value in vars(module).items() if name.isupper() and not name.startswith("_") and _jsonable(value)}


def bot_spec(path: Path, overrides: dict[str, object], requote: bool = False) -> dict:
    kind = kind_of(path)
    if overrides and not _reads_settings()[kind]:
        raise ValueError(f"{path}'s Rust twin doesn't read its settings from the file (a zoo bot runs as written): drop the --set or use --engine python")
    return {"kind": kind, "globals": bot_globals(path, overrides) if _reads_settings()[kind] else {}, "requote": requote}


def config_json(config: EngineConfig) -> dict:
    return {f.name: (str(getattr(config, f.name)) if f.name in ("trade_matching", "queue") else getattr(config, f.name)) for f in fields(config)}


# ---------------------------------------------------------------------------- days


def _whole(price) -> int:
    if price != int(price):
        raise ValueError(f"the Rust engine takes whole prices, got {price}")
    return int(price)


def _name(text: str) -> str:
    if not text.isprintable() or text != text.strip():
        raise ValueError(f"a trader name in a day file is one printable line, without leading or trailing spaces: {text!r}")
    return text


def export_day(day: Day, path: Path) -> None:
    """Writes the day in rust/src/support/dayfile.rs's format: products sorted by name plus the day's own
    order and its limits' order, a format's tick sizes and price unit (Day.info), trader names by
    first appearance, each tick's books in its dict order."""
    products = sorted(day.products)
    index = {p: k for k, p in enumerate(products)}
    names = {"": 0}
    for tick in day.ticks:
        for trades in tick.trades.values():
            for t in trades:
                names.setdefault(_name(t.buyer), len(names))
                names.setdefault(_name(t.seller), len(names))
    info = [(p, meta) for p, meta in day.info.items() if p in index and "tick" in meta]
    lines = ["arena-day 3", f"name {day.name}", f"products {len(products)}", *(f"{p} {day.limits[p]}" for p in products),
             "order" + "".join(f" {index[p]}" for p in day.products), "limits" + "".join(f" {index[p]}" for p in day.limits if p in index),
             f"info {len(info)}", *(f"{index[p]} {float(meta['tick'])!r} {float(meta.get('unit', 0.01))!r}" for p, meta in info),
             f"names {len(names)}", *names, f"ticks {len(day.ticks)}"]
    side = lambda levels: f"{len(levels)}" + "".join(f" {_whole(price)} {volume}" for price, volume in levels)
    for tick in day.ticks:
        trades = [t for p in tick.trades for t in tick.trades[p]]
        lines.append(f"t {tick.timestamp} {len(tick.books)} {len(trades)} {len(tick.marks)}")
        lines += [f"b {index[p]} {side(book.bids)} {side(book.asks)}" for p, book in tick.books.items()]
        lines += [f"x {index[t.product]} {_whole(t.price)} {t.quantity} {names[t.buyer]} {names[t.seller]} {t.timestamp}" for t in trades]
        lines += [f"m {index[p]} {float(mark)!r}" for p, mark in tick.marks.items()]
    path.write_text("\n".join(lines) + "\n")


def write_day(day: Day, stem: Path, only: list[str] | None = None) -> Path:
    """The day for Rust at stem.json, a reference to its Prosperity CSVs that Rust reads itself
    (rust/src/arena/formats/prosperity.rs), if it was loaded from them (prosperity.reference); else exported to
    stem.day. With `only`, just those products (arena.grid.only). Returns the path written."""
    ref = prosperity.reference(day, only)
    if ref is not None:
        path = stem.with_suffix(".json")
        path.write_text(json.dumps(ref))
        return path
    if only is not None:
        from arena.grid import only as restrict

        day = restrict(day, only)
    path = stem.with_suffix(".day")
    export_day(day, path)
    return path


# ---------------------------------------------------------------------------- runs


def prepare(format_name: str, bots: list[Path]) -> None:
    """--engine rust: bots with a Rust twin written for the format (prosperity, or drill for
    bots/drill/template.py) that has been checked against them since they last changed (a warning
    if not), and a built binary. ValueError if not."""
    import sys

    for path in bots:
        if format_of(path) != format_name:
            raise ValueError(f"{path}'s Rust twin is for --format {format_of(path)}, not {format_name}")
    stale = stale_twins()
    if stale:
        print(f"! the Rust twins of {', '.join(stale)} weren't checked since that file changed: their results may differ "
              "(uv run python -m experiments.rust_bench --parity-only --record)", file=sys.stderr)
    build()


def run_days(days: list[Day], bots: list[tuple[str, Path, dict, bool]], config: EngineConfig, threads: int = 1) -> list[list[DayResult]]:
    """`arena-rs run`: the (name, bot file, overrides, requote) participants in one market on each
    day, the days on `threads` threads; per day, each participant's DayResult (read_results)."""
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        scratch = Path(folder)
        paths = [write_day(day, scratch / f"day{k}") for k, day in enumerate(days)]
        dump = scratch / "dump.jsonl"
        out = subprocess.run([str(BINARY), "run", *map(str, paths), *_engine_args(config), *_bot_args(bots, scratch), "--dump", str(dump),
                              "--threads", str(threads)], stdout=subprocess.DEVNULL)
        if out.returncode != 0:
            raise RuntimeError(f"arena-rs run failed (exit {out.returncode}); its message is above")
        lines = dump.read_text().splitlines()
    n = len(bots)
    found = []
    for k, day in enumerate(days):
        results = read_results("\n".join(lines[k * n:(k + 1) * n]), day)
        found.append([results[name] for name, *_ in bots])
    return found


# ---------------------------------------------------------------------------- batches


def run_batch(day_paths: list[Path], specs: list[dict], tasks: list[dict], threads: int, scratch: Path) -> list[dict]:
    """`arena-rs batch`: each task {day, config, bots: [[name, spec index], ...], blocks, fine} on
    `threads` threads, returning per task the first participant's {pnl, blocks, fine, products,
    drawdowns, fills, errors, breaches, races, first_error} (as arena.grid's Piece, plus each
    product's report.max_drawdown) and "others", the other participants' {pnl, products, fills,
    errors, breaches, races}, in task order."""
    path = scratch / "batch.json"
    path.write_text(json.dumps({"days": [str(p) for p in day_paths], "bots": specs, "tasks": tasks}))
    out = subprocess.run([str(BINARY), "batch", str(path), "--threads", str(threads)], stdout=subprocess.PIPE, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"arena-rs batch failed (exit {out.returncode}); its message is above")
    return [json.loads(line) for line in out.stdout.splitlines()]


def _engine_args(config: EngineConfig) -> list[str]:
    args = ["--match-trades", str(config.trade_matching), "--queue", str(config.queue), "--queue-power", repr(config.queue_power),
            "--fill-ratio", repr(config.fill_ratio), "--seed", str(config.seed)]
    return args + (["--resting"] if config.resting else [])


def _bot_args(bots: list[tuple[str, Path, dict, bool]], scratch: Path) -> list[str]:
    """--bot options for (name, bot file, overrides, requote) participants, their specs written to scratch."""
    args = []
    for j, (name, path, overrides, requote) in enumerate(bots):
        spec = scratch / f"bot{j}.json"
        spec.write_text(json.dumps(bot_spec(path, overrides, requote)))
        args += ["--bot", f"{name}={spec}"]
    return args


# ---------------------------------------------------------------------------- reading Rust's output


def _number(text: str) -> int | float:
    """A number as Rust wrote it: an int without a point, a float with one (repr's form)."""
    try:
        return int(text)
    except ValueError:
        return float(text)


def read_day(path: Path, with_books: bool = True) -> Day:
    """A day in rust/src/support/dayfile.rs's format as Python's Day: products and books in the day's own
    order, each tick's trades grouped by product in the order they appear, marks as written (an int
    stays an int). Without `with_books` every tick's books are left empty (quicker, for read_results)."""
    lines = iter(Path(path).read_text().splitlines())
    version = next(lines)
    assert version in ("arena-day 2", "arena-day 3"), f"{path}: not an arena-day 3 file"
    name = next(lines).removeprefix("name ")
    sorted_products, limits = [], {}
    for _ in range(int(next(lines).split()[1])):
        product, limit = next(lines).rsplit(" ", 1)
        sorted_products.append(product)
        limits[product] = int(limit)
    order = [sorted_products[int(k)] for k in next(lines).split()[1:]]
    limits_order, info = order, {}
    if version == "arena-day 3":
        limits_order = [sorted_products[int(k)] for k in next(lines).split()[1:]]
        for _ in range(int(next(lines).split()[1])):
            p, tick, unit = next(lines).split()
            info[sorted_products[int(p)]] = {"tick": float(tick), "unit": float(unit)}
    names = [next(lines) for _ in range(int(next(lines).split()[1]))]
    ticks = []
    for _ in range(int(next(lines).split()[1])):
        _, timestamp, nb, nt, nm = next(lines).split()
        books, trades, marks = {}, defaultdict(list), {}
        for _ in range(int(nb)):
            line = next(lines)
            if not with_books:
                continue
            f = line.split()
            product, k = sorted_products[int(f[1])], 2
            sides = []
            for _ in range(2):
                n = int(f[k])
                sides.append(tuple((int(f[k + 1 + 2 * j]), int(f[k + 2 + 2 * j])) for j in range(n)))
                k += 1 + 2 * n
            books[product] = Book(*sides)
        for _ in range(int(nt)):
            _, p, price, quantity, buyer, seller, ts = next(lines).split()
            product = sorted_products[int(p)]
            trades[product].append(MarketTrade(product, int(price), int(quantity), names[int(buyer)], names[int(seller)], int(ts)))
        for _ in range(int(nm)):
            _, p, mark = next(lines).split()
            marks[sorted_products[int(p)]] = _number(mark)
        ticks.append(Tick(int(timestamp), books, dict(trades), marks))
    return Day(name, order, {p: limits[p] for p in limits_order}, ticks, info)


SERIES = ("positions", "marks", "pnl", "best_bids", "best_asks", "wall_mids")  # per product, one value per tick


def read_dump(text: str) -> dict[str, dict]:
    """`arena-rs run --dump` (and sim's .dump files), one JSON line per participant: its DayResult's
    fields as tuples (fills as (timestamp, product, price, quantity, source, order id, counterparty)),
    by participant name."""
    out = {}
    for line in text.splitlines():
        r = json.loads(line)
        for key in ("fills", "orders", "cancels", "breaches", "races", "errors"):
            r[key] = [tuple(item) for item in r[key]]
        out[r.pop("participant")] = r
    return out


def read_results(text: str, day: Day | None = None) -> dict[str, DayResult]:
    """A dump as Python DayResults: what our engine records, except step timings and output sizes
    (a Rust bot has neither); the fields left out of the dump (--fields) are empty. The market
    trades come from `day`, the day Rust ran on as Python holds it, if given (else none)."""
    out = {}
    market_trades = [(t.timestamp, trade) for t in day.ticks for trades in t.trades.values() for trade in trades] if day is not None else []
    for name, r in read_dump(text).items():
        products = r["products"]
        result = DayResult(r["day"], list(products), dict(zip(products, r["limits"])), r["timestamps"])
        for field in SERIES:
            setattr(result, field, {p: r["series"][p][field] for p in products})
        result.market_trades = list(market_trades)
        result.orders = [(ts, OpenOrder(i, product, price, quantity, placed)) for ts, i, product, price, quantity, placed in r["orders"]]
        result.cancels = r["cancels"]
        result.fills = [Fill(ts, product, price, quantity, source, counterparty, i) for ts, product, price, quantity, source, i, counterparty in r["fills"]]
        result.errors = r["errors"]
        result.limit_breaches = r["breaches"]
        result.races = r["races"]
        out[name] = result
    return out


# ---------------------------------------------------------------------------- one backtest at a time (the experiments)

_SCRATCH: list = []  # this process's folder for exported days, made on first use
_EXPORTED: dict[int, Path] = {}  # id(day) -> its file, while the day lives
_SIM_DAYS: dict[tuple, Path] = {}
_COUNT = itertools.count()  # names this process's day files


def _scratch() -> Path:
    if not _SCRATCH:
        import atexit
        import tempfile

        folder = tempfile.TemporaryDirectory()
        atexit.register(folder.cleanup)
        _SCRATCH.append(folder)
    return Path(_SCRATCH[0].name)


def day_file(day: Day) -> Path:
    """The day for Rust (write_day: a reference to its CSVs, or exported), once per process and
    day: the entry and its file go when the day does."""
    if id(day) not in _EXPORTED:
        _EXPORTED[id(day)] = write_day(day, _scratch() / f"day{next(_COUNT)}")
        weakref.finalize(day, _forget, id(day))
    return _EXPORTED[id(day)]


def _forget(key: int) -> None:
    path = _EXPORTED.pop(key, None)
    if path is not None:
        path.unlink(missing_ok=True)


_REFERENCES: dict[tuple, Path] = {}


def prosperity_day(data: str | Path, round_num: int, day_num: int, only: list[str] | None = None) -> Path:
    """A Prosperity day for Rust that Rust reads from its CSVs itself, with nothing loaded in Python
    (prosperity.reference_to), once per process, into a day file the later runs read: for a worker
    that only backtests on it. `data` is
    a folder or an alias (p2, p3, p4); the results' days are named as the plug-in names them, r{round}d{day}."""
    key = (str(data), round_num, day_num, tuple(only) if only is not None else None)
    if key not in _REFERENCES:
        # Rust reads the CSVs once and writes the day file it reads several times faster (`arena-rs day`)
        folder = _scratch() / f"ref{next(_COUNT)}"
        folder.mkdir()
        reference = folder / "day.json"
        reference.write_text(json.dumps(prosperity.reference_to(prosperity.resolve_data_dir(str(data)), round_num, day_num, only)))
        out = subprocess.run([str(BINARY), "day", str(reference), "--out", str(folder)], stdout=subprocess.DEVNULL)
        if out.returncode != 0:
            raise RuntimeError(f"arena-rs day failed (exit {out.returncode}); its message is above")
        _REFERENCES[key] = folder / f"r{round_num}d{day_num}.day"
    return _REFERENCES[key]


def named_day(data: str | Path, name: str, only: list[str] | None = None) -> Path:
    """prosperity_day for a day named as the plug-in names it (r{round}d{day}, e.g. r1d-2)."""
    round_num, day_num = name.removeprefix("r").split("d")
    return prosperity_day(data, int(round_num), int(day_num), only)


def prosperity_days(data: str | Path, specs: list[str], only: list[str] | None = None) -> list[Path]:
    """prosperity_day for each day the specs select (ROUND or ROUND-DAY, as load_days takes them)."""
    directory = prosperity.resolve_data_dir(str(data))
    return [prosperity_day(data, r, d, only) for r, d in prosperity.parse_day_specs(specs, directory)]


def sim_day_file(spec, seed: int) -> Path:
    """arena.sim's recording of the spec and seed (no bots), written by Rust straight to a day file,
    once per process: what `day_file(arena.sim.run(spec, seed).day)` holds, without the Python run."""
    key = (json.dumps(spec_json(spec), sort_keys=True), seed)
    if key not in _SIM_DAYS:
        folder = _scratch() / f"sim{len(_SIM_DAYS)}"
        folder.mkdir()
        path = folder / "spec.json"
        path.write_text(key[0])
        out = subprocess.run([str(BINARY), "sim", str(path), "--market-seed", str(seed), "--out", str(folder)], stdout=subprocess.DEVNULL)
        if out.returncode != 0:
            raise RuntimeError(f"arena-rs sim failed (exit {out.returncode}); its message is above")
        _SIM_DAYS[key] = folder / f"sim{seed}.day"
    return _SIM_DAYS[key]


def backtest(day: Day | Path, bots: list[tuple[str, Path, dict, bool]], config: EngineConfig, fields: tuple[str, ...] | None = None) -> list[DayResult]:
    """The (name, bot file, overrides, requote) participants in one market on one day (a Day, or a
    day file from day_file or sim_day_file), each one's DayResult; with `fields` only those are
    filled (e.g. ("pnl", "errors", "breaches")), which reads back much faster. A Day gives the
    results its market trades."""
    path = day if isinstance(day, Path) else day_file(day)
    folder = _scratch()
    dump = folder / "dump.jsonl"
    args = [str(BINARY), "run", str(path), *_engine_args(config), *_bot_args(bots, folder), "--dump", str(dump)]
    if fields is not None:
        args += ["--fields", ",".join(fields)]
    out = subprocess.run(args, stdout=subprocess.DEVNULL)
    if out.returncode != 0:
        raise RuntimeError(f"arena-rs run failed (exit {out.returncode}); its message is above")
    results = read_results(dump.read_text(), None if isinstance(day, Path) else day)
    return [results[name] for name, *_ in bots]


# ---------------------------------------------------------------------------- arena.sim


def spec_json(spec) -> dict:
    """An arena.sim MarketSpec as rust/src/arena/sim.rs reads it."""
    return dataclasses.asdict(spec)


def run_sim(spec, seed: int, days: int = 1, bots: list[tuple[str, Path, dict, bool]] = (), config: EngineConfig = EngineConfig(),
            replay: bool = False, read: bool | str = False, csv: Path | None = None, round_number: int = 1, threads: int = 1) -> list[dict]:
    """`arena-rs sim`: the market on seeds seed..seed+days-1 with the (name, bot file, overrides,
    requote) participants in it (resting if config.resting), on `threads` threads. Per day, in seed
    order: {"seed", "day", "trades", "bots": {name: totals}}, the totals being {"pnl", "products":
    {product: pnl}, "fills", "errors", "breaches", "races", "first_error"}; with `replay` also
    "replays" ({trade matching: {name: totals}}: the bots on the day without them, under config's
    other settings, as arena.sim run prints). `read` adds the whole of it as Python objects, which
    costs more than the run: "sim" (an arena.sim.SimDay, as arena.sim.run returns it), and with
    `replay` "recording" (the day without the bots) and "replay_results" ({trade matching: the
    bots' DayResults}); read="results" adds only "results", the bots' DayResults in the market.
    `csv` writes the Prosperity layout there (limits.json is the caller's)."""
    import tempfile

    from arena.sim import SimDay

    with tempfile.TemporaryDirectory() as folder:
        scratch = Path(folder)
        path = scratch / "spec.json"
        path.write_text(json.dumps(spec_json(spec)))
        args = [str(BINARY), "sim", str(path), "--market-seed", str(seed), "--days", str(days), "--threads", str(threads),
                *_engine_args(config), *_bot_args(list(bots), scratch)]
        if read:
            args += ["--out", str(scratch)]
        if replay:
            args.append("--replay")
        if csv is not None:
            args += ["--csv", str(csv), "--round", str(round_number)]
        out = subprocess.run(args, stdout=subprocess.PIPE, text=True)
        if out.returncode != 0:
            raise RuntimeError(f"arena-rs sim failed (exit {out.returncode}); its message is above")
        found = [json.loads(line) for line in out.stdout.splitlines()]
        for row in found:
            if "replays" in row:
                row["replays"] = {TradeMatching(mode): totals for mode, totals in row["replays"].items()}
            if not read:
                continue
            stem = scratch / f"sim{row['seed']}"
            if read == "results":
                results = read_results(stem.with_suffix(".dump").read_text(), read_day(stem.with_suffix(".day"), with_books=False))
                row["results"] = [results[name] for name, *_ in bots]
                continue
            day = read_day(stem.with_suffix(".day"))
            fundamentals = {}
            for line in stem.with_suffix(".fundamentals").read_text().splitlines():
                product, *values = line.split(" ")
                fundamentals[product] = [float(v) for v in values]
            results = read_results(stem.with_suffix(".dump").read_text(), day) if bots else {}
            row["sim"] = SimDay(day, {p: fundamentals[p] for p in day.products}, [results[name] for name, *_ in bots])
            if replay and bots:
                recording = read_day(Path(f"{stem}.recording.day"))
                row["recording"] = recording
                row["replay_results"] = {}
                for mode in TradeMatching:
                    results = read_results(Path(f"{stem}.replay.{mode}.dump").read_text(), recording)
                    row["replay_results"][mode] = [results[name] for name, *_ in bots]
        return found


# ---------------------------------------------------------------------------- arena.stats


def _stats(request: dict):
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "stats.json"
        path.write_text(json.dumps(request))
        out = subprocess.run([str(BINARY), "stats", str(path)], stdout=subprocess.PIPE, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"arena-rs stats failed (exit {out.returncode}); its message is above")
    return json.loads(out.stdout)


def cscv(columns: list[list[float]], max_splits: int | None = None, seed: int = 0):
    """arena.stats.cscv in rust/src/arena/stats.rs."""
    from arena import stats

    found = _stats({"cscv": {"columns": columns, "max_splits": stats.MAX_SPLITS if max_splits is None else max_splits, "seed": seed}})
    return stats.Cscv(found["pbo"], found["loss"], found["rank"], found["splits"], found["of"])


def mean_correlation(scaled: list[list[float]]) -> float | None:
    """arena.stats.mean_correlation in rust/src/arena/stats.rs."""
    return _stats({"correlation": {"scaled": scaled}})


def snooping(d: list[list[float]], q: float, boot: int, alpha: float | None = None, seed: int = 0) -> tuple[dict[str, float], list[int]]:
    """arena.stats.snooping in rust/src/arena/stats.rs."""
    from arena import stats

    found = _stats({"snooping": {"d": d, "q": q, "boot": boot, "alpha": stats.ALPHA if alpha is None else alpha, "seed": seed}})
    return found["spa"], found["stepm"]
