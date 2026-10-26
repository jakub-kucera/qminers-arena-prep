"""First-look diagnostics of a market's data, per product: what kind of market is this?

    uv run python -m arena.diagnose 1 --data p4        # every day of round 1
    uv run python -m arena.diagnose 3-0 --data p4 --csv results/diag.csv

No bot is needed: it reads the days through the format plug-in, so it works on the Arena's
first data download as soon as its format module exists. For each product, pooled over the days:

- **Book:** the tick, the spread in ticks, the share of two-sided ticks at a one-tick spread (the
  large-tick regime, where queue position and book imbalance matter), how often one side of the
  book is empty, and how often the wall mid jumps: moves by more than half the spread (and at
  least a tick) from one tick to the next. Where orders rest, quotes near the touch of a product
  that jumps get filled at their stale price.
- **The market maker's size:** the median size of each side's largest level, and the share of
  sides with a level of at least `WALL_SIZE` lots, the template's default `wall_size`. Where that
  share is low, `sized_mid` falls back to the best level, i.e. the plain mid, on most ticks.
- **Jumps that snap back:** the wall mid's moves of at least `SNAP_SPREADS` times the day's median
  spread, and the share that went the opposite way to the one before. Where that share is high,
  fading each jump pays (the template's `jump` mode); elsewhere it is a coin flip.
- **Noise:** the lag-1 autocorrelation of one-tick changes of the mid, and the signature ratio of
  the mid and of the wall mid (the midpoint of the largest level on each side): the variance per
  tick of one-tick changes over that of `LAG`-tick changes. Near 1 is a random walk; well above 1
  is noise that reverts, which a fair value should filter out.
- **Slow reversion:** the wall mid's variance per tick at `LAG` ticks over that at `LONG_LAG`
  ticks. Well above 1: the price returns to a level over hundreds of ticks, which the lag-1
  numbers can't see.
- **Drift:** the wall mid's change over each day, and that change over the day's noise.
- **Market trades:** each classified against its own tick's book, as `analysis.trade_impact` does
  (+1 at or above the best ask, -1 at or below the best bid; inside the spread: left out). Then:
  - the share of buys and `C(1)`, the correlation of consecutive trade signs;
  - against each reference (the mid, the wall mid): the taker's edge `sign × (ref − price)` and
    the signed move `R(h) = sign × (ref[t+h] − ref[t])` after 1 and `LAG` ticks;
  - the two margins per unit of a market maker who takes the other side, from Bouchaud et al.
    (2018), eqs. 17.13–17.14: slow `−edge − R(LAG)` and fast `−edge × (1 − C(1)) − R(1)`. The
    book writes `s/2` for `−edge`, which is the same against the mid when trades are at the touch;
    measuring it keeps the margin consistent with the reference.
- **Notes:** which regime the numbers point to, using the thresholds below. They are rules of
  thumb calibrated on Prosperity data, not verdicts.
  `references/wiki/concepts/reading-the-data-on-day-one.md` says what each one means for the
  strategy.

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

from arena.formats import FORMATS
from arena.model import Day

LAG = 50  # ticks: the "long run" for impact, noise and the slow margin
LONG_LAG = 1000  # ticks: the horizon for slow reversion to a level
REFERENCES = ("mid", "wall")
LARGE_TICK_SHARE = 0.5  # share of two-sided ticks at a one-tick spread from which a product is large-tick
EMPTY_SIDE_SHARE = 0.02  # share of ticks with one side empty from which it gets a note
WALL_SIZE = 15  # the template's DEFAULTS wall_size: the smallest level sized_mid counts as the market maker's
WALL_SEEN = 0.8  # share of book sides with a level of WALL_SIZE below which wall_size gets a note
# Share of ticks on which the wall mid jumps from which resting quotes get picked off: under --resting, the
# template's market making lost 140k-1.5M on P2/P3 products at 10-63% and still made 18k on Kelp at 0-0.1%.
JUMPY = 0.05
# Jumps that snap back: a wall mid move of at least SNAP_SPREADS × the day's median spread is a jump; a day with
# MIN_JUMPS of them, SNAP_BACK of which went the opposite way to the one before, gets a note. On P2-P4 (637
# product-days), the four product-days the template's jump mode made money on, all in P4 round 5, reverse 86-98%
# (ROBOT_DISHES day 4: 743 jumps, 87%); every other day with 20 such jumps reverses at most 67%.
SNAP_SPREADS = 6
MIN_JUMPS = 20
SNAP_BACK = 0.75
MEAN_REVERTING = -0.2  # lag-1 autocorrelation of the mid's changes at or below which the mid is mostly noise
NOISY_SIGNATURE = 1.5  # signature ratio from which a price is noisy
# Wall mid variance per tick at LAG over LONG_LAG from which it reverts to a level. Three days of 10,000 ticks hold
# only 30 LONG_LAG windows, so a random walk spreads widely: simulated, its median is 1.11 and 2% reach 1.8;
# P4 round 5's 50 products give 0.76-1.64 (median 1.16). A pull to the level of 0.2% a tick gives a median of 2.6.
SLOW_REVERSION = 1.8
FIXED_SD_TICKS = 1.0  # standard deviation of the wall mid, in ticks, up to which it counts as a fixed value
DRIFT_RATIO = 2.0  # |change over a day| / the day's noise from which a day counts as drifting
MIN_TRADES = 30  # market trades below which no trade statistics get a note
ONE_SIDED = 0.1  # share of buys (or sells) at or below which the flow is one-sided
PERSISTENT_SIGNS = 0.5  # C(1) from which trade signs persist
INFORMED_SHARE = 0.25  # |R(LAG)| against the wall mid, as a share of the taker's cost, from which the move gets a note
THIN_MARGIN_SHARE = 0.1  # slow margin against the wall mid, as a share of the spread, below which it is thin
T_STAT = 2.0  # |mean / standard error| from which a mean counts as non-zero (rough: overlapping horizons)


@dataclass
class _Acc:
    """What one product's days add up to."""

    ticks: int = 0
    two_sided: int = 0
    one_empty: int = 0
    tick_size: float | None = None
    spreads: list[float] = field(default_factory=list)
    largest: list[int] = field(default_factory=list)  # each side's largest level, per two-sided tick
    wall_moves: list[tuple[float, float]] = field(default_factory=list)  # (|wall mid change|, half the spread) a tick
    mids: list[float] = field(default_factory=list)
    walls: list[float] = field(default_factory=list)
    autocorr: list[tuple[float, int]] = field(default_factory=list)  # mid, (value, weight) per day
    signature: dict[str, list[tuple[float, int]]] = field(default_factory=lambda: {r: [] for r in REFERENCES})
    reversion: list[tuple[float, int]] = field(default_factory=list)  # wall mid, LAG over LONG_LAG, per day
    drifts: list[float] = field(default_factory=list)  # wall mid change per day
    drift_ratios: list[float] = field(default_factory=list)  # that change over the day's noise
    trades: int = 0
    buys: int = 0
    inside: int = 0
    sign_pairs: list[int] = field(default_factory=list)  # products of consecutive trade signs
    trade_spreads: list[float] = field(default_factory=list)
    edges: dict[str, list[float]] = field(default_factory=lambda: {r: [] for r in REFERENCES})
    moves: dict[tuple[str, int], list[float]] = field(default_factory=dict)  # (reference, horizon)
    slow_gains: dict[str, list[float]] = field(default_factory=lambda: {r: [] for r in REFERENCES})
    snaps: list[tuple[str, int, int, int]] = field(default_factory=list)  # (day, jumps, pairs, pairs reversed) per day


