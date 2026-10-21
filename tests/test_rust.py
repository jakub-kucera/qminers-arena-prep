"""The Rust port (rust/) against our engine and bots: every recorded field in every configuration,
for each Python file with a Rust twin (rust/twins.json), plus the crate's own unit tests. Skipped
without cargo, except the checks that need no build: that each twin's Python file is the one its
port was last checked against, and that rust/README.md's table lists it.

A change to a twin's Python file (arena/engine.py, bots/template.py, ...) goes into its Rust file
too; then `uv run python -m experiments.rust_bench --parity-only --record` checks the pair and
records the new hash."""

import json
import re
import shutil
import subprocess
from dataclasses import replace

import pytest

from arena import rust, sim

needs_cargo = pytest.mark.skipif(shutil.which("cargo") is None, reason="needs cargo (rust/)")
needs_references = pytest.mark.skipif(not (rust.ROOT / "references" / "prosperity4-backtester").exists(), reason="needs references/ (clone.sh)")


@pytest.fixture(scope="module")
def bench():
    from experiments import rust_bench

    rust_bench.build()
    return rust_bench


def test_every_twin_was_checked_since_its_python_file_changed():
    stale = rust.stale_twins()
    assert not stale, (f"{', '.join(stale)} changed since its Rust twin was checked: port the change to the file rust/twins.json names, then "
                       "run `uv run python -m experiments.rust_bench --parity-only --record`")


def test_the_readme_table_lists_every_twin():
    readme = (rust.RUST / "README.md").read_text()
    for path, twin in rust.twins().items():
        assert f"`{path}`" in readme and f"`{twin['rust'].removeprefix('rust/')}`" in readme, path


@needs_cargo
def test_the_crates_unit_tests_pass(bench):
    out = subprocess.run(["cargo", "test", "--release", "--quiet", "--manifest-path", str(bench.RUST / "Cargo.toml")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@needs_cargo
def test_mm_records_what_our_engine_records_in_every_configuration(bench, tmp_path):
    day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), 5).day
    day = replace(day, ticks=day.ticks[:2000])
    results = bench.parity(day, tmp_path)
    assert [name for name, _, _ in results] == [name for name, _, _ in bench.CONFIGS]
    assert {name: found[:1] for name, _, found in results} == {name: [] for name, _, _ in results}
    fills = {name: counts for name, counts, _ in results}
    assert all(counts[0] > 0 for counts in fills.values())
    assert fills["two bots, resting"][1] > 0 and fills["two bots, resting"][2] > 0  # crosses and races happen


@needs_cargo
def test_the_template_trades_the_same_in_every_part_of_its_strategy(bench, tmp_path):
    results = bench.parity(bench.sim_day(1500), tmp_path, bench.template_cases())
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, _, _ in results}
    # Each variant trades differently from the committed settings, so the part it turns on ran.
    default = {label.removesuffix(", default"): counts for label, counts, _ in results if label.endswith(", default")}
    assert set(default) == {label for label, _ in bench.VARIANTS}
    committed = default.pop("as committed")
    assert [label for label, counts in default.items() if (counts[0], counts[4]) == (committed[0], committed[4])] == []


@needs_cargo
def test_the_rivals_trade_the_same(bench, tmp_path):
    results = bench.parity(bench.sim_day(1500), tmp_path, bench.rival_cases())
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, _, _ in results}
    counts = {label: c for label, c, _ in results}
    assert counts["template against the trapper, resting"][1] > 0  # the bait gets crossed
    assert all(c[0] > 0 for c in counts.values())


def test_every_zoo_bot_has_a_rust_twin():
    zoo = rust.ROOT / "bots" / "zoo"
    files = {p.relative_to(rust.ROOT).as_posix() for p in zoo.rglob("*.py") if p.name not in {"bundle.py", "local.py"}}
    assert files - set(rust.twins()) == set()


def test_a_zoo_twin_refuses_settings():
    with pytest.raises(ValueError, match="runs as written"):
        rust.bot_spec(rust.ROOT / "bots/zoo/claude/opus-5.5_baseline.py", {"PARAMS.KELP.take_edge": 2})


