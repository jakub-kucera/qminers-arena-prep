"""Grid search over bot parameters, with robustness checks.

    uv run python -m arena.grid bots/template.py 1 \\
        --grid PARAMS.KELP.make_edge=1,2,3 --grid PARAMS.KELP.take_edge=0..2 --modes all,worse

Every combination of --grid values is backtested on every given day, under each trade-matching
mode in --modes, in parallel. The combination with the best PnL is usually overfit, so each
combination also gets:

  min day   its worst single day: a good setting should do well on every day, not just one
  nbhd      the mean PnL of it and its grid neighbours (one step along any axis), leaving out
            neighbours that failed. Prefer a plateau, where nearby values do about as well, to a
            lone spike.
  <mode>    PnL under each extra --modes entry, e.g. `worse` fill matching. A gain that only
            exists with optimistic fills is probably a backtest artefact.

The summary names the best combination by each measure and says whether they agree. With two or
more days it also holds out each day in turn: the combination with the best PnL on the other days
is scored on the held-out day. The total of those scores is what choosing by PnL earns on days it
didn't see, and its gap to the best combination's PnL is the selection bias of a grid this size.
It only covers the gridded values: a setting the bot fits to the data itself (say a level taken
from the days' mean) needs its own held-out test. Days whose data repeats are flagged, since
holding one out still trains on its copy.

Last, how much the choice can be trusted, on the first mode's PnL cut into blocks of ticks within
days (BLOCKS in all, as evenly as the days allow), with cells whose block PnL is identical counted
once:
  PBO       Bailey et al.'s probability of backtest overfitting by CSCV: over halvings of the blocks,
            how often the best cell on one half ranks at or below the median on the other. Near 50%
            the grid's pick carries no information. The same halvings give the pick's mean relative
            rank out of sample (1 is the top, 0.5 the median) and how often it loses money there.
            (Not the paper's slope of out-of-sample on in-sample performance: with PnL summed over
            blocks, a pick that stays the same cell gives -1 by construction.)
  DSR       Bailey and Lopez de Prado's deflated Sharpe ratio of the best cell's gain over the bot as
            is (--set only), block by block: the chance that the gain's per-block Sharpe ratio beats
            the best of N^ cells with no gain, N^ the cells' count discounted by the average
            correlation of their gains. On the cells' own PnL it would only say that the bot makes
            money. Below 0.95 the summary warns.
  SPA       Hansen's test that no cell beats the bot as is, on each cell's gain per block of
            FINE_TICKS ticks, with Politis and Romano's stationary bootstrap. Its p-value is the
            consistent one (c), between the liberal (l) and the studentized Reality Check (u). Unlike
            the DSR it discounts cells that are clearly worse, so a wide grid's poor corners don't
            hide a real gain.
  StepM     Romano and Wolf's step-down test on the same resamples: every cell that beats the bot as
            is, with the chance of naming even one false cell held at ALPHA.
  pick      StepM's best cell that also beats the bot as is under every other --modes entry, else
            the bot as is. Of ten ways of choosing tried on unseen days, the only one that never lost
            money, under either fill mode (experiments/selection_rules.py).
Halvings and bootstrap blocks mix blocks of the same days, so a day-level change is invisible to
all of them: the held-out days are the check for that, and a cell they accept still has to hold
under the other --modes (references/wiki/concepts/validation-and-overfitting.md).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
import os
import random
import statistics
import sys
import time
from collections.abc import Callable
from operator import itemgetter, mul
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from pathlib import Path

from arena import report
from arena.botfile import OverrideError, parse_value
from arena.cli import Setup, add_common_arguments, add_rival_argument, participant_names, run_with_rivals, setup
from arena.engine import TradeMatching
from arena.formats import FORMATS
from arena.model import Day

SMOKE_TEST_TICKS = 200
BLOCKS = 16  # CSCV's S over all the days: Bailey et al. call 16 reasonable (p. 21-22)
MAX_SPLITS = 4000  # halvings of the blocks to score; sampled (seeded) when there are more
EULER_GAMMA = 0.5772156649015329
FINE_TICKS = 100  # ticks per block for SPA and StepM: about 100 blocks a day
SPA_Q = 0.1  # stationary bootstrap: a new block starts with probability q, so blocks average 1/q
BOOTSTRAP = 1000  # resamples; Romano and Wolf recommend at least 1,000 (p. 15)
ALPHA = 0.05  # StepM's familywise error
MIN_FINE_BLOCKS = 20  # fewer and the bootstrap tests are skipped


@dataclass(frozen=True)
class Axis:
    target: str
    values: list

    @property
    def label(self) -> str:
        return self.target.removeprefix("PARAMS.")


@dataclass
class Outcome:
    """One combination's results, summed over its backtests."""

    index: tuple[int, ...]  # position of each value on its axis
    values: tuple
    day_pnl: dict[TradeMatching, dict[str, float]] = field(default_factory=dict)  # mode -> day -> pnl
    product_pnl: dict[TradeMatching, dict[str, float]] = field(default_factory=dict)  # mode -> product -> pnl
    block_pnl: dict[TradeMatching, list[float]] = field(default_factory=dict)  # mode -> PnL per block, days in order
    fine_pnl: dict[TradeMatching, list[float]] = field(default_factory=dict)  # the same per block of FINE_TICKS ticks
    fills: int = 0  # under the first mode
    errors: int = 0  # over all modes
    limit_breaches: int = 0
    first_error: str = ""

    def pnl(self, mode: TradeMatching) -> float:
        return sum(self.day_pnl[mode].values())

    def min_day(self, mode: TradeMatching) -> float:
        return min(self.day_pnl[mode].values())

    @property
    def failed(self) -> bool:
        return bool(self.errors or self.limit_breaches)


