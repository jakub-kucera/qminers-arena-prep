# Kestrel Bourse Challenge: Round 2 Technical Rules

These are the technical rules for this round. Read them with the public data in `data/` and the
example bot in `example_bot.py`. Where this document and the example disagree, this document wins.
`<ROUND>` below is the folder that contains `public/`.

## 1. The market

**Instruments.** Three instruments trade on the Kestrel Bourse. Their parameters are in
`data/instruments.csv` and repeated here.

| symbol | description               | tick (points) | decimals | position limit (lots) |
|--------|---------------------------|---------------|----------|-----------------------|
| BRAM   | barley malt, front month  | 0.5           | 1        | 80                    |
| OPHIR  | silver-copper spread note | 0.01          | 2        | 60                    |
| TALC   | talc ore, warehouse lot   | 0.05          | 2        | 40                    |

- **Prices** are in **points**, written as decimal strings in the data (`"124.35"`). Every price you
  send must be positive and on the instrument's tick grid: BRAM trades at 149.5, 150.0, 150.5, ...
- **Money.** One point is worth **2 credits** per lot. Scores, cash, fees and charges are in credits.
- **Quantities** are whole lots.

**Sessions.** A session runs from 10:00:00.000 to 10:24:59.750. The exchange runs one **step every
250 ms**, so a session has **6,000 steps**, numbered 0 to 5,999.
- **Independent:** you start each session flat, with zero cash; nothing carries over.
- **Fresh module:** your file is imported fresh for every session.

**Other participants.** The market is a replay of recorded sessions of the exchange's own
participants. Your orders don't change what they do.

## 2. Public data (`data/`)

```
data/instruments.csv            symbol,description,tick,decimals,limit
data/<YYYY-MM-DD>/book.csv      clock,symbol,side,level,price,size
data/<YYYY-MM-DD>/prints.csv    clock,symbol,price,size,aggressor
```

Three sessions are published: 2026-09-14, 2026-09-15 and 2026-09-16.

- **`clock`:** the exchange time of the step, `HH:MM:SS.mmm` (step `n` is 10:00:00.000 + n x 250 ms).
- **`book.csv`:** level-by-level updates of the book, up to 3 levels a side (`side` is `bid` or
  `ask`, `level` 1 is the best). A row appears only when that level changed since the previous step.
  `size` 0 with an empty `price` means the level is now empty. The first step lists every level. A
  step with no rows has the same book as the step before.
- **`prints.csv`:** the trades between other participants after the book at `clock` was published
  and before the next step. `aggressor` is `BUY` (the buyer crossed the spread), `SELL`, or empty
  (unknown).

## 3. The bot interface

Your submission is **one Python file** with module-level functions:

```python
def setup(ctx) -> None: ...          # optional: called once per session, before step 0
def step(ctx, view) -> list: ...     # required: called once per step
```

**`ctx`** is the same object for the whole session. You may store your own state on it (`ctx.x = ...`).
It comes with:

```python
ctx.session      # "2026-09-14"
ctx.steps        # 6000
ctx.step_ms      # 250
ctx.point_value  # 2.0 credits per point per lot
ctx.max_actions  # 6
ctx.max_resting  # 3
ctx.instruments  # {"TALC": {"tick": 0.05, "decimals": 2, "limit": 40}, ...}
```

**`view`**, for step `n`:

```python
{
  "step": 17,
  "clock": "10:00:04.250",
  "book": {"TALC": {"bid": [(123.95, 21), ...], "ask": [(124.65, 18), ...]}, ...},
        # the book at this step, best first, (price in points, lots); your own orders are not in it
  "prints": [{"symbol": "BRAM", "price": 150.0, "size": 12, "aggressor": "BUY"}, ...],
        # other participants' trades since your previous call
  "position": {"BRAM": 0, "OPHIR": -4, "TALC": 7},
  "executions": [{"cid": "a17", "symbol": "OPHIR", "side": "SELL", "price": 41.82, "size": 2,
                  "liquidity": "MAKER"}, ...],
        # your fills since your previous call; liquidity "TAKER" (your order took the book) or "MAKER"
  "working": [{"cid": "a18", "symbol": "TALC", "side": "BUY", "price": 123.9, "remaining": 3}, ...],
        # your orders working on the exchange, as the exchange reports them, oldest first
}
```

