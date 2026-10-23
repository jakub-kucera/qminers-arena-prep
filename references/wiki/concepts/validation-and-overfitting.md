---
title: Validation and avoiding over-fitting
type: concept
updated: 2026-10-19
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
- **The deflated Sharpe ratio** tests the chosen configuration against `SR₀`, the expected best of N̂ independent trials. N̂ comes from M correlated ones as `ρ̂ + (1 − ρ̂)M` (`literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:109-117` (p. 8–9, checked), `literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:213` (p. 14)).
- **Hold-out alone doesn't protect:** repeated 20 times at 95%, a false positive is expected (`literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:77` (p. 6)). That is the theory behind "don't open the unseen day early".
- **Stopping rule** (secretary problem): explore a random 37% of the planned candidates, then stop at the first that beats them all (`literature_md/deflated-sharpe-ratio/deflated-sharpe-ratio.md:141-145` (p. 10–11)). This is a pre-committed plan for capped portal submissions.

- **Testing the best cell against a benchmark, with the joint distribution of all cells** (second pass, 2026-10-19; source pages [SPA](../sources/superior-predictive-ability.md), [StepM](../sources/stepwise-multiple-testing.md)):
  - **White's Reality Check:** a bootstrap of the best of m cells against the benchmark, assuming every cell is exactly as good as the benchmark.
  - **Hansen's SPA test** fixes its weak spot: poor alternatives raise the Reality Check's critical value, so adding junk cells can drive its power to zero (`literature_md/superior-predictive-ability/superior-predictive-ability.md:169` (p. 5)). SPA studentizes each cell and recentres the bootstrap only on cells that aren't clearly worse, `µ̂^c_k = d̄_k·1{√n·d̄_k/ω̂_k ≤ −√(2 log log n)}` (`literature_md/superior-predictive-ability/superior-predictive-ability.md:98-103` (p. 4, checked)). On the paper's own data the two disagree outright: SPA^c 10%, the Reality Check about 96% (`literature_md/superior-predictive-ability/superior-predictive-ability.md:550` (p. 14)).
  - **Romano and Wolf's StepM** steps down from the best cell to name *every* cell that beats the benchmark, with the familywise error held at α (`literature_md/stepwise-multiple-testing/stepwise-multiple-testing.md:274-282` (p. 14, checked)). On autocorrelated data only the studentized version holds its error rate (`literature_md/stepwise-multiple-testing/stepwise-multiple-testing.md:414` (p. 21)).
- **Haircuts and false discovery rates** ([Harvey & Liu](../sources/backtesting-haircut.md)):
  - **The haircut:** convert the Sharpe ratio to a p-value, adjust it for N tests (`p^M = 1 − (1 − p^S)^N` when independent), and convert back (`literature_md/backtesting-haircut/backtesting-haircut.md:73-81` (p. 3, checked)). The cut is nonlinear: marginal strategies lose most.
  - **FDR over FWER:** BHY's false discovery rate is preferred to Bonferroni or Holm when a few false discoveries are acceptable (`literature_md/backtesting-haircut/backtesting-haircut.md:221` (p. 9)).
  - **Out-of-sample tests aren't out of sample** once a strategy is revised after failing, and a split trades in-sample power against out-of-sample power (`literature_md/backtesting-haircut/backtesting-haircut.md:160-174` (p. 6–7)).
- **Reusing a holdout adaptively** ([Dwork et al.](../sources/reusable-holdout.md)): an analyst who keeps checking ideas against the same holdout overfits it. On pure noise their holdout reports 63% accuracy where fresh data gives 50% (`literature_md/reusable-holdout/reusable-holdout.md:570` (p. 21)). Thresholdout answers from the training set unless the holdout disagrees beyond a noisy threshold, and spends a budget each time it does (`literature_md/reusable-holdout/reusable-holdout.md:408-428` (p. 15–16, checked)).
- **Tune on a fitted process, not on the path** ([Carr & López de Prado](../sources/optimal-trading-rules.md)): fit an O-U process, simulate 100,000 paths, and choose the exit thresholds on those (`literature_md/optimal-trading-rules/optimal-trading-rules.md:91-112` (p. 6–7, checked)). For a market maker's mean-reverting inventory the best rule is a small profit-take with a stop several times wider (`literature_md/optimal-trading-rules/optimal-trading-rules.md:132` (p. 8)). On a random walk no rule is best, and any rule a backtest picks is noise (`literature_md/optimal-trading-rules/optimal-trading-rules.md:148` (p. 9)).

