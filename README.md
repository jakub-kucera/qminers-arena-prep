# Qminers Algo Trade Arena prep

Tooling for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague): a backtester, a
parameter grid search, charts and fill statistics, a pre-submission validator and a
single-file bot template. Until the real API is known,
everything runs on IMC Prosperity data and its bot format as a stand-in.

| Path | What it is |
|---|---|
| `python/arena/` | Backtesting engine; the `diagnose`, `backtest`, `grid`, `analysis` and `validate` commands; format plug-ins under `python/arena/formats/` |
| `python/bots/template.py` | Single-file market maker to copy for each round |
| `python/bots/probe.py` | The first-hour probe bot: runs the probes in `ON_THE_DAY.md` and prints what it finds |
| `python/bots/drill/template.py` | The template with its ADAPTER rewritten for the drill format, the worked example of the format swap |
| `python/notebooks/analysis.ipynb` | Backtest → PnL, fills, one product's fills against the book, markouts, PnL split, market-trade impact, grid heatmaps |
| `references/` | Reference repos and the Prosperity data; see [references/README.md](references/README.md) |
| `literature_md/` | Market-microstructure papers and books as markdown with LaTeX equations, for learning the theory; see [literature_md/README.md](literature_md/README.md) |
| `python/tests/` | Unit tests, plus a regression test pinned to jmerle's backtester |
| `python/experiments/` | One-off studies whose results are in `IDEAS.md`; [its README](python/experiments/README.md) lists all of them, and the commands that run the re-tests on the day's data (`--data`, `--format`) |
| `rust/` | The Rust twins of the engine, the simulator, the grid's statistics and the bots, laid out as `python/` is (`rust/src/arena/engine.rs` for `python/arena/engine.py`); see [rust/README.md](rust/README.md) |
| [`ON_THE_DAY.md`](ON_THE_DAY.md) | What to find out about the real Arena at the event, and what each answer changes here |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | How the code fits together: the engine, the formats, the matching rules and their modes, the grid and its statistics, the simulator, the Rust port |
| [`RUNBOOK.md`](RUNBOOK.md) | One page for the day: the commands and checkpoints, in order, each pointing into `ON_THE_DAY.md` |
| [`TODO.md`](TODO.md) | Prep work left before the event ([`TODO_DONE.md`](TODO_DONE.md): the finished items, with their evidence and decisions) |

## Setup

```sh
references/clone.sh   # reference repos + Prosperity data (~2 GB)
uv sync               # installs python/ as the project (editable), so `python -m arena...` runs from here; the engine needs only the standard library, dev adds pytest, pandas, matplotlib
uv run pytest
uv run --group analysis jupyter lab python/notebooks/analysis.ipynb   # optional: Jupyter
```

## Diagnose the data

```sh
uv run python -m arena.diagnose 1                      # Prosperity 3 round 1, every day
uv run python -m arena.diagnose 1 --data p4 --csv results/diag.csv
```

```
product           spread  1 tick  empty  jumps  mid AC1  mid sig  wall sig  slow rev  drift/day  trades  buys   C(1)   edge   R(1)  R(50)   slow   fast
KELP                  3t     13%     0%     0%    -0.48     17.9       2.8       1.4        +11   8,634   35%  +0.13  -0.93  +0.00  -0.01  +0.94  +0.81
RAINFOREST_RESIN      8t      0%     0%     3%    -0.50     50.0      49.6      20.1         +0   7,121   49%  +0.09  -1.49  +0.09  +0.07  +1.41  +1.27
SQUID_INK             3t     14%     0%    16%    -0.17      1.5       1.3       1.7        -53   8,651   35%  +0.12  -0.93  +0.02  -0.02  +0.95  +0.80

KELP: small-tick (median spread 3 ticks); mid mean-reverts at one tick; wall mid filters the mid's noise; market making pays (0.41 of the spread a unit)
...
```

The first thing to run on a new data download: it needs no bot. Per product it measures:
- **The book:** the spread in ticks, how often a side is empty, and how often the wall mid jumps by more than half the spread in one tick. If orders rest, quotes on a product that jumps get picked off.
- **The noise:** how much the mid and the wall mid revert from one tick to the next, and whether the wall mid returns to a level over about 1,000 ticks.
- **The drift:** how far the wall mid moves over a day.
- **The market trades:** which side they hit, whether their signs persist (`C(1)`), what the taker paid, how far the wall mid moves after them, and the margin per unit a market maker would make on them (Bouchaud et al. eqs. 17.13–17.14).

The notes under the table name the regime. [Reading the data on day one](references/wiki/concepts/reading-the-data-on-day-one.md) maps each one to a strategy choice. `--csv` writes every number, against both the mid and the wall mid.

## Backtest

```sh
uv run python -m arena.backtest python/bots/template.py 1                  # Prosperity 3 round 1, every day
uv run python -m arena.backtest python/bots/template.py 1-0 --data p2      # Prosperity 2 round 1, day 0
uv run python -m arena.backtest python/bots/template.py 1 --set PARAMS.KELP.make_edge=2
uv run python -m arena.backtest python/bots/template.py 1 --out results/   # per-day CSVs for arena.analysis
uv run python -m arena.backtest python/bots/template.py 1 --vs python/bots/template.py   # against a copy of itself
```

```
r1d0 · 10,000 ticks
  product                  pnl   fills   volume  max|pos|  at limit
  KELP                   8,616   3,130    8,525        50      9.7%
  RAINFOREST_RESIN      17,295   3,260    7,892        50      0.2%
  total pnl 25,912 · max drawdown 360
  bot time per tick: mean 0.02 ms · p99 0.03 ms · max 0.15 ms
```

Days are `ROUND` (all of its days) or `ROUND-DAY`, e.g. `1`, `1-0` or `1--1`.

