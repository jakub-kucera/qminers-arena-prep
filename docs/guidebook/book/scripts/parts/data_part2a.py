"""The guidebook's Part II, chapters 3-5: the data for chapter 3's story and fair values, G3 (the signature plot), G4 (the market-making margin),
G5 (markouts by horizon) and G6 (Olivia's trades on Squid Ink).

Run from the repo root: uv run python docs/guidebook/book/scripts/make_data.py --only kelp_fairs rival_fair osmium_rivals signature margins markouts olivia
(rival_fair and osmium_rivals run the Python engine against three teams' bots: about a minute each)
Standard library only.
"""

from __future__ import annotations

import bisect
import csv
import re
import subprocess
import tempfile
from pathlib import Path

from make_data import ROOT, TEMPLATE, grid_table, number, run, write

SIGNATURE_LAGS = (1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000)
MARKOUT_HORIZONS = (0, 1, 2, 5, 10, 20, 50, 100, 200, 500)
OLIVIA_HORIZONS = (100, 1000, 5000)


def _days(data: str, spec: str):
    from arena.formats import prosperity

    return prosperity.load_days(prosperity.resolve_data_dir(data), [spec])


def _mid(book) -> float | None:
    return (book.bids[0][0] + book.asks[0][0]) / 2 if book.bids and book.asks else None


def signature() -> None:
    """G3: the variance of h-tick changes of the mid and the wall mid, divided by h, pooled over the days (each day's
    changes on its own, pairs with an empty side left out, as arena.diagnose's signature column does)."""
    rows = []
    for market, data, products in (("Prosperity 3, round 1", "p3", ("KELP", "RAINFOREST_RESIN", "SQUID_INK")),
                                   ("ABIDES, 10 days", "data/abides", ("ABM",))):
        days = _days(data, "1")
        for product in products:
            for reference in ("mid", "wall mid"):
                sums = {h: [0.0, 0] for h in SIGNATURE_LAGS}
                for day in days:
                    books = [tick.books.get(product) for tick in day.ticks]
                    series = [None if b is None else (_mid(b) if reference == "mid" else b.wall_mid) for b in books]
                    for h in SIGNATURE_LAGS:
                        for a, b in zip(series, series[h:]):
                            if a is not None and b is not None:
                                sums[h][0] += (b - a) ** 2
                                sums[h][1] += 1
                for h in SIGNATURE_LAGS:
                    total, count = sums[h]
                    rows.append([market, product, reference, h, round(total / count / h, 5)])
    write("signature", "arena.formats.prosperity.load_days(p3 | data/abides, ['1']): mean squared h-tick change of the mid and the "
          "wall mid over h, pooled over the days", ["market", "product", "reference", "lag", "variance_per_tick"], rows)


def margins() -> None:
    """G4: Bouchaud et al.'s margin a unit, slow = -edge - R(50) against the wall mid, from arena.diagnose's CSV."""
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for market, data in (("Prosperity 3, round 1", "p3"), ("Prosperity 4, round 1", "p4"), ("ABIDES, 10 days", "data/abides")):
            path = Path(folder) / "diagnose.csv"
            run(["-m", "arena.diagnose", "1", "--data", data, "--csv", str(path)])
            for r in csv.DictReader(path.open()):
                edge, r50, slow, spread = (float(r[k]) for k in ("edge_wall", "r50_wall", "slow_wall", "spread_at_trades"))
                rows.append([market, r["product"], round(-edge, 3), round(r50, 3), round(slow, 3), round(spread, 3),
                             round(slow / spread, 3), round(float(r["c1"]), 3)])
    write("margins", "uv run python -m arena.diagnose 1 --data p3 | p4 | data/abides --csv: edge_wall, r50_wall, slow_wall, "
          "spread_at_trades, c1 (ticks: a credit on Prosperity, a cent on ABIDES)",
          ["market", "product", "half_spread_paid", "impact_50", "margin", "spread_at_trades", "margin_share", "c1"], rows)


