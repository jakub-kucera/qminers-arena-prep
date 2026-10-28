"""Does one product's price lead another's? A lead-lag table for any products, from the data alone.

usage (from the repo root): uv run python -m experiments.day.lead_lag
       uv run python -m experiments.day.lead_lag --data DIR --days 1 2 [--format F --products A,B] [--horizons 20,50,100,200] [--lags 250]

Each product's price is its wall mid (the mid when a side has no level), carried forward over
ticks without a book, in the product's ticks (Day.info). For every ordered pair (A, B) and each
horizon h in HORIZONS (or --horizons), at every tick where A's price moved:

  follow    B's mean move over the next h ticks, signed by A's move (in B's ticks), less B's mean
            move over h ticks that day: what B does after A moves, beyond a drift both share. Compare it with B's half-spread: a lead worth trading moves B by more
            than a taker pays to cross.
  own       the same for B after B's own move: a market whose price bounces shows a negative
            `own` (the bid-ask bounce), and a lead must beat that baseline to add anything.
  corr      the correlation of A's one-tick change with B's next h ticks' change, over all ticks.

With --lags K, a second test for a lead at one exact lag: corr(ΔA_t, ΔB_{t+k}) of the one-tick changes
for every k from 1 to K, pooled over the days. A pair is listed when its largest |corr| reaches LAG_Z/√n
with the same sign on every day; with it, B's ticks per A tick at that lag, and how far B's next k ticks
are predicted from A's last k (that slope times A's k-tick sd) against B's half-spread. `follow` can't
see such a lead at a long horizon: a small exact lag is diluted in B's whole move. The cost grows with
pairs × K, so give --products a family.

A pair is listed when its `follow` at the longest horizon has the same sign on every day, a t-statistic
of at least T_STAT (divided by the square root of the horizon, since consecutive windows overlap) and
a size of at least MIN_FOLLOW of B's half-spread; the reverse direction is printed beside it, so
a lead shows as a large A -> B and a small B -> A. The same-tick correlations come first: products
that move together on the same tick are related, and a lead, if any, is among them.

The built-in datasets are controls: P3 round 2's baskets and their legs, and P3 round 3's rock and
its vouchers (related products), and P4 round 1's two products (unrelated). Results: IDEAS.md,
"A lead-lag table for any products". With --data (the day's download) every product there (or
--products) is read on those days.
"""

from __future__ import annotations

import argparse
import math
import statistics
from operator import mul

from arena.cli import add_dataset_arguments, dataset_from
from arena.formats import FORMATS
from arena.model import Day

