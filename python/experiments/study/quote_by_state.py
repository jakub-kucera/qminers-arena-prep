"""Choosing the quote's distance by spread (Guilbaud & Pham), as a variant of the template, by held-out days.

usage (from the repo root): uv run python -m experiments.study.quote_by_state [--jobs N]

`experiments.day.fill_curve`'s part 3 picks, per spread bin, the distance from fair whose one-lot quote
was worth most on the other days (an upper bound: nobody ahead of the quote), and that choice beats a
single distance on every held-out day on P3 round 1 and P4 round 1. Here the same table, fitted on
the other days, sets `make_edge` by the book's spread in a variant of the template (`edge_by_spread`,
patched in at run time, so it follows the committed template and needs no Rust twin), and the
held-out day is backtested with it and with the template as committed, under `all`, `worse` and
`--resting`. Spreads are binned as fill_curve's `spread_bin` in price units (a tick of 1 on
Prosperity). Results: IDEAS.md, "Choosing the quote by state".
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena.cli import backtest
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS
from experiments.day.fill_curve import DISTANCES, quote_values, ticks_of

TEMPLATE = Path("python/bots/template.py")
DATASETS = [("p3", ["1"], ["RAINFOREST_RESIN", "KELP"]), ("p4", ["1", "2"], ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"])]
MODES = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE), "resting": EngineConfig(resting=True)}
PATCHES = (  # (anchor in the template, the text to put after it)
    ('    "make_inside": 1,', None),  # checked only: the line edge_by_spread follows
    ('    best_ask = next((price for price, volume in book.asks if volume > 0), None)\n',
     '    if p["edge_by_spread"] and best_bid is not None and best_ask is not None:\n'
     '        p = {**p, "make_edge": p["edge_by_spread"].get(spread_key(best_ask - best_bid), p["make_edge"])}\n'),
)
DEFAULT = '    "edge_by_spread": None,  # {spread bin: make_edge}, the bins as spread_key\'s; None: make_edge always\n'
KEY = '''

def spread_key(spread: float) -> str:
    """fill_curve's spread bins."""
    return f"{spread:g}" if spread <= 4 else "5-8" if spread <= 8 else "9-16" if spread <= 16 else ">16"
'''
BOT: list[str] = []  # the variant's path, set in each worker


def variant() -> str:
    """The template's source with edge_by_spread in it; fails if an anchor has moved."""
    source = TEMPLATE.read_text()
    for anchor, text in PATCHES:
        if source.count(anchor) != 1:
            raise SystemExit(f"the template changed: {anchor.strip()!r} is not there exactly once")
        if text:
            source = source.replace(anchor, anchor + text)
    line = next(line for line in source.splitlines(keepends=True) if line.startswith('    "make_inside": 1,'))
    source = source.replace(line, line + DEFAULT)
    marker = "\n\ndef make("
    if source.count(marker) != 1:
        raise SystemExit("the template changed: no single make to put spread_key before")
    return source.replace(marker, KEY + marker)


def table(rows: list[dict]) -> dict[str, float]:
    """The best distance per spread bin on these rows (fill_curve's part 3)."""
    return {key: max(DISTANCES, key=lambda d: cell[d][0]) for key, cell in quote_values(rows, DISTANCES).items()}


def _init(bot: str) -> None:
    BOT[:] = [bot]


def _run(job):
    data, spec, day_name, overrides, mode = job
    fmt = FORMATS["prosperity"]
    (day,) = [d for d in fmt.load_days(fmt.resolve_data_dir(data), spec) if d.name == day_name]
    bot = BOT[0] if overrides else str(TEMPLATE)
    (result,) = backtest(day, [("you", bot, overrides, False)], MODES[mode], "python", fields=("pnl",), format_name="prosperity")
    return job, {p: s[-1] for p, s in result.pnl.items() if s}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.study.quote_by_state")
    parser.add_argument("--jobs", type=int, default=None)
    args = parser.parse_args(argv)
    jobs, tables = [], {}
    fmt = FORMATS["prosperity"]
    for data, specs, products in DATASETS:
        days = fmt.load_days(fmt.resolve_data_dir(data), specs)
        rows = {(p, d.name): ticks_of(d, p) for d in days for p in products}
        for test in days:
            overrides = {}
            for p in products:
                fitted = table([r for d in days if d.name != test.name for r in rows[(p, d.name)]])
                overrides[f"PARAMS.{p}.edge_by_spread"] = fitted
                tables[(data, test.name, p)] = fitted
            spec = [test.name.split("d")[0].removeprefix("r")]  # the round the day belongs to: r1d-2 -> 1
            for mode in MODES:
                jobs += [(data, tuple(spec), test.name, overrides, mode), (data, tuple(spec), test.name, {}, mode)]
    with tempfile.TemporaryDirectory() as folder:
        bot = Path(folder) / "quote_by_state.py"
        bot.write_text(variant())
        with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(str(bot),)) as pool:
            results = list(pool.map(_run, [(d, list(s), n, o, m) for d, s, n, o, m in jobs]))
    pnl = {(data, day, bool(overrides), mode): r for (data, _, day, overrides, mode), r in results}
    print("The template with make_edge chosen per spread bin on the other days, against the template as committed, on the held-out day")
    for data, _, products in DATASETS:
        for p in products:
            totals = {(variant_on, mode): 0.0 for variant_on in (True, False) for mode in MODES}
            print(f"\n{data} {p}")
            for (d, day, variant_on, mode), r in sorted(pnl.items()):
                if d == data:
                    totals[(variant_on, mode)] += r.get(p, 0.0)
            for (d, day, product), fitted in tables.items():
                if d == data and product == p:
                    row = " · ".join(f"{mode} {pnl[(d, day, True, mode)].get(p, 0.0):,.0f} vs {pnl[(d, day, False, mode)].get(p, 0.0):,.0f}" for mode in MODES)
                    print(f"  {day}: table {', '.join(f'{k}: {v:g}' for k, v in fitted.items())}  {row}")
            print("  total: " + " · ".join(f"{mode} {totals[(True, mode)]:,.0f} vs {totals[(False, mode)]:,.0f} "
                                            f"({totals[(True, mode)] - totals[(False, mode)]:+,.0f})" for mode in MODES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
