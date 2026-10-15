"""Does the best-level imbalance predict the price on Prosperity data? Gould & Bonart's test, per product and day.

usage (from the repo root): uv run python -m experiments.imbalance

The imbalance is `ρ = (Vᵇ − Vᵃ)/(Vᵇ + Vᵃ)` at the best bid and ask
(references/wiki/concepts/book-imbalance-and-micro-price.md). For each product of the
market-making rounds (DATASETS), three tests:

1. Gould & Bonart: at each tick where the mid changes, `y` = up, against `ρ` one tick before.
   A logistic regression `P(up) = 1/(1 + e^-(x0 + x1 ρ))`, fitted leaving one day out. Reports
   the ROC area and the drop in squared error against a coin flip (0.25), out of sample, the
   sign of `x1` fitted on each day alone, and the same split by spread (in ticks).
2. Fair value: how well each candidate at tick t predicts the wall mid (the market maker's
   price, which the template trades back at) and the mid (Prosperity's mark) H ticks later.
   Root mean squared error, pooled over the days. Candidates: mid, wall_mid, sized_mid (15),
   the weighted mid `W = I·Pᵃ + (1 − I)·Pᵇ` with `I = Vᵇ/(Vᵇ + Vᵃ)`, and `wall_mid + b·ρ`
   with `b` fitted by least squares leaving one day out (the linear micro-price), and
   `wall_mid + G(ρ, spread)`, Stoikov's form: the mean move in each of 5 ρ buckets × the spread
   buckets, also leaving one day out (the micro-price's table at horizon H, without his
   symmetrising or Markov-chain step, so it can only fit better in sample).
3. The fitted `b` per day, in ticks per unit of ρ, at each horizon: a stable sign and size is
   what a `PARAMS` entry would need.
Results go into IDEAS.md ("The micro-price or weighted mid as fair value", "Book imbalance").
"""

from __future__ import annotations

import math
from collections import defaultdict

from arena.formats import prosperity

