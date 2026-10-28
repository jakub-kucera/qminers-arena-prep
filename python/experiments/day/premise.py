"""Is this download Prosperity's kind of market? One command for round 1's first check, before any prior from IDEAS.md.

usage (from the repo root): uv run python -m experiments.day.premise --data D --days 1 [--format F --bot BOT --products A,B] [--engine rust]

Every result in IDEAS.md was measured on Prosperity's generator, where one wall sits at the value,
trades don't move it and the order of the ticks doesn't matter. On ABIDES's agent market none of that
held and the playbook lost; two other settings paid (IDEAS.md, "An independent generator: ABIDES's
RMSC04" and the rows after it). Per product, on the given days:

  - **order** (the shuffle test, arena.grid --permute's): the bot's PnL on the days as recorded and
    its mean on COPIES copies of them with the ticks shuffled (arena.stress.permute, runs of 1). A
    shuffled PnL well above the real one (by SHUFFLE_GAIN of it) means the order of events costs the
    bot: informed or momentum flow, adverse selection. Prosperity: the same; ABIDES: millions against
    thousands.
  - **flow** (arena.diagnose): whether trades move the wall mid, and the market maker's margin.
  - **book** (arena.diagnose): a large-tick book, and on which side quoting at the best pays.
  - **forecast** (experiments.day.predict part 2): whether a held-out linear forecast of the wall mid
    beats the half-spread with R² above 0 on every held-out day (the linear fair's trigger).
  - **verdict**, and what to do, by how many of the three signs show (the order costs the bot, trades
    move the wall mid, the forecast fires): none, "Prosperity-like" (the priors stand); one, "mixed"
    (the priors stand, but each pick is checked against a bot that sends nothing, and the move gate
    gridded); two or three, "agent-like" (benchmark against doing nothing; grid the linear fair if
    the forecast fires, and the move gate). Plus the large-tick rule (make_edge half a tick where the
    margin pays, no quotes where no side does). One sign alone was "agent-like" before 2026-10-28,
    which called P3's Squid Ink so on its shuffle test alone (the fourth audit's R11).

The bot runs with its own PARAMS, and a product it doesn't list with DEFAULTS and the data's limit.
With one day only the forecast needs two, so it is skipped.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

from arena import diagnose, rust, stress
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, bot_params, dataset_from
from arena.engine import EngineConfig
from arena.formats import FORMATS
from experiments.day import predict

COPIES = 5
SHUFFLE_GAIN = 0.2  # a shuffled PnL above the real one by this share of the larger: the order of events matters (on 33 of
# Prosperity's 126 traded product-rounds, mostly small PnLs; on ABIDES 70 times over: IDEAS.md, "The premise check's verdict")
LINEAR_GRID = "--grid PARAMS.{p}.lin_rho3=0,1,3 --grid PARAMS.{p}.lin_momentum=0,0.5 --set PARAMS.{p}.lin_window=100"
GATE_GRID = "--grid 'PARAMS.{p}.gate_move=None,2,5' --grid PARAMS.{p}.gate_window=20,50"


def shuffle_test(days, products: list[str], bot: str, overrides: dict, engine: str, fmt: str) -> dict[str, tuple[float, float]]:
    """Per product: (PnL on the days as recorded, mean PnL on COPIES shuffled copies)."""
    real = {p: 0.0 for p in products}
    shuffled = {p: 0.0 for p in products}
    for day in days:
        for seed in range(COPIES + 1):
            run = day if seed == 0 else stress.permute(day, seed)
            (result,) = backtest(run, [("you", bot, overrides, False)], EngineConfig(), engine, False, ("pnl",), fmt)
            for p in products:
                series = result.pnl.get(p)
                value = series[-1] if series else 0.0
                if seed == 0:
                    real[p] += value
                else:
                    shuffled[p] += value / COPIES
    return {p: (real[p], shuffled[p]) for p in products}


def forecast_fires(days, products: list[str], product: str) -> tuple[bool, str]:
    """The linear fair's trigger: some horizon's held-out R² above 0 on every day and a move per sd above the half-spread."""
    if len(days) < 2:
        return False, "one day: skipped"
    res = predict.forecast_study(days, products, product)
    best = None
    for h, r in res["h"].items():
        r2s = [f["r2"] for f in r["folds"]]
        move = r["move_per_sd"]
        if move is not None and all(x is not None and x > 0 for x in r2s) and move > res["half"]:
            if best is None or move > best[1]:
                best = (h, move)
    if best:
        return True, f"fires at {best[0]} ticks: {best[1]:.2f} a sd against a half-spread of {res['half']:.2f}"
    return False, f"doesn't (half-spread {res['half']:.2f})"


def verdict(product: str, order: tuple[float, float], row: dict, fires: bool, grid: str = "uv run python -m arena.grid BOT DAYS") -> tuple[str, list[str]]:
    real, shuffled = order
    notes = row["notes"]
    signs = [name for name, shown in (("the order costs the bot", shuffled - real > SHUFFLE_GAIN * max(abs(real), abs(shuffled), 1.0)),
                                      ("trades move the wall mid", "trades move the wall mid" in notes),
                                      ("the forecast fires", fires)) if shown]
    kind = "agent-like" if len(signs) >= 2 else "mixed" if signs else "Prosperity-like"
    todo = []
    gate = f"grid the move gate: {grid} {GATE_GRID.format(p=product)} --modes all,worse --scenario rest:resting --holdout last"
    if kind == "agent-like":
        todo.append(f"benchmark: a bot that sends nothing; the playbook's quotes may lose ({', '.join(signs)}; ON_THE_DAY.md, \"Is it Prosperity's kind of market at all?\")")
        if fires:
            todo.append(f"grid the linear fair: {grid} {LINEAR_GRID.format(p=product)} --modes all,worse --scenario rest:resting --holdout last")
        todo.append(gate)
    elif kind == "mixed":
        todo.append(f"the IDEAS.md priors stand, but one sign doesn't ({signs[0]}): grid from diagnose --suggest's entry and check the pick against a bot that sends nothing")
        todo.append(gate)
    else:
        todo.append("the IDEAS.md priors stand: grid from diagnose --suggest's entry")
    if "large-tick" in notes:
        if "neither side" in notes:
            todo.append("large-tick, no side pays at the best: make_size 0 (take only)")
        elif "market making pays" in notes:
            todo.append("large-tick: make_edge 0.5, so the quote joins the best (a tick away never fills)")
    return kind, todo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.premise")
    add_dataset_arguments(parser)
    add_engine_argument(parser)
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
    except ValueError as error:
        parser.error(str(error))
    if dataset is None:
        parser.error("--data and --days are needed: this checks the day's download")
    if args.engine == "rust":
        rust.require(args.allow_stale)
        try:
            rust.kind_of(Path(dataset.bot))
        except ValueError:  # the day's bot before its twin is recorded (KICKOFF_PROMPT.md)
            print(f"note: {dataset.bot} has no Rust twin yet, so its backtests run on the Python engine", file=sys.stderr)
            args.engine = "python"
    fmt = FORMATS[dataset.format]
    days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
    products = args.products.split(",") if args.products else sorted({p for d in days for p in d.products})  # every product, listed or not
    listed = bot_params(dataset.bot, dataset.format)
    limits = {p: d.limits[p] for d in days for p in d.limits}
    overrides = {"PARAMS": {**{p: listed[p] for p in listed}, **{p: {"limit": limits[p]} for p in products if p not in listed}}}
    rows = diagnose.diagnose(days)
    order = shuffle_test(days, products, dataset.bot, overrides, args.engine, dataset.format)
    print(f"{dataset.name}: {len(days)} day(s), the bot {dataset.bot} (DEFAULTS and the limit for products it doesn't list)\n")
    print("| product | PnL as recorded | shuffled (mean of 5) | trades move the wall mid | margin | large-tick | forecast | verdict |")
    print("|---|---|---|---|---|---|---|---|")
    todos = {}
    for product in products:
        row = rows.get(product)
        if row is None:
            continue
        fires, why = forecast_fires(days, products, product)
        grid = f"uv run python -m arena.grid {dataset.bot} {' '.join(dataset.days)} --data {dataset.data} --format {dataset.format}" + (
            " --engine rust" if args.engine == "rust" else "")
        kind, todo = verdict(product, order[product], row, fires, grid)
        todos[product] = todo
        notes = row["notes"]
        margin = "thin or negative" if "thin or negative" in notes else "pays" if "market making pays" in notes else "-"
        real, shuffled = order[product]
        print(f"| {product} | {real:,.0f} | {shuffled:,.0f} | {'yes' if 'trades move the wall mid' in notes else 'no'} | {margin} | "
              f"{'yes' if 'large-tick' in notes else 'no'} | {why} | **{kind}** |")
    print()
    for product, todo in todos.items():
        print(f"{product}:")
        for line in todo:
            print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
