"""Command-line options shared by arena.backtest, arena.validate and arena.grid."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from arena.botfile import parse_override
from arena.engine import DayResult, EngineConfig, QueueModel, TradeMatching, run_market
from arena.formats import FORMATS
from arena.model import Cancel, Day


@dataclass
class Setup:
    format: ModuleType
    days: list[Day]
    config: EngineConfig
    overrides: dict[str, object]
    rivals: list[Path] = field(default_factory=list)  # bots trading in the same market (--vs)
    requote: bool = False  # the rivals cancel all their resting orders every tick (--requote)
    engine: str = "python"  # arena.grid --engine: "rust" runs the backtests on rust/ (arena/rust.py)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("bot", type=Path, help="bot file")
    parser.add_argument("days", nargs="+", help="days to replay: ROUND for all its days, or ROUND-DAY (e.g. 1, 1-0, 1--1)")
    parser.add_argument("--format", default="prosperity", choices=sorted(FORMATS), help="competition format (default: prosperity)")
    parser.add_argument("--data", default="p3", help="data folder, or p2 / p3 / p4 for the Prosperity data in references/ (default: p3)")
    parser.add_argument(
        "--match-trades",
        type=TradeMatching,
        choices=list(TradeMatching),
        default=TradeMatching.ALL,
        help="which market trades leftover orders can fill against: at the order's price or worse (all), "
        "strictly worse (worse), or none (default: all)",
    )
    parser.add_argument(
        "--resting",
        action="store_true",
        help="unfilled orders rest on the book until filled or cancelled, with a queue model "
        "(default: they're cancelled at the end of each tick, as in Prosperity; always on for a format whose orders rest)",
    )
    parser.add_argument(
        "--queue",
        type=QueueModel,
        choices=list(QueueModel),
        default=QueueModel.BACK,
        help="with --resting, where other orders' cancellations at your price fall: always behind you (back), "
        "split by your place in the queue (prob, see --queue-power), or everyone re-posts behind you every tick "
        "(front) (default: back)",
    )
    parser.add_argument(
        "--queue-power",
        type=float,
        default=1.0,
        help="--queue prob: a cancellation lands ahead of you with probability x**N, x your share of the queue "
        "ahead; 1 is uniform, a large N tends to back (default: 1)",
    )
    parser.add_argument(
        "--fill-ratio",
        type=float,
        default=1.0,
        help="share of book and market-trade volume available to you; below 1 approximates other teams "
        "competing for the same fills (default: 1)",
    )
    parser.add_argument("--seed", type=int, default=0, help="seed for --fill-ratio draws (default: 0)")
    parser.add_argument(
        "--set",
        dest="overrides",
        action="append",
        default=[],
        metavar="PATH=VALUE",
        help="override a bot global, e.g. --set PARAMS.KELP.make_edge=2 (repeatable)",
    )


def add_rival_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--vs",
        dest="rivals",
        type=Path,
        action="append",
        default=[],
        metavar="BOT",
        help="another bot trading in the same market: it competes for the same fills and can trade with yours. "
        "Repeatable; give a file twice for two copies. --set only applies to your bot.",
    )
    parser.add_argument(
        "--requote",
        action="store_true",
        help="the rivals cancel all their resting orders before every tick, as bots written for orders that live one "
        "tick (Prosperity's) expect; use it with --resting",
    )


def setup(args: argparse.Namespace) -> Setup:
    fmt = FORMATS[args.format]
    days = fmt.load_days(fmt.resolve_data_dir(args.data), args.days)
    config = EngineConfig(
        trade_matching=args.match_trades,
        resting=args.resting or getattr(fmt, "RESTING", False),  # a format whose orders rest runs that way
        queue=args.queue,
        queue_power=args.queue_power,
        fill_ratio=args.fill_ratio,
        seed=args.seed,
    )
    overrides = dict(parse_override(text) for text in args.overrides)
    return Setup(fmt, days, config, overrides, getattr(args, "rivals", []), getattr(args, "requote", False), getattr(args, "engine", "python"))


def participant_names(bot: Path, rivals: list[Path]) -> list[str]:
    """File stems, numbered from the second copy on: template, template#2, other."""
    seen: Counter[str] = Counter()
    names = []
    for path in [bot, *rivals]:
        seen[path.stem] += 1
        names.append(path.stem if seen[path.stem] == 1 else f"{path.stem}#{seen[path.stem]}")
    return names


def run_with_rivals(
    fmt,
    day: Day,
    bot: Path,
    overrides: dict[str, object],
    rivals: list[Path],
    config: EngineConfig,
    strict: bool = True,
    requote: bool = False,
) -> list[DayResult]:
    """Runs the bot, plus any rivals in the same market. The bot's result comes first."""
    others = [fmt.load_bot(rival, {}, strict) for rival in rivals]
    if requote:
        others = [Requote(other) for other in others]
    bots = [fmt.load_bot(bot, overrides, strict), *others]
    return run_market(day, list(zip(participant_names(bot, rivals), bots)), config)


class Requote:
    """Cancels all of a bot's resting orders before each tick, and hides them from it.

    Bots written for orders that live one tick (Prosperity's) never cancel: under --resting their
    orders pile up until the limit check rejects everything. Wrapped, each tick's orders replace
    the last tick's, which is how they were meant to run, though they keep their queue place only
    for that tick.
    """

    def __init__(self, bot):
        self.bot = bot

    def step(self, tick, positions, own_fills, market_trades, open_orders):
        actions = self.bot.step(tick, positions, own_fills, market_trades, [])
        return [Cancel(order.id) for order in open_orders] + [a for a in actions if not isinstance(a, Cancel)]
