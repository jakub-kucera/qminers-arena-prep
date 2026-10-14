---
title: Li, Polukarov & Ventre, "Detecting financial market manipulation with statistical physics tools" (2023)
type: source
repo: literature_md/manipulation-statistical-physics
status: partly-read
updated: 2026-10-14
---

# Li, Polukarov & Ventre, "Detecting financial market manipulation with statistical physics tools" (ICAIF 2023; arXiv:2308.08683)

## What it is
Orders as particles: size is mass, the change of an order's distance to the mid over time is velocity, and the book's momentum summarises its state; spikes flag spoofing and layering (`manipulation-statistical-physics.md:11` (p. 1)). Applied to the LUNA crash and bitcoin; split from the local `ICAIF_2023_proceedings.pdf` (pp. 565–573 printed).

## Main results
- The momentum measure picked out widespread spoofing and layering during LUNA's crash and beat a z-score anomaly detector on LUNA and bitcoin (`manipulation-statistical-physics.md:11` (p. 1)).

## Assumptions against the Arena
- It needs order events (submissions, cancellations, market orders); from snapshots only level changes are visible, so an approximation would treat a level's growth as submissions and its unexplained shrinkage as cancels *(inferred)*.

## In our notation
Level changes between consecutive `Book`s, signed by side and weighted by distance to the mid.

## Traps
- None found in what was read.

## Read depth
- **Read:** abstract, introduction, the momentum definition.
- **Skimmed:** the experiments.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
