---
title: Zhao & Linetsky, "High frequency automated market making algorithms with adverse selection risk control via RL" (2021)
type: source
repo: literature_md/mm-adverse-selection-rl
status: partly-read
updated: 2026-10-14
---

# Zhao & Linetsky, "High frequency automated market making algorithms with adverse selection risk control via reinforcement learning" (ICAIF 2021)

## What it is
A market-making feature, the **book exhaustion rate (BER)**, argued to measure adverse-selection risk directly, and an RL market maker that uses it, trained on three years of CME S&P 500 and 10-year Treasury futures data (`mm-adverse-selection-rl.md:9` (p. 1), `mm-adverse-selection-rl.md:33` (p. 2)). From the ICAIF 2020–2024 triage.

## Main results
- **Definition** (`mm-adverse-selection-rl.md:101` (p. 4)): over a look-back window w, the offer-side BER is the average market-buy volume executed per second divided by the average size at the best ask; the bid side likewise. It is the share of top-of-book liquidity eaten per second; its inverse is the time to exhaust the best level.
- **Theory:** under mild assumptions BER is about proportional to market makers' equilibrium estimate of the adverse-selection cost (`mm-adverse-selection-rl.md:41` (p. 2)).
- **Use:** the RL maker that sees BER "avoid[s] large losses due to adverse selection and achieve[s] stable performance" (`mm-adverse-selection-rl.md:9` (p. 1); *their claim*).

## Assumptions against the Arena
- One-tick futures books with real informed flow. Computable here from data alone *(inferred)*: market trades at or above the ask in `Tick.trades` over the size at the best ask in `Book`, per tick window.

## In our notation
BER per side, over the last w ticks, as a gate on `make` (pull or widen the side being eaten); `IDEAS.md` has the test.

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction, section 3's definition and the theory's statement.
- **Skimmed:** the RL set-up and results.

## Cited by
[hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