| Option | Meaning |
|---|---|
| `--data` | `p3` (default), `p2`, `p4`, or a folder in the same layout |
| `--set PATH=VALUE` | Override a bot global, e.g. `PARAMS.KELP.skew=2`. Repeatable. |
| `--match-trades` | Which market trades leftover orders can fill against: `all` (default), `worse`, `none`. See below. |
| `--resting` | Unfilled orders rest on the book until filled or cancelled, with a queue model. See [Resting mode](#resting-mode). |
| `--queue back\|prob\|front` | With `--resting`: where other orders' cancellations at your price fall (default `back`). `--queue-power N` sets `prob`'s power. See [Resting mode](#resting-mode). |
| `--vs BOT` | Another bot in the same market, competing for fills and trading with yours. Repeatable. See [Shared market](#shared-market). |
| `--fill-ratio R` | Only this share of each book level and market trade is available to you, a rough stand-in for other teams competing for fills. Seeded with `--seed`. With `--resting`, the volume queued ahead of your order is still all of the visible volume: the others are there whether or not you could trade with them. |
| `--out DIR` | Write `<day>_timeline.csv` (position, mark, PnL, best bid/ask and wall mid per tick), `<day>_fills.csv`, `<day>_orders.csv` and `<day>_trades.csv` (the data's market trades) |
| `--print` | Show the bot's prints |
| `--no-strict` | Let the bot swallow its own exceptions, as it does when submitted |

### Fill assumptions matter

Same template, Prosperity 3 round 1, all three days (Kelp at `make_edge` 0.5 since 2026-10-15, on
`sized_mid` since 2026-10-18; with the earlier edge 1, `all` per tick was 81,292 and `worse` 57,774):

| Fills from | per tick (default) | `--resting` |
|---|---|---|
| book + market trades at your price or worse (`all`, default) | 72,674 | 66,558 |
| book + market trades strictly worse than your price (`worse`) | 63,302 | 63,436 |
| visible book only (`none`) | 28,217 | 30,404 |
| `all`, but only half the liquidity (`--fill-ratio 0.5`) | 40,184 | 34,461 |

Most of the default PnL comes from assuming bots would have traded with your resting quotes
instead of with each other. When comparing variants, check that the better one also wins under
`--match-trades worse`; if the ranking flips, the gain is probably a backtest artefact.

With `--resting`, a quote that joins an existing level waits behind it, so `all` loses about a
sixth. Under `worse` and `none`, fills don't depend on the queue, so the two modes are close.

## Grid search

```sh
uv run python -m arena.grid python/bots/template.py 1 \
    --grid PARAMS.KELP.make_edge=0..3 --grid PARAMS.KELP.take_edge=0..2 \
    --modes all,worse --out results/grid.csv
```

It backtests every combination of the `--grid` values on every day, in parallel (`--jobs`,
default all cores). The example above runs 78 backtests in about 6 s. Each axis is
`PATH=V1,V2,...` or an inclusive range `PATH=START..STOP[..STEP]`. `--set` and the backtest
options apply to every run, including `--vs`, which tunes the bot against rivals in the same
market. A short run of the first combination catches typos before the grid starts.

Each backtest (combination, day, mode) is its own worker task, so a small grid still uses every
core. When the axes set only some products (`PARAMS.KELP.*`), the grid first runs the bot as is
with and without the other products. If those products make the same PnL either way, every
combination runs on them alone and the others' PnL is added from the bot as is, so the summary is
the same as a full run's, faster (Kelp's 64 cells: 14 s against 25 s). `--all-products` runs
everything.

`--screen SHARE` is successive halving for big grids: every combination runs on the first day
under the first mode, and only that share of them, the best there, runs on every day and mode. On
Kelp's 256 cells (`make_edge` × `take_edge` × `clear_edge`, P3 round 1, `--modes all,worse`) it
took 20 s at 0.25 and 14 s at 0.1, against 48 s, with the same best cells and the same pick. The
summary says what the screen dropped (the best dropped cell, and failures) and how well the
screen day ranks the kept cells (Spearman against the other days; a low one means it may have
dropped good cells). The tests after it see the kept cells only, chosen on a day they include, so
they understate the selection bias; with two or more days, SPA, StepM and the pick are repeated
on the days the screen didn't see, which its choice can't bias. Order the days so the first is
typical. A cell that only does well under a later mode can be dropped, and `nbhd` only counts
kept neighbours. With `--permute`, each copy is screened the same way.

`--halving SHARE` is the same with more steps: the cells run one day under one mode at a time (the
first mode's days, then the next mode's), and after each step but the last only that share of the
cells still alive, ranked by their PnL so far (failed ones last), goes on. The summary lists each
step with the best cell it dropped. As with the screen, the tests see the kept cells only; the
unseen-days section leaves out every day a step ranked on, so it appears only when a day is left
(under one mode, the last). It doesn't combine with `--screen` or `--permute`. `--sample N` runs N
cells drawn at random from the grid (`--sample-seed`, default 0) instead of all of them, so a
product of millions is never listed; `--permute`'s copies run the same sample.

`--engine rust` runs the backtests and the statistics that grow with the cells (CSCV, the DSR's
correlation, SPA and StepM) on the Rust port (`rust/`, needs `cargo`), on `--jobs` threads, and
prints and writes the same results to the last digit. The axes, the screen and the permuted copies
stay in Python, and so do the scenarios, whose settings and rivals each task carries. It takes a
bot and rivals with a Rust twin for the run's format (`rust/twins.json`: the template in the
Prosperity format and the drill template in the drill one, the rivals, `mm` and the zoo, all
Prosperity), and refuses to run if a twin it uses was last checked against older Python code
(or never), since Rust would run that older code
(`--allow-stale` runs it anyway, with a warning; every tool and experiment with `--engine rust`
does the same). Kelp's 256 cells (`make_edge` × `take_edge`, P3
round 1, `--modes all,worse`, 1,542 backtests) took 1.3 s against 50.6 s, with the same CSV; the
grid's own work is most of the 1.3 s. 1,024 cells (`make_edge` × `skew`, 337 of them distinct) took
2.7 s against 226 s. The template's 100,000 cells (six of Kelp's and Resin's settings, P3 round 1,
`--modes all,worse`: 600,006 backtests) took 298 s on 14 cores, using at most 1.9 GB in any one
process. With `--halving 0.5` it took 96 s and 0.5 GB. It found the same best cell by `pnl`, worst
day and `worse`, and the same pick; only `nbhd` differed, since it counts only the kept neighbours. A
random 100,000 of a million cells, halved the same way, took 98 s (`experiments.rust_bench`, part 4;
`IDEAS.md`, "Kelp `make_edge` and `take_edge`"). The halved run's DSR was 1.00 against the whole
grid's 0.19: the tests see only the 3,125 cells kept, so they understate the selection bias, as the
summary says.

