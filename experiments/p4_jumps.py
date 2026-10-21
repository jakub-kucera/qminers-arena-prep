"""Fading jumps that snap back: where they are in the data, and the template's jump mode on every product.

usage (from the repo root): uv run python -m experiments.p4_jumps [--jobs N] [--data p4] [--days 5] [--jump-min 50] [--engine rust]

In P4 round 5 some products' wall mids sat on multiples of 100 and moved in steps of 100 that
mostly went straight back (references/wiki/concepts/jumps-and-snap-back.md). The teams' Robots
PnL in IDEAS.md's benchmark is almost all one product on one day: ROBOT_DISHES on day 4 made 280k
for DU (`round5.py`, hold 3 ticks) and 437k for Baguette Fromage (`Phase2_Final.py`, hold until the
next jump); `uv run python -m arena.backtest <their file> 5 --data p4` prints it.

1. Per product and day, the wall mid's jumps: moves of at least --jump-min. How many, the share
   that went the opposite way to the jump before, the share of ticks on a multiple of 100, the
   median spread, and the best case for fading: holding one unit against each jump until the next,
   at the wall mid with no spread paid. Rows with at least 20 jumps. Only this part runs with --data
   other than p4 round 5, e.g. `--data p3 --days 1 2 3 4 5` to look for the effect elsewhere.
2. The template on every product (limit 10, plain market making around wall_mid with make_edge 1,
   as in the benchmark), with the jump mode switched on everywhere at the settings chosen here
   (DEFAULT_JUMP), then one setting changed at a time, and the default under `worse` fills and
   --resting. Each is compared with plain market making per day; the jump mode is meant to run on
   every product, so the cost where there are no jumps counts as much as the gain where there are.
   Under --resting both the plain run and the jump mode only take (make_size 0): arena.diagnose
   says "if orders rest, take only" for every round 5 product, because the wall mid jumps past
   half the spread on half the ticks or more, and full-room quotes resting there lose about 19
   million a day (`uv run python -m arena.backtest bots/template.py 5-2 --data p4 --resting --set
   'PARAMS={"PEBBLES_XL": {"limit": 10, "fair": "wall_mid", "make_edge": 1}}'`: -1.7 million).
"""

import argparse
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import rust
from arena.cli import backtest
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS
from experiments.p4_vouchers import series

FMT = FORMATS["prosperity"]
TEMPLATE = Path("bots/template.py")
PLAIN = {"limit": 10, "fair": "wall_mid", "make_edge": 1}
DEFAULT_JUMP = {"jump_min": 50, "jump_hold": None, "jump_edge": 10, "jump_seen": 5, "jump_share": 0.6}
SWEEP = {
    "jump_min": [30, 80],
    "jump_hold": [3, 10, 50],
    "jump_edge": [5, 20],
    "jump_seen": [0, 2, 10, 20],
    "jump_share": [0, 0.5, 0.7, 0.8],
}
MODES = {
    "default": EngineConfig(),
    "worse": EngineConfig(trade_matching=TradeMatching.WORSE),
    "resting": EngineConfig(resting=True),
}
_DAYS = {}
ENGINE = ["python"]  # set in each worker by _init (--engine)


def jump_stats(day, product: str, jump_min: float) -> dict | None:
    """Part 1 for one product and day; None if it never had a price."""
    rows = series(day, product)
    walls = [w for _, w, _ in rows]
    spreads = [s for _, _, s in rows if s is not None]
    if not spreads:
        return None
    jumps = []  # (tick, wall mid after, signed move)
    last = None
    for i, w in enumerate(walls):
        if w is None:
            continue
        if last is not None and abs(w - last) >= jump_min:
            jumps.append((i, w, w - last))
        last = w
    pairs = list(zip(jumps, jumps[1:]))
    reversed_ = sum(1 for (_, _, a), (_, _, b) in pairs if a * b < 0)
    # One unit held against each jump, from the wall mid after it to the wall mid after the next.
    fade = sum(-(1 if a > 0 else -1) * (w_next - w) for (_, w, a), (_, w_next, _) in pairs)
    valid = [w for w in walls if w is not None]
    return {
        "jumps": len(jumps),
        "reversed": reversed_ / len(pairs) if pairs else None,
        "round100": sum(1 for w in valid if w % 100 == 0) / len(valid),
        "spread": st.median(spreads),
        "fade": fade,
    }


