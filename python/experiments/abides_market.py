"""The template inside ABIDES's market, against the same day replayed: does what a recording says survive agents that see our orders?

usage (from the repo root, after `uv run python -m experiments.abides_days setup`):
  uv run python -m experiments.abides_market --days 10                              # the template as committed
  uv run python -m experiments.abides_market --days 10 --set PARAMS.ABM.lin_rho3=3 --set PARAMS.ABM.lin_momentum=0.5 [--resting]

Every ABIDES row in IDEAS.md comes from converted days: recordings, where the market's agents never
see our orders. Here, for each seed, two runs of the same RMSC04 day (python/experiments/abides_export/
export.py, with template_agent.TemplateAgent in both, so the latency draws and the market agree until
our first order):
  - in the market: the bot (with --set) trades once a second from the open; its PnL, cents, its end
    position valued at the last mid;
  - replayed: the idle run's day converted (experiments.abides_days), and the same bot through our
    engine on it under `all`, `worse` and `--resting --queue prob`.
With --resting the bot in the market keeps its quotes that haven't moved; without, every order of
ours lives one second. The idle runs are kept under data/abides/market/ and reused. Results:
IDEAS.md, "The template inside ABIDES's market".
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from arena.botfile import parse_override
from arena.engine import EngineConfig, QueueModel, TradeMatching, run_day
from arena.formats import prosperity
from experiments import abides_days

MARKET = abides_days.DATA / "market"


def replay(seed: int, bot: Path, overrides: dict) -> dict[str, float]:
    idle = MARKET / f"seed{seed}" / "idle"
    if not (idle / "meta.json").exists():
        idle.mkdir(parents=True, exist_ok=True)
        abides_days.export(seed, idle)
    data = MARKET / f"seed{seed}" / "data"
    if not (data / "round1").exists():
        abides_days.convert(idle, data, 1)
    (day,) = prosperity.load_days(data, ["1-1"])
    configs = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE),
               "resting": EngineConfig(resting=True, queue=QueueModel.PROB)}
    out = {}
    for name, config in configs.items():
        result = run_day(day, prosperity.load_bot(bot, overrides, strict=False), config)
        out[name] = sum(series[-1] for series in result.pnl.values() if series)
    return out


def in_market(seed: int, bot: Path, overrides: dict, resting: bool) -> dict:
    key = hashlib.sha256(json.dumps([str(bot), overrides, resting], sort_keys=True).encode()).hexdigest()[:12]
    run = MARKET / f"seed{seed}" / f"bot-{key}"
    run.mkdir(parents=True, exist_ok=True)
    extra = ["--bot", str(bot.resolve()), "--set", json.dumps(overrides)] + (["--resting"] if resting else [])
    abides_days.export(seed, run, extra=extra)
    return json.loads((run / "agent.json").read_text())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.abides_market")
    parser.add_argument("--days", type=int, default=10, help="seeds 1..N")
    parser.add_argument("--bot", type=Path, default=Path("python/bots/template.py"))
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="PATH=VALUE")
    parser.add_argument("--resting", action="store_true", help="in the market, keep the quotes that haven't moved")
    args = parser.parse_args(argv)
    overrides = dict(parse_override(text) for text in args.overrides)
    print(f"{args.bot} {' '.join(args.overrides) or '(as committed)'}, in ABIDES's market {'resting' if args.resting else 'per second'}, "
          "and its idle run replayed (PnL in cents)\n")
    print("| seed | in the market | lots filled | end position | replay all | replay worse | replay resting |")
    print("|---|---|---|---|---|---|---|")
    totals = [0.0] * 4
    for seed in range(1, args.days + 1):
        live = in_market(seed, args.bot, overrides, args.resting)
        recorded = replay(seed, args.bot, overrides)
        row = [live["pnl"], recorded["all"], recorded["worse"], recorded["resting"]]
        totals = [a + b for a, b in zip(totals, row)]
        print(f"| {seed} | {row[0]:,.0f} | {live['filled']:,} | {live['position']} | {row[1]:,.0f} | {row[2]:,.0f} | {row[3]:,.0f} |")
    print(f"| total | {totals[0]:,.0f} | | | {totals[1]:,.0f} | {totals[2]:,.0f} | {totals[3]:,.0f} |")


if __name__ == "__main__":
    main()
