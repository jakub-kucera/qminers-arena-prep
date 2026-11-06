"""Fit the engine to a submission: which settings make our backtest of the uploaded file show what the portal shows?

usage (from the repo root):
  uv run python -m experiments.day.calibrate --data D --days all --format qminers --bot BOT --portal metrics.json [--results ZIP] [--engine rust]
  uv run python -m experiments.day.calibrate ... --portal-set score=1234.5 --portal-set fills=310 --vary fee=0,1 --vary delay=0,1

The first upload is the calibration pack (ON_THE_DAY.md, "How is PnL scored?"): this runs its four checks
over every plausible engine setting at once. BOT is the file uploaded, D the data its public run used.
Each candidate is a matching mode (all, worse, none), per tick or resting with a queue model (back, prob,
front), a mark (mid, touch, last) and depletion (off, on), on top of the format's ENGINE, times any
`--vary FIELD=V1,V2` (an EngineConfig field: fee, maker_fee, order_fee, delay, limit_penalty, ...). Orders a step late are
tried by default (delay 0 and 1, unless --vary names delay): 144 settings and up.
Each is scored against the portal's figures, given as the portal's own field names (the submission page's
metrics response, pasted into a JSON file, or --portal-set): score, fills, tradedVolume, inventory, cash,
markPrice, breachPenalty, pnlSe, absInventoryQ50/Q68/Q95/Q997. With --results, each product's fills and
volume in the results ZIP too (its fills file found by experiments.day.fill_curve's RESULT_FILES and read by
its RESULT_COLUMNS, only product, quantity and side: the swap's step 11); a ZIP that yields no fills says so.

Our figures are converted to the portal's credits by the data's unit (Day.info) times the format's CREDITS
(arena.cli.credits_per_unit; --scale to override). Where
the portal's meaning is open, the nearest reading counts: the score as the days' sum or their mean, fills as
fills or filled orders, pnlSe as the per-tick, block or per-day standard error (report.format_metrics), markPrice as the products' mean mark or any one's. The
error per figure is |ours - theirs| / max(|theirs|, 1). Settings are ranked by their worst figure, then the
mean, and the best one's per-figure errors are printed. Its ENGINE dict is printed to paste into the format
plug-in only if its worst figure is within --accept (5%): above it, no setting reproduces the portal, and the
cause is usually outside the settings (the audit's round 8, R1): our wrapper or ADAPTER handles something
their exchange doesn't (a cancel of an order not yet listed, a reject, a cap), a cost the engine doesn't
charge (a fee per order), or the money is off by a common factor (the unit or CREDITS; the factor is
printed when every money figure agrees on it, for --scale). It also prints the setting closest on the
fills and volume alone, and where ours trade more than theirs under most settings, suggests
--vary fill_ratio (an exchange that gives resting orders only part of each print: the 2026-11-03
rehearsal's). Then keep the plug-in's ENGINE and widen the grid's --modes. Settings whose every figure is within
half a per cent of the best's can't be told apart by this upload: the probes decide between them.
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
TIE = 0.005  # a setting whose every figure's error is within this of the best's can't be told apart by the upload
ACCEPT = 0.05  # the worst figure's error above which no ENGINE is offered to paste (--accept)
MONEY = ("score", "cash", "breachPenalty", "pnlSe")  # figures a wrong unit or CREDITS scales together, the factor read off them
SCALED = MONEY + ("markPrice",)  # scaled too, but its reading may be another product's: left out of the factor
PATH = ("fills", "tradedVolume")  # what the fill model alone decides (with the ZIP's per-product fills and volume)


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
    every = [last.marks[p][-1] for p in last.products if last.marks.get(p)]
    if marks:  # one product: its mark; several: their mean (the traded ones', or every product's), or any one of them
        out["markPrice"] = [statistics.fmean(marks.values()) * scale, statistics.fmean(every) * scale, *(m * scale for m in marks.values())]
    for r in results:
        for f in r.fills:
            out.setdefault(f"fills {f.product}", [0.0])[0] += 1
            out.setdefault(f"volume {f.product}", [0.0])[0] += abs(f.quantity)
    return out


def error(ours: dict[str, list[float]], theirs: dict[str, float]) -> tuple[float, dict[str, float], dict[str, float]]:
    """The mean relative error over the portal's figures we have, the nearest reading of each, and each one's error."""
    per, nearest = {}, {}
    for name, target in theirs.items():
        options = ours.get(name, [0.0])
        best = min(options, key=lambda v: abs(v - target))
        nearest[name] = best
        per[name] = abs(best - target) / max(abs(target), 1.0)
    return (statistics.fmean(per.values()) if per else 0.0), nearest, per


def common_factor(nearest: dict[str, float], theirs: dict[str, float]) -> tuple[float, float] | None:
    """(theirs / ours, the ratios' largest relative spread) where every money figure (MONEY, two at least) agrees on
    it within 3% and it isn't 1."""
    ratios = [theirs[n] / nearest[n] for n in MONEY if n in theirs and abs(nearest.get(n, 0.0)) > 1e-9 and abs(theirs[n]) > 1e-9]
    if len(ratios) < 2:
        return None
    middle = statistics.median(ratios)
    spread = max(abs(r / middle - 1) for r in ratios) if middle > 0 else 1.0
    if middle <= 0 or abs(middle - 1) < 0.03 or spread > 0.03:
        return None
    return middle, spread


def from_results(source: Path) -> tuple[dict[str, float], list[str]]:
    """Each product's fills and volume in a results ZIP (or folder), and the file names in it. Its fills file is
    found by fill_curve's RESULT_FILES and read by its RESULT_COLUMNS, but only product, quantity and side, so a
    clock timestamp or a price in another unit doesn't stop it."""
    import csv
    import io
    import zipfile

    from experiments.day import fill_curve

    if source.is_dir():
        files = {str(p.relative_to(source)): p.read_text for p in source.rglob("*") if p.is_file()}
    else:
        archive = zipfile.ZipFile(source)
        files = {name: (lambda name=name: archive.read(name).decode("utf-8-sig")) for name in archive.namelist() if not name.endswith("/")}
    pattern, columns = fill_curve._pattern(fill_curve.RESULT_FILES["fills"]), fill_curve.RESULT_COLUMNS["fills"]
    out: dict[str, float] = {}
    for name, read in sorted(files.items()):
        if not pattern.match(name):
            continue
        for raw in csv.DictReader(io.StringIO(read()), delimiter=fill_curve.RESULT_DELIMITER):
            product, quantity = raw.get(columns["product"], ""), raw.get(columns["quantity"], "")
            if not product or quantity in ("", None):
                continue
            out[f"fills {product}"] = out.get(f"fills {product}", 0.0) + 1
            out[f"volume {product}"] = out.get(f"volume {product}", 0.0) + abs(float(quantity))
    return out, sorted(files)


_JOB: dict = {}


def _init(job: dict) -> None:
    _JOB.update(job)


def _score(config: EngineConfig) -> tuple[EngineConfig, float, dict, dict]:
    days, bot, engine, fmt, scale, theirs = (_JOB[k] for k in ("days", "bot", "engine", "format", "scale", "theirs"))
    results = [backtest(day, [("you", bot, {}, False)], config, engine, False, None, fmt, rules=False)[0] for day in days]
    ours = figures(results, scale, config.limit_penalty)
    err, nearest, per = error(ours, theirs)
    return config, err, nearest, per


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
    parser.add_argument("--accept", type=float, default=ACCEPT * 100, metavar="PCT",
                        help=f"the worst figure's error, in per cent, above which no ENGINE is offered (default: {ACCEPT * 100:g})")
    parser.add_argument("--top", type=int, default=12, help="settings to show (default: 12)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: CPU count)")
    args = parser.parse_args(argv)
    try:
        dataset = dataset_from(args)
        if dataset is None:
            raise ValueError("give the uploaded file's data: --data D --days ... (and --format, --bot)")
        theirs: dict[str, float] = {}
        ignored: list[str] = []
        if args.portal:
            loaded = json.loads(args.portal.read_text())
            loaded = {**loaded, **loaded.get("metrics", {})} if isinstance(loaded.get("metrics"), dict) else loaded
            theirs.update({k: float(v) for k, v in loaded.items() if k in PORTAL and v is not None})
            ignored = sorted(k for k in loaded if k not in PORTAL and k != "metrics")
        for text in args.portal_set:
            key, _, value = text.partition("=")
            if key not in PORTAL:
                raise ValueError(f"--portal-set: {key!r} is not a portal figure ({', '.join(PORTAL)})")
            theirs[key] = float(value)
        zip_note = ""
        if args.results:
            found, names = from_results(args.results)
            theirs.update(found)
            if not found:
                zip_note = (f"WARNING: --results gave no fills (its files: {', '.join(names[:6]) or 'none'}): set fill_curve's RESULT_FILES "
                            "and RESULT_COLUMNS to them (the swap's step 11); this fit rests on the portal's figures only")
        if not theirs:
            raise ValueError("nothing to fit to: give --portal, --portal-set or --results")
        vary = {}
        for text in args.vary:
            name, _, values = text.partition("=")
            vary[name] = [parse_value(name, v) for v in values.split(",")]
        vary.setdefault("delay", [0, 1])  # orders a step late: the third rehearsal lost both uploads to it
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
    scored.sort(key=lambda s: (max(s[3].values(), default=0.0), s[1]))  # the worst figure first, then the mean

    from_zip = sum(1 for n in theirs if " " in n)
    print(f"{dataset.bot} on {dataset.name}: {len(configs)} engine settings against {len(theirs)} figures "
          f"({len(theirs) - from_zip} the portal's, {from_zip} from the results ZIP; ours in credits at {scale:g} a unit; "
          "worst = the largest |ours - theirs| / |theirs|, mean = their mean)\n")
    if zip_note:
        print(zip_note + "\n")
    if ignored:
        print(f"portal fields not fitted: {', '.join(ignored)}\n")
    names = list(theirs)
    print("| setting | worst | mean | " + " | ".join(names) + " |")
    print("|---|---|---|" + "---|" * len(names))
    print("| **the portal** | | | " + " | ".join(f"{theirs[n]:,.2f}" for n in names) + " |")
    for config, err, nearest, per in scored[: args.top]:
        print(f"| {describe(config)} | {max(per.values()):.1%} | {err:.1%} | " + " | ".join(f"{nearest[n]:,.2f}" for n in names) + " |")
    best, err, nearest, per = scored[0]
    worst_name = max(per, key=per.get)
    print(f"\nBest: {describe(best)} (worst {per[worst_name]:.1%} off, on {worst_name}; mean {err:.1%}). Per figure: "
          + ", ".join(f"{n} {e:.1%}" for n, e in per.items()))
    ties = [describe(c) for c, _, _, p in scored[1:] if all(abs(p[n] - per[n]) <= TIE for n in per)]
    if per[worst_name] > args.accept / 100:
        print(f"\nNO SETTING REPRODUCES THE PORTAL within {args.accept:g}%: don't paste an ENGINE. Keep the plug-in's and widen "
              "the grid's --modes (ON_THE_DAY.md, \"How is PnL scored?\"). The usual causes, outside these settings:")
        scaled = [(found, config) for config, _, near, p in scored if (found := common_factor(near, theirs))
                  and all(e <= args.accept / 100 for n, e in p.items() if n not in SCALED)]  # the money off by one factor, the rest fitting
        if scaled:
            (factor, _), config = min(scaled, key=lambda item: item[0][1])
            print(f"  - the money: under {describe(config)} every money figure is {factor:.4g} times ours and the rest fit,\n"
                  f"    so the unit or CREDITS is off: re-run with --scale {scale * factor:g}")
        print("  - a cost the settings don't include (a fee per order, the 2026-11-03 rehearsal's 28% of the gross): put the rules'\n"
              "    fee in the plug-in's ENGINE (order_fee, fee) or try it with --vary order_fee=..., and check it against the ZIP's orders")
        print("  - the wrapper: our ADAPTER or format wrapper does something their exchange doesn't (a cancel of an order\n"
              "    not listed yet, a reject, a cap): compare the results ZIP's orders with arena.backtest --out of the same file")
        path = [n for n in theirs if n in PATH or n.startswith(("fills ", "volume "))]
        if path:
            config, _, near, p = min(scored, key=lambda s: max(s[3][n] for n in path))
            over = sum(s[2]["tradedVolume"] > theirs["tradedVolume"] for s in scored) >= 2 / 3 * len(scored) if "tradedVolume" in theirs else False
            print(f"\nClosest on the fills alone ({', '.join(path)}): {describe(config)}, worst {max(p[n] for n in path):.1%} off"
                  + ("; ours trade more than theirs under most settings: try --vary fill_ratio=0.25,0.5,0.75 (their exchange may"
                     "\n  give resting orders only part of each print)" if over and max(p[n] for n in path) > args.accept / 100 else ""))
        return 0
    print("Into the format plug-in (python/arena/formats/qminers.py):")
    print(f"  RESTING = {best.resting}")
    print(f"  ENGINE = {json.dumps(engine_dict(best))}")
    if ties:
        print(f"\n{len(ties)} more with every figure within {TIE:.1%} of it, which this upload can't tell apart (the probes decide): "
              + "; ".join(ties[:6]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