def _init(data, days, engine="python"):
    ENGINE[0] = engine
    _DAYS.update({d.name: d for d in FMT.load_days(FMT.resolve_data_dir(data), days)})


def _run(job):
    variant, jump, mode, day_name = job
    day = _DAYS[day_name]
    base = {**PLAIN, "make_size": 0} if mode == "resting" else PLAIN
    params = {p: {**base, **dict(jump)} for p in day.products}
    (result,) = backtest(day, [("you", TEMPLATE, {"PARAMS": params}, False)], MODES[mode], ENGINE[0], True, ("pnl", "errors", "breaches"))
    pnl = {p: s[-1] for p, s in result.pnl.items() if s}
    return job, (pnl, len(result.limit_breaches) + len(result.errors))


def variants() -> list[tuple[str, tuple]]:
    """(label, jump settings as a hashable tuple) for part 2; the plain run has no settings."""
    out = [("plain", ()), ("default", tuple(DEFAULT_JUMP.items()))]
    for key, values in SWEEP.items():
        out += [(f"{key} {v}", tuple({**DEFAULT_JUMP, key: v}.items())) for v in values]
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--data", default="p4")
    parser.add_argument("--days", nargs="+", default=["5"])
    parser.add_argument("--jump-min", type=float, default=DEFAULT_JUMP["jump_min"])
    parser.add_argument("--engine", choices=("python", "rust"), default="python", help="run the backtests in rust/ (the same results)")
    args = parser.parse_args(argv)
    if args.engine == "rust":
        rust.build()
    _init(args.data, args.days)
    names = list(_DAYS)

    print(f"1. jumps of at least {args.jump_min:g} in the wall mid, products with 20 or more on a day")
    print(f"   {'day':<6} {'product':<30} {'jumps':>6} {'reversed':>9} {'on 100s':>8} {'spread':>7} {'fade/unit':>10}")
    for name in names:
        day = _DAYS[name]
        for product in day.products:
            s = jump_stats(day, product, args.jump_min)
            if s and s["jumps"] >= 20:
                rev = f"{s['reversed']:.0%}" if s["reversed"] is not None else "-"
                print(f"   {name:<6} {product:<30} {s['jumps']:>6} {rev:>9} {s['round100']:>8.0%} "
                      f"{s['spread']:>7g} {s['fade']:>10,.0f}")
    if (args.data, args.days) != ("p4", ["5"]):
        return 0

    runs = variants()
    jobs = [(label, jump, "default", n) for label, jump in runs for n in names]
    jobs += [(label, jump, mode, n) for label, jump in runs[:2] for mode in ("worse", "resting") for n in names]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.data, args.days, args.engine)) as pool:
        out = dict(pool.map(_run, jobs))

    def totals(label, jump, mode):
        return [sum(out[(label, jump, mode, n)][0].values()) for n in names]

    print("\n2. the template on every product, PnL per day in thousands (change against plain market making;")
    print("   under --resting, against taking only)")
    print(f"   {'variant':<18} {'mode':<8} " + " ".join(f"{n:>17}" for n in names) + f" {'total':>17} {'worst day':>10}")
    rows = [(label, jump, "default") for label, jump in runs]
    rows[2:2] = [(label, jump, mode) for label, jump in runs[:2] for mode in ("worse", "resting")]
    for label, jump, mode in rows:
        pnl = totals(label, jump, mode)
        base = totals("plain", (), mode)
        diff = [a - b for a, b in zip(pnl, base)]
        cells = [f"{a / 1000:>8.1f} ({d / 1000:>+6.1f})" for a, d in zip(pnl, diff)]
        issues = sum(out[(label, jump, mode, n)][1] for n in names)
        print(f"   {label:<18} {mode:<8} " + " ".join(cells) + f" {sum(pnl) / 1000:>8.1f} ({sum(diff) / 1000:>+6.1f})"
              f" {min(diff) / 1000:>+10.1f}" + (f"  ! {issues} errors or breaches" if issues else ""))

    default = tuple(DEFAULT_JUMP.items())
    print("\n   the default's change against plain market making by product and day, where above 1k:")
    for n in names:
        plain, jump = out[("plain", (), "default", n)][0], out[("default", default, "default", n)][0]
        moved = sorted(((jump.get(p, 0.0) - plain.get(p, 0.0), p) for p in set(plain) | set(jump)), reverse=True)
        print(f"   {n}: " + ", ".join(f"{p} {d / 1000:+.1f}" for d, p in moved if abs(d) > 1000))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
