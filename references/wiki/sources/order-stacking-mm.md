---
title: Chung, Chung, Lee & Kim, "Market making under order stacking framework: a deep RL approach" (2022)
type: source
repo: literature_md/order-stacking-mm
status: read
updated: 2026-10-14
---

# Chung, Chung, Lee & Kim, "Market making under order stacking framework: a deep reinforcement learning approach" (ICAIF 2022)

## What it is
A market maker on KOSPI 200 index futures (61 days of full LOB data, `order-stacking-mm.md:65` (p. 2)) that keeps resting orders at several levels beyond the best, so that when the price moves it already holds a good queue place there (**order stacking**, `order-stacking-mm.md:21` (p. 1)). Queue positions of all its orders enter an RL agent's state. From the ICAIF 2020–2024 triage.

## Main results
- **Stacking pays even for a simple rule** (Table 3, daily averages, `order-stacking-mm.md:228` (p. 7)): a rule-based maker loses 2.13 without stacking and earns 2.33 with it; RL makers earn 3.15 without, 4.58 with stacking, 5.57 with stacking and all five levels' queue positions in the state. The adverse-fill ratio falls from 0.551 to 0.483.
- **How cancels are applied matters** (`order-stacking-mm.md:91` (p. 3)): under uniform cancellation, subtracting the expected share `q·RQP` from the queue ahead every time (deterministic) was "highly optimistic" on their data, where cancels are frequent; drawing the cancel's location at random (wholly ahead with probability RQP) or binomially gave similar, less optimistic results. They used the binomial rule.

## Assumptions against the Arena
- **It needs orders that rest and a queue with time priority.** Prosperity has neither (orders live one tick; no time priority within a price, per Leo-Hawking); the Arena is unknown (`ON_THE_DAY.md`, probes 1 and 11).
- A one-tick, crowded futures book with frequent cancels.

## In our notation
- Stacking is quoting at several prices; the template quotes one price per side (`bots/template.py:571-576`), and `--resting` keeps each order's queue place (`arena/engine.py`).
- **For the `--queue prob` item in `TODO.md`:** their finding argues for sampling where a cancel falls, not subtracting its expected share, or at least for testing both *(inferred: the difference comes from fills being a threshold event on the queue ahead)*.

## Traps
- PnL units are not stated beyond "daily average"; compare ratios only.

## Read depth
- **Read:** sections 1–2 (stacking, queue positions, the cancellation assumption), the agents and Table 3.
- **Skimmed:** the network architecture and training.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md).
