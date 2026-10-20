# rust/: the engine in Rust, for benchmarking

A Rust port of `arena/engine.py` and one bot, kept apart from the Python code. It answers how much
faster a backtest gets in a compiled language, like for like (TODO.md, the decision "Rewrite the
engine and the strategies in a fast language for huge sweeps?"). It's an example and a
measurement, not part of the toolchain: nothing in `arena/` uses it, and the submitted bot stays a
Python file.

```sh
brew install rust                                  # or rustup; any recent stable toolchain
uv run python -m experiments.rust_bench            # build, check parity in 15 configurations, then time both engines
uv run python -m experiments.rust_bench --parity-only
uv run pytest tests/test_rust.py                   # the parity check on an arena.sim day, and `cargo test`
```

## Layout

| File | What it is |
|---|---|
| `src/engine.rs` | `run_market` / `run_day` ported function for function, with the Python names (`_take` is `take`, `_cross` is `cross`, ...). Both modes, the three queue models, the fill ratio, several bots in one market, every per-tick record of a `DayResult`. |
| `src/model.rs` | `arena/model.py`'s types. Products are indices into the day's product list, sorted by name; trader names are indices into its name table. |
| `src/pyrandom.rs` | Python's `random.Random` (MT19937, int and str seeding, `random`, `shuffle`, `binomialvariate`), draw for draw, so seeded runs match. |
| `src/sha512.rs` | For seeding from a string, as Python does. |
| `src/dayfile.rs` | Reads a day exported by `experiments/rust_bench.py` (`export_day`). The format plug-ins stay in Python; this is the engine's input, after them. |
| `src/bots/mm.rs` | The one bot: a wall-mid market maker. Its Python twin is `bots/mm.py`; keep the two equal. |
| `src/main.rs` | `arena-rs run` (one market, `--dump` writes every recorded field for the parity check) and `arena-rs grid` (a make_edge × take_edge grid on N threads, for timing). |

## What is and isn't ported

Ported: every rule in `arena/engine.py`'s docstring, with the same order of operations, so the
parity check compares fills, orders, cancels, breaches, races, errors and each tick's position,
mark, PnL, best bid and ask and wall mid exactly.

Not ported:
- **Order tags.** They're a format's own ids.
- **A bot's exceptions, prints and step timings.** A Rust bot can't raise or print into the result.
- **`begin_day`'s per-product info.**
- **Fractional prices.** The day file holds whole prices, as Prosperity's are.
- **`lgamma`.** `binomialvariate` calls the C library's, where CPython has its own. They differ by a few ulps, which could flip a draw only when its test lands that close to the bound.

## Keeping it in step

A change to the engine's rules in `arena/engine.py` goes into `src/engine.rs` too, and a change to
`bots/mm.py` into `src/bots/mm.rs`. `tests/test_rust.py` fails until both agree.

A second Rust bot needs two things: a Python twin under `bots/`, and a `--bot` syntax in
`src/main.rs`. The parity check (`experiments/rust_bench.py`, `parity`) then works for it unchanged.