## Where they disagree
Theory against practice: whether a held-out day still protects when it is reused across many variants ([contradictions](../contradictions.md), row 15).

Theory against theory, on our data: the DSR and the bootstrap tests disagree on whether the best cell of a wide grid beats the bot as is ([contradictions](../contradictions.md), row 18).

None on the principle. On the cost of caution: Baguette Fromage notes they shipped parts they suspected were over-fit "because at some point you have to stop researching" (`prosperity4-baguette-fromage/README.md:1099`).

## What it means for our code
`python/arena/grid.py` ranks by PnL, minimum day, neighbourhood mean and extra modes, and flags disagreement. Since 2026-10-13 it also holds out each day in turn: the best combination on the other days is scored on the day left out, which measures the selection bias directly (−14% for Velvetfruit with its vouchers on P4 rounds 3–4, none for Kelp on P3 round 1), and it flags days whose data repeats. This is CSCV's simplest relative: one split per day rather than every halving of the blocks, and no probability of overfitting (`TODO_DONE.md`: "Make `arena.grid` say how many combinations it tried"). The Arena's submission cap and private re-evaluation (`ON_THE_DAY.md`) mean every look at the public backtest is one more trial.

**Is a CSCV-style PBO worth building? Yes** (decided 2026-10-12 from the papers; built 2026-10-18, below):
- **The grid already produces CSCV's input.** It needs only every cell's PnL per block, the difference of `pnl` at block boundaries in each run's timeline. CSCV is then a few dozen lines of standard library.
- **Blocks:** contiguous ticks within a day, never straddling days. For example, 4–8 blocks per day over 3 days gives S = 12–24; at S = 24, sample the 2.7M halvings rather than enumerating them.
- **Report:**
  - N (cells × modes) and the number of blocks;
  - PBO;
  - the in-sample-vs-out-of-sample slope;
  - the out-of-sample probability of loss;
  - the deflated Sharpe ratio of the top cell, with `N̂` from the cells' average correlation.
- **Its blind spot:** halvings mix blocks of the same days, so a day-level regime change is invisible to it. Keep the leave-one-day-out and worst-day checks next to it.

**Built (2026-10-18), `python/arena/grid.py`, "overfitting":** every grid summary prints the trials (cells × modes), PBO by CSCV over about 16 blocks within days (identical cells counted once, halvings sampled to 4,000), the pick's mean out-of-sample rank and loss rate, and the DSR of the best cell's **gain over the bot as is**, block by block, with `N̂` from the gains' average correlation. Two departures from the papers *(our choices)*:
- **DSR on the gain, not the PnL.** On a cell's own PnL the DSR only says the bot makes money (a per-block Sharpe of 12–17 on every grid tried); the gain over the baseline is the selection question.
- **No degradation slope.** With PnL summed over blocks, a pick that stays the same cell has out-of-sample = total − in-sample, a slope of −1 by construction. The pick's mean relative rank out of sample replaces it.

**Measured 2026-10-19: the DSR is too strict on wide grids, and SPA and StepM should sit next to it** (`uv run python -m experiments.snooping_tests`, gains per block of 100 ticks; `IDEAS.md`, "Bootstrap tests of the best cell"):
- **Kelp `make_edge` 0–7 × `take_edge` 0–7, P3 round 1, 12 distinct cells:**
  - **The DSR fails it:** 0.76 over every cell, as `arena.grid` prints, below the 0.95 bar.
  - **SPA and StepM accept it:** SPA^c's p-value is 0.00 with mean bootstrap blocks of 5, 10 or 25 (500–2,500 ticks). StepM names exactly the three cells with `make_edge` 1 as beating the committed 0.5.
  - **The poor cells are why:** the DSR over the 9 best cells is 1.00. Its threshold `SR₀` comes from the variance of the cells' Sharpe ratios, and the poor corners of the grid inflate that variance. This is the Reality Check's weakness, which Hansen's recentring removes.
  - **Held out, SPA was right:** on the four P3 days whose Kelp data isn't round 1's, `make_edge` 1 gains 2.2–2.8k on every day under `all` (contradictions, row 18).
  - **But the gain is a fill-model artefact:** under `worse` it loses 1.2–2.1k on each of those days, and on round 1 too. A significant gain under one matching mode is still only as good as that mode. `arena.grid`'s extra `--modes` column is the check for that, and Kelp stays at 0.5.
