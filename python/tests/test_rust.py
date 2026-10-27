"""The Rust port (rust/) against our engine and bots: every recorded field in every configuration,
for each Python file with a Rust twin (rust/twins.json), plus the crate's own unit tests. Skipped
without cargo, except the checks that need no build: that each twin's Python file is the one its
port was last checked against, and that rust/README.md's table lists it.

A change to a twin's Python file (python/arena/engine.py, python/bots/template.py, ...) goes into its Rust file
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


def test_the_twin_hash_counts_code_not_comments_docstrings_or_the_settings_rust_reads():
    path = "python/bots/template.py"
    reads = rust.twins()[path]["reads"]
    source = (rust.ROOT / path).read_text()
    before = rust.code_hash(source, reads)
    same = [
        source.replace("# Each product is isolated", "# Every product is isolated"),  # a comment
        source.replace('"""Trade against book orders', '"""Takes book orders', 1),  # a docstring
        source.replace('"KELP": {"limit": 50, "fair": "sized_mid", "make_edge": 0.5', '"KELP": {"limit": 50, "fair": "sized_mid", "make_edge": 1'),
        source.replace('"wall_size": 15,', '"wall_size": 20,'),  # DEFAULTS
        source.replace("\n\n\nclass Book:", "\n\n\n\nclass Book:"),  # layout
    ]
    assert all(changed != source for changed in same)
    assert [rust.code_hash(changed, reads) for changed in same] == [before] * len(same)
    code = source.replace("if level[0] > fair - buy_edge:", "if level[0] >= fair - buy_edge:")
    assert code != source and rust.code_hash(code, reads) != before
    # The settings count where Rust doesn't read them from the file: a twin without `reads` (the
    # engine, the zoo) hashes its constants.
    assert rust.code_hash(same[2]) != rust.code_hash(source)


def test_every_twin_sits_at_its_python_files_path():
    """rust/src/ mirrors python/: python/arena/engine.py's twin is rust/src/arena/engine.rs. A template
    twin by config (a row with an `adapter`) is the shared rust/src/bots/template.rs instead."""
    for path, twin in rust.twins().items():
        own = "rust/src/" + path.removeprefix("python/").removesuffix(".py") + ".rs"
        assert twin["rust"] == own or ("adapter" in twin and twin["rust"] == "rust/src/bots/template.rs"), path
        assert (rust.ROOT / twin["rust"]).is_file(), twin["rust"]


def test_the_readme_table_lists_every_twin():
    readme = (rust.RUST / "README.md").read_text()
    for path, twin in rust.twins().items():
        if not path.startswith("python/bots/zoo/") and "adapter" not in twin:  # the zoo's row gives the rule for all 32; twins by config share the template's
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
    assert fills["limit penalty, a bot quoting past its limit"][3] > 0  # ticks over the limit, charged
    assert fills["limit penalty, two bots, resting, mark touch"][2] == 0  # nothing rejected, so no races
    assert fills["delay 1"][2] > 0  # alone, but its fills since it decided make orders race


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
    zoo = rust.ROOT / "python" / "bots" / "zoo"
    files = {p.relative_to(rust.ROOT).as_posix() for p in zoo.rglob("*.py") if p.name not in {"bundle.py", "local.py"}}
    assert files - set(rust.twins()) == set()


def test_a_zoo_twin_refuses_settings():
    with pytest.raises(ValueError, match="runs as written"):
        rust.bot_spec(rust.ROOT / "python/bots/zoo/claude/opus-5.5_baseline.py", {"PARAMS.KELP.take_edge": 2})


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
                               ({"PARAMS.KELP.make_egde": 1}, "unknown params for KELP: make_egde"),
                               ({"PARAMS.NEW": {"fair": "mid"}}, "no limit for NEW: set the competition's in PARAMS")):
        path = tmp_path / "batch.json"
        path.write_text(json.dumps({"days": [str(tmp_path / "day")], "bots": [rust.bot_spec(bench.TEMPLATE, overrides)], "tasks": [task]}))
        out = subprocess.run([str(rust.BINARY), "batch", str(path)], capture_output=True, text=True)
        assert out.returncode != 0 and message in out.stderr, (overrides, out.stderr)


@needs_cargo
def test_the_rust_batch_applies_each_cells_overrides_as_set_does(bench, tmp_path):
    """One spec for every cell, each task's `set` applied in Rust by botfile's rules: the same pieces as a
    spec per cell, and a bad path or value in any task refused, before anything runs, in botfile's words."""
    from arena.botfile import BotFile, OverrideError
    from arena.formats import prosperity

    day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), 1).day
    rust.export_day(replace(day, ticks=day.ticks[:400]), tmp_path / "day")
    task = {"day": 0, "config": rust.config_json(bench.EngineConfig()), "blocks": 2, "fine": 4}
    cells = [{"PARAMS.KELP.make_edge": 1}, {"PARAMS.KELP.make_edge": 3, "PARAMS.KELP.take_edge": 0},
             {"PARAMS.RAINFOREST_RESIN": {"limit": 50, "fair": "wall_mid", "make_edge": 1}}]
    products = [list(day.products)] * len(cells)
    base = rust.bot_spec(bench.TEMPLATE, {})
    one = rust.run_batch([tmp_path / "day"], [base], [{**task, "bots": [["you", 0]], "set": [[k, v] for k, v in c.items()]} for c in cells], 2,
                         tmp_path, products)
    each = rust.run_batch([tmp_path / "day"], [rust.bot_spec(bench.TEMPLATE, c) for c in cells],
                          [{**task, "bots": [["you", k]]} for k in range(len(cells))], 2, tmp_path, products)
    assert one == each and len({piece["pnl"] for piece in one}) == 3
    for path, value in (("PARAMS.KELP.target", 1.5), ("PARAMS.NOPE.make_edge", 1), ("PARAMS.KELP.limit.x", 1), ("NOPE", 1)):
        tasks = [{**task, "bots": [["you", 0]], "set": [["PARAMS.KELP.make_edge", 1]]}, {**task, "bots": [["you", 0]], "set": [[path, value]]}]
        (tmp_path / "batch.json").write_text(json.dumps({"days": [str(tmp_path / "day")], "bots": [base], "tasks": tasks}))
        out = subprocess.run([str(rust.BINARY), "batch", str(tmp_path / "batch.json"), "--binary", str(tmp_path / "x.bin")], capture_output=True, text=True)
        assert out.returncode != 0 and not (tmp_path / "x.bin").exists(), path
        if path != "PARAMS.KELP.target":  # the Rust template's own check of a value; the others are botfile's
            with pytest.raises(OverrideError) as python:
                BotFile(bench.TEMPLATE, {"datamodel": prosperity.dm}).load({path: value})
            assert str(python.value) in out.stderr, (out.stderr, python.value)
        else:
            assert "target must be an integer" in out.stderr


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
    argv = ["python/bots/template.py", "1", "--data", str(tmp_path / "data"), "--grid", "PARAMS.KELP.make_edge=0.5,1,2", "--grid", "PARAMS.KELP.take_edge=1,2",
            "--modes", "all,worse", "--resting", "--vs", "python/bots/rivals/trapper.py", "--screen", "0.5", "--permute", "2", "--jobs", "2"]
    ours = _grid_output(capsys, [*argv, "--out", str(tmp_path / "python.csv")])
    theirs = _grid_output(capsys, [*argv, "--engine", "rust", "--out", str(tmp_path / "rust.csv")])
    assert theirs == ours
    assert (tmp_path / "rust.csv").read_text() == (tmp_path / "python.csv").read_text()
    assert "permutation test" in ours and "screened" in ours and "SPA on pnl" in ours and "CSCV on pnl" in ours


