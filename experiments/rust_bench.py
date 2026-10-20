"""The Rust engine against ours: same results, then how much faster. For TODO.md's decision
"Rewrite the engine and the strategies in a fast language for huge sweeps?".

usage (from the repo root; needs cargo): uv run python -m experiments.rust_bench [--jobs N] [--parity-only]

rust/ ports arena/engine.py whole (both modes, the three queue models, the fill ratio's seeded
draws, several bots in one market) and one bot, rust/src/bots/mm.rs, whose Python twin is
bots/mm.py. Days are loaded by our format plug-ins and exported for it (`export_day`).
  1. parity: every field a DayResult records (fills, orders, cancels, breaches, races, errors, and
     per tick each product's position, mark, PnL, best bid and ask, wall mid), Rust against our
     engine, under each configuration in CONFIGS, on P3 round 1 day -2;
  2. one core: time per backtest of the same bot, ours (the bot file through the Prosperity
     adapter, loaded per backtest as arena.grid does) against Rust's, default and resting mode;
  3. every core: Kelp's 64-cell grid (make_edge 0..7 x take_edge 0..7) on the round's three days
     under all and worse: arena.grid against `arena-rs grid`.
Results go into TODO.md (the decision). tests/test_rust.py runs part 1 on an arena.sim day.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from arena import grid
from arena.engine import EngineConfig, QueueModel, TradeMatching, run_day, run_market
from arena.formats import prosperity
from arena.model import Day

ROOT = Path(__file__).resolve().parent.parent
RUST = ROOT / "rust"
BINARY = RUST / "target" / "release" / "arena-rs"
BOT = ROOT / "bots" / "mm.py"
SAMPLE = 6  # Python backtests timed on one core per measurement

# A bot: (name, {product: (make_edge, take_edge, hold)}). Two products, so the engine's per-product
# paths run; `hold` keeps quotes resting, so their queue position matters.
ONE = [("you", {"KELP": (1, 1, False), "RAINFOREST_RESIN": (2, 1, False)})]
TWO = ONE + [("rival", {"KELP": (0, 1, False), "RAINFOREST_RESIN": (1, 2, False)})]
HOLD = [("you", {"KELP": (1, 1, True), "RAINFOREST_RESIN": (2, 1, True)})]
HOLD_TWO = HOLD + [("rival", {"KELP": (0, 1, True), "RAINFOREST_RESIN": (1, 2, False)})]
ALL, WORSE, NONE = TradeMatching.ALL, TradeMatching.WORSE, TradeMatching.NONE
CONFIGS = [
    ("default, all", EngineConfig(), ONE),
    ("default, worse", EngineConfig(trade_matching=WORSE), ONE),
    ("default, none", EngineConfig(trade_matching=NONE), ONE),
    ("default, fill ratio 0.6", EngineConfig(fill_ratio=0.6, seed=1), ONE),
    ("resting", EngineConfig(resting=True), ONE),
    ("resting, holding, back", EngineConfig(resting=True), HOLD),
    ("resting, holding, back, worse", EngineConfig(resting=True, trade_matching=WORSE), HOLD),
    ("resting, holding, prob", EngineConfig(resting=True, queue=QueueModel.PROB), HOLD),
    ("resting, holding, prob, power 3", EngineConfig(resting=True, queue=QueueModel.PROB, queue_power=3.0), HOLD),
    ("resting, holding, front", EngineConfig(resting=True, queue=QueueModel.FRONT), HOLD),
    ("resting, holding, prob, fill ratio 0.6", EngineConfig(resting=True, queue=QueueModel.PROB, fill_ratio=0.6, seed=2), HOLD),
    ("two bots", EngineConfig(), TWO),
    ("two bots, worse", EngineConfig(trade_matching=WORSE), TWO),
    ("two bots, resting", EngineConfig(resting=True), TWO),
    ("two bots, resting, holding, prob, fill ratio 0.6", EngineConfig(resting=True, queue=QueueModel.PROB, fill_ratio=0.6, seed=3), HOLD_TWO),
]


def build() -> None:
    subprocess.run(["cargo", "build", "--release", "--quiet", "--manifest-path", str(RUST / "Cargo.toml")], check=True)


# ---------------------------------------------------------------------------- export


def _whole(price) -> int:
    if price != int(price):
        raise ValueError(f"the Rust engine takes whole prices, got {price}")
    return int(price)


def _name(text: str) -> str:
    if any(c.isspace() for c in text):
        raise ValueError(f"trader names can't hold whitespace in a day file: {text!r}")
    return text


def export_day(day: Day, path: Path) -> None:
    """Writes the day in rust/src/dayfile.rs's format (products sorted by name, names by first appearance)."""
    products = sorted(day.products)
    index = {p: k for k, p in enumerate(products)}
    names = {"": 0}
    for tick in day.ticks:
        for trades in tick.trades.values():
            for t in trades:
                names.setdefault(_name(t.buyer), len(names))
                names.setdefault(_name(t.seller), len(names))
    lines = ["arena-day 1", f"name {day.name}", f"products {len(products)}", *(f"{p} {day.limits[p]}" for p in products),
             f"names {len(names)}", *names, f"ticks {len(day.ticks)}"]
    side = lambda levels: f"{len(levels)}" + "".join(f" {_whole(price)} {volume}" for price, volume in levels)
    for tick in day.ticks:
        trades = [t for p in tick.trades for t in tick.trades[p]]
        lines.append(f"t {tick.timestamp} {len(tick.books)} {len(trades)} {len(tick.marks)}")
        lines += [f"b {index[p]} {side(book.bids)} {side(book.asks)}" for p, book in tick.books.items()]
        lines += [f"x {index[t.product]} {_whole(t.price)} {t.quantity} {names[t.buyer]} {names[t.seller]} {t.timestamp}" for t in trades]
        lines += [f"m {index[p]} {float(mark)!r}" for p, mark in tick.marks.items()]
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------- parity


