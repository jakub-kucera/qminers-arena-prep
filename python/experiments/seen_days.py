"""Turns the probe bot's SEEN lines into days in the Prosperity layout, for a round that gives no data.

usage (from the repo root):
  uv run python -m experiments.seen_days LOG [LOG ...] --out data/arena/round1/seen --limit 50 [--round 1]

The probe (python/bots/probe.py, the day's copy python/bots/qminers/probe.py) prints one line a tick,
`SEEN {"t", "p", "b", "a", "pos", "open", "fills", "trades"}`: the probed product's book (three levels a
side, as its ADAPTER read them), our position, orders and fills, and the market's trades since the last
tick with their own timestamps. Any text around the lines is skipped (a playground log, a backtest's
--print), and a log whose clock goes back starts a new day. Each day becomes
OUT/round<R>/prices_round_<R>_day_<k>.csv (the book, its mid) and trades_round_<R>_day_<k>.csv (the market's
trades, our own left out: they are what our orders did, not the market), and OUT/limits.json gets
`--limit`. Then every tool runs on it: `--data OUT --days <R> --format prosperity`.

What it can't hold: the other products (the probe watches one), levels beyond the three the probe
prints, a tick whose call raised (probe 6 prints nothing then), and what the probe's own orders changed:
the book includes them where their exchange shows our orders (ON_THE_DAY.md, probe 2), and a market trade
that filled us comes back as our fill, not the market's. Checked on P3 round 1 day 0 through our engine:
the books of all 9,999 printed ticks are the data's; 86 of the 90 ticks whose trades differ are next to
one of the probe's fills. Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

DEPTH = 3


def read(paths: list[Path]) -> list[list[dict]]:
    """The SEEN records of the logs, split into days where the clock goes back."""
    days: list[list[dict]] = []
    last = None
    for path in paths:
        for line in path.read_text(errors="replace").splitlines():
            at = line.find("SEEN {")
            if at < 0:
                continue
            try:
                record = json.loads(line[at + len("SEEN "):])
            except json.JSONDecodeError:
                continue
            if last is None or record["t"] < last:
                days.append([])
            days[-1].append(record)
            last = record["t"]
    return days


def write(days: list[list[dict]], out: Path, round_num: int, limit: int) -> list[str]:
    folder = out / f"round{round_num}"
    folder.mkdir(parents=True, exist_ok=True)
    products, written = set(), []
    for k, day in enumerate(days):
        stem = f"round_{round_num}_day_{k}"
        with (folder / f"prices_{stem}.csv").open("w", newline="") as file:
            rows = csv.writer(file, delimiter=";")
            rows.writerow(["day", "timestamp", "product"]
                          + [f"{side}_{kind}_{n}" for side in ("bid", "ask") for n in range(1, DEPTH + 1) for kind in ("price", "volume")]
                          + ["mid_price", "profit_and_loss"])
            for r in day:
                products.add(r["p"])
                row = [k, r["t"], r["p"]]
                for levels in (r["b"], r["a"]):
                    for n in range(DEPTH):
                        row += [levels[n][0], abs(levels[n][1])] if n < len(levels) else ["", ""]
                mid = (r["b"][0][0] + r["a"][0][0]) / 2 if r["b"] and r["a"] else ""
                rows.writerow(row + [mid, "0.0"])
        with (folder / f"trades_{stem}.csv").open("w", newline="") as file:
            rows = csv.writer(file, delimiter=";")
            rows.writerow(["timestamp", "buyer", "seller", "symbol", "currency", "price", "quantity"])
            for r in day:
                for price, quantity, at in r.get("trades", []):  # two trades alike in one tick are two trades
                    rows.writerow([at, "", "", r["p"], "SEASHELLS", price, abs(quantity)])
        written.append(f"{folder / f'prices_{stem}.csv'}: {len(day):,} ticks of {', '.join(sorted({r['p'] for r in day}))}")
    limits = out / "limits.json"
    known = json.loads(limits.read_text()) if limits.exists() else {}
    limits.write_text(json.dumps({**known, **dict.fromkeys(sorted(products), limit)}, indent=2, sort_keys=True) + "\n")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.seen_days", description=__doc__.splitlines()[0])
    parser.add_argument("logs", nargs="+", type=Path, help="logs holding the probe's SEEN lines")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, required=True, help="the product's position limit, from the rules")
    parser.add_argument("--round", type=int, default=1)
    args = parser.parse_args(argv)
    days = read(args.logs)
    if not days:
        parser.error("no SEEN lines in the logs: run the probe with its prints on (probe 9)")
    for line in write(days, args.out, args.round, args.limit):
        print(line)
    print(f"then: --data {args.out} --days {args.round} --format prosperity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