@needs_cargo
def test_the_grid_and_compare_print_the_same_on_either_engine_under_scenarios(tmp_path, capsys):
    """Scenarios with their own engine settings and rivals (a rival's overrides too), beside --vs."""
    from arena import compare

    data = _sim_data(tmp_path)
    scenarios = ["--scenario", "rest:resting,queue=front,fill=0.7,vs=python/bots/rivals/trapper.py@BAIT=20@PERIOD=100",
                 "--scenario", "alone:match=worse,vs=none", "--vs", "python/bots/rivals/sniper.py", "--jobs", "2"]
    argv = ["python/bots/template.py", "1", "--data", data, "--grid", "PARAMS.KELP.make_edge=0.5,1,2", "--modes", "all", *scenarios]
    ours = _grid_output(capsys, [*argv, "--out", str(tmp_path / "python.csv")])
    assert _grid_output(capsys, [*argv, "--engine", "rust", "--out", str(tmp_path / "rust.csv")]) == ours
    assert (tmp_path / "rust.csv").read_text() == (tmp_path / "python.csv").read_text()
    assert "best by worst" in ours and "rest: match all, resting, queue front, fill 0.7; against python/bots/rivals/trapper.py@BAIT=20@PERIOD=100" in ours
    argv = ["python/bots/template.py", "1", "--data", data, "--bot", "python/bots/template.py@PARAMS.KELP.make_edge=1", *scenarios]
    assert _printed(capsys, compare.main, [*argv, "--engine", "rust"]) == _printed(capsys, compare.main, argv)