def diagnose(days: list[Day]) -> dict[str, dict[str, float | str | None]]:
    """Per product, the diagnostics in the module docstring, pooled over the days."""
    accs: dict[str, _Acc] = {}
    for day in days:
        for product in day.products:
            _add_day(accs.setdefault(product, _Acc()), day, product)
    return {product: _summarise(acc) for product, acc in sorted(accs.items())}


def _add_day(acc: _Acc, day: Day, product: str) -> None:
    series: dict[str, list[float | None]] = {r: [] for r in REFERENCES}
    prices: set[float] = set()
    for tick in day.ticks:
        book = tick.books.get(product)
        acc.ticks += 1
        if book is not None:
            prices.update(p for p, _ in book.bids + book.asks)
        if book is None or not (book.bids and book.asks):
            acc.one_empty += book is not None and bool(book.bids or book.asks)
            series["mid"].append(None)
            series["wall"].append(None)
            continue
        acc.two_sided += 1
        acc.spreads.append(book.asks[0][0] - book.bids[0][0])
        acc.largest += [max(v for _, v in book.bids), max(v for _, v in book.asks)]
        if series["wall"] and series["wall"][-1] is not None and book.wall_mid is not None:
            acc.wall_moves.append((abs(book.wall_mid - series["wall"][-1]), acc.spreads[-1] / 2))
        series["mid"].append(book.mid)
        series["wall"].append(book.wall_mid)
    acc.mids += [m for m in series["mid"] if m is not None]
    acc.walls += [w for w in series["wall"] if w is not None]
    day_spreads = acc.spreads[len(acc.spreads) - sum(w is not None for w in series["mid"]):]
    if day_spreads:
        acc.snaps.append((day.name, *_snap_backs([w for w in series["wall"] if w is not None], statistics.median(day_spreads))))
    ordered = sorted(prices)
    gaps = [b - a for a, b in zip(ordered, ordered[1:])]
    if gaps:
        acc.tick_size = min(gaps + ([acc.tick_size] if acc.tick_size else []))

    changes = [b - a for a, b in zip(series["mid"], series["mid"][1:]) if a is not None and b is not None]
    if len(changes) > 2:
        acc.autocorr.append((_lag1_autocorrelation(changes), len(changes)))
    for name in REFERENCES:
        ratio = _signature_ratio(series[name])
        if ratio is not None:
            acc.signature[name].append((ratio, len(series[name])))

    refs = {name: _forward_fill(values) for name, values in series.items()}
    known = [w for w in refs["wall"] if w is not None]
    per_tick = _variance_per_tick(refs["wall"], LAG)
    per_tick_long = _variance_per_tick(refs["wall"], LONG_LAG)
    if per_tick and per_tick_long and len(known) >= 2 * LONG_LAG:
        acc.reversion.append((per_tick / per_tick_long, len(known)))
    if len(known) > LAG and per_tick is not None:
        noise = (per_tick * len(known)) ** 0.5
        acc.drifts.append(known[-1] - known[0])
        acc.drift_ratios.append((known[-1] - known[0]) / noise if noise else 0.0)

    last_sign = None
    for i, tick in enumerate(day.ticks):
        book = tick.books.get(product)
        if book is None or not (book.bids and book.asks):
            continue
        bid, ask = book.bids[0][0], book.asks[0][0]
        for trade in tick.trades.get(product, []):
            sign = 1 if trade.price >= ask else -1 if trade.price <= bid else 0
            if not sign:
                acc.inside += 1
                continue
            acc.trades += 1
            acc.buys += sign > 0
            acc.trade_spreads.append(ask - bid)
            if last_sign is not None:
                acc.sign_pairs.append(sign * last_sign)
            last_sign = sign
            for name, ref in refs.items():
                acc.edges[name].append(sign * (ref[i] - trade.price))
                for horizon in (1, LAG):
                    if i + horizon < len(ref):
                        acc.moves.setdefault((name, horizon), []).append(sign * (ref[i + horizon] - ref[i]))
                if i + LAG < len(ref):
                    acc.slow_gains[name].append(sign * (trade.price - ref[i + LAG]))


