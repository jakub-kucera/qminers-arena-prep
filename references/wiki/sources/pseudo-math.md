---
title: Bailey, Borwein, López de Prado & Zhu, "Pseudo-mathematics and financial charlatanism" (2014)
type: source
repo: literature_md/pseudo-math
status: read
updated: 2026-10-12
---

# Bailey, Borwein, López de Prado & Zhu, "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance" (Notices of the AMS, 2014)

## What it is
The readable, 34-page entry to the overfitting trilogy (with [PBO](probability-of-backtest-overfitting.md) and the [deflated Sharpe ratio](deflated-sharpe-ratio.md)). Its claims:
- Trying N configurations of a strategy with no edge yields an in-sample best whose Sharpe ratio grows like `√(2 ln N)`.
- So a backtest is meaningless unless the number of trials is reported.
- When performance has *memory* (mean reversion, serial correlation), the in-sample winner is expected to do *worse* than average out of sample.

## Main results
- **Sharpe ratio estimation error** (`pseudo-math.md:95-103` (p. 7–8, checked)): `SR = (μ/σ)√q` with q returns per year. Its estimate over `y` years is asymptotically `N(SR, (1 + SR²/(2q))/y)`. With `SR = 0` and `y = 1` it is a standard normal, whatever the sampling frequency.
- **Expected maximum of N null Sharpe ratios** (Proposition 2.1, `pseudo-math.md:119-123` (p. 9, checked)):
  - `E[max_N] ≈ (1 − γ)·Z⁻¹[1 − 1/N] + γ·Z⁻¹[1 − 1/(Ne)]`, with `γ ≈ 0.5772` (Euler–Mascheroni) and `Z⁻¹` the standard normal quantile.
  - The upper bound is `√(2 ln N)`.
  - N = 10 gives 1.57, recomputed here *(checked)*.
- **Minimum backtest length** (Theorem 3.1, `pseudo-math.md:145` (p. 11, checked)): `MinBTL ≈ (E[max_N]-expression / Ē[max_N])² < 2 ln N / Ē[max_N]²` years. This is the backtest length needed so that N skill-less independent trials don't produce a best in-sample Sharpe ratio of `Ē[max_N]`. With 5 years of data, at most 45 independent configurations keep the expected best below SR 1 (`pseudo-math.md:147` (p. 11)).
- **Not independent?** The trials can be reduced to an effective number of independent ones, e.g. by principal components (`pseudo-math.md:147` (p. 11)). MinBTL is "a necessary, non-sufficient condition".
- **Model complexity:** 7 binary parameters means `N = 2⁷ = 128` trials and an expected best Sharpe above 2.6 (`pseudo-math.md:165` (p. 13, unchecked)).
- **Without memory, overfitting is harmless but useless:** with i.i.d. performance, the selected best has out-of-sample Sharpe around zero (`pseudo-math.md:219` (p. 19)).
- **With memory, it hurts** (`pseudo-math.md:227-263` (p. 19–21)):
  - **Global constraint:** re-centring each path to a fixed mean makes in-sample and out-of-sample Sharpe ratios strongly *negatively* related (Proposition 6.1).
  - **Serial correlation:** an AR(1) with `φ = 0.995` (half-life `−ln 2/ln φ ≈ 138` observations) gives the same result (Propositions 6.2–6.3).
  - "When investment advisers do not control for backtest overfitting, good backtest performance is an indicator of negative future results."
- **Worked example** (`pseudo-math.md:299-303` (p. 25)):
  - A seasonal rule on a pure random walk, searched over entry day × holding period × stop loss × side = 8,800 cells, finds a Sharpe of 1.27 on 1,000 days.
  - Its PSR statistic is 2.83 (p < 1%).

## Assumptions against the Arena
- **Annualised Sharpe ratios on long daily samples.** We have 3 days per Prosperity round and maybe one public day per Arena round. The arithmetic carries over if "Sharpe" is the per-period mean PnL over its standard deviation, with the period a day or a block of ticks. The variance of the estimate is then about `1/D` for D periods, so the best of N null cells has an expected per-period Sharpe of `E[max_N]/√D`. *(Inferred from (2.3)–(3.1).)*
  - N = 100: 2.53 by luck over 1 period, 1.46 over 3 days, 0.46 over 30 blocks *(computed here)*.
- **Independent trials.** Grid neighbours share most of their trades, so the effective N is smaller than the cell count. [The deflated Sharpe ratio](deflated-sharpe-ratio.md) appendix A.3 estimates it by clustering.
- **Memory is the normal case here.** Pegged and mean-reverting products (Resin, Osmium, Squid Ink) are exactly the "compensation effect" setting. A grid optimum tuned to one day's swings is predicted to *under*perform on the next. *(Inferred; not tested on our data.)*
- **Selection is also done by looking.** Every public-backtest submission on the portal and every look at a held-out day is a trial ([validation](../concepts/validation-and-overfitting.md)).

## In our notation
| Paper | Ours |
|---|---|
| a trial / configuration | one `arena.grid` cell (bot file + `--set` + grid values), one manual variant, or one portal submission |
| N | grid cells × variants tried before the choice, not just the final grid's size |
| `y` years, `q` returns per year | D days, or D × blocks per day, of per-period PnL |
| `SR` | per-period mean PnL over its std; `arena.grid` reports the PnL total, `min day` and `nbhd` (`ARCHITECTURE.md`, Grid search), not this ratio |

## Traps
- **OCR:** the upper bound `√(2 ln[N])` reads "p 2 ln[N] 3" (the 3 is a footnote marker) (`pseudo-math.md:123` (p. 9)). MinBTL's bound appears twice, once garbled across a line break (`pseudo-math.md:149-151` (p. 11)).
- **Typo in the paper itself:** eq. (6.3) reads `Δm_τ = (1 − φ)μ + (φ − 1)φm_{τ−1} + σε_τ` in the PDF too *(checked with `pdftotext`)*. It is not consistent with eq. (6.4), `m_τ = (1 − φ)μ + φm_{τ−1} + σε_τ`, which implies `(φ − 1)m_{τ−1}` (`pseudo-math.md:251` (p. 21, checked)). Use (6.4).
- `E[max_N]` assumes N i.i.d. standard normals; it is a *large-N* approximation.

## Read depth
- **Read:** sections 1–9.
- **Checked against the PDF (page images):** (2.3), (2.4), (3.1), (3.2) and the upper bound.
- **Not read:** the appendix proofs and the Python code of Section 10.5.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
