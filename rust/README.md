# rust/: the engine and the bots in Rust

A Rust port of `arena/engine.py`, `arena/sim.py`'s market and every bot we run, kept apart from the
Python code. It gives the same results as the Python, to the bit, about 100–200 times faster.
`arena.grid --engine rust` runs its backtests and statistics here and `arena.sim --engine rust` its market;
loading data, the statistics and the reports stay Python. The submitted bot is still a Python file: a Rust bot is a twin for searching, never for
submitting.

```sh
brew install rust                                     # or rustup; any recent stable toolchain
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..7 --engine rust
uv run python -m arena.sim run bots/template.py --days 20 --engine rust
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
| `arena/sim.py` | `src/sim.rs` | the market: the book, the fundamental (reversion, jumps and their bursts, regimes), the five agent kinds drawing from their own seeded `random.Random`s, bots trading inside it in both modes. The specs, presets, `--spec` and regimes stay in Python, which passes the spec as JSON; the Prosperity CSVs of `generate` are written by both | the recording (books, trades and their order, marks, ints kept apart from floats), the fundamental, and every bot's DayResult in the market and in its replays: every preset, both modes, two regimes, agents shown by name, the maker among the takers with skew, the rivals, and all 32 zoo bots racing (13 cases); `arena.sim run` and `generate` print and write the same, byte for byte |
| `arena/stats.py` | `src/stats.rs` | the grid's statistics whose cost grows with the cells: `cscv` (PBO; every halving, or 4,000 sampled with `random.sample`), `mean_correlation` (the DSR's independent trials), and `snooping` (Hansen's `omega2` and stationary bootstrap, SPA, StepM). `expected_max_sharpe`, `deflated_sharpe` and `standardized` stay Python only, being cheap | 12 cases (`stats_parity`): every halving and sampled ones, ties in the ranks, a constant cell, one cell; correlated and independent cells; no gain, planted gains, 400 cells, whole numbers; and `arena.grid` prints the same on either engine |
| `bots/mm.py` | `src/bots/mm.rs` | a plain wall-mid market maker, the benchmark's bot | 15 engine configurations (`CONFIGS`) |
| `bots/template.py` | `src/bots/template.rs` | STRATEGY and EXECUTION function for function, and ADAPTER as the Prosperity plug-in presents a tick to it; the settings come from the Python file's own DEFAULTS and PARAMS | 18 variants, one per part of STRATEGY, alone and in a resting market with a rival; the committed settings in 6 more configurations; 10 real days (P2, P3, P4) under two configurations |
| `bots/drill/template.py` | `src/bots/template.rs` (`Template::drill`) | the same STRATEGY and EXECUTION behind the drill format's ADAPTER (`drill_step`): prices converted from the format's units to each product's ticks and back as `arena/formats/drill.py` and the ADAPTER do, products in the exchange's order, trades without names, the limit from the exchange. Its days carry `Day.info`'s ticks and unit in the day file | on two drill-format days (`format_drill`'s, prices in cents on ticks of 0.05, 0.01 and 0.25): as committed in each queue model, per tick, against a copy, and the 17 variants of STRATEGY (44 cases); inside `arena.sim`'s market, where it sees prices in its unit |
| `bots/rivals/sniper.py`, `bots/rivals/spoofer.py`, `bots/rivals/trapper.py` | `src/bots/rivals.rs` | the adversarial `--vs` rivals | 13 cases: against the template and `mm`, resting and per tick, with their constants changed by `--set`, all three at once |
| the 32 zoo bots, below | `src/bots/zoo/` | translated line by line, never edited on either side; they don't read settings from the file, so `--set` on one is refused | each alone (all, worse, a fill ratio, resting as written, resting requoted) and all of them with the template in one market, per tick and resting, on a simulated day, the same day trending hard up and down, a day with products their prompt never named (where most raise, or trade with limits they made up), and the first day of P2, P3 and P4 round 1: 1,134 cases |

The zoo's twins, one row per Python file (several small bots share a Rust file, one struct each):

| Python | Rust | | |
|---|---|---|---|
| `bots/zoo/chatgpt/gpt-5-6-luna_baseline.py` | `src/bots/zoo/chatgpt_luna_baseline.rs` | | |
| `bots/zoo/chatgpt/gpt-5-6-luna_market_maker.py` | `src/bots/zoo/chatgpt_luna_market_maker.rs` | | |
| `bots/zoo/claude/haiku-5.5_baseline.py` | `src/bots/zoo/claude_haiku_baseline.rs` | | |
| `bots/zoo/claude/opus-5.5_baseline.py` | `src/bots/zoo/claude_opus_baseline.rs` | | |
| `bots/zoo/claude/opus-5.5_market_maker.py` | `src/bots/zoo/claude_opus_market_maker.rs` | | |
| `bots/zoo/claude/opus-5.5_mean_reversion.py` | `src/bots/zoo/claude_opus_mean_reversion.rs` | | |
| `bots/zoo/claude/opus-5.5_momentum.py` | `src/bots/zoo/claude_opus_momentum.rs` | | |
| `bots/zoo/claude/sonnet-5.5_baseline.py` | `src/bots/zoo/claude_sonnet_baseline.rs` | | |
| `bots/zoo/gemini/gemini-3-8-flash-high_baseline.py` | `src/bots/zoo/gemini_flash_baseline.rs` | | |
| `bots/zoo/gemini/gemini-3-8-flash-high_market_maker.py` | `src/bots/zoo/gemini_flash_market_maker.rs` | | |
| `bots/zoo/other/deepseek-r1-14b_baseline.py` | `src/bots/zoo/deepseek_baseline.rs` | | |
| `bots/zoo/other/deepseek-r1-14b_baseline_2.py` | `src/bots/zoo/deepseek_baseline_2.rs` | | |
| `bots/zoo/other/deepseek-r1-14b_market_maker.py` | `src/bots/zoo/deepseek_market_maker.rs` | | |
| `bots/zoo/other/deepseek-r1-14b_market_maker_2.py` | `src/bots/zoo/deepseek_market_maker_2.rs` | | |
| `bots/zoo/other/gemma4-26b_baseline.py` | `src/bots/zoo/gemma_baseline.rs` | | |
| `bots/zoo/other/gemma4-26b_baseline_2.py` | `src/bots/zoo/gemma_baseline_2.rs` | | |
| `bots/zoo/other/gemma4-26b_market_maker.py` | `src/bots/zoo/gemma_market_maker.rs` | | |
| `bots/zoo/other/gemma4-26b_market_maker_2.py` | `src/bots/zoo/gemma_market_maker_2.rs` | | |
| `bots/zoo/other/gpt-oss-120B_baseline.py` | `src/bots/zoo/gpt_oss.rs` | | |
| `bots/zoo/other/gpt-oss-120B_market_maker.py` | `src/bots/zoo/gpt_oss.rs` | | |
| `bots/zoo/other/gpt-oss-20b_baseline.py` | `src/bots/zoo/gpt_oss.rs` | | |
| `bots/zoo/other/gpt-oss-20b_baseline_2.py` | `src/bots/zoo/gpt_oss.rs` | | |
| `bots/zoo/other/gpt-oss-20b_market_maker.py` | `src/bots/zoo/gpt_oss.rs` | | |
| `bots/zoo/other/gpt-oss-20b_market_maker_2.py` | `src/bots/zoo/gpt_oss.rs` | | |
| `bots/zoo/other/phi4-14b_baseline.py` | `src/bots/zoo/phi4.rs` | | |
| `bots/zoo/other/phi4-14b_baseline_2.py` | `src/bots/zoo/phi4.rs` | | |
| `bots/zoo/other/phi4-14b_market_maker.py` | `src/bots/zoo/phi4.rs` | | |
| `bots/zoo/other/phi4-14b_market_maker_2.py` | `src/bots/zoo/phi4.rs` | | |
| `bots/zoo/other/qwen3.8-27b-medium_baseline.py` | `src/bots/zoo/qwen.rs` | | |
| `bots/zoo/other/qwen3.8-27b-medium_baseline_2.py` | `src/bots/zoo/qwen.rs` | | |
| `bots/zoo/other/qwen3.8-27b-medium_market_maker.py` | `src/bots/zoo/qwen.rs` | | |
| `bots/zoo/other/qwen3.8-27b-medium_market_maker_2.py` | `src/bots/zoo/qwen.rs` | | |

Supporting pieces that copy Python exactly but have no file of their own to hash:

| Python | Rust | |
|---|---|---|
| `arena/model.py` | `src/model.rs` | the types; products are indices into the day's list (sorted by name), trader names into its name table |
| `random.Random` (CPython 3.12) | `src/pyrandom.rs` | MT19937, int and str seeding, `random`, `shuffle`, `randint`, `uniform`, `gauss`, `binomialvariate`, draw for draw (`cargo test` has CPython's vectors) |
| `arena.cli.Requote` | `Requote` in `src/bots/mod.rs` | `--requote` for rivals |
| `arena.grid.block_pnl`, `report.total_pnl`, `product_stats` | `block_pnl`, `piece` in `src/main.rs` | what a grid task returns (`arena-rs batch`) |
| `math.erf`, `x ** 2`, `math.exp`, `math.log` | libm's `erf`, `pow`, `exp`, `log` | CPython calls the C library for these, so the Rust does too. On macOS `pow(x, 2)` isn't always `x * x`. |
| `math.fsum`, `statistics.fmean`, `random.sample` | `fsum`, `fmean`, `sample` in `src/stats.rs` | Shewchuk's partials as `mathmodule.c` has them; `sample`'s two branches as `Lib/random.py` |
| `sum()` of floats, and of ints and floats mixed; `round(x, n)`, `//`, `max`/`min`; numpy's `mean`, `std` | `src/py.rs` | CPython 3.12's `sum` is compensated (Neumaier), not a plain loop, and adds ints after the first float uncompensated; numpy's sums are pairwise from 0.0. Each checked against the real thing on random inputs, and `cargo test` holds CPython's vectors |
| an exception in `Trader.run` | `Bot::failed` | the twin reports the traceback's last line, word for word (`KeyError: 'SQUID_INK'`, `ValueError: min() iterable argument is empty`, NameError's "Did you mean"), and the engine drops the tick's orders and records it, as `_call_bot` does. The twin keeps what the Python keeps: traderData as last returned, the instance's changes up to the error |
| what an experiment reads from a bot's traderData | `Bot::memory` | the template's: which products' loss stop fired (`experiments/sim_regimes.py`) |

