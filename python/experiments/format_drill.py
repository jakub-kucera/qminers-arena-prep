"""Make drill-format data: simulated days written as the drill format's sessions.

usage (from the repo root): uv run python -m experiments.format_drill OUT [--seed 1000] [--days 3]
       uv run python -m experiments.format_drill --sync [FILE ...]

--sync copies DEFAULTS, STRATEGY and EXECUTION from python/bots/template.py into every format's
template, python/bots/<format>/template.py (the drill's, and on the day the Arena's, e.g.
python/bots/qminers/template.py), or into the FILEs given. python/tests/test_drill.py requires it
after any change to them, for every such file.

Runs `arena.sim generate` into OUT/prosperity (the presets, in the Prosperity layout), then writes
round 1 as drill sessions into OUT/drill (`arena.formats.drill.convert`): ALPHA is KELP at 0.05 a
tick, BETA RAINFOREST_RESIN at 0.01, GAMMA SQUID_INK at 0.25, prices in decimals. Then, e.g.:

    uv run python -m arena.diagnose all --format drill --data OUT/drill
    uv run python -m arena.backtest python/bots/drill/template.py all --format drill --data OUT/drill

The format drill used seeds 1000-1002: don't give the mock round these.
"""

import argparse
import sys
from pathlib import Path

from arena import sim
from arena.formats import drill


TEMPLATE, DRILL = Path("python/bots/template.py"), Path("python/bots/drill/template.py")


def format_templates() -> list[Path]:
    """Every format's copy of the template: python/bots/<format>/template.py."""
    return sorted(TEMPLATE.parent.glob("*/template.py"))
STRATEGY, ADAPTER = "# " + "-" * 78 + " STRATEGY", "# " + "-" * 78 + " ADAPTER"


def _defaults(text: str) -> tuple[int, int]:
    start = text.index("DEFAULTS = {")
    return start, text.index("\n}\n", start) + 3


def sync(path: Path = DRILL) -> None:
    """Copies DEFAULTS and everything from STRATEGY to ADAPTER from the template into a format's copy."""
    source, target = TEMPLATE.read_text(), path.read_text()
    (a, b), (c, d) = _defaults(source), _defaults(target)
    target = target[:c] + source[a:b] + target[d:]
    core = source[source.index(STRATEGY) : source.index(ADAPTER)]
    target = target[: target.index(STRATEGY)] + core + target[target.index(ADAPTER) :]
    path.write_text(target)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, nargs="*", help="the folder to write (or, with --sync, the templates to sync)")
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--sync", action="store_true",
                        help="copy the template's DEFAULTS, STRATEGY and EXECUTION into every python/bots/<format>/template.py, or the files given")
    args = parser.parse_args(argv)
    if args.sync:
        for path in args.out or format_templates():
            sync(path)
            print(f"copied DEFAULTS, STRATEGY and EXECUTION from {TEMPLATE} into {path}")
        return 0
    if len(args.out) != 1:
        parser.error("give one OUT folder, or --sync")
    args.out = args.out[0]
    spec = sim.preset_market()
    for k in range(args.days):
        sim.write_day(sim.run(spec, args.seed + k), args.out / "prosperity", 1, k)
    for path in drill.convert(args.out / "prosperity", 1, args.out / "drill"):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
