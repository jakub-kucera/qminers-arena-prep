"""What an agent market's book says about its hidden value: the fair modes against ABIDES's fundamental,
and whether large moves continue.

usage (from the repo root, after `uv run python -m experiments.abides_days generate --days 10`):
  uv run python -m experiments.abides_study                     # the ABIDES days, P3 round 1's Kelp as the control
  uv run python -m experiments.abides_study --data D --days 1 --products P [--format F]

Part 1, the fair modes (as the template's `price`: mid, wall_mid, sized_mid with wall_size 15,
weighted_mid), each smoothed as the template smooths (s * previous + (1 - s) * now), against the
value they stand for. Where a fundamental file exists (ABIDES's and arena.sim's answer key), the
error is against the fundamental at the same tick; for every product also against the mid
HORIZON ticks ahead (what a quote's markout sees). Root mean square, in the product's ticks.

Part 2, continuation: after the wall mid moved by at least k ticks over the last LOOKBACK ticks,
its mean move over the next HORIZON ticks, signed by the past move (positive: the move continues,
as with momentum traders or stop cascades; negative: it reverts). Per day, so a sign that holds on
every day can be told from one that doesn't. Results: IDEAS.md, "An independent generator:
ABIDES's RMSC04".
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path

from arena.cli import add_dataset_arguments, dataset_from
from arena.formats import FORMATS
from arena.model import Day

DATASETS = [  # (data, format, round, products): the ABIDES days, then a Prosperity control
    ("data/abides", "prosperity", "1", ["ABM"]),
    ("p3", "prosperity", "1", ["KELP"]),
]
FAIRS = ("mid", "wall_mid", "sized_mid", "weighted_mid")
SMOOTHING = (0.0, 0.5, 0.9, 0.95)
WALL_SIZE = 15
HORIZON = 50
LOOKBACK = 20
MOVES = (2, 5, 10)  # past moves of at least this many ticks


def price(book, method: str) -> float | None:
    """The template's `price` (python/bots/template.py) for the four book methods."""
    if not book.bids or not book.asks:
        return None
    if method == "mid":
        return (book.bids[0][0] + book.asks[0][0]) / 2
    if method == "wall_mid":
        return (max(book.bids, key=lambda level: level[1])[0] + max(book.asks, key=lambda level: level[1])[0]) / 2
    if method == "sized_mid":
        sized = lambda levels: next((level for level in levels if level[1] >= WALL_SIZE), levels[0])[0]
        return (sized(book.bids) + sized(book.asks)) / 2
    share = book.bids[0][1] / (book.bids[0][1] + book.asks[0][1])
    return share * book.asks[0][0] + (1 - share) * book.bids[0][0]


def series(day: Day, product: str, method: str, smoothing: float) -> list[float | None]:
    """The fair a tick, smoothed, kept through ticks with an empty side (as the template keeps it)."""
    out, previous = [], None
    for tick in day.ticks:
        now = price(tick.books[product], method) if product in tick.books else None
        if now is not None:
            previous = now if previous is None or not smoothing else smoothing * previous + (1 - smoothing) * now
        out.append(previous)
    return out


def fundamental(data_dir: Path, day: Day, product: str) -> list[float] | None:
    """The answer key a tick (fundamental_round_R_day_D.csv, as arena.sim and abides_days write it), or None."""
    try:
        rnd, d = day.name[1:].split("d", 1)  # r<R>d<D>, the Prosperity layout's day names
    except ValueError:
        return None
    path = data_dir / f"round{rnd}" / f"fundamental_round_{rnd}_day_{d}.csv"
    if not path.exists():
        return None
    with path.open(newline="") as file:
        values = {int(r["timestamp"]): float(r["value"]) for r in csv.DictReader(file, delimiter=";") if r["product"] == product}
    return [values.get(t.timestamp) for t in day.ticks]


