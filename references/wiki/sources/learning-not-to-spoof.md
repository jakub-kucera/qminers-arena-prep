---
title: Byrd, "Learning not to spoof" (2022)
type: source
repo: literature_md/learning-not-to-spoof
status: partly-read
updated: 2026-10-14
---

# Byrd, "Learning not to spoof" (ICAIF 2022)

## What it is
In an agent-based market, first learn to recognise a hand-coded spoofer's action sequences; then show that a plain profit-maximising RL trader discovers spoofing on its own; then use the recogniser to shape its reward so it stays profitable without spoofing (`learning-not-to-spoof.md:9` (p. 1)). Split from the local `ICAIF_2022_proceedings.pdf` (pp. 139–147 printed).

## Main results
- **Spoofing is found, not designed:** the RL trader independently discovers it as its optimal strategy (`learning-not-to-spoof.md:9` (p. 1)).
- **A recogniser as a guard:** with the recogniser in its reward, the agent remains profitable while avoiding spoofing that would have paid even more.

## Assumptions against the Arena
- **For our own tuning** *(inferred)*: an optimiser over a reactive day generator (`harder-rounds`, A1) could discover spoof-like order patterns; check any tuned bot for large orders it never lets fill.
- For rivals: an RL-tuned bot in a shared market may spoof without its authors meaning it to.

## In our notation
The recogniser's inputs are order sequences: submissions, cancels and fills per tick, which `_orders.csv` and `_fills.csv` record for our own bot.

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction.
- **Skimmed:** the experiments and the reward shaping.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
