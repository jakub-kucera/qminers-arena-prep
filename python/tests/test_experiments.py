"""The experiments that ON_THE_DAY.md re-runs on the Arena's data take it through --data and
--format: each runs here on two short drill-format days (python/arena/formats/drill.py), as it
would on the day's download through its own plug-in. Their Prosperity defaults are what IDEAS.md
quotes, so those stay as they were (checked by hand against the previous output, not here: they
take minutes)."""

import importlib
import importlib.util
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
    for package in ("experiments.day", "experiments.study", "experiments"):  # day tools, studies, then the tools at the top
        if importlib.util.find_spec(f"{package}.{name}") is not None:
            module = importlib.import_module(f"{package}.{name}")
            break
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
    from experiments.day import lead_lag

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
    from experiments.day import lead_lag

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

    from experiments.study import reversion_term

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


def test_the_ou_bands_reproduce_cartea_et_als_table_and_the_fit_recovers_kappa():
    import math
    import random

    from experiments.day import baskets

    # Algorithmic and High-Frequency Trading, section 11.3.3's table: rho 0.01, sigma 0.5, theta 1, c 0.01.
    for kappa, (long_entry, short_entry) in ((1.0, (-0.1815, 1.7460)), (4.0, (-0.0410, 1.4367))):
        assert baskets.ou_bands(kappa, 0.5, 1.0, 0.01, 0.01) == (pytest.approx(long_entry, abs=2e-4), pytest.approx(short_entry, abs=2e-4))
    rng, b = random.Random(3), math.exp(-0.01)
    days = []
    for _ in range(3):
        x, path = 0.0, []
        for _ in range(10_000):
            x = b * x + rng.gauss(0, 1)
            path.append(50 + x)
        days.append(path)
    kappa, sigma = baskets.ou_fit(days)
    assert kappa == pytest.approx(0.01, rel=0.15) and sigma == pytest.approx(math.sqrt(2 * 0.01 / (1 - b * b)), rel=0.05)


def test_quote_by_state_picks_a_distance_per_spread_and_the_variant_quotes_it(tmp_path):
    from arena.botfile import BotFile
    from arena.formats import prosperity_datamodel
    from experiments.day.fill_curve import by_state
    from experiments.study import quote_by_state

    def row(spread, far):  # a tick whose prints reach `far` ticks on the bid side, none on the ask
        return {"spread": spread, "rho": 0.0, "bid": [(far, 1)], "ask": [], "move": 0.0}

    days = [[row(1, 0.5), row(4, 2)] * 50 for _ in range(3)]  # tight: prints at 0.5; wide: at 2
    for _, choice, single, state, flat in by_state(days, (0.5, 2)):
        assert choice == {"1": 0.5, "4": 2} and state > flat
    path = tmp_path / "variant.py"
    path.write_text(quote_by_state.variant())
    bot = BotFile(path, {"datamodel": prosperity_datamodel}, strict=True).load()
    assert bot.DEFAULTS["edge_by_spread"] is None and bot.spread_key(3) == "3" and bot.spread_key(7) == "5-8"
    book, p = bot.Book([[96, 10]], [[104, 10]]), {**bot.DEFAULTS, "limit": 10, "make_inside": None}
    plan = bot.Plan(0, 10)
    bot.make(book, 100.0, {**p, "edge_by_spread": {"5-8": 3}}, plan)  # an 8-wide spread: 3 from fair
    assert [price for price, _ in plan.quotes] == [97, 103]


def test_basket_trades_are_signed_against_the_ticks_book():
    from arena.model import Book, MarketTrade
    from experiments.study.cross_product_timing import signed_volume

    book = Book(((99, 5),), ((103, 5),))
    trades = [MarketTrade("B", 103, 2), MarketTrade("B", 98, 3), MarketTrade("B", 102, 1), MarketTrade("B", 101, 7)]
    assert signed_volume(trades, book) == 2 - 3 + 1  # at the ask, through the bid, above the mid; at the mid unsigned


