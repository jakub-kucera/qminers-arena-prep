"""Trading a basket's spread with the template, scored on days it wasn't tuned on.

usage (from the repo root): uv run python -m experiments.baskets [--jobs N] [--engine rust]

Datasets: P3 round 2 (PICNIC_BASKET1 = 6 Croissants + 3 Jams + 1 Djembes, PICNIC_BASKET2 =
4 Croissants + 2 Jams) and P2 round 3 (GIFT_BASKET = 4 Chocolate + 6 Strawberries + 1 Roses),
three days each, default engine mode. Only the baskets and their legs are traded.

Each basket trades its spread (its wall mid less the legs' weighted wall mids) with the
template's `basket` mode: the full limit against a move of level_band from the usual spread
(level). Baskets and hedging legs only trade toward their targets (make_size 0: resting quotes on
the baskets were picked off under --resting). The legs, with `hedge`, hold -weight * hedge_ratio
per basket held. clear_edge is about half of each product's spread.

1. Premium statistics per day (mean, sd, the open).
2. Nested leave-one-day-out: for each held-out day, the level is the mean spread of the other two
   days and level_band is k times their mean sd; k, level_exit and hedge_ratio are the grid's best
   by total PnL on those two days. The total over the held-out days is the honest number.
3. For comparison, on the same days: plain market making on the baskets and legs (the template
   with fair wall_mid, make_edge 1), the best setting chosen on all three days (in-sample), and
   the held-out settings with the level from the day so far ("day").
"""

import argparse
import itertools
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import add_engine_argument, backtest
from arena.engine import EngineConfig
from arena.formats import FORMATS

FMT = FORMATS["prosperity"]
TEMPLATE = Path("python/bots/template.py")
DATASETS = {
    "P3 round 2": {
        "data": "p3",
        "days": ["2"],
        # basket -> (legs and weights, limit, clear_edge)
        "baskets": {
            "PICNIC_BASKET1": ({"CROISSANTS": 6, "JAMS": 3, "DJEMBES": 1}, 60, 5),
            "PICNIC_BASKET2": ({"CROISSANTS": 4, "JAMS": 2}, 100, 3),
        },
        "legs": {"CROISSANTS": (250, 1), "JAMS": (350, 1), "DJEMBES": (60, 1)},  # (limit, clear_edge)
    },
    "P2 round 3": {
        "data": "p2",
        "days": ["3"],
        "baskets": {"GIFT_BASKET": ({"CHOCOLATE": 4, "STRAWBERRIES": 6, "ROSES": 1}, 60, 6)},
        "legs": {"CHOCOLATE": (250, 1), "STRAWBERRIES": (350, 1), "ROSES": (60, 1)},
    },
}
GRID = {"k": [0.5, 0.75, 1.0, 1.5, 2.0], "level_exit": [None, 0], "hedge_ratio": [0.0, 0.5, 1.0]}
_DAYS: dict = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine="python"):
    ENGINE[0] = engine
    if engine == "rust":  # the workers' Rust reads each day's CSVs itself (_run): nothing to load
        return
    for name, d in DATASETS.items():
        _DAYS[name] = {day.name: day for day in FMT.load_days(FMT.resolve_data_dir(d["data"]), d["days"])}


def spreads(day, basket, legs) -> list[float]:
    out = []
    for t in day.ticks:
        prices = [t.books[p].wall_mid if p in t.books else None for p in (basket, *legs)]
        if None not in prices:
            out.append(prices[0] - sum(w * x for w, x in zip(legs.values(), prices[1:])))
    return out


def premium_stats(days, d) -> dict:
    """basket -> day -> (mean, sd, open) of its spread."""
    return {
        basket: {day.name: (st.mean(s), st.pstdev(s), s[0]) for day in days for s in [spreads(day, basket, legs)]}
        for basket, (legs, _, _) in d["baskets"].items()
    }


def overrides(d, setting) -> dict:
    """setting: None for plain market making, else (levels, sds, k, level_exit, hedge_ratio)."""
    out = {}
    for basket, (legs, limit, clear_edge) in d["baskets"].items():
        if setting is None:
            out[f"PARAMS.{basket}"] = {"limit": limit, "fair": "wall_mid", "make_edge": 1}
            continue
        levels, sds, k, level_exit, hedge_ratio = setting
        level = levels if levels == "day" else levels[basket]
        out[f"PARAMS.{basket}"] = {
            "limit": limit, "fair": "wall_mid", "make_size": 0, "basket": legs, "level": level,
            "level_band": k * sds[basket], "level_exit": level_exit, "hedge_ratio": hedge_ratio, "clear_edge": clear_edge,
        }
    for leg, (limit, clear_edge) in d["legs"].items():
        if setting is None:
            out[f"PARAMS.{leg}"] = {"limit": limit, "fair": "wall_mid", "make_edge": 1}
        else:
            out[f"PARAMS.{leg}"] = {"limit": limit, "fair": "wall_mid", "hedge": True, "clear_edge": clear_edge,
                                    "take_edge": 10**6, "make_size": 0}
    return out


