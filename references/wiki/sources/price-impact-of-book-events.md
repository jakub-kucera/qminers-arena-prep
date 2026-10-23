---
title: Cont, Kukanov & Stoikov, "The price impact of order book events" (2011)
type: source
repo: literature_md/price-impact-of-book-events
status: read
updated: 2026-10-12
---

# Cont, Kukanov & Stoikov, "The price impact of order book events" (working paper, March 2011; later Journal of Financial Econometrics, 2014)

## What it is
A 26-page empirical paper on one month (April 2010) of TAQ Level-1 data for 50 random S&P 500 stocks. It defines **order flow imbalance (OFI)**, the net change in the best bid and ask queues over an interval. It shows that the mid-price change over the *same* interval is linear in OFI, with a slope inversely proportional to depth. It is the source of the "order-flow imbalance" that teams and our `TODO_DONE.md` mention next to the static book imbalance `ρ`.

## Main results
- **Event contribution** (`price-impact-of-book-events.md:75-77` (p. 4, checked)): between two snapshots n−1 and n of the best levels (`P^B, q^B, P^A, q^A`), `e_n = 1{P^B_n ≥ P^B_{n−1}} q^B_n − 1{P^B_n ≤ P^B_{n−1}} q^B_{n−1} − 1{P^A_n ≤ P^A_{n−1}} q^A_n + 1{P^A_n ≥ P^A_{n−1}} q^A_{n−1}`. In words:
  - **Bid at the same price:** `q^B_n − q^B_{n−1}`, the size added or removed. A market sell and a cancelled buy count the same.
  - **Bid moves up:** `+q^B_n`. **Bid moves down:** `−q^B_{n−1}`.
  - **The ask:** the same with signs reversed.
- **OFI over an interval:** `OFI_k = Σ e_n` over the events in `[t_{k−1}, t_k]`. The mid change in ticks is `ΔP_k = (P_k − P_{k−1})/δ` (`price-impact-of-book-events.md:79-87` (p. 4, checked)).
- **Stylised book** (every level behind the best has depth D, events only at the best): `ΔP = OFI/(2D) + ε` (eq. 1, `price-impact-of-book-events.md:114-129` (p. 6, checked)).
- **The model** (eq. 2–3, `price-impact-of-book-events.md:137-150` (p. 6–7, checked)): `ΔP_k = β·OFI_k + ε_k` and `β_i = c/AD_i^λ + ν_i`. `AD_i` is the average of `(q^B + q^A)/2` over the half hour.
- **Fit:** 10-second intervals, OLS per half-hour per stock, about 180 points each (`price-impact-of-book-events.md:178-191` (p. 8–9)).
  - **Average R² is 65%** (`price-impact-of-book-events.md:48` (p. 3)). β is significant almost always, and the intercept almost never.
  - A quadratic term adds 3 points of R², so the relation is linear.
  - Without the price-changing events, R² drops to 35–60% (`price-impact-of-book-events.md:189` (p. 8)).
  - Results hold from 10 quote updates to 10 minutes, with R² rising with the interval.
- **Depth:** `λ ≈ 1`; `λ = 1` is not rejected for 35 of 50 stocks. `ĉ` is usually below the stylised ½, so prices are more resilient than the top-of-book depth suggests (`price-impact-of-book-events.md:330` (p. 12, unchecked)). Impact is about twice the average at the open, where depth is about half (`price-impact-of-book-events.md:406` (p. 14)).
- **Trades add nothing beyond OFI** (`price-impact-of-book-events.md:449-451` (p. 16–17)):
  - Trade imbalance alone has R² 32%, against OFI's 65%.
  - Put together, trade imbalance is significant in only 31% of subsamples.
  - The well-known "square-root" impact of volume is shown to be a statistical artefact of aggregation (Proposition 1, eq. 13–14).

## Assumptions against the Arena
- **The regression is contemporaneous, not predictive.** `ΔP_k` and `OFI_k` cover the same interval, and the paper never tests whether OFI predicts the *next* interval. It notes that autocorrelations at 10 seconds are small and vanish quickly (`price-impact-of-book-events.md:154` (p. 7)). So OFI explains moves; on this evidence it is not a signal to trade on. Any use as a forecast must be tested here first.
- **What does carry over is the impact of our own taking.** Taking `x` units at the best level is an OFI of `x`, so the stylised model says the mid moves about `x/(2D)` ticks. With Prosperity's thin books, a take that clears a level moves the mid by construction. That matters for size decisions in `take` and when unwinding (`python/bots/template.py`).
- **Snapshot data.** Prosperity gives one book snapshot per tick, so `e_n` between consecutive ticks lumps all the events in between, which is what the paper does with 10-second TAQ data.
- **Depth is a bot's quote size** in Prosperity, so `AD` is mostly constant per product, and the depth-scaling result has little to work with.

## In our notation
| Paper | Ours |
|---|---|
| `P^B_n, q^B_n, P^A_n, q^A_n` | `bid_price_1`, `bid_volume_1`, `ask_price_1`, `ask_volume_1` of tick n in the CSVs; `book.bids[0]`, `book.asks[0]` in the bot |
| `e_n` | computable in the bot from the previous tick's best levels, stored in `traderData` |
| `δ` | 1 price unit |
| `AD` | mean of `bid_volume_1` and `ask_volume_1` |

## Traps
- **OCR:** in the definition of `e_n` the first two indicators read `P^A_n ≥ P^A_{n−1}` and `P^A_n ≤ P^A_{n−1}`; the PDF has `P^B` there (`price-impact-of-book-events.md:75` (p. 4)). Coded from the markdown, the bid side would follow the ask price.
- **OCR:** the ceiling brackets `⌈ ⌉` in the stylised model's `ΔP^a` and `ΔP` became square brackets (`price-impact-of-book-events.md:118-122` (p. 6)).
- **"Price impact" here is contemporaneous co-movement.** Citing this paper for "order-flow imbalance predicts prices" overstates it. The predictive claims for imbalance come from Gould & Bonart and Cartea et al. 2018, which use the static imbalance `ρ`, not OFI.

## Read depth
- **Read:** sections 1–5.
- **Checked against the PDF (page images):** `e_n`, `OFI_k`, `ΔP_k`, eq. (1)–(3) and the depth average `AD_i`.
- **Mapped only:** the tables (stock-by-stock regression outputs), the intraday-pattern figures, the proof of Proposition 1, the appendix on TAQ cleaning.

## Cited by
[book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md).
