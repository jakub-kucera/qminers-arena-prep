"""What adversarial rivals cost the template: a trapper, a spoofer and a sniper (bots/rivals/).

usage (from the repo root): uv run python -m experiments.adversaries [--jobs N] [--engine rust]

P3 round 1, all three days, --resting (the rivals' orders are only visible to other bots when
orders rest), --match-trades all. Each template variant (VARIANTS) alone and in one market with
each rival (RIVALS: a plain copy of the template, as the cost of any competitor, then the
adversaries, some with their settings changed). For each: the template's PnL per product, the
rival's PnL, and the template's fills against the rival with their value 50 ticks later against
the recorded wall mid (positive: the template won those trades).
Results go into IDEAS.md ("Adversarial rivals") and
references/wiki/concepts/shared-market-and-adversaries.md.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from arena import rust
from arena.cli import backtest, backtest_days
from arena.engine import EngineConfig

TEMPLATE = "bots/template.py"
VARIANTS = {
    "committed": {},
    "Kelp sized_mid": {"PARAMS.KELP.fair": "sized_mid"},
    "Kelp outer_mid": {"PARAMS.KELP.fair": "outer_mid"},
    "Resin no guard": {"PARAMS.RAINFOREST_RESIN.fixed_guard": None},
}
RIVALS = {
    "alone": None,
    "template copy": (TEMPLATE, {}),
    "trapper": ("bots/rivals/trapper.py", {}),
    "spoofer, 1 behind": ("bots/rivals/spoofer.py", {}),
    "spoofer, 10 behind": ("bots/rivals/spoofer.py", {"OFFSET": 10}),
    "sniper": ("bots/rivals/sniper.py", {}),
}
MARKOUT = 50
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def run(task: tuple[str, str]) -> tuple[tuple[str, str], dict]:
    variant, rival = task
    days = backtest_days("p3", ["1"], ENGINE[0])
    out = {"pnl": defaultdict(float), "rival": 0.0, "vol": 0, "markout": 0.0}
    for day in days:
        bots = [("template", TEMPLATE, VARIANTS[variant], False)]
        if RIVALS[rival]:
            path, overrides = RIVALS[rival]
            bots.append(("rival", path, overrides, False))
        results = backtest(day, bots, EngineConfig(resting=True), ENGINE[0], fields=("pnl", "fills", "wall_mids"))
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
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.build()
    tasks = [(v, r) for v in VARIANTS for r in RIVALS]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        results = dict(pool.map(run, tasks))
    print(f"P3 round 1, all three days, --resting, all. PnL in thousands; 'vs rival' is the template's fills with the rival,")
    print(f"in units, and their value {MARKOUT} ticks later.\n")
    print("| Template | Rival | Template (Kelp / Resin) | Change from alone | Rival | Template vs rival: units, value |")
    print("|---|---|---|---|---|---|")
    for v in VARIANTS:
        alone = sum(results[(v, "alone")]["pnl"].values())
        for r in RIVALS:
            o = results[(v, r)]
            total = sum(o["pnl"].values())
            split = f"{o['pnl'].get('KELP', 0) / 1000:.1f} / {o['pnl'].get('RAINFOREST_RESIN', 0) / 1000:.1f}"
            rival = f"{o['rival'] / 1000:.1f}" if RIVALS[r] else "-"
            fills = f"{o['vol']:,}, {o['markout'] / 1000:+.1f}" if RIVALS[r] else "-"
            print(f"| {v} | {r} | {total / 1000:.1f} ({split}) | {(total - alone) / 1000:+.1f} | {rival} | {fills} |")


if __name__ == "__main__":
    main()
