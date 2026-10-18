# Qminers Algo Trade Arena prep

Tooling for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague): a backtester, a
parameter grid search, charts and fill statistics, a pre-submission validator and a
single-file bot template. Until the real API is known,
everything runs on IMC Prosperity data and its bot format as a stand-in.

| Path | What it is |
|---|---|
| `arena/` | Backtesting engine; the `diagnose`, `backtest`, `grid`, `analysis` and `validate` commands; format plug-ins under `arena/formats/` |
| `bots/template.py` | Single-file market maker to copy for each round |
| `bots/probe.py` | The first-hour probe bot: runs the probes in `ON_THE_DAY.md` and prints what it finds |
| `bots/drill/template.py` | The template with its ADAPTER rewritten for the drill format, the worked example of the format swap |
| `notebooks/analysis.ipynb` | Backtest → PnL, fills, one product's fills against the book, markouts, PnL split, market-trade impact, grid heatmaps |
| `references/` | Reference repos and the Prosperity data; see [references/README.md](references/README.md) |
| `literature_md/` | Market-microstructure papers and books as markdown with LaTeX equations, for learning the theory; see [literature_md/README.md](literature_md/README.md) |
| `tests/` | Unit tests, plus a regression test pinned to jmerle's backtester |
| [`ON_THE_DAY.md`](ON_THE_DAY.md) | What to find out about the real Arena at the event, and what each answer changes here |
| [`TODO.md`](TODO.md) | Prep work left before the event |

## Setup

```sh
references/clone.sh   # reference repos + Prosperity data (~2 GB)
uv sync               # the engine needs only the standard library; dev adds pytest, pandas, matplotlib
uv run pytest
uv run --group analysis jupyter lab notebooks/analysis.ipynb   # optional: Jupyter
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
uv run python -m arena.backtest bots/template.py 1                  # Prosperity 3 round 1, every day
uv run python -m arena.backtest bots/template.py 1-0 --data p2      # Prosperity 2 round 1, day 0
uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2
uv run python -m arena.backtest bots/template.py 1 --out results/   # per-day CSVs for arena.analysis
uv run python -m arena.backtest bots/template.py 1 --vs bots/template.py   # against a copy of itself
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
| `--fill-ratio R` | Only this share of each book level and market trade is available to you, a rough stand-in for other teams competing for fills. Seeded with `--seed`. |
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
uv run python -m arena.grid bots/template.py 1 \
    --grid PARAMS.KELP.make_edge=0..3 --grid PARAMS.KELP.take_edge=0..2 \
    --modes all,worse --out results/grid.csv
```

It backtests every combination of the `--grid` values on every day, in parallel (`--jobs`,
default all cores). The example above runs 78 backtests in about 6 s. Each axis is
`PATH=V1,V2,...` or an inclusive range `PATH=START..STOP[..STEP]`. `--set` and the backtest
options apply to every run, including `--vs`, which tunes the bot against rivals in the same
market. A short run of the first combination catches typos before the grid starts.

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
level from the days' mean, needs its own held-out test (`experiments/p4_level_template.py` does
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

```
overfitting: 12 cells × 2 modes = 24 trials on 6 days
  CSCV on pnl(all) in 18 blocks (3 a day), 12 distinct cells, 4,000 of 48,620 halvings:
  PBO 0%  ·  the pick's mean rank out of sample 0.80 (1 top, 0.5 median)  ·  it loses money there in 0%
  DSR 0.00 for the best cell's gain over the bot as is: per-block Sharpe 0.05 against 1.20, the best of N^ 5.9 cells with no gain
! the best cell's gain over the bot as is is not clearly more than the best of that many cells with no gain (DSR < 0.95)
```

`--sort` ranks the table by another measure. `--out` writes every combination to a CSV:
per-mode totals, `min day` and `nbhd`, then per-day and per-product PnL. Combinations with errors
or limit breaches are left out of the summary's picks and of the heatmaps, and the grid exits with 1
if every combination failed.

## Charts and fill statistics

```sh
uv run python -m arena.backtest bots/template.py 1 --out results/run
uv run python -m arena.analysis results/run                              # every day in the folder
uv run python -m arena.analysis results/run r1d0 --start 300000 --end 330000
uv run python -m arena.analysis results/run --reference wall_mid            # measure fills against the wall mid
uv run python -m arena.analysis --grid results/grid.csv                  # heatmaps
```

