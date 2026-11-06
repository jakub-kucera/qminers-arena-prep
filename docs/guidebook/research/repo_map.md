# A map of the qminers_arena repo, for planning the guidebook

I read CLAUDE.md, ARCHITECTURE.md, RUNBOOK.md, python/experiments/README.md, IDEAS.md's index, ON_THE_DAY.md's headings and its "Known so far" section, and the parts of README.md that matter here. I also checked the template's DEFAULTS and fair-value code, the format docstrings, the mock-round READMEs, the zoo README and the wiki's day-one page. I changed nothing. All paths are under `/Users/jakubkucera/Documents/qminers_arena/`.

## A. Architecture

**Components and where they live:**
- **Internal model:** `python/arena/model.py` defines `Book`, `Tick`, `Day`, `Order`, `Cancel`, `OpenOrder`, `Fill`, `MarketTrade`. `Book.wall_mid` is defined here.
- **Engine:** `python/arena/engine.py`. `run_day(day, bot, config)` is `run_market` with one participant. It replays a `Day` against any object with `step(tick, positions, own_fills, market_trades, open_orders)` and returns a `DayResult`.
  - The engine knows no format.
  - The default mode follows Prosperity's matching rules, and its parity with jmerle's prosperity3bt is pinned (`python/tests/test_parity.py`).
  - Modes: `--resting` with `--queue back|prob|front`, `--match-trades`, `--fill-ratio`, `--mark`, `--limit-penalty`, `--delay`, `--deplete`, fees, order caps, and `--vs` (a shared market with rivals).
- **Reports:** `python/arena/report.py` writes the CSVs (timeline, fills, orders, trades). `python/arena/analysis.py` is the only module that uses pandas or matplotlib: charts, markouts, `pnl_split`, `trade_impact`.
- **Format plug-ins:** `python/arena/formats/`, registered in `FORMATS` in `__init__.py`. Each provides `PROVIDED_MODULES`, `resolve_data_dir`, `load_days`, `load_bot`, `check_source`, and optionally `RESTING`, `ENGINE` and `CREDITS`.
  - `prosperity.py` plus `prosperity_datamodel.py`: the stand-in format.
  - `drill.py` plus `drill_exchange.py`: the practice format.
  - `snapshots.py` plus `snapshots_api.py`, and `orderlog.py`: skeletons.
  - `qminers.py`: the day's skeleton (`SKELETON = True`, a copy of `snapshots.py` with `TODO(day)` markers).
- **Bot loading:** `python/arena/botfile.py` execs the bot into a fresh module, injects the format's modules, and applies `--set GLOBAL.key=literal` overrides.
- **Bot template:** `python/bots/template.py` has PARAMS (DEFAULTS at L41, per-product entries), STRATEGY (fair → take → clear → make, plus the target modes), EXECUTION (`execute` at L935, `on_the_way`/`went` for orders that arrive late), ADAPTER (L1001+, the only Prosperity code) and `Trader.run` (L1063).
  - Copies for other formats: `python/bots/drill/template.py` and `python/bots/qminers/template.py`, kept in sync by `experiments.format_drill --sync`.
  - Also `python/bots/probe.py` (the first-hour probes), `rivals/` (adversarial bots), `research/` (one-idea copies of the template), `mm.py` and `zoo/`.
- **Tools on top of the engine (`python/arena/`):**
  - `backtest.py`: one run; prints `--metrics` and the PnL path's risk.
  - `grid.py`: parallel grid with `--screen`, `--halving`, `--sample`, `--search coord|tpe` (via `search.py`), `--scenario` (via `scenario.py`), `--permute`, `--holdout` and the overfitting statistics.
  - `stats.py`: CSCV/PBO, DSR, bootstrap, SPA, StepM.
  - `compare.py`: several bots compared through the grid's statistics.
  - `stress.py`: perturbed days, and `permute` for the permutation test.
  - `diagnose.py`: works from the data alone, with no bot. It prints per-product notes and, with `--suggest`, a PARAMS entry.
  - `validate.py`: the pre-upload checks (size, time, state kept outside `traderData`, `--late`).
  - `compact.py`: shrinks a bot over the size cap.
  - `sim.py`: an agent-based market with presets and regimes, separate from the engine.
  - `cli.py`: shared flags and `format_config`. `rust.py`: the bridge to Rust.
