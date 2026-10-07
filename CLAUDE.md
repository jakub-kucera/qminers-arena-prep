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
references/clone.sh                 # fetch the reference repos + Prosperity data (gitignored, ~2 GB)
uv sync                             # Python 3.12; dev group = pytest, pandas, matplotlib
uv run pytest                       # all tests (~9 s)
uv run pytest tests/test_engine.py::test_trade_matching_at_the_same_price   # one test

uv run python -m arena.backtest bots/template.py 1                # Prosperity 3 round 1, every day
uv run python -m arena.backtest bots/template.py 1-0 --data p2    # Prosperity 2, round 1 day 0
uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2 --out results/
uv run python -m arena.backtest bots/template.py 1 --resting --vs bots/template.py   # orders rest; a rival copy shares the market
uv run python -m arena.validate bots/template.py 1                # pre-submission checks, exit 1 on FAIL
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..3 --modes all,worse --out results/grid.csv
uv run python -m arena.analysis results/                          # PNGs to results/plots/ + fill/markout tables
uv run python -m arena.analysis --grid results/grid.csv           # grid heatmaps
uv run --group analysis jupyter lab notebooks/analysis.ipynb      # the analysis group adds Jupyter
```

- **Day specs:** `ROUND` (every day in the round) or `ROUND-DAY`, e.g. `1`, `1-0`, `1--1`.
- **`--data` aliases:** `p2` and `p3` point into `references/prosperity{2,3}-backtester-jmerle/.../resources`.
- **Tests without the data:** `tests/test_parity.py` skips if `references/` hasn't been cloned. All other tests use a tiny CSV fixture from `tests/conftest.py`.
- **Notebook check:** `uv run --group analysis jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output-dir <scratch>` runs it end to end. Commit the notebook without outputs.
- **No linter or formatter is configured.**

## Architecture

**The engine doesn't know any format.**
- `arena/model.py` defines the internal types: `Book`, `Tick`, `Day`, `Order`, `Cancel`, `OpenOrder`, `Fill`, `MarketTrade`. Order and fill quantities are signed; book volumes are positive.
- `arena/engine.py` `run_day(day, bot, config)` replays a `Day` against any object with `step(tick, positions, own_fills, market_trades, open_orders) -> list[Order | Cancel]`.
- It records per-tick positions, marks, PnL and best bid/ask, plus orders, fills, errors, limit breaches and timings, in a `DayResult`.
- `arena/report.py` `write_csvs` turns it into `<day>_timeline.csv`, `_fills.csv` and `_orders.csv`. Those columns are the contract with `arena/analysis.py`, so change both together.
- **Only `arena/analysis.py` imports pandas and matplotlib.** Everything else is standard library.
- The engine catches the bot's exceptions and records them per tick, so a run never aborts.

**Formats are plug-ins** (`arena/formats/`). A format module must provide:
- `PROVIDED_MODULES`
- `resolve_data_dir`
- `load_days`
- `load_bot`
- `check_source`

It is registered in `arena/formats/__init__.py` `FORMATS`. `prosperity.py` is the only format today. It holds:
- **The CSV loader:** `;`-separated. Prosperity 2 trade files have `_wn`/`_nn` name variants.
- **The `LIMITS` table:** the loader raises on any product without a limit.
- **`ProsperityBot`:** it builds a `TradingState`, calls `Trader().run(state)`, type-checks the returned `(orders, conversions, traderData)`, and converts the orders.

`prosperity_datamodel.py` is our own copy of IMC's `datamodel` module, without jsonpickle. On the day, the plan is to add `arena/formats/qminers.py`, modelled on `prosperity.py`.

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
- **Trade fills:** trades at its price first use up the queue ahead of it; trades through its price fill it.
- **Book fills:** a next snapshot that crosses it fills it at its own price (`Fill.source == "cross"`), and the bot sees that snapshot minus the volume.
- **Bot interface:** `Bot.step` gets `open_orders` (always empty in the default mode) and may return `Cancel(order_id)` among its orders. The Prosperity format exposes these as datamodel extensions: `state.open_orders`, `Cancel`, `Order(..., ioc=True)`.
- **The default path doesn't change:** resting-mode code lives in its own branch of `run_day` and in the helpers below the "resting mode" marker. Parity only covers the default mode.

`--fill-ratio` thins out liquidity with binomial draws, seeded and independent of the bot's orders, so variants of a bot can be compared fairly.

**Shared market** (`run_market(day, [(name, bot), ...], config)`, CLI `--vs BOT`):
- **One engine:** `run_day` is `run_market` with one participant. Every helper works on `_Live` orders carrying an `owner`, and fills are routed to their owner by `order_id`.
- **Arrival:** all bots see the same tick and decide at once. Their actions are then processed in a seeded shuffle, drawn from its own random stream so the `--fill-ratio` draws don't depend on the number of bots.
- **Matching:** `_take` matches a new order against the recorded levels and other owners' working orders, best price first. At one price the recorded volume goes first. Each bot's book (`_seen_by`) adds the others' resting orders, never its own.
- **Breaches vs races:** limits are checked twice. Orders that don't fit the position the bot saw are `limit_breaches`, the bot's bug. Orders that fitted but don't fit after another bot's fill are `races`. Both are rejected, but the grid only discards combinations with breaches.
- **CLI:** `arena.cli.run_with_rivals` loads the bot and its `--vs` rivals and runs them, for both the backtest and the grid. `--set` only applies to the main bot.

**Grid search** (`arena/grid.py`):
- **Parallel runs:** a `ProcessPoolExecutor` runs every combination as (bot file + `--set` + grid values) × days × `--modes`. Each worker loads the days once, in `_init_worker`, into the module-level `_WORKER` dict. `--jobs 1` runs in-process.
- **Smoke test:** before the pool starts, a 200-tick run of the first combination makes typos fail fast.
- **Ranking:** combinations are ranked on `pnl`, `min day`, `nbhd` (mean over the combination and its one-step grid neighbours) and the PnL under each extra mode. The summary flags when these measures disagree.

**Analysis** (`arena/analysis.py`):
- **No pyplot:** charts are `Chart` objects, a `Figure` subclass with `_repr_png_`, so they display in notebooks and save from the CLI without pyplot. Each `Chart` keeps the rc params of the theme it was drawn in.
- **Palette:** `THEMES` holds palettes checked with the dataviz skill's validator. Keep categorical colors in slot order.
- **Product colors:** `Run.colors` gives each product the same color in every chart of a run. It covers the `MAX_SERIES` products with the largest |PnL|; charts fold the rest into "other".
- **Fill edge:** measured against the **arrival mid**, one tick before the fill. A taken order is part of its own tick's book and skews that tick's mid.
- **Markout horizons start at 1 tick**, for the same reason.

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
- **STRATEGY:** format-agnostic. Fair value (fixed, mid, or `wall_mid`) → take → clear → make. `Plan` keeps all orders inside the full room under the limit, counting buys and sells separately. It holds `takes` (take, clear) and `quotes` (make) apart.
- **EXECUTION:** format-agnostic. `execute(plan, resting)` returns cancels and new orders:
  - takes are sent as IOC
  - a resting quote is kept while a quote on its side and price still wants at least its size
  - everything else is cancelled

  The engine applies cancels before the limit check, which is why planning with the full room is safe. With nothing resting, it sends the whole plan, so one file works in both engine modes.
- **ADAPTER:** the only Prosperity-specific code, including the resting extensions (`state.open_orders`, `Cancel`, `ioc`).
- **`Trader.run`:** a try/except per product, swallowed unless `STRICT`. A product that errors cancels its resting orders.

New strategy logic goes in STRATEGY, order-management changes go in EXECUTION, and format changes go in ADAPTER. `bots/datamodel.py` only
lets editors resolve imports; it is never submitted.

## Known gaps (from README)

- **The queue model is an estimate.** It assumes the back of the queue, and only moves an order up when visible volume shrinks.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **Rivals are only the bots you bring** with `--vs`. Real teams will behave differently.

## Repo conventions

- **`references/`:** third-party clones listed in `references/clone.sh`. Read them for ideas, but don't edit or import from them.
  - `references/algotrade2026-pitfa19/` contains its own `CLAUDE.md` and `AGENTS.md`. They describe that repo, not this one, so don't follow them.
  - `references/README.md` summarises what each repo is useful for.
- **`literature_md/`:** market-microstructure papers and books, converted from `literature_raw/*.pdf` to markdown by `literature_md/convert.sh` (Marker). Gitignored except the script and its `README.md`, which indexes the documents. Search it for the theory behind a strategy (market making, order-book imbalance, micro-price, price impact).
  - **Verify formulas against the PDF.** Marker's equations are LaTeX but OCR-based, so they can contain slips (e.g. `S_{τ1}, S_{τ1}` where the paper has `I_{τ1}, S_{τ1}`). Before implementing any formula from `literature_md/`, check it against the original PDF page (the `README.md` explains how to find the page), and don't trust a formula that disagrees with the surrounding text or with its own derivation.
- **Commits:** author commits as the user (Jakub) only. Never put a `Co-Authored-By: Claude …` trailer, or any other Claude attribution, in commit messages or PR descriptions.
