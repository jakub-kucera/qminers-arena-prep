---
title: Carr & López de Prado, "Determining optimal trading rules without backtesting" (2014)
type: source
repo: literature_md/optimal-trading-rules
status: read
updated: 2026-10-19
---

# Carr & López de Prado, "Determining Optimal Trading Rules without Backtesting" (working paper, arXiv:1408.1159, August 2014)

## What it is
A 39-page working paper, most of it heat maps. The idea: don't tune a trading rule's thresholds on the historical path, which overfits them. Instead, fit a price process to the whole history, simulate many paths from the fitted process, and choose the rule on those (`optimal-trading-rules.md:19` (p. 2)). The rule studied is the exit of an existing position, a profit-taking and a stop-loss threshold (`optimal-trading-rules.md:31` (p. 3)). This is the theory behind tuning on `arena.sim` days rather than on the handed-out ones.

## Main results
- **An overfit rule** (Definition 2, `optimal-trading-rules.md:65` (p. 5, checked)): the in-sample optimal rule `R*` is overfit if its expected out-of-sample Sharpe ratio falls below the median over the alternative rules. That is PBO's definition ([PBO](probability-of-backtest-overfitting.md)).
- **The process** (eq. 2, `optimal-trading-rules.md:73` (p. 5, checked)): a discrete Ornstein–Uhlenbeck process, `P_t = (1 − φ)·E_0[P_T] + φ·P_{t−1} + σ·ε_t`, `ε_t ∼ N(0, 1)`. It is stationary for `φ ∈ (−1, 1)` (`optimal-trading-rules.md:83-85` (p. 6, checked)).
- **The procedure** (p. 6–7, checked against the page images; the markdown lost its inline math):
  - **Step 1:** estimate `φ` and `σ` by OLS on the deviations from the target level (eq. 5–7, `optimal-trading-rules.md:91-93` (p. 6, checked)).
  - **Step 2:** a 21 × 21 mesh of stop-losses `{0, −½σ, …, −10σ}` and profit-takings `{0, ½σ, …, 10σ}` (`optimal-trading-rules.md:108` (p. 7, checked)).
  - **Step 3:** 100,000 paths from the fitted process, each with a maximum holding period such as 100 observations (`optimal-trading-rules.md:110` (p. 7, checked)).
  - **Steps 4–5:** the Sharpe ratio of every node over the paths; take the best node, or the best stop-loss for a given profit target, or the reverse (`optimal-trading-rules.md:112-118` (p. 7)).
- **Half-life** (`optimal-trading-rules.md:120` (p. 7, checked)): `τ = −ln 2 / ln φ`, so `φ = 2^(−1/τ)`.
- **Zero expected profit, the market maker's case** (`optimal-trading-rules.md:132` (p. 8)): with a short half-life (5) the best rule is a small profit-take with a stop-loss 5–7 times larger, at a per-path Sharpe ratio of about 3.2. "This is in fact what many market-makers do in practice." A symmetric rule earns about nothing.
- **Random walk** (`optimal-trading-rules.md:148` (p. 9)): as the half-life grows the heat map loses any structure. Tuning on history would then pick a random node; the simulation shows there is no optimal rule.
- **Only a conjecture** (`optimal-trading-rules.md:204` (p. 11)): no closed form; they conjecture a unique optimal rule for an O-U price.

## Assumptions against the Arena
- **Everything rests on the fitted process.** If the product isn't O-U, or `φ` changes during the day, the "optimal" rule is optimal for the wrong market. Overfitting the rule is traded for misspecifying the model *(inferred)*.
- **An exit rule for one position,** not a market maker's continuous quoting. The template's analogue is `stop_loss` per product and the `level_band` of a product that returns to a level (`python/bots/template.py` PARAMS); its quotes are not covered.
- **The template's stops already follow the market-maker shape:** each `stop_loss` is about 3 times the plain-day drawdown, wide against small per-trade edges (`IDEAS.md`, "A loss stop per product"). That is consistent with Figure 1 *(inferred; not tested against a fitted process)*.
- **Not measured here:** `φ` and the half-life of any Prosperity product's deviation from its level. `arena.sim`'s `HYDROGEL_PACK` preset already uses an O-U fundamental calibrated on P4's Hydrogel (`ARCHITECTURE.md`, "Simulated market").

## In our notation
| Paper | Ours |
|---|---|
| `E_0[P_T]`, the target level | a product's `level` (template PARAMS), or the fundamental of an `arena.sim` preset |
| `φ`, `σ`, half-life | O-U parameters of the deviation from that level |
| stop-loss / profit-taking `(π, π̄)` | `stop_loss`; `level_band` and the take edges |
| 100,000 simulated paths | `arena.sim generate` days from a calibrated preset |

## Traps
- **OCR lost every inline formula,** including the mesh, the half-life and the step inputs (`optimal-trading-rules.md:108-120` (p. 7)). Read Section 4 from the PDF.
- **The heat maps are images** without the parameter values in the text (Table 1 and the figures are referred to as "[TABLE 1 HERE]" in the source). The parameter combinations in the captions are only on the PDF pages.
- **"Please do not cite without the authors' permission"** on the cover: a working paper.

## Read depth
- **Read:** the whole text (Sections 1–5).
- **Checked against the PDF (page images):** eq. 2–7, the procedure's steps and the half-life (p. 5–7).
- **Not read:** the appendix code; the individual heat maps beyond the text's description of them.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
