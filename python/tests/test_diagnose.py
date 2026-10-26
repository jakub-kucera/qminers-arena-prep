import random

import pytest

from arena import diagnose
from arena.diagnose import LAG
from arena.model import Book, Day, MarketTrade, Tick


def make_day(walls, half_spread=1, trades=None, touch=None, product="X", name="d"):
    """A day whose wall (volume 20) sits half_spread around each wall mid.

    `touch` optionally gives per tick a (bid, ask) of volume 1 in front of the walls.
    `trades` maps a tick index to a list of trade prices.
    """
    ticks = []
    for i, wall in enumerate(walls):
        bids, asks = [(wall - half_spread, 20)], [(wall + half_spread, 20)]
        if touch and touch[i]:
            bids.insert(0, (touch[i][0], 1))
            asks.insert(0, (touch[i][1], 1))
        prints = [MarketTrade(product, p, 1) for p in (trades or {}).get(i, [])]
        ticks.append(Tick(i * 100, {product: Book(tuple(bids), tuple(asks))}, {product: prints} if prints else {}, {}))
    return Day(name, [product], {product: 10}, ticks)


def test_alternating_uninformed_trades_give_the_textbook_margins():
    # Buys at the ask and sells at the bid, in turn, around a wall mid that never moves.
    trades = {i: [101 if i % 4 == 0 else 99] for i in range(0, 300, 2)}
    row = diagnose.diagnose([make_day([100] * 300, trades=trades)])["X"]
    assert row["trades"] == 150
    assert row["buy_share"] == pytest.approx(0.5)
    assert row["c1"] == pytest.approx(-1)
    assert row["edge_wall"] == pytest.approx(-1)
    assert row["r1_wall"] == row[f"r{LAG}_wall"] == 0
    assert row["slow_wall"] == pytest.approx(1)  # half the spread
    assert row["fast_wall"] == pytest.approx(2)  # -edge * (1 - C(1)): never caught on one side
    assert "wall mid nearly fixed at 100" in row["notes"]


def test_trades_inside_the_spread_are_left_out():
    row = diagnose.diagnose([make_day([100] * 10, trades={1: [100, 101], 2: [99.5]})])["X"]
    assert row["trades"] == 1
    assert row["inside_share"] == pytest.approx(2 / 3)


def test_spread_is_counted_in_ticks():
    # Prices on a half-unit grid: a one-unit spread is two ticks.
    row = diagnose.diagnose([make_day([100, 100.5] * 20, half_spread=0.5, touch=[(99.5, 100.5), None] * 20)])["X"]
    assert row["tick"] == 0.5
    assert row["spread_ticks_median"] == 2
    assert row["at_one_tick"] == 0


def test_a_one_tick_spread_is_large_tick():
    row = diagnose.diagnose([make_day([100.5] * 10, half_spread=0.5)])["X"]
    assert row["at_one_tick"] == 1
    assert "large-tick" in row["notes"]


def test_an_empty_side_is_counted():
    day = make_day([100] * 4)
    ticks = day.ticks[:2] + [Tick(200, {"X": Book((), ((101, 5),))}, {}, {}), Tick(300, {"X": Book()}, {}, {})]
    row = diagnose.diagnose([Day("d", ["X"], {"X": 10}, ticks)])["X"]
    assert row["one_side_empty"] == pytest.approx(0.25)  # an empty book has no side to count
    assert row["two_sided"] == pytest.approx(0.5)


def test_a_market_maker_smaller_than_wall_size_is_flagged():
    big = diagnose.diagnose([make_day([100] * 50)])["X"]  # walls of 20
    assert big["wall_size"] == 20 and big["wall_seen"] == 1.0 and "wall_size" not in big["notes"]
    day = make_day([100] * 50)
    small = Day(day.name, day.products, day.limits, [
        Tick(t.timestamp, {"X": Book(((99, 10),), ((101, 10),))}, {}, {}) for t in day.ticks
    ])
    row = diagnose.diagnose([small])["X"]
    assert row["wall_size"] == 10 and row["wall_seen"] == 0.0
    assert "a level of 15+ on only 0% of sides (largest level median 10)" in row["notes"]


def test_a_wall_mid_that_jumps_past_half_the_spread_is_flagged():
    jumpy = diagnose.diagnose([make_day([100, 104] * 20)])["X"]  # moves of 4 against a half-spread of 1
    assert jumpy["jump_share"] == 1
    assert "if orders rest, take only" in jumpy["notes"]
    calm = diagnose.diagnose([make_day([100, 101] * 20)])["X"]  # one tick: not a jump
    assert calm["jump_share"] == 0
    assert "jumps" not in calm["notes"]


def _jumping(steps, reverse_share, seed=0):
    """Wall mids that step by 100 (50 spreads of 2) every fifth tick, each step reversing the one before with this probability."""
    rng, walls, wall, step = random.Random(seed), [], 10_000, 100
    for i in range(steps * 5):
        if i % 5 == 0 and i:
            step = -step if rng.random() < reverse_share else step
            wall += step
        walls.append(wall + rng.choice((-1, 0, 1)))
    return walls


