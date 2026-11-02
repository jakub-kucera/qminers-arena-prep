"""Fitting arena.sim to the day's data: a preset's parameters by simulated method of moments, then days to tune on.

usage (from the repo root): uv run python -m experiments.day.sim_fit                     # the controls: P3 round 1 Kelp, P4 round 1 Osmium
       uv run python -m experiments.day.sim_fit --data D --days 1 2 --format F --products A,B [--preset KELP] [--evals 150]
       uv run python -m experiments.day.sim_fit --data D --days 1 --products A --out data/fitted --generate 20   # days to grid on
       uv run python -m experiments.day.sim_fit --check                                  # recover a known spec first

Why: a grid on three downloaded days overfits them, and arena.sim can make as many days as we like,
but only of the markets its presets describe. Fitted to the download, its days are a tuning ground
that shares the download's book and flow (IDEAS.md, "Fitting arena.sim to the download").

Per product:
1. Moments, per data day and pooled, from arena.diagnose (MOMENTS: the spread, its share at one
   tick, the wall's size, the wall mid's reversion and jumps, the mid's lag-1 autocorrelation, the
   trades' rate, buy share and share inside the spread) and two of our own: the sd of the wall mid's
   one-tick change and the mean trade size. Prices are in the product's ticks; the simulator works
   in ticks of 1, so a download with another tick is fitted, and generated, in its ticks.
2. The start: each preset in STARTS, renamed to the product, given the data's limit, its opening
   wall mid and day mean, scored by the distance below; the nearest (or --preset) is the start.
3. Nelder-Mead over FITTED (positive parameters in logs, shares in logits, size ranges by a common
   factor) on the distance: the sum over moments of ((simulated - data) / scale)², the scale the
   moment's sd across the data's days or 5% of its value, whichever is larger (and at least a floor),
   each evaluation on the same --sim-days seeds (common random numbers, so the surface is smooth).
4. The fitted spec as arena.sim --spec overrides, and the moments: data, start, fitted.
With --out, --generate days of the fitted market are written there in the Prosperity layout, the
product under its own name: `arena.grid BOT 1 --data OUT` tunes on them.

--check makes three days from KELP with four parameters moved, fits from KELP, and prints the true
and the recovered values: the fit is worth trusting only where it recovers a known spec.
"""

from __future__ import annotations

import argparse
import math
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from arena import diagnose, sim
from arena.cli import add_dataset_arguments, dataset_from
from arena.formats import FORMATS

CONTROLS = [("p3", ["1"], ["KELP"]), ("p4", ["1"], ["ASH_COATED_OSMIUM"])]
STARTS = ["KELP", "RAINFOREST_RESIN", "SQUID_INK", "HYDROGEL_PACK", "LARGE_TICK"]
MOMENTS = {  # name: (arena.diagnose's key or our own, floor of its scale)
    "spread": ("spread_ticks_mean", 0.05),
    "one tick": ("at_one_tick", 0.01),
    "wall size": ("wall_size", 0.5),
    "tick vol": ("tick_vol", 0.01),
    "reversion": ("wall_reversion", 0.5),  # noisy on a random walk (0.7 to 1.7 from day to day): only a large gap counts
    "jumps": ("jump_share", 0.002),
    "mid AC1": ("mid_lag1_autocorr", 0.02),
    "trades/tick": ("trade_rate", 0.005),
    "trade size": ("trade_size", 0.1),
    "buys": ("buy_share", 0.01),
    "inside": ("inside_share", 0.01),
}
# (path in the ProductSpec, transform): "log" a positive number, "logit" a share, "scale" a (low, high) range
FITTED = [("fundamental.sd", "log"), ("fundamental.reversion", "log"), ("maker.half_spread", "log"), ("maker.size", "scale"),
          ("limit_traders.rate", "log"), ("limit_traders.offset", "scale"), ("noise.rate", "log"), ("noise.size", "scale"),
          ("value.rate", "log"), ("noise.buy_share", "logit")]
