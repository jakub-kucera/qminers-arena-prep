"""The Rust port (rust/) against ours: every twin trades the same, then how much faster.

usage (from the repo root; needs cargo): uv run python -m experiments.rust_bench [--jobs N] [--parity-only] [--record]

rust/ ports arena/engine.py whole and the bots listed in rust/twins.json, each with its Python
file as a twin (rust/README.md). Days are loaded by our format plug-ins and exported for it
(arena/rust.py, `export_day`), and each Rust bot reads its settings from its Python file.
  1. parity: every field a DayResult records (fills, orders, cancels, breaches, races, errors, and
     per tick each product's position, mark, PnL, best bid and ask, wall mid), Rust against our
     engine, for bots/mm.py in each engine configuration (CONFIGS) on P3 round 1 day -2; for the
     template in each part of its STRATEGY (VARIANTS, template_cases) on an arena.sim day, and on
     real days from P2 to P4 (REAL); for the rivals (rival_cases); for every zoo bot alone and all in
     one market, on calm and trending arena.sim days and a real one (zoo_parity); for arena.sim's market
     itself, with and without twins trading in it, and their replays (sim_parity). --record then writes
     each twin's hash to rust/twins.json, if every case was identical;
  2. one core: time per backtest of mm, of the template, and of the zoo's whole field in one market, ours (the bot file through the
     Prosperity adapter, loaded per backtest as arena.grid does) against Rust's; and per arena.sim day;
  3. every core: Kelp's 64-cell mm grid on the round's three days under all and worse, arena.grid
     against `arena-rs grid`; and the template's 256-cell Kelp grid, arena.grid end to end with
     --engine python against --engine rust (the same CSV).
Results go into TODO.md (the decisions on the Rust port). tests/test_rust.py runs part 1, shorter.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from arena import grid, rust
from arena.cli import Requote
from arena.engine import EngineConfig, QueueModel, TradeMatching, run_day, run_market
from arena.formats import prosperity
from arena.model import Day

ROOT = Path(__file__).resolve().parent.parent
RUST = rust.RUST
BINARY = rust.BINARY
BOT = ROOT / "bots" / "mm.py"
TEMPLATE = ROOT / "bots" / "template.py"
SAMPLE = 6  # Python backtests timed on one core per measurement

build, export_day = rust.build, rust.export_day


def mm(params: dict) -> dict:
    """bots/mm.py's PARAMS override from {product: (make_edge, take_edge, hold)}."""
    return {"PARAMS": {p: {"make_edge": m, "take_edge": t, "hold": h} for p, (m, t, h) in params.items()}}


# A participant: (name, bot file, overrides, requote). Two products, so the engine's per-product
# paths run; `hold` keeps quotes resting, so their queue position matters.
ONE = [("you", BOT, mm({"KELP": (1, 1, False), "RAINFOREST_RESIN": (2, 1, False)}), False)]
TWO = ONE + [("rival", BOT, mm({"KELP": (0, 1, False), "RAINFOREST_RESIN": (1, 2, False)}), False)]
HOLD = [("you", BOT, mm({"KELP": (1, 1, True), "RAINFOREST_RESIN": (2, 1, True)}), False)]
HOLD_TWO = HOLD + [("rival", BOT, mm({"KELP": (0, 1, True), "RAINFOREST_RESIN": (1, 2, False)}), False)]
ALL, WORSE, NONE = TradeMatching.ALL, TradeMatching.WORSE, TradeMatching.NONE
CONFIGS = [
    ("default, all", EngineConfig(), ONE),
    ("default, worse", EngineConfig(trade_matching=WORSE), ONE),
    ("default, none", EngineConfig(trade_matching=NONE), ONE),
    ("default, fill ratio 0.6", EngineConfig(fill_ratio=0.6, seed=1), ONE),
    ("resting", EngineConfig(resting=True), ONE),
    ("resting, holding, back", EngineConfig(resting=True), HOLD),
    ("resting, holding, back, worse", EngineConfig(resting=True, trade_matching=WORSE), HOLD),
    ("resting, holding, prob", EngineConfig(resting=True, queue=QueueModel.PROB), HOLD),
    ("resting, holding, prob, power 3", EngineConfig(resting=True, queue=QueueModel.PROB, queue_power=3.0), HOLD),
    ("resting, holding, front", EngineConfig(resting=True, queue=QueueModel.FRONT), HOLD),
    ("resting, holding, prob, fill ratio 0.6", EngineConfig(resting=True, queue=QueueModel.PROB, fill_ratio=0.6, seed=2), HOLD),
    ("two bots", EngineConfig(), TWO),
    ("two bots, worse", EngineConfig(trade_matching=WORSE), TWO),
    ("two bots, resting", EngineConfig(resting=True), TWO),
    ("two bots, resting, holding, prob, fill ratio 0.6", EngineConfig(resting=True, queue=QueueModel.PROB, fill_ratio=0.6, seed=3), HOLD_TWO),
]

