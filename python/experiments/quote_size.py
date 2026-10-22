"""Using less than the full position limit: the template's quote size, alone and against rivals.

usage (from the repo root): uv run python -m experiments.quote_size [--jobs N] [--engine rust]

`make_size` None quotes all the room under the limit on each side: at a long target of 80, Pepper
Root offered its whole position and 80 more one tick above fair (it quotes 10 at most since
2026-10-18, this experiment's result; the caps below override it). Alone, the market's
passive flow per tick is small, so a cap of 20 costs nothing on any of the template's P3 round 1
and P4 rounds 1-2 products (arena.grid over make_size; IDEAS.md, "Using less than the full
position limit"). This asks what the cap does against rivals that could take more: a copy of the
template as committed, a copy with the same cap, and python/bots/rivals/' trapper, spoofer and sniper
(those three only see our orders when they rest, so --resting only).

For each dataset, mode, cap (CAPS, on every product the template trades there) and rival: our
PnL per product over the days, and our worst day.
Results go into IDEAS.md ("Using less than the full position limit").
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

from arena import rust
from arena.cli import add_engine_argument, backtest, backtest_days
from arena.engine import EngineConfig, TradeMatching

TEMPLATE = "python/bots/template.py"
DATASETS = {  # name: (data, days, the products the template trades there)
    "P3 r1": ("p3", ["1"], ["KELP", "RAINFOREST_RESIN"]),
    "P4 r1-2": ("p4", ["1", "2"], ["ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT"]),
}
MODES = {
    "all": EngineConfig(),
    "worse": EngineConfig(trade_matching=TradeMatching.WORSE),
    "resting": EngineConfig(resting=True),
}
CAPS = {"full room": None, "20": 20, "10": 10}
RIVALS = {  # name: (file, whether the rival takes our cap, the modes it runs in)
    "alone": None,
    "template copy": (TEMPLATE, False, ("all", "worse", "resting")),
    "copy, same cap": (TEMPLATE, True, ("all", "worse", "resting")),
    "trapper": ("python/bots/rivals/trapper.py", False, ("resting",)),
    "spoofer, 10 behind": ("python/bots/rivals/spoofer.py", False, ("resting",)),
    "sniper": ("python/bots/rivals/sniper.py", False, ("resting",)),
}


ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str) -> None:
    ENGINE[0] = engine


def _caps(products: list[str], cap: int | None) -> dict:
    return {f"PARAMS.{p}.make_size": cap for p in products}


def run(task: tuple[str, str, str, str]) -> tuple[tuple, dict]:
    dataset, mode, cap, rival = task
    data, days, products = DATASETS[dataset]
    out = {"pnl": defaultdict(float), "days": []}
    for day in backtest_days(data, days, ENGINE[0]):
        bots = [("template", TEMPLATE, _caps(products, CAPS[cap]), False)]
        if RIVALS[rival]:
            path, same_cap, _ = RIVALS[rival]
            overrides = _caps(products, CAPS[cap]) if same_cap else {"OFFSET": 10} if "spoofer" in rival else {}
            bots.append(("rival", path, overrides, False))
        mine = backtest(day, bots, MODES[mode], ENGINE[0], fields=("pnl",))[0]
        for p in products:
            out["pnl"][p] += mine.pnl[p][-1] if mine.pnl.get(p) else 0.0
        out["days"].append(sum(mine.pnl[p][-1] for p in products if mine.pnl.get(p)))
    return task, out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.quote_size")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    args = parser.parse_args()
    if args.engine == "rust":
        rust.require(args.allow_stale)
    tasks = [(d, m, c, r) for d in DATASETS for m in MODES for c in CAPS for r in RIVALS
             if RIVALS[r] is None or m in RIVALS[r][2]]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine,)) as pool:
        results = dict(pool.map(run, tasks))
    print("Our PnL in thousands over the dataset's days, per product, and our worst day (all products).\n")
    for d, (_, _, products) in DATASETS.items():
        print(f"| {d} | Mode | Rival | " + " | ".join(f"{p}: {c}" for p in products for c in CAPS) + " | Worst day: " + " / ".join(CAPS) + " |")
        print("|---|---|---|" + "---|" * (len(products) * len(CAPS) + 1))
        for m in MODES:
            for r in RIVALS:
                if (d, m, "full room", r) not in results:
                    continue
                cells = [f"{results[(d, m, c, r)]['pnl'][p] / 1000:.1f}" for p in products for c in CAPS]
                worst = " / ".join(f"{min(results[(d, m, c, r)]['days']) / 1000:.1f}" for c in CAPS)
                print(f"| | {m} | {r} | " + " | ".join(cells) + f" | {worst} |")
        print()


if __name__ == "__main__":
    main()
