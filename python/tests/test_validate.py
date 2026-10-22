import textwrap
from pathlib import Path

import pytest

from arena import validate

TEMPLATE = Path(__file__).parents[1] / "bots" / "template.py"


@pytest.fixture
def check(tmp_path, data_dir, capsys):
    """Runs the validator on a bot body; returns (exit code, output)."""

    def run(body=None, *args):
        path = TEMPLATE
        if body is not None:
            path = tmp_path / "bot.py"
            path.write_text(textwrap.dedent(body))
        code = validate.main([str(path), "1", "--data", str(data_dir), *args])
        return code, capsys.readouterr().out

    return run


def test_template_passes(check):
    code, out = check()
    assert code == 0, out
    assert "FAIL" not in out and "WARN" not in out


def test_exceptions_fail(check):
    code, out = check(
        """
        class Trader:
            def run(self, state):
                raise ZeroDivisionError("oops")
        """
    )
    assert code == 1
    assert "FAIL  4 errors" in out and "ZeroDivisionError: oops" in out


def test_exceptions_from_the_lenient_path_fail(check):
    # Fine with STRICT set, but its own error handling breaks once STRICT is off.
    code, out = check(
        """
        STRICT = False

        class Trader:
            def run(self, state):
                if not STRICT:
                    raise KeyError("handler bug")
                return {}, 0, ""
        """
    )
    assert code == 1
    assert "exceptions escaped the bot with STRICT off" in out and "handler bug" in out


def test_limit_breaches_fail(check):
    code, out = check(
        """
        from datamodel import Order

        class Trader:
            def run(self, state):
                return {"KELP": [Order("KELP", 1, 51)]}, 0, ""
        """
    )
    assert code == 1
    assert "FAIL  4 times orders were cancelled for breaching a position limit" in out


def test_imports_and_environment_are_checked(check):
    code, out = check(
        """
        import os
        import numpy

        class Trader:
            def run(self, state):
                return {}, 0, os.environ.get("X", "")
        """
    )
    assert code == 1
    assert "FAIL  imports outside the standard library: numpy" in out
    assert "WARN  uses os.environ" in out

    code, out = check(None, "--allow", "numpy")
    assert code == 0


def test_state_outside_trader_data_warns(check):
    code, out = check(
        """
        from datamodel import Order

        class Trader:
            ticks = 0

            def run(self, state):
                Trader.ticks += 1
                orders = [Order("KELP", 2100, 1)] if Trader.ticks == 2 else []
                return {"KELP": orders}, 0, ""
        """
    )
    assert code == 0
    assert "WARN  fills change when the bot is reloaded every tick" in out


def test_syntax_errors_stop_before_replaying(check):
    code, out = check("class Trader(:\n")
    assert code == 1
    assert "syntax error" in out and "errors in" not in out


def _seeds_that_order_a_set_differently(names: set[str]) -> tuple[str, str]:
    import subprocess
    import sys

    first = {}
    for seed in map(str, range(40)):
        out = subprocess.run([sys.executable, "-c", f"print(next(iter({names!r})))"], capture_output=True, text=True,
                             env={"PYTHONHASHSEED": seed})
        first.setdefault(out.stdout.strip(), seed)
        if len(first) == 2:
            return tuple(first.values())
    raise AssertionError("no two seeds order the set differently")


def test_a_bot_that_depends_on_the_hash_seed_warns(check, monkeypatch):
    # Which product comes first out of a set of strings changes with PYTHONHASHSEED, so a rerun in
    # another process (the organisers') trades another product.
    monkeypatch.setattr(validate, "HASH_SEEDS", _seeds_that_order_a_set_differently({"KELP", "RAINFOREST_RESIN"}))
    code, out = check(
        """
        from datamodel import Order

        class Trader:
            def run(self, state):
                first = next(iter(set(state.order_depths)))
                asks = state.order_depths[first].sell_orders
                return {first: [Order(first, min(asks), 1)]} if asks else {}, 0, ""
        """
    )
    assert code == 0
    assert "WARN  fills differ between Python processes with other hash seeds" in out
    assert "PASS  same fills when r1d-1 is replayed again" in out  # one process can't see it
