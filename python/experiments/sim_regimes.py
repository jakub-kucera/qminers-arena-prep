"""The template inside arena.sim when the regime changes mid-day: do its stops and guards hold?

usage (from the repo root): uv run python -m experiments.sim_regimes [--days 10] [--jobs N] [--engine rust]

The market is the Kelp, Resin and Hydrogel presets (the template's PARAMS trade all three as they
are), for seeds 0 to days-1, plain and under each `arena.sim` regime (`with_regime`: from mid-day
a shift of 5 wall spreads, or a trend of 10 over the afternoon). The template runs inside the
market, so the maker re-centres and the value takers trade toward the new value, unlike
`arena.stress`'s moved recordings. The variants:

  committed    PARAMS as committed: stop_loss on every product, fixed_guard on Resin
  unprotected  the same without stop_loss and fixed_guard
  resting      as committed, with orders that rest (--resting)
  cpd 10k      as committed, with changepoint detection on Hydrogel's level (cpd_hazard 10,000;
               cpd_reversion and cpd_sd are the preset's, as the download's would be on the day)
  cpd 3k       the same with cpd_hazard 3,000
  drop 0.5     cpd_hazard 10,000, cpd_action "drop": keep the level, and drop the bet for the day once
               the chance that the level moved passes 0.5 (drop 0.9: 0.9)
  stop 20k     as committed, with Hydrogel's stop_loss at 20,000 instead of 48,000 (stop 10k: 10,000)

Printed per regime and product: PnL summed over the days (thousands), the worst day, and on how
many days the loss stop fired.
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust, sim
from arena.engine import EngineConfig
from arena.formats import prosperity

TEMPLATE = Path("python/bots/template.py")
PRODUCTS = ["KELP", "RAINFOREST_RESIN", "HYDROGEL_PACK"]
REGIMES = ["plain", *sim.REGIMES]
UNPROTECTED = {
    "PARAMS.KELP.stop_loss": None,
    "PARAMS.RAINFOREST_RESIN.stop_loss": None,
    "PARAMS.RAINFOREST_RESIN.fixed_guard": None,
    "PARAMS.HYDROGEL_PACK.stop_loss": None,
}
HYDROGEL = sim.PRESETS["HYDROGEL_PACK"].fundamental
CPD = {"PARAMS.HYDROGEL_PACK.cpd_reversion": HYDROGEL.reversion, "PARAMS.HYDROGEL_PACK.cpd_sd": HYDROGEL.sd}
VARIANTS = {
    "committed": ({}, False),
    "unprotected": (UNPROTECTED, False),
    "resting": ({}, True),
    "cpd 10k": ({**CPD, "PARAMS.HYDROGEL_PACK.cpd_hazard": 10_000}, False),
    "cpd 3k": ({**CPD, "PARAMS.HYDROGEL_PACK.cpd_hazard": 3_000}, False),
    "drop 0.5": ({**CPD, "PARAMS.HYDROGEL_PACK.cpd_hazard": 10_000, "PARAMS.HYDROGEL_PACK.cpd_action": "drop"}, False),
    "drop 0.9": ({**CPD, "PARAMS.HYDROGEL_PACK.cpd_hazard": 10_000, "PARAMS.HYDROGEL_PACK.cpd_action": "drop", "PARAMS.HYDROGEL_PACK.cpd_threshold": 0.9}, False),
    "stop 20k": ({"PARAMS.HYDROGEL_PACK.stop_loss": 20_000}, False),
    "stop 10k": ({"PARAMS.HYDROGEL_PACK.stop_loss": 10_000}, False),
}


ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def _run(job):
    regime, variant, seed = job
    overrides, resting = VARIANTS[variant]
    spec = sim.preset_market(PRODUCTS)
    if regime != "plain":
        spec = sim.with_regime(spec, regime)
    if ENGINE[0] == "rust":
        (row,) = rust.run_sim(spec, seed, 1, [("template", TEMPLATE, dict(overrides), False)], EngineConfig(resting=resting))
        totals = row["bots"]["template"]
        return job, {p: (totals["products"][p], bool(totals["memory"].get(p, {}).get("stopped"))) for p in PRODUCTS}, totals["errors"]
    bot = prosperity.load_bot(TEMPLATE, dict(overrides), strict=True)
    result = sim.run(spec, seed, [("template", bot)], resting=resting).results[0]
    memory = json.loads(bot._trader_data or "{}")
    return job, {p: (result.pnl[p][-1], bool(memory.get(p, {}).get("stopped"))) for p in PRODUCTS}, len(result.errors)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args(argv)
    if args.engine == "rust":
        rust.build()
    jobs = [(r, v, s) for r in REGIMES for v in VARIANTS for s in range(args.days)]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        results = list(pool.map(_run, jobs))
    errors = sum(e for _, _, e in results)
    table = defaultdict(lambda: defaultdict(list))  # (regime, variant) -> product -> [(pnl, stopped)]
    for (regime, variant, _), row, _ in results:
        for product, value in row.items():
            table[(regime, variant)][product].append(value)
    print(f"{args.days} days a cell (seeds 0-{args.days - 1}); PnL in thousands summed over them / worst day / days the stop fired"
          + (f"; ! {errors} bot errors" if errors else ""))
    print(f"{'':<12}{'':<13}" + "".join(f"{p:>30}" for p in PRODUCTS) + f"{'total':>10}")
    for regime in REGIMES:
        for variant in VARIANTS:
            cells, total = [], 0.0
            for product in PRODUCTS:
                values = table[(regime, variant)][product]
                pnl = sum(v for v, _ in values)
                total += pnl
                cells.append(f"{pnl / 1000:>10.1f} {min(v for v, _ in values) / 1000:>8.1f} {sum(s for _, s in values):>5}")
            print(f"{regime:<12}{variant:<13}" + "".join(f"{c:>30}" for c in cells) + f"{total / 1000:>10.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
