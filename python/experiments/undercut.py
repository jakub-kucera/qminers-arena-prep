"""What a rival that undercuts us costs the template, and whether undercutting back wins it back.

usage (from the repo root): uv run python -m experiments.undercut [--jobs N] [--engine rust]
       uv run python -m experiments.undercut --data DIR --days 1 2 [--format F --bot FILE --products A,B] [--war PRODUCT]

Wang et al. (references/wiki/sources/marl-competition-no-collusion.md): a market maker trained to
cut its rival's PnL quoted tighter and took 84% of the flow. The simplest such rival is a copy of
the template that quotes up to the fair value itself (`make_edge` 0 on every product it trades),
so it always sits at or inside our quote.

For each dataset (the template's tuned products), engine mode (per tick under --match-trades all
and worse, and --resting, where each bot sees the other's resting quotes and pennies them), our
variant (OURS) and rival (RIVALS): our PnL, the rival's, and each side's passive fill volume
(market trades and crossed resting orders, not takes), so our share of the passive flow.
Then, for Resin (a fair known exactly), --resting: ours at each `make_edge` in EDGES against a
rival at each, the payoff matrix of the price war.
Results go into IDEAS.md ("Against a rival that undercuts us").

With --data (the day's download) the one dataset replaces DATASETS, and the price-war table is
for the product --war names (a fair known exactly, Resin-like), or skipped.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, backtest_days, dataset_from
from arena.engine import EngineConfig, TradeMatching

TEMPLATE = "python/bots/template.py"
DATASETS = {  # name: (data, days, the products the template trades there)
    "P3 r1": ("p3", ["1"], ["KELP", "RAINFOREST_RESIN"]),
    "P4 r1-2": ("p4", ["1", "2"], ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
}
MODES = {
    "all": EngineConfig(),
    "worse": EngineConfig(trade_matching=TradeMatching.WORSE),
    "resting": EngineConfig(resting=True),
}
OURS = {"committed": None, "make_edge 0": 0}  # None: PARAMS as committed; a number: make_edge on every product
RIVALS = {"alone": "none", "template copy": None, "undercutter": 0}
EDGES = (2, 1, 0)


ENGINE = ["python"]  # set in each worker by _init (--engine)
FORMAT = "prosperity"
WAR = ("p3", ["1"], "RAINFOREST_RESIN")  # the price war's data, days and product; --data and --war change it


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})


def _overrides(products: list[str], edge: int | None) -> dict:
    return {} if edge is None else {f"PARAMS.{p}.make_edge": edge for p in products}


def _passive(result, product: str) -> int:
    return sum(abs(f.quantity) for f in result.fills if f.product == product and f.source in ("trade", "cross"))


def run(task: tuple[str, str, str, str]) -> tuple[tuple, dict]:
    dataset, mode, ours, rival = task
    data, days, products = DATASETS[dataset]
    out = {p: {"pnl": 0.0, "rival": 0.0, "passive": 0, "rival passive": 0, "days": []} for p in products}
    for day in backtest_days(data, days, ENGINE[0], FORMAT):
        bots = [("template", TEMPLATE, _overrides(products, OURS[ours]), False)]
        if RIVALS[rival] != "none":
            bots.append(("rival", TEMPLATE, _overrides(products, RIVALS[rival]), False))
        results = backtest(day, bots, MODES[mode], ENGINE[0], fields=("pnl", "fills"), format_name=FORMAT)
        for p in products:
            o = out[p]
            pnl = results[0].pnl[p][-1] if results[0].pnl.get(p) else 0.0
            o["pnl"] += pnl
            o["days"].append(pnl)
            o["passive"] += _passive(results[0], p)
            if len(results) > 1:
                o["rival"] += results[1].pnl[p][-1] if results[1].pnl.get(p) else 0.0
                o["rival passive"] += _passive(results[1], p)
    return task, out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.undercut")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser)
    parser.add_argument("--war", metavar="PRODUCT", help="with --data: the product of the price-war table (default: none)")
    args = parser.parse_args()
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    settings = {}
    if dataset:
        settings = {"DATASETS": {dataset.name: (dataset.data, list(dataset.days), list(dataset.products))}, "TEMPLATE": dataset.bot,
                    "FORMAT": dataset.format, "WAR": (dataset.data, list(dataset.days), args.war) if args.war else None}
    globals().update(settings)
    tasks = [(d, m, o, r) for d in DATASETS for m in MODES for o in OURS for r in RIVALS]
    pairs = [(o, r) for o in EDGES for r in (None, *EDGES)] if WAR else []
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        results = dict(pool.map(run, tasks))
        resin = dict(pool.map(resin_war, pairs))
    print("PnL in thousands over the dataset's days, per product; 'share' is our share of the two bots' passive fill")
    print("volume (their fills against each other included).\n")
    print("| Product | Mode | Ours | Rival | Ours: PnL (worst day) | Change from committed alone | Rival PnL | Passive units: ours / rival (share) |")
    print("|---|---|---|---|---|---|---|---|")
    for d, (_, _, products) in DATASETS.items():
        for p in products:
            for m in MODES:
                base = results[(d, m, "committed", "alone")][p]["pnl"]
                for o in OURS:
                    for r in RIVALS:
                        print(_row(p, m, o, r, results[(d, m, o, r)][p], base))
    if not WAR:
        return
    where = "P3 round 1" if not dataset else dataset.name
    print(f"\n{WAR[2]}, {where}, --resting: ours / the rival's PnL in thousands, by each one's make_edge.\n")
    print("| Ours \\ rival | alone | " + " | ".join(str(e) for e in EDGES) + " |")
    print("|---|---|" + "---|" * len(EDGES))
    for o in EDGES:
        cells = [f"{resin[(o, None)][0] / 1000:.1f}"] + [f"{resin[(o, r)][0] / 1000:.1f} / {resin[(o, r)][1] / 1000:.1f}" for r in EDGES]
        print(f"| {o} | " + " | ".join(cells) + " |")


def resin_war(pair: tuple[int, int | None]) -> tuple[tuple, tuple[float, float]]:
    ours, rival = pair
    data, days, product = WAR
    key = f"PARAMS.{product}.make_edge"
    totals = [0.0, 0.0]
    for day in backtest_days(data, days, ENGINE[0], FORMAT):
        bots = [("template", TEMPLATE, {key: ours}, False)] + ([("rival", TEMPLATE, {key: rival}, False)] if rival is not None else [])
        for k, result in enumerate(backtest(day, bots, EngineConfig(resting=True), ENGINE[0], fields=("pnl",), format_name=FORMAT)):
            totals[k] += result.pnl[product][-1]
    return pair, tuple(totals)


def _row(product: str, mode: str, ours: str, rival: str, x: dict, base: float) -> str:
    alone = RIVALS[rival] == "none"
    both = x["passive"] + x["rival passive"]
    share = f"{x['passive']:,}" if alone or not both else f"{x['passive']:,} / {x['rival passive']:,} ({x['passive'] / both:.0%})"
    return (f"| {product} | {mode} | {ours} | {rival} | {x['pnl'] / 1000:.1f} ({min(x['days']) / 1000:.1f}) | "
            f"{(x['pnl'] - base) / 1000:+.1f} | {'-' if alone else f'{x["rival"] / 1000:.1f}'} | {share} |")

if __name__ == "__main__":
    main()
