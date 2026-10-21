"""The template's Velvetfruit level bet with its vouchers following, scored on days it wasn't tuned on.

usage (from the repo root): uv run python -m experiments.p4_vouchers_template [--jobs N] [--engine rust]

Velvetfruit trades its level mode, and VEV_4000-VEV_5500 follow its target (`follow_target`),
on the four distinct days of P4 rounds 3-4 (Hydrogel switched off), default engine mode.

1. Nested leave-one-day-out: for each held-out day, Velvetfruit's level is the other three days'
   mean wall mid, and level_band, clear_edge and the vouchers' max_cost_per_delta are the grid's
   best by total PnL (Velvetfruit plus vouchers) on those three days.
2. The template's PARAMS as committed (tuned on all four days), and with the level from the other
   days or from the day so far.
"""

import argparse
import itertools
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import backtest
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


def _init(engine="python"):
    ENGINE[0] = engine
    if engine == "rust":  # Rust reads each day's CSVs itself (_day): nothing to load here
        return
    _DAYS.update({d.name: d for d in FMT.load_days(FMT.resolve_data_dir("p4"), DAYS)})


def _day(name: str):
    return rust.named_day("p4", name) if ENGINE[0] == "rust" else _DAYS[name]


def _run(job):
    overrides, day_name = job
    bots = [("you", TEMPLATE, {"PARAMS.HYDROGEL_PACK.fair": "fixed", **dict(overrides)}, False)]
    (result,) = backtest(_day(day_name), bots, EngineConfig(), ENGINE[0], True, ("pnl",))
    pnl = {p: s[-1] for p, s in result.pnl.items() if s}
    return job, (pnl.get(UNDERLYING, 0.0), sum(v for p, v in pnl.items() if p.startswith("VEV_")))


def _name(spec):
    rnd, d = spec.split("-")
    return f"r{rnd}d{d}"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args(argv)
    if args.engine == "rust":
        rust.build()
    names = [_name(s) for s in DAYS]
    means = day_means(FMT.load_days(FMT.resolve_data_dir("p4"), DAYS))
    loo = {d: st.mean(means[o][UNDERLYING] for o in names if o != d) for d in names}
    level = f"PARAMS.{UNDERLYING}.level"

    jobs = []
    for test in names:
        for values in itertools.product(*GRID.values()):
            jobs += [(((level, loo[test]), *zip(GRID, values)), day) for day in names]
        jobs += [(((level, loo[test]),), test), (((level, "day"),), test)]
    jobs += [((), day) for day in names]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        pnl = dict(pool.map(_run, jobs, chunksize=4))

    def total(job):
        return sum(pnl[job])

    print("1. nested leave-one-day-out (Velvetfruit + vouchers, thousands)")
    held_out = [0.0, 0.0]
    for test in names:
        train = [d for d in names if d != test]
        best = max(itertools.product(*GRID.values()),
                   key=lambda values: sum(total((((level, loo[test]), *zip(GRID, values)), d)) for d in train))
        under, vouchers = pnl[(((level, loo[test]), *zip(GRID, best)), test)]
        held_out[0] += under
        held_out[1] += vouchers
        chosen = ", ".join(f"{k.split('.')[-1]} {v}" for k, v in zip(GRID, best))
        print(f"   {test}: level {loo[test]:.1f}, {chosen}: Velvetfruit {under / 1000:.1f}, vouchers {vouchers / 1000:.1f}")
    print(f"   total over the held-out days: Velvetfruit {held_out[0] / 1000:.1f}, vouchers {held_out[1] / 1000:.1f}, "
          f"together {sum(held_out) / 1000:.1f}")

    print("2. PARAMS as committed, by day (Velvetfruit + vouchers)")
    for label, job_for in [
        ("level 5247, all four days", lambda d: ((), d)),
        ("level from the other days", lambda d: (((level, loo[d]),), d)),
        ("the day so far (\"day\")", lambda d: (((level, "day"),), d)),
    ]:
        rows = [pnl[job_for(d)] for d in names]
        print(f"   {label:<28} together {sum(map(sum, rows)) / 1000:>7.1f}  (Velvetfruit {sum(r[0] for r in rows) / 1000:.1f}, "
              f"vouchers {sum(r[1] for r in rows) / 1000:.1f}; days {' / '.join(f'{sum(r) / 1000:.1f}' for r in rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
