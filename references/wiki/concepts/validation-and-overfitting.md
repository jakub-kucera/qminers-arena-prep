---
title: Validation and avoiding over-fitting
type: concept
updated: 2026-10-12
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

- **The oracle can disagree with the backtester** (Kayzerjali): one product showed backtest +2,415 against live +436 on the same window, so their loop uses the live result as the objective and the backtester only as a bug check (`online-snapshots/Kayzerjali_Prosperity2026/run_cycle.md:4-5`); one change per cycle and a written stopping rule after five consecutive live failures (`online-snapshots/Kayzerjali_Prosperity2026/run_cycle.md:24-28`). Four logged cycles are no evidence that the loop works.
- **Recheck cross-round assumptions and don't mistake consensus for truth** (Leo-Hawking): "what environment parameters does this belief depend on, and do they still hold this round?"; a human and an AI agreeing can entrench an error (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:581-609`).
- **Sample or practice data can be part of the scored data** (CMU Physics): the website's sample was the first 1,000 timestamps of live day 1 (`online-snapshots/chrispyroberts_imc-prosperity-3.README.md:70`); and a model that fit well in sample (a quadratic IV fit) broke on the submission day (`online-snapshots/chrispyroberts_imc-prosperity-3.README.md:236`).

**What the theory says** (Bailey, Borwein, López de Prado and others; source pages [pseudo-math](../sources/pseudo-math.md), [PBO](../sources/probability-of-backtest-overfitting.md), [deflated Sharpe ratio](../sources/deflated-sharpe-ratio.md)):
- **The best of N skill-less trials looks good by construction.**
  - Its expected Sharpe ratio is `E[max_N] ≈ (1 − γ)Z⁻¹[1 − 1/N] + γZ⁻¹[1 − 1/(Ne)]` standard errors, below `√(2 ln N)` (`literature_md/pseudo-math/pseudo-math.md:119-123` (p. 9, checked)).
  - Measured per period over D periods, the best of N = 100 null cells shows a per-period Sharpe of 2.53/√D: 1.46 over 3 days, 0.46 over 30 blocks *(computed here)*.
  - Hence MinBTL `< 2 ln N / E[max_N]²` (`literature_md/pseudo-math/pseudo-math.md:145` (p. 11, checked)).
- **With memory it is worse than luck.** When performance mean-reverts or is serially correlated, the in-sample winner is expected to *under*perform out of sample (`literature_md/pseudo-math/pseudo-math.md:227-263` (p. 19–21)). Our pegged and mean-reverting products are that case *(inferred)*.
- **PBO via CSCV:**
  - Split per-period PnL into S blocks. For each of the `C(S, S/2)` halvings, pick the in-sample best and record its out-of-sample rank.
  - PBO is the share of halvings where it lands at or below the median (`literature_md/probability-of-backtest-overfitting/probability-of-backtest-overfitting.md:117-150` (p. 11–12, checked)).
  - It needs N well above 10. Report every trial, and never optimise on PBO itself.
- **The deflated Sharpe ratio** tests the chosen configuration against `SR₀`, the expected best of N̂ independent trials. N̂ comes from M correlated ones as `ρ̂ + (1 − ρ̂)M` (`literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:109-117` (p. 8–9, checked), `literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:213` (p. 15)).
- **Hold-out alone doesn't protect:** repeated 20 times at 95%, a false positive is expected (`literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:77` (p. 6)). That is the theory behind "don't open the unseen day early".
- **Stopping rule** (secretary problem): explore a random 37% of the planned candidates, then stop at the first that beats them all (`literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:141-145` (p. 10–11)). This is a pre-committed plan for capped portal submissions.

## Where they disagree
None on the principle. On the cost of caution: Baguette Fromage notes they shipped parts they suspected were over-fit "because at some point you have to stop researching" (`prosperity4-baguette-fromage/README.md:1099`).

## What it means for our code
`arena/grid.py` ranks by PnL, minimum day, neighbourhood mean and extra modes, and flags disagreement. It does not know how many combinations it tried (`TODO.md`: "Make `arena.grid` say how many combinations it tried"). The Arena's submission cap and private re-evaluation (`ON_THE_DAY.md`) mean every look at the public backtest is one more trial.

**Is a CSCV-style PBO worth building? Yes** (decided 2026-10-12 from the papers; not yet built):
- **The grid already produces CSCV's input.** It needs only every cell's PnL per block, the difference of `pnl` at block boundaries in each run's timeline. CSCV is then a few dozen lines of standard library.
- **Blocks:** contiguous ticks within a day, never straddling days. For example, 4–8 blocks per day over 3 days gives S = 12–24; at S = 24, sample the 2.7M halvings rather than enumerating them.
- **Report:**
  - N (cells × modes) and the number of blocks;
  - PBO;
  - the in-sample-vs-out-of-sample slope;
  - the out-of-sample probability of loss;
  - the deflated Sharpe ratio of the top cell, with `N̂` from the cells' average correlation.
- **Its blind spot:** halvings mix blocks of the same days, so a day-level regime change is invisible to it. Keep the leave-one-day-out and worst-day checks next to it.

## How to test it here
1. **Check the detector before trusting it:** add a parameter with no effect (or shuffle the products' days) to a grid, and confirm that PBO comes out near 50% and the deflated Sharpe ratio is low.
2. **Then run it on real grids:** `make_edge` × `skew` on P3 and P4 round 1. Compare PBO across a pegged product (Resin) and a drifting one (Kelp); the memory argument predicts a worse slope on the pegged one.
3. **Record N** (cells × modes, including earlier grids on the same days) next to every grid result reported in `TODO.md` or a wiki page.

## Sources
[pseudo-math](../sources/pseudo-math.md), [PBO](../sources/probability-of-backtest-overfitting.md), [deflated Sharpe ratio](../sources/deflated-sharpe-ratio.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [Qminers 2025](../sources/qminers-hackathon-2025.md) (hidden seasons). [Kayzerjali](../sources/prosperity4-kayzerjali.md), [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [CMU Physics](../sources/prosperity3-cmu-physics.md).
