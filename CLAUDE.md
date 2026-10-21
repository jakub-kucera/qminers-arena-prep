# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Prep tooling for the Qminers Algo Trade Arena, a 24-hour in-person hackathon (7–8 Nov 2026). It
has four 5-hour rounds, and teams submit a Python bot file at the end of each one. The real API
won't be known until the event, so everything here runs on **IMC Prosperity data and its bot
format as a stand-in**. Keep competition-specific code isolated so it can be swapped quickly on
the day (see "Formats" below).

## Commands

```sh
references/clone.sh                 # fetch the reference repos + Prosperity data at their pinned commits (gitignored, ~2 GB)
uv sync                             # Python 3.12; dev group = pytest, pandas, matplotlib
uv run pytest                       # all tests (~90 s; tests/test_rust.py's parity checks are most of it)
uv run pytest tests/test_engine.py::test_trade_matching_at_the_same_price   # one test

uv run python -m arena.diagnose 1 --data p4                       # per-product market diagnostics, no bot needed
uv run python -m arena.backtest bots/template.py 1                # Prosperity 3 round 1, every day
uv run python -m arena.backtest bots/template.py 1-0 --data p2    # Prosperity 2, round 1 day 0
uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2 --out results/
uv run python -m arena.backtest bots/template.py 1 --resting --vs bots/template.py   # orders rest; a rival copy shares the market
uv run python -m arena.backtest bots/template.py 1 --engine rust   # the same report and CSVs, on rust/ (compare, stress, sim and the experiments take it too)
uv run python -m arena.validate bots/template.py 1                # pre-submission checks, exit 1 on FAIL
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..3 --modes all,worse --out results/grid.csv
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..7 --grid PARAMS.KELP.take_edge=0..7 --modes all,worse --screen 0.25   # big grids: screen on the first day, the best quarter on all
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..15 --grid PARAMS.KELP.take_edge=0..15 --engine rust   # the same output, its backtests on rust/ (a bot with a Rust twin)
uv run python -m arena.compare bots/template.py 1 --bot bots/zoo/claude/*.py "bots/template.py@PARAMS.KELP.make_edge=1" --modes all,worse   # several bots or variants against a baseline
uv run python -m arena.analysis results/                          # PNGs to results/plots/ + fill/markout tables
uv run python -m arena.stress bots/template.py 1                    # the bot on perturbed days (trend, shift, spike, vol x2, no wall)
uv run python -m arena.sim generate data/sim --days 5              # simulated days in the Prosperity layout (--data data/sim)
uv run python -m arena.sim run bots/template.py --days 5           # the bot inside the agent market, against replaying the same days
uv run python -m arena.sim run bots/template.py --products KELP,RAINFOREST_RESIN,HYDROGEL_PACK --regime trend_up   # a mid-day regime change, in a market that reacts
uv run python -m arena.sim run bots/template.py --days 20 --engine rust   # the same output, the market in rust/src/sim.rs (generate takes it too)
uv run python -m arena.backtest bots/probe.py 1 --print --no-strict   # the probe bot: one PROBE line per first-hour probe
uv run python -m experiments.format_drill data/drill               # drill-format data, then any tool with --format drill --data data/drill/drill
uv run python -m experiments.format_drill --sync                   # copy the template's DEFAULTS, STRATEGY and EXECUTION into bots/drill/template.py
uv run python -m arena.analysis --grid results/grid.csv           # grid heatmaps
uv run --group analysis jupyter lab notebooks/analysis.ipynb      # the analysis group adds Jupyter
uv run python -m experiments.p4_levels                            # a one-off study; its numbers are in IDEAS.md
uv run python -m experiments.zoo                                  # scores every LLM-written bot in bots/zoo/ against the template (--local: local models in the field too)
uv run python -m experiments.zoo_h2h                              # the template against each zoo bot, per product, under all and worse
uv run python -m experiments.adversaries                          # the template against a trapper, spoofers and a sniper (bots/rivals/), --resting
uv run python -m experiments.undercut                             # the template against a copy of itself at make_edge 0 (Wang et al.), per tick and --resting
uv run python -m experiments.quote_size                           # make_size caps against rivals: a copy, the trapper, spoofer and sniper
uv run python -m experiments.p3_smile                             # P3's volcanic vouchers: the smile by held-out days, its residual, and the template's smile fair traded on it (~3 min)
uv run python -m experiments.imbalance                            # does the best-level imbalance predict the mid / the wall mid, per product and day
uv run python -m experiments.sim_regimes                          # the template's stops and guards under each arena.sim regime change
uv run python -m experiments.snooping_tests                       # Hansen's SPA and Romano-Wolf's StepM next to the grid's DSR, on two grids and null controls
uv run python -m experiments.selection_rules                      # ten ways of picking a grid cell, scored on days the grid never saw
uv run python -m experiments.selection_rules_sim                  # the same rules on fresh arena.sim days, tuned on 3 and scored on 20
uv run python -m experiments.rust_bench                           # the Rust port (rust/, needs cargo) against ours: every twin's parity, then speed
uv run python -m experiments.rust_bench --parity-only --record    # after changing a twin (rust/twins.json): check it, then record its hash
```