def tick_size(day: Day, product: str) -> float:
    info = day.info.get(product, {})
    return round(info["tick"] / info["unit"]) if "tick" in info and "unit" in info else 1


def rmse(pairs) -> float | None:
    errors = [(a - b) ** 2 for a, b in pairs if a is not None and b is not None]
    return math.sqrt(statistics.fmean(errors)) if errors else None


def fair_table(data_dir: Path, days: list[Day], product: str) -> list[str]:
    keys = [fundamental(data_dir, day, product) for day in days]
    has_key = all(k is not None for k in keys)
    lines = [f"Fair modes for {product}, root mean square error in ticks" + (" (against the fundamental now / the mid "
             f"{HORIZON} ticks ahead)" if has_key else f" (against the mid {HORIZON} ticks ahead)") + ":", "",
             "| fair | " + " | ".join(f"smoothing {s:g}" for s in SMOOTHING) + " |", "|---|" + "---|" * len(SMOOTHING)]
    mids = [series(day, product, "mid", 0.0) for day in days]
    for method in FAIRS:
        cells = []
        for s in SMOOTHING:
            ahead, now = [], []
            for day, key, m in zip(days, keys, mids):
                tick = tick_size(day, product)
                fair = series(day, product, method, s)
                ahead += [(f / tick, x / tick) for f, x in zip(fair[:-HORIZON], m[HORIZON:]) if f is not None and x is not None]
                if has_key:
                    now += [(f / tick, k / tick) for f, k in zip(fair, key) if f is not None and k is not None]
            ahead_error = rmse(ahead)
            cells.append(f"{rmse(now):.2f} / {ahead_error:.2f}" if has_key else f"{ahead_error:.2f}")
        lines.append(f"| {method} | " + " | ".join(cells) + " |")
    return lines


def continuation(days: list[Day], product: str) -> list[str]:
    lines = [f"Continuation for {product}: the wall mid's move over the next {HORIZON} ticks after one of at least k ticks "
             f"over the last {LOOKBACK}, signed by it (positive: it continues), in ticks; per day:", "",
             "| k | moves | mean | per day | days positive |", "|---|---|---|---|---|"]
    walls = [[x / tick_size(day, product) if x is not None else None for x in series(day, product, "wall_mid", 0.0)] for day in days]
    for k in MOVES:
        pooled, per_day = [], []
        for w in walls:
            signed = []
            for t in range(LOOKBACK, len(w) - HORIZON, LOOKBACK):  # disjoint windows
                if w[t] is None or w[t - LOOKBACK] is None or w[t + HORIZON] is None:
                    continue
                past = w[t] - w[t - LOOKBACK]
                if abs(past) >= k:
                    signed.append((w[t + HORIZON] - w[t]) * (1 if past > 0 else -1))
            pooled += signed
            per_day.append(statistics.fmean(signed) if signed else None)
        days_up = sum(1 for d in per_day if d is not None and d > 0)
        lines.append(f"| {k} | {len(pooled):,} | {statistics.fmean(pooled) if pooled else float('nan'):+.2f} | "
                     + ", ".join("-" if d is None else f"{d:+.1f}" for d in per_day)
                     + f" | {days_up} of {sum(1 for d in per_day if d is not None)} |")
    return lines


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.abides_study")
    add_dataset_arguments(parser, bot=False)
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    datasets = DATASETS if not dataset else [(dataset.data, dataset.format, None, list(dataset.products))]
    for data, format_name, rnd, products in datasets:
        fmt = FORMATS[format_name]
        try:
            data_dir = fmt.resolve_data_dir(data)
        except ValueError as error:
            print(f"## {data}: skipped ({error})\n")
            continue
        days = fmt.load_days(data_dir, [rnd] if rnd else list(dataset.days))
        print(f"## {data} ({len(days)} days)\n")
        for product in products:
            print("\n".join(fair_table(Path(data_dir), days, product)) + "\n")
            print("\n".join(continuation(days, product)) + "\n")


if __name__ == "__main__":
    main()