def _summarise(acc: _Acc) -> dict[str, float | str | None]:
    tick = acc.tick_size or 1.0
    spread_ticks = [s / tick for s in acc.spreads]
    c1 = _mean(acc.sign_pairs)
    row: dict[str, float | str | None] = {
        "ticks": acc.ticks,
        "two_sided": _share(acc.two_sided, acc.ticks),
        "one_side_empty": _share(acc.one_empty, acc.ticks),
        "tick": acc.tick_size,
        "mean_mid": _mean(acc.mids),
        "wall_median": statistics.median(acc.walls) if acc.walls else None,
        "wall_sd": statistics.pstdev(acc.walls) if acc.walls else None,
        "spread_ticks_median": statistics.median(spread_ticks) if spread_ticks else None,
        "spread_ticks_mean": _mean(spread_ticks),
        "wall_size": statistics.median(acc.largest) if acc.largest else None,
        "wall_seen": _share(sum(1 for v in acc.largest if v >= WALL_SIZE), len(acc.largest)),
        "at_one_tick": _share(sum(1 for s in spread_ticks if s <= 1 + 1e-9), len(spread_ticks)),
        "jump_share": _share(sum(1 for move, half in acc.wall_moves if move > max(half, tick) + 1e-9), len(acc.wall_moves)),
        "snap_jumps": sum(n for _, n, _, _ in acc.snaps),
        "snap_back": _share(sum(r for *_, r in acc.snaps), sum(p for _, _, p, _ in acc.snaps)) if sum(n for _, n, _, _ in acc.snaps) >= MIN_JUMPS else None,
        "mid_lag1_autocorr": _weighted(acc.autocorr),
        "mid_signature": _weighted(acc.signature["mid"]),
        "wall_signature": _weighted(acc.signature["wall"]),
        "wall_reversion": _weighted(acc.reversion),
        "drift_per_day": _mean(acc.drifts),
        "drift_ratio_least": min(acc.drift_ratios, key=abs) if acc.drift_ratios else None,
        "drift_ratio_most": max(acc.drift_ratios, key=abs) if acc.drift_ratios else None,
        "trades": acc.trades,
        "inside_share": _share(acc.inside, acc.trades + acc.inside),
        "buy_share": _share(acc.buys, acc.trades),
        "c1": c1,
        "spread_at_trades": _mean(acc.trade_spreads),
    }
    for name in REFERENCES:
        edge = _mean(acc.edges[name])
        r1, rl = _mean(acc.moves.get((name, 1))), _mean(acc.moves.get((name, LAG)))
        row[f"edge_{name}"] = edge
        row[f"r1_{name}"] = r1
        row[f"r{LAG}_{name}"] = rl
        row[f"r{LAG}_{name}_t"] = _t_stat(acc.moves.get((name, LAG)))
        row[f"slow_{name}"] = _mean(acc.slow_gains[name])
        row[f"slow_{name}_t"] = _t_stat(acc.slow_gains[name])
        row[f"fast_{name}"] = -edge * (1 - c1) - r1 if None not in (edge, r1, c1) else None
    row["notes"] = "; ".join(_notes(row, acc)) or "-"
    return row


