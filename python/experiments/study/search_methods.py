"""Searching a grid without running all of it: which search finds, for a share of the backtests, a cell as good on unseen days?

usage (from the repo root): uv run python -m experiments.study.search_methods --engine rust [--part 1|2] [--seeds N] [--studies Kelp,Osmium,ABM]

The objective every method maximises is a cell's smaller training PnL under `all` and `worse` (the
"both modes" rule of experiments.day.selection_rules), one product alone on its days. A cell's cost is
its backtests: every training day under both modes is one "cell" of budget; halving's partial cells
count by the backtests they ran.

METHODS:
  random    BUDGET cells drawn at random, the best kept (arena.grid --sample)
  halving   successive halving over the (day, mode)s as arena.grid --halving 0.5 runs it, from as
            many random cells as the budget pays for (about twice the budget's backtests per cell)
  coord     (arena.search, as arena.grid --search runs it) coordinate descent from DEFAULTS: each axis in turn (seeded order), every value
            along it, moving to the best; a sweep with no move restarts from a random cell
  tpe       (arena.search) a tree-structured Parzen estimator (Bergstra et al. 2011, Optuna's default): each
            axis's values weighted by the best GAMMA of the cells so far against the rest, 24
            draws a pick, BATCH picks a round
  gp        Bayesian optimisation: a Gaussian process (Matern 5/2, a length scale per axis and
            the noise fitted by marginal likelihood each round) on the axes' indices scaled to
            0-1, on at most GP_POINTS cells, expected improvement over a pool of POOL random cells
            and the neighbours of the five best, BATCH picks a round, each penalised near the ones
            already picked

Part 1 (STUDIES: Kelp on P3, Osmium on P4, ABIDES's ABM; 3,600-6,480 cells of six or seven of the
product's settings) runs each grid whole, on the training days and on test days that repeat none of
them (arena.grid.repeated_days), then runs each method SEEDS times on that table at each of BUDGETS,
looking the cells up. Per method and budget: the pick's training objective as a share of the whole
grid's best, and its gain over the bot as is on the test days under all and worse, beside the whole
grid's own pick (its best training objective) and the oracle (the best cell on the test days). Gains
are over the cell of the template's DEFAULTS, the start for a product first seen on the day (the
committed settings were tuned on some of these days, so they would start ahead).

Part 2 (BIG: Kelp, eleven settings, 933,120 cells, too many to run whole on every day) runs each method
live at a budget of BIG_BUDGET cells, and halving from every cell (arena.grid --halving 0.5 on the
whole grid), each pick then scored on the test days. Results: IDEAS.md, "Searching a big grid".
"""

from __future__ import annotations

import argparse
import itertools
import math
import random
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from operator import mul
from pathlib import Path

from arena import grid, rust
from arena import search as sr
from arena.cli import Setup, add_engine_argument, bot_module
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS

TEMPLATE = Path("python/bots/template.py")
MODES = (TradeMatching.ALL, TradeMatching.WORSE)
METHODS = ("random", "halving", "coord", "tpe", "gp")
BUDGETS = (25, 50, 100, 200, 400)
SEEDS = 20
BATCH = sr.BATCH  # cells a round for tpe and gp
POOL = 600
GP_POINTS = 300  # gp fits on at most this many cells: the best two thirds of them, then the latest (pure Python: O(n^3) a fit)
STUDIES = {  # name: (data, training days, test days, product, {setting: values}); the bot as is must be a cell
    "Kelp": ("p3", ["1"], ["2", "3", "4", "5"], "KELP", {
        "make_edge": [0.5, 1, 1.5, 2, 3], "take_edge": [0, 1, 2, 3], "clear_edge": [0, 1, 2], "skew": [0, 1, 2, 4],
        "smoothing": [0, 0.5, 0.8], "wall_size": [10, 15, 20], "make_inside": [0, 1, 2]}),
    "Osmium": ("p4", ["1"], ["2"], "ASH_COATED_OSMIUM", {
        "make_edge": [0, 0.5, 1, 2, 3], "smoothing": [0, 0.5, 0.7, 0.9, 0.95], "take_edge": [0, 1, 2, 3], "clear_edge": [0, 1, 2],
        "skew": [0, 2, 5, 10], "make_inside": [0, 1, 2]}),
    "ABM": ("data/abides", [f"1-{d}" for d in range(1, 6)], [f"1-{d}" for d in range(6, 11)], "ABM", {
        "lin_rho3": [0, 1, 2, 3, 5], "lin_momentum": [0, 0.25, 0.5, 1], "lin_window": [20, 50, 100, 200], "make_edge": [0.5, 1, 2, 3],
        "take_edge": [0, 1, 2, 3], "skew": [0, 1, 2]}),
}
BIG = ("Kelp", {**STUDIES["Kelp"][4], "imbalance": [0, 0.5, 1], "size_skew": [0, 0.5, 1], "make_size": [None, 10, 20, 30],
                "stop_loss": [None, 600, 1200, 2400]})