def _run(job):
    name, setting, day_name = job
    d = DATASETS[name]
    day = rust.named_day(d["data"], day_name) if ENGINE[0] == "rust" else _DAYS[name][day_name]
    (result,) = backtest(day, [("you", TEMPLATE, overrides(d, _thaw(setting)), False)], EngineConfig(), ENGINE[0], True, ("pnl", "errors", "breaches"))
    pnl = {p: s[-1] for p, s in result.pnl.items() if s}
    baskets = sum(pnl.get(b, 0.0) for b in d["baskets"])
    legs = sum(pnl.get(leg, 0.0) for leg in d["legs"])
    return job, (baskets, legs, len(result.limit_breaches) + len(result.errors))


# Settings go through the process pool as hashable tuples.
def _freeze(setting):
    if setting is None:
        return None
    levels, sds, *rest = setting
    return (levels if levels == "day" else tuple(sorted(levels.items())), tuple(sorted(sds.items())), *rest)


def _thaw(setting):
    if setting is None:
        return None
    levels, sds, *rest = setting
    return (levels if levels == "day" else dict(levels), dict(sds), *rest)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    args = parser.parse_args(argv)
    if args.engine == "rust":
        rust.require(args.allow_stale)
    _init()
    stats, jobs, folds = {}, [], {}
    for name, d in DATASETS.items():
        names = list(_DAYS[name])
        stats[name] = premium_stats(_DAYS[name].values(), d)

        def fit(train):
            levels = {b: st.mean(stats[name][b][n][0] for n in train) for b in d["baskets"]}
            sds = {b: st.mean(stats[name][b][n][1] for n in train) for b in d["baskets"]}
            return levels, sds

        folds[name] = {test: fit([n for n in names if n != test]) for test in names}
        folds[name]["all"] = fit(names)
        for fold, (levels, sds) in folds[name].items():
            for values in itertools.product(*GRID.values()):
                setting = _freeze((levels, sds, *values))
                jobs += [(name, setting, day) for day in names]
                if fold != "all":
                    jobs.append((name, _freeze(("day", sds, *values)), fold))
        jobs += [(name, None, day) for day in names]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        pnl = dict(pool.map(_run, jobs, chunksize=4))

    for name, d in DATASETS.items():
        names = list(_DAYS[name])
        print(f"\n{name}")
        print("  1. the spread per day: mean, sd, open")
        for basket in d["baskets"]:
            row = "  ".join(f"{n} {m:.1f} / {s:.1f} / {o:.1f}" for n, (m, s, o) in stats[name][basket].items())
            print(f"     {basket:<15} {row}")

        def total(levels_sds, values, days):
            setting = _freeze((*levels_sds, *values))
            return sum(sum(pnl[(name, setting, n)][:2]) for n in days)

        print("  2. nested leave-one-day-out (baskets + legs, in thousands)")
        held, held_day = 0.0, 0.0
        for test in names:
            train = [n for n in names if n != test]
            best = max(itertools.product(*GRID.values()), key=lambda values: total(folds[name][test], values, train))
            baskets, legs, issues = pnl[(name, _freeze((*folds[name][test], *best)), test)]
            day_mode = pnl[(name, _freeze(("day", folds[name][test][1], *best)), test)]
            held += baskets + legs
            held_day += day_mode[0] + day_mode[1]
            chosen = ", ".join(f"{k} {v}" for k, v in zip(GRID, best))
            levels = ", ".join(f"{b} {v:.1f}" for b, v in folds[name][test][0].items())
            print(f"     {test}: level {levels}; {chosen}: baskets {baskets / 1000:.1f}, legs {legs / 1000:.1f}"
                  + (f"  ! {issues} errors or breaches" if issues else ""))
        print(f"     total over the held-out days {held / 1000:.1f}; with the level from the day so far {held_day / 1000:.1f}")

        best_all = max(itertools.product(*GRID.values()), key=lambda values: total(folds[name]["all"], values, names))
        in_sample = [sum(pnl[(name, _freeze((*folds[name]["all"], *best_all)), n)][:2]) for n in names]
        plain = [sum(pnl[(name, None, n)][:2]) for n in names]
        chosen = ", ".join(f"{k} {v}" for k, v in zip(GRID, best_all))
        print(f"  3. in-sample best ({chosen}): {sum(in_sample) / 1000:.1f}  ({' / '.join(f'{v / 1000:.1f}' for v in in_sample)})")
        print(f"     plain market making on the same products: {sum(plain) / 1000:.1f}  ({' / '.join(f'{v / 1000:.1f}' for v in plain)})")
        for ratio in GRID["hedge_ratio"]:
            best = max((v for v in itertools.product(*GRID.values()) if v[2] == ratio), key=lambda values: total(folds[name]["all"], values, names))
            legs = sum(pnl[(name, _freeze((*folds[name]["all"], *best)), n)][1] for n in names)
            print(f"     in-sample best with hedge_ratio {ratio} ({', '.join(f'{k} {v}' for k, v in zip(GRID, best))}): "
                  f"{total(folds[name]['all'], best, names) / 1000:.1f}, of which legs {legs / 1000:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