def test_an_option_named_without_a_strike_takes_one_and_a_single_strike_fits_flat():
    from types import SimpleNamespace

    from experiments.day import p3_smile, p4_vouchers

    day = SimpleNamespace(products=["COCONUT", "COCONUT_COUPON", "VEV_5000"])
    assert p4_vouchers.strikes(day, "COCONUT_COUPON") == []
    assert p4_vouchers.strikes(day, "COCONUT_COUPON", 10_000) == [("COCONUT_COUPON", 10_000)]
    assert p4_vouchers.strikes(day, "VEV_") == [("VEV_5000", 5000)]
    rows = [{"K": 10_000, "m": m, "v": v} for m, v in ((-0.01, 0.19), (0.0, 0.2), (0.02, 0.21))]
    assert p3_smile.fit_parabola(rows) == (0.0, 0.0, pytest.approx(0.2))  # one strike: no parabola across strikes


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
    from experiments.day import rival_field as rf

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
    from experiments.study import kelp_drift

    day = sim.run(sim.preset_market(["KELP"], ticks=800), 3).day
    flipped = kelp_drift.mirrored(day)
    assert kelp_drift.flow(flipped, "KELP")[0] == pytest.approx(1 - kelp_drift.flow(day, "KELP")[0])
    a = run_day(day, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True))
    b = run_day(flipped, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True))
    assert a.fills and b.positions["KELP"] == [-x for x in a.positions["KELP"]]  # the template quotes symmetrically
    assert b.pnl["KELP"] == pytest.approx(a.pnl["KELP"])


def test_order_flow_splits_the_best_levels_changes_into_adds_and_removals():
    from arena.model import Book, Day, MarketTrade, Tick
    from experiments.day import imbalance

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


def test_abides_market_keeps_each_setups_runs_apart_and_flags_a_runaway_day(tmp_path, monkeypatch):
    from experiments.study import abides_market

    monkeypatch.setattr(abides_market, "MARKET", tmp_path)
    monkeypatch.setitem(abides_market.SETUP, "options", {})
    assert abides_market._folder(1) == tmp_path / "seed1"
    monkeypatch.setitem(abides_market.SETUP, "options", {"num_momentum_agents": 50})
    folder = abides_market._folder(1)
    assert folder.parent.name.startswith("options-") and folder.name == "seed1"
    data = folder / "data" / "round1"
    data.mkdir(parents=True)
    header = "day;timestamp;product;bid_price_1;bid_volume_1;ask_price_1;ask_volume_1;mid_price;profit_and_loss"
    ticks = ["1;0;ABM;99;1;101;1;100.0;0", "1;100;ABM;;;301;1;301.0;0", "1;200;ABM;199;1;201;1;200.0;0", "1;300;ABM;99;1;101;1;100.0;0"]
    (data / "prices_round_1_day_1.csv").write_text("\n".join([header, *ticks]) + "\n")
    (data / "fundamental_round_1_day_1.csv").write_text("timestamp;product;value\n" + "".join(f"{k * 100};ABM;100.0\n" for k in range(4)))
    one_sided, off = abides_market.sanity(1)
    assert one_sided == 0.25 and off == 1.0  # a side empty a quarter of the time, the mid at twice the fundamental
    assert one_sided > abides_market.BROKEN[0] and off > abides_market.BROKEN[1]


def test_abides_days_wont_mix_days_written_by_other_export_code(tmp_path, monkeypatch):
    import json

    from experiments import abides_days

    code = tmp_path / "abides_export"
    code.mkdir()
    (code / "export.py").write_text("print(1)\n")
    monkeypatch.setattr(abides_days, "EXPORT", code)
    first = abides_days.code_hash()
    for seed, written in ((1, first), (2, "0123456789abcdef"), (3, None)):
        (tmp_path / "raw" / f"seed{seed}").mkdir(parents=True)
        (tmp_path / "raw" / f"seed{seed}" / "meta.json").write_text(json.dumps({"seed": seed, **({"code": written} if written else {})}))
    assert [m.parent.name for m in abides_days.stale(tmp_path)] == ["seed2", "seed3"]  # no hash: written before 2026-10-28
    (code / "export.py").write_text("print(2)\n")
    assert abides_days.code_hash() != first and len(abides_days.stale(tmp_path)) == 3
    with pytest.raises(SystemExit, match="other export code"):
        abides_days.main(["generate", "--days", "1", "--out", str(tmp_path)])


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
    # a level-1 file (one level a side) converts the same
    one = tmp_path / "raw1"
    one.mkdir()
    (one / "AAPL_2012-06-21_34200000_57600000_message_1.csv").write_text("\n".join(",".join(map(str, r)) for r in events) + "\n")
    (one / "AAPL_2012-06-21_34200000_57600000_orderbook_1.csv").write_text("\n".join(",".join(map(str, b)) for b in books) + "\n")
    lobster_days.main([str(one), "--out", str(tmp_path / "data1")])
    (day1,) = prosperity.load_days(tmp_path / "data1", ["1-1"])
    assert [(t.books["AAPL"].bids, t.books["AAPL"].asks) for t in day1.ticks] == [(t.books["AAPL"].bids, t.books["AAPL"].asks) for t in day.ticks]

