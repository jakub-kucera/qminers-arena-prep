"""What kind of process made each product's prices? A structure scan of any download, from the data alone.

usage (from the repo root): uv run python -m experiments.day.structure
       uv run python -m experiments.day.structure --data DIR --days 1 2 [--format F --products A,B --sections sums,fingerprints]
       uv run python -m experiments.day.structure --plugin FILE.py --format FILE --data DIR --days all   (a plug-in not yet in FORMATS)

Each product's price is its wall mid (the mid of the largest level a side), carried over ticks
without a two-sided book; moves are counted in the product's ticks (Day.info). Seven sections:

  moves         per product, the one-tick returns' autocorrelation to lag MAX_LAG against the
                random-walk band ±1.96/√n, the variance ratio at 10/100/1,000 ticks (1 for a
                random walk, below 1 reverting, above trending), and the periodogram's top peaks
                over their neighbours, against the same returns shuffled (a cycle shows far above the shuffle's).
  increments    the one-tick moves' sizes: the common ones, the large ones (at least LARGE times the
                median move: jumps of one exact size are a generator's), and a price grid (wall mids
                on multiples of k ticks far more often than 1/k).
  trades        market-trade arrivals against Poisson: the gaps between ticks with a trade (their
                coefficient of variation is √(1 − p) for independent ticks) and the dispersion of
                the counts per 100 ticks (1 for Poisson, above 1 clustered, below regular); and the
                products that trade on exactly the same ticks every day (one trade clock).
  starts        each day's opening wall mid against the previous day's close: days that continue
                one path, reset to one level, or jump.
  repeats       exact repeats across days and products: every WINDOW-tick run of one-tick moves
                (with at least ACTIVE moves) hashed, and each series' windows looked up in every
                other series, at any offset. A day replayed, or a product copied, shows near 100%.
  sums          the integer-weight fixed-sum search within each group of products (a name prefix,
                or every product when no prefix is shared): weights in [−3, 3] (in [−1, 1] above 6
                products), scored on one day by tightness w'Sw / Σ w_i² S_ii of the wall-mid levels
                (about 1 for unrelated walks, 0 for an identity), then the sum's mean and sd on the
                held-out days. A level that holds across days is an identity; tight within each day
                with a level that moves is a mirror or a factor. Also every pair's sum and difference
                across groups, and any weights named with --weights.
  fingerprints  how the generator builds the book: the inner (non-wall) levels' offsets from the wall
                mid (fixed offsets are a generator's lattice); shared noise streams (pairs of products
                whose inner (side, volume) multisets are identical on the same tick, against one
                product a tick later); and hidden depth (market trades at a price with no displayed
                level, or larger than the volume shown there, and trades outside every level the
                book showed that tick and the tick before: what a quote far from the book could
                catch, and the only trades a replay can fill such a quote from).

The built-in datasets carry known answers: P4 round 5 (Pebbles sum to 50,000 exactly; chocolate and
vanilla mirror; Alpha Search's UV visor sum, checked as --weights, holds on no day), P3 round 1 (no
sum; Kelp and Squid Ink share a noise stream), P4 round 1 (Osmium's inner orders at fixed offsets)
and P4 rounds 3–4 (round 4 replays two of round 3's days). Results: IDEAS.md, "A structure scan of
any download".
"""

from __future__ import annotations

import argparse
import cmath
import importlib.util
import itertools
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from arena.cli import add_dataset_arguments, dataset_from
from arena.formats import FORMATS
from arena.model import Book, Day

DATASETS = [  # (name, data alias, day specs, products or None for all, --weights checks)
    ("p4 round 5", "p4", ["5"], None, ["UV_VISOR_MAGENTA:3,UV_VISOR_AMBER:2,UV_VISOR_RED:1"]),
    ("p3 round 1", "p3", ["1"], None, []),
    ("p4 round 1", "p4", ["1"], None, []),
    ("p4 rounds 3-4", "p4", ["3", "4"], None, []),
]
SECTIONS = ("moves", "increments", "trades", "starts", "repeats", "sums", "fingerprints")
MAX_LAG = 2000  # autocorrelation lags
VR_LAGS = (10, 100, 1000)
BLOCK = 128  # periodogram ordinates a peak is measured against
LARGE = 5  # a move at least this many times the median nonzero move is large
GRIDS = (2, 4, 5, 10, 20, 25, 50, 100, 200, 500, 1000)  # candidate price grids, in ticks
WINDOW = 100  # ticks in a hashed window
ACTIVE = 10  # ...with at least this many nonzero moves
REPEAT_SHARE = 0.05  # a pair of series is listed when this share of one's windows is in the other
TIGHT = 0.05  # an identity's tightness on every day
MIRROR = 0.10  # tight within each day
STREAM_SHARE = 0.10  # a pair shares a stream when this share of its ticks have identical inner orders...
STREAM_LIFT = 3.0  # ...and this many times the share with one product a tick later
TOP = 3


# ---------------------------------------------------------------------------- series


def scale(day: Day, product: str) -> tuple[int, float]:
    """The product's tick in engine price units, and the data's price per engine unit."""
    info = day.info.get(product, {})
    tick = round(info["tick"] / info["unit"]) if "tick" in info and "unit" in info else 1
    return max(tick, 1), float(info.get("unit", 1))


def wall_mids(day: Day, product: str) -> list[float | None]:
    """The wall mid a tick in engine units, None without a two-sided book."""
    out = []
    for t in day.ticks:
        book = t.books.get(product)
        out.append(book.wall_mid if book is not None else None)
    return out


