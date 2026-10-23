"""The template's level mode on P4 Hydrogel and Velvetfruit, scored on days it wasn't tuned on.

usage (from the repo root): uv run python -m experiments.p4_level_template [--jobs N] [--engine rust]
       uv run python -m experiments.p4_level_template --data DIR --days 3 4 --products A,B [--format F --bot FILE]

Two tests on the four distinct days of P4 rounds 3-4, one product at a time (the other is
switched off), default engine mode:

1. Nested leave-one-day-out. For each held-out day the level is the mean wall mid of the other
   three days, and level_band, clear_edge and level_exit are the grid's best by total PnL on
   those three days. The held-out day is scored with that choice. Nothing about the held-out day
   is used, so the total is an honest estimate (with four days, a noisy one).
2. With the settings chosen on all four days (CHOSEN, as committed on 2026-10-13), the level
   estimated in other ways: the mean of the other days (fixed, or blended with the day's own mean
   through level_weight) and the mean of the day so far ("day", no history).

With --data (the day's download) the products are --products (those arena.diagnose notes as
returning to a level), each traded alone with plain settings plus the level mode (limit from the
data); its grid is level_band at 0.5-2 times the product's mean daily sd of the wall mid,
clear_edge at one and two half spreads, level_exit None or 0; and part 2's settings are the grid's
best on all the days (in-sample), as CHOSEN was.
"""

import argparse
import itertools
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, dataset_from
from arena.engine import EngineConfig
from arena.formats import FORMATS
from experiments.p4_levels import day_means
from experiments.p4_vouchers import DAYS

FMT = FORMATS["prosperity"]
TEMPLATE = Path("python/bots/template.py")
GRIDS = {
    "HYDROGEL_PACK": {"level_band": [10, 15, 20, 30, 40, 50], "clear_edge": [4, 6, 8, 10], "level_exit": [None, 0]},
    "VELVETFRUIT_EXTRACT": {"level_band": [10, 15, 20, 25, 30, 40], "clear_edge": [2, 3, 5], "level_exit": [None, 0, 5]},
}
# The grid's best on all four days, pinned here so the results don't move with the template's PARAMS.
CHOSEN = {
    "HYDROGEL_PACK": {"level": 9994, "level_band": 30, "level_exit": 0, "clear_edge": 8},
    "VELVETFRUIT_EXTRACT": {"level": 5247, "level_band": 20, "level_exit": None, "clear_edge": 2},
}
WEIGHTS = [None, 1_000, 5_000, 20_000]  # level_weight with the other days' mean as the level
_DAYS = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)
DATA, SPECS, FORMAT, BASE = "p4", DAYS, "prosperity", None  # --data sets them; BASE: each product's plain settings


def _init(engine="python", settings=None):
    ENGINE[0] = engine
    globals().update(settings or {})
    globals()["FMT"] = FORMATS[FORMAT]
    if engine == "rust" and FORMAT == "prosperity":  # Rust reads each day's CSVs itself (_day): nothing to load here
        return
    _DAYS.update({d.name: d for d in FMT.load_days(FMT.resolve_data_dir(DATA), SPECS)})


def _day(name: str):
    return rust.named_day(DATA, name) if ENGINE[0] == "rust" and FORMAT == "prosperity" else _DAYS[name]


def _settings(dataset) -> dict:
    """The day's data: its products' plain settings and level grids, from the data's own spreads and sds."""
    fmt = FORMATS[dataset.format]
    days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
    base, grids = {}, {}
    for product in dataset.products:
        unit = _tick(days[0], product)
        walls = [[t.books[product].wall_mid / unit for t in day.ticks if product in t.books and t.books[product].wall_mid is not None] for day in days]
        spreads = [(b.asks[0][0] - b.bids[0][0]) / unit for day in days for t in day.ticks if (b := t.books.get(product)) and b.bids and b.asks]
        if not spreads or any(len(w) < 2 for w in walls):
            raise ValueError(f"{product}: no two-sided book on every day")
        sd, half = st.mean(st.pstdev(w) for w in walls), st.median(spreads) / 2
        base[product] = {"limit": days[0].limits[product], "fair": "wall_mid", "make_edge": 1}
        grids[product] = {"level_band": sorted({max(1, round(k * sd)) for k in (0.5, 1, 1.5, 2)}),
                          "clear_edge": sorted({max(1, round(k * half)) for k in (1, 2)}), "level_exit": [None, 0]}
    return {"DATA": dataset.data, "SPECS": list(dataset.days), "FORMAT": dataset.format, "TEMPLATE": Path(dataset.bot),
            "GRIDS": grids, "CHOSEN": {p: {} for p in grids}, "BASE": base}


def _tick(day, product: str) -> float:
    """The product's tick in the data's price unit (Day.info), 1 for Prosperity: the template works in ticks."""
    info = day.info.get(product, {})
    return round(info["tick"] / info["unit"]) if "tick" in info and "unit" in info else 1


def _means(days, products) -> dict[str, dict[str, float]]:
    """Each day's mean wall mid per product, in its ticks."""
    return {day.name: {p: st.mean(t.books[p].wall_mid / _tick(day, p) for t in day.ticks if p in t.books and t.books[p].wall_mid is not None)
                       for p in products} for day in days}


