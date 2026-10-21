# Algorithmic trading round: participant specification

You are writing the trading algorithm for one round of an algorithmic trading competition. Your
algorithm trades against an exchange simulator for a whole day, and your score is its profit.

## The products

| Symbol | Position limit | What we know |
|---|---|---|
| `RAINFOREST_RESIN` | 50 | Its value has been stable throughout its history. |
| `KELP` | 50 | Its price goes up and down over time. |
| `SQUID_INK` | 50 | Volatile, with large swings; there may be a pattern in how it moves. |

Prices and volumes are integers. All profit is counted in one currency (SEASHELLS).

## How a day runs

- A day has 10,000 iterations, with timestamps 0, 100, 200, ..., 999,900.
- In each iteration the exchange calls `Trader.run(state)` once. `state` shows the order book of
  every product, your position, your own trades and the other participants' trades since the last
  iteration.
- `run` returns the orders you want to send. Each order is a limit order: a symbol, an integer
  price and an integer quantity (positive to buy, negative to sell).
- **Matching:** your orders first trade against the order book you were shown, at the book's
  prices, best price first. Whatever is left of an order can then trade with other participants
  who trade during that iteration at your price or better, at your price. Anything still unfilled
  is cancelled at the end of the iteration: no order stays on the book into the next iteration.
- **Position limits:** your position in each product must stay within ± its limit. If the
  orders you send for a product could take you past its limit when they all fill (all your buys,
  or all your sells), **every** order for that product in that iteration is rejected.
- **Score:** your profit at the end of the day: cash from trades plus your final positions
  valued at each product's final mid price.

## The interface

Submit one Python file that defines a class `Trader` with a method `run`:

```python
from datamodel import OrderDepth, TradingState, Order
from typing import List

class Trader:
    def run(self, state: TradingState):
        result = {}  # symbol -> list of Order
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
            # ... your logic ...
            result[product] = orders
        conversions = 0  # not used in this round; always 0
        traderData = ""  # any string; you get it back next iteration as state.traderData
        return result, conversions, traderData
```

The `datamodel` module is provided by the exchange:

```python
class Order:
    def __init__(self, symbol: str, price: int, quantity: int): ...
    # quantity > 0 buys, quantity < 0 sells

class OrderDepth:
    buy_orders: dict[int, int]   # price -> volume, volumes positive
    sell_orders: dict[int, int]  # price -> volume, volumes NEGATIVE

class Trade:
    symbol: str
    price: int
    quantity: int
    buyer: str     # may be empty
    seller: str    # may be empty
    timestamp: int

class TradingState:
    traderData: str                          # what you returned last iteration ("" at first)
    timestamp: int
    order_depths: dict[str, OrderDepth]      # the book of every product, this iteration
    own_trades: dict[str, list[Trade]]       # your trades since the last iteration
    market_trades: dict[str, list[Trade]]    # other participants' trades since the last iteration
    position: dict[str, int]                 # your position per product; a product you hold none of may be missing
    observations: object                     # not used in this round
    listings: dict                           # not used
```

## Rules for the file

- One file. Python 3.12. You may use the standard library, `numpy` and `pandas`. Nothing else.
- **Keep every value you need across iterations in `traderData`.** The exchange may create a new
  `Trader` object for any iteration, so instance attributes, class attributes and module globals
  are not guaranteed to survive. `traderData` is a string: serialise with `json`.
- Each call to `run` must finish within 900 ms.
- The algorithm must be deterministic: the organisers rerun the top submissions and expect the
  same result. If you use randomness, seed it.
- Printing is allowed but not needed.

## Data

Historical data for three days of this market is available to participants. The first rows of
one day, to show the format and the price levels (`;`-separated, up to three levels a side):

```
day;timestamp;product;bid_price_1;bid_volume_1;bid_price_2;bid_volume_2;bid_price_3;bid_volume_3;ask_price_1;ask_volume_1;ask_price_2;ask_volume_2;ask_price_3;ask_volume_3;mid_price;profit_and_loss
0;0;RAINFOREST_RESIN;9998;1;9995;30;;;10005;30;;;;;10001.5;0.0
0;0;KELP;2028;30;;;;;2032;30;;;;;2030.0;0.0
0;0;SQUID_INK;1968;30;;;;;1971;30;;;;;1969.5;0.0
0;100;SQUID_INK;1969;4;1967;31;;;1971;31;;;;;1970.0;0.0
0;100;KELP;2030;4;2028;31;;;2032;31;;;;;2031.0;0.0
0;100;RAINFOREST_RESIN;9996;1;9995;30;;;10002;6;10004;1;10005;30;9999.0;0.0
0;200;SQUID_INK;1966;1;1965;21;;;1969;22;;;;;1967.5;0.0
0;200;RAINFOREST_RESIN;9996;1;9995;21;;;10004;1;10005;21;;;10000.0;0.0
0;200;KELP;2029;1;2028;21;;;2032;22;;;;;2030.5;0.0
```

Trades (the other participants' trades):

```
timestamp;buyer;seller;symbol;currency;price;quantity
100;;;RAINFOREST_RESIN;SEASHELLS;10002.0;1
300;;;KELP;SEASHELLS;2029.0;6
300;;;RAINFOREST_RESIN;SEASHELLS;9998.0;2
300;;;SQUID_INK;SEASHELLS;1965.0;6
500;;;KELP;SEASHELLS;2031.0;1
```
