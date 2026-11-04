"""The guidebook's Part IV data (chapters 11 to 13): the permutation test's copies, the Kelp grid's statistics, the
depletion check and the standings calculator's risk tables. Each step writes a CSV in book/data/ whose first line
names its command; make_data.py runs them (--only NAME). Standard library only."""

from __future__ import annotations

import json
import re

from make_data import TEMPLATE, number, run, write

# arena.grid's own run, with format_permutations wrapped so that the values it summarises (the best cell's PnL and
# its lift over the median cell, on the real days and on each shuffled copy) are printed too; the grid's printed
# output is unchanged and comes first.
PERMUTE = """
import json, multiprocessing, sys
multiprocessing.set_start_method("fork")
import arena.grid as grid
captured = {}
original = grid.format_permutations
def spy(axes, outcomes, copies, mode, block, products):
    traded = grid.axis_products(axes, products)
    captured["real"] = grid.search_stats(outcomes, mode, traded)
    captured["copies"] = [grid.search_stats(o, mode, traded) for o in copies]
    return original(axes, outcomes, copies, mode, block, products)
grid.format_permutations = spy
code = grid.main(sys.argv[1:])
print("PER-COPY " + json.dumps(captured))
sys.exit(code)
"""

PERMUTED = {
    # IDEAS.md, "A permutation test of the whole search": Kelp's edges (the null holds) and Hydrogel's level settings
    # (the positive control)
    "Kelp": [TEMPLATE, "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0..7", "--grid", "PARAMS.KELP.take_edge=0..7",
             "--modes", "all,worse", "--permute", "19", "--engine", "rust"],
    "Hydrogel": [TEMPLATE, "3", "4", "--data", "p4", "--grid", "PARAMS.HYDROGEL_PACK.level_band=15,25,35,45,55",
                 "--grid", "PARAMS.HYDROGEL_PACK.clear_edge=2,5,10,15", "--permute", "19", "--engine", "rust"],
}


def permutation_null() -> None:
    """G17: each grid on the real days and on 19 copies with their ticks shuffled: the best cell's PnL and its lift
    over the median cell, per copy (only the products the axes set), with the p-values the grid printed."""
    rows, printed = [], []
    for name, args in PERMUTED.items():
        output = run(["-c", PERMUTE, *args])
        captured = json.loads(output.split("PER-COPY ", 1)[1].splitlines()[0])
        p = [float(x) for x in re.findall(r"; p ([\d.]+) that", output)]
        rows.append([name, "real", 0, *captured["real"], *p])
        rows += [[name, "copy", k, *values, "", ""] for k, values in enumerate(captured["copies"], start=1)]
        printed.append(f"{name}: uv run python -m arena.grid {' '.join(args)}")
    write("permutation_null", "; ".join(printed) + " (each copy's values captured from arena.grid's format_permutations)",
          ["grid", "run", "copy", "best", "lift", "p_best", "p_lift"], rows)


KELP_GRID = [TEMPLATE, "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0,0.5,1,1.5,2,3", "--grid", "PARAMS.KELP.take_edge=0,0.5,1,2",
             "--modes", "all,worse", "--engine", "rust", "--holdout", "last"]


def kelp_stats() -> None:
    """Chapter 11's grid read in full (F10's command with --holdout last): every line of its summary from the held-out
    days on, as printed."""
    output = run(["-m", "arena.grid", *KELP_GRID])
    lines = output.splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("best by pnl"))
    rows = [[k, line.rstrip()] for k, line in enumerate(lines[at:]) if line.strip()]
    write("kelp_stats", "uv run python -m arena.grid " + " ".join(KELP_GRID) + ": its summary, from 'best by pnl' on", ["line", "text"], rows)


def depletion() -> None:
    """Chapter 12's story 16: the first rehearsal's bot on its hidden days, the book restored each step and with what it
    takes kept gone (IDEAS.md, "The kickoff prompts on a disguised round")."""
    rows = []
    for name, extra in (("restored", []), ("deplete", ["--deplete"])):
        output = run(["python/experiments/mock_round/private/evaluate.py", "python/experiments/mock_round/results/repo_template.py",
                      "--days", "hidden", *extra])
        rows.append([name, number(re.search(r"TOTAL PnL: ([-\d,.]+)", output).group(1))])
    write("depletion", "uv run python python/experiments/mock_round/private/evaluate.py python/experiments/mock_round/results/repo_template.py "
          "--days hidden [--deplete]: the round's own units", ["book", "pnl"], rows)


# G20: experiments.day.standings on its synthetic field (30 teams, three rounds played, us 3 sds ahead), for three
# distributions of our last round's PnL (IDEAS.md, "A standings calculator for round 4"), with the mean scaling with
# the stake (mean power 1) or not (0).
OURS = {"steady (mean 35k, sd 11k)": "20000,30000,35000,40000,50000", "weak (mean 10k, sd 19k)": "-15000,0,10000,20000,35000",
        "volatile (mean 35k, sd 49k)": "-30000,10000,35000,60000,100000"}


def standings() -> None:
    """G20: the leader's chance of first, of the top 3 and of losing a place against its risk multiplier k, under
    PnL weighted 10/20/30/40 (the site's unconfirmed weights)."""
    rows = []
    for power in ("1", "0"):
        for case, ours in OURS.items():
            output = run(["-m", "experiments.day.standings", "--synthetic", "--seed", "4", "--lead", "3", f"--ours={ours}", "--mean-power", power])
            table = output.split("risk multiplier k", 1)[1].split("relative hedge", 1)[0]
            for line in table.splitlines():
                found = re.match(r"\s+pnl 10/20/30/40\s+([\d.]+)\s+([\d.]+)\s+(\d+)%\s+(\d+)%\s+(\d+)%", line)
                if found:
                    k, rank, first, top3, lose = found.groups()
                    rows.append([power, case, float(k), float(rank), int(first) / 100, int(top3) / 100, int(lose) / 100])
    write("standings", "uv run python -m experiments.day.standings --synthetic --seed 4 --lead 3 --ours=<case> --mean-power 1|0: "
          "its risk-multiplier table under pnl 10/20/30/40", ["mean_power", "case", "k", "mean_rank", "first", "top3", "lose_place"], rows)


STEPS = {"permutation_null": permutation_null, "kelp_stats": kelp_stats, "depletion": depletion, "standings": standings}
