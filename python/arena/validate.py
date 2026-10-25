"""Checks a bot file before submission.

    uv run python -m arena.validate python/bots/template.py 1
    uv run python -m arena.validate python/bots/template.py 1 --allow numpy --time-limit-ms 900

Static checks: the file parses and defines the competition's entry point, imports only the
standard library (plus --allow and the modules the competition provides), and doesn't use
environment variables, files, processes or the network, which the submission environment
probably won't have.

Replay checks on the given days: no exceptions, well-formed orders, no orders cancelled for
breaching a position limit, and no tick slower than --time-limit-ms. The first day is then
replayed again: once to check the results repeat exactly, twice in other Python processes with
other hash seeds (PYTHONHASHSEED), which catches a bot that iterates a set of strings, so that the
organisers' rerun wouldn't reproduce it, once reloading the bot every tick, which shows whether it
relies on state the real engine might not keep between calls, and once with STRICT off, as
submitted, to check that no exception escapes its own error handling.

Exits with 1 if any check fails.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import os
import statistics
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

from arena import report
from arena.botfile import OverrideError
from arena.cli import Setup, add_common_arguments, setup
from arena.engine import run_day

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"

RISKY_MODULES = {"subprocess", "socket", "urllib", "http", "requests"}
HASH_SEEDS = ("1", "2")  # PYTHONHASHSEED of the two other processes the first day is replayed in


@dataclass(frozen=True)
class Check:
    status: str
    message: str


def static_checks(source: str, fmt, allow: set[str]) -> tuple[list[Check], bool]:
    """Returns the checks, and whether the file is sound enough to replay."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [Check(FAIL, f"syntax error: {error}")], False

    checks = []
    problems = fmt.check_source(tree)
    if problems:
        checks.append(Check(FAIL, "entry point: " + "; ".join(problems)))
    else:
        checks.append(Check(PASS, "parses and defines the entry point"))

    imported = _imported_modules(tree)
    outside = sorted(
        m for m in imported if m not in sys.stdlib_module_names and m not in fmt.PROVIDED_MODULES and m not in allow
    )
    if outside:
        checks.append(
            Check(FAIL, f"imports outside the standard library: {', '.join(outside)} (--allow them if the competition does)")
        )
    else:
        checks.append(Check(PASS, f"imports: {', '.join(sorted(imported)) or 'none'}"))

    risky = _risky_uses(tree, imported)
    if risky:
        checks.append(Check(WARN, f"uses {', '.join(risky)}: probably unavailable when submitted"))
    else:
        checks.append(Check(PASS, "no environment variables, files, processes or network"))

    return checks, not problems


def replay_checks(path: Path, s: Setup, time_limit_ms: float, argv: list[str] | None = None) -> list[Check]:
    """argv, this run's arguments, lets the first day be replayed in other processes (hash_seed_check)."""
    results, bots = [], []
    for day in s.days:
        bot = s.format.load_bot(path, s.overrides, strict=True)
        results.append(run_day(day, bot, s.config))
        bots.append(bot)

    checks = []
    ticks = sum(len(r.timestamps) for r in results)
    errors = [(r.day, timestamp, error) for r in results for timestamp, error in r.errors]
    if errors:
        day, timestamp, error = errors[0]
        checks.append(
            Check(FAIL, f"{len(errors)} errors in {ticks:,} ticks; first on {day} at {timestamp}:\n{_indent(error)}")
        )
    else:
        checks.append(Check(PASS, f"no errors in {ticks:,} ticks"))

    breaches = [(r.day, timestamp, product) for r in results for timestamp, product in r.limit_breaches]
    if breaches:
        day, timestamp, product = breaches[0]
        checks.append(
            Check(
                FAIL,
                (f"{len(breaches)} ticks over a position limit (--limit-penalty charges each); " if s.config.limit_penalty is not None
                 else f"{len(breaches)} times orders were cancelled for breaching a position limit; ")
                + f"first {product} on {day} at {timestamp}",
            )
        )
    else:
        checks.append(Check(PASS, "orders never breach a position limit"))

    step_ms = [seconds * 1000 for r in results for seconds in r.step_seconds]
    slowest = max(step_ms, default=0.0)
    checks.append(
        Check(
            FAIL if slowest > time_limit_ms else PASS,
            f"slowest tick {slowest:.1f} ms (limit {time_limit_ms:g} ms), mean {statistics.fmean(step_ms or [0]):.2f} ms",
        )
    )

    first, baseline = s.days[0], results[0].fills
    repeat = run_day(first, s.format.load_bot(path, s.overrides, strict=True), s.config)
    if repeat.fills == baseline:
        checks.append(Check(PASS, f"same fills when {first.name} is replayed again"))
    else:
        checks.append(Check(WARN, "fills differ on a repeat run: the bot isn't deterministic (clock, randomness, set order?)"))
    if argv is not None:
        checks.append(hash_seed_check(argv, fills_digest(baseline), first.name))

    fresh = run_day(first, s.format.load_bot(path, s.overrides, strict=True, fresh_each_tick=True), s.config)
    if fresh.fills == baseline:
        checks.append(Check(PASS, "same fills when the bot is reloaded every tick"))
    else:
        checks.append(
            Check(
                WARN,
                "fills change when the bot is reloaded every tick: it keeps state in instance or module "
                "variables, which the real engine may not preserve between calls",
            )
        )

    # The replays above set STRICT, so a bot's own error handling never ran. Run it as submitted.
    lenient = run_day(first, s.format.load_bot(path, s.overrides, strict=False), s.config)
    if lenient.errors:
        timestamp, error = lenient.errors[0]
        checks.append(
            Check(
                FAIL,
                f"{len(lenient.errors)} exceptions escaped the bot with STRICT off (as submitted); first at {timestamp}:\n"
                f"{_indent(error)}",
            )
        )
    else:
        checks.append(Check(PASS, f"no exception escapes the bot with STRICT off on {first.name}"))

    pnl = " · ".join(f"{r.day} {(report.total_pnl(r) or [0])[-1]:,.0f}" for r in results)
    state = max((getattr(bot, "max_state_chars", 0) for bot in bots), default=0)
    output = max(r.max_output_chars for r in results)
    checks.append(Check(INFO, f"pnl: {pnl}"))
    checks.append(Check(INFO, f"largest state {state:,} chars, largest print per tick {output:,} chars"))
    return checks


