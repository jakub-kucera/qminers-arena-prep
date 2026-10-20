# rust/: the engine and the bots in Rust

A Rust port of `arena/engine.py` and of the bots we run most, kept apart from the Python code. It
gives the same results as the Python, to the bit, about 100–200 times faster. `arena.grid --engine
rust` runs its backtests here; everything else (loading data, the statistics, the reports) stays
Python. The submitted bot is still a Python file: a Rust bot is a twin for searching, never for
submitting.

```sh
brew install rust                                     # or rustup; any recent stable toolchain
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..7 --engine rust
uv run python -m experiments.rust_bench               # build, check every twin, then time both engines
uv run python -m experiments.rust_bench --parity-only --record   # after changing a twin: check, then record its hash
uv run pytest tests/test_rust.py                      # the parity checks, shorter, and `cargo test`
```

## What is in Python, in Rust, and in both

**In both**: every Rust file below has a Python twin, and the two must stay equal.
`rust/twins.json` lists the pairs with the hash of the Python file the port was last checked
against. `tests/test_rust.py` fails when a Python twin changes until the Rust side is updated and
`experiments.rust_bench --record` has checked the pair again.

| Python | Rust | What it is | How they're checked |
|---|---|---|---|
| `arena/engine.py` | `src/engine.rs` | `run_market` / `run_day` function for function (`_take` is `take`, ...): both modes, the three queue models, the fill ratio, several bots in one market, every per-tick record of a `DayResult` | every field a `DayResult` records, under every engine configuration, by all the bots below |
| `bots/mm.py` | `src/bots/mm.rs` | a plain wall-mid market maker, the benchmark's bot | 15 engine configurations (`CONFIGS`) |
| `bots/template.py` | `src/bots/template.rs` | STRATEGY and EXECUTION function for function, and ADAPTER as the Prosperity plug-in presents a tick to it; the settings come from the Python file's own DEFAULTS and PARAMS | 18 variants, one per part of STRATEGY, alone and in a resting market with a rival; the committed settings in 6 more configurations; 10 real days (P2, P3, P4) under two configurations |
| `bots/rivals/sniper.py`, `bots/rivals/spoofer.py`, `bots/rivals/trapper.py` | `src/bots/rivals.rs` | the adversarial `--vs` rivals | 13 cases: against the template and `mm`, resting and per tick, with their constants changed by `--set`, all three at once |

Supporting pieces that copy Python exactly but have no file of their own to hash:

| Python | Rust | |
|---|---|---|
| `arena/model.py` | `src/model.rs` | the types; products are indices into the day's list (sorted by name), trader names into its name table |
| `random.Random` (CPython 3.12) | `src/pyrandom.rs` | MT19937, int and str seeding, `random`, `shuffle`, `binomialvariate`, draw for draw (`cargo test` has CPython's vectors) |
| `arena.cli.Requote` | `Requote` in `src/bots/mod.rs` | `--requote` for rivals |
| `arena.grid.block_pnl`, `report.total_pnl`, `product_stats` | `block_pnl`, `piece` in `src/main.rs` | what a grid task returns (`arena-rs batch`) |
| `math.erf`, `x ** 2`, `math.exp`, `math.log` | libm's `erf`, `pow`, `exp`, `log` | CPython calls the C library for these, so the Rust does too. On macOS `pow(x, 2)` isn't always `x * x`. |

**Only in Python**:
- the format plug-ins (`arena/formats/`), which load the data;
- `arena.backtest` and `arena.validate`;
- everything in `arena.grid` but the backtests: the axes, screening, the permutation test's shuffles (`arena.stress.permute`), and the statistics (held-out days, PBO, DSR, SPA, StepM);
- `arena.compare`, `arena.analysis`, `arena.diagnose`, `arena.stress`, `arena.sim`, and `arena.report`'s CSVs;
- `bots/drill/template.py`, `bots/probe.py`, `bots/zoo/`, and `experiments/`.

`arena/rust.py` is the bridge. It exports days, turns a twin's Python file into its Rust bot's settings (`bot_spec`, with any `--set` overrides), and runs `arena-rs batch`.

**Only in Rust**: the day-file reader (`src/dayfile.rs`, for days `arena/rust.py` exports after the plug-ins have loaded them), the thread pool of `arena-rs batch` and `grid`, SHA-512 (string seeds, as CPython hashes them), and a JSON reader.

## Layout

| File | What it is |
|---|---|
| `src/engine.rs` | the engine (above) |
| `src/model.rs`, `src/dayfile.rs` | the types, and the exported day format |
| `src/bots/` | the twins; `mod.rs` builds one by its kind (`rust/twins.json`) from its Python file's globals |
| `src/pyrandom.rs`, `src/sha512.rs`, `src/json.rs` | Python's random numbers, its string seeding, and the settings' format |
| `src/main.rs` | `arena-rs run` (one market; `--dump` writes every recorded field for the parity check), `batch` (arena.grid's backtests on N threads), `grid` (`mm`'s make × take grid, for timing) |

## What is and isn't ported

- **The engine.** Ported: every rule in `arena/engine.py`'s docstring, in the same order of operations. Not ported:
  - order tags (a format's own ids);
  - a bot's exceptions, prints and step timings;
  - `begin_day`'s per-product info;
  - fractional prices (the day file holds whole prices, as Prosperity's are);
  - CPython's own `lgamma`: `binomialvariate` calls the C library's. They differ by a few ulps, which could flip a fill-ratio draw only when its test lands that close to the bound.
- **The template.** Ported: all of STRATEGY and EXECUTION. Not ported: `STRICT`, and the per-product try/except (a Rust bot can't raise). Settings that the Python would only fail on while running are refused when the bot is built, so its grid cell fails before it starts. That covers an unknown key, an unknown fair method, and a float where an integer is needed (`limit`, `target`, `make_size`, `cpd_block`).
- **A bot's state across ticks.** The Python bots keep it in `traderData` as JSON. The Rust ones keep the same values in fields, which is equivalent because JSON gives every float back exactly.

## Keeping it in step

1. Change the rule or the strategy in Python, and port the change to the file `rust/twins.json` names.
2. Run `uv run python -m experiments.rust_bench --parity-only --record`. It compares every recorded field in every case, and records the new hashes only if every case is identical.
3. Run `uv run pytest tests/test_rust.py`.

Python files without a Rust twin need nothing. `arena.grid --engine rust` refuses a bot without a twin, and warns when a twin's hash is stale.

A new twin needs four things:
- a Rust file under `src/bots/`;
- a kind in `src/bots/mod.rs`;
- a row in `rust/twins.json` and in the table above;
- cases in `experiments/rust_bench.py`, run by `tests/test_rust.py`.
