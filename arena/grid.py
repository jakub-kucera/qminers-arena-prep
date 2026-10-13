"""Grid search over bot parameters, with robustness checks.

    uv run python -m arena.grid bots/template.py 1 \\
        --grid PARAMS.KELP.make_edge=1,2,3 --grid PARAMS.KELP.take_edge=0..2 --modes all,worse

Every combination of --grid values is backtested on every given day, under each trade-matching
mode in --modes, in parallel. The combination with the best PnL is usually overfit, so each
combination also gets:

  min day   its worst single day: a good setting should do well on every day, not just one
  nbhd      the mean PnL of it and its grid neighbours (one step along any axis). Prefer a
            plateau, where nearby values do about as well, to a lone spike.
  <mode>    PnL under each extra --modes entry, e.g. `worse` fill matching. A gain that only
            exists with optimistic fills is probably a backtest artefact.

The summary names the best combination by each measure and says whether they agree. With two or
more days it also holds out each day in turn: the combination with the best PnL on the other days
is scored on the held-out day. The total of those scores is what choosing by PnL earns on days it
didn't see, and its gap to the best combination's PnL is the selection bias of a grid this size.
It only covers the gridded values: a setting the bot fits to the data itself (say a level taken
from the days' mean) needs its own held-out test. Days whose data repeats are flagged, since
holding one out still trains on its copy.
"""

from __future__ import annotations

import argparse
import ast
import csv
import itertools
import math
import os
import statistics
import sys
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from pathlib import Path

from arena import report
from arena.botfile import OverrideError
from arena.cli import Setup, add_common_arguments, add_rival_argument, participant_names, run_with_rivals, setup
from arena.engine import TradeMatching
from arena.formats import FORMATS
from arena.model import Day

SMOKE_TEST_TICKS = 200


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
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


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


def _init_worker(format_name, data_arg, day_specs, bot_path, base_overrides, targets, modes, config, rivals, days=None):
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
    )


def _evaluate(index: tuple[int, ...], values: tuple) -> Outcome:
    w = _WORKER
    overrides = {**w["base"], **dict(zip(w["targets"], values))}
    outcome = Outcome(index, values)
    for mode_number, mode in enumerate(w["modes"]):
        config = replace(w["config"], trade_matching=mode)
        days, products = outcome.day_pnl.setdefault(mode, {}), outcome.product_pnl.setdefault(mode, {})
        for day in w["days"]:
            result = run_with_rivals(w["fmt"], day, w["bot"], overrides, w["rivals"], config)[0]
            days[day.name] = (report.total_pnl(result) or [0.0])[-1]
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
    init_args = (format_name, data_arg, day_specs, bot, s.overrides, [axis.target for axis in axes], modes, s.config, s.rivals)

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
    result = run_with_rivals(s.format, sample, bot, overrides, s.rivals, s.config)[0]
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
    """Mean PnL of a combination and its neighbours one step along each axis."""
    pnls = [outcomes[index].pnl(mode)]
    for axis, size in enumerate(shape):
        for step in (-1, 1):
            position = index[axis] + step
            if 0 <= position < size:
                pnls.append(outcomes[index[:axis] + (position,) + index[axis + 1 :]].pnl(mode))
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


def repeated_days(days: list[Day]) -> list[list[str]]:
    """Groups of days with the same books and trades: the same data loaded twice.

    Trades are compared without counterparty names: P4's round 4 repeats two days of round 3 with
    names added.
    """
    groups: dict[tuple, list[str]] = {}
    for day in days:
        ticks = day.ticks[:SMOKE_TEST_TICKS]
        trades = [sorted((p, tr.price, tr.quantity) for p, trs in t.trades.items() for tr in trs) for t in ticks]
        key = (len(day.ticks), repr([(t.timestamp, t.books) for t in ticks]), repr(trades))
        groups.setdefault(key, []).append(day.name)
    return [names for names in groups.values() if len(names) > 1]


def format_held_out(axes: list[Axis], modes: list[TradeMatching], outcomes: dict[tuple[int, ...], Outcome], repeats: list[list[str]]) -> str:
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
    for names in repeats:
        lines.append(f"! {', '.join(names)} hold the same data: holding one out still trains on the other")
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
    failed = [o for o in outcomes.values() if o.first_error]
    if failed:
        print(f"first error: {failed[0].first_error}")
    if args.out:
        write_csv(args.out, axes, modes, outcomes)
        print(f"\nall combinations written to {args.out}")
    return 0


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