BIG_BUDGET = 1000
BIG_SEEDS = 3


# ---------------------------------------------------------------------------- the space


class Space(sr.Space):
    """The axes of one product's settings, a cell an index tuple. `base` is the cell of the template's
    DEFAULTS, where a product first seen on the day starts (its other settings as committed);
    `committed` the bot as committed, if its settings are on the axes."""

    def __init__(self, product: str, axes: dict, bot: Path = TEMPLATE):
        module = bot_module(str(bot), "prosperity")
        current = {**module.DEFAULTS, **module.PARAMS.get(product, {})}
        self.product, self.names, self.values = product, list(axes), list(axes.values())
        missing = [n for n, v in axes.items() if module.DEFAULTS[n] not in v]
        if missing:
            raise ValueError(f"{product}: DEFAULTS isn't a cell, its {', '.join(missing)} not on the axes")
        super().__init__([len(v) for v in self.values], tuple(v.index(module.DEFAULTS[n]) for n, v in axes.items()))
        on = all(current.get(n) in v for n, v in axes.items())
        self.committed = tuple(v.index(current[n]) for n, v in axes.items()) if on else None

    def overrides(self, cell: tuple) -> tuple:
        return tuple(self.values[i][j] for i, j in enumerate(cell))

    def targets(self) -> list[str]:
        return [f"PARAMS.{self.product}.{n}" for n in self.names]

    def point(self, cell: tuple) -> list[float]:
        return [j / (n - 1) if n > 1 else 0.0 for j, n in zip(cell, self.sizes)]

def both_modes(days: int):
    """The objective: a cell's smaller total over the training days under all and under worse (its pieces: the first mode's days, then the next's)."""
    return lambda values: min(sum(values[m * days:(m + 1) * days]) for m in range(len(MODES)))


def Search(space: Space, pieces, count: int, days: int, budget: float) -> sr.Search:
    return sr.Search(space, pieces, count, budget, both_modes(days))


Spent = sr.Spent


# ---------------------------------------------------------------------------- the methods


