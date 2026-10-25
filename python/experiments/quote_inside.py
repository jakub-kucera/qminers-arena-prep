"""Quoting nearer fair than one tick inside the book: the template's make_inside against rivals that
quote nearer fair, and what it costs alone.

usage (from the repo root): uv run python -m experiments.quote_inside [--jobs N] [--engine rust]

`make` quotes make_edge from fair, or make_inside ticks inside the best book quote if that is further
out (1 as committed). Per tick nobody's orders rest, so the book shows no rival's quote; with price
priority a rival quoting nearer fair takes each market trade first (IDEAS.md, "Why the zoo beat the
template head to head"). make_inside None quotes at make_edge whatever the book.

P3 round 1, all three days, Kelp and Resin (what the template trades there). CANDIDATES: make_inside
1, 2, 3 and None, each with the committed make_edge (Kelp 0.5, Resin 2) and with Kelp 1, Resin 1.
CONTEXTS, each per tick (--match-trades all) and with --resting (the zoo bots requoted each tick):
  - alone (also per tick under worse);
  - against Gemini's zoo market maker, the one that took Resin from the template;
  - against each hosted zoo bot in turn (the 12 not from local models), their mean;
  - in one market with all 12;
  - against python/bots/mm.py at make_edge 0.5 and at 1 (experiments.rival_field's makers).
For each product: our PnL in thousands per candidate and context, the best candidate in each, and
each candidate's worst and mean over the contexts with rivals, against its cost alone.
Results go into IDEAS.md ("Quoting nearer fair than one tick inside the book, against rivals that do").
"""

from __future__ import annotations

import argparse
import itertools
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import add_engine_argument, backtest, backtest_days
from arena.engine import EngineConfig, TradeMatching
from experiments.zoo import TEMPLATE, is_local, label, zoo_bots

PRODUCTS = ("KELP", "RAINFOREST_RESIN")
INSIDE = (1, 2, 3, None)
EDGES = {"committed edges": {"KELP": 0.5, "RAINFOREST_RESIN": 2}, "Kelp 1, Resin 1": {"KELP": 1, "RAINFOREST_RESIN": 1}}
GEMINI = Path("python/bots/zoo/gemini/gemini-3-8-flash-high_market_maker.py")
MM = Path("python/bots/mm.py")
MODES = {"per tick": EngineConfig(), "resting": EngineConfig(resting=True)}
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def candidates() -> list[tuple[str, dict]]:
    return [(f"inside {'None' if inside is None else inside}, {name}",
             {f"PARAMS.{p}.{key}": value for p in PRODUCTS for key, value in (("make_inside", inside), ("make_edge", edges[p]))})
            for (name, edges), inside in itertools.product(EDGES.items(), INSIDE)]


def hosted() -> list[Path]:
    return [p for p in zoo_bots() if not is_local(p)]


def mm(edge: float) -> tuple[Path, dict]:
    return MM, {"PARAMS": {p: {"make_edge": edge, "take_edge": 1, "hold": False} for p in PRODUCTS}}


def contexts() -> dict[str, tuple[str, list[tuple[str, Path, dict]]]]:
    """name: (mode, the rivals), "h2h" contexts standing for one context a hosted zoo bot."""
    out = {"alone, all": ("per tick", []), "alone, worse": ("worse", []), "alone, resting": ("resting", [])}
    for mode in MODES:
        out[f"vs Gemini mm, {mode}"] = (mode, [("gemini", GEMINI, {})])
        for path in hosted():
            out[f"h2h {label(path)}, {mode}"] = (mode, [("rival", path, {})])
        out[f"zoo field, {mode}"] = (mode, [(label(p), p, {}) for p in hosted()])
        for edge in (0.5, 1):
            out[f"vs mm {edge}, {mode}"] = (mode, [(f"mm {edge}", *mm(edge))])
    return out


def run(task: tuple[int, str]) -> tuple[tuple[int, str], dict[str, float]]:
    """One candidate in one context: our PnL per product over the days."""
    k, context = task
    mode, rivals = contexts()[context]
    config = EngineConfig(trade_matching=TradeMatching.WORSE) if mode == "worse" else MODES[mode]
    requote = config.resting  # the zoo bots never cancel: requote them each tick when orders rest
    bots = [("you", TEMPLATE, candidates()[k][1], False)] + [(name, path, o, requote and path != MM) for name, path, o in rivals]
    totals = dict.fromkeys(PRODUCTS, 0.0)
    for day in backtest_days("p3", ["1"], ENGINE[0]):
        (mine, *_) = backtest(day, bots, config, ENGINE[0], fields=("pnl",))
        for p in PRODUCTS:
            totals[p] += mine.pnl[p][-1] if mine.pnl.get(p) else 0.0
    return task, totals


def table(names: list[str], columns: list[str], value) -> list[str]:
    lines = ["| Candidate | " + " | ".join(columns) + " |", "|---" * (len(columns) + 1) + "|"]
    lines += [f"| {name} | " + " | ".join(value(k, c) for c in columns) + " |" for k, name in enumerate(names)]
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.quote_inside")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.require(args.allow_stale)
    names, found = [n for n, _ in candidates()], contexts()
    tasks = [(k, c) for k in range(len(names)) for c in found]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        pnl = dict(pool.map(run, tasks, chunksize=1))

    h2h = {mode: [c for c in found if c.startswith("h2h ") and c.endswith(mode)] for mode in MODES}
    shown = [c for c in found if not c.startswith("h2h ")]
    columns = shown[:3] + [c for mode in MODES for c in (f"vs Gemini mm, {mode}", f"h2h mean, {mode}", f"zoo field, {mode}",
                                                          f"vs mm 0.5, {mode}", f"vs mm 1, {mode}")]

    def value(k: int, context: str, product: str) -> float:
        if context.startswith("h2h mean, "):
            return statistics.fmean(pnl[(k, c)][product] for c in h2h[context.removeprefix("h2h mean, ")])
        return pnl[(k, context)][product]

    rivals = columns[3:]
    print(f"P3 round 1, all three days. Our PnL in thousands per product, each candidate (make_inside, make_edge) in each "
          f"context; h2h mean: the mean over the {len(hosted())} hosted zoo bots one at a time; zoo field: all of them in one market.")
    for product in PRODUCTS:
        print(f"\n{product}:\n")
        print("\n".join(table(names, columns, lambda k, c: f"{value(k, c, product) / 1000:.1f}")))
        best = {c: max(range(len(names)), key=lambda k: value(k, c, product)) for c in columns}
        print("| **best** | " + " | ".join(names[best[c]] for c in columns) + " |")
        print(f"\n{product}, over the {len(rivals)} contexts with rivals (worst / mean) against alone (all / worse / resting), thousands:")
        for k, name in enumerate(names):
            against = [value(k, c, product) for c in rivals]
            alone = [value(k, c, product) for c in columns[:3]]
            print(f"  {name:<34} worst {min(against) / 1000:>6.1f}  mean {statistics.fmean(against) / 1000:>6.1f}   alone "
                  + " / ".join(f"{v / 1000:.1f}" for v in alone))
        worst = max(range(len(names)), key=lambda k: min(value(k, c, product) for c in rivals))
        mean = max(range(len(names)), key=lambda k: statistics.fmean(value(k, c, product) for c in rivals))
        print(f"  max-min: {names[worst]}; mean: {names[mean]}")


if __name__ == "__main__":
    main()