def test_structure_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "structure", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "## drill all" in out and "### Fixed sums: searched on" in out and "| ALPHA |" in out


def test_structure_finds_a_planted_sum_repeat_stream_grid_and_cycle():
    import math
    import random

    from arena.model import Book, Day, Tick
    from experiments.day import structure

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


def test_hidden_depth_counts_trades_outside_every_level_shown():
    from arena.model import Book, Day, MarketTrade, Tick
    from experiments.day import structure

    book = Book(((99, 5), (97, 20)), ((101, 5), (103, 20)))
    empty_bid = Book((), ((101, 5), (103, 20)))
    trades = [{}, {"X": [MarketTrade("X", 98, 2)]}, {"X": [MarketTrade("X", 90, 1), MarketTrade("X", 103, 1)]}, {"X": [MarketTrade("X", 110, 1)]}]
    ticks = [Tick(i * 100, {"X": b}, trades[i], {}) for i, b in enumerate((book, book, empty_bid, empty_bid))]
    h = structure.hidden_depth([Day("d", ["X"], {"X": 10}, ticks)], "X")
    # 98 sits between shown levels; 90 is below the last tick's lowest bid (97) by 7; 103 is shown; 110 is 7 above 103
    assert h["trades"] == 4 and h["outside"] == pytest.approx(2 / 4) and h["furthest"] == 7


def test_repeats_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "repeats", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "## drill all" in out and "| ALPHA |" in out


def test_repeats_finds_a_taker_that_comes_back_the_next_day():
    import random

    from arena.model import Book, Day, MarketTrade, Tick
    from experiments.day import repeats

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
    from experiments.day.quote_markouts import autocov

    import itertools

    bounce = [100 + (k % 2) for k in range(20)]
    runs = [100, *itertools.accumulate([0, 0, 0, 1, 1, 1] * 3, initial=100)]  # moves that come in runs of three
    assert autocov(bounce, 19) < 0 and autocov([100 + k for k in range(20)], 19) == 0
    assert autocov(runs, len(runs) - 1) > 0



def test_quote_markouts_exhaustion_is_hits_before_over_the_size_at_the_best():
    from experiments.day.quote_markouts import exhaustion

    hits, sizes = [0, 4, 0, 6, 9], [10, 10, 10, 10, 10]
    assert exhaustion(hits, sizes, 4, 3) == pytest.approx((4 + 0 + 6) / 30)  # tick 4's own hits come after its book
    assert exhaustion([0] * 5, sizes, 4, 3) == 0 and exhaustion(hits, [0] * 5, 4, 3) == 0


def test_the_exhaustion_gate_variant_patches_the_template_and_pulls_the_side_being_hit(tmp_path):
    from arena.botfile import BotFile
    from arena.formats import prosperity_datamodel
    from experiments.study import exhaustion_gate

    path = tmp_path / "variant.py"
    path.write_text(exhaustion_gate.variant())
    bot = BotFile(path, {"datamodel": prosperity_datamodel}, strict=True).load()
    assert bot.DEFAULTS["gate_ber"] is None
    gate, book = bot.exhaustion_gate, bot.Book([[99, 10]], [[101, 10]])
    p, memory = {"gate_ber": 0.5, "ber_window": 2}, {}
    assert gate([], book, p, memory) == 0  # no book before it yet
    assert gate([("", "", 8, 99)], book, p, memory) == 0  # one call of the window
    assert gate([("", "", 4, 99), ("", "", 1, 101)], book, p, memory) == -1  # 12 sold into 20 at the bid: pull it
    assert gate([("", "", 12, 101)], book, p, memory) == 1

