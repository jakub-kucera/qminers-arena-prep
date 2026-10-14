---
title: Zhang, Cucuringu & Shestopaloff, "Dynamic time warping for lead-lag relationship detection in lagged multi-factor models" (2023)
type: source
repo: literature_md/dtw-lead-lag
status: mapped
updated: 2026-10-14
---

# Zhang, Cucuringu & Shestopaloff, "Dynamic time warping for lead-lag relationship detection in lagged multi-factor models" (ICAIF 2023)

## What it is
A cluster-driven method using dynamic time warping to detect lead-lag between many time series in lagged multi-factor models, tested on financial markets with trading strategies built on the lags (`dtw-lead-lag.md:15` (p. 1)). Split from the local `ICAIF_2023_proceedings.pdf` (pp. 454–462 printed). For `harder-rounds` B5's cross-product diagnose.

## Main results
Mapped only: the abstract claims robust detection and economic benefit.

## Assumptions against the Arena
- Daily equity returns with many series; an Arena round has a handful of products. Plain lagged correlations (as in `experiments/cross_product_timing.py`) come first; this is the method to try if those are noisy *(inferred)*.

## In our notation
The products' wall-mid returns per tick.

## Traps
- Not read.

## Read depth
- **Read:** abstract.
- **Unread:** the rest.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
