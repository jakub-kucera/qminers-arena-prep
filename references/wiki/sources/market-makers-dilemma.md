---
title: Albers, Cucuringu, Howison & Shestopaloff, "The market maker's dilemma" (2025)
type: source
repo: literature_md/market-makers-dilemma
status: partly-read
updated: 2026-10-13
---

# Albers, Cucuringu, Howison & Shestopaloff, "The market maker's dilemma: navigating the fill probability vs. post-fill returns trade-off" (arXiv:2502.18625, 2025)

## What it is
A **live trading experiment**: 232,897 minimum-size maker orders on the Binance bitcoin perpetual over a week, posted at the touch on both sides with no signal and cancelled only when the price left them behind (`market-makers-dilemma.md:23` (p. 1), `market-makers-dilemma.md:185` (p. 9)). Real fills, so no fill model is assumed: the paper measures what backtesters have to guess. Found in the arXiv q-fin.TR sweep of 2026-10-13 (`references/SEARCH_LOG.md`).

## Main results
- **Fill probability against post-fill return is a trade-off.** An order whose next price move goes against it fills for certain; one whose move goes its way may be left behind. So fill probability and post-fill return are negatively correlated (`market-makers-dilemma.md:23` (p. 1)).
- **Queues set the fill probability:** posted with a large near-side queue and a small opposite one, an order fills as rarely as 30% of the time; the reverse, over 90% (`market-makers-dilemma.md:270` (p. 15)).
- **Naive two-sided quoting loses** (`market-makers-dilemma.md:412-416` (p. 22)): post at the best on both sides, then only on the side that flattens. Over three days it lost almost 60% (Sharpe −109, *their numbers*): most round trips earn a little, and the rare large losses dominate. **Quoting with the imbalance also loses** (`market-makers-dilemma.md:428` (p. 22)).
- **What worked, barely:** posting *against* an adverse imbalance when a model predicts a reversal, to hold an early queue place when the price turns; slightly profitable at minimum size and low fees, "likely not scalable" (`market-makers-dilemma.md:693-697` (p. 36)). Their "Unprofitability Principle": forecasting ability and ease of exploitation are anti-correlated (`market-makers-dilemma.md:81` (p. 4)).

## Assumptions against the Arena
- **A one-tick, crowded, fee-charging market.** Bitcoin perpetual queues are deep and the spread is one tick. Prosperity is the opposite case: spreads of 2–21 ticks set by bots, and a maker earning about half the spread per unit (`arena.diagnose`, [reading the data](../concepts/reading-the-data-on-day-one.md); *checked on P4 round 1*). So the headline loss does not transfer to a Prosperity-like Arena. It would transfer to a shared Arena where teams compete at a one-tick spread.
- **Their method transfers:** minimum-size orders posted without a signal measure the fill probability *and* the post-fill markout at once. That is a probe (`ON_THE_DAY.md`).

## In our notation
| Paper | Ours |
|---|---|
| post-fill return at horizon h | the markouts in `arena.analysis` (from 1 tick on) |
| near- and opposite-side queue | the volumes at our side's and the other side's best in `Book` |
| fill probability per state | as in [Guilbaud & Pham](limit-and-market-orders.md), fills over time in the state |

## Traps
- Results are with minimum-size orders; the authors expect larger ones to do worse (footnote 13).
- The live data are not public; nothing here can be re-run.

## Read depth
- **Read:** the abstract, introduction, section 4's fill-probability results, section 6 (naive and imbalance strategies), the conclusion.
- **Mapped:** section 5 (price drift) and section 7 (the reversal model and its features), by headings.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md).
