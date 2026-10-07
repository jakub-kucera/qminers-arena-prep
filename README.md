# Qminers Algo Trade Arena prep

Tooling for the Qminers Algo Trade Arena (7–8 Nov 2026, MFF UK, Prague): a backtester, a
pre-submission validator and a single-file bot template. Until the real API is known,
everything runs on IMC Prosperity data and its bot format as a stand-in.

| Path | What it is |
|---|---|
| `arena/` | Backtesting engine, the `backtest` and `validate` commands, and format plug-ins under `arena/formats/` |
| `bots/template.py` | Single-file market maker to copy for each round |
| `references/` | Reference repos and the Prosperity data; see [references/README.md](references/README.md) |
| `tests/` | Unit tests, plus a regression test pinned to jmerle's backtester |

## Setup

```sh
references/clone.sh   # reference repos + Prosperity data (~2 GB)
uv sync
uv run pytest
```

## Backtest

```sh
uv run python -m arena.backtest bots/template.py 1                  # Prosperity 3 round 1, every day
uv run python -m arena.backtest bots/template.py 1-0 --data p2      # Prosperity 2 round 1, day 0
uv run python -m arena.backtest bots/template.py 1 --set PARAMS.KELP.make_edge=2
uv run python -m arena.backtest bots/template.py 1 --out results/   # per-day timeline and fills CSVs
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
| `--fill-ratio R` | Only this share of each book level and market trade is available to you, a rough stand-in for other teams competing for fills. Seeded with `--seed`. |
| `--out DIR` | Write `<day>_timeline.csv` (position, mark, PnL per tick) and `<day>_fills.csv` |
| `--print` | Show the bot's prints |
| `--no-strict` | Let the bot swallow its own exceptions, as it does when submitted |

### Fill assumptions matter

Same template, Prosperity 3 round 1, all three days:

| Fills from | PnL |
|---|---|
| book + market trades at your price or worse (`all`, default) | 81,292 |
| book + market trades strictly worse than your price (`worse`) | 57,774 |
| visible book only (`none`) | 28,216 |
| `all`, but only half the liquidity (`--fill-ratio 0.5`) | 44,900 |

Most of the default PnL comes from assuming bots would have traded with your resting quotes
instead of with each other. When comparing variants, check that the better one also wins under
`--match-trades worse`; if the ranking flips, the gain is probably a backtest artefact.

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

## The bot template

`bots/template.py` is one file in four sections:

- **PARAMS:** per-product settings. Products not listed aren't traded. Keys missing from a product's entry come from `DEFAULTS`.
- **STRATEGY:** format-agnostic. Each product goes through four steps:
  - **Fair value:** fixed, mid, or `wall_mid`. `wall_mid` is the midpoint of the largest-size level on each side, which is how the top Prosperity teams found the market-maker bot's price.
  - **Take:** trade against book orders at least `take_edge` better than fair.
  - **Clear:** cut inventory at fair to free room under the limit.
  - **Make:** quote `make_edge` from fair, or one tick inside the book, moved by `skew` against inventory.
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
   - whether unfilled orders rest between ticks
2. **Write `arena/formats/qminers.py`**, using `prosperity.py` as the model. It needs a loader into `Day`/`Tick` and a bot wrapper that builds their state and converts orders back. Register it in `arena/formats/__init__.py`.
3. **Update the bot:** rewrite its ADAPTER section and the `datamodel` import. Leave STRATEGY alone.
4. **Validate** with `--format qminers`, their time limit, and `--allow` for their libraries.

## Known gaps

- **No resting orders or queue model.** If the Arena keeps unfilled orders between ticks, step 5 of the engine rules no longer holds and matching needs rework.
- **No conversions.** Trading with another island isn't supported (Prosperity 2 Orchids, Prosperity 3 Macarons).
- **No real competing teams.** In a market shared with other teams, `--fill-ratio` is only a rough stand-in for competition.