def _rust_bots(bots) -> list[str]:
    return [arg for name, params in bots
            for arg in ("--bot", f"{name}=" + "+".join(f"{p}:{m}:{t}" + (":hold" if h else "") for p, (m, t, h) in params.items()))]


def _rust_engine(config: EngineConfig) -> list[str]:
    args = ["--match-trades", str(config.trade_matching), "--queue", str(config.queue), "--queue-power", repr(config.queue_power),
            "--fill-ratio", repr(config.fill_ratio), "--seed", str(config.seed)]
    return args + (["--resting"] if config.resting else [])


def _python_bot(params: dict):
    return prosperity.load_bot(BOT, {"PARAMS": {p: {"make_edge": m, "take_edge": t, "hold": h} for p, (m, t, h) in params.items()}}, strict=True)


def _int_or_none(text: str):
    return None if text == "~" else int(text)


def _float_or_none(text: str):
    return None if text == "~" else float(text)


def _fill(line: str) -> tuple:
    f = line.split(" ", 6)
    return int(f[0]), f[1], int(f[2]), int(f[3]), f[4], int(f[5]), f[6] if len(f) > 6 else ""


SECTIONS = {
    "fills": _fill,
    "orders": lambda line: tuple(x if i == 2 else int(x) for i, x in enumerate(line.split())),
    "cancels": lambda line: tuple(map(int, line.split())),
    "breaches": lambda line: (int(line.split()[0]), line.split()[1]),
    "races": lambda line: (int(line.split()[0]), line.split()[1]),
    "errors": lambda line: (int(line.split(" ", 1)[0]), line.split(" ", 1)[1]),
}
SERIES = {"positions": int, "marks": float, "pnl": float, "best_bids": _int_or_none, "best_asks": _int_or_none, "wall_mids": _float_or_none}


