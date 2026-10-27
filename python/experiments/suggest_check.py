"""Does `arena.diagnose --suggest` get near the hand-tuned PARAMS? Suggested from the first days, scored on the last.

usage (from the repo root): uv run python -m experiments.suggest_check [--engine rust]
       uv run python -m experiments.suggest_check --data DIR --days 1 [--format F --bot FILE --products A,B] [--engine rust]

For each product-round the template has hand-tuned PARAMS for (DATASETS: P2 round 1, P3 round 1, P4
rounds 1-4), diagnose reads every day of the round but the last, `arena.diagnose.suggest` turns its
row into a PARAMS entry, and the template runs on the last day twice: with the suggested entries
and with its own PARAMS (tuned by hand on all the round's days, the held-out one included, so the
comparison favours them). Per product, under `--match-trades all` and `worse`, and with
`--resting`. With --data the dataset's last day is held out the same way, and "hand" is the bot as
it is (on the day: last round's bot, or the plain template with only the limits).

The question is whether the notes alone, before any grid, give a bot worth starting from: near the
hand-tuned PnL, and not losing where the hand-tuned one makes money. Results: IDEAS.md, "`arena.diagnose --suggest`".
"""

from __future__ import annotations

import argparse
import sys

from arena import diagnose, rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, bot_params, dataset_from
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS

DATASETS = [  # (data, round, products): the rounds whose products the template's PARAMS were tuned on
    ("p2", "1", ["AMETHYSTS", "STARFRUIT"]),
    ("p3", "1", ["RAINFOREST_RESIN", "KELP"]),
    ("p4", "1", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
    ("p4", "2", ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
    ("p4", "3", ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]),
    ("p4", "4", ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]),
]
MODES = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE), "resting": EngineConfig(resting=True)}


def check(data: str, specs: list[str], products: list[str], fmt_name: str, bot: str, engine: str) -> list[tuple]:
    """Per product: (product, suggested entry, why, {mode: (suggested PnL, hand PnL)}) on the dataset's last day."""
    fmt = FORMATS[fmt_name]
    days = fmt.load_days(fmt.resolve_data_dir(data), specs)
    train, test = days[:-1], days[-1]
    rows = diagnose.diagnose(train)
    suggested = {p: diagnose.suggest(rows[p]) for p in products if p in rows}
    params = {p: entry for p, (entry, _) in suggested.items()}
    hand = bot_params(bot, fmt_name)
    if engine == "rust" and fmt_name == "prosperity":  # Rust reads the day's CSVs itself
        test = rust.named_day(data, test.name)
    pnl: dict[str, dict[str, tuple[float, float]]] = {p: {} for p in params}
    for mode, config in MODES.items():
        runs = {}
        for label, overrides in (("suggested", {"PARAMS": params}), ("hand", {"PARAMS": {p: hand[p] for p in params if p in hand}})):
            (result,) = backtest(test, [("you", bot, overrides, False)], config, engine, True, ("pnl", "errors", "breaches"), fmt_name)
            runs[label] = {p: s[-1] for p, s in result.pnl.items() if s}
        for p in params:
            pnl[p][mode] = (runs["suggested"].get(p, 0.0), runs["hand"].get(p, 0.0))
    return [(p, params[p], suggested[p][1], pnl[p]) for p in params]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_dataset_arguments(parser)
    add_engine_argument(parser)
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    if dataset is None:
        jobs = [(data, [r], products, "prosperity", "python/bots/template.py", f"{data} r{r}") for data, r, products in DATASETS]
    else:
        fmt = FORMATS[dataset.format]
        # --products, else every product in the data: the hand side is the bot as it is, which may not list them
        products = list(args.products.split(",")) if args.products else sorted(
            {p for d in fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days)) for p in d.products})
        jobs = [(dataset.data, list(dataset.days), products, dataset.format, dataset.bot, dataset.name)]
    totals = {mode: [0.0, 0.0] for mode in MODES}
    print("| data | product | suggested (from all days but the last) | why | " + " | ".join(f"{m}: suggested / hand" for m in MODES) + " |")
    print("|---|---|---|---|" + "---|" * len(MODES))
    for data, specs, products, fmt_name, bot, name in jobs:
        for product, entry, why, pnl in check(data, specs, products, fmt_name, bot, args.engine):
            cells = []
            for mode in MODES:
                s, h = pnl[mode]
                totals[mode][0] += s
                totals[mode][1] += h
                cells.append(f"{s:,.0f} / {h:,.0f}")
            shown = {k: v for k, v in entry.items() if k != "limit"}
            print(f"| {name} | {product} | `{shown}` | {'; '.join(why) or 'plain market making'} | " + " | ".join(cells) + " |", flush=True)
    print("| total | | | | " + " | ".join(f"{s:,.0f} / {h:,.0f}" for s, h in totals.values()) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
