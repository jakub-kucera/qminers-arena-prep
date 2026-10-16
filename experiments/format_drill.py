"""Make drill-format data: simulated days written as the drill format's sessions.

usage (from the repo root): uv run python -m experiments.format_drill OUT [--seed 1000] [--days 3]

Runs `arena.sim generate` into OUT/prosperity (the presets, in the Prosperity layout), then writes
round 1 as drill sessions into OUT/drill (`arena.formats.drill.convert`): ALPHA is KELP at 0.05 a
tick, BETA RAINFOREST_RESIN at 0.01, GAMMA SQUID_INK at 0.25, prices in decimals. Then, e.g.:

    uv run python -m arena.diagnose all --format drill --data OUT/drill
    uv run python -m arena.backtest bots/drill/template.py all --format drill --data OUT/drill

The format drill used seeds 1000-1002: don't give the mock round these.
"""

import argparse
import sys
from pathlib import Path

from arena import sim
from arena.formats import drill


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--days", type=int, default=3)
    args = parser.parse_args(argv)
    spec = sim.preset_market()
    for k in range(args.days):
        sim.write_day(sim.run(spec, args.seed + k), args.out / "prosperity", 1, k)
    for path in drill.convert(args.out / "prosperity", 1, args.out / "drill"):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
