"""Why the template holds Kelp long: the takers' flow, or a bias in its fair value or quotes?

usage (from the repo root): uv run python -m experiments.kelp_drift [--jobs N]

P3 round 1, all three days, the template as committed, under --match-trades all and worse and
--resting. For Kelp, and Rainforest Resin as a control:

1. Each day and its mirror image: every price reflected around twice the product's median wall
   mid (so a fixed fair stays right), bids and asks swapped, buyers and sellers swapped. The
   template's quoting is symmetric (floor below fair, ceil above, one tick inside each side), so a
   bias in it holds the same sign on both, while a position the takers' flow builds flips sign.
   Printed: the mean position, the share of ticks at each limit, our passive and taken volume on
   each side, and the PnL, then the market trades' share of buys at the touch, by count and volume.
2. Harris's test (references/wiki/concepts/informed-counterparties.md): the correlation of our
   position with the mark's change over the next h ticks. Negative means informed counterparties
   (we build a position before the price moves against it).
3. Kelp's `skew` (quotes shifted `skew` ticks at the full limit, against the position), 0 to 3:
   the mean position and the PnL, per mode.
Results go into IDEAS.md ("`skew` against Kelp's long position") and TODO_DONE.md ("Explain Kelp's
long drift").
"""

from __future__ import annotations

import argparse
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from arena.engine import EngineConfig, TradeMatching, run_day
from arena.formats import FORMATS
from arena.model import Book, Day

FMT = FORMATS["prosperity"]
TEMPLATE = Path("python/bots/template.py")
PRODUCTS = ("KELP", "RAINFOREST_RESIN")
MODES = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE), "resting": EngineConfig(resting=True)}
HORIZONS = (10, 50, 200, 1000)
SKEWS = (0, 1, 2, 3)
_DAYS: dict[str, Day] = {}  # each worker's copy of the three days, loaded once


def mirrored(day: Day) -> Day:
    """The day reflected: each product's prices around twice its median wall mid, bids for asks, buyers for sellers."""
    centers = {}
    for product in day.products:
        walls = [b.wall_mid for t in day.ticks for b in [t.books.get(product)] if b is not None and b.wall_mid is not None]
        centers[product] = 2 * round(statistics.median(walls)) if walls else 0
    ticks = []
    for t in day.ticks:
        books = {p: Book(tuple((centers[p] - price, v) for price, v in b.asks), tuple((centers[p] - price, v) for price, v in b.bids))
                 for p, b in t.books.items()}
        trades = {p: [replace(x, price=centers[p] - x.price, buyer=x.seller, seller=x.buyer) for x in xs] for p, xs in t.trades.items()}
        ticks.append(replace(t, books=books, trades=trades, marks={p: centers[p] - m for p, m in t.marks.items()}))
    return replace(day, ticks=ticks)


def flow(day: Day, product: str) -> tuple[float, float]:
    """The market trades' share of buys (at or above the ask) among those at the touch, by count and by volume."""
    buys = sells = buy_volume = sell_volume = 0
    for t in day.ticks:
        book = t.books.get(product)
        if book is None or not (book.bids and book.asks):
            continue
        for trade in t.trades.get(product, []):
            if trade.price >= book.asks[0][0]:
                buys, buy_volume = buys + 1, buy_volume + trade.quantity
            elif trade.price <= book.bids[0][0]:
                sells, sell_volume = sells + 1, sell_volume + trade.quantity
    return buys / max(buys + sells, 1), buy_volume / max(buy_volume + sell_volume, 1)


def run(job: tuple[str, str, bool, int]) -> tuple[tuple[str, str, bool, int], dict]:
    """One day (mirrored or not) under one mode, Kelp at one skew: per product, the statistics above."""
    day_name, mode, mirror, skew = job
    if not _DAYS:
        _DAYS.update({d.name: d for d in FMT.load_days(FMT.resolve_data_dir("p3"), ["1"])})
    day = mirrored(_DAYS[day_name]) if mirror else _DAYS[day_name]
    bot = FMT.load_bot(TEMPLATE, {"PARAMS.KELP.skew": skew} if skew else {}, strict=True)
    result = run_day(day, bot, MODES[mode])
    out = {}
    for p in PRODUCTS:
        positions, marks, limit = result.positions[p], result.marks[p], result.limits[p]
        fills = [f for f in result.fills if f.product == p]
        volume = {(passive, side): sum(abs(f.quantity) for f in fills if (f.source != "book") == passive and (f.quantity > 0) == side)
                  for passive in (True, False) for side in (True, False)}
        out[p] = {
            "mean": statistics.fmean(positions),
            "long": sum(x >= limit for x in positions) / len(positions),
            "short": sum(x <= -limit for x in positions) / len(positions),
            "volume": volume,
            "pnl": result.pnl[p][-1],
            "flow": flow(day, p),
            "harris": {h: statistics.correlation(positions[:-h], [b - a for a, b in zip(marks, marks[h:])]) for h in HORIZONS},
        }
    return job, out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.kelp_drift")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    args = parser.parse_args()
    days = [d.name for d in FMT.load_days(FMT.resolve_data_dir("p3"), ["1"])]
    jobs = [(d, m, mirror, 0) for d in days for m in MODES for mirror in (False, True)]
    jobs += [(d, m, False, s) for d in days for m in MODES for s in SKEWS if s]
    with ProcessPoolExecutor(args.jobs) as pool:
        found = dict(pool.map(run, jobs, chunksize=1))

    print("P3 round 1, the template as committed. 1. Each day and its mirror image (prices reflected, buyers for sellers).")
    print("pos: mean position; at +/-: share of ticks at each limit; passive and taken: our volume bought / sold; "
          "flow: the market trades' share of buys at the touch, by count / volume.")
    for p in PRODUCTS:
        print(f"\n{p}:")
        for m in MODES:
            for d in days:
                for mirror in (False, True):
                    r = found[(d, m, mirror, 0)][p]
                    v = r["volume"]
                    print(f"  {m:<7} {d:<6} {'mirror' if mirror else 'as is':<6}  pos {r['mean']:+6.1f}  at +/- {r['long']:4.0%} / {r['short']:4.0%}  "
                          f"passive {v[(True, True)]:>5,} / {v[(True, False)]:>5,}  taken {v[(False, True)]:>5,} / {v[(False, False)]:>5,}  "
                          f"pnl {r['pnl']:>8,.0f}  flow {r['flow'][0]:.0%} / {r['flow'][1]:.0%}")

    print("\n2. Harris: corr(our position, the mark's change over the next h ticks), as is; negative = informed counterparties.")
    for p in PRODUCTS:
        for m in MODES:
            cells = "  ".join(f"h={h}: " + " ".join(f"{found[(d, m, False, 0)][p]['harris'][h]:+.3f}" for d in days) for h in HORIZONS)
            print(f"  {p:<16} {m:<7} {cells}")

    print("\n3. Kelp's skew (ticks at the full limit): mean position and PnL over the three days, as is.")
    for m in MODES:
        cells = []
        for s in SKEWS:
            rs = [found[(d, m, False, s)]["KELP"] for d in days]
            cells.append(f"skew {s}: pos {statistics.fmean(r['mean'] for r in rs):+5.1f} pnl {sum(r['pnl'] for r in rs):>7,.0f}")
        print(f"  {m:<7} " + "   ".join(cells))


if __name__ == "__main__":
    main()
