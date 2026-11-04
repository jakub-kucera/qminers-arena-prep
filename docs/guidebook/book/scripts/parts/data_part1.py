"""Part I's data (the guidebook's chapters 1 and 2): chapter 2's worked order, its limit penalty and its claim check.

Run from the repo root: uv run python docs/guidebook/book/scripts/make_data.py --only worked_order hidden_depth kestrel_breach
"""

from __future__ import annotations

import bisect
import csv
import json
import re
from collections import defaultdict

from make_data import ROOT, p3_day, run, write

ZSE = ROOT / "references/algotrade2026-pitfa19/market_data"


def _snapshots() -> dict[str, tuple[list[int], list[tuple[int, int]]]]:
    """Each ZSE instrument's snapshot times and (lowest bid shown, highest ask shown), in time order."""
    books: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    with (ZSE / "ZSE_orderbooks.csv").open() as file:
        for row in csv.DictReader(file):
            if row["bid3_price"] and row["ask3_price"]:
                books[row["instrument"]].append((int(row["time"]), int(float(row["bid3_price"])), int(float(row["ask3_price"]))))
    out = {}
    for name, rows in books.items():
        rows.sort()
        out[name] = ([t for t, _, _ in rows], [(b, a) for _, b, a in rows])
    return out


def hidden_depth() -> None:
    """Chapter 2's claim check: the share of AlgoTrade's ZSE prints outside the three levels a side the team's recorder
    kept (the exchange sent five), by
    mm_analysis.md's own test (the last snapshot at or before the print, as its zse_mm_extract.py does) and by a
    stricter one (outside both that snapshot and the next), with Prosperity 3's round 1 beside it from
    experiments.day.structure's hidden-depth column."""
    books = _snapshots()
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    with (ZSE / "ZSE_trades.csv").open() as file:
        for row in csv.DictReader(file):
            name = row["instrument"]
            if name not in books:
                continue
            times, levels = books[name]
            t, price = int(row["time"]), int(float(row["price"]))
            k = bisect.bisect_right(times, t) - 1
            if k < 0:
                continue
            low, high = levels[k]
            before = price < low or price > high
            nxt = levels[k + 1] if k + 1 < len(levels) else levels[k]
            after = price < nxt[0] or price > nxt[1]
            c = counts[name.replace("ZSE-", "")]
            c[0] += 1
            c[1] += before
            c[2] += before and after
    rows = [["ZSE", name, n, round(a / n, 4), round(b / n, 4)] for name, (n, a, b) in sorted(counts.items())]
    n, a, b = (sum(c[i] for c in counts.values()) for i in range(3))
    rows.append(["ZSE", "all", n, round(a / n, 4), round(b / n, 4)])
    output = run(["-m", "experiments.day.structure", "--data", "p3", "--days", "1", "--sections", "fingerprints"])
    for line in output.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 9 and cells[5].replace(",", "").isdigit():
            outside = float(re.match(r"([\d.]+)%", cells[8]).group(1)) / 100
            rows.append(["Prosperity 3 round 1", cells[0], int(cells[5].replace(",", "")), outside, ""])
    write("hidden_depth", "references/algotrade2026-pitfa19/market_data/ZSE_{orderbooks,trades}.csv: prints outside the shown "
          "bid3..ask3 (the last snapshot at or before; and that and the next); Prosperity: uv run python -m experiments.day.structure "
          "--data p3 --days 1 --sections fingerprints, 'outside the book'",
          ["market", "product", "prints", "outside_last", "outside_both"], rows)


class _OneOrder:
    """A bot that sends one order, a buy of 10 Kelp at 2,031, at timestamp 400, and nothing else."""

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        from arena.model import Order

        return [Order("KELP", 2031, 10)] if tick.timestamp == 400 else []


def worked_order() -> None:
    """Chapter 2's worked example: one buy order on F2's book (P3 round 1 day 0, timestamp 400) under Prosperity's
    rules (all and worse) and with orders resting, and the books and trades of the ticks around it."""
    from arena.engine import EngineConfig, TradeMatching, run_day

    day = p3_day()
    rows = []
    for tick in day.ticks[3:7]:
        book = tick.books["KELP"]
        rows.append(["book", tick.timestamp, " ".join(f"{p}x{v}" for p, v in book.bids), " ".join(f"{p}x{v}" for p, v in book.asks),
                     " ".join(f"{m.price}x{m.quantity}" for m in tick.trades.get("KELP", []))])
    for name, config in (("all", EngineConfig()), ("worse", EngineConfig(trade_matching=TradeMatching.WORSE)),
                         ("resting", EngineConfig(resting=True))):
        for fill in run_day(day, _OneOrder(), config).fills:
            rows.append([f"fill ({name})", fill.timestamp, fill.price, fill.quantity, fill.source])
    write("worked_order", "arena.engine.run_day on P3 round 1 day 0 with a bot that buys 10 KELP at 2031 at timestamp 400: "
          "EngineConfig() (all), trade_matching worse, resting", ["row", "timestamp", "bids_or_price", "asks_or_lots", "trades_or_source"], rows)


def kestrel_breach() -> None:
    """Chapter 2's limits: the Kestrel rehearsal's bots on its hidden sessions, scored by its portal (a breach charged
    0.25 credits a lot a step, not rejected), as its README scores them."""
    folder = "python/experiments/mock_round/round3"
    rows = []
    for run_name in ("before", "after", "in_flight"):
        output = run([f"{folder}/private/portal.py", "hidden", f"{folder}/results/{run_name}/template.py"])
        metrics = json.loads(output[output.index("{"):output.rindex("}") + 1])["metrics"]
        rows.append([run_name, metrics["score"], metrics["breachPenalty"], metrics["absInventoryQ50"], metrics["tradedVolume"]])
    write("kestrel_breach", f"uv run python {folder}/private/portal.py hidden {folder}/results/<run>/template.py: credits",
          ["run", "score", "breach_penalty", "abs_inventory_q50", "traded_volume"], rows)


STEPS = {"worked_order": worked_order, "hidden_depth": hidden_depth, "kestrel_breach": kestrel_breach}
