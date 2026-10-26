# Meridian Trading Challenge: Round 2 Technical Rules

These are the technical rules for the round. Read them together with the public backtest data in
`data/` and the minimal bot `example_bot.py`. If this document and the example bot disagree, this
document wins.

## 1. The market

- **Instruments.** You can trade three instruments: `CALDERA`, `LUMEN` and `OBERON`. Each has its
  own tick size and position limit, listed in `data/instruments.csv` and repeated here:

  | symbol  | tick size | position limit |
  |---------|-----------|----------------|
  | CALDERA | 0.10      | 15             |
  | LUMEN   | 0.05      | 120            |
  | OBERON  | 0.02      | 60             |

  Prices are in credits (CR). Quantities are whole lots.
- **Sessions.** A session runs from 09:00:00.000 to 10:06:39.600. The exchange publishes a
  snapshot of every order book every 400 ms, so a session has 10,000 steps, numbered `seq` 0 to
  9,999. Sessions are independent. You start each one flat with zero cash, and your bot is
  loaded fresh for each one.
- **Other participants.** The market is made up of the exchange's own participants: market
  makers, liquidity providers and liquidity takers. The round is a replay of recorded sessions,
  so your orders don't move the recorded market. They only consume the liquidity they trade
  against (section 4).

## 2. Public backtest data (`data/`)

```
data/instruments.csv          symbol,tick_size,position_limit,currency
data/<YYYY-MM-DD>/depth.csv   seq,time,symbol,side,level,price,size
data/<YYYY-MM-DD>/prints.csv  seq,time,symbol,price,size,aggressor
```

- **`depth.csv`** has one row per visible price level of each snapshot. `side` is `BID` or `ASK`,
  and `level` 1 is the best price. A side with no rows at some `seq` was empty at that moment.
- **`prints.csv`** lists every trade between other participants. A print with sequence number
  `seq` happened after snapshot `seq` was taken and before snapshot `seq + 1`. `aggressor` is
  the side that crossed the spread (`BUY` or `SELL`), or empty if unknown.
- **Sessions.** Three are published: 2026-03-03, 2026-03-04 and 2026-03-05.

## 3. The bot interface

Your submission is one Python file. It must define one top-level function and may define a
second:

```python
def init(session: dict) -> dict:          # optional: called once, before the first step
    ...
def trade(snapshot: dict, memory: dict) -> list[dict]:   # required: called once per step
    ...
```

**`session`:**

```python
{"date": "2026-03-03",
 "instruments": {"LUMEN": {"tick_size": 0.05, "position_limit": 120}, ...}}
```

`init` returns the initial `memory` dict. Without an `init`, `memory` starts as `{}`.

**`snapshot`**, for step `seq`:

```python
{
  "seq": 1234,
  "time": "09:08:13.600",
  "books": {"LUMEN": {"bids": [[99.70, 18], ...], "asks": [[100.40, 20], ...]}, ...},
                    # best price first; your own resting orders are NOT included
  "prints": {"OBERON": [{"price": 50.04, "size": 3, "aggressor": "BUY"}, ...], ...},
                    # others' trades since your previous step, as in prints.csv for seq - 1
  "positions": {"CALDERA": 0, "LUMEN": -4, "OBERON": 12},
  "fills": [{"id": "q17", "symbol": "LUMEN", "side": "SELL", "price": 100.40, "size": 2}, ...],
                    # your fills since your previous step
  "orders": [{"id": "q18", "symbol": "LUMEN", "side": "BUY", "price": 99.70, "remaining": 5}, ...],
                    # your orders still resting, oldest first
}
```

**`memory`** is your state between steps. Mutate it in place. After each successful call the
exchange stores it as JSON, and it hands you back a copy at the next step.
- **Contents:** it must be JSON-serialisable, and at most 100,000 characters once serialised.
- **No other state:** keep anything you need across steps in `memory`. Module globals and other
  in-process state are not guaranteed to survive between steps.

**Return value:** `trade` returns a list of actions, at most 50 per step:

```python
{"action": "new", "symbol": "LUMEN", "side": "BUY", "price": 99.75, "size": 3,
 "tif": "GTC", "id": "q19"}                 # tif and id optional
{"action": "cancel", "id": "q18"}
```

- **`side`:** `"BUY"` or `"SELL"`.
- **`price`:** a positive multiple of the instrument's tick size.
- **`size`:** a positive integer.
- **`tif`:** `"GTC"` (default) rests until it fills or you cancel it. `"IOC"` trades what it can
  immediately and the rest is cancelled.
- **`id`:** a string of at most 32 characters, unique within the session. If you leave it out,
  the exchange assigns one. Fills and resting orders carry the id.
- **Invalid actions:** an action that breaks these rules is rejected on its own (wrong side, off
  the tick grid, unknown symbol, duplicate id, cancelling an id that isn't resting). The
  other actions of the step still go through.

## 4. Order handling and matching

Each step `seq` is processed in this order:

1. **The market moves to snapshot `seq`.** If the opposite side of the new snapshot reaches or
   crosses the price of one of your resting orders, the order fills at its own price, up to the
   volume shown at or through that price.
2. **Your bot is called.** `trade` receives snapshot `seq` (minus any volume you just traded
   with), your fills since the last call, and the prints since the last call.
3. **Your actions are applied.** Cancels go first, then the position-limit check (section 5).
   Then each new order, in the order you returned them, trades against the visible book of
   snapshot `seq`, best price first, at the book's prices and up to the shown volume. What's
   left of a GTC order rests at its limit price. What's left of an IOC order is cancelled.
4. **Prints fill resting orders.** The prints between snapshots `seq` and `seq + 1` fill your
   resting orders when the print's price is strictly worse for the other side than your
   price: a print below your bid fills your bid, and a print above your ask fills your ask.
   - **Price:** you get your own price, up to the print's size.
   - **Not at your price:** a print exactly at your price does not fill you, because the
     displayed queue at that price is ahead of you.

**Other rules:**
- **Queue position:** a resting order joins the back of the queue at its price.
- **Own orders:** your own orders never trade with each other.
- **Fees:** there are none.
- **Hidden-day matching:** it follows the same rules.

## 5. Position limits

The check runs per instrument and per step, after that step's cancels. It adds up all your buy
orders, resting and new, as if they all filled:

```
position + (all your buy orders) > limit      or
position - (all your sell orders) < -limit
```

If either inequality holds, **every new order for that instrument in that step is rejected**,
and the step counts as a breach. Your cancels and resting orders are unaffected, and so are
the other instruments. The exchange never forces your position back inside the limit, but the
check makes it impossible to cross it.

## 6. Scoring

- **Per session:** your PnL is your cash plus each position valued at the instrument's mid price
  (the average of the best bid and ask) in the session's final snapshot. If a side is empty
  then, the last mid available is used instead.
- **Over the round:** your score is the sum over instruments and sessions. Positions aren't
  carried from one session to the next.
- **The final score is on hidden sessions.** It uses two sessions recorded later than the public
  data: the same instruments and the same rules, but not the same days. The public sessions
  are for development and feedback only.

## 7. Runtime and environment

- **Language and imports:** Python 3.12, **standard library only.** A submission that imports
  anything else is rejected at upload.
- **Sandboxing:** no file, network or subprocess access, and no threads.
- **Per call:** each call to `trade` or `init` must return within **100 ms** of wall-clock time.
  A call that takes longer, or raises an exception, has all its actions discarded, and
  `memory` keeps its value from before the call.
- **Errors:** the session keeps running after an error, and errors are listed in your
  submission report.
- **Output:** standard output is discarded. Don't print every step.

## 8. Submissions

- **How many:** you may make **3 submissions per round**. A file that fails to load (a syntax
  error, a missing `trade`, a disallowed import) is rejected and doesn't count.
- **Feedback:** each accepted submission is run on the three public sessions. You get its total
  PnL, its PnL per instrument and session, fill counts, end positions, breaches and errors.
- **Final submission:** your last accepted submission is final. It is scored on the hidden
  sessions once the round closes.