def test_the_grid_refuses_a_bot_without_a_rust_twin(tmp_path, capsys):
    from arena import grid

    day = sim.run(sim.preset_market(["KELP"]), 1)
    sim.write_day(replace(day, day=replace(day.day, ticks=day.day.ticks[:300])), tmp_path, 1, 0)
    with pytest.raises(SystemExit):
        grid.main(["python/bots/probe.py", "1", "--data", str(tmp_path), "--grid", "LIMIT=40,50", "--engine", "rust"])
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
    argv = ["run", "python/bots/template.py", "--vs", "python/bots/rivals/trapper.py", "--resting", "--products", "KELP,ROBOT_DISHES", "--regime", "trend_up", *common]
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
        arena_sim.main(["run", "python/bots/probe.py", "--days", "1", "--ticks", "100", "--engine", "rust"])
    assert "has no Rust twin" in capsys.readouterr().err


@needs_cargo
def test_the_grid_statistics_are_the_same_in_rust(bench):
    """python/arena/stats.py's CSCV (every halving, sampled ones, tied ranks), the trials' correlation, and SPA
    with StepM (no gain, planted gains, many cells) against rust/src/arena/stats.rs."""
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
    argv = ["python/bots/template.py", "1", "--data", data, "--vs", "python/bots/rivals/trapper.py", "--resting"]
    ours = _printed(capsys, backtest.main, [*argv, "--out", str(tmp_path / "python")])
    assert _printed(capsys, backtest.main, [*argv, "--engine", "rust", "--out", str(tmp_path / "rust")]) == ours
    for path in (tmp_path / "python").iterdir():
        assert (tmp_path / "rust" / path.name).read_text() == path.read_text(), path.name
    argv = ["python/bots/template.py", "1", "--data", data, "--modes", "all,worse", "--jobs", "2",
            "--bot", "python/bots/zoo/claude/opus-5.5_market_maker.py", "python/bots/zoo/other/deepseek-r1-14b_baseline.py", "python/bots/template.py@PARAMS.KELP.make_edge=1"]
    ours = _printed(capsys, compare.main, argv)
    assert _printed(capsys, compare.main, [*argv, "--engine", "rust"]) == ours
    assert "NameError: name 'Order' is not defined" in ours  # a bot that raises reads the same
    argv = ["python/bots/template.py", "1", "--data", data, "--only", "trend_up,no_wall", "--vs", "python/bots/rivals/spoofer.py", "--resting", "--jobs", "2"]
    assert _printed(capsys, stress.main, [*argv, "--engine", "rust"]) == _printed(capsys, stress.main, argv)


