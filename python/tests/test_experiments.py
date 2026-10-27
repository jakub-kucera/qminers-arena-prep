"""The experiments that ON_THE_DAY.md re-runs on the Arena's data take it through --data and
--format: each runs here on two short drill-format days (python/arena/formats/drill.py), as it
would on the day's download through its own plug-in. Their Prosperity defaults are what IDEAS.md
quotes, so those stay as they were (checked by hand against the previous output, not here: they
take minutes)."""

import importlib
import inspect
import sys
from pathlib import Path

import pytest

from arena import sim
from arena.formats import drill


@pytest.fixture(scope="module")
def drill_data(tmp_path_factory):
    """Two 400-tick drill sessions: KELP, RAINFOREST_RESIN and SQUID_INK as ALPHA, BETA and GAMMA."""
    out = tmp_path_factory.mktemp("drill")
    spec = sim.preset_market(ticks=400)
    for k in range(2):
        sim.write_day(sim.run(spec, 2000 + k), out / "prosperity", 1, k)
    drill.convert(out / "prosperity", 1, out / "drill")
    return str(out / "drill")


def run(capsys, monkeypatch, name: str, *args: str) -> str:
    module = importlib.import_module(f"experiments.{name}")
    monkeypatch.setattr(sys, "argv", [name, *args])
    if inspect.signature(module.main).parameters:
        module.main(list(args))
    else:
        module.main()
    return capsys.readouterr().out


DRILL = ("--format", "drill", "--jobs", "2")


@pytest.mark.parametrize("name, extra, expect", [
    ("adversaries", ("--days", "all"), "| every product sized_mid | template copy |"),
    ("undercut", ("--days", "all", "--war", "BETA"), "BETA, drill all, --resting"),
    ("quote_size", ("--days", "all"), "| drill all | Mode | Rival | ALPHA: full room"),
    ("quote_markouts", ("--days", "all"), "by spread:"),
    ("glft_skew", ("--days", "all", "--products", "ALPHA"), "ALPHA                committed"),
    ("counterparties", ("--days", "all"), "2. leave one day out"),
    ("p4_level_template", ("--days", "all", "--products", "BETA"), "1. nested leave-one-day-out"),
])
def test_an_experiment_runs_on_the_days_data_in_another_format(capsys, monkeypatch, drill_data, name, extra, expect):
    assert expect in run(capsys, monkeypatch, name, "--data", drill_data, *DRILL, *extra)


