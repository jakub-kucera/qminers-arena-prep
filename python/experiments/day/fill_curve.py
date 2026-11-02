"""What a quote at each distance from fair could fill, from the data alone, and what ours did fill.

usage (from the repo root): uv run python -m experiments.day.fill_curve
       uv run python -m experiments.day.fill_curve --data DIR --days 1 2 [--format F --products A,B] [--fair mid]
       uv run python -m experiments.day.fill_curve --data p3 --days 1 --results RESULTS   # RESULTS: a results ZIP or an --out folder

The grids tune `make_edge`, `make_inside` and `make_size` by PnL alone; this is the measurement
behind them (IDEAS.md, "A fill-rate curve", "A fill-size curve"). Run through our engine the curve
would only restate the engine's fill rule, so it comes in two halves.

1. **The market's offer, from the data alone.** A bid at distance d below fair (fair = the wall mid,
   or --fair) fills, on an exchange with price priority and nobody ahead of it, against every market
   trade printed at or below it: per tick, the chance that some trade prints at or beyond d on that
   side, and the lots it prints there. That is an upper bound on what a quote at d can fill, before
   any queue or rival. Sides are pooled (a bid at d and an ask at d), each trade counted on the side
   it reaches, as the engine lets one trade fill a buy and a sell. Split by:
     - spread: the best ask less the best bid, in ticks, when the quote was decided;
     - imbalance: s × (Vb − Va)/(Vb + Va) at the best level, s = +1 for a bid, in terciles of the
       product's own distribution: `favours` means the queue on our side is the larger one;
     - trade size: the printed trade's size against the product's median trade size m.
   With each distance, the value of such a fill per lot at --horizon ticks: d + s × (fair then −
   fair now), in ticks (edge plus the move; negative = the prints that reach far are informed).
   The fill-size curve: a quote of Q lots at d gets at most min(Q, the lots printed at or beyond d)
   a tick; its mean per tick for Q in SIZES (multiples of the median trade), and the value a lot (as above) of the lots a Q-lot quote
   gets beyond what the next smaller one gets: if the last lots fill only when the price runs
   through, their value falls below d.
2. **Our own fills, from the portal's results ZIP** (its layout is unknown until the day). RESULT_FILES
   and RESULT_COLUMNS map its files and columns onto ours, as python/arena/formats/snapshots.py's
   COLUMNS do for the data; edit only those names on the day. The stand-in is `arena.backtest --out`'s
   CSVs (a folder or a ZIP of it). For each tick our orders rested passively at distance d (from the
   orders file; an order that crossed the book is a take and left out), the share of those ticks with
   one of our fills, against the share where the market printed at or beyond d (half 1, on the same
   ticks): their ratio is the **queue share**, the fill model measured. A resting quote the next
   snapshot crossed (source "cross") counts at the tick it was quoted, as a fill and as the market
   reaching it (before 2026-10-28 no such fill matched a quote: the fourth audit's R9). In lots: our filled lots against
   min(our size, the lots printed at or beyond d). A per-tick backtest under `--match-trades all`
   gives 1 by construction (every print at or beyond the quote fills it), `worse` less, and the
   portal's ratio is what to set the backtest's `--fill-ratio`, `--match-trades` and queue to.

3. **Choosing the quote by state** (Guilbaud & Pham: best, one tick inside or cross, by spread). From
   half 1's offer, a one-lot quote at d is worth P(a print at or beyond d) × (d + the move) a side-tick.
   Per held-out day: on the other days, the best d for each spread bin and the best single d; on the
   held-out day, the value of each choice. An upper bound, as half 1: nobody ahead of the quote, so
   it favours joining the best at a wide spread, which a queue denies. On P3 and P4 the per-spread
   choice wins here on every held-out day yet loses under `worse` and `--resting` once traded
   (`experiments.study.quote_by_state`): read it only with half 2's queue share from the day.

Distances are in each product's ticks (Day.info, as arena.diagnose), from fair at the tick the quote
was decided; a quote's distance is rounded to the nearest half tick. With --data the one dataset
replaces DATASETS.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import statistics as st
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from arena.cli import add_dataset_arguments, dataset_from
from arena.formats import FORMATS

DATASETS = [  # (data alias, round, products): the market-making rounds of P3 and P4
    ("p3", "1", ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]),
    ("p4", "1", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
]
DISTANCES = (0, 0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10)
SHORT = (0.5, 1, 2, 4, 8)  # the distances the split tables show
SIZES = (1, 2, 5, 10, 20, 50)  # quote sizes, in multiples of the product's median trade
HORIZON = 20

# ---------------------------------------------------------------------------- the results ZIP's layout (edit on the day)

# File name patterns inside the ZIP (or folder); {day} matches the day's label. Our --out names them so.
RESULT_FILES = {"fills": "{day}_fills.csv", "orders": "{day}_orders.csv"}
# Our name -> the ZIP's column. None: the ZIP has no such column. "side": a BUY/SELL column, when
# the quantity is unsigned; "source": how a fill matched (ours: book, trade, cross); without it,
# a fill is passive if its price didn't cross the book at its tick.
RESULT_COLUMNS = {
    "fills": {"timestamp": "timestamp", "product": "product", "price": "price", "quantity": "quantity",
              "side": None, "order_id": "order_id", "source": "source"},
    "orders": {"timestamp": "timestamp", "id": "id", "product": "product", "price": "price", "quantity": "quantity",
               "side": None},
}
SIDES = {"BUY": 1, "B": 1, "BID": 1, "SELL": -1, "S": -1, "ASK": -1}
RESULT_DELIMITER = ","
RESULT_PRICE_SCALE = 1  # the data's price units per ZIP price unit (100 if the ZIP has currency and the data cents)
DAY_NAMES: dict[str, str] = {}  # the ZIP's day label -> the data's Day.name, when they differ
PASSIVE_SOURCES = {"trade", "cross"}


# ---------------------------------------------------------------------------- half 1: the market's offer


def unit_of(day, product) -> float:
    info = day.info.get(product, {})
    return round(info["tick"] / info["unit"]) if "tick" in info and "unit" in info else 1


def fair_of(book, how: str) -> float | None:
    if not book.bids or not book.asks:
        return None
    return book.wall_mid if how == "wall_mid" else book.mid


def spread_bin(s: float) -> str:
    return f"{s:g}" if s <= 4 else "5-8" if s <= 8 else "9-16" if s <= 16 else ">16"


def ticks_of(day, product: str, how: str = "wall_mid", horizon: int = HORIZON) -> list[dict]:
    """Per tick with both sides quoted: the fair, the spread and ρ, each side's prints as (distance in
    ticks, lots), and the fair's move to `horizon` ticks later (the last known fair at the day's end)."""
    unit = unit_of(day, product)
    fairs = []
    for tick in day.ticks:
        book = tick.books.get(product)
        fairs.append(fair_of(book, how) if book is not None else None)
    rows = []
    for i, tick in enumerate(day.ticks):
        book, fair = tick.books.get(product), fairs[i]
        if fair is None:
            continue
        later = next((f for f in reversed(fairs[i:min(i + horizon, len(fairs) - 1) + 1]) if f is not None), fair)
        (pb, vb), (pa, va) = book.bids[0], book.asks[0]
        trades = tick.trades.get(product, [])
        rows.append({
            "i": i, "timestamp": tick.timestamp, "fair": fair, "unit": unit, "spread": (pa - pb) / unit, "rho": (vb - va) / (vb + va),
            "bid": [((fair - t.price) / unit, abs(t.quantity)) for t in trades],
            "ask": [((t.price - fair) / unit, abs(t.quantity)) for t in trades],
            "move": (later - fair) / unit, "best_bid": pb, "best_ask": pa,
        })
    return rows


def side_views(rows: list[dict]):
    """Each tick twice, as a bid's and an ask's view: (row, s, prints, s×ρ, s×move)."""
    for r in rows:
        yield r, 1, r["bid"], r["rho"], r["move"]
        yield r, -1, r["ask"], -r["rho"], -r["move"]


def tercile_cut(rows: list[dict]) -> float:
    """c with P(|ρ| < c) = 1/3: s×ρ below −c, between, above c are the three terciles of a symmetric distribution."""
    values = sorted(abs(r["rho"]) for r in rows)
    return values[len(values) // 3] if values else 0.0


def imbalance_bin(x: float, cut: float) -> str:
    return "favours" if x > cut else "against" if x < -cut else "even"


def size_bin(q: int, m: float) -> str:
    return "<=m/2" if q <= m / 2 else "<=m" if q <= m else "<=2m" if q <= 2 * m else ">2m"


def curve(rows_by_day: list[list[dict]], distances=DISTANCES, horizon: int = HORIZON) -> dict:
    """Half 1 for one product over its days."""
    rows = [r for day in rows_by_day for r in day]
    out: dict = {"ticks": len(rows), "days": len(rows_by_day), "horizon": horizon}
    cut = tercile_cut(rows)
    traded = [q for r in rows for _, q in r["bid"]]
    m = st.median(traded) if traded else 1
    sizes = sorted({max(1, round(k * m)) for k in SIZES})
    out["cut"], out["median_size"], out["sizes"] = cut, m, sizes
    out["spread"] = st.median(r["spread"] for r in rows) if rows else None
    # The main curve, per day and pooled: P(a print at or beyond d) per side-tick, lots per side-tick, value per lot.
    out["curve"] = {}
    for d in distances:
        per_day = []
        hits = lots = 0
        value, value_lots = 0.0, 0
        for day in rows_by_day:
            day_hits = 0
            for r, s, prints, _, move in side_views(day):
                q = sum(lot for dist, lot in prints if dist >= d)
                if q:
                    day_hits += 1
                    lots += q
                    value += q * (d + move)
                    value_lots += q
            hits += day_hits
            per_day.append(day_hits / (2 * len(day)) if day else 0.0)
        n = 2 * len(rows)
        out["curve"][d] = {"p": hits / n if n else 0.0, "lots": lots / n if n else 0.0, "days": per_day,
                           "value": value / value_lots if value_lots else None}
    # Splits: P(print at or beyond d) by spread and by imbalance; prints per 1,000 side-ticks by size class.
    by = {"spread": defaultdict(lambda: [0, defaultdict(int)]), "imbalance": defaultdict(lambda: [0, defaultdict(int)])}
    by_size = defaultdict(lambda: defaultdict(int))
    fill_size = defaultdict(lambda: [0.0, 0.0])  # (Q, d) -> [lots, their value at the horizon]
    for r, s, prints, x, move in side_views(rows):
        keys = {"spread": spread_bin(r["spread"]), "imbalance": imbalance_bin(x, cut)}
        for name, key in keys.items():
            by[name][key][0] += 1
        for d in distances:
            q = sum(lot for dist, lot in prints if dist >= d)
            if q:
                for name, key in keys.items():
                    by[name][key][1][d] += 1
                for size in sizes:
                    got = min(size, q)
                    fill_size[(size, d)][0] += got
                    fill_size[(size, d)][1] += got * (d + move)
            for dist, lot in prints:
                if dist >= d:
                    by_size[size_bin(lot, m)][d] += 1
    out["by"] = {name: {key: (n, {d: c / n for d, c in hits.items()}) for key, (n, hits) in table.items()} for name, table in by.items()}
    out["by_size"] = {key: {d: 1000 * c / (2 * len(rows)) for d, c in counts.items()} for key, counts in by_size.items()}
    out["fill_size"] = {}  # (Q, d) -> (lots a side-tick, the value a lot of the lots beyond the next smaller Q's)
    for (size, d), (lots, value) in fill_size.items():
        smaller = [q for q in sizes if q < size]
        lots0, value0 = fill_size[(smaller[-1], d)] if smaller else (0.0, 0.0)
        out["fill_size"][(size, d)] = (lots / (2 * len(rows)), (value - value0) / (lots - lots0) if lots - lots0 > 1e-9 else None)
    return out


def quote_values(rows: list[dict], distances) -> dict[str, dict[float, list[float]]]:
    """Spread bin -> d -> [summed value of a one-lot quote at d (d + move when a print reaches it), side-ticks]."""
    out: dict = defaultdict(lambda: {d: [0.0, 0] for d in distances})
    for r, s, prints, _, move in side_views(rows):
        cell = out[spread_bin(r["spread"])]
        far = max((dist for dist, _ in prints), default=None)
        for d in distances:
            cell[d][1] += 1
            if far is not None and far >= d:
                cell[d][0] += d + move
    return out


def by_state(rows_by_day: list[list[dict]], distances) -> list[tuple[str, dict, float, float, float]]:
    """Per held-out day: (day index, the per-spread choice fitted on the others, the single d, the value a side-tick
    on the held-out day of the per-spread choice and of the single d)."""
    out = []
    for k, test in enumerate(rows_by_day):
        train = quote_values([r for j, day in enumerate(rows_by_day) if j != k for r in day], distances)
        pooled = {d: sum(cell[d][0] for cell in train.values()) for d in distances}
        single = max(distances, key=pooled.get)
        choice = {key: max(distances, key=lambda d: cell[d][0]) for key, cell in train.items()}
        held = quote_values(test, distances)
        n = sum(cell[single][1] for cell in held.values())
        state = sum(cell[choice.get(key, single)][0] for key, cell in held.items()) / n if n else 0.0
        flat = sum(cell[single][0] for cell in held.values()) / n if n else 0.0
        out.append((str(k), choice, single, state, flat))
    return out


# ---------------------------------------------------------------------------- half 2: our fills from the results ZIP


def _pattern(template: str) -> re.Pattern:
    return re.compile("^(?:.*/)?" + re.escape(template).replace(re.escape("{day}"), "(?P<day>.+)") + "$")


def _read_table(text: str, columns: dict[str, str | None]) -> list[dict]:
    out = []
    for raw in csv.DictReader(io.StringIO(text), delimiter=RESULT_DELIMITER):
        row = {ours: raw.get(theirs, "") for ours, theirs in columns.items() if theirs is not None}
        if not row.get("timestamp"):
            continue
        quantity = float(row["quantity"])
        if columns.get("side"):
            quantity = abs(quantity) * SIDES[raw[columns["side"]].strip().upper()]
        row.update(timestamp=int(float(row["timestamp"])), price=float(row["price"]) * RESULT_PRICE_SCALE, quantity=quantity)
        out.append(row)
    return out


def read_results(source: Path) -> dict[str, dict[str, list[dict]]]:
    """{day label: {"fills": rows, "orders": rows}} from a results ZIP or a folder, through RESULT_FILES and RESULT_COLUMNS."""
    if source.is_dir():
        files = {str(p.relative_to(source)): p.read_text for p in source.rglob("*") if p.is_file()}
    else:
        archive = zipfile.ZipFile(source)
        files = {name: (lambda name=name: archive.read(name).decode("utf-8-sig")) for name in archive.namelist() if not name.endswith("/")}
    out: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"fills": [], "orders": []})
    for kind, template in RESULT_FILES.items():
        pattern = _pattern(template)
        for name, read in sorted(files.items()):
            match = pattern.match(name)
            if match:
                out[DAY_NAMES.get(match["day"], match["day"])][kind] += _read_table(read(), RESULT_COLUMNS[kind])
    return dict(out)


def queue_share(day, product: str, results: dict[str, list[dict]], how: str = "wall_mid") -> dict:
    """Half 2 for one product and day: per half-tick distance, the ticks our passive quotes rested there, the
    share with one of our fills, the market's share with a print at or beyond it, and the same in lots."""
    ordered = ticks_of(day, product, how)
    rows = {r["timestamp"]: r for r in ordered}
    before = {b["timestamp"]: a["timestamp"] for a, b in zip(ordered, ordered[1:])}
    quoted: dict[tuple[int, int], list[tuple[float, float]]] = defaultdict(list)  # (timestamp, side) -> [(distance, lots)]
    for order in results["orders"]:
        r = rows.get(order["timestamp"])
        if order["product"] != product or r is None or not order["quantity"]:
            continue
        s = 1 if order["quantity"] > 0 else -1
        if (s > 0 and order["price"] >= r["best_ask"]) or (s < 0 and order["price"] <= r["best_bid"]):
            continue  # a take
        quoted[(order["timestamp"], s)].append((round(2 * s * (r["fair"] - order["price"]) / r["unit"]) / 2, abs(order["quantity"])))
    filled: dict[tuple[int, int, float], float] = defaultdict(float)  # (timestamp, side, distance) -> our lots
    crossed: dict[tuple[int, int, float], float] = defaultdict(float)  # ...of those, filled by the next snapshot crossing the quote
    for fill in results["fills"]:
        timestamp = fill["timestamp"]
        source = fill.get("source")
        if source == "cross":  # the quote rested from the tick before, when it was recorded (as quote_markouts keys it)
            timestamp = before.get(timestamp)
        r = rows.get(timestamp)
        if fill["product"] != product or r is None or not fill["quantity"]:
            continue
        s = 1 if fill["quantity"] > 0 else -1
        if source:
            if source not in PASSIVE_SOURCES:
                continue
        elif (s > 0 and fill["price"] >= r["best_ask"]) or (s < 0 and fill["price"] <= r["best_bid"]):
            continue
        key = (timestamp, s, round(2 * s * (r["fair"] - fill["price"]) / r["unit"]) / 2)
        filled[key] += abs(fill["quantity"])
        if source == "cross":
            crossed[key] += abs(fill["quantity"])
    out = defaultdict(lambda: {"ticks": 0, "ours": 0, "market": 0, "our_lots": 0.0, "market_lots": 0.0})
    for (timestamp, s), quotes in quoted.items():
        r = rows[timestamp]
        prints = r["bid"] if s > 0 else r["ask"]
        for d, lots in quotes:
            cell = out[d]
            cell["ticks"] += 1
            ours = filled.get((timestamp, s, d), 0.0)
            market = sum(q for dist, q in prints if dist >= d) + crossed.get((timestamp, s, d), 0.0)  # a crossing book reached the quote too
            cell["ours"] += ours > 0
            cell["market"] += market > 0
            cell["our_lots"] += min(ours, lots)
            cell["market_lots"] += min(market, lots)
    return dict(out)


