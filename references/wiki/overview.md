---
title: Overview of what the references teach
type: overview
updated: 2026-10-10
---

# Overview of what the references teach

A synthesis of 25 sources (17 team or competition sources, three documents and articles, five tools) read on 2026-10-10 and 2026-10-11. Every line links to the concept page with the evidence and the caveats. The Prosperity record is the best match to the Arena's described format (a file uploaded to a portal and run on a backtest), but the Arena is a different competition, so treat all of it as a prior.

## What the record says about doing well

0. **Start with experiments on the environment, not strategies** ([probing](concepts/probing-the-environment.md)). The strongest statement of this is Frankfurt Hedgehogs' essay ([source](sources/timo-diehm-medium-article.md)): question the framing, then build controlled tests of how prices are generated, how matching works and whether bots are predictable. If the organisers hand out the simulator source, read it first.
1. **Find the simulator's true price first** ([fair value](concepts/fair-value-and-wall-mid.md)). The mark is the market maker's mid, not the top of book. Probe it; do not trust a definition because a famous team named it.
2. **A plain take / clear / make market maker is the backbone** of nearly every top result, and on the live day it beat the elaborate overlays that were built on top ([market making](concepts/market-making-and-inventory-skew.md)). Whether to skew against inventory is genuinely unsettled ([contradictions](contradictions.md)).
3. **Study the generator, not only the prices.** The largest single edges were properties of the simulator: empty book sides filled by far-away quotes ([hidden takers](concepts/hidden-takers-and-empty-sides.md)), jumps by round numbers that reverse ([snap-back](concepts/jumps-and-snap-back.md)), and exact sums and known baskets ([baskets](concepts/baskets-and-fixed-sums.md)).
4. **Expect one product to carry a round** and log per-product PnL from the first run ([backtesting](concepts/backtesting-and-tooling.md)).
5. **A fixed anchor and the handed-out days are both dangerous** ([drift and regime](concepts/drift-and-regime-change.md)).
6. **Name-based signals and statistical relationships between many products mostly did not survive** a held-out day ([informed counterparties](concepts/informed-counterparties.md), [validation](concepts/validation-and-overfitting.md)). The teams that tested out of sample kept their results.
7. **Use structure for many products**: one object per product, strategies as targets, one owner per structural edge, limits and safety nets above them ([architecture](concepts/many-products-architecture.md)).
8. **Choose risk by the scoring rule** and write down in advance when to stop ([risk](concepts/risk-and-protecting-a-lead.md)).
9. **AI agents are a productivity tool, not a substitute for understanding the production code** ([AI-assisted work](concepts/ai-assisted-work.md)).

## What probably carries to the Arena, and what does not
- **Carries (format-level):** a single uploaded file, a position-limit rule that cancels orders, a public backtest with downloadable data, probably hidden evaluation data and a cap on submissions ([submission mechanics](concepts/submission-and-scoring-mechanics.md)). Validation discipline, safety nets, and per-product logging carry regardless of the market.
- **Might carry (generator-level):** empty sides, repeating takers, discretisation, fixed sums. These are properties of IMC's generator; check the Arena's public data for each before building anything.
- **Does not carry:** product-specific constants (10,000, 50,000, 5,250), counterparty names, prior-edition data, conversions, live-exchange mechanics.

## What to read next
[`index.md`](index.md) for the page list, [`contradictions.md`](contradictions.md) for what is unsettled, and `ON_THE_DAY.md` for what to find out first on the day. The weakest parts of the evidence are listed on each source page under "Read depth".