def test_suggest_check_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    # Suggested from the first session, scored on the second against the drill template as it is.
    out = run(capsys, monkeypatch, "suggest_check", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "| drill all | ALPHA | `{'fair': " in out and "| total |" in out


def test_imbalance_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "imbalance", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "| drill all | ALPHA |" in out


def test_lead_lag_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "lead_lag", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "## drill all" in out and "| ALPHA |  |" in out


def test_lead_lag_finds_a_planted_lead_one_way_and_nothing_between_unrelated_walks():
    import random

    from arena.model import Book, Day, Tick
    from experiments import lead_lag

    def day(seed, name):
        rng, a, c, ticks = random.Random(seed), [100], [500], []
        for _ in range(3000):
            a.append(a[-1] + rng.choice((-1, 0, 0, 1)))
            c.append(c[-1] + rng.choice((-1, 0, 0, 1)))
        b = [p + 200 for p in [a[0]] * 3 + a[:-3]]  # B is A three ticks late
        for t in range(len(a)):
            ticks.append(Tick(t * 100, {k: Book(((v - 2, 20),), ((v + 2, 20),)) for k, v in (("A", a[t]), ("B", b[t]), ("C", c[t]))}, {}, {}))
        return Day(name, ["A", "B", "C"], {"A": 10, "B": 10, "C": 10}, ticks)

    products = ["A", "B", "C"]
    result = lead_lag.study([day(1, "d1"), day(2, "d2")], products)
    assert lead_lag.leads(result, products) == [("A", "B")]
    assert result["pairs"][("A", "B", 5)]["follow"] == pytest.approx(1.0, abs=0.1)  # B repeats A's whole move
    assert abs(result["pairs"][("B", "A", 5)]["follow"]) < 0.1
    assert result["same"][("A", "C")] == pytest.approx(0, abs=0.05)


def test_lead_lag_finds_a_small_exact_lag_and_takes_other_horizons(capsys, monkeypatch, drill_data):
    import random

    from arena.model import Book, Day, Tick
    from experiments import lead_lag

    def day(seed, name):
        rng, a, b, c, ticks = random.Random(seed), [1000], [3000], [5000], []
        moves = [rng.choice((-2, -1, 1, 2)) for _ in range(4000)]
        for t, m in enumerate(moves):
            a.append(a[-1] + m)
            b.append(b[-1] + (moves[t - 40] if t >= 40 and rng.random() < 0.3 else 0) + rng.choice((-2, -1, 0, 1, 2)))  # B takes 30% of A's moves 40 ticks late
            c.append(c[-1] + rng.choice((-1, 0, 1)))
        for t in range(len(a)):
            ticks.append(Tick(t * 100, {k: Book(((v - 2, 20),), ((v + 2, 20),)) for k, v in (("A", a[t]), ("B", b[t]), ("C", c[t]))}, {}, {}))
        return Day(name, ["A", "B", "C"], {"A": 10, "B": 10, "C": 10}, ticks)

    found = lead_lag.lag_scan([day(1, "d1"), day(2, "d2")], ["A", "B", "C"], 60)
    assert [(r["a"], r["b"], r["lag"]) for r in found] == [("A", "B", 40)]
    assert found[0]["slope"] == pytest.approx(0.3, abs=0.05)
    out = run(capsys, monkeypatch, "lead_lag", "--data", drill_data, "--days", "all", "--format", "drill", "--horizons", "2,10", "--lags", "5")
    assert "at 2, 10 ticks" in out and "Exact lags: corr(ΔA at t, ΔB at t + k) for k = 1–5" in out


def test_the_reversion_term_of_a_flickering_price_is_minus_a_half():
    import random

    from experiments import reversion_term

    rng = random.Random(4)
    w = [100 + rng.choice((-1, 0, 1)) for _ in range(20_000)]  # a level plus independent noise: every move half reverts
    assert reversion_term.beta(w, 1) == pytest.approx(-0.5, abs=0.02)
    r = reversion_term.forecasts([w, w[::-1]], 1)
    assert reversion_term.rmse(r["beta"]) < reversion_term.rmse(r["plain"])


def test_jumps_and_selection_rules_run_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "p4_jumps", "--data", drill_data, "--days", "all", "--format", "drill", "--jump-min", "50", "--trade",
              "--jobs", "2")
    assert "2. the template on every product" in out
    out = run(capsys, monkeypatch, "selection_rules", "--data", drill_data, "--format", "drill", "--train", "0", "--test", "1",
              "--products", "ALPHA", "--grid", "make_edge=0.5,1", "--grid", "take_edge=0,1", "--jobs", "2")
    assert "| ALPHA: make_edge, take_edge (1) |" in out and "| ALPHA (reversed)" in out


