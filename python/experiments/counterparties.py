"""Following named traders: whose trades tell where the price goes, and the template's copy mode.

usage (from the repo root): uv run python -m experiments.counterparties [--jobs N] [--engine rust]

The trade files of P3 round 5 and P4 round 4 name each trade's buyer and seller. The bot sees a
tick's trades on the next tick (python/arena/engine.py), so every move here is measured from the wall
mid of the tick after the trade.

1. Per name, product and side (buying or selling), per day: the number of trades and the mean
   move of the wall mid in that side's direction 10, 100, 500 and 1,000 ticks later, against half
   the median spread (the cost of crossing in to follow it). A row is starred when its sign holds
   on every day at some horizon and its smallest daily move there is above half the spread.
2. Leave one day out: for each day, the names chosen on the other days, then traded on it. On the
   training days a (name, product) needs at least MIN_TRADES trades on each day, its buys and
   sells pooled, and then is chosen by one of two rules, each the same way on every training day:
     mean   its mean move at HORIZON is beyond half the spread: followed (weight 1) if with it,
            faded (-1) if against it;
     hits   at least HIT_SHARE of its trades were followed by a move its way at HORIZON (followed),
            or against it (faded). An informed trader is right on nearly every trade, not on
            average. This rule was written after the mean rule had failed here, so it is not a
            clean out-of-sample test.
   The held-out day is
   traded with the template's copy mode on those products, plain market making on every other
   (limit from the format's LIMITS, wall_mid, make_edge 1), and compared with plain market making
   on every product. Nothing about the held-out day is used.
3. The settings kept (FIXED, chosen with all three P3 days in view, so in-sample): copying Olivia
   on Croissants and Squid Ink, per product and day, in the default mode, under `worse` fills and
   under --resting; and copying her on Kelp, which loses. Under --resting, both runs only take
   (make_size 0): these products' prices jump past half the spread, and full-room quotes resting
   there lose (`arena.diagnose 5 --data p3`).
"""

import argparse
import statistics as st
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import backtest
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS
from arena.formats.prosperity import LIMITS

FMT = FORMATS["prosperity"]
TEMPLATE = Path("python/bots/template.py")
DATASETS = {"P3 round 5": ("p3", "5"), "P4 round 4": ("p4", "4")}
HORIZONS = [10, 100, 500, 1000]
HORIZON = 500
MIN_TRADES = 2
HIT_SHARE = 0.8
RULES = ["mean", "hits"]
FIXED = {"CROISSANTS": {"Olivia": 1}, "SQUID_INK": {"Olivia": 1}}
MODES = {
    "default": EngineConfig(),
    "worse": EngineConfig(trade_matching=TradeMatching.WORSE),
    "resting": EngineConfig(resting=True),
}
_DAYS = {}


def walls(day) -> dict[str, list[float | None]]:
    """Each product's wall mid per tick, the last one carried over a tick with an empty side."""
    out = {}
    for product in day.products:
        last, series = None, []
        for tick in day.ticks:
            book = tick.books.get(product)
            last = (book.wall_mid if book else None) or last
            series.append(last)
        out[product] = series
    return out


def name_moves(day) -> dict[tuple[str, str, int], list[list[float]]]:
    """(name, product, side) -> per trade, the wall mid's move in that side's direction at each horizon."""
    w, n = walls(day), len(day.ticks)
    out = defaultdict(list)
    for i, tick in enumerate(day.ticks[:-1]):
        for product, trades in tick.trades.items():
            start = w[product][i + 1]
            if start is None:
                continue
            for trade in trades:
                for name, side in ((trade.buyer, 1), (trade.seller, -1)):
                    if name:
                        out[(name, product, side)].append([side * (w[product][min(i + 1 + h, n - 1)] - start) for h in HORIZONS])
    return out


