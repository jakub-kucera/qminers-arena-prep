"""Command-line options shared by arena.backtest and arena.validate."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from arena.botfile import parse_override
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS
from arena.model import Day


@dataclass
class Setup:
    format: ModuleType
    days: list[Day]
    config: EngineConfig
    overrides: dict[str, object]


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


def setup(args: argparse.Namespace) -> Setup:
    fmt = FORMATS[args.format]
    days = fmt.load_days(fmt.resolve_data_dir(args.data), args.days)
    config = EngineConfig(trade_matching=args.match_trades, fill_ratio=args.fill_ratio, seed=args.seed)
    overrides = dict(parse_override(text) for text in args.overrides)
    return Setup(fmt, days, config, overrides)
