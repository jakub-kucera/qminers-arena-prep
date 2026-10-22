"""Why the zoo's market makers beat the template head to head, per product.

usage (from the repo root): uv run python -m experiments.zoo_h2h [--jobs N] [--engine rust]

Three versions of the template (VARIANTS: as committed, with Squid Ink traded, and tuned for
`worse` fills), each on P3 round 1 (all three days) under --match-trades all and worse:
  - alone, PnL per product;
  - in one market with each zoo bot (`--vs`, per tick), PnL per product for both, and per product
    where each one's fills came from: the book (takes) or market trades (its quotes), with the
    mean edge against the wall mid;
  - inside arena.sim's market (its presets, seeds 0-4), alone.
Results go into IDEAS.md ("Why the zoo beat the template head to head").
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust, sim
from arena.cli import add_engine_argument, backtest, backtest_days
from arena.engine import EngineConfig, TradeMatching
from arena.formats import prosperity
from experiments.zoo import TEMPLATE, label, zoo_bots

SQUID_INK = {"limit": 50, "fair": "wall_mid", "make_edge": 1, "stop_loss": 18_000}
VARIANTS = {
    "committed": {},
    "+squid": {"PARAMS.SQUID_INK": SQUID_INK},
    "worse-tuned": {"PARAMS.KELP.make_edge": 0.5, "PARAMS.SQUID_INK": {**SQUID_INK, "make_edge": 0.5}},
}
MODES = (TradeMatching.ALL, TradeMatching.WORSE)
SEEDS = range(5)
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def per_product(result) -> dict[str, dict[str, float]]:
    """PnL, and volume and summed edge against the wall mid by fill source."""
    wall = {(ts, p): result.wall_mids[p][k] for p in result.products for k, ts in enumerate(result.timestamps)}
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for product, series in result.pnl.items():
        out[product]["pnl"] += series[-1] if series else 0.0
    for fill in result.fills:
        w = wall.get((fill.timestamp, fill.product))
        if w is not None:
            out[fill.product][f"vol_{fill.source}"] += abs(fill.quantity)
            out[fill.product][f"edge_{fill.source}"] += (w - fill.price) * fill.quantity
    return out


def add(total: dict, part: dict) -> None:
    for product, values in part.items():
        for key, value in values.items():
            total.setdefault(product, defaultdict(float))[key] += value


def run(task: tuple[str, str | None, str]) -> tuple[tuple[str, str | None, str], list[dict]]:
    """(variant, zoo bot or None for alone, mode) -> per-product stats for the template [and the bot]."""
    variant, rival, mode = task
    days = backtest_days("p3", ["1"], ENGINE[0])
    totals: list[dict] = [{}, {}] if rival else [{}]
    for day in days:
        bots = [("template", TEMPLATE, VARIANTS[variant], False)] + ([("rival", Path(rival), {}, False)] if rival else [])
        results = backtest(day, bots, EngineConfig(trade_matching=TradeMatching(mode)), ENGINE[0], fields=("pnl", "fills", "wall_mids"))
        for total, result in zip(totals, results):
            add(total, per_product(result))
    return task, totals


def in_sim(variant: str) -> tuple[str, dict[str, float]]:
    spec = sim.preset_market()
    pnl: dict[str, float] = defaultdict(float)
    if ENGINE[0] == "rust":
        for row in rust.run_sim(spec, SEEDS[0], len(SEEDS), [("template", TEMPLATE, VARIANTS[variant], False)]):
            for product, value in row["bots"]["template"]["products"].items():
                pnl[product] += value
        return variant, pnl
    for seed in SEEDS:
        bot = prosperity.load_bot(TEMPLATE, VARIANTS[variant], strict=False)
        for product, series in sim.run(spec, seed, [("template", bot)]).results[0].pnl.items():
            pnl[product] += series[-1] if series else 0.0
    return variant, pnl


def k(x: float) -> str:
    return f"{x / 1000:.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.zoo_h2h")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.require(args.allow_stale)
    rivals = [str(p) for p in zoo_bots()]
    tasks = [(v, r, m.value) for v in VARIANTS for r in [None, *rivals] for m in MODES]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        results = dict(pool.map(run, tasks))
        sims = dict(pool.map(in_sim, VARIANTS))
    products = sorted({p for stats in results.values() for s in stats for p in s})

    print("P3 round 1, all three days, PnL in thousands. Variants:")
    for name, overrides in VARIANTS.items():
        print(f"  {name}: {overrides or 'python/bots/template.py as is'}")
    print("\nThe template alone (and inside arena.sim, seeds 0-4):\n")
    print("| Variant | " + " | ".join(f"{m.value}: " + " / ".join(products) for m in MODES) + " | sim: " + " / ".join(products) + " |")
    print("|---|---|---|---|")
    for v in VARIANTS:
        cells = [" / ".join(k(results[(v, None, m.value)][0].get(p, {}).get("pnl", 0)) for p in products) for m in MODES]
        print(f"| {v} | " + " | ".join(cells) + " | " + " / ".join(k(sims[v].get(p, 0)) for p in products) + " |")

    print("\nHead to head, template / zoo bot, total and per product (" + ", ".join(products) + "):\n")
    print("| Zoo bot | Variant | " + " | ".join(m.value for m in MODES) + " |")
    print("|---|---|---|---|")
    for r in rivals:
        for v in VARIANTS:
            cells = []
            for m in MODES:
                mine, theirs = results[(v, r, m.value)]
                total = f"**{k(sum(s['pnl'] for s in mine.values()))} / {k(sum(s['pnl'] for s in theirs.values()))}**"
                split = ", ".join(f"{k(mine.get(p, {}).get('pnl', 0))} / {k(theirs.get(p, {}).get('pnl', 0))}" for p in products)
                cells.append(f"{total} ({split})")
            print(f"| {label(Path(r))} | {v} | " + " | ".join(cells) + " |")

    print("\nWhere the fills came from, committed template against each zoo bot, under all (volume @ mean edge to the wall mid):")
    for r in rivals:
        mine, theirs = results[("committed", r, "all")]
        for who, stats in (("template", mine), (label(Path(r)), theirs)):
            for p in products:
                s = stats.get(p)
                if not s or not (s.get("vol_book") or s.get("vol_trade")):
                    continue
                parts = [f"{src} {s[f'vol_{src}']:,.0f} @ {s[f'edge_{src}'] / s[f'vol_{src}']:+.2f}" for src in ("book", "trade") if s.get(f"vol_{src}")]
                print(f"  vs {label(Path(r)):32} {who:32} {p:18} " + "  ".join(parts))


if __name__ == "__main__":
    main()