@needs_cargo
def test_the_zoo_twins_trade_the_same(bench, tmp_path):
    """Every zoo bot alone in five configurations and all of them in one market, on a simulated day,
    the same day trending hard up and down (where the trend followers trade), and a day with
    products the zoo's prompt never named (where most of them raise)."""
    results = bench.zoo_parity(tmp_path, bench.zoo_days(1000))
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, _, _ in results}
    assert len(results) == 4 * (5 * len(bench.zoo_twins()) + 2)
    momentum = [counts[0] for label, counts, _ in results if "opus-5.5_momentum.py, all" in label]
    assert momentum[0] == 0 and min(momentum[1:3]) > 0  # flat on the calm day, trading on the trends


@needs_cargo
@needs_references
def test_the_template_trades_the_same_on_real_days(bench, tmp_path):
    results = bench.real_parity(tmp_path, ticks=1000)
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, _, _ in results}
    assert all(counts[0] > 0 for _, counts, _ in results)


@needs_cargo
def test_settings_the_rust_template_cant_hold_are_refused(bench, tmp_path):
    day = sim.run(sim.preset_market(["KELP"]), 1).day
    rust.export_day(replace(day, ticks=day.ticks[:50]), tmp_path / "day")
    task = {"day": 0, "config": rust.config_json(bench.EngineConfig()), "bots": [["you", 0]], "blocks": 1, "fine": 0}
    for overrides, message in (({"PARAMS.KELP.target": 1.5}, "target must be an integer"),
                               ({"PARAMS.KELP.fair": "best_guess"}, "fair must be a known fair value method"),
                               ({"PARAMS.KELP.make_egde": 1}, "unknown params for KELP: make_egde")):
        path = tmp_path / "batch.json"
        path.write_text(json.dumps({"days": [str(tmp_path / "day")], "bots": [rust.bot_spec(bench.TEMPLATE, overrides)], "tasks": [task]}))
        out = subprocess.run([str(rust.BINARY), "batch", str(path)], capture_output=True, text=True)
        assert out.returncode != 0 and message in out.stderr, (overrides, out.stderr)


def _grid_output(capsys, argv) -> str:
    from arena import grid

    assert grid.main(argv) == 0
    out = capsys.readouterr().out
    return "\n".join(re.sub(r"  \(\d+ s\)$", "", line) for line in out.splitlines() if not line.startswith(("done in", "all combinations written")))


@needs_cargo
def test_the_grid_prints_the_same_on_either_engine(bench, tmp_path, capsys):
    """Everything arena.grid prints and writes, with a rival, resting, a screen and a permutation test."""
    for k, seed in enumerate((11, 12)):
        day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), seed)
        sim.write_day(replace(day, day=replace(day.day, ticks=day.day.ticks[:1000])), tmp_path / "data", 1, k)
    argv = ["bots/template.py", "1", "--data", str(tmp_path / "data"), "--grid", "PARAMS.KELP.make_edge=0.5,1,2", "--grid", "PARAMS.KELP.take_edge=1,2",
            "--modes", "all,worse", "--resting", "--vs", "bots/rivals/trapper.py", "--screen", "0.5", "--permute", "2", "--jobs", "2"]
    ours = _grid_output(capsys, [*argv, "--out", str(tmp_path / "python.csv")])
    theirs = _grid_output(capsys, [*argv, "--engine", "rust", "--out", str(tmp_path / "rust.csv")])
    assert theirs == ours
    assert (tmp_path / "rust.csv").read_text() == (tmp_path / "python.csv").read_text()
    assert "permutation test" in ours and "screened" in ours and "SPA on pnl" in ours and "CSCV on pnl" in ours


def test_the_grid_refuses_a_bot_without_a_rust_twin(tmp_path, capsys):
    from arena import grid

    day = sim.run(sim.preset_market(["KELP"]), 1)
    sim.write_day(replace(day, day=replace(day.day, ticks=day.day.ticks[:300])), tmp_path, 1, 0)
    with pytest.raises(SystemExit):
        grid.main(["bots/probe.py", "1", "--data", str(tmp_path), "--grid", "LIMIT=40,50", "--engine", "rust"])
    assert "has no Rust twin" in capsys.readouterr().err


