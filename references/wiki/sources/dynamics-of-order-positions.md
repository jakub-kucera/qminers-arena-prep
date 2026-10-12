---
title: Guo, Ruan & Zhu, "Dynamics of order positions and related queues in a limit order book" (2015)
type: source
repo: literature_md/dynamics-of-order-positions
status: partly-read
updated: 2026-10-12
---

# Guo, Ruan & Zhu, "Dynamics of Order Positions and Related Queues in a Limit Order Book" (arXiv:1505.04810, 2015)

## What it is
A 42-page probability paper: fluid limits (law-of-large-numbers), diffusion limits and large deviations for **one order's position in the best bid queue**, together with the best bid and ask queue lengths. The order arrival process is general (Poisson, Hawkes, Cox). The part useful to us is the first-order (fluid) equation for how fast your position advances, and its extension to cancellations that are not uniform over the queue. That extension is the theory behind hftbacktest's probabilistic queue models ([queue position](../concepts/queue-position-and-fills.md)).

## Main results
- **Setup** (`dynamics-of-order-positions.md:53-74` (p. 4–5)):
  - Six order types: limit, market and cancel at the best bid and at the best ask.
  - Orders arrive at rate `λ`; the mean sizes are `V̄¹` (bid limit), `V̄²` (market sell at the bid), `V̄³` (bid cancel), and `V̄⁴…V̄⁶` for the ask.
  - `Z(t)` is the volume ahead of our order.
- **Fluid limit** (Theorem 11, `dynamics-of-order-positions.md:253-300` (p. 10, checked)):
  - `Q^b(t) = q^b − λv^b·t` and `Q^a(t) = q^a − λv^a·t`, with net depletion rates `v^b = −V̄¹ + V̄² + V̄³` and `v^a = −V̄⁴ + V̄⁵ + V̄⁶`.
  - **`dZ/dt = −λ·(V̄² + V̄³·Z/Q^b)`:** the position advances by every market order, plus the *share of cancellations that falls ahead of it*, which is `Z/Q^b` under uniform cancellation.
  - The time to execution `τ^z` has a closed form in `a = λV̄²`, `b = q^b/(λV̄³)` and `c = −v^b/V̄³` (eq. 2.11–2.12). The queues empty at `τ^b = q^b/(λv^b)` and `τ^a = q^a/(λv^a)`.
- **Non-uniform cancellation** (Section 5.1, `dynamics-of-order-positions.md:996-1008` (p. 30–31, checked)):
  - "One may assume (more realistically) that the closer the order to the queue head, the less likely it is cancelled."
  - Replace `Z/Q^b` by `Υ(Z/Q^b)`, with `Υ` increasing from `[0, 1]` to `[0, 1]`, `Υ(0) = 0` and `Υ(1) = 1`. The fluid limit carries over (Theorem 31).
- **Fluctuations:** order positions fluctuate around the fluid limit as mean-reverting Gaussian processes (Theorem 15). Hitting times and execution times have explicit expressions (Section 4). Mapped only.
- The authors cite Moallemi & Yuan's finding that queue position is worth about a half-spread (`dynamics-of-order-positions.md:25` (p. 2)).

## Assumptions against the Arena
- **Fluid limits need many orders.** Prosperity's best levels are often one bot's quote of a fixed size, refreshed every tick, so "rate of cancellations ahead of you" has little meaning there, and Leo-Hawking found no queue priority at all ([queue position](../concepts/queue-position-and-fills.md)). The value is the vocabulary for the `--resting` queue options, not a formula to fit to Prosperity data.
- **`Υ` is the queue-model choice in `TODO.md`** *(inferred mapping)*:
  - With `x = Z/Q`, our current `--resting` (cancels never advance you) is `Υ ≡ 0`.
  - hftbacktest's `ProbQueueModel` with `f(x) = x` is uniform cancellation, `Υ(x) = x`.
  - With `f(x) = xⁿ` it is `Υ(x) = xⁿ/(xⁿ + (1 − x)ⁿ)`.
  - `log(1 + x)` gives a `Υ` that depends on the queue size too.
  - "Front of the queue" is a separate assumption about where we join, not a `Υ`.

## In our notation
| Paper | Ours |
|---|---|
| `Z(t)` | the volume ahead of a resting order in `arena/engine.py`'s resting mode |
| `V̄²` (market orders at our level) | trades at our price in the trade files |
| `V̄³·Υ(Z/Q)` | the part of a visible level's shrinkage, net of trades, credited as "ahead of us"; zero today |
| `τ^z` | expected time to fill a resting quote |

## Traps
- **OCR:** the order-size vector reads `(V^bb, V^mbb, V^cbb, V^cb, V^mba, V^cba) := (V_1^i, V_1^i, …)`. The PDF's fourth type is `ba`, and the right side is `(V_i^1, …, V_i^6)` (`dynamics-of-order-positions.md:61` (p. 4, checked)).
- **OCR:** the matrix in (5.1) lost a column, five where the PDF has six (`dynamics-of-order-positions.md:1001` (p. 30)). (5.2) is intact.
- Theorem 11's closed form for `τ^z` needs `q^a/v^a > q^b/v^b` (the ask doesn't empty first).

## Read depth
- **Read:** the abstract and introduction, Section 2.1 (notation), Section 2.4 (Theorem 11), Section 5.1 (non-uniform cancellation).
- **Checked against the PDF (page images):** Theorem 11 with (2.7)–(2.13), (5.1)–(5.2).
- **Mapped only:** Sections 2.2–2.3 (assumptions, the Kurtz–Protter detour), 3 (diffusion limits, large deviations), 4 (applications: examples, hitting times), 5.2–5.3 and the appendix.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md).
