"""Does `arena.diagnose --suggest` get near the hand-tuned PARAMS? Suggested from the first days, scored on the last.

usage (from the repo root): uv run python -m experiments.day.suggest_check [--engine rust]
       uv run python -m experiments.day.suggest_check --data DIR --days 1 [--format F --bot FILE --products A,B] [--engine rust]
       uv run python -m experiments.day.suggest_check --fresh [--engine rust]     # out of sample: data no rule was shaped on

For each product-round the template has hand-tuned PARAMS for (DATASETS: P2 round 1, P3 round 1, P4
rounds 1-4), diagnose reads every day of the round but the last, `arena.diagnose.suggest` turns its
row into a PARAMS entry, and the template runs on the last day twice: with the suggested entries
and with its own PARAMS (tuned by hand on all the round's days, the held-out one included, so the
comparison favours them). Per product, under `--match-trades all` and `worse`, and with
`--resting`. With --data the dataset's last day is held out the same way, and "hand" is the bot as
it is (on the day: last round's bot, or the plain template with only the limits).

The question is whether the notes alone, before any grid, give a bot worth starting from: near the
hand-tuned PnL, and not losing where the hand-tuned one makes money. Results: IDEAS.md, "`arena.diagnose --suggest`".

--fresh asks it out of sample, as on the day: every product of the rounds and presets no rule of
`suggest` was shaped on (FRESH: P2 rounds 3-4, P3 rounds 2-5, P4 round 5, and FRESH_SIM_DAYS new
arena.sim days of each preset), against what the template does with a product it has no PARAMS for,
DEFAULTS and the data's limit ("plain"), and against doing nothing (0). Per dataset: the PnL of each,
the products where the suggestion beats plain, and those where it loses money while plain doesn't.
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
FRESH = [("p2", "3"), ("p2", "4"), ("p3", "2"), ("p3", "3"), ("p3", "4"), ("p3", "5"), ("p4", "5")]
FRESH_SIM_DAYS = 4  # three to read, the last to score
FRESH_SIM_SEED = 7000
MODES = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE), "resting": EngineConfig(resting=True)}


def check(data: str, specs: list[str], products: list[str], fmt_name: str, bot: str, engine: str, plain: bool = False) -> list[tuple]:
    """Per product: (product, suggested entry, why, {mode: (suggested PnL, hand PnL)}) on the dataset's last day.
    With `plain` the hand side is DEFAULTS with the data's limit, as the template trades a product it has no PARAMS for."""
    fmt = FORMATS[fmt_name]
    days = fmt.load_days(fmt.resolve_data_dir(data), specs)
    train, test = days[:-1], days[-1]
    rows = diagnose.diagnose(train)
    suggested = {p: diagnose.suggest(rows[p]) for p in products if p in rows}
    params = {p: entry for p, (entry, _) in suggested.items()}
    hand = {p: {"limit": test.limits[p]} for p in products if p in test.limits} if plain else bot_params(bot, fmt_name)
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


def fresh(engine: str) -> int:
    import tempfile
    from pathlib import Path

    from arena import sim

    print("| data | products | suggested: all / worse / resting | plain (DEFAULTS + limit): all / worse / resting | "
          "suggested beats plain (all, worse, resting) | suggested loses where plain doesn't |")
    print("|---|---|---|---|---|---|")
    totals = [[0.0] * 3, [0.0] * 3]
    with tempfile.TemporaryDirectory() as scratch:
        jobs = [(data, [r], f"{data} r{r}") for data, r in FRESH]
        for name, preset in sim.PRESETS.items():
            folder = Path(scratch) / name
            for k in range(FRESH_SIM_DAYS):
                sim.write_day(sim.run(sim.preset_market([name]), FRESH_SIM_SEED + k), folder, 1, k)
            jobs.append((str(folder), ["1"], f"sim {name}"))
        for data, specs, label in jobs:
            fmt = FORMATS["prosperity"]
            products = sorted({p for d in fmt.load_days(fmt.resolve_data_dir(data), specs) for p in d.products})
            rows = check(data, specs, products, "prosperity", "python/bots/template.py", engine, plain=True)
            s = [sum(pnl[m][0] for *_, pnl in rows) for m in MODES]
            h = [sum(pnl[m][1] for *_, pnl in rows) for m in MODES]
            wins = [sum(pnl[m][0] > pnl[m][1] for *_, pnl in rows) for m in MODES]
            worse = sorted({p for p, _, _, pnl in rows for m in MODES if pnl[m][0] < 0 <= pnl[m][1]})
            for t, v in zip(totals, (s, h)):
                for k, x in enumerate(v):
                    t[k] += x
            print(f"| {label} | {len(rows)} | {' / '.join(f'{x:,.0f}' for x in s)} | {' / '.join(f'{x:,.0f}' for x in h)} | "
                  f"{', '.join(map(str, wins))} of {len(rows)} | {', '.join(worse) or '-'} |", flush=True)
    print(f"| total | | {' / '.join(f'{x:,.0f}' for x in totals[0])} | {' / '.join(f'{x:,.0f}' for x in totals[1])} | | |")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_dataset_arguments(parser)
    add_engine_argument(parser)
    parser.add_argument("--fresh", action="store_true", help="out of sample: data no rule was shaped on, against DEFAULTS with the limit")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    if args.fresh:
        return fresh(args.engine)
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
