"""Fit the engine to a submission: which settings make our backtest of the uploaded file show what the portal shows?

usage (from the repo root):
  uv run python -m experiments.day.calibrate --data D --days all --format qminers --bot BOT --portal metrics.json [--results ZIP] [--engine rust]
  uv run python -m experiments.day.calibrate ... --portal-set score=1234.5 --portal-set fills=310 --vary fee=0,1 --vary delay=0,1

The first upload is the calibration pack (ON_THE_DAY.md, "How is PnL scored?"): this runs its four checks
over every plausible engine setting at once. BOT is the file uploaded, D the data its public run used.
Each candidate is a matching mode (all, worse, none), per tick or resting with a queue model (back, prob,
front), a mark (mid, touch, last) and depletion (off, on), on top of the format's ENGINE, times any
`--vary FIELD=V1,V2` (an EngineConfig field: fee, maker_fee, delay, limit_penalty, ...): 72 settings and up.
Each is scored against the portal's figures, given as the portal's own field names (the submission page's
metrics response, pasted into a JSON file, or --portal-set): score, fills, tradedVolume, inventory, cash,
markPrice, breachPenalty, pnlSe, absInventoryQ50/Q68/Q95/Q997. With --results, each product's fills and
volume in the results ZIP too (read through experiments.day.fill_curve's column map, the swap's step 11).

Our figures are converted to the portal's credits by the data's unit (Day.info) times the format's CREDITS
(arena.cli.credits_per_unit; --scale to override). Where
the portal's meaning is open, the nearest reading counts: the score as the days' sum or their mean, fills as
fills or filled orders, pnlSe as the per-tick, block or per-day standard error (report.format_metrics), markPrice as the products' mean mark or any one's. The
error per figure is |ours - theirs| / max(|theirs|, 1); a setting's error is their mean. The table ranks the
settings, and the best one's ENGINE dict is printed to paste into the format plug-in. Settings within a few
per cent of each other can't be told apart by this upload: the probes decide between them (ON_THE_DAY.md).
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields, replace
from pathlib import Path

from arena import report
from arena.cli import _ENUMS, add_dataset_arguments, add_engine_argument, backtest, credits_per_unit, dataset_from, format_config
from arena.engine import EngineConfig, Mark, QueueModel, TradeMatching
from arena.formats import FORMATS

PORTAL = ("score", "fills", "tradedVolume", "inventory", "cash", "markPrice", "breachPenalty", "pnlSe",
          "absInventoryQ50", "absInventoryQ68", "absInventoryQ95", "absInventoryQ997")
QUANTILES = dict(zip(("absInventoryQ50", "absInventoryQ68", "absInventoryQ95", "absInventoryQ997"), report.QUANTILES))
CLOSE = 0.02  # settings within this of the best's error can't be told apart by the upload


def candidates(base: EngineConfig, vary: dict[str, list]) -> list[EngineConfig]:
    """Every matching x (per tick, or resting with each queue) x mark x depletion x --vary, on the format's base."""
    fills = [{"resting": False}] + [{"resting": True, "queue": q} for q in QueueModel]
    names, values = list(vary), [vary[n] for n in vary]
    out = []
    for matching, fill, mark, deplete in itertools.product(TradeMatching, fills, Mark, (False, True)):
        for extra in itertools.product(*values):
            out.append(replace(base, trade_matching=matching, mark=mark, deplete=deplete, **fill, **dict(zip(names, extra))))
    return out


def describe(config: EngineConfig) -> str:
    fill = f"resting, {config.queue.value}" if config.resting else "per tick"
    text = f"{config.trade_matching.value}, {fill}, {config.mark.value}" + (", deplete" if config.deplete else "")
    for f in fields(EngineConfig):
        if f.name not in ("trade_matching", "resting", "queue", "mark", "deplete", "capture_output") and getattr(config, f.name) != f.default:
            text += f", {f.name} {getattr(config, f.name)}"
    return text


def engine_dict(config: EngineConfig) -> dict:
    """The fields a plug-in's ENGINE needs for this setting (resting goes in its RESTING)."""
    value = lambda v: v.value if hasattr(v, "value") else v
    return {f.name: value(getattr(config, f.name)) for f in fields(EngineConfig)
            if f.name not in ("resting", "capture_output", "seed") and getattr(config, f.name) != f.default}


