"""Our settings against fields of rival archetypes in one market: which setting is the best reply
to each field, and which holds up across them all.

usage (from the repo root): uv run python -m experiments.rival_field [--jobs N] [--engine rust]
       uv run python -m experiments.rival_field --data DIR --days 1 2 [--products A,B] [--candidate PARAMS.P.KEY=V1,V2 ...]

P3 round 1, all three days, --match-trades all, per tick and --resting. CANDIDATES: the template
with Kelp's make_edge 0.5, 1 or 1.5 and Resin's 1 or 2 (the committed bot is Kelp 0.5, Resin 2).
ARCHETYPES: python/bots/mm.py quoting Kelp and Resin at make_edge 0.5, 1 and 2, the taker, the
sniper, the spoofer and the trapper (python/bots/rivals/), and a copy of the template as
committed. FIELDS: none, each archetype alone, and five mixes of three to six. For each mode:
  1. our PnL per candidate and field, in thousands;
  2. the best reply to each field;
  3. each candidate's worst and mean PnL over the fields with rivals: the max-min and the mean
     choice, against the best reply to a copy alone (the two-bot answer, experiments.undercut's).
Results go into IDEAS.md ("Our settings against a field of rival archetypes").

With --data (Prosperity-format data: the rivals are Prosperity bots), the archetypes trade
--products (default: every product the template trades there) with the data's limits, and each
--candidate (an axis as arena.grid takes it, repeatable) replaces the default candidates.
"""

from __future__ import annotations

import argparse
import itertools
import statistics
from concurrent.futures import ProcessPoolExecutor

from arena import grid, rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, backtest_days, dataset_from
from arena.engine import EngineConfig

TEMPLATE = "python/bots/template.py"
MM, RIVALS = "python/bots/mm.py", "python/bots/rivals"
AXES = {"PARAMS.KELP.make_edge": [0.5, 1, 1.5], "PARAMS.RAINFOREST_RESIN.make_edge": [1, 2]}
DATA, DAYS, FORMAT, PRODUCTS, LIMITS = "p3", ["1"], "prosperity", ["KELP", "RAINFOREST_RESIN"], {}  # --data changes them
MODES = {"per tick": EngineConfig(), "resting": EngineConfig(resting=True)}
ENGINE = ["python"]  # set in each worker by _init (--engine)


def archetypes() -> dict[str, tuple[str, dict]]:
    """name: (bot file, overrides), on PRODUCTS with LIMITS (the data's, with --data)."""
    def mm(edge):
        overrides = {"PARAMS": {p: {"make_edge": edge, "take_edge": 1, "hold": False} for p in PRODUCTS}}
        return MM, overrides | ({"LIMIT": min(LIMITS.values())} if LIMITS else {})
    limits = {"LIMITS": LIMITS} if LIMITS else {}
    return {"mm 0.5": mm(0.5), "mm 1": mm(1), "mm 2": mm(2), "taker": (f"{RIVALS}/taker.py", limits), "sniper": (f"{RIVALS}/sniper.py", limits),
            "spoofer": (f"{RIVALS}/spoofer.py", limits), "trapper": (f"{RIVALS}/trapper.py", limits), "copy": (TEMPLATE, {})}


FIELDS = {"none": ()} | {name: (name,) for name in ("mm 0.5", "mm 1", "mm 2", "taker", "sniper", "spoofer", "trapper", "copy")} | {
    "three makers": ("mm 0.5", "mm 1", "mm 2"),
    "adversaries": ("sniper", "spoofer", "trapper"),
    "flow": ("mm 1", "taker", "copy"),
    "crowd": ("copy", "mm 0.5", "mm 1", "taker", "sniper"),
    "six": ("mm 0.5", "mm 2", "taker", "sniper", "spoofer", "copy"),
}


def candidates() -> list[dict]:
    return [dict(zip(AXES, values)) for values in itertools.product(*AXES.values())]


