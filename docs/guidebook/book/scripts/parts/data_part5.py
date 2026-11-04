"""Part V's data (the guidebook's chapters 14 and 15, appendix B): the Kestrel rehearsal's scores, one tick through
the template, the parameters' IDEAS verdicts, and the Prosperity days.

Run from the repo root: uv run python docs/guidebook/book/scripts/make_data.py --only kestrel one_tick parameters datasets
"""

from __future__ import annotations

import ast
import csv
import importlib.util
import sys
from pathlib import Path

from make_data import ROOT, TEMPLATE, run, write

KESTREL = ROOT / "python/experiments/mock_round/round3"


# -- Chapter 14's story: the Kestrel rehearsal, before and after counting the orders on their way -----------------

def kestrel() -> None:
    """The after-run's bot and the same bot with EXECUTION's on_the_way and went (results/in_flight/), scored by the
    round's portal on its public and hidden sessions (portal.py's run_session and metrics, which `portal.py upload`
    and `hidden` call, without counting an upload or writing a results ZIP), in credits."""
    if not list((KESTREL / "public/data").glob("20*")):
        raise SystemExit("the Kestrel sessions are missing: run python/experiments/mock_round/round3/README.md's rebuild first")
    spec = importlib.util.spec_from_file_location("kestrel_portal", KESTREL / "private/portal.py")
    portal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(portal)
    rows = []
    for bot in ("before", "after", "in_flight"):
        path = KESTREL / f"results/{bot}/template.py"
        for which in ("public", "hidden"):
            folder = portal.DATA[which]
            runs = [portal.run_session(str(path), str(folder), date) for date in portal.sessions(folder)]
            results = [r for r, *_ in runs]
            m = portal.metrics(results)
            products = sorted({p for r in results for p in r.products})
            per = {p: round(sum(r.pnl[p][-1] for r in results) * portal.UNIT, 2) for p in products}
            rows.append([bot, which, m["score"], m["breachPenalty"], m["fills"], *(per[p] for p in products)])
    write("kestrel", "python/experiments/mock_round/round3/private/portal.py's run_session and metrics on results/{before,after,in_flight}/"
          "template.py, public and hidden sessions: credits", ["bot", "sessions", "score", "breach_penalty", "fills", *products], rows)


# -- Chapter 14's worked example: one Kelp tick through the template -----------------------------------------------

TICK = 4054  # P3 round 1 day 0, timestamp 405,400: a take and a clear in one tick (found by scanning the day)


def one_tick() -> None:
    """The template on P3 round 1 day 0 (our engine, default mode), then Kelp's tick TICK step by step: the book, the
    position the bot saw, the fair, what take, clear and make planned, what EXECUTION sent and what filled."""
    sys.path.insert(0, str(ROOT / "python"))
    from arena.botfile import BotFile
    from arena.engine import run_day
    from arena.formats import prosperity
    from arena.formats import prosperity_datamodel as dm

    day = prosperity.load_days(prosperity.resolve_data_dir("p3"), ["1-0"])[0]
    result = run_day(day, prosperity.load_bot(ROOT / TEMPLATE, {}, True))
    bot = BotFile(ROOT / TEMPLATE, {"datamodel": dm}, {}, True).load()
    p = bot.params_for("KELP")
    tick = day.ticks[TICK]
    position = result.positions["KELP"][TICK - 1]  # after the tick before: what the bot saw
    seen = tick.books["KELP"]
    book = bot.Book([[px, v] for px, v in seen.bids], [[px, v] for px, v in seen.asks])
    fair = bot.fair_value(book, p, {})
    plan, left = bot.Plan(position, p["limit"]), book.copy()
    bot.take(left, fair, p, plan)
    took = list(plan.takes)
    bot.clear(left, fair, p, plan)
    cleared = plan.takes[len(took):]
    bot.make(left, fair, p, plan)
    cancels, new = bot.execute(plan, [])
    # the same orders as the template sent in the run (its loss stop reads the day's memory, so it isn't rerun here)
    sent = [(o.price, o.quantity) for t, o in result.orders if t == tick.timestamp and o.product == "KELP"]
    assert sent == [(px, q) for px, q, _ in new], f"the steps don't reproduce what the template sent: {sent}"
    fills = [f for f in result.fills if f.timestamp == tick.timestamp and f.product == "KELP"]
    show = lambda orders: "; ".join(f"{'buy' if q > 0 else 'sell'} {abs(q)} at {px}" for px, q, *_ in orders) or "none"
    rows = [
        ["timestamp", tick.timestamp], ["bids", "; ".join(f"{v} at {px}" for px, v in seen.bids)],
        ["asks", "; ".join(f"{v} at {px}" for px, v in seen.asks)], ["position", position], ["wall_size", p["wall_size"]],
        ["take_edge", p["take_edge"]], ["clear_edge", p["clear_edge"]], ["make_edge", p["make_edge"]], ["make_inside", p["make_inside"]],
        ["limit", p["limit"]], ["fair", fair], ["take", show(took)], ["clear", show(cleared)], ["make", show(plan.quotes)],
        ["net_if_all_fill", plan.net], ["cancels", len(cancels)],
        ["sent", "; ".join(f"{'buy' if q > 0 else 'sell'} {abs(q)} at {px}{' (ioc)' if ioc else ''}" for px, q, ioc in new)],
        ["filled", "; ".join(f"{'bought' if f.quantity > 0 else 'sold'} {abs(f.quantity)} at {f.price} ({f.source})" for f in fills) or "none"],
        ["position_after", result.positions["KELP"][TICK]],
        ["pnl_before", result.pnl["KELP"][TICK - 1]], ["pnl_after", result.pnl["KELP"][TICK]],
    ]
    write("one_tick", f"arena.engine.run_day(P3 1-0, the template) and the template's own fair_value, take, clear, make and execute on "
          f"Kelp's tick {TICK}: credits", ["key", "value"], rows)


