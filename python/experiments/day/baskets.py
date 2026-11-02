"""Trading a basket's spread with the template, scored on days it wasn't tuned on.

usage (from the repo root): uv run python -m experiments.day.baskets [--jobs N] [--engine rust]
       uv run python -m experiments.day.baskets --data DIR --days 2 --basket B1=LEG1:6,LEG2:3 [--basket ...] [--format F --bot FILE]

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
4. Cartea et al.'s optimal bands for an Ornstein-Uhlenbeck spread (Algorithmic and High-Frequency
   Trading, section 11.3; literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6381-6566), in
   place of k sds: per held-out day, kappa and sigma from an AR(1) of the other days' spreads less
   each day's mean, c the basket's clear_edge (about half its spread), and an urgency rho of one
   over the ticks in a day (and a tenth and ten times it). Double-sided, the long entry is the short
   exit (11.4) and the short entry the long exit (11.2), so the template's flip between two bands is
   that strategy. The model discounts the spread's whole value, so a level far from 0 would skew
   the bands; a premium's level is arbitrary, so they are solved for the spread less its level
   (theta 0), which makes them symmetric: level as in part 2, level_band the long exit, level_exit
   None, no hedge.

With --data (the day's download) the baskets come from --basket (NAME=LEG:WEIGHT,...; a family
that sums to a constant is a basket with legs of weight -1), each product's limit from the data,
and each clear_edge about half its median spread.
"""

import argparse
import itertools
import math
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, dataset_from
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
URGENCY = (0.1, 1.0, 10.0)  # rho in units of one over the ticks in a day
_DAYS: dict = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)
FORMAT = "prosperity"  # --data sets it, with FMT, TEMPLATE and DATASETS


def _init(engine="python", settings=None):
    ENGINE[0] = engine
    globals().update(settings or {})
    globals()["FMT"] = FORMATS[FORMAT]
    if engine == "rust" and FORMAT == "prosperity":  # the workers' Rust reads each day's CSVs itself (_run): nothing to load
        return
    for name, d in DATASETS.items():
        _DAYS[name] = {day.name: day for day in FMT.load_days(FMT.resolve_data_dir(d["data"]), d["days"])}


def parse_basket(text: str) -> tuple[str, dict[str, float]]:
    """`NAME=LEG:WEIGHT,LEG:WEIGHT` (--basket) as (basket, {leg: weight})."""
    name, sep, legs = text.partition("=")
    try:
        weights = {leg.strip(): float(weight) for leg, weight in (part.split(":") for part in legs.split(","))}
    except ValueError:
        raise ValueError(f"--basket {text!r}: write NAME=LEG:WEIGHT,LEG:WEIGHT, e.g. PICNIC_BASKET2=CROISSANTS:4,JAMS:2") from None
    if not sep or not name.strip() or not weights:
        raise ValueError(f"--basket {text!r}: write NAME=LEG:WEIGHT,LEG:WEIGHT")
    return name.strip(), {leg: int(w) if w == int(w) else w for leg, w in weights.items()}


def _dataset_settings(dataset, baskets: list[str]) -> dict:
    """DATASETS for the day's data: the baskets from --basket, limits from the data, clear_edge half the median spread."""
    fmt = FORMATS[dataset.format]
    days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
    limits = {p: v for day in days for p, v in day.limits.items()}
    spreads: dict = {}
    for day in days:
        for tick in day.ticks:
            for product, book in tick.books.items():
                if book.bids and book.asks:
                    spreads.setdefault(product, []).append(book.asks[0][0] - book.bids[0][0])
    edge = {p: max(1, round(st.median(s) / 2)) for p, s in spreads.items()}
    parsed = dict(parse_basket(text) for text in baskets)
    missing = sorted({p for name, legs in parsed.items() for p in (name, *legs)} - set(limits))
    if missing:
        raise ValueError(f"not in the data: {', '.join(missing)}")
    legs = {leg for weights in parsed.values() for leg in weights}
    d = {"data": dataset.data, "days": list(dataset.days),
         "baskets": {name: (weights, limits[name], edge.get(name, 1)) for name, weights in parsed.items()},
         "legs": {leg: (limits[leg], edge.get(leg, 1)) for leg in sorted(legs)}}
    return {"DATASETS": {dataset.name: d}, "TEMPLATE": Path(dataset.bot), "FORMAT": dataset.format}


def spreads(day, basket, legs) -> list[float]:
    out = []
    for t in day.ticks:
        prices = [t.books[p].wall_mid if p in t.books else None for p in (basket, *legs)]
        if None not in prices:
            out.append(prices[0] - sum(w * x for w, x in zip(legs.values(), prices[1:])))
    return out


def ou_fit(series: list[list[float]]) -> tuple[float, float]:
    """kappa and sigma per tick of an Ornstein-Uhlenbeck process from an AR(1) of each day's series less its own mean."""
    pairs = []
    for s in series:
        m = st.fmean(s)
        pairs += [(a - m, b - m) for a, b in zip(s, s[1:])]
    xy, xx = sum(a * b for a, b in pairs), sum(a * a for a, _ in pairs)
    b = xy / xx
    residual = st.fmean((y - b * x) ** 2 for x, y in pairs)
    kappa = -math.log(b)
    return kappa, math.sqrt(residual * 2 * kappa / (1 - b * b))


