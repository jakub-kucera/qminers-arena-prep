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
