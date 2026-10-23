"""Which way of picking a grid cell holds up on days the grid never saw?

usage (from the repo root): uv run python -m experiments.selection_rules [--jobs N] [--engine rust]
       uv run python -m experiments.selection_rules --data DIR --train 1 --test 2 --products A,B
           --grid make_edge=0,0.5,1,2 --grid take_edge=0,1,2 [--format F --bot FILE]

Each study grids two of one product's parameters on a training round, picks a cell by each RULE
from the training days alone, and scores the pick on the product's later days that repeat no
training day (Prosperity reuses days; compared as arena.grid.repeated_days does, repeats among the
test days counted once). The score is the pick's gain over the bot as is on those days, under
--match-trades all and worse, in the product's own PnL (each day holds only that product, which
gives the same PnL for products that don't follow or hedge another). Each study also runs reversed:
trained on the later rounds and tested on the first. Repeats within the training days count once.
P2's Starfruit and Amethysts were tried and left out: the later P2 rounds (6, 7) hold no market
trades, so passive quotes never fill there and every cell scores the same.

RULES:
  base        keep the baseline (gain 0 by definition)
  pnl         the best training PnL under all
  nbhd        the best mean over the cell and its grid neighbours (arena.grid's plateau measure)
  min day     the best worst training day
  worse       the best training PnL under worse
  both modes  the best of the smaller gain over the base across all and worse
  top-5 mean  each parameter averaged over the five best cells by PnL, snapped to the grid
  DSR gate    the best PnL cell if its DSR (as arena.grid computes it) is 0.95 or more, else the base
  SPA gate    the best of StepM's cells if SPA's p is under 5%, else the base
  SPA+worse   the same, among StepM's cells that also beat the base under worse
Two baselines: the bot as committed, whose settings were partly tuned on these very days (so it
starts ahead), and the template's DEFAULTS for the two gridded parameters, the position of a
product first seen on the day. The oracle (the best cell on the test days themselves) gives the
scale. Results go into IDEAS.md
("Selection rules on unseen days") and references/wiki/concepts/validation-and-overfitting.md.

With --data (the Arena's rounds, once two exist) each of --products is a study: the --grid axes
(each PARAM=V1,V2,...) trained on the --train days and tested on the --test days, and reversed.
"""

from __future__ import annotations

import argparse
import itertools
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from pathlib import Path

from arena import grid, rust
from arena.botfile import BotFile
from arena.cli import TEMPLATES, add_engine_argument, backtest, bot_module
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS, prosperity

TEMPLATE = "python/bots/template.py"
MODES = (TradeMatching.ALL, TradeMatching.WORSE)
STUDIES = {  # name: (data, training round, test rounds, product, {parameter: values})
    "Kelp": ("p3", ["1"], ["2", "3", "4", "5"], "KELP", {"make_edge": [0, 0.5, 1, 1.5, 2, 3], "take_edge": [0, 1, 2, 3]}),
    "Resin": ("p3", ["1"], ["2", "3", "4", "5"], "RAINFOREST_RESIN", {"make_edge": [1, 2, 3, 4], "take_edge": [0, 1, 2]}),
    "Osmium": ("p4", ["1"], ["2"], "ASH_COATED_OSMIUM", {"make_edge": [0, 0.5, 1, 2, 3], "smoothing": [0, 0.5, 0.7, 0.9, 0.95]}),
    "Pepper Root": ("p4", ["1"], ["2"], "INTARIAN_PEPPER_ROOT", {"make_edge": [0, 1, 2, 3], "skew": [0, 10, 20, 40]}),
}
for _name in list(STUDIES):  # the same grids the other way round: train on the later days, test on the first round
    _data, _train, _test, _product, _axes = STUDIES[_name]
    STUDIES[f"{_name} (reversed)"] = (_data, _test, _train, _product, _axes)
DEFAULTS = BotFile(Path(TEMPLATE), {"datamodel": prosperity.dm}, {}, False).load().DEFAULTS
RULES = ["base", "pnl", "nbhd", "min day", "worse", "both modes", "top-5 mean", "DSR gate", "SPA gate", "SPA+worse"]
_DAYS: dict = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)
_KEPT: dict = {}  # --engine rust: per study, the names of the training and test days days_for keeps
FORMAT = "prosperity"  # --data sets it, with STUDIES, TEMPLATE and DEFAULTS


