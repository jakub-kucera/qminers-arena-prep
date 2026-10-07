# On the day: what to find out

The organisers won't answer questions. Everything here has to come from their docs, the
playground, or a probe bot (see [Probes](#probes)). Settle the **first hour** list before writing
any strategy, because those answers change the code.

The tooling assumes IMC Prosperity's rules unless told otherwise. Each item says what we assume
now, and what to change if the Arena differs. **Write the answer in under each item as soon as
you know it**, with where it came from (docs, probe, email), so the whole team works from the
same facts.

## Known so far

- 24 hours in person, 7–8 Nov 2026 at MFF UK: four rounds of 5 hours each.
- Python bots trading on a simulated limit-order-book exchange.
- Probably one Python file submitted at the end of each round (unconfirmed).
- Unknown whether all teams share one market or each team trades alone.
- Pre-written code, internet and AI tools are allowed.

## First hour: answers that change the code

- [ ] **How is the bot called?**
  - Find out: the entry point (class or function), its arguments, and what it must return. Is it called once per tick with a snapshot, or fed events as they happen? AlgoTrade 2026 was a websocket with a broadcast every 100 ms.
  - We assume: `Trader().run(state)` once per tick, returning `(orders, conversions, traderData)`.
  - If different: write `arena/formats/qminers.py`, modelled on `prosperity.py`, and rewrite the template's ADAPTER. An event-driven API also needs engine work, so flag it at once.
- [ ] **Do unfilled orders rest between ticks?**
  - Find out: probe 1.
  - We assume: no. Everything unfilled is cancelled at the end of the tick.
  - If they rest: backtest with `--resting`. The template already handles both.
- [ ] **Does the book you see include your own orders?**
  - Find out: probe 2.
  - We assume: no. That's how the backtester shows it in every mode.
  - If it does: in the template's ADAPTER, subtract your open orders from the book before STRATEGY sees it. Otherwise `make` keeps stepping one tick ahead of its own quote.
- [ ] **How do orders, cancels and order types work?**
  - Find out: do orders get ids, and when do you learn them? Can you cancel by id, or cancel all? Are there IOC or market orders? Must orders carry an expiry (AlgoTrade's limit orders did)? Does shrinking an order keep its place in the queue?
  - We assume: ids arrive next tick in `state.open_orders`, `Cancel(order_id)` cancels, `ioc=True` exists, and there's no amend.
  - If different: change the ADAPTER. EXECUTION's logic (keep a quote that hasn't moved, cancel the rest) carries over.
- [ ] **How are position limits enforced?**
  - Find out: probe 4. What's the limit per product? Do open orders count, or only the position? Is only the offending order rejected, or every order for the product? Are long and short limits the same (AlgoTrade had +2,000 / −200, plus a cash floor)?
  - We assume: Prosperity's rule. If all your buys, or all your sells, filling could breach the limit, every order for that product is cancelled. Limits are symmetric.
  - If different: update the limits table (`LIMITS` in the format module), the template's `Plan` room, and the engine's `_breaches` if backtests need to match.
- [ ] **Is the market shared with the other teams?**
  - Find out: do trades or book levels appear that the exchange's own bots couldn't explain? Are counterparties named?
  - If shared: tune with `--vs` (copies or variants of your bot) as well as alone, and prefer settings that hold up in both.
- [ ] **Where does state live between calls?**
  - Find out: probe 7. Do module and instance variables survive between calls? Is there a state string like `traderData`, and how big can it be?
  - We assume: only `traderData` survives. The validator's reload-every-tick check enforces this.
  - If more survives: nothing breaks. Keeping state in `traderData` still works.
- [ ] **What does the runtime allow?**
  - Find out: Python version, allowed imports (probe 10), time limit per call (probe 8), and what happens to prints (probe 9).
  - Then: run `arena.validate` with `--allow numpy` (etc.) and `--time-limit-ms` set to their limit.
- [ ] **What data can you backtest on?**
  - Find out: are historical files provided, and in which format? Does the live data look the same (book depth, tick spacing)?
  - Then: write the loader in `arena/formats/qminers.py`, and run the template and validator on it before changing any strategy.

## Before the first submission

- [ ] **How do submissions work?** The exact deadline, whether you can resubmit, which submission counts, and whether you can test-run one before it counts.
- [ ] **What does an exception do?** Probe 6. Is the tick skipped, the bot stopped, or the round lost? The template catches errors per product unless `STRICT` is set.
- [ ] **What are the price units?** Integer ticks? Tick size? Cents? The template rounds prices to `int`.
- [ ] **How is PnL scored?**
  - At which price are open positions valued: mid, last trade, or a settlement price?
  - Are positions liquidated at the end, and at what price? If badly, flatten before the close.
  - How are the rounds combined into a ranking? Is there a penalty for risk or drawdown?
- [ ] **Are there fees, rate limits or caps?** Fees or rebates per trade, the maximum number of orders per call or per second, and the maximum number of open orders. AlgoTrade closed your connection above 500 messages a second, and allowed 6,000 open orders.

## Every round

- [ ] **Products:** the new products, their position limits, and whether any are related, such as baskets, ETFs or options. AlgoTrade defined each ETF's fair value as the mean of its constituents.
- [ ] **Other traders:** are there exchange bots, and are counterparties named? In Prosperity's round 5, the names gave away informed traders.
- [ ] **Evaluation data:** is the round scored on the data you were given, or on fresh data? If fresh, trust the grid's `nbhd` and `min day` measures over its best `pnl`.
- [ ] **Extra information:** news, external prices, or conversions to another market.
- [ ] **Rule changes:** anything different from the previous round, such as limits, fees or matching.

## Probes

A throwaway bot can answer most of the first-hour list in one playground run. Have it print
everything it sees (book, open orders, fills, positions) every tick, and run one experiment
at a time:

1. **Resting:** at tick 1, bid well below the best bid. At tick 2, send nothing. If the order is still listed, or fills later, orders rest.
2. **Own orders in the book:** with that bid resting, check the book for a level at its price and size.
3. **Fill timing and price:** send a buy at the best ask. Is the fill reported in the same call, the next call, or later, and at which price?
4. **Limits:** send two buys that together exceed the limit by one. Is one rejected, both, or every order for the product? Is there an error message?
5. **Self-trade:** send a bid and an ask at the same price. Do they trade with each other?
6. **Exceptions:** raise an exception in one tick. Does the bot get called again?
7. **State:** set a module global and an instance attribute, then read them on the next call.
8. **Time limit:** sleep 50, 200 and 500 ms in different ticks. Note what happens at each.
9. **Prints:** print about 10 KB in one call. Where does it show up? Is it cut off?
10. **Imports:** inside `try`, import numpy, pandas and scipy, and print which ones loaded.
