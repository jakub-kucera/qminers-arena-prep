"""Is each option a fixed function of its underlying? Implied volatility per strike and day.

usage (from the repo root): uv run python -m experiments.p4_vouchers [DAYS...]
    [--data p4 --underlying VELVETFRUIT_EXTRACT --prefix VEV_ --expiry r3d0=7,r3d1=6,...]

By default: P4's vouchers on the four distinct days of rounds 3-4 (round 4 days 1 and 2 repeat
round 3's), with time to expiry as the teams read the round pages: 7 days at the start of round 3
day 0, one fewer per day, so round 4 day 3 starts at 4. For other data, name the underlying, the
options' common prefix (the strike is the number at the end of each name) and the days to expiry
at the open of each day, e.g. P3's volcanic vouchers:
    3 --data p3 --underlying VOLCANIC_ROCK --prefix VOLCANIC_ROCK_VOUCHER_ --expiry r3d0=8,r3d1=7,r3d2=6
Prices are wall mids.

Per strike and day it prints the median implied volatility, how much it moves within the day, and
the residual: the voucher's wall mid minus Black-Scholes at Velvetfruit's wall mid and that day's
median volatility. A residual smaller than half the voucher's spread means the voucher is just
Velvetfruit with a fixed delta: there is no separate mispricing to trade.
"""

import argparse
import math
import statistics as st
import sys
from statistics import NormalDist

from arena.formats import FORMATS

UNDERLYING = "VELVETFRUIT_EXTRACT"
DAYS = ["3-0", "3-1", "3-2", "4-3"]
DAYS_TO_EXPIRY = {"r3d0": 7, "r3d1": 6, "r3d2": 5, "r4d1": 6, "r4d2": 5, "r4d3": 4}
_N = NormalDist()


def years_left(day_name: str, timestamp: int, expiry: dict[str, float] = DAYS_TO_EXPIRY) -> float:
    return (expiry[day_name] - timestamp / 1_000_000) / 365


def bs_call(s: float, k: float, t: float, sigma: float) -> float:
    if t <= 0 or sigma <= 0:
        return max(s - k, 0.0)
    d1 = (math.log(s / k) + 0.5 * sigma * sigma * t) / (sigma * math.sqrt(t))
    return s * _N.cdf(d1) - k * _N.cdf(d1 - sigma * math.sqrt(t))


def bs_delta(s: float, k: float, t: float, sigma: float) -> float:
    if t <= 0 or sigma <= 0:
        return 1.0 if s > k else 0.0
    return _N.cdf((math.log(s / k) + 0.5 * sigma * sigma * t) / (sigma * math.sqrt(t)))


def implied_vol(price: float, s: float, k: float, t: float) -> float | None:
    """Bisection; None when the price carries no time value to invert (at or below intrinsic)."""
    if price <= max(s - k, 0.0) + 1e-9 or price >= s:
        return None
    lo, hi = 1e-4, 5.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if bs_call(s, k, t, mid) > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def strikes(day, prefix: str = "VEV_") -> list[tuple[str, int]]:
    return sorted((p, int(p.rsplit("_", 1)[1])) for p in day.products if p.startswith(prefix))


def series(day, product):
    """Per tick: (timestamp, wall mid or None, spread or None)."""
    out = []
    for t in day.ticks:
        b = t.books.get(product)
        if b and b.bids and b.asks:
            out.append((t.timestamp, b.wall_mid, b.asks[0][0] - b.bids[0][0]))
        else:
            out.append((t.timestamp, None, None))
    return out


