"""The statistics arena.grid judges a search by: Bailey et al.'s CSCV (PBO), Bailey and Lopez de
Prado's deflated Sharpe ratio and its number of independent trials, Hansen's SPA test with
Politis and Romano's stationary bootstrap, and Romano and Wolf's StepM. python/arena/grid.py's docstring
says what each one answers; the formulas are cited where they are computed.

rust/src/arena/stats.rs is this module's twin, the same to the bit (rust/twins.json): the parts whose
cost grows with the cells (cscv, mean_correlation, snooping), which arena.grid --engine rust runs
there. Standard library only.
"""

from __future__ import annotations

import itertools
import math
import random
import statistics
from dataclasses import dataclass
from operator import itemgetter, mul

MAX_SPLITS = 4000  # halvings of the blocks to score; sampled (seeded) when there are more
EULER_GAMMA = 0.5772156649015329
ALPHA = 0.05  # StepM's familywise error


@dataclass(frozen=True)
class Cscv:
    pbo: float  # share of halvings where the in-sample best is at or below the out-of-sample median
    loss: float  # share of halvings where it loses money out of sample
    rank: float  # its mean relative rank w out of sample: near 1 the top, 0.5 the median
    splits: int  # halvings scored
    of: int  # halvings there are


def cscv(columns: list[list[float]], max_splits: int = MAX_SPLITS, seed: int = 0) -> Cscv:
    """Bailey et al.'s combinatorially symmetric cross-validation (Algorithm 2.3, p. 11-12).

    `columns` holds each cell's PnL per block, the blocks in the same order for every cell. Each
    halving of the blocks is a training half and a test half; the cell with the best training PnL
    gets its test rank r in 1..N (higher is better, ties averaged), w = r / (N + 1), and the
    halving counts as overfit when the logit ln(w / (1 - w)) <= 0.
    """
    n, s = len(columns), len(columns[0])
    of = math.comb(s, s // 2)
    if of <= max_splits:
        halvings = list(itertools.combinations(range(s), s // 2))
    else:
        rng, seen = random.Random(seed), set()
        while len(seen) < max_splits:
            seen.add(tuple(sorted(rng.sample(range(s), s // 2))))
        halvings = sorted(seen)
    totals = [sum(column) for column in columns]
    overfit = losses = 0
    ranks = []
    for train in halvings:
        inside = [sum(column[i] for i in train) for column in columns]
        outside = [total - x for total, x in zip(totals, inside)]
        best = max(range(n), key=inside.__getitem__)
        mine = outside[best]
        rank = sum(1 for v in outside if v < mine) + (sum(1 for v in outside if v == mine) + 1) / 2
        w = rank / (n + 1)
        overfit += math.log(w / (1 - w)) <= 0
        losses += mine < 0
        ranks.append(w)
    return Cscv(overfit / len(halvings), losses / len(halvings), statistics.fmean(ranks), len(halvings), of)


def expected_max_sharpe(variance: float, trials: float) -> float:
    """SR0, the best Sharpe ratio expected from `trials` independent cells with no edge whose Sharpe
    ratios have this variance (Bailey and Lopez de Prado, eq. 1-2, p. 7-9). 0 below two trials."""
    if trials < 2:
        return 0.0
    z = statistics.NormalDist().inv_cdf
    return math.sqrt(variance) * ((1 - EULER_GAMMA) * z(1 - 1 / trials) + EULER_GAMMA * z(1 - 1 / (trials * math.e)))


def deflated_sharpe(sharpe: float, sharpe0: float, periods: int, skew: float, kurtosis: float) -> float | None:
    """DSR = Z[(SR - SR0) sqrt(T - 1) / sqrt(1 - skew SR + (kurtosis - 1) / 4 SR^2)] (eq. 2, p. 8-9);
    kurtosis is not excess (3 for a normal). None when the root's argument isn't positive."""
    spread = 1 - skew * sharpe + (kurtosis - 1) / 4 * sharpe**2
    if spread <= 0 or periods < 2:
        return None
    return statistics.NormalDist().cdf((sharpe - sharpe0) * math.sqrt(periods - 1) / math.sqrt(spread))


def independent_trials(columns: list[list[float]], correlation=None) -> float:
    """N^ = rho + (1 - rho) M, rho the average pairwise correlation of the M cells' block PnL (eq. 9,
    p. 14-15). Cells with a constant PnL per block have no correlation and are left out of rho.
    `correlation` computes rho from the standardized columns (default mean_correlation; arena.rust's
    is its twin)."""
    m = len(columns)
    rho = (correlation or mean_correlation)(standardized(columns))
    return float(m) if rho is None else rho + (1 - rho) * m


def standardized(columns: list[list[float]]) -> list[list[float]]:
    """Each column with a spread, as (x - mean) / sd (population sd); constant columns left out."""
    scaled = []
    for column in columns:
        sd = statistics.pstdev(column)
        if sd > 0:
            mean = statistics.fmean(column)
            scaled.append([(x - mean) / sd for x in column])
    return scaled


def mean_correlation(scaled: list[list[float]]) -> float | None:
    """The mean over every pair of standardized columns of their correlation; None with fewer than two."""
    pairs = [(a, b) for i, a in enumerate(scaled) for b in scaled[i + 1 :]]
    if not pairs:
        return None
    return statistics.fmean(sum(x * y for x, y in zip(a, b)) / len(a) for a, b in pairs)


def omega2(d: list[float], q: float) -> float:
    """Hansen's variance of sqrt(n) times the mean under the stationary bootstrap (p. 8):
    gamma_0 + 2 sum_i kappa(n, i) gamma_i, kappa(n, i) = (n-i)/n (1-q)^i + i/n (1-q)^(n-i)."""
    n, mean = len(d), statistics.fmean(d)
    c = [x - mean for x in d]
    total = sum(map(mul, c, c)) / n
    for i in range(1, n):
        kappa = (n - i) / n * (1 - q) ** i + i / n * (1 - q) ** (n - i)
        if kappa < 1e-12:
            continue
        total += 2 * kappa * sum(map(mul, c, itertools.islice(c, i, None))) / n
    return total


def bootstrap_means(d: list[list[float]], q: float, boot: int, seed: int) -> list[list[float]]:
    """Each resample's mean of every column, by Politis and Romano's stationary bootstrap (Hansen,
    p. 7): with probability q the next index is drawn afresh, else it follows the last, wrapping."""
    n, rng, out = len(d[0]), random.Random(seed), []
    for _ in range(boot):
        idx, t = [], rng.randrange(n)
        for _ in range(n):
            idx.append(t)
            t = rng.randrange(n) if rng.random() < q else (t + 1) % n
        pick = itemgetter(*idx)
        out.append([sum(pick(column)) / n for column in d])
    return out


def _scales(d: list[list[float]], q: float) -> list[float]:
    return [math.sqrt(max(omega2(c, q), 1e-12)) for c in d]


def spa(d: list[list[float]], q: float, boot: int, seed: int = 0, *, omegas=None, draws=None) -> dict[str, float]:
    """Hansen's SPA p-values for H0: no column of gains has a positive mean (p. 4 and 7-8). The
    bootstrap is recentred at mu_l = min(mean, 0), at mu_c (only means clearly below 0 kept, the
    consistent one) and at mu_u = 0 (the studentized Reality Check)."""
    n = len(d[0])
    means = [statistics.fmean(c) for c in d]
    omegas = omegas or _scales(d, q)
    t = max(0.0, max(math.sqrt(n) * m / w for m, w in zip(means, omegas)))
    loglog = math.sqrt(2 * math.log(math.log(n)))
    shifts = {
        "l": [max(0.0, m) for m in means],
        "c": [m if m >= -w / math.sqrt(n) * loglog else 0.0 for m, w in zip(means, omegas)],
        "u": means,
    }
    draws = draws or bootstrap_means(d, q, boot, seed)
    out = {}
    for name, shift in shifts.items():
        above = sum(max(0.0, max(math.sqrt(n) * (x - s) / w for x, s, w in zip(draw, shift, omegas))) > t for draw in draws)
        out[name] = above / len(draws)
    return out


def stepm(d: list[list[float]], q: float, boot: int, alpha: float = ALPHA, seed: int = 1, *, omegas=None, draws=None) -> list[int]:
    """Romano and Wolf's studentized step-down (Algorithms 4.1-4.2, p. 14-15): the columns whose
    mean gain is significantly positive, the familywise error held at alpha. Studentized by
    Hansen's omega, fixed across resamples (ours; the paper recomputes it in each)."""
    n = len(d[0])
    means = [statistics.fmean(c) for c in d]
    omegas = omegas or _scales(d, q)
    z = [math.sqrt(n) * m / w for m, w in zip(means, omegas)]
    draws = draws or bootstrap_means(d, q, boot, seed)
    centred = [[math.sqrt(n) * (x - m) / w for x, m, w in zip(draw, means, omegas)] for draw in draws]
    active, rejected = set(range(len(d))), []
    while active:
        maxima = sorted(max(draw[k] for k in active) for draw in centred)
        c = maxima[min(len(maxima) - 1, math.ceil((1 - alpha) * len(maxima)) - 1)]
        newly = [k for k in active if z[k] > c]
        if not newly:
            break
        rejected += newly
        active -= set(newly)
    return sorted(rejected)


def snooping(d: list[list[float]], q: float, boot: int, alpha: float = ALPHA, seed: int = 0) -> tuple[dict[str, float], list[int]]:
    """SPA's p-values and StepM's columns on the same studentization and resamples, as arena.grid
    reports them."""
    omegas = _scales(d, q)
    draws = bootstrap_means(d, q, boot, seed)
    return spa(d, q, boot, omegas=omegas, draws=draws), stepm(d, q, boot, alpha, omegas=omegas, draws=draws)
