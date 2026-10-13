"""How much of the teams' P4 round 3-4 PnL survives without their hard-coded price levels?

usage (from the repo root): uv run python -m experiments.p4_levels [--jobs N]

Baguette Fromage (`Strategies/Phase2_Options.py`) and DU (`round4.py`) trade Hydrogel and
Velvetfruit (and DU every active voucher with it) toward a level typed into the code: Hydrogel
10,000 / 9,990, Velvetfruit 5,250. Each run replaces those constants before every tick, without
editing the teams' files, with:

  published   the constants as published
  +10 / -10   the constants moved by 10 (both products)
  other days  the mean wall mid of the other three distinct days (leave one day out)
  intraday    the mean wall mid of the day so far, from the open: no history at all

DTU's round 4 trader, which estimates its own anchors (a rolling median for Hydrogel, a clamped
EMA for Velvetfruit), runs as published for comparison.

Days: the four distinct days of rounds 3-4 (round 4 days 1 and 2 repeat round 3's), default engine
mode. For the published runs it also splits each product group's PnL against the wall mid: spread
captured by fills that took the book and by passive fills, carry (position times the wall mid's
move), and for the vouchers, the part of the carry that is just delta times Velvetfruit's move.
"""

import argparse
import statistics as st
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena.engine import EngineConfig, run_day
from arena.formats import FORMATS
from experiments.p4_vouchers import DAYS, UNDERLYING, bs_delta, day_vols, years_left

FMT = FORMATS["prosperity"]
HYDROGEL = "HYDROGEL_PACK"
R = Path("references")
TEAMS = {
    "Baguette": R / "prosperity4-baguette-fromage/Strategies/Phase2_Options.py",
    "DU": R / "prosperity4-du-trading/round4.py",
    "DTU": R / "prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py",
}
VARIANTS = ["published", "+10", "-10", "other days", "intraday"]
GROUPS = {  # product -> group printed
    HYDROGEL: "Hydrogel",
    UNDERLYING: "Velvetfruit",
    **{f"VEV_{k}": "VEV 4000-4500" for k in (4000, 4500)},
    **{f"VEV_{k}": "VEV 5000-5500" for k in (5000, 5100, 5200, 5300, 5400, 5500)},
    **{f"VEV_{k}": "VEV 6000-6500" for k in (6000, 6500)},
}
GROUP_ORDER = ["Hydrogel", "Velvetfruit", "VEV 4000-4500", "VEV 5000-5500", "VEV 6000-6500"]


def _set_baguette(trader, levels):
    trader.GEL_MEAN, trader.FRUIT_MEAN = levels[HYDROGEL], levels[UNDERLYING]


def _set_du(trader, levels):
    g = type(trader).run.__globals__
    g["HYDROGEL_MEAN"], g["VEV_MEAN"] = levels[HYDROGEL], levels[UNDERLYING]


PUBLISHED = {
    "Baguette": ({HYDROGEL: 10_000.0, UNDERLYING: 5_250.0}, _set_baguette),
    "DU": ({HYDROGEL: 9_990.0, UNDERLYING: 5_250.0}, _set_du),
}


class Levelled:
    """Sets the team's level constants before each tick, from `estimate(tick)`."""

    def __init__(self, bot, setter, estimate):
        self.bot, self.setter, self.estimate = bot, setter, estimate

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        self.setter(self.bot._trader, self.estimate(tick))
        return self.bot.step(tick, positions, own_fills, market_trades, open_orders)


class DaySoFar:
    """The mean wall mid of each product from the open to this tick."""

    def __init__(self, fallback):
        self.sums, self.counts, self.fallback = defaultdict(float), defaultdict(int), fallback

    def __call__(self, tick):
        out = {}
        for product, fallback in self.fallback.items():
            book = tick.books.get(product)
            if book is not None and book.wall_mid is not None:
                self.sums[product] += book.wall_mid
                self.counts[product] += 1
            out[product] = self.sums[product] / self.counts[product] if self.counts[product] else fallback
        return out


def day_means(days) -> dict[str, dict[str, float]]:
    out = {}
    for day in days:
        out[day.name] = {
            p: st.mean(t.books[p].wall_mid for t in day.ticks if p in t.books and t.books[p].wall_mid is not None)
            for p in (HYDROGEL, UNDERLYING)
        }
    return out


def _run(job):
    team, variant, spec = job
    days = FMT.load_days(FMT.resolve_data_dir("p4"), DAYS)
    day = next(d for d in days if d.name == _name(spec))
    bot = FMT.load_bot(TEAMS[team], {}, True)
    if team in PUBLISHED and variant != "published":
        levels, setter = PUBLISHED[team]
        if variant in ("+10", "-10"):
            shift = float(variant)
            fixed = {p: v + shift for p, v in levels.items()}
            bot = Levelled(bot, setter, lambda tick, fixed=fixed: fixed)
        elif variant == "other days":
            means = day_means(days)
            others = [m for name, m in means.items() if name != day.name]
            fixed = {p: st.mean(m[p] for m in others) for p in levels}
            bot = Levelled(bot, setter, lambda tick, fixed=fixed: fixed)
        elif variant == "intraday":
            bot = Levelled(bot, setter, DaySoFar(levels))
    result = run_day(day, bot, EngineConfig())
    return job, summarise(day, result, split=variant == "published")


