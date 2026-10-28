# Halden Exchange Open: Round 3 Technical Rules

These are the complete technical rules for this round. Read them with the public data in `data/`
and the minimal strategy in `example_bot.py`. Where this document and the example disagree, this
document wins.

## 1. The market

**Products.** Four products trade on the Halden Exchange. Their parameters are in
`data/products.json` and repeated here.

| symbol | description                          | tick (pips) | position limit |
|--------|--------------------------------------|-------------|----------------|
| AURIC  | spot metal                           | 1           | 60             |
| BRISA  | spot metal                           | 1           | 60             |
| CORONA | index certificate on a metals basket | 1           | 30             |
| VANTA  | front-month energy future            | 4           | 40             |

- **Prices** are whole numbers of **pips**. Every price you send must be a positive multiple of the
  product's tick: VANTA trades only at 4, 8, 12, ... pips.
- **Money.** One pip is worth **0.25 credits** (`pip_value`), for one lot. Scores are in credits.
- **Quantities** are whole lots.

**Sessions.** A session runs from 13:30:00.000 to 14:29:59.500 UTC. The exchange publishes a
snapshot of every book every 500 ms, so a session has **7,200 steps**, numbered `n` 0 to 7,199.
- **Independent:** sessions don't carry over. You start each one flat, with zero cash.
- **Fresh strategy:** your file is imported fresh and `Strategy()` is constructed anew for every
  session.

**Other participants.** The market is a replay of recorded sessions of the exchange's own
participants: market makers, liquidity providers and liquidity takers. Your orders don't change
what they do. Each snapshot is shown as recorded, except that volume which just traded with your
resting orders is removed (section 4, step 1).

## 2. Public data (`data/`)

```
data/products.json                 exchange, currency, pip_value, step_ms, and per product: tick, limit, blurb
data/sessions/<YYYY-MM-DD>.jsonl.gz   gzip-compressed JSON lines, one line per step
```

Three sessions are published: 2026-05-11, 2026-05-12 and 2026-05-13. Each line looks like this:

```json
{"n": 17, "ts": "2026-05-11T13:30:08.500Z",
 "book": {"AURIC": {"bid": [[3179, 21], [3178, 4]], "ask": [[3182, 18]]}, "BRISA": {...}, ...},
 "tape": [["AURIC", 3182, 2, "B"], ["CORONA", 4398, 1, "S"]]}
```

- **`book`:** up to 3 price levels a side, `[price, lots]`, best first. An empty list means the
  side was empty.
- **`tape`:** every trade between other participants that printed **since the previous line**,
  as `[symbol, price, lots, aggressor]`. The aggressor is `"B"` (the buyer crossed the spread),
  `"S"` (the seller did) or `"?"` (unknown).
  - The tape of line `n` happened after snapshot `n - 1` and before snapshot `n`.
  - Line 0's tape is empty.
  - Trades after the last snapshot are not published.

## 3. The strategy interface

Your submission is **one Python file** that defines a class `Strategy`. Its constructor takes no
arguments.

```python
class Strategy:
    def on_start(self, config: dict) -> None: ...        # optional: called once, before step 0
    def on_market(self, update: dict) -> list: ...       # required: called once per step
```

**`config`** looks like this:

```python
{"session": "2026-05-11", "steps": 7200, "step_ms": 500, "pip_value": 0.25, "max_actions": 10,
 "products": {"AURIC": {"tick": 1, "limit": 60, "max_resting": 4}, ...}}
```

**`update`**, for step `n`, looks like this:

```python
{
  "n": 17,
  "ts": "2026-05-11T13:30:08.500Z",
  "book": {"AURIC": {"bid": [[3179, 21], ...], "ask": [[3182, 18], ...]}, ...},
        # snapshot n; your own resting orders are NOT in it
  "tape": [["AURIC", 3182, 2, "B"], ...],
        # others' trades since your previous call (data line n's tape), minus the volume that filled you
  "pos":  {"AURIC": 0, "BRISA": -4, "CORONA": 0, "VANTA": 12},
  "fills": [[ref, "BRISA", -2, 1203, "maker"], ...],
        # your fills since your previous call: ref, symbol, signed lots (+ bought), price, "maker" | "taker"
  "open": [[ref, "AURIC", 3, 3178], ...],
        # your resting orders, oldest first: ref, symbol, signed remaining lots, price
}
```

**Actions.** `on_market` returns a list of actions. Each is a tuple:

| action                                  | meaning |
|-----------------------------------------|---------|
| `("post", symbol, qty, price, ref)`     | a limit order. `qty` is signed: `+3` buys 3, `-3` sells 3. What doesn't trade at once **rests** until it fills or you pull it. |
| `("take", symbol, qty, price, ref)`     | immediate-or-cancel: trades what it can at `price` or better at once, and the rest is cancelled. |
| `("pull", ref)`                         | cancel one resting order. |
| `("pull_all",)` or `("pull_all", symbol)` | cancel all your resting orders (on one product). |

- **`ref`:** a positive int that you choose. It must not repeat the ref of an earlier accepted
  post or take in the session. Fills and open orders carry it.
- **`None` or `[]`:** no actions.
- **Action limit:** at most **10 actions** per call. Actions after the 10th are dropped.

## 4. How each step is processed

1. **The market moves to snapshot `n`.** If the opposite side of the new snapshot reaches or
   crosses one of your resting orders, that order fills at **its own price**, up to the volume
   shown at or through that price. This is a maker fill. That volume is removed from the
   snapshot and the tape you are shown.
2. **`on_market(update)` is called** with snapshot `n`, the fills since your previous call, and
   the tape since your previous call.
3. **Pulls are applied.** Every `pull` and `pull_all` in the list is applied first, wherever it
   appears in the list.
4. **Posts and takes are applied one by one, in list order.** Each is checked on its own. A
   rejected order doesn't affect the others.
   - **Validity:** known symbol, non-zero int `qty`, positive int `price` on the tick grid, and a
     positive int `ref` not used before.
   - **Position limit:** with `B` your resting buy lots (after this step's pulls) plus the buy
     lots of this step's orders accepted so far, a buy of `q` is rejected if
     `position + B + q > limit`. Sells are the mirror: rejected if `position - S - q < -limit`.
     So your position can never pass the limit.
   - **Resting cap:** a `post` is rejected if that product already has **4** orders resting,
     counting the posts accepted earlier in the same call (whether or not they will fill).
5. **An accepted order trades at once** against the visible snapshot `n`, best price first, at
   the book's prices, up to the shown volume. These are taker fills. What's left of a `post`
   rests at its price. What's left of a `take` is cancelled.
6. **The trades printed before snapshot `n + 1`** (data line `n + 1`'s tape) can fill your
   resting orders, at your price:
   - **Through your price:** a trade at a price worse for its passive side than yours fills you
     at once, up to its size. For example, a print at 3175 fills your bid at 3177.
   - **At your price:** a trade first uses up the volume queued ahead of you, then fills you.

**Queue position.** A new resting order joins the back of the queue: the snapshot's displayed
volume at its price is ahead of it. Each later snapshot updates that queue:
- **Trades:** trades at your price reduce the volume ahead of you.
- **Other decreases:** any other decrease of the displayed level counts as cancellations. Those
  are split between the volume ahead of you and the volume behind you, in proportion to their
  sizes.
- **Emptied level:** if your price level empties, or the best price moves behind yours, you are
  at the front.

**Other rules:**
- **Self-trades:** your own orders never trade with each other.
- **Fees:** a **taker fill** (step 5) costs **1 pip a lot**. Maker fills (steps 1 and 6) are free.
- **Hidden sessions:** matching on them follows the same rules.

## 5. Scoring

- **Per session:** PnL = cash + each position valued at the **touch** in the final snapshot (step
  7,199): a long position at the best bid, a short position at the best ask. If that side is
  empty, the last mid price is used. Cash includes fees. PnL is converted to credits at 0.25 per
  pip.
- **Score:** the sum over products and sessions.
- **The final score is on two hidden sessions,** recorded after the public ones. They have the
  same products and rules, but not the same days. The public sessions are for development and
  feedback only.

## 6. Runtime

- **Imports:** Python 3.12, **standard library only.** A file that imports anything else, or has
  no top-level `class Strategy` with an `on_market` method, is rejected at upload.
- **Sandbox:** no file, network or subprocess access, and no threads.
- **State:** the `Strategy` instance lives for the whole session, so keep state on `self`. Nothing
  survives between sessions.
- **Time limit:** each `on_market` call must return within **50 ms**. A slower call has all its
  actions discarded, but the changes it made to `self` stay. `on_start` has 2 s.
- **Errors:** if `on_market` raises, or returns something that isn't a list, that step's actions
  are discarded. The session continues, and errors are listed in your report.
- **Output:** standard output is discarded.

## 7. Submissions

- **How many:** you have **3 submissions** for this round. A file rejected at upload doesn't
  count.
- **Feedback:** each accepted submission is run on the three public sessions. You get the score,
  PnL per product and session, fill counts (including taker lots), end positions, rejected
  actions, errors and slow calls.
- **Final submission:** your last accepted submission is final, and is scored on the hidden
  sessions.
