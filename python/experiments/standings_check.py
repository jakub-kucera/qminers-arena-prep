"""Does the standings calculator (experiments.standings) predict a real field's last round?

usage (from the repo root): uv run python -m experiments.standings_check [--rounds4 20] [--jobs N]

The field is the LLM zoo (python/bots/zoo/, its non-local bots, each a team) and the template, each
trading alone, per tick, under `all`:
  - rounds 1-3: P3 round 1's three days, one a round, each team's leaderboard entry its PnL and
    PnL curve (every 100 ticks), as experiments.leaderboard_curves reads the portal's;
  - round 4: one of ROUND4 fresh arena.sim days of the same products (the default market, seeds
    1000 on; every other one with a regime change at midday: the finale that punishes the playbook).
From rounds 1-3 the calculator predicts our place after round 4 (field_model and simulate, as the
command does) from what we would know before it: our per-day PnL on HELD_OUT other simulated days.
Each of the ROUND4 days is then one real round 4, played: the realised chance of first place, of the
top 3 and of losing a place, and the mean rank, set beside the prediction. The same for a variant at
half the template's risk (its own limit 25 on Kelp and Resin, of the exchange's 50), and the calculator's own k = 0.5 from the
full-size distribution. Results: IDEAS.md, "A standings calculator for round 4".
"""

from __future__ import annotations

import argparse
import statistics
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from arena import sim
from arena.cli import backtest, backtest_days
from arena.engine import EngineConfig
from experiments import leaderboard_curves as lc
from experiments import standings as st
from experiments.zoo import TEMPLATE, is_local, label, zoo_bots

ROUND4 = 20
HELD_OUT = 5  # simulated days for our own distribution, as the round's public data would give it
SEED = 1000
WEIGHTS = st.WEIGHTS
HALF = {"PARAMS.KELP.limit": 25, "PARAMS.RAINFOREST_RESIN.limit": 25}  # the template holds half its room: half the risk
STEP = 100  # ticks between a curve's points