- **Calibrate:** `python/experiments/day/calibrate.py` fits the engine settings so that our backtest of an uploaded file reproduces the portal's metrics and the results ZIP. It prints a `RESTING`/`ENGINE` to paste, or refuses when no fit comes within 5%.
- **Rust twins:** `rust/` mirrors `python/`.
  - `engine.rs`, `sim.rs`, `stats.rs`, `stress.rs`, plus the bots: the template, the rivals, `mm` and every zoo bot.
  - `rust/twins.json` holds hashes; a twin whose Python code changed is stale and `--engine rust` refuses it.
  - Results match Python to the bit (`rust/src/support/pyrandom.rs` reproduces Python's random numbers). Parity is checked by `experiments.rust_bench --parity-only --record`.
- **Experiments:**
  - `python/experiments/day/`: re-run on the Arena's data with `--data D --days ... --format F --bot B`.
  - `python/experiments/study/`: one-off Prosperity or ABIDES studies.
  - Top-level tools: `abides_days`, `lobster_days`, `seen_days`, `format_drill`, `rust_bench`, `ideas_index`, `mock_round/`.
- **Wiki:** `references/wiki/` has `index.md`, `concepts/*.md` (23 pages), `sources/` (one per reference clone) and `log.md`, checked by `lint.py`. It links to `literature_md/`.
- **Mock rounds:** `python/experiments/mock_round/` (round 1 plus `round2/`, `round3/`, `round4/`) are disguised rehearsals. Each has `public/` (`rules.md`, `example_bot.py`), `private/` (generator, disguise, portal/evaluator, `ANSWER_KEY.md`) and `results/`.
- **Day docs:** `RUNBOOK.md` → `ON_THE_DAY.md` → `KICKOFF_PROMPT.md`. `IDEAS.md` holds the priors.

**Data flow, as boxes and arrows:**
```
[Raw data: Prosperity CSV | drill JSONL | Arena download | ABIDES/LOBSTER/arena.sim → Prosperity layout]
      │ format plug-in: load_days
      ▼
[Day (model.py): Ticks of Book + MarketTrades, Day.info]
      ├──► [arena.diagnose (no bot)] ──notes──► [wiki day-one table] ──► PARAMS (--suggest)
      ├──► [experiments.day.* (structure, premise, imbalance, ...)] ──► IDEAS.md rows
      ▼
[Bot file] ─botfile.load (+--set, PROVIDED_MODULES)─► format's load_bot wrapper (e.g. ProsperityBot → Trader.run(TradingState))
      ▼
[engine.run_market: matching / resting / queue / delay / fees / --vs rivals]  ⇄  [Rust twin engine.rs (--engine rust)]
      ▼
[DayResult] ──► report.write_csvs ──► analysis.py (charts, markouts)
      ├──► arena.backtest (--metrics = portal-style figures)
      ├──► arena.grid / compare (many cells × days × modes/scenarios) ──► stats.py / stats.rs (PBO, DSR, SPA, StepM, holdout) ──► "pick"
      ├──► arena.stress (perturbed days) ──► stop_loss sizes
      └──► arena.validate ──► upload ──► portal metrics.json + results ZIP ──► calibrate ──► plug-in ENGINE/RESTING ──► back to engine
[arena.sim] produces Days (write_day) and also runs bots in a reacting market, beside the engine
```

## B. Data formats and vocabulary

**The formats:**
- **Prosperity** (`python/arena/formats/prosperity.py`), `;`-separated:
  - `prices_round_R_day_D.csv` has `day;timestamp;product;bid_price_1..3;bid_volume_1..3;ask_price_1..3;ask_volume_1..3;mid_price;profit_and_loss`, so three book levels a side.
  - `trades_round_R_day_D.csv` has `timestamp;buyer;seller;symbol;currency;price;quantity`. Names are often empty; P2 has `_wn`/`_nn` variants.
  - Timestamps run 0..999,900 in steps of 100, so a day has 10,000 ticks.
  - The bot's API is `Trader.run(state: TradingState) -> (orders, conversions, traderData)`. `TradingState` has `traderData`, `timestamp`, `order_depths`, `own_trades`, `market_trades`, `position` and `observations`, plus our extension `open_orders` (`prosperity_datamodel.py:148`).
  - `traderData` is a string, the only state that survives between calls (Prosperity cut it at 50k characters).
  - Limits come from the `LIMITS` table or a `limits.json`. Conversions are not supported.
- **Drill** (`drill.py`): `instruments.json` (a price unit, and a tick and max position per product) and `session_<n>.jsonl` events (`level`, `trade` with an aggressor, `step`).
  - Decimal prices are stored in integer cents.
  - The bot API is a callback: `Bot.on_tick(api)` with `api.buy/sell/cancel` and opaque ids (via `Order.tag`).
  - Orders rest (`RESTING`), and state lives on the bot instance.
- **qminers skeleton** (`qminers.py`, currently the same as `snapshots.py`): `limits.json`, `<day>_book.csv` (N levels), and optionally `<day>_trades.csv`.
  - The API is `class Strategy: on_tick(self, state) -> [api.Order | api.Cancel]`.
  - On the day it is rewritten using the 13-step checklist in `ON_THE_DAY.md`, "The format swap, step by step".
- **`orderlog.py`:** an order-by-order event log (`add`/`modify`/`delete`/`execute`/`trade`) rebuilt into a book at each step.
- **Mock rounds** (all disguised `arena.sim` products):
  - Round 1, "Meridian": `depth.csv` and `prints.csv` with an aggressor flag; the API is `init(session)` and `trade(snapshot, memory) -> list[dict]`.
  - Round 2, Halden: gzipped JSON lines, prices in pips; `class Strategy.on_market(update)` returning post/take/pull tuples.
  - Round 3, Kestrel: level changes as CSV; a function API `setup(ctx)`, `step(ctx, view)`; hidden `worse` matching, last-trade mark and a one-step delay.
  - Round 4, Varde: JSON lines, cents on a 5-cent tick; `Strategy(limits).on_tick(state)`. Its portal is not our engine: half of each print reaches resting orders, the mark is a 100-print VWAP, and there is a fee per order.
- **ABIDES** (`python/experiments/abides_days.py`): RMSC04 is one stock, "ABM", traded by noise, value, momentum and adaptive-market-maker agents. It is converted to the Prosperity layout: a tick a second (23,400 a day), three levels, cents, plus the fundamental.
- **LOBSTER** (`python/experiments/lobster_days.py`): real NASDAQ message and orderbook files, converted the same way (a tick a second, three levels, cents, anonymous trades from the next second). The files themselves are still to be obtained (`docs/MANUAL_TODO.md`).

**Vocabulary:**
- **Tick:** one snapshot step: a book, the market trades since the last one, and one bot call.
- **Book level:** a price and its total volume on one side; level 1 is the best.
- **Wall:** the largest-volume level on a side, the exchange's own market-maker bot. Its quote sits near the true value.
- **Mid:** (best bid + best ask)/2. It is noisy, because small orders move the best prices.
- **Wall mid:** the midpoint of the two walls (`model.py:26`, `template.py:463`).
  - Variants: `outer_mid` (the outermost levels), `sized_mid` (the first level with at least `wall_size`, robust to rivals' resting orders), `weighted_mid` (the micro-price) and `hysteresis_mid`.
- **Print / market trade:** a trade between other participants, reported in the data. Our order can fill against a print at our own price when the engine runs with `--match-trades`.
- **Fill:** our own execution, with a `source` field:
  - `book`: we took a level;
  - `trade`: a print reached our order;
  - `cross`: the next snapshot crossed our resting order.
- **Position limit:** the maximum |position| per product. In Prosperity, an order set that could breach it is cancelled whole; `--limit-penalty` instead charges for lots beyond it.

**Three kinds of data (the distinction the user once confused):**
1. **Competition data:** the IMC Prosperity 2–4 rounds in `references/`, aliases `p2`/`p3`/`p4`. This is the stand-in for the Arena. It is generated by IMC's simulator with exchange bots: a wall at the value, uninformed takers, prices that are often mean-reverting.
2. **Simulator data:**
   - `arena.sim`: ours, with presets calibrated to P3/P4 (KELP, KELP_NOISY, HYDROGEL_PACK, ROBOT_DISHES, LARGE_TICK...). It also runs bots in a market that reacts to them.
   - ABIDES: JP Morgan's agent-based market, which we did not write. It has informed and momentum agents and no wall. It is the "a market unlike Prosperity" control.
3. **Real-market data:** LOBSTER's NASDAQ books.

**The zoo is not a data source.** `python/bots/zoo/` holds bots written blind by language models (Claude, Gemini, ChatGPT, local models) from one spec, `zoo/SPEC.md`, and the prompts in `PROMPTS.md`: baseline, market_maker, mean_reversion, momentum.
- They serve as the baseline an LLM-using team would start from, and as `--vs` rivals.
- They run on Prosperity data like any other bot. They are never edited, and each has a Rust twin.
- Results are in IDEAS.md, "The LLM zoo" (L213) and "Why the zoo beat the template head to head" (L214, kept).

## C. Techniques catalogue

Each line gives the parameter(s), what the technique does, and its IDEAS.md row and verdict. Parameters live in `python/bots/template.py` DEFAULTS (L41–222).

**Core market making**
- `take_edge`, `make_edge`, `make_inside`, `clear_edge`: take mispriced book orders, quote around fair, cut inventory at fair. L162, L163: kept.
- `make_inside` 2–3 against rivals quoting nearer fair: L211, kept.
- Per-side edges (`*_buy`/`*_sell`): L249, dropped here.
- Laddered quotes (`make_levels`/`make_step`): L250, open.
- `take_reserve`: L251, dropped here.
- Online `make_edge` learner (`bots/research/online_edge.py`): L237, dropped here.

**Fair value**
- `wall_mid`/`outer_mid`/`sized_mid` definitions: L173, kept; `sized_mid` is the default.
- `weighted_mid` (micro-price): L225, dropped here.
- `imbalance` ρ term: L223, dropped here.
- ρ3 depth term: L259, dropped here.
- `smoothing` (an EMA; Osmium uses 0.9): L227, kept. The Kalman-implied value from diagnose: L228, measured.
- One-tick reversion term: L230, dropped here.
- Linear fair (`lin_rho3`, `lin_momentum`): L260 and L255, open. It won strongly on ABIDES and costs a little on Prosperity.
- Combined models and blends: L240, dropped here.
- `hysteresis_mid` and the `join_min` gate for large-tick books: L253, dropped here.

**Inventory**
- `skew` against inventory: L166 and L191, dropped here.
- GLFT closed-form skew: L185, dropped here.
- `size_skew`: L168, dropped here.
- Guéant cross-product Γ: L265, dropped here.
- `target` long bias on a drifting product: L169, kept. Other drift strategies: L272, open.
- `make_size` cap below the limit: L187, kept.
- `cross_max`/`cross_excess` (passive-first execution toward a target): L254, kept.

**Target modes (directional bets)**
- `level`/`level_band`/`level_exit` (trade toward a known level): L175, kept. The day's own drifting level: L182, open. `cpd_*` changepoint detection: L221, dropped here.
- `basket` and `hedge` (trade a basket's spread against its legs): L177, kept.
  - Residual baskets: L178, dropped here. The package take: L179, dropped here.
  - Legs leading the basket: L192, dropped here. Optimal OU bands: L269, dropped here.
- Options:
  - `smile` (fit an IV smile, BS fair, trade deviations): L188 and L264, kept.
  - `follow` (vouchers hold the underlying's bet as delta): in the template; row L176, measured.
  - Long gamma: L271, dropped here.
- `jump_min`/`jump_share` (fade jumps that snap back): L181, kept. Market making on jumping products with resting orders: L180, measured.
- `copy` (follow named informed traders): L190, kept. `copy_sizes` (a nameless informed detector): L245, measured.
- `gate_move` (pull the side a move runs over): L255, open.
- Book-exhaustion gate: L257, dropped here.
- Per-side gate on adverse moves: L184, dropped here.
- Quoting by state: L273, dropped here.

**Protection and the close**
- `stop_loss` at about 3× the plain-day drawdown from `arena.stress`: L216, kept.
- `fixed_guard` (a fixed fair that gives way): L217, kept.
- `level_guard`: L218, dropped here. `vol_guard`: L219, dropped here.
- `flatten_from`: L222, kept. `flatten_keep` (keep a small position at the close): L252, dropped here.

**Market and environment facts (not strategies)**
- Lead-lag: L193, mixed (and L194, open).
- Structure scan, fixed sums, generator fingerprints: L195–197, measured.
- Recurring takers: L198, measured.
- Trade impact: L170, measured. Do the takes earn: L171, measured. Does making pay (Bouchaud margin): L172, measured.
- Fill-rate and fill-size curves: L241–242, measured. Implementation shortfall: L243, measured.
- Queue models: L206, measured.
- Adversarial rivals: L207, measured. Undercutting rival: L186, measured. Rival field: L208, open.
- Spoofing other bots: L212, open. Delay: L200, open. Fees: L201, open.
- Kronos forecaster: L275, dropped here.
- The 11 untested ideas: L321–331.

## D. Metrics and evaluation catalogue

**PnL and fill modes** (README "Fill assumptions matter", README L116; ARCHITECTURE "Matching rules"):
- `--match-trades all`: a print at or worse than our price fills us. This is the default and is optimistic.
- `worse`: only prints strictly through our price fill us. This is the robustness check: a ranking that flips under it is an artefact.
- `none`: the visible book only.
- On P3 round 1: all 72,674, worse 63,302, none 28,217.
- `--resting`: orders persist and queue. Queue models: `back` (default, pessimistic), `prob` (hftbacktest's power rule) and `front` (they re-post every tick).
- `--fill-ratio`: thins the available liquidity.
- `--delay`: latency.
- `--deplete`: our takes remove volume from later snapshots.
- `--mark mid|touch|last`: what open positions are valued at.
- `--limit-penalty`, fees: exchange-specific scoring.
- `--scenario`: bundles these settings, plus rivals, as named modes. `worst_case` is the pick's worst over all scenarios (L235, kept).

**Grid measures** (`python/arena/grid.py`):
- `pnl`: total PnL.
- `min day`: the worst day, a check on robustness.
- `nbhd`: the mean over a cell and its one-step neighbours, which penalises a lone spike.
- PnL under each extra mode (e.g. `worse`).
- Risk columns (`report.PathRisk`): max drawdown, `conc` (concentration in the best window), `under`/`run` (time below the running high), daily and block Sharpe, late days (L236, measured).

**Overfitting statistics** (`python/arena/stats.py`):
- PBO via CSCV (Bailey et al.): the probability that the in-sample best cell ranks below the median out of sample.
- DSR (deflated Sharpe ratio): the best cell's Sharpe corrected for the number of trials (`independent_trials`) and non-normality.
- SPA (Hansen): is the best cell's gain over the baseline real, given every cell tried?
- StepM (Romano–Wolf): which cells individually beat the baseline, at family-wise level `TEST_ALPHA` = 4%. Both SPA and StepM use a stationary bootstrap over 100-tick blocks.
- `pick`: the best cell StepM confirms under every gate mode. It is the only setting change the RUNBOOK allows.
- Held-out data:
  - `leave_one_day_out`;
  - `--holdout last|DAY|SHARE%` re-runs the tests without that data;
  - `repeated_days` flags days Prosperity reused.
- `--permute N`: ranks the real search's best against searches on shuffled days (L234, kept).
- Selection rules on unseen days: L232, kept. Null false-positive rates: `study/snooping_null_rates.py`.

**Portal metrics** (ON_THE_DAY "Known so far"; `arena.backtest --metrics`; `calibrate.py:53`):
- `score`: the PnL the leaderboard ranks by.
- `fills`, `tradedVolume`, `inventory`: fills, lots traded, end position.
- `cash`, `markPrice`: cash, and the price the end position is valued at. This is not a markout.
- `breachPenalty`: the position-limit penalty.
- `pnlSe`: the PnL's standard error, computed per tick, per block or per day.
- `absInventoryQ50/Q68/Q95/Q997`: quantiles of |position|.
- The identity to check: score = cash + position × mark − penalty.
- Calibrate ranks engine settings by their worst per-figure error against these numbers.

**Markouts and fill analysis** (`python/arena/analysis.py`):
- Fill edge against the arrival mid.
- Markouts: the price move after a fill at horizons from 1 tick, measured against the mark or the wall mid. They show adverse selection.
- `pnl_split`: splits PnL by reference and adds up exactly.
- `trade_impact`: how far the data's prints move the price.
- `experiments.day.quote_markouts`: passive fills by state.

**`arena.diagnose` notes** (thresholds at `diagnose.py:121-161`; each mapped to an action in `references/wiki/concepts/reading-the-data-on-day-one.md`):
- large-tick and small-tick, plus Gao–Wang's λ± test for whether quoting at a one-tick spread pays;
- an empty side;
- `wall_size` too large for the book;
- jumps past half the spread (take only if orders rest);
- snap-back jumps;
- mid mean-reverts, or the wall mid filters noise (signature ratio, lag-1 autocorrelation);
- a fixed level;
- noisy, with the Kalman-implied `smooth`;
- slow reversion to a level;
- drift every day, or drift on k of n days;
- time-of-day profile;
- persistent queues (`kept`);
- flow: one-sided, persistent signs, informed share, thin Bouchaud margin;
- the wall's lead over the mid.

**`premise` verdict** (L239, measured): uses the shuffle test plus the margin and large-tick signs to say whether each product is Prosperity-like or agent-like.

## E. Suggested learning order

1. `README.md`, top table and Setup: what exists.
2. `CLAUDE.md`: the commands and the rules that keep the parts consistent.
3. The vocabulary in `references/wiki/concepts/fair-value-and-wall-mid.md` and `market-making-and-inventory-skew.md`, with `python/bots/template.py` L41–222 (DEFAULTS) and L370–470 (fair value) beside them.
4. `ARCHITECTURE.md` "Architecture" up to "Matching rules", then README's "Fill assumptions matter" and "How the engine works / Resting mode". Run `arena.backtest` in each mode.
5. `references/wiki/concepts/reading-the-data-on-day-one.md` with `arena.diagnose 1 --data p3`.
6. `references/wiki/concepts/validation-and-overfitting.md`, README "Grid search", and ARCHITECTURE "Grid search". Run a small grid and read its `pick`.
7. IDEAS.md: the index and the "What a market we didn't write said" paragraph (just after the index), then rows by topic. Cross-reference `python/experiments/README.md`.
8. The special modes: wiki pages on baskets, options and vouchers, jumps, informed counterparties, drift and regime change, queue position.
9. Simulators and other markets: README "Simulated market", the `abides_days`/`lobster_days` docstrings, the zoo README.
10. The day itself: `RUNBOOK.md` → `ON_THE_DAY.md` ("Known so far", "The format swap", "Probes") → `KICKOFF_PROMPT.md`.
11. One mock round (`python/experiments/mock_round/round4/README.md` and its `results/`) as a worked example of the whole loop.
12. Optional: the `rust/README.md` twin table, and `literature_md/` through the wiki's Literature section.