def test_options_and_baskets_say_what_they_need(capsys, monkeypatch, drill_data):
    with pytest.raises(SystemExit):
        run(capsys, monkeypatch, "p4_vouchers", "all", "--data", drill_data, "--format", "drill", "--underlying", "ALPHA", "--prefix", "OPT_",
            "--expiry", "s0=5,s1=4")
    with pytest.raises(SystemExit):
        run(capsys, monkeypatch, "baskets", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "--data and --basket go together" in capsys.readouterr().err
    out = run(capsys, monkeypatch, "baskets", "--data", drill_data, "--days", "all", *DRILL, "--basket", "ALPHA=BETA:1")
    assert "2. nested leave-one-day-out" in out


def test_the_rival_field_runs_on_prosperity_format_days(capsys, monkeypatch, drill_data):
    """The archetypes are Prosperity bots: the field runs on the fixture's days before their drill conversion."""
    data = str(Path(drill_data).parent / "prosperity")
    out = run(capsys, monkeypatch, "rival_field", "--data", data, "--days", "1", "--products", "KELP,RAINFOREST_RESIN",
              "--candidate", "PARAMS.KELP.make_edge=1,2", "--jobs", "2")
    assert "| KELP.make_edge 1 |" in out and out.count("max-min:") == 2
    with pytest.raises(SystemExit):
        run(capsys, monkeypatch, "rival_field", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "Prosperity-format bots" in capsys.readouterr().err


def test_the_rival_field_game_runs_on_prosperity_format_days(capsys, monkeypatch, drill_data):
    data = str(Path(drill_data).parent / "prosperity")
    out = run(capsys, monkeypatch, "rival_field", "--game", "--background", "taker", "--data", data, "--days", "1",
              "--products", "KELP,RAINFOREST_RESIN", "--candidate", "PARAMS.KELP.make_edge=1,2", "--jobs", "2")
    assert "with taker in every game" in out and out.count("pure equilibria") == 4 and out.count("fictitious play") == 4
    assert "the seat (the engine's arrival order" in out


def test_the_games_equilibria_best_replies_and_fictitious_play():
    from experiments import rival_field as rf

    # matching pennies: no pure equilibrium, best replies cycle, fictitious play settles near half and half
    U = [[1.0, -1.0], [-1.0, 1.0]]
    V = [[-u for u in row] for row in U]
    assert rf.pure_equilibria(U, V) == []
    path, fixed = rf.best_reply_path(U, V, (0, 0))
    assert not fixed and path[-1] == (0, 1) and set(path[1:]) == {(0, 1), (1, 0)}  # a cycle between the two
    play = rf.fictitious_play(U, V, (0, 0), steps=4000)
    assert all(abs(f - 0.5) < 0.05 for f in play.p + play.q) and play.gain_row < 0.1 and play.gain_column < 0.1
    # a prisoner's dilemma: one equilibrium, reached from every start
    U = [[3.0, 0.0], [5.0, 1.0]]
    V = [list(col) for col in zip(*U)]
    assert rf.pure_equilibria(U, V) == [(1, 1)]
    assert all(rf.best_reply_path(U, V, (i, j)) == ([(i, j)] if (i, j) == (1, 1) else [(i, j), (1, 1)], True)
               for i in range(2) for j in range(2))
    play = rf.fictitious_play(U, V, (0, 0), steps=200)
    assert play.settled and play.p[1] > 0.99 and play.gain_row < 0.01 and play.gain_column < 0.01  # the start's one round of (0, 0) remains
    # both seats averaged: S[i][j] is setting i's PnL against j, whichever seat it had
    S, seat = rf.symmetrised([[1.0, 2.0], [3.0, 4.0]], [[1.0, 5.0], [2.0, 4.0]])
    assert S == [[1.0, 2.0], [4.0, 4.0]] and seat == 2.0


def test_the_days_data_options_need_data(capsys, monkeypatch):
    with pytest.raises(SystemExit):
        run(capsys, monkeypatch, "undercut", "--format", "drill")
    assert "give --data too" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        run(capsys, monkeypatch, "undercut", "--data", "p3")
    assert "--data needs --days" in capsys.readouterr().err


def test_kelp_drift_mirrors_a_day_and_the_template_mirrors_its_position():
    from arena.engine import run_day
    from experiments import kelp_drift

    day = sim.run(sim.preset_market(["KELP"], ticks=800), 3).day
    flipped = kelp_drift.mirrored(day)
    assert kelp_drift.flow(flipped, "KELP")[0] == pytest.approx(1 - kelp_drift.flow(day, "KELP")[0])
    a = run_day(day, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True))
    b = run_day(flipped, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True))
    assert a.fills and b.positions["KELP"] == [-x for x in a.positions["KELP"]]  # the template quotes symmetrically
    assert b.pnl["KELP"] == pytest.approx(a.pnl["KELP"])


def test_order_flow_splits_the_best_levels_changes_into_adds_and_removals():
    from arena.model import Book, Day, MarketTrade, Tick
    from experiments import imbalance

    books = [
        Book(((99, 5),), ((101, 5),)),
        Book(((99, 8),), ((101, 5),)),  # 3 added at the bid
        Book(((100, 2),), ((101, 1),)),  # a new, higher bid of 2; 4 removed at the ask
        Book(((99, 6),), ((102, 3),)),  # the bid of 2 gone; the ask of 1 gone
    ]
    trades = {3: [MarketTrade("X", 102, 2), MarketTrade("X", 99, 1), MarketTrade("X", 100, 7)]}  # a buy, a sell, one inside
    day = Day("d", ["X"], {"X": 10}, [Tick(t * 100, {"X": b}, {"X": trades[t]} if t in trades else {}, {}) for t, b in enumerate(books)])
    rows = imbalance.flows(day, "X")
    assert rows[0] is None
    assert [(r["adds"], r["removals"], r["ofi"]) for r in rows[1:]] == [(3, 0, 3), (2, 4, 6), (0, 1 - 2, -1)]
    assert rows[3]["trades"] == 2 - 1 and rows[3]["rho3"] == (6 - 3) / 9


