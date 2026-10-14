---
title: Balcau, Sánchez-Betancourt, Sarkadi & Ventre, "Detecting collective liquidity taking distributions" (2024)
type: source
repo: literature_md/collective-liquidity-taking
status: partly-read
updated: 2026-10-14
---

# Balcau, Sánchez-Betancourt, Sarkadi & Ventre, "Detecting collective liquidity taking distributions" (ICAIF 2024)

## What it is
Infer the mix of liquidity takers in a market, informed traders, noise traders and trend followers, from what anyone can see: the paths of the mid's trend and volatility, and traded volumes. Simulated markets with a strategic market maker; the mix is the label (`collective-liquidity-taking.md:13` (p. 1)). From the ICAIF 2020–2024 triage.

## Main results
- **Price paths alone are not enough:** the trend and the volatility each carry "insufficient information" about the mix; non-linearly combined with the volume path, the detector reaches an MCC of 0.708 and an F1 of 0.805, against 0.333 for chance (`collective-liquidity-taking.md:13` (p. 1), `collective-liquidity-taking.md:49` (p. 2)).

## Assumptions against the Arena
- Simulated agents with known types and a fixed population per run; the Arena's bots are unknown.
- **The lesson for day one** *(inferred)*: who is taking liquidity shows in volumes more than in the price path, so `arena.diagnose`'s trade-based columns (impact `R(h)`, trade-sign correlation `C(1)`) say more about the takers than the mid's drift and noise do.

## In our notation
Informed takers are what `trade_impact` detects (a lasting move after their trades); noise takers leave none; trend followers trade with the recent move.

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction, the agent types and the headline result.
- **Skimmed:** the ML pipelines and robustness checks.

## Cited by
[hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [informed-counterparties](../concepts/informed-counterparties.md).