def _init(engine: str, kept: dict | None = None, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    _KEPT.update(kept or {})
    globals().update(settings or {})


def _settings(args) -> dict:
    """The studies --data names: one per product, its --grid axes trained on --train and tested on --test."""
    bot = str(args.bot or TEMPLATES.get(args.format, TEMPLATE))
    axes = {axis.target: axis.values for axis in map(grid.parse_axis, args.grid)}  # PARAM=V1,V2,... or START..STOP[..STEP]
    if not (args.train and args.test and args.products and axes):
        raise ValueError("--data needs --train, --test, --products and at least one --grid")
    studies = {}
    for product in (p.strip() for p in args.products.split(",") if p.strip()):
        studies[product] = (args.data, list(args.train), list(args.test), product, axes)
        studies[f"{product} (reversed)"] = (args.data, list(args.test), list(args.train), product, axes)
    return {"STUDIES": studies, "TEMPLATE": bot, "FORMAT": args.format, "DEFAULTS": bot_module(bot, args.format).DEFAULTS}


def kept(name: str) -> tuple[str, tuple[list[str], list[str]]]:
    """The names of the days days_for keeps (it reads their books to drop repeats)."""
    train, test = days_for(name)
    return name, ([d.name for d in train], [d.name for d in test])


def _rust_days(name: str) -> tuple[list, list]:
    """days_for's days for Rust, which reads them from their CSVs (only the study's product): no Python load."""
    data, product = STUDIES[name][0], STUDIES[name][3]
    if FORMAT != "prosperity":  # exported once per process (arena.rust.day_file)
        return days_for(name)
    day = lambda n: rust.prosperity_day(data, *map(int, n.removeprefix("r").split("d")), [product])
    return tuple([day(n) for n in names] for names in _KEPT[name])


def only(day, product):
    """The day with one product's books, trades and marks."""
    ticks = [replace(t, books={product: t.books[product]} if product in t.books else {},
                     trades={product: t.trades.get(product, [])}, marks={k: v for k, v in t.marks.items() if k == product})
             for t in day.ticks]
    return replace(day, products=[product], limits={product: day.limits[product]}, ticks=ticks,
                   info={k: v for k, v in day.info.items() if k == product})


def days_for(name: str) -> tuple[list, list]:
    """The training days and the unseen test days, each holding only the study's product."""
    if name not in _DAYS:
        data, train, test, product, _ = STUDIES[name]
        fmt = FORMATS[FORMAT]
        directory = fmt.resolve_data_dir(data)
        train_days = [d for d in fmt.load_days(directory, train) if product in d.products]
        test_days = [d for d in fmt.load_days(directory, test) if product in d.products]
        training = {d.name for d in train_days}
        drop = set()
        for names, products in grid.repeated_days(train_days + test_days):
            if product in products:
                first = next((n for n in names if n in training), names[0])
                drop |= set(names) - {first}  # a repeat counts once, and a test day that repeats a training day not at all
        _DAYS[name] = ([only(d, product) for d in train_days if d.name not in drop],
                       [only(d, product) for d in test_days if d.name not in drop])
    return _DAYS[name]


def cells(name: str) -> list[dict]:
    product, axes = STUDIES[name][3], STUDIES[name][4]
    return [{f"PARAMS.{product}.{k}": v for k, v in zip(axes, values)} for values in itertools.product(*axes.values())]


def run(task: tuple[str, int]) -> tuple[tuple[str, int], dict]:
    """One cell (-1: the bot as is): PnL per day and mode on both sets, and the training blocks."""
    name, k = task
    product = STUDIES[name][3]
    overrides = {} if k < 0 else cells(name)[k]
    train, test = _rust_days(name) if ENGINE[0] == "rust" else days_for(name)
    out = {"train": {m: [] for m in MODES}, "test": {m: [] for m in MODES}, "fine": [], "coarse": []}
    for part, days in (("train", train), ("test", test)):
        for day in days:
            for mode in MODES:
                (result,) = backtest(day, [("you", TEMPLATE, overrides, False)], EngineConfig(trade_matching=mode), ENGINE[0], fields=("pnl",),
                                     format_name=FORMAT)
                series = result.pnl.get(product) or [0.0] * len(result.timestamps)
                out[part][mode].append(series[-1])
                if part == "train" and mode is TradeMatching.ALL:
                    out["fine"] += grid.block_pnl(series, len(series) // grid.FINE_TICKS)
                    out["coarse"] += grid.block_pnl(series, grid.blocks_per_day(len(days)))
    return task, out


def dsr(base: list[float], columns: list[list[float]], best: list[float]) -> float | None:
    gains = [[x - b for x, b in zip(c, base)] for c in {tuple(round(x, 6) for x in c): c for c in columns}.values()]
    mine = [x - b for x, b in zip(best, base)]
    sharpes = [statistics.fmean(g) / statistics.stdev(g) for g in gains if statistics.stdev(g) > 0]
    if len(sharpes) < 2 or statistics.stdev(mine) == 0:
        return None
    mean, sd = statistics.fmean(mine), statistics.pstdev(mine)
    skew = statistics.fmean(((x - mean) / sd) ** 3 for x in mine)
    kurtosis = statistics.fmean(((x - mean) / sd) ** 4 for x in mine)
    sharpe0 = grid.expected_max_sharpe(statistics.variance(sharpes), grid.independent_trials(gains))
    return grid.deflated_sharpe(mean / statistics.stdev(mine), sharpe0, len(mine), skew, kurtosis)


def default_cell(axes: dict) -> int | None:
    """The grid cell with the template's DEFAULTS for both parameters; None if the grid doesn't hold it."""
    values = tuple(DEFAULTS[k] for k in axes)
    cells = list(itertools.product(*axes.values()))
    return cells.index(values) if values in cells else None


def pick(axes: dict, base: dict, results: list[dict]) -> dict[str, int | None]:
    """Each rule's cell, from the training days only (None: the baseline). `axes` maps each
    parameter to its values, results are the cells in itertools.product order."""
    all_, worse = MODES
    shape = tuple(len(v) for v in axes.values())
    index = list(itertools.product(*(range(n) for n in shape)))
    pnl = {m: [sum(r["train"][m]) for r in results] for m in MODES}
    gain = {m: [p - sum(base["train"][m]) for p in pnl[m]] for m in MODES}

    def nbhd(k):
        at, around = index[k], [pnl[all_][k]]
        for axis, size in enumerate(shape):
            for step in (-1, 1):
                j = at[axis] + step
                if 0 <= j < size:
                    around.append(pnl[all_][index.index(at[:axis] + (j,) + at[axis + 1:])])
        return statistics.fmean(around)

    ks = range(len(results))
    best = max(ks, key=pnl[all_].__getitem__)
    out = {"base": None, "pnl": best, "nbhd": max(ks, key=nbhd), "min day": max(ks, key=lambda k: min(results[k]["train"][all_])),
           "worse": max(ks, key=pnl[worse].__getitem__), "both modes": max(ks, key=lambda k: min(gain[all_][k], gain[worse][k]))}
    top = sorted(ks, key=lambda k: -pnl[all_][k])[:5]
    snapped = tuple(min(range(n), key=lambda j, a=a, n=n: abs(list(axes.values())[a][j] - statistics.fmean(list(axes.values())[a][index[k][a]] for k in top)))
                    for a, n in enumerate(shape))
    out["top-5 mean"] = index.index(snapped)
    d = dsr(base["coarse"], [r["coarse"] for r in results], results[best]["coarse"])
    out["DSR gate"] = best if d is not None and d >= 0.95 else None
    columns, owners = [], []
    for k, r in enumerate(results):
        g = [x - b for x, b in zip(r["fine"], base["fine"])]
        if any(g):
            columns.append(g)
            owners.append(k)
    winners = []
    if columns:
        p = grid.spa(columns, grid.SPA_Q, grid.BOOTSTRAP)
        if p["c"] < grid.ALPHA:
            winners = [owners[j] for j in grid.stepm(columns, grid.SPA_Q, grid.BOOTSTRAP)]
    out["SPA gate"] = max(winners, key=pnl[all_].__getitem__) if winners else None
    holding = [k for k in winners if gain[worse][k] > 0]
    out["SPA+worse"] = max(holding, key=pnl[all_].__getitem__) if holding else None
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.selection_rules")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    group = parser.add_argument_group("the day's data", "studies on the Arena's rounds in place of the built-in Prosperity ones")
    group.add_argument("--data", help="a data folder, or p2 / p3 / p4")
    group.add_argument("--format", default="prosperity", choices=sorted(FORMATS), help="the data's format (default: prosperity)")
    group.add_argument("--bot", type=Path, help="the template file, written for that format")
    group.add_argument("--products", help="comma-separated: a study for each")
    group.add_argument("--train", nargs="+", help="the training day specs, e.g. 1")
    group.add_argument("--test", nargs="+", help="the test day specs, e.g. 2")
    group.add_argument("--grid", action="append", default=[], metavar="PARAM=V1,V2,...", help="an axis of each product's grid (repeatable)")
    args = parser.parse_args()
    settings = {}
    if args.data:
        try:
            settings = _settings(args)
        except ValueError as error:
            parser.error(str(error))
        globals().update(settings)
    elif args.format != "prosperity" or args.bot or args.products or args.train or args.test or args.grid:
        parser.error("--format, --bot, --products, --train, --test and --grid choose the day's data: give --data too")
    if args.engine == "rust":
        rust.require(args.allow_stale)
    tasks = [(name, k) for name in STUDIES for k in range(-1, len(cells(name)))]
    days = {}
    if args.engine == "rust" and FORMAT == "prosperity":  # each study's days loaded once, here, to find the repeats; the workers load nothing
        with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, None, settings)) as pool:
            days = dict(pool.map(kept, STUDIES))
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, days, settings)) as pool:
        done = dict(pool.map(run, tasks, chunksize=1))
    for baseline in ("committed", "defaults"):
        totals = {rule: {m: 0.0 for m in MODES} for rule in RULES}
        print(f"\nBaseline: the bot {'as committed' if baseline == 'committed' else 'with DEFAULTS for the two parameters'}. "
              "Gain over it on the unseen test days, in the product's PnL: all / worse. The pick is in brackets.\n")
        print("| Study (test days) | " + " | ".join(RULES) + " | oracle |")
        print("|---" * (len(RULES) + 2) + "|")
        for name in STUDIES:
            results = [done[(name, k)] for k in range(len(cells(name)))]
            if baseline == "defaults" and default_cell(STUDIES[name][4]) is None:
                defaults = ", ".join(f"{k} {DEFAULTS[k]}" for k in STUDIES[name][4])
                print(f"| {name}: the grid doesn't hold DEFAULTS' values ({defaults}), so there is no such baseline |")
                continue
            base = done[(name, -1)] if baseline == "committed" else results[default_cell(STUDIES[name][4])]
            picks = pick(STUDIES[name][4], base, results)
            axes = STUDIES[name][4]
            row = []
            for rule in RULES:
                k = picks[rule]
                g = {m: 0.0 if k is None else sum(results[k]["test"][m]) - sum(base["test"][m]) for m in MODES}
                for m in MODES:
                    totals[rule][m] += g[m]
                label = "base" if k is None else ",".join(str(v) for v in cells(name)[k].values())
                row.append(f"{g[MODES[0]]:+,.0f} / {g[MODES[1]]:+,.0f} ({label})")
            oracle = max(sum(r["test"][MODES[0]]) for r in results) - sum(base["test"][MODES[0]])
            print(f"| {name}: {', '.join(axes)} ({len(base['test'][MODES[0]])}) | " + " | ".join(row) + f" | {oracle:+,.0f} |")
        print("| **Total** | " + " | ".join(f"**{totals[r][MODES[0]]:+,.0f} / {totals[r][MODES[1]]:+,.0f}**" for r in RULES) + " | |")

if __name__ == "__main__":
    main()