# The template's settings, each turning on one part of STRATEGY, on a day of KELP (about 2,030)
# and RAINFOREST_RESIN (10,000): (label, --set overrides). Some pair the products in ways that make
# no economic sense (Kelp as a call on Resin), only so the code runs with numbers it can't fold away.
K, R = "PARAMS.KELP.", "PARAMS.RAINFOREST_RESIN."
VARIANTS = [
    ("as committed", {}),
    ("mid", {K + "fair": "mid"}),
    ("wall_mid, smoothing", {K + "fair": "wall_mid", K + "smoothing": 0.6}),
    ("outer_mid", {K + "fair": "outer_mid", K + "make_edge": 1}),
    ("weighted_mid, imbalance", {K + "fair": "weighted_mid", K + "imbalance": 0.7, K + "take_edge": 0.5}),
    ("skew, size_skew, target, make_size", {K + "skew": 3, K + "size_skew": 0.8, K + "target": 12, K + "make_size": 9, K + "clear_edge": 1}),
    ("level: the day's mean, exit", {K + "level": "day", K + "level_band": 2, K + "level_exit": 0, K + "clear_edge": 2}),
    ("level: a number, weight, guard", {K + "level": 2031, K + "level_weight": 500, K + "level_band": 2.5, K + "level_guard": 2, K + "clear_edge": 1}),
    ("stop loss that fires", {K + "stop_loss": 3, R + "stop_loss": 2, R + "stop_edge": 1}),
    ("flatten before the close", {K + "flatten_from": 120_000, R + "flatten_from": 150_000, R + "flatten_edge": 2}),
    ("vol guard", {K + "vol_guard": 1.3, K + "level": "day", K + "level_band": 2}),
    ("changepoint, level", {K + "level": 2031, K + "level_band": 2, K + "cpd_hazard": 3000, K + "cpd_reversion": 0.02, K + "cpd_sd": 1.2, K + "cpd_block": 20}),
    ("changepoint, drop", {K + "level": 2031, K + "level_band": 2, K + "cpd_hazard": 3000, K + "cpd_reversion": 0.02, K + "cpd_sd": 1.2,
                           K + "cpd_block": 20, K + "cpd_action": "drop", K + "cpd_threshold": 0.3}),
    ("jumps", {K + "jump_min": 0.5, K + "jump_seen": 2, K + "jump_share": 0.3, K + "jump_hold": 15, K + "jump_edge": 2}),
    ("copy: our own fills and a rival", {K + "copy": {"SUBMISSION": 0.4, "rival": -1.5}, K + "copy_hold": 30}),
    ("basket with a hedged leg", {R + "basket": {"KELP": 5}, R + "fair": "wall_mid", R + "level": "day", R + "level_band": 3, R + "hedge_ratio": 0.5,
                                  R + "make_size": 0, K + "hedge": True}),
    ("follow: a call on the other", {R + "level": "day", R + "level_band": 1, R + "fair": "wall_mid", K + "follow": "RAINFOREST_RESIN",
                                     K + "strike": 9000, K + "fair": "wall_mid", K + "max_cost_per_delta": 50, K + "clear_edge": 3}),
    ("smile, hedged", {K + "smile": (0.05, 0.01, 0.15), K + "underlying": "RAINFOREST_RESIN", K + "strike": 9000, K + "expiry": 3, K + "hedge_ratio": 0.6,
                       K + "fair": "wall_mid", R + "hedge": True}),
]


def template_cases(variants=VARIANTS) -> list[tuple[str, EngineConfig, list]]:
    """Every variant on its own (per tick) and in a resting market with a rival (prob queue, a fill
    ratio), plus the committed settings in every configuration with a rival or a copy."""
    def bots(overrides, rivals=()):
        return [("you", TEMPLATE, {k: v for k, v in overrides.items()}, False), *rivals]
    rival = ("rival", BOT, mm({"KELP": (1, 1, True), "RAINFOREST_RESIN": (1, 1, True)}), False)
    resting = EngineConfig(resting=True, queue=QueueModel.PROB, fill_ratio=0.7, seed=4)
    cases = [(f"{label}, default", EngineConfig(), bots(o, [rival])) for label, o in variants]
    cases += [(f"{label}, resting with a rival", resting, bots(o, [rival])) for label, o in variants]
    committed = dict(variants)["as committed"] if "as committed" in dict(variants) else {}
    copy = ("template#2", TEMPLATE, {K + "make_edge": 1}, False)
    cases += [
        ("as committed, worse", EngineConfig(trade_matching=WORSE), bots(committed)),
        ("as committed, none, fill ratio 0.5", EngineConfig(trade_matching=NONE, fill_ratio=0.5, seed=7), bots(committed)),
        ("as committed, resting, back", EngineConfig(resting=True), bots(committed)),
        ("as committed, resting, front, worse", EngineConfig(resting=True, queue=QueueModel.FRONT, trade_matching=WORSE), bots(committed)),
        ("as committed against a copy, resting", EngineConfig(resting=True), bots(committed, [copy])),
        ("as committed against a requoted mm, resting", EngineConfig(resting=True), bots(committed, [("mm", BOT, mm({"KELP": (0, 1, False)}), True)])),
    ]
    return cases


RIVALS = {name: ROOT / "bots" / "rivals" / f"{name}.py" for name in ("sniper", "spoofer", "trapper")}


def rival_cases() -> list[tuple[str, EngineConfig, list]]:
    """bots/rivals/ against the template and mm: resting (where the rivals mean something), per
    tick, with --set changes to their constants, and all three in one market."""
    template = ("template", TEMPLATE, {}, False)
    holding = ("mm", BOT, mm({"KELP": (1, 1, True), "RAINFOREST_RESIN": (2, 1, True)}), False)
    resting, prob = EngineConfig(resting=True), EngineConfig(resting=True, queue=QueueModel.PROB, fill_ratio=0.8, seed=5)
    cases = []
    for name, path in RIVALS.items():
        rival = (name, path, {}, False)
        cases += [(f"template against the {name}, resting", resting, [template, rival]),
                  (f"template against the {name}, per tick", EngineConfig(), [template, rival]),
                  (f"mm holding against the {name}, resting, prob, fill ratio", prob, [holding, rival])]
    cases += [
        ("the spoofer 3 ticks behind, flipping every 50", resting, [template, ("spoofer", RIVALS["spoofer"], {"OFFSET": 3, "PERIOD": 50}, False)]),
        ("a small trapper with a short cooldown", resting, [template, ("trapper", RIVALS["trapper"], {"BAIT": 12, "PERIOD": 60, "COOLDOWN": 5}, False)]),
        ("the sniper at edge 0, Kelp's limit 20", resting, [template, ("sniper", RIVALS["sniper"], {"EDGE": 0, "LIMITS.KELP": 20}, False)]),
        ("all three against the template, resting, worse", EngineConfig(resting=True, trade_matching=WORSE),
         [template, *[(name, path, {}, False) for name, path in RIVALS.items()]]),
    ]
    return cases


