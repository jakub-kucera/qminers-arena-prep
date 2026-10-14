---
title: Gao & Wang, "Optimal market making in the presence of latency" (2018 preprint)
type: source
repo: literature_md/market-making-latency
status: partly-read
updated: 2026-10-14
---

# Gao & Wang, "Optimal market making in the presence of latency" (arXiv:1806.05849)

## What it is
A market maker on a large-tick asset whose orders reach the book with a delay, as a Markov decision process; the value of an order (its execution price against the fair value) is the one-period reward (`market-making-latency.md:7` (p. 1)). For `harder-rounds` C3; fetched from arXiv.

## Main results
- **When making pays** (`market-making-latency.md:7` (p. 1)): when the rate of small, uninformed market orders hitting the quotes is high enough against the rate of price jumps, and the horizon is long enough.
- **Latency is a further risk** that lowers profit.

## Assumptions against the Arena
- **The test, on our data** *(inferred)*: per product, compare how often the data's market trades hit the best quotes without moving the price with how often the price jumps (`arena.diagnose`, the "jumps" column); a product where jumps are as frequent as uninformed hits is a poor one to quote, and more so if the Arena adds latency.

## In our notation
| Paper | Ours |
|---|---|
| uninformed hit rate `λ±` | market trades at the best per tick (`Tick.trades`) |
| jump rate | `arena.diagnose`'s "jumps" share |
| latency | the engine option in `TODO.md` (harder-rounds C3) |

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction and contribution summary.
- **Skimmed:** the MDP and the numerical results.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