def figures(results, scale: float, penalty: float | None) -> dict[str, list[float]]:
    """Our candidates for each portal figure, in credits: a list where the portal's meaning is open."""
    rate = penalty or 0.0
    daily = [sum(series[-1] for series in r.pnl.values() if series) for r in results]
    last = results[-1]
    traded = [p for r in results for p in r.products if r.positions.get(p) and (any(f.product == p for f in r.fills) or any(r.positions[p]))]
    products = sorted(set(traded)) or list(last.products)
    inventory = sum(last.positions[p][-1] for p in products if last.positions.get(p))
    paid = sum(report.penalty_paid(r, rate) for r in results)
    marks = {p: last.marks[p][-1] for p in products if last.marks.get(p)}
    cash = sum(daily) - sum(last.positions[p][-1] * marks[p] for p in marks) + paid
    changes = [b - a for r in results for a, b in zip([0.0, *report.total_pnl(r)], report.total_pnl(r))]
    se_ticks = statistics.stdev(changes) * len(changes) ** 0.5 if len(changes) > 1 else 0.0
    edges = [len(changes) * k // report.BLOCKS for k in range(report.BLOCKS + 1)]
    se_blocks = statistics.stdev(sum(changes[a:b]) for a, b in zip(edges, edges[1:])) * report.BLOCKS ** 0.5 if len(changes) >= 2 * report.BLOCKS else se_ticks
    se_days = statistics.stdev(daily) * len(daily) ** 0.5 if len(daily) > 1 else se_ticks
    held = [sum(abs(r.positions[p][k]) for p in products if r.positions.get(p)) for r in results for k in range(len(r.timestamps))]
    quantiles = report._quantiles(held or [0], report.QUANTILES)
    out = {
        "score": [sum(daily) * scale, statistics.fmean(daily) * scale],
        "fills": [float(sum(len(r.fills) for r in results)), float(sum(len({f.order_id for f in r.fills}) for r in results))],
        "tradedVolume": [float(sum(abs(f.quantity) for r in results for f in r.fills))],
        "inventory": [float(inventory)],
        "cash": [cash * scale],
        "breachPenalty": [paid * scale],
        "pnlSe": [se_ticks * scale, se_blocks * scale, se_days * scale],
        **{name: [q] for name, q in zip(QUANTILES, quantiles)},
    }
    if marks:  # one product: its mark; several: their mean, or any one of them (the portal shows one markPrice)
        out["markPrice"] = [statistics.fmean(marks.values()) * scale, *(m * scale for m in marks.values())]
    for r in results:
        for f in r.fills:
            out.setdefault(f"fills {f.product}", [0.0])[0] += 1
            out.setdefault(f"volume {f.product}", [0.0])[0] += abs(f.quantity)
    return out


def error(ours: dict[str, list[float]], theirs: dict[str, float]) -> tuple[float, dict[str, float]]:
    """The mean relative error over the portal's figures we have, and the nearest reading of each."""
    errors, nearest = [], {}
    for name, target in theirs.items():
        options = ours.get(name, [0.0])
        best = min(options, key=lambda v: abs(v - target))
        nearest[name] = best
        errors.append(abs(best - target) / max(abs(target), 1.0))
    return (statistics.fmean(errors) if errors else 0.0), nearest


def from_results(source: Path) -> dict[str, float]:
    """Each product's fills and volume in a results ZIP (or folder), through fill_curve's column map."""
    from experiments.day import fill_curve

    out: dict[str, float] = {}
    for tables in fill_curve.read_results(source).values():
        for row in tables["fills"]:
            out[f"fills {row['product']}"] = out.get(f"fills {row['product']}", 0.0) + 1
            out[f"volume {row['product']}"] = out.get(f"volume {row['product']}", 0.0) + abs(row["quantity"])
    return out


_JOB: dict = {}


def _init(job: dict) -> None:
    _JOB.update(job)


def _score(config: EngineConfig) -> tuple[EngineConfig, float, dict, dict]:
    days, bot, engine, fmt, scale, theirs = (_JOB[k] for k in ("days", "bot", "engine", "format", "scale", "theirs"))
    results = [backtest(day, [("you", bot, {}, False)], config, engine, False, None, fmt, rules=False)[0] for day in days]
    ours = figures(results, scale, config.limit_penalty)
    err, nearest = error(ours, theirs)
    return config, err, nearest, ours


def parse_value(name: str, text: str):
    kind = {f.name: f.type for f in fields(EngineConfig)}.get(name)
    if kind is None:
        raise ValueError(f"--vary: no engine setting {name!r}")
    if name in _ENUMS:
        return _ENUMS[name](text)
    if text.lower() in ("none", "null"):
        return None
    if "bool" in str(kind):
        return text.lower() in ("1", "true", "yes", "on")
    return int(text) if "int" in str(kind) and "float" not in str(kind) else float(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.calibrate", description=__doc__.split("\n")[0])
    add_dataset_arguments(parser, products=False)
    add_engine_argument(parser)
    parser.add_argument("--portal", type=Path, help="the submission's metrics as the portal's API gives them (JSON; a 'metrics' key is looked into)")
    parser.add_argument("--portal-set", action="append", default=[], metavar="FIELD=VALUE", help="a portal figure by hand, e.g. score=1234.5 (repeatable)")
    parser.add_argument("--results", type=Path, help="the submission's results ZIP (or folder): each product's fills and volume join the figures")
    parser.add_argument("--vary", action="append", default=[], metavar="FIELD=V1,V2", help="one more engine setting to try, e.g. fee=0,1 or delay=0,1 (repeatable)")
    parser.add_argument("--scale", type=float, help="credits per engine price unit (default: the data's Day.info unit times the format's CREDITS)")
    parser.add_argument("--top", type=int, default=12, help="settings to show (default: 12)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: CPU count)")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
        if dataset is None:
            raise ValueError("give the uploaded file's data: --data D --days ... (and --format, --bot)")
        theirs: dict[str, float] = {}
        if args.portal:
            loaded = json.loads(args.portal.read_text())
            loaded = {**loaded, **loaded.get("metrics", {})} if isinstance(loaded.get("metrics"), dict) else loaded
            theirs.update({k: float(v) for k, v in loaded.items() if k in PORTAL and v is not None})
        for text in args.portal_set:
            key, _, value = text.partition("=")
            if key not in PORTAL:
                raise ValueError(f"--portal-set: {key!r} is not a portal figure ({', '.join(PORTAL)})")
            theirs[key] = float(value)
        if args.results:
            theirs.update(from_results(args.results))
        if not theirs:
            raise ValueError("nothing to fit to: give --portal, --portal-set or --results")
        vary = {}
        for text in args.vary:
            name, _, values = text.partition("=")
            vary[name] = [parse_value(name, v) for v in values.split(",")]
    except (ValueError, OSError, json.JSONDecodeError) as e:
        parser.error(str(e))

    fmt = FORMATS[dataset.format]
    days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
    engine = args.engine
    if engine == "rust":
        from arena import rust

        try:
            rust.kind_of(Path(dataset.bot))
        except (KeyError, ValueError):
            print(f"note: {dataset.bot} has no Rust twin yet, so its backtests run on the Python engine", file=sys.stderr)
            engine = "python"
    scale = args.scale if args.scale is not None else credits_per_unit(dataset.format, days)
    configs = candidates(format_config(dataset.format), vary)
    job = {"days": days, "bot": dataset.bot, "engine": engine, "format": dataset.format, "scale": scale, "theirs": theirs}
    if args.jobs > 1:
        with ProcessPoolExecutor(args.jobs, initializer=_init, initargs=(job,)) as pool:
            scored = list(pool.map(_score, configs))
    else:
        _init(job)
        scored = [_score(c) for c in configs]
    scored.sort(key=lambda s: s[1])

    print(f"{dataset.bot} on {dataset.name}: {len(configs)} engine settings against the portal's {len(theirs)} figures "
          f"(ours in credits at {scale:g} a unit; error = mean |ours - theirs| / |theirs|)\n")
    names = list(theirs)
    print("| setting | error | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    print("| **the portal** | | " + " | ".join(f"{theirs[n]:,.2f}" for n in names) + " |")
    for config, err, nearest, _ in scored[: args.top]:
        print(f"| {describe(config)} | {err:.1%} | " + " | ".join(f"{nearest[n]:,.2f}" for n in names) + " |")
    best, err, _, _ = scored[0]
    close = [describe(c) for c, e, _, _ in scored[1:] if e - err <= CLOSE]
    print(f"\nBest: {describe(best)} ({err:.1%} off). Into the format plug-in (python/arena/formats/qminers.py):")
    print(f"  RESTING = {best.resting}")
    print(f"  ENGINE = {json.dumps(engine_dict(best))}")
    if close:
        print(f"\n{len(close)} more within {CLOSE:.0%} of it, which this upload can't tell apart (the probes decide): " + "; ".join(close[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
