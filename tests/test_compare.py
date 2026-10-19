import csv
import textwrap

import pytest

from arena import compare

# Buys `size` KELP at the 2032 ask on the first tick of each day; KELP is marked at 2030,
# so each day loses 2 per unit and the total over the two fixture days is -4 * size.
BOT = """
from datamodel import Order

PARAMS = {"size": 1}

class Trader:
    def run(self, state):
        if state.timestamp == 0:
            return {"KELP": [Order("KELP", 2032, PARAMS["size"])]}, 0, ""
        return {}, 0, ""
"""


@pytest.fixture
def bots(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    paths = {"base": tmp_path / "a" / "bot.py", "same_stem": tmp_path / "b" / "bot.py", "broken": tmp_path / "broken.py"}
    paths["base"].write_text(textwrap.dedent(BOT))
    paths["same_stem"].write_text(textwrap.dedent(BOT).replace('"size": 1', '"size": 3'))
    paths["broken"].write_text("class Trader(:\n")
    return paths


def test_candidates_parse_files_and_variants(bots):
    c = compare.parse_candidate(f"{bots['base']}@PARAMS.size=2@PARAMS.extra='x'")
    assert c.path == bots["base"] and c.overrides == {"PARAMS.size": 2, "PARAMS.extra": "x"}
    assert c.label == "bot size=2 extra=x"
    with pytest.raises(ValueError, match="no bot file"):
        compare.parse_candidate("missing.py")


def test_labels_are_made_unique(bots):
    a, b = compare.parse_candidate(str(bots["base"])), compare.parse_candidate(str(bots["same_stem"]))
    assert [c.label for c in compare.labelled([a, b])] == ["a/bot", "b/bot"]
    assert [c.label for c in compare.labelled([a, a])] == ["a/bot", "a/bot#2"]


def run_main(capsys, *args):
    code = compare.main([str(a) for a in args])
    return code, capsys.readouterr().out


def test_compare_ranks_bots_and_reports_a_broken_one(capsys, bots, data_dir, tmp_path):
    out = tmp_path / "compare.csv"
    code, text = run_main(capsys, bots["base"], "1", "--data", data_dir, "--modes", "all,worse", "--jobs", "1", "--out", out,
                          "--bot", f"{bots['base']}@PARAMS.size=2", bots["broken"])
    assert code == 0
    assert "2 bots and the baseline × 2 days × 2 modes (12 backtests)" in text
    lines = text.splitlines()
    first = next(line for line in lines if line.lstrip().startswith("1 "))
    assert "bot" in first and "-4" in first and "(base)" in first  # the baseline loses least
    assert any("bot size=2" in line and "-8" in line for line in lines)
    assert any(line.startswith("! broken:") for line in lines)  # its load error is shown
    assert "pick:" in text or "SPA, StepM: skipped" in text
    with out.open() as file:
        rows = list(csv.DictReader(file))
    assert [r["bot"] for r in rows] == ["bot", "bot size=2", "broken"]
    assert float(rows[1]["pnl_all"]) == -8 and rows[1]["overrides"] == "PARAMS.size=2"
    assert int(rows[2]["errors"]) > 0


def test_compare_exits_1_when_every_bot_fails(capsys, bots, data_dir):
    code, _ = run_main(capsys, bots["base"], "1", "--data", data_dir, "--jobs", "1", "--bot", bots["broken"])
    assert code == 1


def test_compare_runs_in_parallel_with_the_same_numbers(capsys, bots, data_dir):
    args = [bots["base"], "1", "--data", data_dir, "--bot", f"{bots['base']}@PARAMS.size=2"]
    _, serial = run_main(capsys, *args, "--jobs", "1")
    _, parallel = run_main(capsys, *args, "--jobs", "2")
    strip = lambda text: [line for line in text.splitlines() if "done in" not in line and "workers" not in line]
    assert strip(serial) == strip(parallel)
