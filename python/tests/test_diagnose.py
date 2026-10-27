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


def _jumping(steps, reverse_share, seed=0, noise=(-1, 0, 1), start=10_000):
    """Wall mids that step by 100 (50 spreads of 2) every fifth tick, each step reversing the one before with this probability."""
    rng, walls, wall, step = random.Random(seed), [], start, 100
    for i in range(steps * 5):
        if i % 5 == 0 and i:
            step = -step if rng.random() < reverse_share else step
            wall += step
        walls.append(wall + rng.choice(noise))
    return walls


@pytest.mark.parametrize("share, snaps", [(0.95, True), (0.5, False)])
def test_jumps_that_snap_back_are_flagged(share, snaps):
    row = diagnose.diagnose([make_day(_jumping(200, share), name="r5d4")])["X"]
    assert row["snap_jumps"] == 199
    assert row["snap_back"] == pytest.approx(share, abs=0.06)
    assert ("jumps of 6+ spreads snap back (r5d4" in row["notes"]) is snaps
    assert ("the template's jump mode" in row["notes"]) is snaps
    assert row["jump_size"] == 100  # the median |move|: steps of 100 between noise of a tick
    assert ("usual size 100" in row["notes"] and "jump_min about 50" in row["notes"]) is snaps
    assert "mod 100" not in row["notes"]  # the noise spreads the wall mid over three values modulo 100


def test_the_snap_back_note_gives_the_jumps_size_and_grid():
    # Steps of exactly 100 between prices 30 above a multiple of 100, apart from one tick in five.
    row = diagnose.diagnose([make_day(_jumping(200, 0.95, noise=(0, 0, 0, 0, 1), start=10_030), name="r5d4")])["X"]
    assert row["jump_size"] == 100
    assert "reversed the one before; usual size 100, exactly that on " in row["notes"]
    assert "the wall mid at 30 mod 100 on 8" in row["notes"]  # about 80% of ticks
    assert "the template's jump mode with jump_min about 50" in row["notes"]
    size, exact, residue, share = diagnose._jump_grid({"d": ([6, 6, 6, 7], [3, 9, 15, 9, 16])}, ["d"], 1.0)
    assert (size, exact, residue) == (6, 0.75, 3) and share == pytest.approx(0.8)


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


def _day_with_an_open(wide: bool, name: str) -> Day:
    """1,000 ticks; with `wide`, the first 100 have a spread of 6 and a wall mid that moves 2 a tick,
    the rest a spread of 2 and a rise of 1 every fourth tick."""
    ticks, wall = [], 100
    for i in range(1000):
        opening = wide and i < 100
        wall += (2 if i % 2 else -2) if opening else (1 if i % 4 == 0 else 0)  # a trend, so the wall mid isn't "nearly fixed"
        half = 3 if opening else 1
        ticks.append(Tick(i * 100, {"X": Book(((wall - half, 20),), ((wall + half, 20),))}, {}, {}))
    return Day(name, ["X"], {"X": 10}, ticks)


def test_an_open_that_is_wider_and_faster_every_day_gets_a_note_and_a_profile():
    days = [_day_with_an_open(True, f"d{n}") for n in range(2)]
    row = diagnose.diagnose(days)["X"]
    assert row["open_spread"] == pytest.approx(3.0) and row["open_move"] == pytest.approx(8.0, rel=0.05)
    assert "the open (first tenth): spread 3.0x, volatility 8.0x the day's middle" in row["notes"]
    assert "the close" not in row["notes"]
    profile = diagnose.time_profile(days)["X"]
    assert len(profile["spread"]) == diagnose.PARTS and profile["spread"][0] == pytest.approx(6) and profile["spread"][5] == pytest.approx(2)
    assert "0-10%" in diagnose.format_profile({"X": profile})
    # One ordinary day among them: the days disagree, so no note, though the pooled ratio is still past the threshold.
    mixed = diagnose.diagnose([*days, _day_with_an_open(False, "d2")])["X"]
    assert mixed["open_spread"] > diagnose.PROFILE_RATIO and "the open" not in mixed["notes"]


