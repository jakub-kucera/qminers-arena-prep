"""Does the best grid cell beat the bot as is? Hansen's SPA test and Romano and Wolf's StepM next to
arena.grid's deflated Sharpe ratio, on the same grids.

usage (from the repo root): uv run python -m experiments.snooping_tests [--jobs N] [--boot B]

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
            the familywise error controlled (studentized with Hansen's fixed omega, not a
            bootstrap-studentized one: our simplification)

GRIDS holds two real grids and a null control: the template at fill ratio 0.8, each cell a
different liquidity seed and the bot as is another, so no cell has an edge and every test should
come out clean (SPA p spread over 0-1, no StepM rejections). Results go into IDEAS.md ("Bootstrap
tests of the best cell") and references/wiki/concepts/validation-and-overfitting.md.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
from concurrent.futures import ProcessPoolExecutor
from operator import itemgetter

from arena import grid, report
from arena.engine import EngineConfig, run_day
from arena.formats import prosperity

TEMPLATE = "bots/template.py"
TICKS_PER_BLOCK = 100
QS = (0.2, 0.1, 0.04)  # stationary bootstrap: mean blocks of 5, 10 and 25 (500 to 2,500 ticks)
ALPHA = 0.05
NULL_CELLS, NULL_RUNS = 32, 5


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


def run(task: tuple[str, int]) -> tuple[tuple[str, int], list[float], list[float], float]:
    """One cell (-1: the bot as is) on every day: PnL per fine block, per grid block, and in all."""
    name, cell = task
    data, specs, base, cells = GRIDS[name]
    overrides, config = base if cell < 0 else cells[cell][1:]
    key = (data, tuple(specs))
    if key not in _DAYS:
        _DAYS[key] = prosperity.load_days(prosperity.resolve_data_dir(data), specs)
    days = _DAYS[key]
    fine, coarse, total = [], [], 0.0
    for day in days:
        result = run_day(day, prosperity.load_bot(TEMPLATE, overrides, strict=False), config)
        series = report.total_pnl(result) or [0.0] * len(day.ticks)
        fine += grid.block_pnl(series, len(series) // TICKS_PER_BLOCK)
        coarse += grid.block_pnl(series, grid.blocks_per_day(len(days)))
        total += series[-1]
    return task, fine, coarse, total


# ---------------------------------------------------------------------------- the tests


def omega2(d: list[float], q: float) -> float:
    """Hansen's variance of sqrt(n) times the mean under the stationary bootstrap (p. 7-8):
    gamma_0 + 2 sum_i kappa(n, i) gamma_i, kappa(n, i) = (n-i)/n (1-q)^i + i/n (1-q)^(n-i)."""
    n, mean = len(d), statistics.fmean(d)
    c = [x - mean for x in d]
    total = sum(x * x for x in c) / n
    for i in range(1, n):
        kappa = (n - i) / n * (1 - q) ** i + i / n * (1 - q) ** (n - i)
        if kappa < 1e-12:
            continue
        total += 2 * kappa * sum(c[j] * c[j + i] for j in range(n - i)) / n
    return total


def bootstrap_means(d: list[list[float]], q: float, boot: int, seed: int) -> list[list[float]]:
    """Each resample's mean of every column, Politis and Romano's stationary bootstrap (p. 7)."""
    n, rng, out = len(d[0]), random.Random(seed), []
    for _ in range(boot):
        idx, t = [], rng.randrange(n)
        for _ in range(n):
            idx.append(t)
            t = rng.randrange(n) if rng.random() < q else (t + 1) % n
        pick = itemgetter(*idx)
        out.append([sum(pick(column)) / n for column in d])
    return out


def spa(d: list[list[float]], q: float, boot: int, seed: int = 0) -> dict[str, float]:
    """Hansen's SPA p-values for H0: no column has a positive mean, with the bootstrap recentred
    at mu_l = min(mean, 0), mu_c (only the clearly negative means kept) and mu_u = 0 (p. 7-8)."""
    n = len(d[0])
    means = [statistics.fmean(c) for c in d]
    omegas = [math.sqrt(max(omega2(c, q), 1e-12)) for c in d]
    t = max(0.0, max(math.sqrt(n) * m / w for m, w in zip(means, omegas)))
    loglog = math.sqrt(2 * math.log(math.log(n)))
    g = {
        "l": [max(0.0, m) for m in means],
        "c": [m if m >= -w / math.sqrt(n) * loglog else 0.0 for m, w in zip(means, omegas)],
        "u": means,
    }
    draws = bootstrap_means(d, q, boot, seed)
    out = {}
    for name, shift in g.items():
        above = sum(
            max(0.0, max(math.sqrt(n) * (x - s) / w for x, s, w in zip(draw, shift, omegas))) > t for draw in draws
        )
        out[name] = above / boot
    return out


def stepm(d: list[list[float]], q: float, boot: int, alpha: float = ALPHA, seed: int = 1) -> list[int]:
    """Romano and Wolf's studentized step-down (Algorithms 3.1-3.2, p. 9-12): the columns whose
    mean is significantly positive, the familywise error held at alpha."""
    n = len(d[0])
    means = [statistics.fmean(c) for c in d]
    omegas = [math.sqrt(max(omega2(c, q), 1e-12)) for c in d]
    z = [math.sqrt(n) * m / w for m, w in zip(means, omegas)]
    draws = [[math.sqrt(n) * (x - m) / w for x, m, w in zip(draw, means, omegas)] for draw in bootstrap_means(d, q, boot, seed)]
    active, rejected = set(range(len(d))), []
    while active:
        maxima = sorted(max(draw[k] for k in active) for draw in draws)
        c = maxima[min(len(maxima) - 1, math.ceil((1 - alpha) * len(maxima)) - 1)]
        newly = [k for k in active if z[k] > c]
        if not newly:
            break
        rejected += newly
        active -= set(newly)
    return sorted(rejected)


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


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.snooping_tests")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    parser.add_argument("--boot", type=int, default=2000, help="bootstrap resamples (default: 2000)")
    args = parser.parse_args()
    tasks = [(name, cell) for name, (_, _, _, cells) in GRIDS.items() for cell in range(-1, len(cells))]
    with ProcessPoolExecutor(args.jobs) as pool:
        results = {task: rest for task, *rest in pool.map(run, tasks, chunksize=1)}

    def fmt(x):
        return "-" if x is None else f"{x:.2f}"

    print(f"Gains over the bot as is per block of {TICKS_PER_BLOCK} ticks; SPA p-values l / c / u; StepM at {ALPHA:.0%}; "
          f"{args.boot} bootstrap resamples; q = {' / '.join(map(str, QS))} (mean blocks of {' / '.join(str(round(1 / q)) for q in QS)}).\n")
    print("| Grid | Cells | Blocks | Best cell (gain) | DSR, all cells | DSR, top 9 only | SPA p (l / c / u) per q | StepM: cells that beat the bot as is |")
    print("|---|---|---|---|---|---|---|---|")
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
        spas = [spa(distinct, q, args.boot) for q in QS]
        spa_text = "; ".join(f"{s['l']:.2f} / {s['c']:.2f} / {s['u']:.2f}" for s in spas)
        steps = stepm(distinct, QS[1], args.boot)
        winners = ", ".join(next(cells[k][0] for k in range(len(cells)) if gains[k] == distinct[j]) for j in steps) or "none"
        print(f"| {name} | {len(cells)} ({len(distinct)} distinct) | {len(base_fine)} | {cells[best][0]} ({totals[best] - base_total:+,.0f}) "
              f"| {fmt(dsr_all)} | {fmt(dsr_top)} | {spa_text} | {len(steps)}: {winners} |")


if __name__ == "__main__":
    main()