def test_the_family_skew_variant_moves_a_target_against_the_rest_of_the_family(tmp_path):
    from arena.botfile import BotFile
    from arena.formats import prosperity_datamodel
    from experiments.study import family_skew

    path = tmp_path / "variant.py"
    path.write_text(family_skew.variant({"A_X": 10, "A_Y": 20, "B_Z": 5}))
    bot = BotFile(path, {"datamodel": prosperity_datamodel}, strict=True).load()
    assert bot.DEFAULTS["family_weight"] == 0.0
    assert bot.PARAMS["A_X"]["family"] == ["A_Y"] and bot.PARAMS["B_Z"] == {"limit": 5, "family": []}
    book = bot.Book([[99, 10]], [[101, 10]])
    market = bot.Market({"A_X": book, "A_Y": book})
    market.positions = {"A_Y": 10}  # half A_Y's limit
    p = {**bot.params_for("A_X"), "family_weight": 1.0}
    assert bot.trade_product("A_X", book, 0, p, {}, market).target == -5  # half of A_X's limit, against it
    market.positions = {"A_Y": 40}
    assert bot.trade_product("A_X", book, 0, p, {}, market).target == -10  # clamped to the limit
    assert bot.trade_product("A_X", book, 0, {**p, "family_weight": 0.0}, {}, market).target == 0


def test_family_fills_counts_clustered_ticks_against_independence(capsys, monkeypatch, drill_data):
    from experiments.day import family_fills

    assert family_fills.families(["A_X", "A_Y", "B_Z"]) == {"A": ["A_X", "A_Y"]}
    assert family_fills.at_least_two([0.5, 0.5]) == pytest.approx(0.25)
    together = [{"A_X": 1, "A_Y": 1}, {}, {}, {}] * 25  # both fill on the same ticks, each a quarter of the time
    c = family_fills.clustering(together, ["A_X", "A_Y"])
    assert c["observed"] == 25 and c["expected"] == pytest.approx(100 / 16) and c["same"] == 25
    out = run(capsys, monkeypatch, "family_fills", "--data", drill_data, "--days", "all", "--format", "drill", "--jobs", "2")
    assert "0. The market's trade ticks" in out


def test_informed_flags_a_buy_at_the_days_low_and_the_template_can_copy_it(capsys, monkeypatch, drill_data):
    from arena.model import Book, Day, MarketTrade, Tick
    from experiments.day import informed

    monkeypatch.setattr(informed, "WARMUP", 2)
    path = [100, 99, 98, 97, 96, 97, 98, 99, 100, 101]  # the wall mid: down to a low at tick 4, then up; a sell at the low of tick 2 is against it
    trades = {4: [MarketTrade("X", 97, 15, "Olivia", "b")], 2: [MarketTrade("X", 97, 15, "c", "d")], 7: [MarketTrade("X", 98, 2, "e", "f")]}
    ticks = [Tick(k * 100, {"X": Book(((p - 1, 20),), ((p + 1, 20),))}, {"X": trades.get(k, [])}, {}) for k, p in enumerate(path)]
    day = Day("d", ["X"], {"X": 50}, ticks)
    ev = informed.events(day, "X", informed.size_classes([day], "X"))
    by_tick = {t["i"]: t for t in ev["trades"]}
    assert by_tick[4]["extreme"] and by_tick[4]["side"] == 1 and by_tick[4]["name"] == "Olivia"  # a buy at the ask, at the low
    assert not by_tick[2]["extreme"] and not by_tick[7]["extreme"]
    blank = informed.anonymous(day)
    assert [(t.buyer, t.seller, t.quantity) for tick in blank.ticks for t in tick.trades["X"]] == [("", "", 15), ("", "", 15), ("", "", 2)]
    assert informed.sizes_in(["15", "4-7"]) == [4, 5, 6, 7, 15]  # an octave is every size in it, for the template's copy_sizes
    out = run(capsys, monkeypatch, "informed", "--data", drill_data, "--days", "all", "--format", "drill", "--jobs", "2")
    assert "2. Leave one day out" in out


