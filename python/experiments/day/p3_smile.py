"""Is there a volatility smile to trade? P3's volcanic vouchers, by held-out days.

usage (from the repo root): uv run python -m experiments.day.p3_smile [--window N] [--engine rust]
       uv run python -m experiments.day.p3_smile --data DIR --days 3-0 3-1 --underlying U --prefix U_OPT_ --expiry r3d0=8,r3d1=7 [--format F --bot FILE]

The five distinct days with the vouchers: P3 round 3 days 0-2, round 4 day 3 and round 5 day 4
(round 4 days 1-2 and round 5 days 2-3 repeat them; arena.grid.repeated_days). Time to expiry is
8 days at the open of day 0, one fewer per day, as Frankfurt's code reads it
(references/prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:644). Prices are wall
mids; the rock's is the spot S.

1. The smile: per tick and strike with time value, the implied vol v against the moneyness
   m = ln(K/S)/sqrt(T), and a parabola v(m) fitted by least squares on the other four days, as
   Frankfurt fitted theirs (README.md:439). Per day: the fit, and how far the day's own points sit
   from it.
2. The residual per strike and day: the voucher's wall mid less Black-Scholes at v(m) from the
   other days. Its mean (a strike's persistent offset), its sd, and the sd of its fast part (the
   residual less its EMA over --window ticks, what Frankfurt's "IV scalping" trades), against
   half the voucher's spread, the cost of crossing it. With the fast part's lag-1 autocorrelation:
   near 1 it drifts, well below 1 it reverts tick to tick and only crossing the spread could catch it.
3. Trading it: the template with each voucher's fair from `smile_fair` (the smile from the other
   four days, plus the voucher's EMA offset from it), so take, clear and make trade the fast
   deviations, against the template as committed (the vouchers follow the rock's level bet). Each
   variant in VARIANTS, per day, on the rock and the vouchers alone, under --match-trades all and
   worse and with --resting, with or without a delta hedge in the rock (`hedge_ratio` 1: the rock holds minus the
   vouchers' delta). Then the variant chosen by PnL on the other four days, scored on the fifth.
Results go into IDEAS.md ("Options: trading implied-volatility deviations from a fitted smile").

With --data (the day's download), the options are the products named --prefix plus a strike, on
--underlying, with --expiry the days to expiry at each day's open (by day name, as the tables show
it). The variants cover every strike found, and the trading part sets each product's whole PARAMS
entry (limits from the data), since the bot's own PARAMS may not list them. The fit needs at least
two days (it leaves one out).
"""

from __future__ import annotations

import argparse
import math
import statistics as st
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from arena import rust
from arena.cli import add_dataset_arguments, add_engine_argument, backtest as run_backtest, dataset_from
from arena.engine import EngineConfig, TradeMatching
from arena.formats import FORMATS
from experiments.day.p4_vouchers import bs_call, implied_vol

FMT = FORMATS["prosperity"]
UNDERLYING = "VOLCANIC_ROCK"
PREFIX = "VOLCANIC_ROCK_VOUCHER_"
DAYS = ["3-0", "3-1", "3-2", "4-3", "5-4"]
STRIKES = (9500, 9750, 10000, 10250, 10500)
TEMPLATE = "python/bots/template.py"
MODES = {"all": EngineConfig(), "worse": EngineConfig(trade_matching=TradeMatching.WORSE), "resting": EngineConfig(resting=True)}
# name: (strikes on the smile, take_edge, make_edge or None for no quotes, hedge_ratio, model)
# model "smile": the parabola from the other days; "flat": one volatility for every strike (the
# parabola's value at m = 0), so only the EMA offset adapts; "none": no option model, the
# template's plain market making around each voucher's own wall mid.
VARIANTS = {
    f"{label}, take {take}{', make ' + str(make) if make is not None else ''}{', hedged' if hedge else ''}": (strikes, take, make, hedge, "smile")
    for label, strikes in (("all strikes", STRIKES), ("9750 and 10000", (9750, 10000)))
    for take in (0.5, 1, 1.5, 2)
    for make in (None, 1)
    for hedge in (0, 1)
} | {
    f"control: 9750 and 10000, take 0.5, make 1, {model} model": ((9750, 10000), 0.5, 1, 0, model)
    for model in ("flat", "none")
}


DATA, FORMAT, EXPIRY, LIMITS, CUSTOM = "p3", "prosperity", {}, {}, False  # --data sets them (_settings)


def days_to_expiry(day_name: str) -> int:
    return EXPIRY[day_name] if EXPIRY else 8 - int(day_name.split("d")[-1])


