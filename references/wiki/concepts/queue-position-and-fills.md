---
title: Queue position and fill models
type: concept
updated: 2026-10-13
---

# Queue position and fill models

## Summary
In Prosperity, orders live one tick against a snapshot, so queue position hardly matters. Our `--resting` mode lets orders rest, and then the queue assumption decides the result. Ours is the most pessimistic model that hftbacktest documents. The one measurement we have, a single ES futures order checked against order-by-order data, sat between ours and a strong back-of-queue bias, far from uniform cancellation and further still from "front of the queue".

## What the sources say
- **Prosperity's mechanics:** previous orders are cleared at the start of each timestep, makers act, then takers, then your bot, then other bots; speed and cancellation are irrelevant (`prosperity3-frankfurt-hedgehogs/README.md:173`).
- **Backtester limits:** it "could not ... properly handle fill probabilities after inserting liquidity" for Resin and Kelp (`prosperity3-frankfurt-hedgehogs/README.md:900`).
- **hftbacktest's models:** `RiskAdverseQueueModel` (an order only advances when the visible level shrinks below the volume ahead: ours), `ProbQueueModel` (after the trades at the level are subtracted, a decrease is split by `prob`, the probability it was behind: `f(back) / (f(back) + f(front))` with `f(x) = x^n` or `log(1 + x)`, `f(back) / f(back + front)`, or `1 − (front/(front + back))^n`, `PowerProbQueueFunc3`, `hftbacktest/hftbacktest/src/backtest/models/queue.rs:219-327`), and order-by-order L3 (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:44`, `hftbacktest/hftbacktest/src/backtest/models/queue.rs:139-219`, `hftbacktest/hftbacktest/src/backtest/models/queue.rs:481`). Fill conditions are in `hftbacktest/docs/order_fill.rst`.
- **The estimation rules** ([Rigtorp](../sources/rigtorp-queue-position.md), [Quant.SE](../sources/quant-se-order-position.md)): start with the visible level ahead of you; a fill at your price moves you up one for one; split other decreases by `p = f(ahead)/(f(ahead) + f(behind))` (`literature_md/rigtorp-queue-position/rigtorp-queue-position.md:30-34` (p. 2, checked)). The Quant.SE answer's "risk-averse" rule, taking every decrease from behind first, is ours; its "neutral" rule is `ProbQueueModel` (`literature_md/quant-se-order-position/quant-se-order-position.md:74-82` (p. 3, checked)).
- **`log(1 + x)` is not a back-of-queue bias at every position.** It pulls the split toward one half. With 100 ahead and 10 behind, a decrease is 34% behind with `log(1 + x)` against 9% with `f(x) = x`; with 10 ahead and 100 behind, it is 66% behind against 91% *(computed here)*. So it is more pessimistic than uniform only while we are nearer the back.
- **Evidence on cancellations** ([Databento](../sources/databento-queue-position.md)): one ES futures order against order-by-order data. Their family is `P(ahead) = x^{1/(1+k)}` for the fraction `x` of the queue ahead of us (the code's rule; the formula printed on their page is its inverse), i.e. hftbacktest's `PowerProbQueueFunc3` with `n = 1/(1 + k)`. Uniform (`k = 0`) put the order at the front within the order's life; `k = −0.8` (`n = 5`) and `k = −0.95` (`n = 20`) came closer, and for most of the 175 s the truth sat above even `n = 20`, between it and our rule *(read off their chart)*. Their claim: every L2 replay backtester they have seen overstates passive fills (`literature_md/databento-queue-position/databento-queue-position.md:33` (p. 3, checked)).
- hftbacktest's own author raised the power queue parameter from 2 to 3 in 2025 "to reflect ... a more challenging fill in the queue" (`Market Making with Alpha - Order Book Imbalance` notebook), *their claim*. For `PowerProbQueueFunc`, a larger `n` sends more of a decrease to whichever side is larger, so whether fills get harder depends on where the order sits *(inferred from the formula)*.
- **What a queue position is worth** (Moallemi & Yuan, [source](../sources/queue-position-valuation.md)):
  - Order value = fill probability × (premium − adverse selection), `V = α(δ − AS)` (`literature_md/queue-position-valuation/queue-position-valuation.md:101-109` (p. 8, checked)). Adverse selection *grows* with queue position: the back of a long queue fills only against large, informed trades.
  - Their backtest inserts artificial orders at the back ("regular") and the front ("touch") of the real ITCH queue. Back: −0.04 to 0.15 ticks, front: 0.03 to 0.31 ticks, on 9 large-tick stocks (`literature_md/queue-position-valuation/queue-position-valuation.md:442-452` (p. 23, checked)). That is our `back` against `front` comparison.
  - But in small-tick assets "investors can obtain priority … by competing on price" and queueing matters less (`literature_md/queue-position-valuation/queue-position-valuation.md:72` (p. 6)).
- **Uniform cancellation overstates fills** (Huang, Lehalle & Rosenbaum, [source](../sources/queue-reactive-model.md)):
  - Their execution probabilities assume cancellations uniform over the orders ahead, and they warn this "might slightly overestimate" fills, because lower-priority orders are cancelled more.
  - A Poisson model with a linearly rising cancellation rate "clearly overestimates them" (`literature_md/queue-reactive-model/queue-reactive-model.md:277-287` (p. 16, checked)).
  - Measured cancellation rates rise concavely with queue size, and market-order rates fall exponentially with it.
- **The general form of the queue rule** (Guo, Ruan & Zhu, [source](../sources/dynamics-of-order-positions.md)):
  - The volume ahead shrinks at `λ(V̄_market + V̄_cancel·Υ(Z/Q))`, where `Υ` is the share of cancellations falling ahead of you as a function of your relative position (`literature_md/dynamics-of-order-positions/dynamics-of-order-positions.md:276` (p. 10, checked), `literature_md/dynamics-of-order-positions/dynamics-of-order-positions.md:996-1008` (p. 30–31, checked)).
  - In those terms *(inferred)*: our `--resting` is `Υ ≡ 0`, `ProbQueueModel` with `f(x) = x` is uniform (`Υ(x) = x`, Moallemi & Yuan's assumption), and `f(x) = xⁿ` gives `Υ(x) = xⁿ/(xⁿ + (1 − x)ⁿ)`.
- **Event-driven venues** (AlgoTrade) are price-time FIFO with trades at the passive order's price (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:407-413`).

- **In Prosperity there is no queue at all** (Leo-Hawking, from a round 0 probe): orders at the best price are processed regardless of arrival time, bots only hit the best price, and "posting at the best price requires no consideration of queue priority" (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:198-214`). So the `--resting` queue assumption only matters if the Arena has a real queue.
- **Where market orders fill** (Cartea et al. 2018, Nasdaq): 91.6–99.9% of market orders are filled by the volume at the best price alone (`literature_md/order-book-signals/order-book-signals.md:61` (p. 4)), which is why quotes deeper than the touch rarely fill.
- **Priority rules decide what a queue position is** ([Gould et al.](../sources/limit-order-books.md), `literature_md/limit-order-books/limit-order-books.md:251-261` (p. 6)):
  - Price-time (the usual rule, and what our resting mode assumes) rewards arriving early.
  - Pro-rata splits each fill by share of the queue, so quoting more than you want to trade buys priority.
  - Price-size favours the largest order. Prosperity, per Leo-Hawking above, had no time priority within a price.
  - A large tick makes stepping in front of a queue cost a full tick, so queues are long; a tiny tick makes it free, so queues stay thin (`literature_md/limit-order-books/limit-order-books.md:319` (p. 8)).
  - Orders arrive inside the spread more often when the queue at the best is long, read as traders buying priority with price (`literature_md/limit-order-books/limit-order-books.md:464` (p. 12)).
- **What priority is worth** ([Bouchaud et al.](../sources/trades-quotes-prices.md)):
  - On large-tick stocks only orders near the front pay. With NASDAQ numbers the critical position is about half a lot (eq. 21.24, `literature_md/trades-quotes-prices/trades-quotes-prices.md:7930-7934` (p. 420, checked)).
  - A randomly placed order fills mainly on large sweeps and suffers more adverse selection than one at the front (`literature_md/trades-quotes-prices/trades-quotes-prices.md:6643` (p. 347, unchecked)).
  - With small ticks, queues are short and almost any order at the best fills (`literature_md/trades-quotes-prices/trades-quotes-prices.md:6448` (p. 339)). Prosperity's 2–5 tick spreads put it nearer that case *(inferred)*.

## Where they disagree
No disagreement on direction: the papers that model queues assume uniform cancellation for tractability, and the two that look at order-by-order data (Huang et al.'s caveat, Databento) say it overstates fills at the back. So `Υ(x) = x` is an optimistic middle. The earlier reading here, that `log(1 + x)` is the realistic middle, does not hold: it is less pessimistic than uniform near the front of the queue. A power `P(ahead) = xⁿ` with `n` from 1 (uniform) to ∞ (ours) is the one-parameter family the evidence fits, with `n` of 5–20 or more on Databento's one order. Open: which `n` fits a bot-made book, if the Arena has a queue at all.

## What it means for our code
`arena/engine.py` implements the `RiskAdverseQueueModel` rule in its resting mode (module docstring). `TODO.md`: add `--queue back|prob|front`, with `prob` as hftbacktest's `ProbQueueModel` update and `P(ahead) = xⁿ` (`PowerProbQueueFunc3`) as the middle case.

## How to test it here
Compare a market maker's PnL under `back`, `prob` (with `n` = 1, 5 and 20) and `front`. A strategy whose edge exists only under `front` is not trustworthy. Report it as Moallemi & Yuan do: per-order value, fill probability and adverse selection (markout) for each model, not only total PnL. On Prosperity data the gap between `back` and `front` should be small, because spreads are wide and the template improves the price by a tick rather than queueing *(prediction from the papers, untested)*.

## Sources
[Bouchaud et al.](../sources/trades-quotes-prices.md), [Gould et al.](../sources/limit-order-books.md), [Moallemi & Yuan](../sources/queue-position-valuation.md), [Huang et al.](../sources/queue-reactive-model.md), [Guo et al.](../sources/dynamics-of-order-positions.md), [Cartea et al. 2018](../sources/order-book-signals.md), [hftbacktest](../sources/hftbacktest.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [jmerle P3 backtester](../sources/prosperity3-backtester-jmerle.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [Rigtorp](../sources/rigtorp-queue-position.md), [Quant.SE](../sources/quant-se-order-position.md), [Databento](../sources/databento-queue-position.md).