# ---------------------------------------------------------------------------- output


def _spread_order(key: str) -> float:
    return float(key.split("-")[0].lstrip(">")) + (0.5 if key.startswith(">") else 0)


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.1f}%"


def print_curve(label: str, product: str, c: dict, distances) -> None:
    short = [d for d in SHORT if d in distances] or list(distances)[:5]
    print(f"\n### {label} {product}: {c['ticks']:,} ticks over {c['days']} days, median spread {c['spread']:g} ticks, "
          f"median trade {c['median_size']:g} lots, imbalance tercile cut {c['cut']:.2f}\n")
    print(f"| d (ticks) | P(print at or beyond d) a side a tick | per day | lots a side a tick | value a lot at {c['horizon']} (ticks) |")
    print("|---|---|---|---|---|")
    for d in distances:
        k = c["curve"][d]
        value = "-" if k["value"] is None else f"{k['value']:+.2f}"
        print(f"| {d:g} | {_pct(k['p'])} | {' / '.join(_pct(x) for x in k['days'])} | {k['lots']:.3f} | {value} |")
    for name in ("spread", "imbalance"):
        print(f"\nP(print at or beyond d) by {name} (side-ticks in the state):\n")
        print(f"| {name} | side-ticks | " + " | ".join(f"d={d:g}" for d in short) + " |")
        print("|---|---|" + "---|" * len(short))
        order = sorted(c["by"][name], key=_spread_order) if name == "spread" else [k for k in ("against", "even", "favours") if k in c["by"][name]]
        for key in order:
            n, p = c["by"][name][key]
            print(f"| {key} | {n:,} | " + " | ".join(_pct(p.get(d, 0.0)) for d in short) + " |")
    print(f"\nPrints at or beyond d per 1,000 side-ticks, by the trade's size (m = {c['median_size']:g} lots):\n")
    print("| size | " + " | ".join(f"d={d:g}" for d in short) + " |")
    print("|---|" + "---|" * len(short))
    for key in ("<=m/2", "<=m", "<=2m", ">2m"):
        if key in c["by_size"]:
            print(f"| {key} | " + " | ".join(f"{c['by_size'][key].get(d, 0.0):.1f}" for d in short) + " |")
    print("\nThe fill-size curve: lots a side a tick a Q-lot quote at d could fill (and the value a lot at "
          f"{c['horizon']} ticks of the lots beyond the next smaller Q's, in ticks):\n")
    print("| Q | " + " | ".join(f"d={d:g}" for d in short) + " |")
    print("|---|" + "---|" * len(short))
    for size in c["sizes"]:
        cells = []
        for d in short:
            lots, value = c["fill_size"].get((size, d), (0.0, None))
            cells.append(f"{lots:.3f} ({'-' if value is None else f'{value:+.2f}'})")
        print(f"| {size} | " + " | ".join(cells) + " |")


