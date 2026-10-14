---
title: Hidden takers and empty book sides
type: concept
updated: 2026-10-14
---

# Hidden takers and empty book sides

## Summary
In Prosperity 4 round 1, one side of the book was empty on ~8% of ticks, and a bot would sometimes lift a quote placed far from fair on that side. Quoting ~100 away from the wall mid on an empty side was one of the biggest single edges of the round. The same simulator generated repeating taker events that could be predicted.

## What the sources say
- **Frequency** *(checked)*: 7.6% of rows in the Prosperity 4 round 1 data have an empty best side; none in rounds 3 and 5 (`prosperity4-backtester/prosperity4bt/resources/round1/prices_round_1_day_0.csv`). Baguette Fromage says about 8% (`prosperity4-baguette-fromage/README.md:354`).
- **Size of the edge** (their claim): a quote at about 100 from the previous wall mid, worth ~18.6k a day on Osmium (`prosperity4-baguette-fromage/README.md:356-365`); production used 98 as a margin (`prosperity4-baguette-fromage/README.md:392-394`, `prosperity4-baguette-fromage/Strategies/Phase1.py:243`). DU measured the bots' tolerance at **±100 for Osmium and ±120 for Pepper Root** and coded 98 and 120 (`prosperity4-du-trading/README.md:55`, `prosperity4-du-trading/README.md:71`, `prosperity4-du-trading/round2.py:557`, `prosperity4-du-trading/round2.py:560`).
- **Origin** (admins, via DU): the generator first produced the bots' quotes and then **randomly removed 20% of the orders** (`prosperity4-du-trading/README.md:77`).
- **Extra market access is a trap for this edge.** Paying for it ("~20% more quotes") would repair empty sides and add competition; Baguette Fromage and DU both chose not to bid (`prosperity4-baguette-fromage/README.md:500-519`, `prosperity4-du-trading/README.md:77`). The median bid was 50.
- **Recurring takers** (Baguette Fromage, round 2): takers reappeared at the same timestamp, side and size on the next day (97.7% for size ≥ 7 on Osmium), absent in round 1 and not in later rounds (`prosperity4-baguette-fromage/README.md:557-668`). The trade: clear the visible liquidity, leave one side empty, post an extreme quote, only if `p_repeat × q × edge > c_clear` (`prosperity4-baguette-fromage/README.md:651-661`). DU saw the predictable timestamps and did not exploit them (`prosperity4-du-trading/README.md:79`).
- **Earlier editions had the same family of leak.** In Prosperity 3 the bots behaved like Prosperity 2's to over 95%, so teams hard-coded trades at known timestamps; Frankfurt reported it and IMC fixed it (`prosperity3-frankfurt-hedgehogs/README.md:967-978`).
- Alpha Search missed the empty-side fill entirely (`prosperity4-alpha-search/README.md:81`).
- **Telling the takers apart** ([Balcau et al.](../sources/collective-liquidity-taking.md), [Mahfouz et al.](../sources/classify-trading-agents.md)): in simulation, the mid's trend and volatility say little about the mix of informed, noise and trend-following takers; with traded volumes added, a detector reached an MCC of 0.708 (`literature_md/collective-liquidity-taking/collective-liquidity-taking.md:49` (p. 2)). Classifying single orders by archetype gave mixed results even with labels (`literature_md/classify-trading-agents/classify-trading-agents.md:244` (p. 5)). So read the takers from trades (impact, sign correlation) rather than from the price path.
- **How fast the best level is eaten** ([Zhao & Linetsky](../sources/mm-adverse-selection-rl.md)): the book exhaustion rate per side (`literature_md/mm-adverse-selection-rl/mm-adverse-selection-rl.md:101` (p. 4)) flags the moments a taker is sweeping.

- **Large orders that never trade** (Lee et al., quoted in [Cartea, Jaimungal & Wang](../sources/optimal-spoofing.md)): on the Korea Exchange, spoof orders rested 6 or more ticks from the price at twice the usual size and rarely filled (`literature_md/optimal-spoofing/optimal-spoofing.md:49` (p. 4)). On Prosperity data the far levels are the bots' walls, so the size rule needs the product's own baseline.

## Where they disagree
Not about the effect; only about its persistence (present in R1/R2, gone in later phases).

## What it means for our code
`bots/template.py` has no rule for an empty side. Our engine matches unfilled orders against the tick's recorded market trades at the order's own price (`--match-trades`), so whether a far quote would fill in a replay depends on a trade existing in the data at that price. That has not been tested.

## How to test it here
Needs `--data p4` (`TODO.md`). Then: run Baguette Fromage's round 1 idea (quote ±98 from the last wall mid when a side is empty) on Prosperity 4 round 1 and see whether the engine produces fills. On the day: count empty sides and extreme-price trades in the Arena's public data before assuming any of this exists (`ON_THE_DAY.md`).

## Sources
[Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DU Trading](../sources/prosperity4-du-trading.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [prosperity4btest](../sources/prosperity4-backtester.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md) (the built-in market maker's ladder), [Balcau et al.](../sources/collective-liquidity-taking.md), [Mahfouz et al.](../sources/classify-trading-agents.md), [Zhao & Linetsky](../sources/mm-adverse-selection-rl.md), [Cartea, Jaimungal & Wang](../sources/optimal-spoofing.md).
