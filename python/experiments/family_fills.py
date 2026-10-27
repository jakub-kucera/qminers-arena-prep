"""Do the template's fills arrive in several members of a product family at once, and do the family's inventories net?

usage (from the repo root): uv run python -m experiments.family_fills [--jobs N] [--engine rust]
       uv run python -m experiments.family_fills --data DIR --days 1 2 [--format F --bot FILE --products A,B]

Baguette Fromage on P4 round 5 (references/prosperity4-baguette-fromage, README 909-911): "if we got
filled, we often got filled in many assets at once". If fills cluster across a family's members, the
members' inventories build together, and a skew on each product's own inventory under-states the
risk: Guéant's Γ (references/wiki/concepts/many-products-architecture.md) skews on the family's.

The template as committed runs on P4 round 5 with every product given the data's limit and DEFAULTS
otherwise (the template as on products it wasn't tuned for), per tick (`all`) and `--resting`.
A family is the products sharing the first word of their names (GALAXY_..., PEBBLES_...). Per family:

1. **Clustering:** the ticks where 2 or more members filled, against the count expected if each
   member filled independently at its own rate that day (a Poisson-binomial per tick), and the
   share of those ticks whose fills all went the same way. The same for the market's own trades
   (prints in 2 or more members in one tick): where the clustering comes from.
2. **Netting:** the carry each member's position earns a tick (position × the wall mid's change),
   summed over the family: its variance over the sum of the members' variances (1 = independent,
   below 1 = the positions hedge each other, above = they add up), the mean pairwise correlation of
   the members' positions and of their one-tick and 100-tick wall-mid changes, and |Σ position| / Σ
   |position| averaged over the ticks with a position (1 = every member held the same way).
"""

from __future__ import annotations

import argparse
import math
import statistics as st
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, dataset_from
from arena.engine import EngineConfig
from arena.formats import FORMATS

DATA, ROUND = "p4", "5"
TEMPLATE = Path("python/bots/template.py")
FORMAT = "prosperity"
MODES = {"all": EngineConfig(), "resting": EngineConfig(resting=True)}
LAG = 100
ENGINE = ["python"]
DAYS: dict = {}


def families(products: list[str]) -> dict[str, list[str]]:
    """Products grouped by the first word of their names; groups of one are dropped."""
    out = defaultdict(list)
    for product in sorted(products):
        out[product.split("_")[0]].append(product)
    return {name: members for name, members in out.items() if len(members) > 1}


def walls(day, product: str) -> list[float | None]:
    out, last = [], None
    for tick in day.ticks:
        book = tick.books.get(product)
        if book is not None and book.bids and book.asks:
            last = book.wall_mid
        out.append(last)
    return out


def at_least_two(rates: list[float]) -> float:
    """P(2 or more of independent Bernoullis with these rates)."""
    none = math.prod(1 - p for p in rates)
    one = sum(p * math.prod(1 - q for j, q in enumerate(rates) if j != i) for i, p in enumerate(rates))
    return 1 - none - one


def clustering(events: list[dict[str, int]], members: list[str]) -> dict:
    """events: per tick, {member: the sign of its net fill (or trade)}. Observed and expected ticks with 2+ members."""
    n = len(events)
    rates = [sum(member in e for e in events) / n for member in members] if n else []
    observed = [e for e in events if sum(m in e for m in members) >= 2]
    same = sum(1 for e in observed if len({e[m] for m in members if m in e}) == 1)
    return {"ticks": n, "any": sum(1 for e in events if any(m in e for m in members)), "observed": len(observed),
            "expected": n * at_least_two(rates) if n else 0.0, "same": same}


def _corr(xs: list[float], ys: list[float]) -> float | None:
    try:
        return st.correlation(xs, ys)
    except st.StatisticsError:
        return None


def netting(day, members: list[str], positions: dict[str, list[int]]) -> dict:
    w = {m: walls(day, m) for m in members}
    n = len(day.ticks)
    carries = {m: [] for m in members}
    for t in range(1, n):
        for m in members:
            a, b = w[m][t - 1], w[m][t]
            carries[m].append(positions[m][t - 1] * (b - a) if a is not None and b is not None else 0.0)
    total = [sum(carries[m][t] for m in members) for t in range(n - 1)]
    parts = sum(st.pvariance(carries[m]) for m in members)
    pairs = [(a, b) for i, a in enumerate(members) for b in members[i + 1:]]

    def changes(m, lag):
        return [(w[m][t] - w[m][t - lag]) if w[m][t] is not None and w[m][t - lag] is not None else 0.0 for t in range(lag, n, lag)]

    def mean_corr(series):
        values = [c for a, b in pairs if (c := _corr(series[a], series[b])) is not None]
        return st.fmean(values) if values else None

    held = [(abs(sum(positions[m][t] for m in members)), sum(abs(positions[m][t]) for m in members)) for t in range(n)]
    held = [a / b for a, b in held if b]
    return {"ratio": st.pvariance(total) / parts if parts else None,
            "pos_corr": mean_corr({m: [float(x) for x in positions[m]] for m in members}),
            "move_corr": mean_corr({m: changes(m, 1) for m in members}),
            "move_corr_lag": mean_corr({m: changes(m, LAG) for m in members}),
            "net": st.fmean(held) if held else None}


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})