DATASETS = [  # (data alias, round, products): the rounds whose products the template makes markets in
    ("p2", "1", ["AMETHYSTS", "STARFRUIT"]),
    ("p3", "1", ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]),
    ("p3", "5", ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]),
    ("p4", "1", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
    ("p4", "2", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
]
HORIZONS = (1, 10, 50)
WALL_SIZE = 15
RHO_BUCKETS = 5
TABLE = "wall_mid + G(ρ, spread)"


def imbalance(book) -> float:
    vb, va = book.bids[0][1], book.asks[0][1]
    return (vb - va) / (vb + va)


def sized_mid(book) -> float:
    bid = next((p for p, v in book.bids if v >= WALL_SIZE), book.bids[0][0])
    ask = next((p for p, v in book.asks if v >= WALL_SIZE), book.asks[0][0])
    return (bid + ask) / 2


def weighted_mid(book) -> float:
    i = book.bids[0][1] / (book.bids[0][1] + book.asks[0][1])
    return i * book.asks[0][0] + (1 - i) * book.bids[0][0]


def series(day, product) -> list[dict]:
    """Per tick with both sides present: ρ, spread and the candidate prices."""
    out = []
    for tick in day.ticks:
        book = tick.books.get(product)
        if book is None or not book.bids or not book.asks:
            out.append(None)
            continue
        out.append({
            "rho": imbalance(book), "spread": book.asks[0][0] - book.bids[0][0],
            "mid": book.mid, "wall_mid": book.wall_mid, "sized_mid": sized_mid(book), "weighted": weighted_mid(book),
        })
    return out


def logistic(xs: list[float], ys: list[int], steps: int = 25) -> tuple[float, float]:
    """Fit P(y=1) = 1/(1 + e^-(a + b x)) by Newton's method."""
    a = b = 0.0
    for _ in range(steps):
        ga = gb = haa = hab = hbb = 0.0
        for x, y in zip(xs, ys):
            p = 1 / (1 + math.exp(-(a + b * x)))
            w = p * (1 - p)
            ga += y - p
            gb += (y - p) * x
            haa += w
            hab += w * x
            hbb += w * x * x
        det = haa * hbb - hab * hab
        if det <= 1e-12:
            break
        a += (hbb * ga - hab * gb) / det
        b += (haa * gb - hab * ga) / det
    return a, b


def auc(scores: list[float], ys: list[int]) -> float:
    """ROC area by ranks, ties counted half."""
    pairs = sorted(zip(scores, ys))
    pos = sum(ys)
    neg = len(ys) - pos
    if not pos or not neg:
        return float("nan")
    rank_sum, k = 0.0, 0
    while k < len(pairs):
        j = k
        while j < len(pairs) and pairs[j][0] == pairs[k][0]:
            j += 1
        mean_rank = (k + 1 + j) / 2
        rank_sum += mean_rank * sum(y for _, y in pairs[k:j])
        k = j
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


def moves(rows: list[dict | None]) -> list[tuple[float, int, float]]:
    """(ρ before, up?, spread before) at each tick where the mid changes."""
    out = []
    for prev, cur in zip(rows, rows[1:]):
        if prev and cur and cur["mid"] != prev["mid"]:
            out.append((prev["rho"], int(cur["mid"] > prev["mid"]), prev["spread"]))
    return out


def ols_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope through the origin (the move is centred on the current price)."""
    den = sum(x * x for x in xs)
    return sum(x * y for x, y in zip(xs, ys)) / den if den else 0.0


def ahead(rows: list[dict | None], h: int, target: str) -> list[tuple[dict, float]]:
    return [(r, rows[k + h][target]) for k, r in enumerate(rows[:-h]) if r and rows[k + h]]


def rho_bucket(rho: float) -> int:
    return min(int((rho + 1) / 2 * RHO_BUCKETS), RHO_BUCKETS - 1)


def spread_bucket(s: float) -> str:
    return "1-2" if s <= 2 else "3-5" if s <= 5 else "6-9" if s <= 9 else "10+"


def study(days: list, product: str) -> dict:
    rows = [series(day, product) for day in days]
    out: dict = {"days": [d.name for d in days]}

    # 1. Gould & Bonart, leave one day out.
    per_day = [moves(r) for r in rows]
    out["slopes"] = [logistic([x for x, _, _ in m], [y for _, y, _ in m])[1] for m in per_day]
    scores, ys, spreads = [], [], []
    for k, test in enumerate(per_day):
        train = [m for j, d in enumerate(per_day) if j != k for m in d]
        a, b = logistic([x for x, _, _ in train], [y for _, y, _ in train])
        for x, y, s in test:
            scores.append(1 / (1 + math.exp(-(a + b * x))))
            ys.append(y)
            spreads.append(s)
    out["n"] = len(ys)
    out["auc"] = auc(scores, ys)
    out["brier"] = 1 - sum((p - y) ** 2 for p, y in zip(scores, ys)) / len(ys) / 0.25 if ys else float("nan")
    by_spread = defaultdict(lambda: ([], []))
    for p, y, s in zip(scores, ys, spreads):
        by_spread[spread_bucket(s)][0].append(p)
        by_spread[spread_bucket(s)][1].append(y)
    out["by_spread"] = {k: (len(v[1]), auc(*v)) for k, v in by_spread.items()}

    # 2-3. Candidates as predictors of the wall mid and the mid H ticks later.
    out["rmse"], out["b"] = {}, {}
    for target in ("wall_mid", "mid"):
        for h in HORIZONS:
            pairs = [ahead(r, h, target) for r in rows]
            moves_by_day = [([r["rho"] for r, _ in p], [f - r["wall_mid"] for r, f in p]) for p in pairs]
            out["b"][(target, h)] = [ols_slope(*m) for m in moves_by_day]
            err = defaultdict(float)
            count = 0
            for k, p in enumerate(pairs):
                xs = [x for j, m in enumerate(moves_by_day) if j != k for x in m[0]]
                dy = [y for j, m in enumerate(moves_by_day) if j != k for y in m[1]]
                b = ols_slope(xs, dy)
                sums = defaultdict(lambda: [0.0, 0])
                for j, q in enumerate(pairs):
                    if j != k:
                        for r, future in q:
                            cell = sums[(rho_bucket(r["rho"]), spread_bucket(r["spread"]))]
                            cell[0] += future - r["wall_mid"]
                            cell[1] += 1
                table = {key: total / n for key, (total, n) in sums.items()}
                for r, future in p:
                    g = table.get((rho_bucket(r["rho"]), spread_bucket(r["spread"])), 0.0)
                    err[TABLE] += (r["wall_mid"] + g - future) ** 2
                    for name in ("mid", "wall_mid", "sized_mid", "weighted"):
                        err[name] += (r[name] - future) ** 2
                    err["wall_mid + b·ρ"] += (r["wall_mid"] + b * r["rho"] - future) ** 2
                count += len(p)
            out["rmse"][(target, h)] = {name: math.sqrt(e / count) for name, e in err.items()}
    return out


def main() -> None:
    results = {}
    for alias, rnd, products in DATASETS:
        days = prosperity.load_days(prosperity.resolve_data_dir(alias), [rnd])
        for product in products:
            results[(alias, rnd, product)] = study(days, product)

    print("1. Gould & Bonart: the direction of the next mid change from ρ one tick before, leaving one day out.\n")
    print("| Data | Product | Mid changes | ROC area | Squared error vs a coin flip | x1 per day | ROC area by spread (ticks: n, area) |")
    print("|---|---|---|---|---|---|---|")
    for (alias, rnd, product), o in results.items():
        slopes = ", ".join(f"{s:+.2f}" for s in o["slopes"])
        spreads = "; ".join(f"{k}: {n:,}, {a:.2f}" for k, (n, a) in sorted(o["by_spread"].items()))
        print(f"| {alias} r{rnd} | {product} | {o['n']:,} | {o['auc']:.3f} | {o['brier'] * 100:+.1f}% | {slopes} | {spreads} |")

    for target in ("wall_mid", "mid"):
        print(f"\n2. Root mean squared error of each candidate against the {target} H ticks later (pooled over the days; "
              "b fitted leaving one day out).\n")
        names = ["mid", "wall_mid", "sized_mid", "weighted", "wall_mid + b·ρ", TABLE]
        print("| Data | Product | H | " + " | ".join(names) + " |")
        print("|---|---|---|" + "---|" * len(names))
        for (alias, rnd, product), o in results.items():
            for h in HORIZONS:
                r = o["rmse"][(target, h)]
                best = min(r.values())
                cells = [f"**{r[n]:.3f}**" if r[n] == best else f"{r[n]:.3f}" for n in names]
                print(f"| {alias} r{rnd} | {product} | {h} | " + " | ".join(cells) + " |")

    print("\n3. The fitted b (ticks of wall-mid move per unit of ρ) on each day alone, target the wall mid.\n")
    print("| Data | Product | " + " | ".join(f"H={h}" for h in HORIZONS) + " |")
    print("|---|---|" + "---|" * len(HORIZONS))
    for (alias, rnd, product), o in results.items():
        cells = [", ".join(f"{b:+.2f}" for b in o["b"][("wall_mid", h)]) for h in HORIZONS]
        print(f"| {alias} r{rnd} | {product} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