DRILL = ROOT / "bots" / "drill" / "template.py"


def drill_days(scratch: Path, ticks: int = 2000) -> list[Day]:
    """Drill-format days as experiments/format_drill.py makes them: arena.sim's P3 round 1 presets
    (Kelp, Resin and Squid Ink become ALPHA, BETA and GAMMA, on ticks of 0.05, 0.01 and 0.25),
    converted, then loaded by the drill plug-in (prices in cents, Day.info's ticks)."""
    from arena import sim
    from arena.formats import drill

    spec = sim.preset_market(ticks=ticks)
    for k, seed in enumerate((1000, 1001)):
        sim.write_day(sim.run(spec, seed), scratch / "prosperity", 1, k)
    drill.convert(scratch / "prosperity", 1, scratch / "drill")
    return drill.load_days(scratch / "drill", ["all"])


def drill_cases() -> list[tuple[str, EngineConfig, list]]:
    """bots/drill/template.py: as committed in every queue model and mode (the format rests; per
    tick too), against a copy, and each part of STRATEGY in VARIANTS on its products (in ticks, the
    same numbers as on the Prosperity day they were converted from)."""
    rename = {"KELP": "ALPHA", "RAINFOREST_RESIN": "BETA", "SQUID_INK": "GAMMA"}

    def drilled(overrides: dict) -> dict:
        text = json.dumps(overrides)
        for old, new in rename.items():
            text = text.replace(old, new)
        return {k: tuple(v) if isinstance(v, list) else v for k, v in json.loads(text).items()}

    me = lambda o: ("you", DRILL, o, False)
    resting = EngineConfig(resting=True)
    cases = [("as committed, resting, back", resting, [me({})]),
             ("as committed, resting, prob, worse", EngineConfig(resting=True, queue=QueueModel.PROB, trade_matching=WORSE), [me({})]),
             ("as committed, resting, front, fill ratio 0.7", EngineConfig(resting=True, queue=QueueModel.FRONT, fill_ratio=0.7, seed=8), [me({})]),
             ("as committed, per tick", EngineConfig(), [me({})]),
             ("against a copy at make_edge 0, resting", resting, [me({}), ("copy", DRILL, {"PARAMS.ALPHA.make_edge": 0}, False)])]
    cases += [(f"{label}, resting", resting, [me(drilled(o))]) for label, o in VARIANTS if label != "as committed"]
    return cases


def zoo_twins() -> list[Path]:
    """The zoo bots with a Rust twin."""
    return [ROOT / path for path in rust.twins() if path.startswith("bots/zoo/")]


def zoo_days(ticks: int = 2000) -> list[tuple[str, Day]]:
    """The days the zoo twins are checked on: arena.sim's three P3 round 1 products as they are, and
    trending hard up and down (arena.stress, 60 spreads over the day), where the trend followers trade;
    and a day with Kelp and two products the zoo's prompt never named (most of them raise on it, or
    trade it with limits they made up)."""
    from arena import sim, stress

    day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN", "SQUID_INK"]), 5).day
    other = sim.run(sim.preset_market(["KELP", "ROBOT_DISHES", "HYDROGEL_PACK"]), 6).day
    days = [("a simulated day", day), ("trending up", stress.perturb(day, "trend_up", 60)), ("trending down", stress.perturb(day, "trend_down", 60)),
            ("other products", other)]
    return [(label, replace(d, ticks=d.ticks[:ticks])) for label, d in days]


def zoo_parity(scratch: Path, days: list[tuple[str, Day]], paths: list[Path] | None = None) -> list[tuple[str, tuple, list[str]]]:
    """zoo_cases on each of the days."""
    return [(f"{label}: {case}", counts, found) for label, day in days for case, counts, found in parity(day, scratch, zoo_cases(paths))]


def zoo_cases(paths: list[Path] | None = None) -> list[tuple[str, EngineConfig, list]]:
    """Each zoo twin alone (all, worse, a fill ratio, resting as written, resting requoted), then
    all of them with the template in one market, per tick and resting (requoted, as
    experiments/zoo.py runs them)."""
    paths = zoo_twins() if paths is None else paths
    cases = []
    for path in paths:
        name = path.relative_to(ROOT / "bots" / "zoo").as_posix()
        alone = [(path.stem, path, {}, False)]
        cases += [(f"{name}, all", EngineConfig(), alone),
                  (f"{name}, worse", EngineConfig(trade_matching=WORSE), alone),
                  (f"{name}, fill ratio 0.7", EngineConfig(fill_ratio=0.7, seed=6), alone),
                  (f"{name}, resting as written", EngineConfig(resting=True), alone),
                  (f"{name}, resting requoted, prob", EngineConfig(resting=True, queue=QueueModel.PROB), [(path.stem, path, {}, True)])]
    field = [("template", TEMPLATE, {}, False)]
    names = [p.stem for p in paths]
    field += [(stem if names.count(stem) == 1 else f"{p.parent.name}/{stem}", p, {}, False) for stem, p in zip(names, paths)]
    if paths:
        cases += [("the field: the template and every zoo twin, all", EngineConfig(), field),
                  ("the field, resting, the zoo requoted", EngineConfig(resting=True), [field[0]] + [(n, p, o, True) for n, p, o, _ in field[1:]])]
    return cases


def _python_bot(path: Path, overrides: dict, requote: bool):
    from arena.formats import FORMATS

    bot = FORMATS[rust.format_of(path)].load_bot(path, overrides, strict=True)
    return Requote(bot) if requote else bot