@needs_cargo
def test_the_marks_and_the_limit_penalty_print_the_same_on_either_engine(tmp_path, capsys):
    """--mark and --limit-penalty through arena.backtest (one Rust run per day) and arena.grid's
    scenarios (the batch's configs), with mm.py taking 3 through its fair, up to 80 against the days' limit of 50."""
    from arena import backtest, grid

    data = _sim_data(tmp_path)
    greedy = '{"KELP": {"make_edge": 1, "take_edge": -3, "hold": False}, "RAINFOREST_RESIN": {"make_edge": 1, "take_edge": -3, "hold": False}}'
    argv = ["python/bots/mm.py", "1", "--data", data, "--set", "LIMIT=80", "--set", f"PARAMS={greedy}", "--vs", "python/bots/template.py", "--resting",
            "--mark", "touch", "--limit-penalty", "2"]
    ours = _printed(capsys, backtest.main, argv)
    assert _printed(capsys, backtest.main, [*argv, "--engine", "rust"]) == ours
    assert "ticks over a limit (--limit-penalty)" in ours
    argv = ["python/bots/template.py", "1", "--data", data, "--grid", "PARAMS.KELP.make_edge=0.5,1", "--modes", "all",
            "--scenario", "portal:mark=last,penalty=1,vs=python/bots/mm.py@LIMIT=80", "--scenario", "touch:mark=touch,resting", "--jobs", "2"]
    ours = _printed(capsys, grid.main, argv)
    assert _printed(capsys, grid.main, [*argv, "--engine", "rust"]) == ours
    assert "portal: match all, per tick, mark last, limit penalty 1; against python/bots/mm.py@LIMIT=80" in ours


@needs_cargo
def test_a_delay_prints_the_same_on_either_engine(tmp_path, capsys):
    """--delay through arena.backtest (one Rust run per day), per tick alone and resting with a rival,
    and through arena.grid's scenarios (the batch's configs)."""
    from arena import backtest, grid

    data = _sim_data(tmp_path)
    for k, extra in enumerate((["--delay", "1"], ["--delay", "2", "--resting", "--vs", "python/bots/rivals/trapper.py"])):
        argv = ["python/bots/template.py", "1", "--data", data, *extra]
        ours = _printed(capsys, backtest.main, [*argv, "--out", str(tmp_path / f"python{k}")])
        assert _printed(capsys, backtest.main, [*argv, "--engine", "rust", "--out", str(tmp_path / f"rust{k}")]) == ours
        for path in (tmp_path / f"python{k}").iterdir():
            assert (tmp_path / f"rust{k}" / path.name).read_text() == path.read_text(), path.name
    assert _printed(capsys, backtest.main, ["python/bots/template.py", "1", "--data", data]) != ours  # the delay changes the run
    argv = ["python/bots/template.py", "1", "--data", data, "--grid", "PARAMS.KELP.make_edge=0.5,1", "--modes", "all",
            "--scenario", "late:delay=1", "--scenario", "later:delay=2,resting,vs=python/bots/rivals/sniper.py", "--jobs", "2"]
    ours = _printed(capsys, grid.main, argv)
    assert _printed(capsys, grid.main, [*argv, "--engine", "rust"]) == ours
    assert "late: match all, per tick, delay 1; no rivals" in ours


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
    """python/bots/drill/template.py against the Rust template's drill ADAPTER on drill-format days (prices
    in cents, ticks of 0.05, 0.01 and 0.25): as committed in every queue model, per tick, against a
    copy, and each part of STRATEGY."""
    results = [case for day in bench.drill_days(tmp_path, 800) for case in bench.parity(day, tmp_path, bench.drill_cases())]
    assert {label: found[:1] for label, _, found in results} == {label: [] for label, _, _ in results}
    assert all(counts[0] > 0 for _, counts, _ in results)


