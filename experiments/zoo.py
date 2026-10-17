"""Scores every bot in bots/zoo/ against the template.

usage (from the repo root): uv run python -m experiments.zoo [--jobs N]

Each zoo bot, and the template, on P3 round 1 (all three days, the data SPEC.md describes):
  - alone, per tick, under --match-trades all and worse;
  - in one market with the template (`--vs`, per tick, all): the zoo bot's PnL and the template's;
  - inside arena.sim's market (its presets, seeds 0-2, default mode), where orders move the price.
Then the whole field at once: the template and every zoo bot in one market on P3 round 1.
Errors, limit breaches and the bot's slowest tick are listed too. Results go into IDEAS.md
("The LLM zoo"); bots/zoo/README.md says how to add bots from other providers.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import sim
from arena.engine import EngineConfig, TradeMatching, run_market
from arena.formats import prosperity

ZOO = Path("bots/zoo")
TEMPLATE = Path("bots/template.py")
SEEDS = (0, 1, 2)


def zoo_bots() -> list[Path]:
    return sorted(p for p in ZOO.rglob("*.py") if p.name not in {"bundle.py", "local.py"})


def label(path: Path) -> str:
    return "template" if path == TEMPLATE else f"{path.parent.name}/{path.stem}"


def load(path: Path):
    return prosperity.load_bot(path, {}, strict=False)


def total(result) -> float:
    return sum(series[-1] for series in result.pnl.values() if series)


def score(path: Path) -> dict:
    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["1"])
    row = {"bot": label(path), "errors": 0, "breaches": 0, "slowest_ms": 0.0, "by_product": {}}
    for mode in (TradeMatching.ALL, TradeMatching.WORSE):
        pnl = 0.0
        for day in days:
            (result,) = run_market(day, [("bot", load(path))], EngineConfig(trade_matching=mode))
            pnl += total(result)
            if mode is TradeMatching.ALL:
                row["errors"] += len(result.errors)
                row["breaches"] += len(result.limit_breaches)
                row["slowest_ms"] = max(row["slowest_ms"], 1000 * max(result.step_seconds, default=0))
                for product, series in result.pnl.items():
                    row["by_product"][product] = row["by_product"].get(product, 0.0) + (series[-1] if series else 0.0)
                if result.errors and "first_error" not in row:
                    row["first_error"] = result.errors[0][1].strip().splitlines()[-1]
        row[mode.value] = pnl
    if path != TEMPLATE:
        mine = theirs = 0.0
        for day in days:
            template, bot = run_market(day, [("template", load(TEMPLATE)), ("bot", load(path))])
            mine, theirs = mine + total(template), theirs + total(bot)
        row["vs_template"], row["template_vs"] = theirs, mine
    spec = sim.preset_market()
    row["sim"] = sum(total(sim.run(spec, seed, [("bot", load(path))]).results[0]) for seed in SEEDS)
    return row


def field() -> dict[str, float]:
    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["1"])
    paths = [TEMPLATE, *zoo_bots()]
    totals = dict.fromkeys(map(label, paths), 0.0)
    for day in days:
        results = run_market(day, [(label(p), load(p)) for p in paths])
        for path, result in zip(paths, results):
            totals[label(path)] += total(result)
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.zoo")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    args = parser.parse_args()
    paths = [TEMPLATE, *zoo_bots()]
    with ProcessPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(score, paths))
        crowd = pool.submit(field).result()

    print("P3 round 1, all three days; sim = arena.sim presets, seeds 0-2. PnL in thousands.\n")
    print("| Bot | alone, `all` | alone, `worse` | with the template (bot / template) | in arena.sim | in the field | errors | breaches | slowest tick |")
    print("|---|---|---|---|---|---|---|---|---|")
    for row in rows:
        vs = f"{row['vs_template'] / 1000:.1f} / {row['template_vs'] / 1000:.1f}" if "vs_template" in row else "-"
        print(
            f"| {row['bot']} | {row['all'] / 1000:.1f} | {row['worse'] / 1000:.1f} | {vs} | {row['sim'] / 1000:.1f}"
            f" | {crowd[row['bot']] / 1000:.1f} | {row['errors']} | {row['breaches']} | {row['slowest_ms']:.1f} ms |"
        )
    print("\nAlone under `all`, by product (thousands):")
    for row in rows:
        products = ", ".join(f"{p} {v / 1000:.1f}" for p, v in row["by_product"].items())
        print(f"  {row['bot']}: {products}" + (f"  (first error: {row['first_error']})" if "first_error" in row else ""))


if __name__ == "__main__":
    main()
