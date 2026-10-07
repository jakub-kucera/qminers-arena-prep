"""Regression test pinned to jmerle's prosperity3bt 0.12.0.

The expected fill counts and PnL are what prosperity3bt reported for fixtures/parity_bot.py,
and the engine matched every fill. If this fails after an engine change, the change broke
Prosperity's matching rules. Needs the Prosperity 3 data from references/clone.sh.
"""

from pathlib import Path

import pytest

from arena.engine import EngineConfig, TradeMatching, run_day
from arena.formats import prosperity

BOT = Path(__file__).parent / "fixtures" / "parity_bot.py"
DATA = prosperity.DATA_DIRS["p3"]

EXPECTED = [
    # round, day, matching, fills, total pnl (jmerle's convention, see below)
    (1, 0, "all", 8080, 27_664.5),
    (1, 0, "worse", 4527, 16_750.5),
    (1, 0, "none", 2638, 9_317.0),
    (5, 2, "all", 10946, 60_434.0),
    (5, 2, "worse", 5872, 24_667.5),
    (5, 2, "none", 2806, 17_885.5),
]


@pytest.mark.skipif(not DATA.is_dir(), reason="Prosperity 3 data missing: run references/clone.sh")
@pytest.mark.parametrize("round_num, day_num, matching, fills, pnl", EXPECTED)
def test_matches_prosperity3bt(round_num, day_num, matching, fills, pnl):
    day = prosperity.load_day(DATA, round_num, day_num)
    bot = prosperity.load_bot(BOT, {}, strict=True)
    result = run_day(day, bot, EngineConfig(trade_matching=TradeMatching(matching)))

    assert result.errors == []
    assert len(result.fills) == fills
    # prosperity3bt's final PnL is taken before the last tick's fills, at the last tick's mark.
    total = sum(
        result.pnl[p][-2] + result.positions[p][-2] * (result.marks[p][-1] - result.marks[p][-2])
        for p in result.products
    )
    assert total == pytest.approx(pnl)
