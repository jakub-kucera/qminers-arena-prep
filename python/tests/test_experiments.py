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
