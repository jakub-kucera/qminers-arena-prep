"""Our settings against fields of rival archetypes in one market: which setting is the best reply
to each field, and which holds up across them all.

usage (from the repo root): uv run python -m experiments.day.rival_field [--jobs N] [--engine rust]
       uv run python -m experiments.day.rival_field --data DIR --days 1 2 [--products A,B] [--candidate PARAMS.P.KEY=V1,V2 ...]
       uv run python -m experiments.day.rival_field --game [--background FIELD] [--engine rust]

P3 round 1, all three days, --match-trades all, per tick and --resting. CANDIDATES: the template
with Kelp's make_edge 0.5, 1 or 1.5 and Resin's 1 or 2 (the committed bot is Kelp 0.5, Resin 2).
ARCHETYPES: python/bots/mm.py quoting Kelp and Resin at make_edge 0.5, 1 and 2, the taker, the
sniper, the spoofer and the trapper (python/bots/rivals/), and a copy of the template as
committed. FIELDS: none, each archetype alone, and five mixes of three to six. For each mode:
  1. our PnL per candidate and field, in thousands;
  2. the best reply to each field;
  3. each candidate's worst and mean PnL over the fields with rivals: the max-min and the mean
     choice, against the best reply to a copy alone (the two-bot answer, experiments.day.undercut's).
Results go into IDEAS.md ("Our settings against a field of rival archetypes").

--game: co-evolution. A rival copy of the template chooses from the same candidates as we do, both
in one market (with --background, a FIELDS entry's archetypes fixed in every game). For each mode,
the payoff matrix (our PnL and the rival's for each pair), then where play goes when each side keeps
replying to the other instead of to a fixed field:
  - pure equilibria: pairs where each side's setting is its best reply to the other's;
  - best replies in turn, from every starting pair: the stable pair (or the cycle) each reaches;
  - fictitious play (Brown): each side best-replies to the other's choices so far, GAME_STEPS
    rounds from the committed settings; whether the frequencies settle, and how much either side
    could still gain by deviating from them (0 at an equilibrium).

With --data (Prosperity-format data: the rivals are Prosperity bots), the archetypes trade
--products (default: every product the template trades there) with the data's limits, and each
--candidate (an axis as arena.grid takes it, repeatable) replaces the default candidates.
"""

from __future__ import annotations

import argparse
import itertools
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from arena import grid, rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest, backtest_days, dataset_from
from arena.engine import EngineConfig

TEMPLATE = "python/bots/template.py"
MM, RIVALS = "python/bots/mm.py", "python/bots/rivals"
AXES = {"PARAMS.KELP.make_edge": [0.5, 1, 1.5], "PARAMS.RAINFOREST_RESIN.make_edge": [1, 2]}
DATA, DAYS, FORMAT, PRODUCTS, LIMITS = "p3", ["1"], "prosperity", ["KELP", "RAINFOREST_RESIN"], {}  # --data changes them
MODES = {"per tick": EngineConfig(), "resting": EngineConfig(resting=True)}
ENGINE = ["python"]  # set in each worker by _init (--engine)
BACKGROUND = "none"  # --game: the FIELDS entry whose archetypes join every game (--background)
COMMITTED = {"PARAMS.KELP.make_edge": 0.5, "PARAMS.RAINFOREST_RESIN.make_edge": 2}  # the template as committed: fictitious play starts here
GAME_STEPS = 2000  # fictitious play's rounds
SETTLED = 0.02  # fictitious play has settled when no frequency moved more than this over its second half


def archetypes() -> dict[str, tuple[str, dict]]:
    """name: (bot file, overrides), on PRODUCTS with LIMITS (the data's, with --data)."""
    def mm(edge):
        overrides = {"PARAMS": {p: {"make_edge": edge, "take_edge": 1, "hold": False} for p in PRODUCTS}}
        return MM, overrides | ({"LIMIT": min(LIMITS.values())} if LIMITS else {})
    limits = {"LIMITS": LIMITS} if LIMITS else {}
    return {"mm 0.5": mm(0.5), "mm 1": mm(1), "mm 2": mm(2), "taker": (f"{RIVALS}/taker.py", limits), "sniper": (f"{RIVALS}/sniper.py", limits),
            "spoofer": (f"{RIVALS}/spoofer.py", limits), "trapper": (f"{RIVALS}/trapper.py", limits), "copy": (TEMPLATE, {})}