@needs_cargo
def test_the_day_file_rejects_what_the_rust_engine_cant_hold(bench, tmp_path):
    day = sim.run(sim.preset_market(["KELP"]), 1).day
    tick = day.ticks[0]
    book = tick.books["KELP"]
    fractional = replace(day, ticks=[replace(tick, books={"KELP": replace(book, bids=((book.bids[0][0] + 0.5, 1),))})])
    with pytest.raises(ValueError, match="whole prices"):
        bench.export_day(fractional, tmp_path / "day")


@needs_cargo
def test_the_simulated_market_is_the_same_in_rust(bench):
    """arena.sim with and without twins in it: the recording, the fundamental, every bot's DayResult
    in the market and its replays, in every preset, both modes, regimes, and the whole zoo racing."""
    results = bench.sim_parity(600)
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, *_ in bench.sim_cases(600)}
    counts = {label: c for label, c, _ in results}
    assert counts["the template and every zoo twin requoted, resting"][2] > 0  # races happen
    assert counts["the template copying the noise takers, agents named"][0] != counts["the template, per tick"][0]


@needs_cargo
def test_arena_sim_prints_and_writes_the_same_on_either_engine(tmp_path, capsys):
    from arena import sim as arena_sim

    def run(argv):
        assert arena_sim.main(argv) == 0
        return "\n".join(line for line in capsys.readouterr().out.splitlines() if "bot time per tick" not in line)

    common = ["--days", "2", "--ticks", "800", "--jobs", "2"]
    argv = ["run", "bots/template.py", "--vs", "bots/rivals/trapper.py", "--resting", "--products", "KELP,ROBOT_DISHES", "--regime", "trend_up", *common]
    assert run([*argv, "--engine", "rust", "--out", str(tmp_path / "rust")]) == run([*argv, "--out", str(tmp_path / "python")])
    assert sorted(p.name for p in (tmp_path / "rust").iterdir()) == sorted(p.name for p in (tmp_path / "python").iterdir())
    for path in (tmp_path / "python").iterdir():
        assert (tmp_path / "rust" / path.name).read_text() == path.read_text(), path.name
    argv = ["generate", "--names", "--products", "KELP_FLOW,HYDROGEL_PACK", *common]
    run([*argv[:1], str(tmp_path / "g_python"), *argv[1:]])
    run([*argv[:1], str(tmp_path / "g_rust"), *argv[1:], "--engine", "rust"])
    files = sorted(p.relative_to(tmp_path / "g_python") for p in (tmp_path / "g_python").rglob("*") if p.is_file())
    assert len(files) == 7  # three files a day, and limits.json
    for name in files:
        assert (tmp_path / "g_rust" / name).read_bytes() == (tmp_path / "g_python" / name).read_bytes(), name


def test_arena_sim_refuses_a_bot_without_a_rust_twin(capsys):
    from arena import sim as arena_sim

    with pytest.raises(SystemExit):
        arena_sim.main(["run", "bots/probe.py", "--days", "1", "--ticks", "100", "--engine", "rust"])
    assert "has no Rust twin" in capsys.readouterr().err


@needs_cargo
def test_the_grid_statistics_are_the_same_in_rust(bench):
    """arena/stats.py's CSCV (every halving, sampled ones, tied ranks), the trials' correlation, and SPA
    with StepM (no gain, planted gains, many cells) against rust/src/stats.rs."""
    results = bench.stats_parity()
    assert {label: found for label, _, found in results} == {label: [] for label, *_ in bench.stats_cases()}


def _sim_data(tmp_path, days=2, ticks=800):
    for k in range(days):
        day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), 20 + k)
        sim.write_day(replace(day, day=replace(day.day, ticks=day.day.ticks[:ticks])), tmp_path / "data", 1, k)
    return str(tmp_path / "data")


def _printed(capsys, main, argv) -> str:
    main(argv)
    out = capsys.readouterr().out
    return "\n".join(line for line in out.splitlines() if "bot time per tick" not in line and not line.startswith(("done in", "CSVs written")))


