---
title: Wang, Ventre & Polukarov, "Multi-agent reinforcement learning for market making: competition without collusion" (2025)
type: source
repo: literature_md/marl-competition-no-collusion
status: read
updated: 2026-10-13
---

# Wang, Ventre & Polukarov, "Multi-agent reinforcement learning for market making: competition without collusion" (ICAIF 2025; arXiv:2510.25929)

## What it is
A simulation of RL market makers quoting against each other: a robust maker A (trained against an adversary that perturbs volatility and order flow), and three rivals, B1 (maximises its own PnL), B2 (maximises **minus A's PnL**), and B★ (a learned mix of the two) (`marl-competition-no-collusion.md:13` (p. 1), `marl-competition-no-collusion.md:149` (p. 3)). It is the counterpart of [Han](algorithmic-cooperation-mm.md)'s tacit-collusion result, from ICAIF 2025's proceedings (`references/SEARCH_LOG.md`, the ICAIF table); the user saved the ACM copy.

## Main results
- **The market** (`marl-competition-no-collusion.md:83-89` (p. 2, checked)): an exogenous Brownian mid; market orders in Poisson batches split evenly into buys and sells; a quote at distance `d` gets weight `exp(−αd)`, and each side's orders are shared out multinomially in proportion to the weights. So a tighter quote gets *more* of the flow, not all of it.
- **Two self-interested makers do not collude** (`marl-competition-no-collusion.md:259-263` (p. 5)): A alone earns 506 mean PnL; against B1 it earns 193 and B1 275, with 37% and 63% of the executions. The authors attribute the absence of collusion to the exogenous price, which no agent can push.
- **A spiteful rival wins the flow by quoting tighter** (`marl-competition-no-collusion.md:269` (p. 5), `marl-competition-no-collusion.md:277-281` (p. 6), `marl-competition-no-collusion.md:295` (p. 6)): against B2, A earns 81 and gets 16% of the executions; B2 earns 261 with 84%. B2's average spread is 1.48 against A's 2.52; A widens in response. A rival trained only to hurt A also profited well.
- **The hybrid B★** takes market share with "a milder adverse impact" on the others (abstract); the authors read this as more sustainable co-existence.

## Assumptions against the Arena
- **Soft priority.** In a real book, and in our `--vs`, the best price fills first; a tick inside takes the whole flow at that moment, not a larger share *(inferred: the effect of undercutting would be stronger here)*.
- **Learning agents.** Arena teams ship fixed bots per round; a spiteful team would have to design for it. When ranking is relative, hurting a rival and earning are not opposites.
- Results are means over simulated episodes; no real data.

## In our notation
- B2's behaviour is a rival with a smaller `make_edge` than ours, quoting inside us. `--vs` can play it: run the template against a copy with `make_edge` 0 or set to step inside, and read the split of fills and PnL (`IDEAS.md`).
- Our defence is not to widen like A did: the template keeps stepping one tick inside the best remaining quote while `make_edge` allows (`python/bots/template.py:789-794`), and `take` lifts a rival's quote that is better than fair.

## Traps
- "PnL" is in the simulator's units; only the ratios mean anything.

## Read depth
- **Read:** sections 1–3 (model, agents, rewards), 5.2–5.3 (the joint evaluations) and the conclusion; tables 5–6 from the text extraction (the fill model, eq. on p. 2, on the page image).
- **Skimmed:** 5.1 (single-agent robustness) and 5.4 (the hybrid agent).

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [algorithmic-cooperation-mm](algorithmic-cooperation-mm.md).