def test_the_kalman_smoothing_of_a_random_walk_in_noise():
    # A local level stepping with variance q = 0.25, seen through noise of variance r = 4: the steady-state
    # Kalman gain is K = P / (P + r), P = (q + sqrt(q^2 + 4 q r)) / 2, and the template's smoothing 1 - K.
    rng, days = random.Random(3), []
    for n in range(3):
        level, walls = 1000.0, []
        for _ in range(5000):
            level += rng.gauss(0, 0.5)
            walls.append(level + rng.gauss(0, 2))
        days.append(make_day(walls, name=f"d{n}"))
    row = diagnose.diagnose(days)["X"]
    predicted = (0.25 + (0.25 ** 2 + 4 * 0.25 * 4) ** 0.5) / 2
    assert row["q_wall"] == pytest.approx(0.25, rel=0.15) and row["r_wall"] == pytest.approx(4, rel=0.1)
    assert row["smoothing_wall"] == pytest.approx(1 - predicted / (predicted + 4), abs=0.03)  # 0.78
    assert f"mid and wall mid both noisy (Kalman smoothing: wall mid {row['smoothing_wall']:.2f}" in row["notes"]
    # A random walk alone needs none; noise around a fixed value, all of it.
    walk = [1000.0]
    for _ in range(4999):
        walk.append(walk[-1] + rng.choice((-1, 1)))
    assert diagnose.diagnose([make_day(walk)])["X"]["smoothing_wall"] == pytest.approx(0, abs=0.05)
    assert diagnose.diagnose([make_day([1000 + rng.choice((-1, 1)) for _ in range(5000)])])["X"]["smoothing_wall"] > 0.95


def test_the_ema_error_is_least_at_the_kalman_smoothing_and_a_drift_lowers_it():
    q, r = 0.25, 4.0
    predicted = (q + (q * q + 4 * q * r) ** 0.5) / 2
    kalman = r / (predicted + r)
    grid = [k / 1000 for k in range(999)]
    assert min(grid, key=lambda s: diagnose._ema_error(s, q, r, 0.0)) == pytest.approx(kalman, abs=0.002)
    # With a drift the EMA lags it by drift * s / (1 - s), so the best s is lower.
    variogram = [[(lag * q + 2 * r) * 100, 100] for lag in diagnose.KALMAN_LAGS]
    assert diagnose._kalman(variogram)[2] == pytest.approx(kalman)
    drifting = diagnose._kalman(variogram, 0.1 ** 2)[2]
    assert drifting == pytest.approx(min(grid, key=lambda s: diagnose._ema_error(s, q, r, 0.01)), abs=0.002)
    assert drifting < kalman - 0.03


