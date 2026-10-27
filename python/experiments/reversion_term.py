"""Is a one-tick reversion term in the fair more than `smoothing`? Linear Utility's and DTU's term, checked.

usage (from the repo root): uv run python -m experiments.reversion_term

Linear Utility's Starfruit fair is the market maker's mid plus −0.229 times its last return
(`references/prosperity2-linear-utility/round1/round_1_v6.py:183-191`), and DTU's round 5 fair the mid
less 0.14–0.15 times its last change on two Oxygen Shakes (`references/prosperity4-dtu-quant-lab/round_5/algorithmic/trader.py:500-506`,
`:594-598`). Both are a forecast w_t + β (w_t − w_{t−1}), here of the wall mid h ticks ahead, in ticks,
with β fitted on the other days (leave one day out), against the plain w_t and an EMA of w (the
template's `smoothing`: s = α s + (1 − α) w), the best α of EMAS, by RMSE over every tick.

Results: IDEAS.md, "A one-tick reversion term in the fair".
"""

from __future__ import annotations

import math
import statistics

from arena.formats import FORMATS
from arena.model import Day
from experiments.structure import carried, scale, wall_mids

DATASETS = [  # (data alias, round, products)
    ("p2", "1", ["STARFRUIT"]),
    ("p3", "1", ["KELP", "SQUID_INK"]),
    ("p4", "1", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
    ("p4", "5", ["OXYGEN_SHAKE_EVENING_BREATH", "OXYGEN_SHAKE_CHOCOLATE"]),
]
HORIZONS = (1, 5, 20)
EMAS = (0.25, 0.5, 0.8, 0.9)


def walls(day: Day, product: str) -> list[float]:
    """The wall mid in ticks, carried over ticks without a two-sided book."""
    tick, _ = scale(day, product)
    return [p / tick for p in carried(wall_mids(day, product))]


def rmse(errors: list[float]) -> float:
    return math.sqrt(statistics.fmean(e * e for e in errors))


def beta(w: list[float], h: int) -> float:
    """The slope of w's next h ticks' change on its last one-tick change."""
    x = [w[t] - w[t - 1] for t in range(1, len(w) - h)]
    y = [w[t + h] - w[t] for t in range(1, len(w) - h)]
    vx = statistics.pvariance(x)
    return statistics.covariance(x, y) / vx if vx else 0.0


def forecasts(ws: list[list[float]], h: int) -> dict:
    """The errors of the three forecasts of w h ticks ahead over every day, β from the other days."""
    betas = [beta(w, h) for w in ws]
    out = {"plain": [], "beta": [], "folds": [], "ema": {a: [] for a in EMAS}}
    for i, w in enumerate(ws):
        b = statistics.fmean(betas[:i] + betas[i + 1:]) if len(ws) > 1 else betas[0]
        out["folds"].append(b)
        for t in range(1, len(w) - h):
            y = w[t + h] - w[t]
            out["plain"].append(y)
            out["beta"].append(y - b * (w[t] - w[t - 1]))
        for a in EMAS:
            s = w[0]
            for t in range(1, len(w) - h):
                s = a * s + (1 - a) * w[t]
                out["ema"][a].append(w[t + h] - s)
    return out


def main() -> None:
    print("The wall mid h ticks ahead, in ticks: RMSE of the plain wall mid, with the reversion term (β fitted leaving one day out), "
          "and the best EMA\n")
    print("| data | product | h | β (mean of the folds) | RMSE: plain | with β | gain | best EMA (α) | gain |")
    print("|---|---|---|---|---|---|---|---|---|")
    for alias, spec, products in DATASETS:
        fmt = FORMATS["prosperity"]
        days = fmt.load_days(fmt.resolve_data_dir(alias), [spec])
        for p in products:
            ws = [walls(day, p) for day in days]
            for h in HORIZONS:
                r = forecasts(ws, h)
                r0, r1 = rmse(r["plain"]), rmse(r["beta"])
                best = min(EMAS, key=lambda a: rmse(r["ema"][a]))
                r2 = rmse(r["ema"][best])
                print(f"| {alias} r{spec} | {p} | {h} | {statistics.fmean(r['folds']):+.3f} | {r0:.3f} | {r1:.3f} | {(r0 - r1) / r0:+.1%} | "
                      f"{r2:.3f} ({best}) | {(r0 - r2) / r0:+.1%} |")


if __name__ == "__main__":
    main()
