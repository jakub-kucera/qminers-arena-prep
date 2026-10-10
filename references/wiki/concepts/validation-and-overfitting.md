---
title: Validation and avoiding over-fitting
type: concept
updated: 2026-10-10
---

# Validation and avoiding over-fitting

## Summary
Every team that did well on the final rounds describes the same discipline: treat the backtester as a filter, require a change to survive more than the average day, and be suspicious of anything that looks too good. The Arena adds two features that make this sharper: a capped number of submissions and, probably, a private rerun on hidden data.

## What the sources say
- **Backtester as filter** (Baguette Fromage): no market impact, simplified book, imperfect bot replication; discard what fails locally, question what passes (`prosperity4-baguette-fromage/README.md:232-253`). Frankfurt: use the website for bot-interaction questions, the open backtester for taking and simple quoting, and never optimise the website score (`prosperity3-frankfurt-hedgehogs/README.md:889-908`).
- **Worst-day rule** (DTU): a variant ships only if its worst single backtest day is positive; they say it killed ~80% of ideas and kept the final trader from blowing up (`prosperity4-dtu-quant-lab/README.md:260`, `prosperity4-dtu-quant-lab/README.md:334`). Our `arena.grid` ranks by it.
- **Leave-one-day-out** (Ryan Challman): fit on the rest, test on the held-out day (`prosperity4-ryan-challman/README.md:75`). The named-trader bias did not generalise (`prosperity4-ryan-challman/README.md:89-91`).
- **Fit on two days, test on the third** (Baguette Fromage): relationships "that looked statistically convincing immediately collapsed" (`prosperity4-baguette-fromage/README.md:885-901`).
- **Multiple testing** (Alpha Search): a basket accepted when any one of three folds has p < 0.05 gives ~14% false positives; Bonferroni over the true search space would need p ~ 1e-6 (`prosperity4-alpha-search/README.md:124-141`). Check each finding with a second implementation (`prosperity4-alpha-search/README.md:162`).
- **Don't open the unseen day early; re-sweep after each baseline change** (Ryan Challman): once you've looked, every later choice is tuned to it; a take threshold locked under one baseline lost five figures under another (`prosperity4-ryan-challman/README.md:27`, `prosperity4-ryan-challman/README.md:280`).
- **Sharp optima** (Ryan Challman): single-tick tightenings lost $3k–$34k each (`prosperity4-ryan-challman/README.md:270`).
- **Live was worse than the backtest** (Linear Utility round 3: 111k live, teams ahead had over-fitted more: `prosperity2-linear-utility/README.md:156`); the handed-out days may not look like the scored day (DTU Hydrogel: `prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:261-296`).
- **Size a tempting one-day signal for the average day** (Ryan Challman `ROBOT_DISHES`: `prosperity4-ryan-challman/README.md:133-137`).

## Where they disagree
None on the principle. On the cost of caution: Baguette Fromage notes they shipped parts they suspected were over-fit "because at some point you have to stop researching" (`prosperity4-baguette-fromage/README.md:1099`).

## What it means for our code
`arena/grid.py` ranks by PnL, minimum day, neighbourhood mean and extra modes, and flags disagreement. It does not know how many combinations it tried (`TODO.md`: "Make `arena.grid` say how many combinations it tried"). The Arena's submission cap and private re-evaluation (`ON_THE_DAY.md`) mean every look at the public backtest is one more trial.

## How to test it here
Add the trial count and a warning to `arena.grid`. Theory is in `literature_md/pseudo-math/` (Theorem 3.1: `MinBTL < 2 ln N / E[max_N]²`, stated for annualised Sharpe on independent trials, transfer to a few days of tick data unproven), `literature_md/probability-of-backtest-overfitting/` and `literature_md/deflated-sharpe-ratio/`.

## Sources
[Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [Qminers 2025](../sources/qminers-hackathon-2025.md) (hidden seasons).