def test_gao_and_wangs_rates_at_a_one_tick_spread():
    # A one-tick spread around 100.5: buys at the ask on every other tick, the mid steps a tick every fifth tick.
    walls = [100.5 + (i // 5) for i in range(1000)]
    trades = {i: [walls[i] + 0.5] for i in range(0, 1000, 2) if i % 5 != 4}
    row = diagnose.diagnose([make_day(walls, half_spread=0.5, trades=trades)])["X"]
    assert row["one_tick_ticks"] == 999
    assert row["lambda"] == pytest.approx(199 / 999)  # the mid moves after every fifth tick
    assert row["lambda_buy"] == pytest.approx(400 / 999) and row["lambda_sell"] == 0  # hits after which it didn't
    assert "making at a one-tick spread pays on the ask only (Gao & Wang: uninformed hits λ+ 0.400, λ- 0.000 a tick against λ/2 0.100)" in row["notes"]
    # A mid that moves every tick: no side pays.
    flicker = diagnose.diagnose([make_day([100.5 + i % 2 for i in range(1000)], half_spread=0.5, trades=trades)])["X"]
    assert flicker["lambda"] == 1 and "pays on neither side" in flicker["notes"]
    # A small-tick product gets no such note, though the rates are in the CSV.
    assert "one-tick spread pays" not in diagnose.diagnose([make_day(walls, half_spread=2, trades=trades)])["X"]["notes"]


def _book_led_day(lead: bool, order: int, seed=0) -> Day:
    """Three levels a side, a tick apart, 10 lots each on one side and 30 on the other. With `lead`, the mid then
    moves a tick toward the heavier side; without, at random. A market buy of `order` lots every third tick."""
    rng, mid, ticks = random.Random(seed), 100.5, []
    for i in range(3000):
        heavy_bid = rng.random() < 0.5
        b, a = (30, 10) if heavy_bid else (10, 30)
        book = Book(tuple((mid - 0.5 - k, b) for k in range(3)), tuple((mid + 0.5 + k, a) for k in range(3)))
        prints = [MarketTrade("X", mid + 0.5, order)] if i % 3 == 0 else []
        ticks.append(Tick(i * 100, {"X": book}, {"X": prints} if prints else {}, {}))
        toward = 1 if heavy_bid else -1
        mid += toward if lead or rng.random() < 0.5 else -toward
    return Day("d", ["X"], {"X": 10}, ticks)


def test_tao_et_als_spoofability():
    # The next move follows the imbalance (µ+ 2 ticks a unit of 2ı - 1 = ±0.5) and buys of 2 lots never empty a level.
    row = diagnose.diagnose([_book_led_day(True, 2)])["X"]
    assert row["spoof_mu"] == pytest.approx(2, abs=0.01)
    assert row["spoof_q0"] == 0 and row["spoof_nu0"] == 0
    assert row["spoof_size"] == pytest.approx(2 / 60, abs=0.005)  # the ask holds 30 or 90 over its 3 levels
    assert row["spoof_score"] > 0 and "spoofable (Tao et al.'s score" in row["notes"]
    # A move the imbalance doesn't call, and buys of 35 that empty the best level whatever it holds.
    calm = diagnose.diagnose([_book_led_day(False, 35)])["X"]
    assert abs(calm["spoof_mu"]) < 0.1 and calm["spoof_q0"] == 1 and calm["spoof_score"] < 0
    assert "spoofable" not in calm["notes"]


def test_suggest_reads_the_notes_into_params():
    # Pegged, with uninformed trades around it: fair fixed at the peg, a tick of make_edge, the data's limit.
    trades = {i: [101 if i % 4 == 0 else 99] for i in range(0, 300, 2)}
    pegged, why = diagnose.suggest(diagnose.diagnose([make_day([100] * 300, trades=trades)])["X"])
    assert pegged["fair"] == "fixed" and pegged["fixed_fair"] == 100 and pegged["limit"] == 10
    assert pegged["make_edge"] == 2 and "pegged" in why  # a tick: the book's prices, 99 and 101, are 2 apart
    # A steady rise every day: hold the limit.
    rising = diagnose.diagnose([make_day([100 + i * 0.1 for i in range(1000)], name=f"d{n}") for n in range(2)])["X"]
    assert diagnose.suggest(rising)[0]["target"] == 10
    # Jumps of 100 that snap back: the jump mode at half the size, no target from anything else.
    jumping = diagnose.suggest(diagnose.diagnose([make_day(_jumping(200, 0.95), name="r5d4")])["X"])[0]
    assert jumping["jump_min"] == 50 and "target" not in jumping and "level" not in jumping
    # A random walk in noise: the wall mid at the Kalman smoothing.
    rng, walls, level = random.Random(3), [], 1000.0
    for _ in range(5000):
        level += rng.gauss(0, 0.5)
        walls.append(level + rng.gauss(0, 2))
    noisy = diagnose.diagnose([make_day(walls)])["X"]
    assert diagnose.suggest(noisy)[0]["smoothing"] == round(noisy["smoothing_wall"], 2)


def test_suggest_gives_prices_in_the_bots_ticks_where_the_format_has_them():
    trades = {i: [101 if i % 4 == 0 else 99] for i in range(0, 300, 2)}
    day = make_day([100] * 300, trades=trades)
    row = diagnose.diagnose([Day(day.name, day.products, day.limits, day.ticks, {"X": {"tick": 0.05, "unit": 0.01}})])["X"]
    params = diagnose.suggest(row)[0]
    assert params["fixed_fair"] == 20 and params["make_edge"] == 0.4  # 100 and 2 (the data's tick here) in its unit, the bot's tick being 5


def test_cli_suggest_prints_a_params_block(data_dir, capsys):
    import ast

    assert diagnose.main(["1", "--data", str(data_dir), "--suggest"]) == 0
    out = capsys.readouterr().out
    block = out[out.index("PARAMS = {"):]
    params = ast.literal_eval(block.split("=", 1)[1].strip())
    assert set(params) == {"KELP", "RAINFOREST_RESIN"} and all(p["fair"] in ("wall_mid", "fixed") for p in params.values())