@dataclass(frozen=True)
class Row:
    """A combination as shown in the summary."""

    values: tuple
    pnl: dict[TradeMatching, float]
    min_day: float  # under the first mode
    nbhd: float  # under the first mode
    fills: int
    failed: bool


# ---------------------------------------------------------------------------- axes


def parse_axis(text: str) -> Axis:
    """`PATH=V1,V2,...` or `PATH=START..STOP[..STEP]` (inclusive).

    Values are Python literals; bare words are strings, e.g. PARAMS.KELP.fair=mid,wall_mid.
    """
    target, sep, raw = text.partition("=")
    target, raw = target.strip(), raw.strip()
    if not sep or not target or not raw:
        raise ValueError(f"expected PATH=V1,V2,... or PATH=START..STOP[..STEP], got {text!r}")
    values = _range(raw) if ".." in raw else [_literal(part.strip()) for part in raw.split(",")]
    if len({repr(v) for v in values}) != len(values):
        raise ValueError(f"{target}: duplicate values")
    return Axis(target, values)


def _literal(text: str):
    return parse_value(text)


def _range(text: str) -> list:
    parts = [_literal(part.strip()) for part in text.split("..")]
    if len(parts) not in (2, 3) or not all(isinstance(p, (int, float)) and not isinstance(p, bool) for p in parts):
        raise ValueError(f"bad range {text!r}: use START..STOP or START..STOP..STEP with numbers")
    start, stop, step = parts[0], parts[1], parts[2] if len(parts) == 3 else 1
    if step <= 0 or stop < start:
        raise ValueError(f"bad range {text!r}: needs STOP >= START and STEP > 0")
    count = math.floor((stop - start) / step + 1e-9) + 1
    values = [start + i * step for i in range(count)]
    return values if all(isinstance(p, int) for p in parts) else [round(v, 10) for v in values]


# ---------------------------------------------------------------------------- running

# Set once per worker process by _init_worker, read by _evaluate.
_WORKER: dict = {}


def _init_worker(format_name, data_arg, day_specs, bot_path, base_overrides, targets, modes, config, rivals, requote, days=None):
    fmt = FORMATS[format_name]
    _WORKER.update(
        fmt=fmt,
        days=days if days is not None else fmt.load_days(fmt.resolve_data_dir(data_arg), day_specs),
        bot=bot_path,
        base=base_overrides,
        targets=targets,
        modes=modes,
        config=config,
        rivals=rivals,
        requote=requote,
    )