def test_predict_ridge_recovers_a_planted_linear_rule_and_reads_feed_files(capsys, monkeypatch, tmp_path, drill_data):
    import random

    from experiments.day import predict

    rng = random.Random(1)
    days = []
    for _ in range(2):
        xs = [[rng.gauss(0, 1), rng.gauss(0, 3)] for _ in range(2000)]
        days.append(predict.sufficient(xs, [2 * a - b + rng.gauss(0, 0.1) for a, b in xs]))
    monkeypatch.setattr(predict, "RIDGE", 1e-6)
    beta, mu, sd, _ = predict.ridge(days)
    assert [b / s for b, s in zip(beta, sd)] == pytest.approx([2, -1], abs=0.02)

    for k in range(2):
        sim.write_day(sim.run(sim.preset_market(["KELP"], ticks=600), 30 + k), tmp_path / "data", 1, k)
    out = run(capsys, monkeypatch, "predict", "--data", str(tmp_path / "data"), "--days", "1")
    assert "| fundamental.value |" in out and "R² pooled" in out
    out = run(capsys, monkeypatch, "predict", "--data", drill_data, "--days", "all", "--format", "drill", "--part", "2")
    assert "### drill all ALPHA" in out


def test_the_forecast_sees_a_ticks_trades_a_tick_later(tmp_path):
    from arena.formats import prosperity
    from experiments.day import predict

    sim.write_day(sim.run(sim.preset_market(["KELP"], ticks=400), 31), tmp_path, 1, 0)
    (day,) = prosperity.load_days(tmp_path, ["1-0"])
    names, xs, rows = predict.feature_rows(day, ["KELP"], "KELP")
    k = names.index("trades")
    checked = [(i, x) for i, x in enumerate(xs) if x is not None]
    assert checked and all(x[k] == rows[i - 1]["trades"] for i, x in checked)  # the trades before the snapshot, not after
    assert any(rows[i]["trades"] != rows[i - 1]["trades"] for i, _ in checked)


def test_fill_curve_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "fill_curve", "--data", drill_data, "--days", "all", "--format", "drill", "--products", "ALPHA")
    assert "### drill all ALPHA" in out and "The fill-size curve" in out


def test_fill_curve_reads_a_results_zip_and_a_per_tick_all_run_takes_every_print(tmp_path, monkeypatch):
    import csv
    import zipfile

    from arena.engine import EngineConfig, TradeMatching, run_day
    from arena.report import write_csvs
    from experiments.day import fill_curve
    from experiments.study import kelp_drift

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


def test_fill_curve_counts_a_resting_quote_the_next_snapshot_crossed(tmp_path):
    from arena.engine import EngineConfig, QueueModel, run_day
    from arena.report import write_csvs
    from experiments.day import fill_curve
    from experiments.study import kelp_drift

    day = sim.run(sim.preset_market(["KELP"], ticks=1500), 5).day
    write_csvs(run_day(day, kelp_drift.FMT.load_bot(kelp_drift.TEMPLATE, {}, strict=True), EngineConfig(resting=True, queue=QueueModel.PROB)), tmp_path)
    results = fill_curve.read_results(tmp_path)[day.name]
    crosses = sum(abs(f["quantity"]) for f in results["fills"] if f["product"] == "KELP" and f.get("source") == "cross")
    assert crosses > 0
    lots = lambda r: sum(c["our_lots"] for c in fill_curve.queue_share(day, "KELP", r).values())
    without = {**results, "fills": [f for f in results["fills"] if f.get("source") != "cross"]}
    assert lots(results) - lots(without) > 0.5 * crosses  # the crossed fills match the quotes they came from


def test_shortfall_reads_a_runs_csvs_and_values_fills_at_the_decision(tmp_path, capsys, monkeypatch):
    from arena.engine import EngineConfig, run_day
    from arena.formats import prosperity
    from arena.report import write_csvs
    from experiments.day import shortfall
    from experiments.study import kelp_drift

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


