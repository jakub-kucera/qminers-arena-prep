"""Make drill-format data: simulated days written as the drill format's sessions.

usage (from the repo root): uv run python -m experiments.format_drill OUT [--seed 1000] [--days 3]
       uv run python -m experiments.format_drill --sync

--sync copies DEFAULTS, STRATEGY and EXECUTION from python/bots/template.py into python/bots/drill/template.py,
which python/tests/test_drill.py requires after any change to them.

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
STRATEGY, ADAPTER = "# " + "-" * 78 + " STRATEGY", "# " + "-" * 78 + " ADAPTER"


def _defaults(text: str) -> tuple[int, int]:
    start = text.index("DEFAULTS = {")
    return start, text.index("\n}\n", start) + 3


def sync() -> None:
    """Copies DEFAULTS and everything from STRATEGY to ADAPTER from the template into the drill bot."""
    source, target = TEMPLATE.read_text(), DRILL.read_text()
    (a, b), (c, d) = _defaults(source), _defaults(target)
    target = target[:c] + source[a:b] + target[d:]
    core = source[source.index(STRATEGY) : source.index(ADAPTER)]
    target = target[: target.index(STRATEGY)] + core + target[target.index(ADAPTER) :]
    DRILL.write_text(target)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, nargs="?")
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--sync", action="store_true", help="copy the template's DEFAULTS, STRATEGY and EXECUTION into the drill bot")
    args = parser.parse_args(argv)
    if args.sync:
        sync()
        print(f"copied DEFAULTS, STRATEGY and EXECUTION from {TEMPLATE} into {DRILL}")
        return 0
    if args.out is None:
        parser.error("give OUT, or --sync")
    spec = sim.preset_market()
    for k in range(args.days):
        sim.write_day(sim.run(spec, args.seed + k), args.out / "prosperity", 1, k)
    for path in drill.convert(args.out / "prosperity", 1, args.out / "drill"):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
