---
title: DeLise, "The negative drift of a limit order fill" (2024)
type: source
repo: literature_md/negative-drift-of-a-fill
status: partly-read
updated: 2026-10-13
---

# DeLise, "The negative drift of a limit order fill" (arXiv:2407.16527, 2024)

## What it is
A short argument, in a three-outcome tick model and in a market simulation on 10-year Treasury futures (`negative-drift-of-a-fill.md:187-189` (p. 14)), that **limit-order fills coincide with adverse price moves**, so fill models that treat fills as random arrivals overstate a market maker's PnL. Found in the arXiv sweep of 2026-10-13.

## Main results
- **The model** (`negative-drift-of-a-fill.md:119-136` (p. 11, checked)): each step the mid moves up a tick, stays, or moves down a tick. A buy at the best bid always fills on a down move, and fills with probability `R_f` otherwise. Then `E[d | fill] = (R_f·P(U) − P(D)) / P(f)`, with `P(f) = P(D) + R_f·(P(M) + P(U))`. With `P(U) = P(D)` and `R_f < 1` the expected move after a buy fill is negative; empirically `R_f` is close to 0.
- **Simulation** (Table 5 and the text around it, `negative-drift-of-a-fill.md:291-306` (p. 22–23)): one naive market maker's orders replayed four ways on the same data. Filling against every market order (85% of orders filled) is the most optimistic; Poisson arrivals give too few fills (30%); the author's rule, **always fill on an adverse move plus a calibrated random fill otherwise**, gives 65% against the live simulator's 60% and the closest PnL path.
- **Textbook fill assumptions it criticises:** filling at-the-touch orders against every market order (`negative-drift-of-a-fill.md:51` (p. 6)), and continuous-price models where fills do not move the mid.

## Assumptions against the Arena
- A one-tick spread, where any move against the order fills it. With 2–21-tick spreads, a move of a tick need not reach a resting quote *(inferred)*.
- **Our `--resting` mode already has the adverse-fill rule:** a resting order fills when the next snapshot crosses it (`Fill.source == "cross"`, `python/arena/engine.py` module docstring) *(checked: the docstring)*. In the default mode orders live one tick, so the issue reduces to which tick's trades they meet.

## In our notation
`E[d | fill]` is the fill's markout at one tick in `arena.analysis`, measured against the arrival mid. The paper's prediction for us: markouts after passive fills should be negative on average where spreads are one tick.

## Traps
- **OCR:** eq. 3 reads `E_t[d_t f]` where the PDF has `E_t[d_t | f]`, the conditional bar lost (`negative-drift-of-a-fill.md:133` (p. 11)).

## Read depth
- **Read:** sections 1–3 and the simulation results.
- **Skimmed:** section 3.1 (the compound Hawkes version) and the discussion.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md).