def _notes(row: dict, acc: _Acc) -> list[str]:
    notes = []
    if row["at_one_tick"] is not None:
        if row["at_one_tick"] >= LARGE_TICK_SHARE:
            notes.append(f"large-tick (one-tick spread {row['at_one_tick']:.0%} of the time)")
        else:
            notes.append(f"small-tick (median spread {row['spread_ticks_median']:g} ticks)")
    if row["wall_seen"] is not None and row["wall_seen"] < WALL_SEEN:
        notes.append(
            f"a level of {WALL_SIZE}+ on only {row['wall_seen']:.0%} of sides (largest level median {row['wall_size']:g}): "
            "set wall_size near it, or sized_mid falls back to the mid"
        )
    if (row["one_side_empty"] or 0) >= EMPTY_SIDE_SHARE:
        notes.append(f"a side empty {row['one_side_empty']:.0%} of ticks")
    if (row["jump_share"] or 0) >= JUMPY:
        notes.append(f"wall mid jumps past half the spread on {row['jump_share']:.0%} of ticks: if orders rest, take only")
    snapping = [(day, n, r / p) for day, n, p, r in acc.snaps if n >= MIN_JUMPS and p and r / p >= SNAP_BACK]
    if snapping:
        days = ", ".join(f"{day} {share:.0%} of {n}" for day, n, share in snapping)
        notes.append(f"jumps of {SNAP_SPREADS}+ spreads snap back ({days} reversed the one before): fade them, the template's jump mode")
    fixed = row["wall_sd"] is not None and row["wall_sd"] <= FIXED_SD_TICKS * (row["tick"] or 1.0)
    if fixed:
        notes.append(f"wall mid nearly fixed at {row['wall_median']:g} (sd {row['wall_sd']:.2f})")
    if row["mid_lag1_autocorr"] is not None and row["mid_lag1_autocorr"] <= MEAN_REVERTING:
        notes.append("mid mean-reverts at one tick")
    mid_sig, wall_sig = row["mid_signature"], row["wall_signature"]
    if mid_sig is not None and wall_sig is not None and mid_sig >= NOISY_SIGNATURE:
        if wall_sig < mid_sig / 2:
            notes.append("wall mid filters the mid's noise")
        else:
            notes.append("mid and wall mid both noisy")
    if not fixed and row["wall_reversion"] is not None and row["wall_reversion"] >= SLOW_REVERSION:
        notes.append(f"wall mid reverts to a level over ~{LONG_LAG:,} ticks")
    ratios = acc.drift_ratios
    drifting = [r for r in ratios if abs(r) >= DRIFT_RATIO]
    if ratios and len(drifting) == len(ratios) and len({r > 0 for r in ratios}) == 1:
        notes.append(f"drifts {'up' if ratios[0] > 0 else 'down'} every day ({row['drift_per_day']:+,.0f} a day)")
    elif drifting:
        notes.append(f"drifts on {len(drifting)} of {len(ratios)} days")

    if acc.trades < MIN_TRADES:
        notes.append(f"{acc.trades} market trades: too few for trade statistics")
        return notes
    buys = row["buy_share"]
    one_sided = buys <= ONE_SIDED or buys >= 1 - ONE_SIDED
    if one_sided:
        notes.append(f"trades nearly all {'buys' if buys > 0.5 else 'sells'}")
    if row["c1"] >= PERSISTENT_SIGNS:
        notes.append(f"trade signs persist (C(1) {row['c1']:.2f})")
    cost, move, t = -row["edge_wall"], row[f"r{LAG}_wall"], row[f"r{LAG}_wall_t"]
    if t is not None and abs(t) >= T_STAT and abs(move) >= INFORMED_SHARE * abs(cost):
        notes.append("trades move the wall mid" if move > 0 else "wall mid reverts after trades")
    slow, slow_t, spread = row["slow_wall"], row["slow_wall_t"], row["spread_at_trades"]
    if slow is not None and spread:
        share = slow / spread
        if one_sided or row["c1"] >= PERSISTENT_SIGNS:
            fast = row["fast_wall"] / spread if row["fast_wall"] is not None else 0.0
            notes.append(f"a maker's position only grows: fast margin {fast:+.2f} of the spread")
        elif slow_t is not None and abs(slow_t) < T_STAT:
            notes.append(f"market-making margin not measurably non-zero ({share:+.2f} of the spread)")
        elif share < THIN_MARGIN_SHARE:
            notes.append(f"thin or negative market-making margin ({share:+.2f} of the spread)")
        else:
            notes.append(f"market making pays ({share:.2f} of the spread a unit)")
    return notes


