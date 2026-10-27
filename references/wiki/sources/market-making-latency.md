---
title: Gao & Wang, "Optimal market making in the presence of latency" (2018 preprint)
type: source
repo: literature_md/market-making-latency
status: partly-read
updated: 2026-10-27
---

# Gao & Wang, "Optimal market making in the presence of latency" (arXiv:1806.05849)

## What it is
A market maker on a large-tick asset whose orders reach the book with a delay, as a Markov decision process; the value of an order (its execution price against the fair value) is the one-period reward (`market-making-latency.md:7` (p. 1)). For `harder-rounds` C3; fetched from arXiv.

## Main results
- **When making pays** (`market-making-latency.md:7` (p. 1)): when the rate of small, uninformed market orders hitting the quotes is high enough against the rate of price jumps, and the horizon is long enough.
- **Latency is a further risk** that lowers profit.
- **The condition, exactly** (Theorem 4.1(c), `market-making-latency.md:205` (p. 12, checked)): an ask order has a positive value iff `λ+ > λ/2`, the bid likewise with `λ−`; `λ` is the rate of mid moves (up and down at `λ/2` each), `λ±` the rate of small market orders that hit the best without moving it. The reason (`market-making-latency.md:209-211` (p. 12)): a fill is either an uninformed hit, +0.5 tick, or the price jumping through the quote, −0.5 tick. Theorem 4.3 (`market-making-latency.md:267-268` (p. 15)): no profit if both sides fail; a positive one over a long enough horizon if both pass.

## Assumptions against the Arena
- **The test, on our data** (`arena.diagnose`'s `λ`, `λ+`, `λ-` columns and its large-tick note, 2026-10-27): on the ticks at a one-tick spread, `λ` is the share after which the mid moves and `λ±` the share with a market buy at the ask (sell at the bid) after which it doesn't. Our reading of the rates as shares of snapshots, one hit counted per tick and side *(inferred)*. On every P2–P4 large-tick product but the deepest P4 vouchers it says neither side pays: P3 Croissants λ+ 0.028, λ− 0.046 against λ/2 0.123, Djembes 0.023/0.026 against 0.265, the rock 0.002/0.007 against 0.446, its vouchers and P2's Chocolate, Roses, Strawberries, Coconut and its coupon alike; P4 `VEV_5400`/`VEV_5500` 0/0.007–0.010 against 0.027–0.115. P4 `VEV_6000`/`VEV_6500` (the mid never moves, λ 0; every trade a sell at the bid, λ− 0.009–0.011): the bid only, DU's bid at 0. The ABIDES days: both sides, barely (λ+ 0.139, λ− 0.138 against λ/2 0.116) (`IDEAS.md`, "Quote only where uninformed hits outnumber jumps").
- **The model fills our quote on every uninformed hit**, as if we were first in the queue. Behind a queue it fills only on the hits that empty it, mostly the jumps, so on ABIDES (queues of about 200 lots) both sides pass and resting quotes still lose. A mid move from a spread that widens counts as a jump here, which overstates `λ` where spreads flicker.

## In our notation
| Paper | Ours |
|---|---|
| uninformed hit rate `λ±` | `arena.diagnose`'s `lambda_buy` / `lambda_sell`: a market trade at the best with the mid unchanged a tick later, per one-tick-spread tick |
| jump rate `λ` | `arena.diagnose`'s `lambda`: the mid moved a tick later, per one-tick-spread tick |
| latency | the engine option in `TODO_DONE.md` (harder-rounds C3) |

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction and contribution summary; Theorem 4.1 and its discussion, Theorem 4.3 (pp. 12–15).
- **Skimmed:** the MDP and the numerical results.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
