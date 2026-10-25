---
title: Moallemi & Yuan, "A model for queue position valuation in a limit order book" (2017)
type: source
repo: literature_md/queue-position-valuation
status: read
updated: 2026-10-13
---

# Moallemi & Yuan, "A Model for Queue Position Valuation in a Limit Order Book" (working paper, Columbia, 2017)

## What it is
A 33-page model of what a resting order is worth as a function of its place in a FIFO queue, for **large-tick** stocks (spread one tick, long queues). It is calibrated on NASDAQ ITCH order-by-order data. It is validated by a backtest that inserts artificial orders at the **back** ("regular") and the **front** ("touch") of the queue, which is the same comparison as our planned `--queue back|front` ([queue position](../concepts/queue-position-and-fills.md)).

## Main results
- **Order value** (eq. 1, `queue-position-valuation.md:101-123` (p. 8–9, checked)):
  - `V = α·(δ − AS)`: fill probability × (liquidity premium − adverse selection).
  - `δ = P_A − P_t` is the quote's distance from the efficient price, a half-spread if that is the mid.
  - `AS = E[P_{τ*} − P_t | fill]` is how far the efficient price has moved against the order by the time it fills.
- **Price model** (`queue-position-valuation.md:134-158` (p. 9–10)):
  - The efficient price moves by `λ·u` per trade of signed size u (linear permanent impact) and by price jumps.
  - Trades and jumps arrive as Poisson processes; a positive jump fills every order at the ask, and a negative one cancels it.
- **Queue model** (`queue-position-valuation.md:195-208` (p. 12)): trades eat the queue from the front. **Cancellations shrink the whole queue proportionally**, `q → ℓq` with `ℓ` drawn from a fitted Beta, "uniformly across different queue positions". Cancellations carry no information.
- **Value function** (Theorem 1, `queue-position-valuation.md:243-256` (p. 14, checked)):
  - `V(q, δ) = α(q)·δ − β(q)`, where `α` and `β` solve two Volterra integral equations (6)–(7) with boundary values (8).
  - Only *ratios* of arrival rates matter: jumps to trades `γ/μ` and cancels to trades `η⁺/μ`.
  - `α(q)` decreases with queue position, `AS = β/α > 0` and it **grows with queue position**: the back of a long queue fills only against large, informed trades (Theorem 2, `queue-position-valuation.md:271-290` (p. 15–16, unchecked)).
- **Calibration on BAC, August 2013** (`queue-position-valuation.md:320-347` (p. 17–18)):
  - About 1.4 trades a minute against about 125 cancellations a minute; average queue about 47,000 shares; jumps of about 0.9 ticks.
  - Front versus average queue position is worth 0.21–0.26 ticks a day, "comparable to the bid-ask spread" (`queue-position-valuation.md:384` (p. 20)).
- **Backtest validation** (Table 3, `queue-position-valuation.md:442-458` (p. 23–24, checked)), 9 stocks over 30 days:
  - The model matches the order-by-order simulation within about 0.05 ticks.
  - An order at the back is worth −0.04 to 0.15 ticks, with fill probability 0.53–0.64 and adverse selection 0.53–0.89 ticks.
  - At the front it is worth 0.03–0.31 ticks.
  - The back-to-front gap is over 0.1 ticks for BAC and CSCO and under 0.1 for PFE and PBR.
- **Scope** (`queue-position-valuation.md:72` (p. 6)): in small-tick assets "investors can obtain priority in the order book by competing on price and the important of queueing … is diminished".

## Assumptions against the Arena
- **Large-tick only.** Prosperity's spreads are 2–21 ticks *(checked, [micro-price](micro-price.md))*, the small-tick regime, where the paper says queue position matters little because one tick inside the spread buys priority. That is what the template does: it quotes one tick inside the best book quote (`python/bots/template.py:684-729`).
- **Prosperity has no queue at all,** per Leo-Hawking's round 0 probe: orders at the best price are processed regardless of arrival time ([queue position](../concepts/queue-position-and-fills.md)). The model matters only if the Arena runs a real FIFO book, an open question in `ON_THE_DAY.md`.
- **Proportional, uniform cancellations** is the same rule as hftbacktest's `ProbQueueModel` with `f(x) = x`. A decrease of size `c` at the level moves an order with `front` ahead and `back` behind forward by `c × front/(front + back)`, which is what uniform cancellation gives in expectation *(inferred from the two definitions)*. The order-by-order evidence (Rigtorp, Databento) says real cancels come more from the back, i.e. `log(1 + x)`, so this paper's queue model sits on the optimistic side of that.
- **The efficient price is estimated as the mid one minute after a fill;** our markouts do the same at 1–N ticks.

## In our notation
| Paper | Ours |
|---|---|
| `δ` | the quote's distance from fair: `make_edge` or more (`python/bots/template.py:45`) |
| `AS` | the markout of passive fills, sign-flipped (`python/arena/analysis.py:189`) |
| `α(q)` | fill rate of resting orders by queue position; measurable only in `--resting` mode |
| regular order / touch order | `--queue back` (our resting model today) / `--queue front` (`TODO_DONE.md`) |
| `ℓ`, uniform cancels | `ProbQueueModel` with `f(x) = x` (`TODO_DONE.md` proposes `P(ahead) = xⁿ`) |

## Traps
- **Typo in the paper itself:** case 2(b) says "J_k > 0. Under a negative price jump" (`queue-position-valuation.md:194` (p. 12)); the PDF has the same *(checked with `pdftotext`)*. It means `J_k < 0`.
- **Typo in the paper itself:** Table 3 lists "EMM" where Table 2 has EEM (`queue-position-valuation.md:451` (p. 23)).
- **OCR:** the definitions `ū⁺ ≜ E[u·1{u>0}]` and `J̄⁺ ≜ E[J·1{J>0}]` lost their indicators (`queue-position-valuation.md:238` (p. 14, checked)). The Figure 2 text is spilled into the body (`queue-position-valuation.md:76-82` (p. 6–7)).
- The paper's 0.21–0.26 tick gap compares the *front* with the *average* position, not the back.

## Read depth
- **Read:** sections 1–6.
- **Checked against the PDF (page images):** eq. (1) with its definitions, Theorem 1 with (6)–(8), Table 3.
- **Not read:** the supplementary proofs (Appendix A) and the two-sided-exponential closed form (Theorem 3, mapped only).

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md).
