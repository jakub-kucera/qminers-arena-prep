---
title: Gould & Bonart, "Queue imbalance as a one-tick-ahead price predictor" (2015)
type: source
repo: literature_md/queue-imbalance-predictor
status: read
updated: 2026-10-12
---

# Gould & Bonart, "Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book" (arXiv:1512.03492, 2015)

## What it is
An empirical paper (30 pp.) that asks one narrow question: does the imbalance between the best bid and ask queues predict the **direction of the next mid-price change**? The answer comes from a logistic regression on 10 Nasdaq stocks over 2014, with an out-of-sample test against a coin flip. It is the cleanest test design in the literature for the imbalance signal, and the one to copy on our data.

## Main results
- **The signal:** `I(t) = (nᵇ − nᵃ)/(nᵇ + nᵃ)`, with `nᵇ`, `nᵃ` the volumes at the best bid and ask, so `I ∈ [−1, 1]` (`queue-imbalance-predictor.md:112` (p. 7, checked)). Stoikov's `I` is the same quantity rescaled to `[0, 1]` (`queue-imbalance-predictor.md:116-128` (p. 7–8)).
- **The test design** (`queue-imbalance-predictor.md:165-191` (p. 11–12)):
  - The target `y_i` is 1 if the i-th mid change is up and 0 if down. Ticks where the mid does not move are not targets, and the size of the move is ignored.
  - `I` is sampled at a random time between two mid changes.
  - 100 mid changes per day, 252 days, then a random 80/20 train/test split.
- **The model:** `ŷ(I) = 1/(1 + e^{−(x₀ + I·x₁)})`, a logistic regression fitted by maximum likelihood (`queue-imbalance-predictor.md:233` (p. 13, checked)). It is scored against the null `ŷ = ½` by the out-of-sample ROC area (null 0.5) and the mean squared residual (null 0.25) (`queue-imbalance-predictor.md:241-260` (p. 14, unchecked)).
- **Fits** (Table 2, `queue-imbalance-predictor.md:298-312` (p. 17, checked)): `x₀` is about 0 for every stock (buy and sell sides symmetric). `x₁` is 2.0–2.7 for the five large-tick stocks (spread ≈ 1 tick, long queues) and 0.5–0.85 for the five small-tick stocks. At `I` near 1, the probability of an up move is 0.8–0.9 for large-tick stocks and 0.6–0.7 for small-tick ones (`queue-imbalance-predictor.md:332` (p. 18)).
- **Out of sample:**
  - ROC area 0.75–0.81 for large-tick stocks and 0.58–0.64 for small-tick ones (Table 4, `queue-imbalance-predictor.md:356-369` (p. 20, checked)).
  - Mean squared residual 0.18–0.20 against 0.25, a 20–30% cut, for large-tick stocks, but only 0.235–0.246, a 2–6% cut, for small-tick ones (Table 5, `queue-imbalance-predictor.md:371-384` (p. 21, checked)).
  - In-sample and out-of-sample numbers are almost equal, so the fits do not over-fit.
- **A nonparametric fit adds almost nothing:** local logistic regression matches these numbers to the third decimal in most cases (`queue-imbalance-predictor.md:400-404` (p. 22)).
- **Why tick size matters** (`queue-imbalance-predictor.md:453-455` (p. 26)):
  - At a 1-tick spread, the mid can only move when a best queue empties, so queue lengths decide it.
  - At wider spreads, a new order inside the spread can also move the mid, and the imbalance cannot see that coming.
  - Small-tick stocks also have short queues, where a single market order moves the price.
- **Practical notes** (`queue-imbalance-predictor.md:447-449` (p. 25)): the signal is strongest near `I = ±1` and weak near 0, so "abstain from trading when I ≈ 0". It is less informative when both queues are small.

## Assumptions against the Arena
- **Prosperity looks like the small-tick case.** Spreads are 2–4 ticks on P3 Kelp and Squid Ink and 13–21 ticks on P4 round 1 *(checked: [micro-price](micro-price.md), "Assumptions")*. A new quote inside the spread is common there, and the paper says that is when `I` predicts least. Expect a ROC area nearer 0.6 than 0.8, if anything.
- **The target ignores the size of the move.** A market maker with a wide spread cares about expected price change over its holding time, not the sign of the next move. Use the paper's design for the go/no-go test, then measure the size separately.
- **The best levels in Prosperity are bot quotes.** Their volumes may be set by the bot's rules rather than by order flow, so the imbalance may tell us about the bot's inventory or quoting rule, not about pressure. That may be useful, but it is a different mechanism.
- **Sample size:** 25,200 points per stock. One Prosperity day has 10,000 ticks with a mid change on 60–78% of them, so a day gives enough points per product for a two-parameter fit.

## In our notation
| Paper | Ours |
|---|---|
| `nᵇ(b(t), t)`, `nᵃ(a(t), t)` | `book.bids[0][1]`, `book.asks[0][1]` (volumes positive in `bots/template.py` and `arena/model.py`); `bid_volume_1`, `ask_volume_1` in the CSVs (ask volumes are positive there too) |
| `I` | the `ρ` of Cartea et al. 2018 ([order-book-signals](order-book-signals.md)); Stoikov's `I` is `(1 + ρ)/2` |
| mid change times `T` | ticks where `mid_price` differs from the previous tick's |

## Traps
- **OCR:** Tables 2–6 lost their decimal points ("2 49" for 2.49, "0 781" for 0.781) and some columns are shifted (`queue-imbalance-predictor.md:298-326` (p. 17–18)). Use the PDF for any number in a table.
- **OCR:** eq. (16) reads `P(ŷ_{'t} > 1/2)` where the PDF has `P(ŷ_{i'} > 1/2) = 1/2 and P(ŷ_{j'} > 1/2) = 1/2` (`queue-imbalance-predictor.md:228` (p. 13, checked)).
- The paper reports statistical significance for all 10 stocks (Wald and likelihood-ratio tests). With 25,000 points, significance is easy; the out-of-sample residuals are the honest measure.

## Read depth
- **Read:** all sections (1–8).
- **Checked against the PDF (page images):** eq. (7), eq. (17), Tables 2 and 4; Table 5 via `pdftotext`.
- **Not read:** the reference list.

## Cited by
[book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md).
