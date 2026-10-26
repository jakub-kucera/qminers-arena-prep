"""How often do arena.grid's SPA, StepM and pick name a cell when no cell has an edge?

usage (from the repo root): uv run python -m experiments.snooping_null_rates [--trials N] [--engine rust]

From the second audit (2026-10-26, A4; its script null_stats.py, adapted): each trial draws CELLS
cells' gains over the bot as is per block (BLOCKS blocks, as a grid's 100-tick blocks over three
days), all with mean zero: a common factor (cross-cell correlation 0.7) plus each cell's own part,
each an AR(1) with coefficient phi and Student-t innovations (or Gaussian). A valid 5% test names a
cell in about 5% of trials or fewer. Each row reports, over TRIALS trials:

  SPA         SPA's consistent p under 5%
  StepM       StepM names a cell
  + worse     the pick: StepM's best cell that also gains under a second mode, its draws correlated
              with the first's at the row's rho (the `worse` gate of --modes all,worse)
  + holdout   the pick of arena.grid --gate first --holdout 25%: SPA and StepM on the first 75% of the
              blocks, StepM's best cell there kept only if it also gains on the last 25%

The tests are the repo's own (arena.stats.snooping, or its Rust twin with --engine rust, the same to
the bit). Results: IDEAS.md, "Bootstrap tests of the best cell".
"""

from __future__ import annotations

import argparse
import random
import statistics
import time

from arena import rust, stats
from arena.cli import add_engine_argument
from arena.grid import BOOTSTRAP, SPA_Q

CELLS, BLOCKS, CROSS_CELL = 24, 300, 0.7
HOLDOUT = 0.25
ROWS = (  # (label, phi, Student-t degrees of freedom or None for Gaussian, rho between the two modes)
    ("t(4), phi 0, modes 0.8", 0.0, 4, 0.8),
    ("t(4), phi 0.3, modes 0.8", 0.3, 4, 0.8),
    ("t(4), phi 0.8, modes 0.8", 0.8, 4, 0.8),
    ("Gaussian, phi 0, modes 0.8", 0.0, None, 0.8),
    ("Gaussian, phi 0.3, modes 0.8", 0.3, None, 0.8),
    ("t(4), phi 0.3, modes independent", 0.3, 4, 0.0),
)


def draw(rng: random.Random, phi: float, df: int | None) -> list[list[float]]:
    """CELLS columns of BLOCKS zero-mean gains: a common factor and each cell's own, each AR(1)."""

    def series() -> list[float]:
        x, out = 0.0, []
        for _ in range(BLOCKS):
            e = rng.gauss(0, 1)
            if df is not None:
                e /= rng.gammavariate(df / 2, 2 / df) ** 0.5
            x = phi * x + e
            out.append(x)
        return out

    common = series()
    return [[CROSS_CELL ** 0.5 * c + (1 - CROSS_CELL) ** 0.5 * o for c, o in zip(common, series())] for _ in range(CELLS)]


def row(trials: int, phi: float, df: int | None, rho: float, snooping, seed: int = 1) -> dict[str, float]:
    rng = random.Random(seed)
    counts = {"SPA": 0, "StepM": 0, "+ worse": 0, "+ holdout": 0}
    cut = BLOCKS - round(HOLDOUT * BLOCKS)
    for _ in range(trials):
        first = draw(rng, phi, df)
        noise = draw(rng, phi, df)
        second = [[rho * a + (1 - rho * rho) ** 0.5 * b for a, b in zip(ca, cb)] for ca, cb in zip(first, noise)]
        p, winners = snooping(first, SPA_Q, BOOTSTRAP)
        counts["SPA"] += p["c"] < stats.ALPHA
        counts["StepM"] += bool(winners)
        if winners:
            best = max(winners, key=lambda k: statistics.fmean(first[k]))
            counts["+ worse"] += sum(second[best]) > 0
        _, kept = snooping([c[:cut] for c in first], SPA_Q, BOOTSTRAP)
        if kept:
            best = max(kept, key=lambda k: statistics.fmean(first[k][:cut]))
            counts["+ holdout"] += sum(first[best][cut:]) > 0
    return {name: n / trials for name, n in counts.items()}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.snooping_null_rates")
    parser.add_argument("--trials", type=int, default=300, help="trials per row (default: 300; the standard error of a 5%% rate is then 1.3 points)")
    add_engine_argument(parser, "run the bootstrap tests in rust/ (the same results; Python takes far longer)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.require(args.allow_stale)
    snooping = rust.snooping if args.engine == "rust" else stats.snooping
    print(f"{CELLS} cells, {BLOCKS} blocks, cross-cell correlation {CROSS_CELL}, {args.trials} trials a row, nominal 5%:\n")
    names = ["SPA", "StepM", "+ worse", "+ holdout"]
    print("| Null | " + " | ".join(names) + " |")
    print("|---" * (len(names) + 1) + "|")
    for label, phi, df, rho in ROWS:
        start = time.perf_counter()
        rates = row(args.trials, phi, df, rho, snooping)
        print(f"| {label} | " + " | ".join(f"{rates[n]:.1%}" for n in names) + f" |  ({time.perf_counter() - start:.0f} s)")


if __name__ == "__main__":
    main()
