"""Does the best grid cell beat the bot as is? Hansen's SPA test and Romano and Wolf's StepM next to
arena.grid's deflated Sharpe ratio, on the same grids.

usage (from the repo root): uv run python -m experiments.snooping_tests [--jobs N] [--boot B] [--engine rust]

Hansen (literature_md/superior-predictive-ability/) argues that White's Reality Check, which takes
its critical value as if every alternative were exactly as good as the benchmark, loses power when
poor alternatives are added, and fixes it by studentizing each cell and by recentring the bootstrap
only on cells that aren't clearly worse. arena.grid's DSR takes its threshold from the spread of
the cells' Sharpe ratios, so poor cells raise it too. Each cell's gain over the bot as is, per block
of TICKS_PER_BLOCK ticks (days concatenated), goes through:

  DSR       as arena.grid computes it (its 16 blocks over all the days), over every distinct cell and, as an
            illustration of its sensitivity only (the subset is chosen on the same data), over the
            nine cells with the most PnL
  SPA       Hansen's p-value that no cell beats the bot as is, with the null recentred three ways:
            l (liberal), c (consistent, the one to use) and u (every cell as good as the bot: the
            studentized Reality Check). The stationary bootstrap, mean block of 1/q blocks
  StepM     Romano and Wolf's step-down test at 5%: how many cells beat the bot as is, each with
            the familywise error controlled (each resample studentized by its own omega, as SPA's
            too: arena.stats' default since 2026-10-26; before, by the original's in every one)
The tests are arena.grid's (spa, stepm), which every grid summary now prints at one block length.

  PBO       arena.grid's CSCV over its 16 blocks. On the null grids it should average about 50%;
            well below would mean blocks next to each other leak (the reason for purging and an
            embargo in López de Prado's cross-validation)
  BHY       Harvey and Liu's false-discovery procedure at 5% on each cell's one-sided p-value
            (normal, studentized by Hansen's omega): how many cells it calls real

GRIDS holds two real grids and a null control: the template at fill ratio 0.8, each cell a
different liquidity seed and the bot as is another, so no cell has an edge and every test should
come out clean (SPA p spread over 0-1, no StepM rejections). Results go into IDEAS.md ("Bootstrap
tests of the best cell") and references/wiki/concepts/validation-and-overfitting.md.
"""

from __future__ import annotations

import argparse
import statistics
from concurrent.futures import ProcessPoolExecutor

from arena import grid, report, rust
from arena.cli import add_engine_argument, backtest, backtest_days
from arena.engine import EngineConfig
from arena.formats import prosperity

TEMPLATE = "python/bots/template.py"
TICKS_PER_BLOCK = 100
QS = (0.2, 0.1, 0.04)  # stationary bootstrap: mean blocks of 5, 10 and 25 (500 to 2,500 ticks)
NULL_CELLS, NULL_RUNS = 32, 10


def _grids() -> dict:
    """name: (data, day specs, the bot as is (overrides, config), cells [(label, overrides, config)])."""
    out = {
        "Kelp make_edge 0..7 × take_edge 0..7 (P3 r1)": (
            "p3", ["1"], ({}, EngineConfig()),
            [(f"{a},{b}", {"PARAMS.KELP.make_edge": a, "PARAMS.KELP.take_edge": b}, EngineConfig()) for a in range(8) for b in range(8)],
        ),
        "Osmium smoothing (P4 r1-2)": (
            "p4", ["1", "2"], ({}, EngineConfig()),
            [(str(s), {"PARAMS.ASH_COATED_OSMIUM.smoothing": s}, EngineConfig()) for s in (0, 0.5, 0.7, 0.95, 0.98, 0.99)],
        ),
    }
    for r in range(NULL_RUNS):
        out[f"null {r + 1}: liquidity seeds (P3 r1, fill ratio 0.8)"] = (
            "p3", ["1"], ({}, EngineConfig(fill_ratio=0.8, seed=10_000 + r)),
            [(f"seed {s}", {}, EngineConfig(fill_ratio=0.8, seed=s)) for s in range(NULL_CELLS * r, NULL_CELLS * (r + 1))],
        )
    return out