def search_random(s: sr.Search, rng: random.Random) -> None:
    s.whole(s.space.draw(rng, int(s.limit // s.count)))


def halving_start(total: int, count: int, budget: float, share: float = 0.5) -> int:
    """The most cells halving can start from within `budget` cells' backtests."""
    def cost(n: int) -> int:
        alive, spent = n, 0
        for k in range(count):
            spent += alive
            if k < count - 1 and alive > 1:
                alive = max(1, math.ceil(share * alive))
        return spent
    lo, hi = 1, total
    while lo < hi:
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if cost(mid) <= budget * count else (lo, mid - 1)
    return lo


def search_halving(s: sr.Search, rng: random.Random, share: float = 0.5, cells: list[tuple] | None = None) -> None:
    """arena.grid's --halving: the first mode's days, then the next's, keeping `share` by PnL so far."""
    if cells is None:
        cells = s.space.draw(rng, halving_start(s.space.total, s.count, s.limit / s.count, share))
    so_far = {c: 0.0 for c in cells}
    for k in range(s.count):  # pieces are in grid's order: the first mode's days, then the next mode's
        for c, v in zip(cells, s.piece(cells, k)):
            so_far[c] += v
        if k < s.count - 1 and len(cells) > 1:
            cells = sorted(cells, key=lambda c: -so_far[c])[: max(1, math.ceil(share * len(cells)))]


def _matern(r: float) -> float:
    a = math.sqrt(5.0) * r
    return (1.0 + a + a * a / 3.0) * math.exp(-a)


def _cholesky(a: list[list[float]]) -> list[list[float]] | None:
    n = len(a)
    low = [[0.0] * n for _ in range(n)]
    for i in range(n):
        li = low[i]
        for j in range(i + 1):
            lj = low[j]
            x = a[i][j] - sum(map(mul, li[:j], lj[:j]))
            if i == j:
                if x <= 0:
                    return None
                li[i] = math.sqrt(x)
            else:
                li[j] = x / lj[j]
    return low


def _solve_lower(low: list[list[float]], b: list[float]) -> list[float]:
    x = []
    for i, li in enumerate(low):
        x.append((b[i] - sum(map(mul, li[:i], x))) / li[i])
    return x


def _solve_upper(low: list[list[float]], b: list[float]) -> list[float]:
    n = len(low)
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (b[i] - sum(low[k][i] * x[k] for k in range(i + 1, n))) / low[i][i]
    return x


class GP:
    """A Gaussian process on points in [0, 1]^d: unit amplitude on standardised y, a length scale per
    axis, the noise a share of the variance."""

    def __init__(self, xs: list[list[float]], ys: list[float], scales: list[float], noise: float):
        self.xs, self.scales, self.noise = xs, scales, noise
        self.mean, self.sd = statistics.fmean(ys), statistics.pstdev(ys) or 1.0
        z = [(y - self.mean) / self.sd for y in ys]
        k = [[self.kernel(a, b) + (noise if i == j else 0.0) for j, b in enumerate(xs)] for i, a in enumerate(xs)]
        self.low = _cholesky(k)
        if self.low is None:
            self.fit = -math.inf
            return
        v = _solve_lower(self.low, z)
        self.alpha = _solve_upper(self.low, v)
        self.fit = -0.5 * sum(map(mul, v, v)) - sum(math.log(self.low[i][i]) for i in range(len(xs)))

    def kernel(self, a: list[float], b: list[float]) -> float:
        return _matern(math.sqrt(sum(((x - y) / s) ** 2 for x, y, s in zip(a, b, self.scales))))

    def predict(self, x: list[float]) -> tuple[float, float]:
        k = [self.kernel(x, b) for b in self.xs]
        v = _solve_lower(self.low, k)
        mean = sum(map(mul, k, self.alpha))
        var = max(1.0 + self.noise - sum(map(mul, v, v)), 1e-12)
        return self.mean + self.sd * mean, self.sd * math.sqrt(var)


def fit_gp(xs: list[list[float]], ys: list[float], scales: list[float]) -> GP:
    """One sweep of coordinate ascent on the marginal likelihood: each axis's length scale, then the noise."""
    best = GP(xs, ys, scales, 0.1)
    for i in range(len(scales)):
        for scale in (0.15, 0.4, 1.0, 3.0):
            trial = scales[:i] + [scale] + scales[i + 1:]
            gp = GP(xs, ys, trial, best.noise)
            if gp.fit > best.fit:
                best, scales = gp, trial
    for noise in (0.01, 0.03, 0.3):
        gp = GP(xs, ys, best.scales, noise)
        if gp.fit > best.fit:
            best = gp
    return best


def expected_improvement(mean: float, sd: float, best: float) -> float:
    z = (mean - best) / sd
    return (mean - best) * 0.5 * (1 + math.erf(z / math.sqrt(2))) + sd * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)


def search_gp(s: sr.Search, rng: random.Random) -> None:
    space = s.space
    s.whole(space.draw(rng, BATCH))
    scales = [0.4] * len(space.sizes)
    while True:
        cells = list(s.seen)
        if len(cells) > GP_POINTS:
            best = set(sorted(cells, key=lambda c: -s.seen[c])[: 2 * GP_POINTS // 3])
            cells = [c for c in cells if c in best] + [c for c in cells if c not in best][-(GP_POINTS - len(best)):]
        gp = fit_gp([space.point(c) for c in cells], [s.seen[c] for c in cells], scales)
        scales = gp.scales
        top = sorted(cells, key=lambda c: -s.seen[c])[:5]
        pool = list(dict.fromkeys([n for c in top for n in space.neighbours(c)] + space.draw(rng, POOL)))
        pool = [c for c in pool if c not in s.seen]
        if not pool:
            return
        best = max(s.seen.values())
        scored = []
        for c in pool:
            mean, sd = gp.predict(space.point(c))
            scored.append((expected_improvement(mean, sd, best), c))
        picks: list[tuple] = []
        for _ in range(min(BATCH, len(scored))):
            def penalised(item):  # near a cell already picked this round, less: the GP would expect about the same
                ei, c = item
                for p in picks:
                    ei *= 1.0 - gp.kernel(space.point(c), space.point(p))
                return ei
            ei, cell = max(((penalised(item), item[1]) for item in scored if item[1] not in picks), key=lambda item: item[0])
            picks.append(cell)
        s.whole(picks)


SEARCHES = {"random": search_random, "halving": search_halving, "coord": sr.coord, "tpe": sr.tpe, "gp": search_gp}


def run_method(method: str, space: Space, pieces, count: int, days: int, budgets: tuple, seed: int) -> dict[float, tuple | None]:
    """The method's pick at each budget: one run to the largest, read at the smaller ones, except
    halving, which starts from a different number of cells at each."""
    out = {}
    if method == "halving":
        for budget in budgets:
            s = Search(space, pieces, count, days, budget)
            try:
                search_halving(s, random.Random(seed))
            except Spent:
                pass
            out[budget] = s.best()
        return out
    s = Search(space, pieces, count, days, max(budgets))
    try:
        SEARCHES[method](s, random.Random(seed))
    except Spent:
        pass
    completed = list(s.seen)
    for budget in budgets:  # whole cells only: the first `budget` cells completed
        out[budget] = s.best(int(budget)) if completed else None
    return out


# ---------------------------------------------------------------------------- the backtests


def study_days(data: str, train: list[str], test: list[str], product: str) -> tuple[list, list]:
    """The training days and the test days that repeat none of them (repeats among either counted once)."""
    fmt = FORMATS["prosperity"]
    directory = fmt.resolve_data_dir(data)
    train_days = [d for d in fmt.load_days(directory, train) if product in d.products]
    test_days = [d for d in fmt.load_days(directory, test) if product in d.products]
    training = {d.name for d in train_days}
    drop = set()
    for names, products in grid.repeated_days(train_days + test_days):
        if product in products:
            first = next((n for n in names if n in training), names[0])
            drop |= set(names) - {first}
    return [d for d in train_days if d.name not in drop], [d for d in test_days if d.name not in drop]


class Backtests:
    """Each cell's PnL of the product alone, per day and mode, on the training days (pieces 0..) and
    the test days, through arena.grid's runner (Rust's batch with --engine rust)."""

    def __init__(self, space: Space, train: list, test: list, engine: str, jobs: int):
        self.space, self.train, self.test = space, train, test
        days = train + test
        self.setup = Setup(FORMATS["prosperity"], days, EngineConfig(), {}, engine=engine)
        axes = [grid.Axis(t, v) for t, v in zip(space.targets(), space.values)]
        self.runner = grid._Runner(self.setup, TEMPLATE, axes, list(MODES), jobs if engine == "rust" else 1, "prosperity", "", [],
                                   [space.product])
        self.runs = 0

    def __enter__(self):
        self.runner.__enter__()
        return self

    def __exit__(self, *exc):
        self.runner.__exit__(*exc)

    def _run(self, wanted: list[tuple[tuple | None, int, TradeMatching]]) -> dict:
        """(cell or None for the bot as is, day index into train + test, mode) -> PnL."""
        tasks = [((cell, d, m), () if cell is None else self.space.overrides(cell), d, m, True, None) for cell, d, m in wanted]
        self.runs += len(tasks)
        found = self.runner.run(tasks)
        return {key: piece.pnl for key, piece in found.items()}

    def pieces(self, wanted: list[tuple[tuple, int]]) -> dict:
        """Search's pieces: (cell, k), k = mode * training days + day."""
        n = len(self.train)
        found = self._run([(cell, k % n, MODES[k // n]) for cell, k in wanted])
        return {(cell, k): found[(cell, k % n, MODES[k // n])] for cell, k in wanted}

    def test_gain(self, cells: list[tuple]) -> dict[tuple, tuple[float, float]]:
        """Each cell's gain over DEFAULTS' cell on the test days, under all and worse."""
        n, base = len(self.train), self.space.base
        wanted = [(c, n + d, m) for c in dict.fromkeys([base, *cells]) for d in range(len(self.test)) for m in MODES]
        found = self._run(wanted)
        total = lambda c, m: sum(found[(c, n + d, m)] for d in range(len(self.test)))
        return {c: tuple(total(c, m) - total(base, m) for m in MODES) for c in cells}


# ---------------------------------------------------------------------------- part 1: a whole grid, searched by lookup


_TABLE: dict = {}


def _init(table: dict) -> None:
    _TABLE.update(table)


def _lookup(wanted: list[tuple[tuple, int]]) -> dict:
    return {w: _TABLE["pieces"][w[0]][w[1]] for w in wanted}


def _one(task: tuple[str, int]) -> tuple[str, int, dict]:
    method, seed = task
    t = _TABLE
    return method, seed, run_method(method, t["space"], _lookup, t["count"], t["days"], BUDGETS, seed)


def part1(names: list[str], engine: str, jobs: int, seeds: int) -> None:
    for name in names:
        data, train_specs, test_specs, product, axes = STUDIES[name]
        space = Space(product, axes)
        train, test = study_days(data, train_specs, test_specs, product)
        start = time.perf_counter()
        cells = list(itertools.product(*(range(n) for n in space.sizes)))
        with Backtests(space, train, test, engine, jobs) as b:
            count = len(train) * len(MODES)
            found = b.pieces([(c, k) for c in cells for k in range(count)])
            pieces = {c: [found[(c, k)] for k in range(count)] for c in cells}
            gains = b.test_gain(cells)
            runs = b.runs
        elapsed = time.perf_counter() - start
        objective = {c: min(sum(p[m * len(train):(m + 1) * len(train)]) for m in range(len(MODES))) for c, p in pieces.items()}
        top = max(objective.values())
        grid_pick = max(cells, key=lambda c: objective[c])
        oracle = max(cells, key=lambda c: min(gains[c]))
        table = {"space": space, "pieces": pieces, "count": count, "days": len(train)}
        with ProcessPoolExecutor(jobs, initializer=_init, initargs=(table,)) as pool:
            results = list(pool.map(_one, [(m, seed) for m in METHODS for seed in range(seeds)]))

        print(f"## {name}: {product}, {space.total:,} cells ({' × '.join(f'{n} {k}' for n, k in zip(space.names, space.sizes))}); "
              f"trained on {', '.join(d.name for d in train)}, tested on {', '.join(d.name for d in test)}")
        print(f"the whole grid: {runs:,} backtests in {elapsed:.0f} s ({runs / elapsed:,.0f} a second, {engine}); its best training objective "
              f"{top:,.0f} (DEFAULTS {objective[space.base]:,.0f}" + (f", as committed {objective[space.committed]:,.0f}" if space.committed else "") + ")\n")
        print(f"Each cell: the pick's training objective as a share of the grid's best; its test gain over DEFAULTS' cell, all / worse; "
              f"the seeds (of {seeds}) whose pick lost on the test days under either. Means over the seeds.\n")
        print(f"| method | {' | '.join(f'{b} cells ({b / space.total:.1%})' for b in BUDGETS)} |")
        print(f"|---|{'---|' * len(BUDGETS)}")
        for method in METHODS:
            row = [f"| {method}"]
            for budget in BUDGETS:
                picks = [r[2][budget] for r in results if r[0] == method]
                share = statistics.fmean(objective[p] / top for p in picks) if top > 0 else float("nan")
                g_all = statistics.fmean(gains[p][0] for p in picks)
                g_worse = statistics.fmean(gains[p][1] for p in picks)
                lost = sum(min(gains[p]) < 0 for p in picks)
                row.append(f"{share:.1%}; {g_all:+,.0f} / {g_worse:+,.0f}; {lost}")
            print(" | ".join(row) + " |")
        cell = lambda c: ", ".join(f"{n} {v}" for n, v in zip(space.names, space.overrides(c)))
        ranks = sorted(cells, key=lambda c: -min(gains[c]))
        print(f"\n- the whole grid ({space.total:,} cells): {gains[grid_pick][0]:+,.0f} / {gains[grid_pick][1]:+,.0f}, "
              f"{ranks.index(grid_pick) + 1:,} of {len(cells):,} on the test days: {cell(grid_pick)}")
        print(f"- the oracle (the best on the test days): {gains[oracle][0]:+,.0f} / {gains[oracle][1]:+,.0f}, its training objective "
              f"{objective[oracle] / top:.1%} of the best: {cell(oracle)}")
        print(f"- DEFAULTS (where coord starts, gain 0): {ranks.index(space.base) + 1:,} on the test days: {cell(space.base)}")
        if space.committed:
            print(f"- as committed (tuned on Prosperity days, these among them): {gains[space.committed][0]:+,.0f} / {gains[space.committed][1]:+,.0f}, "
                  f"{ranks.index(space.committed) + 1:,} on the test days: {cell(space.committed)}")
        print()


# ---------------------------------------------------------------------------- part 2: a grid too big to run whole


def part2(engine: str, jobs: int, seeds: int) -> None:
    name, axes = BIG
    data, train_specs, test_specs, product, _ = STUDIES[name]
    space = Space(product, axes)
    train, test = study_days(data, train_specs, test_specs, product)
    count = len(train) * len(MODES)
    print(f"## {name}, {len(space.names)} settings, {space.total:,} cells; trained on {', '.join(d.name for d in train)}, "
          f"tested on {', '.join(d.name for d in test)}; {BIG_BUDGET:,} cells a search ({BIG_BUDGET / space.total:.2%})\n")
    print("| method | seed | backtests | seconds | training objective | test gain all / worse | pick |")
    print("|---|---|---|---|---|---|---|")
    cell = lambda c: ", ".join(f"{n} {v}" for n, v in zip(space.names, space.overrides(c)))
    with Backtests(space, train, test, engine, jobs) as b:
        base = Search(space, b.pieces, count, len(train), 1)
        base.whole([space.base])
        print(f"| DEFAULTS (gain 0) | | | | {base.seen[space.base]:,.0f} | | {cell(space.base)} |")
        runs = []
        for method in ("random", "coord", "tpe", "gp"):
            for seed in range(seeds):
                before, start = b.runs, time.perf_counter()
                pick = run_method(method, space, b.pieces, count, len(train), (BIG_BUDGET,), seed)[BIG_BUDGET]
                runs.append((method, seed, b.runs - before, time.perf_counter() - start, pick))
        before, start = b.runs, time.perf_counter()
        s = Search(space, b.pieces, count, len(train), space.total)
        search_halving(s, random.Random(0), cells=list(itertools.product(*(range(n) for n in space.sizes))))
        runs.append((f"halving, every cell", 0, b.runs - before, time.perf_counter() - start, s.best()))
        objectives = {}
        for method, seed, n, seconds, pick in runs:
            if pick not in objectives:
                probe = Search(space, b.pieces, count, len(train), 1)
                probe.whole([pick])
                objectives[pick] = probe.seen[pick]
        gains = b.test_gain(list({r[4] for r in runs}))
        for method, seed, n, seconds, pick in runs:
            print(f"| {method} | {seed} | {n:,} | {seconds:.0f} | {objectives[pick]:,.0f} | {gains[pick][0]:+,.0f} / {gains[pick][1]:+,.0f} | {cell(pick)} |")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.study.search_methods")
    parser.add_argument("--part", type=int, choices=(1, 2))
    parser.add_argument("--studies", default=",".join(STUDIES), help="part 1's studies (default: all)")
    parser.add_argument("--seeds", type=int, default=None, help=f"runs of each method (default: {SEEDS} in part 1, {BIG_SEEDS} in part 2)")
    parser.add_argument("--jobs", type=int, default=None)
    add_engine_argument(parser)
    args = parser.parse_args(argv)
    if args.engine == "rust":
        rust.prepare("prosperity", [TEMPLATE], args.allow_stale)
    import os

    jobs = args.jobs or os.cpu_count() or 1
    if args.part in (None, 1):
        part1([n.strip() for n in args.studies.split(",")], args.engine, jobs, args.seeds or SEEDS)
    if args.part in (None, 2):
        part2(args.engine, jobs, args.seeds or BIG_SEEDS)


if __name__ == "__main__":
    main()