def test_an_abides_export_converts_to_the_prosperity_layout(tmp_path):
    import json

    from arena.formats import prosperity
    from experiments import abides_days

    raw = tmp_path / "raw"
    raw.mkdir()
    open_ns = 1_000 * 1_000_000_000
    levels = lambda *pairs: [x for pair in pairs for x in pair] + [""] * (10 - 2 * len(pairs))
    header = ["second"] + [f"{s}_{k}_{i}" for s in ("bid", "ask") for i in range(1, 6) for k in ("price", "volume")]
    book = [header, [0] + levels() + levels(),  # no makers yet: dropped
            [1] + levels((99_998, 100), (99_997, 50)) + levels((100_000, 80)),
            [2] + levels((99_999, 10)) + levels((100_000, 80), (100_001, 5))]
    (raw / "book.csv").write_text("\n".join(",".join(map(str, r)) for r in book) + "\n")
    s = 1_000_000_000
    (raw / "trades.csv").write_text(
        "time_ns,price,quantity,aggressor,passive_agent_type,aggressor_agent_type\n"
        f"{open_ns + 2 * s},99990,1,SELL,ValueAgent,ValueAgent\n"  # by tick 0's snapshot (the end of second 1): dropped
        f"{open_ns + 2 * s + 1},99998,7,SELL,AdaptiveMarketMakerAgent,ValueAgent\n"  # just after it: tick 0's
        f"{open_ns + 3 * s + 1},100000,3,BUY,ValueAgent,NoiseAgent\n")  # after tick 1's: tick 1's
    (raw / "fundamental.csv").write_text(f"time_ns,value\n{open_ns},100000.0\n{open_ns + 3 * s},100002.5\n")
    (raw / "meta.json").write_text(json.dumps({"open_ns": open_ns}))

    assert abides_days.convert(raw, tmp_path / "data", 1, names=True) == 2
    (day,) = prosperity.load_days(tmp_path / "data", ["1-1"])
    assert day.limits == {"ABM": abides_days.LIMIT} and [t.timestamp for t in day.ticks] == [0, 100]
    first, second = (t.books["ABM"] for t in day.ticks)
    assert first.bids == ((99_998, 100), (99_997, 50)) and first.asks == ((100_000, 80),)
    assert second.bids == ((99_999, 10),) and second.asks == ((100_000, 80), (100_001, 5))
    (sold,) = day.ticks[0].trades["ABM"]
    (bought,) = day.ticks[1].trades["ABM"]
    assert (sold.price, sold.quantity, sold.buyer, sold.seller) == (99_998, 7, "AdaptiveMarketMakerAgent", "ValueAgent")
    assert (bought.price, bought.buyer, bought.seller) == (100_000, "NoiseAgent", "ValueAgent")
    fundamental = (tmp_path / "data" / "round1" / "fundamental_round_1_day_1.csv").read_text().splitlines()
    assert fundamental[1:] == ["0;ABM;100000.000", "100;ABM;100002.500"]


def test_the_abides_study_reads_the_fundamental_where_the_data_has_one(capsys, monkeypatch, tmp_path):
    spec = sim.preset_market(ticks=400)
    for k in range(2):
        sim.write_day(sim.run(spec, 3000 + k), tmp_path, 1, k)
    out = run(capsys, monkeypatch, "abides_study", "--data", str(tmp_path), "--days", "1", "--products", "KELP")
    assert "(against the fundamental now / the mid 50 ticks ahead)" in out and "| wall_mid | " in out
    assert "| 2 | " in out  # the continuation table's first row


