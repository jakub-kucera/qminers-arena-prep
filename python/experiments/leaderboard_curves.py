"""Reading the leaderboard's PnL curves: did each team trade alone, on the same data, or in one
shared market?

usage (from the repo root): uv run python -m experiments.leaderboard_curves --engine rust [--jobs N]
       uv run python -m experiments.leaderboard_curves --read FILE [--team NAME]

After each round's deadline the portal's leaderboard holds every team's PnL curve from the private
run, on one time axis in seconds (ON_THE_DAY.md, "Known so far"). Whether the market is shared is
the largest unknown about the Arena, and the playground may not settle it if only the private run
is shared. The curves can, from how pairs of teams' PnL changes move together (`read_curves`):
  1. Co-movement: T × the mean squared correlation over every pair of moving curves (T changes
     each), as a multiple of the same with each curve shifted in time by its own random offset,
     which keeps each curve's own pattern and destroys only their timing. Near 1: the curves don't
     move together, so each team traded data of its own.
  2. If they do, the balance of signs. Teams alone on the same data meet the same prices and the
     same takers, so most pairs move together (a positive mean). In one market a fill one team
     gets is a fill another misses, so as many pairs move against each other as with (a mean near 0).
  3. Identical curves that move: the same bot run alone on the same data, twice. In one market the
     two would split the fills.

Without --read it calibrates that rule on fields where the answer is known: the template and a copy
of it (two teams submitting the same bot), every bot in python/bots/zoo/, and python/bots/mm.py at
make_edge 0.5, 1 and 2, then the same without the zoo's local models (python/bots/zoo/local.py),
in five cases:
  - replay, shared: all in one market, per tick, on P3 round 1's three days (arena.engine);
  - replay, alone: each alone on the same days;
  - sim, shared: all inside arena.sim's market, seeds 0-2;
  - sim, alone: each alone in that market with the same seed;
  - sim, own seed: each alone with a seed of its own.
Each curve is sampled every 10, 100 and 500 ticks (T = 999, 99 and 19 changes a day). It prints
the statistics per case and whether the rule names the case right. Results go into IDEAS.md
("Reading the leaderboard's curves").

--read FILE: the leaderboard's data as the page receives it, a JSON list with one entry per team
({teamName, rank, isTie, pnl, pnlSeries: [{elapsedS, pnl}]}; ON_THE_DAY.md says how to save it).
It prints the standing, and the rule's verdict on the curves.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import itertools
import json
import math
import random
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from operator import mul
from pathlib import Path

from arena import rust, sim
from arena.cli import add_engine_argument, backtest, backtest_days
from arena.engine import EngineConfig
from arena.formats import prosperity
from experiments.zoo import TEMPLATE, is_local, label, zoo_bots

MM = Path("python/bots/mm.py")
DATA, DAYS = "p3", ["1"]
SEEDS = (0, 1, 2)
OWN_SEEDS = 100  # each bot's own seed in "sim, own seed": OWN_SEEDS * (seed + 1) + its index
STEPS = (10, 100, 500)
TICKS = None  # arena.sim's ticks a day (None: its preset's 10,000); the tests shorten it
SHIFTS = 20  # random time shifts behind the co-movement's baseline
CO_MOVEMENT = 1.5  # below: the curves don't move together (data of each team's own reached 1.2 in the calibration)
MEAN = 0.04  # a mean pair correlation at or above this, with SIGNS times more pairs with than against, is one sign
SIGNS = 2.0
FLAT = 1e-9  # a curve whose changes vary less than this doesn't move
ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})


# ---------------------------------------------------------------------------- the statistics


@dataclass
class Reading:
    teams: int  # curves that move
    changes: int  # T, each curve's changes
    mean: float  # the mean pair correlation
    co_movement: float  # T x the mean squared pair correlation, over the same for shifted curves
    together: float  # the share of pairs correlated above 2 / sqrt(T)
    against: float  # ... and below -2 / sqrt(T)
    twins: list[tuple[str, str]] = field(default_factory=list)  # pairs of identical moving curves
    verdict: str = ""


def _standardised(values: list[float]) -> list[float] | None:
    spread = statistics.pstdev(values)
    if spread <= FLAT:
        return None
    mean = statistics.fmean(values)
    return [(v - mean) / spread for v in values]


def _correlations(series: list[list[float]]) -> list[float]:
    n = len(series[0])
    return [sum(map(mul, a, b)) / n for a, b in itertools.combinations(series, 2)]


def read_curves(curves: dict[str, list[float]], shifts: int = SHIFTS, seed: int = 0) -> Reading:
    """The rule's statistics and verdict on curves sampled at the same times (equal lengths)."""
    changes = {name: [b - a for a, b in zip(c, c[1:])] for name, c in curves.items()}
    moving = {name: z for name, z in ((n, _standardised(d)) for n, d in changes.items() if len(d) > 1) if z is not None}
    names = list(moving)
    t = len(next(iter(moving.values()))) if moving else 0
    if len(names) < 3 or t < 10:
        return Reading(len(names), t, math.nan, math.nan, math.nan, math.nan, verdict="too few moving curves or points to say")
    series = [moving[n] for n in names]
    pairs = _correlations(series)
    square = statistics.fmean(c * c for c in pairs)
    rng = random.Random(seed)
    baseline = []
    for _ in range(shifts):
        shifted = []
        for s in series:
            k = rng.randrange(1, t)
            shifted.append(s[k:] + s[:k])
        baseline.append(statistics.fmean(c * c for c in _correlations(shifted)))
    edge = 2 / math.sqrt(t)
    twins = [(a, b) for a, b in itertools.combinations(names, 2) if max(abs(x - y) for x, y in zip(curves[a], curves[b])) <= 1e-6 * (1 + max(map(abs, curves[a])))]
    reading = Reading(len(names), t, statistics.fmean(pairs), square / statistics.fmean(baseline),
                      sum(c > edge for c in pairs) / len(pairs), sum(c < -edge for c in pairs) / len(pairs), twins)
    reading.verdict = verdict(reading)
    return reading