def _error(text: str) -> str:
    """A bot's exception as its traceback's last line (a Rust twin reports that line); the engine's own errors whole."""
    return text.strip().splitlines()[-1] if text.startswith("Traceback") else text


def python_view(result) -> dict:
    """The same fields from our engine's DayResult."""
    return {
        "fills": [(f.timestamp, f.product, f.price, f.quantity, f.source, f.order_id, f.counterparty) for f in result.fills],
        "orders": [(ts, o.id, o.product, o.price, o.quantity, o.timestamp) for ts, o in result.orders],
        "cancels": list(result.cancels),
        "breaches": list(result.limit_breaches),
        "races": list(result.races),
        "errors": [(ts, _error(text)) for ts, text in result.errors],
        "market_trades": len(result.market_trades),
        "series": {p: {field: getattr(result, field)[p] for field in rust.SERIES} for p in sorted(result.products)},
    }


def _first(a: list, b: list) -> int:
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def differences(ours: dict, theirs: dict) -> list[str]:
    """Where two views disagree: the first difference per field, with its index."""
    found = []
    for key, a in ours.items():
        b = theirs[key]
        if key == "series":
            for product, fields in a.items():
                for field, values in fields.items():
                    other = b[product][field]
                    if values != other:
                        k = _first(values, other)
                        found.append(f"{product} {field}[{k}]: {values[k:k + 1]} against {other[k:k + 1]} ({len(values)} / {len(other)} values)")
        elif isinstance(a, list) and a != b:
            k = _first(a, b)
            found.append(f"{key}[{k}]: {a[k:k + 1]} against {b[k:k + 1]} ({len(a)} / {len(b)})")
        elif a != b:
            found.append(f"{key}: {a} against {b}")
    return found


_CASE: dict = {}  # set per worker process by _init_case: the day and its exported file


def _init_case(day: Day, path: Path, scratch: Path) -> None:
    _CASE.update(day=day, path=path, scratch=scratch)


def _run_case(k: int, label: str, config: EngineConfig, bots: list) -> tuple[str, tuple, list[str]]:
    """One case in both engines: (label, (fills, cross fills, races, breaches, the first participant's PnL), differences)."""
    day, path, scratch = _CASE["day"], _CASE["path"], _CASE["scratch"]
    args = []
    for j, (name, bot, overrides, requote) in enumerate(bots):
        spec = scratch / f"case{k}_bot{j}.json"
        spec.write_text(json.dumps(rust.bot_spec(bot, overrides, requote)))
        args += ["--bot", f"{name}={spec}"]
    dump = scratch / f"case{k}_dump.txt"
    run = subprocess.run([str(BINARY), "run", str(path), *_rust_engine(config), *args, "--dump", str(dump)], capture_output=True, text=True)
    if run.returncode != 0:
        return label, (0, 0, 0, 0, 0.0), [f"arena-rs failed: {run.stderr.strip()}"]
    theirs = rust.read_dump(dump.read_text())
    ours = run_market(day, [(name, _python_bot(bot, overrides, requote)) for name, bot, overrides, requote in bots], config)
    found = [f"{name}: {d}" for (name, *_), result in zip(bots, ours) for d in differences(python_view(result), theirs[name])]
    counts = (sum(len(r.fills) for r in ours), sum(f.source == "cross" for r in ours for f in r.fills),
              sum(len(r.races) for r in ours), sum(len(r.limit_breaches) for r in ours), sum(s[-1] for s in ours[0].pnl.values() if s))
    return label, counts, found


def parity(day: Day, scratch: Path, configs=CONFIGS, jobs: int | None = None) -> list[tuple[str, tuple, list[str]]]:
    """Each case (label, config, participants) on the day in both engines, on `jobs` processes
    (default: every core): (label, (fills, cross fills, races, breaches, the first participant's
    PnL), differences), in the cases' order."""
    path = scratch / (day.name.replace("/", "_") + ".day")
    export_day(day, path)
    jobs = jobs or os.cpu_count() or 1
    cases = [(k, *case) for k, case in enumerate(configs)]
    if jobs <= 1 or len(cases) <= 1:
        _init_case(day, path, scratch)
        return [_run_case(*case) for case in cases]
    with ProcessPoolExecutor(min(jobs, len(cases)), initializer=_init_case, initargs=(day, path, scratch)) as pool:
        return list(pool.map(_run_case, *zip(*cases)))


_rust_engine = rust._engine_args


# ---------------------------------------------------------------------------- arena.sim


def _days_differ(a: Day, b: Day) -> str | None:
    """Where two recordings differ: books, trades (and their order by product), marks (and whether an int)."""
    if (a.name, a.products, a.limits, len(a.ticks)) != (b.name, b.products, b.limits, len(b.ticks)):
        return f"day {a.name} {a.products} {len(a.ticks)} ticks against {b.name} {b.products} {len(b.ticks)}"
    for k, (s, t) in enumerate(zip(a.ticks, b.ticks)):
        for field in ("timestamp", "books", "trades", "marks"):
            x, y = getattr(s, field), getattr(t, field)
            if x != y or (isinstance(x, dict) and list(x) != list(y)):
                return f"tick {k} {field}: {x} against {y}"
        if any(type(s.marks[p]) is not type(t.marks[p]) for p in s.marks):
            return f"tick {k} marks: {s.marks} against {t.marks} (int against float)"
    return None


