"""The template's `skew` from GLFT's closed form, per product, against the committed setting.

usage (from the repo root): uv run python -m experiments.glft_skew [--jobs N] [--engine rust]

Guéant, Lehalle & Fernandez-Tapia's stationary quotes shift by c2 per unit of inventory, with
c2 = sqrt(sigma^2 gamma / (2 k A) x (1 + gamma/k)^(1 + k/gamma))
(literature_md/dealing-with-inventory-risk/dealing-with-inventory-risk.md:225-229, p. 11, checked
against the PDF). The template's `make` shifts both quotes by skew x position / limit, so the
theory's value is skew = c2 x limit (references/wiki/concepts/optimal-quoting-models.md).

Per product, on the data the template is tuned on (one tick = one time unit):
  1. sigma: the standard deviation of one-tick changes of the wall mid (the fair value, not the
     mid, as the wiki's recipe says);
  2. A and k: the chance per tick that a quote delta from the wall mid would be reached by a
     market trade (at its price or beyond, either side, averaged), fitted as A exp(-k delta) by
     least squares on log rate over the deltas seen on at least 1% of ticks. The fit's R^2 says
     whether the exponential model applies (the wiki: if log rate isn't linear, it doesn't);
  3. for each gamma in GAMMAS, the theory's skew, and the template's PnL with it, against the
     committed skew, under --match-trades all and worse.
"""

from __future__ import annotations

import argparse
import math
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import backtest as run_backtest
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS

FMT = FORMATS["prosperity"]
TEMPLATE = Path("bots/template.py")
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine
PRODUCTS = {  # product: (data, days)
    "AMETHYSTS": ("p2", ["1"]),
    "STARFRUIT": ("p2", ["1"]),
    "RAINFOREST_RESIN": ("p3", ["1"]),
    "KELP": ("p3", ["1"]),
    "ASH_COATED_OSMIUM": ("p4", ["1", "2"]),
}
GAMMAS = (0.001, 0.01, 0.1, 1.0)
MODES = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE)}


def _days(product):
    data, days = PRODUCTS[product]
    return FMT.load_days(FMT.resolve_data_dir(data), days)


def measure(product: str) -> dict:
    steps, reach, ticks = [], {}, 0
    for day in _days(product):
        last = None
        for tick in day.ticks:
            book = tick.books.get(product)
            wall = book.wall_mid if book is not None else None
            if wall is None:
                continue
            if last is not None:
                steps.append(wall - last)
            last = wall
            ticks += 1
            far = {1: 0.0, -1: 0.0}  # the farthest trade beyond the wall mid on each side this tick
            for trade in tick.trades.get(product, []):
                side = 1 if trade.price > wall else -1 if trade.price < wall else 0
                if side:
                    far[side] = max(far[side], abs(trade.price - wall))
            for distance in far.values():
                for delta in range(1, math.floor(distance) + 1):
                    reach[delta] = reach.get(delta, 0) + 0.5  # per side, averaged over the two
    rates = {d: n / ticks for d, n in sorted(reach.items()) if n / ticks >= 0.01}
    xs, ys = list(rates), [math.log(r) for r in rates.values()]
    slope, intercept = st.linear_regression(xs, ys) if len(xs) >= 2 else (float("nan"), float("nan"))
    fitted = [intercept + slope * x for x in xs]
    ss = sum((y - st.mean(ys)) ** 2 for y in ys)
    r2 = 1 - sum((y - f) ** 2 for y, f in zip(ys, fitted)) / ss if ss else float("nan")
    return {"sigma": st.pstdev(steps), "A": math.exp(intercept), "k": -slope, "r2": r2, "rates": rates}


def c2(sigma: float, A: float, k: float, gamma: float) -> float:
    return math.sqrt(sigma**2 * gamma / (2 * k * A) * (1 + gamma / k) ** (1 + k / gamma))


def backtest(job: tuple[str, float | None, str]) -> tuple[tuple, float]:
    product, skew, mode = job
    overrides = {} if skew is None else {f"PARAMS.{product}.skew": skew}
    pnl = 0.0
    for day in _days(product):
        (result,) = run_backtest(day, [("you", TEMPLATE, overrides, False)], MODES[mode], ENGINE[0], fields=("pnl",))
        pnl += result.pnl[product][-1] if result.pnl.get(product) else 0.0
    return job, pnl


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.glft_skew")
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.build()
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        fits = dict(zip(PRODUCTS, pool.map(measure, PRODUCTS)))
        limits = {p: FMT.LIMITS[p] for p in PRODUCTS}
        skews = {p: {g: c2(f["sigma"], f["A"], f["k"], g) * limits[p] for g in GAMMAS} for p, f in fits.items()}
        jobs = [(p, s, m) for p in PRODUCTS for s in [None, *skews[p].values()] for m in MODES]
        pnl = dict(pool.map(backtest, jobs))

    print("Per product: sigma (wall mid, per tick), and the fit of the chance per tick that a quote delta from the wall mid is reached.\n")
    for p, f in fits.items():
        rates = ", ".join(f"{d}: {r:.3f}" for d, r in list(f["rates"].items())[:8])
        print(f"  {p:<20} sigma {f['sigma']:.3f}  A {f['A']:.3f}  k {f['k']:.3f}  R^2 {f['r2']:.3f}   rate by delta: {rates}")
    print("\nThe theory's skew (c2 x limit) per gamma, and the product's PnL with it; 'committed' is PARAMS as it is.\n")
    print(f"  {'product':<20} {'setting':<16} {'skew':>8} {'pnl all':>10} {'pnl worse':>10}")
    for p in PRODUCTS:
        print(f"  {p:<20} {'committed':<16} {'':>8} {pnl[(p, None, 'all')]:>10,.0f} {pnl[(p, None, 'worse')]:>10,.0f}")
        for g, s in skews[p].items():
            print(f"  {'':<20} {'gamma ' + str(g):<16} {s:>8.2f} {pnl[(p, s, 'all')]:>10,.0f} {pnl[(p, s, 'worse')]:>10,.0f}")


if __name__ == "__main__":
    main()