FIELDS = {"none": ()} | {name: (name,) for name in ("mm 0.5", "mm 1", "mm 2", "taker", "sniper", "spoofer", "trapper", "copy")} | {
    "three makers": ("mm 0.5", "mm 1", "mm 2"),
    "adversaries": ("sniper", "spoofer", "trapper"),
    "flow": ("mm 1", "taker", "copy"),
    "crowd": ("copy", "mm 0.5", "mm 1", "taker", "sniper"),
    "six": ("mm 0.5", "mm 2", "taker", "sniper", "spoofer", "copy"),
}


def candidates() -> list[dict]:
    return [dict(zip(AXES, values)) for values in itertools.product(*AXES.values())]


def label(candidate: dict) -> str:
    return ", ".join(f"{k.removeprefix('PARAMS.').replace('RAINFOREST_RESIN', 'RESIN')} {v}" for k, v in candidate.items())


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})


def _settings(dataset, axes: list[str]) -> dict:
    from arena.formats import FORMATS

    if dataset.format != "prosperity":
        raise ValueError("the archetypes are Prosperity-format bots: --format prosperity only")
    fmt = FORMATS[dataset.format]
    limits = {p: v for day in fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days)) for p, v in day.limits.items()
              if p in dataset.products}
    settings = {"DATA": dataset.data, "DAYS": list(dataset.days), "PRODUCTS": list(dataset.products), "TEMPLATE": dataset.bot, "LIMITS": limits}
    if axes:
        settings["AXES"] = {axis.target: list(axis.values) for axis in map(grid.parse_axis, axes)}
    return settings


def run(task: tuple[int, str, str]) -> tuple[tuple[int, str, str], float]:
    """One candidate in one field under one mode: our PnL over the days."""
    k, field, mode = task
    found = archetypes()
    bots = [("you", TEMPLATE, candidates()[k], False)] + [(name, *found[name], False) for name in FIELDS[field]]
    total = 0.0
    for day in backtest_days(DATA, DAYS, ENGINE[0], FORMAT):
        (mine, *_) = backtest(day, bots, MODES[mode], ENGINE[0], fields=("pnl",), format_name=FORMAT)
        total += sum(series[-1] for series in mine.pnl.values() if series)
    return task, total


def _total(result) -> float:
    return sum(series[-1] for series in result.pnl.values() if series)


def run_game(task: tuple[int, int, str]) -> tuple[tuple[int, int, str], tuple[float, float]]:
    """Us with candidate i against a rival copy of the template with candidate j (and BACKGROUND's
    archetypes) under one mode: our PnL and the rival's over the days."""
    i, j, mode = task
    found, chosen = archetypes(), candidates()
    bots = [("you", TEMPLATE, chosen[i], False), ("rival", TEMPLATE, chosen[j], False)] + [(name, *found[name], False) for name in FIELDS[BACKGROUND]]
    ours = theirs = 0.0
    for day in backtest_days(DATA, DAYS, ENGINE[0], FORMAT):
        mine, rival, *_ = backtest(day, bots, MODES[mode], ENGINE[0], fields=("pnl",), format_name=FORMAT)
        ours, theirs = ours + _total(mine), theirs + _total(rival)
    return task, (ours, theirs)


# ---------------------------------------------------------------------------- the game's analysis


def _argmax(values: list[float]) -> int:
    return max(range(len(values)), key=lambda k: (values[k], -k))  # ties: the first


def reply_row(U: list[list[float]], q: list[float]) -> int:
    """The row player's best reply to the column player's mixture q."""
    return _argmax([sum(qj * u for qj, u in zip(q, row)) for row in U])


def reply_column(V: list[list[float]], p: list[float]) -> int:
    """The column player's best reply to the row player's mixture p (V[i][j]: its payoff at row i, column j)."""
    return _argmax([sum(p[i] * V[i][j] for i in range(len(V))) for j in range(len(V[0]))])


def _pure(n: int, k: int) -> list[float]:
    return [1.0 if m == k else 0.0 for m in range(n)]


def pure_equilibria(U: list[list[float]], V: list[list[float]]) -> list[tuple[int, int]]:
    rows, cols = len(U), len(U[0])
    return [(i, j) for i in range(rows) for j in range(cols)
            if U[i][j] >= max(U[k][j] for k in range(rows)) and V[i][j] >= max(V[i][k] for k in range(cols))]


def best_reply_path(U: list[list[float]], V: list[list[float]], start: tuple[int, int], limit: int = 100) -> tuple[list[tuple[int, int]], bool]:
    """Best replies in turn from `start`: the row player replies to the column's choice, then the
    column to the row's, until a pair repeats. Returns the pairs visited and whether it ended at a
    fixed pair (False: a cycle)."""
    path, seen = [start], {start}
    i, j = start
    for _ in range(limit):
        i = reply_row(U, _pure(len(U[0]), j))
        j = reply_column(V, _pure(len(U), i))
        if (i, j) == path[-1]:
            return path, True
        if (i, j) in seen:
            return path + [(i, j)], False
        path.append((i, j))
        seen.add((i, j))
    return path, False


