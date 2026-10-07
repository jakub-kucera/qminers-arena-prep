# Qminers Algo Trade Arena prep

Tooling for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague): a backtester, a
parameter grid search, charts and fill statistics, a pre-submission validator and a
single-file bot template. Until the real API is known,
everything runs on IMC Prosperity data and its bot format as a stand-in.

| Path | What it is |
|---|---|
| `arena/` | Backtesting engine; the `backtest`, `grid`, `analysis` and `validate` commands; format plug-ins under `arena/formats/` |
| `bots/template.py` | Single-file market maker to copy for each round |
| `notebooks/analysis.ipynb` | Backtest → PnL, fills, one product's fills against the book, markouts, grid heatmaps |
| `references/` | Reference repos and the Prosperity data; see [references/README.md](references/README.md) |
| `tests/` | Unit tests, plus a regression test pinned to jmerle's backtester |

## Setup

```sh
references/clone.sh   # reference repos + Prosperity data (~2 GB)
uv sync               # the engine needs only the standard library; dev adds pytest, pandas, matplotlib
uv run pytest
uv run --group analysis jupyter lab notebooks/analysis.ipynb   # optional: Jupyter
```

## Backtest

```sh
uv run python -m arena.backtest bots/template.py 1                  # Prosperity 3 round 1, every day
uv run python -m arena.backtest bots/template.py 1-0 --data p2      # Prosperity 2 round 1, day 0
uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2
uv run python -m arena.backtest bots/template.py 1 --out results/   # per-day CSVs for arena.analysis
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
| `--data` | `p3` (default), `p2`, or a folder in the same layout |
| `--set PATH=VALUE` | Override a bot global, e.g. `PARAMS.KELP.skew=2`. Repeatable. |
| `--match-trades` | Which market trades leftover orders can fill against: `all` (default), `worse`, `none`. See below. |
| `--resting` | Unfilled orders rest on the book until filled or cancelled, with a queue model. See [Resting mode](#resting-mode). |
| `--fill-ratio R` | Only this share of each book level and market trade is available to you, a rough stand-in for other teams competing for fills. Seeded with `--seed`. |
| `--out DIR` | Write `<day>_timeline.csv` (position, mark, PnL, best bid/ask per tick), `<day>_fills.csv` and `<day>_orders.csv` |
| `--print` | Show the bot's prints |
| `--no-strict` | Let the bot swallow its own exceptions, as it does when submitted |

### Fill assumptions matter

Same template, Prosperity 3 round 1, all three days:

| Fills from | per tick (default) | `--resting` |
|---|---|---|
| book + market trades at your price or worse (`all`, default) | 81,292 | 68,043 |
| book + market trades strictly worse than your price (`worse`) | 57,774 | 57,958 |
| visible book only (`none`) | 28,216 | 28,412 |
| `all`, but only half the liquidity (`--fill-ratio 0.5`) | 44,900 | 35,088 |

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
options apply to every run. A short run of the first combination catches typos before the
grid starts.

The highest backtest PnL is usually overfit, so each combination is ranked on four measures:

| Measure | Meaning |
|---|---|
| `pnl` | Total PnL under the first `--modes` entry |
| `min day` | Its worst single day |
| `nbhd` | Mean PnL of the combination and its grid neighbours (one step along any axis). A plateau beats a lone spike. |
| `pnl(<mode>)` | Total under each extra mode, e.g. `worse` fills |

```
rank  KELP.make_edge  KELP.take_edge  pnl(all)  min day    nbhd  pnl(worse)   fills
   1               1               1    81,292   25,912  75,662      57,774  19,310
   2               1               2    80,256   25,418  74,028      54,776  18,467
   ...