def _run_sim_case(label: str, spec, seed: int, bots: list, config: EngineConfig) -> tuple[str, tuple, list[str]]:
    """One arena.sim case in both: the recording, the fundamental, every bot's DayResult in the
    market, and its replays on the day without it under each trade matching."""
    from arena import sim

    ours = sim.run(spec, seed, [(name, _python_bot(bot, overrides, requote)) for name, bot, overrides, requote in bots], resting=config.resting)
    theirs = rust.run_sim(spec, seed, bots=bots, config=config, replay=bool(bots), read=True)[0]
    found = []
    if (d := _days_differ(ours.day, theirs["sim"].day)) is not None:
        found.append(f"recording: {d}")
    if ours.fundamentals != theirs["sim"].fundamentals:
        found.append("the fundamental differs")
    for (name, *_), a, b in zip(bots, ours.results, theirs["sim"].results):
        found += [f"{name}: {d}" for d in differences(python_view(a), python_view(b))]
    if bots:
        recording = sim.run(spec, seed).day
        for mode, results in theirs["replay_results"].items():
            replays = run_market(recording, [(name, _python_bot(bot, overrides, requote)) for name, bot, overrides, requote in bots],
                                 replace(config, trade_matching=mode))
            for (name, *_), a, b in zip(bots, replays, results):
                found += [f"{name}, replay {mode}: {d}" for d in differences(python_view(a), python_view(b))]
    rs = ours.results
    counts = (sum(len(r.fills) for r in rs), 0, sum(len(r.races) for r in rs), sum(len(r.limit_breaches) for r in rs),
              sum(s[-1] for s in rs[0].pnl.values() if s) if rs else 0.0)
    return label, counts, found


def sim_cases(ticks: int = 2000) -> list[tuple]:
    """arena.sim with twins in it: (label, spec, seed, participants, config). Every preset, both
    modes, regimes, the agents shown by name (for the template's copy), the maker among the takers
    with skew, several bots racing in one market, and bots that raise."""
    from arena import sim

    p3 = sim.preset_market(ticks=ticks)
    named = sim.preset_market(ticks=ticks, names=True)
    others = sim.preset_market(["KELP_FLOW", "ROBOT_DISHES", "HYDROGEL_PACK"], ticks=ticks)
    skewed = sim.with_override(sim.with_override(p3, "KELP.maker.first", False), "KELP.maker.skew", 0.1)
    template = ("template", TEMPLATE, {}, False)
    holding = ("mm", BOT, mm({"KELP": (1, 1, True), "RAINFOREST_RESIN": (2, 1, True)}), False)
    resting, prob = EngineConfig(resting=True), EngineConfig(resting=True, queue=QueueModel.PROB)
    jumps = {"PARAMS.ROBOT_DISHES": {"limit": 10, "fair": "wall_mid", "make_edge": 1, "jump_min": 50, "jump_edge": 10, "jump_seen": 5, "jump_share": 0.6},
             "PARAMS.HYDROGEL_PACK": {"limit": 200, "fair": "wall_mid", "level": "day", "level_band": 5}, "PARAMS.KELP_FLOW": {"limit": 50, "fair": "wall_mid"}}
    zoo = [(p.stem if [q.stem for q in zoo_twins()].count(p.stem) == 1 else f"{p.parent.name}/{p.stem}", p, {}, False) for p in zoo_twins()]
    return [
        ("no bots", p3, 3, [], EngineConfig()),
        ("the template, per tick", p3, 3, [template], EngineConfig()),
        ("the template, resting", p3, 3, [template], resting),
        ("the template against mm holding, resting, prob", p3, 4, [template, holding], prob),
        ("the template copying the noise takers, agents named", named, 5,
         [("template", TEMPLATE, {"PARAMS.KELP.copy": {"noise": 1.0}, "PARAMS.KELP.copy_hold": 20}, False)], EngineConfig()),
        ("the template on a trend up", sim.with_regime(p3, "trend_up"), 6, [template], resting),
        ("the template on a shift down, per tick", sim.with_regime(p3, "shift_down", 0.3), 6, [template], EngineConfig()),
        ("Kelp's maker among the takers, skewed", skewed, 7, [template, holding], resting),
        ("other presets: jumps, a level, one-sided flow", others, 8, [("template", TEMPLATE, jumps, False)], EngineConfig()),
        ("other presets, resting", others, 8, [("template", TEMPLATE, jumps, False)], resting),
        ("the rivals against the template, resting", p3, 9, [template, *[(n, path, {}, False) for n, path in RIVALS.items()]], resting),
        ("the template and every zoo twin, per tick", p3, 10, [template, *zoo], EngineConfig()),
        ("the template and every zoo twin requoted, resting", p3, 10, [template, *[(n, path, o, True) for n, path, o, _ in zoo]], resting),
        ("the drill template in the market (prices in its unit)", p3, 11, [("drill", DRILL, {"PARAMS.KELP": {"fair": "wall_mid", "make_edge": 1}}, False)], resting),
    ]


