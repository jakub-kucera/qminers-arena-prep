---
title: Petit, Cucuringu & Cartea, "Data-driven trade flow decomposition for ETFs and their constituents" (2025)
type: source
repo: literature_md/etf-trade-flow-decomposition
status: partly-read
updated: 2026-10-13
---

# Petit, Cucuringu & Cartea, "Data-driven trade flow decomposition for exchange-traded funds and their constituents" (ICAIF 2025; CC BY 4.0)

## What it is
A daily cross-sectional study on SPY and its constituents, 2018–2021 (`etf-trade-flow-decomposition.md:231` (p. 5)). Each trade is described by what traded around it within ±τ: in the ETF or the constituents, same or opposite sign, before or after, counted and in notional (16 features, `etf-trade-flow-decomposition.md:81-87` (p. 3)). PCA and k-means++ cluster the trades; order imbalances computed *within* each cluster then drive factor-mimicking portfolios (`etf-trade-flow-decomposition.md:11-13` (p. 1)). It generalises Lu et al.'s rule-based four types: isolated trades, trades co-occurring with the same security only, with other securities only, or with both (`etf-trade-flow-decomposition.md:49-53` (p. 2)). From the ICAIF 2025 triage; the user saved the ACM copy (open access).

## Main results
- **Conditional order imbalances carry information that the plain imbalance does not:** some cluster factors have significant daily Sharpe ratios after orthogonalising to the Fama–French factors, momentum and the plain imbalance, up to 1.91 (`etf-trade-flow-decomposition.md:237-242` (p. 5); *their numbers*).

## Assumptions against the Arena
- **Daily horizon, hundreds of stocks.** The signal is a next-day cross-sectional return; an Arena round is one session of a few products. Nothing here is an intraday quoting rule.
- **What could carry over** *(inferred)*: in a product family with a basket, a trade in the basket that coincides with trades in its legs is arbitrage flow, and one that does not is a directional bet. Classifying the data's market trades that way is a few lines over `Tick.trades`.

## In our notation
| Paper | Ours |
|---|---|
| co-occurrence within ±τ | the same or neighbouring ticks of `Tick.trades` across the basket's products |
| conditional order imbalance | signed volume of one class of market trades, per product |

## Tested here
- 2026-11-02 (`IDEAS.md`, "Classifying market trades by co-occurrence across a basket and its legs"; `python/experiments/study/cross_product_timing.py`, section 3): on P3 round 2's baskets and P2 round 3's gift basket, basket trades with a leg trade within a tick and those without move the basket alike (+0.5 to +1.8 ticks over 1–20 ticks, the gaps within one standard error, the days disagreeing), and every move is below half the basket's spread. No flow class to trade there.

## Traps
- None found in what was read.

## Read depth
- **Read:** sections 1–2 (motivation, features, normalisation, PCA, clustering), the portfolio construction and Table 2's headline, the conclusion.
- **Skimmed:** the results tables beyond Table 2, the appendix.

## Cited by
[baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md).