def test_the_premise_check_reads_a_market_whose_order_matters():
    from experiments.day import premise

    pays = {"notes": "market making pays (0.4 of the spread a unit)"}
    kind, todo = premise.verdict("X", (10_000.0, 10_200.0), pays, fires=False)
    assert kind == "Prosperity-like" and "priors stand" in todo[0]
    informed = {"notes": "trades move the wall mid; thin or negative market-making margin; large-tick (one-tick spread 70%)"}
    kind, todo = premise.verdict("X", (28_000.0, 1_500_000.0), informed, fires=True)
    assert kind == "agent-like" and any("lin_rho3" in line for line in todo) and any("gate_move" in line for line in todo)
    kind, todo = premise.verdict("X", (6_987.0, 10_742.0), pays, fires=False)  # P3's Squid Ink: the shuffle test alone
    assert kind == "mixed" and "the order costs the bot" in todo[0] and "priors stand" in todo[0] and any("gate_move" in line for line in todo)
    large = {"notes": "large-tick (one-tick spread 100%); market making pays (0.5 of the spread a unit)"}
    assert any("make_edge 0.5" in line for line in premise.verdict("X", (5_000.0, 5_000.0), large, fires=False)[1])


def test_the_premise_check_runs_on_the_days_data(capsys, monkeypatch, drill_data):
    out = run(capsys, monkeypatch, "premise", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "| ALPHA |" in out and "verdict" in out



def test_the_premise_check_runs_under_the_formats_rules(capsys, monkeypatch, drill_data):
    # The 2026-10-28 rehearsal: premise's PnL ignored the rules' fee and mark, and disagreed in sign with the
    # backtest under them. Now it starts from the format's RESTING and ENGINE (arena.cli.format_config).
    import re

    from arena.formats import drill

    real = lambda out: {m[0]: float(m[1].replace(",", "")) for m in re.findall(r"\| (\w+) \| (-?[\d,]+) \|", out)}
    plain = run(capsys, monkeypatch, "premise", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "under the format's rules: resting True" in plain
    monkeypatch.setattr(drill, "ENGINE", {"fee": 50.0, "trade_matching": "none"}, raising=False)
    ruled = run(capsys, monkeypatch, "premise", "--data", drill_data, "--days", "all", "--format", "drill")
    assert "trade_matching none" in ruled and "fee 50.0" in ruled  # premise has one mode: the rules' own
    assert all(real(ruled)[p] < real(plain)[p] for p in real(plain) if real(plain)[p])

def test_the_premise_check_runs_a_bot_without_a_twin_on_the_python_engine(capsys, monkeypatch, drill_data, tmp_path):
    from arena import rust

    bot = tmp_path / "days_bot.py"  # the day's bot before its twin is recorded
    bot.write_text(Path("python/bots/drill/template.py").read_text())
    monkeypatch.setattr(rust, "require", lambda allow_stale=False: None)
    module = importlib.import_module("experiments.day.premise")
    module.main(["--data", drill_data, "--days", "all", "--format", "drill", "--bot", str(bot), "--engine", "rust"])
    out, err = capsys.readouterr()
    assert "| ALPHA |" in out and "no Rust twin yet" in err and "--engine rust" not in out


def test_calibrate_finds_the_engine_setting_a_portal_showed(capsys, monkeypatch, drill_data, tmp_path):
    # A "portal" made by our own engine under one setting (worse, resting, the touch mark): the calibration
    # ranks a setting that reproduces it first, at no error, and prints the ENGINE to paste.
    import json
    from dataclasses import replace

    from arena.cli import backtest, format_config
    from arena.engine import Mark, TradeMatching
    from arena.formats import FORMATS
    from experiments.day import calibrate

    fmt = FORMATS["drill"]
    days = fmt.load_days(fmt.resolve_data_dir(drill_data), ["all"])
    config = replace(format_config("drill"), trade_matching=TradeMatching.WORSE, mark=Mark.TOUCH)
    results = [backtest(d, [("you", "python/bots/drill/template.py", {}, False)], config, "python", False, None, "drill", rules=False)[0] for d in days]
    f = calibrate.figures(results, 0.01, None)
    portal = tmp_path / "metrics.json"
    portal.write_text(json.dumps({"metrics": {"score": f["score"][0], "fills": f["fills"][1], "tradedVolume": f["tradedVolume"][0],
                                              "cash": f["cash"][0], "absInventoryQ95": f["absInventoryQ95"][0]}}))
    out = run(capsys, monkeypatch, "calibrate", "--data", drill_data, "--days", "all", "--format", "drill", "--portal", str(portal), "--jobs", "2")
    best = out.split("Best: ")[1].split("\n")[0]
    assert best.startswith("worse, resting,") and "touch" in best and "(0.0% off)" in best
    assert 'ENGINE = {"trade_matching": "worse", "mark": "touch"}' in out and "RESTING = True" in out
