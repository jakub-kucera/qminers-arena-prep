"""Backtests a bot file on recorded data.

    uv run python -m arena.backtest bots/template.py 1              # every day of round 1
    uv run python -m arena.backtest bots/template.py 1-0 --data p2  # Prosperity 2 data
    uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2 --out results/
    uv run python -m arena.backtest bots/template.py 1 --vs bots/template.py   # against a copy of itself
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from arena import report
from arena.botfile import OverrideError
from arena.cli import add_common_arguments, add_rival_argument, participant_names, run_with_rivals, setup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arena.backtest", description="Backtest a bot file on recorded data.")
    add_common_arguments(parser)
    add_rival_argument(parser)
    parser.add_argument("--out", type=Path, help="write <day>_timeline.csv, _fills.csv and _orders.csv to this folder")
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
        for rival in s.rivals:
            s.format.load_bot(rival, {}, strict=True)
    except (ValueError, OSError, OverrideError) as error:
        parser.error(str(error))

    config = replace(s.config, capture_output=not args.print)
    names = participant_names(args.bot, s.rivals)
    results, rival_results = [], []
    for day in s.days:
        result, *rivals = run_with_rivals(s.format, day, args.bot, s.overrides, s.rivals, config, strict=not args.no_strict, requote=s.requote)
        results.append(result)
        rival_results.append(rivals)
        print(report.format_day(result))
        if rivals:
            print(report.format_rivals(names[1:], rivals))
        print()
        if args.out:
            report.write_csvs(result, args.out)

    if len(results) > 1:
        print(report.format_overall(results))
        if s.rivals:
            totals = [sum((report.total_pnl(day[k]) or [0.0])[-1] for day in rival_results) for k in range(len(s.rivals))]
            print("  rivals: " + " · ".join(f"{name} {total:,.0f}" for name, total in zip(names[1:], totals)))
    if args.out:
        print(f"CSVs written to {args.out}/")
    return 1 if any(r.errors for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