The highest backtest PnL is usually overfit, so each combination is ranked on four measures:

| Measure | Meaning |
|---|---|
| `pnl` | Total PnL under the first `--modes` entry |
| `min day` | Its worst single day |
| `nbhd` | Mean PnL of the combination and its grid neighbours (one step along any axis), leaving out neighbours with errors or limit breaches. A plateau beats a lone spike. |
| `pnl(<mode>)` | Total under each extra mode, e.g. `worse` fills |

```
rank  KELP.make_edge  KELP.take_edge  pnl(all)  min day    nbhd  pnl(worse)   fills
   1               1               1    81,292   25,912  75,695      57,774  19,310
   2               1               2    80,256   25,418  74,064      54,776  18,467
   ...
best by pnl      KELP.make_edge=1, KELP.take_edge=1  (81,292)
best by nbhd     KELP.make_edge=1, KELP.take_edge=1  (75,695)
best by min-day  KELP.make_edge=1, KELP.take_edge=1  (25,912)
best by worse    KELP.make_edge=0, KELP.take_edge=1  (63,054)
measures disagree: prefer a setting near the top on every measure over the single best pnl
```

With two or more days, the summary also holds out each day in turn. The best combination by
PnL on the other days is scored on the day left out, from the runs already done. The total is
what choosing by PnL earns on days the grid didn't see, and its gap to the best combination is
the grid's selection bias. On Kelp above there is none: every day picks the same setting. On P4
rounds 3–4, for Velvetfruit's level bet with its vouchers (`level_band` × `clear_edge`), it is
−14%:

```
held-out days: the best pnl(all) on the other days, scored on the day left out
  r3d0: VELVETFRUIT_EXTRACT.level_band=30, VELVETFRUIT_EXTRACT.clear_edge=2  279,418  (best combination: 279,418)
  r3d1: VELVETFRUIT_EXTRACT.level_band=30, VELVETFRUIT_EXTRACT.clear_edge=2  174,596  (best combination: 174,596)
  r3d2: VELVETFRUIT_EXTRACT.level_band=20, VELVETFRUIT_EXTRACT.clear_edge=3  142,519  (best combination: 284,464)
  r4d3: VELVETFRUIT_EXTRACT.level_band=30, VELVETFRUIT_EXTRACT.clear_edge=2  262,606  (best combination: 262,606)
held out 859,139 against 1,001,084 for the best combination (-14%); 2 different settings chosen over 4 days
```

This only covers the gridded values. A setting the bot takes from the data itself, such as a
level from the days' mean, needs its own held-out test (`python/experiments/p4_level_template.py` does
both). Days whose data repeats are flagged, product by product, since holding one out still trains on its
copy. Prosperity reuses days across rounds: P4's round 4 days 1–2 are round 3's, and P3's round 3
days 0–1 are round 2's for every product round 2 had. It reuses them across editions too, under a new
name: P3 round 1's `RAINFOREST_RESIN` has the same books on all three days as P2 round 1's `AMETHYSTS`.
The check matches product names, so it can't see that.

Last, the summary says how far the choice can be trusted. Each run's PnL is cut into blocks of
ticks within days (about 16 in all), and cells whose block PnL is identical count once:

- **PBO** (Bailey et al.'s probability of backtest overfitting, by CSCV): over halvings of the
  blocks, how often the best cell on one half ranks at or below the median on the other. Near 50%
  the pick carries no information.
- **DSR** (Bailey and López de Prado's deflated Sharpe ratio) of the best cell's gain over the bot
  as is, block by block: the chance that the gain beats the best of that many cells with no gain,
  their number discounted by how correlated their gains are. Below 0.95 the summary warns.

On P3 round 1, Kelp's `make_edge` × `skew` gets PBO 0% and DSR 1.00 against the committed edge;
Osmium's (P4 rounds 1–2) gets PBO 0% but DSR 0.00, since its best cell gains nothing real over the
bot as is; its `smoothing` grid gets PBO 43%, since which of 0.5–0.95 wins is noise, though any of
them beats none (DSR 0.98 against the template before smoothing). Halvings mix blocks of the same
days, so a change between days is invisible to both: that is what the held-out days check.

Then two bootstrap tests, on each cell's gain over the bot as is per block of 100 ticks (about
100 a day), with Politis and Romano's stationary bootstrap (blocks of 1,000 ticks on average,
1,000 resamples):

