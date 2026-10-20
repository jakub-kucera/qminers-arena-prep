"""How much faster is a backtest in Rust? A measurement for TODO.md's decision "Rewrite the engine
and the strategies in a fast language for huge sweeps?".

usage (from the repo root; needs cargo): uv run python -m experiments.rust_bench [--jobs N]

One strategy, written twice: experiments/rust_mm/mm.py (a Prosperity bot file) and `strategy` in
experiments/rust_mm/src/main.rs, with the engine's default mode ported beside it (one participant,
orders live one tick, fill ratio 1). On P3 round 1's three days, Kelp only (as arena.grid runs a
Kelp grid), a 64-cell grid of make_edge 0..7 x take_edge 0..7 under `all` and `worse`:
  1. parity: every cell's PnL and fill count, our engine against the Rust one;
  2. one core: time per backtest, the bot through our engine and format (what arena.grid runs) and
     in Rust, plus the template on the same Kelp days for scale;
  3. every core: the grid end to end, arena.grid on the bot file against the Rust binary.
Results go into TODO.md (the decision) and IDEAS.md is not touched: this is tooling, not strategy.
"""

from __future__ import annotations

import argparse
import itertools
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import grid
from arena.engine import EngineConfig, TradeMatching, run_day
from arena.formats import prosperity

HERE = Path(__file__).parent / "rust_mm"
BOT, TEMPLATE = HERE / "mm.py", Path("bots/template.py")
EDGES = list(range(8))
MODES = [TradeMatching.ALL, TradeMatching.WORSE]
SAMPLE = 6  # Python backtests timed on one core, per bot


def kelp_days():
    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["1"])
    return [grid.only(day, ["KELP"]) for day in days]


def export(day, path: Path) -> None:
    """One line per tick: the mark (engine._mark's rule), then bids, asks and market trades as counted pairs."""
    lines, last = [], 0.0
    for tick in day.ticks:
        book = tick.books.get("KELP")
        mark = tick.marks.get("KELP", book.mid if book and book.mid is not None else last)
        last = mark
        bids, asks = (book.bids, book.asks) if book else ((), ())
        trades = [(t.price, t.quantity) for t in tick.trades.get("KELP", [])]
        pairs = lambda levels: f"{len(levels)} " + " ".join(f"{p} {v}" for p, v in levels)
        lines.append(f"{mark!r} {pairs(bids)} {pairs(asks)} {pairs(trades)}")
    path.write_text("\n".join(lines) + "\n")


_DAYS: list = []


def _python(task):
    d, mode, make, take = task
    if not _DAYS:
        _DAYS.extend(kelp_days())
    bot = prosperity.load_bot(BOT, {"PARAMS.KELP.make_edge": make, "PARAMS.KELP.take_edge": take}, strict=True)
    result = run_day(_DAYS[d], bot, EngineConfig(trade_matching=mode))
    return task, (result.pnl["KELP"][-1], len(result.fills))


def rust(binary: Path, files: list[Path], threads: int, repeat: int) -> tuple[dict, str]:
    edges = ",".join(map(str, EDGES))
    out = subprocess.run([str(binary), *map(str, files), "--make", edges, "--take", edges, "--modes", "all,worse",
                          "--threads", str(threads), "--repeat", str(repeat)], capture_output=True, text=True, check=True)
    rows = {}
    for line in out.stdout.splitlines()[1:]:
        d, mode, make, take, pnl, fills = line.split(",")
        rows[(int(d), TradeMatching(mode), int(float(make)), int(float(take)))] = (float(pnl), int(fills))
    return rows, out.stderr.strip()


def one_core(days, path: Path, overrides: dict) -> tuple[float, float]:
    """Seconds per backtest on one core (SAMPLE runs, the first day under `all`, the bot loaded each
    time as arena.grid does), and the share of it spent in the bot's step (format adapter included)."""
    start, in_bot = time.perf_counter(), 0.0
    for _ in range(SAMPLE):
        result = run_day(days[0], prosperity.load_bot(path, overrides, strict=False), EngineConfig(trade_matching=TradeMatching.ALL))
        in_bot += sum(result.step_seconds)
    total = time.perf_counter() - start
    return total / SAMPLE, in_bot / total


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.rust_bench")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()

    subprocess.run(["cargo", "build", "--release", "--quiet", "--manifest-path", str(HERE / "Cargo.toml")], check=True)
    binary = HERE / "target" / "release" / "rust_mm"
    days = kelp_days()
    with tempfile.TemporaryDirectory() as scratch:
        files = [Path(scratch) / f"{day.name}.txt" for day in days]
        for day, path in zip(days, files):
            export(day, path)
        found, _ = rust(binary, files, 1, 1)
        _, rust_one = rust(binary, files, 1, 20)
        _, rust_all = rust(binary, files, args.jobs, 20)

        tasks = [(d, m, a, b) for d in range(len(days)) for m in MODES for a, b in itertools.product(EDGES, EDGES)]
        start = time.perf_counter()
        with ProcessPoolExecutor(args.jobs) as pool:
            ours = dict(pool.map(_python, tasks, chunksize=4))
        python_pool = time.perf_counter() - start

    worst = max(abs(ours[t][0] - found[t][0]) for t in tasks)
    fills = sum(ours[t][1] != found[t][1] for t in tasks)
    print(f"1. parity on {len(tasks)} backtests (3 Kelp days x 2 modes x 64 cells): largest PnL difference {worst:.6f}, "
          f"{fills} with a different fill count")
    best = max(itertools.product(EDGES, EDGES), key=lambda c: sum(ours[(d, MODES[0], *c)][0] for d in range(len(days))))
    print(f"   best cell under all: make_edge {best[0]}, take_edge {best[1]}, "
          f"{sum(ours[(d, MODES[0], *best)][0] for d in range(len(days))):,.0f} over the days")

    (mm, mm_bot), (template, template_bot) = one_core(days, BOT, {}), one_core(days, TEMPLATE, {})
    print(f"2. one core, per backtest of a {len(days[0].ticks):,}-tick Kelp day: mm.py through our engine {mm * 1e3:.1f} ms "
          f"({mm_bot:.0%} in the bot and its format adapter), the template {template * 1e3:.1f} ms ({template_bot:.0%}); Rust: {rust_one}")
    print(f"3. every core ({args.jobs}): {len(tasks)} Python backtests in a process pool in {python_pool:.1f} s; Rust: {rust_all}")
    sys.stdout.flush()
    start = time.perf_counter()
    subprocess.run([sys.executable, "-m", "arena.grid", str(BOT), "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0..7",
                    "--grid", "PARAMS.KELP.take_edge=0..7", "--modes", "all,worse", "--jobs", str(args.jobs)],
                   check=True, capture_output=True)
    print(f"   arena.grid on mm.py, the same grid with its checks: {time.perf_counter() - start:.1f} s")


if __name__ == "__main__":
    main()