@dataclass
class Play:
    p: list[float]  # the row player's frequencies
    q: list[float]  # the column player's
    moved: float  # the largest change of a frequency over the second half
    gain_row: float  # what the row player could still gain by deviating from p against q
    gain_column: float

    @property
    def settled(self) -> bool:
        return self.moved <= SETTLED


def fictitious_play(U: list[list[float]], V: list[list[float]], start: tuple[int, int], steps: int = GAME_STEPS) -> Play:
    """Brown's fictitious play from `start`: each round both sides best-reply to the other's
    frequencies so far, at once."""
    rows, cols = len(U), len(U[0])
    count_p, count_q = _pure(rows, start[0]), _pure(cols, start[1])
    half = None
    for t in range(1, steps + 1):
        total = sum(count_p)
        p, q = [c / total for c in count_p], [c / total for c in count_q]
        i, j = reply_row(U, q), reply_column(V, p)
        count_p[i] += 1
        count_q[j] += 1
        if t == steps // 2:
            half = ([c / (t + 1) for c in count_p], [c / (t + 1) for c in count_q])
    p, q = [c / (steps + 1) for c in count_p], [c / (steps + 1) for c in count_q]
    moved = max(abs(a - b) for a, b in zip(p + q, half[0] + half[1])) if half else 1.0
    value_row = sum(p[i] * q[j] * U[i][j] for i in range(rows) for j in range(cols))
    value_col = sum(p[i] * q[j] * V[i][j] for i in range(rows) for j in range(cols))
    best_row = max(sum(q[j] * U[i][j] for j in range(cols)) for i in range(rows))
    best_col = max(sum(p[i] * V[i][j] for i in range(rows)) for j in range(cols))
    return Play(p, q, moved, best_row - value_row, best_col - value_col)


def symmetrised(U: list[list[float]], V: list[list[float]]) -> tuple[list[list[float]], float]:
    """Both seats of a game between two copies of one bot: S[i][j], a setting i's PnL against a
    setting j, the mean of its PnL in either seat (U[i][j] and V[j][i]); and the largest gap between them."""
    n = len(U)
    S = [[(U[i][j] + V[j][i]) / 2 for j in range(n)] for i in range(n)]
    return S, max(abs(U[i][j] - V[j][i]) for i in range(n) for j in range(n))


def format_game(names: list[str], U: list[list[float]], V: list[list[float]], start: int, matrix: bool = True) -> str:
    """The payoff matrix (ours / the rival's, in thousands), the pure equilibria, where best replies
    in turn go from every start, and fictitious play from (start, start)."""
    n = len(names)
    lines = ["| Us \\ rival | " + " | ".join(names) + " |", "|---" * (n + 1) + "|"]
    for i in range(n):
        lines.append(f"| {names[i]} | " + " | ".join(f"{U[i][j] / 1000:.1f} / {V[i][j] / 1000:.1f}" for j in range(n)) + " |")
    lines = lines if matrix else []
    pairs = pure_equilibria(U, V)
    show = lambda pair: f"({names[pair[0]]} ; {names[pair[1]]})"
    if matrix:
        lines.append("")
    lines.append("pure equilibria (each side's best reply to the other): " + (", ".join(show(e) for e in pairs) if pairs else "none"))
    ends: dict[tuple, int] = {}
    for i0 in range(n):
        for j0 in range(n):
            path, fixed = best_reply_path(U, V, (i0, j0))
            key = (path[-1],) if fixed else tuple(path[path.index(path[-1]):-1])
            ends[key] = ends.get(key, 0) + 1
    for key, count in sorted(ends.items(), key=lambda item: -item[1]):
        what = f"settle at {show(key[0])}" if len(key) == 1 else "cycle through " + " -> ".join(show(pair) for pair in key)
        lines.append(f"best replies in turn: {count} of {n * n} starts {what}")
    play = fictitious_play(U, V, (start, start))
    mix = lambda freqs: ", ".join(f"{names[k]} {f:.0%}" for k, f in sorted(enumerate(freqs), key=lambda kf: -kf[1]) if f >= 0.005)
    lines.append(f"fictitious play from the committed ({names[start]}), {GAME_STEPS:,} rounds: "
                 + ("settled" if play.settled else f"still moving (a frequency moved {play.moved:.0%} over the second half)"))
    lines.append(f"  we play {mix(play.p)}; the rival plays {mix(play.q)}")
    lines.append(f"  either side could still gain {play.gain_row / 1000:.2f}k (us) and {play.gain_column / 1000:.2f}k (the rival) by deviating "
                 "(0 at an equilibrium)")
    return "\n".join(lines)


