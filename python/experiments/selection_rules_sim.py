"""The selection rules of python/experiments/selection_rules.py on simulated days, where fresh days are unlimited.

usage (from the repo root): uv run python -m experiments.selection_rules_sim [--jobs N] [--reps R] [--engine rust]

The rules were compared on eight Prosperity studies with 1-6 test days each, and the grid's pick
(SPA, then StepM, then every mode) was chosen from that table, so its record there is in-sample.
Here each product of arena.sim's presets gets a two-parameter grid, tuned on TRAIN_DAYS fresh
simulated days (seeds differ per repetition) and scored on TEST_DAYS other days, for REPS
repetitions; the days are generated from the preset alone (one product, no bot in the market) and
replayed by the engine, as the Prosperity days are. Carr and López de Prado's point
(references/wiki/sources/optimal-trading-rules.md): on a calibrated process, out-of-sample days
cost nothing.

For each product, baseline (the bot as committed, or DEFAULTS for the two parameters) and rule:
the mean gain over the baseline per test day under --match-trades all and worse, and in how many
repetitions the pick lost money under each. The presets copy P3 round 1's Kelp and Resin and P4's
Hydrogel (whose level, about 10,009 on these days, isn't the template's 9,994). Results go into
IDEAS.md ("Selection rules on unseen days").
"""

from __future__ import annotations

import argparse
import itertools
import statistics
from concurrent.futures import ProcessPoolExecutor

from arena import grid, rust, sim
from arena.cli import add_engine_argument, backtest
from arena.engine import EngineConfig, TradeMatching
from experiments.selection_rules import MODES, RULES, TEMPLATE, default_cell, pick

TRAIN_DAYS, TEST_DAYS, REPS = 3, 20, 10
PRODUCTS = {  # preset: {parameter: values}; each grid holds the committed and the DEFAULTS cell
    "KELP": {"make_edge": [0, 0.5, 1, 1.5, 2, 3], "take_edge": [0, 1, 2, 3]},
    "RAINFOREST_RESIN": {"make_edge": [1, 2, 3, 4], "take_edge": [0, 1, 2]},
    "HYDROGEL_PACK": {"level_band": [15, 20, 35, 50], "clear_edge": [0, 2, 5, 10, 15]},
}
_DAYS: dict = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def train_seeds(rep: int) -> list[int]:
    return [10_000 + 100 * rep + i for i in range(TRAIN_DAYS)]


TEST_SEEDS = [900_000 + i for i in range(TEST_DAYS)]


def day(product: str, seed: int):
    if ENGINE[0] == "rust":
        return rust.sim_day_file(sim.preset_market([product]), seed)
    if (product, seed) not in _DAYS:
        _DAYS[(product, seed)] = sim.run(sim.preset_market([product]), seed).day
    return _DAYS[(product, seed)]


def cells(product: str) -> list[dict]:
    axes = PRODUCTS[product]
    return [{f"PARAMS.{product}.{k}": v for k, v in zip(axes, values)} for values in itertools.product(*axes.values())]


def run(task: tuple[str, int, int | None]) -> tuple[tuple, dict]:
    """One cell (-1: the bot as committed) on one repetition's training days (rep), or on the test days (rep None)."""
    product, k, rep = task
    overrides = {} if k < 0 else cells(product)[k]
    seeds = TEST_SEEDS if rep is None else train_seeds(rep)
    out = {m: [] for m in MODES} | {"fine": [], "coarse": []}
    for seed in seeds:
        d = day(product, seed)
        for mode in MODES:
            (result,) = backtest(d, [("you", TEMPLATE, overrides, False)], EngineConfig(trade_matching=mode), ENGINE[0], fields=("pnl",))
            series = result.pnl.get(product) or [0.0] * len(result.timestamps)
            out[mode].append(series[-1])
            if rep is not None and mode is TradeMatching.ALL:
                out["fine"] += grid.block_pnl(series, len(series) // grid.FINE_TICKS)
                out["coarse"] += grid.block_pnl(series, grid.blocks_per_day(len(seeds)))
    return task, out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.selection_rules_sim")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    parser.add_argument("--reps", type=int, default=REPS, help=f"repetitions with fresh training days (default: {REPS})")
    add_engine_argument(parser, "run the days and backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.require(args.allow_stale)
    tasks = [(p, k, rep) for p in PRODUCTS for k in range(-1, len(cells(p))) for rep in [None, *range(args.reps)]]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        done = dict(pool.map(run, tasks, chunksize=1))

    print(f"Each grid tuned on {TRAIN_DAYS} simulated days, {args.reps} times with fresh seeds, and scored on the same {TEST_DAYS} other days.")
    print("Per cell: the mean gain over the baseline per test day, all / worse, then how many repetitions lost money under all / worse.\n")
    for baseline in ("committed", "defaults"):
        print(f"Baseline: the bot {'as committed' if baseline == 'committed' else 'with DEFAULTS for the two parameters'}.\n")
        print("| Product | " + " | ".join(RULES) + " | oracle |")
        print("|---" * (len(RULES) + 2) + "|")
        totals = {r: {m: 0.0 for m in MODES} for r in RULES}
        lost = {r: {m: 0 for m in MODES} for r in RULES}
        for product, axes in PRODUCTS.items():
            n = len(cells(product))
            row = {r: {m: [] for m in MODES} for r in RULES}
            oracle = []
            for rep in range(args.reps):
                results = [{"train": {m: done[(product, k, rep)][m] for m in MODES}, "test": {m: done[(product, k, None)][m] for m in MODES},
                            "fine": done[(product, k, rep)]["fine"], "coarse": done[(product, k, rep)]["coarse"]} for k in range(n)]
                if baseline == "committed":
                    b = done[(product, -1, rep)]
                    base = {"train": {m: b[m] for m in MODES}, "test": {m: done[(product, -1, None)][m] for m in MODES}, "fine": b["fine"], "coarse": b["coarse"]}
                else:
                    base = results[default_cell(axes)]
                picks = pick(axes, base, results)
                for rule in RULES:
                    k = picks[rule]
                    for m in MODES:
                        gain = 0.0 if k is None else (sum(results[k]["test"][m]) - sum(base["test"][m])) / TEST_DAYS
                        row[rule][m].append(gain)
                oracle.append(max(sum(r["test"][MODES[0]]) for r in results) / TEST_DAYS - sum(base["test"][MODES[0]]) / TEST_DAYS)
            cells_text = []
            for rule in RULES:
                means = {m: statistics.fmean(row[rule][m]) for m in MODES}
                losses = {m: sum(g < -1e-9 for g in row[rule][m]) for m in MODES}
                for m in MODES:
                    totals[rule][m] += means[m]
                    lost[rule][m] += losses[m]
                cells_text.append(f"{means[MODES[0]]:+,.0f} / {means[MODES[1]]:+,.0f} (lost {losses[MODES[0]]} / {losses[MODES[1]]})")
            print(f"| {product}: {', '.join(axes)} | " + " | ".join(cells_text) + f" | {statistics.fmean(oracle):+,.0f} |")
        print("| **Total** | " + " | ".join(f"**{totals[r][MODES[0]]:+,.0f} / {totals[r][MODES[1]]:+,.0f} (lost {lost[r][MODES[0]]} / {lost[r][MODES[1]]})**"
                                           for r in RULES) + " | |\n")


if __name__ == "__main__":
    main()