- **SPA** (Hansen's test for superior predictive ability): the p-value that no cell beats the bot
  as is. Unlike the DSR, it discounts cells that are clearly worse, so a wide grid's poor corners
  don't hide a real gain. Kelp's 64-cell `make_edge` × `take_edge` grid gets DSR 0.76 but SPA p 0.000,
  and on the days the grid never saw the gain held (`references/wiki/contradictions.md`, row 18).
- **StepM** (Romano and Wolf's step-down test): every cell that beats the bot as is, with the
  chance of naming even one false cell held at 5%. Each is then checked under the other `--modes`.
- **pick**: StepM's best cell that beats the bot as is under every mode, else the bot as is. Ten
  ways of choosing a cell were scored on unseen days. On Prosperity's (`python/experiments/selection_rules.py`)
  it was the only one that never lost money under either fill mode. On fresh simulated days
  (`python/experiments/selection_rules_sim.py`) it lost in 2 of 120 runs, where the rules that gained as
  much lost in 10 to 22. From the template's defaults it found most of the gain the best cell on
  those days had.

```
overfitting: 64 cells × 2 modes = 128 trials on 3 days
  CSCV on pnl(all) in 18 blocks (6 a day), 12 distinct cells, 4,000 of 48,620 halvings:
  PBO 0%  ·  the pick's mean rank out of sample 0.92 (1 top, 0.5 median)  ·  it loses money there in 0%
  DSR 0.76 for the best cell's gain over the bot as is: per-block Sharpe 5.75 against 5.09, the best of N^ 8.5 cells with no gain
! the best cell's gain over the bot as is is not clearly more than the best of that many cells with no gain (DSR < 0.95)
  SPA on pnl(all) gains over the bot as is, 300 blocks of 100 ticks, 12 distinct cells, bootstrap blocks of 1,000 ticks on average, 1,000 resamples:
  p 0.000 that no cell beats the bot as is (bounds 0.000 to 0.000; the upper is the Reality Check)
  StepM at 5%: 3 cells beat the bot as is: KELP.make_edge=1, KELP.take_edge=1 | ...
! SPA finds a gain the DSR doesn't: the DSR's bar rises with the spread of all cells, poor ones included, and SPA discounts those (references/wiki/contradictions.md, row 18)
  under worse: 0 of StepM's 8 cells beat the bot as is (best by -5,537)
! StepM's cells only beat the bot as is under all: the gain depends on the fill model
  pick: the bot as is: no StepM cell beats it under every mode
```

`--permute N` adds a permutation test of the whole search, after Masters' (our adaptation: the
book isn't read). The grid is rerun on N copies of the days made of their own ticks in a shuffled
order (`arena.stress.permute`). Each tick keeps its book, its trades and its wall bid's real move,
and is shifted to continue from the tick before it; `--permute-block` shuffles in runs of that many
ticks, keeping the order inside a run. Two statistics of the search, on the PnL of the products the
axes set, are ranked among the copies': the best cell's PnL, and its lift over the median cell. A
small p for the lift says choosing exploits the order of the ticks (a trend, a level the price
returns to, a signal that leads it). A large one says a search this wide finds as much without it,
from each tick's book and the fill model, so check the pick under `--modes worse`. Neither is
measured against the bot as is, whose settings were tuned to the real order. Each copy reruns the
whole grid under the first mode, so 19 copies (the fewest for p 0.05) cost about 19 grids.

`--scenario NAME:ITEM,...` adds a fill model to the `--modes`, scored like a mode (its own
`pnl(NAME)` column, in the held-out days, and in the pick, which must beat the bot as is under every
one). Each item changes one engine setting from the run's own: `match=all|worse|none`,
`resting` (or `resting=no`), `queue=back|prob|front`, `power=N`, `fill=RATIO`, `seed=N`. A
`vs=FILE[@PATH=VALUE...]` item (repeatable) gives the scenario its own rivals in place of `--vs`, with
`--set`-style overrides, and `vs=none` runs it alone:

```sh
uv run python -m arena.grid python/bots/template.py 1 --grid PARAMS.KELP.make_edge=0.5,1,1.5,2 --modes all,worse \
    --scenario rest:resting,queue=prob --scenario thin:fill=0.5 --scenario war:vs=python/bots/template.py@PARAMS.KELP.make_edge=0 --engine rust
```

With a scenario, the summary also gives each cell's `worst` PnL over them all (`--sort worst`, and
a `worst` column in `--out`). That is a measure to read, not a rule: chosen by it, cells lost money
most often of five rules on unseen Prosperity and simulated days, while the pick lost least
(`IDEAS.md`, "Choosing a cell by its worst case over fill-model scenarios"). Grid under the
scenarios the playground probes leave possible, and take the pick.

An axis whose values never change any working combination's PnL, with the other axes held fixed, is flagged: a typo'd key (`--set` accepts a new one) or a setting another one overrides. `arena.compare` flags a variant that makes exactly its baseline's PnL the same way. `--sort` ranks the table by another measure. `--out` writes every combination to a CSV:
per-mode totals, `min day` and `nbhd`, then per-day and per-product PnL. Combinations with errors
or limit breaches are left out of the summary's picks and of the heatmaps, and the grid exits with 1
if every combination failed.

## Compare bots

`arena.grid` varies settings inside one file. `arena.compare` runs several bot files, or variants of
them, against one baseline, with the same checks:

```sh
uv run python -m arena.compare python/bots/template.py 1 --bot python/bots/zoo/claude/*.py --modes all,worse
uv run python -m arena.compare python/bots/template.py 1 --bot python/bots/mine.py "python/bots/template.py@PARAMS.KELP.make_edge=1@PARAMS.KELP.take_edge=2"
uv run python -m arena.compare python/bots/template.py 1 2 --data p4 --resting --bot python/bots/a.py python/bots/b.py --vs python/bots/rivals/sniper.py --out results/compare.csv
```

- **The baseline** is the first bot, the bot as is. `--set` applies to it alone.
- **Each `--bot`** is a file, or `FILE@PATH=VALUE@...` for a variant. It takes several, so a shell glob works. `NAME:FILE@...` names a variant in the tables; without a name, a value over 16 characters (a whole product's dict) is cut in its label, and the summary lists such variants' settings in full.
- **One worker task per (bot, day, mode),** so even a few bots use every core. Every bot trades against the same `--vs` rivals.
- **`--scenario`** works as in the grid: a fill model with its own engine settings and rivals, a `worst` column, and the pick checked under each.
- **The summary:**
  - a ranked table (PnL, the gain over the baseline, worst day, each extra mode, fills);
  - PnL per product, the ten products with the most at stake;
  - each day held out;
  - the grid's overfitting lines, ending with the pick: StepM's best bot that beats the baseline under every mode, or the baseline.
- **A bot that fails to load, raises or breaches a limit** is flagged with its first error and left out of the picks. The command exits with 1 only if every bot does.

## Charts and fill statistics

```sh
uv run python -m arena.backtest python/bots/template.py 1 --out results/run
uv run python -m arena.analysis results/run                              # every day in the folder
uv run python -m arena.analysis results/run r1d0 --start 300000 --end 330000
uv run python -m arena.analysis results/run --reference wall_mid            # measure fills against the wall mid
uv run python -m arena.analysis --grid results/grid.csv                  # heatmaps
```

This saves PNGs to `plots/` next to the input (`--dark` for a dark theme) and prints four tables per day, plus the market-trade table pooled over all days.
The notebook does the same steps interactively, through the same functions in `python/arena/analysis.py`.

- **PnL:** total and per product over the day.
- **Product:** price (the mark, and the wall mid dashed) with the book spread and your fills, then position against the limit, then PnL. Blue ▲ marks buys and orange ▼ marks sells; solid means you took liquidity, hollow means a resting quote was filled. In a short window (≤ 1,500 ticks) your quotes are drawn too.
- **Fills table:** fills, volume and bought/sold per product, split into took vs passive. `edge` is the average profit per unit against the mid one tick before the fill. It isn't measured against the mid at the fill tick, because an order you take is part of that tick's book and drags the mid toward its own price.
- **Markouts:** the mid 1–500 ticks after each fill, minus the fill price (flipped for sells), per unit. Flat lines mean fills keep their value. Falling lines mean the market moves against you after you trade, i.e. adverse selection.
- **Reference price (`--reference`):** the fills table, markouts and PnL split measure against the mark (the data's mid) by default, or against the wall mid, the midpoint of the largest level on each side. On Prosperity data the mid is mostly noise at one tick, so markouts against it mix that noise into adverse selection.
- **PnL split:** per product, spread captured on taken and passive fills, plus inventory carried through price moves (and, against the wall mid, the end position's gap between mark and wall mid). The parts add up to the PnL exactly. Against the mark, taking can look like a loss because the taken order skews that tick's mid.
- **Market trades:** for the data's trades (buys at the ask, sells at the bid), what the taker paid against each reference and how far that reference moves in the trade's direction 1–50 ticks later. A move that stays above zero means trades carry information.
- **Grid heatmap:** one metric over two parameters, with the best cell outlined. With more than two parameters, each cell shows the best value over the rest.

## Validate before submitting

```sh
uv run python -m arena.validate python/bots/template.py 1
uv run python -m arena.validate python/bots/my_bot.py 1 --allow numpy --time-limit-ms 900
```

It fails (exit code 1) on:
- a syntax error, or a missing entry point (`class Trader` with `run`)
- imports from outside the standard library that aren't listed in `--allow`
- any exception, or malformed orders (e.g. float prices)
- orders the engine cancels for possibly breaching a position limit
- a tick slower than `--time-limit-ms`

It warns about:
- use of environment variables, files, subprocesses or the network
- results that change on a repeat run, or when the first day is replayed in two other Python processes with other hash seeds (`PYTHONHASHSEED`), which catches a bot that iterates a set of strings: the organisers rerun the top bots, and such a bot wouldn't reproduce
- results that change when the bot is reloaded every tick, which means it keeps state outside `traderData` that the real engine may not preserve
- settings that can't matter, if the bot lists them (the template's `param_conflicts`): two target modes on one product (the first in `trade_product`'s order wins), a static `target` that a mode replaces, or a mode's own setting while the mode is off

## How the engine works

`python/arena/engine.py` replays a day tick by tick, using the rules from IMC Prosperity:

1. The bot sees the book and returns orders.
2. If a product's orders could breach its position limit (all buys, or all sells, filling), every order for that product is cancelled.
3. Each order trades against the visible book at the book's prices, best price first.
4. What's left can fill against that tick's market trades, at the order's own price (`--match-trades`).
5. Anything still unfilled is cancelled. No order rests into the next tick.

Positions are valued at each tick's mid price.

The fills matched jmerle's `prosperity3bt` 0.12.0 exactly in 15 comparisons: 5 days, with all
three trade-matching modes on each. Those days include round 5, with all 15 products and books
that are sometimes empty on one side. `python/tests/test_parity.py` pins 6 of them: round 1 day 0 and
round 5 day 2, in each mode.

### Resting mode

A realistic exchange keeps orders open until they fill or you cancel them. That was the case in
AlgoTrade 2026 (`references/algotrade2026-pitfa19/.firecrawl/algotrade-api.md`), and it may be
the case at the Arena. `--resting` replaces rule 5 with that:

- **New orders:** each one takes what it can from the visible book (rule 3), then the rest rests on the book. An `ioc` order is cancelled instead.
- **Queue:** a resting order joins the back of the queue. The visible volume at its price is ahead of it, and a price better than the best level puts it at the front.
- **Fills from trades:** market trades at its price first use up the volume ahead of it, then fill it. Trades at a worse price fill it straight away. `--match-trades worse` drops fills at its own price and `none` drops trade fills altogether.
- **Fills from the next book:** if the next snapshot shows the other side at or through its price, those orders would have traded with it. It fills at its own price (source `cross`), and the bot sees the snapshot without that volume. That tick's market trades at the crossed prices lose the same volume, since they traded with the same orders.
- **Moving up:** if the visible volume at its price drops below the volume counted ahead of it, orders ahead were cancelled, so it moves up. An emptied level puts it at the front.
- **Queue models (`--queue`):** that rule is `back`, the pessimistic end: every cancellation is behind you. `prob` splits each drop of the level that trades don't explain: a share `xⁿ` comes from ahead of you, `x` being your share of the queue ahead and `n` `--queue-power` (hftbacktest's `ProbQueueModel` with `PowerProbQueueFunc3`; 1 is uniform, a large `n` tends to `back`). `front`, the optimistic end: everyone else at your price re-posts every tick, behind you, so nothing is ahead of you from the snapshot after you joined. Position in the queue only matters under `--match-trades all`.
- **Limits:** the limit check counts resting orders, and only rejects that tick's new orders.
- **Self-trades:** your own orders never trade with each other.

In the Prosperity format, bots see their resting orders in `state.open_orders` (each has an
`id`). They cancel one by returning `Cancel(order_id)` in its product's order list, and send
`Order(symbol, price, quantity, ioc=True)` for an order that mustn't rest. These are our
extensions to the datamodel. A bot written for per-tick cancellation never cancels, so it keeps
adding orders until every new one breaches the limit.

Template, Prosperity 3 round 1, all three days, `--resting`, `--match-trades all`:

| `--queue` | Template | Kelp at `make_edge` 1 |
|---|---|---|
| `back` (default) | 66,558 | 67,450 |
| `prob`, `--queue-power 1` | 66,562 | 68,058 |
| `prob`, `--queue-power 5` / `20` | 66,558 | 67,474 / 67,450 |
| `front` | 67,070 | 74,918 |

The template quotes one tick inside the best price, where it is usually alone, so its queue barely
matters; a quote that joins a level does depend on it. In `arena.sim`, where the market maker
re-posts its walls every tick, `front` is closest to what the bot makes in the market
(`IDEAS.md`, "Queue models against a market that re-posts"). `prob` stays near `back` there: a
level that is re-posted at the same size shows no drop to split.

### Shared market

`--vs BOT` puts more bots in the market: copies of yours (give the same file again) or other
versions. `--set` only applies to your bot. Rivals' results are summarised under each day.
This models a market shared by all teams much better than `--fill-ratio`:

- **Same view, random arrival:** every tick all bots see the same market and decide at once. Their orders then reach the exchange in a random order, seeded and drawn again each tick.
- **Trading with each other:** a new order trades with the recorded book and with the other bots' orders, best price first. At one price the recorded volume goes first. Fills are at the price of the order that was there first.
- **Market trades:** what's left of the bots' orders meets the tick's market trades best price first, then oldest, whoever arrived first, in both modes (until 2026-10-23 the per-tick mode took them in arrival order, so a worse bid could beat a better one to a trade; the per-tick rival results were re-run then). A bot alone keeps prosperity3bt's rule: its orders take the trades in the order it sent them.
- **What each bot sees:** the book includes the other bots' resting orders, never its own. Trades between other bots appear among its market trades, named after the bot files (`template`, `template#2`, ...).
- **Rivals written for Prosperity:** their orders were meant to live one tick, so they never cancel, and under `--resting` their orders pile up until every new one breaches the limit. `--requote` makes every rival cancel its resting orders before each tick.
- **Races:** another bot can fill one of your orders after your bot decided. If your new orders then no longer fit the limit, they are rejected and counted as a race, not a limit breach. A cancel for an order that filled in the meantime does nothing.

Template against copies of itself, Prosperity 3 round 1, all three days (Kelp at `make_edge` 0.5, `sized_mid`; per tick re-run 2026-10-23 after market trades went best price first, when one copy made 42,033 + 42,304):

| Market | per tick (default) | `--resting` |
|---|---|---|
| alone | 72,674 | 66,558 |
| with one copy | 41,352 + 41,848 | 26,904 + 25,322 |
| with two copies | 27,460 + 28,970 + 29,515 | 13,161 + 14,568 + 19,044 |

The two copies together make more than one alone in the default mode, because each has its
own position limit. They also get extra fills: when one beats the other to an ask, the other's
take order is left at that price for the rest of the tick, where market trades can fill it.

Rivals change which settings win. With `--resting`, Kelp `make_edge=0` is the best setting
under `worse` fills when trading alone. Against one copy of the baseline it loses 4,920 (10,980
under `worse`). Its quotes at fair get crossed by the next snapshot, and the rival picks them
off: the rival's `wall_mid` treats your large quote as the market maker's level. Against the teams' own P4 bots the same trap cost the template 374k on Osmium in one round, and `fair: sized_mid` turned that into +17k (`IDEAS.md`).

**Adversarial rivals** (`python/bots/rivals/`, for `--resting`): `trapper.py` baits with a large order
one tick inside the best and sells into whoever steps in front of it (Harris); `spoofer.py` rests
a large order `OFFSET` ticks behind the best and takes what that mispricing brings; `sniper.py`
takes any order left through its fair; `taker.py` takes at the touch, on momentum and at random
(seeded draws that don't depend on the other bots). `uv run python -m experiments.adversaries` runs the
template against each. On P3 round 1 the trap and the near spoof barely cost it; a large order 10
ticks behind the best took Kelp from 16.8k to −2.1k through `wall_mid`, and `sized_mid` is immune
(`IDEAS.md`, "Adversarial rivals").

`uv run python -m experiments.rival_field --engine rust` puts candidate settings against fields of
these archetypes, `mm.py` at three edges and a copy, per tick and resting, and prints the payoff
matrix, the best reply to each field, and the max-min and mean choices. On P3 round 1 the best
reply changed with the field, and the reply to one copy was neither of the two robust choices
(`IDEAS.md`, "Our settings against a field of rival archetypes").

`uv run python -m experiments.leaderboard_curves --engine rust` asks whether the leaderboard's PnL curves, which
the portal shows for every team after each deadline, tell how the private run was played: each team on data
of its own, alone on the same data, or in one market. On simulated fields whose answer was known, the
correlations of pairs of curves' changes told them apart in 88 of 90 cases; on the day, `--read FILE --team NAME`
reads the saved leaderboard (`IDEAS.md`, "Reading the leaderboard's curves").

`uv run python -m experiments.quote_inside --engine rust` tests `make_inside` against rivals that quote nearer
fair than the template's one tick inside the book. Per tick nobody's orders rest, so the template can't see
them, and with price priority they take the trades first. On Resin, `make_inside` 3 took the template from
5.7k to 24.8k in a field of 12 zoo bots, for 4–10k alone; with resting orders the template already steps in
front of the quotes it sees (`IDEAS.md`, "Quoting nearer fair than one tick inside the book").

## The engine in Rust

`rust/` is a Rust port of the engine, `arena.sim`'s market, the template, the rivals, every zoo bot and `python/bots/mm.py`, each with its Python file as a twin that must trade the
same (`rust/README.md` has the table of what is in Python, in Rust, and in both). `uv run python -m experiments.rust_bench` builds it
(needs `cargo`), then checks every recorded field against our engine:
- 15 engine configurations with `mm`;
- every part of the template's STRATEGY, alone and with a rival;
- 10 real days from P2 to P4;
- the rivals;
- every zoo bot alone and all 32 with the template in one market, on calm and trending days;
- `arena.sim`'s market with and without them in it, and their replays.

Then it times both. On P3 round 1, one core, per day, the template as committed takes 577 ms in Python and 4.5 ms in Rust (129×);
`mm` takes 208 ms against 1.5 ms; the template and the whole zoo in one market take 27.5 s against 0.34 s; an `arena.sim` day with the template in it, 977 ms against 29 ms.

Every tool that runs our bots takes `--engine rust`: `arena.backtest`, `arena.grid`, `arena.compare`,
`arena.stress`, `arena.sim` and the experiments. Each prints and writes what the Python engine does (a
Rust bot has no step timings, so a report leaves out the bot-timing line). The Rust bots take their settings from the Python file, so `--set` reaches both. `rust/twins.json` records the hash of each Python
twin's code as last checked (comments, docstrings and the settings Rust reads from the file don't count), and `python/tests/test_rust.py` fails when its code changes until `uv run python -m experiments.rust_bench --parity-only
--record` has checked the pair again. The submitted bot stays a Python file.

## Stress

`arena.stress` reruns a bot on perturbed copies of each day: each product's whole book, trades and
mark moved together, so only the price path changes. The perturbations: volatility ×2 (every move of the price doubled; the spread keeps its width, so the market is tighter relative to its moves), a trend
each way, a level shift at mid-day each way, a 100-tick spike each way, and the walls removed for
the middle fifth. Each is sized in the product's median spread and moves prices by whole ticks. It prints each product's PnL under each one, its largest plain-day drawdown
(what a loss stop must leave room for) and its worst single day.

```sh
uv run python -m arena.stress python/bots/template.py 1                 # P3 round 1, every perturbation
uv run python -m arena.stress python/bots/template.py 1 2 3 4 --data p4 --only trend_up,trend_down --size 2
```

On P4 rounds 1–4 a trend up turns the template's 2.27M into −0.32M: the level bets and the vouchers
keep betting on a price that has left. The per-product `stop_loss` bounds each day's loss without
changing the plain days (`IDEAS.md`, "Stress: what a regime change costs" and the rows after it).

## Simulated market

The engine replays a recording, so the market never reacts to your orders. `arena.sim` is a
small agent-based market that does: a take moves the price, the market maker can skew against
the flow it receives, and every seed is a new day. Per product and tick, the fundamental moves
(a level it reverts to, steps, drift, jumps that may snap back). Then the market maker re-quotes
its walls and small limit traders post near the fundamental. Then the book is snapshotted and
the bots trade. Then noise, value and momentum takers arrive and trade against the book, bots'
orders included. Its module docstring has the details. Three presets, `KELP`, `RAINFOREST_RESIN`
and `SQUID_INK`, are calibrated so that `arena.diagnose` sees P3 round 1 in them, and named so the
template trades them as it is; they are the default market. Three more are chosen with `--products`:
`HYDROGEL_PACK` returns to a level as P4's Hydrogel does; `KELP_FLOW` is Kelp with P3 round 1's
one-sided takers (35% of trades are buys, larger than the sells), which push a two-sided quote long;
`ROBOT_DISHES` jumps by 100 in bursts that mostly go straight back, as on P4 round 5's day 4. `--regime shift_up` (or `shift_down`,
`trend_up`, `trend_down`; `--regime-at`, default mid-day) changes every product's regime during the
day, as Qminers' 2024 final did: a shift of 5 wall spreads, or a trend of 10 over the rest of the
day. Unlike `arena.stress`'s moved recordings, the market reacts to it.

```sh
uv run python -m arena.sim generate data/sim --days 5            # Prosperity layout, plus limits.json and the fundamental
uv run python -m arena.backtest python/bots/template.py 1 --data data/sim
uv run python -m arena.sim run python/bots/template.py --days 5        # the bot in the market, against replaying the same days
uv run python -m arena.sim run python/bots/template.py --spec KELP.maker.skew=0.05 --resting
uv run python -m arena.sim run python/bots/template.py --products KELP,RAINFOREST_RESIN,HYDROGEL_PACK --regime trend_up
```

`--spec PATH=VALUE` changes any preset field, e.g. `KELP.fundamental.sd=0.3` or `KELP.limit_traders.rate=2`.
`run` prints each product's PnL in the market next to replaying the same seed's recording, without the bot, in each `--match-trades` mode. Both commands run one day per worker (`--jobs`, default all cores). `run --format` loads the bots through another format, such as `drill`.
`--engine rust` runs the market in `rust/src/arena/sim.rs` (bots with a Rust twin): the same days and output, without the bot-timing line.
The recording and the run share every random draw, so the gap is the market's reaction to the bot.

The template over seeds 0–4 (`IDEAS.md`, "Replay against a market that reacts"):

| Product | replay `all` | replay `worse` | replay `none` | in the market |
|---|---|---|---|---|
| Kelp | 37,090 | 12,138 | 0 | 13,478 |
| Kelp, `--resting` | 25,678 | 12,138 | 5 | 36,329 |
| Resin | 105,242 | 101,690 | 34,024 | 115,131 |

What it doesn't match: the takers' signs don't persist (`C(1)` about 0, against 0.1 in P3), the flow is balanced (P3's Kelp is 35% buys), and takers pay more against the wall mid (Kelp 1.3, against 0.9).

## The bot template

`python/bots/template.py` is one file in five sections:

- **PARAMS:** per-product settings. Products not listed aren't traded. Keys missing from a product's entry come from `DEFAULTS`.
- **STRATEGY:** format-agnostic. Each product goes through four steps:
  - **Fair value:** fixed, mid, `wall_mid`, `outer_mid`, `sized_mid` (the default for a product whose PARAMS don't set `fair`) or `weighted_mid`. `imbalance` quotes around the fair plus a multiple of the best-level imbalance (the linear micro-price); it and `weighted_mid` lost on Prosperity data, so neither is used (`IDEAS.md`). `wall_mid` is the midpoint of the largest-size level on each side, which is how the top Prosperity teams found the market-maker bot's price. `outer_mid` takes the outermost levels. `sized_mid` takes the first level from the top with at least `wall_size`. It is the only one of the three that holds up when other traders' resting orders share the book (see [Shared market](#shared-market)).
  - **Take:** trade against book orders at least `take_edge` better than fair.
  - **Clear:** cut inventory at fair to free room under the limit.
  - **Make:** quote `make_edge` from fair, or `make_inside` ticks inside the book (1; `None` quotes at `make_edge` whatever the book, against rivals nearer fair), moved by `skew` against inventory, with sizes scaled by `size_skew` (both work toward `target`).
  - **The close** (optional): from `flatten_from`, every product works its position to zero: no takes, `clear` crosses up to the spread, and `make` quotes only the side that reduces it. For an exchange that liquidates open positions at a bad price; over the last 200 ticks it cost 1.7–3.3% of a Prosperity day valued at the mid (`IDEAS.md`).
  - **Level** (optional): for a product that returns to a price `level`, the target becomes the full limit against any move of `level_band` from it, held until the other band (or until the price comes back within `level_exit` of the level, or past it). `clear` then crosses the spread toward it, up to `clear_edge` worse than fair. Set `level` from the earlier days' mean, or `"day"` when there is no history. On P4 rounds 3–4 it makes about 52k a day on Hydrogel and Velvetfruit when scored on days it wasn't tuned on, against 15k for plain market making (`IDEAS.md`). `cpd_*` adds online changepoint detection on the level (Adams & MacKay): it finds shifts and trends, but neither re-estimating the level nor dropping the bet paid on Prosperity data, so it is off.
  - **Follow** (optional): a call option on another product (`follow`, `strike`) holds that product's target as a share of its own limit, so it adds its delta to the same bet. A strike whose half-spread per unit of delta is above `max_cost_per_delta` stays flat. Delta comes from the option's own price through Black–Scholes in total variance, so no expiry date is needed. `Trader.run` trades the followed product first and hands its plan over. On P4 the vouchers following Velvetfruit add about 165k a day out of sample (`IDEAS.md`).
  - **Basket** (optional): a product that is a known combination of others (`basket`: `{leg: weight}`) trades its spread, its price less the legs' weighted prices, with the level settings: `level` is the usual spread. A family that sums to a constant is a basket with legs of weight −1. Legs with `hedge` hold `-weight × hedge_ratio` per basket held, though hedging never helped on Prosperity data. On P3 round 2 and P2 round 3 it makes 71k and 294k over three days out of sample, against 20k for plain market making. Baskets only take (`make_size` 0): under `--resting`, quotes on a product that jumps several ticks at once get picked off.
  - **Jump** (optional): for a price that jumps and snaps back, the target becomes the full limit against each move of at least `jump_min`, held until the next one (or for `jump_hold` ticks), crossing up to `jump_edge` toward it. It only trades once `jump_seen` of the day's jumps have followed another and `jump_share` of those reversed it, so it can be switched on for every product. On P4 round 5 that added 501k over three days to plain market making, in-sample, with no losing day (`IDEAS.md`).
  - **Copy** (optional): follows named traders. `copy` is `{name: weight}`: each trade adds the buyer's weight and takes away the seller's, and the target becomes that share of the limit (capped at the full limit), held until the next signal (or for `copy_hold` ticks), crossing up to `copy_edge` toward it. It reads the counterparties of our own fills too. On P3 round 5, copying Olivia on Croissants and Squid Ink adds 54k over three days out of sample; on Kelp it loses (`IDEAS.md`).
  - **Protection** (optional): `stop_loss` flattens a product and stops it for the day once its PnL is that far below the day's high; `fixed_guard` lets a fixed fair give way to the sized mid once the market has left it; `level_guard` and `vol_guard` drop the target bets when the price leaves the level's range or volatility jumps (both off: they cost more than they saved under `arena.stress`).
- **EXECUTION:** format-agnostic order management. Takes go out immediate-or-cancel. A resting quote is kept, with its place in the queue, while the plan still wants at least its size at its price. Everything else is cancelled and re-sent. When nothing rests between ticks, every planned order is simply sent, so the same file works under both engine modes.
- **ADAPTER:** the only part that knows the Prosperity types.
- **Trader:** the entry point. It isolates each product, so one product's bug doesn't stop the others. It keeps all state in `traderData`, and it swallows exceptions unless `STRICT` is set. The backtester sets `STRICT` so errors show up.

## The LLM zoo

`python/bots/zoo/` holds bots that language models wrote from a Prosperity-style spec alone: the
baseline an agent-using team starts from, and rivals for `--vs`. `uv run python -m
experiments.zoo` scores each one alone, against the template, inside `arena.sim` and all
together. `python/bots/zoo/README.md` explains how to add bots from other providers (Gemini,
ChatGPT, ...) cleanly. On P3 round 1, the best Claude-written market makers come close to the template
alone on Kelp and Resin and beat it head to head, all of it on Squid Ink, which the template
doesn't trade. `uv run python -m experiments.zoo_h2h` splits each pairing by product and fill
mode (`IDEAS.md`, "The LLM zoo" and "Why the zoo beat the template head to head").

## On the day: adapting to the real format

Start from [`RUNBOOK.md`](RUNBOOK.md), one page of the day's commands; the steps below are the format swap in detail.

1. **Work through [`ON_THE_DAY.md`](ON_THE_DAY.md).** It lists what to find out first (entry point, order handling, limits, whether orders rest, whether the book shows your own orders, the runtime), what each answer changes here, and probes for answering them in the playground. `python/bots/probe.py` runs most of the probes in one run: rewrite its ADAPTER like the template's, and read its `PROBE` lines (`uv run python -m arena.backtest python/bots/probe.py 1 --print --no-strict` shows what our engine answers).
2. **Write `python/arena/formats/qminers.py`**, using `drill.py` as the model, and register it in `python/arena/formats/__init__.py`. `drill.py` is a practice format deliberately unlike Prosperity's: JSON events of book changes, decimal prices with a tick per product, a callback API with calls for orders, opaque order ids, orders that rest. Every place it had to differ is marked "Unlike Prosperity". It needs a loader into `Day`/`Tick` and a bot wrapper that builds their view and converts orders back. `ON_THE_DAY.md`, "The format swap, step by step", is the checklist.
3. **Update the bot:** rewrite its imports, PARAMS and ADAPTER section, and leave DEFAULTS, STRATEGY and EXECUTION alone. `python/bots/drill/template.py` is the worked example: it is the template with only those parts rewritten for the drill API, and on the same simulated days it makes the same PnL as the template, to the cent (`python/tests/test_drill.py`).
4. **Validate** with `--format qminers`, their time limit, and `--allow` for their libraries.

Practise it: `uv run python -m experiments.format_drill <folder>` makes drill data from simulated days, then any tool runs with `--format drill --data <folder>/drill`.

## Known gaps

- **The simulated market is one guess at a design** (`arena.sim`). Its agents are the literature's minimal set, calibrated to P3 round 1's statistics, not to how the Arena's bots behave.
- **The queue model is an estimate.** By default you join the back of the queue and only move up when the visible volume shrinks. `--queue prob` and `--queue front` bracket it, but none of them sees individual orders, so a level re-posted at the same size looks unchanged to `prob`. Orders priced beyond the visible depth keep their last queue estimate.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **Rivals are only the bots you bring.** `--vs` shows how bots like yours interact, but real teams will quote, size and react differently.
