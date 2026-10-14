---
title: Tao, Day, Ling & Drapeau, "On detecting spoofing strategies in high frequency trading" (2022)
type: source
repo: literature_md/detecting-spoofing-strategies
status: partly-read
updated: 2026-10-14
---

# Tao, Day, Ling & Drapeau, "On detecting spoofing strategies in high frequency trading" (Quantitative Finance 22(8), 2022; arXiv:2009.14818)

## What it is
A static model of a spoofer who moves a multi-level book imbalance to buy cheaper, the conditions under which spoofing pays, and a real-time detector calibrated on TMX level-2 data (`detecting-spoofing-strategies.md:5` (p. 1)). For harder-round item D3 (`references/SEARCH_LOG.md`, the spoofing table); fetched from arXiv.

## Main results
- **Where spoofing pays** (`detecting-spoofing-strategies.md:87` (p. 4)): when the spoofer's genuine order is large next to the book's depth, when the book starts balanced, and with the spoof posted away from the top. Whether thin books are more spoofable is inconclusive in the model.
- **The detector** (`detecting-spoofing-strategies.md:93` (p. 4)): a spoof only pays if a market order follows it, so compare the imbalance just before each market order with its usual distribution (and with the imbalance just after), by a Wasserstein distance; a spoofed book shows an imbalance before the trade that snaps back after it.

## Assumptions against the Arena
- A static, one-shot spoof on level-2 data; the Arena gives us snapshots, which is enough for imbalances by level *(inferred)*.
- **The tell for the day** *(inferred)*: in a product where large levels appear, look at the multi-level imbalance on ticks with market trades against all ticks; a spoofer shows as an imbalance that is unusually one-sided before trades and back to normal after.

## In our notation
The multi-level imbalance is computable from `Book` (volumes by level, weighted by depth); market orders are the data's `Tick.trades` classified against the book.

## Traps
- None found in what was read.

## Read depth
- **Read:** abstract, introduction (with its summary of conditions and the detection idea).
- **Skimmed:** the model, the optimal strategy and the TMX calibration.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md).
