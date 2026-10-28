"""LOBSTER's NASDAQ sample days (real books, real informed flow) in the Prosperity layout.

usage (from the repo root, once a sample is saved: MANUAL_TODO.md, "LOBSTER's sample files"):
  uv run python -m experiments.lobster_days data/lobster/raw          # every *_message_*.csv there -> data/lobster
  uv run python -m arena.diagnose 1 --data data/lobster               # then any tool, with --data data/lobster

A LOBSTER day is two files (lobsterdata.com's documentation): TICKER_DATE_34200000_57600000_message_L.csv,
one row an event (time in seconds after midnight, type, order id, size, price in $0.0001, the
limit order's direction: 1 buy, -1 sell), and ..._orderbook_L.csv, the book after each event (ask
price, ask size, bid price, bid size, level by level; an empty level's price is ±9,999,999,999).
Event types 4 and 5 are executions of a visible and a hidden limit order; the trade's aggressor
is the other side of that order.

As experiments.abides_days converts ABIDES's days: a tick per second from the first second with
both sides quoted (23,400 for a full session), the book at the end of each second, three levels a
side, prices in cents, and the trades of the second after each snapshot at its tick, anonymous
(hidden executions included: they print, so a quote at that price could have met them). The
position limit is LIMIT shares. Each sample file becomes a day of round 1, in file-name order.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

LIMIT = 100
LEVELS = 3
TICK = 100  # timestamps a second apart
EMPTY = 9_999_999_999
UNITS_PER_CENT = 100  # LOBSTER's prices are in $0.0001


def convert(message: Path, orderbook: Path, data_dir: Path, day: int, round_num: int = 1) -> tuple[str, int, int]:
    """Writes one LOBSTER day as round<round_num>/prices_..., trades_... day <day>; returns the
    ticker, the ticks written and the trades written."""
    ticker = message.name.split("_")[0]
    folder = data_dir / f"round{round_num}"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"round_{round_num}_day_{day}"

    snapshots: dict[int, list[str]] = {}  # second -> the book after its last event
    trades: list[tuple[float, int, int]] = []  # (time, price in cents, size)
    with message.open(newline="") as m, orderbook.open(newline="") as b:
        for event, book in zip(csv.reader(m), csv.reader(b)):
            time, kind, size, price = float(event[0]), int(event[1]), int(event[3]), int(event[4])
            snapshots[int(time)] = book
            if kind in (4, 5):
                trades.append((time, price // UNITS_PER_CENT, size))

    def levels(book: list[str], offset: int) -> list[tuple[int, int]]:
        out = []
        for level in range(min(LEVELS, len(book) // 4)):  # a level-1 or level-2 file has fewer columns
            price, size = int(book[4 * level + offset]), int(book[4 * level + offset + 1])
            if abs(price) != EMPTY and size > 0:
                out.append((price // UNITS_PER_CENT, size))
        return out

    seconds = sorted(snapshots)
    ticks, book = [], None
    for second in range(seconds[0], seconds[-1] + 1):
        book = snapshots.get(second, book)  # a second with no event keeps the last book
        asks, bids = levels(book, 0), levels(book, 2)
        if not ticks and not (asks and bids):
            continue
        ticks.append((second, bids, asks))

    with (folder / f"prices_{stem}.csv").open("w", newline="") as file:
        out = csv.writer(file, delimiter=";")
        out.writerow(["day", "timestamp", "product"]
                     + [f"{side}_{kind}_{k}" for side in ("bid", "ask") for k in range(1, LEVELS + 1) for kind in ("price", "volume")]
                     + ["mid_price", "profit_and_loss"])
        for k, (_, bids, asks) in enumerate(ticks):
            row = [day, k * TICK, ticker]
            for side in (bids, asks):
                for level in range(LEVELS):
                    row += list(side[level]) if level < len(side) else ["", ""]
            row += [f"{(bids[0][0] + asks[0][0]) / 2:.1f}" if bids and asks else "", "0.0"]
            out.writerow(row)

    first = ticks[0][0]
    written = 0
    with (folder / f"trades_{stem}.csv").open("w", newline="") as file:
        out = csv.writer(file, delimiter=";")
        out.writerow(["timestamp", "buyer", "seller", "symbol", "currency", "price", "quantity"])
        for time, price, size in trades:
            k = int(time) - 1 - first  # in the second after tick k's snapshot, the end of second first + k
            if 0 <= k < len(ticks):
                out.writerow([k * TICK, "", "", ticker, "USD", f"{price:.1f}", size])
                written += 1

    limits_path = data_dir / "limits.json"
    limits = json.loads(limits_path.read_text()) if limits_path.exists() else {}
    limits[ticker] = LIMIT
    limits_path.write_text(json.dumps(limits, indent=2, sort_keys=True) + "\n")
    return ticker, len(ticks), written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.lobster_days")
    parser.add_argument("raw", type=Path, help="a folder with LOBSTER's *_message_*.csv and *_orderbook_*.csv files")
    parser.add_argument("--out", type=Path, default=Path("data/lobster"), help="the data folder (default data/lobster)")
    args = parser.parse_args(argv)
    messages = sorted(args.raw.glob("*_message_*.csv"))
    if not messages:
        parser.error(f"no *_message_*.csv in {args.raw}")
    for day, message in enumerate(messages, start=1):
        orderbook = message.with_name(message.name.replace("_message_", "_orderbook_"))
        ticker, ticks, trades = convert(message, orderbook, args.out, day)
        print(f"day {day}: {ticker} from {message.name}, {ticks:,} ticks, {trades:,} trades")


if __name__ == "__main__":
    main()