def stats_cases() -> list[tuple[str, str, dict]]:
    """arena/stats.py's heavy statistics on inputs that exercise them: (label, function, arguments).
    CSCV with every halving and with sampled ones, ties in the ranks, a constant cell, one cell;
    the correlation of standardized cells; SPA and StepM with no gain, with planted gains, and with
    many cells."""
    import random

    from arena import stats

    r = random.Random(42)
    noise = lambda n, s, mu=0.0: [[r.gauss(mu, 1) for _ in range(s)] for _ in range(n)]
    whole = lambda n, s: [[float(r.randint(-3, 3)) for _ in range(s)] for _ in range(n)]
    planted = noise(40, 300) + noise(5, 300, 0.3)
    return [
        ("cscv, 8 blocks: every halving", "cscv", {"columns": noise(30, 8)}),
        ("cscv, 18 blocks: 4,000 sampled halvings", "cscv", {"columns": noise(200, 18)}),
        ("cscv, 16 blocks, 500 sampled, seed 3", "cscv", {"columns": noise(50, 16, 0.1), "max_splits": 500, "seed": 3}),
        ("cscv, whole numbers: tied ranks", "cscv", {"columns": whole(60, 12)}),
        ("cscv, a constant cell and two cells", "cscv", {"columns": [[1.0] * 10, [r.gauss(0, 1) for _ in range(10)]]}),
        ("correlation of 300 cells", "mean_correlation", {"scaled": stats.standardized(noise(300, 18))}),
        ("correlation of correlated cells", "mean_correlation", {"scaled": stats.standardized([[x + r.gauss(0, 0.3) for x in base] for base in noise(1, 18) for _ in range(50)])}),
        ("correlation of one cell", "mean_correlation", {"scaled": stats.standardized(noise(1, 18))}),
        ("SPA and StepM, no gain", "snooping", {"d": noise(30, 120), "q": 0.1, "boot": 500}),
        ("SPA and StepM, five planted gains", "snooping", {"d": planted, "q": 0.1, "boot": 1000}),
        ("SPA and StepM, 400 cells, seed 7, alpha 0.1", "snooping", {"d": noise(400, 60, 0.05), "q": 0.2, "boot": 300, "alpha": 0.1, "seed": 7}),
        ("SPA and StepM, whole numbers", "snooping", {"d": whole(20, 50), "q": 0.1, "boot": 200}),
    ]


def _run_stats_case(label: str, name: str, arguments: dict) -> tuple[str, tuple, list[str]]:
    from arena import stats

    ours, theirs = getattr(stats, name)(**arguments), getattr(rust, name)(**arguments)
    found = [] if ours == theirs else [f"{name}: {ours} against {theirs}"]
    return label, (0, 0, 0, 0, 0.0), found


def stats_parity(jobs: int | None = None) -> list[tuple[str, tuple, list[str]]]:
    """stats_cases in both, on `jobs` processes."""
    cases = stats_cases()
    with ProcessPoolExecutor(min(jobs or os.cpu_count() or 1, len(cases))) as pool:
        return list(pool.map(_run_stats_case, *zip(*cases)))


def sim_parity(ticks: int = 2000, jobs: int | None = None, cases=None) -> list[tuple[str, tuple, list[str]]]:
    """sim_cases in both, on `jobs` processes."""
    cases = sim_cases(ticks) if cases is None else cases
    jobs = jobs or os.cpu_count() or 1
    if jobs <= 1 or len(cases) <= 1:
        return [_run_sim_case(*case) for case in cases]
    with ProcessPoolExecutor(min(jobs, len(cases))) as pool:
        return list(pool.map(_run_sim_case, *zip(*cases)))


# ---------------------------------------------------------------------------- timing


def python_time(day: Day, config: EngineConfig) -> tuple[float, float]:
    """Seconds per backtest of bots/mm.py as committed (Kelp only), loaded per backtest as arena.grid
    does, and the share of it in the bot's step (the Prosperity adapter included)."""
    start, in_bot = time.perf_counter(), 0.0
    for _ in range(SAMPLE):
        result = run_day(day, prosperity.load_bot(BOT, {}, strict=False), config)
        in_bot += sum(result.step_seconds)
    total = time.perf_counter() - start
    return total / SAMPLE, in_bot / total


def rust_grid(paths: list[Path], config: EngineConfig, threads: int, repeat: int, edges=(1,), modes="all") -> tuple[float, float, str]:
    """`arena-rs grid`: (thread-seconds per backtest, wall seconds per repeat, its CSV)."""
    values = ",".join(map(str, edges))
    out = subprocess.run([str(BINARY), "grid", *map(str, paths), *_rust_engine(config), "--make", values, "--take", values, "--modes", modes,
                          "--threads", str(threads), "--repeat", str(repeat)], check=True, capture_output=True, text=True)
    match = re.search(r"in ([\d.]+) s: ([\d.]+) ms of a thread each", out.stderr)
    return float(match.group(2)) / 1e3, float(match.group(1)) / repeat, out.stdout


def template_time(day: Day, path: Path, config: EngineConfig, scratch: Path) -> tuple[float, float]:
    """Seconds per backtest of bots/template.py as committed: ours (loaded per backtest), and the
    Rust twin's (`arena-rs batch` on one thread, 41 tasks less 1 to leave out loading)."""
    start = time.perf_counter()
    for _ in range(SAMPLE):
        run_day(day, prosperity.load_bot(TEMPLATE, {}, strict=False), config)
    ours = (time.perf_counter() - start) / SAMPLE
    spec = rust.bot_spec(TEMPLATE, {})
    task = {"day": 0, "config": rust.config_json(config), "bots": [["template", 0]], "blocks": 2, "fine": 10}
    seconds = []
    for n in (1, 41):
        start = time.perf_counter()
        rust.run_batch([path], [spec], [task] * n, 1, scratch)
        seconds.append(time.perf_counter() - start)
    return ours, (seconds[1] - seconds[0]) / 40


def _grid_wall(engine: str, jobs: int, out: Path) -> float:
    start = time.perf_counter()
    subprocess.run([sys.executable, "-m", "arena.grid", str(TEMPLATE), "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0..15",
                    "--grid", "PARAMS.KELP.take_edge=0..15", "--modes", "all,worse", "--jobs", str(jobs), "--engine", engine, "--out", str(out)],
                   check=True, capture_output=True)
    return time.perf_counter() - start


def field_time(day: Day, path: Path, config: EngineConfig, scratch: Path) -> tuple[int, float, float]:
    """The template and every zoo twin in one market: (participants, Python seconds, Rust seconds
    on one thread, 5 runs less 1 to leave out loading)."""
    field = [("template", TEMPLATE)] + [(p.relative_to(ROOT / "bots" / "zoo").as_posix(), p) for p in zoo_twins()]
    start = time.perf_counter()
    run_market(day, [(name, prosperity.load_bot(p, {}, strict=False)) for name, p in field], config)
    ours = time.perf_counter() - start
    specs = [rust.bot_spec(p, {}) for _, p in field]
    task = {"day": 0, "config": rust.config_json(config), "bots": [[name, k] for k, (name, _) in enumerate(field)], "blocks": 2, "fine": 10}
    seconds = []
    for n in (1, 5):
        start = time.perf_counter()
        rust.run_batch([path], specs, [task] * n, 1, scratch)
        seconds.append(time.perf_counter() - start)
    return len(field), ours, (seconds[1] - seconds[0]) / 4