def parse_dump(text: str) -> dict[str, dict]:
    """arena-rs run --dump: per participant, its DayResult's fields."""
    out, lines, k = {}, text.split("\n"), 0
    while k < len(lines) and lines[k]:
        name = lines[k].split(" ", 2)[2]
        k += 1
        r = {}
        for key, parse in SECTIONS.items():
            label, count = lines[k].split()
            assert label == key, (label, key)
            r[key] = [parse(line) for line in lines[k + 1:k + 1 + int(count)]]
            k += 1 + int(count)
        r["market_trades"] = int(lines[k].split()[1])
        k += 1
        r["series"] = {}
        while k < len(lines) and lines[k].startswith("series "):
            product = lines[k].split(" ", 1)[1]
            r["series"][product] = {field: [parse(x) for x in row.split()] for (field, parse), row in zip(SERIES.items(), lines[k + 1:k + 7])}
            k += 7
        out[name] = r
    return out


def python_view(result) -> dict:
    """The same fields from our engine's DayResult."""
    return {
        "fills": [(f.timestamp, f.product, f.price, f.quantity, f.source, f.order_id, f.counterparty) for f in result.fills],
        "orders": [(ts, o.id, o.product, o.price, o.quantity, o.timestamp) for ts, o in result.orders],
        "cancels": list(result.cancels),
        "breaches": list(result.limit_breaches),
        "races": list(result.races),
        "errors": list(result.errors),
        "market_trades": len(result.market_trades),
        "series": {p: {field: getattr(result, field)[p] for field in SERIES} for p in sorted(result.products)},
    }


def _first(a: list, b: list) -> int:
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def differences(ours: dict, theirs: dict) -> list[str]:
    """Where two views disagree: the first difference per field, with its index."""
    found = []
    for key, a in ours.items():
        b = theirs[key]
        if key == "series":
            for product, fields in a.items():
                for field, values in fields.items():
                    other = b[product][field]
                    if values != other:
                        k = _first(values, other)
                        found.append(f"{product} {field}[{k}]: {values[k:k + 1]} against {other[k:k + 1]} ({len(values)} / {len(other)} values)")
        elif isinstance(a, list) and a != b:
            k = _first(a, b)
            found.append(f"{key}[{k}]: {a[k:k + 1]} against {b[k:k + 1]} ({len(a)} / {len(b)})")
        elif a != b:
            found.append(f"{key}: {a} against {b}")
    return found


def parity(day: Day, scratch: Path, configs=CONFIGS) -> list[tuple[str, tuple, list[str]]]:
    """Each configuration on the day in both engines: (name, (fills, cross fills, races, breaches), differences)."""
    path = scratch / f"{day.name}.day"
    export_day(day, path)
    out = []
    for name, config, bots in configs:
        dump = scratch / "dump.txt"
        subprocess.run([str(BINARY), "run", str(path), *_rust_engine(config), *_rust_bots(bots), "--dump", str(dump)], check=True, capture_output=True)
        theirs = parse_dump(dump.read_text())
        ours = run_market(day, [(bot, _python_bot(params)) for bot, params in bots], config)
        found = [f"{bot}: {d}" for (bot, _), result in zip(bots, ours) for d in differences(python_view(result), theirs[bot])]
        counts = (sum(len(r.fills) for r in ours), sum(f.source == "cross" for r in ours for f in r.fills),
                  sum(len(r.races) for r in ours), sum(len(r.limit_breaches) for r in ours))
        out.append((name, counts, found))
    return out


# ---------------------------------------------------------------------------- timing


def python_time(day: Day, config: EngineConfig) -> tuple[float, float]:
    """Seconds per backtest of bots/mm.py as committed (Kelp only), loaded per backtest as arena.grid
    does, and the share of it in the bot's step (the Prosperity adapter included)."""
    start, in_bot = time.perf_counter(), 0.0
    for _ in range(SAMPLE):
        result = run_day(day, prosperity.load_bot(BOT, {}, strict=False), config)
        in_bot += sum(result.step_seconds)
    total = time.perf_counter() - start
    return total / SAMPLE, in_bot / total