FLOORS = {"fundamental.sd": 0.01, "fundamental.reversion": 1e-4, "maker.half_spread": 0.5, "limit_traders.rate": 0.01,
          "noise.rate": 0.005, "value.rate": 0.002}
CHECK_TRUTH = {"fundamental.sd": 0.25, "maker.half_spread": 2.5, "noise.rate": 0.15, "limit_traders.rate": 1.6}


def moments(day, product: str) -> dict[str, float]:
    """One day's moments for one product (MOMENTS' keys)."""
    row = diagnose.diagnose([day])[product]
    tick = row["tick"] or 1
    walls = []
    for t in day.ticks:
        book = t.books.get(product)
        if book is not None and book.bids and book.asks:
            walls.append(book.wall_mid)
    changes = [(b - a) / tick for a, b in zip(walls, walls[1:])]
    sizes = [abs(x.quantity) for t in day.ticks for x in t.trades.get(product, [])]
    own = {"tick_vol": st.pstdev(changes) if len(changes) > 1 else 0.0, "trade_size": st.fmean(sizes) if sizes else 0.0,
           "trade_rate": len(sizes) / max(len(day.ticks), 1)}
    return {name: float(own.get(key, row.get(key)) or 0.0) for name, (key, _) in MOMENTS.items()}


def target(per_day: list[dict[str, float]]) -> tuple[dict[str, float], dict[str, float]]:
    """The data's moments pooled over its days, and each moment's scale."""
    mean = {k: st.fmean(m[k] for m in per_day) for k in MOMENTS}
    scale = {}
    for k, (_, floor) in MOMENTS.items():
        spread = st.pstdev([m[k] for m in per_day]) if len(per_day) > 1 else 0.0
        scale[k] = max(spread, 0.05 * abs(mean[k]), floor)
    return mean, scale


def distance(got: dict[str, float], mean: dict[str, float], scale: dict[str, float]) -> float:
    return sum(((got[k] - mean[k]) / scale[k]) ** 2 for k in MOMENTS)


def _get(spec: sim.ProductSpec, path: str):
    obj = spec
    for key in path.split("."):
        obj = getattr(obj, key)
    return obj


def _set(spec: sim.ProductSpec, path: str, value) -> sim.ProductSpec:
    head, key = path.split(".")
    return replace(spec, **{head: replace(getattr(spec, head), **{key: value})})


def encode(spec: sim.ProductSpec) -> list[float]:
    """The spec's FITTED parameters in the search's coordinates (a size range is factor 1: log 0)."""
    out = []
    for path, kind in FITTED:
        if kind == "scale":
            out.append(0.0)
        elif kind == "logit":
            p = min(max(_get(spec, path), 0.01), 0.99)
            out.append(math.log(p / (1 - p)))
        else:
            out.append(math.log(max(_get(spec, path), FLOORS[path])))
    return out


def decode(base: sim.ProductSpec, x: list[float]) -> sim.ProductSpec:
    spec = base
    for (path, kind), v in zip(FITTED, x):
        if kind == "scale":
            low, high = _get(base, path)
            f = math.exp(max(min(v, 3.0), -3.0))
            if isinstance(low, int):  # lots: whole and at least 1
                spec = _set(spec, path, (max(1, round(low * f)), max(1, round(high * f))))
            else:  # distances
                spec = _set(spec, path, (low * f, high * f))
        elif kind == "logit":
            spec = _set(spec, path, 1 / (1 + math.exp(-v)))
        else:
            spec = _set(spec, path, math.exp(max(min(v, 8.0), -12.0)))
    return spec


def simulate(spec: sim.ProductSpec, seeds: list[int], ticks: int) -> dict[str, float]:
    """The spec's moments averaged over one simulated day per seed."""
    market = sim.MarketSpec((spec,), ticks=ticks)
    per = [moments(sim.run(market, seed).day, spec.name) for seed in seeds]
    return {k: st.fmean(m[k] for m in per) for k in MOMENTS}


