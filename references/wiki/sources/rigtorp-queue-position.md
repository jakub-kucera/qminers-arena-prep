---
title: Rigtorp, "Estimating order queue position" (2013)
type: source
repo: literature_md/rigtorp-queue-position
status: read
updated: 2026-10-13
---

# Rigtorp, "Estimating order queue position" (blog post, 2013-06-08)

## What it is
A two-page blog post by Erik Rigtorp on estimating where your order sits in a FIFO queue when the feed only shows the aggregate size per price level. It is the method behind hftbacktest's `ProbQueueModel`, whose docstring cites it next to the [Quant.SE answer](quant-se-order-position.md) (`hftbacktest/hftbacktest/src/backtest/models/queue.rs:130-138`). Printed from <https://rigtorp.se/2013/06/08/estimating-order-queue-position.html> by the user on 2026-10-13.

## Main results
- **Initial position** (`rigtorp-queue-position.md:13` (p. 1, checked)): an order of size `S` at price `P` starts with `V̂(t₀) = Q(t₀)`, the level's size when the order is sent (or at the acknowledgement, or their average). If the feed shows the level growing by `S` shortly after, set `V̂ = Q − S` at that moment.
- **Fills** (`rigtorp-queue-position.md:14` (p. 1, checked)): when the feed tells fills from cancels, a fill at `P` moves the order up one for one, `V̂(n + 1) = max(V̂(n) + ΔQ(n), 0)`.
- **Other decreases** (`rigtorp-queue-position.md:30-34` (p. 2, checked)): `V̂(n + 1) = max(V̂(n) + p(n)ΔQ(n), 0)`, with `p(n)` the probability that the decrease was **ahead** of us,
  `p(n) = f(V̂(n)) / (f(V̂(n)) + f(max(Q(n) − S − V̂(n), 0)))`,
  i.e. `f(ahead) / (f(ahead) + f(behind))`, for an increasing `f` such as `ln(1 + x)` or the identity. `f` "would ideally be estimated using data from our own fills".

## Assumptions against the Arena
- **FIFO price-time priority.** Leo-Hawking found Prosperity had no time priority within a price ([queue position](../concepts/queue-position-and-fills.md)); the Arena's rule is unknown (`ON_THE_DAY.md`, probe 11).
- **Event time.** The rule runs once per book update. With one snapshot per tick, several cancels and adds at a level net out into one change, so the estimate sees less than an event feed would *(inferred)*.

## In our notation
| Rigtorp | Ours (`arena/engine.py`, resting mode) |
|---|---|
| `V̂` (volume ahead) | the order's queue-ahead volume |
| `Q − S − V̂` (volume behind) | the visible level minus the volume ahead (our orders are not in the recorded book) |
| fills at `P` | the data's market trades at the order's price, which use up the queue ahead first |
| `p(n)` | 0 in our model until the volume behind is used up (the level is clipped, `front = min(front, level)`) |

## Traps
- **Which way `p` points.** Rigtorp's `p` is the share *ahead*; hftbacktest's `prob` is the share *behind*, `f(back)/(f(back) + f(front))`. The two are the same model.
- **`ln(1 + x)` is not a back-of-queue bias everywhere.** It pulls the split toward one half: with 100 ahead and 10 behind, 66% of a decrease lands ahead (91% with the identity), but with 10 ahead and 100 behind, 34% lands ahead (9% with the identity) *(computed here)*. So it blames the back more than uniform only while more volume is ahead of us than behind. For a bias toward the back at every position, see [Databento](databento-queue-position.md).
- **OCR:** the inline math is lost from the prose (`rigtorp-queue-position.md:13-22` (p. 1–2)). The first display formula (`rigtorp-queue-position.md:30` (p. 2)) repeats the cancel rule with `p(n)`; on the page that line is the fill rule without `p(n)`, which is in the prose at `rigtorp-queue-position.md:14` (p. 1).

## Read depth
- **Read:** all of it (two pages).

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [databento-queue-position](databento-queue-position.md), [quant-se-order-position](quant-se-order-position.md).
