---
title: Risk appetite and protecting a lead
type: concept
updated: 2026-10-10
---

# Risk appetite and protecting a lead

## Summary
How much variance to take depends on how the competition scores. Teams that were ahead repeatedly lost the lead by keeping variance on; the cleanest counter-example stopped trading once first place was mathematically safe.

## What the sources say
- **Scoring formats differ** and set the right risk appetite: UChicago scored `(rank − 1)²` per round with later rounds weighted more, rewarding consistency (`uchicago-trading-2026/README.md:83`, `uchicago-trading-2026/README.md:221`); AlgoTrade scored log-scaled profit against the best team (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:415-426`); Prosperity ranked by cumulative PnL with a leaderboard reset after the qualifier (`prosperity4-ryan-challman/README.md:11`); the Arena's site shows weights 10/20/30/40% over four phases (`ON_THE_DAY.md`, "Known so far"). The Arena's Technical Rules decide which of these it resembles.
- **Cut variance when ahead:** Linear Utility left delta unhedged on the coconut coupon while 2nd, lost, and fell to 26th (`prosperity2-linear-utility/README.md:169`).
- **Stop when the lead is safe:** UChicago's winners computed the rank they needed in the last round (top 11 of 41) and stopped the bot after ~8 minutes, because teams were manipulating books in the final minutes (`uchicago-trading-2026/README.md:233`).
- **A manual click-trading side bet is a tail risk:** an exchange freeze plus news cost ~$200k in seconds and turned a top-5 round into 35th (`uchicago-trading-2026/README.md:203`, `uchicago-trading-2026/README.md:231`).
- **An aggressive objective can hurt:** Baguette Fromage optimised `E[PnL] − 0.25 Std` for round 4 and say that likely explains the worse round (`prosperity4-baguette-fromage/README.md:827-840`).
- **Size down a one-day edge:** Ryan Challman's `ROBOT_DISHES` weight 0.06 (`prosperity4-ryan-challman/README.md:137`).
- **Rank is partly luck:** Alpha Animals' 2nd place after round 3 came from a bug that happened to pay (`prosperity3-alpha-animals/README.md:135`).
- **Fractional Kelly** was the staking rule in the Qminers sports-betting solution: 25% Kelly, 5% per bet, 20% per day (`qminers-hackathon-2025/README.md:25-27`; theory in `literature_md/kelly-criterion/`).

- **Correlated books stack risk** (Leo-Hawking): applying the same mean-reversion logic to all highly correlated assets makes every asset build positions in the same direction at once, which hurt in round 4 (rank 95th to 132nd) though the market had been friendly in round 3 (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:408-446`).

## Where they disagree
No team argues for more variance after taking a lead.

## What it means for our code
Nothing yet. The decision is a policy (flatten, or stop) rather than a strategy; the template has no end-of-round flatten parameter (a deferred item in `TODO.md`).

## How to test it here
Once the Technical Rules give the scoring formula, compute what rank or PnL secures each outcome and decide in advance, in writing, when to stop. Log per-product PnL from the first run.

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [UChicago](../sources/uchicago-trading-2026.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [Qminers 2025](../sources/qminers-hackathon-2025.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md). [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md).
