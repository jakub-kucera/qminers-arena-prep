"""The make_edge learner in python/bots/research/online_edge.py, and python/experiments/online_edge.py's scoring."""

from dataclasses import replace
from pathlib import Path

import pytest

from arena import sim
from arena.botfile import BotFile
from arena.engine import EngineConfig, run_market
from arena.formats import prosperity
from arena.formats import prosperity_datamodel as dm
from experiments import online_edge as experiment

BOTS = Path(__file__).parents[1] / "bots"
RESEARCH = BOTS / "research" / "online_edge.py"


@pytest.fixture
def bot():
    return BotFile(RESEARCH, {"datamodel": dm}, strict=True).load()


def learn_params(bot, **overrides):
    return {**bot.DEFAULTS, "limit": 10, "make_edge": 1.0, "learn_edge": True, "learn_window": 1, "learn_horizon": 1,
            "learn_step": 0.5, **overrides}


def tick(bot, p, memory, fills, fair=100.0):
    """One tick of the learner: the edge it quotes, then its quotes recorded at fair -/+ 1 - side."""
    edge = bot.learn_edge(fair, fills, p, memory)
    plan = bot.Plan(0, p["limit"])
    side = memory["learn"]["side"]
    plan.buy(int(fair) - 1 - side, 5, quote=True)
    plan.sell(int(fair) + 1 + side, 5, quote=True)
    bot.learn_record(plan, memory)
    return edge


def test_off_by_default_it_trades_as_the_template():
    day = sim.run(replace(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), ticks=600), 5).day
    fills = []
    for path in (BOTS / "template.py", RESEARCH):
        result = run_market(day, [("me", prosperity.load_bot(path, {}, True))], EngineConfig())[0]
        fills.append([(f.timestamp, f.product, f.price, f.quantity) for f in result.fills])
    assert fills[0] and fills[0] == fills[1]


def test_probe_windows_pair_the_centre_with_each_side_in_turn(bot):
    sides = [bot._learn_side(k, "probe") for k in range(8)]
    assert sides == [1, 0, -1, 0, 0, 1, 0, -1]
    assert [bot._learn_side(k, "symmetric") for k in range(4)] == [1, -1, -1, 1]


def test_the_edge_steps_toward_a_probe_that_scores_more_and_stays_otherwise(bot):
    p = learn_params(bot)
    memory = {}
    assert tick(bot, p, memory, []) == 1.5  # window 0 probes +0.5
    assert tick(bot, p, memory, [(98, 5)]) == 1.0  # its bid filled; window 1 is the centre
    tick(bot, p, memory, [])  # the fill matures (+10 for the probe), and the pair ends
    assert memory["learn"]["e"] == 1.5

    memory = {}
    tick(bot, p, memory, [])
    tick(bot, p, memory, [(98, 5)])  # the probe's bid fills at 98, marked to a fair of 96: -10
    tick(bot, p, memory, [], fair=96.0)
    assert memory["learn"]["e"] == 1.0


def test_takes_are_not_scored_and_the_edge_stays_in_bounds(bot):
    p = learn_params(bot, learn_min=0.5, learn_max=1.5, learn_design="symmetric")
    memory = {}
    tick(bot, p, memory, [])
    tick(bot, p, memory, [(95, 5)])  # no quote at 95: a take, not scored
    tick(bot, p, memory, [])
    assert memory["learn"]["e"] == 1.0  # a tie: no move
    for _ in range(20):  # the + side's ask always fills, and the price falls away from it
        _, ask, side = memory["learn"]["q"][-1]
        tick(bot, p, memory, [(ask, -5)] if side > 0 else [], fair=95.0)
    assert memory["learn"]["e"] == 1.5


def test_the_settings_score_by_their_worst_regret():
    table = {  # one product: model -> label -> (PnL, ends, path)
        "all": {"fixed 1": (10, [], []), "fixed 2": (20, [], []), "learn 1": (18, [], [])},
        "worse": {"fixed 1": (10, [], []), "fixed 2": (0, [], []), "learn 1": (7, [], [])},
    }
    assert experiment.regrets(table)["learn 1"] == {"all": 2, "worse": 3}
    assert experiment.regrets(table)["fixed 2"] == {"all": 0, "worse": 10}
    assert experiment.score_setting({"P": table}) == (3, 2.5)