best by pnl      KELP.make_edge=1, KELP.take_edge=1  (81,292)
best by nbhd     KELP.make_edge=1, KELP.take_edge=1  (75,662)
best by min-day  KELP.make_edge=1, KELP.take_edge=1  (25,912)
best by worse    KELP.make_edge=0, KELP.take_edge=1  (63,068)
measures disagree: prefer a setting near the top on every measure over the single best pnl
```

`--sort` ranks the table by another measure. `--out` writes every combination to a CSV:
per-mode totals, `min day` and `nbhd`, then per-day and per-product PnL.

## Charts and fill statistics

```sh
uv run python -m arena.backtest bots/template.py 1 --out results/run
uv run python -m arena.analysis results/run                              # every day in the folder
uv run python -m arena.analysis results/run r1d0 --start 300000 --end 330000
uv run python -m arena.analysis --grid results/grid.csv                  # heatmaps
```

This saves PNGs to `plots/` next to the input (`--dark` for a dark theme) and prints two tables.
The notebook does the same steps interactively, through the same functions in `arena/analysis.py`.

- **PnL:** total and per product over the day.
- **Product:** price with the book spread and your fills, then position against the limit, then PnL. Blue ▲ marks buys and orange ▼ marks sells; solid means you took liquidity, hollow means a resting quote was filled. In a short window (≤ 1,500 ticks) your quotes are drawn too.
- **Fills table:** fills, volume and bought/sold per product, split into took vs passive. `edge` is the average profit per unit against the mid one tick before the fill. It isn't measured against the mid at the fill tick, because an order you take is part of that tick's book and drags the mid toward its own price.
- **Markouts:** the mid 1–500 ticks after each fill, minus the fill price (flipped for sells), per unit. Flat lines mean fills keep their value. Falling lines mean the market moves against you after you trade, i.e. adverse selection.
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

The fills match jmerle's `prosperity3bt` 0.12.0 exactly in 15 comparisons: 5 days, with all
three trade-matching modes on each. Those days include round 5, with all 15 products and books
that are sometimes empty on one side. `tests/test_parity.py` pins those numbers.

### Resting mode

A realistic exchange keeps orders open until they fill or you cancel them. That was the case in
AlgoTrade 2026 (`references/algotrade2026-pitfa19/.firecrawl/algotrade-api.md`), and it may be
the case at the Arena. `--resting` replaces rule 5 with that:

- **New orders:** each one takes what it can from the visible book (rule 3), then the rest rests on the book. An `ioc` order is cancelled instead.
- **Queue:** a resting order joins the back of the queue. The visible volume at its price is ahead of it, and a price better than the best level puts it at the front.
- **Fills from trades:** market trades at its price first use up the volume ahead of it, then fill it. Trades at a worse price fill it straight away. `--match-trades worse` drops fills at its own price and `none` drops trade fills altogether.
- **Fills from the next book:** if the next snapshot shows the other side at or through its price, those orders would have traded with it. It fills at its own price (source `cross`), and the bot sees the snapshot without that volume.
- **Moving up:** if the visible volume at its price drops below the volume counted ahead of it, orders ahead were cancelled, so it moves up. An emptied level puts it at the front.
- **Limits:** the limit check counts resting orders, and only rejects that tick's new orders.
- **Self-trades:** your own orders never trade with each other.

In the Prosperity format, bots see their resting orders in `state.open_orders` (each has an
`id`). They cancel one by returning `Cancel(order_id)` in its product's order list, and send
`Order(symbol, price, quantity, ioc=True)` for an order that mustn't rest. These are our
extensions to the datamodel. A bot written for per-tick cancellation never cancels, so it keeps
adding orders until every new one breaches the limit.

## The bot template

`bots/template.py` is one file in five sections:

- **PARAMS:** per-product settings. Products not listed aren't traded. Keys missing from a product's entry come from `DEFAULTS`.
- **STRATEGY:** format-agnostic. Each product goes through four steps:
  - **Fair value:** fixed, mid, or `wall_mid`. `wall_mid` is the midpoint of the largest-size level on each side, which is how the top Prosperity teams found the market-maker bot's price.
  - **Take:** trade against book orders at least `take_edge` better than fair.
  - **Clear:** cut inventory at fair to free room under the limit.
  - **Make:** quote `make_edge` from fair, or one tick inside the book, moved by `skew` against inventory.
- **EXECUTION:** format-agnostic order management. Takes go out immediate-or-cancel. A resting quote is kept, with its place in the queue, while the plan still wants at least its size at its price. Everything else is cancelled and re-sent. When nothing rests between ticks, every planned order is simply sent, so the same file works under both engine modes.
- **ADAPTER:** the only part that knows the Prosperity types.
- **Trader:** the entry point. It isolates each product, so one product's bug doesn't stop the others. It keeps all state in `traderData`, and it swallows exceptions unless `STRICT` is set. The backtester sets `STRICT` so errors show up.

## On the day: adapting to the real format

1. **In the playground, find out:**
   - the bot's entry point and state object
   - the order format
   - the data files
   - position limits
   - the time limit per tick
   - which imports are allowed
   - whether unfilled orders rest between ticks (if they do, backtest with `--resting`)
2. **Write `arena/formats/qminers.py`**, using `prosperity.py` as the model. It needs a loader into `Day`/`Tick` and a bot wrapper that builds their state and converts orders back. Register it in `arena/formats/__init__.py`.
3. **Update the bot:** rewrite its ADAPTER section and the `datamodel` import. Leave STRATEGY and EXECUTION alone.
4. **Validate** with `--format qminers`, their time limit, and `--allow` for their libraries.

## Known gaps

- **The queue model is an estimate.** It assumes you join the back of the queue and only move up when the visible volume shrinks. Prosperity's bots re-quote every tick, so a real resting order there would often reach the front sooner. Orders priced beyond the visible depth keep their last queue estimate.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **No real competing teams.** In a market shared with other teams, `--fill-ratio` is only a rough stand-in for competition.