def test_a_lobster_day_converts_to_the_prosperity_layout(tmp_path):
    from arena.formats import prosperity
    from experiments import lobster_days

    e = lobster_days.EMPTY
    # second 34200: an ask only (dropped); then the book at the end of 34201, 34202 and 34203
    events = [(34200.5, 1, 1, 100, 5_852_100, -1), (34201.2, 1, 2, 50, 5_851_900, 1), (34201.9, 4, 1, 10, 5_852_100, -1),
              (34202.4, 4, 2, 20, 5_851_900, 1), (34203.1, 1, 3, 40, 5_852_000, 1)]
    books = [[5_852_100, 100, -e, 0], [5_852_100, 100, 5_851_900, 50], [5_852_100, 90, 5_851_900, 50],
             [5_852_100, 90, 5_851_900, 30], [5_852_100, 90, 5_852_000, 40]]
    raw = tmp_path / "raw"
    raw.mkdir()
    pad = lambda row: row + [e, 0, -e, 0] * 2  # levels 2 and 3 empty
    (raw / "AAPL_2012-06-21_34200000_57600000_message_3.csv").write_text("\n".join(",".join(map(str, r)) for r in events) + "\n")
    (raw / "AAPL_2012-06-21_34200000_57600000_orderbook_3.csv").write_text("\n".join(",".join(map(str, pad(b))) for b in books) + "\n")
    lobster_days.main([str(raw), "--out", str(tmp_path / "data")])

    (day,) = prosperity.load_days(tmp_path / "data", ["1-1"])
    assert day.products == ["AAPL"] and day.limits == {"AAPL": lobster_days.LIMIT}
    assert [(t.books["AAPL"].bids, t.books["AAPL"].asks) for t in day.ticks] == [
        (((58_519, 50),), ((58_521, 90),)), (((58_519, 30),), ((58_521, 90),)), (((58_520, 40),), ((58_521, 90),))]
    # the execution in second 34202 (after tick 0's snapshot at the end of 34201) is tick 0's; 34201's is before any tick
    assert {t.timestamp: [(x.price, x.quantity) for x in t.trades.get("AAPL", [])] for t in day.ticks} == {0: [(58_519, 20)], 100: [], 200: []}

def test_structure_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "structure", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "## drill all" in out and "### Fixed sums: searched on" in out and "| ALPHA |" in out


def test_structure_finds_a_planted_sum_repeat_stream_grid_and_cycle():
    import math
    import random

    from arena.model import Book, Day, Tick
    from experiments import structure

    def walk(rng, start, n, steps=(-1, 0, 0, 1)):
        out = [start]
        for _ in range(n - 1):
            out.append(out[-1] + rng.choice(steps))
        return out

    n, days, replayed = 600, [], None
    for k in range(3):
        rng = random.Random(10 + k)
        a, b = walk(rng, 10_000, n), walk(rng, 9_000, n)
        c = [30_000 - x - y for x, y in zip(a, b)]  # X_A + X_B + X_C = 30,000
        if k < 2:  # D's moves on day 2 replay day 1's, from another level
            replayed = replayed or [rng.choice((-1, 0, 1)) for _ in range(n - 1)]
            d = [500 + 100 * k]
            for m in replayed:
                d.append(d[-1] + m)
        else:
            d = walk(rng, 700, n)
        g = walk(rng, 5_000, n, steps=(-5, 0, 0, 5))  # on a grid of 5
        s = [2_000 + round(8 * math.sin(2 * math.pi * t / 20)) + x for t, x in enumerate(walk(rng, 0, n, (-1, 0, 1)))]  # a 20-tick cycle
        ticks = []
        for t in range(n):
            shared, own, other = rng.randint(1, 9), rng.randint(1, 9), rng.randint(1, 9)  # X_A and X_B draw their inner order from one stream
            books = {}
            for name, price, inner in (("X_A", a[t], shared), ("X_B", b[t], shared), ("X_C", c[t], own), ("D", d[t], other), ("G", g[t], 3), ("S", s[t], 4)):
                books[name] = Book(((price - 1, inner), (price - 2, 20)), ((price + 2, 20),))
            ticks.append(Tick(t * 100, books, {}, {}))
        days.append(Day(f"d{k + 1}", list(books), {p: 10 for p in books}, ticks))
    products = ["X_A", "X_B", "X_C", "D", "G", "S"]

    found = structure.sums(days, products, structure.groups_of(products, []), [{"X_A": 1, "X_B": 1}])
    group = found["groups"][0]
    assert group["members"] == ["X_A", "X_B", "X_C"]
    assert group["best"][0]["weights"] == (1, 1, 1) and group["best"][0]["verdict"] == "identity"
    assert group["best"][0]["means"] == [30_000, 30_000, 30_000]
    assert found["checks"][0][1]["verdict"] == "none"  # two of the three legs are no identity
    pairs = structure.repeats(days, products)["pairs"]
    assert [(a, b, off) for a, b, count, total, off in pairs if count == total] == [(("D", "d1"), ("D", "d2"), 0), (("D", "d2"), ("D", "d1"), 0)]
    assert [(a, b) for a, b, *_ in structure.streams(days, products)] == [("X_A", "X_B")]
    assert structure.increments(days, "G")["grid"][0] == 5 and structure.increments(days, "X_A")["grid"] is None
    assert abs(structure.moves(days, "S")["peaks"][0][0] - 20) < 0.5
    assert structure.starts(days, "X_A")["reading"] != "each day continues the last"  # each day starts at 10,000 again