def _integral(r: float, z: float, n: int = 4000) -> float:
    """∫_0^∞ u^(r-1) exp(z u - u²/2) du for r > 0, by Simpson's rule; the u^(r-1) pole is taken out
    for r < 1 (its part ∫_0^1 u^(r-1) du = 1/r)."""
    top = max(z, 0.0) + 12.0

    def simpson(f, a: float, b: float) -> float:
        h = (b - a) / n
        return h / 3 * (f(a) + f(b) + sum((4 if k % 2 else 2) * f(a + k * h) for k in range(1, n)))

    def g(u: float) -> float:
        return math.exp(z * u - u * u / 2)

    if r >= 1:
        return simpson(lambda u: u ** (r - 1) * g(u), 0.0, top)
    near = simpson(lambda u: u ** (r - 1) * (g(u) - 1) if u > 0 else 0.0, 0.0, 1.0) + 1 / r
    return near + simpson(lambda u: u ** (r - 1) * g(u), 1.0, max(top, 1.0))


def ou_bands(kappa: float, sigma: float, theta: float, c: float, rho: float) -> tuple[float, float]:
    """Cartea et al.'s double-sided triggers for an OU spread: (long entry, short entry), the short exit
    from (11.4) and the long exit from (11.2), which the book's table shows equal them."""
    a, r = math.sqrt(2 * kappa) / sigma, rho / kappa

    def long_exit(e: float) -> float:  # (e - c) F+'(e) - F+(e), F+(e) = I(r, a(e - theta))
        z = a * (e - theta)
        return (e - c) * a * _integral(r + 1, z) - _integral(r, z)

    def short_exit(e: float) -> float:  # (e + c) F-'(e) - F-(e), F-(e) = I(r, -a(e - theta))
        z = -a * (e - theta)
        return -(e + c) * a * _integral(r + 1, z) - _integral(r, z)

    def root(f, lo: float, hi: float) -> float:
        flo = f(lo)
        for _ in range(60):
            mid = (lo + hi) / 2
            if (f(mid) > 0) == (flo > 0):
                lo, flo = mid, f(mid)
            else:
                hi = mid
        return (lo + hi) / 2

    spread = sigma / math.sqrt(2 * kappa)  # the stationary sd
    long_from, short_from = max(c, theta), min(-c, theta)
    return root(short_exit, short_from - 12 * spread, short_from), root(long_exit, long_from, long_from + 12 * spread)


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
    day = rust.named_day(d["data"], day_name) if ENGINE[0] == "rust" and FORMAT == "prosperity" else _DAYS[name][day_name]
    (result,) = backtest(day, [("you", TEMPLATE, overrides(d, _thaw(setting)), False)], EngineConfig(), ENGINE[0], True,
                         ("pnl", "errors", "breaches"), FORMAT)
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
    add_dataset_arguments(parser, products=False)
    parser.add_argument("--basket", action="append", default=[], metavar="NAME=LEG:WEIGHT,...",
                        help="with --data: a basket and its legs (repeatable), e.g. PICNIC_BASKET2=CROISSANTS:4,JAMS:2")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
        if bool(dataset) != bool(args.basket):
            raise ValueError("--data and --basket go together: the baskets of the day's data")
        settings = _dataset_settings(dataset, args.basket) if dataset else {}
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    _init(settings=settings)
    stats, jobs, folds, ou = {}, [], {}, {}
    for name, d in DATASETS.items():
        names = list(_DAYS[name])
        stats[name] = premium_stats(_DAYS[name].values(), d)

        def fit(train):
            levels = {b: st.mean(stats[name][b][n][0] for n in train) for b in d["baskets"]}
            sds = {b: st.mean(stats[name][b][n][1] for n in train) for b in d["baskets"]}
            return levels, sds

        folds[name] = {test: fit([n for n in names if n != test]) for test in names}
        folds[name]["all"] = fit(names)
        for test in names:
            train = [_DAYS[name][n] for n in names if n != test]
            levels = folds[name][test][0]
            for m in URGENCY:
                fitted, bands = {}, {}
                for basket, (legs, _, clear_edge) in d["baskets"].items():
                    kappa, sigma = ou_fit([spreads(day, basket, legs) for day in train])
                    bands[basket] = ou_bands(kappa, sigma, 0.0, clear_edge, m / len(train[0].ticks))[1]
                    fitted[basket] = (kappa, sigma)
                ou[(name, test, m)] = (fitted, bands)
                jobs.append((name, _freeze((levels, bands, 1.0, None, 0.0)), test))
        for fold, (levels, sds) in folds[name].items():
            for values in itertools.product(*GRID.values()):
                setting = _freeze((levels, sds, *values))
                jobs += [(name, setting, day) for day in names]
                if fold != "all":
                    jobs.append((name, _freeze(("day", sds, *values)), fold))
        jobs += [(name, None, day) for day in names]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
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
        print("  4. Cartea et al.'s OU bands, fitted on the other days (in thousands; the band also in the other days' sds)")
        for m in URGENCY:
            held = 0.0
            for test in names:
                fitted, bands = ou[(name, test, m)]
                levels, sds = folds[name][test]
                baskets, legs, issues = pnl[(name, _freeze((levels, bands, 1.0, None, 0.0)), test)]
                held += baskets + legs
                read = "; ".join(f"{b} half-life {math.log(2) / k:.0f} ticks, sd {s / math.sqrt(2 * k):.1f}, band {bands[b]:.1f} ({bands[b] / sds[b]:.2f} sd)"
                                 for b, (k, s) in fitted.items())
                print(f"     rho {m:g}/day, {test}: {read}: {(baskets + legs) / 1000:.1f}" + (f"  ! {issues} errors or breaches" if issues else ""))
            print(f"     rho {m:g}/day: total over the held-out days {held / 1000:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