# -- Chapter 15: the parameters, grouped, with the IDEAS row that tested each and its verdict ----------------------

# (group, the label on the figure, the DEFAULTS keys it covers, the IDEAS row's title or the start of it). The rows are
# docs/guidebook/research/repo_map.md's section C; the verdicts are parsed from IDEAS.md on every run.
PARAMETERS = [
    ("Quoting", "take_edge, make_edge, clear_edge", ["take_edge", "make_edge", "clear_edge"], "The template's market maker"),
    ("Quoting", "make_inside", ["make_inside"], "Quoting nearer fair than one tick inside the book"),
    ("Quoting", "per-side edges (*_buy, *_sell)", ["take_edge_buy", "take_edge_sell", "make_edge_buy", "make_edge_sell"], "Per-side edges"),
    ("Quoting", "make_levels, make_step", ["make_levels", "make_step"], "Laddered quotes"),
    ("Quoting", "take_reserve", ["take_reserve"], "A take reserve"),
    ("Quoting", "join_min, join_ratio", ["join_min", "join_ratio"], "A large-tick book"),
    ("Fair value", "fair: wall, outer or sized mid; wall_size", ["fair", "wall_size"], "Wall-mid definitions"),
    ("Fair value", "fair: weighted_mid", [], "The weighted mid as fair value"),
    ("Fair value", "fair: hysteresis_mid", [], "A large-tick book"),
    ("Fair value", "smoothing", ["smoothing"], "A slow fair on Osmium"),
    ("Fair value", "imbalance", ["imbalance"], "Book imbalance `ρ` and the micro-price"),
    ("Fair value", "lin_rho3", ["lin_rho3"], "A `linear` fair"),
    ("Fair value", "lin_momentum, lin_window", ["lin_momentum", "lin_window"], "A linear fair and a gate on the last move"),
    ("Inventory", "skew", ["skew"], "`skew` against Kelp's long position"),
    ("Inventory", "size_skew", ["size_skew"], "Inventory control through quote size"),
    ("Inventory", "target", ["target"], "A long bias on a drifting product"),
    ("Inventory", "make_size", ["make_size"], "Using less than the full position limit"),
    ("Inventory", "cross_max, cross_excess", ["cross_max", "cross_excess"], "Passive-first execution toward a target"),
    ("Target modes", "level, level_band, level_exit, level_weight", ["level", "level_band", "level_exit", "level_weight"],
     "Trading toward a known level"),
    ("Target modes", "level \"day\"", [], "The day's own level where the level drifts across days"),
    ("Target modes", "cpd_* (changepoints)", ["cpd_hazard", "cpd_reversion", "cpd_sd", "cpd_block", "cpd_action", "cpd_threshold"],
     "A changepoint detector on the level"),
    ("Target modes", "basket, hedge, hedge_ratio", ["basket", "hedge", "hedge_ratio"], "Trading a basket's spread"),
    ("Target modes", "smile, underlying, expiry, smile_window", ["smile", "underlying", "expiry", "smile_window", "day_length"],
     "Options: trading implied-volatility deviations"),
    ("Target modes", "follow, strike, max_cost_per_delta", ["follow", "strike", "max_cost_per_delta"], "What the P4 vouchers are"),
    ("Target modes", "jump_min, jump_*", ["jump_min", "jump_hold", "jump_edge", "jump_seen", "jump_share"], "Fading jumps that snap back"),
    ("Target modes", "copy, copy_hold, copy_edge", ["copy", "copy_hold", "copy_edge"], "Following informed counterparties"),
    ("Target modes", "copy_sizes, copy_warmup", ["copy_sizes", "copy_warmup"], "A nameless informed-trade detector"),
    ("Target modes", "gate_move, gate_window", ["gate_move", "gate_window"], "A linear fair and a gate on the last move"),
    ("Protection", "stop_loss, stop_edge", ["stop_loss", "stop_edge"], "A loss stop per product"),
    ("Protection", "fixed_fair, fixed_guard", ["fixed_fair", "fixed_guard"], "A fixed fair that gives way"),
    ("Protection", "level_guard", ["level_guard"], "Dropping a level bet once the price is far from the level"),
    ("Protection", "vol_guard", ["vol_guard"], "A volatility guard"),
    ("Protection", "flatten_from, flatten_edge, reduce_only", ["flatten_from", "flatten_edge", "reduce_only"], "Flattening before the close"),
    ("Protection", "flatten_keep, flatten_widen", ["flatten_keep", "flatten_widen"], "Keeping a small position at the close"),
    ("Execution", "DELAY, ORDERS_REST", [], "Orders that arrive a tick late"),
    ("Execution", "MAX_RESTING", [], "Order caps"),
]
UNTESTED = ["limit"]  # a rule of the exchange, not a choice: no row


