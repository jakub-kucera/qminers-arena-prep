"""Backtests a bot file on recorded data.

    uv run python -m arena.backtest bots/template.py 1              # every day of round 1
    uv run python -m arena.backtest bots/template.py 1-0 --data p2  # Prosperity 2 data
    uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2 --out results/
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from arena import report
from arena.botfile import OverrideError
from arena.cli import add_common_arguments, setup
from arena.engine import run_day


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arena.backtest", description="Backtest a bot file on recorded data.")
    add_common_arguments(parser)
    parser.add_argument("--out", type=Path, help="write <day>_timeline.csv and <day>_fills.csv to this folder")
    parser.add_argument("--print", action="store_true", help="show the bot's prints")
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="leave the bot's STRICT flag alone, so it handles its own exceptions as it would when submitted",
    )
    args = parser.parse_args(argv)

    try:
        s = setup(args)
        s.format.load_bot(args.bot, s.overrides, strict=True)  # fail fast on a bad path or --set
    except (ValueError, OSError, OverrideError) as error:
        parser.error(str(error))

    config = replace(s.config, capture_output=not args.print)
    results = []
    for day in s.days:
        bot = s.format.load_bot(args.bot, s.overrides, strict=not args.no_strict)
        result = run_day(day, bot, config)
        results.append(result)
        print(report.format_day(result), end="\n\n")
        if args.out:
            report.write_csvs(result, args.out)

    if len(results) > 1:
        print(report.format_overall(results))
    if args.out:
        print(f"CSVs written to {args.out}/")
    return 1 if any(r.errors for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
