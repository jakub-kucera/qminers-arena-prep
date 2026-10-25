---
title: Bailey, Borwein, López de Prado & Zhu, "The probability of backtest overfitting" (2017)
type: source
repo: literature_md/probability-of-backtest-overfitting
status: read
updated: 2026-10-12
---

# Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" (Journal of Computational Finance, 2017)

## What it is
A 34-page paper that defines the **probability of backtest overfitting (PBO)**: the chance that the configuration chosen as best in sample ranks below the median out of sample. It estimates PBO with **CSCV** (combinatorially symmetric cross-validation), which needs only the per-period PnL of every configuration tried. It is model-free and non-parametric, and the direct answer to `TODO_DONE.md`'s question of whether a PBO estimate for `arena.grid` is worth building.

## Main results
- **Definitions** (`probability-of-backtest-overfitting.md:101-107` (p. 9–10, checked)):
  - A selection process *overfits* if the in-sample best has an expected out-of-sample rank below the median.
  - `PBO = Σₙ Prob[r̄ₙ < N/2 | n is best IS]·Prob[n is best IS]`. "Overfitting" here is about **selecting** among N configurations, not about fitting one model.
- **CSCV** (Algorithm 2.3, `probability-of-backtest-overfitting.md:117-150` (p. 11–12, checked)):
  1. Build `M`, a `T × N` matrix: per-period PnL of each of the N configurations, synchronous rows.
  2. Split the rows into an even number `S` of contiguous blocks.
  3. For each of the `C(S, S/2)` ways to pick half the blocks: the picked half is in-sample, the rest out-of-sample, both kept in time order.
  4. Find the in-sample best `n*` and its out-of-sample relative rank `ω̄ = r̄_{n*}/(N + 1)`, then the logit `λ = ln(ω̄/(1 − ω̄))`.
  5. **`PBO` is the share of combinations with `λ ≤ 0`**, i.e. the in-sample best landed at or below the out-of-sample median.
- **Three more diagnostics** (`probability-of-backtest-overfitting.md:171-178` (p. 13–14)):
  - *Performance degradation:* regress out-of-sample on in-sample performance of the chosen configuration. The slope is usually negative, through the compensation effects of [pseudo-math](pseudo-math.md).
  - *Probability of loss:* the share of combinations in which the chosen configuration loses out of sample.
  - *Stochastic dominance:* does picking the in-sample best beat picking at random?
- **Choosing S and N** (`probability-of-backtest-overfitting.md:256-262` (p. 21–22)):
  - S = 16 gives C(16, 8) = 12,870 logits and `σ[f(λ)] < 0.0045`; the authors call S = 16 "reasonable … in most cases". S must stay small enough to keep each block's time structure.
  - N must be well above 10, or the ranks are too coarse.
  - T should be **twice** the data used to make the choice, because each half is judged on T/2.
- **Misuse** (`probability-of-backtest-overfitting.md:278-290` (p. 24–25)):
  - Report every trial; hidden trials bias PBO down. For a guided search, use each search's end point.
  - PBO says nothing about a flawed backtest (wrong fills, look-ahead).
  - It cannot see a regime break outside the sample.
  - A high PBO can also mean many equally good configurations.
  - **Never use PBO as the objective of the search**, since that overfits PBO.
- **Example** (`probability-of-backtest-overfitting.md:298-316` (p. 25–27)): the 8,800-cell seasonal rule on a random walk (in-sample Sharpe 1.27) gets PBO 55%. With a real planted monthly effect, PBO is 13%.

## Assumptions against the Arena
- **Needs a per-period PnL for every configuration tried.** `arena.grid` already runs every cell × day × mode in parallel, but keeps totals and `min day`. Per-block PnL is the difference of the `pnl` column at block boundaries in each run's timeline (`python/arena/report.py:144`). CSCV itself is a few dozen lines of standard library *(inferred)*.
- **Few days.** Three Prosperity days cut into blocks of about 1,250 ticks give S = 24. That is enough combinations, but the blocks are not independent within a day, and a day-level effect (one trending day) moves several blocks together. Blocks should not straddle days. *(Inferred.)*
- **The test sees only the data it is given.** If the Arena's scored data is a different regime from the public data, PBO on the public data can be low and the choice still wrong (limitation 3).
- **The portal is a second, hidden selection loop.** Every public-backtest submission compared by its score is a trial that CSCV over our grid does not see.

## In our notation
| Paper | Ours |
|---|---|
| configuration / trial `n` | one `arena.grid` cell (parameter combination, with `--modes` as separate trials or as a robustness filter) |
| `M` (T × N) | per-block PnL: rows are blocks of ticks (within days), columns are cells |
| in-sample best | the grid's top cell by the chosen ranking (`pnl`, `min day` or `nbhd`) |
| PBO | not computed today; `TODO_DONE.md`, "Make `arena.grid` say how many combinations it tried" |

## Traps
- **Typo in the paper itself:** "if S = 16, we will form 12,780 combinations" (`probability-of-backtest-overfitting.md:132` (p. 11)); C(16, 8) = 12,870 *(computed)*. The PDF has 12,780 too *(checked)*. The other counts it gives (S = 12: 924; S = 24: 2,704,156) are right.
- **Typo in the paper itself:** step c) says the in-sample statistics come from "the nth column of J (the testing set)"; J is the training set (`probability-of-backtest-overfitting.md:140` (p. 12)).
- **OCR:** bars over `R̄`, `J̄` and `r̄` are lost throughout, so the markdown writes the in-sample and out-of-sample symbols identically. Read the definitions from the PDF.
- The rank convention is "higher is better": `r = (1, 3, 2)` for performances `(0.5, 1.1, 0.7)` (`probability-of-backtest-overfitting.md:97` (p. 9, unchecked)).

## Read depth
- **Read:** sections 1–7 (the introduction only skimmed).
- **Checked against the PDF (page images):** Definition 2.2, (2.3), the CSCV steps and the logit.
- **Not read:** the reference list.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
