---
title: Cartea, Jaimungal & Wang, "Spoofing and price manipulation in order-driven markets" (2020)
type: source
repo: literature_md/optimal-spoofing
status: partly-read
updated: 2026-10-14
---

# Cartea, Jaimungal & Wang, "Spoofing and price manipulation in order-driven markets" (Applied Mathematical Finance 27, 2020)

## What it is
The optimal strategy of an investor liquidating a position who may add spoof buy orders to tilt the book's volume imbalance, against an expected fine; the imbalance is a Markov chain fitted to Nasdaq data (`optimal-spoofing.md:13` (p. 1)). The author version from Oxford's repository.

## Main results
- **Why it works** (`optimal-spoofing.md:13` (p. 1)): in the buy-heavy imbalance regime buy market orders arrive faster and the mid drifts up, so spoof buy orders that move the book into that regime let the investor sell at better prices, with fewer market orders and some round trips from spoof orders that fill by accident.
- **The fine:** as its expected value rises the investor spoofs less, and past a point not at all (`optimal-spoofing.md:13` (p. 1)).
- **Lee et al.'s empirical definition** (Korea Exchange), quoted here (`optimal-spoofing.md:49` (p. 4)): an order resting at least 6 ticks from the price and at least twice the previous day's average order size; such orders rarely fill, earn their owners substantial extra profit, and target more volatile, smaller, cheaper stocks.

## Assumptions against the Arena
- In a simulator there is no fine unless the rules impose one, so a scripted spoofer would spoof all the time *(inferred)*.
- **What this predicts for D3:** an organiser spoofer tilts the imbalance at the best quotes, and the traders it fools are imbalance-readers; the template's `wall_mid` reads level sizes, not the imbalance, but a spoofed largest level drags it (`harder-rounds`, D3).

## In our notation
Volume imbalance at the best quotes is `ρ`; the regimes are its terciles.

## Traps
- The Lee et al. criterion is second-hand here (from this paper's literature review).

## Read depth
- **Read:** abstract, introduction and literature review.
- **Skimmed:** the control problem and the Nasdaq calibration.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md).