GRIDS = _grids()
_DAYS: dict = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def run(task: tuple[str, int]) -> tuple[tuple[str, int], list[float], list[float], float]:
    """One cell (-1: the bot as is) on every day: PnL per fine block, per grid block, and in all."""
    name, cell = task
    data, specs, base, cells = GRIDS[name]
    overrides, config = base if cell < 0 else cells[cell][1:]
    key = (data, tuple(specs))
    if key not in _DAYS:
        _DAYS[key] = backtest_days(data, specs, ENGINE[0])
    days = _DAYS[key]
    fine, coarse, total = [], [], 0.0
    for day in days:
        (result,) = backtest(day, [("you", TEMPLATE, overrides, False)], config, ENGINE[0], fields=("pnl",))
        series = report.total_pnl(result) or [0.0] * len(result.timestamps)
        fine += grid.block_pnl(series, len(series) // TICKS_PER_BLOCK)
        coarse += grid.block_pnl(series, grid.blocks_per_day(len(days)))
        total += series[-1]
    return task, fine, coarse, total


# ---------------------------------------------------------------------------- the tests


def dsr(base: list[float], cells: list[list[float]], best: list[float]) -> float | None:
    """arena.grid's DSR of the best cell's gain over the bot as is, against `cells` as the trials."""
    gains = [[x - b for x, b in zip(c, base)] for c in cells]
    mine = [x - b for x, b in zip(best, base)]
    sharpes = [statistics.fmean(g) / statistics.stdev(g) for g in gains if statistics.stdev(g) > 0]
    if len(sharpes) < 2 or statistics.stdev(mine) == 0:
        return None
    mean, sd = statistics.fmean(mine), statistics.pstdev(mine)
    skew = statistics.fmean(((x - mean) / sd) ** 3 for x in mine)
    kurtosis = statistics.fmean(((x - mean) / sd) ** 4 for x in mine)
    sharpe = statistics.fmean(mine) / statistics.stdev(mine)
    sharpe0 = grid.expected_max_sharpe(statistics.variance(sharpes), grid.independent_trials(gains))
    return grid.deflated_sharpe(sharpe, sharpe0, len(mine), skew, kurtosis)


def bhy(pvalues: list[float], level: float = 0.05) -> int:
    """How many hypotheses Benjamini, Hochberg and Yekutieli's adjustment rejects at `level`
    (Harvey and Liu, p. 5): from the largest p, p_(i) = min(p_(i+1), M c(M) / i p_(i))."""
    m = len(pvalues)
    c = sum(1 / j for j in range(1, m + 1))
    adjusted, running = [0.0] * m, 1.0
    for i, p in sorted(enumerate(sorted(pvalues), 1), reverse=True):
        running = min(running, m * c / i * p)
        adjusted[i - 1] = running
    return sum(a < level for a in adjusted)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.snooping_tests")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    parser.add_argument("--boot", type=int, default=2000, help="bootstrap resamples (default: 2000)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.require(args.allow_stale)
    tasks = [(name, cell) for name, (_, _, _, cells) in GRIDS.items() for cell in range(-1, len(cells))]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        results = {task: rest for task, *rest in pool.map(run, tasks, chunksize=1)}

    def fmt(x):
        return "-" if x is None else f"{x:.2f}"

    print(f"Gains over the bot as is per block of {TICKS_PER_BLOCK} ticks; SPA p-values l / c / u; StepM at {grid.ALPHA:.0%}; "
          f"{args.boot} bootstrap resamples; q = {' / '.join(map(str, QS))} (mean blocks of {' / '.join(str(round(1 / q)) for q in QS)}).\n")
    print("| Grid | Cells | Blocks | Best cell (gain) | PBO | DSR, all cells | DSR, top 9 only | SPA p (l / c / u) per q | StepM: cells that beat the bot as is | BHY |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name, (_, _, _, cells) in GRIDS.items():
        base_fine, base_coarse, base_total = results[(name, -1)]
        fine = [results[(name, k)][0] for k in range(len(cells))]
        coarse = [results[(name, k)][1] for k in range(len(cells))]
        totals = [results[(name, k)][2] for k in range(len(cells))]
        order = sorted(range(len(cells)), key=lambda k: -totals[k])
        best = order[0]
        gains = [[x - b for x, b in zip(c, base_fine)] for c in fine]
        distinct = list({tuple(round(x, 6) for x in g): g for g in gains if any(g)}.values())
        def unique(ks):  # identical cells counted once, as arena.grid does
            return list({tuple(round(x, 6) for x in coarse[k]): coarse[k] for k in ks}.values())

        dsr_all = dsr(base_coarse, unique(range(len(cells))), coarse[best])
        dsr_top = dsr(base_coarse, unique(order[:9]), coarse[best])
        stat = rust if args.engine == "rust" else grid  # the bootstraps in rust/src/arena/stats.rs, the same to the bit
        spas = [stat.spa(distinct, q, args.boot) for q in QS]
        spa_text = "; ".join(f"{s['l']:.2f} / {s['c']:.2f} / {s['u']:.2f}" for s in spas)
        steps = stat.stepm(distinct, QS[1], args.boot)
        n, normal = len(distinct[0]), statistics.NormalDist()
        pvalues = [1 - normal.cdf(n**0.5 * statistics.fmean(g) / w) for g, w in zip(distinct, (rust.scales if args.engine == "rust" else grid._scales)(distinct, QS[1]))]
        columns = unique(range(len(cells)))
        pbo = f"{stat.cscv(columns).pbo:.0%}" if len(columns) > 1 else "-"
        winners = ", ".join(next(cells[k][0] for k in range(len(cells)) if gains[k] == distinct[j]) for j in steps) or "none"
        print(f"| {name} | {len(cells)} ({len(distinct)} distinct) | {len(base_fine)} | {cells[best][0]} ({totals[best] - base_total:+,.0f}) "
              f"| {pbo} | {fmt(dsr_all)} | {fmt(dsr_top)} | {spa_text} | {len(steps)}: {winners} | {bhy(pvalues)} |")


if __name__ == "__main__":
    main()