def rust_grid(paths: list[Path], config: EngineConfig, threads: int, repeat: int, edges=(1,), modes="all") -> tuple[float, float, str]:
    """`arena-rs grid`: (thread-seconds per backtest, wall seconds per repeat, its CSV)."""
    values = ",".join(map(str, edges))
    out = subprocess.run([str(BINARY), "grid", *map(str, paths), *_rust_engine(config), "--make", values, "--take", values, "--modes", modes,
                          "--threads", str(threads), "--repeat", str(repeat)], check=True, capture_output=True, text=True)
    match = re.search(r"in ([\d.]+) s: ([\d.]+) ms of a thread each", out.stderr)
    return float(match.group(2)) / 1e3, float(match.group(1)) / repeat, out.stdout


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.rust_bench")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--parity-only", action="store_true")
    args = parser.parse_args()
    build()
    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["1"])
    with tempfile.TemporaryDirectory() as folder:
        scratch = Path(folder)
        print(f"1. parity on {days[0].name}, every recorded field (bots/mm.py against rust/src/bots/mm.rs):")
        for name, (fills, crossed, races, breaches), found in parity(days[0], scratch):
            print(f"   {name:<50} {fills:>6,} fills ({crossed:,} crossed), {races} races, {breaches} breaches: "
                  + ("identical" if not found else f"! {len(found)} differences: {found[0]}"))
        if args.parity_only:
            return

        full = [scratch / f"{day.name}.day" for day in days]
        kelp = [scratch / f"{day.name}.kelp.day" for day in days]
        for day, a, b in zip(days, full, kelp):
            export_day(day, a)
            export_day(grid.only(day, ["KELP"]), b)
        print(f"\n2. one core, per backtest of a {len(days[0].ticks):,}-tick day, bots/mm.py on Kelp (Python: the bot file "
              "through the Prosperity adapter, loaded per backtest):")
        for label, day, path, config in (("all three products, default", days[0], full[0], EngineConfig()),
                                         ("all three products, resting", days[0], full[0], EngineConfig(resting=True)),
                                         ("Kelp only, default", grid.only(days[0], ["KELP"]), kelp[0], EngineConfig())):
            ours, share = python_time(day, config)
            theirs = rust_grid([path], config, 1, 200)[0]
            print(f"   {label:<30} Python {ours * 1e3:6.1f} ms ({share:.0%} in the bot)   Rust {theirs * 1e3:6.3f} ms   {ours / theirs:,.0f}x")

        edges = range(8)
        print(f"\n3. every core ({args.jobs}): Kelp's 64-cell grid on {len(days)} days under all and worse (384 backtests):")
        sys.stdout.flush()
        start = time.perf_counter()
        subprocess.run([sys.executable, "-m", "arena.grid", str(BOT), "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0..7",
                        "--grid", "PARAMS.KELP.take_edge=0..7", "--modes", "all,worse", "--jobs", str(args.jobs)], check=True, capture_output=True)
        python_wall = time.perf_counter() - start
        _, rust_kelp, csv_kelp = rust_grid(kelp, EngineConfig(), args.jobs, 20, edges, "all,worse")
        _, rust_full, csv_full = rust_grid(full, EngineConfig(), args.jobs, 20, edges, "all,worse")
        same = [line.split(",")[4] for line in csv_kelp.splitlines()[1:]] == [line.split(",")[4] for line in csv_full.splitlines()[1:]]
        print(f"   arena.grid (its checks, Kelp-only days): {python_wall:.1f} s;  arena-rs grid: {rust_kelp * 1e3:.0f} ms on Kelp-only days, "
              f"{rust_full * 1e3:.0f} ms on full days (same PnL: {same});  {python_wall / rust_kelp:,.0f}x")


if __name__ == "__main__":
    main()
