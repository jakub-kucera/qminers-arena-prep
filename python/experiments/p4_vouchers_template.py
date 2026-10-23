"""The template's Velvetfruit level bet with its vouchers following, scored on days it wasn't tuned on.

usage (from the repo root): uv run python -m experiments.p4_vouchers_template [--jobs N] [--engine rust]
       uv run python -m experiments.p4_vouchers_template --data DIR --days 3 4 --underlying U --prefix U_OPT_ [--format F --bot FILE]

Velvetfruit trades its level mode, and VEV_4000-VEV_5500 follow its target (`follow_target`),
on the four distinct days of P4 rounds 3-4 (Hydrogel switched off), default engine mode.

1. Nested leave-one-day-out: for each held-out day, Velvetfruit's level is the other three days'
   mean wall mid, and level_band, clear_edge and the vouchers' max_cost_per_delta are the grid's
   best by total PnL (Velvetfruit plus vouchers) on those three days.
2. The template's PARAMS as committed (tuned on all four days), and with the level from the other
   days or from the day so far.

With --data (the day's download) the underlying and its options (named --prefix plus a strike)
get whole PARAMS entries: the underlying plain settings plus the level mode, each option following
it, taking only, clear_edge about half its spread, limits from the data. The grid's level_band is
0.5-2 times the underlying's mean daily sd, clear_edge one and two half spreads; part 2's
"committed" row is then the plain market maker with no level bet.
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
UNDERLYING = "VELVETFRUIT_EXTRACT"
GRID = {
    f"PARAMS.{UNDERLYING}.level_band": [15, 20, 25, 30, 40],
    f"PARAMS.{UNDERLYING}.clear_edge": [2, 3],
    "DEFAULTS.max_cost_per_delta": [5, 12, 20],
}
_DAYS = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)
NAME = "Velvetfruit"  # the underlying as the tables name it
DATA, SPECS, FORMAT, PREFIX, ENTRIES = "p4", DAYS, "prosperity", "VEV_", None  # --data sets them; ENTRIES: whole PARAMS entries


def _init(engine="python", settings=None):
    ENGINE[0] = engine
    globals().update(settings or {})
    globals()["FMT"] = FORMATS[FORMAT]
    if engine == "rust" and FORMAT == "prosperity":  # Rust reads each day's CSVs itself (_day): nothing to load here
        return
    _DAYS.update({d.name: d for d in FMT.load_days(FMT.resolve_data_dir(DATA), SPECS)})


def _day(name: str):
    return rust.named_day(DATA, name) if ENGINE[0] == "rust" and FORMAT == "prosperity" else _DAYS[name]


def _tick(day, product: str) -> float:
    info = day.info.get(product, {})
    return round(info["tick"] / info["unit"]) if "tick" in info and "unit" in info else 1


def _settings(dataset, underlying: str, prefix: str) -> dict:
    fmt = FORMATS[dataset.format]
    days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
    options = sorted({p for day in days for p in day.products if p.startswith(prefix) and p.removeprefix(prefix).isdigit()},
                     key=lambda p: int(p.removeprefix(prefix)))
    if underlying not in days[0].products or not options:
        raise ValueError(f"no {underlying} or no options named {prefix}<strike> in the data")

    def stats(product):
        unit = _tick(days[0], product)
        walls = [[t.books[product].wall_mid / unit for t in day.ticks if product in t.books and t.books[product].wall_mid is not None] for day in days]
        spreads = [(b.asks[0][0] - b.bids[0][0]) / unit for day in days for t in day.ticks if (b := t.books.get(product)) and b.bids and b.asks]
        return st.mean(st.pstdev(w) for w in walls if len(w) > 1), st.median(spreads) / 2 if spreads else 1

    sd, half = stats(underlying)
    entries = {underlying: {"limit": days[0].limits[underlying], "fair": "wall_mid", "make_edge": 1}}
    for option in options:
        entries[option] = {"limit": days[0].limits[option], "fair": "wall_mid", "follow": underlying, "strike": int(option.removeprefix(prefix)),
                           "clear_edge": max(1, round(stats(option)[1])), "take_edge": 10**6, "make_size": 0}
    grid = {f"PARAMS.{underlying}.level_band": sorted({max(1, round(k * sd)) for k in (0.5, 1, 1.5, 2)}),
            f"PARAMS.{underlying}.clear_edge": sorted({max(1, round(k * half)) for k in (1, 2)}),
            "DEFAULTS.max_cost_per_delta": [5, 12, 20]}
    return {"DATA": dataset.data, "SPECS": list(dataset.days), "FORMAT": dataset.format, "TEMPLATE": Path(dataset.bot),
            "UNDERLYING": underlying, "PREFIX": prefix, "GRID": grid, "ENTRIES": entries}


def _run(job):
    overrides, day_name = job
    if ENTRIES:  # whole entries, then the job's settings
        bots = [("you", TEMPLATE, {**{f"PARAMS.{p}": dict(entry) for p, entry in ENTRIES.items()}, **dict(overrides)}, False)]
    else:
        bots = [("you", TEMPLATE, {"PARAMS.HYDROGEL_PACK.fair": "fixed", **dict(overrides)}, False)]
    (result,) = backtest(_day(day_name), bots, EngineConfig(), ENGINE[0], True, ("pnl",), FORMAT)
    pnl = {p: s[-1] for p, s in result.pnl.items() if s}
    return job, (pnl.get(UNDERLYING, 0.0), sum(v for p, v in pnl.items() if p.startswith(PREFIX)))


def _name(spec):
    rnd, d = spec.split("-")
    return f"r{rnd}d{d}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser, products=False)
    parser.add_argument("--underlying", help="with --data: the product whose level the options follow")
    parser.add_argument("--prefix", help="with --data: the options' common name; the strike is the number after it")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
        if dataset and not (args.underlying and args.prefix):
            raise ValueError("--data needs --underlying and --prefix")
        settings = _settings(dataset, args.underlying, args.prefix) if dataset else {}
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    if dataset:
        _init(settings=settings)
        days = list(_DAYS.values()) or FMT.load_days(FMT.resolve_data_dir(DATA), SPECS)
        names = [d.name for d in days]
        means = {d.name: {UNDERLYING: st.mean(t.books[UNDERLYING].wall_mid / _tick(d, UNDERLYING) for t in d.ticks
                                               if UNDERLYING in t.books and t.books[UNDERLYING].wall_mid is not None)} for d in days}
        if len(names) < 2:
            parser.error("the held-out test needs two days or more")
    else:
        names = [_name(s) for s in DAYS]
        means = day_means(FMT.load_days(FMT.resolve_data_dir("p4"), DAYS))
    loo = {d: st.mean(means[o][UNDERLYING] for o in names if o != d) for d in names}
    globals()["NAME"] = "Velvetfruit" if not dataset else UNDERLYING
    level = f"PARAMS.{UNDERLYING}.level"

    jobs = []
    for test in names:
        for values in itertools.product(*GRID.values()):
            jobs += [(((level, loo[test]), *zip(GRID, values)), day) for day in names]
        jobs += [(((level, loo[test]),), test), (((level, "day"),), test)]
    jobs += [((), day) for day in names]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        pnl = dict(pool.map(_run, jobs, chunksize=4))

    def total(job):
        return sum(pnl[job])

    print(f"1. nested leave-one-day-out ({NAME} + vouchers, thousands)")
    held_out = [0.0, 0.0]
    for test in names:
        train = [d for d in names if d != test]
        best = max(itertools.product(*GRID.values()),
                   key=lambda values: sum(total((((level, loo[test]), *zip(GRID, values)), d)) for d in train))
        under, vouchers = pnl[(((level, loo[test]), *zip(GRID, best)), test)]
        held_out[0] += under
        held_out[1] += vouchers
        chosen = ", ".join(f"{k.split('.')[-1]} {v}" for k, v in zip(GRID, best))
        print(f"   {test}: level {loo[test]:.1f}, {chosen}: {NAME} {under / 1000:.1f}, vouchers {vouchers / 1000:.1f}")
    print(f"   total over the held-out days: {NAME} {held_out[0] / 1000:.1f}, vouchers {held_out[1] / 1000:.1f}, "
          f"together {sum(held_out) / 1000:.1f}")

    print(f"2. PARAMS as committed, by day ({NAME} + vouchers)")
    for label, job_for in [
        ("level 5247, all four days" if not dataset else "no level bet (plain market making)", lambda d: ((), d)),
        ("level from the other days", lambda d: (((level, loo[d]),), d)),
        ("the day so far (\"day\")", lambda d: (((level, "day"),), d)),
    ]:
        rows = [pnl[job_for(d)] for d in names]
        print(f"   {label:<28} together {sum(map(sum, rows)) / 1000:>7.1f}  ({NAME} {sum(r[0] for r in rows) / 1000:.1f}, "
              f"vouchers {sum(r[1] for r in rows) / 1000:.1f}; days {' / '.join(f'{sum(r) / 1000:.1f}' for r in rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
