"""Implementation shortfall and missed-trade cost per order (Harris), from our orders and fills or the results ZIP.

usage (from the repo root): uv run python -m experiments.day.shortfall [--jobs N] [--engine rust]   # the --delay check on P3 round 1
       uv run python -m experiments.day.shortfall --data DIR --days 1 2 --results RESULTS [--delay N] [--format F]

Fill-time markouts (arena.analysis, experiments.day.quote_markouts) value a fill against the price when
it happened, so they can't see a fill that came late or never came. Harris's implementation shortfall
(literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:9853-9859, :10018-10022)
values each order against the price when it was decided:

    edge at decision  = sum over its fills of q × (fair at the decision − price)   what its fills earned
    edge at arrival   = the same against the fair when the order reached the exchange
    delay cost        = edge at arrival − edge at decision, less 0 if the fair moved our way
    missed-trade cost = unfilled q × (fair at the next decision − fair at the decision)
                        what the lots we wanted and didn't get would have made by the time we could
                        decide again: the tick after the order's last working tick

q is signed (a buy positive), the fair is the wall mid (--fair), the costs are in the data's price
units and positive when they cost us. The decision is the order's first working tick less --delay
ticks: our engine records an order when it reaches the exchange, and the ZIP may too. Orders the
engine rejected (a limit breach, or a race lost to our own earlier late fills) are not in the orders
file at all, so their missed trades are invisible here; the race count says how many ticks lost them.
Takes (orders that crossed the book on arrival) and quotes are shown apart.

Default: the template as committed on P3 round 1 with `--delay` 0, 1 and 2, per product and summed
over the days: PnL, and each part's change against delay 0, to check how much of the PnL a delay
costs the shortfall explains. With --results, the table for one run (our --out folder or the
portal's ZIP, read through python/experiments/day/fill_curve.py's column map).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, dataset_from
from arena.engine import EngineConfig
from arena.formats import FORMATS
from experiments.day.fill_curve import read_results

TEMPLATE = Path("python/bots/template.py")
DATA, ROUND = "p3", "1"
DELAYS = (0, 1, 2)
PARTS = ("edge_decision", "edge_arrival", "missed")
ENGINE = ["python"]


def fairs(day, product: str, how: str = "wall_mid") -> list[float | None]:
    """The fair per tick, the last one carried over a tick with an empty side."""
    out, last = [], None
    for tick in day.ticks:
        book = tick.books.get(product)
        if book is not None and book.bids and book.asks:
            last = book.wall_mid if how == "wall_mid" else book.mid
        out.append(last)
    return out


def rows_of(result) -> dict[str, list[dict]]:
    """A DayResult's orders and fills as fill_curve.read_results gives a ZIP's."""
    return {
        "orders": [{"timestamp": t, "id": str(o.id), "product": o.product, "price": float(o.price), "quantity": float(o.quantity)}
                   for t, o in result.orders],
        "fills": [{"timestamp": f.timestamp, "product": f.product, "price": float(f.price), "quantity": float(f.quantity),
                   "order_id": str(f.order_id), "source": f.source} for f in result.fills],
    }


def shortfall(day, product: str, results: dict[str, list[dict]], delay: int = 0, how: str = "wall_mid") -> dict:
    """Per kind ("take", "quote"): orders, filled lots, wanted lots, and PARTS summed over the orders."""
    index = {tick.timestamp: i for i, tick in enumerate(day.ticks)}
    fair = fairs(day, product, how)
    n = len(fair)
    orders: dict[str, dict] = {}
    for row in results["orders"]:
        if row["product"] != product or row["timestamp"] not in index:
            continue
        i = index[row["timestamp"]]
        order = orders.get(row["id"])
        if order is None:
            book = day.ticks[i].books.get(product)
            q = row["quantity"]
            take = book is not None and ((q > 0 and book.asks and row["price"] >= book.asks[0][0]) or (q < 0 and book.bids and row["price"] <= book.bids[0][0]))
            orders[row["id"]] = {"first": i, "last": i, "wanted": q, "take": take}
        else:
            order["last"] = max(order["last"], i)
    fills = defaultdict(list)
    for row in results["fills"]:
        if row["product"] == product:
            fills[row["order_id"]].append(row)
    out = {kind: dict.fromkeys(("orders", "filled", "wanted", *PARTS), 0.0) for kind in ("take", "quote")}
    for order_id, order in orders.items():
        decided, arrived, after = max(order["first"] - delay, 0), order["first"], min(order["last"] + 1, n - 1)
        f_dec, f_arr, f_next = fair[decided], fair[arrived], fair[after]
        if f_dec is None or f_arr is None or f_next is None:
            continue
        got = fills.get(order_id, [])
        filled = sum(r["quantity"] for r in got)
        cell = out["take" if order["take"] else "quote"]
        cell["orders"] += 1
        cell["filled"] += abs(filled)
        cell["wanted"] += abs(order["wanted"])
        cell["edge_decision"] += sum(r["quantity"] * (f_dec - r["price"]) for r in got)
        cell["edge_arrival"] += sum(r["quantity"] * (f_arr - r["price"]) for r in got)
        cell["missed"] += (order["wanted"] - filled) * (f_next - f_dec)
    return out


# ---------------------------------------------------------------------------- the --delay check


def _init(engine: str) -> None:
    ENGINE[0] = engine


def _run(job: tuple[str, int]) -> tuple[tuple[str, int], dict]:
    day_name, delay = job
    fmt = FORMATS["prosperity"]
    (day,) = [d for d in fmt.load_days(fmt.resolve_data_dir(DATA), [ROUND]) if d.name == day_name]
    (result,) = backtest(day, [("you", TEMPLATE, {}, False)], EngineConfig(delay=delay), ENGINE[0], fields=("pnl", "fills", "orders", "races"))
    rows = rows_of(result)
    races = defaultdict(int)
    for _, product in result.races:
        races[product] += 1
    out = {p: {"pnl": result.pnl[p][-1] if result.pnl.get(p) else 0.0, "races": races[p], "parts": shortfall(day, p, rows, delay)}
           for p in day.products}
    return job, out


def _total(parts: dict, key: str) -> float:
    return sum(cell[key] for cell in parts.values())


def print_check(results: dict, days: list[str], products: list[str]) -> None:
    print("The template as committed on P3 round 1, summed over its days, by --delay (price units; edges positive = earned, "
          "missed positive = cost; the change against delay 0 in brackets). PnL = edge at decision + the rest (the fills' "
          "positions carried from the decision to the close), so the share of the PnL's change that the edge's change makes "
          "is how much of the delay's cost the shortfall explains. Arrival − decision: what the fair's move between the two "
          "added to the fills' edge.\n")
    print("| Product | Delay | PnL | Edge at decision: takes / quotes | Share of ΔPnL | Arrival − decision | Missed-trade cost: takes / quotes | Filled / wanted lots | Race ticks |")
    print("|---|---|---|---|---|---|---|---|---|")
    for product in products:
        base = None
        for delay in DELAYS:
            cells = [results[(day, delay)][product] for day in days]
            pnl = sum(c["pnl"] for c in cells)
            parts = {kind: {key: sum(c["parts"][kind][key] for c in cells) for key in ("orders", "filled", "wanted", *PARTS)} for kind in ("take", "quote")}
            if not _total(parts, "orders"):
                continue
            edge, arrival = _total(parts, "edge_decision"), _total(parts, "edge_arrival")
            row = {"pnl": pnl, "edge": edge, "missed": _total(parts, "missed")}
            if base is None:
                base = row
            d = {k: row[k] - base[k] for k in row}
            share = f"{d['edge'] / d['pnl']:.0%}" if abs(d["pnl"]) > 1e-9 else "-"
            print(f"| {product} | {delay} | {pnl:,.0f} ({d['pnl']:+,.0f}) | {parts['take']['edge_decision']:,.0f} / {parts['quote']['edge_decision']:,.0f} "
                  f"({d['edge']:+,.0f}) | {share} | {arrival - edge:+,.0f} | {parts['take']['missed']:+,.0f} / {parts['quote']['missed']:+,.0f} "
                  f"({d['missed']:+,.0f}) | {_total(parts, 'filled'):,.0f} / {_total(parts, 'wanted'):,.0f} | {sum(c['races'] for c in cells):,} |")


def print_one(label: str, tables: dict[str, dict]) -> None:
    print(f"Shortfall per product in {label} (price units; edges positive = earned, missed positive = cost)\n")
    print("| Product | Kind | Orders | Filled / wanted lots | Edge at decision | Edge at arrival | Missed-trade cost |")
    print("|---|---|---|---|---|---|---|")
    for product, parts in tables.items():
        for kind, c in parts.items():
            if c["orders"]:
                print(f"| {product} | {kind} | {c['orders']:,.0f} | {c['filled']:,.0f} / {c['wanted']:,.0f} | {c['edge_decision']:,.1f} | "
                      f"{c['edge_arrival']:,.1f} | {c['missed']:+,.1f} |")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.shortfall")
    parser.add_argument("--jobs", type=int, default=None)
    add_engine_argument(parser, "run the --delay check's backtests in rust/ (the same results)")
    add_dataset_arguments(parser, bot=False)
    parser.add_argument("--results", type=Path, help="a results ZIP or an arena.backtest --out folder of a run on --data's days")
    parser.add_argument("--delay", type=int, default=0, help="with --results: ticks between a decision and the order's first working tick (default 0)")
    parser.add_argument("--fair", choices=("wall_mid", "mid"), default="wall_mid")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if bool(args.results) != bool(dataset):
        parser.error("--results and --data go together: the run's results and the days it was on")
    if dataset:
        fmt = FORMATS[dataset.format]
        days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
        runs = read_results(args.results)
        tables = {}
        for product in dataset.products:
            total = None
            for day in days:
                if day.name not in runs or product not in day.products:
                    continue
                parts = shortfall(day, product, runs[day.name], args.delay, args.fair)
                total = parts if total is None else {k: {key: total[k][key] + parts[k][key] for key in parts[k]} for k in parts}
            if total:
                tables[product] = total
        print_one(f"{args.results} ({dataset.name}, delay {args.delay})", tables)
        return
    if args.engine == "rust":
        rust.require(args.allow_stale)
    fmt = FORMATS["prosperity"]
    days = fmt.load_days(fmt.resolve_data_dir(DATA), [ROUND])
    names = [d.name for d in days]
    products = sorted({p for d in days for p in d.products})
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        results = dict(pool.map(_run, [(name, delay) for name in names for delay in DELAYS]))
    print_check(results, names, products)


if __name__ == "__main__":
    main(sys.argv[1:])
