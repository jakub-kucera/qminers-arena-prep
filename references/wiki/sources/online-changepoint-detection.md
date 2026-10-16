---
title: Adams & MacKay, "Bayesian online changepoint detection" (2007)
type: source
repo: literature_md/online-changepoint-detection
status: read
updated: 2026-10-14
---

# Adams & MacKay, "Bayesian online changepoint detection" (arXiv:0710.3742, 2007)

## What it is
A 7-page paper giving an exact online algorithm for the probability that the data's regime changed `r` steps ago, for every `r` (the "run length"). It needs only a predictive probability for the next observation under each run length. It is the detector behind the regime guard (B1) in [harder-rounds](../concepts/harder-rounds.md), and the missing jump detector of [Das](learning-market-maker.md). Fetched from arXiv on 2026-10-14.

## Main results
- **The run length's prior** has two outcomes, so the algorithm is cheap. Either `r_t = r_{t−1} + 1` with probability `1 − H`, or a change, `r_t = 0`, with probability `H` (eq. 4, `online-changepoint-detection.md:47` (p. 2, checked)). With geometric gaps of mean `λ`, the hazard is constant, `H = 1/λ` (`online-changepoint-detection.md:53` (p. 2)).
- **Algorithm 1** (`online-changepoint-detection.md:103` (p. 3, checked); checked on the page image). For each `r`:
  1. Compute the predictive probability `π_t^(r)` of the new datum from that run's sufficient statistics.
  2. Growth: `P(r_t = r+1, x_{1:t}) = P(r_{t−1} = r, x_{1:t−1})·π^(r)·(1−H)`.
  3. Change: `P(r_t = 0, x_{1:t}) = Σ_r P(r_{t−1} = r, x_{1:t−1})·π^(r)·H`.
  4. Normalise.
  5. Update each run's statistics, and start a fresh run from the prior.
- **Cost** is linear in the time since the start (`online-changepoint-detection.md:145` (p. 4)). Dropping run lengths whose probability is below a threshold (e.g. 10⁻⁴) makes it constant on average, about the expected run length (`online-changepoint-detection.md:131` (p. 3)).
- **A volatility regime in finance, as an example:** daily Dow Jones returns from 1972 to 1975, modelled as a zero-mean Gaussian with a variance that changes in steps. The precision has a gamma prior (`a = 1`, `b = 10⁻⁴`) and `λ_gap = 250` (`online-changepoint-detection.md:169` (p. 5)). The detected changes line up with Watergate, the oil embargo and Nixon's resignation.

## Assumptions against the Arena
- **The data are independent within a regime.** Tick-level mid changes aren't: Prosperity's mid has a lag-1 autocorrelation of about −0.5 (bid–ask bounce, `arena.diagnose`'s `mid AC1`). Run it on wall-mid changes, or on changes over a coarser step, not on the raw mid *(inferred)*.
- **The hazard is a guess.** `λ` should be about the expected number of ticks between regime changes. From Prosperity data, regime changes are rare within a day (DTU's Hydrogel switched between days, `drift-and-regime-change.md`), so `λ` would be in the thousands of ticks.

## In our notation
- **The regime guard (B1):** feed it each tick's wall-mid change. Use a zero-mean Gaussian model with an unknown variance for a volatility regime, or a Gaussian with an unknown mean for a drift or level shift. When `P(r_t < k)` passes a threshold, the template drops its `level`/`jump` bets and falls back to plain market making.
- **Das's recentring:** the same detector says when to reset the value distribution.
- **Built 2026-10-17** (`changepoint_level` in `bots/template.py`; our derivation, not the paper's):
  - The observations are block means of the wall mid, and the model is a level with a known variance, not the Gaussian–gamma model, so no Student-t predictive is needed. Each block mean is transformed so that, for a product that returns to its level at a known rate, it is an independent noisy observation of the level.
  - The first run starts at the configured level with a narrow prior, so a level from earlier days is trusted until the evidence moves it. New runs start at the latest block mean with a wide one.
  - **It detects well, but acting on it didn't pay** on Prosperity-like data (`IDEAS.md`, "A changepoint detector on the level").
- **State in `traderData`:** a truncated list of (run probability, sufficient statistics), a few dozen numbers per product.
- **The Student-t predictive** of the Gaussian–gamma model is a standard conjugate result that this paper doesn't print. Check it in a textbook before coding (`SCHEMA.md`, rule 9).

## Traps
- **Algorithm 1 uses `H(r_{t−1})`** where eq. 4 has `H(r_{t−1}+1)`, in the original. With a constant hazard it doesn't matter.
- **Step 1's two initialisations** (`P(r_0) = S̃(r)` or `P(r_0 = 0) = 1`) correspond to whether the series starts at a change (start of a day: use `P(r_0 = 0) = 1`).

## Read depth
- **Read:** the whole paper, with Algorithm 1 checked on the page image of p. 3.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [learning-market-maker](learning-market-maker.md).