def day_vols(day, underlying: str = UNDERLYING, prefix: str = "VEV_", expiry: dict[str, float] = DAYS_TO_EXPIRY) -> dict[str, dict]:
    """Per strike: the median implied volatility and the statistics printed by `main`."""
    spot = series(day, underlying)
    out = {}
    for product, k in strikes(day, prefix):
        rows = series(day, product)
        vols, spreads, pairs = [], [], []
        for (ts, s, _), (_, v, spread) in zip(spot, rows):
            if s is None or v is None:
                continue
            spreads.append(spread)
            pairs.append((ts, s, v))
            iv = implied_vol(v, s, k, years_left(day.name, ts, expiry))
            if iv is not None:
                vols.append((ts, iv, s))
        row = {"strike": k, "spread": st.median(spreads), "time_value": st.mean(v - max(s - k, 0) for _, s, v in pairs),
               "share_inverted": len(vols) / len(pairs)}
        row["pinned"] = st.median(v for _, _, v in pairs) <= 1  # quoted 0 / 1 all day: the vol says nothing
        if not row["pinned"] and row["share_inverted"] >= 0.9:
            sigma = st.median(iv for _, iv, _ in vols)
            first = st.median(iv for ts, iv, _ in vols if ts < 100_000) if any(ts < 100_000 for ts, _, _ in vols) else None
            last = st.median(iv for ts, iv, _ in vols if ts >= 900_000) if any(ts >= 900_000 for ts, _, _ in vols) else None
            residuals = [v - bs_call(s, k, years_left(day.name, ts, expiry), sigma) for ts, s, v in pairs]
            row.update(
                sigma=sigma,
                iv_iqr=_iqr([iv for _, iv, _ in vols]),
                iv_first=first,
                iv_last=last,
                iv_spot_corr=_corr([iv for _, iv, _ in vols], [s for _, _, s in vols]),
                residual_sd=st.pstdev(residuals),
                residual_mean=st.mean(residuals),
                delta=st.median(bs_delta(s, k, years_left(day.name, ts, expiry), sigma) for ts, s, _ in pairs),
            )
        else:
            row.update(sigma=None, delta=st.median(1.0 if s > k else 0.0 for _, s, _ in pairs))
        out[product] = row
    return out


def _iqr(xs):
    q = st.quantiles(xs, n=4)
    return q[2] - q[0]


def _corr(xs, ys):
    try:
        return st.correlation(xs, ys)
    except st.StatisticsError:
        return float("nan")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("days", nargs="*", default=DAYS)
    parser.add_argument("--data", default="p4")
    parser.add_argument("--underlying", default=UNDERLYING)
    parser.add_argument("--prefix", default="VEV_")
    parser.add_argument("--expiry", help="days to expiry at each day's open, e.g. r3d0=8,r3d1=7 (default: P4's)")
    args = parser.parse_args(argv)
    expiry = {k: float(v) for k, v in (pair.split("=") for pair in args.expiry.split(","))} if args.expiry else DAYS_TO_EXPIRY
    fmt = FORMATS["prosperity"]
    days = fmt.load_days(fmt.resolve_data_dir(args.data), args.days)
    print("strike: spread (median), time value (mean), share of ticks with an implied vol; median vol, its IQR within the day,")
    print("first / last tenth of the day, corr(vol, spot); residual sd and mean against BS at the day's median vol; median delta;")
    print("half the spread per unit of delta, the cost of a round trip in the underlying's terms (P4 Velvetfruit's own: 2.5)")
    width = max(len(p) for day in days for p, _ in strikes(day, args.prefix))
    for day in days:
        print(f"\n{day.name} ({expiry[day.name]:g} days to expiry at the open)")
        for product, r in day_vols(day, args.underlying, args.prefix, expiry).items():
            head = f"  {product:<{width}} spread {r['spread']:>4} time value {r['time_value']:>6.1f} inverted {r['share_inverted']:>4.0%}"
            if r["sigma"] is None:
                why = "quoted 0 / 1" if r["pinned"] else "priced at intrinsic, no time value to invert"
                cost = f"  half-spread per delta {r['spread'] / 2 / r['delta']:.1f}" if r["delta"] > 0.01 else ""
                print(f"{head}  ({why}) delta {r['delta']:.2f}{cost}")
                continue
            print(
                f"{head}  vol {r['sigma']:.3f} IQR {r['iv_iqr']:.3f} first/last {_fmt(r['iv_first'])}/{_fmt(r['iv_last'])}"
                f" corr {r['iv_spot_corr']:+.2f}  residual sd {r['residual_sd']:.2f} mean {r['residual_mean']:+.2f}  delta {r['delta']:.2f}"
                f"  half-spread per delta {r['spread'] / 2 / r['delta']:.1f}"
            )
    return 0


def _fmt(x):
    return "  -  " if x is None else f"{x:.3f}"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