def _name(spec):
    rnd, d = spec.split("-")
    return f"r{rnd}d{d}"


def summarise(day, result, split):
    pnl = defaultdict(float)
    for product, series in result.pnl.items():
        if series:
            pnl[GROUPS.get(product, product)] += series[-1]
    out = {"pnl": dict(pnl), "errors": len(result.errors), "breaches": len(result.limit_breaches)}
    if split:
        out["split"] = split_pnl(day, result)
        for group, parts in out["split"].items():
            parts["sum"] = parts.get("takes", 0.0) + parts.get("passive", 0.0) + parts["carry"] + parts["end mark"]
            assert abs(parts["sum"] - pnl[group]) < 1e-6 * max(1.0, abs(pnl[group])) + 1e-6, (group, parts, pnl[group])
    return out


def split_pnl(day, result):
    """Per group: takes, passive, carry (and its delta part for vouchers), end mark. Sums to the PnL."""
    vols = day_vols(day)
    walls = {p: _filled(result.wall_mids[p]) for p in result.products}
    index = {ts: i for i, ts in enumerate(result.timestamps)}
    parts = defaultdict(lambda: defaultdict(float))
    for f in result.fills:
        w = walls[f.product][index[f.timestamp]]
        kind = "takes" if f.source == "book" else "passive"
        parts[GROUPS.get(f.product, f.product)][kind] += f.quantity * (w - f.price)
    spot = walls[UNDERLYING]
    for product in result.products:
        group = GROUPS.get(product, product)
        pos, w = result.positions[product], walls[product]
        sigma = vols.get(product, {}).get("sigma")
        strike = vols.get(product, {}).get("strike")
        for i in range(1, len(w)):
            move = pos[i - 1] * (w[i] - w[i - 1])
            parts[group]["carry"] += move
            if strike is not None:
                ts = result.timestamps[i - 1]
                delta = bs_delta(spot[i - 1], strike, years_left(day.name, ts), sigma) if sigma else (1.0 if spot[i - 1] > strike else 0.0)
                parts[group]["carry: delta x spot move"] += pos[i - 1] * delta * (spot[i] - spot[i - 1])
        parts[group]["end mark"] += pos[-1] * (result.marks[product][-1] - w[-1])
    return {g: dict(v) for g, v in parts.items()}


def _filled(values):
    out, last = [], None
    for v in values:
        last = v if v is not None else last
        out.append(last)
    first = next(v for v in out if v is not None)
    return [first if v is None else v for v in out]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    args = parser.parse_args(argv)
    jobs = [(team, variant, spec) for team in TEAMS for variant in (VARIANTS if team in PUBLISHED else ["published"]) for spec in DAYS]
    with ProcessPoolExecutor(args.jobs) as pool:
        results = dict(pool.map(_run, jobs))

    days = FMT.load_days(FMT.resolve_data_dir("p4"), DAYS)
    print("Daily mean wall mid: " + "; ".join(f"{n} Hydrogel {m[HYDROGEL]:.1f} Velvetfruit {m[UNDERLYING]:.1f}" for n, m in day_means(days).items()))
    print("\nPnL in thousands per day (" + ", ".join(_name(s) for s in DAYS) + "), and the total over the four days")
    for team in TEAMS:
        for variant in VARIANTS if team in PUBLISHED else ["published"]:
            rows = [results[(team, variant, spec)] for spec in DAYS]
            totals = [sum(r["pnl"].values()) for r in rows]
            issues = sum(r["errors"] + r["breaches"] for r in rows)
            print(f"\n{team} {variant}: total {sum(totals) / 1000:,.1f}  days {' / '.join(f'{t / 1000:.1f}' for t in totals)}"
                  + (f"  errors+breaches {issues}" if issues else ""))
            for group in GROUP_ORDER:
                values = [r["pnl"].get(group, 0.0) for r in rows]
                print(f"    {group:<14} {sum(values) / 1000:>8.1f}   {' / '.join(f'{v / 1000:.1f}' for v in values)}")

    print("\nWhere the published PnL comes from, summed over the four days, in thousands (against the wall mid)")
    for team in TEAMS:
        merged = defaultdict(lambda: defaultdict(float))
        for spec in DAYS:
            for group, parts in results[(team, "published", spec)]["split"].items():
                for k, v in parts.items():
                    merged[group][k] += v
        print(f"\n{team}")
        for group in GROUP_ORDER:
            p = merged.get(group)
            if not p:
                continue
            line = f"    {group:<14} takes {p.get('takes', 0.0) / 1000:>7.1f}  passive {p.get('passive', 0.0) / 1000:>7.1f}  carry {p['carry'] / 1000:>7.1f}"
            if "carry: delta x spot move" in p:
                line += f" (delta x spot move {p['carry: delta x spot move'] / 1000:>7.1f})"
            line += f"  end mark {p['end mark'] / 1000:>6.1f}  = {p['sum'] / 1000:>7.1f}"
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
