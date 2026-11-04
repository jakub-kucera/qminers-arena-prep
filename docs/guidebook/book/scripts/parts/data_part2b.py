"""The guidebook's Part II, chapters 6 and 7: holding a position and what prices do (G7-G10, and the numbers
chapter 6's story re-runs). Each step runs a committed command, or calls a committed experiment's functions, and
writes a CSV; make_data.py runs them (--only NAME).
"""

from __future__ import annotations

import csv
import math
import statistics
import tempfile
from pathlib import Path

from make_data import ROOT, TEMPLATE, number, run, write


def _grid_out(args: list[str]) -> list[dict]:
    """An arena.grid run's per-cell CSV (--out), which carries each product's PnL under each mode."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "grid.csv"
        run(args + ["--out", str(path)])
        with path.open() as file:
            return list(csv.DictReader(file))


# -- G7 the mirror test -------------------------------------------------------------------------------------------

def mirror_test() -> None:
    """G7: Kelp's position over one day and over the same day mirrored (experiments.study.kelp_drift's `mirrored`),
    the template as committed under the default fill rule; and, for each day, both PnLs and the part of the PnL that
    came from the position riding the price: the sum of each tick's position times the next tick's change in the wall
    mid (not the mid, whose one-tick bounce would book the spread a fill earns as the position's gain)."""
    from arena.engine import run_day
    from experiments.study.kelp_drift import FMT, MODES, mirrored

    days = FMT.load_days(FMT.resolve_data_dir("p3"), ["1"])
    bot = lambda: FMT.load_bot(Path(ROOT / TEMPLATE), {}, strict=True)  # noqa: E731
    rows, summary = [], []
    for day in days:
        normal, flipped = run_day(day, bot(), MODES["all"]), run_day(mirrored(day), bot(), MODES["all"])
        q, m = normal.positions["KELP"], normal.marks["KELP"]
        wall, last = [], m[0]
        for w in normal.wall_mids["KELP"]:  # a tick with a side empty keeps the last wall mid
            last = w if w is not None else last
            wall.append(last)
        riding = sum(a * (w2 - w1) for a, w1, w2 in zip(q, wall, wall[1:]))
        riding_mid = sum(a * (m2 - m1) for a, m1, m2 in zip(q, m, m[1:]))  # the same against the mid, for contrast
        summary.append([day.name, round(normal.pnl["KELP"][-1], 1), round(flipped.pnl["KELP"][-1], 1),
                        round(statistics.fmean(q), 1), round(statistics.fmean(flipped.positions["KELP"]), 1), round(riding, 1),
                        round(riding_mid, 1), m[0], m[-1]])
        if day.name == "r1d-2":
            mq, mm = flipped.positions["KELP"], flipped.marks["KELP"]
            rows = [[k, m[k], mm[k], q[k], mq[k]] for k in range(0, len(q), 10)]
    source = ("experiments.study.kelp_drift's mirrored() and arena.engine.run_day: python/bots/template.py on P3 round 1, "
              "--match-trades all; KELP")
    write("mirror_test", source + ", day r1d-2, every 10th tick", ["tick", "mark", "mark_mirrored", "position", "position_mirrored"], rows)
    write("mirror_summary", source + "; riding = sum of position x the next change in the wall mid (riding_mid: in the mid)",
          ["day", "pnl", "pnl_mirrored", "mean_position", "mean_position_mirrored", "riding", "riding_mid", "mark_open", "mark_close"], summary)


# -- G8 PnL against skew ------------------------------------------------------------------------------------------

def skew_grid() -> None:
    """G8: Kelp's PnL against `skew` (ticks at the full limit) under all and worse, P3 round 1 (Kelp alone)."""
    args = ["-m", "arena.grid", TEMPLATE, "1", "--data", "p3", "--grid", "PARAMS.KELP.skew=0,1,2,3,4,6,8", "--modes", "all,worse",
            "--engine", "rust"]
    rows = sorted([float(r["PARAMS.KELP.skew"]), number(r["pnl_all_KELP"]), number(r["pnl_worse_KELP"])] for r in _grid_out(args))
    write("skew_grid", "uv run python -m arena.grid python/bots/template.py 1 --data p3 --grid PARAMS.KELP.skew=0,1,2,3,4,6,8 "
          "--modes all,worse --engine rust --out ...: the KELP columns", ["skew", "pnl_all", "pnl_worse"], rows)


def osmium_skew() -> None:
    """Chapter 6's story: Osmium's skew on P4 rounds 1-2 (the wiki's contradictions row 1, its command), Osmium alone."""
    args = ["-m", "arena.grid", TEMPLATE, "1", "2", "--data", "p4", "--set", "PARAMS.ASH_COATED_OSMIUM.fixed_fair=10000",
            "--grid", "PARAMS.ASH_COATED_OSMIUM.fair=fixed,wall_mid", "--grid", "PARAMS.ASH_COATED_OSMIUM.skew=0,1,2,4,8",
            "--modes", "all,worse", "--engine", "rust"]
    rows = sorted([r["PARAMS.ASH_COATED_OSMIUM.fair"], float(r["PARAMS.ASH_COATED_OSMIUM.skew"]), number(r["pnl_all_ASH_COATED_OSMIUM"]),
                   number(r["pnl_worse_ASH_COATED_OSMIUM"])] for r in _grid_out(args))
    write("osmium_skew", "uv run python -m arena.grid python/bots/template.py 1 2 --data p4 --set PARAMS.ASH_COATED_OSMIUM.fixed_fair=10000 "
          "--grid PARAMS.ASH_COATED_OSMIUM.fair=fixed,wall_mid --grid PARAMS.ASH_COATED_OSMIUM.skew=0,1,2,4,8 --modes all,worse "
          "--engine rust --out ...: the ASH_COATED_OSMIUM columns", ["fair", "skew", "pnl_all", "pnl_worse"], rows)


# -- G9 does the coupon's residual revert, and how fast -----------------------------------------------------------

LAGS = (1, 2, 5, 10, 20, 50, 100, 200, 300, 500, 1000, 2000, 5000)


def coupon_acf() -> None:
    """G9: Prosperity 2 round 4's coconut coupon, its residual against Black-Scholes at the other days' vol, as
    experiments.day.p3_smile defines it (its functions, with the IDEAS row's settings): the residual's
    autocorrelation at each lag, each day, and the lag-1 autocorrelation of its fast part (the residual less its EMA
    over the window), the number the IDEAS row and p3_smile's part 2 print."""
    import argparse

    from arena.cli import add_dataset_arguments, dataset_from
    from experiments.day import p3_smile
    from experiments.day.p4_vouchers import bs_call

    parser = argparse.ArgumentParser()
    add_dataset_arguments(parser, products=False)
    dataset = dataset_from(parser.parse_args(["--data", "p2", "--days", "4"]))
    settings = p3_smile._settings(dataset, "COCONUT", "COCONUT_COUPON", "r4d1=250,r4d2=249,r4d3=248", 10000)
    saved = {key: vars(p3_smile)[key] for key in settings if key in vars(p3_smile)}
    vars(p3_smile).update(settings)  # p3_smile keeps its dataset in module globals: put P3's back afterwards
    try:
        by_day = {day.name: p3_smile.points(day) for day in p3_smile.load()}
    finally:
        vars(p3_smile).update(saved)
    rows = []
    for name, points in by_day.items():
        others = [r for n, rs in by_day.items() if n != name for r in rs]
        coef = p3_smile.fit_parabola(others)
        residual = [r["price"] - bs_call(r["S"], r["K"], r["T"], p3_smile.smile(coef, r["m"])) for r in points]
        mean = statistics.fmean(residual)
        x = [v - mean for v in residual]
        variance = sum(v * v for v in x)
        for lag in LAGS:
            rows.append([name, "residual", lag, round(sum(a * b for a, b in zip(x, x[lag:])) / variance, 4)])
        lag1 = sum(a * b for a, b in zip(x, x[1:])) / variance
        rows.append([name, "half-life from lag 1", round(-math.log(2) / math.log(lag1), 1), 0.5])  # Bailey et al., eq. 6.5
        for window in (20, 200, 1000, 5000, 20000):
            alpha, ema, fast = 2 / (window + 1), residual[0], []
            for v in residual:
                fast.append(v - ema)
                ema += alpha * (v - ema)
            rows.append([name, f"fast part, window {window}", 1, round(statistics.correlation(fast[:-1], fast[1:]), 4)])
    write("coupon_acf", "experiments.day.p3_smile's residual (points, fit_parabola, smile, bs_call) on P2 round 4's COCONUT_COUPON "
          "(--data p2 --days 4 --underlying COCONUT --prefix COCONUT_COUPON --strike 10000 --expiry r4d1=250,r4d2=249,r4d3=248): "
          "its autocorrelation at each lag, demeaned per day", ["day", "series", "lag", "autocorrelation"], rows)


# -- G10 the perturbed days ---------------------------------------------------------------------------------------

STRESS = (("as committed", []),
          ("without the loss stops", ["--set", "PARAMS.KELP.stop_loss=None", "--set", "PARAMS.RAINFOREST_RESIN.stop_loss=None"]),
          ("without Resin's guard", ["--set", "PARAMS.RAINFOREST_RESIN.fixed_guard=None"]))


def stress_variants() -> None:
    """G10: arena.stress on P3 round 1, the template as committed, without its loss stops, and without Resin's
    fixed_guard: each product's PnL over the three days under each perturbation."""
    rows = []
    for variant, extra in STRESS:
        lines = run(["-m", "arena.stress", TEMPLATE, "1", "--engine", "rust", *extra]).splitlines()
        at = next(i for i, line in enumerate(lines) if line.startswith("product "))
        header = lines[at].split()[1:10]  # plain, vol2, trend_up, ..., no_wall
        for line in lines[at + 1:]:
            cells = line.split()
            if not cells:
                break
            for name, value in zip(header, cells[1:10]):
                rows.append([variant, cells[0], name, number(value)])
    write("stress_variants", "uv run python -m arena.stress python/bots/template.py 1 --engine rust [--set PARAMS.KELP.stop_loss=None "
          "--set PARAMS.RAINFOREST_RESIN.stop_loss=None | --set PARAMS.RAINFOREST_RESIN.fixed_guard=None]",
          ["variant", "product", "perturbation", "pnl"], rows)


def level_heldout() -> None:
    """Chapter 7: the template's level mode on P4 Hydrogel and Velvetfruit, held out (experiments.day.p4_level_template;
    the IDEAS row "Trading toward a known level"), per product: the nested leave-one-day-out total and the in-sample one."""
    import re

    output = run(["-m", "experiments.day.p4_level_template", "--engine", "rust"])
    rows = []
    for block in re.split(r"\n(?=[A-Z_]+\n)", output):
        if not block.strip():
            continue
        name = block.strip().splitlines()[0]
        held = re.search(r"total over the held-out days ([-\d.]+)k", block)
        chosen = re.search(r"CHOSEN \(tuned and levelled on all four days\): ([-\d.]+)k", block)
        others = re.search(r"other days' mean, level_weight None\s+([-\d.]+)k", block)
        so_far = re.search(r"the day so far \(\"day\"\)\s+([-\d.]+)k", block)
        if held and chosen and others and so_far:
            rows.append([name, float(held.group(1)), float(chosen.group(1)), float(others.group(1)), float(so_far.group(1))])
    write("level_heldout", "uv run python -m experiments.day.p4_level_template --engine rust: thousands of credits over P4 rounds 3-4's "
          "four distinct days; the last two, the committed settings with the level from the other days or from the day so far",
          ["product", "held_out", "in_sample", "level_other_days", "level_day_so_far"], rows)


def glft_skew() -> None:
    """Chapter 6: the theory's skew (GLFT's closed form, c2 x limit) per risk aversion and each product's PnL with it
    (experiments.day.glft_skew; the IDEAS row "The skew coefficient from GLFT's closed form")."""
    lines = run(["-m", "experiments.day.glft_skew"]).splitlines()
    at = next(i for i, line in enumerate(lines) if line.strip().startswith("product ") and "skew" in line)
    rows, product = [], None
    for line in lines[at + 1:]:
        cells = line.split()
        if not cells:
            continue
        if cells[0].isupper():
            product, cells = cells[0], cells[1:]
        if cells[0] == "committed":
            rows.append([product, "committed", "", number(cells[1]), number(cells[2])])
        elif cells[0] == "gamma":
            rows.append([product, f"gamma {cells[1]}", float(cells[2]), number(cells[3]), number(cells[4])])
    write("glft_skew", "uv run python -m experiments.day.glft_skew: the theory's skew per gamma and the product's PnL with it",
          ["product", "setting", "skew", "pnl_all", "pnl_worse"], rows)


def size_controls() -> None:
    """Chapter 6's one-liners: `size_skew` on Kelp, and `make_size` caps on Kelp and Resin, P3 round 1 (the IDEAS rows
    "Inventory control through quote size" and "Using less than the full position limit"), each product alone."""
    rows = []
    for product, name, values in (("KELP", "size_skew", "0,0.5,1,2,4"), ("KELP", "make_size", "5,10,20,40,None"),
                                  ("RAINFOREST_RESIN", "make_size", "5,10,20,40,None")):
        args = ["-m", "arena.grid", TEMPLATE, "1", "--data", "p3", "--grid", f"PARAMS.{product}.{name}={values}", "--modes", "all,worse",
                "--engine", "rust"]
        for r in _grid_out(args):
            rows.append([product, name, r[f"PARAMS.{product}.{name}"] or "None", number(r[f"pnl_all_{product}"]), number(r[f"pnl_worse_{product}"])])
    write("size_controls", "uv run python -m arena.grid python/bots/template.py 1 --data p3 --grid PARAMS.KELP.size_skew=0,0.5,1,2,4 | "
          "PARAMS.KELP.make_size=5,10,20,40,None | PARAMS.RAINFOREST_RESIN.make_size=5,10,20,40,None --modes all,worse --engine rust --out ...",
          ["product", "parameter", "value", "pnl_all", "pnl_worse"], rows)


def drift_target() -> None:
    """Chapter 7: Prosperity 4's Pepper Root, which drifts up every day, with the template's committed long target
    (target 80, skew 20) and as a plain market maker (target 0, skew 0), per day (the IDEAS row "A long bias on a
    drifting product")."""
    import re

    rows = []
    for setting, extra in (("target 80, skew 20 (committed)", []),
                           ("plain market making", ["--set", "PARAMS.INTARIAN_PEPPER_ROOT.target=0", "--set", "PARAMS.INTARIAN_PEPPER_ROOT.skew=0"])):
        output = run(["-m", "arena.backtest", TEMPLATE, "1", "2", "--data", "p4", "--engine", "rust", *extra])
        for day, pnl in re.findall(r"(r\d+d-?\d+) · [\d,]+ ticks\n(?:.*\n)*?\s+INTARIAN_PEPPER_ROOT\s+([-\d,]+)", output):
            rows.append([setting, day, number(pnl)])
    write("drift_target", "uv run python -m arena.backtest python/bots/template.py 1 2 --data p4 --engine rust "
          "[--set PARAMS.INTARIAN_PEPPER_ROOT.target=0 --set PARAMS.INTARIAN_PEPPER_ROOT.skew=0]: Pepper Root's PnL per day",
          ["setting", "day", "pnl"], rows)


def sim_regimes() -> None:
    """Chapter 7's other market: the template inside arena.sim's Kelp, Resin and Hydrogel presets under regime changes,
    as committed and unprotected (experiments.study.sim_regimes, about a minute on 14 cores; the IDEAS row "Regime
    changes in a market that reacts"): thousands of credits over ten seeds."""
    rows = []
    for line in run(["-m", "experiments.study.sim_regimes"]).splitlines():
        cells = line.split()
        if len(cells) == 12 and cells[1] in ("committed", "unprotected"):
            for product, at in (("KELP", 2), ("RAINFOREST_RESIN", 5), ("HYDROGEL_PACK", 8)):
                rows.append([cells[0], cells[1], product, float(cells[at]), float(cells[at + 1])])
    write("sim_regimes", "uv run python -m experiments.study.sim_regimes: thousands of credits over 10 seeds, and the worst day",
          ["regime", "variant", "product", "pnl_k", "worst_day_k"], rows)


def hydrogel_days() -> None:
    """Chapter 7's story 20: Prosperity 4's Hydrogel on the handed-out round-3 days, its wall mid's range, sd and mean
    per day (the engine's loader), against the live day DTU describes."""
    from arena.formats import prosperity

    rows = []
    for day in prosperity.load_days(prosperity.resolve_data_dir("p4"), ["3"]):
        walls = [t.books["HYDROGEL_PACK"].wall_mid for t in day.ticks
                 if "HYDROGEL_PACK" in t.books and t.books["HYDROGEL_PACK"].wall_mid is not None]
        rows.append([day.name, min(walls), max(walls), round(statistics.pstdev(walls), 1), round(statistics.fmean(walls), 1)])
    write("hydrogel_days", "arena.formats.prosperity.load_days(p4, ['3']): HYDROGEL_PACK's wall mid per day",
          ["day", "low", "high", "sd", "mean"], rows)


STEPS = {"mirror_test": mirror_test, "skew_grid": skew_grid, "osmium_skew": osmium_skew, "coupon_acf": coupon_acf,
         "stress_variants": stress_variants, "level_heldout": level_heldout,
         "glft_skew": glft_skew, "size_controls": size_controls,
         "drift_target": drift_target, "sim_regimes": sim_regimes,
         "hydrogel_days": hydrogel_days}
