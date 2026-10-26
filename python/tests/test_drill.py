"""The drill format: a second format, unlike Prosperity's, run through the same engine and template."""

import json
import textwrap
from pathlib import Path

import pytest

from arena import sim
from arena.botfile import BotFile
from arena.engine import EngineConfig, run_day
from arena.formats import drill, prosperity

ROOT = Path(__file__).parents[1]  # python/
RESTING = EngineConfig(resting=True)


def write_data(folder: Path, events: list[dict], instruments=None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    instruments = instruments or {"ALPHA": {"tick": "0.05", "max_position": 10}}
    (folder / "instruments.json").write_text(json.dumps({"price_unit": "0.01", "instruments": instruments}))
    (folder / "session_0.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    return folder


def level(t, side, px, qty, sym="ALPHA"):
    return {"t": t, "type": "level", "sym": sym, "side": side, "px": px, "qty": qty}


def step(t):
    return {"t": t, "type": "step"}


EVENTS = [
    level(0, "bid", "99.95", 5), level(0, "ask", "100.05", 5), step(0),
    level(250, "ask", "100.05", 0), level(250, "ask", "100.10", 4),
    {"t": 250, "type": "trade", "sym": "ALPHA", "px": "100.05", "qty": 2, "aggressor": "buy"}, step(250),
    step(500),
]


def test_the_loader_applies_level_changes_and_keeps_prices_in_cents(tmp_path):
    (day,) = drill.load_days(write_data(tmp_path, EVENTS), ["all"])
    assert [t.timestamp for t in day.ticks] == [0, 250, 500]
    assert day.ticks[0].books["ALPHA"].asks == ((10005, 5),)
    assert day.ticks[1].books["ALPHA"].asks == ((10010, 4),)  # the 100.05 level was removed
    assert day.ticks[2].books == day.ticks[1].books  # nothing changed: the book stands
    (trade,) = day.ticks[1].trades["ALPHA"]
    assert (trade.price, trade.quantity, trade.buyer) == (10005, 2, drill.TAKER)
    assert day.limits == {"ALPHA": 10} and day.info == {"ALPHA": {"tick": 0.05, "unit": 0.01}}


@pytest.mark.parametrize(
    "event, message",
    [(level(0, "bid", "99.97", 5), "off the 0.05 tick grid"), (level(0, "bid", "99.95", 5, sym="OMEGA"), "not in instruments"),
     ({"t": 0, "type": "quote"}, "unknown event type")],
)
def test_the_loader_rejects_bad_events_with_their_line(tmp_path, event, message):
    with pytest.raises(ValueError, match=message):
        drill.load_days(write_data(tmp_path, [event, step(0)]), ["0"])


def test_session_specs(tmp_path):
    data = write_data(tmp_path, EVENTS)
    assert [d.name for d in drill.load_days(data, ["0..3"])] == ["s0"]
    with pytest.raises(ValueError, match="bad session"):
        drill.load_days(data, ["1-0"])


BOT = """
COUNT = 0

class Bot:
    def __init__(self):
        self.calls = 0
        self.ids, self.seen = [], []

    def on_tick(self, api):
        global COUNT
        COUNT += 1
        self.calls += 1
        self.seen.append((api.time, api.orders("ALPHA"), api.fills()))
        if self.calls == 1:
            self.ids.append(api.buy("ALPHA", 100.00, 3))  # rests: the best ask is 100.05
            self.ids.append(api.buy("ALPHA", 100.05, 1, ioc=True))  # takes
        elif self.calls == 2:
            api.cancel(self.ids[0])
        if KEEP_IN_MODULE and COUNT == 3:
            api.sell("ALPHA", 99.95, 1)
"""


def load(tmp_path, keep_in_module=False, **kwargs):
    path = tmp_path / "bot.py"
    path.write_text(textwrap.dedent(BOT).replace("KEEP_IN_MODULE", str(keep_in_module)))
    return drill.load_bot(path, {}, strict=True, **kwargs)


def test_the_bot_api_places_takes_and_cancels_through_opaque_ids(tmp_path):
    day = drill.load_days(write_data(tmp_path / "data", EVENTS), ["0"])[0]
    bot = load(tmp_path)
    result = run_day(day, bot, RESTING)
    assert not result.errors
    first, second = bot._bot.ids
    assert len(first) == 10 and first != second
    assert [(f.price, f.quantity, f.tag) for f in result.fills] == [(10005, 1, second)]
    _, orders, fills = bot._bot.seen[1]
    assert [(o.order_id, o.price, o.size) for o in orders] == [(first, 100.0, 3)]  # in decimals, with our id
    assert [(f.order_id, f.price, f.size) for f in fills] == [(second, 100.05, 1)]
    assert result.cancels and bot._bot.seen[2][1] == []  # the cancel went through


def test_off_grid_prices_and_unknown_cancels_are_bot_errors(tmp_path):
    day = drill.load_days(write_data(tmp_path / "data", EVENTS), ["0"])[0]
    (tmp_path / "bad.py").write_text("class Bot:\n    def on_tick(self, api):\n        api.buy('ALPHA', 100.01, 1)\n")
    result = run_day(day, drill.load_bot(tmp_path / "bad.py", {}, strict=True), RESTING)
    assert "off its 0.05 tick grid" in result.errors[0][1]
    (tmp_path / "ghost.py").write_text("class Bot:\n    def on_tick(self, api):\n        api.cancel('nope')\n")
    result = run_day(day, drill.load_bot(tmp_path / "ghost.py", {}, strict=True), RESTING)
    assert "no such open order" in result.errors[0][1]


def test_a_fresh_module_every_tick_keeps_the_instance_but_not_module_state(tmp_path):
    day = drill.load_days(write_data(tmp_path / "data", EVENTS), ["0"])[0]
    run = lambda keep, fresh: run_day(day, load(tmp_path, keep, fresh_each_tick=fresh), RESTING).fills
    assert run(False, False) == run(False, True)  # state on self survives the reload
    assert run(True, False) != run(True, True)  # a module global doesn't, which the validator flags


def test_check_source():
    import ast

    assert drill.check_source(ast.parse("class Bot:\n    def on_tick(self, api): pass")) == []
    assert drill.check_source(ast.parse("class Trader:\n    def run(self, state): pass")) == ["no top-level class Bot"]


def _sections(text: str) -> tuple[str, str]:
    start = text.index("DEFAULTS = {")
    defaults = text[start : text.index("\n}\n", start) + 3]
    core = text[text.index("# " + "-" * 78 + " STRATEGY") : text.index("# " + "-" * 78 + " ADAPTER")]
    return defaults, core


@pytest.mark.parametrize("path", sorted((ROOT / "bots").glob("*/template.py")), ids=lambda p: p.parent.name)
def test_every_formats_template_keeps_the_templates_strategy_and_execution_word_for_word(path):
    # The drill's, and on the day the Arena's (python/bots/qminers/template.py): only imports, PARAMS and ADAPTER differ.
    template = (ROOT / "bots" / "template.py").read_text()
    assert _sections(path.read_text()) == _sections(template), "uv run python -m experiments.format_drill --sync"


def test_the_drill_template_trades_like_the_template_on_the_same_days(tmp_path):
    # One simulated day in the Prosperity layout, converted: ALPHA is KELP at 0.05 a tick (five
    # cents), BETA is RAINFOREST_RESIN at 0.01, so the PnL must match in cents.
    day = sim.run(sim.preset_market(ticks=800), 7).day
    sim.write_day(sim.run(sim.preset_market(ticks=800), 7), tmp_path / "sim", 1, 0)
    drill.convert(tmp_path / "sim", 1, tmp_path / "drill")
    same = {
        "PARAMS.KELP": {"limit": 50, "fair": "wall_mid", "make_edge": 1},
        "PARAMS.RAINFOREST_RESIN": {"limit": 50, "fair": "fixed", "fixed_fair": 10_000},
        "PARAMS.SQUID_INK": {"limit": 50, "fair": "wall_mid", "make_size": 0},
    }
    prosperity_day = prosperity.load_days(tmp_path / "sim", ["1"])[0]
    drill_day = drill.load_days(tmp_path / "drill", ["0"])[0]
    assert len(prosperity_day.ticks) == len(drill_day.ticks) == len(day.ticks)
    template = prosperity.load_bot(ROOT / "bots" / "template.py", same, strict=True)
    drill_bot = drill.load_bot(ROOT / "bots" / "drill" / "template.py", {}, strict=True)
    a, b = run_day(prosperity_day, template, RESTING), run_day(drill_day, drill_bot, RESTING)
    assert not a.errors and not b.errors
    assert a.pnl["KELP"][-1] != 0
    assert b.pnl["ALPHA"][-1] == pytest.approx(5 * a.pnl["KELP"][-1])
    assert b.pnl["BETA"][-1] == pytest.approx(a.pnl["RAINFOREST_RESIN"][-1])
    assert len(a.fills) == len(b.fills)


def test_the_grids_smoke_test_keeps_the_days_tick_sizes(tmp_path, capsys):
    """A grid's 200-tick smoke test used to rebuild the day without Day.info, so a format's per-product
    ticks fell back to 0.01 there (found in the 2026-10-26 dry run)."""
    from arena import grid

    data = write_data(tmp_path / "data", EVENTS)
    bot = tmp_path / "bot.py"
    bot.write_text(textwrap.dedent("""
        SIZE = 1

        class Bot:
            def on_tick(self, api):
                assert api.tick_size("ALPHA") == 0.05, api.tick_size("ALPHA")
    """))
    code = grid.main([str(bot), "all", "--format", "drill", "--data", str(data), "--grid", "SIZE=1,2", "--jobs", "1"])
    assert code == 0, capsys.readouterr().out