DATASETS = [  # (data alias, round, products)
    ("p3", "2", ["PICNIC_BASKET1", "PICNIC_BASKET2", "CROISSANTS", "JAMS", "DJEMBES"]),
    ("p3", "3", ["VOLCANIC_ROCK", "VOLCANIC_ROCK_VOUCHER_9500", "VOLCANIC_ROCK_VOUCHER_10000", "VOLCANIC_ROCK_VOUCHER_10500"]),
    ("p4", "1", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
]
HORIZONS = (1, 5, 20)
MIN_FOLLOW = 0.25  # a pair is listed when B follows A by at least this share of B's half-spread at the longest horizon
T_STAT = 3.0  # ...and its follow's |mean / standard error| is at least this
LAG_Z = 4.5  # --lags lists a pair whose largest |corr| over the lags reaches this many standard errors (1/√n)


def prices(day: Day, product: str) -> tuple[list[float], float | None]:
    """The product's wall mid a tick in its own ticks, carried forward (and back to the first), and its
    median half-spread in ticks (None without a two-sided book)."""
    info = day.info.get(product, {})
    tick = round(info["tick"] / info["unit"]) if "tick" in info and "unit" in info else 1
    out: list[float | None] = []
    spreads = []
    for t in day.ticks:
        book = t.books.get(product)
        if book is None or not (book.bids and book.asks):
            out.append(out[-1] if out else None)
            continue
        spreads.append((book.asks[0][0] - book.bids[0][0]) / tick)
        price = book.wall_mid if book.wall_mid is not None else (book.bids[0][0] + book.asks[0][0]) / 2
        out.append(price / tick)
    first = next((p for p in out if p is not None), 0.0)
    return [first if p is None else p for p in out], (statistics.median(spreads) / 2 if spreads else None)


def follow(a: list[float], b: list[float], h: int) -> tuple[float, float, int]:
    """Over ticks where `a` moved, sign(a's move) x b's move over the next h ticks, less b's mean move
    over h ticks that day (so a drift both share isn't read as a lead): its sum, sum of squares and count."""
    ticks = range(1, len(a) - h)
    drift = statistics.fmean(b[t + h] - b[t] for t in ticks) if ticks else 0.0
    total, squares, n = 0.0, 0.0, 0
    for t in ticks:
        move = a[t] - a[t - 1]
        if move:
            x = (b[t + h] - b[t] - drift) * (1 if move > 0 else -1)
            total += x
            squares += x * x
            n += 1
    return total, squares, n


def correlation(a: list[float], b: list[float], h: int) -> float | None:
    """The correlation of a's one-tick change at t with b's change over (t, t + h]; h = 0 is the same tick's."""
    if h == 0:
        x = [a[t] - a[t - 1] for t in range(1, len(a))]
        y = [b[t] - b[t - 1] for t in range(1, len(b))]
    else:
        x = [a[t] - a[t - 1] for t in range(1, len(a) - h)]
        y = [b[t + h] - b[t] for t in range(1, len(b) - h)]
    try:
        return statistics.correlation(x, y)
    except statistics.StatisticsError:  # a series that never moves
        return None


def study(days: list[Day], products: list[str], horizons: tuple[int, ...] = HORIZONS) -> dict:
    """Per day, every product's prices; then the same-tick correlations and, per ordered pair and
    horizon, the follow pooled and per day, the own baseline and the correlation."""
    series = [{p: prices(day, p) for p in products} for day in days]
    half = {p: statistics.median([s[p][1] for s in series if s[p][1] is not None] or [0.0]) for p in products}
    same = {}
    for i, a in enumerate(products):
        for b in products[i + 1:]:
            values = [c for s in series if (c := correlation(s[a][0], s[b][0], 0)) is not None]
            same[(a, b)] = statistics.fmean(values) if values else None
    pairs = {}
    for a in products:
        for b in products:
            for h in horizons:
                per_day = [follow(s[a][0], s[b][0], h) for s in series]
                total, squares, n = (sum(f[k] for f in per_day) for k in range(3))
                own = [follow(s[b][0], s[b][0], h) for s in series]
                own_total, own_n = sum(f[0] for f in own), sum(f[2] for f in own)
                mean = total / n if n else None
                sd = math.sqrt(max(squares / n - mean * mean, 0.0) * n / (n - 1)) if n > 1 else None
                corrs = [c for s in series if (c := correlation(s[a][0], s[b][0], h)) is not None] if a != b else []
                pairs[(a, b, h)] = {
                    "follow": mean,
                    "n": n,
                    "t": mean / (sd / math.sqrt(n)) / math.sqrt(h) if sd else None,  # overlapping windows: about n / h independent
                    "days": [t / k if k else None for t, _, k in per_day],
                    "own": own_total / own_n if own_n else None,
                    "corr": statistics.fmean(corrs) if corrs else None,
                }
    return {"half": half, "same": same, "pairs": pairs, "horizons": tuple(horizons)}


def leads(result: dict, products: list[str]) -> list[tuple[str, str]]:
    """The ordered pairs whose follow at the longest horizon keeps its sign every day and is at least
    MIN_FOLLOW of B's half-spread, largest first."""
    h = result["horizons"][-1]
    found = []
    for a in products:
        for b in products:
            if a == b:
                continue
            r = result["pairs"][(a, b, h)]
            days = [d for d in r["days"] if d is not None]
            half = result["half"][b]
            if r["follow"] is None or not days or not half:
                continue
            steady = all(d > 0 for d in days) or all(d < 0 for d in days)
            if steady and r["t"] is not None and abs(r["t"]) >= T_STAT and abs(r["follow"]) >= MIN_FOLLOW * half:
                found.append((abs(r["follow"]) / half, a, b))
    return [(a, b) for _, a, b in sorted(found, reverse=True)]


def lagged(xs: list[list[float]], ys: list[list[float]], lags) -> tuple[dict[int, float], list[dict[int, float]], int]:
    """corr(Δx_t, Δy_{t+k}) for each k in lags: pooled over the days (each day's changes de-meaned), per
    day, and the number of changes."""
    num: dict[int, float] = {k: 0.0 for k in lags}
    xx = yy = 0.0
    n = 0
    per_day = []
    for x, y in zip(xs, ys):
        dx = [b - a for a, b in zip(x, x[1:])]
        dy = [b - a for a, b in zip(y, y[1:])]
        if len(dx) < 2:
            continue
        mx, my = statistics.fmean(dx), statistics.fmean(dy)
        dx = [v - mx for v in dx]
        dy = [v - my for v in dy]
        sxx, syy = sum(map(mul, dx, dx)), sum(map(mul, dy, dy))
        xx, yy, n = xx + sxx, yy + syy, n + len(dx)
        day = {}
        for k in lags:
            value = sum(map(mul, dx[:len(dx) - k], dy[k:]))
            num[k] += value
            day[k] = value / math.sqrt(sxx * syy) if sxx and syy else 0.0
        per_day.append(day)
    norm = math.sqrt(xx * yy)
    return {k: v / norm if norm else 0.0 for k, v in num.items()}, per_day, n


def lag_scan(days: list[Day], products: list[str], max_lag: int) -> list[dict]:
    """The ordered pairs whose one-tick changes correlate at one exact lag (1..max_lag) beyond LAG_Z/√n,
    with the same sign every day, largest first."""
    loaded = {p: [prices(day, p) for day in days] for p in products}
    series = {p: [xs for xs, _ in loaded[p]] for p in products}
    half = {p: statistics.median([h for _, h in loaded[p] if h is not None] or [0.0]) for p in products}
    sd = {}
    for p in products:
        moves = [b - a for xs in series[p] for a, b in zip(xs, xs[1:])]
        sd[p] = statistics.pstdev(moves) if len(moves) > 1 else 0.0
    found = []
    for a in products:
        for b in products:
            if a == b or not sd[a] or not sd[b]:
                continue
            corr, per_day, n = lagged(series[a], series[b], range(1, max_lag + 1))
            k = max(corr, key=lambda k: abs(corr[k]))
            days_ = [d[k] for d in per_day]
            if n and abs(corr[k]) >= LAG_Z / math.sqrt(n) and (all(d > 0 for d in days_) or all(d < 0 for d in days_)):
                slope = corr[k] * sd[b] / sd[a]
                found.append({"a": a, "b": b, "lag": k, "corr": corr[k], "days": days_, "n": n, "slope": slope,
                              "predicted": abs(slope) * sd[a] * math.sqrt(k), "half": half[b]})
    return sorted(found, key=lambda r: -abs(r["corr"]))


def lag_report(found: list[dict], max_lag: int) -> str:
    lines = ["", f"Exact lags: corr(ΔA at t, ΔB at t + k) for k = 1–{max_lag}, listed when the largest reaches {LAG_Z:g}/√n "
             "with one sign every day; B's next k ticks predicted from A's last k (B ticks per A tick × A's k-tick sd):", ""]
    if not found:
        return "\n".join(lines + ["none"])
    lines += ["| A -> B | lag | corr | per day | √n × corr | B ticks per A tick | predicted over the lag | B's half-spread |",
              "|---|---|---|---|---|---|---|---|"]
    for r in found:
        lines.append(f"| {r['a']} -> {r['b']} | {r['lag']} | {r['corr']:+.4f} | {' / '.join(f'{d:+.3f}' for d in r['days'])} | "
                     f"{r['corr'] * math.sqrt(r['n']):+.1f} | {r['slope']:+.3f} | {r['predicted']:.1f} | {r['half']:g} |")
    return "\n".join(lines)


def _num(value: float | None, fmt: str) -> str:
    return "-" if value is None else format(value, fmt)


def report(name: str, result: dict, products: list[str]) -> str:
    lines = [f"## {name}", "", "Same-tick correlation of the one-tick changes (mean over the days):", "",
             "| | " + " | ".join(products) + " |", "|---|" + "---|" * len(products)]
    for a in products:
        cells = ["" if a == b else _num(result["same"].get((a, b), result["same"].get((b, a))), "+.2f") for b in products]
        lines.append(f"| {a} | " + " | ".join(cells) + " |")
    found = leads(result, products)
    horizons = result["horizons"]
    h = horizons[-1]
    lines += ["", f"Leads: B's move after A's, signed by A's, in B's ticks, at {', '.join(map(str, horizons))} ticks; "
              f"listed when at {h} it keeps its sign every day, |t| reaches {T_STAT:g} and its size {MIN_FOLLOW:g} of B's half-spread:", ""]
    if not found:
        lines.append("none")
        return "\n".join(lines)
    lines += ["| A -> B | A's moves | follow | B -> A | own (B) | B's half-spread | per day at " + str(h) + " | t at " + str(h) + " | corr at " + str(h) + " |",
              "|---|---|---|---|---|---|---|---|---|"]
    for a, b in found:
        rows = [result["pairs"][(a, b, x)] for x in horizons]
        back = [result["pairs"][(b, a, x)] for x in horizons]
        follows = " / ".join(_num(r["follow"], "+.2f") for r in rows)
        reverse = " / ".join(_num(r["follow"], "+.2f") for r in back)
        own = " / ".join(_num(r["own"], "+.2f") for r in rows)
        days = ", ".join(_num(d, "+.2f") for d in rows[-1]["days"])
        lines.append(f"| {a} -> {b} | {rows[0]['n']:,} | {follows} | {reverse} | {own} | {result['half'][b]:g} | {days} | "
                     f"{_num(rows[-1]['t'], '+.1f')} | {_num(rows[-1]['corr'], '+.3f')} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.lead_lag")
    add_dataset_arguments(parser, bot=False)
    parser.add_argument("--lags", type=int, default=0, metavar="K",
                        help="also test every exact lag 1..K by the one-tick changes' correlation (default: 0, off)")
    parser.add_argument("--horizons", default=",".join(map(str, HORIZONS)),
                        help="comma-separated horizons in ticks, the last one the listing's (default: %(default)s)")
    args = parser.parse_args(argv)
    try:
        horizons = tuple(sorted({int(h) for h in args.horizons.split(",") if h.strip()}))
    except ValueError:
        parser.error(f"--horizons wants whole numbers of ticks, got {args.horizons!r}")
    if not horizons or horizons[0] < 1:
        parser.error("--horizons wants positive numbers of ticks")
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    datasets = [(f"{alias} round {rnd}", alias, "prosperity", [rnd], products) for alias, rnd, products in DATASETS]
    if dataset:
        datasets = [(dataset.name, dataset.data, dataset.format, list(dataset.days), list(dataset.products))]
    for name, data, format_name, specs, products in datasets:
        fmt = FORMATS[format_name]
        days = fmt.load_days(fmt.resolve_data_dir(data), specs)
        text = report(name, study(days, products, horizons), products)
        if args.lags > 0:
            text += "\n" + lag_report(lag_scan(days, products, args.lags), args.lags)
        print(text + "\n")


if __name__ == "__main__":
    main()