def placed(preset: str, product: str, limit: int, open_: float, level: float) -> sim.ProductSpec:
    """A preset as the product: its name and limit, opening at the data's first wall mid, reverting to its day mean."""
    spec = replace(sim.PRESETS[preset], name=product, limit=limit)
    return replace(spec, fundamental=replace(spec.fundamental, start=open_, level=level))


def nelder_mead(f, x0: list[float], step: float = 0.4, evals: int = 150) -> tuple[list[float], float, int]:
    """Minimises f from x0 (the standard reflection, expansion, contraction and shrink); returns (x, f(x), evaluations)."""
    n = len(x0)
    simplex = [x0] + [[x + (step if i == j else 0.0) for j, x in enumerate(x0)] for i in range(n)]
    values = [f(x) for x in simplex]
    used = len(simplex)
    while used < evals:
        order = sorted(range(n + 1), key=values.__getitem__)
        simplex, values = [simplex[i] for i in order], [values[i] for i in order]
        if values[-1] - values[0] < 1e-6:
            break
        centre = [sum(p[j] for p in simplex[:-1]) / n for j in range(n)]
        reflect = [c + (c - w) for c, w in zip(centre, simplex[-1])]
        fr = f(reflect)
        used += 1
        if fr < values[0]:
            expand = [c + 2 * (c - w) for c, w in zip(centre, simplex[-1])]
            fe = f(expand)
            used += 1
            simplex[-1], values[-1] = (expand, fe) if fe < fr else (reflect, fr)
        elif fr < values[-2]:
            simplex[-1], values[-1] = reflect, fr
        else:
            inside = [c + 0.5 * (w - c) for c, w in zip(centre, simplex[-1])]
            fc = f(inside)
            used += 1
            if fc < values[-1]:
                simplex[-1], values[-1] = inside, fc
            else:
                simplex = [simplex[0]] + [[b + 0.5 * (p - b) for b, p in zip(simplex[0], q)] for q in simplex[1:]]
                values = [values[0]] + [f(x) for x in simplex[1:]]
                used += n
    best = min(range(n + 1), key=values.__getitem__)
    return simplex[best], values[best], used


def fit(per_day: list[dict[str, float]], product: str, limit: int, open_: float, level: float, ticks: int,
        preset: str | None, sim_days: int, evals: int) -> dict:
    """Steps 2 and 3 for one product."""
    mean, scale = target(per_day)
    seeds = list(range(1, sim_days + 1))
    starts = {name: placed(name, product, limit, open_, level) for name in ([preset] if preset else STARTS)}
    scored = {name: distance(simulate(spec, seeds, ticks), mean, scale) for name, spec in starts.items()}
    chosen = min(scored, key=scored.get)
    base = starts[chosen]
    x, value, used = nelder_mead(lambda x: distance(simulate(decode(base, x), seeds, ticks), mean, scale), encode(base), evals=evals)
    spec = decode(base, x)
    return {"data": mean, "scale": scale, "starts": scored, "preset": chosen, "base": base, "spec": spec, "distance": value, "evals": used,
            "start_moments": simulate(base, seeds, ticks), "fitted_moments": simulate(spec, seeds, ticks)}


def overrides(spec: sim.ProductSpec, preset: str) -> list[str]:
    """The fitted spec as arena.sim --spec overrides on `--products preset`, its own name kept out."""
    out = [f"{preset}.limit={spec.limit}", f"{preset}.fundamental.start={spec.fundamental.start:g}",
           f"{preset}.fundamental.level={spec.fundamental.level:g}"]
    for path, kind in FITTED:
        value = _get(spec, path)
        out.append(f"{preset}.{path}={[round(v, 4) for v in value] if kind == 'scale' else round(value, 5)}")
    return out