def _snap_backs(walls: list[float], spread: float) -> tuple[int, int, int]:
    """One day's wall mids: (jumps of at least SNAP_SPREADS × spread, consecutive pairs of them, pairs in opposite directions)."""
    jumps = [b - a for a, b in zip(walls, walls[1:]) if spread and abs(b - a) >= SNAP_SPREADS * spread]
    pairs = list(zip(jumps, jumps[1:]))
    return len(jumps), len(pairs), sum(1 for a, b in pairs if a * b < 0)


def _lag1_autocorrelation(x: list[float]) -> float:
    mean = statistics.fmean(x)
    var = sum((v - mean) ** 2 for v in x)
    return sum((a - mean) * (b - mean) for a, b in zip(x, x[1:])) / var if var else 0.0


def _variance_per_tick(series: list[float | None], lag: int) -> float | None:
    """Mean squared change over `lag` ticks, over `lag` (no mean taken out, as in a variogram)."""
    squares = [
        (series[i + lag] - series[i]) ** 2
        for i in range(len(series) - lag)
        if series[i] is not None and series[i + lag] is not None
    ]
    return sum(squares) / len(squares) / lag if squares else None


def _signature_ratio(series: list[float | None]) -> float | None:
    short, long = _variance_per_tick(series, 1), _variance_per_tick(series, LAG)
    return short / long if short is not None and long else None


def _forward_fill(values: list[float | None]) -> list[float | None]:
    out, last = [], None
    for value in values:
        last = value if value is not None else last
        out.append(last)
    # Ticks before the first price take the first price.
    first = next((v for v in out if v is not None), None)
    return [first if v is None else v for v in out]


def _t_stat(values: list[float] | None) -> float | None:
    if not values or len(values) < 2:
        return None
    mean, sd = statistics.fmean(values), statistics.stdev(values)
    if not sd:
        return math.copysign(math.inf, mean) if mean else 0.0
    return mean / (sd / len(values) ** 0.5)


def _weighted(pairs: list[tuple[float, int]]) -> float | None:
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def _mean(values) -> float | None:
    return statistics.fmean(values) if values else None


def _share(part: int, whole: int) -> float | None:
    return part / whole if whole else None


# ---------------------------------------------------------------------------- report

