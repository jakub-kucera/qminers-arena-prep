"""Can a bot learn its make_edge online, from its own fills, whatever the exchange's fill model?

usage (from the repo root): uv run python -m experiments.online_edge [--jobs N] [--part tune|test|both] [--hyper KEY=V,...]

Every setting is tuned in backtests under a fill model we guess at, and Kelp's best fixed make_edge
differs by model (TODO.md, "Decisions": 0.5 under worse, 1-1.5 under all). The learner in
python/bots/research/online_edge.py (learn_edge: paired windows at make_edge +/- learn_delta, each
passive fill scored by its markout, a sign step toward the better side) should land near each
model's best fixed edge, and its worst case over the models should beat every fixed edge's.

Each product of a dataset gets the same treatment at once (products don't interact in these
markets, so each is read on its own): a fixed make_edge from FIXED, or the learner started at
each of STARTS. Each runs under every model in MODELS: all, worse, worse with a 0.5 fee, resting
with the queue by probability, one tick late, and resting against a copy of the template. Under
the fee, the learner is also run told of the fee (learn_cost 0.5, the "known" rows), since a bot
can't see a fee in its fills.

Part 1 (tune) chooses the learner's own settings, all trials, on P3 round 1 day -2 alone: each
setting of HYPER_GRID, scored by its worst regret over the models (the best fixed edge's PnL
less the learner's, per product, averaged over the starts), summed over Kelp and Resin. Part 2
(test) runs the chosen setting, untouched, on the other P3 round 1 days, on P4 round 1 (Osmium
and Pepper Root) and on fresh arena.sim days (Kelp and Resin presets, seeds SIM_SEEDS), with day
-2 shown as in sample. Per dataset and product: PnL per model, the worst over the models, the
worst regret, and where the learned edge ends (its mean over days, and its path through the day).
The "best fixed" row is chosen with hindsight on the same days; the learner starts blind, so the
fair comparison for a start is also the fixed row at the same value.
Results go into IDEAS.md ("Learning make_edge online"). Python engine only: the research bot has
no Rust twin.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import statistics
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import sim
from arena.cli import participant_names
from arena.engine import EngineConfig, run_market
from arena.formats import FORMATS
from arena.scenario import config_for, parse_scenario, rivals_for

BOT = Path("python/bots/research/online_edge.py")
MODELS = [parse_scenario(text) for text in (
    "all:match=all",
    "worse:match=worse",
    "wfee05:match=worse,fee=0.5",
    "rest:resting,queue=prob",
    "late:delay=1",
    "war:resting,vs=python/bots/template.py",
)]
FEE_MODEL, FEE = "wfee05", 0.5
FIXED = (0.5, 1, 1.5, 2, 3)
STARTS = (0.5, 1, 2)
HYPER_GRID = {"learn_design": ("symmetric", "probe"), "learn_window": (100, 250, 500), "learn_horizon": (5, 20, 100), "learn_step": (0.25, 0.5)}
HYPER_FIXED = {"learn_delta": 0.5, "learn_min": 0.5, "learn_max": 4.0}  # the smallest probe that moves a quote off a half-integer fair
# Part 1's pick, which part 2 runs alone (--part test) and `--part both` checks against.
CHOSEN = HYPER_FIXED | {"learn_design": "probe", "learn_window": 100, "learn_horizon": 5, "learn_step": 0.5}
PATH_EVERY = 2_500  # ticks between samples of the learned edge (a quarter of a Prosperity day)
SIM_SEEDS = tuple(800_000 + i for i in range(5))
P3, P4 = ("KELP", "RAINFOREST_RESIN"), ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT")
# name: (data, day specs or sim seeds, products)
DATASETS = {
    "p3 1--2": ("p3", ["1--2"], P3),
    "p3 1--1 1-0": ("p3", ["1--1", "1-0"], P3),
    "p4 1": ("p4", ["1"], P4),
    "sim": ("sim", list(SIM_SEEDS), P3),
}
TUNE_SET = "p3 1--2"

_DAYS: dict = {}


def days(name: str) -> list:
    if name not in _DAYS:
        data, specs, products = DATASETS[name]
        if data == "sim":
            _DAYS[name] = [sim.run(sim.preset_market(list(products)), seed).day for seed in specs]
        else:
            fmt = FORMATS["prosperity"]
            _DAYS[name] = fmt.load_days(fmt.resolve_data_dir(data), specs)
    return _DAYS[name]


class Tracked:
    """The bot, sampling its learned edges from traderData every PATH_EVERY ticks."""

    def __init__(self, bot, products):
        self.bot, self.products, self.ticks, self.path = bot, products, 0, {p: [] for p in products}

    def __getattr__(self, name):  # begin_day and anything else run_market asks of the bot
        return getattr(self.bot, name)

    def step(self, *args):
        actions = self.bot.step(*args)
        self.ticks += 1
        if self.ticks % PATH_EVERY == 0:
            memory = json.loads(self.bot._trader_data or "{}")
            for p in self.products:
                e = memory.get(p, {}).get("learn", {}).get("e")
                if e is not None:
                    self.path[p].append(e)
        return actions


def overrides(products, edge: float, learn: dict | None) -> dict:
    out = {}
    for p in products:
        out[f"PARAMS.{p}.make_edge"] = edge
        if learn is not None:
            out[f"PARAMS.{p}.learn_edge"] = True
            out |= {f"PARAMS.{p}.{k}": v for k, v in learn.items()}
    return out


def run(task: tuple) -> tuple:
    """One candidate on one day under one model: (task, PnL per product, the learned edges' paths, errors)."""
    dataset, d, edge, learn, model = task
    learn = dict(learn) if learn is not None else None
    products = DATASETS[dataset][2]
    day = days(dataset)[d]
    fmt = FORMATS["prosperity"]
    scenario = next(m for m in MODELS if m.name == model)
    rivals = rivals_for([], scenario)
    me = Tracked(fmt.load_bot(BOT, overrides(products, edge, learn), True), products)
    bots = [me, *(fmt.load_bot(r.path, r.overrides, True) for r in rivals)]
    result = run_market(day, list(zip(participant_names(BOT, rivals), bots)), config_for(EngineConfig(), scenario))[0]
    pnl = {p: result.pnl[p][-1] if result.pnl.get(p) else 0.0 for p in products}
    return task, pnl, me.path, len(result.errors) + len(result.limit_breaches)


def candidates(learn: dict, model: str) -> list[tuple[str, float, dict | None]]:
    """(label, make_edge, learner settings or None) for each run under a model."""
    out = [(f"fixed {e:g}", e, None) for e in FIXED] + [(f"learn {e:g}", e, learn) for e in STARTS]
    if model == FEE_MODEL:
        out += [(f"learn {e:g} known", e, learn | {"learn_cost": FEE}) for e in STARTS]
    return out


def run_all(tasks: list[tuple], jobs: int) -> dict:
    found = {}
    if jobs <= 1:
        results = map(run, tasks)
    else:
        pool = ProcessPoolExecutor(jobs)
        results = pool.map(run, tasks, chunksize=1)
    for task, pnl, path, errors in results:
        if errors:
            print(f"! {task}: {errors} errors or breaches")
        found[task] = (pnl, path)
    if jobs > 1:
        pool.shutdown()
    return found


def _key(learn: dict | None):
    return None if learn is None else tuple(sorted(learn.items()))


def collect(dataset: str, learn: dict, found: dict) -> dict:
    """{product: {model: {label: (total PnL over the days, [end edges per day], [mean path])}}}"""
    products = DATASETS[dataset][2]
    n = len(days(dataset))
    by_task = found
    out = {p: {} for p in products}
    for m in MODELS:
        for label, edge, settings in candidates(learn, m.name):
            runs = [by_task[(dataset, d, edge, _key(settings), m.name)] for d in range(n)]
            for p in products:
                ends = [path[p][-1] for _, path in runs if path[p]]
                paths = [path[p] for _, path in runs if path[p]]
                mean_path = [statistics.mean(x) for x in zip(*paths)] if paths else []
                out[p].setdefault(m.name, {})[label] = (sum(pnl[p] for pnl, _ in runs), ends, mean_path)
    return out


def tasks_for(dataset: str, learn: dict) -> list[tuple]:
    return [(dataset, d, edge, _key(settings), m.name) for m in MODELS for _, edge, settings in candidates(learn, m.name)
            for d in range(len(days(dataset)))]


def regrets(table: dict) -> dict[str, dict[str, float]]:
    """Per learner label: per model, the best fixed edge's PnL less the learner's (one product's table)."""
    out = {}
    for model, rows in table.items():
        best = max(v[0] for label, v in rows.items() if label.startswith("fixed"))
        for label, v in rows.items():
            out.setdefault(label, {})[model] = best - v[0]
    return out


def score_setting(tables: dict) -> tuple[float, float]:
    """(worst regret over models, mean regret), each averaged over the starts and summed over the products."""
    worst = mean = 0.0
    for table in tables.values():
        r = regrets(table)
        learners = [label for label in r if label.startswith("learn") and not label.endswith("known")]
        worst += statistics.mean(max(r[label].values()) for label in learners)
        mean += statistics.mean(statistics.mean(r[label].values()) for label in learners)
    return worst, mean


# ---------------------------------------------------------------------------- printing


def _num(x: float) -> str:
    return f"{x:,.0f}"


def format_table(title: str, table: dict) -> str:
    models = [m.name for m in MODELS]
    labels = list(table[models[0]])
    known = [label for label in table[FEE_MODEL] if label.endswith("known")]
    r = regrets(table)
    header = ["", *models, "worst", "max regret"]
    rows = []
    for label in [*labels, *known]:
        cells = [table[m][label][0] if label in table[m] else None for m in models]
        present = [c for c in cells if c is not None]
        worst = min(present) if len(present) == len(models) else None
        rows.append([label, *("" if c is None else _num(c) for c in cells), "" if worst is None else _num(worst),
                     _num(max(r[label].values())) if len(r[label]) == len(models) else ""])
    best = ["best fixed"]
    for m in models:
        fixed = {label: v[0] for label, v in table[m].items() if label.startswith("fixed")}
        best.append(max(fixed, key=fixed.get).removeprefix("fixed "))
    fixed_worst = {label: min(table[m][label][0] for m in models) for label in labels if label.startswith("fixed")}
    best += [max(fixed_worst, key=fixed_worst.get).removeprefix("fixed "), ""]
    rows.append(best)
    widths = [max(len(c) for c in column) for column in zip(header, *rows)]
    lines = [title]
    lines += ["  ".join(c.ljust(w) if i == 0 else c.rjust(w) for i, (c, w) in enumerate(zip(cells, widths))) for cells in [header, *rows]]
    return "\n".join(lines)


def format_edges(table: dict) -> str:
    """Where each learner's edge ends: the mean over days, the range, and the mean path through the day."""
    lines = ["  learned edge at the close (mean over days [min-max]; mean path at each quarter of the day):"]
    for m in MODELS:
        parts = []
        for label, (_, ends, path) in table[m.name].items():
            if label.startswith("learn") and ends:
                parts.append(f"{label.removeprefix('learn ')}: {statistics.mean(ends):.2f} [{min(ends):g}-{max(ends):g}] "
                             f"({' '.join(f'{x:.2f}' for x in path)})")
        lines.append(f"    {m.name:<7} " + "; ".join(parts))
    return "\n".join(lines)


def _value(text: str):
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.online_edge", description=__doc__.split("\n")[0])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--part", choices=["tune", "test", "both"], default="both")
    parser.add_argument("--hyper", help="the learner's settings for part 2 in place of part 1's pick, e.g. learn_window=250,learn_horizon=20,learn_step=0.25")
    parser.add_argument("--sets", help=f"comma-separated datasets for part 2 (default: all of {', '.join(DATASETS)})")
    args = parser.parse_args(argv)
    start = time.perf_counter()

    chosen = None
    if args.hyper:
        chosen = HYPER_FIXED | {k: _value(v) for k, v in (item.split("=") for item in args.hyper.split(","))}
    if args.part in ("tune", "both"):
        settings = [HYPER_FIXED | dict(zip(HYPER_GRID, values)) for values in itertools.product(*HYPER_GRID.values())]
        tasks = list(dict.fromkeys(t for s in settings for t in tasks_for(TUNE_SET, s)))
        print(f"part 1: {len(settings)} learner settings on {TUNE_SET} ({len(tasks)} backtests)")
        found = run_all(tasks, args.jobs)
        scored = [(score_setting(collect(TUNE_SET, s, found)), s) for s in settings]
        scored.sort(key=lambda item: item[0])
        print("worst regret over the models (each product's best fixed edge per model, less the learner's PnL; mean over the starts, "
              "summed over the products), and the mean regret")
        print(f"{'design':>9} {'window':>6} {'horizon':>7} {'step':>5}  {'worst regret':>12}  {'mean regret':>11}")
        for (worst, mean), s in scored:
            print(f"{s['learn_design']:>9} {s['learn_window']:>6} {s['learn_horizon']:>7} {s['learn_step']:>5}  {_num(worst):>12}  {_num(mean):>11}")
        tables = collect(TUNE_SET, settings[0], found)
        for e in FIXED:
            r = [regrets(t)[f"fixed {e:g}"] for t in tables.values()]
            print(f"{'fixed':>9} {e:>6} {'':>7} {'':>5}  {_num(sum(max(x.values()) for x in r)):>12}  "
                  f"{_num(sum(statistics.mean(x.values()) for x in r)):>11}")
        if chosen is None:
            chosen = scored[0][1]
        print(f"chosen: {', '.join(f'{k}={v}' for k, v in chosen.items())}" + ("" if chosen == CHOSEN else " (not CHOSEN, the committed pick)") + "\n")
    if args.part in ("test", "both"):
        chosen = chosen or CHOSEN
        sets = [s.strip() for s in args.sets.split(",")] if args.sets else list(DATASETS)
        tasks = [t for name in sets for t in tasks_for(name, chosen)]
        print(f"part 2: the learner at {', '.join(f'{k}={v}' for k, v in chosen.items())}, {len(tasks)} backtests")
        found = run_all(tasks, args.jobs)
        for name in sets:
            note = " (in sample: the learner's settings were chosen here)" if name == TUNE_SET else ""
            for product, table in collect(name, chosen, found).items():
                print(format_table(f"\n{name}, {product}: PnL summed over {len(days(name))} days{note}", table))
                print(format_edges(table))
    print(f"\ndone in {time.perf_counter() - start:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
