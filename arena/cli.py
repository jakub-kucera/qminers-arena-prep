"""Command-line options shared by arena.backtest, arena.validate and arena.grid."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from arena.botfile import parse_override
from arena.engine import DayResult, EngineConfig, TradeMatching, run_market
from arena.formats import FORMATS
from arena.model import Day


@dataclass
class Setup:
    format: ModuleType
    days: list[Day]
    config: EngineConfig
    overrides: dict[str, object]
    rivals: list[Path] = field(default_factory=list)  # bots trading in the same market (--vs)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("bot", type=Path, help="bot file")
    parser.add_argument("days", nargs="+", help="days to replay: ROUND for all its days, or ROUND-DAY (e.g. 1, 1-0, 1--1)")
    parser.add_argument("--format", default="prosperity", choices=sorted(FORMATS), help="competition format (default: prosperity)")
    parser.add_argument("--data", default="p3", help="data folder, or p2 / p3 for the Prosperity data in references/ (default: p3)")
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
        "(default: they're cancelled at the end of each tick, as in Prosperity)",
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


def setup(args: argparse.Namespace) -> Setup:
    fmt = FORMATS[args.format]
    days = fmt.load_days(fmt.resolve_data_dir(args.data), args.days)
    config = EngineConfig(
        trade_matching=args.match_trades, resting=args.resting, fill_ratio=args.fill_ratio, seed=args.seed
    )
    overrides = dict(parse_override(text) for text in args.overrides)
    return Setup(fmt, days, config, overrides, getattr(args, "rivals", []))


def participant_names(bot: Path, rivals: list[Path]) -> list[str]:
    """File stems, numbered from the second copy on: template, template#2, other."""
    seen: Counter[str] = Counter()
    names = []
    for path in [bot, *rivals]:
        seen[path.stem] += 1
        names.append(path.stem if seen[path.stem] == 1 else f"{path.stem}#{seen[path.stem]}")
    return names


def run_with_rivals(
    fmt, day: Day, bot: Path, overrides: dict[str, object], rivals: list[Path], config: EngineConfig, strict: bool = True
) -> list[DayResult]:
    """Runs the bot, plus any rivals in the same market. The bot's result comes first."""
    bots = [fmt.load_bot(bot, overrides, strict)] + [fmt.load_bot(rival, {}, strict) for rival in rivals]
    return run_market(day, list(zip(participant_names(bot, rivals), bots)), config)