def half_spreads(days) -> dict[str, float]:
    spreads = defaultdict(list)
    for day in days:
        for tick in day.ticks:
            for product, book in tick.books.items():
                if book.bids and book.asks:
                    spreads[product].append(book.asks[0][0] - book.bids[0][0])
    return {product: st.median(s) / 2 for product, s in spreads.items()}


def choose(moves_by_day: list[dict], half: dict[str, float], rule: str) -> dict[str, dict[str, int]]:
    """Part 2's rule on the training days: {product: {name: +1 or -1}}."""
    k = HORIZONS.index(HORIZON)
    pooled = [defaultdict(list) for _ in moves_by_day]  # per day: (name, product) -> moves at HORIZON
    for day_moves, out in zip(moves_by_day, pooled):
        for (name, product, _), moves in day_moves.items():
            out[(name, product)] += [m[k] for m in moves]
    chosen = defaultdict(dict)
    for key in set.intersection(*(set(day) for day in pooled)):
        name, product = key
        if any(len(day[key]) < MIN_TRADES for day in pooled):
            continue
        if rule == "mean":
            means = [st.mean(day[key]) for day in pooled]
            up, down = all(m > half[product] for m in means), all(m < -half[product] for m in means)
        else:
            up = all(sum(m > 0 for m in day[key]) >= HIT_SHARE * len(day[key]) for day in pooled)
            down = all(sum(m < 0 for m in day[key]) >= HIT_SHARE * len(day[key]) for day in pooled)
        if up:
            chosen[product][name] = 1
        elif down:
            chosen[product][name] = -1
    return dict(chosen)


ENGINE = ["python"]  # set in each worker by _init (--engine)


_PRODUCTS: dict = {}  # --engine rust: {label: {day name: its products}}, from the main process


def _init(datasets, engine="python", products=None):
    ENGINE[0] = engine
    if products is not None:  # Rust reads each day's CSVs itself (_run): only the products are needed here
        _PRODUCTS.update(products)
        return
    for label in datasets:
        data, rnd = DATASETS[label]
        _DAYS[label] = {d.name: d for d in FMT.load_days(FMT.resolve_data_dir(data), [rnd])}


def _params(products, copy, mode):
    out = {}
    for product in products:
        p = {"limit": LIMITS[product], "fair": "wall_mid", "make_edge": 1}
        if mode == "resting":
            p["make_size"] = 0
        if product in copy:
            p["copy"] = dict(copy[product])
        out[product] = p
    return out


def _run(job):
    label, day_name, copy, mode = job
    if ENGINE[0] == "rust":
        day, products = rust.named_day(DATASETS[label][0], day_name), _PRODUCTS[label][day_name]
    else:
        day = _DAYS[label][day_name]
        products = day.products
    copy = {product: dict(names) for product, names in copy}
    (result,) = backtest(day, [("you", TEMPLATE, {"PARAMS": _params(products, copy, mode)}, False)], MODES[mode], ENGINE[0], True, ("pnl", "errors", "breaches"))
    return job, ({p: s[-1] for p, s in result.pnl.items() if s}, len(result.limit_breaches) + len(result.errors))


def _print_folds(label, rule, names, folds, out):
    print(f"\n{label}\n2. leave one day out, rule {rule!r}: names chosen on the other days, traded on this one (thousands)")
    total = 0.0
    for test in names:
        chosen = folds[(rule, test)]
        plain, _ = out[(label, test, (), "default")]
        pnl, issues = out[(label, test, _freeze(chosen), "default")]
        diff = {p: pnl.get(p, 0.0) - plain.get(p, 0.0) for p in chosen}
        total += sum(diff.values())
        picks = "; ".join(f"{p} " + ", ".join(f"{'follow' if w > 0 else 'fade'} {n}" for n, w in sorted(c.items()))
                          for p, c in sorted(chosen.items())) or "none"
        print(f"   {test}: chosen {picks}")
        print(f"      change against plain market making: {sum(diff.values()) / 1000:+.1f} ("
              + ", ".join(f"{p} {d / 1000:+.1f}" for p, d in sorted(diff.items())) + ")"
              + (f"  ! {issues} errors or breaches" if issues else ""))
    print(f"   total over the held-out days: {total / 1000:+.1f}")


