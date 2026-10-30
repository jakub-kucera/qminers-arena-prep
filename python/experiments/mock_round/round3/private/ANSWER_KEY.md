# Kestrel round answer key (PRIVATE: never show to the team)

The point of this round: **the exchange's matching rules differ from the repo engine's defaults on
purpose, and four of the differences are not in the rules.** A team has to find them from its first
upload (the portal's metrics and results ZIP) and set its plug-in's ENGINE to match.

## The truth: the portal's EngineConfig

`private/portal.py`, `TRUTH`, run through `arena.engine.run_day` on every session:

```python
EngineConfig(
    resting=True,                      # stated: GTC orders rest until filled or cancelled; IOC exists
    trade_matching=TradeMatching.WORSE,  # NOT stated ("matched against the market's activity")
    queue=QueueModel.PROB, queue_power=1.0,  # NOT stated; inert under WORSE (see below)
    mark=Mark.LAST,                    # NOT stated ("valued at the end of the session")
    delay=1,                           # NOT stated: a step's actions reach the exchange one step later
    fee_bps=2.0,                       # stated: taker 2 bps of value
    maker_fee_bps=-0.5,                # stated: maker rebate 0.5 bps
    max_actions=6,                     # stated: 6 actions a step, cancels included
    max_resting=3,                     # stated: 3 working orders per instrument
    limit_penalty=0.25,                # stated: 0.25 credits per lot beyond the limit, per step; no rejection
)
```

All other fields are the defaults (fill_ratio 1, seed 0, fee 0, maker_fee None, deplete False,
max_orders None). As a plug-in ENGINE (what `experiments.day.calibrate` prints for the best setting):

```
RESTING = True
ENGINE = {"trade_matching": "worse", "queue": "prob", "mark": "last", "limit_penalty": 0.25, "delay": 1,
          "fee_bps": 2.0, "maker_fee_bps": -0.5, "max_actions": 6, "max_resting": 3}
```

**Units.** Engine prices are integer hundredths of a point; a point is 2 credits a lot, so one engine
unit is 0.02 credits (`Day.info[sym]["unit"] = 0.02`, with a `tick` key so `price_units` reads it). The
limit penalty, given in credits, becomes 12.5 engine units a lot a step; bps fees are unit-free.

### What each hidden rule means, and how a team can see it

| rule | effect | where it shows on the first upload |
|------|--------|------------------------------------|
| **matching "worse"** | a resting order fills only from a print strictly through its price, or a book that crosses it; prints *at* its price never fill it, whatever the queue | BRAM (one-tick spread): a quote at the touch never fills from prints at its price (mm_bot gets no BRAM fills at all; the example bot's BRAM fills all come when the book moves through it). MAKER fills come only from prints strictly through the price or a book that crosses it: mm_bot's public fills are OPHIR 2,173 cross / 1,397 through-prints, TALC 633 through-prints / 8 cross, none at the price. |
| queue "prob" | irrelevant under "worse" (queue position only matters for prints at the price) | can't be seen; calibrate ties back / prob / front exactly |
| **mark "last"** | end positions are valued at the instrument's last print in the data, not the mid or touch | `markPrice` (mean over traded instruments, in credits = points x 2) equals the mean of the last prints; `pnl_<session>.csv` moves with prints, not the mid, while flat-ish |
| **delay 1** | the actions returned at step t reach the exchange at step t+1: they meet t+1's book and prints | `orders_<session>.csv`: every NEW's ts is one step (250 ms) after the bot decided it; `working` omits an order for one step after it is sent; cancels sent with the order they cancel are logged "cancel ignored: the order is not open"; a purely passive bot gets TAKER fills (mm_bot: ~300 OPHIR taker fills a session, its quotes arriving after the book moved through them); takes priced at step t's touch often miss |

Stated but easy to miss: the 6-action cap counts cancels; the 3-working-orders cap (refusals in the
log); the penalty instead of rejection (a bot that doesn't check its own limit runs over it, as the
delay lets several orders fill before it sees them); the point value (2 credits).

## How the data was made

```sh
private/generate.sh                 # arena.sim days -> private/raw/{pub1,pub2,pub3,hid1,hid2}
uv run python private/disguise.py   # -> public/data (3 sessions), private/hidden_data (2); reloads and checks each
```

Each session is one `arena.sim generate --days 1 --ticks 6000` call on the presets
`HYDROGEL_PACK,KELP,LARGE_TICK` with the `--spec`s in `generate.sh`.

| session | date       | seed  | TALC level (points) |
|---------|------------|-------|---------------------|
| pub1    | 2026-09-14 | 73112 | 124.00              |
| pub2    | 2026-09-15 | 73458 | 124.00              |
| pub3    | 2026-09-16 | 73790 | 124.00              |
| hid1    | 2026-09-21 | 95204 | 124.60              |
| hid2    | 2026-09-22 | 95561 | 123.55              |

## The instruments

| symbol | preset | what it is | points from raw |
|--------|--------|------------|-----------------|
| TALC   | HYDROGEL_PACK | **mean-reverting**: an OU fundamental (reversion 0.003 a step, half-life ~230 steps, sd 1.6 raw ticks a step, so a stationary sd of ~21 raw ticks = 1.03 points) around a level, walls 14 ticks (0.70 points) apart, thin limit orders inside, few prints (~350 a session). Limit 40. **The level moves on hidden days** (124.60 and 123.55 against 124.00): a bot that hard-codes 124.00 is off by 12 or 9 ticks. | (raw - 9995 + 2480 + shift) x 0.05 |
| OPHIR  | KELP | **random walk with informed flow**: sd 1.0 a step, walls 4 apart that re-quote after the snapshot (`maker.first=False`, the shown walls are a step old), value takers (rate 0.25, view noise 0.1, threshold 0.3, 3-8 lots) who know the fundamental: arena.diagnose's R(1) ~ +0.45 ticks after a print. A passive quoter is adversely selected (mm_bot loses on it). Limit 60. | (raw - 2030 + 4180) x 0.01 |
| BRAM   | LARGE_TICK | **large tick**: a one-tick spread (0.5 points = 1 credit a lot) 100% of the time, deep queues (walls ~320), a value that barely moves (sd 0.06 raw a step). ~3,800 prints a session. Limit 80. Under "worse" a quote at the touch never fills from prints, only when the book moves through it. | (raw - 1000 + 300) x 0.5 |

## Scores (portal, credits)

| bot | public (3 sessions) | hidden (2 sessions) |
|-----|---------------------|---------------------|
| `public/example_bot.py` (1 lot at the touch) | 129.50 | -20.82 |
| `private/tests/mm_bot.py` (3 lots one tick inside the walls, skewed) | 441.11 | 325.28 |
| `private/tests/edge_bot.py` (edge cases, no fills) | 0.00 | 0.00 |

Public metrics of the verification uploads are kept in `private/verification_uploads/` (the round's
upload counter was reset to 0 afterwards).

**What each hidden rule is worth** (`uv run python private/check_configs.py BOT [public|hidden]`,
summed over sessions, credits):

| mm_bot, hidden | BRAM | OPHIR | TALC | total |
|----------------|------|-------|------|-------|
| TRUTH (worse, prob, last, delay 1) | 0.0 | -101.2 | 426.5 | 325.3 |
| matching all (queue prob) | 98.9 | -73.4 | 489.1 | 514.6 |
| mark mid | 0.0 | -101.0 | 430.3 | 329.3 |
| mark touch | 0.0 | -101.3 | 403.0 | 301.7 |
| delay 0 | 0.0 | -18.9 | 859.2 | 840.2 |
| repo defaults for all four (all, back, mid, delay 0) | 64.7 | 2.1 | 811.0 | 877.7 |

| mm_bot, public | BRAM | OPHIR | TALC | total |
|----------------|------|-------|------|-------|
| TRUTH | 0.0 | -140.9 | 582.0 | 441.1 |
| repo defaults for all four | 114.4 | 14.1 | 884.8 | 1,013.4 |

So a team that backtests on the repo's defaults over-estimates a maker by about 2.3-2.7x, mostly from
the delay (TALC) and from "all" matching (BRAM fills that never happen here).

**edge_bot** expects per session: 9 rejected actions, 1 slow step, the step-3 exception, one
resting-cap refusal and 4 "cancel ignored" (its docstring lists them).

## What a good bot exploits

1. **TALC's reversion and wide walls.** Quote inside the 0.70-point walls, lean on the distance
   from a level estimated *intraday* (not the public 124.00), take when far from it. The delay costs
   most here (mm_bot TALC 859 -> 427 on hidden): quotes must allow for a step of staleness.
2. **OPHIR's informed flow.** Don't quote tight; widen or lean with recent aggressor flow (prints
   lead the mid by ~0.45 ticks); or trade with the informed side.
3. **BRAM:** under "worse" joining the touch earns nothing from prints; only quotes that the book
   moves through fill (adverse). A bot that thinks it earns the spread here (the repo's default
   "all") is wrong. Fees/rebates are tiny (2 bps of ~300 credits = 0.06 credits a lot).
4. **The delay:** track your own orders by cid instead of trusting `working`; don't cancel an order
   in the same list (or the step after) you send it; price takes for the next step's book; keep a
   margin under the limit (the penalty is 0.25 credits a lot a step).
5. **The mark:** an end position is valued at the last print, which for OPHIR lags the informed
   fundamental; flattening before the end removes the dependence.

## How the portal implements the rules

- **Loader:** `load_session` rebuilds every step's book from `book.csv`'s level updates and reads
  `prints.csv`; a print stamped t is a trade of engine tick t (after the book at t). `disguise.py`
  checks every session round-trips to the raw books and trades.
- **Adapter (`KestrelBot`):** validates the dict actions (fields, tick grid, unique cids, cancels of
  known cids), truncates to the first 6 actions, and converts to `Order(..., tag=cid)` /
  `LazyCancel`, a `Cancel` whose engine order id is looked up by cid when the engine reads it at
  arrival (after the delay), from the `working` orders and executions the adapter has seen by then.
  An unknown id (-1) gives the engine's "cancel ... isn't open" error, shown as "cancel ignored".
- **Engine caps:** `max_actions` (never triggers past the adapter's own cut), `max_resting`
  (refusals logged), `limit_penalty` (no limit rejection at all).
- **Time:** step() over 100 ms raises inside the adapter and its actions are dropped (logged).
- **Metrics:** `experiments.day.calibrate.figures` at scale 0.02 with the first reading of each
  (score = sum of the sessions, fills = fills, pnlSe = the per-session reading stdev x sqrt(n));
  `markPrice` = the last session's mark of the instrument if one traded, else the mean of the traded
  instruments' last marks (calibrate has no reading for the mean: see `check_calibrate.md`).
- **Uploads:** `private/state.json` counts them (max 3, a 4th is refused); `private/.evaluation.lock`
  allows one evaluation at a time; `reset` sets the count to 0.
