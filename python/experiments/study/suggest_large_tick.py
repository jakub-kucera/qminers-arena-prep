"""Should `arena.diagnose --suggest` stop quoting a large-tick product that trends?

usage (from the repo root; the rehearsal round's data rebuilt first, python/experiments/mock_round/round2/README.md):
  uv run python -m experiments.study.suggest_large_tick

In the 2026-10-28 rehearsal (the Halden round), --suggest quoted both sides of VANTA, a large-tick future
that sits flat and then trends from a point that changes each session, and VANTA lost on every public
session. Two checks of the suggestion (join the best, make_edge 0.5) against taking only (make_size 0):
  - part 1: the round itself, the before-run's bot (results/before/template.py) with VANTA as suggested,
    take-only and off, scored by the round's portal on its public and hidden sessions;
  - part 2: arena.sim's LARGE_TICK preset, 10 days, with no regime change, a trend up, a trend down and a
    shift, per tick and resting, the suggestion read off such days by --suggest. On the Rust engine.
Part 2's suggestion is --suggest's own, read off ten trending LARGE_TICK days (seeds 0-9) each run, so the study
follows the rules as they are (the audit's round 8, R8). Results: IDEAS.md, "`arena.diagnose --suggest`" (read every
column: under replay worse the trends lose).
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

ROUND = Path("python/experiments/mock_round/round2")
VANTA = '    "VANTA": {"limit": 40, "fair": "wall_mid", "smoothing": 0.49, "make_edge": 0.5, "stop_loss": 625},'
TAKE_ONLY = ["--set", "PARAMS.LARGE_TICK.make_size=0"]


def _run(cmd: list[str]) -> str:
    return subprocess.run(["uv", "run", "python", *cmd], capture_output=True, text=True, check=True).stdout


def part1() -> None:
    print("Part 1: the Halden round's portal, the before-run's bot (credits)\n")
    print("| VANTA | public: VANTA | public: total | hidden: VANTA | hidden: total |\n|---|---|---|---|---|")
    source = (ROUND / "results" / "before" / "template.py").read_text()
    assert VANTA in source
    variants = {"as suggested": VANTA, "take only (make_size 0)": VANTA.replace('"stop_loss": 625}', '"stop_loss": 625, "make_size": 0}'),
                "off": '    "VANTA": {"limit": 0, "fair": "wall_mid", "make_size": 0},'}
    with tempfile.TemporaryDirectory() as scratch:
        for name, line in variants.items():
            bot = Path(scratch) / "bot.py"
            bot.write_text(source.replace(VANTA, line))
            cells = []
            for days in ("public", "hidden"):
                row = re.search(r"^all +(\S+) +(\S+) +(\S+) +(\S+) +(\S+)", _run([str(ROUND / "private" / "evaluate.py"), str(bot), "--days", days]), re.M)
                cells += [row.group(4), row.group(5)]
            print(f"| {name} | " + " | ".join(cells) + " |")
    print()


def suggested() -> tuple[list[str], list[str]]:
    """--suggest's PARAMS for LARGE_TICK off ten trend_up days, as --set arguments, and its reasons."""
    from arena import diagnose
    from arena.formats import FORMATS

    with tempfile.TemporaryDirectory() as folder:
        _run(["-m", "arena.sim", "generate", folder, "--products", "LARGE_TICK", "--regime", "trend_up", "--days", "10", "--seed", "0"])
        fmt = FORMATS["prosperity"]
        row = diagnose.diagnose(fmt.load_days(Path(folder), ["1"]))["LARGE_TICK"]
    params, why = diagnose.suggest(row)
    sets = [arg for key, value in params.items() if key != "limit" for arg in ("--set", f"PARAMS.LARGE_TICK.{key}={value}")]
    return sets, why


def part2() -> None:
    sets, why = suggested()
    print(f"Part 2: arena.sim's LARGE_TICK, 10 days (seeds 0-9), PnL; --suggest on trend_up days: {' '.join(sets[1::2])} ({'; '.join(why)})\n")
    print("| regime | mode | setting | replay all | replay worse | in the market |\n|---|---|---|---|---|---|")
    for regime in (None, "trend_up", "trend_down", "shift_up"):
        for resting in (False, True):
            for name, extra in (("as suggested", []), ("take only (make_size 0)", TAKE_ONLY)):
                cmd = ["-m", "arena.sim", "run", "python/bots/template.py", "--products", "LARGE_TICK", "--days", "10", "--engine", "rust", *sets, *extra]
                cmd += (["--regime", regime] if regime else []) + (["--resting"] if resting else [])
                row = re.findall(r"^  total +(-?[\d,]+) +(-?[\d,]+) +(-?[\d,]+) +(-?[\d,]+)", _run(cmd), re.M)[-1]
                print(f"| {regime or 'none'} | {'resting' if resting else 'per tick'} | {name} | {row[0]} | {row[1]} | {row[3]} |", flush=True)


def main() -> None:
    part1()
    part2()


if __name__ == "__main__":
    main()
