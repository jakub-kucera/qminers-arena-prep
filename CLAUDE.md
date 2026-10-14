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
uv run pytest                       # all tests (~9 s)
uv run pytest tests/test_engine.py::test_trade_matching_at_the_same_price   # one test

uv run python -m arena.diagnose 1 --data p4                       # per-product market diagnostics, no bot needed
uv run python -m arena.backtest bots/template.py 1                # Prosperity 3 round 1, every day
uv run python -m arena.backtest bots/template.py 1-0 --data p2    # Prosperity 2, round 1 day 0
uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2 --out results/
uv run python -m arena.backtest bots/template.py 1 --resting --vs bots/template.py   # orders rest; a rival copy shares the market
uv run python -m arena.validate bots/template.py 1                # pre-submission checks, exit 1 on FAIL
uv run python -m arena.grid bots/template.py 1 --grid PARAMS.KELP.make_edge=0..3 --modes all,worse --out results/grid.csv
uv run python -m arena.analysis results/                          # PNGs to results/plots/ + fill/markout tables
uv run python -m arena.sim generate data/sim --days 5              # simulated days in the Prosperity layout (--data data/sim)
uv run python -m arena.sim run bots/template.py --days 5           # the bot inside the agent market, against replaying the same days
uv run python -m arena.analysis --grid results/grid.csv           # grid heatmaps
uv run --group analysis jupyter lab notebooks/analysis.ipynb      # the analysis group adds Jupyter
uv run python -m experiments.p4_levels                            # a one-off study; its numbers are in IDEAS.md
uv run python -m experiments.zoo                                  # scores every LLM-written bot in bots/zoo/ against the template
```

- **Day specs:** `ROUND` (every day in the round) or `ROUND-DAY`, e.g. `1`, `1-0`, `1--1`.
- **`--data` aliases:** `p2` and `p3` point into `references/prosperity{2,3}-backtester-jmerle/.../resources`, `p4` into `references/prosperity4-backtester/prosperity4bt/resources` (rounds 0–5).
- **Tests without the data:** `tests/test_parity.py` skips if `references/` hasn't been cloned. All other tests use a tiny CSV fixture from `tests/conftest.py`.
- **Notebook check:** `uv run --group analysis jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output-dir <scratch>` runs it end to end. Commit the notebook without outputs.
- **No linter or formatter is configured.**

## Architecture

**The engine doesn't know any format.**
- `arena/model.py` defines the internal types: `Book`, `Tick`, `Day`, `Order`, `Cancel`, `OpenOrder`, `Fill`, `MarketTrade`. Order and fill quantities are signed; book volumes are positive.
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
- **Presets** are calibrated against P3 round 1 through `arena.diagnose`; `tests/test_sim.py` holds the bands. `write_day` writes the Prosperity layout plus `limits.json`, which the Prosperity loader merges into `LIMITS`.

**Grid search** (`arena/grid.py`):
- **Parallel runs:** a `ProcessPoolExecutor` runs every combination as (bot file + `--set` + grid values) × days × `--modes`. Each worker loads the days once, in `_init_worker`, into the module-level `_WORKER` dict. `--jobs 1` runs in-process.
- **Smoke test:** before the pool starts, a 200-tick run of the first combination makes typos fail fast.
- **Ranking:** combinations are ranked on `pnl`, `min day`, `nbhd` (mean over the combination and its one-step grid neighbours) and the PnL under each extra mode. The summary flags when these measures disagree.
- **Held-out days:** with two or more days, `leave_one_day_out` scores each day with the best combination by PnL on the other days, from the per-day PnL already collected (no extra runs). `repeated_days` flags days that share a product's books and trades (ignoring counterparty names): Prosperity reuses days across rounds.

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
- **STRATEGY:** format-agnostic. Fair value (fixed, mid, `wall_mid`, `outer_mid` or `sized_mid`; `sized_mid` survives rivals' resting orders) → take → clear → make. `clear`, `skew` and `size_skew` work inventory toward `target` (default 0; a long target holds with a steady drift). With `level` set, `level_target` replaces `target`: the full limit against a move of `level_band` from a price the product returns to. With `follow` set, `follow_target` makes a call option hold its underlying's target as a share of its own limit (Black–Scholes helpers in total variance, so no expiry is needed). A product with `basket` trades its spread against its legs with the level settings, and legs with `hedge` take what the baskets ask of them (`Plan.legs`). With `jump_min` set, `jump_target` holds the full limit against each jump once enough of the day's jumps have reversed (a gate measured on the day, so it can run on every product), crossing up to `jump_edge`. With `copy` set (`{name: weight}`), `copy_target` holds the weighted direction of the named traders' last trades, from `Market.trades`, which the ADAPTER fills from both `market_trades` and our own fills' counterparties. The cross-product hook is `Market`: every product's book, and this tick's `Plan`s so far. `Trader.run` trades products that `follow` or `hedge` another after it (one level of dependency). `Plan` keeps all orders inside the full room under the limit, counting buys and sells separately. It holds `takes` (take, clear) and `quotes` (make) apart.
- **EXECUTION:** format-agnostic. `execute(plan, resting)` returns cancels and new orders:
  - takes are sent as IOC
  - a resting quote is kept while a quote on its side and price still wants at least its size
  - everything else is cancelled

  The engine applies cancels before the limit check, which is why planning with the full room is safe. With nothing resting, it sends the whole plan, so one file works in both engine modes.
- **ADAPTER:** the only Prosperity-specific code, including the resting extensions (`state.open_orders`, `Cancel`, `ioc`).
- **`Trader.run`:** a try/except per product, swallowed unless `STRICT`. A product that errors cancels its resting orders.

`bots/zoo/` holds bots written blind by language models from `bots/zoo/SPEC.md` and `PROMPTS.md`: the agent baseline and `--vs` rivals. Never edit a zoo bot or a prompt once used; its README has the protocol for adding other providers' bots.

New strategy logic goes in STRATEGY, order-management changes go in EXECUTION, and format changes go in ADAPTER. `bots/datamodel.py` only
lets editors resolve imports; it is never submitted.

## Known gaps (from README)

- **The queue model is an estimate.** It assumes the back of the queue, and only moves an order up when visible volume shrinks.
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