def _markouts(folder: Path, product: str) -> dict:
    """Volume-weighted markout a unit of the passive fills (source trade or cross: arena.analysis's "passive"),
    side x (reference h ticks after the fill's tick - fill price), pooled over the days in an --out folder."""
    sums: dict = {}
    for timeline in sorted(folder.glob("*_timeline.csv")):
        day = timeline.name.split("_")[0]
        rows = [r for r in csv.DictReader(timeline.open()) if r["product"] == product]
        stamps = [int(r["timestamp"]) for r in rows]
        refs = {"mid": [float(r["mark"]) for r in rows], "wall mid": [float(r["wall_mid"]) if r["wall_mid"] else None for r in rows]}
        for fill in csv.DictReader((folder / f"{day}_fills.csv").open()):
            if fill["product"] != product or fill["source"] not in ("trade", "cross"):
                continue
            quantity = int(fill["quantity"])
            side, at = (1 if quantity > 0 else -1), bisect.bisect_left(stamps, int(fill["timestamp"]))
            for name, ref in refs.items():
                for h in MARKOUT_HORIZONS:
                    if at + h < len(ref) and ref[at + h] is not None:
                        entry = sums.setdefault((name, h), [0.0, 0])
                        entry[0] += abs(quantity) * side * (ref[at + h] - float(fill["price"]))
                        entry[1] += abs(quantity)
    return sums


def markouts() -> None:
    """G5: the template's passive fills on P3 round 1's Kelp and on the ABIDES days, by ticks after the fill."""
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for market, data, product in (("Prosperity 3 Kelp", "p3", "KELP"), ("ABIDES", "data/abides", "ABM")):
            out = Path(folder) / product
            run(["-m", "arena.backtest", TEMPLATE, "1", "--data", data, "--engine", "rust", "--out", str(out)])
            for (reference, h), (total, volume) in sorted(_markouts(out, product).items()):
                rows.append([market, reference, h, round(total / volume, 3), volume])
    write("markouts", "uv run python -m arena.backtest python/bots/template.py 1 --data p3 | data/abides --engine rust --out DIR: "
          "the passive fills' side x (reference h ticks later - price), volume-weighted over the days",
          ["market", "reference", "horizon", "markout", "lots"], rows)


def olivia() -> None:
    """G6: Squid Ink's wall mid over P3 round 5's three days and Olivia's trades on it, with the move her way from the
    wall mid a tick after each (counterparties.py's measure, clipped at the day's end)."""
    days = _days("p3", "5")
    prices, trades = [], []
    for k, day in enumerate(days):
        walls = [tick.books["SQUID_INK"].wall_mid if "SQUID_INK" in tick.books else None for tick in day.ticks]
        near = {j for i, tick in enumerate(day.ticks)
                if any("Olivia" in (t.buyer, t.seller) for t in tick.trades.get("SQUID_INK", []))
                for j in range(i - 50, i + 51)}
        for i in range(len(walls)):
            if walls[i] is not None and (i % 10 == 0 or i in near):
                prices.append([day.name, k * len(walls) + i, walls[i]])
        known = [w for w in walls if w is not None]
        low, high = min(known), max(known)
        for i, tick in enumerate(day.ticks):
            for trade in tick.trades.get("SQUID_INK", []):
                if "Olivia" not in (trade.buyer, trade.seller):
                    continue
                side = 1 if trade.buyer == "Olivia" else -1
                start = walls[min(i + 1, len(walls) - 1)]
                moves = [round(side * (walls[min(i + 1 + h, len(walls) - 1)] - start), 1) for h in OLIVIA_HORIZONS]
                trades.append([day.name, k * len(walls) + i, "buy" if side > 0 else "sell", trade.price, trade.quantity,
                               trade.seller if side > 0 else trade.buyer, low, high, *moves])
    write("olivia_prices", "arena.formats.prosperity.load_days(p3, ['5']): SQUID_INK's wall mid, every 10th tick and every tick within 50 of "
          "one of Olivia's trades, days end to end",
          ["day", "tick", "wall_mid"], prices)
    write("olivia_trades", "arena.formats.prosperity.load_days(p3, ['5']): SQUID_INK's market trades with Olivia as buyer or seller; "
          "move her way from the wall mid a tick after, at 100, 1,000 and 5,000 ticks (clipped at the day's end)",
          ["day", "tick", "side", "price", "lots", "counterparty", "day_low", "day_high", "move_100", "move_1000", "move_5000"], trades)