def label(candidate: dict) -> str:
    return ", ".join(f"{k.removeprefix('PARAMS.').replace('RAINFOREST_RESIN', 'RESIN')} {v}" for k, v in candidate.items())


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})


def _settings(dataset, axes: list[str]) -> dict:
    from arena.formats import FORMATS

    if dataset.format != "prosperity":
        raise ValueError("the archetypes are Prosperity-format bots: --format prosperity only")
    fmt = FORMATS[dataset.format]
    limits = {p: v for day in fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days)) for p, v in day.limits.items()
              if p in dataset.products}
    settings = {"DATA": dataset.data, "DAYS": list(dataset.days), "PRODUCTS": list(dataset.products), "TEMPLATE": dataset.bot, "LIMITS": limits}
    if axes:
        settings["AXES"] = {axis.target: list(axis.values) for axis in map(grid.parse_axis, axes)}
    return settings


def run(task: tuple[int, str, str]) -> tuple[tuple[int, str, str], float]:
    """One candidate in one field under one mode: our PnL over the days."""
    k, field, mode = task
    found = archetypes()
    bots = [("you", TEMPLATE, candidates()[k], False)] + [(name, *found[name], False) for name in FIELDS[field]]
    total = 0.0
    for day in backtest_days(DATA, DAYS, ENGINE[0], FORMAT):
        (mine, *_) = backtest(day, bots, MODES[mode], ENGINE[0], fields=("pnl",), format_name=FORMAT)
        total += sum(series[-1] for series in mine.pnl.values() if series)
    return task, total


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.rival_field")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    parser.add_argument("--candidate", action="append", default=[], metavar="PARAMS.P.KEY=V1,V2",
                        help="with --data: an axis of the candidate settings, as arena.grid's --grid (repeatable)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser)
    args = parser.parse_args()
    try:
        dataset = dataset_from(args)
        if args.candidate and not dataset:
            raise ValueError("--candidate goes with --data")
        settings = _settings(dataset, args.candidate) if dataset else {}
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    globals().update(settings)
    tasks = [(k, f, m) for k in range(len(candidates())) for f in FIELDS for m in MODES]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        pnl = dict(pool.map(run, tasks, chunksize=1))

    names, fields, rivals = [label(c) for c in candidates()], list(FIELDS), [f for f in FIELDS if FIELDS[f]]
    where = f"{dataset.name}" if dataset else "P3 round 1, all three days"
    print(f"{where}, --match-trades all. Our PnL in thousands, each candidate in each field of rivals: "
          + "; ".join(f"{f} = {' + '.join(FIELDS[f])}" for f in fields if len(FIELDS[f]) > 1) + ".")
    for mode in MODES:
        print(f"\n{mode}:\n")
        print("| Candidate | " + " | ".join(fields) + " | worst | mean |")
        print("|---" * (len(fields) + 3) + "|")
        for k, name in enumerate(names):
            row = [pnl[(k, f, mode)] for f in fields]
            against = [pnl[(k, f, mode)] for f in rivals]
            print(f"| {name} | " + " | ".join(f"{v / 1000:.1f}" for v in row) + f" | {min(against) / 1000:.1f} | {statistics.fmean(against) / 1000:.1f} |")
        best = {f: max(range(len(names)), key=lambda k: pnl[(k, f, mode)]) for f in fields}
        print("| **best reply** | " + " | ".join(names[best[f]] for f in fields) + " | | |")
        worst = max(range(len(names)), key=lambda k: min(pnl[(k, f, mode)] for f in rivals))
        mean = max(range(len(names)), key=lambda k: statistics.fmean(pnl[(k, f, mode)] for f in rivals))
        replies = {names[best[f]] for f in rivals}
        print(f"\nmax-min: {names[worst]}; mean: {names[mean]}; against a copy alone (the two-bot answer): {names[best['copy']]}. "
              f"{len(replies)} different best replies over {len(rivals)} fields.")


if __name__ == "__main__":
    main()