def verdict(r: Reading) -> str:
    if r.twins:
        return "alone, on the same data (identical curves)"
    if r.co_movement < CO_MOVEMENT:
        return "alone, each on data of its own (no co-movement)"
    if r.mean >= MEAN and r.together >= SIGNS * r.against:
        return "alone, on the same data (co-movement of one sign)"
    return "one shared market (co-movement of both signs)"


# ---------------------------------------------------------------------------- the leaderboard


@dataclass
class Team:
    name: str
    rank: int | None
    tie: bool
    pnl: float
    series: list[tuple[float, float]]  # (elapsed seconds, pnl)


def load_leaderboard(path: Path) -> list[Team]:
    """The page's leaderboard data: a list of teams, or an object holding it under one key."""
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        if len(lists) != 1:
            raise ValueError("expected a list of teams, or an object holding one")
        data = lists[0]
    teams = []
    for row in data:
        series = sorted((float(p["elapsedS"]), float(p["pnl"])) for p in row.get("pnlSeries") or [])
        teams.append(Team(str(row.get("teamName") or row.get("teamId")), row.get("rank"), bool(row.get("isTie")),
                          float(row.get("pnl") or (series[-1][1] if series else 0.0)), series))
    return teams


def aligned(teams: list[Team]) -> dict[str, list[float]]:
    """Each team's PnL at every time any team's curve has a point, the last value carried forward
    (0 before a team's first point), as the page's chart merges them."""
    times = sorted({t for team in teams for t, _ in team.series})
    curves = {}
    for team in teams:
        points, k, value, curve = team.series, 0, 0.0, []
        for t in times:
            while k < len(points) and points[k][0] <= t:
                value = points[k][1]
                k += 1
            curve.append(value)
        curves[team.name] = curve
    return curves


def format_reading(r: Reading) -> str:
    if math.isnan(r.mean):
        return f"{r.teams} moving curves, {r.changes} changes: {r.verdict}"
    twins = ", ".join(f"{a} = {b}" for a, b in r.twins) or "none"
    return (f"{r.teams} moving curves, {r.changes} changes each: mean pair correlation {r.mean:+.3f}; co-movement {r.co_movement:.1f}x "
            f"the shifted curves'; pairs moving together {r.together:.0%}, against {r.against:.0%}; identical curves: {twins}.\n"
            f"verdict: {r.verdict}")


