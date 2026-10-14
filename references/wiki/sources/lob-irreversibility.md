---
title: Yeo, Cha & Hwang, "Irreversibility in real and simulated order book paths" (2026)
type: source
repo: literature_md/lob-irreversibility
status: read
updated: 2026-10-14
---

# Yeo, Cha & Hwang, "Neural estimation of irreversibility in real and simulated limit order book paths" (ICAIF 2026 preprint)

## What it is
Can a stretch of order book be told apart from the same stretch played backwards? A network learns to do this on Nasdaq data (`lob-irreversibility.md:11` (p. 1)). Comparing a network that sees the order of blocks with one that doesn't separates two sources of asymmetry: what the blocks contain, and the order they come in. A calibrated queue-reactive simulator gets the first right and almost none of the second, so the authors propose the comparison as a benchmark for book simulators. This is arXiv 2610.16151v1 (9 pages, an oral at ICAIF 2026), downloaded by the agent. The code is at `github.com/hjyeo30/lob-irreversibility` (not checked).

## Main results
- **The data and the path** (`lob-irreversibility.md:132-148` (p. 3)): 15 days of Nasdaq market-by-order data (July 2026) for NVDA plus 11 other symbols. The book is sampled on an event clock, in blocks of `B = 10` book updates. Each block has 37 features: the spread, depth and imbalance at both ends, the gross and net depth change, the depletion and appearance counts at the best, and the price moves. A path is `K = 6` blocks.
- **Reversal is physical** (`lob-irreversibility.md:164` (p. 4)). States keep their values and swap position, signed changes flip sign, and liquidity that vanished in forward time appears in reverse. The score is antisymmetric by construction, `s_0(W) = g(W) − g(RW)` (eq. 3, `lob-irreversibility.md:169` (p. 4, checked)). It is trained with a logistic loss, so it estimates the forward-to-reverse log-density ratio.
- **Real books carry an arrow of time, mostly in their order.** For NVDA, the network blind to order reaches 0.036 nats per event and the order-aware one 0.054, so the ordering increment is 0.018 (`lob-irreversibility.md:212` (p. 5)). Linear scores reach 0.0004, two orders of magnitude less: the asymmetry is nonlinear. With the clock features removed, shuffling the blocks cuts the increment from 0.0071 to 0.00055 (`lob-irreversibility.md:220` (p. 5)). The increment is positive on all 12 symbols on every test date, from 0.0038 (SOFI) to 0.0184 (AAPL) (`lob-irreversibility.md:228` (p. 5)).
- **It depends on the coarse-graining.** At a fixed horizon of 60 updates, the increment is 0.0216 with 5-update blocks, 0.0179 with 10 and 0.0020 with 30 (`lob-irreversibility.md:242` (p. 6)). So a rate belongs to a representation, not to a market.
- **More than one step of memory.** A surrogate that keeps the coarse one-step transition counts exactly but reshuffles their sequence recovers 30% less than the real paths (`lob-irreversibility.md:260` (p. 7)).
- **No forecasting gain.** Adding the scores to 29 standard book and recent-flow inputs changed the error of return forecasts by under 0.12% in 22 of 24 cases (`lob-irreversibility.md:266` (p. 7)).
- **The simulator test** (`lob-irreversibility.md:272-288` (p. 7–8)). The simulator is a queue-reactive one in the style of Huang et al., calibrated on the same days. Its intensities depend on queue size, and all queues are redrawn when the best queue empties. It reaches an order-aware rate of 0.052 against the real 0.054, but its increment is 0.0006 against 0.018. Giving it the real timing doesn't help (0.00075). Its spread never moved within a day, and four of its features were constant. The one-step surrogate removes 0.09% of its rate, against 30% of the real one. The authors expect generators that learn from longer histories to do better, but that is untested.

## Assumptions against the Arena
- **For the A1 day generator** ([harder-rounds](../concepts/harder-rounds.md)): if we build one from PyMarketSim-style agents, matching spreads, depths and impact won't show whether it moves the book through its states in the real order *(inferred)*. A cheap check without a network is to fit the same strategy on real days, on generated days, and on real days with blocks of ticks shuffled. A generator realistic in this sense should be hurt by the shuffle as much as the real data is.
- **Prosperity's books are themselves a simulator's output.** Our trade-arrival check finds no clustering ([hawkes-structured-mm](hawkes-structured-mm.md)), which agrees with a memoryless generator. A history-based signal therefore has little to find beyond the current book and position *(inferred; not measured with this paper's estimator)*.
- **No trading rule.** The paper itself finds the scores add nothing to forecasts.

## In our notation
A Prosperity "event" is a tick: every product's book snapshot plus that tick's trades, so `B` counts ticks. Even under reversal: the spread, depth, absolute moves and gross changes. Odd: mid changes, net depth changes, and our signed fills. The paper's even-times-odd products (spread × signed depth change) are what a linear model can't form, which is why it needs a network.

## Traps
- **The simulator compared is deliberately simple.** It is first-order and redraws its queues, so the gap shows what such a simulator misses, not that every simulator does.
- **The forecasting comparison is exploratory** (their caveat): its evaluation dates weren't held out from the earlier analyses.
- **The networks aren't matched in size** (8,609 and 12,929 parameters). The `K = 1` control, where the bigger network's increment is negative (−0.00135), argues that capacity alone doesn't explain the gap.

## Read depth
- **Read:** sections 1, 3–7.
- **Skimmed:** the related work (section 2).
- **Unread:** the code and the figures as images.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