def parameters() -> None:
    """Each group's parameters with their IDEAS row and its verdict, parsed as experiments.ideas_index parses it (the
    first of kept, dropped here, measured, open in backticks in the verdict cell), so a rebuild shows a change. Fails
    on a row it can't find, and on a DEFAULTS key in no entry."""
    sys.path.insert(0, str(ROOT / "python"))
    from experiments import ideas_index

    tested, _ = ideas_index.rows((ROOT / "IDEAS.md").read_text().splitlines())
    by_title = {title: verdict for _, title, verdict, _ in tested}
    tree = ast.parse((ROOT / TEMPLATE).read_text())
    defaults = next(node.value for node in tree.body if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "DEFAULTS")
    keys = [k.value for k in defaults.keys]
    covered = {key for *_, entry_keys, _ in PARAMETERS for key in entry_keys} | set(UNTESTED)
    if set(keys) - covered:
        raise SystemExit(f"DEFAULTS keys in no entry of PARAMETERS: {sorted(set(keys) - covered)}")
    rows = []
    for group, label, entry_keys, start in PARAMETERS:
        found = [title for title in by_title if title.startswith(start)]
        if len(found) != 1:
            raise SystemExit(f"IDEAS.md has {len(found)} rows starting {start!r}")
        rows.append([group, label, " ".join(entry_keys), found[0], by_title[found[0]]])
    write("parameters", f"IDEAS.md's verdicts (experiments.ideas_index.rows) for the template's parameters ({len(keys)} DEFAULTS keys; "
          "docs/guidebook/research/repo_map.md, C)", ["group", "label", "keys", "row", "verdict"], rows)


# -- Appendix B: the Prosperity days in references/ ------------------------------------------------------------------

def datasets() -> None:
    """Every Prosperity round the three backtesters' folders hold: its days and its products (as the plug-in lists them)."""
    sys.path.insert(0, str(ROOT / "python"))
    from arena.formats import prosperity

    rows = []
    for alias in ("p2", "p3", "p4"):
        folder = prosperity.resolve_data_dir(alias)
        rounds: dict[int, list[int]] = {}
        for round_num, day in prosperity.list_days(folder):
            rounds.setdefault(round_num, []).append(day)
        for round_num, days in sorted(rounds.items()):
            prices = sorted((folder / f"round{round_num}").glob("prices_*.csv"))[0]
            with prices.open() as file:
                products = sorted({row["product"] for row in csv.DictReader(file, delimiter=";")})
            rows.append([alias, round_num, len(days), " ".join(str(d) for d in sorted(days)), len(products),
                         " ".join(products) if len(products) <= 15 else f"{products[0]} ... {products[-1]}"])
    write("datasets", "arena.formats.prosperity.list_days on references/' p2, p3 and p4 folders; products from each round's first prices file",
          ["data", "round", "days", "day_numbers", "products", "names"], rows)


STEPS = {"kestrel": kestrel, "one_tick": one_tick, "parameters": parameters, "datasets": datasets}
