---
title: Shearer, Rauterberg & Wellman, "Learning to manipulate a financial benchmark" (2023)
type: source
repo: literature_md/benchmark-manipulation
status: partly-read
updated: 2026-10-14
---

# Shearer, Rauterberg & Wellman, "Learning to manipulate a financial benchmark" (ICAIF 2023)

## What it is
A trader with outside holdings valued at a transaction-based benchmark (a VWAP) trades to move it, in an agent-based market of zero-intelligence traders; strategies hand-adjusted and learned by deep RL (`benchmark-manipulation.md:11` (p. 1)). Split from the local `ICAIF_2023_proceedings.pdf` (pp. 592–600 printed). For `harder-rounds` C5, how the close is settled.

## Main results
- **How it is done** (`benchmark-manipulation.md:33` (p. 1)): a few marketable orders near the end of the window shift the VWAP (100.3 to 99.2 in their example).
- **It pays overall** (`benchmark-manipulation.md:49` (p. 2)): the manipulator gives up trading profit and gains more on its benchmark holdings; background traders' surplus rises a little, and the market's information quality falls.

## Assumptions against the Arena
- **If the Arena marks positions at an average over a closing window** (AlgoTrade did) *(inferred)*: a bot holding inventory can move its own mark by trading in that window, and so can a rival or an organiser bot. Find out how the close is settled (`ON_THE_DAY.md`, "How is PnL scored?") before the last round; treat a one-sided run of market orders in the window as a tell, and don't rely on doing it ourselves, since the organisers verify solutions.

## In our notation
The closing window's VWAP of the data's trades against the last mid; our PnL is marked per tick (`arena/engine.py`).

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction, the market set-up.
- **Skimmed:** the RL strategies and welfare results.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md).
