"""The probe bot answers the first-hour probes in our own engine, where the answers are known."""

import time
from pathlib import Path

import pytest

from arena import sim
from arena.engine import EngineConfig, run_day
from arena.formats import prosperity

PROBE = Path(__file__).parents[1] / "bots" / "probe.py"


def findings(capsys, monkeypatch, resting):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)  # probe 8 sleeps up to 500 ms
    day = sim.run(sim.preset_market(["KELP"], ticks=450), 5).day
    result = run_day(day, prosperity.load_bot(PROBE, {}, strict=False), EngineConfig(resting=resting, capture_output=False))
    out = capsys.readouterr().out.splitlines()
    lines = [line for line in out if line.startswith("PROBE ")]
    seen = [line for line in out if line.startswith("SEEN ")]
    return dict(line[len("PROBE ") :].split(": ", 1) for line in lines), result, seen


@pytest.mark.parametrize("resting", [False, True])
def test_the_probe_bot_answers_the_probes_in_both_engine_modes(capsys, monkeypatch, resting):
    found, result, seen = findings(capsys, monkeypatch, resting)
    assert len(found) == 14  # every probe reported once
    assert len(seen) == 449  # and one SEEN line a tick, except the tick that raised on purpose
    assert found["resting"].startswith("orders rest between ticks: " + ("yes" if resting else "no"))
    if resting:
        assert found["resting"].endswith("the book shows our own order: no")
    assert found["self_trade"].endswith(": no")
    assert "reported 1 call(s) later" in found["fill_timing"]
    assert "both rejected" in found["limits"]
    assert ("orders don't rest" in found["queue"]) is not resting  # resting: it waited in the queue
    assert "was called again" in found["exception"]
    assert found["state"] == "state kept between calls: traderData, module globals, instance attributes"
    assert len(result.errors) == 1 and "probe 6: an exception on purpose" in result.errors[0][1]