def test_repeats_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "repeats", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "## drill all" in out and "| ALPHA |" in out


def test_repeats_finds_a_taker_that_comes_back_the_next_day():
    import random

    from arena.model import Book, Day, MarketTrade, Tick
    from experiments import repeats

    def day(name, seed, plan):
        rng = random.Random(seed)
        ticks = []
        for i in range(1000):
            book = Book(((99, 20),), ((101, 20),))
            trades = {"R": [MarketTrade("R", 101 if plan[i] > 0 else 99, abs(plan[i]))]} if plan.get(i) else {}
            if rng.random() < 0.05:  # B's trades are new every day
                trades["B"] = [MarketTrade("B", rng.choice((99, 101)), rng.randint(1, 9))]
            ticks.append(Tick(i * 100, {"R": book, "B": book}, trades, {}))
        return Day(name, ["R", "B"], {"R": 20, "B": 20}, ticks)

    taker = {i: random.Random(i).choice((-8, 9, 2, -3)) for i in range(0, 1000, 37)}  # R's taker: the same ticks, sides and sizes
    days = [day("d1", 1, taker), day("d2", 2, taker), day("d3", 3, {})]
    rows = repeats.study(days, "R")
    assert rows[0]["all"][:2] == (len(taker), len(taker)) and rows[0]["all"][2] < 0.05
    assert rows[0]["big"][:2] == (sum(1 for q in taker.values() if abs(q) >= 7),) * 2
    assert rows[1]["all"][1] == 0 and rows[0]["two"] == (0.0, None)
    assert repeats.flagged(rows[:1]) == ["all", "small", "big"] and repeats.flagged(repeats.study(days[:2], "B")) == []
    assert repeats.predicted(days[:2], "R") == [(i * 100, 1 if q > 0 else -1, abs(q), 1) for i, q in sorted(taker.items())]


def test_quote_markouts_autocov_is_negative_for_a_bounce_and_positive_for_runs():
    from experiments.quote_markouts import autocov

    import itertools

    bounce = [100 + (k % 2) for k in range(20)]
    runs = [100, *itertools.accumulate([0, 0, 0, 1, 1, 1] * 3, initial=100)]  # moves that come in runs of three
    assert autocov(bounce, 19) < 0 and autocov([100 + k for k in range(20)], 19) == 0
    assert autocov(runs, len(runs) - 1) > 0


def test_family_fills_counts_clustered_ticks_against_independence(capsys, monkeypatch, drill_data):
    from experiments import family_fills

    assert family_fills.families(["A_X", "A_Y", "B_Z"]) == {"A": ["A_X", "A_Y"]}
    assert family_fills.at_least_two([0.5, 0.5]) == pytest.approx(0.25)
    together = [{"A_X": 1, "A_Y": 1}, {}, {}, {}] * 25  # both fill on the same ticks, each a quarter of the time
    c = family_fills.clustering(together, ["A_X", "A_Y"])
    assert c["observed"] == 25 and c["expected"] == pytest.approx(100 / 16) and c["same"] == 25
    out = run(capsys, monkeypatch, "family_fills", "--data", drill_data, "--days", "all", "--format", "drill", "--jobs", "2")
    assert "0. The market's trade ticks" in out


def test_fill_curve_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "fill_curve", "--data", drill_data, "--days", "all", "--format", "drill", "--products", "ALPHA")
    assert "### drill all ALPHA" in out and "The fill-size curve" in out


