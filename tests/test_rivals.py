"""The adversarial --vs rivals in bots/rivals/: what each one sends, and that they run cleanly."""

from pathlib import Path

import pytest

from arena.engine import EngineConfig, run_market
from arena.formats import prosperity
from arena.model import Book, Day, Order, Tick

RIVALS = Path("bots/rivals")
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


@pytest.mark.parametrize("name", ["trapper", "spoofer", "sniper"])
def test_each_rival_runs_against_the_template_without_errors_or_breaches(name):
    ticks = [Tick(100 * k, {"KELP": Book(((98 + k % 3, 5), (95, 25)), ((102 + k % 3, 5), (105, 25)))}, {}, {}) for k in range(50)]
    day = Day("test", ["KELP"], {"KELP": 50}, ticks)
    bots = [("template", prosperity.load_bot(Path("bots/template.py"), {}, strict=True)), (name, prosperity.load_bot(RIVALS / f"{name}.py", {}, strict=True))]
    for result in run_market(day, bots, EngineConfig(resting=True)):
        assert not result.errors and not result.limit_breaches