COLUMNS = (  # (key, header, format)
    ("spread_ticks_median", "spread", "{:g}t"),
    ("at_one_tick", "1 tick", "{:.0%}"),
    ("one_side_empty", "empty", "{:.0%}"),
    ("wall_size", "wall", "{:g}"),
    ("wall_seen", f"{WALL_SIZE}+", "{:.0%}"),
    ("jump_share", "jumps", "{:.0%}"),
    ("snap_back", "snap", "{:.0%}"),
    ("mid_lag1_autocorr", "mid AC1", "{:+.2f}"),
    ("mid_signature", "mid sig", "{:.1f}"),
    ("wall_signature", "wall sig", "{:.1f}"),
    ("wall_reversion", "slow rev", "{:.1f}"),
    ("drift_per_day", "drift/day", "{:+,.0f}"),
    ("trades", "trades", "{:,}"),
    ("buy_share", "buys", "{:.0%}"),
    ("c1", "C(1)", "{:+.2f}"),
    ("edge_wall", "edge", "{:+.2f}"),
    ("r1_wall", "R(1)", "{:+.2f}"),
    (f"r{LAG}_wall", f"R({LAG})", "{:+.2f}"),
    ("slow_wall", "slow", "{:+.2f}"),
    ("fast_wall", "fast", "{:+.2f}"),
)

LEGEND = (
    "spread: median, in ticks. 1 tick: share of two-sided ticks at a one-tick spread. empty: share of ticks with one side empty.\n"
    f"wall: median size of each side's largest level. {WALL_SIZE}+: share of sides with a level of {WALL_SIZE} or more (the template's wall_size).\n"
    "jumps: share of ticks on which the wall mid moves more than half the spread (and at least a tick).\n"
    f"snap: share of the wall mid's jumps of {SNAP_SPREADS}+ median spreads that went the opposite way to the one before "
    f"(with {MIN_JUMPS} or more; a day at {SNAP_BACK:.0%} gets a note).\n"
    f"mid AC1: lag-1 autocorrelation of the mid's changes. sig: variance per tick at lag 1 over lag {LAG} (1 = random walk).\n"
    f"slow rev: the wall mid's variance per tick at lag {LAG} over lag {LONG_LAG:,} (above 1: it returns to a level).\n"
    "drift/day: the wall mid's change per day. buys: share of market trades at or above the ask. C(1): sign correlation of consecutive trades.\n"
    f"Against the wall mid: edge = the taker's mean edge (negative = paid), R(h) = the signed move h ticks after a trade,\n"
    f"and a market maker's margin a unit, slow = -edge - R({LAG}), fast = -edge (1 - C(1)) - R(1) (Bouchaud et al. eqs. 17.13-17.14).\n"
    "The CSV (--csv) also has them against the mid. See references/wiki/concepts/reading-the-data-on-day-one.md."
)


def format_report(rows: dict[str, dict]) -> str:
    width = max([len(p) for p in rows] + [len("product")])
    cells = [[_cell(row.get(key), fmt) for key, _, fmt in COLUMNS] for row in rows.values()]
    widths = [max([len(header)] + [len(c[i]) for c in cells]) for i, (_, header, _) in enumerate(COLUMNS)]
    lines = ["  ".join([f"{'product':<{width}}"] + [f"{h:>{w}}" for (_, h, _), w in zip(COLUMNS, widths)])]
    for product, row_cells in zip(rows, cells):
        lines.append("  ".join([f"{product:<{width}}"] + [f"{c:>{w}}" for c, w in zip(row_cells, widths)]))
    lines.append("")
    lines += [f"{product}: {row['notes']}" for product, row in rows.items()]
    lines += ["", LEGEND]
    return "\n".join(lines)


def _cell(value, fmt: str) -> str:
    return "-" if value is None else fmt.format(value)


def write_csv(rows: dict[str, dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(next(iter(rows.values()), {}))
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["product", *keys])
        for product, row in rows.items():
            writer.writerow([product, *("" if row.get(k) is None else row[k] for k in keys)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arena.diagnose", description="Per-product diagnostics of a market's data.")
    parser.add_argument("days", nargs="+", help="days to read: ROUND for all its days, or ROUND-DAY (e.g. 1, 1-0, 1--1)")
    parser.add_argument("--format", default="prosperity", choices=sorted(FORMATS), help="competition format (default: prosperity)")
    parser.add_argument("--data", default="p3", help="data folder, or p2 / p3 / p4 for the Prosperity data in references/ (default: p3)")
    parser.add_argument("--csv", type=Path, help="also write every diagnostic, against both references, to this CSV")
    args = parser.parse_args(argv)
    fmt = FORMATS[args.format]
    try:
        days = fmt.load_days(fmt.resolve_data_dir(args.data), args.days)
    except ValueError as error:
        parser.error(str(error))
    rows = diagnose(days)
    print(f"{len(days)} day(s): {', '.join(d.name for d in days)}\n")
    print(format_report(rows))
    if args.csv:
        write_csv(rows, args.csv)
        print(f"\nwritten to {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