@needs_cargo
def test_backtest_compare_and_stress_print_the_same_on_either_engine(tmp_path, capsys):
    from arena import backtest, compare, stress

    data = _sim_data(tmp_path)
    argv = ["bots/template.py", "1", "--data", data, "--vs", "bots/rivals/trapper.py", "--resting"]
    ours = _printed(capsys, backtest.main, [*argv, "--out", str(tmp_path / "python")])
    assert _printed(capsys, backtest.main, [*argv, "--engine", "rust", "--out", str(tmp_path / "rust")]) == ours
    for path in (tmp_path / "python").iterdir():
        assert (tmp_path / "rust" / path.name).read_text() == path.read_text(), path.name
    argv = ["bots/template.py", "1", "--data", data, "--modes", "all,worse", "--jobs", "2",
            "--bot", "bots/zoo/claude/opus-5.5_market_maker.py", "bots/zoo/other/deepseek-r1-14b_baseline.py", "bots/template.py@PARAMS.KELP.make_edge=1"]
    ours = _printed(capsys, compare.main, argv)
    assert _printed(capsys, compare.main, [*argv, "--engine", "rust"]) == ours
    assert "NameError: name 'Order' is not defined" in ours  # a bot that raises reads the same
    argv = ["bots/template.py", "1", "--data", data, "--only", "trend_up,no_wall", "--vs", "bots/rivals/spoofer.py", "--resting", "--jobs", "2"]
    assert _printed(capsys, stress.main, [*argv, "--engine", "rust"]) == _printed(capsys, stress.main, argv)


@needs_cargo
def test_the_experiments_backtests_are_the_same_on_either_engine(bench):
    """arena.cli.backtest, which the experiments run through: the same results on both engines, in
    full and with only some fields read back, and on a simulated day Rust wrote to a file itself."""
    from arena import cli
    from arena.engine import EngineConfig

    spec = sim.preset_market(["KELP", "RAINFOREST_RESIN"], ticks=600)
    day = sim.run(spec, 3).day
    bots = [("you", bench.TEMPLATE, {"PARAMS.KELP.make_edge": 1}, False), ("rival", bench.RIVALS["sniper"], {}, True)]
    config = EngineConfig(resting=True)
    ours = [bench.python_view(r) for r in cli.backtest(day, bots, config)]
    assert [bench.python_view(r) for r in cli.backtest(day, bots, config, "rust")] == ours
    assert [bench.python_view(r) for r in cli.backtest(rust.sim_day_file(spec, 3), bots, config, "rust")] == [{**v, "market_trades": 0} for v in ours]
    light = cli.backtest(day, bots, config, "rust", fields=("pnl", "errors"))
    assert [r.pnl for r in light] == [r.pnl for r in cli.backtest(day, bots, config)]
    assert light[0].orders == [] and light[0].fills == [] and light[0].positions["KELP"] == []


@needs_cargo
def test_the_drill_template_trades_the_same(bench, tmp_path):
    """bots/drill/template.py against the Rust template's drill ADAPTER on drill-format days (prices
    in cents, ticks of 0.05, 0.01 and 0.25): as committed in every queue model, per tick, against a
    copy, and each part of STRATEGY."""
    results = [case for day in bench.drill_days(tmp_path, 800) for case in bench.parity(day, tmp_path, bench.drill_cases())]
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, _, _ in results}
    assert all(counts[0] > 0 for _, counts, _ in results)


@needs_cargo
def test_the_grid_prints_the_same_on_either_engine_in_the_drill_format(bench, tmp_path, capsys):
    bench.drill_days(tmp_path, 600)
    argv = ["bots/drill/template.py", "all", "--format", "drill", "--data", str(tmp_path / "drill"), "--grid", "PARAMS.ALPHA.make_edge=0,1,2",
            "--modes", "all,worse", "--jobs", "2"]
    assert _grid_output(capsys, [*argv, "--engine", "rust"]) == _grid_output(capsys, argv)


def test_a_twin_runs_only_in_its_own_format():
    with pytest.raises(ValueError, match="is for --format drill"):
        rust.prepare("prosperity", [rust.ROOT / "bots/drill/template.py"])
    with pytest.raises(ValueError, match="is for --format prosperity"):
        rust.prepare("drill", [rust.ROOT / "bots/template.py"])