def carried(values: list[float | None]) -> list[float]:
    """Carried forward over gaps, and back from the first value."""
    first = next((v for v in values if v is not None), 0.0)
    out, last = [], first
    for v in values:
        last = v if v is not None else last
        out.append(last)
    return out


def diffs(xs: list[float]) -> list[float]:
    return [b - a for a, b in zip(xs, xs[1:])]


# ---------------------------------------------------------------------------- moves


def fft(values: list[complex], inverse: bool = False) -> list[complex]:
    """Radix-2 FFT (len(values) a power of two), unscaled both ways."""
    n = len(values)
    out = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    sign = 1 if inverse else -1
    size = 2
    while size <= n:
        half = size // 2
        twiddles = [cmath.exp(sign * 2j * math.pi * k / size) for k in range(half)]
        for start in range(0, n, size):
            for k in range(half):
                a = out[start + k]
                b = out[start + k + half] * twiddles[k]
                out[start + k] = a + b
                out[start + k + half] = a - b
        size *= 2
    return out


def spectrum(returns: list[float], size: int) -> list[float]:
    """|FFT|² of the de-meaned returns, zero-padded to `size`."""
    mean = statistics.fmean(returns) if returns else 0.0
    padded = [complex(r - mean) for r in returns] + [0j] * (size - len(returns))
    return [abs(x) ** 2 for x in fft(padded)]