def load():
    return FMT.load_days(FMT.resolve_data_dir(DATA), DAYS)


def _settings(dataset, underlying: str, prefix: str, expiry: str) -> dict:
    """The module's settings for the day's data: its options (found by prefix), expiry and limits, and
    variants over every strike."""
    fmt = FORMATS[dataset.format]
    days = fmt.load_days(fmt.resolve_data_dir(dataset.data), list(dataset.days))
    strikes = tuple(sorted({int(p.removeprefix(prefix)) for day in days for p in day.products if p.startswith(prefix) and p.removeprefix(prefix).isdigit()}))
    if underlying not in {p for day in days for p in day.products} or not strikes:
        raise ValueError(f"no {underlying} or no options named {prefix}<strike> in the data")
    try:
        table = {name: int(n) for name, n in (part.split("=") for part in expiry.split(","))}
    except ValueError:
        raise ValueError(f"--expiry {expiry!r}: write DAY=DAYS,..., e.g. r3d0=8,r3d1=7") from None
    missing = [day.name for day in days if day.name not in table]
    if missing:
        raise ValueError(f"--expiry has no entry for {', '.join(missing)}")
    variants = {
        f"all strikes, take {take}{', make ' + str(make) if make is not None else ''}{', hedged' if hedge else ''}": (strikes, take, make, hedge, "smile")
        for take in (0.5, 1, 1.5, 2) for make in (None, 1) for hedge in (0, 1)
    } | {f"control: all strikes, take 0.5, make 1, {model} model": (strikes, 0.5, 1, 0, model) for model in ("flat", "none")}
    return {"DATA": dataset.data, "DAYS": list(dataset.days), "FORMAT": dataset.format, "FMT": fmt, "TEMPLATE": dataset.bot,
            "UNDERLYING": underlying, "PREFIX": prefix, "STRIKES": strikes, "EXPIRY": table, "VARIANTS": variants, "CUSTOM": True,
            "KEEP": [underlying, *(f"{prefix}{k}" for k in strikes)], "LIMITS": {p: v for day in days for p, v in day.limits.items()}}


def points(day) -> list[dict]:
    """One row per tick and strike: S, K, T in years, the voucher's wall mid and spread, m and v (None without time value)."""
    rows = []
    for tick in day.ticks:
        rock = tick.books.get(UNDERLYING)
        s = rock.wall_mid if rock is not None else None
        if s is None:
            continue
        t = (days_to_expiry(day.name) - tick.timestamp / 1_000_000) / 365
        for product, book in tick.books.items():
            if not product.startswith(PREFIX) or book.wall_mid is None or not (book.bids and book.asks):
                continue
            k = int(product.removeprefix(PREFIX))
            rows.append({"t": tick.timestamp, "product": product, "S": s, "K": k, "T": t, "price": book.wall_mid,
                         "half_spread": (book.asks[0][0] - book.bids[0][0]) / 2, "m": math.log(k / s) / math.sqrt(t),
                         "v": implied_vol(book.wall_mid, s, k, t)})
    return rows


def fit_parabola(rows: list[dict]) -> tuple[float, float, float]:
    """Least squares v = a m^2 + b m + c over the rows with an implied vol (normal equations, 3x3)."""
    xs = [(r["m"], r["v"]) for r in rows if r["v"] is not None]
    sums = [sum(m**p for m, _ in xs) for p in range(5)]
    rhs = [sum(v * m**p for m, v in xs) for p in range(3)]
    a = [[sums[i + j] for j in range(3)] for i in range(3)]  # rows for the powers 0, 1, 2
    c0, c1, c2 = _solve(a, rhs)
    return c2, c1, c0


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    return [m[i][n] / m[i][i] for i in range(n)]


def smile(coef: tuple[float, float, float], m: float) -> float:
    a, b, c = coef
    return a * m * m + b * m + c


KEEP = [UNDERLYING, *(f"{PREFIX}{k}" for k in STRIKES)]  # the products the trading part keeps


def _only_options(day):
    keep = set(KEEP)
    ticks = [replace(t, books={p: b for p, b in t.books.items() if p in keep}, trades={p: x for p, x in t.trades.items() if p in keep},
                     marks={p: x for p, x in t.marks.items() if p in keep}) for t in day.ticks]
    return replace(day, products=[p for p in day.products if p in keep], ticks=ticks)


