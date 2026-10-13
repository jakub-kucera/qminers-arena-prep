---
title: Risk appetite and protecting a lead
type: concept
updated: 2026-10-12
---

# Risk appetite and protecting a lead

## Summary
How much variance to take depends on how the competition scores. Teams that were ahead repeatedly lost the lead by keeping variance on; the cleanest counter-example stopped trading once first place was mathematically safe. For sizing, the Kelly criterion contributes edge-over-variance scaling and the case for sizing below the estimated optimum, but not its objective.

## What the sources say
- **Scoring formats differ** and set the right risk appetite: UChicago scored `(rank − 1)²` per round with later rounds weighted more, rewarding consistency (`uchicago-trading-2026/README.md:83`, `uchicago-trading-2026/README.md:221`); AlgoTrade scored log-scaled profit against the best team (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:415-426`); Prosperity ranked by cumulative PnL with a leaderboard reset after the qualifier (`prosperity4-ryan-challman/README.md:11`); the Arena's site shows weights 10/20/30/40% over four phases (`ON_THE_DAY.md`, "Known so far"). The Arena's Technical Rules decide which of these it resembles.
- **Cut variance when ahead:** Linear Utility left delta unhedged on the coconut coupon while 2nd, lost, and fell to 26th (`prosperity2-linear-utility/README.md:169`).
- **Stop when the lead is safe:** UChicago's winners computed the rank they needed in the last round (top 11 of 41) and stopped the bot after ~8 minutes, because teams were manipulating books in the final minutes (`uchicago-trading-2026/README.md:233`).
- **A manual click-trading side bet is a tail risk:** an exchange freeze plus news cost ~$200k in seconds and turned a top-5 round into 35th (`uchicago-trading-2026/README.md:203`, `uchicago-trading-2026/README.md:231`).
- **An aggressive objective can hurt:** Baguette Fromage optimised `E[PnL] − 0.25 Std` for round 4 and say that likely explains the worse round (`prosperity4-baguette-fromage/README.md:827-840`).
- **Size down a one-day edge:** Ryan Challman's `ROBOT_DISHES` weight 0.06 (`prosperity4-ryan-challman/README.md:137`).
- **Rank is partly luck:** Alpha Animals' 2nd place after round 3 came from a bug that happened to pay (`prosperity3-alpha-animals/README.md:135`).
- **Fractional Kelly** was the staking rule in the Qminers sports-betting solution: 25% Kelly, 5% per bet, 20% per day (`qminers-hackathon-2025/README.md:25-27`). The theory is in the sizing section below.

- **Correlated books stack risk** (Leo-Hawking): applying the same mean-reversion logic to all highly correlated assets makes every asset build positions in the same direction at once, which hurt in round 4 (rank 95th to 132nd) though the market had been friendly in round 3 (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:408-446`).

### Sizing: what Kelly says and what carries over
The Kelly criterion ([Thorp](../sources/kelly-criterion.md)) sizes each bet to maximise the long-run growth of reinvested capital:
- **Size is edge over variance:** `f* = (m − r)/s²` for a security (`literature_md/kelly-criterion/kelly-criterion.md:528` (p. 24, checked)), `f* = p − q` for an even-money bet.
- **Fractional Kelly is cheap insurance:** betting `c·f*` keeps `c(2 − c)` of the growth (`literature_md/kelly-criterion/kelly-criterion.md:556` (p. 26, checked)). Half Kelly keeps 3/4 of it and cuts the chance of ever losing half from 1/2 to 1/8 (`literature_md/kelly-criterion/kelly-criterion.md:692` (p. 32, checked)).
- **Overbetting is the expensive mistake:** `c = 1.5` loses as much growth as `c = 0.5` with three times the volatility, and `c = 2` loses all of it.
- **Estimated edges are too high,** through data mining, non-stationarity and competition for the same edge. Thorp's rule is to bet between `0.5f*` and `f*` of the *estimated* optimum (`literature_md/kelly-criterion/kelly-criterion.md:626-636` (p. 29–30)).

Only part of this carries over *(inferred)*:
- **The objective differs.** Kelly maximises log growth over many reinvested bets. The Arena scores four rounds, weighted 10/20/30/40%, against other teams, with a position limit instead of a bankroll and no ruin. Maximising expected log growth is not maximising rank, so `f*` itself has no meaning here.
- **What carries:** the edge-over-variance scaling, so a product with a thin edge and a volatile price gets less of its limit; the asymmetry, so when unsure, size down; and the warning that backtest edges overstate live ones ([validation](validation-and-overfitting.md)).
- **The position limit is the bankroll cap.** Using the full limit is the right size only when the edge per unit of risk is large. The template's `make_size` and `skew` are the knobs (`bots/template.py:41-44`).
- **Rank changes the appetite.** Behind, more variance can raise the chance of a top place; ahead, it only adds the risk of losing it. That is the rest of this page, and no part of Kelly.

## Where they disagree
No team argues for more variance after taking a lead. How much of the position limit to use, Kelly against full-room market making: [contradictions](../contradictions.md), row 14.

## What it means for our code
Nothing yet. The decision is a policy (flatten, or stop) rather than a strategy; the template has no end-of-round flatten parameter (a deferred item in `TODO.md`).

For sizing, nothing is built either. If a round has a directional signal (a predicted move per tick), size its target position as predicted move over the variance of the per-tick price change, then take a fraction of that, capped by the limit. For market making, compare products by PnL per unit of inventory risk before giving each the full limit. *(Inferred from [Kelly](../sources/kelly-criterion.md).)*

## How to test it here
Once the Technical Rules give the scoring formula, compute what rank or PnL secures each outcome and decide in advance, in writing, when to stop. Log per-product PnL from the first run.

For sizing: grid `make_size` (or a soft limit) per product next to the edge parameters, and compare PnL against its spread across days. Kelly predicts a flat top: a size well below the full limit should lose little PnL while cutting its variance.

## Sources
[Linear Utility](../sources/prosperity2-linear-utility.md), [UChicago](../sources/uchicago-trading-2026.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [Qminers 2025](../sources/qminers-hackathon-2025.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [Thorp on Kelly](../sources/kelly-criterion.md).