- **Day specs:** `ROUND` (every day in the round) or `ROUND-DAY`, e.g. `1`, `1-0`, `1--1`.
- **`--data` aliases:** `p2` and `p3` point into `references/prosperity{2,3}-backtester-jmerle/.../resources`, `p4` into `references/prosperity4-backtester/prosperity4bt/resources` (rounds 0–5).
- **Tests without the data:** `tests/test_parity.py` skips if `references/` hasn't been cloned. All other tests use a tiny CSV fixture from `tests/conftest.py`.
- **Notebook check:** `uv run --group analysis jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output-dir <scratch>` runs it end to end. Commit the notebook without outputs.
- **No linter or formatter is configured.**

## Architecture

**The engine doesn't know any format.**
- `arena/model.py` defines the internal types: `Book`, `Tick`, `Day`, `Order`, `Cancel`, `OpenOrder`, `Fill`, `MarketTrade`. Order and fill quantities are signed; book volumes are positive. `Order.tag` (a bot API's own order id) is copied, unread, to the order's `OpenOrder` and `Fill`s. `Day.info` holds a format's per-product metadata (e.g. tick sizes); `run_market` and `arena.sim` hand the day to any bot with a `begin_day(day)` method before the first tick.
- `arena/engine.py` `run_day(day, bot, config)` replays a `Day` against any object with `step(tick, positions, own_fills, market_trades, open_orders) -> list[Order | Cancel]`.
- It records per-tick positions, marks, PnL and best bid/ask, plus orders, fills, errors, limit breaches and timings, in a `DayResult`.
- `arena/report.py` `write_csvs` turns it into `<day>_timeline.csv` (with the book's `wall_mid`), `_fills.csv`, `_orders.csv` and `_trades.csv` (the data's market trades). Those columns are the contract with `arena/analysis.py`, so change both together.
- **Only `arena/analysis.py` imports pandas and matplotlib.** Everything else is standard library.
- **`arena/diagnose.py`** reads days through the format plug-in, with no bot or engine. Per product, it prints the spread regime, noise, drift, and the market trades' impact and market-making margins. Its notes use thresholds calibrated on Prosperity data, as module constants. `references/wiki/concepts/reading-the-data-on-day-one.md` maps each note to a strategy choice, so change both together.
- The engine catches the bot's exceptions and records them per tick, so a run never aborts.

**Formats are plug-ins** (`arena/formats/`). A format module must provide:
- `PROVIDED_MODULES`
- `resolve_data_dir`
- `load_days`
- `load_bot`
- `check_source`

It is registered in `arena/formats/__init__.py` `FORMATS`, and may set `RESTING = True` if its orders rest until cancelled (the CLI then runs as with `--resting`). There are two formats. `drill.py` is a practice format deliberately unlike Prosperity's (decimal prices in integer cents, `Day.info` tick sizes, a `Bot.on_tick(api)` callback, opaque order ids through `Order.tag`), and the one to copy on the day; `bots/drill/template.py` is the template with only its imports, PARAMS and ADAPTER rewritten for it, and `tests/test_drill.py` checks that the rest matches `bots/template.py` word for word and that both make the same PnL on the same days. `prosperity.py` holds:
- **The CSV loader:** `;`-separated. Prosperity 2 trade files have `_wn`/`_nn` name variants.
- **The `LIMITS` table:** the loader raises on any product without a limit.
- **`ProsperityBot`:** it builds a `TradingState`, calls `Trader().run(state)`, type-checks the returned `(orders, conversions, traderData)`, and converts the orders.

`prosperity_datamodel.py` is our own copy of IMC's `datamodel` module, without jsonpickle. On the day, the plan is to add `arena/formats/qminers.py`, modelled on `drill.py`. When `bots/template.py`'s DEFAULTS, STRATEGY or EXECUTION change, run `uv run python -m experiments.format_drill --sync` to copy them into `bots/drill/template.py` (`tests/test_drill.py` fails until you do).

**Bot loading** (`arena/botfile.py`). `BotFile` compiles the bot source once. Each `load()` execs it into a fresh module, then:
- **Injects provided modules:** the format's modules go into `sys.modules`, so `from datamodel import ...` resolves to ours.
- **Sets `STRICT = True`:** only in strict mode, and only if the bot defines `STRICT`.
- **Applies `--set` overrides:** `GLOBAL.key.key=literal`. Missing intermediate keys raise `OverrideError`; a new leaf key is allowed.

The validator's `fresh_each_tick` mode reloads the module every tick to catch state kept outside `traderData`.

**Matching rules (Prosperity semantics):**
1. The bot quotes against the current tick's book.
2. If a product's orders could breach its position limit (all buys, or all sells, filling), every order for that product is cancelled.
3. Each order matches the visible book at the book's prices.
4. What's left matches that tick's market trades at the order's own price. `--match-trades all|worse|none` controls which trades qualify.
5. Everything unfilled is cancelled. Nothing rests between ticks.

**Resting mode** (`--resting`, `EngineConfig.resting`) replaces rule 5. The module docstring of `engine.py` has the full rules.
- **Resting:** unfilled orders rest until filled or cancelled, unless `Order.ioc`. Each one queues behind the visible volume at its price.
- **Queue models** (`--queue`, `EngineConfig.queue`): `back` (default) moves an order up only as far as the visible volume forces; `prob` splits unexplained drops by the share ahead to the power `--queue-power` (hftbacktest's); `front` puts it ahead of everyone after one snapshot (they re-post every tick). Each `_Live` keeps `seen` and `traded` for `prob`.
- **Trade fills:** trades at its price first use up the queue ahead of it; trades through its price fill it.
- **Book fills:** a next snapshot that crosses it fills it at its own price (`Fill.source == "cross"`), and the bot sees that snapshot minus the volume. That tick's market trades at the crossed prices lose the same volume (`_spend_crossed`), so the order can't fill from the same orders twice.
- **Bot interface:** `Bot.step` gets `open_orders` (always empty in the default mode) and may return `Cancel(order_id)` among its orders. The Prosperity format exposes these as datamodel extensions: `state.open_orders`, `Cancel`, `Order(..., ioc=True)`.
- **The default path doesn't change:** resting-mode code lives in its own branch of `run_day` and in the helpers below the "resting mode" marker. Parity only covers the default mode.

`--fill-ratio` thins out liquidity with binomial draws, seeded and independent of the bot's orders, so variants of a bot can be compared fairly.

**Shared market** (`run_market(day, [(name, bot), ...], config)`, CLI `--vs BOT`):
- **One engine:** `run_day` is `run_market` with one participant. Every helper works on `_Live` orders carrying an `owner`, and fills are routed to their owner by `order_id`.
- **Arrival:** all bots see the same tick and decide at once. Their actions are then processed in a seeded shuffle, drawn from its own random stream so the `--fill-ratio` draws don't depend on the number of bots.
- **Matching:** `_take` matches a new order against the recorded levels and other owners' working orders, best price first. At one price the recorded volume goes first. Each bot's book (`_seen_by`) adds the others' resting orders, never its own.
- **Breaches vs races:** limits are checked twice. Orders that don't fit the position the bot saw are `limit_breaches`, the bot's bug. Orders that fitted but don't fit after another bot's fill are `races`. Both are rejected, but the grid only discards combinations with breaches.
- **CLI:** `arena.cli.run_with_rivals` loads the bot and its `--vs` rivals and runs them, for both the backtest and the grid. `--set` only applies to the main bot.
- **The teams' Prosperity bots as rivals:** they were written for orders that live one tick and never cancel, so in `--resting` their orders pile up until they breach limits. `--requote` wraps every rival (`arena.cli.Requote`) to cancel its open orders before each tick. Some import jsonpickle: `uv run --with jsonpickle ...`.

**Simulated market** (`arena/sim.py`): an agent-based market with its own price-time book, separate from the engine (the engine is untouched, so parity is too).
- **Agents per product:** a fundamental, a market maker quoting walls (optional inventory skew), limit traders, then, after the snapshot and the bots, noise, value and momentum takers. That order is what a Prosperity tick implies, so a recorded day replays with the same semantics.
- **Seeding:** one generator per product and agent kind, ABIDES's rule; each arrival makes the same draws whatever the book shows, so a run with a bot and the recording without it share every random number.
- **Bots:** the same `Bot` protocol and `DayResult` as the engine, both modes (default: an order lives for that tick's takers; `--resting`), `--vs`. It reuses `engine._breaches`, `_call_bot`, `_known`, `_new_result`, `_record`.
- **Presets** are calibrated through `arena.diagnose`, and `tests/test_sim.py` holds the bands. `KELP`, `RAINFOREST_RESIN` and `SQUID_INK` copy P3 round 1 and are the default market. `HYDROGEL_PACK` copies P4's Hydrogel (an Ornstein–Uhlenbeck fundamental), `KELP_FLOW` is Kelp with P3's one-sided takers (35% buys, `NoiseTakers.sell_size` and `persistence`), and `ROBOT_DISHES` copies P4 round 5's jumping day (jumps of 100 in bursts that mostly reverse: `jump_excite`, `jump_decay`, `jump_reverse`); they are chosen with `--products`. New fields draw random numbers only when set, so the older presets' days don't change. `write_day` writes the Prosperity layout plus `limits.json`, which the Prosperity loader merges into `LIMITS`.
- **Regimes:** `with_regime` (`--regime`, `--regime-at`) shifts or trends every product's fundamental and its level from mid-day, sized in its wall spread. The morning keeps the same draws, so it is the same day until the change.
- **Formats:** `run --format` loads the bots through any format plug-in. The market's prices are whole ticks, and `begin_day` gets a day with no `info`, so a decimal-price format sees them in its price unit.
- **Rust** (`--engine rust`): `rust/src/sim.rs` is the market's twin, the same to the bit; `generate` writes the same files and `run` prints the same, but for the bot-timing line. `arena/rust.py` `run_sim` runs seeds on threads and returns each bot's totals (PnL per product, fills, errors) in the market and its replays, or, with `read`, the SimDays and DayResults (reading them back costs more than the run).

**Stress harness** (`arena/stress.py`): `permute(day, seed, block)` (for the grid's permutation test) is separate from the perturbations. Each perturbation (volatility ×2, a trend, a mid-day shift, a spike, the walls removed) moves a product's whole book, its trades and its mark by one offset per tick. Offsets are sized in the product's median spread and kept on its tick grid (the gcd of the gaps between its prices), so a format with a tick coarser than its price unit stays on the grid.

**Grid search** (`arena/grid.py`):
- **Parallel runs:** `_Runner` keeps one `ProcessPoolExecutor` for a run, with one task per (combination, day, mode) (`_run_piece`, a `Piece`), and `_assemble` adds the pieces into each `Outcome`, days in order. Each worker loads the days once, in `_init_worker`, into the module-level `_WORKER` dict. `--jobs 1` runs in-process.
- **Only the axes' products:** when the axes set only some products (`axis_products`), the bot as is runs on full days and on days holding only those (`only`). If their PnL agrees on every day and mode, every combination runs on the smaller days and gets the other products' PnL, blocks and fills from the bot as is's run (`_difference`), so the summary is what a full run prints. `--all-products` turns it off.
- **Smoke test:** before the pool starts, a 200-tick run of the first combination makes typos fail fast.
- **Ranking:** combinations are ranked on `pnl`, `min day`, `nbhd` (mean over the combination and its one-step grid neighbours) and the PnL under each extra mode. The summary flags when these measures disagree.
- **Screen** (`--screen SHARE`, successive halving with one rung): every combination on the first day under the first mode (`screened`), then only the best share on every day and mode; `GridRun.outcomes` holds only the kept cells and `GridRun.screen` the rest. `format_screen` says what was dropped; `format_unseen` repeats SPA, StepM and the pick without the first day (`without_first_day`). `run_permutations` screens each copy the same way.
- **Rust engine** (`--engine rust`, `Setup.engine`): `_Runner._rust` sends each batch to `arena-rs batch` (`arena/rust.py`, `run_batch`) instead of the pool, and the statistics go to `arena-rs stats`. Each day (restricted, permuted) is exported once per run, and each combination's settings are read from the bot file once (`bot_spec`). It returns the same `Piece`s. `rust.prepare` refuses a bot or rival without a Rust twin for the run's format (`rust/twins.json`'s `format`: the drill template's is drill) before the smoke test.
- **Permutation test** (`--permute N`, `--permute-block`): the whole grid reruns under the first mode on N copies from `arena.stress.permute` (the days' own ticks shuffled in runs, each shifted to continue by its real wall-bid move), and the real search's best PnL and its lift over the median cell, on the products the axes set, are ranked among the copies' (`format_permutations`).
- **SPA, StepM and the pick:** each cell's PnL is also kept per block of `FINE_TICKS` (100) ticks for Hansen's SPA test and Romano and Wolf's StepM (stationary bootstrap, `SPA_Q`, `BOOTSTRAP`). StepM's cells are checked under every `--modes` entry, and the summary's `pick` is the best that beats the bot as is under all of them (`format_snooping`).
- **Held-out days:** with two or more days, `leave_one_day_out` scores each day with the best combination by PnL on the other days, from the per-day PnL already collected (no extra runs). `repeated_days` flags days that share a product's books and trades (ignoring counterparty names): Prosperity reuses days across rounds.
- **Overfitting:** each run's PnL is also kept per block of ticks (`block_pnl`, about `BLOCKS` = 16 over the days, never straddling one). `format_overfitting` prints the trial count, `cscv`'s PBO (Bailey et al., sampled to `MAX_SPLITS` halvings) and `deflated_sharpe` of the best cell's gain over the baseline (the bot with only `--set`), with `independent_trials` from the gains' average correlation. Both formulas were checked against the PDFs; `tests/test_grid.py` reproduces the DSR paper's worked example.
- **The statistics live in `arena/stats.py`** (`cscv`, the DSR's helpers, `omega2`, `bootstrap_means`, `spa`, `stepm`, and `snooping`, SPA and StepM on one bootstrap); `arena.grid` re-exports the names. `rust/src/stats.rs` twins the ones that grow with the cells (`cscv`, `mean_correlation`, `snooping`), and `--engine rust` runs those there: 4,096 distinct cells take 1.9 s against 21.9 s.

**Bot comparison** (`arena/compare.py`): several bot files or `FILE@PATH=VALUE` variants against the first bot as baseline, one pool task per (bot, day, mode). Each bot becomes an `arena.grid.Outcome` under a one-value `Axis("bot")`, so the grid's held-out days, PBO, DSR, SPA, StepM and pick apply unchanged.

**Rust port** (`rust/`, its own Cargo crate, kept apart from the Python code; `rust/README.md` has the table of what is in Python, Rust and both):
- **Twins:** `rust/src/engine.rs` ports `arena/engine.py` function for function, with the Python names, `rust/src/sim.rs` the market of `arena/sim.py`, and `rust/src/stats.rs` the heavy statistics of `arena/stats.py`. `rust/src/bots/` ports `bots/template.py` (all of STRATEGY and EXECUTION, and ADAPTER as the Prosperity plug-in presents a tick; `bots/drill/template.py` is the same core behind the drill ADAPTER, `Template::drill`), `bots/rivals/`, `bots/mm.py` and every zoo bot (`rust/src/bots/zoo/`, with exceptions reproduced by `Bot::failed`, message and all). `rust/src/py.rs` holds Python's arithmetic where it isn't IEEE's (`sum`, `round`, numpy's `mean`/`std`).
- **`rust/twins.json`** lists each pair with the hash of the Python file as last checked. `tests/test_rust.py` fails when one changes. **A change to a twin's Python file goes into its Rust file too**, then `experiments.rust_bench --parity-only --record` compares every recorded field in every case and records the new hash.
- **The bridge** (`arena/rust.py`):
  - days are loaded by the Python format plug-ins; a Prosperity day goes to Rust as a reference to its own CSVs, which `rust/src/prosperity.rs` reads as the plug-in does (`write_day`, `prosperity.reference`; the plug-in remembers each day's files while it lives), and any other day is exported (`export_day`; format in `rust/src/dayfile.rs`, products sorted by name plus the Python order, since order ids depend on it);
  - a Rust bot reads its settings from its Python file's upper-case globals after `--set` (`bot_spec`);
  - what Rust writes comes back as Python's own `Day` and `DayResult` (`read_day`, `read_results`; results as JSON lines), so the reports work unchanged;
  - every tool that runs our bots takes `--engine rust` (`arena.cli.add_engine_argument`); the experiments run each backtest through `arena.cli.backtest(day, participants, config, engine, fields=...)`, setting the engine in their workers with an `_init`; on Rust a worker that only backtests on a Prosperity day takes `arena.cli.backtest_days` or `arena.rust.prosperity_day`/`named_day` (Rust reads the CSVs, nothing is loaded in Python).
- **Exact floats:** `rust/src/pyrandom.rs` reproduces Python's `random.Random` draw for draw (`gauss` included), and the template calls libm's `erf`, `exp`, `log` and `pow` as CPython does (`x ** 2` is `pow`, not `x * x`), so the PnL matches to the bit.
- `tests/test_rust.py` is skipped without `cargo`, except the hash check.

**Analysis** (`arena/analysis.py`):
- **No pyplot:** charts are `Chart` objects, a `Figure` subclass with `_repr_png_`, so they display in notebooks and save from the CLI without pyplot. Each `Chart` keeps the rc params of the theme it was drawn in.
- **Palette:** `THEMES` holds palettes checked with the dataviz skill's validator. Keep categorical colors in slot order.
- **Product colors:** `Run.colors` gives each product the same color in every chart of a run. It covers the `MAX_SERIES` products with the largest |PnL|; charts fold the rest into "other".
- **Fill edge:** measured against the **arrival mid**, one tick before the fill. A taken order is part of its own tick's book and skews that tick's mid.
- **Markout horizons start at 1 tick**, for the same reason.
- **Reference price:** fill edge, markouts and `pnl_split` take `reference="mark"` (default) or `"wall_mid"` (`Book.wall_mid`, carried over ticks with an empty side). `pnl_split` adds up to the engine's PnL exactly for either.
- **`trade_impact`:** per product and reference, the taker's edge and the signed move after the data's market trades. A tick's trades are classified against that tick's book. Pass a list of runs to pool days.

**Parity with prosperity3bt is pinned.** The engine matched jmerle's prosperity3bt 0.12.0 fill for fill. `tests/test_parity.py` (needs `references/`) asserts fill counts and PnL for `tests/fixtures/parity_bot.py`.
- **Engine changes:** any change to matching, limits or marking must keep this test passing.
- **The fixture:** it is a frozen snapshot. Don't edit it, even when `bots/template.py` changes.
- **PnL conventions differ:** ours is marked after each tick's fills. prosperity3bt reports final PnL before the last tick's fills, and the test converts between the two.

## Bot files (`bots/`)

The competition runs one file, so a bot must stay **self-contained, standard library only, and keep all
cross-tick state in `traderData`**. The real engine may not keep instance or module variables
between calls.

`bots/template.py` has five sections:
- **PARAMS:** `DEFAULTS` plus a per-product dict. Products not listed aren't traded. Unknown keys raise, which catches typos.
- **STRATEGY:** format-agnostic. Fair value (fixed, mid, `wall_mid`, `outer_mid`, `sized_mid` or `weighted_mid`; `sized_mid` survives rivals' resting orders) → take → clear → make, the last three around the fair plus `imbalance` × the best-level imbalance (off by default). `clear`, `skew` and `size_skew` work inventory toward `target` (default 0; a long target holds with a steady drift). With `level` set, `level_target` replaces `target`: the full limit against a move of `level_band` from a price the product returns to. `cpd_*` adds online changepoint detection on that level (`changepoint_level`; dropped on Prosperity data, off by default). `flatten_from` works every position to zero before the close (target 0, no takes, `reduce_only` quotes). With `follow` set, `follow_target` makes a call option hold its underlying's target as a share of its own limit (Black–Scholes helpers in total variance, so no expiry is needed). With `smile` set, `smile_fair` prices a call off its `underlying` instead: Black–Scholes at a fitted smile in `m = ln(K/S)/√T` (needs `expiry`), plus an EMA of the call's offset from it, and take/clear/make trade around that. A product with `basket` trades its spread against its legs with the level settings, and legs with `hedge` take what the baskets ask of them (`Plan.legs`). With `jump_min` set, `jump_target` holds the full limit against each jump once enough of the day's jumps have reversed (a gate measured on the day, so it can run on every product), crossing up to `jump_edge`. With `copy` set (`{name: weight}`), `copy_target` holds the weighted direction of the named traders' last trades, from `Market.trades`, which the ADAPTER fills from both `market_trades` and our own fills' counterparties. `stop_loss` (per product, about 3× its plain-day drawdown from `arena.stress`) flattens and stops a product for the day; `fixed_guard` lets a fixed fair give way to the sized mid; `level_guard` and `vol_guard` exist but are off. The cross-product hook is `Market`: every product's book, and this tick's `Plan`s so far. `Trader.run` trades products that `follow` or `hedge` another after it (one level of dependency). `Plan` keeps all orders inside the full room under the limit, counting buys and sells separately. It holds `takes` (take, clear) and `quotes` (make) apart.
- **EXECUTION:** format-agnostic. `execute(plan, resting)` returns cancels and new orders:
  - takes are sent as IOC
  - a resting quote is kept while a quote on its side and price still wants at least its size
  - everything else is cancelled

  ADAPTER passes the resting orders oldest first: `execute` doesn't sort them, since a format's ids needn't grow with age.

  The engine applies cancels before the limit check, which is why planning with the full room is safe. With nothing resting, it sends the whole plan, so one file works in both engine modes.
- **ADAPTER:** the only Prosperity-specific code, including the resting extensions (`state.open_orders`, `Cancel`, `ioc`).
- **`Trader.run`:** a try/except per product, swallowed unless `STRICT`. A product that errors cancels its resting orders.

`bots/rivals/` holds adversarial `--vs` rivals for `--resting`: a quote-matching trapper, a spoofer (`OFFSET` ticks behind the best) and a sniper of stale quotes.

`bots/zoo/` holds bots written blind by language models from `bots/zoo/SPEC.md` and `PROMPTS.md`: the agent baseline and `--vs` rivals. Never edit a zoo bot or a prompt once used; its README has the protocol for adding other providers' bots. Each zoo bot has a Rust twin (`rust/src/bots/zoo/`), and `tests/test_rust.py` fails until a new one has its own.

New strategy logic goes in STRATEGY, order-management changes go in EXECUTION, and format changes go in ADAPTER. `bots/datamodel.py` only
lets editors resolve imports; it is never submitted. `bots/probe.py` runs `ON_THE_DAY.md`'s probes in a schedule of tick windows and prints a `PROBE` line per finding and a `SEEN` line per tick (Prosperity format; only its ADAPTER, `PRODUCT` and `LIMIT` change on the day); `tests/test_probe.py` checks its findings against the engine's known behaviour in both modes.

## Known gaps (from README)

- **The queue model is an estimate.** `--queue back` (default) and `front` bracket it; `prob` can't see a level re-posted at the same size.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **Rivals are only the bots you bring** with `--vs`. Real teams will behave differently.

## Repo conventions

- **`TODO.md`:** prep work left before the event, each item with a "done when". Tick items off when that holds, and add new ones as they come up.
- **`ON_THE_DAY.md`:** the checklist of what to find out about the real Arena. For each item it gives our current assumption and what to change if the Arena differs, and it ends with playground probes. When a session learns an answer, write it in under that item with its source. When a session adds an assumption about the real format, add an item.
- **`IDEAS.md`:** every strategy idea tested on Prosperity data, with its result (date, data, command, numbers), and the ideas not yet tested. Results there are priors for the Arena, not verdicts: never remove an idea because it failed on Prosperity data; mark it `dropped here`, so it is re-tested on the day. Record every new test result in its row.
- **`MANUAL_TODO.md`:** things only a person can obtain (organiser documents, web pages the agent's fetch tool is blocked from, books). Each item says where to save the file and what "done" means. When the user hands something over, ingest it as `references/wiki/SCHEMA.md` describes and tick the item.
- **Nothing stays only in the chat.** Before ending a task, file what it turned up, in the same commit as the work:
  - prep work or a follow-up → `TODO.md`, with a "done when"
  - a new idea or a test result → `IDEAS.md`, with what to re-test on the day
  - a question about the real Arena, or advice for the day → `ON_THE_DAY.md`
  - something only a person can obtain → `MANUAL_TODO.md`
  - a choice only the user can make → `TODO.md`, "Decisions", with the options, the evidence and a recommendation

  When asked what to do next, start from the open items in `TODO.md` and the untested rows of `IDEAS.md`.
- **Results reproduce from the repo.** The command given for a result in `IDEAS.md` or the wiki runs from a clean checkout: a CLI with `--set`, or a script committed under `experiments/` along with the result. A scratchpad path is not a command.

- **`references/`:** third-party clones listed in `references/clone.sh`, each pinned to a commit (`tests/test_references.py` checks). Read them for ideas, but don't edit or import from them. Move a pin only with `clone.sh --update`, then the lint and the tests.
  - `references/algotrade2026-pitfa19/` contains its own `CLAUDE.md` and `AGENTS.md`. They describe that repo, not this one, so don't follow them.
  - `references/README.md` summarises what each repo is useful for.
  - **`references/wiki/` is the way into the clones and the literature.** It follows Karpathy's LLM-wiki pattern: read `references/wiki/index.md` first, then a concept page, then the source page, and only then the raw file at the cited line. Pages cite code as `path:line`, say what is a team's claim and what was checked, and say what was not read. `references/wiki/SCHEMA.md` has the conventions and the ingest / query / lint workflows. After editing the wiki run `python3 references/wiki/lint.py`; log changes in `references/wiki/log.md`.
  - **Pages cite `bots/template.py` by line,** and the lint only checks that the line exists. After an edit shifts the template's lines, re-map those citations (`grep -rn 'template\.py:[0-9]' references/wiki`).
- **`literature_md/`:** market-microstructure papers and books, converted from `literature_raw/*.pdf` to markdown by `literature_md/convert.sh` (Marker). Committed (the source PDFs in `literature_raw/` are gitignored); `literature_md/README.md` indexes the documents. For the theory behind a strategy (market making, order-book imbalance, micro-price, price impact), go through the wiki first: the Literature section of `references/wiki/index.md`, then the concept page, and only then the raw text at the cited line.
  - **Verify formulas against the PDF.** Marker's equations are LaTeX but OCR-based, so they can contain slips (e.g. `S_{τ1}, S_{τ1}` where the paper has `I_{τ1}, S_{τ1}`). Before implementing any formula from `literature_md/`, check it against the original PDF page (`python3 literature_md/pdfpage.py <slug> <line>` finds the page and prints its text), and don't trust a formula that disagrees with the surrounding text or with its own derivation.
- **Commits:** commit each finished step on its own, with the docs it changed, once the tests (and the wiki lint, if the wiki changed) pass. A request with several steps gets one commit per step. Author commits as the user (Jakub) only. Never put a `Co-Authored-By: Claude …` trailer, or any other Claude attribution, in commit messages or PR descriptions.
