"""The adversarial --vs rivals in python/bots/rivals/: what each one sends, and that they run cleanly."""

from pathlib import Path

import pytest

from arena.botfile import BotFile
from arena.engine import EngineConfig, run_market
from arena.formats import prosperity
from arena.model import Book, Day, Order, Tick

RIVALS = Path("python/bots/rivals")
BOOK = Book(((98, 5), (95, 25)), ((102, 5), (105, 25)))  # walls at 95 / 105: fair 100


def orders(name, book=BOOK, position=0, overrides=None):
    bot = prosperity.load_bot(RIVALS / f"{name}.py", overrides or {}, strict=True)
    return [o for o in bot.step(Tick(0, {"KELP": book}, {}, {}), {"KELP": position}, [], {}, []) if isinstance(o, Order)]


def test_the_trapper_baits_one_tick_inside_the_best():
    assert orders("trapper") == [Order("KELP", 99, 40)]


def test_the_spoofer_rests_a_large_order_behind_the_best():
    assert orders("spoofer") == [Order("KELP", 97, 40)]
    assert orders("spoofer", overrides={"OFFSET": 10}) == [Order("KELP", 88, 40)]


def test_the_sniper_takes_what_is_through_its_fair_and_rests_nothing():
    stale = Book(((101, 4), (95, 25)), ((103, 5), (105, 25)))  # someone's bid left above fair
    assert orders("sniper", stale) == [Order("KELP", 101, -4, ioc=True)]
    assert orders("sniper") == []


def test_the_taker_follows_the_last_move_takes_at_random_and_unwinds_past_hold():
    """RATE 1: it always follows the move; NOISE 1 with RATE 0: a side by the draw alone; past HOLD it only unwinds."""
    taker = prosperity.load_bot(RIVALS / "taker.py", {"RATE": 1.0, "NOISE": 0.0}, strict=True)
    up = Book(((99, 5), (95, 25)), ((103, 5), (105, 25)))  # the mid moves from 100 to 101
    taker.step(Tick(0, {"KELP": BOOK}, {}, {}), {"KELP": 0}, [], {}, [])
    assert [o for o in taker.step(Tick(100, {"KELP": up}, {}, {}), {"KELP": 0}, [], {}, []) if isinstance(o, Order)] == [Order("KELP", 103, 5, ioc=True)]
    assert orders("taker", position=30) == [Order("KELP", 98, -5, ioc=True)] and orders("taker", position=-31) == [Order("KELP", 102, 5, ioc=True)]
    assert orders("taker", overrides={"RATE": 0.0, "NOISE": 0.0}) == []
    sides = [orders("taker", overrides={"RATE": 0.0, "NOISE": 1.0, "SEED": seed})[0].quantity for seed in range(40)]
    assert {abs(q) for q in sides} == {5} and 10 < sum(q > 0 for q in sides) < 30  # a side by the draw, about half each way


def test_the_takers_draws_are_uniform_and_depend_on_each_input():
    module = BotFile(RIVALS / "taker.py", {"datamodel": prosperity.dm}).load()
    draws = [module.draw(100 * t, "KELP", 0) for t in range(4000)]
    assert all(0 <= d < 1 for d in draws) and abs(sum(draws) / len(draws) - 0.5) < 0.02
    assert module.draw(0, "KELP", 0) != module.draw(0, "KELP", 1) != module.draw(0, "SQUID_INK", 1)


@pytest.mark.parametrize("name", ["trapper", "spoofer", "sniper", "taker"])
def test_each_rival_runs_against_the_template_without_errors_or_breaches(name):
    ticks = [Tick(100 * k, {"KELP": Book(((98 + k % 3, 5), (95, 25)), ((102 + k % 3, 5), (105, 25)))}, {}, {}) for k in range(50)]
    day = Day("test", ["KELP"], {"KELP": 50}, ticks)
    bots = [("template", prosperity.load_bot(Path("python/bots/template.py"), {}, strict=True)), (name, prosperity.load_bot(RIVALS / f"{name}.py", {}, strict=True))]
    for result in run_market(day, bots, EngineConfig(resting=True)):
        assert not result.errors and not result.limit_breaches