- **Osmium `smoothing`, P4 rounds 1–2:** every test agrees nothing beats the committed 0.9 (DSR 0.13, SPA^c p 0.87–0.93, StepM none).
- **Null controls:** 5 grids of 32 cells, each cell the same bot under a different liquidity seed (fill ratio 0.8). SPA^c p-values were 0.20–0.88 and StepM rejected nothing, so neither test produced a false positive. The DSR stayed below 0.95 (0.18–0.65); over the top 9 it reached 0.94, which is why that subset is only an illustration.
- **Built into `arena.grid`, 2026-10-19:**
  - **What every grid summary now prints:** SPA's p-value that no cell beats the bot as is, and StepM's cells that do. Each StepM cell is checked under the other `--modes`, then the summary gives a pick: StepM's best cell that beats the bot as is under every mode, else the bot as is (`python/arena/grid.py:963`, `format_snooping`).
  - **What it costs:** about 0.4 s even at 64 cells × 600 blocks.
  - **The DSR, PBO and the held-out days stay.** Every one of these tests shares a blind spot: blocks within days can't see a change between days.
- **Ten selection rules on unseen days** (`uv run python -m experiments.selection_rules`; `IDEAS.md`, "Selection rules on unseen days"):
  - **The setup:** six two-parameter grids (Kelp, Resin, Osmium, Pepper Root), each trained on one round and scored on that product's later days that repeat no training day, plus each reversed (trained on the later days, tested on the first round).
  - **From the committed settings,** which were partly tuned on these days: every rule that picks by `all` PnL loses money under `worse` in total (best PnL +12.2k / −19.8k; plateau `nbhd` +16.2k / −26.2k; top-5 average +16.2k / −28.9k; SPA alone +13.3k / −18.0k). Most of it is Kelp's `make_edge` 1.5. SPA + `worse` and the DSR gate never move off the bot as is: 0 / 0.
  - **From the template's DEFAULTS** for the two parameters (a product first seen on the day): SPA + `worse` makes +310.8k / +294.7k, with no study negative under either mode. The best of any rule is +316.2k under `all` and +303.4k under `worse`. The DSR gate makes +207.1k: it misses Pepper Root reversed (+83.7k) and every Kelp gain.
  - **So the pick rule is SPA, then StepM, then every mode.** It was the only rule never to lose money, in either table or either mode. The plateau rules (`nbhd`, top-5 average) did no better than the single best PnL here.
  - **On fresh simulated days** (`uv run python -m experiments.selection_rules_sim`: Kelp, Resin and Hydrogel presets, each grid tuned on 3 days ten times and scored on 20 other days, per test day `all` / `worse`):
    - **From the committed settings:** the pick made +507 / +363 and never lost. Every rule that picks by `all` PnL lost under `worse` on Kelp in all 10 repetitions. On Hydrogel, choosing the level settings from 3 days lost in 6 of 10, and SPA refused to move.
    - **From DEFAULTS:** the pick made +33.9k / +33.0k and lost twice, on Kelp under `worse`. The top-5 average made +38.0k / +33.8k without a loss there, but lost all 10 Kelp repetitions under `worse` from the committed settings. The DSR gate never lost but made +3.3k, missing Hydrogel's +30.7k.
    - **So it is not "never loses" but "loses least often among the rules that gain":** 2 of 120 (repetition, mode) runs, against 10–22 for the rules that gained as much or more.
- **Across fill-model scenarios** (2026-10-23, `uv run python -m experiments.selection_rules --part 2` and `selection_rules_sim --part 2`; repo `IDEAS.md`, "Choosing a cell by its worst case over fill-model scenarios"): Kelp's and Resin's grids under ten scenarios (three trade matchings, three queue models, two fill ratios, a copy, an undercutter), five rules.
  - **Max-min of the PnL lost most often:** 25 of 40 study-scenarios on held-out days and 92 of 200 on simulated ones, from the committed settings. It picks the cell that does best in the harshest scenario (on Kelp, `none`, where only takes fill) and loses in the others.
  - **The grid's pick, checked under every scenario, lost least:** never from the committed settings (it keeps them), and once in 40 and twice in 200 from DEFAULTS, where it made +7.3k and +349 a test day. Max-min of the *gain* over the bot as is picked the same cells. The lower quartile gained more and lost in 6 and 8.
  - **So `arena.grid --scenario` keeps the pick as the rule,** and its `worst` column is for reading only.