This saves PNGs to `plots/` next to the input (`--dark` for a dark theme) and prints four tables per day, plus the market-trade table pooled over all days.
The notebook does the same steps interactively, through the same functions in `arena/analysis.py`.

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
uv run python -m arena.validate bots/template.py 1
uv run python -m arena.validate bots/my_bot.py 1 --allow numpy --time-limit-ms 900
```

It fails (exit code 1) on:
- a syntax error, or a missing entry point (`class Trader` with `run`)
- imports from outside the standard library that aren't listed in `--allow`
- any exception, or malformed orders (e.g. float prices)
- orders the engine cancels for possibly breaching a position limit
- a tick slower than `--time-limit-ms`

It warns about:
- use of environment variables, files, subprocesses or the network
- results that change on a repeat run
- results that change when the bot is reloaded every tick, which means it keeps state outside `traderData` that the real engine may not preserve

## How the engine works

`arena/engine.py` replays a day tick by tick, using the rules from IMC Prosperity:

1. The bot sees the book and returns orders.
2. If a product's orders could breach its position limit (all buys, or all sells, filling), every order for that product is cancelled.
3. Each order trades against the visible book at the book's prices, best price first.
4. What's left can fill against that tick's market trades, at the order's own price (`--match-trades`).
5. Anything still unfilled is cancelled. No order rests into the next tick.

Positions are valued at each tick's mid price.

The fills matched jmerle's `prosperity3bt` 0.12.0 exactly in 15 comparisons: 5 days, with all
three trade-matching modes on each. Those days include round 5, with all 15 products and books
that are sometimes empty on one side. `tests/test_parity.py` pins 6 of them: round 1 day 0 and
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
- **What each bot sees:** the book includes the other bots' resting orders, never its own. Trades between other bots appear among its market trades, named after the bot files (`template`, `template#2`, ...).
- **Rivals written for Prosperity:** their orders were meant to live one tick, so they never cancel, and under `--resting` their orders pile up until every new one breaches the limit. `--requote` makes every rival cancel its resting orders before each tick.
- **Races:** another bot can fill one of your orders after your bot decided. If your new orders then no longer fit the limit, they are rejected and counted as a race, not a limit breach. A cancel for an order that filled in the meantime does nothing.

Template against copies of itself, Prosperity 3 round 1, all three days (Kelp at `make_edge` 0.5, `sized_mid`):

| Market | per tick (default) | `--resting` |
|---|---|---|
| alone | 72,674 | 66,558 |
| with one copy | 42,033 + 42,304 | 26,904 + 25,322 |
| with two copies | | 13,161 + 14,568 + 19,044 |

The two copies together make more than one alone in the default mode, because each has its
own position limit. They also get extra fills: when one beats the other to an ask, the other's
take order is left at that price for the rest of the tick, where market trades can fill it.

Rivals change which settings win. With `--resting`, Kelp `make_edge=0` is the best setting
under `worse` fills when trading alone. Against one copy of the baseline it loses 4,920 (10,980
under `worse`). Its quotes at fair get crossed by the next snapshot, and the rival picks them
off: the rival's `wall_mid` treats your large quote as the market maker's level. Against the teams' own P4 bots the same trap cost the template 374k on Osmium in one round, and `fair: sized_mid` turned that into +17k (`IDEAS.md`).

**Adversarial rivals** (`bots/rivals/`, for `--resting`): `trapper.py` baits with a large order
one tick inside the best and sells into whoever steps in front of it (Harris); `spoofer.py` rests
a large order `OFFSET` ticks behind the best and takes what that mispricing brings; `sniper.py`
takes any order left through its fair. `uv run python -m experiments.adversaries` runs the
template against each. On P3 round 1 the trap and the near spoof barely cost it; a large order 10
ticks behind the best took Kelp from 16.8k to −2.1k through `wall_mid`, and `sized_mid` is immune
(`IDEAS.md`, "Adversarial rivals").

## Stress

`arena.stress` reruns a bot on perturbed copies of each day: each product's whole book, trades and
mark moved together, so only the price path changes. The perturbations: volatility ×2, a trend
each way, a level shift at mid-day each way, a 100-tick spike each way, and the walls removed for
the middle fifth. Each is sized in the product's median spread and moves prices by whole ticks. It prints each product's PnL under each one, its largest plain-day drawdown
(what a loss stop must leave room for) and its worst single day.

```sh
uv run python -m arena.stress bots/template.py 1                 # P3 round 1, every perturbation
uv run python -m arena.stress bots/template.py 1 2 3 4 --data p4 --only trend_up,trend_down --size 2
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
uv run python -m arena.backtest bots/template.py 1 --data data/sim
uv run python -m arena.sim run bots/template.py --days 5        # the bot in the market, against replaying the same days
uv run python -m arena.sim run bots/template.py --spec KELP.maker.skew=0.05 --resting
uv run python -m arena.sim run bots/template.py --products KELP,RAINFOREST_RESIN,HYDROGEL_PACK --regime trend_up
```

`--spec PATH=VALUE` changes any preset field, e.g. `KELP.fundamental.sd=0.3` or `KELP.limit_traders.rate=2`.
`run` prints each product's PnL in the market next to replaying the same seed's recording, without the bot, in each `--match-trades` mode. `run --format` loads the bots through another format, such as `drill`.
The recording and the run share every random draw, so the gap is the market's reaction to the bot.

