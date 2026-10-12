---
title: Bailey & López de Prado, "The deflated Sharpe ratio" (2014)
type: source
repo: literature_md/deflated-sharpe-ratio
status: read
updated: 2026-10-12
---

# Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality" (Journal of Portfolio Management, 2014)

## What it is
A short, 22-page paper with one usable formula: the **deflated Sharpe ratio (DSR)**, the probability that the chosen strategy's true Sharpe ratio is above what the best of N skill-less trials would show. It needs the number of independent trials, the variance of their Sharpe ratios, the sample length, and the skew and kurtosis of the chosen strategy's returns. It is parametric where [PBO](probability-of-backtest-overfitting.md) is not, and cheap when the trials' full PnL series aren't kept. It also gives a rule for estimating the number of independent trials and a stopping rule for testing.

## Main results
- **Expected best of N trials** (eq. 1, `deflated-sharpe-ratio.md:91-95` (p. 7)): `E[max SR_n] ≈ E[SR_n] + √V[SR_n] · ((1 − γ)Z⁻¹[1 − 1/N] + γZ⁻¹[1 − 1/(Ne)])`. It is [pseudo-math](pseudo-math.md)'s Proposition 2.1, scaled to the trials' own mean and variance.
- **DSR** (eq. 2, `deflated-sharpe-ratio.md:109-117` (p. 8–9, checked)):
  - **`DSR = Z[ (SR − SR₀)·√(T − 1) / √(1 − γ̂₃·SR + ((γ̂₄ − 1)/4)·SR²) ]`**
  - **`SR₀ = √V[{SR_n}] · ((1 − γ)Z⁻¹[1 − 1/N] + γZ⁻¹[1 − 1/(Ne)])`**
  - `SR` is the chosen strategy's per-period (non-annualised) Sharpe ratio over `T` periods. `γ̂₃` and `γ̂₄` are its returns' skewness and kurtosis (not excess: a normal has 3). `V[{SR_n}]` is the variance of the Sharpe ratios across trials, and `N` the number of *independent* trials.
  - DSR is the probabilistic Sharpe ratio (PSR) with its threshold raised from 0 to `SR₀`.
- **Worked example** (`deflated-sharpe-ratio.md:123-133` (p. 9–10, checked)):
  - Annualised SR 2.5 over 5 years of daily data (T = 1,250), N = 100, `V = ½` annualised, `γ̂₃ = −3`, `γ̂₄ = 10`.
  - That gives `SR₀ ≈ 0.1132` per day and **DSR = 0.9004 < 0.95**, so rejected.
  - It would pass with N = 46 (0.9505), or with normal returns up to N = 88. All three are recomputed here *(checked)*.
- **Independent trials from correlated ones** (Appendix A.3, `deflated-sharpe-ratio.md:199-219` (p. 14–15)):
  - With M trials and average pairwise correlation `ρ̂`, use `N̂ = ρ̂ + (1 − ρ̂)·M` (eq. 9).
  - Caveat: when M exceeds the sample length T, the correlation matrix is ill-conditioned and the average correlation "may itself be overfit". Reduce the dimension first, or use information-theoretic redundancy.
- **Hold-out doesn't fix it** (`deflated-sharpe-ratio.md:77` (p. 6)): applying a hold-out test 20 times at 95% makes a false positive *expected*.
- **When to stop testing** (`deflated-sharpe-ratio.md:137-147` (p. 10–11)), the secretary problem: from the configurations you can justify in theory, try a random `1/e ≈ 37%`. Then keep testing one at a time and stop at the first that beats all before it.
- **Memory makes overfitting harmful, not just useless** (`deflated-sharpe-ratio.md:71` (p. 6)), as in [pseudo-math](pseudo-math.md).

## Assumptions against the Arena
- **Normal trials' Sharpe ratios and a long sample.** With 3 days, T must be blocks of ticks (for example 24), and `√(T − 1)` is small. Low T is the honest result: little data means little confidence. *(Inferred.)*
- **Needs only summary statistics of the trials,** not their series: the count, the variance of their Sharpe ratios, and the chosen one's series. `arena.grid` already has every cell's PnL per day and mode; per-block PnL would give the Sharpe ratios.
- **Grid cells are highly correlated,** so `N̂` from eq. (9) is much smaller than the cell count. With more cells than blocks, `ρ̂` is unreliable, which is the paper's own warning.
- **The secretary rule fits the portal:** with a cap on submissions, decide the candidate set in advance, spend about 37% exploring, then submit the first that beats everything before it. That is a pre-committed rule, not a reaction to each score *(inferred application)*.

## In our notation
| Paper | Ours |
|---|---|
| a trial, M trials | a grid cell, all cells tried (including earlier grids on the same data) |
| `N̂` | `ρ̂ + (1 − ρ̂)M`, with `ρ̂` the average correlation of cells' per-block PnL |
| `SR`, `T` | the chosen cell's per-block mean PnL over its std, number of blocks |
| `V[{SR_n}]` | variance of per-block Sharpe ratios across cells |
| `γ̂₃`, `γ̂₄` | skew and kurtosis of the chosen cell's per-block PnL |

## Traps
- **OCR lost nearly all inline math.** The definition of `SR₀`, the example's inputs (N = 100, V = ½, T = 1,250, γ̂₃ = −3, γ̂₄ = 10) and its computed values are blank in the markdown (`deflated-sharpe-ratio.md:113` (p. 8), `deflated-sharpe-ratio.md:125-127` (p. 9–10)). Exhibits are missing ("[EXHIBIT 2 HERE]"). This document must be read from the PDF.
- `γ̂₄` is kurtosis, not excess kurtosis: `(γ̂₄ − 1)/4` is ½ for normal returns.
- `V[{SR_n}]` and `SR` must be in the same units, both per period. The example converts an annualised variance of ½ into `1/(2·250)` per day.

## Read depth
- **Read:** the whole paper, including the appendices.
- **Checked against the PDF (page images):** eq. (2), `SR₀`, the worked example (and recomputed); eq. (9) via the markdown, which kept it.
- **Not read:** the exhibits (images only).

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