def _evaluate(index: tuple[int, ...], values: tuple) -> Outcome:
    w = _WORKER
    overrides = {**w["base"], **dict(zip(w["targets"], values))}
    outcome = Outcome(index, values)
    for mode_number, mode in enumerate(w["modes"]):
        config = replace(w["config"], trade_matching=mode)
        days, products = outcome.day_pnl.setdefault(mode, {}), outcome.product_pnl.setdefault(mode, {})
        blocks = outcome.block_pnl.setdefault(mode, [])
        fine = outcome.fine_pnl.setdefault(mode, [])
        for day in w["days"]:
            result = run_with_rivals(w["fmt"], day, w["bot"], overrides, w["rivals"], config, requote=w["requote"])[0]
            series = report.total_pnl(result) or [0.0] * len(day.ticks)
            days[day.name] = series[-1]
            blocks += block_pnl(series, blocks_per_day(len(w["days"])))
            fine += block_pnl(series, len(series) // FINE_TICKS)
            for stats in report.product_stats(result):
                products[stats.product] = products.get(stats.product, 0.0) + stats.pnl
            if mode_number == 0:
                outcome.fills += len(result.fills)
            outcome.errors += len(result.errors)
            outcome.limit_breaches += len(result.limit_breaches)
            if result.errors and not outcome.first_error:
                outcome.first_error = report.last_line(result.errors[0][1])
    return outcome


def run_grid(
    s: Setup, bot: Path, axes: list[Axis], modes: list[TradeMatching], jobs: int, format_name: str, data_arg: str, day_specs: list[str]
) -> tuple[Outcome, dict[tuple[int, ...], Outcome]]:
    """Returns the baseline (the bot with only --set applied) and every combination's outcome."""
    combos = list(itertools.product(*(range(len(axis.values)) for axis in axes)))
    tasks = [((), ())] + [(index, tuple(axes[i].values[j] for i, j in enumerate(index))) for index in combos]
    init_args = (format_name, data_arg, day_specs, bot, s.overrides, [axis.target for axis in axes], modes, s.config, s.rivals, s.requote)

    outcomes: dict[tuple[int, ...], Outcome] = {}
    progress = _Progress(len(tasks))
    if jobs <= 1:
        _init_worker(*init_args, days=s.days)  # reuse the days already loaded
        for index, values in tasks:
            outcomes[index] = _evaluate(index, values)
            progress.step()
    else:
        with ProcessPoolExecutor(jobs, initializer=_init_worker, initargs=init_args) as pool:
            futures = [pool.submit(_evaluate, index, values) for index, values in tasks]
            for future in as_completed(futures):
                outcome = future.result()
                outcomes[outcome.index] = outcome
                progress.step()
    progress.done()
    return outcomes.pop(()), outcomes


def smoke_test(s: Setup, bot: Path, axes: list[Axis]) -> None:
    """Runs the first combination briefly, so a typo fails fast instead of in every run."""
    overrides = {**s.overrides, **{axis.target: axis.values[0] for axis in axes}}
    day = s.days[0]
    sample = Day(day.name, day.products, day.limits, day.ticks[:SMOKE_TEST_TICKS])
    result = run_with_rivals(s.format, sample, bot, overrides, s.rivals, s.config, requote=s.requote)[0]
    if result.errors:
        raise ValueError(f"the bot fails with the first combination: {report.last_line(result.errors[0][1])}")


class _Progress:
    def __init__(self, total: int):
        self.total, self.done_count = total, 0
        self.live = sys.stderr.isatty()

    def step(self) -> None:
        self.done_count += 1
        if self.live:
            print(f"\r  {self.done_count}/{self.total} combinations", end="", file=sys.stderr, flush=True)

    def done(self) -> None:
        if self.live:
            print("\r" + " " * 40 + "\r", end="", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------- results


def neighborhood_mean(outcomes: dict[tuple[int, ...], Outcome], index: tuple[int, ...], shape: tuple[int, ...], mode) -> float:
    """Mean PnL of a combination and its neighbours one step along each axis.

    Neighbours that failed (errors or limit breaches) are left out: their PnL isn't what the
    setting would make, and the summary leaves them out too.
    """
    pnls = [outcomes[index].pnl(mode)]
    for axis, size in enumerate(shape):
        for step in (-1, 1):
            position = index[axis] + step
            if 0 <= position < size:
                neighbour = outcomes[index[:axis] + (position,) + index[axis + 1 :]]
                if not neighbour.failed:
                    pnls.append(neighbour.pnl(mode))
    return statistics.fmean(pnls)


def build_rows(axes: list[Axis], modes: list[TradeMatching], outcomes: dict[tuple[int, ...], Outcome]) -> list[Row]:
    shape, primary = tuple(len(axis.values) for axis in axes), modes[0]
    return [
        Row(
            values=outcome.values,
            pnl={mode: outcome.pnl(mode) for mode in modes},
            min_day=outcome.min_day(primary),
            nbhd=neighborhood_mean(outcomes, index, shape, primary),
            fills=outcome.fills,
            failed=outcome.failed,
        )
        for index, outcome in sorted(outcomes.items())
    ]


def measures(modes: list[TradeMatching]) -> dict[str, Callable[[Row], float]]:
    """Ranking measures by name: pnl, nbhd, min-day, and one per extra mode."""
    primary = modes[0]
    named = {
        "pnl": lambda row: row.pnl[primary],
        "nbhd": lambda row: row.nbhd,
        "min-day": lambda row: row.min_day,
    }
    for mode in modes[1:]:
        named[mode.value] = lambda row, mode=mode: row.pnl[mode]
    return named


def format_summary(axes, modes, baseline: Outcome, rows: list[Row], sort: str, top: int) -> str:
    primary = modes[0]
    named = measures(modes)
    lines = [
        "baseline (bot as is): "
        + " · ".join(f"pnl({mode}) {baseline.pnl(mode):,.0f}" for mode in modes)
        + (f" · ! {baseline.errors} errors" if baseline.errors else "")
    ]

    header = ["rank", *(axis.label for axis in axes), f"pnl({primary})", "min day", "nbhd"]
    header += [f"pnl({mode})" for mode in modes[1:]] + ["fills", ""]
    ranked = sorted(rows, key=named[sort], reverse=True)
    table = []
    for rank, row in enumerate(ranked[:top], 1):
        cells = [str(rank), *(str(v) for v in row.values), _num(row.pnl[primary]), _num(row.min_day), _num(row.nbhd)]
        cells += [_num(row.pnl[mode]) for mode in modes[1:]] + [f"{row.fills:,}", "!" if row.failed else ""]
        table.append(cells)
    widths = [max(len(cell) for cell in column) for column in zip(header, *table)]
    lines.append("")
    for cells in [header, *table]:
        lines.append("  ".join(cell.rjust(width) for cell, width in zip(cells, widths)).rstrip())
    if len(ranked) > top:
        lines.append(f"  ... {len(ranked) - top} more (--top, or --out for all)")

    usable = [row for row in rows if not row.failed]
    failed = len(rows) - len(usable)
    lines.append("")
    if failed:
        lines.append(f"! {failed} combinations had errors or limit breaches and are left out below")
    if not usable:
        lines.append("every combination failed")
        return "\n".join(lines)

    picks = {}
    width = max(len(name) for name in named)
    for name, key in named.items():
        best = max(usable, key=key)
        picks[name] = best.values
        setting = ", ".join(f"{axis.label}={str(v)}" for axis, v in zip(axes, best.values))
        lines.append(f"best by {name:<{width}}  {setting}  ({_num(key(best))})")
    if len(set(picks.values())) == 1:
        lines.append("all measures agree")
    else:
        lines.append("measures disagree: prefer a setting near the top on every measure over the single best pnl")
    return "\n".join(lines)


def leave_one_day_out(outcomes: dict[tuple[int, ...], Outcome], mode: TradeMatching) -> dict[str, Outcome]:
    """For each day, the combination with the best PnL on the other days (failed ones left out)."""
    usable = [outcome for _, outcome in sorted(outcomes.items()) if not outcome.failed]
    if not usable or len(usable[0].day_pnl[mode]) < 2:
        return {}
    return {
        day: max(usable, key=lambda outcome, day=day: outcome.pnl(mode) - outcome.day_pnl[mode][day])
        for day in usable[0].day_pnl[mode]
    }


def repeated_days(days: list[Day]) -> list[tuple[list[str], list[str]]]:
    """Days whose data repeats, as (day names, the products whose books and trades are the same).

    Compared product by product, since Prosperity reuses a day for the products a later round keeps
    (P3 round 3's days 0 and 1 are round 2's for every round 2 product), and trades without
    counterparty names (P4's round 4 repeats two days of round 3 with names added).
    """
    by_product: dict[tuple, list[str]] = {}
    for day in days:
        ticks = day.ticks[:SMOKE_TEST_TICKS]
        for product in day.products:
            books = [(t.timestamp, t.books.get(product)) for t in ticks]
            trades = [sorted((tr.price, tr.quantity) for tr in t.trades.get(product, [])) for t in ticks]
            by_product.setdefault((product, len(day.ticks), repr(books), repr(trades)), []).append(day.name)
    groups: dict[tuple[str, ...], list[str]] = {}
    for (product, *_), names in by_product.items():
        if len(names) > 1:
            groups.setdefault(tuple(names), []).append(product)
    return [(list(names), sorted(products)) for names, products in groups.items()]


def format_held_out(
    axes: list[Axis], modes: list[TradeMatching], outcomes: dict[tuple[int, ...], Outcome], repeats: list[tuple[list[str], list[str]]]
) -> str:
    mode = modes[0]
    picks = leave_one_day_out(outcomes, mode)
    if not picks:
        return ""
    best = max((o for o in outcomes.values() if not o.failed), key=lambda outcome: outcome.pnl(mode))
    lines = [f"held-out days: the best pnl({mode}) on the other days, scored on the day left out"]
    for day, pick in picks.items():
        setting = ", ".join(f"{axis.label}={str(v)}" for axis, v in zip(axes, pick.values))
        lines.append(f"  {day}: {setting}  {_num(pick.day_pnl[mode][day])}  (best combination: {_num(best.day_pnl[mode][day])})")
    held, full = sum(pick.day_pnl[mode][day] for day, pick in picks.items()), best.pnl(mode)
    gap = f" ({(held - full) / abs(full):+.0%})" if full else ""
    choices = len({pick.values for pick in picks.values()})
    lines.append(f"held out {_num(held)} against {_num(full)} for the best combination{gap}; {choices} different settings chosen over {len(picks)} days")
    for names, products in repeats:
        which = ", ".join(products) if len(products) <= 4 else f"{len(products)} products"
        lines.append(f"! {', '.join(names)} hold the same data for {which}: holding one out still trains on the other")
    return "\n".join(lines)


# ---------------------------------------------------------------------------- overfitting


def blocks_per_day(days: int) -> int:
    """Blocks to cut each day into: about BLOCKS in all, an even number over the days (CSCV halves them)."""
    per_day = math.ceil(BLOCKS / days)
    return per_day + (per_day * days) % 2


def block_pnl(series: list[float], blocks: int) -> list[float]:
    """A day's cumulative PnL series cut into contiguous blocks: each block's PnL. Empty if too short."""
    if len(series) < blocks:
        return []
    out, last = [], 0.0
    for k in range(blocks):
        end = series[round(len(series) * (k + 1) / blocks) - 1]
        out.append(end - last)
        last = end
    return out


@dataclass(frozen=True)
class Cscv:
    pbo: float  # share of halvings where the in-sample best is at or below the out-of-sample median
    loss: float  # share of halvings where it loses money out of sample
    rank: float  # its mean relative rank w out of sample: near 1 the top, 0.5 the median
    splits: int  # halvings scored
    of: int  # halvings there are


def cscv(columns: list[list[float]], max_splits: int = MAX_SPLITS, seed: int = 0) -> Cscv:
    """Bailey et al.'s combinatorially symmetric cross-validation (Algorithm 2.3, p. 11-12).

    `columns` holds each cell's PnL per block, the blocks in the same order for every cell. Each
    halving of the blocks is a training half and a test half; the cell with the best training PnL
    gets its test rank r in 1..N (higher is better, ties averaged), w = r / (N + 1), and the
    halving counts as overfit when the logit ln(w / (1 - w)) <= 0.
    """
    n, s = len(columns), len(columns[0])
    of = math.comb(s, s // 2)
    if of <= max_splits:
        halvings = list(itertools.combinations(range(s), s // 2))
    else:
        rng, seen = random.Random(seed), set()
        while len(seen) < max_splits:
            seen.add(tuple(sorted(rng.sample(range(s), s // 2))))
        halvings = sorted(seen)
    totals = [sum(column) for column in columns]
    overfit = losses = 0
    ranks = []
    for train in halvings:
        inside = [sum(column[i] for i in train) for column in columns]
        outside = [total - x for total, x in zip(totals, inside)]
        best = max(range(n), key=inside.__getitem__)
        mine = outside[best]
        rank = sum(1 for v in outside if v < mine) + (sum(1 for v in outside if v == mine) + 1) / 2
        w = rank / (n + 1)
        overfit += math.log(w / (1 - w)) <= 0
        losses += mine < 0
        ranks.append(w)
    return Cscv(overfit / len(halvings), losses / len(halvings), statistics.fmean(ranks), len(halvings), of)


def expected_max_sharpe(variance: float, trials: float) -> float:
    """SR0, the best Sharpe ratio expected from `trials` independent cells with no edge whose Sharpe
    ratios have this variance (Bailey and Lopez de Prado, eq. 1-2, p. 7-9). 0 below two trials."""
    if trials < 2:
        return 0.0
    z = statistics.NormalDist().inv_cdf
    return math.sqrt(variance) * ((1 - EULER_GAMMA) * z(1 - 1 / trials) + EULER_GAMMA * z(1 - 1 / (trials * math.e)))


def deflated_sharpe(sharpe: float, sharpe0: float, periods: int, skew: float, kurtosis: float) -> float | None:
    """DSR = Z[(SR - SR0) sqrt(T - 1) / sqrt(1 - skew SR + (kurtosis - 1) / 4 SR^2)] (eq. 2, p. 8-9);
    kurtosis is not excess (3 for a normal). None when the root's argument isn't positive."""
    spread = 1 - skew * sharpe + (kurtosis - 1) / 4 * sharpe**2
    if spread <= 0 or periods < 2:
        return None
    return statistics.NormalDist().cdf((sharpe - sharpe0) * math.sqrt(periods - 1) / math.sqrt(spread))


def independent_trials(columns: list[list[float]]) -> float:
    """N^ = rho + (1 - rho) M, rho the average pairwise correlation of the M cells' block PnL (eq. 9,
    p. 14-15). Cells with a constant PnL per block have no correlation and are left out of rho."""
    m = len(columns)
    scaled = []
    for column in columns:
        sd = statistics.pstdev(column)
        if sd > 0:
            mean = statistics.fmean(column)
            scaled.append([(x - mean) / sd for x in column])
    pairs = [(a, b) for i, a in enumerate(scaled) for b in scaled[i + 1 :]]
    if not pairs:
        return float(m)
    rho = statistics.fmean(sum(x * y for x, y in zip(a, b)) / len(a) for a, b in pairs)
    return rho + (1 - rho) * m


def omega2(d: list[float], q: float) -> float:
    """Hansen's variance of sqrt(n) times the mean under the stationary bootstrap (p. 8):
    gamma_0 + 2 sum_i kappa(n, i) gamma_i, kappa(n, i) = (n-i)/n (1-q)^i + i/n (1-q)^(n-i)."""
    n, mean = len(d), statistics.fmean(d)
    c = [x - mean for x in d]
    total = sum(map(mul, c, c)) / n
    for i in range(1, n):
        kappa = (n - i) / n * (1 - q) ** i + i / n * (1 - q) ** (n - i)
        if kappa < 1e-12:
            continue
        total += 2 * kappa * sum(map(mul, c, itertools.islice(c, i, None))) / n
    return total


def bootstrap_means(d: list[list[float]], q: float, boot: int, seed: int) -> list[list[float]]:
    """Each resample's mean of every column, by Politis and Romano's stationary bootstrap (Hansen,
    p. 7): with probability q the next index is drawn afresh, else it follows the last, wrapping."""
    n, rng, out = len(d[0]), random.Random(seed), []
    for _ in range(boot):
        idx, t = [], rng.randrange(n)
        for _ in range(n):
            idx.append(t)
            t = rng.randrange(n) if rng.random() < q else (t + 1) % n
        pick = itemgetter(*idx)
        out.append([sum(pick(column)) / n for column in d])
    return out


def _scales(d: list[list[float]], q: float) -> list[float]:
    return [math.sqrt(max(omega2(c, q), 1e-12)) for c in d]


def spa(d: list[list[float]], q: float, boot: int, seed: int = 0, *, omegas=None, draws=None) -> dict[str, float]:
    """Hansen's SPA p-values for H0: no column of gains has a positive mean (p. 4 and 7-8). The
    bootstrap is recentred at mu_l = min(mean, 0), at mu_c (only means clearly below 0 kept, the
    consistent one) and at mu_u = 0 (the studentized Reality Check)."""
    n = len(d[0])
    means = [statistics.fmean(c) for c in d]
    omegas = omegas or _scales(d, q)
    t = max(0.0, max(math.sqrt(n) * m / w for m, w in zip(means, omegas)))
    loglog = math.sqrt(2 * math.log(math.log(n)))
    shifts = {
        "l": [max(0.0, m) for m in means],
        "c": [m if m >= -w / math.sqrt(n) * loglog else 0.0 for m, w in zip(means, omegas)],
        "u": means,
    }
    draws = draws or bootstrap_means(d, q, boot, seed)
    out = {}
    for name, shift in shifts.items():
        above = sum(max(0.0, max(math.sqrt(n) * (x - s) / w for x, s, w in zip(draw, shift, omegas))) > t for draw in draws)
        out[name] = above / len(draws)
    return out


def stepm(d: list[list[float]], q: float, boot: int, alpha: float = ALPHA, seed: int = 1, *, omegas=None, draws=None) -> list[int]:
    """Romano and Wolf's studentized step-down (Algorithms 4.1-4.2, p. 14-15): the columns whose
    mean gain is significantly positive, the familywise error held at alpha. Studentized by
    Hansen's omega, fixed across resamples (ours; the paper recomputes it in each)."""
    n = len(d[0])
    means = [statistics.fmean(c) for c in d]
    omegas = omegas or _scales(d, q)
    z = [math.sqrt(n) * m / w for m, w in zip(means, omegas)]
    draws = draws or bootstrap_means(d, q, boot, seed)
    centred = [[math.sqrt(n) * (x - m) / w for x, m, w in zip(draw, means, omegas)] for draw in draws]
    active, rejected = set(range(len(d))), []
    while active:
        maxima = sorted(max(draw[k] for k in active) for draw in centred)
        c = maxima[min(len(maxima) - 1, math.ceil((1 - alpha) * len(maxima)) - 1)]
        newly = [k for k in active if z[k] > c]
        if not newly:
            break
        rejected += newly
        active -= set(newly)
    return sorted(rejected)


def format_snooping(axes: list[Axis], baseline: Outcome, outcomes: dict[tuple[int, ...], Outcome], modes: list[TradeMatching], dsr: float | None) -> str:
    """SPA and StepM on each distinct cell's gain over the bot as is, per block of FINE_TICKS ticks,
    under the first mode; StepM's cells are then checked against the bot as is under the others."""
    mode = modes[0]
    base = baseline.fine_pnl.get(mode, [])
    cells: dict[tuple, tuple[list[float], list[Outcome]]] = {}
    for _, o in sorted(outcomes.items()):
        fine = o.fine_pnl.get(mode, [])
        if o.failed or len(fine) != len(base):
            continue
        gain = [x - b for x, b in zip(fine, base)]
        if any(gain):
            cells.setdefault(tuple(round(x, 6) for x in gain), (gain, []))[1].append(o)
    if baseline.failed or len(base) < MIN_FINE_BLOCKS or not cells:
        return f"  SPA, StepM: skipped (needs a working bot as is, a cell that differs from it, and {MIN_FINE_BLOCKS}+ blocks of {FINE_TICKS} ticks)"
    groups = list(cells.values())
    d = [gain for gain, _ in groups]
    omegas = _scales(d, SPA_Q)
    draws = bootstrap_means(d, SPA_Q, BOOTSTRAP, seed=0)
    p = spa(d, SPA_Q, BOOTSTRAP, omegas=omegas, draws=draws)
    winners = stepm(d, SPA_Q, BOOTSTRAP, omegas=omegas, draws=draws)
    lines = [
        f"  SPA on pnl({mode}) gains over the bot as is, {len(base)} blocks of {FINE_TICKS} ticks, {len(d)} distinct cells, "
        f"bootstrap blocks of {round(FINE_TICKS / SPA_Q):,} ticks on average, {BOOTSTRAP:,} resamples:",
        f"  p {p['c']:.3f} that no cell beats the bot as is (bounds {p['l']:.3f} to {p['u']:.3f}; the upper is the Reality Check)",
    ]
    if winners:
        ranked = sorted(winners, key=lambda k: -statistics.fmean(d[k]))
        named = ["; ".join(", ".join(f"{a.label}={v}" for a, v in zip(axes, o.values)) for o in groups[k][1]) for k in ranked]
        shown = " | ".join(named[:5]) + (f" | ... {len(named) - 5} more" if len(named) > 5 else "")
        lines.append(f"  StepM at {ALPHA:.0%}: {len(winners)} cells beat the bot as is: {shown}")
    else:
        lines.append(f"  StepM at {ALPHA:.0%}: no cell beats the bot as is")
    if p["c"] < ALPHA and dsr is not None and dsr < 0.95:
        lines.append("! SPA finds a gain the DSR doesn't: the DSR's bar rises with the spread of all cells, poor ones included, "
                     "and SPA discounts those (references/wiki/contradictions.md, row 18)")
    for other in modes[1:]:
        found = [o for k in winners for o in groups[k][1]]
        if not found:
            break
        holds = [o for o in found if o.pnl(other) > baseline.pnl(other)]
        best = max(o.pnl(other) - baseline.pnl(other) for o in found)
        lines.append(f"  under {other}: {len(holds)} of StepM's {len(found)} cells beat the bot as is (best by {best:+,.0f})")
        if not holds:
            lines.append(f"! StepM's cells only beat the bot as is under {mode}: the gain depends on the fill model")
    if p["c"] < ALPHA and len(modes) == 1:
        lines.append("  a gain under one matching mode still has to hold under the others: rerun with --modes all,worse")
    found = [o for k in winners for o in groups[k][1]]
    holding = [o for o in found if all(o.pnl(m) > baseline.pnl(m) for m in modes[1:])]
    if holding:
        best = max(holding, key=lambda o: o.pnl(mode))
        setting = ", ".join(f"{a.label}={v}" for a, v in zip(axes, best.values))
        gains = " · ".join(f"{m} {best.pnl(m) - baseline.pnl(m):+,.0f}" for m in modes)
        lines.append(f"  pick: {setting} ({gains}): StepM's best cell that beats the bot as is under every mode")
    else:
        lines.append("  pick: the bot as is: no StepM cell beats it under every mode")
    return "\n".join(lines)


def format_overfitting(baseline: Outcome, outcomes: dict[tuple[int, ...], Outcome], modes: list[TradeMatching], days: int, axes: list[Axis] | None = None) -> str:
    mode = modes[0]
    usable = [o for _, o in sorted(outcomes.items()) if not o.failed]
    columns = list({tuple(round(v, 6) for v in o.block_pnl[mode]): o.block_pnl[mode] for o in usable}.values())
    lines = [f"overfitting: {len(outcomes)} cells × {len(modes)} modes = {len(outcomes) * len(modes)} trials on {days} days"]
    blocks = len(columns[0]) if columns else 0
    if len(columns) < 2 or blocks < 2 or any(len(c) != blocks for c in columns):
        lines.append("  fewer than two distinct cells, or days too short to cut into blocks: no PBO or DSR")
        if axes is not None:
            lines.append(format_snooping(axes, baseline, outcomes, modes, None))
        return "\n".join(lines)
    result = cscv(columns)
    sampled = f"{result.splits:,} of {result.of:,}" if result.splits < result.of else f"all {result.of:,}"
    coarse = " (under 10: coarse ranks)" if len(columns) < 10 else ""
    lines.append(f"  CSCV on pnl({mode}) in {blocks} blocks ({blocks // days} a day), {len(columns)} distinct cells{coarse}, {sampled} halvings:")
    lines.append(f"  PBO {result.pbo:.0%}  ·  the pick's mean rank out of sample {result.rank:.2f} (1 top, 0.5 median)  ·  it loses money there in {result.loss:.0%}")
    base = baseline.block_pnl[mode]
    gains = [[x - b for x, b in zip(c, base)] for c in columns] if len(base) == blocks else []
    best = [x - b for x, b in zip(max(usable, key=lambda o: o.pnl(mode)).block_pnl[mode], base)] if gains else []
    sharpes = [statistics.fmean(g) / statistics.stdev(g) for g in gains if statistics.stdev(g) > 0]
    trials = independent_trials(gains) if gains else 0.0
    dsr = None
    if best and not any(best):
        lines.append("  the best cell is the bot as is: no gain to deflate")
    elif best and statistics.stdev(best) > 0 and len(sharpes) >= 2:
        mean, sd = statistics.fmean(best), statistics.pstdev(best)
        skew = statistics.fmean(((x - mean) / sd) ** 3 for x in best)
        kurtosis = statistics.fmean(((x - mean) / sd) ** 4 for x in best)
        sharpe, sharpe0 = statistics.fmean(best) / statistics.stdev(best), expected_max_sharpe(statistics.variance(sharpes), trials)
        dsr = deflated_sharpe(sharpe, sharpe0, blocks, skew, kurtosis)
        rough = " (more cells than blocks: N^ is rough)" if len(columns) > blocks else ""
        shown = f"{dsr:.2f}" if dsr is not None else "-"
        lines.append(f"  DSR {shown} for the best cell's gain over the bot as is: per-block Sharpe {sharpe:.2f} against {sharpe0:.2f}, "
                     f"the best of N^ {trials:.1f} cells with no gain{rough}")
        if dsr is not None and dsr < 0.95:
            lines.append("! the best cell's gain over the bot as is is not clearly more than the best of that many cells with no gain (DSR < 0.95)")
    if result.pbo >= 0.5:
        lines.append("! PBO >= 50%: the best cell in one half of the blocks is as likely as not to be below the median in the other")
    if axes is not None:
        lines.append(format_snooping(axes, baseline, outcomes, modes, dsr))
    return "\n".join(lines)


def write_csv(path: Path, axes: list[Axis], modes: list[TradeMatching], outcomes: dict[tuple[int, ...], Outcome]) -> None:
    """One row per combination: axis values, then per mode its pnl, min day, nbhd, per-day and per-product pnl."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(outcomes.items())
    shape = tuple(len(axis.values) for axis in axes)
    first = ordered[0][1]
    days = {mode: list(first.day_pnl[mode]) for mode in modes}
    products = {mode: sorted({p for _, o in ordered for p in o.product_pnl[mode]}) for mode in modes}

    header = [axis.target for axis in axes]
    for mode in modes:
        header += [f"pnl_{mode}", f"min_day_{mode}", f"nbhd_{mode}"]
        header += [f"pnl_{mode}_{day}" for day in days[mode]]
        header += [f"pnl_{mode}_{product}" for product in products[mode]]
    header += ["fills", "errors", "limit_breaches"]

    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for index, outcome in ordered:
            row = list(outcome.values)
            for mode in modes:
                row += [outcome.pnl(mode), outcome.min_day(mode), neighborhood_mean(outcomes, index, shape, mode)]
                row += [outcome.day_pnl[mode][day] for day in days[mode]]
                row += [outcome.product_pnl[mode].get(product, 0.0) for product in products[mode]]
            row += [outcome.fills, outcome.errors, outcome.limit_breaches]
            writer.writerow(row)


def _num(value: float) -> str:
    return f"{value:,.0f}"



# ---------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m arena.grid", description="Grid-search bot parameters, with robustness checks."
    )
    add_common_arguments(parser)
    add_rival_argument(parser)
    parser.add_argument(
        "--grid",
        dest="axes",
        action="append",
        required=True,
        metavar="PATH=VALUES",
        help="a parameter to vary: PATH=V1,V2,... or PATH=START..STOP[..STEP], inclusive. Repeat for more axes.",
    )
    parser.add_argument(
        "--modes",
        help="comma-separated trade-matching modes to run every combination under, e.g. all,worse. "
        "The first is the main one (default: --match-trades)",
    )
    parser.add_argument("--sort", default="pnl", help="rank by pnl, nbhd, min-day, or an extra mode's pnl (default: pnl)")
    parser.add_argument("--top", type=int, default=15, help="rows to show (default: 15)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: CPU count)")
    parser.add_argument("--out", type=Path, help="write every combination's results to this CSV")
    args = parser.parse_args(argv)

    try:
        s = setup(args)
        axes = [parse_axis(text) for text in args.axes]
        modes = [TradeMatching(mode.strip()) for mode in args.modes.split(",")] if args.modes else [args.match_trades]
        _check(axes, modes, s, args.sort)
        smoke_test(s, args.bot, axes)
    except (ValueError, OSError, OverrideError) as error:
        parser.error(str(error))

    combos = math.prod(len(axis.values) for axis in axes)
    jobs = max(1, min(args.jobs, combos + 1))
    runs = (combos + 1) * len(s.days) * len(modes)
    print(f"{combos} combinations × {len(s.days)} days × {len(modes)} modes ({runs} backtests) on {jobs} workers")
    if s.rivals:
        print(f"each against {', '.join(participant_names(args.bot, s.rivals)[1:])} in the same market")
    start = time.perf_counter()
    baseline, outcomes = run_grid(s, args.bot, axes, modes, jobs, args.format, args.data, args.days)
    print(f"done in {time.perf_counter() - start:.1f} s\n")

    rows = build_rows(axes, modes, outcomes)
    print(format_summary(axes, modes, baseline, rows, args.sort, args.top))
    held_out = format_held_out(axes, modes, outcomes, repeated_days(s.days))
    if held_out:
        print("\n" + held_out)
    print("\n" + format_overfitting(baseline, outcomes, modes, len(s.days), axes))
    failed = [o for o in outcomes.values() if o.first_error]
    if failed:
        print(f"first error: {failed[0].first_error}")
    if args.out:
        write_csv(args.out, axes, modes, outcomes)
        print(f"\nall combinations written to {args.out}")
    return 1 if all(outcome.failed for outcome in outcomes.values()) else 0


def _check(axes: list[Axis], modes: list[TradeMatching], s: Setup, sort: str) -> None:
    targets = [axis.target for axis in axes]
    duplicated = {t for t in targets if targets.count(t) > 1} | (set(targets) & set(s.overrides))
    if duplicated:
        raise ValueError(f"set more than once by --grid/--set: {', '.join(sorted(duplicated))}")
    if len(set(modes)) != len(modes):
        raise ValueError("--modes lists a mode twice")
    if sort not in measures(modes):
        raise ValueError(f"--sort must be one of {', '.join(measures(modes))}")


if __name__ == "__main__":
    sys.exit(main())
