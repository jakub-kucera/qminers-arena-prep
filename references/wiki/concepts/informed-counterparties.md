---
title: Informed counterparties (named traders)
type: concept
updated: 2026-10-10
---

# Informed counterparties

## Summary
When the data names buyers and sellers (Prosperity 3 round 5, Prosperity 4 round 4), teams hunted for informed names. One pattern was clear and old (Olivia, who bought the daily low and sold the daily high); the Prosperity 4 `Mark XX` signals were weak and fragile, and the careful teams switched them off.

## What the sources say
- **Prosperity 3, Olivia:** bought 15 lots at the daily minimum and sold at the daily maximum; Frankfurt detected it from trade sizes and running extrema before names were revealed, and went to ±limit with her on Squid Ink (`prosperity3-frankfurt-hedgehogs/README.md:270-319`, code `prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:382-405`); Alpha Animals copy-traded her on Squid Ink and Croissants (`prosperity3-alpha-animals/README.md:163-175`). Names appeared only in round 5 *(checked)*.
- **Prosperity 4, the Marks** (names only in round 4's trade files *(checked)*):
  - DU: classification of Marks 01/14/22/38/49/55/67; **Mark 67 the informed buyer in velvetfruit** (mid +~2 ticks within 100 timestamps after he buys) (`prosperity4-du-trading/README.md:141-149`, `prosperity4-du-trading/README.md:157-163`). The published round 4 code does not read names (see [DU](../sources/prosperity4-du-trading.md)).
  - DTU: a decayed signed-flow tracker per (product, name); only Hydrogel with Mark 14 (+0.20) / Mark 38 (−0.20) shipped, the rest disabled because it hurt on some days (`prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:134-218`).
  - Ryan Challman: per-trader weights fitted on training days **did not generalise**; switching them off recovered ~$15.8k (`prosperity4-ryan-challman/README.md:89-91`).
  - Baguette Fromage: "for all Marks the signal was either too weak, too unstable, or too hard to monetize"; none shipped (`prosperity4-baguette-fromage/README.md:844-848`).
  - Alpha Search: only Mark 67 had a clear edge, too small after costs (`prosperity4-alpha-search/README.md:113-117`).
- **How to score names:** Alpha Animals' notebook tags a trade informed when it sits at a rolling price extreme and flags names above the 95th percentile (`counterparty_edge.ipynb` in [Alpha Animals](../sources/prosperity3-alpha-animals.md)); DTU used average forward dollars at a 200-tick horizon (`prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:134-143`).
- UChicago and AlgoTrade had no names on the wire (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:313`).

- **More Prosperity 4 readings of the Marks:** Leo-Hawking bucketed each bot's trades by price deviation from an EMA and found **Mark 14 and Mark 55** informed; following them added stable execution but "limited alpha", and their rank fell from 95th to 132nd (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:408-446`). heyman7913 (JaneRT) matched six recurring fingerprints before names were revealed and traded **Mark 67** (963 Velvetfruit buys in three days, 58.8% positive at 50 ticks, effect lasting ~3,000 ticks), **Mark 55** (informed Velvetfruit flow) and **Mark 01 with Mark 22** (multi-strike option baskets), each with a time-to-live of 3,000 or 6,000 ticks (`online-snapshots/heyman7913_imc-prosperity-4.README.md:373-398`).

## Where they disagree
Which Mark, if any, is worth acting on: see [contradictions](../contradictions.md), row 3. By team: Mark 67 (DU, heyman7913; Alpha Search found it real but too small), Mark 14 (DTU, Leo-Hawking), Mark 55 (Leo-Hawking, heyman7913), none that survived (Ryan Challman, Baguette Fromage).

## What it means for our code
`arena/model.py` `MarketTrade` already has `buyer` and `seller` (`arena/model.py:27-35`), and the Prosperity format passes them through. No strategy uses them.

## How to test it here
If the Arena names counterparties: forward-return table per name at 100/200/500 ticks, **leave-one-day-out**, a hard switch-off if any name flips sign across days. Do not ship a name-based signal that fails a held-out day (rule from [validation-and-overfitting](validation-and-overfitting.md)).

## Sources
[Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [DU Trading](../sources/prosperity4-du-trading.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [heyman7913](../sources/prosperity4-heyman7913.md).