def read_main(path: Path, team: str | None) -> None:
    teams = load_leaderboard(path)
    ranked = sorted(teams, key=lambda t: -t.pnl)
    pnls = [t.pnl for t in ranked]
    print(f"{len(teams)} teams; PnL min {min(pnls):,.0f}, quartiles {', '.join(f'{q:,.0f}' for q in statistics.quantiles(pnls, n=4)) if len(pnls) > 1 else '-'}, "
          f"max {max(pnls):,.0f}; ties: {sum(t.tie for t in teams)}.")
    for k, t in enumerate(ranked[:10], 1):
        print(f"  {t.rank if t.rank is not None else k:>3}  {t.name:<30} {t.pnl:>14,.0f}{'  (tie)' if t.tie else ''}")
    if team:
        found = [k for k, t in enumerate(ranked) if t.name == team]
        if not found:
            raise SystemExit(f"no team named {team!r} on the leaderboard")
        k = found[0]
        third = pnls[min(2, len(pnls) - 1)]
        print(f"{team}: rank {k + 1} of {len(teams)}, PnL {pnls[k]:,.0f}; behind the first by {pnls[0] - pnls[k]:,.0f}, "
              f"{'ahead of' if pnls[k] >= third else 'behind'} the third by {abs(pnls[k] - third):,.0f}.")
    print(format_reading(read_curves(aligned(teams))))


# ---------------------------------------------------------------------------- calibration


def fields() -> dict[str, dict[str, tuple[Path, dict]]]:
    """The two fields: everyone, and without the zoo's local models."""
    def mm(edge):
        return MM, {"PARAMS": {p: {"make_edge": edge, "take_edge": 1, "hold": False} for p in ("KELP", "RAINFOREST_RESIN", "SQUID_INK")}}
    everyone = {"template": (TEMPLATE, {}), "template copy": (TEMPLATE, {})} | {label(p): (p, {}) for p in zoo_bots()} | {f"mm {e}": mm(e) for e in (0.5, 1, 2)}
    hosted = {name: bot for name, bot in everyone.items() if not (bot[0] != TEMPLATE and bot[0] != MM and is_local(bot[0]))}
    return {f"all {len(everyone)}": everyone, f"hosted {len(hosted)}": hosted}


@functools.lru_cache(maxsize=None)
def _days():
    return backtest_days(DATA, DAYS, ENGINE[0])


def _spec():
    spec = sim.preset_market()
    return spec if TICKS is None else dataclasses.replace(spec, ticks=TICKS)


def _total(result) -> list[float]:
    series = [s for s in result.pnl.values() if s]
    return [sum(values) for values in zip(*series)]


def run(task: tuple[str, int, tuple[tuple[str, Path, dict], ...]]) -> list[list[float]]:
    """One market: ("replay", day index, bots) or ("sim", seed, bots); each bot's total PnL curve."""
    kind, where, bots = task
    if kind == "replay":
        results = backtest(_days()[where], [(n, p, o, False) for n, p, o in bots], EngineConfig(), ENGINE[0], fields=("pnl",))
    elif ENGINE[0] == "rust":
        results = rust.run_sim(_spec(), where, 1, [(n, p, o, False) for n, p, o in bots], EngineConfig(), read="results")[0]["results"]
    else:
        results = sim.run(_spec(), where, [(n, prosperity.load_bot(p, o, strict=False)) for n, p, o in bots]).results
    return [_total(r) for r in results]


def cases(bots: dict[str, tuple[Path, dict]], days: int) -> list[tuple[str, int, list[tuple[str, int, tuple]]]]:
    """(case, day or seed, its markets) over `days` replay days and SEEDS: one market for "shared",
    one a bot otherwise."""
    entries = [(name, path, overrides) for name, (path, overrides) in bots.items()]
    out = []
    for d in range(days):
        out.append(("replay, shared", d, [("replay", d, tuple(entries))]))
        out.append(("replay, alone", d, [("replay", d, (e,)) for e in entries]))
    for s in SEEDS:
        out.append(("sim, shared", s, [("sim", s, tuple(entries))]))
        out.append(("sim, alone", s, [("sim", s, (e,)) for e in entries]))
        out.append(("sim, own seed", s, [("sim", OWN_SEEDS * (s + 1) + k, (e,)) for k, e in enumerate(entries)]))
    return out