def _freeze(copy):
    return tuple(sorted((product, tuple(sorted(names.items()))) for product, names in copy.items()))


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args(argv)
    if args.engine == "rust":
        rust.build()
    _init(DATASETS)

    jobs, folds = [], {}
    for label, days in _DAYS.items():
        names = list(days)
        moves = {n: name_moves(days[n]) for n in names}
        half = half_spreads(days.values())
        folds[label] = {(rule, test): choose([moves[n] for n in names if n != test], half, rule)
                        for rule in RULES for test in names}

        print(f"\n{label}\n1. per name, product and side: trades and mean move its way at {HORIZONS} ticks, per day")
        rows = []
        for key in sorted(set().union(*moves.values())):
            per = [moves[n].get(key, []) for n in names]
            if sum(len(x) for x in per) < 6:
                continue
            means = [[st.mean(m[k] for m in x) if x else None for k in range(len(HORIZONS))] for x in per]
            star = any(all(d[k] is not None for d in means)
                       and (all(d[k] > half[key[1]] for d in means) or all(d[k] < -half[key[1]] for d in means))
                       for k in range(len(HORIZONS)))
            rows.append((not star, key, per, means))
        for not_star, (name, product, side), per, means in sorted(rows)[:25]:
            cells = "  ".join(f"{len(x):>4}: " + "/".join("-" if v is None else f"{v:+.1f}" for v in d) for x, d in zip(per, means))
            print(f"   {' ' if not_star else '*'} {name:<9} {product:<28} {'buys ' if side > 0 else 'sells'} {cells}  half spread {half[product]:g}")
        print(f"   ({len(rows)} rows with 6 or more trades; the first 25, starred first)")

        for (rule, test), chosen in folds[label].items():
            jobs.append((label, test, (), "default"))
            jobs.append((label, test, _freeze(chosen), "default"))
        if label == "P3 round 5":
            for mode in MODES:
                for n in names:
                    jobs.append((label, n, (), mode))
                    jobs.append((label, n, _freeze(FIXED), mode))
            jobs += [(label, n, _freeze({"KELP": {"Olivia": 1}}), "default") for n in names]
    products = {label: {name: day.products for name, day in days.items()} for label, days in _DAYS.items()} if args.engine == "rust" else None
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(list(DATASETS), args.engine, products)) as pool:
        out = dict(pool.map(_run, set(jobs)))

    for label, days in _DAYS.items():
        names = list(days)
        for rule in RULES:
            _print_folds(label, rule, names, folds[label], out)

        if label != "P3 round 5":
            continue
        print("\n3. copying Olivia on Croissants and Squid Ink (in-sample), against plain market making (thousands;")
        print("   under --resting both only take)")
        for mode in MODES:
            cells = []
            for product in FIXED:
                per = [out[(label, n, _freeze(FIXED), mode)][0].get(product, 0.0) for n in names]
                base = [out[(label, n, (), mode)][0].get(product, 0.0) for n in names]
                cells.append(f"{product} " + " / ".join(f"{a / 1000:.1f}" for a in per)
                             + f" (plain " + " / ".join(f"{b / 1000:.1f}" for b in base) + ")")
            print(f"   {mode:<8} " + "; ".join(cells))
        kelp = [out[(label, n, _freeze({"KELP": {"Olivia": 1}}), "default")][0].get("KELP", 0.0) for n in names]
        base = [out[(label, n, (), "default")][0].get("KELP", 0.0) for n in names]
        print("   KELP, copying her too: " + " / ".join(f"{a / 1000:.1f}" for a in kelp)
              + " (plain " + " / ".join(f"{b / 1000:.1f}" for b in base) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