def test_fill_curve_reads_a_results_zip_and_a_per_tick_all_run_takes_every_print(tmp_path, monkeypatch):
    import csv
    import zipfile

    from arena.engine import EngineConfig, TradeMatching, run_day
    from arena.report import write_csvs
    from experiments import fill_curve, kelp_drift

    day = sim.run(sim.preset_market(["KELP"], ticks=1500), 5).day
    shares = {}
    for name, config in (("all", EngineConfig()), ("worse", EngineConfig(trade_matching=TradeMatching.WORSE))):
        write_csvs(run_day(day, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True), config), tmp_path / name)
        archive = tmp_path / f"{name}.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for path in (tmp_path / name).iterdir():
                z.write(path, f"results/{path.name}")
        cells = fill_curve.queue_share(day, "KELP", fill_curve.read_results(archive)[day.name])
        assert sum(c["ours"] for c in cells.values()) > 20
        shares[name] = sum(c["ours"] for c in cells.values()) / sum(c["market"] for c in cells.values())
    assert shares["all"] == 1.0 and shares["worse"] < 1.0  # every print at or beyond the quote fills it, only under `all`

    # A ZIP with other names: an unsigned quantity and a side column, mapped through RESULT_COLUMNS.
    folder = tmp_path / "theirs"
    folder.mkdir()
    for kind in ("fills", "orders"):
        with (tmp_path / "all" / f"{day.name}_{kind}.csv").open() as src, (folder / f"{kind}-{day.name}.csv").open("w", newline="") as dst:
            out = csv.writer(dst)
            out.writerow(["time", "symbol", "px", "qty", "side", "oid"])
            for row in csv.DictReader(src):
                q = int(row["quantity"])
                out.writerow([row["timestamp"], row["product"], row["price"], abs(q), "BUY" if q > 0 else "SELL", row.get("order_id") or row["id"]])
    monkeypatch.setattr(fill_curve, "RESULT_FILES", {"fills": "fills-{day}.csv", "orders": "orders-{day}.csv"})
    monkeypatch.setattr(fill_curve, "RESULT_COLUMNS", {
        "fills": {"timestamp": "time", "product": "symbol", "price": "px", "quantity": "qty", "side": "side", "order_id": "oid", "source": None},
        "orders": {"timestamp": "time", "id": "oid", "product": "symbol", "price": "px", "quantity": "qty", "side": "side"},
    })
    mapped = fill_curve.queue_share(day, "KELP", fill_curve.read_results(folder)[day.name])
    assert sum(c["ours"] for c in mapped.values()) / sum(c["market"] for c in mapped.values()) == 1.0


def test_shortfall_reads_a_runs_csvs_and_values_fills_at_the_decision(tmp_path, capsys, monkeypatch):
    from arena.engine import EngineConfig, run_day
    from arena.formats import prosperity
    from arena.report import write_csvs
    from experiments import kelp_drift, shortfall

    sim.write_day(sim.run(sim.preset_market(["KELP"], ticks=1200), 9), tmp_path / "data", 1, 0)
    (day,) = prosperity.load_days(tmp_path / "data", ["1"])
    wall = shortfall.fairs(day, "KELP")
    index = {tick.timestamp: i for i, tick in enumerate(day.ticks)}
    for delay in (0, 2):
        result = run_day(day, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True), EngineConfig(delay=delay))
        parts = shortfall.shortfall(day, "KELP", shortfall.rows_of(result), delay)
        # Against the fair where the fills happened (orders here live one tick, so that is their arrival), the edge is the fills' capture.
        capture = sum(f.quantity * (wall[index[f.timestamp]] - f.price) for f in result.fills)
        assert sum(c["edge_arrival"] for c in parts.values()) == pytest.approx(capture)
        assert sum(c["filled"] for c in parts.values()) == sum(abs(f.quantity) for f in result.fills) > 0
        if delay == 0:
            assert all(c["edge_decision"] == c["edge_arrival"] for c in parts.values())
    write_csvs(result, tmp_path / "out")
    out = run(capsys, monkeypatch, "shortfall", "--data", str(tmp_path / "data"), "--days", "1", "--results", str(tmp_path / "out"), "--delay", "2")
    assert "| KELP | quote |" in out