**Only in Python**:
- the format plug-ins (`arena/formats/`), which load the data;
- `arena.validate`, which checks the Python file itself;
- everything in `arena.grid` but the backtests and the heavy statistics: the axes, screening, the permutation test's shuffles (`arena.stress.permute`, 0.09 s a day), held-out days, and the DSR's own formula;
- `arena.analysis`, `arena.diagnose`, `arena.stress`'s perturbations, and `arena.report`'s CSVs (written from the results Rust hands back);
- `experiments/p4_levels.py` (other teams' bots, which have no twins) and `format_drill.py` (three simulated days);
- `arena.sim`'s specs, presets, `--spec` overrides and regimes, and its command line, which prints from the results Rust hands back;
- `bots/probe.py`, the zoo's tooling (`bundle.py`, `local.py`), and `experiments/`.

`arena/rust.py` is the bridge. It exports days, turns a twin's Python file into its Rust bot's settings (`bot_spec`, with any `--set` overrides), runs `arena-rs run`, `batch`, `sim` and `stats`, and reads what Rust writes back as Python's own `Day` and `DayResult` (`read_day`, `read_results`), so the reports and CSVs work unchanged. A Rust bot has no step timings, so a report from Rust leaves out the "bot time per tick" line (and `experiments/zoo.py` its slowest-tick column).

Every tool that runs our bots takes `--engine rust`: `arena.backtest`, `arena.grid`, `arena.compare`, `arena.stress`, `arena.sim`, and the experiments, which go through `arena.cli.backtest` (one market on one day on either engine; `fields` limits what is read back, `arena.rust.sim_day_file` has Rust write a simulated day straight to a file).

**Only in Rust**: the day-file reader (`src/dayfile.rs`, for days `arena/rust.py` exports after the plug-ins have loaded them), the thread pool of `arena-rs batch` and `grid`, SHA-512 (string seeds, as CPython hashes them), and a JSON reader.

## Layout

| File | What it is |
|---|---|
| `src/engine.rs` | the engine (above) |
| `src/model.rs`, `src/dayfile.rs` | the types, and the exported day format (version 3: with the limits' order and `Day.info`'s ticks) |
| `src/sim.rs` | arena.sim's market (above), and its Prosperity CSVs |
| `src/bots/` | the twins; `mod.rs` builds one by its kind (`rust/twins.json`) from its Python file's globals; `zoo/` holds the zoo's |
| `src/stats.rs` | the grid's statistics (above) |
| `src/py.rs` | Python's arithmetic where it isn't IEEE's plain operations |
| `src/pyrandom.rs`, `src/sha512.rs`, `src/json.rs` | Python's random numbers, its string seeding, and the settings' format |
| `src/main.rs` | `arena-rs run` (one market; `--dump` writes every recorded field, a JSON line per participant), `batch` (arena.grid's backtests on N threads), `sim` (arena.sim's market on N seeds at once, its replays and files), `stats` (the grid's statistics), `grid` (`mm`'s make × take grid, for timing) |

## What is and isn't ported

- **The engine.** Ported: every rule in `arena/engine.py`'s docstring, in the same order of operations. Not ported:
  - order tags (a format's own ids);
  - a bot's exceptions, prints and step timings;
  - fractional prices (the day file holds whole prices, as Prosperity's are; a format with decimal prices loads them as whole units, as the drill's does);
  - CPython's own `lgamma`: `binomialvariate` calls the C library's. They differ by a few ulps, which could flip a fill-ratio draw only when its test lands that close to the bound.
- **The template.** Ported: all of STRATEGY and EXECUTION. Not ported: `STRICT`, and the per-product try/except (a Rust bot can't raise). Settings that the Python would only fail on while running are refused when the bot is built, so its grid cell fails before it starts. That covers an unknown key, an unknown fair method, and a float where an integer is needed (`limit`, `target`, `make_size`, `cpd_block`).
- **A bot's state across ticks.** The Python bots keep it in `traderData` as JSON. The Rust ones keep the same values in fields, which is equivalent because JSON gives every float back exactly.

## Keeping it in step

1. Change the rule or the strategy in Python, and port the change to the file `rust/twins.json` names.
2. Run `uv run python -m experiments.rust_bench --parity-only --record`. It compares every recorded field in every case, and records the new hashes only if every case is identical.
3. Run `uv run pytest tests/test_rust.py`.

Python files without a Rust twin need nothing. `arena.grid --engine rust` refuses a bot without a twin, and warns when a twin's hash is stale.

A new twin needs four things:
- a Rust file under `src/bots/` (a new format's template: another adapter in `src/bots/template.rs`, as `Template::drill`);
- a kind in `src/bots/mod.rs`;
- a row in `rust/twins.json` (with `"format"` if it isn't Prosperity's) and in the table above;
- cases in `experiments/rust_bench.py`, run by `tests/test_rust.py`.