def main_game(args, settings: dict) -> None:
    globals().update(settings)
    chosen = candidates()
    n = len(chosen)
    tasks = [(i, j, m) for i in range(n) for j in range(n) for m in MODES]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        pnl = dict(pool.map(run_game, tasks, chunksize=1))
    names = [label(c) for c in chosen]
    start = next((k for k, c in enumerate(chosen) if all(COMMITTED.get(key) == v for key, v in c.items())), 0)  # else the first candidate
    where = "P3 round 1, all three days" if not settings.get("DATA") or settings.get("DATA") == "p3" else settings["DATA"]
    background = f", with {' + '.join(FIELDS[BACKGROUND])} in every game" if FIELDS[BACKGROUND] else ""
    print(f"{where}, --match-trades all: us against a rival copy of the template, each choosing from the same {n} settings{background}. "
          "Our PnL / the rival's, in thousands.")
    for mode in MODES:
        U = [[pnl[(i, j, mode)][0] for j in range(n)] for i in range(n)]
        V = [[pnl[(i, j, mode)][1] for j in range(n)] for i in range(n)]
        S, seat = symmetrised(U, V)
        print(f"\n{mode}:\n")
        print(format_game(names, U, V, start))
        print(f"\nthe seat (the engine's arrival order, \"you\" against \"rival\") moves a pair's payoff by up to {seat / 1000:.2f}k: the same "
              "game with each payoff the mean of both seats, a setting's PnL against another's:\n")
        print(format_game(names, S, [list(row) for row in zip(*S)], start))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.rival_field")
    parser.add_argument("--jobs", type=int, default=None, help="worker processes (default: one per CPU)")
    parser.add_argument("--candidate", action="append", default=[], metavar="PARAMS.P.KEY=V1,V2",
                        help="with --data: an axis of the candidate settings, as arena.grid's --grid (repeatable)")
    parser.add_argument("--game", action="store_true",
                        help="co-evolution: a rival copy of the template choosing from the same candidates; the payoff matrix, its pure "
                             "equilibria, best replies in turn and fictitious play")
    parser.add_argument("--background", default="none", choices=sorted(FIELDS),
                        help="with --game: the archetypes of this field in every game (default: none)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser)
    args = parser.parse_args()
    try:
        dataset = dataset_from(args)
        if args.candidate and not dataset:
            raise ValueError("--candidate goes with --data")
        settings = _settings(dataset, args.candidate) if dataset else {}
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    if args.game:
        main_game(args, settings | {"BACKGROUND": args.background})
        return
    globals().update(settings)
    tasks = [(k, f, m) for k in range(len(candidates())) for f in FIELDS for m in MODES]
    with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(args.engine, settings)) as pool:
        pnl = dict(pool.map(run, tasks, chunksize=1))

    names, fields, rivals = [label(c) for c in candidates()], list(FIELDS), [f for f in FIELDS if FIELDS[f]]
    where = f"{dataset.name}" if dataset else "P3 round 1, all three days"
    print(f"{where}, --match-trades all. Our PnL in thousands, each candidate in each field of rivals: "
          + "; ".join(f"{f} = {' + '.join(FIELDS[f])}" for f in fields if len(FIELDS[f]) > 1) + ".")
    for mode in MODES:
        print(f"\n{mode}:\n")
        print("| Candidate | " + " | ".join(fields) + " | worst | mean |")
        print("|---" * (len(fields) + 3) + "|")
        for k, name in enumerate(names):
            row = [pnl[(k, f, mode)] for f in fields]
            against = [pnl[(k, f, mode)] for f in rivals]
            print(f"| {name} | " + " | ".join(f"{v / 1000:.1f}" for v in row) + f" | {min(against) / 1000:.1f} | {statistics.fmean(against) / 1000:.1f} |")
        best = {f: max(range(len(names)), key=lambda k: pnl[(k, f, mode)]) for f in fields}
        print("| **best reply** | " + " | ".join(names[best[f]] for f in fields) + " | | |")
        worst = max(range(len(names)), key=lambda k: min(pnl[(k, f, mode)] for f in rivals))
        mean = max(range(len(names)), key=lambda k: statistics.fmean(pnl[(k, f, mode)] for f in rivals))
        replies = {names[best[f]] for f in rivals}
        print(f"\nmax-min: {names[worst]}; mean: {names[mean]}; against a copy alone (the two-bot answer): {names[best['copy']]}. "
              f"{len(replies)} different best replies over {len(rivals)} fields.")


if __name__ == "__main__":
    main()
