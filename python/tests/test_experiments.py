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
