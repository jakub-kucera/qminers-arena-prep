---
title: Capponi, Figueroa-López & Yu, "Market making with stochastic liquidity demand" (2021)
type: source
repo: literature_md/stochastic-liquidity-demand
status: partly-read
updated: 2026-10-13
---

# Capponi, Figueroa-López & Yu, "Market making with stochastic liquidity demand: simultaneous order arrival and price change forecasts" (arXiv:2101.03086)

## What it is
A **discrete-time** market maker: each period it posts a bid and an ask around a fundamental price, the number of shares filled is linear in the quote's distance with random slope and intercept, buy and sell market orders can both arrive in one period, and inventory left at the end of the day pays a linear-impact liquidation cost (`stochastic-liquidity-demand.md:9` (p. 1), `stochastic-liquidity-demand.md:25` (p. 3)). Closed-form optimal quotes, tested on LOB data. Found in the arXiv sweep of 2026-10-13.

## Main results
(From the introduction's summary, `stochastic-liquidity-demand.md:45` (p. 5); the derivations were not read.)
- **Random demand weakens inventory control:** the more the fill slope varies, the smaller the optimal inventory adjustment.
- **Simultaneous buy and sell arrivals** (probability `π(1,1)` per period) narrow the optimal spread and stop it widening toward the end of the day, because offsetting fills manage inventory for free.
- **A threshold:** with inventory below some level, the maker widens both quotes to keep the position instead of trading it down.
- **Forecasts:** an expected price change shifts the quotes by an amount proportional to it (`stochastic-liquidity-demand.md:47` (p. 6)), a parsimonious way to plug a signal into the quotes.
- In their data `π(1,1) ≈ 0.05` per one-second period, larger at five seconds or more (`stochastic-liquidity-demand.md:369` (p. 20)).

## Assumptions against the Arena
- **Simultaneous arrivals are rare per tick on Prosperity data** *(checked 2026-10-13: share of ticks with a market trade at or above the ask and one at or below the bid, against that tick's book; `uv run python -m experiments.cross_product_timing`)*: P4 round 1, Osmium 0.0002 and Pepper Root 0.0001; P3 round 1, Kelp 0.011, Resin 0.006, Squid Ink 0.011; each below the product of the one-sided rates. So the paper's main novelty does not bite at one-tick periods, and the standard result stands for the end of the day: inventory gets more expensive toward the close.
- **An end-of-day liquidation cost** is what the Arena's scoring may impose (`ON_THE_DAY.md`, "How is PnL scored?"); if it does, this is a closed-form model of how quotes should change near the close.
- Fills linear in distance, not exponential as in Avellaneda–Stoikov.

## In our notation
| Paper | Ours |
|---|---|
| period | a tick |
| forecast of the price change | a drift or signal; the template's `target` holds a position against a known drift instead (`python/bots/template.py:59`) |
| liquidation cost at the end of the day | the "flatten before the close" item in `TODO_DONE.md` |

## Traps
- The summary results are the authors' statements; the closed forms were not checked.

## Read depth
- **Read:** the abstract and introduction (pp. 1–7), the paragraph on `π(1,1)`.
- **Unread:** the model and its solution (sections 2–4), the empirical study (section 5), the appendices.

## Cited by
[risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [optimal-quoting-models](../concepts/optimal-quoting-models.md).
