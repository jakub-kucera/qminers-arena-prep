"""The template inside ABIDES's market, against the same day replayed: does what a recording says survive agents that see our orders?

usage (from the repo root, after `uv run python -m experiments.abides_days setup`):
  uv run python -m experiments.abides_market --days 10                              # the template as committed
  uv run python -m experiments.abides_market --days 10 --set PARAMS.ABM.lin_rho3=3 --set PARAMS.ABM.lin_momentum=0.5 [--resting]
  uv run python -m experiments.abides_market --days 10 --options '{"num_momentum_agents": 0}'   # another RMSC04 setup

Every ABIDES row in IDEAS.md comes from converted days: recordings, where the market's agents never
see our orders. Here, for each seed, two runs of the same RMSC04 day (python/experiments/abides_export/
export.py, with template_agent.TemplateAgent in both, so the latency draws and the market agree until
our first order, though not the same day after it: our messages shift when the agents query the
oracle, so the fundamental parts within a minute):
  - in the market: the bot (with --set) trades once a second from the open; its PnL, cents, its end
    position valued at the last mid, and its largest |position| (within the limit since 2026-10-28,
    template_agent.py); --see-own leaves its own orders in the book it reads;
  - replayed: the idle run's day converted (experiments.abides_days), and the same bot through our
    engine on it under `all`, `worse` and `--resting --queue prob`.
With --resting the bot in the market keeps its quotes that haven't moved; without, every order of
ours lives one second. --options passes RMSC04's build_config arguments (its agents' numbers, the
fundamental's volatility), each setup's runs in its own folder. The idle runs are kept under
--out (data/abides/market/) and reused while meta.json's `code` matches the export code
(experiments.abides_days.code_hash); ABIDES's own log/ goes beside them. A day whose idle run leaves a side of the book empty or the mid far
from the fundamental (BROKEN: the price ran away, as with 50 momentum agents) is flagged and left out
of the total. Results:
IDEAS.md, "The template inside ABIDES's market".
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

from arena.botfile import parse_override
from arena.engine import EngineConfig, QueueModel, TradeMatching, run_day
from arena.formats import prosperity
from experiments import abides_days

MARKET = abides_days.DATA / "market"
BROKEN = (0.01, 0.5)  # a day with more one-sided seconds than this, or a mid this far from the fundamental, is broken (RMSC04: 0.1%, 0.1%)
SETUP = {"options": {}}  # RMSC04's build_config arguments, set by --options


def _folder(seed: int) -> Path:
    if not SETUP["options"]:
        return MARKET / f"seed{seed}"  # the default's runs where they always were
    key = hashlib.sha256(json.dumps(SETUP, sort_keys=True).encode()).hexdigest()[:10]
    return MARKET / f"options-{key}" / f"seed{seed}"


def replay(seed: int, bot: Path, overrides: dict) -> dict[str, float]:
    idle = _folder(seed) / "idle"
    if not (idle / "meta.json").exists() or json.loads((idle / "meta.json").read_text()).get("code") != abides_days.code_hash():
        idle.mkdir(parents=True, exist_ok=True)
        abides_days.export(seed, idle, **SETUP)
        shutil.rmtree(_folder(seed) / "data", ignore_errors=True)  # converted from the old idle run
    data = _folder(seed) / "data"
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


def sanity(seed: int) -> tuple[float, float]:
    """The idle day's share of seconds with a side of the book empty, and its mid's largest distance from the fundamental."""
    folder = _folder(seed) / "data" / "round1"
    with open(folder / "prices_round_1_day_1.csv") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    with open(folder / "fundamental_round_1_day_1.csv") as file:
        fundamental = [float(r["value"]) for r in csv.DictReader(file, delimiter=";")]
    both = [(float(r["mid_price"]), f) for r, f in zip(rows, fundamental) if r["bid_price_1"] and r["ask_price_1"]]
    return 1 - len(both) / len(rows), max(abs(mid - f) / f for mid, f in both)


def in_market(seed: int, bot: Path, overrides: dict, resting: bool, see_own: bool = False) -> dict:
    key = hashlib.sha256(json.dumps([str(bot), overrides, resting] + ([True] if see_own else []), sort_keys=True).encode()).hexdigest()[:12]
    run = _folder(seed) / f"bot-{key}"
    run.mkdir(parents=True, exist_ok=True)
    extra = ["--bot", str(bot.resolve()), "--set", json.dumps(overrides)] + (["--resting"] if resting else []) + (["--see-own"] if see_own else [])
    abides_days.export(seed, run, extra=extra, **SETUP)
    return json.loads((run / "agent.json").read_text())


def main(argv: list[str] | None = None) -> None:
    global MARKET
    parser = argparse.ArgumentParser(prog="python -m experiments.abides_market")
    parser.add_argument("--days", type=int, default=10, help="seeds 1..N")
    parser.add_argument("--bot", type=Path, default=Path("python/bots/template.py"))
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="PATH=VALUE")
    parser.add_argument("--resting", action="store_true", help="in the market, keep the quotes that haven't moved")
    parser.add_argument("--out", type=Path, default=MARKET, help=f"where the runs go (default {MARKET.relative_to(abides_days.ROOT)})")
    parser.add_argument("--see-own", action="store_true", help="in the market, the bot's book keeps its own live orders in")
    parser.add_argument("--options", default="{}", help="its build_config arguments, a JSON object, e.g. '{\"num_momentum_agents\": 0}'")
    args = parser.parse_args(argv)
    SETUP.update(options=json.loads(args.options))
    MARKET = args.out
    overrides = dict(parse_override(text) for text in args.overrides)
    print(f"{args.bot} {' '.join(args.overrides) or '(as committed)'}, in ABIDES's market ({args.options}) {'resting' if args.resting else 'per second'}{', seeing its own orders' if args.see_own else ''}, "
          "and its idle run replayed (PnL in cents)\n")
    print("| seed | in the market | lots filled | end position, largest | replay all | replay worse | replay resting | idle day: one-sided, mid off the fundamental |")
    print("|---|---|---|---|---|---|---|---|")
    totals, sane = [0.0] * 4, 0
    for seed in range(1, args.days + 1):
        live = in_market(seed, args.bot, overrides, args.resting, args.see_own)
        recorded = replay(seed, args.bot, overrides)
        row = [live["pnl"], recorded["all"], recorded["worse"], recorded["resting"]]
        one_sided, off = sanity(seed)
        broken = one_sided > BROKEN[0] or off > BROKEN[1]
        if not broken:
            totals = [a + b for a, b in zip(totals, row)]
            sane += 1
        print(f"| {seed} | {row[0]:,.0f} | {live['filled']:,} | {live['position']}, {live['max_position']} | {row[1]:,.0f} | {row[2]:,.0f} | {row[3]:,.0f} | "
              f"{one_sided:.1%}, {off:.1%}{' **broken**, not in the total' if broken else ''} |")
    print(f"| total ({sane} days) | {totals[0]:,.0f} | | | {totals[1]:,.0f} | {totals[2]:,.0f} | {totals[3]:,.0f} | |")


if __name__ == "__main__":
    main()
