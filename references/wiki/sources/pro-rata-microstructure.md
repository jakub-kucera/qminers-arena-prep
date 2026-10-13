---
title: Guilbaud & Pham, "Optimal high-frequency trading in a pro rata microstructure with predictive information" (2013)
type: source
repo: literature_md/pro-rata-microstructure
status: mapped
updated: 2026-10-13
---

# Guilbaud & Pham, "Optimal high-frequency trading in a pro rata microstructure with predictive information" (Mathematical Finance, 2013)

## What it is
The companion of [limit-and-market-orders](limit-and-market-orders.md) for a **one-tick, pro-rata** book (short-term interest-rate futures): the spread is always one tick, and a market order is split across the resting orders at the best in proportion to their size, so a limit order fills only partly (`pro-rata-microstructure.md:11` (p. 1), `pro-rata-microstructure.md:51` (p. 4), `pro-rata-microstructure.md:59-61` (p. 4)). Conditional reading: only if probe 11 (`ON_THE_DAY.md`) finds pro-rata matching. The user saved the published version.

## Main results
Mapped only. The abstract and conclusion name two risks peculiar to pro-rata: **overtrading** (the filled quantity is not under the maker's control, so inventory jumps) and adverse selection, and a predictive price signal as a state variable to rebalance before the price moves. Mixed limit and market orders beat limit orders alone on mean over volatility.

## Assumptions against the Arena
A spread fixed at one tick; Prosperity's are 2–21 ticks.

## In our notation
Under pro-rata, quoting more than you want to trade buys a larger share ([queue position](../concepts/queue-position-and-fills.md), priority rules); `make_size` would then set the fill share, not only the exposure.

## Traps
None found; not read.

## Read depth
- **Read:** the abstract, introduction, the start of section 2 and the conclusion.
- **Unread:** everything else.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md).
