---
title: Harvey & Liu, "Backtesting" (2015)
type: source
repo: literature_md/backtesting-haircut
status: read
updated: 2026-10-19
---

# Harvey & Liu, "Backtesting" (Journal of Portfolio Management, Fall 2015)

## What it is
A 17-page practitioner paper. It replaces the industry's flat 50% "haircut" on backtested Sharpe ratios with one derived from multiple testing: turn the Sharpe ratio into a t-ratio, adjust its p-value for the number of strategies tried, and turn the adjusted p-value back into a Sharpe ratio (`backtesting-haircut.md:15-27` (p. 1)). It also contrasts its approach with López de Prado's PBO and with out-of-sample testing.

## Main results
- **Independent tests** (eq. 3–5, `backtesting-haircut.md:73-81` (p. 3, checked)):
  - **Single test:** `p^S = Pr(|r| > SR·√T)`, with `r` a t-distribution with T − 1 degrees of freedom.
  - **The best of N independent strategies:** `p^M = 1 − (1 − p^S)^N`.
  - **The haircut Sharpe ratio:** `HSR` solves `p^M = Pr(|r| > HSR·√T)`.
  - **Worked example:** T = 240 months, annual SR 0.75, gives `p^S` = 0.0008. With N = 200 that becomes `p^M` = 0.15 and HSR 0.32, a haircut of about 60%. Recomputed with a normal in place of the t: 0.00080, 0.147, 0.324 and 57% *(checked)*.
- **The haircut is nonlinear** (`backtesting-haircut.md:27` (p. 1)): high Sharpe ratios lose little, marginal ones lose most, so a flat 50% is too harsh on the best and too lenient on the marginal.
- **Three adjustments** (p. 4–5, checked against the PDF, and the paper's six-p-value example recomputed):
  - **Bonferroni:** `min[M·p_(i), 1]`.
  - **Holm:** `min[max_{j≤i} (M − j + 1)·p_(j), 1]` (`backtesting-haircut.md:120` (p. 4, checked)).
  - **BHY:** going down from the largest p-value, `p_(i)^BHY = min[p_(i+1)^BHY, M·c(M)/i·p_(i)]` with `c(M) = Σ_{j=1}^M 1/j` (`backtesting-haircut.md:136-138` (p. 5, checked)).
  - Bonferroni and Holm control the FWER; BHY controls the false discovery rate under any dependence. On the example's six p-values (0.005 … 0.06) they find 1, 2 and 4 discoveries at 5% (`backtesting-haircut.md:142` (p. 5)).
  - The authors advocate BHY for finance (`backtesting-haircut.md:221` (p. 9)).
- **Correlation and unseen trials** (`backtesting-haircut.md:148` (p. 5)): correlated strategies are fewer independent tests, and the tests never reported still count. The paper handles both with HLZ's structural model of 316+ published factors, which is about equity factors, not our grids.
- **Against PBO** (`backtesting-haircut.md:152-158` (p. 6)): PBO asks whether a *selection process* overfits, using every strategy's series; the haircut asks which *individual* strategies are real, from test statistics alone. When every strategy is true, the haircut may still call the weakest significant, where PBO would rarely favour it.
- **Against out-of-sample tests** (`backtesting-haircut.md:160-174` (p. 6–7)):
  - **Not truly out of sample:** an OOS test isn't OOS once the researcher revises a strategy after seeing it fail, or knows what happened in the period.
  - **The split trades power:** with a 50-50 split the in-sample half misses true strategies; with 90-10 the OOS part is too short to separate good from bad.
  - **Their tentative combination:** a lenient in-sample cut (p = 0.2), then the OOS test, intersected with a multiple test on the full data.

## Assumptions against the Arena
- **A Sharpe ratio over a long sample, with a t-distribution.** Our grid cells' per-block gains are short (16–300 blocks) and autocorrelated within a day; the t-ratio's standard error needs a correction (as Hansen's `ω̂` does) *(inferred)*.
- **Independent tests in the simple version.** Grid cells are strongly correlated (neighbouring settings trade alike), so `p^M = 1 − (1 − p^S)^N` with N = cells overstates the penalty. Their full method needs a model of the correlation that we don't have; a bootstrap over the cells' joint series ([SPA](superior-predictive-ability.md), [StepM](stepwise-multiple-testing.md)) gets it from the data.
- **The count of tests.** The one input that matters most, and the one nobody records. For us: every cell of every grid run on the same days, including the ones before the one reported.
- **The OOS critique fits three days well.** Every variant judged on a held-out day spends that day (contradictions, row 15); with 3 days, splits are too short to tell close variants apart *(inferred)*.

## In our notation
| Paper | Ours |
|---|---|
| strategy, N tested | a grid cell, every cell tried on the same days (`arena.grid` prints "trials") |
| `SR`, `T` | per-block mean over std of the cell's gain, the number of blocks |
| `p^S`, `p^M` | single and multiple-test p-values of the best cell |
| BHY | an option for "which cells are real" when false discoveries are acceptable |

## Traps
- **OCR:** in Holm's formula the subscript `j ≤ i` sits under the `min` in the markdown, where the PDF has it under the `max` (`backtesting-haircut.md:120` (p. 4)).
- **OCR:** the inline worked numbers of the Holm and BHY examples are scrambled (`backtesting-haircut.md:122-142` (p. 4–5)); read them from the PDF.
- **The 316 factors and the HLZ model** are calibrated on academic equity factors; don't carry the haircut tables (Exhibits 2–4) over to a grid.

## Read depth
- **Read:** the whole text through the IS/OOS section and the conclusion of the applications.
- **Checked against the PDF (page images):** eq. 3–5 and the worked example (p. 3, recomputed); the Bonferroni, Holm and BHY formulas and their six-p-value example (p. 4–5, recomputed).
- **Not read:** the appendix on the HLZ model; Exhibits 1–5 as tables.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
