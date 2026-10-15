"""Do the template's loss stops hold on days they weren't sized on?

usage (from the repo root): uv run python -m experiments.stops_held_out [--jobs N]

Every `stop_loss` in bots/template.py is about 3× the product's largest plain-day drawdown on the
days it was then tested on (IDEAS.md, "A loss stop per product"), so "never fires on a plain day"
held there by construction. Three checks off those days:

1. Held-out recorded days: P3 rounds 2-5, the days whose Kelp and Resin data aren't round 1's
   (Prosperity reuses days across rounds; compared as arena.grid.repeated_days does). P4 round 5
   has none of the products with a stop, and P4 rounds 1-4 were all used to size them.
2. Generated days: arena.sim's presets (Kelp and Resin; Squid Ink isn't traded), seeds 0-9, as
   recordings replayed by the engine.
   On both: per product, the plain days on which the stop fired (PnL with the stop differs from
   PnL with every stop off) and what it cost, and the worst loss on a perturbed day (arena.stress's
   perturbations) against the stop.
3. The sizing rule, leaving one day out, on the days the stops were sized on (P3 round 1, the
   distinct days of P4 rounds 1-2 and of rounds 3-4): with every stop off, a stop of 3× the largest
   drawdown on the other days, and whether the held-out day's drawdown exceeds it.
Drawdowns are of the engine's PnL (marked to the mid); the template's stop marks to its fair.
Results go into IDEAS.md ("A loss stop per product").
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import report, sim
from arena.botfile import BotFile
from arena.engine import EngineConfig, run_day
from arena.formats import prosperity
from arena.grid import SMOKE_TEST_TICKS
from arena.stress import PERTURBATIONS, perturb

TEMPLATE = Path("bots/template.py")
SEEDS = range(10)
HELD_OUT_PRODUCTS = ("KELP", "RAINFOREST_RESIN")
SIZED_ON = [("p3", [1]), ("p4", [1, 2]), ("p4", [3, 4])]  # each group's distinct days, for leave one day out
RULE = 3  # stop = RULE × the largest plain-day drawdown


def stops() -> dict[str, float]:
    module = BotFile(TEMPLATE, {"datamodel": prosperity.dm}, {}, False).load()
    return {p: v["stop_loss"] for p, v in module.PARAMS.items() if v.get("stop_loss") is not None}


def load(ref) -> object:
    if ref[0] == "sim":
        return sim.run(sim.preset_market(), ref[1]).day
    alias, rnd, day = ref
    return prosperity.load_day(prosperity.resolve_data_dir(alias), rnd, day)


def run(task):
    """(day ref, perturbation or None, stops on?) -> {product: (PnL, drawdown)}."""
    ref, perturbation, stops_on = task
    day = load(ref)
    if perturbation:
        day = perturb(day, perturbation)
    overrides = {} if stops_on else {f"PARAMS.{p}.stop_loss": None for p in stops() if p in day.products}
    result = run_day(day, prosperity.load_bot(TEMPLATE, overrides, strict=False), EngineConfig())
    return task, {p: (s[-1] if s else 0.0, report.max_drawdown(s)) for p, s in result.pnl.items()}


def fingerprint(day, product: str) -> str:
    ticks = day.ticks[:SMOKE_TEST_TICKS]
    return repr([(t.timestamp, t.books.get(product)) for t in ticks])


def distinct_days(alias: str, rounds: list[int], exclude: set[str] = frozenset(), products=None) -> list[tuple]:
    """Day refs of the rounds whose data (for `products`, else every product) is new."""
    data_dir = prosperity.resolve_data_dir(alias)
    seen, out = set(exclude), []
    for rnd, num in prosperity.list_days(data_dir):
        if rnd not in rounds:
            continue
        day = prosperity.load_day(data_dir, rnd, num)
        keys = {fingerprint(day, p) for p in (products or day.products) if p in day.products}
        if keys and not keys & seen:
            out.append((alias, rnd, num))
        seen |= keys
    return out


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.stops_held_out")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    args = parser.parse_args()
    limits = stops()

    p3 = prosperity.resolve_data_dir("p3")
    round1 = {fingerprint(prosperity.load_day(p3, 1, n), p) for r, n in prosperity.list_days(p3) if r == 1 for p in HELD_OUT_PRODUCTS}
    held_out = distinct_days("p3", [2, 3, 4, 5], round1, HELD_OUT_PRODUCTS)
    generated = [("sim", seed) for seed in SEEDS]
    groups = {f"{alias} rounds {'-'.join(map(str, rounds))}": distinct_days(alias, rounds) for alias, rounds in SIZED_ON}

    tasks = [(ref, None, on) for ref in held_out + generated for on in (True, False)]
    tasks += [(ref, name, True) for ref in held_out + generated for name in PERTURBATIONS]
    tasks += [(ref, None, False) for refs in groups.values() for ref in refs]
    with ProcessPoolExecutor(args.jobs) as pool:
        results = dict(pool.map(run, list(dict.fromkeys(tasks))))

    print("1-2. Off the sizing days. Stop fires: plain days where PnL with the stop differs from PnL without it.\n")
    print("| Days | Product | Stop | Plain days | Stop fires (PnL change) | Largest plain drawdown | Worst perturbed day |")
    print("|---|---|---|---|---|---|---|")
    for label, refs in (("P3 rounds 2-5, " + ", ".join(f"r{r} d{n}" for _, r, n in held_out), held_out), (f"arena.sim seeds 0-{SEEDS[-1]}", generated)):
        for product in HELD_OUT_PRODUCTS:
            fired, change, drawdown, worst = 0, 0.0, 0.0, (0.0, "")
            for ref in refs:
                on, off = results[(ref, None, True)][product], results[(ref, None, False)][product]
                if abs(on[0] - off[0]) > 1e-6:
                    fired += 1
                    change += on[0] - off[0]
                drawdown = max(drawdown, off[1])
                for name in PERTURBATIONS:
                    pnl = results[(ref, name, True)][product][0]
                    if pnl < worst[0]:
                        worst = (pnl, f"{ref[-1]} {name}")
            worst_text = f"{worst[0]:,.0f} ({worst[1]})" if worst[1] else "none negative"
            print(f"| {label} | {product} | {limits[product]:,.0f} | {len(refs)} | {fired} ({change:+,.0f}) | {drawdown:,.0f} | {worst_text} |")

    print(f"\n3. The sizing rule leaving one day out: stop = {RULE}× the largest drawdown on the other days, every stop off.\n")
    print("| Days | Product | Stop in PARAMS | Drawdown per day | Held-out days past their stop |")
    print("|---|---|---|---|---|")
    for label, refs in groups.items():
        products = sorted({p for ref in refs for p in results[(ref, None, False)] if p in limits})
        for product in products:
            dd = [results[(ref, None, False)].get(product, (0.0, 0.0))[1] for ref in refs]
            past = []
            for k, ref in enumerate(refs):
                stop = RULE * max(d for j, d in enumerate(dd) if j != k)
                if dd[k] > stop:
                    past.append(f"r{ref[1]} d{ref[2]}: {dd[k]:,.0f} > {stop:,.0f}")
            print(f"| {label} | {product} | {limits[product]:,.0f} | " + ", ".join(f"{d:,.0f}" for d in dd) + f" | {'; '.join(past) or 'none'} |")


if __name__ == "__main__":
    main()
