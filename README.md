# Qminers Algo Trade Arena prep

Tooling for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague): a backtester, a
parameter grid search, charts and fill statistics, a pre-submission validator and a
single-file bot template. Until the real API is known,
everything runs on IMC Prosperity data and its bot format as a stand-in.

| Path | What it is |
|---|---|
| `arena/` | Backtesting engine; the `diagnose`, `backtest`, `grid`, `analysis` and `validate` commands; format plug-ins under `arena/formats/` |
| `bots/template.py` | Single-file market maker to copy for each round |
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
| `--vs BOT` | Another bot in the same market, competing for fills and trading with yours. Repeatable. See [Shared market](#shared-market). |
| `--fill-ratio R` | Only this share of each book level and market trade is available to you, a rough stand-in for other teams competing for fills. Seeded with `--seed`. |
| `--out DIR` | Write `<day>_timeline.csv` (position, mark, PnL, best bid/ask and wall mid per tick), `<day>_fills.csv`, `<day>_orders.csv` and `<day>_trades.csv` (the data's market trades) |
| `--print` | Show the bot's prints |
| `--no-strict` | Let the bot swallow its own exceptions, as it does when submitted |

### Fill assumptions matter

Same template, Prosperity 3 round 1, all three days:

| Fills from | per tick (default) | `--resting` |
|---|---|---|
| book + market trades at your price or worse (`all`, default) | 81,292 | 67,446 |
| book + market trades strictly worse than your price (`worse`) | 57,774 | 57,958 |
| visible book only (`none`) | 28,216 | 28,412 |
| `all`, but only half the liquidity (`--fill-ratio 0.5`) | 44,900 | 34,968 |

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
days 0–1 are round 2's for every product round 2 had.

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
- **Limits:** the limit check counts resting orders, and only rejects that tick's new orders.
- **Self-trades:** your own orders never trade with each other.

In the Prosperity format, bots see their resting orders in `state.open_orders` (each has an
`id`). They cancel one by returning `Cancel(order_id)` in its product's order list, and send
`Order(symbol, price, quantity, ioc=True)` for an order that mustn't rest. These are our
extensions to the datamodel. A bot written for per-tick cancellation never cancels, so it keeps
adding orders until every new one breaches the limit.

### Shared market

`--vs BOT` puts more bots in the market: copies of yours (give the same file again) or other
versions. `--set` only applies to your bot. Rivals' results are summarised under each day.
This models a market shared by all teams much better than `--fill-ratio`:

- **Same view, random arrival:** every tick all bots see the same market and decide at once. Their orders then reach the exchange in a random order, seeded and drawn again each tick.
- **Trading with each other:** a new order trades with the recorded book and with the other bots' orders, best price first. At one price the recorded volume goes first. Fills are at the price of the order that was there first.
- **What each bot sees:** the book includes the other bots' resting orders, never its own. Trades between other bots appear among its market trades, named after the bot files (`template`, `template#2`, ...).
- **Races:** another bot can fill one of your orders after your bot decided. If your new orders then no longer fit the limit, they are rejected and counted as a race, not a limit breach. A cancel for an order that filled in the meantime does nothing.

Template against copies of itself, Prosperity 3 round 1, all three days:

| Market | per tick (default) | `--resting` |
|---|---|---|
| alone | 81,292 | 67,446 |
| with one copy | 46,875 + 47,674 | 29,695 + 28,222 |
| with two copies | | 16,266 + 19,522 + 16,279 |

The two copies together make more than one alone in the default mode, because each has its
own position limit. They also get extra fills: when one beats the other to an ask, the other's
take order is left at that price for the rest of the tick, where market trades can fill it.

Rivals change which settings win. With `--resting`, Kelp `make_edge=0` is the best setting
under `worse` fills when trading alone. Against one copy of the baseline it loses 4,920 (10,980
under `worse`). Its quotes at fair get crossed by the next snapshot, and the rival picks them
off: the rival's `wall_mid` treats your large quote as the market maker's level. Against the teams' own P4 bots the same trap cost the template 374k on Osmium in one round, and `fair: sized_mid` turned that into +17k (`IDEAS.md`).

## The bot template

`bots/template.py` is one file in five sections:

- **PARAMS:** per-product settings. Products not listed aren't traded. Keys missing from a product's entry come from `DEFAULTS`.
- **STRATEGY:** format-agnostic. Each product goes through four steps:
  - **Fair value:** fixed, mid, `wall_mid`, `outer_mid` or `sized_mid`. `wall_mid` is the midpoint of the largest-size level on each side, which is how the top Prosperity teams found the market-maker bot's price. `outer_mid` takes the outermost levels. `sized_mid` takes the first level from the top with at least `wall_size`. It is the only one of the three that holds up when other traders' resting orders share the book (see [Shared market](#shared-market)).
  - **Take:** trade against book orders at least `take_edge` better than fair.
  - **Clear:** cut inventory at fair to free room under the limit.
  - **Make:** quote `make_edge` from fair, or one tick inside the book, moved by `skew` against inventory, with sizes scaled by `size_skew` (both work toward `target`).
  - **Level** (optional): for a product that returns to a price `level`, the target becomes the full limit against any move of `level_band` from it, held until the other band (or until the price comes back within `level_exit` of the level, or past it). `clear` then crosses the spread toward it, up to `clear_edge` worse than fair. Set `level` from the earlier days' mean, or `"day"` when there is no history. On P4 rounds 3–4 it makes about 52k a day on Hydrogel and Velvetfruit when scored on days it wasn't tuned on, against 15k for plain market making (`IDEAS.md`).
  - **Follow** (optional): a call option on another product (`follow`, `strike`) holds that product's target as a share of its own limit, so it adds its delta to the same bet. A strike whose half-spread per unit of delta is above `max_cost_per_delta` stays flat. Delta comes from the option's own price through Black–Scholes in total variance, so no expiry date is needed. `Trader.run` trades the followed product first and hands its plan over. On P4 the vouchers following Velvetfruit add about 165k a day out of sample (`IDEAS.md`).
  - **Basket** (optional): a product that is a known combination of others (`basket`: `{leg: weight}`) trades its spread, its price less the legs' weighted prices, with the level settings: `level` is the usual spread. A family that sums to a constant is a basket with legs of weight −1. Legs with `hedge` hold `-weight × hedge_ratio` per basket held, though hedging never helped on Prosperity data. On P3 round 2 and P2 round 3 it makes 71k and 294k over three days out of sample, against 20k for plain market making. Baskets only take (`make_size` 0): under `--resting`, quotes on a product that jumps several ticks at once get picked off.
- **EXECUTION:** format-agnostic order management. Takes go out immediate-or-cancel. A resting quote is kept, with its place in the queue, while the plan still wants at least its size at its price. Everything else is cancelled and re-sent. When nothing rests between ticks, every planned order is simply sent, so the same file works under both engine modes.
- **ADAPTER:** the only part that knows the Prosperity types.
- **Trader:** the entry point. It isolates each product, so one product's bug doesn't stop the others. It keeps all state in `traderData`, and it swallows exceptions unless `STRICT` is set. The backtester sets `STRICT` so errors show up.

## On the day: adapting to the real format

1. **Work through [`ON_THE_DAY.md`](ON_THE_DAY.md).** It lists what to find out first (entry point, order handling, limits, whether orders rest, whether the book shows your own orders, the runtime), what each answer changes here, and probes for answering them in the playground.
2. **Write `arena/formats/qminers.py`**, using `prosperity.py` as the model. It needs a loader into `Day`/`Tick` and a bot wrapper that builds their state and converts orders back. Register it in `arena/formats/__init__.py`.
3. **Update the bot:** rewrite its ADAPTER section and the `datamodel` import. Leave STRATEGY and EXECUTION alone.
4. **Validate** with `--format qminers`, their time limit, and `--allow` for their libraries.

## Known gaps

- **The queue model is an estimate.** It assumes you join the back of the queue and only move up when the visible volume shrinks. Prosperity's bots re-quote every tick, so a real resting order there would often reach the front sooner. Orders priced beyond the visible depth keep their last queue estimate.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **Rivals are only the bots you bring.** `--vs` shows how bots like yours interact, but real teams will quote, size and react differently.
