---
title: Databento, "Getting queue position from L2 and order book data" (2025), with its tutorial
type: source
repo: literature_md/databento-queue-position
status: read
updated: 2026-10-13
---

# Databento, "Getting queue position from L2 and order book data" (blog post, 2025-02-26) and the tutorial behind it

## What it is
A short blog post comparing a queue-position estimate built from level data (MBP-10) against the exact position from order-by-order data (MBO), plus the docs tutorial it summarises. The post was printed by the user on 2026-10-13. The tutorial needs JavaScript, so it was rendered with headless Chrome and saved as text: `online-snapshots/databento-queue-position-tutorial.md` (formula, code and prose; no chart).

## Main results
- **The model** (`databento-queue-position.md:17-25` (p. 2, checked)): `p(x)` is the probability that a cancel at the level is **in front of** you when you are a fraction `x` of the way back in the queue; `p(1) = 1` when you have just joined, `p(0) = 0` at the front, and `p(x) = x` is uniform. A bias `k` (−1 < k ≤ 0) makes cancels come more from the back.
- **What the code actually computes** (`online-snapshots/databento-queue-position-tutorial.md:277-292`, `online-snapshots/databento-queue-position-tutorial.md:377-384`): it draws `u ~ U(0, 1)`, transforms it to `u^{1+k}`, and counts the whole decrease as ahead of you when that is below `x`. So **`P(ahead) = P(u^{1+k} < x) = x^{1/(1+k)}`**: `x⁵` at k = −0.8, `x²⁰` at k = −0.95 *(derived, and confirmed by simulating the tutorial's `apply_bias` with 200,000 draws: at x = 0.9, 0.588 and 0.122 against 0.590 and 0.122)*.
- **The evidence** (one ES futures order, `GLBX.MDP3`, 2025-02-12, size 1, `online-snapshots/databento-queue-position-tutorial.md:302-312`; the chart on the post's p. 3): over the order's 175 s life, the visible level grew from about 65 to 75 while the true volume ahead fell from about 65 to 54, then to 46 at 140 s and 24 just before the fill. The uniform estimate fell to about 2; k = −0.8 ended near 35; k = −0.95 stayed near 53 *(read off the chart)*. For most of the order's life the truth sat **above even the k = −0.95 curve**, between it and a model that takes every cancel from behind (ours).
- **Their conclusions** (their claims): "cancels are mostly pulled from the back of the queue" (`databento-queue-position.md:31` (p. 3)); the most common mistake is underestimating the bias, and every L2 "market replay" backtester they have come across was overly optimistic about passive fills, and also underestimates adverse fills (`databento-queue-position.md:33` (p. 3)); estimates break once the price leaves the visible levels (`databento-queue-position.md:35` (p. 3)).

## Assumptions against the Arena
- **A real exchange's queue** (ES futures, FIFO, many participants who cancel stale orders). In Prosperity the bots re-quote every tick, which is a different mechanism; that is the case for the `front` option in `TODO_DONE.md`, not for this one.
- **One order on one day.** The direction is plausible and agrees with Huang, Lehalle & Rosenbaum's caveat ([queue-reactive model](queue-reactive-model.md)); the size of the bias is not established.

## In our notation
- `x` = volume ahead / (visible level − own size): `front / (front + back)` in hftbacktest's terms.
- `P(ahead) = x^n` with `n = 1/(1 + k)` is hftbacktest's `PowerProbQueueFunc3`, whose `prob` (the share behind) is `1 − (front/(front + back))^n` (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:309-327`). `n = 1` is uniform; `n → ∞` is our resting mode, where nothing ahead is cancelled until the volume behind is used up.

## Traps
- **The formula on the tutorial page is the inverse of the code.** The page writes `p_k(x) = x^{1+k}` for k < 0 (`online-snapshots/databento-queue-position-tutorial.md:21`). Taken as `P(ahead)`, that would put *more* cancels in front as k falls (0.98 at x = 0.9, k = −0.8), the opposite of the text and the chart. The formula is the transform applied to the random draw; the probability is `x^{1/(1+k)}`.
- **Their simulation treats every decrease as a cancel**, trades included (`online-snapshots/databento-queue-position-tutorial.md:377`), and attributes each decrease wholly ahead or wholly behind, then takes the median of 100 runs (`online-snapshots/databento-queue-position-tutorial.md:397`). hftbacktest subtracts trades at the level first, then splits the rest in expectation (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:181-204`). Copy hftbacktest's update, not the tutorial's.
- **OCR:** the math-italic symbols came out as `��` (`databento-queue-position.md:17-21` (p. 2)); the text is legible on the PDF.

## Read depth
- **Read:** the post, the tutorial's prose and code; the chart, from the post's page image.
- **Not run:** the tutorial itself (it needs a Databento API key and paid data).

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [rigtorp-queue-position](rigtorp-queue-position.md).