TRUTH = {"replay, shared": "one shared market", "replay, alone": "alone, on the same data", "sim, shared": "one shared market",
         "sim, alone": "alone, on the same data", "sim, own seed": "alone, each on data of its own"}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.leaderboard_curves")
    parser.add_argument("--read", type=Path, metavar="FILE", help="the leaderboard's data, saved from the portal's page")
    parser.add_argument("--team", help="with --read: our team's name on the leaderboard")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    add_engine_argument(parser, "run the markets in rust/ (the same results)")
    args = parser.parse_args()
    if args.read:
        read_main(args.read, args.team)
        return
    if args.team:
        parser.error("--team goes with --read")
    if args.engine == "rust":
        rust.require(args.allow_stale)
    settings = {"DATA": DATA, "DAYS": DAYS, "TICKS": TICKS}
    _init(args.engine)
    days = len(_days())
    rows, right, total, alone_right = [], {}, {}, {}
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        for field_name, bots in fields().items():
            names = list(bots)
            for case, where, markets in cases(bots, days):
                found = list(pool.map(run, markets, chunksize=1))
                curves = dict(zip(names, found[0] if len(found) == 1 else [c[0] for c in found]))
                for step in STEPS:
                    r = read_curves({n: c[::step] for n, c in curves.items()})
                    ok = r.verdict.startswith(TRUTH[case])
                    signs = verdict(dataclasses.replace(r, twins=[]))  # the rule without identical curves
                    right[step] = right.get(step, 0) + ok
                    alone_right[step] = alone_right.get(step, 0) + signs.startswith(TRUTH[case])
                    total[step] = total.get(step, 0) + 1
                    rows.append((case, field_name, where, step, r, ok, signs))

    print(f"PnL curves of each field's bots, sampled every {', '.join(map(str, STEPS))} ticks; replay on {DATA} {' '.join(DAYS)} "
          f"({days} days), sim seeds {', '.join(map(str, SEEDS))}. Co-movement: T x mean squared pair correlation, "
          f"over the same for curves shifted in time ({SHIFTS} shifts). The rule: identical moving curves, or co-movement "
          f"of {CO_MOVEMENT}x or more with a mean of {MEAN} or more and {SIGNS}x as many pairs with as against: alone on the "
          f"same data; co-movement below {CO_MOVEMENT}x: alone on data of its own; else one shared market.\n")
    print("| Case | Field | Day / seed | Every | T | Moving | Mean corr | Co-movement | With | Against | Identical pairs | Verdict | Right | Without identical curves |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for case, field_name, where, step, r, ok, signs in rows:
        print(f"| {case} | {field_name} | {where} | {step} | {r.changes} | {r.teams} | {r.mean:+.3f} | {r.co_movement:.1f} | "
              f"{r.together:.0%} | {r.against:.0%} | {len(r.twins)} | {r.verdict} | {'yes' if ok else '**no**'} | "
              f"{'right' if signs.startswith(TRUTH[case]) else '**' + signs + '**'} |")
    print("\nThe rule named the case right in " + "; ".join(f"{right[s]} of {total[s]} sampled every {s} ticks" for s in STEPS) + "; "
          "without the identical curves (the template's copy), in " + "; ".join(f"{alone_right[s]} of {total[s]}" for s in STEPS) + ".")
    print("\nBy case (every step and field): mean pair correlation, co-movement, with / against:")
    for case in TRUTH:
        found = [r for c, _, _, _, r, _, _ in rows if c == case]
        print(f"  {case:<16} mean {min(r.mean for r in found):+.3f} to {max(r.mean for r in found):+.3f}; "
              f"co-movement {min(r.co_movement for r in found):.1f} to {max(r.co_movement for r in found):.1f}; "
              f"with {min(r.together for r in found):.0%}-{max(r.together for r in found):.0%}, against {min(r.against for r in found):.0%}-{max(r.against for r in found):.0%}")


if __name__ == "__main__":
    main()