def _run(job: tuple[str, str]) -> tuple[tuple[str, str], dict]:
    day_name, mode = job
    fmt = FORMATS[FORMAT]
    (day,) = [d for d in fmt.load_days(fmt.resolve_data_dir(DATA), [ROUND] if isinstance(ROUND, str) else list(ROUND)) if d.name == day_name]
    groups = families(PRODUCTS or day.products)
    traded = sorted({m for members in groups.values() for m in members})
    params = {p: {"limit": day.limits[p]} for p in traded}
    (result,) = backtest(day, [("you", TEMPLATE, {"PARAMS": params}, False)], MODES[mode], ENGINE[0], fields=("fills", "positions", "pnl"), format_name=FORMAT)
    index = {tick.timestamp: i for i, tick in enumerate(day.ticks)}
    net = defaultdict(lambda: defaultdict(int))  # tick -> product -> net fill
    for fill in result.fills:
        net[index[fill.timestamp]][fill.product] += fill.quantity
    fills = [{p: (1 if q > 0 else -1) for p, q in net.get(i, {}).items() if q} for i in range(len(day.ticks))]
    trades = []
    for tick in day.ticks:
        signs = {}
        for product, prints in tick.trades.items():
            book = tick.books.get(product)
            if not prints or book is None:
                continue
            mid = book.mid if book.bids and book.asks else None
            signed = sum(t.quantity * (1 if mid is None or t.price >= mid else -1) for t in prints)
            signs[product] = 1 if signed >= 0 else -1
        trades.append(signs)
    out = {}
    for name, members in groups.items():
        out[name] = {"fills": clustering(fills, members), "trades": clustering(trades, members),
                     "netting": netting(day, members, result.positions),
                     "pnl": sum(result.pnl[m][-1] for m in members if result.pnl.get(m))}
    return job, out


PRODUCTS: list[str] = []


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.family_fills")
    parser.add_argument("--jobs", type=int, default=None)
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser)
    args = parser.parse_args(argv)
    products = args.products
    args.products = None  # every product in the data is traded here, listed in the bot's PARAMS or not
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    settings = {}
    if dataset:
        settings = {"DATA": dataset.data, "ROUND": tuple(dataset.days), "FORMAT": dataset.format, "TEMPLATE": Path(dataset.bot),
                    "PRODUCTS": [p.strip() for p in products.split(",")] if products else []}
    if args.engine == "rust":
        rust.require(args.allow_stale)
    _init(args.engine, settings)
    fmt = FORMATS[FORMAT]
    days = fmt.load_days(fmt.resolve_data_dir(DATA), [ROUND] if isinstance(ROUND, str) else list(ROUND))
    jobs = [(day.name, mode) for day in days for mode in MODES]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        out = dict(pool.map(_run, jobs))
    names = sorted(next(iter(out.values())))
    print(f"The template on {DATA} round {ROUND}, every product at its limit with DEFAULTS; per family, summed over "
          f"{len(days)} days.\n")
    print("0. The market's trade ticks by how many products print in them (products: ticks), per day:")
    for day in days:
        counts = defaultdict(int)
        for tick in day.ticks:
            n = sum(1 for p, prints in tick.trades.items() if prints and (not PRODUCTS or p in PRODUCTS))
            if n:
                counts[n] += 1
        print(f"   {day.name}: " + ", ".join(f"{n}: {c:,}" for n, c in sorted(counts.items())))
    print()
    print("1. Ticks with fills in 2+ members: observed / expected if the members filled independently (and the share all one "
          "way); the same for the market's trades.\n")
    print("| Family | Mode | Ticks with a fill | 2+ members: observed / expected | ratio | all one way | Market: 2+ members observed / expected | ratio |")
    print("|---|---|---|---|---|---|---|---|")
    for name in names:
        for mode in MODES:
            f = {k: sum(out[(d.name, mode)][name]["fills"][k] for d in days) for k in ("any", "observed", "expected", "same")}
            t = {k: sum(out[(d.name, mode)][name]["trades"][k] for d in days) for k in ("observed", "expected")}
            ratio = f"{f['observed'] / f['expected']:.2f}" if f["expected"] else "-"
            tratio = f"{t['observed'] / t['expected']:.2f}" if t["expected"] else "-"
            same = f"{f['same'] / f['observed']:.0%}" if f["observed"] else "-"
            print(f"| {name} | {mode} | {f['any']:,} | {f['observed']:,} / {f['expected']:,.0f} | {ratio} | {same} | "
                  f"{t['observed']:,} / {t['expected']:,.0f} | {tratio} |")
    print("\n2. Netting, per day (day / day / day): the family's carry variance over the sum of its members' (1 = independent, "
          f"< 1 = they hedge), the mean pairwise correlation of positions, of 1-tick and {LAG}-tick wall-mid changes, "
          "|Σ position| / Σ |position|, and the family's PnL.\n")
    print(f"| Family | Mode | Carry variance ratio | Position corr | Move corr (1) | Move corr ({LAG}) | Net share | PnL |")
    print("|---|---|---|---|---|---|---|---|")

    def cell(values):
        return " / ".join("-" if v is None else f"{v:+.2f}" if isinstance(v, float) and v < 1.5 and v > -1.5 else f"{v:.2f}" for v in values)

    for name in names:
        for mode in MODES:
            rows = [out[(d.name, mode)][name] for d in days]
            nets = [r["netting"] for r in rows]
            print(f"| {name} | {mode} | {cell([x['ratio'] for x in nets])} | {cell([x['pos_corr'] for x in nets])} | "
                  f"{cell([x['move_corr'] for x in nets])} | {cell([x['move_corr_lag'] for x in nets])} | {cell([x['net'] for x in nets])} | "
                  + " / ".join(f"{r['pnl']:,.0f}" for r in rows) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])