def print_share(label: str, product: str, cells: dict) -> None:
    print(f"\n### {label} {product}: our passive quotes against the market's prints on the same ticks\n")
    print("| d (ticks) | ticks quoted | our fill share | market print share | queue share (ours / market) | lots: ours / market |")
    print("|---|---|---|---|---|---|")
    for d in sorted(cells):
        c = cells[d]
        if c["ticks"] < 20:
            continue
        ratio = f"{c['ours'] / c['market']:.2f}" if c["market"] else "-"
        lots = f"{c['our_lots'] / c['market_lots']:.2f}" if c["market_lots"] else "-"
        print(f"| {d:g} | {int(c['ticks']):,} | {_pct(c['ours'] / c['ticks'])} | {_pct(c['market'] / c['ticks'])} | {ratio} | {lots} |")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.fill_curve")
    add_dataset_arguments(parser, bot=False)
    parser.add_argument("--fair", choices=("wall_mid", "mid"), default="wall_mid", help="the fair distances are measured from (default: wall_mid)")
    parser.add_argument("--distances", help=f"comma-separated distances in ticks (default: {','.join(f'{d:g}' for d in DISTANCES)})")
    parser.add_argument("--horizon", type=int, default=HORIZON, help=f"ticks ahead for a fill's value (default: {HORIZON})")
    parser.add_argument("--results", type=Path, help="a results ZIP, or an arena.backtest --out folder, of a run on --data's days: half 2")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if args.results and not dataset:
        parser.error("--results needs --data and --days: the days the run was on")
    distances = tuple(float(x) for x in args.distances.split(",")) if args.distances else DISTANCES
    datasets = [(f"{alias} r{rnd}", alias, "prosperity", [rnd], products) for alias, rnd, products in DATASETS]
    if dataset:
        datasets = [(dataset.name, dataset.data, dataset.format, list(dataset.days), list(dataset.products))]
    print(f"1. What a quote at distance d from the {args.fair.replace('_', ' ')} could fill: the market's prints at or beyond d, "
          "a side a tick, before any queue.")
    loaded, states = {}, {}
    for label, data, format_name, specs, products in datasets:
        fmt = FORMATS[format_name]
        days = fmt.load_days(fmt.resolve_data_dir(data), specs)
        loaded[label] = days
        for product in products:
            rows = [ticks_of(day, product, args.fair, args.horizon) for day in days if product in day.products]
            if any(rows):
                print_curve(label, product, curve(rows, distances, args.horizon), distances)
                states[(label, product)] = rows
    print("\n3. The quote's distance chosen per spread bin on the other days, against one distance for all, scored on the held-out day "
          "(a one-lot quote's value a side-tick, in ticks)")
    for (label, product), rows in states.items():
        days = [day for day in rows if day]
        if len(days) < 2:
            continue
        for k, choice, single, state, flat in by_state(days, distances):
            table = ", ".join(f"{key}: {d:g}" for key, d in sorted(choice.items(), key=lambda kv: _spread_order(kv[0])))
            print(f"   {label} {product} day {int(k) + 1}: per spread ({table}) {state:.4f} against {single:g} for all {flat:.4f} ({(state / flat - 1) if flat else 0:+.1%})")
    if args.results:
        results = read_results(args.results)
        (label, _, _, _, products), days = datasets[0], loaded[datasets[0][0]]
        print(f"\n2. Our fills in {args.results} against the market's prints (the queue share)")
        missing = [day.name for day in days if day.name not in results]
        if missing:
            print(f"   no results for {', '.join(missing)} (found {', '.join(sorted(results)) or 'nothing'}): check RESULT_FILES and DAY_NAMES")
        for product in products:
            cells = defaultdict(lambda: defaultdict(float))
            for day in days:
                if day.name in results and product in day.products:
                    for d, c in queue_share(day, product, results[day.name], args.fair).items():
                        for key, value in c.items():
                            cells[d][key] += value
            if cells:
                print_share(label, product, cells)


if __name__ == "__main__":
    main(sys.argv[1:])
