---
title: Cartea, Chang & García-Arenas, "Spoofing order books with learning algorithms" (2023; thesis chapters, 2025)
type: source
repo: literature_md/spoofing-learning-algorithms
status: partly-read
updated: 2026-10-14
---

# Cartea, Chang & García-Arenas, "Spoofing order books with learning algorithms" (SSRN 4639959, 2023), as chapters 2–3 of García-Arenas's DPhil thesis (Oxford, 2025)

## What it is
When will a learning market maker discover quote-based manipulation, posting a large order on one side to tilt the book and buy or sell on the other? Conditions that depend only on observable book dynamics, tested on Euronext, LSE, Nasdaq and NYSE stocks (`spoofing-learning-algorithms.md:37` (p. 4)). SSRN blocks downloads, so the local file is pages 11–82 of the thesis (openly hosted by Oxford's repository), chapters 2 and 3, which present the paper.

## Main results
- **The mechanism** (`spoofing-learning-algorithms.md:15` (p. 2)): traders read a volume imbalance at the best quotes as news, so a large order on one side raises the arrival of market orders from the other side; with a non-zero tick, that lets the manipulator fill its genuine order at a better price.
- **Who learns to spoof** (`spoofing-learning-algorithms.md:37` (p. 4)): a maker more tolerant of inventory risk; and the range where manipulation is optimal shrinks with the quoted spread, vanishing at zero spread. In every stock studied an algorithm learns to manipulate for some range of inventory aversion; Nasdaq's conditions favour it.

## Assumptions against the Arena
- A stationary Markov strategy over inventory and the imbalance state; any learning algorithm that finds an optimal stationary policy qualifies.
- **Two consequences** *(inferred)*: rival or organiser bots tuned by learning in a market with an imbalance signal and a spread of a tick or more may spoof; and our own tuning should not be allowed to discover it, since the organisers verify solutions (`ON_THE_DAY.md`, reproducibility) and manipulation is likely against the rules.

## In our notation
The imbalance state is `ρ` of [book imbalance](../concepts/book-imbalance-and-micro-price.md); the template does not post orders it means to cancel.

## Traps
- The thesis numbering (chapters 2–3) differs from the SSRN paper's sections.

## Read depth
- **Read:** chapter 2's introduction and summary of results.
- **Skimmed:** the model, proofs and chapter 3's empirical extensions.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md).
