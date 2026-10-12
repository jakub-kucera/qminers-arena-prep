---
title: Queue position and fill models
type: concept
updated: 2026-10-10
---

# Queue position and fill models

## Summary
In Prosperity, orders live one tick against a snapshot, so queue position hardly matters. Our `--resting` mode lets orders rest, and then the queue assumption decides the result. Ours is the most pessimistic model that hftbacktest documents; the evidence points to something less extreme but not to "front of the queue".

## What the sources say
- **Prosperity's mechanics:** previous orders are cleared at the start of each timestep, makers act, then takers, then your bot, then other bots; speed and cancellation are irrelevant (`prosperity3-frankfurt-hedgehogs/README.md:173`).
- **Backtester limits:** it "could not ... properly handle fill probabilities after inserting liquidity" for Resin and Kelp (`prosperity3-frankfurt-hedgehogs/README.md:900`).
- **hftbacktest's models:** `RiskAdverseQueueModel` (an order only advances when the visible level shrinks below the volume ahead: ours), `ProbQueueModel` (a decrease is split by `p = f(back) / (f(back) + f(front))`, the probability it was behind, with `f(x) = x^n` or `log(1 + x)`), and order-by-order L3 (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:44`, `hftbacktest/hftbacktest/src/backtest/models/queue.rs:139-219`, `hftbacktest/hftbacktest/src/backtest/models/queue.rs:481`). Fill conditions are in `hftbacktest/docs/order_fill.rst`.
- **Evidence on cancellations:** Rigtorp and Databento (read through page summaries) say real cancels come mostly from the back of the queue and that models assuming too little of that bias overstate passive fills (`references/README.md`, "Read online"). `log(1 + x)` blames the back more than `x`: front 100, back 10 gives 9% behind with `x` and 34% with `log(1 + x)` *(computed here)*. hftbacktest's own author raised the queue parameter from 2 to 3 in 2025, i.e. fills got harder (`Market Making with Alpha - Order Book Imbalance` notebook).
- **Theory:** `literature_md/queue-position-valuation/` (value of a place in the queue), `literature_md/dynamics-of-order-positions/`, `literature_md/queue-reactive-model/`.
- **Event-driven venues** (AlgoTrade) are price-time FIFO with trades at the passive order's price (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:407-413`).

- **In Prosperity there is no queue at all** (Leo-Hawking, from a round 0 probe): orders at the best price are processed regardless of arrival time, bots only hit the best price, and "posting at the best price requires no consideration of queue priority" (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:198-214`). So the `--resting` queue assumption only matters if the Arena has a real queue.
- **Where market orders fill** (Cartea et al. 2018, Nasdaq): 91.6–99.9% of market orders are filled by the volume at the best price alone (`literature_md/order-book-signals/order-book-signals.md:61`), which is why quotes deeper than the touch rarely fill.

## Where they disagree
No disagreement among sources; open is which `f` to use.

## What it means for our code
`arena/engine.py` implements the `RiskAdverseQueueModel` rule in its resting mode (module docstring). `TODO.md`: add `--queue back|prob|front` with `ProbQueueModel` and `f(x) = log(1 + x)` as the middle case.

## How to test it here
Compare a market maker's PnL under `back`, `prob` and `front`; a strategy whose edge exists only under `front` is not trustworthy. Check formulas against the PDF pages before coding (`literature_md/README.md`).

## Sources
[hftbacktest](../sources/hftbacktest.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [jmerle P3 backtester](../sources/prosperity3-backtester-jmerle.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [online articles](../sources/online-articles.md).
