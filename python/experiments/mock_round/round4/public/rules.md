# The Varde Exchange: Technical Rules, round 1

## Products and limits
Three products trade: **LUMEN** (position limit 40), **QUILL** (60) and **SORREL** (30). Prices are in **cents**, on a
**5-cent tick** (every price is a multiple of 5). Results are reported in **euros** (100 cents); one lot of a product
moves by its price in cents.

## Data
`data/session_1.jsonl` to `session_3.jsonl`: three public sessions of 5,000 steps, one JSON object per line:
`{"t": step, "book": {SYMBOL: {"bids": [[price, volume], ...], "asks": [...]}}, "prints": [{"sym", "px", "qty",
"aggressor": "buy" | "sell"}]}`. The book shows up to three levels a side, best first, before the step's trading.
The prints are the trades between other participants during that step; `aggressor` is the side that crossed.
Your submission is scored on **two other sessions** of the same market, which you never see.

## Your bot
One Python file, standard library only, defining:

```python
class Strategy:
    def __init__(self, limits): ...        # {symbol: position limit}
    def on_tick(self, state): ...          # once a step; returns a list of actions
```

`state` holds `t`, `book` (as in the data, this step), `prints` (the **previous** step's prints), `position`
({symbol: lots}), `orders` (your resting orders: `id`, `sym`, `px`, `qty` signed, what is left), `fills` (your fills
since the last call: `id`, `sym`, `px`, `qty` signed) and `cash` (euros, fees included). The same object is called
for the whole session, so it may keep state in itself.

Actions, at most **10 a step** (the rest are ignored):
- `{"type": "limit", "sym": ..., "px": cents, "qty": lots}`: a limit order, `qty` positive to buy, negative to sell.
  The exchange gives it an id, which you see in `orders` from the next step.
- `{"type": "cancel", "id": ...}`: cancels a resting order. Cancels are processed before the step's new orders.

## Matching
A new order first trades with the book shown that step, at the book's prices. What is left **rests** until it is
filled or cancelled. Resting orders are filled by the step's prints at the order's price, best price first, then
oldest first: a sell print fills bids at or above its price, a buy print asks at or below it. Fills are reported in
the next step's `fills`.

## Limits, fees and errors
If a step's new orders for a product could take its position past the limit (counting what already rests), **all**
of that step's new orders for that product are rejected. A fee of **0.1 cent per lot traded** and **0.5 cent per
order placed** is charged. A call slower than **50 ms**, or one that raises, has its actions dropped. All rejections
are written to the log in the results.

## Score
Your score is your profit in euros over the scored sessions: cash, fees included, plus open positions valued at the
session's settlement price. The upload page shows the submission's metrics and a results file with your fills,
orders and the log. You have **3 public submissions** this round; files up to 100 kB.
