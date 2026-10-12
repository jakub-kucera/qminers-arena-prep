---
title: Overview of what the references teach
type: overview
updated: 2026-10-12
---

# Overview of what the references teach

A synthesis of 25 sources (17 team or competition sources, three documents and articles, five tools) read on 2026-10-10 and 2026-10-11, plus the literature in `literature_md/` (19 documents with a source page, from 2026-10-12, including chapter maps of the two books; see "What the literature adds"). Every line links to the concept page with the evidence and the caveats. The Prosperity record is the best match to the Arena's described format (a file uploaded to a portal and run on a backtest), but the Arena is a different competition, so treat all of it as a prior.

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

## What the literature adds
Market-microstructure theory, read against the Prosperity record. Most of it was derived for large-tick equities (a 1-tick spread, long queues, Poisson order flow), while Prosperity's spreads are 2–21 ticks and its books are made by a few bots. So the theory mostly tells us **what to measure** and **which effects to expect to be small**. Findings from 2026-10-12:

1. **Book imbalance predicts the next move only at 1-tick spreads** ([book imbalance](concepts/book-imbalance-and-micro-price.md)). Gould & Bonart cut the forecast error by 20–30% on large-tick stocks but by only 2–6% otherwise, and Stoikov finds no information at a 4-tick spread. So test `ρ` per product with Gould & Bonart's design before building a micro-price. Prosperity marks PnL to the market maker's mid, which the wall mid estimates directly.
2. **Quoting at the touch regardless of the book loses to adverse selection** (Cartea et al. 2018: a negative Sharpe for 11 of 11 stocks). Quote a side only when the edge beats the expected move against you after a fill on that side, which is the markout our analysis already computes. Not yet broken down by book state.
3. **The template's linear `skew` is the textbook answer** ([optimal quoting](concepts/optimal-quoting-models.md)). GLFT's and Guéant's closed forms are "fair ± half-spread − c × inventory", linear and time-independent.
   - What theory adds is `c` from the product's fair-value volatility and fill-rate curve, so one risk knob can serve all products.
   - It predicts little or no skew on a pegged product, which fits Frankfurt and Baguette Fromage against DTU's Avellaneda–Stoikov loss ([contradictions](contradictions.md), row 1).
4. **Correlated products share one risk budget** (Guéant 2017): the skew on one product should use the inventory of its correlated products ([many products](concepts/many-products-architecture.md)).
5. **The best of N skill-less configurations looks good by construction**, by about `√(2 ln N)` standard errors ([validation](concepts/validation-and-overfitting.md)). When performance mean-reverts, the in-sample winner is expected to *lose* out of sample.
   - Count trials.
   - Estimate the probability of overfitting (CSCV) on the grid; decided worth building.
   - Pre-commit how portal submissions will be spent (the 37% stopping rule).
6. **Queue position matters for large-tick FIFO books, not for wide spreads** ([queue position](concepts/queue-position-and-fills.md)). In Prosperity, one tick of price buys priority, and Leo-Hawking found no queue at all, so the `--queue` options matter only if the Arena runs a FIFO book. Models with uniform cancellation overstate fills at the back.
7. **Order-flow imbalance explains moves, it doesn't forecast them** ([Cont et al.](sources/price-impact-of-book-events.md)). R² 65% on the same 10 seconds, and no test on the next interval. Its use for us is the impact of our own takes.
8. **Our template quotes the way Harris calls quote matching** ([shared market](concepts/shared-market-and-adversaries.md)). It quotes one tick in front of the bot's large quote, with that quote as a backstop. That is safe against a bot that doesn't cancel, and exactly what a rival can trap in a shared market. Resting quotes also give faster traders a timing option.
9. **Adverse selection has a measurable signature:** if counterparties are informed, the market maker's inventory is negatively correlated with the next price changes ([informed counterparties](concepts/informed-counterparties.md)). It is the first test for Kelp's long drift.
10. **Only pure arbitrages must revert** ([baskets](concepts/baskets-and-fixed-sums.md)). Known baskets and fixed sums revert; searched relationships may not. For a mean-reverting spread, optimal entry and exit bands are computable offline (Cartea et al. ch. 11, reproduced).
11. **The converted text is not the paper.** OCR dropped minus signs from tables and moved factors in and out of square roots. Several papers have typos of their own. Read every formula and table off the PDF before coding it (`literature_md/README.md`, "Caveats").

12. **On Prosperity data, the bots' trades don't move the fair value** ([price impact](concepts/price-impact.md)). Measured against the wall mid, the long-run move after a market trade is near zero in every product of P2 round 1 and P3 rounds 1–2 except the baskets, while takers pay 0.6–2.2 ticks. Against the raw mid the same trades seem to have a lasting impact, but it is selection: trades hit quotes that sit off the wall.
13. **The top-of-book mid is mostly noise at one tick** ([fair value](concepts/fair-value-and-wall-mid.md)). Bouchaud's volatility signature plot puts numbers on it: Kelp's mid varies 28 times more per tick at lag 1 than at lag 200, its wall mid 3 times. Our markouts use the mid, so they mix that noise into adverse selection.
14. **Size by edge over variance, then shade down** ([risk](concepts/risk-and-protecting-a-lead.md)). Kelly's `f* = (m − r)/s²` carries over only as a scaling: the Arena has position limits and a rank, not a compounding bankroll. Its useful facts are that half Kelly keeps 3/4 of the growth, that oversizing costs as much as undersizing with more risk, and that estimated edges run high.

## What to read next
[`index.md`](index.md) for the page list, [`contradictions.md`](contradictions.md) for what is unsettled, and `ON_THE_DAY.md` for what to find out first on the day. The weakest parts of the evidence are listed on each source page under "Read depth".