def write_days(folder: Path, seeds: list[int], regimes: bool) -> None:
    """arena.sim days in the Prosperity layout, round 1, day = seed; with `regimes`, every other one changes regime."""
    for k, seed in enumerate(seeds):
        spec = sim.preset_market()
        if regimes and k % 2:
            spec = sim.with_regime(spec, sim.REGIMES[(k // 2) % len(sim.REGIMES)])
        sim.write_day(sim.run(spec, seed), folder, 1, seed)


def played(task: tuple[str, str, str, Path, dict]) -> tuple[str, str, float, list[float]]:
    """One team alone on one day: its PnL and its curve."""
    name, data, spec, path, overrides = task
    (day,) = backtest_days(data, [spec], "rust")
    (result,) = backtest(day, [(name, path, overrides, False)], EngineConfig(), "rust", fields=("pnl",))
    series = [sum(values) for values in zip(*(s for s in result.pnl.values() if s))] or [0.0]
    return name, spec, series[-1], series[::STEP] + [series[-1]]


def teams(results: list[tuple[str, str, float, list[float]]], spec: str) -> list[lc.Team]:
    rows = [(name, pnl, curve) for name, s, pnl, curve in results if s == spec]
    return [lc.Team(name, None, False, pnl, [(float(k * STEP), v) for k, v in enumerate(curve)]) for name, pnl, curve in rows]


def realised(board: st.Board, us: int, scoring: st.Scoring, round4: dict[str, float]) -> tuple[int, int]:
    """Our rank before and after a played round 4."""
    before = st.rank_of(st.totals(board, scoring), us)
    after = st.Board(board.teams, board.pnl + [[round4.get(name, 0.0) for name in board.teams]], board.curves)
    return before, st.rank_of(st.totals(after, scoring), us)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.standings_check")
    parser.add_argument("--rounds4", type=int, default=ROUND4)
    parser.add_argument("--jobs", type=int, default=None)
    args = parser.parse_args(argv)

    field = [(label(p), p) for p in [TEMPLATE, *(p for p in zoo_bots() if not is_local(p))]]
    variants = {"template": {}, "template at half its limit": HALF}
    with tempfile.TemporaryDirectory() as scratch:
        later, ours_dir = Path(scratch) / "round4", Path(scratch) / "ours"
        round4_seeds = list(range(SEED, SEED + args.rounds4))
        held_seeds = list(range(SEED + 500, SEED + 500 + HELD_OUT))
        write_days(later, round4_seeds, regimes=True)
        write_days(ours_dir, held_seeds, regimes=True)
        tasks = [(name, "p3", spec, path, {}) for name, path in field for spec in ("1--2", "1--1", "1-0")]
        tasks += [(name, str(later), f"1-{seed}", path, {}) for name, path in field for seed in round4_seeds]
        tasks += [(f"{v} (half)", str(later), f"1-{seed}", TEMPLATE, HALF) for v in ["template"] for seed in round4_seeds]
        tasks += [(f"ours:{v}", str(ours_dir), f"1-{seed}", TEMPLATE, o) for v, o in variants.items() for seed in held_seeds]
        tasks += [(name, str(ours_dir), f"1-{seed}", path, {}) for name, path in field[1:] for seed in held_seeds]  # the zoo on them: the scale
        tasks += [(f"{v} r1-3", "p3", spec, TEMPLATE, HALF) for v in ["half"] for spec in ("1--2", "1--1", "1-0")]
        with ProcessPoolExecutor(args.jobs) as pool:
            results = list(pool.map(played, tasks, chunksize=8))

    print(f"The field: the template and {len(field) - 1} zoo bots, each alone, per tick, `all`. Rounds 1-3: P3 round 1's days; "
          f"round 4: {args.rounds4} arena.sim days (seeds {round4_seeds[0]}-{round4_seeds[-1]}, every other one with a regime change).\n")
    for variant, overrides in variants.items():
        board = st.board_of([teams(results, spec) for spec in ("1--2", "1--1", "1-0")])
        us = board.teams.index("template")
        if overrides:  # our rounds 1-3 as the half-size variant played them
            for r, spec in enumerate(("1--2", "1--1", "1-0")):
                board.pnl[r][us] = next(pnl for name, s, pnl, _ in results if name == "half r1-3" and s == spec)
        ours = st.our_round([pnl for name, _, pnl, _ in results if name == f"ours:{variant}"], 1)
        model = st.field_model(board)
        r3 = statistics.pstdev(board.pnl[-1])
        r4 = statistics.fmean(statistics.pstdev([pnl for n, s, pnl, _ in results if s == f"1-{seed}" and n in board.teams]) for seed in round4_seeds)
        zoo = [n for n in board.teams if n != "template"]
        held = statistics.fmean(statistics.pstdev([pnl for n, s, pnl, _ in results if s == f"1-{seed}" and n in zoo and not n.startswith("ours:")])
                                for seed in held_seeds)
        proxy = held / statistics.pstdev([v for n, v in zip(board.teams, board.pnl[-1]) if n in zoo])
        growth = {"measured": (1.0, st.growth_spread(board)), "0.5": (1.0, 0.5), f"from the zoo on the held-out days, {proxy:.2f}": (proxy, 0.0),
                  f"the realised scale, {r4 / r3:.2f}": (r4 / r3, 0.0)}
        print(f"## {variant}: our round-4 PnL from {HELD_OUT} held-out days, mean {ours[0]:,.0f}, sd {ours[1]:,.0f}; "
              f"the field's persistence {model.persistence:.2f}, its bet's share {model.common:.2f}; the field's sd {r3:,.0f} in round 3, "
              f"{r4:,.0f} in round 4 on average (growth-sd measured on rounds 1-3: {growth['measured'][1]:.2f})\n")
        print("| scoring | the next round's scale | rank after 3 | predicted mean rank | realised | predicted P(1st) | realised | predicted P(top 3) | realised | "
              "predicted P(lose a place) | realised | calculator at k 0.5 (mean rank, P(1st)) |")
        print("|---|---|---|---|---|---|---|---|---|---|---|---|")
        name = "template" if not overrides else "template (half)"
        for (g, (scale, g_sd)), scoring in ((g, s) for g in growth.items() for s in st.scorings(WEIGHTS)):
            predicted = st.simulate(board, us, ours, st.field_model(board, scale), WEIGHTS, multipliers=(0.5, 1.0), hedges=(0.0,), sims=st.SIMS,
                                    growth_sd=g_sd)
            ranks = []
            for seed in round4_seeds:
                round4 = {n: pnl for n, s, pnl, _ in results if s == f"1-{seed}" and not n.startswith(("ours:", "template (half)"))}
                round4["template"] = next(pnl for n, s, pnl, _ in results if n == name and s == f"1-{seed}")
                ranks.append(realised(board, us, scoring, round4))
            now = ranks[0][0]
            after = [r for _, r in ranks]
            tally, half = predicted.risk[(scoring.name, 1.0)], predicted.risk[(scoring.name, 0.5)]
            print(f"| {scoring.name} | {g} | {now} | {tally.mean_rank:.2f} | {statistics.fmean(after):.2f} | {tally.share(tally.first):.0%} | "
                  f"{sum(r == 1 for r in after) / len(after):.0%} | {tally.share(tally.top3):.0%} | {sum(r <= 3 for r in after) / len(after):.0%} | "
                  f"{tally.share(tally.lost):.0%} | {sum(r > now for r in after) / len(after):.0%} | {half.mean_rank:.2f}, {half.share(half.first):.0%} |")
        print()


if __name__ == "__main__":
    main()
