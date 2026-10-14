---
title: Mahfouz, Balch, Veloso & Mandic, "Learning to classify and imitate trading agents in continuous double auction markets" (2021)
type: source
repo: literature_md/classify-trading-agents
status: partly-read
updated: 2026-10-14
---

# Mahfouz, Balch, Veloso & Mandic, "Learning to classify and imitate trading agents in continuous double auction markets" (ICAIF 2021)

## What it is
In an agent-based order-book market (ABIDES), classify which archetype placed an order (market maker, market taker, mean reversion, momentum, against noise and value background agents) from features of its orders, and imitate each archetype by behavioural cloning (`classify-trading-agents.md:13` (p. 1)). From the ICAIF 2020–2024 triage.

## Main results
- **Classification works only partly:** trained on three simulated days and tested on the next two (`classify-trading-agents.md:223` (p. 4)), a feed-forward classifier and the baselines give "mixed performance" across archetypes, so the authors suggest an ensemble (`classify-trading-agents.md:244` (p. 5)).

## Assumptions against the Arena
- **It needs each order's owner as a label,** in a simulator where the archetypes are known. We see the book and anonymous (or, in some Prosperity rounds, named) market trades, not orders by owner.
- What carries over is the idea of describing bots by archetype; [informed counterparties](../concepts/informed-counterparties.md) did that by name on Prosperity data.

## In our notation
The archetypes are those `arena.diagnose` already separates by their effect: the market maker's walls, takers' trade impact, reversion and drift.

## Traps
- None found.

## Read depth
- **Read:** abstract, the agent archetypes (section 4), the classification set-up and its summary.
- **Skimmed:** the imitation (behavioural cloning) results.

## Cited by
[hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md).
