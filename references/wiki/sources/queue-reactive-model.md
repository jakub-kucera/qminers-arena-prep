---
title: Huang, Lehalle & Rosenbaum, "Simulating and analyzing order book data: the queue-reactive model" (2015)
type: source
repo: literature_md/queue-reactive-model
status: partly-read
updated: 2026-10-12
---

# Huang, Lehalle & Rosenbaum, "Simulating and analyzing order book data: The queue-reactive model" (Journal of the American Statistical Association, 2015)

## What it is
A 29-page model of the order book as a Markov queueing system. The arrival rates of limit orders, cancellations and market orders at each level depend on the **current queue sizes**. A reference price jumps when a best queue empties. It is meant as a **market simulator** for testing execution tactics, and DTU Quant Lab cites it for queue-aware quoting ([DTU](prosperity4-dtu-quant-lab.md)). The data is France Telecom and Alcatel-Lucent on Euronext Paris, both large-tick.

## Main results
- **Setup** (`queue-reactive-model.md:45-60` (p. 3–4)):
  - Track K = 3 levels a side around a reference price. Queue sizes are counted in average event sizes.
  - Within a period of constant reference price, the book is a continuous-time Markov jump process: each level gains an order at rate `f_i(q)` and loses one at rate `g_i(q)`.
- **Model I, independent queues** (`queue-reactive-model.md:130` (p. 7)): `f_i = λ^L_i(q_i)` and `g_i = λ^C_i(q_i) + λ^M_i(q_i)`, estimated by maximum likelihood from waiting times between events.
- **Estimated shapes** (France Telecom, `queue-reactive-model.md:160-172` (p. 8–10)):
  - At the best level, limit-order arrivals are roughly constant in queue size, and lower when the queue is empty.
  - **Cancellations rise concavely, then flatten**, not linearly as in the classic Poisson models.
  - **Market orders fall exponentially with the volume available:** traders "rush for liquidity" when it is scarce.
  - Models II-a and II-b add dependence between the first two levels and between bid and ask.
- **Execution probability** (`queue-reactive-model.md:277-287` (p. 16, checked)):
  - A buy order joins the best bid; its probability of filling before the ask queue empties is computed by Monte Carlo under each model.
  - Cancellations are taken uniform over the orders ahead (Assumptions 3–4). The authors note "orders with lower priority are actually more likely to be canceled", so their probabilities "might be slightly overestimated".
  - **A Poisson model with a linear cancellation rate clearly overestimates execution.**
- **Queue-reactive model** (Model III, `queue-reactive-model.md:289-325` (p. 16–18)):
  - When the mid moves and a best queue is empty, the reference price moves with probability `θ`; with probability `θ_reinit` the book is redrawn from its stationary law, representing exogenous information.
  - Fitted values for France Telecom are θ = 0.7 and θ_reinit = 0.85.
  - With no exogenous redraws, the order flow alone produces 5 bps of 10-minute volatility against 14 bps observed. Book dynamics alone are strongly mean-reverting (`queue-reactive-model.md:323` (p. 18)).
- **Use as a simulator** (`queue-reactive-model.md:327-381` (p. 18–22)): comparing "fire and forget" with "peg to the best" execution tactics, the concave impact profiles reproduce the square-root law.
- **Scope** (footnote 1, `queue-reactive-model.md:33` (p. 2)): "relevant for any asset whose average spread is smaller than 2.5 ticks".

## Assumptions against the Arena
- **Spread under 2.5 ticks.** P3 Kelp and Squid Ink sit at 2–4 ticks (borderline) and P4 round 1 at 13–21 *(checked, [micro-price](micro-price.md))*.
- **Needs event data.** It counts insertions, cancels and market orders per level. Prosperity gives snapshots per tick plus trades, so only net queue changes can be inferred, the same limit as `--resting`'s queue estimate (`CLAUDE.md`, "Known gaps").
- **Prosperity has no queue priority** ([queue position](../concepts/queue-position-and-fills.md), Leo-Hawking). The model becomes relevant only if the Arena runs a FIFO book with persistent orders.
- **The useful result for us is the direction of the bias:** uniform-cancellation queue models overestimate fills for the order at the back. Our `--resting` (cancels never advance you) is pessimistic; `ProbQueueModel` with `f(x) = x` is close to uniform, so it errs on the optimistic side *(inferred)*.

## In our notation
| Paper | Ours |
|---|---|
| `Q_{±i}`, `q_i` | book levels in `book.bids` / `book.asks`; volumes in lots, not average event sizes |
| `λ^C_i(q)` (cancellation intensity) | not observable from snapshots; the visible level shrinking without a trade is the closest proxy |
| uniform cancellation over orders ahead (Assumptions 3–4) | `ProbQueueModel` with `f(x) = x` |
| execution probability before the opposite queue empties | fill rate of `--resting` quotes before the price moves |

## Traps
- **OCR:** the maximum-likelihood estimators of the intensities are missing; the text says "where 'mean' denotes the empirical mean" with no formula before it (`queue-reactive-model.md:138-158` (p. 7–8)).
- **OCR:** the generator definition has `Q_{q,q} = −Σ_{q∈Ω, ≠q} Q_{q,q}` (`queue-reactive-model.md:55` (p. 4, unchecked)); it should sum `Q_{q,p}` over `p ≠ q`. Not checked against the PDF.

## Read depth
- **Read:** abstract, introduction, section 2.1, 2.3 (Model I and its empirical shapes), 2.5 (execution probability), section 3 (the queue-reactive model and the tactic study), conclusion.
- **Checked against the PDF (page images):** Assumptions 3–4 and the execution-probability comparison (p. 16).
- **Mapped only:** sections 2.2 (reference-price estimation), 2.3.3 and 2.4 (Models II-a and II-b, asymptotics), the appendix (proofs, quasi-birth-death solution, Alcatel-Lucent results).

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md).