- **Leakage between neighbouring blocks** (the reason for López de Prado's purging and embargo): on ten null grids, CSCV's PBO over the grid's 16 blocks averaged 46.5% (11–86%), close to the 50% of no information. Neighbouring blocks don't leak enough to bias it at that block size *(checked, `python/experiments/snooping_tests.py`)*.
- **Harvey & Liu's BHY** (false discovery rate at 5%) named the same number of cells as StepM on every grid: 3 on Kelp, 0 on Osmium and the nulls.
- **A permutation test of the whole search** (`arena.grid --permute N`, after Masters' idea: rerun the whole optimisation on data with its order destroyed; our adaptation, his book unread, `MANUAL_TODO.md` G):
  - **The copies** (`python/arena/stress.py`, `permute`): the days' own ticks in a shuffled order, in runs of `--permute-block`. Each tick is shifted so its wall bid continues by its own real move. Each tick's book, its trades and the products' ticks together are kept; any structure longer than a run is gone.
  - **Two statistics, on the products the axes set:** the best cell's PnL (does the strategy family need the real order?) and its lift over the median cell (does the *choice* need it?). Neither is measured against the bot as is: its settings were tuned to the real order, so on the copies almost any cell beat it, and that first version said nothing.
  - **Measured 2026-10-19** (19 copies, `IDEAS.md`, "A permutation test of the whole search"): Hydrogel's level grid is the positive control. Its lift is 97.6k against the copies' 36.8k (p 0.05 for runs of 1 and of 100 ticks). Resin and Pepper Root need the order for their best PnL (p 0.05) but not for the choice (lift p 0.90, 0.95). Kelp's edge grid needs it for neither (best p 0.55, lift p 0.80): its gain comes from the books and the fill model, the same conclusion `worse` and the held-out days reached.
  - **What it adds to SPA and StepM:** they say a cell beats the bot as is on these days. The permutation test says whether that comes from how the price moves (which can change on the scored day) or from what each tick looks like (which the fill model decides).
- **Screening a big grid** (`arena.grid --screen SHARE`, successive halving with one rung, 2026-10-20): every cell on the first day, then the best share everywhere. The screen is a selection on that day, so the tests on the kept cells over all days understate the bias of the cells tried. The grid repeats SPA, StepM and the pick on the days the screen didn't see, the screen-then-test split that keeps them clean *(our design, not from a source)*. On Kelp's 256 cells it kept the same best cell and pick at 25% and 10%, in 20 s and 14 s against 48 s.

## How to test it here
Done 2026-10-18 (`python/tests/test_grid.py`, and the grids below, each `--modes all,worse`):
- **The detector:** on noise (20 cells × 12 blocks, 10 seeds) PBO averages near 50%; one cell with an edge brings it under 10%. The DSR reproduces the paper's worked example (0.9004; 0.9505 at N = 46).
- **Real grids:** Kelp `make_edge 0..3` × `skew 0,5,10` (P3 round 1): PBO 0%, DSR 1.00 against the committed `make_edge` 0.5 under `all`. Resin's: PBO 0%, the bot as is is best. Osmium's (P4 rounds 1–2): PBO 0%, DSR 0.00, a gain over the committed setting of nothing real. Hydrogel's 48-cell level grid (P4 rounds 3–4): PBO 30%. Osmium `smoothing 0.5–0.95`: PBO 43%, which value wins is noise, while the gain of any of them over none has DSR 0.98. The memory argument's prediction (a worse PBO on the pegged Resin than on Kelp) isn't visible: both are 0%.

Before:
1. **Check the detector before trusting it:** add a parameter with no effect (or shuffle the products' days) to a grid, and confirm that PBO comes out near 50% and the deflated Sharpe ratio is low.
2. **Then run it on real grids:** `make_edge` × `skew` on P3 and P4 round 1. Compare PBO across a pegged product (Resin) and a drifting one (Kelp); the memory argument predicts a worse slope on the pegged one.
3. **Record N** (cells × modes, including earlier grids on the same days) next to every grid result reported in `TODO.md` or a wiki page.

## Sources
[pseudo-math](../sources/pseudo-math.md), [PBO](../sources/probability-of-backtest-overfitting.md), [deflated Sharpe ratio](../sources/deflated-sharpe-ratio.md), [SPA](../sources/superior-predictive-ability.md), [StepM](../sources/stepwise-multiple-testing.md), [Harvey & Liu](../sources/backtesting-haircut.md), [reusable holdout](../sources/reusable-holdout.md), [optimal trading rules](../sources/optimal-trading-rules.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [Qminers 2025](../sources/qminers-hackathon-2025.md) (hidden seasons). [Kayzerjali](../sources/prosperity4-kayzerjali.md), [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [CMU Physics](../sources/prosperity3-cmu-physics.md).