def sim_time(bots: list, config: EngineConfig) -> tuple[float, float]:
    """Seconds per arena.sim day: ours, and Rust's (61 days less 1 on one thread, to leave out starting it)."""
    from arena import sim

    spec = sim.preset_market()
    start = time.perf_counter()
    for seed in range(2):
        sim.run(spec, seed, [(name, _python_bot(bot, o, r)) for name, bot, o, r in bots], resting=config.resting)
    ours = (time.perf_counter() - start) / 2
    seconds = []
    for n in (1, 61):
        start = time.perf_counter()
        rust.run_sim(spec, 0, n, bots, config)
        seconds.append(time.perf_counter() - start)
    return ours, (seconds[1] - seconds[0]) / 60


def _report(label: str, counts: tuple, found: list[str], width: int = 58) -> bool:
    fills, crossed, races, breaches, pnl = counts
    print(f"   {label:<{width}} {fills:>6,} fills ({crossed:,} crossed), {races} races, {breaches} breaches, PnL {pnl:>9,.0f}: "
          + ("identical" if not found else f"! {len(found)} differences: {found[0]}"))
    return not found


# Real days for the template: (data, round, what it exercises, --set overrides), each on the round's
# first day, the committed settings unless the label says otherwise.
REAL = [
    ("p2", "1", "Amethysts (fixed fair) and Starfruit", {}),
    ("p2", "3", "the gift basket against its legs", {}),
    ("p3", "1", "Kelp, Resin (stop losses, fixed guard)", {}),
    ("p3", "2", "the picnic baskets", {}),
    ("p3", "3", "Volcanic Rock (the day's level) and its vouchers (follow)", {}),
    ("p3", "3", "a voucher priced off a smile, hedged", {"PARAMS.VOLCANIC_ROCK_VOUCHER_10000": {
        "limit": 200, "fair": "wall_mid", "smile": [0.25, 0.0, 0.16], "underlying": "VOLCANIC_ROCK", "strike": 10000, "expiry": 5,
        "hedge_ratio": 0.5, "make_size": 20}}),
    ("p3", "5", "copying Olivia", {"PARAMS.SQUID_INK": {"limit": 50, "fair": "wall_mid", "copy": {"Olivia": 1}, "copy_edge": 5}}),
    ("p4", "1", "Osmium (smoothing), Pepper Root (target, skew, make_size)", {}),
    ("p4", "3", "Hydrogel, Velvetfruit (levels) and the VEV vouchers", {}),
    ("p4", "5", "fading Robot Dishes' jumps", {"PARAMS.ROBOT_DISHES": {"limit": 10, "fair": "wall_mid", "make_edge": 1, "jump_min": 50,
                                                                     "jump_edge": 10, "jump_seen": 5, "jump_share": 0.6}}),
]
REAL_CONFIGS = [("default", EngineConfig()), ("resting, prob, worse", EngineConfig(resting=True, queue=QueueModel.PROB, trade_matching=WORSE))]


def real_parity(scratch: Path, ticks: int | None = None, real=REAL) -> list[tuple[str, tuple, list[str]]]:
    """REAL in both engines, each case under REAL_CONFIGS (on the first `ticks` ticks if given)."""
    out = []
    for data, round_, label, overrides in real:
        day = prosperity.load_days(prosperity.resolve_data_dir(data), [round_])[0]
        day = replace(day, ticks=day.ticks[:ticks]) if ticks else day
        cases = [(f"{data} {day.name}: {label}, {name}", config, [("you", TEMPLATE, overrides, False)]) for name, config in REAL_CONFIGS]
        out += parity(day, scratch, cases)
    return out