@needs_cargo
def test_the_grid_prints_the_same_on_either_engine_in_the_drill_format(bench, tmp_path, capsys):
    bench.drill_days(tmp_path, 600)
    argv = ["python/bots/drill/template.py", "all", "--format", "drill", "--data", str(tmp_path / "drill"), "--grid", "PARAMS.ALPHA.make_edge=0,1,2",
            "--modes", "all,worse", "--jobs", "2"]
    assert _grid_output(capsys, [*argv, "--engine", "rust"]) == _grid_output(capsys, argv)


def test_a_twin_runs_only_in_its_own_format():
    with pytest.raises(ValueError, match="is for --format drill"):
        rust.prepare("prosperity", [rust.ROOT / "python/bots/drill/template.py"])
    with pytest.raises(ValueError, match="is for --format prosperity"):
        rust.prepare("drill", [rust.ROOT / "python/bots/template.py"])


def test_a_stale_twin_refuses_to_run_unless_allowed(monkeypatch, capsys):
    """A twin checked against older Python code would run that older code: refused, by the tools and
    the experiments, unless --allow-stale."""
    built = []
    monkeypatch.setattr(rust, "build", lambda: built.append(True))
    template = rust.ROOT / "python/bots/template.py"
    monkeypatch.setattr(rust, "stale_twins", lambda: ["python/bots/template.py"])
    with pytest.raises(ValueError, match="python/bots/template.py were checked against older Python code"):
        rust.prepare("prosperity", [template])
    with pytest.raises(ValueError, match="--allow-stale"):
        rust.require()
    rust.prepare("prosperity", [rust.ROOT / "python/bots/mm.py"])  # a stale bot the run doesn't use doesn't matter
    rust.prepare("prosperity", [template], allow_stale=True)
    assert "! the Rust twins of python/bots/template.py" in capsys.readouterr().err
    monkeypatch.setattr(rust, "stale_twins", lambda: ["python/arena/engine.py"])  # the engine's twin matters to every run
    with pytest.raises(ValueError, match="engine.py"):
        rust.prepare("prosperity", [rust.ROOT / "python/bots/mm.py"])
    assert len(built) == 2


def _rust_day(tmp_path, day, only=None):
    path = rust.write_day(day, tmp_path / "ref", only)
    assert path.suffix == ".json"  # a reference to the CSVs, not an export
    subprocess.run([str(rust.BINARY), "day", str(path), "--out", str(tmp_path)], check=True)
    return rust.read_day(tmp_path / f"{day.name}.day")


def _same_day(a, b) -> bool:
    return (a.name, a.products, list(a.limits.items()), [t.timestamp for t in a.ticks]) == (b.name, b.products, list(b.limits.items()), [t.timestamp for t in b.ticks]) and all(
        x.books == y.books and list(x.books) == list(y.books) and x.marks == y.marks and list(x.marks) == list(y.marks)
        and {p: v for p, v in x.trades.items() if v} == {p: v for p, v in y.trades.items() if v} for x, y in zip(a.ticks, b.ticks))


@needs_cargo
def test_rust_reads_prosperity_csvs_as_the_plug_in_does(bench, tmp_path):
    """rust/src/arena/formats/prosperity.rs against python/arena/formats/prosperity.py: arena.sim days written in the
    Prosperity layout (limits.json included), whole and restricted to one product."""
    from arena import grid
    from arena.formats import prosperity

    for k, products in enumerate((["KELP", "RAINFOREST_RESIN"], ["HYDROGEL_PACK", "ROBOT_DISHES"])):
        sim.write_day(sim.run(sim.preset_market(products, ticks=500), k), tmp_path / "data", 1, k)
    for day in prosperity.load_days(tmp_path / "data", ["1"]):
        assert _same_day(_rust_day(tmp_path, day), day)
        assert _same_day(_rust_day(tmp_path, day, day.products[:1]), grid.only(day, day.products[:1]))
    assert prosperity.reference(sim.run(sim.preset_market(["KELP"], ticks=10), 0).day) is None  # not from files: exported instead