def kelp_fairs() -> None:
    """Chapter 3: Kelp's fair-value method and its smoothing, under all and worse (IDEAS, "The weighted mid as fair
    value" and "The Kalman-implied smoothing")."""
    rows = []
    for axis, grid in (("fair", 'PARAMS.KELP.fair="wall_mid","sized_mid","weighted_mid","mid"'),
                       ("smoothing", "PARAMS.KELP.smoothing=0,0.2,0.43,0.6,0.8,0.9")):
        output = run(["-m", "arena.grid", TEMPLATE, "1", "--data", "p3", "--grid", grid, "--modes", "all,worse", "--engine", "rust", "--top", "100"])
        for r in grid_table(output):
            rows.append([axis, r[f"KELP.{axis}"], number(r["pnl(all)"]), number(r["pnl(worse)"])])
    write("kelp_fairs", "uv run python -m arena.grid python/bots/template.py 1 --data p3 --grid 'PARAMS.KELP.fair=\"wall_mid\",\"sized_mid\",\"weighted_mid\",\"mid\"' "
          "| --grid PARAMS.KELP.smoothing=0,0.2,0.43,0.6,0.8,0.9 --modes all,worse --engine rust", ["axis", "setting", "pnl_all", "pnl_worse"], rows)


RIVALS = ["--vs", "references/prosperity4-du-trading/round2.py", "--vs", "references/prosperity4-baguette-fromage/Strategies/Phase1.py",
          "--vs", "references/prosperity4-dtu-quant-lab/round_2/algorithmic/trader.py"]


def _p4(extra: list[str]) -> str:
    """The template on P4 round 1 through the Python engine (the teams' bots need jsonpickle), its printed output."""
    args = ["uv", "run", "--with", "jsonpickle", "python", "-m", "arena.backtest", TEMPLATE, "1", "--data", "p4", *extra]
    done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"failed: {' '.join(args)}\n{done.stderr[-2000:]}")
    return done.stdout


def osmium_rivals() -> None:
    """Chapter 4's story: the template's Osmium income on P4 round 1 alone, against each team's bot and against all
    three, orders living one tick (IDEAS, "The template against the teams' P4 traders in one market")."""
    rows = []
    fields = [("alone", [])] + [(name, RIVALS[k:k + 2]) for name, k in (("against DU", 0), ("against Baguette Fromage", 2),
                                                                         ("against DTU", 4))] + [("against all three", RIVALS)]
    for field, extra in fields:
        output = _p4(extra)
        rows.append([field, number(re.search(r"ASH_COATED_OSMIUM ([-\d,]+)", output).group(1))])
    write("osmium_rivals", "uv run --with jsonpickle python -m arena.backtest python/bots/template.py 1 --data p4 [--vs <DU round2.py | "
          "Baguette Fromage Phase1.py | DTU round_2 trader.py>]: the template's Osmium PnL over round 1 (credits)", ["field", "osmium_pnl"], rows)


def rival_fair() -> None:
    """Chapter 3's story: Osmium against the three teams' P4 bots, orders resting, with the largest level (wall_mid) and
    the first of 15 lots (sized_mid); without smoothing or a stop loss (which reproduces the IDEAS row) and as committed."""
    rows = []
    for version, extra in (("no smoothing, no stop loss (the IDEAS row's run)", ["--set", "PARAMS.ASH_COATED_OSMIUM.smoothing=0",
                                                                     "--set", "PARAMS.ASH_COATED_OSMIUM.stop_loss=None"]),
                           ("as committed: smoothing 0.9, stop loss 5,500", [])):
        for fair in ("wall_mid", "sized_mid"):
            output = _p4(["--resting", "--requote", *RIVALS, "--set", f"PARAMS.ASH_COATED_OSMIUM.fair={fair}", *extra])
            osmium = number(re.search(r"ASH_COATED_OSMIUM ([-\d,]+)", output).group(1))
            rows.append([version, fair, osmium])
    write("rival_fair", "uv run --with jsonpickle python -m arena.backtest python/bots/template.py 1 --data p4 --resting --requote "
          "--vs <DU round2.py, Baguette Fromage Phase1.py, DTU round_2 trader.py> --set PARAMS.ASH_COATED_OSMIUM.fair=wall_mid|sized_mid "
          "[--set PARAMS.ASH_COATED_OSMIUM.smoothing=0 --set PARAMS.ASH_COATED_OSMIUM.stop_loss=None]: Osmium's PnL over round 1",
          ["template", "fair", "osmium_pnl"], rows)


STEPS = {"kelp_fairs": kelp_fairs, "rival_fair": rival_fair, "osmium_rivals": osmium_rivals, "signature": signature, "margins": margins, "markouts": markouts, "olivia": olivia}

__all__ = ["STEPS", "ROOT"]