def overrides(variant: str | None, coef: tuple[float, float, float], expiry: int) -> dict:
    """The --set overrides for a variant; None is the template as committed."""
    if variant is None:
        return {}
    strikes, take, make, hedge, model = VARIANTS[variant]
    if model == "flat":
        coef = (0.0, 0.0, coef[2])
    if CUSTOM:  # whole entries: the bot's PARAMS needn't list these products
        out = {f"PARAMS.{UNDERLYING}": {"limit": LIMITS[UNDERLYING], "fair": "wall_mid", "hedge": True, "take_edge": 10**6, "make_size": 0, "clear_edge": 1}}
        for k in STRIKES:
            product = f"{PREFIX}{k}"
            entry = {"limit": LIMITS[product], "fair": "wall_mid", "strike": k}
            if k in strikes and model == "none":
                entry |= {"take_edge": take, "make_size": None, "make_edge": make, "clear_edge": 0}
            elif k in strikes:
                entry |= {"smile": coef, "underlying": UNDERLYING, "expiry": expiry, "take_edge": take, "make_size": None if make is not None else 0,
                          "make_edge": make if make is not None else 2, "clear_edge": 0, "hedge_ratio": hedge}
            else:
                entry |= {"take_edge": 10**6, "make_size": 0}
            out[f"PARAMS.{product}"] = entry
        return out
    out = {"PARAMS.VOLCANIC_ROCK.level": None, "PARAMS.VOLCANIC_ROCK.hedge": True, "PARAMS.VOLCANIC_ROCK.take_edge": 10**6,
           "PARAMS.VOLCANIC_ROCK.make_size": 0, "PARAMS.VOLCANIC_ROCK.clear_edge": 1}
    for k in STRIKES:
        key = f"PARAMS.{PREFIX}{k}"
        out[f"{key}.follow"] = None
        if k in strikes and model == "none":
            out |= {f"{key}.take_edge": take, f"{key}.make_size": None, f"{key}.make_edge": make, f"{key}.clear_edge": 0}
        elif k in strikes:
            out |= {f"{key}.smile": coef, f"{key}.underlying": UNDERLYING, f"{key}.expiry": expiry, f"{key}.take_edge": take,
                    f"{key}.make_size": None if make is not None else 0, f"{key}.make_edge": make if make is not None else 2,
                    f"{key}.clear_edge": 0, f"{key}.hedge_ratio": hedge}
        else:
            out[f"{key}.make_size"] = 0  # not traded: no quotes, and take_edge is already out of reach
    return out


ENGINE = ["python"]  # set in each worker by _init (--engine)


def _init(engine: str, settings: dict | None = None) -> None:
    ENGINE[0] = engine
    globals().update(settings or {})
    globals()["FMT"] = FORMATS[FORMAT]


def backtest(job: tuple[str, str | None, str, tuple]) -> tuple[tuple, dict]:
    day_name, variant, mode, coef = job
    if ENGINE[0] == "rust" and FORMAT == "prosperity":  # Rust reads the day's CSVs itself, keeping the options: nothing to load here
        r, d = day_name.removeprefix("r").split("d")
        day = rust.prosperity_day(DATA, int(r), int(d), KEEP)
    else:
        (day,) = [_only_options(d) for d in load() if d.name == day_name]
    bots = [("you", TEMPLATE, overrides(variant, coef, days_to_expiry(day_name)), False)]
    (result,) = run_backtest(day, bots, MODES[mode], ENGINE[0], fields=("pnl", "errors", "breaches"), format_name=FORMAT)
    pnl = {p: s[-1] for p, s in result.pnl.items() if s}
    return (day_name, variant, mode), {"rock": pnl.get(UNDERLYING, 0.0), "options": sum(v for p, v in pnl.items() if p != UNDERLYING),
                                       "errors": len(result.errors), "breaches": len(result.limit_breaches)}