def conflict_checks(path: Path, s: Setup) -> list[Check]:
    """A WARN for each setting the bot itself says can't matter, if it says (the template's
    param_conflicts(product): a second target mode, a target a mode replaces, a mode's own setting
    while the mode is off)."""
    s.format.load_bot(path, s.overrides, strict=True)
    module = sys.modules.get(f"arena_bot_{Path(path).stem}")  # BotFile.load registers the module under this name
    conflicts, params = getattr(module, "param_conflicts", None), getattr(module, "PARAMS", None)
    if not callable(conflicts) or not isinstance(params, dict):
        return []
    found = [f"{product}: {reason}" for product in params for reason in conflicts(product)]
    if not found:
        return [Check(PASS, "no setting in PARAMS is overridden by another or left without its mode")]
    return [Check(WARN, "settings that can't matter: " + "; ".join(found))]


def fills_digest(fills) -> str:
    return hashlib.sha256(repr(fills).encode()).hexdigest()


def hash_seed_check(argv: list[str], digest: str, day: str) -> Check:
    """The first day's fills in two other Python processes, with other PYTHONHASHSEEDs, against
    this process's. A repeat in one process can't see a dependence on the hash seed: set and dict
    order of strings stay the same there, and change between processes."""
    found = []
    for seed in HASH_SEEDS:
        out = subprocess.run([sys.executable, "-m", "arena.validate", *argv, "--fills-digest"], capture_output=True, text=True,
                             env={**os.environ, "PYTHONHASHSEED": seed})
        if out.returncode != 0:
            last = (out.stderr.strip().splitlines() or ["no output"])[-1]
            return Check(WARN, f"couldn't replay {day} in another Python process: {last}")
        found.append(out.stdout.split()[-1])
    if all(other == digest for other in found):
        return Check(PASS, f"same fills when {day} is replayed in other Python processes (PYTHONHASHSEED {', '.join(HASH_SEEDS)})")
    return Check(WARN, "fills differ between Python processes with other hash seeds: the bot depends on the order of a set of "
                 "strings (or something built from one), so a rerun by the organisers may not reproduce its result")


def _imported_modules(tree: ast.Module) -> set[str]:
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return modules


def _risky_uses(tree: ast.Module, imported: set[str]) -> list[str]:
    found = {module for module in imported if module in RISKY_MODULES}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
            and node.attr in {"environ", "getenv"}
        ):
            found.add(f"os.{node.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            found.add("open()")
    return sorted(found)


def _indent(text: str) -> str:
    return textwrap.indent(text.rstrip(), "        ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arena.validate", description="Check a bot file before submitting it.")
    add_common_arguments(parser)
    parser.add_argument("--allow", default="", help="comma-separated non-standard-library modules the competition allows")
    parser.add_argument("--time-limit-ms", type=float, default=900, help="slowest allowed tick (default: 900, Prosperity's limit)")
    parser.add_argument("--fills-digest", action="store_true", help=argparse.SUPPRESS)  # hash_seed_check's other processes
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parser.parse_args(argv)
    if args.fills_digest:
        s = setup(args)
        print(fills_digest(run_day(s.days[0], s.format.load_bot(args.bot, s.overrides, strict=True), s.config).fills))
        return 0

    try:
        s = setup(args)
        source = args.bot.read_text(encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.error(str(error))

    allow = {module.strip() for module in args.allow.split(",") if module.strip()}
    print(f"Validating {args.bot} on {', '.join(day.name for day in s.days)} ({args.format} format)")
    checks, replayable = static_checks(source, s.format, allow)
    if replayable:
        try:
            checks += replay_checks(args.bot, s, args.time_limit_ms, argv)
            checks += conflict_checks(args.bot, s)
        except OverrideError as error:
            parser.error(str(error))
        except Exception as error:  # the bot failed while loading, before any tick ran
            checks.append(Check(FAIL, f"bot failed to load: {type(error).__name__}: {error}"))

    for check in checks:
        print(f"  {check.status}  {check.message}")
    failed = any(check.status == FAIL for check in checks)
    print("Result: FAILED" if failed else "Result: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