**Actions.** `step` returns a list of dicts:

| action | meaning |
|--------|---------|
| `{"type": "limit", "cid": "a1", "symbol": "TALC", "side": "BUY", "price": "123.90", "size": 3, "tif": "GTC"}` | a limit order. `tif` `"GTC"` (the default): what doesn't trade at once **rests until it fills or you cancel it**. `"IOC"`: what doesn't trade at once is cancelled. |
| `{"type": "cancel", "cid": "a1"}` | cancel your order `a1`, or what is left of it. |

- **`cid`:** your client id, a string of 1-32 characters. A limit order's cid must not repeat one
  used earlier in the session. Executions and working orders carry it.
- **`price`:** a decimal string or a number, on the tick grid. **`size`:** a positive int.
- **`None` or `[]`:** no actions.
- **Action limit:** at most **6 actions** per step, **cancels included**. Actions after the 6th are
  dropped.
- **Working-order limit:** at most **3 orders working per instrument**. A new resting order beyond
  that is refused by the exchange (IOC orders don't count).
- **Order of processing:** the cancels in a list are applied before its new orders; new orders are
  processed in list order.
- **Rejected actions** (bad fields, a repeated cid, a cancel of a cid you never sent) are dropped and
  listed in your log. A cancel for an order that is no longer working is ignored.

## 4. Matching

- Orders are matched against the market's activity: the book and the other participants' trades.
  A buy at or above the best ask trades at once against the book at the book's prices, best first,
  up to the volume shown, and likewise for sells.
- Resting orders wait in the book at their price and can fill later at their own price.
- **Self-trades:** your own orders never trade with each other.
- **Fees:** each fill on an order that took the book (`TAKER`) costs **2 basis points** of its value.
  Each `MAKER` fill earns a **rebate of 0.5 basis points** of its value. Value = price x lots x 2 credits.
- **Position limits are not enforced by rejecting orders.** Instead, after every step, each lot of a
  position beyond its limit is charged **0.25 credits**. Holding 5 lots too many for 100 steps costs
  125 credits.

## 5. Scoring

- **Per session:** PnL = cash (fees and rebates included) + your end positions valued at the end of
  the session - limit charges, in credits.
- **Score:** the sum over sessions.
- **The final score is on two hidden sessions,** recorded after the public ones: same instruments
  and rules, other days. The public sessions are for development and feedback.

## 6. Runtime

- **Imports:** Python 3.12, **standard library only.** A file that imports anything else, doesn't
  parse, or has no top-level `step` function is rejected at upload (and doesn't count).
- **Sandbox:** no file, network or subprocess access, and no threads. Standard output is discarded.
- **Time limit:** each `step` call must return within **100 ms**. A slower call has its actions
  discarded (what it stored on `ctx` stays). `setup` has 2 s.
- **Errors:** if `step` raises, or returns something that isn't a list, that step's actions are
  discarded. The session continues; errors are listed in your log.

## 7. Uploads

- **How:** from the qminers_arena repo root, `uv run python <ROUND>/private/portal.py upload BOT.py`
  (any path to your file). The portal is a black box: call it, don't read it. It runs **one
  evaluation at a time**.
- **How many:** **3 uploads** for this round. A file rejected at upload doesn't count;
  `uv run python <ROUND>/private/portal.py status` shows how many you have used.
- **Feedback:** each upload runs on the three public sessions. The portal prints the submission's
  metrics as JSON and writes them, with a results ZIP, to `<ROUND>/uploads/upload_<n>/`:
  - **metrics** (money in credits; `markPrice` in credits per lot, i.e. points x 2): `score`, `fills`, `tradedVolume`, `inventory` (end position),
    `cash`, `markPrice`, `breachPenalty`, `pnlSe`, `absInventoryQ50`, `absInventoryQ68`,
    `absInventoryQ95`, `absInventoryQ997`;
  - **results ZIP**, per session: `executions_<session>.csv` (ts, symbol, px, qty, side, client_id,
    liquidity), `orders_<session>.csv` (ts, event NEW/CANCEL, client_id, symbol, side, px, qty, tif;
    ts is the exchange's time), `pnl_<session>.csv` (position and PnL every 10 s) and
    `log_<session>.txt` (rejected actions, exchange messages, errors, slow steps).
- **Final submission:** your last accepted upload is final, and is scored on the hidden sessions.