def trade(held: dict, engine: str = "python", settings: dict | None = None) -> None:
    jobs = [(d, v, m, held[d]) for d in held for v in (None, *VARIANTS) for m in MODES]
    settings = {k: v for k, v in (settings or {}).items() if k != "FMT"}  # a module doesn't pickle: _init finds it
    with ProcessPoolExecutor(initializer=_init, initargs=(engine, settings)) as pool:
        results = dict(pool.map(backtest, jobs))
    names = list(held)
    print("\n3. Trading it: rock + vouchers PnL in thousands per day (rock / vouchers in the total column), under all; worse and --resting in the last columns\n")
    print("| Variant | " + " | ".join(names) + " | Total (rock / vouchers) | Worst day | Total under worse | With --resting |")
    print("|---|" + "---|" * (len(names) + 4))
    rows = {}
    for v in (None, *VARIANTS):
        per_day = {d: results[(d, v, "all")]["rock"] + results[(d, v, "all")]["options"] for d in names}
        rock = sum(results[(d, v, "all")]["rock"] for d in names)
        worse, resting = (sum(results[(d, v, m)]["rock"] + results[(d, v, m)]["options"] for d in names) for m in ("worse", "resting"))
        bad = sum(results[(d, v, m)]["errors"] + results[(d, v, m)]["breaches"] for d in names for m in MODES)
        rows[v] = per_day
        flag = f" ! {bad} errors or breaches" if bad else ""
        print(f"| {v or 'committed (follow the rock)'}{flag} | " + " | ".join(f"{per_day[d] / 1000:.1f}" for d in names)
              + f" | {sum(per_day.values()) / 1000:.1f} ({rock / 1000:.1f} / {(sum(per_day.values()) - rock) / 1000:.1f}) | "
              f"{min(per_day.values()) / 1000:.1f} | {worse / 1000:.1f} | {resting / 1000:.1f} |")
    print("\nHeld out: per day, the smile variant with the best total under all on the other four days")
    total = 0.0
    for d in names:
        pick = max((v for v in VARIANTS if not v.startswith("control")), key=lambda v: sum(rows[v][o] for o in names if o != d))
        total += rows[pick][d]
        print(f"  {d}: {pick}  {rows[pick][d] / 1000:.1f}  (committed {rows[None][d] / 1000:.1f})")
    print(f"held out {total / 1000:.1f} against {sum(rows[None].values()) / 1000:.1f} for the committed template")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.day.p3_smile")
    parser.add_argument("--window", type=int, default=20, help="EMA ticks for the residual's slow part (default 20)")
    add_engine_argument(parser, "run the backtests in rust/ (the same results)")
    add_dataset_arguments(parser, products=False)
    parser.add_argument("--underlying", help="with --data: the options' underlying")
    parser.add_argument("--prefix", help="with --data: the options' common name; the strike is the number after it")
    parser.add_argument("--expiry", help="with --data: days to expiry at each day's open, e.g. r3d0=8,r3d1=7")
    args = parser.parse_args()
    try:
        dataset = dataset_from(args)
        if dataset and not (args.underlying and args.prefix and args.expiry):
            raise ValueError("--data needs --underlying, --prefix and --expiry")
        settings = _settings(dataset, args.underlying, args.prefix, args.expiry) if dataset else {}
    except ValueError as error:
        parser.error(str(error))
    if args.engine == "rust":
        rust.require(args.allow_stale)
    globals().update(settings)
    by_day = {day.name: points(day) for day in load()}
    alpha = 2 / (args.window + 1)

    print("1. The smile v(m), fitted on the other four days, and the day's own fit (a m^2 + b m + c)\n")
    print("| Day | Days to expiry | Fit on the others | Fit on the day | v's sd about the others' fit |")
    print("|---|---|---|---|---|")
    held = {}
    for name, rows in by_day.items():
        others = [r for n, rs in by_day.items() if n != name for r in rs]
        held[name] = fit_parabola(others)
        own = fit_parabola(rows)
        gaps = [r["v"] - smile(held[name], r["m"]) for r in rows if r["v"] is not None]
        print(f"| {name} | {days_to_expiry(name)} | {', '.join(f'{x:.4f}' for x in held[name])} | "
              f"{', '.join(f'{x:.4f}' for x in own)} | {st.pstdev(gaps):.4f} |")

    print(f"\n2. The residual (wall mid less Black-Scholes at the others' smile), and its fast part (less its {args.window}-tick EMA)\n")
    print("| Day | Strike | Ticks with time value | Mean | Sd | Fast part's sd | Its lag-1 autocorrelation | Half spread |")
    print("|---|---|---|---|---|---|---|---|")
    for name, rows in by_day.items():
        for product in sorted({r["product"] for r in rows}, key=lambda p: int(p.removeprefix(PREFIX))):
            series = [r for r in rows if r["product"] == product]
            residual = [r["price"] - bs_call(r["S"], r["K"], r["T"], smile(held[name], r["m"])) for r in series]
            ema, fast = residual[0], []
            for x in residual:
                fast.append(x - ema)
                ema += alpha * (x - ema)
            lag1 = st.correlation(fast[:-1], fast[1:]) if len(fast) > 2 and st.pstdev(fast) > 0 else float("nan")
            alive = sum(1 for r in series if r["v"] is not None)
            print(f"| {name} | {product.removeprefix(PREFIX)} | {alive:,} | {st.fmean(residual):+.2f} | {st.pstdev(residual):.2f} | "
                  f"{st.pstdev(fast):.2f} | {lag1:.2f} | {st.fmean(r['half_spread'] for r in series):.2f} |")
    trade(held, args.engine, settings)


if __name__ == "__main__":
    main()