@needs_cargo
@needs_references
def test_rust_reads_every_prosperity_day_as_the_plug_in_does(bench, tmp_path):
    from arena.formats import prosperity

    for data in ("p2", "p3", "p4"):
        directory = prosperity.resolve_data_dir(data)
        for r, d in prosperity.list_days(directory)[::4]:
            day = prosperity.load_day(directory, r, d)
            assert _same_day(_rust_day(tmp_path, day), day), (data, r, d)


@needs_cargo
def test_a_day_cut_to_some_products_but_not_its_limits_exports(tmp_path):
    """python/experiments/p3_smile.py keeps a day's options and drops the rest, leaving `limits` whole."""
    from arena import cli
    from arena.engine import EngineConfig

    day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"], ticks=300), 2).day
    cut = replace(day, products=["KELP"], ticks=[replace(t, books={"KELP": t.books["KELP"]}, trades={p: v for p, v in t.trades.items() if p == "KELP"},
                                                          marks={p: v for p, v in t.marks.items() if p == "KELP"}) for t in day.ticks])
    bots = [("you", rust.ROOT / "python/bots/template.py", {}, False)]
    assert [r.pnl for r in rust.backtest(cut, bots, EngineConfig())] == [r.pnl for r in cli.backtest(cut, bots, EngineConfig())]


@needs_cargo
def test_the_stress_copies_are_the_same_in_rust(bench, tmp_path):
    """python/arena/stress.py's perturbations (each, at several sizes) and permute (seeds, block
    lengths) against rust/src/arena/stress.rs, on a simulated day and a drill day (ALPHA's tick is 5)."""
    results = bench.stress_parity(tmp_path, bench.stress_days(tmp_path, ticks=1500, real=False))
    assert {label: found for label, _, found in results} == {label: [] for label, *_ in results}
    assert len(results) == 2 * len(bench.stress_transforms())


DRILL_CHOICES = {"units": True, "names": False, "own_trades": False, "exchange_limit": True, "exchange_order": True, "sorted_resting": False}


def _as_config_twin(monkeypatch, tmp_path, adapter):
    """A copy of the drill template, declared in rust/twins.json (for this test) as a template twin by
    its adapter's choices alone: what the Arena's template becomes on the day."""
    copy = tmp_path / "arena_template.py"
    copy.write_text((rust.ROOT / "python/bots/drill/template.py").read_text())
    rows = {**rust.twins(), str(copy): {"kind": "template", "format": "drill", "rust": "rust/src/bots/template.rs", "adapter": adapter}}
    monkeypatch.setattr(rust, "_rows", lambda: rows)
    for cached in (rust._kinds, rust._reads_settings):
        cached.cache_clear()
    return copy


@needs_cargo
@pytest.mark.parametrize("adapter, same", [(DRILL_CHOICES, True), ({**DRILL_CHOICES, "units": False}, False)], ids=["right choices", "a wrong one"])
def test_a_template_twin_by_config_trades_as_its_python_file(bench, tmp_path, monkeypatch, adapter, same):
    try:
        copy = _as_config_twin(monkeypatch, tmp_path, adapter)
        day = bench.drill_days(tmp_path, ticks=600)[0]
        results = bench.parity(day, tmp_path, bench.twin_cases(copy, ["ALPHA", "BETA"], resting=True)[:7], jobs=1)
    finally:
        for cached in (rust._kinds, rust._reads_settings):
            cached.cache_clear()
    differing = [label for label, _, found in results if found]
    assert (differing == []) is same, differing


def test_a_python_run_takes_its_statistics_from_rust_when_it_builds(monkeypatch):
    """The studentized bootstrap is slow in Python and the same to the bit in Rust (stats_parity),
    so a Python-engine grid uses the Rust statistics whenever the binary builds and stats.py's twin
    is current."""
    assert rust.stats_engine("rust") == "rust"
    if shutil.which("cargo"):
        assert rust.stats_engine("python") == "rust"
    monkeypatch.setattr(rust, "stale_twins", lambda: ["python/arena/stats.py"])
    assert rust.stats_engine("python") == "python"
    monkeypatch.setattr(rust.shutil, "which", lambda name: None)
    assert rust.stats_engine("python") == "python"
