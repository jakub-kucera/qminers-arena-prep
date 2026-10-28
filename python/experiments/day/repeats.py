"""Do market trades recur across days at the same timestamp, side and size? The cross-day repeat scan.

usage (from the repo root): uv run python -m experiments.day.repeats
       uv run python -m experiments.day.repeats --data DIR --days 1 2 [--format F --products A,B --big 7 --csv FILE]

Baguette Fromage found takers that "reappeared at identical timestamps, with identical side, and
with identical size, on consecutive days" in Prosperity 4's round 2, 97.7% of Osmium's trades of
size 7 or more (their claim), and none in round 1 (`references/prosperity4-baguette-fromage/README.md:557-668`).
A market trade's side is read from the same tick's book: at or above the best ask (or above the bid
with no asks) a buy, at or below the best bid a sell, inside the spread unknown and left out.

For each product and each pair of consecutive days (d, d + 1) in the order loaded:

  recur      the share of day d's (tick, side, size) trades that day d + 1 has too (each matched at
             most once), for all sizes, below --big and from --big up;
  baseline   the same with day d + 1's ticks shifted by SHIFTS random offsets (cyclically): what
             chance gives for that many trades;
  two days   with three or more days, the share of day d's on day d + 2, and of those not on d + 1
             (their Markov-style claim: a trade carries to d + 2 only through d + 1).

A product whose recur share is at least FLAG and FLAG_LIFT times its baseline is listed below the
table with where its recurring trades print (past the wall mid, against how much visible depth,
how often on an empty side), and the predicted events for the day after the last one: the last
day's trades that the day before had too (--csv writes all of them).

In a replay the predicted taker meets the book as recorded, so a quote at the touch already gets
what it gives; it pays only on a platform whose takers lift a far quote on an empty side (probe 14),
by Baguette Fromage's rule: clear the side and post an extreme quote when p_repeat × q × edge > c_clear.
Results: IDEAS.md, "Takers that recur across days".
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from collections import Counter
from pathlib import Path

from arena.cli import add_dataset_arguments, dataset_from
from arena.formats import FORMATS
from arena.model import Book, Day, MarketTrade

DATASETS = [("p4", "2"), ("p4", "1"), ("p4", "3"), ("p4", "4"), ("p4", "5"), ("p3", "1"), ("p3", "2"), ("p2", "1")]
BIG = 7  # Baguette Fromage's size cut
SHIFTS = 20
FLAG = 0.2  # a product is listed when this share of a class recurs...
FLAG_LIFT = 10  # ...and this many times its baseline


def side(trade: MarketTrade, book: Book | None) -> int:
    """+1 a buy, -1 a sell, 0 unknown, from the same tick's book."""
    if book is None:
        return 0
    if book.asks and trade.price >= book.asks[0][0]:
        return 1
    if book.bids and trade.price <= book.bids[0][0]:
        return -1
    if not book.asks and book.bids and trade.price > book.bids[0][0]:
        return 1  # into an empty ask side
    if not book.bids and book.asks and trade.price < book.asks[0][0]:
        return -1
    return 0


def events(day: Day, product: str) -> Counter:
    """(tick index, side, size) of the day's market trades whose side is known, with their counts."""
    out: Counter = Counter()
    for i, tick in enumerate(day.ticks):
        book = tick.books.get(product)
        for trade in tick.trades.get(product, ()):
            if s := side(trade, book):
                out[(i, s, abs(trade.quantity))] += 1
    return out


def matched(a: Counter, b: Counter, keep=lambda key: True) -> tuple[int, int]:
    """a's trades that keep() selects, and how many of them b has too."""
    total = sum(c for k, c in a.items() if keep(k))
    return total, sum(min(c, b.get(k, 0)) for k, c in a.items() if keep(k))


def shifted(b: Counter, offset: int, n: int) -> Counter:
    return Counter({((i + offset) % n, s, q): c for (i, s, q), c in b.items()})


CLASSES = {"all": lambda k: True, "small": lambda k: k[2] < BIG, "big": lambda k: k[2] >= BIG}


def study(days: list[Day], product: str, seed: int = 0) -> list[dict]:
    """Per consecutive pair of days: the recur shares by size class, their baselines, and two days on."""
    rng = random.Random(seed)
    per_day = [events(day, product) for day in days]
    rows = []
    for d in range(len(days) - 1):
        a, b = per_day[d], per_day[d + 1]
        n = len(days[d + 1].ticks)
        offsets = [rng.randrange(1, n) for _ in range(SHIFTS)] if n > 1 else []
        row = {"days": (days[d].name, days[d + 1].name)}
        for name, keep in CLASSES.items():
            total, found = matched(a, b, keep)
            base = [matched(a, shifted(b, k, n), keep) for k in offsets]
            base_total = sum(t for t, _ in base)
            row[name] = (total, found, sum(f for _, f in base) / base_total if base_total else None)
        if d + 2 < len(days):
            c = per_day[d + 2]
            keys = set(a)
            later = [k for k in keys if k in c]
            skipped = [k for k in keys if k not in b]
            row["two"] = (len(later) / len(keys) if keys else None,
                          sum(1 for k in skipped if k in c) / len(skipped) if skipped else None)
        rows.append(row)
    return rows


def flagged(rows: list[dict]) -> list[str]:
    """The size classes whose recur share is at least FLAG and FLAG_LIFT times the baseline on every pair."""
    out = []
    for name in CLASSES:
        cells = [r[name] for r in rows if r[name][0]]
        if cells and all(f / t >= FLAG and f / t >= FLAG_LIFT * (base or 0) for t, f, base in cells):
            out.append(name)
    return out


