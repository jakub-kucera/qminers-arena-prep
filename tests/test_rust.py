"""The Rust port of the engine (rust/) against ours, on a short arena.sim day: every recorded field
under each configuration of experiments/rust_bench.py, plus the crate's own unit tests. Skipped
without cargo. A change to arena/engine.py's rules must be made in rust/src/engine.rs too."""

import shutil
import subprocess
from dataclasses import replace

import pytest

from arena import sim

pytestmark = pytest.mark.skipif(shutil.which("cargo") is None, reason="needs cargo (rust/)")


@pytest.fixture(scope="module")
def bench():
    from experiments import rust_bench

    rust_bench.build()
    return rust_bench


def test_the_crates_unit_tests_pass(bench):
    out = subprocess.run(["cargo", "test", "--release", "--quiet", "--manifest-path", str(bench.RUST / "Cargo.toml")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_rust_records_what_our_engine_records_in_every_configuration(bench, tmp_path):
    day = sim.run(sim.preset_market(["KELP", "RAINFOREST_RESIN"]), 5).day
    day = replace(day, ticks=day.ticks[:2000])
    results = bench.parity(day, tmp_path)
    assert [name for name, _, _ in results] == [name for name, _, _ in bench.CONFIGS]
    assert {name: found[:1] for name, _, found in results} == {name: [] for name, _, _ in results}
    fills = {name: counts for name, counts, _ in results}
    assert all(counts[0] > 0 for counts in fills.values())
    assert fills["two bots, resting"][1] > 0 and fills["two bots, resting"][2] > 0  # crosses and races happen


def test_the_day_file_rejects_what_the_rust_engine_cant_hold(bench, tmp_path):
    day = sim.run(sim.preset_market(["KELP"]), 1).day
    tick = day.ticks[0]
    book = tick.books["KELP"]
    fractional = replace(day, ticks=[replace(tick, books={"KELP": replace(book, bids=((book.bids[0][0] + 0.5, 1),))})])
    with pytest.raises(ValueError, match="whole prices"):
        bench.export_day(fractional, tmp_path / "day")
