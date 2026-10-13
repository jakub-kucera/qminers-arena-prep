---
title: Quant.SE, "How do we estimate position of our order in order book queue?" (2012)
type: source
repo: literature_md/quant-se-order-position
status: read
updated: 2026-10-13
---

# Quant.SE, "How do we estimate position of our order in order book queue?" (question 3782, answered 2012)

## What it is
A Quantitative Finance Stack Exchange thread whose one answer (by the user "lehalle", 13.1k reputation, `quant-se-order-position.md:96-98` (p. 3), presumably Charles-Albert Lehalle *(inferred from the name only)*) gives two queue-estimation rules for a level-by-level feed. hftbacktest's `ProbQueueModel` docstring cites it next to [Rigtorp](rigtorp-queue-position.md) (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:130-138`). Our fetch tool is blocked on the domain; the user printed it on 2026-10-13.

## Main results
- **Set-up** (`quant-se-order-position.md:47-49` (p. 2, checked)): estimate the delay `δ̂` between your private fill messages and the public feed; after inserting `Q_i` at `P_i`, look for the level to grow by `Q_i` around `t_i + δ̂` to get the volume ahead `V̂₋(0)`. Track the volume behind `V̂₊` too. An increase of the level goes behind you.
- **Two rules for a decrease** `ΔV` (`quant-se-order-position.md:74-82` (p. 3, checked)):
  - **Risk-averse:** take it all from behind first, `V̂₊ ← [V̂₊ − ΔV]₊`, and only the overflow from ahead, `V̂₋ ← V̂₋ + [V̂₊ − ΔV]₋`. *This is our resting mode's rule and hftbacktest's `RiskAdverseQueueModel`* *(checked: same update as `arena/engine.py`'s module docstring and `hftbacktest/hftbacktest/src/backtest/models/queue.rs:81-84`)*.
  - **Neutral:** split it by `ℙ₊ = f(V̂₊)/(f(V̂₊) + f(V̂₋))`, the probability it was behind, for any increasing `f` ("you can take the identity"): `V̂₊ ← [V̂₊ − ℙ₊ΔV]₊` and `V̂₋ ← V̂₋ − (1 − ℙ₊)ΔV + [V̂₊ − ℙ₊ΔV]₋`. hftbacktest's `ProbQueueModel` implements exactly this update (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:195-204`).
- **What breaks the estimate** (comments and answer): pro-rata or other priority rules, routing instructions, hidden orders and members-only orders (`quant-se-order-position.md:29` (p. 1)); icebergs and venue internalisation (`quant-se-order-position.md:49` (p. 2)).

## Assumptions against the Arena
Same as [Rigtorp](rigtorp-queue-position.md): FIFO, and an event feed rather than one snapshot per tick.

## In our notation
`V̂₋` is our queue-ahead volume, `V̂₊` the visible level minus it. The risk-averse rule is `--resting` today; the neutral rule is the `prob` option of the `TODO.md` queue item.

## Traps
- **OCR:** the hats and the box symbol `□` (the level's size) are partly lost, and the risk-averse rule at `quant-se-order-position.md:74` (p. 3) has `V` for `V̂`. The prose between the formulas is garbled (`quant-se-order-position.md:49-70` (p. 2–3)); read it on the PDF.

## Read depth
- **Read:** the question, the comments and the answer.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [rigtorp-queue-position](rigtorp-queue-position.md).
