---
title: Online articles read through page-fetch summaries (no local copy)
type: source
repo: none
status: partly-read
updated: 2026-10-11
---

# Online articles read through page-fetch summaries (no local copy)

## What it is
Pages that could be fetched but are not saved in `references/`, so nothing here can be cited by line. Everything below is a summary produced by the fetch tool, not a reading of the full text: check a formula on the page before coding it.

## Layout and code map
- **Rigtorp, "Estimating order queue position"** (<https://rigtorp.se/2013/06/08/estimating-order-queue-position.html>): the probability model behind hftbacktest's `ProbQueueModel`. See [queue-position-and-fills](../concepts/queue-position-and-fills.md).
- **Databento, "Getting queue position from L2 and order book data"** (<https://databento.com/blog/getting-queue-position-from-l2-and-order-book-data>): compares L2 estimates with order-by-order data; cancels come mostly from the back of the queue.
- **Hummingbot, "Guide to the Avellaneda & Stoikov strategy"** (<https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/>) and **"Technical deep dive"** (<https://hummingbot.org/blog/technical-deep-dive-into-the-avellaneda--stoikov-strategy/>). As written on the deep-dive page: reservation price `r = s − q·γ·σ²·(T − t)`, total spread `γ·σ²·(T − t) + (2/γ)·ln(1 + γ/κ)`. **γ and κ are not estimated from the book**: they are derived from the user's minimum and maximum spread and an "inventory risk aversion" parameter (κ is chosen so that the spread at t = 0 is the maximum allowed). A finite closing time T is kept and parameters are recalibrated each cycle; an order-size shape factor η decays size with distance from the inventory target. Neither page offers backtest evidence.
- **Optiver explainers** (<https://www.optiver.com/insights/explainers/>): 33 short primers (only 18 listed on the page), of which ten concern options (pricing, Greeks, volatility, strategies) and one the order book ("Orders and the order book"). A free, concise alternative to a textbook if options appear. Titles read, articles not.
- **Quant.SE, "How do we estimate position of our order in order book"** (<https://quant.stackexchange.com/questions/3782/how-do-we-estimate-position-of-our-order-in-order-book>): **not fetchable** with our tools (the domain is blocked). Cited next to Rigtorp in hftbacktest's source.

## What carries over
- **Hummingbot's spread differs from our copy of A–S.** Its spread includes `γσ²(T − t)`; the A–S preprint in `literature_md/` has only `(2/γ)·ln(1 + γ/k)`. GLFT's footnote quotes A–S with the extra term, so the published A–S probably has it ([Avellaneda–Stoikov](hft-in-a-limit-order-book.md), "Traps").
- Hummingbot shows that the textbook Avellaneda–Stoikov is run in practice with heuristic parameters and a skew `q·γ·σ²·(T − t)` that depends on volatility and time left; compare with the linear skews teams shipped ([market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md)). Check the formulas against `literature_md/hft-in-a-limit-order-book/` before use.

## Traps
Summaries from a fetch tool can drop or misstate formulas (the Hummingbot guide page shows its formulas only as images).

## Read depth
- **Read (as summaries):** Rigtorp, Databento, the two Hummingbot pages, the Optiver listing.
- **Unread:** the individual Optiver articles; the Quant.SE thread (blocked).

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [options-and-vouchers](../concepts/options-and-vouchers.md).
