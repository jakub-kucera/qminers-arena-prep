"""When is a quote worth posting? The template's passive fills, valued against the wall mid by state.

usage (from the repo root): uv run python -m experiments.quote_markouts [--jobs N] [--horizon H] [--engine rust]

For every passive fill of the template as committed (a market trade at our price, or a resting
order crossed by the next snapshot), its value per unit at horizon h, against the wall mid:

    edge = sign x (wall mid when quoted - price)            what the quote earned at once
    move = sign x (wall mid h ticks later - wall mid when quoted)    the adverse (or helpful) move
    total = edge + move

"When quoted" is the last book the bot saw before the fill: this tick's for a fill from this
tick's market trades, the tick before for a resting order crossed by the next snapshot (the
template re-plans every tick, so that is when it last chose to keep the order). DeLise and Albers
et al. (references/wiki/sources/negative-drift-of-a-fill.md, market-makers-dilemma.md) predict
that fills come with adverse moves; the question is whether any state the bot can see before it
quotes has a negative total, so that `make` should skip that side there.

States, each signed so that positive favours the fill:
  - spread: the best ask less the best bid, in ticks;
  - place: the quote inside the best (alone, pennying) or at it (joining a level);
  - imbalance: sign x (Vb - Va) / (Vb + Va) at the best level (Cartea et al.'s rho);
  - momentum: sign x the wall mid's change over the last MOMENTUM ticks;
  - inventory: whether the fill adds to the position or reduces it.

Datasets: P2 round 1, P3 round 1, P4 rounds 1-2 (the template's tuned products), each in three
engine modes: per tick under --match-trades all and worse, and --resting. A bin counts as a
finding only if its mean total has the same sign on every day of its dataset: totals at long
horizons overlap, so a t-statistic over fills would overstate the evidence.
"""

from __future__ import annotations

import argparse
import statistics as st
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import backtest
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS

FMT = FORMATS["prosperity"]
TEMPLATE = Path("python/bots/template.py")
DATASETS = {"P2 r1": ("p2", ["1"]), "P3 r1": ("p3", ["1"]), "P4 r1-2": ("p4", ["1", "2"])}
MODES = {
    "all": EngineConfig(),
    "worse": EngineConfig(trade_matching=TradeMatching.WORSE),
    "resting": EngineConfig(resting=True),
}
HORIZONS = (1, 5, 20, 100)
MOMENTUM = 20
MIN_FILLS = 200  # a bin with fewer fills in a dataset and mode isn't shown


def _bins(spread: float, place: str, imbalance: float, momentum: float, adds: bool) -> dict[str, str]:
    return {
        "spread": f"{spread:g}" if spread <= 8 else ">8",
        "place": place,
        "imbalance": "favours" if imbalance > 0.2 else "against" if imbalance < -0.2 else "even",
        "momentum": "favours" if momentum > 0 else "against" if momentum < 0 else "flat",
        "inventory": "adds" if adds else "reduces",
    }


ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def run(job: tuple[str, str, str]) -> list[dict]:
    """One dataset, mode and day: a row per passive fill unit-weighted by its volume."""
    dataset, mode, day_name = job
    data, days = DATASETS[dataset]
    (day,) = [d for d in FMT.load_days(FMT.resolve_data_dir(data), days) if d.name == day_name]
    (result,) = backtest(day, [("you", TEMPLATE, {}, False)], MODES[mode], ENGINE[0], fields=("fills",))
    index = {tick.timestamp: i for i, tick in enumerate(day.ticks)}
    walls = {p: [] for p in day.products}
    for tick in day.ticks:
        for p in day.products:
            book = tick.books.get(p)
            wall = book.wall_mid if book is not None else None
            walls[p].append(wall if wall is not None else (walls[p][-1] if walls[p] else None))
    position = defaultdict(int)
    rows = []
    for fill in result.fills:
        before = position[fill.product]
        position[fill.product] += fill.quantity
        if fill.source not in ("trade", "cross"):
            continue
        i = index[fill.timestamp] - (1 if fill.source == "cross" else 0)
        book, wall = day.ticks[i].books.get(fill.product), walls[fill.product]
        if i < MOMENTUM or book is None or not (book.bids and book.asks) or wall[i] is None:
            continue
        sign = 1 if fill.quantity > 0 else -1
        bid, ask = book.bids[0], book.asks[0]
        best = bid[0] if sign > 0 else ask[0]
        place = "inside" if sign * (fill.price - best) > 0 else "at best" if fill.price == best else "behind"
        row = {
            "dataset": dataset, "mode": mode, "day": day_name, "product": fill.product, "units": abs(fill.quantity),
            "edge": sign * (wall[i] - fill.price),
            **_bins(ask[0] - bid[0], place, sign * (bid[1] - ask[1]) / (bid[1] + ask[1]),
                    sign * (wall[i] - wall[i - MOMENTUM]), sign * before >= 0),
        }
        for h in HORIZONS:
            j = min(i + h, len(wall) - 1)
            row[f"move{h}"] = sign * (wall[j] - wall[i])
        rows.append(row)
    return rows


def _mean(rows: list[dict], key: str) -> float:
    units = sum(r["units"] for r in rows)
    return sum(r[key] * r["units"] for r in rows) / units


def table(rows: list[dict], feature: str, horizon: int) -> list[str]:
    out = []
    groups = defaultdict(list)
    for r in rows:
        groups[(r["dataset"], r["mode"], r["product"], r[feature])].append(r)
    for (dataset, mode, product, value), group in sorted(groups.items()):
        if len(group) < MIN_FILLS:
            continue
        for r in group:
            r["total"] = r["edge"] + r[f"move{horizon}"]
        by_day = defaultdict(list)
        for r in group:
            by_day[r["day"]].append(r)
        day_totals = [_mean(g, "total") for g in by_day.values()]
        same = "every day <0" if all(t < 0 for t in day_totals) else "every day >0" if all(t > 0 for t in day_totals) else "mixed"
        moves = "  ".join(f"{_mean(group, f'move{h}'):+6.2f}" for h in HORIZONS)
        out.append(
            f"  {dataset:<8} {mode:<8} {product:<22} {value:<9} {len(group):>7,} {sum(r['units'] for r in group):>8,}"
            f"  {_mean(group, 'edge'):+6.2f}  {moves}  {_mean(group, 'total'):+6.2f}  {same}"
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.quote_markouts")
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--horizon", type=int, default=20, choices=HORIZONS, help="the horizon of the total and of the day test (default 20)")
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.build()
    jobs = []
    for dataset, (data, days) in DATASETS.items():
        for day in FMT.load_days(FMT.resolve_data_dir(data), days):
            jobs += [(dataset, mode, day.name) for mode in MODES]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        rows = [row for part in pool.map(run, jobs) for row in part]
    header = (f"  {'data':<8} {'mode':<8} {'product':<22} {'state':<9} {'fills':>7} {'units':>8}  {'edge':>6}  "
              + "  ".join(f"{'move' + str(h):>6}" for h in HORIZONS) + f"  {'total':>6}  sign of the total per day")
    print(f"Passive fills of the template, per unit against the wall mid; total = edge + move{args.horizon}.\n")
    for feature in ("spread", "place", "imbalance", "momentum", "inventory"):
        print(f"by {feature}:")
        print(header)
        print("\n".join(table(rows, feature, args.horizon)))
        print()


if __name__ == "__main__":
    main()
