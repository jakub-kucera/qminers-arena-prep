# Mock round answer key (PRIVATE: never show to the teams)

## How the data was made

```sh
private/generate.sh                      # raw simulator days, Prosperity layout -> private/raw_public, private/raw_hidden
uv run python private/disguise.py
                                         # -> public/data (3 sessions), private/hidden_data (2 sessions)
```

`generate.sh` runs these commands from the repo:

```sh
uv run python -m arena.sim generate private/raw_public --days 3 --seed 48213 --products HYDROGEL_PACK,ROBOT_DISHES,KELP_NOISY <SPECS>
uv run python -m arena.sim generate private/raw_hidden --days 2 --seed 77305 --products HYDROGEL_PACK,ROBOT_DISHES,KELP_NOISY <SPECS>
```

**Seeds.** Day k uses seed + k:

| set    | seeds              | dates                              |
|--------|--------------------|------------------------------------|
| public | 48213, 48214, 48215 | 2026-03-03, 2026-03-04, 2026-03-05 |
| hidden | 77305, 77306       | 2026-03-06, 2026-03-09             |

Each day has 10,000 ticks.

**`<SPECS>`,** the changes from each preset:

| preset        | field                      | preset value | used         |
|---------------|----------------------------|--------------|--------------|
| HYDROGEL_PACK | limit                      | 200          | 120          |
|               | fundamental.start          | 9995         | 10240        |
|               | fundamental.reversion      | 0.0022       | 0.003        |
|               | fundamental.sd             | 2.06         | 1.8          |
|               | maker.half_spread          | 8            | 7            |
|               | maker.size                 | (20,30)      | (15,25)      |
|               | noise.rate                 | 0.03         | 0.04         |
| ROBOT_DISHES  | limit                      | 10           | 15           |
|               | fundamental.start          | 10400        | 6300         |
|               | fundamental.jump_size      | 100          | 60           |
|               | fundamental.jump_rate      | 0.03         | 0.025        |
|               | fundamental.jump_reverse   | 0.87         | 0.84         |
|               | maker.half_spread          | 4            | 3            |
|               | maker.size                 | (5,10)       | (4,9)        |
|               | limit_traders.offset       | (4.5,5.5)    | (3.5,4.5)    |
| KELP_NOISY    | limit                      | 50           | 60           |
|               | fundamental.start          | 2030         | 1480         |
|               | fundamental.sd             | 0.12         | 0.15         |
|               | maker.half_spread          | 1.75         | 2.25         |
|               | maker.noise                | 1.0          | 1.3          |
|               | maker.skew                 | 0.02         | 0.025        |
|               | noise.rate                 | 0.25         | 0.3          |

## Which instrument is which

| public symbol | preset        | type                                                                 | tick | shift (raw ticks) | limit |
|---------------|---------------|----------------------------------------------------------------------|------|-------------------|-------|
| LUMEN         | HYDROGEL_PACK | returns to a level (Ornstein-Uhlenbeck, about 230-tick half-life of the gap), walls 14 ticks apart, thin flow | 0.05 | -8240 | 120 |
| CALDERA       | ROBOT_DISHES  | jumps of 60 raw ticks (6.00 CR) that snap back about 84% of the time, in bursts; walls 6 ticks apart | 0.10 | -5000 | 15 |
| OBERON        | KELP_NOISY    | random walk, but the market maker doesn't know the price: its centre has 1.3 ticks of noise and an inventory skew, so the wall mid is noisy | 0.02 | +1020 | 60 |

**What `arena.diagnose` notes on the raw public days:**
- **HYDROGEL_PACK:** median spread 14t; reverts to a level over about 1,000 ticks; market making pays 0.50 of the spread.
- **KELP_NOISY:** spread 4t; the wall mid jumps on 30% of ticks; mid AC1 -0.50; the mid and the wall mid are both noisy.
- **ROBOT_DISHES:** spread 6t; walls of only about 7 lots; jumps of 6+ spreads snap back (84-86%).

## Price and time transformation

- **Prices:** the public price is `(raw_price + shift) * tick`, per instrument, as in the table above.
  - LUMEN: raw 10240 becomes 100.00.
  - CALDERA: raw 6300 becomes 130.0.
  - OBERON: raw 1480 becomes 50.00.
- **Times:** the raw timestamp `ts` (0, 100, ..., 999900) becomes `seq = ts / 100`, and
  `time = 09:00:00.000 + seq * 400 ms`.
- **Trade direction:** prints get an aggressor from the snapshot of the same seq: at or above
  the ask is BUY, at or below the bid is SELL, otherwise the side of the mid.
- **Data not published:** the fundamental files in `raw_*/round1/fundamental_*.csv`.
- **Converting PnL:** PnL in CR is the raw-tick PnL times the instrument's tick, since a shift
  doesn't change PnL.

## How the harness implements the rules

`private/evaluate.py` runs `arena.engine.run_day` with
`EngineConfig(resting=True, trade_matching=TradeMatching.WORSE)`.
- **Queue model:** "back", the default.
- **Marks:** at the mid, since the data carries no marks.
- **Bot calls:** the engine calls the bot through `ArenaBot`, an adapter from
  `trade(snapshot, memory)`.
- **Discarded steps:** a timeout (over 100 ms), unserialisable or oversized memory, or an
  exception discards the step's actions and keeps the previous memory, and each is counted as
  an error.
- **Rejected actions:** invalid actions are rejected one by one and counted as "rejected actions".
- **Upload check:** a non-stdlib import or a missing `trade` rejects the file with exit code 2.

## The example bot's results

These are `public/example_bot.py`'s results, which join the touch with 1 lot:

| days   | CALDERA   | LUMEN | OBERON | total         |
|--------|-----------|-------|--------|---------------|
| public | -6,722.40 | -0.70 | -4.58  | **-6,727.68** |
| hidden | -3,641.10 | -1.05 | -7.38  | **-3,649.53** |

**Public sessions:**

| session    | PnL       |
|------------|-----------|
| 2026-03-03 | -2,053.26 |
| 2026-03-04 | -2,091.56 |
| 2026-03-05 | -2,582.86 |

**Hidden sessions:**

| session    | PnL       |
|------------|-----------|
| 2026-03-06 | -1,807.99 |
| 2026-03-09 | -1,841.54 |

The run had no errors, no breaches and no rejected actions.

**Why it loses:** quoting CALDERA at the touch gets filled by every jump at the stale price
(about -3.3 CR a fill).