def sim_day(ticks: int = 2000) -> Day:
    """The day VARIANTS are written for: arena.sim's Kelp and Resin, seed 5."""
    from arena import sim

    day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), 5).day
    return replace(day, ticks=day.ticks[:ticks])


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.rust_bench")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--parity-only", action="store_true")
    parser.add_argument("--record", action="store_true",
                        help="with every case identical, record each twin's Python file as checked (rust/twins.json)")
    args = parser.parse_args()
    build()
    days = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["1"])
    with tempfile.TemporaryDirectory() as folder:
        scratch = Path(folder)
        same = True
        print(f"1. parity, every recorded field. bots/mm.py against rust/src/bots/mm.rs on {days[0].name}:")
        for label, counts, found in parity(days[0], scratch):
            same &= _report(label, counts, found)
        print("   bots/template.py against rust/src/bots/template.rs, each part of STRATEGY on arena.sim's Kelp and Resin (2,000 ticks):")
        for label, counts, found in parity(sim_day(), scratch, template_cases()):
            same &= _report(label, counts, found)
        print("   bots/rivals/ against rust/src/bots/rivals.rs, on the same day:")
        for label, counts, found in parity(sim_day(), scratch, rival_cases()):
            same &= _report(label, counts, found)
        print("   bots/zoo/ against rust/src/bots/zoo/, on arena.sim days (2,000 ticks) and the first day of P2, P3 and P4 round 1, whole:")
        real = [(f"{data.upper()} {day.name}", day) for data in ("p2", "p3", "p4") for day in prosperity.load_days(prosperity.resolve_data_dir(data), ["1"])[:1]]
        for label, counts, found in zoo_parity(scratch, [*zoo_days(), *real]):
            same &= _report(label, counts, found, 90)
        print("   ... and the template on real days, whole:")
        for label, counts, found in real_parity(scratch):
            same &= _report(label, counts, found, 80)
        print("   bots/drill/template.py against rust/src/bots/template.rs's drill ADAPTER, on two drill-format days (2,000 ticks):")
        for day in drill_days(scratch):
            for label, counts, found in parity(day, scratch, drill_cases()):
                same &= _report(f"{day.name}: {label}", counts, found, 80)
        print("   arena/stats.py against rust/src/stats.rs:")
        for label, counts, found in stats_parity(args.jobs):
            print(f"   {label:<58} " + ("identical" if not found else f"! {found[0]}"))
            same &= not found
        print("   arena/sim.py against rust/src/sim.rs, the market with twins in it and their replays (2,000 ticks):")
        for label, counts, found in sim_parity(2000, args.jobs):
            same &= _report(label, counts, found, 80)
        print("   all identical" if same else "   ! differences")
        if args.record:
            if not same:
                sys.exit("not recorded: the twins differ")
            rust.record_hashes()
            print(f"   recorded in {rust.TWINS.relative_to(ROOT)}")
        if args.parity_only:
            return

        full = [scratch / f"{day.name}.day" for day in days]
        kelp = [scratch / f"{day.name}.kelp.day" for day in days]
        for day, a, b in zip(days, full, kelp):
            export_day(day, a)
            export_day(grid.only(day, ["KELP"]), b)
        print(f"\n2. one core, per backtest of a {len(days[0].ticks):,}-tick day (Python: the bot file through the Prosperity adapter, "
              "loaded per backtest). bots/mm.py on Kelp:")
        for label, day, path, config in (("all three products, default", days[0], full[0], EngineConfig()),
                                         ("all three products, resting", days[0], full[0], EngineConfig(resting=True)),
                                         ("Kelp only, default", grid.only(days[0], ["KELP"]), kelp[0], EngineConfig())):
            ours, share = python_time(day, config)
            theirs = rust_grid([path], config, 1, 200)[0]
            print(f"   {label:<30} Python {ours * 1e3:6.1f} ms ({share:.0%} in the bot)   Rust {theirs * 1e3:6.3f} ms   {ours / theirs:,.0f}x")
        print("   bots/template.py as committed (Kelp and Resin):")
        for label, day, path, config in (("all three products, default", days[0], full[0], EngineConfig()),
                                         ("all three products, resting", days[0], full[0], EngineConfig(resting=True)),
                                         ("Kelp only, default", grid.only(days[0], ["KELP"]), kelp[0], EngineConfig())):
            ours, theirs = template_time(day, path, config, scratch)
            print(f"   {label:<30} Python {ours * 1e3:6.1f} ms   Rust {theirs * 1e3:6.3f} ms   {ours / theirs:,.0f}x")

        print("   the template and every zoo bot in one market (P3 round 1, all three products):")
        for label, config in (("default", EngineConfig()), ("resting", EngineConfig(resting=True))):
            n, ours, theirs = field_time(days[0], full[0], config, scratch)
            print(f"   {label:<30} {n} bots: Python {ours:6.1f} s   Rust {theirs * 1e3:6.1f} ms   {ours / theirs:,.0f}x")

        print("   arena.sim, one 10,000-tick day of P3 round 1's presets (Python: arena.sim.run; Rust: arena-rs sim, totals only):")
        for label, bots, config in (("no bots", [], EngineConfig()), ("the template, per tick", [("template", TEMPLATE, {}, False)], EngineConfig()),
                                    ("the template, resting", [("template", TEMPLATE, {}, False)], EngineConfig(resting=True))):
            ours, theirs = sim_time(bots, config)
            print(f"   {label:<30} Python {ours * 1e3:6.0f} ms   Rust {theirs * 1e3:6.1f} ms   {ours / theirs:,.0f}x")

        edges = range(8)
        print(f"\n3. every core ({args.jobs}). Kelp's 64-cell mm grid on {len(days)} days under all and worse (384 backtests):")
        sys.stdout.flush()
        start = time.perf_counter()
        subprocess.run([sys.executable, "-m", "arena.grid", str(BOT), "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0..7",
                        "--grid", "PARAMS.KELP.take_edge=0..7", "--modes", "all,worse", "--jobs", str(args.jobs)], check=True, capture_output=True)
        python_wall = time.perf_counter() - start
        _, rust_kelp, csv_kelp = rust_grid(kelp, EngineConfig(), args.jobs, 20, edges, "all,worse")
        _, rust_full, csv_full = rust_grid(full, EngineConfig(), args.jobs, 20, edges, "all,worse")
        same = [line.split(",")[4] for line in csv_kelp.splitlines()[1:]] == [line.split(",")[4] for line in csv_full.splitlines()[1:]]
        print(f"   arena.grid (its checks, Kelp-only days): {python_wall:.1f} s;  arena-rs grid: {rust_kelp * 1e3:.0f} ms on Kelp-only days, "
              f"{rust_full * 1e3:.0f} ms on full days (same PnL: {same});  {python_wall / rust_kelp:,.0f}x")
        print("   the template's 256-cell Kelp grid (make_edge 0..15 x take_edge 0..15) under all and worse (1,542 backtests), arena.grid end to end:")
        sys.stdout.flush()
        ours, theirs = _grid_wall("python", args.jobs, scratch / "python.csv"), _grid_wall("rust", args.jobs, scratch / "rust.csv")
        same = (scratch / "python.csv").read_text() == (scratch / "rust.csv").read_text()
        print(f"   --engine python {ours:.1f} s, --engine rust {theirs:.1f} s ({ours / theirs:,.0f}x), the same CSV: {same}")


if __name__ == "__main__":
    main()
