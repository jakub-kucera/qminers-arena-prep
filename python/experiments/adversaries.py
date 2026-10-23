"""What adversarial rivals cost the template: a trapper, a spoofer and a sniper (python/bots/rivals/).

usage (from the repo root): uv run python -m experiments.adversaries [--jobs N] [--engine rust]
       uv run python -m experiments.adversaries --data DIR --days 1 2 [--format F --bot FILE --products A,B]

P3 round 1, all three days, --resting (the rivals' orders are only visible to other bots when
orders rest), --match-trades all. Each template variant (VARIANTS) alone and in one market with
each rival (RIVALS: a plain copy of the template, as the cost of any competitor, then the
adversaries, some with their settings changed). For each: the template's PnL per product, the
rival's PnL, and the template's fills against the rival with their value 50 ticks later against
the recorded wall mid (positive: the template won those trades).
Results go into IDEAS.md ("Adversarial rivals") and
references/wiki/concepts/shared-market-and-adversaries.md.

With --data (the day's download), the variants are the bot as it is and every product on
`sized_mid` or `wall_mid`, and the rivals get the data's limits. The rivals are Prosperity-format
bots, so in another format only the template copy runs (their ADAPTERs would need rewriting).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, backtest_days, dataset_from
from arena.engine import EngineConfig

TEMPLATE = "python/bots/template.py"
VARIANTS = {
    "committed": {},
    "Kelp sized_mid": {"PARAMS.KELP.fair": "sized_mid"},
    "Kelp outer_mid": {"PARAMS.KELP.fair": "outer_mid"},
    "Resin no guard": {"PARAMS.RAINFOREST_RESIN.fixed_guard": None},
}
RIVALS = {
    "alone": None,
    "template copy": (TEMPLATE, {}),
    "trapper": ("python/bots/rivals/trapper.py", {}),
    "spoofer, 1 behind": ("python/bots/rivals/spoofer.py", {}),
    "spoofer, 10 behind": ("python/bots/rivals/spoofer.py", {"OFFSET": 10}),
    "sniper": ("python/bots/rivals/sniper.py", {}),
}
MARKOUT = 50
ENGINE = ["python"]  # set in each worker by _init (--engine)
DATA, DAYS, FORMAT, PRODUCTS = "p3", ["1"], "prosperity", ["KELP", "RAINFOREST_RESIN"]  # --data changes them


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})


def _settings(dataset) -> dict:
    """The module's settings for the day's data: its days, the bot, the variants and the rivals."""
    from arena.formats import FORMATS

    fmt = FORMATS[dataset.format]
    limits = {p: v for day in fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days)) for p, v in day.limits.items()}
    products = list(dataset.products)
    rivals = {"alone": None, "template copy": (dataset.bot, {})}
    if dataset.format == "prosperity":
        rivals |= {name: (path, {**overrides, "LIMITS": limits}) for name, entry in RIVALS.items() if entry and entry[0] != TEMPLATE
                   for path, overrides in [entry]}
    variants = {"committed": {}} | {f"every product {fair}": {f"PARAMS.{p}.fair": fair for p in products} for fair in ("sized_mid", "wall_mid")}
    return {"DATA": dataset.data, "DAYS": list(dataset.days), "FORMAT": dataset.format, "PRODUCTS": products, "TEMPLATE": dataset.bot,
            "VARIANTS": variants, "RIVALS": rivals}


def run(task: tuple[str, str]) -> tuple[tuple[str, str], dict]:
    variant, rival = task
    days = backtest_days(DATA, DAYS, ENGINE[0], FORMAT)
    out = {"pnl": defaultdict(float), "rival": 0.0, "vol": 0, "markout": 0.0}
    for day in days:
        bots = [("template", TEMPLATE, VARIANTS[variant], False)]
        if RIVALS[rival]:
            path, overrides = RIVALS[rival]
            bots.append(("rival", path, overrides, False))
        results = backtest(day, bots, EngineConfig(resting=True), ENGINE[0], fields=("pnl", "fills", "wall_mids"), format_name=FORMAT)
        mine = results[0]
        for product, series in mine.pnl.items():
            out["pnl"][product] += series[-1] if series else 0.0
        if len(results) > 1:
            out["rival"] += sum(s[-1] for s in results[1].pnl.values() if s)
        index = {t: k for k, t in enumerate(mine.timestamps)}
        last = len(mine.timestamps) - 1
        for fill in mine.fills:
            if fill.counterparty != "rival":
                continue
            later = mine.wall_mids[fill.product][min(index[fill.timestamp] + MARKOUT, last)]
            out["vol"] += abs(fill.quantity)
            if later is not None:
                out["markout"] += (later - fill.price) * fill.quantity
    return task, out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.adversaries")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser)
    args = parser.parse_args()
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    settings = _settings(dataset) if dataset else {}
    globals().update(settings)
    tasks = [(v, r) for v in VARIANTS for r in RIVALS]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        results = dict(pool.map(run, tasks))
    where = f"{dataset.name} ({dataset.format})" if dataset else "P3 round 1, all three days"
    print(f"{where}, --resting, all. PnL in thousands; 'vs rival' is the template's fills with the rival,")
    print(f"in units, and their value {MARKOUT} ticks later.\n")
    names = "Kelp / Resin" if not dataset else " / ".join(PRODUCTS)
    print(f"| Template | Rival | Template ({names}) | Change from alone | Rival | Template vs rival: units, value |")
    print("|---|---|---|---|---|---|")
    for v in VARIANTS:
        alone = sum(results[(v, "alone")]["pnl"].values())
        for r in RIVALS:
            o = results[(v, r)]
            total = sum(o["pnl"].values())
            split = " / ".join(f"{o['pnl'].get(product, 0) / 1000:.1f}" for product in PRODUCTS)
            rival = f"{o['rival'] / 1000:.1f}" if RIVALS[r] else "-"
            fills = f"{o['vol']:,}, {o['markout'] / 1000:+.1f}" if RIVALS[r] else "-"
            print(f"| {v} | {r} | {total / 1000:.1f} ({split}) | {(total - alone) / 1000:+.1f} | {rival} | {fills} |")


if __name__ == "__main__":
    main()