def _run(job):
    product, overrides, day_name = job
    if BASE:  # the day's data: the product alone, plain settings plus the level mode
        full = {f"PARAMS.{product}": {**BASE[product], **CHOSEN[product], **dict(overrides)}}
        (result,) = backtest(_day(day_name), [("you", TEMPLATE, full, False)], EngineConfig(), ENGINE[0], True, ("pnl",), FORMAT)
        return job, result.pnl[product][-1] if result.pnl.get(product) else 0.0
    other = next(p for p in GRIDS if p != product)
    chosen = {f"PARAMS.{product}.{k}": v for k, v in CHOSEN[product].items()}
    full = {f"PARAMS.{other}.fair": "fixed", **chosen, **{f"PARAMS.{product}.{k}": v for k, v in overrides}}
    (result,) = backtest(_day(day_name), [("you", TEMPLATE, full, False)], EngineConfig(), ENGINE[0], True, ("pnl",))
    return job, result.pnl[product][-1] if result.pnl.get(product) else 0.0


def _name(spec):
    rnd, d = spec.split("-")
    return f"r{rnd}d{d}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser)
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
        if dataset and not args.products:
            raise ValueError("--data needs --products: the ones arena.diagnose notes as returning to a level")
        settings = _settings(dataset) if dataset else {}
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    _init(settings=settings) if dataset else None
    if dataset:
        days = list(_DAYS.values()) or FORMATS[FORMAT].load_days(FORMATS[FORMAT].resolve_data_dir(DATA), SPECS)
        names, means = [d.name for d in days], _means(days, GRIDS)
        if len(names) < 2:
            parser.error("the held-out test needs two days or more")
        # The settings part 2 keeps: the grid's best on all the days, with their mean as the level (in-sample).
        jobs = [(product, (("level", st.mean(means[d][product] for d in names)), *zip(grid, values)), day)
                for product, grid in GRIDS.items() for values in itertools.product(*grid.values()) for day in names]
        with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
            found = dict(pool.map(_run, jobs, chunksize=4))
        for product, grid in GRIDS.items():
            level = st.mean(means[d][product] for d in names)
            best = max(itertools.product(*grid.values()), key=lambda v: sum(found[(product, (("level", level), *zip(grid, v)), d)] for d in names))
            CHOSEN[product] = {"level": level, **dict(zip(grid, best))}
        settings["CHOSEN"] = CHOSEN
    else:
        names = [_name(s) for s in DAYS]
        means = day_means(FMT.load_days(FMT.resolve_data_dir("p4"), DAYS))
    loo = {p: {d: st.mean(means[o][p] for o in names if o != d) for d in names} for p in GRIDS}

    jobs = []
    for product, grid in GRIDS.items():
        keys = list(grid)
        for test in names:  # one fold per held-out day: its level is the other days' mean
            for values in itertools.product(*grid.values()):
                overrides = (("level", loo[product][test]), *zip(keys, values))
                jobs += [(product, overrides, day) for day in names]
        for test in names:
            for weight in WEIGHTS:
                jobs.append((product, (("level", loo[product][test]), ("level_weight", weight)), test))
            jobs.append((product, (("level", "day"),), test))
        jobs += [(product, (), day) for day in names]  # CHOSEN as is
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        pnl = dict(pool.map(_run, jobs, chunksize=4))

    for product, grid in GRIDS.items():
        keys = list(grid)
        print(f"\n{product}")
        print("  1. nested leave-one-day-out: the held-out day's level and settings come from the other three days")
        total = 0.0
        for test in names:
            train = [d for d in names if d != test]
            level = loo[product][test]

            def score(values):
                overrides = (("level", level), *zip(keys, values))
                return sum(pnl[(product, overrides, d)] for d in train)

            best = max(itertools.product(*grid.values()), key=score)
            held = pnl[(product, (("level", level), *zip(keys, best)), test)]
            total += held
            chosen = ", ".join(f"{k} {v}" for k, v in zip(keys, best))
            print(f"     {test}: level {level:.1f}, {chosen}: held-out PnL {held / 1000:.1f}k (training days {score(best) / 1000:.1f}k)")
        print(f"     total over the held-out days {total / 1000:.1f}k")
        committed = [pnl[(product, (), d)] for d in names]
        print(f"     CHOSEN (tuned and levelled on all {'four' if not dataset else len(names)} days): {sum(committed) / 1000:.1f}k  "
              f"({' / '.join(f'{v / 1000:.1f}' for v in committed)})")

        print("  2. CHOSEN, with the level estimated differently (per day, then total)")
        for label, overrides_for in [
            *[(f"other days' mean, level_weight {w}", lambda d, w=w: (("level", loo[product][d]), ("level_weight", w))) for w in WEIGHTS],
            ("the day so far (\"day\")", lambda d: (("level", "day"),)),
        ]:
            values = [pnl[(product, overrides_for(d), d)] for d in names]
            print(f"     {label:<38} {sum(values) / 1000:>7.1f}k  ({' / '.join(f'{v / 1000:.1f}' for v in values)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
