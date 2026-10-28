"""The probe bot answers the first-hour probes in our own engine, where the answers are known."""

import time
from pathlib import Path

import pytest

from arena import sim
from arena.engine import EngineConfig, run_day
from arena.formats import prosperity, qminers

PROBE = Path(__file__).parents[1] / "bots" / "probe.py"
# The day's copy (python/bots/qminers/probe.py) is the Prosperity probe until its ADAPTER is rewritten.
PROBES = [PROBE] + ([PROBE.parent / "qminers" / "probe.py"] if qminers.SKELETON else [])


def findings(capsys, monkeypatch, resting, path=PROBE):
    monkeypatch.setattr(time, "sleep", lambda seconds: None)  # probe 8 sleeps up to 500 ms
    day = sim.run(sim.preset_market(["KELP"], ticks=450), 5).day
    result = run_day(day, prosperity.load_bot(path, {}, strict=False), EngineConfig(resting=resting, capture_output=False))
    out = capsys.readouterr().out.splitlines()
    lines = [line for line in out if line.startswith("PROBE ")]
    seen = [line for line in out if line.startswith("SEEN ")]
    return dict(line[len("PROBE ") :].split(": ", 1) for line in lines), result, seen


@pytest.mark.parametrize("path", PROBES, ids=lambda p: p.parent.name)
@pytest.mark.parametrize("resting", [False, True])
def test_the_probe_bot_answers_the_probes_in_both_engine_modes(capsys, monkeypatch, resting, path):
    found, result, seen = findings(capsys, monkeypatch, resting, path)
    assert len(found) == 14  # every probe reported once
    assert len(seen) == 449  # and one SEEN line a tick, except the tick that raised on purpose
    assert found["resting"].startswith("orders rest between ticks: " + ("yes" if resting else "no"))
    if resting:
        assert found["resting"].endswith("the book shows our own order: no")
    assert found["self_trade"].endswith(": no")
    assert "reported 1 call(s) later" in found["fill_timing"]
    assert "both rejected" in found["limits"]
    if resting:  # it waited in the queue
        assert "orders don't rest" not in found["queue"]
    else:  # gone after a tick, or filled in its own tick by a market trade at its price
        assert "orders don't rest" in found["queue"] or "filled after 1 ticks" in found["queue"]
    assert "was called again" in found["exception"]
    assert found["state"] == "state kept between calls: traderData, module globals, instance attributes"
    assert len(result.errors) == 1 and "probe 6: an exception on purpose" in result.errors[0][1]


def test_the_risky_probes_run_last_and_the_mark_lot_is_held_to_the_end(capsys, monkeypatch):
    found, result, _ = findings(capsys, monkeypatch, False)
    assert list(found)[-3:] == ["imports", "exception", "time_limit"]  # each can end the run, so they come last
    assert list(found)[:3] == ["state", "resting", "self_trade"]
    assert result.positions["KELP"][-1] == 1  # the mark probe's lot, not flattened by the probes after it


def test_without_the_risky_block_the_bot_runs_the_other_probes(capsys, monkeypatch, tmp_path):
    """The safe build for a sandbox that scans the source: delete the RISKY PROBES block."""
    source = PROBE.read_text()
    start = source.index("# ------------------------------------------------------------------------------ RISKY PROBES")
    end = source.index("# ------------------------------------------------------------------------------ END RISKY PROBES")
    safe = source[:start] + source[source.index("\n", end) + 1 :]
    assert "importlib" not in safe and "time.sleep" not in safe and "raise RuntimeError" not in safe
    path = tmp_path / "probe_safe.py"
    path.write_text(safe)
    found, result, seen = findings(capsys, monkeypatch, True, path)
    assert len(found) == 11 and not {"imports", "exception", "time_limit"} & set(found)
    assert result.errors == [] and len(seen) == 450
    assert found["resting"].startswith("orders rest between ticks: yes")
