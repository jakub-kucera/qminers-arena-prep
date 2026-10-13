---
title: Lee, Hwang, Kim, Yang, Lee & Kim, "From constituents to index: interpretable price movement prediction via cross-asset order flow" (2025)
type: source
repo: literature_md/cross-asset-order-flow
status: read
updated: 2026-10-13
---

# Lee et al., "From constituents to index: interpretable price movement prediction via cross-asset order flow" (ICAIF 2025; CC BY 4.0)

## What it is
A deep-learning predictor of the KOSPI 200 index future's direction from its constituents' order-flow imbalance (OFI): select the 30 most influential constituents (`cross-asset-order-flow.md:93` (p. 3)), forecast each one's OFI with an Informer, and classify the index's up / flat / down move over 5–60 seconds with attention over stocks and time (`cross-asset-order-flow.md:17` (p. 1)). From the ICAIF 2025 triage; the user saved the ACM copy (open access).

## Main results
- **Constituents' order flow helps** (Table 2, `cross-asset-order-flow.md:227-233` (p. 6, checked)): F1 (macro) with the index future alone 0.343, 0.376, 0.396, 0.370 at 5, 10, 30, 60 s; with the constituents' futures 0.387, 0.407, 0.424, 0.393. Three classes, so chance is about 0.33.
- **A 30-second lag:** the gain peaks at 30 s, read as the time for constituents' order flow to reach the index (`cross-asset-order-flow.md:271` (p. 7)).
- **Costs not covered:** the class threshold of 2 basis points is below the round-trip cost, as the authors acknowledge (`cross-asset-order-flow.md:215-219` (p. 6)). The test period is about one week (Table 3's dates).

## Assumptions against the Arena
- A neural network over 137 futures–spot pairs cannot run in a standard-library bot; only the premise, that legs lead the basket, could be used, as a linear rule.
- **The premise fails on Prosperity's baskets** *(checked 2026-10-13, P3 round 2, all three days, mid prices: `uv run python -m experiments.cross_product_timing`)*: the correlation between the legs' implied move this tick (`Σ wᵢ ΔSᵢ`) and the basket's move over the next 1, 5 or 20 ticks is +0.013 to +0.027 for PICNIC_BASKET1 and +0.020 to +0.027 for PICNIC_BASKET2, and the reverse direction (the basket leading the legs) is the same size, +0.007 to +0.036. Neither side leads.

## In our notation
OFI is Cont, Kukanov & Stoikov's order-flow imbalance ([price impact of book events](price-impact-of-book-events.md)), computable from consecutive `Book` snapshots.

## Traps
- **OCR:** Table 2's first row reads `0.3576` and `0.3959` (`cross-asset-order-flow.md:231` (p. 6)) where the PDF has 0.3759 and 0.3957.

## Read depth
- **Read:** all sections; Tables 1–2 on the page image.

## Cited by
[baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md).