def report(product: str, r: dict) -> None:
    starts = ", ".join(f"{name} {d:.0f}" for name, d in sorted(r["starts"].items(), key=lambda kv: kv[1]))
    print(f"\n{product}: start {r['preset']} (distances: {starts}); fitted distance {r['distance']:.1f} after {r['evals']} evaluations")
    print("| moment | data | its scale | start | fitted |")
    print("|---|---|---|---|---|")
    for k in MOMENTS:
        print(f"| {k} | {r['data'][k]:.4g} | {r['scale'][k]:.3g} | {r['start_moments'][k]:.4g} | {r['fitted_moments'][k]:.4g} |")
    print("fitted: " + " ".join(f"--spec {o}" for o in overrides(r["spec"], r["preset"])) + f"  (on --products {r['preset']})")


def _fit_product(job) -> tuple[str, dict]:
    data, fmt_name, specs, product, preset, sim_days, evals = job
    fmt = FORMATS[fmt_name]
    days = [d for d in fmt.load_days(fmt.resolve_data_dir(data), specs) if product in d.products]
    per_day = [moments(d, product) for d in days]
    walls = [t.books[product].wall_mid for d in days for t in d.ticks if product in t.books and t.books[product].bids and t.books[product].asks]
    first = next(t.books[product].wall_mid for t in days[0].ticks if product in t.books and t.books[product].bids and t.books[product].asks)
    return product, fit(per_day, product, days[0].limits.get(product, 50), first, st.fmean(walls), len(days[0].ticks), preset, sim_days, evals)


def check(sim_days: int, evals: int) -> dict:
    """Recover CHECK_TRUTH from three days of KELP with it set."""
    truth = sim.PRESETS["KELP"]
    for path, value in CHECK_TRUTH.items():
        truth = _set(truth, path, value)
    days = [sim.run(sim.MarketSpec((truth,)), seed).day for seed in (101, 102, 103)]
    per_day = [moments(d, "KELP") for d in days]
    r = fit(per_day, "KELP", 50, truth.fundamental.start, truth.fundamental.start, 10_000, "KELP", sim_days, evals)
    r["truth"] = truth
    return r


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.sim_fit")
    add_dataset_arguments(parser, bot=False)
    parser.add_argument("--preset", choices=sorted(sim.PRESETS), help="start from this preset (default: the nearest of STARTS)")
    parser.add_argument("--sim-days", type=int, default=2, help="simulated days per evaluation (default 2)")
    parser.add_argument("--evals", type=int, default=150, help="Nelder-Mead's evaluations per product (default 150)")
    parser.add_argument("--out", type=Path, help="write --generate days of each fitted product here (Prosperity layout, round 1)")
    parser.add_argument("--generate", type=int, default=20)
    parser.add_argument("--check", action="store_true", help="recover a known spec from KELP days instead")
    args = parser.parse_args(argv)
    if args.check:
        r = check(args.sim_days, args.evals)
        report("KELP, moved", r)
        print("| parameter | true | preset | recovered |")
        print("|---|---|---|---|")
        for path, _ in FITTED:
            print(f"| {path} | {_get(r['truth'], path)} | {_get(sim.PRESETS['KELP'], path)} | {_get(r['spec'], path)} |")
        return 0
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if dataset:
        fmt = FORMATS[dataset.format]
        products = list(dataset.products) or fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))[0].products
        jobs = [(dataset.data, dataset.format, list(dataset.days), p, args.preset, args.sim_days, args.evals) for p in products]
    else:
        jobs = [(data, "prosperity", specs, p, args.preset, args.sim_days, args.evals) for data, specs, products in CONTROLS for p in products]
    with ProcessPoolExecutor(min(len(jobs), 8)) as pool:
        fitted = list(pool.map(_fit_product, jobs))
    for product, r in fitted:
        report(product, r)
    if args.out:
        market = sim.MarketSpec(tuple(r["spec"] for _, r in fitted))
        for k in range(args.generate):
            sim.write_day(sim.run(market, 1000 + k), args.out, 1, k)
        print(f"\n{args.generate} days of the fitted market in {args.out} (round 1, days 0-{args.generate - 1}, seeds 1000+)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