def where(days: list[Day], product: str) -> dict:
    """For day d + 1's trades of size --big and up: how far past the wall mid they paid (in the taker's
    disfavour), the visible depth on the side they hit, and how often that side was empty, split by
    whether day d had them."""
    out = {"recurring": [], "new": []}
    for d in range(1, len(days)):
        before = events(days[d - 1], product)
        for i, tick in enumerate(days[d].ticks):
            book = tick.books.get(product)
            for trade in tick.trades.get(product, ()):
                s = side(trade, book)
                if not s or abs(trade.quantity) < BIG or book is None:
                    continue
                fair = book.wall_mid if book.wall_mid is not None else (book.bids or book.asks)[0][0]
                hit = book.asks if s > 0 else book.bids
                out["recurring" if before.get((i, s, abs(trade.quantity))) else "new"].append(
                    (s * (trade.price - fair), sum(v for _, v in hit), not hit, abs(trade.quantity)))
    return out


def predicted(days: list[Day], product: str) -> list[tuple[int, int, int, int]]:
    """The last day's (timestamp, side, size, count) trades that the day before had too: the events to
    expect on the next day."""
    if len(days) < 2:
        return []
    last, before = events(days[-1], product), events(days[-2], product)
    out = []
    for (i, s, q), c in sorted(last.items()):
        if before.get((i, s, q)):
            out.append((days[-1].ticks[i].timestamp, s, q, min(c, before[(i, s, q)])))
    return out


def _pct(total: int, found: int) -> str:
    return f"{found}/{total} = {found / total:.1%}" if total else "-"


def _base(value: float | None) -> str:
    return "-" if value is None else f"{value:.1%}"


def report(name: str, days: list[Day], products: list[str], show: int, writer=None) -> str:
    lines = [f"## {name}: days {', '.join(d.name for d in days)}", "",
             f"Trades on day d whose (timestamp, side, size) day d + 1 has too, by size (big: {BIG} and up), against the same "
             f"with day d + 1 shifted ({SHIFTS} random offsets); two days on: day d's on day d + 2, and of those not on d + 1:", "",
             "| product | days | all | small | big | baseline all / big | two days on / not on d + 1 |", "|---|---|---|---|---|---|---|"]
    listed = []
    for p in products:
        rows = study(days, p)
        for r in rows:
            two = r.get("two")
            lines.append(f"| {p} | {r['days'][0]} → {r['days'][1]} | {_pct(*r['all'][:2])} | {_pct(*r['small'][:2])} | {_pct(*r['big'][:2])} | "
                         f"{_base(r['all'][2])} / {_base(r['big'][2])} | "
                         + (f"{_base(two[0])} / {_base(two[1])}" if two else "-") + " |")
        if rows and (classes := flagged(rows)):
            listed.append((p, classes))
    if not listed:
        lines += ["", f"No product's trades recur on every pair of days (at least {FLAG:.0%} and {FLAG_LIFT}× the baseline)."]
        return "\n".join(lines)
    for p, classes in listed:
        w = where(days, p)
        lines += ["", f"**{p}** recurs ({', '.join(classes)}). Where its trades of size {BIG} and up print (past the wall mid in the taker's "
                  "disfavour, the visible depth on the side hit, how often that side was empty):", ""]
        for kind in ("recurring", "new"):
            rows = w[kind]
            if rows:
                lines.append(f"- {kind}: {len(rows)}, size {statistics.fmean(r[3] for r in rows):.1f}, past the wall mid "
                             f"{statistics.fmean(r[0] for r in rows):+.2f} (median {statistics.median(r[0] for r in rows):+.1f}), "
                             f"depth {statistics.fmean(r[1] for r in rows):.1f}, empty side {sum(r[2] for r in rows)}")
        events_ = predicted(days, p)
        lines += ["", f"Predicted for the day after {days[-1].name}: {len(events_)} events ({sum(e[3] for e in events_)} trades, "
                  f"{sum(e[3] for e in events_ if e[2] >= BIG)} of size {BIG} and up); the first {min(show, len(events_))}:", ""]
        lines.append(", ".join(f"{ts} {'buy' if s > 0 else 'sell'} {q}" + (f" ×{c}" if c > 1 else "") for ts, s, q, c in events_[:show]) or "none")
        if writer is not None:
            for ts, s, q, c in events_:
                writer.writerow([name, p, ts, "buy" if s > 0 else "sell", q, c])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    global BIG
    parser = argparse.ArgumentParser(prog="python -m experiments.day.repeats")
    add_dataset_arguments(parser, bot=False)
    parser.add_argument("--big", type=int, default=BIG, help=f"the size class cut (default: {BIG}, Baguette Fromage's)")
    parser.add_argument("--show", type=int, default=20, help="predicted events printed per product (default: 20)")
    parser.add_argument("--csv", type=Path, help="write every predicted event to this CSV (dataset, product, timestamp, side, size, count)")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    BIG = args.big
    runs = [(f"{alias} round {rnd}", alias, "prosperity", [rnd], None) for alias, rnd in DATASETS]
    if dataset:
        runs = [(dataset.name, dataset.data, dataset.format, list(dataset.days), list(dataset.products))]
    handle = args.csv.open("w", newline="") if args.csv else None
    writer = csv.writer(handle) if handle else None
    if writer:
        writer.writerow(["dataset", "product", "timestamp", "side", "size", "count"])
    try:
        for name, data, format_name, specs, products in runs:
            fmt = FORMATS[format_name]
            days = fmt.load_days(fmt.resolve_data_dir(data), specs)
            print(report(name, days, products or sorted({p for day in days for p in day.products}), args.show, writer) + "\n")
    finally:
        if handle:
            handle.close()


if __name__ == "__main__":
    main()
