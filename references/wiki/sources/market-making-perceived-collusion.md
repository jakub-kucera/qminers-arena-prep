---
title: Xiong & Cont, "Interactions of market making algorithms: a study on perceived collusion" (2021)
type: source
repo: literature_md/market-making-perceived-collusion
status: read
updated: 2026-10-14
---

# Xiong & Cont, "Interactions of market making algorithms: a study on perceived collusion" (ICAIF 2021)

## What it is
A game-theoretic dealer market: N market makers set spreads around a known price, order flow falls with the market spread, and a **market-share rule** splits it between them. The equilibrium and collusive spreads are derived, then four makers learn their spreads with decentralised MADDPG, seeing only their own spread and the market's (`market-making-perceived-collusion.md:39` (p. 1)). From the ICAIF 2020–2024 triage (`references/SEARCH_LOG.md`).

## Main results
- **The allocation rule decides whether learners collude** (`market-making-perceived-collusion.md:39` (p. 1)). Three rules (`market-making-perceived-collusion.md:142` (p. 4)): constant shares, shares decreasing exponentially in one's own spread, and winner takes all (the tightest spread gets the flow, i.e. price priority).
- **Constant shares:** the learners converge to the collusive spread (about 2.56 in their example, `market-making-perceived-collusion.md:283` (p. 6)). **Spread-dependent shares:** spreads cycle around the collusive level, above the equilibrium. **Winner takes all:** spreads oscillate violently but stay much lower; "seemingly collusive behavior is mostly alleviated" (`market-making-perceived-collusion.md:311` (p. 6)).

## Assumptions against the Arena
- Continuous spreads, a known fundamental price, and learners updating over thousands of rounds; Arena teams ship fixed bots per round *(inferred)*.
- **Price priority is the competitive case.** A real book, and our `--vs`, are winner-takes-all at a price. With discrete ticks, [Han](algorithmic-cooperation-mm.md) found Q-learners could still hold spreads above the competitive one ([contradictions](../contradictions.md), row on learned collusion).

## In our notation
The three rules map to `--vs` set-ups only partly: our engine is winner-takes-all by price; at one price the recorded volume goes first, then the bots' orders in a seeded random arrival order each tick (`arena/engine.py`), with no constant-share mode.

## Traps
- None found.

## Read depth
- **Read:** abstract, sections 1–3 (model, equilibria, allocation rules), the experiments and their figures' text.
- **Skimmed:** the proofs of propositions 3.11–3.14.

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [contradictions](../contradictions.md).