The template over seeds 0–4 (`IDEAS.md`, "Replay against a market that reacts"):

| Product | replay `all` | replay `worse` | replay `none` | in the market |
|---|---|---|---|---|
| Kelp | 37,090 | 12,138 | 0 | 13,478 |
| Kelp, `--resting` | 25,678 | 12,138 | 5 | 36,329 |
| Resin | 105,242 | 101,690 | 34,024 | 115,131 |

What it doesn't match: the takers' signs don't persist (`C(1)` about 0, against 0.1 in P3), the flow is balanced (P3's Kelp is 35% buys), and takers pay more against the wall mid (Kelp 1.3, against 0.9).

## The bot template

`bots/template.py` is one file in five sections:

- **PARAMS:** per-product settings. Products not listed aren't traded. Keys missing from a product's entry come from `DEFAULTS`.
- **STRATEGY:** format-agnostic. Each product goes through four steps:
  - **Fair value:** fixed, mid, `wall_mid`, `outer_mid`, `sized_mid` (the default for a product whose PARAMS don't set `fair`) or `weighted_mid`. `imbalance` quotes around the fair plus a multiple of the best-level imbalance (the linear micro-price); it and `weighted_mid` lost on Prosperity data, so neither is used (`IDEAS.md`). `wall_mid` is the midpoint of the largest-size level on each side, which is how the top Prosperity teams found the market-maker bot's price. `outer_mid` takes the outermost levels. `sized_mid` takes the first level from the top with at least `wall_size`. It is the only one of the three that holds up when other traders' resting orders share the book (see [Shared market](#shared-market)).
  - **Take:** trade against book orders at least `take_edge` better than fair.
  - **Clear:** cut inventory at fair to free room under the limit.
  - **Make:** quote `make_edge` from fair, or one tick inside the book, moved by `skew` against inventory, with sizes scaled by `size_skew` (both work toward `target`).
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

`bots/zoo/` holds bots that language models wrote from a Prosperity-style spec alone: the
baseline an agent-using team starts from, and rivals for `--vs`. `uv run python -m
experiments.zoo` scores each one alone, against the template, inside `arena.sim` and all
together. `bots/zoo/README.md` explains how to add bots from other providers (Gemini,
ChatGPT, ...) cleanly. On P3 round 1, the best Claude-written market makers come close to the template
alone on Kelp and Resin and beat it head to head, all of it on Squid Ink, which the template
doesn't trade. `uv run python -m experiments.zoo_h2h` splits each pairing by product and fill
mode (`IDEAS.md`, "The LLM zoo" and "Why the zoo beat the template head to head").

## On the day: adapting to the real format

1. **Work through [`ON_THE_DAY.md`](ON_THE_DAY.md).** It lists what to find out first (entry point, order handling, limits, whether orders rest, whether the book shows your own orders, the runtime), what each answer changes here, and probes for answering them in the playground. `bots/probe.py` runs most of the probes in one run: rewrite its ADAPTER like the template's, and read its `PROBE` lines (`uv run python -m arena.backtest bots/probe.py 1 --print --no-strict` shows what our engine answers).
2. **Write `arena/formats/qminers.py`**, using `drill.py` as the model, and register it in `arena/formats/__init__.py`. `drill.py` is a practice format deliberately unlike Prosperity's: JSON events of book changes, decimal prices with a tick per product, a callback API with calls for orders, opaque order ids, orders that rest. Every place it had to differ is marked "Unlike Prosperity". It needs a loader into `Day`/`Tick` and a bot wrapper that builds their view and converts orders back. `ON_THE_DAY.md`, "The format swap, step by step", is the checklist.
3. **Update the bot:** rewrite its imports, PARAMS and ADAPTER section, and leave DEFAULTS, STRATEGY and EXECUTION alone. `bots/drill/template.py` is the worked example: it is the template with only those parts rewritten for the drill API, and on the same simulated days it makes the same PnL as the template, to the cent (`tests/test_drill.py`).
4. **Validate** with `--format qminers`, their time limit, and `--allow` for their libraries.

Practise it: `uv run python -m experiments.format_drill <folder>` makes drill data from simulated days, then any tool runs with `--format drill --data <folder>/drill`.

## Known gaps

- **The simulated market is one guess at a design** (`arena.sim`). Its agents are the literature's minimal set, calibrated to P3 round 1's statistics, not to how the Arena's bots behave.
- **The queue model is an estimate.** By default you join the back of the queue and only move up when the visible volume shrinks. `--queue prob` and `--queue front` bracket it, but none of them sees individual orders, so a level re-posted at the same size looks unchanged to `prob`. Orders priced beyond the visible depth keep their last queue estimate.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **Rivals are only the bots you bring.** `--vs` shows how bots like yours interact, but real teams will quote, size and react differently.