def relative(power: list[float]) -> list[float]:
    """Each ordinate over the median of its neighbours: a cycle is a narrow peak above them, where the
    bid-ask bounce or a slow drift only tilt the whole spectrum. The neighbours are its block of
    BLOCK ordinates, or below BLOCK, where a drift's tilt is steep, those within half an octave."""
    out = [0.0] * len(power)
    for start in range(0, len(power), BLOCK):
        block = power[start:start + BLOCK]
        median = statistics.median(block) or 1.0
        for k in range(start, start + len(block)):
            out[k] = power[k] / median
    for k in range(1, min(BLOCK, len(power))):
        out[k] = power[k] / (statistics.median(power[max(1, k * 2 // 3):k * 3 // 2 + 2]) or 1.0)
    return out


def moves(days: list[Day], product: str, seed: int = 0) -> dict:
    """Autocorrelation to MAX_LAG pooled over days, the variance ratios, and the periodogram's peaks
    with the shuffled returns' highest peak as the baseline."""
    rng = random.Random(seed)
    paths = [[p / scale(day, product)[0] for p in carried(wall_mids(day, product))] for day in days]
    returns = [diffs(prices) for prices in paths]
    n = sum(len(r) for r in returns)
    if n < 2 or not any(any(r) for r in returns):
        return {"n": n, "moved": 0}
    longest = max(len(r) for r in returns)
    lag = min(MAX_LAG, longest - 1)
    size = 1 << (longest + lag).bit_length()
    cov = [0.0] * (lag + 1)
    power = [0.0] * (size // 2)
    shuffled = [0.0] * (size // 2)
    for r in returns:
        if len(r) < 2:
            continue
        s = spectrum(r, size)
        back = fft([complex(x) for x in s], inverse=True)
        for k in range(lag + 1):
            cov[k] += back[k].real / size
        for k in range(1, size // 2):
            power[k] += s[k]
        mixed = r[:]
        rng.shuffle(mixed)
        s = spectrum(mixed, size)
        for k in range(1, size // 2):
            shuffled[k] += s[k]
    acf = [c / cov[0] if cov[0] else 0.0 for c in cov]
    band = 1.96 / math.sqrt(n)
    beyond = [(abs(acf[k]), k) for k in range(2, lag + 1)]
    peaks = []  # local maxima above their neighbourhood, each period once
    local, noise = relative(power), relative(shuffled)
    span = range(max(2, 4 * size // longest), size // 2 - 1)  # periods that fit 4+ times in a day
    for k in sorted(span, key=lambda k: local[k], reverse=True):
        if power[k] >= power[k - 1] and power[k] >= power[k + 1] and all(abs(k - j) > max(size // longest * 2, j // 50) for j, _ in peaks):
            peaks.append((k, local[k]))
        if len(peaks) == TOP:
            break
    ratios = {}
    for q in VR_LAGS:
        num = den = 0.0
        count = 0
        for prices, one in zip(paths, returns):
            if len(prices) <= q or len(one) < 2:
                continue
            drift = statistics.fmean(one)
            num += sum((prices[t + q] - prices[t] - q * drift) ** 2 for t in range(len(prices) - q))
            den += sum((x - drift) ** 2 for x in one) * (len(prices) - q) / len(one)
            count += 1
        ratios[q] = num / (q * den) if count and den else None
    return {
        "n": n,
        "moved": sum(1 for r in returns for x in r if x),
        "acf1": acf[1] if lag >= 1 else None,
        "lags": lag - 1,
        "outside": sum(1 for v, _ in beyond if v > band),
        "largest": max(beyond) if beyond else None,
        "vr": ratios,
        "peaks": [(size / k, ratio) for k, ratio in peaks],
        "shuffled": max(noise[k] for k in span) if any(shuffled) else None,
    }


# ---------------------------------------------------------------------------- increments


def increments(days: list[Day], product: str) -> dict:
    """The one-tick moves' sizes in the data's price unit, the large ones and the price grid per day."""
    sizes: Counter = Counter()
    grids = []
    tick_price = None
    for day in days:
        tick, unit = scale(day, product)
        tick_price = tick * unit
        mids = wall_mids(day, product)
        for a, b in zip(mids, mids[1:]):
            if a is not None and b is not None and a != b:
                sizes[round(abs(b - a) / tick, 6)] += 1  # in ticks
        grids.append([m / tick for m in mids if m is not None])
    if not sizes:
        return {"moves": 0, "tick": tick_price}
    total = sum(sizes.values())
    median = statistics.median(sorted(sizes.elements()))
    large = Counter({s: c for s, c in sizes.items() if s >= LARGE * median})
    passing = []  # (k, shares per day): a day has at least max(20%, 3/k) of its wall mids on k's multiples, at 3+ levels
    for k in GRIDS:
        on = [[x for x in xs if abs(x / k - round(x / k)) < 1e-9] for xs in grids]
        shares = [len(o) / len(xs) if xs else 0.0 for o, xs in zip(on, grids)]
        if any(s >= max(0.2, 3 / k) and len(set(o)) >= 3 for s, o in zip(shares, on)):
            passing.append((k, shares))
    best = max((max(shares) for _, shares in passing), default=0.0)
    chosen = max(((k, shares) for k, shares in passing if max(shares) >= 0.75 * best), default=None)  # 2k holds only half of k's
    return {
        "moves": total,
        "tick": tick_price,
        "common": [(s, c / total) for s, c in sizes.most_common(TOP + 1)],
        "median": median,
        "large": sum(large.values()),
        "large_sizes": [(s, c / sum(large.values())) for s, c in large.most_common(2)],
        "grid": chosen,
        "days": len(days),
    }


# ---------------------------------------------------------------------------- trades


def arrivals(days: list[Day], product: str) -> dict:
    """Gaps between ticks with a market trade, and the dispersion of trade counts per 100 ticks."""
    gaps, windows = [], []
    trades = with_trade = ticks = 0
    for day in days:
        counts = [len(t.trades.get(product, ())) for t in day.ticks]
        ticks += len(counts)
        trades += sum(counts)
        at = [i for i, c in enumerate(counts) if c]
        with_trade += len(at)
        gaps += diffs(at)
        windows += [sum(counts[i:i + 100]) for i in range(0, len(counts) - 99, 100)]
    if len(gaps) < 2:
        return {"trades": trades, "days": len(days)}
    p = with_trade / ticks
    mean_w = statistics.fmean(windows) if windows else 0.0
    return {
        "trades": trades,
        "days": len(days),
        "p": p,
        "per_tick": trades / with_trade,
        "gap": statistics.fmean(gaps),
        "cv": statistics.pstdev(gaps) / statistics.fmean(gaps),
        "cv_poisson": math.sqrt(1 - p),
        "dispersion": statistics.pvariance(windows) / mean_w if len(windows) > 1 and mean_w else None,
        "gap_mode": Counter(gaps).most_common(1)[0],
    }


def clocks(days: list[Day], products: list[str]) -> list[list[str]]:
    """Groups of two or more products that trade on exactly the same ticks every day: one trade clock."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for p in products:
        key = tuple(frozenset(i for i, t in enumerate(day.ticks) if t.trades.get(p)) for day in days)
        if any(key):
            groups[key].append(p)
    return sorted((g for g in groups.values() if len(g) > 1), key=lambda g: (-len(g), g))


# ---------------------------------------------------------------------------- starts


def starts(days: list[Day], product: str) -> dict:
    """Each day's first and last wall mid in ticks, the gaps from the previous close and the one-tick sd."""
    opens, closes, moves_ = [], [], []
    for day in days:
        tick, _ = scale(day, product)
        mids = [m / tick for m in wall_mids(day, product) if m is not None]
        if not mids:
            continue
        opens.append(mids[0])
        closes.append(mids[-1])
        moves_ += diffs(mids)
    if len(opens) < 2:
        return {"opens": opens}
    sd = statistics.pstdev(moves_) if len(moves_) > 1 else 0.0
    gaps = [o - c for o, c in zip(opens[1:], closes)]
    path = statistics.pstdev(moves_) * math.sqrt(len(moves_) / len(opens)) if moves_ else 0.0  # a day's typical travel
    rms = math.sqrt(statistics.fmean(g * g for g in gaps))
    if max(opens) - min(opens) <= 1:
        reading = "every day opens at one level"
    elif all(abs(g) <= max(10 * sd, 2) for g in gaps):
        reading = "each day continues the last"
    elif statistics.pstdev(opens) < 0.5 * rms:
        reading = "each day opens near one level"
    elif all(abs(g) <= path for g in gaps):
        reading = "gaps within a day's travel"
    else:
        reading = "jumps between days"
    return {"opens": opens, "gaps": gaps, "sd": sd, "path": path, "reading": reading}


# ---------------------------------------------------------------------------- repeats

MOD = (1 << 61) - 1
BASE = 1_000_003


def window_hashes(moves_: list[int]) -> list[int | None]:
    """A rolling hash of every WINDOW-long run of moves (None for runs with fewer than ACTIVE moves)."""
    out: list[int | None] = []
    if len(moves_) < WINDOW:
        return out
    top = pow(BASE, WINDOW - 1, MOD)
    h = 0
    active = 0
    for i, m in enumerate(moves_):
        if i >= WINDOW:
            old = moves_[i - WINDOW]
            h = (h - (old % MOD) * top) % MOD
            active -= old != 0
        h = (h * BASE + m) % MOD
        active += m != 0
        if i >= WINDOW - 1:
            out.append(h if active >= ACTIVE else None)
    return out


def repeats(days: list[Day], products: list[str]) -> dict:
    """For every ordered pair of (product, day) series: the share of the first's non-overlapping windows
    found anywhere in the second, and the most common offset between them (in ticks)."""
    names, hashes = [], []
    for day in days:
        for p in products:
            tick, _ = scale(day, p)
            mids = carried(wall_mids(day, p))
            names.append((p, day.name))
            hashes.append(window_hashes([round(2 * x / tick) for x in diffs(mids)]))  # half ticks
    where: dict[int, list[int]] = defaultdict(list)
    for sid, hs in enumerate(hashes):
        for h in set(h for h in hs if h is not None):
            where[h].append(sid)
    found: dict[tuple[int, int], int] = Counter()
    windows = []
    for sid, hs in enumerate(hashes):
        own = [hs[i] for i in range(0, len(hs), WINDOW) if hs[i] is not None]
        windows.append(len(own))
        for h in own:
            for other in where.get(h, ()):
                if other != sid:
                    found[(sid, other)] += 1
    pairs = []
    for (a, b), count in found.items():
        share = count / windows[a]
        if share >= REPEAT_SHARE and count >= 3:
            at = {h: i for i, h in enumerate(hashes[b]) if h is not None}
            offsets = Counter(at[hashes[a][i]] - i for i in range(0, len(hashes[a]), WINDOW) if hashes[a][i] in at)
            pairs.append((names[a], names[b], count, windows[a], offsets.most_common(1)[0][0]))
    return {"series": len(names), "windows": sum(windows), "pairs": sorted(pairs, key=lambda r: (-r[2] / r[3], r[0], r[1]))}


# ---------------------------------------------------------------------------- sums


def groups_of(products: list[str], given: list[list[str]]) -> list[list[str]]:
    """The groups named with --group, else products sharing a name prefix (before the first _), else all."""
    if given:
        return given
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for p in products:
        by_prefix[p.split("_")[0]].append(p)
    groups = [g for g in by_prefix.values() if len(g) > 1]
    if not groups and 1 < len(products):
        groups = [list(products)]
    return groups


def covariance(series: list[list[float]]) -> list[list[float]]:
    means = [statistics.fmean(s) for s in series]
    centred = [[x - m for x in s] for s, m in zip(series, means)]
    n = len(series[0])
    k = len(series)
    out = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(i, k):
            out[i][j] = out[j][i] = sum(map(float.__mul__, centred[i], centred[j])) / max(n - 1, 1)
    return out


def tightness(w: tuple[int, ...], cov: list[list[float]]) -> float:
    k = len(w)
    var = sum(w[i] * w[j] * cov[i][j] for i in range(k) for j in range(k) if w[i] and w[j])
    norm = sum(w[i] * w[i] * cov[i][i] for i in range(k))
    return var / norm if norm else math.inf


def vectors(k: int):
    """Canonical integer weights: in [-3, 3] up to 6 products, [-1, 1] up to 11, at least two nonzero,
    the first nonzero positive, gcd 1."""
    span = 3 if k <= 6 else 1 if k <= 11 else 0
    for w in itertools.product(range(-span, span + 1), repeat=k):
        nonzero = [x for x in w if x]
        if len(nonzero) < 2 or nonzero[0] < 0 or math.gcd(*nonzero) != 1:
            continue
        yield w


def package(days: list[Day], members: list[str], w: tuple[int, ...], level: float) -> list[dict]:
    """The package take on an identity (DU's Pebbles rule): per day, the ticks where selling every leg at
    the touch (w > 0 at the bid, w < 0 at the ask) brings more than the level, or buying them costs less,
    the mean excess, and the gross excess times the size the touch and the limits allow (an upper bound:
    as if each tick's deviation could be taken and the position reset)."""
    out = []
    for day in days:
        units = [scale(day, p)[1] for p in members]
        row = {"day": day.name, "sell": 0, "buy": 0, "excess": 0.0, "gross": 0.0}
        for t in day.ticks:
            books = [t.books.get(p) for p in members]
            if any(b is None or not b.bids or not b.asks for b in books):
                continue
            for side, sign in (("sell", 1), ("buy", -1)):
                # selling takes the bids of the positive legs and the asks of the negative ones; buying the reverse
                touch = [(b.bids[0] if (wi > 0) == (sign > 0) else b.asks[0]) for b, wi in zip(books, w)]
                value = sum(wi * price * u for wi, (price, _), u in zip(w, touch, units))
                excess = sign * (value - level)
                if excess > 1e-9:
                    size = min(min(volume // abs(wi), day.limits.get(p, volume) // abs(wi))
                               for wi, (_, volume), p in zip(w, touch, members) if wi)
                    row[side] += 1
                    row["excess"] += excess
                    row["gross"] += excess * size
        ticks = row["sell"] + row["buy"]
        row["excess"] = row["excess"] / ticks if ticks else 0.0
        out.append(row)
    return out


def evaluate(w: tuple[int, ...], members: list[str], levels: list[dict[str, list[float]]], covs: list) -> dict:
    """The weighted sum's mean, sd and tightness on every day, and the verdict."""
    means, sds, tights = [], [], []
    for day, cov in zip(levels, covs):
        total = [sum(wi * day[p][t] for wi, p in zip(w, members) if wi) for t in range(len(day[members[0]]))]
        means.append(statistics.fmean(total))
        sds.append(statistics.pstdev(total))
        tights.append(tightness(w, cov))
    holds = all(abs(m - means[0]) <= 2 * max(sds[0], s, 0.5) for m, s in zip(means[1:], sds[1:]))
    if len(means) == 1:
        verdict = "one day: no held-out check"
    elif all(t < TIGHT for t in tights) and holds:
        verdict = "identity"
    elif all(t < MIRROR for t in tights):
        verdict = "tight within each day, the level moves"
    elif tights[0] < MIRROR:
        verdict = "tight on the search day only"
    else:
        verdict = "none"
    return {"weights": w, "means": means, "sds": sds, "tights": tights, "verdict": verdict}


def sums(days: list[Day], products: list[str], groups: list[list[str]], checks: list[dict[str, int]], search: int = 0) -> dict:
    """Per group, the tightest weight vectors on the search day with their held-out days; every pair's
    sum and difference across all products; the named checks."""
    order = [days[search]] + days[:search] + days[search + 1:]
    levels = []
    for day in order:
        levels.append({p: [x * scale(day, p)[1] for x in carried(wall_mids(day, p))] for p in products})
    out = {"days": [d.name for d in order], "groups": [], "pairs": [], "checks": []}
    for members in groups:
        members = [p for p in members if p in products and statistics.pstdev(levels[0][p]) > 0]
        if len(members) < 2:
            continue
        covs = [covariance([day[p] for p in members]) for day in levels]
        span = 3 if len(members) <= 6 else 1 if len(members) <= 11 else 0
        if not span:
            out["groups"].append({"members": members, "skipped": True})
            continue
        scored = sorted((tightness(w, covs[0]), w) for w in vectors(len(members)))
        legs = statistics.median(math.sqrt(covs[0][i][i]) for i in range(len(members)))
        best = [evaluate(w, members, levels, covs) for _, w in scored[:TOP]]
        for b in best:
            if b["verdict"] == "identity":
                b["package"] = package(order, members, b["weights"], b["means"][0])
        out["groups"].append({"members": members, "span": span, "count": len(scored), "legs": legs, "best": best})
    if 2 < len(products) <= 60:
        cov = covariance([levels[0][p] for p in products])
        candidates = []
        for i, j in itertools.combinations(range(len(products)), 2):
            for sign in (1, -1):
                norm = cov[i][i] + cov[j][j]
                if norm:
                    candidates.append(((cov[i][i] + cov[j][j] + 2 * sign * cov[i][j]) / norm, products[i], products[j], sign))
        for t, a, b, sign in sorted(candidates)[:TOP + 2]:
            if t >= MIRROR:
                break
            members = [a, b]
            covs = [covariance([day[a], day[b]]) for day in levels]
            out["pairs"].append((members, evaluate((1, sign), members, levels, covs)))
    for check in checks:
        members = [p for p in check if p in products]
        if len(members) == len(check) and len(members) > 1:
            covs = [covariance([day[p] for p in members]) for day in levels]
            out["checks"].append((members, evaluate(tuple(check[p] for p in members), members, levels, covs)))
    return out


# ---------------------------------------------------------------------------- fingerprints


def _wall(levels: tuple[tuple[float, int], ...]) -> tuple[float, int] | None:
    return max(levels, key=lambda level: level[1]) if levels else None  # first of the largest: nearest the touch, as Book.wall_mid


def inner(book: Book | None) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """The non-wall levels' volumes a side, sorted: the book's noise orders."""
    if book is None:
        return (), ()
    wb, wa = _wall(book.bids), _wall(book.asks)
    return tuple(sorted(v for level in book.bids if level != wb for v in level[1:])), tuple(sorted(v for level in book.asks if level != wa for v in level[1:]))


def offsets(days: list[Day], product: str) -> dict:
    """The inner levels' offsets from the wall mid, in ticks, and their volumes."""
    found: Counter = Counter()
    volumes: Counter = Counter()
    for day in days:
        tick, _ = scale(day, product)
        for t in day.ticks:
            book = t.books.get(product)
            if book is None or book.wall_mid is None:
                continue
            wb, wa = _wall(book.bids), _wall(book.asks)
            for level in book.bids + book.asks:
                if level not in (wb, wa):
                    found[(level[0] - book.wall_mid) / tick] += 1
                    volumes[level[1]] += 1
    n = sum(found.values())
    return {"n": n, "top": [(o, c / n) for o, c in found.most_common(4)] if n else [],
            "volumes": (min(volumes), max(volumes), len(volumes)) if volumes else None}


def streams(days: list[Day], products: list[str]) -> list[tuple[str, str, float, float, int]]:
    """Pairs whose inner (side, volume) multisets are identical on the same tick, against the share with
    the second product one tick later: (a, b, share, null share, ticks)."""
    index = {p: i for i, p in enumerate(products)}
    same: Counter = Counter()
    null: Counter = Counter()
    den_same: Counter = Counter()
    den_null: Counter = Counter()
    for day in days:
        keys = []
        pres = {p: 0 for p in products}
        full = {p: 0 for p in products}
        for i, t in enumerate(day.ticks):
            row = {}
            for p in products:
                book = t.books.get(p)
                if book is None:
                    continue
                pres[p] |= 1 << i
                key = inner(book)
                if key != ((), ()):
                    full[p] |= 1 << i
                    row[p] = key
            keys.append(row)
        for i, row in enumerate(keys):
            groups: dict = defaultdict(list)
            for p, key in row.items():
                groups[key].append(p)
            for members in groups.values():
                for a, b in itertools.combinations(sorted(members, key=index.get), 2):
                    same[(a, b)] += 1
            if i + 1 < len(keys):
                later: dict = defaultdict(list)
                for p, key in keys[i + 1].items():
                    later[key].append(p)
                for key, members in groups.items():
                    for a in members:
                        for b in later.get(key, ()):
                            if index[a] < index[b]:
                                null[(a, b)] += 1
        for a, b in itertools.combinations(products, 2):
            den_same[(a, b)] += (pres[a] & pres[b] & (full[a] | full[b])).bit_count()
            den_null[(a, b)] += (pres[a] & (pres[b] >> 1) & (full[a] | (full[b] >> 1))).bit_count()
    out = []
    for (a, b), n in den_same.items():
        if not n:
            continue
        share = same[(a, b)] / n
        base = null[(a, b)] / den_null[(a, b)] if den_null[(a, b)] else 0.0
        if share >= STREAM_SHARE and share >= STREAM_LIFT * base:
            out.append((a, b, share, base, n))
    return sorted(out, key=lambda r: -r[2])


def clusters(pairs: list[tuple[str, str, float, float, int]]) -> list[tuple[list[str], list[tuple]]]:
    """The listed pairs joined into connected groups of products, largest first."""
    parent: dict[str, str] = {}

    def root(x: str) -> str:
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    for a, b, *_ in pairs:
        parent[root(a)] = root(b)
    groups: dict[str, list[str]] = defaultdict(list)
    for x in list(parent):
        groups[root(x)].append(x)
    out = [(sorted(members), [r for r in pairs if root(r[0]) == key]) for key, members in groups.items()]
    return sorted(out, key=lambda c: (-len(c[0]), c[0]))


def hidden_depth(days: list[Day], product: str) -> dict:
    """Market trades at a price with no displayed level (and of those, inside the spread), and trades
    larger than the volume displayed at their price, against the same tick's book. And trades outside
    every price this tick's book and the last showed (below the lowest level, above the highest), with
    how far beyond the furthest went, in the data's price units."""
    total = missing = inside = larger = outside = 0
    furthest = 0.0
    for day in days:
        last = None
        for t in day.ticks:
            book = t.books.get(product)
            shown_prices = [price for b in (last, book) if b is not None for price, _ in (*b.bids, *b.asks)]
            for trade in t.trades.get(product, ()):
                total += 1
                if shown_prices:
                    beyond = max(min(shown_prices) - trade.price, trade.price - max(shown_prices), 0)
                    outside += beyond > 0
                    furthest = max(furthest, beyond)
                if book is None:
                    missing += 1
                    continue
                shown = dict(book.bids) | dict(book.asks)
                if trade.price not in shown:
                    missing += 1
                    inside += bool(book.bids and book.asks and book.bids[0][0] < trade.price < book.asks[0][0])
                elif abs(trade.quantity) > shown[trade.price]:
                    larger += 1
            if book is not None and (book.bids or book.asks):
                last = book
    return {"trades": total, "missing": missing / total if total else None, "inside": inside / total if total else None,
            "larger": larger / total if total else None, "outside": outside / total if total else None, "furthest": furthest}


# ---------------------------------------------------------------------------- report


def _num(value: float | None, fmt: str) -> str:
    return "-" if value is None else format(value, fmt)


def _weights(w: tuple[int, ...], members: list[str]) -> str:
    parts = []
    for x, p in zip(w, members):
        if x:
            parts.append(("+ " if x > 0 else "- ") + (f"{abs(x)} " if abs(x) != 1 else "") + p)
    text = " ".join(parts)
    return text[2:] if text.startswith("+ ") else text


def _sum_row(members: list[str], r: dict) -> str:
    tights = " / ".join(_num(t, ".3f") for t in r["tights"])
    days = " / ".join(f"{m:,.1f} sd {s:,.1f}" for m, s in zip(r["means"], r["sds"]))
    return f"| {_weights(r['weights'], members)} | {tights} | {days} | {r['verdict']} |"


def report(name: str, days: list[Day], products: list[str], sections: list[str], groups: list[list[str]],
           checks: list[dict[str, int]], search: int = 0) -> str:
    lines = [f"## {name}: {len(products)} products, days {', '.join(d.name for d in days)}"]
    if "moves" in sections:
        lines += ["", f"### Moves: one-tick returns of the wall mid, in ticks (band ±1.96/√n: about 5% of lags outside by chance; "
                  "VR is 1 for a random walk; a peak is against the median of its 128 neighbours, and the shuffled returns' highest is the noise level)", "",
                  f"| product | moves | ACF lag 1 | lags 2–{MAX_LAG:,} outside the band | largest beyond lag 1 (lag) | VR "
                  + " / ".join(map(str, VR_LAGS)) + " | periodogram peaks: period in ticks (× its neighbours' median) | shuffled peak |",
                  "|---|---|---|---|---|---|---|---|"]
        for p in products:
            r = moves(days, p)
            if not r.get("moved"):
                lines.append(f"| {p} | 0 | - | - | - | - | - | - |")
                continue
            largest = r["largest"]
            vr = " / ".join(_num(r["vr"][q], ".2f") for q in VR_LAGS)
            peaks = ", ".join(f"{period:,.1f} ({ratio:.1f})" for period, ratio in r["peaks"])
            lines.append(f"| {p} | {r['moved']:,} | {r['acf1']:+.3f} | {r['outside']:,} of {r['lags']:,} | "
                         f"{_num(largest and largest[0], '.3f')} ({largest[1] if largest else '-'}) | {vr} | {peaks} | {_num(r['shuffled'], '.1f')} |")
    if "increments" in sections:
        lines += ["", f"### Increments: the wall mid's one-tick moves in ticks (large: at least {LARGE}× the median move; "
                  "grid: the largest k whose multiples hold the wall mid on at least max(20%, 3/k) of a day's ticks)", "",
                  "| product | tick | moves | common sizes (share) | large moves | their sizes: ticks = price (share of large) | grid: k ticks, share per day |",
                  "|---|---|---|---|---|---|---|"]
        for p in products:
            r = increments(days, p)
            if not r["moves"]:
                lines.append(f"| {p} | {r['tick']:g} | 0 | - | - | - | - |")
                continue
            common = ", ".join(f"{s:g} ({c:.0%})" for s, c in r["common"])
            large = ", ".join(f"{s:g} = {s * r['tick']:g} ({c:.0%})" for s, c in r["large_sizes"]) or "-"
            grid = f"{r['grid'][0]}: " + " / ".join(f"{s:.0%}" for s in r["grid"][1]) if r["grid"] else "none"
            lines.append(f"| {p} | {r['tick']:g} | {r['moves']:,} | {common} | {r['large']:,} | {large} | {grid} |")
    if "trades" in sections:
        lines += ["", "### Trade arrivals against Poisson (gap CV √(1 − p) and dispersion 1 for independent ticks)", "",
                  "| product | trades a day | ticks with a trade | trades a trade tick | mean gap | gap CV (Poisson) | dispersion per 100 ticks | commonest gap (count) |",
                  "|---|---|---|---|---|---|---|---|"]
        for p in products:
            r = arrivals(days, p)
            if "p" not in r:
                lines.append(f"| {p} | {r['trades'] / max(r['days'], 1):,.0f} | - | - | - | - | - | - |")
                continue
            lines.append(f"| {p} | {r['trades'] / r['days']:,.0f} | {r['p']:.1%} | {r['per_tick']:.2f} | {r['gap']:.1f} | "
                         f"{r['cv']:.2f} ({r['cv_poisson']:.2f}) | {_num(r['dispersion'], '.2f')} | {r['gap_mode'][0]} ({r['gap_mode'][1]:,}) |")
        shared = clocks(days, products)
        lines += ["", "Products that trade on exactly the same ticks every day: "
                  + ("; ".join(f"{len(g)} ({', '.join(g) if len(g) <= 6 else ', '.join(g[:5]) + ', ...'})" for g in shared) or "none")]
    if "starts" in sections and len(days) > 1:
        lines += ["", "### Day starts: each day's opening wall mid against the previous day's close, in ticks", "",
                  "| product | opens | gaps from the previous close | one-tick sd | a day's travel | reading |", "|---|---|---|---|---|---|"]
        for p in products:
            r = starts(days, p)
            if "gaps" not in r:
                continue
            lines.append(f"| {p} | {' / '.join(f'{o:,.1f}' for o in r['opens'])} | {' / '.join(f'{g:+,.1f}' for g in r['gaps'])} | "
                         f"{r['sd']:.2f} | {r['path']:,.1f} | {r['reading']} |")
    if "repeats" in sections:
        r = repeats(days, products)
        lines += ["", f"### Exact repeats: {WINDOW}-tick runs of moves with at least {ACTIVE} moves, from {r['series']} series "
                  f"(product, day), {r['windows']:,} windows; pairs where {REPEAT_SHARE:.0%} of one's windows are in the other", ""]
        same_product: dict = defaultdict(list)
        others, seen = [], set()
        for a, b, count, total, off in r["pairs"]:
            if a[0] == b[0]:
                if (b[1], a[1], -off) not in same_product:  # each pair of days once
                    same_product[(a[1], b[1], off)].append(count / total)
            elif (b, a) not in seen:
                seen.add((a, b))
                others.append((a, b, count, total, off))
        if not same_product and not others:
            lines.append("none")
        else:
            lines += ["| series | found in | products | windows found | offset (ticks) |", "|---|---|---|---|---|"]
            for (da, db, off), shares in sorted(same_product.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                lines.append(f"| day {da} | day {db} | {len(shares)} of {len(products)}, the same product | "
                             f"{min(shares):.0%}–{max(shares):.0%} | {off:+,} |")
            for a, b, count, total, off in others[:20]:
                lines.append(f"| {a[0]} {a[1]} | {b[0]} {b[1]} | across products | {count}/{total} = {count / total:.0%} | {off:+,} |")
    if "sums" in sections:
        r = sums(days, products, groups_of(products, groups), checks, search)
        if r["groups"] or r["pairs"] or r["checks"]:
            lines += ["", f"### Fixed sums: searched on {r['days'][0]}, held out {', '.join(r['days'][1:]) or 'none'} "
                      f"(tightness about 1 for unrelated walks, 0 for an identity; identity: below {TIGHT} every day and the level within 2 sds)", ""]
        else:
            lines += ["", "### Fixed sums: no group of two or more moving products"]
        for g in r["groups"]:
            if g.get("skipped"):
                lines.append(f"- {', '.join(g['members'])}: {len(g['members'])} products, too many to search")
                continue
            lines += [f"**{', '.join(g['members'])}** ({g['count']:,} weight vectors in [−{g['span']}, {g['span']}]; legs' median sd {g['legs']:,.1f}):", "",
                      "| weights | tightness per day | the sum per day: mean, sd | verdict |", "|---|---|---|---|"]
            lines += [_sum_row(g["members"], b) for b in g["best"]] + [""]
            for b in g["best"]:
                if "package" in b:
                    lines += [f"The package take on {_weights(b['weights'], g['members'])} = {b['means'][0]:,.1f} (sell every leg at the touch when "
                              "that brings more, buy when it costs less; gross: the excess times the size the touch and limits allow, an upper bound): "
                              + "; ".join(f"{r['day']}: {r['sell']:,} ticks to sell and {r['buy']:,} to buy, {r['excess']:.1f} on average, "
                                          f"gross {r['gross']:,.0f}" for r in b["package"]), ""]
        if r["pairs"]:
            lines += ["**Pairs across all products** (sums and differences, tightness below "
                      f"{MIRROR} on the search day):", "", "| weights | tightness per day | the sum per day: mean, sd | verdict |", "|---|---|---|---|"]
            lines += [_sum_row(m, b) for m, b in r["pairs"]] + [""]
        if r["checks"]:
            lines += ["**Named weights** (--weights):", "", "| weights | tightness per day | the sum per day: mean, sd | verdict |", "|---|---|---|---|"]
            lines += [_sum_row(m, b) for m, b in r["checks"]] + [""]
    if "fingerprints" in sections:
        lines += ["", "### Fingerprints: inner orders' offsets from the wall mid (ticks), and hidden depth", "",
                  "| product | inner levels | top offsets (share) | on those four | inner volumes: min–max (distinct) | trades | at no shown price (inside the spread) | larger than shown | outside the book (furthest beyond it) |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for p in products:
            o, h = offsets(days, p), hidden_depth(days, p)
            top = ", ".join(f"{x:+g} ({c:.0%})" for x, c in o["top"]) or "-"
            vols = f"{o['volumes'][0]}–{o['volumes'][1]} ({o['volumes'][2]})" if o["volumes"] else "-"
            lines.append(f"| {p} | {o['n']:,} | {top} | {sum(c for _, c in o['top']):.0%} | {vols} | {h['trades']:,} | "
                         f"{_num(h['missing'], '.1%')} ({_num(h['inside'], '.1%')}) | {_num(h['larger'], '.1%')} | "
                         f"{_num(h['outside'], '.2%')} ({h['furthest']:g}) |")
        pairs = streams(days, products)
        lines += ["", f"Shared noise streams: pairs whose inner (side, volume) multisets match on at least {STREAM_SHARE:.0%} of ticks "
                  f"and {STREAM_LIFT:g}× the share with the second a tick later, joined into clusters:", ""]
        if not pairs:
            lines.append("none")
        else:
            lines += ["| products sharing a stream | pairs listed | identical on | a tick apart |", "|---|---|---|---|"]
            for members, rows in clusters(pairs):
                lines.append(f"| {', '.join(members)} | {len(rows)} of {len(members) * (len(members) - 1) // 2} | "
                             f"{min(r[2] for r in rows):.0%}–{max(r[2] for r in rows):.0%} | {max(r[3] for r in rows):.0%} at most |")
    return "\n".join(lines)


def parse_weights(text: str) -> dict[str, int]:
    """PRODUCT:W,PRODUCT:W into {product: weight}."""
    out = {}
    for part in text.split(","):
        product, _, weight = part.strip().rpartition(":")
        if not product:
            raise ValueError(f"--weights wants PRODUCT:W,PRODUCT:W, got {text!r}")
        out[product] = int(weight)
    return out


def register_plugin(argv: list[str] | None) -> None:
    """--plugin FILE: a format plug-in not yet in FORMATS, registered under its file's stem."""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--plugin", type=Path)
    known, _ = pre.parse_known_args(argv)
    if known.plugin:
        spec = importlib.util.spec_from_file_location(known.plugin.stem, known.plugin)
        module = importlib.util.module_from_spec(spec)
        sys.modules[known.plugin.stem] = module
        spec.loader.exec_module(module)
        FORMATS.setdefault(known.plugin.stem, module)


def main(argv: list[str] | None = None) -> None:
    register_plugin(argv if argv is not None else sys.argv[1:])
    parser = argparse.ArgumentParser(prog="python -m experiments.day.structure")
    add_dataset_arguments(parser, bot=False)
    parser.add_argument("--plugin", type=Path, help="a format plug-in file not yet registered in FORMATS; then --format <its file's stem>")
    parser.add_argument("--sections", default=",".join(SECTIONS), help=f"comma-separated sections to print (default: all of {', '.join(SECTIONS)})")
    parser.add_argument("--group", action="append", default=[], metavar="A,B,...",
                        help="products to search for fixed sums together (repeatable; default: name prefixes, or every product)")
    parser.add_argument("--weights", action="append", default=[], metavar="A:W,B:W",
                        help="a weight vector to check on every day, e.g. a published basket (repeatable)")
    parser.add_argument("--search-day", type=int, default=0, help="which loaded day the fixed-sum search scores on, by position (default: 0, the first)")
    args = parser.parse_args(argv)
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    if unknown := [s for s in sections if s not in SECTIONS]:
        parser.error(f"unknown sections {', '.join(unknown)}; choose from {', '.join(SECTIONS)}")
    try:
        dataset = dataset_from(args)
        checks = [parse_weights(w) for w in args.weights]
    except ValueError as error:
        parser.error(str(error))
    groups = [[p.strip() for p in g.split(",") if p.strip()] for g in args.group]
    runs = [(name, alias, "prosperity", specs, products, [parse_weights(w) for w in named]) for name, alias, specs, products, named in DATASETS]
    if dataset:
        runs = [(dataset.name, dataset.data, dataset.format, list(dataset.days), list(dataset.products), checks)]
    for name, data, format_name, specs, products, named in runs:
        fmt = FORMATS[format_name]
        days = fmt.load_days(fmt.resolve_data_dir(data), specs)
        products = products or sorted({p for day in days for p in day.products})
        search = min(max(args.search_day, 0), len(days) - 1)
        print(report(name, days, products, sections, groups, named, search) + "\n")


if __name__ == "__main__":
    main()