@pytest.mark.parametrize("share, snaps", [(0.95, True), (0.5, False)])
def test_jumps_that_snap_back_are_flagged(share, snaps):
    row = diagnose.diagnose([make_day(_jumping(200, share), name="r5d4")])["X"]
    assert row["snap_jumps"] == 199
    assert row["snap_back"] == pytest.approx(share, abs=0.06)
    assert ("jumps of 6+ spreads snap back (r5d4" in row["notes"]) is snaps
    assert ("the template's jump mode" in row["notes"]) is snaps


def test_too_few_jumps_get_no_snap_back_note():
    row = diagnose.diagnose([make_day(_jumping(diagnose.MIN_JUMPS - 1, 1.0))])["X"]
    assert row["snap_back"] is None and "snap back" not in row["notes"]
    assert diagnose._snap_backs([0, 12, 0, 12, 13], 2) == (3, 2, 2)  # moves of 12 or more: +12, -12, +12


def test_the_simulators_jumping_preset_snaps_back_and_kelp_doesnt():
    from arena import sim

    rows = diagnose.diagnose([sim.run(sim.preset_market(["ROBOT_DISHES", "KELP"], ticks=3000), 0).day])
    assert "snap back" in rows["ROBOT_DISHES"]["notes"] and "snap back" not in rows["KELP"]["notes"]


def test_a_bouncing_mid_mean_reverts_and_the_wall_mid_filters_it():
    # The touch flips between just above and just below a wall mid that walks slowly.
    walls = [100 + (i // 25) for i in range(400)]
    touch = [(w - 1, w + 2) if i % 2 else (w - 2, w + 1) for i, w in enumerate(walls)]
    row = diagnose.diagnose([make_day(walls, half_spread=3, touch=touch)])["X"]
    assert row["mid_lag1_autocorr"] < -0.4
    assert row["mid_signature"] > 2 * row["wall_signature"]
    assert "mid mean-reverts at one tick" in row["notes"]
    assert "wall mid filters the mid's noise" in row["notes"]


def test_a_steady_rise_is_a_drift_every_day():
    days = [make_day([100 + i * 0.1 for i in range(1000)], half_spread=1, name=f"d{n}") for n in range(2)]
    row = diagnose.diagnose(days)["X"]
    assert row["drift_per_day"] == pytest.approx(99.9)
    assert "drifts up every day" in row["notes"]


@pytest.mark.parametrize("pull, reverts", [(0.005, True), (0.0, False)])
def test_slow_reversion_to_a_level(pull, reverts):
    # Unit steps, pulled back toward 100 by `pull` of the gap each tick (an Ornstein-Uhlenbeck walk).
    rng = random.Random(1)  # without the pull, this seed gives 1.16, near the median of a random walk (1.11)
    days = []
    for n in range(3):
        level, walls = 100.0, []
        for _ in range(10_000):
            level += rng.choice((-1, 1)) - pull * (level - 100)
            walls.append(round(level))
        days.append(make_day(walls, name=f"d{n}"))
    row = diagnose.diagnose(days)["X"]
    assert (row["wall_reversion"] >= diagnose.SLOW_REVERSION) is reverts
    assert ("reverts to a level" in row["notes"]) is reverts


def test_informed_buys_move_the_wall_mid():
    # Every buy is followed by a one-unit rise that stays: R(LAG) is the whole move.
    walls, trades, level = [], {}, 100
    for i in range(600):
        if i % 10 == 0:
            trades[i] = [level + 1]
        if i % 10 == 1:
            level += 1
        walls.append(level)
    row = diagnose.diagnose([make_day(walls, trades=trades)])["X"]
    assert row["c1"] == 1
    assert row[f"r{LAG}_wall"] == pytest.approx(5)
    assert row["slow_wall"] == pytest.approx(-4)
    assert "trades move the wall mid" in row["notes"]
    assert "trades nearly all buys" in row["notes"]
    assert "a maker's position only grows" in row["notes"]


def test_few_trades_get_no_trade_notes():
    row = diagnose.diagnose([make_day([100] * 10, trades={1: [101]})])["X"]
    assert "too few for trade statistics" in row["notes"]
    assert "market making" not in row["notes"]


def test_cli_prints_the_table_and_writes_the_csv(data_dir, tmp_path, capsys):
    out_csv = tmp_path / "diag.csv"
    assert diagnose.main(["1", "--data", str(data_dir), "--csv", str(out_csv)]) == 0
    out = capsys.readouterr().out
    assert "KELP" in out and "RAINFOREST_RESIN" in out and "slow" in out
    header = out_csv.read_text().splitlines()[0].split(",")
    assert header[:3] == ["product", "ticks", "two_sided"]
    assert "slow_mid" in header and "slow_wall" in header


def test_cli_rejects_a_bad_day(data_dir):
    with pytest.raises(SystemExit):
        diagnose.main(["x", "--data", str(data_dir)])
