---
title: Cartea, Donnelly & Jaimungal, "Enhancing trading strategies with order book signals" (2018)
type: source
repo: literature_md/order-book-signals
status: read
updated: 2026-10-12
---

# Cartea, Donnelly & Jaimungal, "Enhancing Trading Strategies with Order Book Signals" (Applied Mathematical Finance, 2018; accepted manuscript)

## What it is
A 42-page paper with an empirical half and a control half, both on Nasdaq 2014 data:
- **Empirical half:** best-level volume imbalance predicts the side of the next market order and the price move just after it. A market maker that always quotes at the touch loses money.
- **Control half:** a market maker that may post at the best bid and/or ask, conditioned on an imbalance regime and the spread, is fitted on January–June and tested on July–December.

It is the one paper that turns the imbalance signal into a quoting rule, and its rule of thumb maps directly onto our markout tables.

## Main results
- **The signal:** `ρ_t = (V^b_t − V^a_t)/(V^b_t + V^a_t) ∈ [−1, 1]`, volumes at the best bid and ask (`order-book-signals.md:75-79` (p. 5, checked)). It is the same quantity as Gould & Bonart's `I` ([queue-imbalance-predictor](queue-imbalance-predictor.md)). It is bucketed into regimes: sell-heavy `[−1, −⅓)`, neutral `[−⅓, ⅓]`, buy-heavy `(⅓, 1]` (`order-book-signals.md:128` (p. 9)).
- **Quoting at the touch loses money.** A "zero-intelligence" maker that always quotes at the best bid and ask, with an inventory cap Q and flattened every 30 minutes, has a **negative annualised Sharpe ratio for all 11 stocks and every Q from 1 to 200**. This holds even when the inventory is flattened at the mid (Table 2, `order-book-signals.md:462-477` (p. 30, checked); `order-book-signals.md:104` (p. 7)). The cause is adverse selection.
- **Quoting deeper does not escape it:** 91.6% (GOOG) to 99.9% (INTC, ORCL) of market orders fill entirely at the best price (Table B.8, `order-book-signals.md:652-669` (p. 38–39, checked)). A quote behind the touch rarely fills. So a continuous-depth model (Avellaneda–Stoikov, Guéant et al.) rounded to the tick behaves like "always at the touch with an inventory cap" (`order-book-signals.md:112` (p. 8)).
- **What the imbalance predicts** (Figures 3–4, Table B.9, `order-book-signals.md:134-144` (p. 9–11)):
  - In a buy-heavy regime most market orders are buys.
  - The mid change 10 ms after a market buy is larger when the book is buy-heavy. This holds even counting only buys, so it is not just a composition effect.
- **The control problem** (`order-book-signals.md:232-260` (p. 16–17)):
  - The agent posts unit orders at the touch (`γ± ∈ {0, 1}`), always filled by the next market order.
  - It maximises terminal wealth minus a running penalty `φ∫q²` and a liquidation cost, subject to `Q̲ ≤ q ≤ Q̄`.
  - The state is (imbalance regime, spread). The model is fitted per state: market-order intensities `λ±(J)` and the expected mid jump right after each event, `ε±(J)`.
- **Rule of thumb** (eq. 13, `order-book-signals.md:304-312` (p. 20, checked)):
  - Post the sell quote when `Δ/2 − ε⁺(J) + Σ₁⁺ > Σ₀⁺`, and the buy quote likewise with `ε⁻`. `Σ` are inventory and terminal corrections.
  - Without inventory costs and far from the end, **post a side only if half the spread exceeds the expected adverse mid move after a fill on that side in the current state**. That quantity is "the expected amount of cash that the agent earns if the position is unwound at the midprice".
  - The terms `γ±·Δ/2` are the spread earned, and `−γ±·ε±(J)` is the adverse-selection cost (`order-book-signals.md:300` (p. 19, checked)).
- **Optimal regions** (Figure 6, `order-book-signals.md:334-346` (p. 21–22)): in a buy-heavy state the buy region grows and the sell region shrinks, and near zero inventory the agent may post *nothing* and let the position appreciate.
- **Out of sample** (July–December 2014, half-hour windows, Q = 50; Tables 3–5, `order-book-signals.md:479-528` (p. 30–31, checked)):
  - With no imbalance (`n_Z = 1`), results are mixed: INTC is negative at every `φ`.
  - With 3 or 5 imbalance regimes, the Sharpe ratio is positive for nearly all stocks and rises with the inventory penalty `φ`.
- **Honest fill model** (Table 7, `order-book-signals.md:530-574` (p. 31–33, checked)):
  - Each fill is given a probability equal to the share of market orders that clear the whole best queue, 0.02–0.87 depending on stock and regime. That is the back of the queue.
  - With it, Sharpe ratios shrink to about −5…+12. ARCC is negative at every `φ` and INTC is near zero.
  - The authors place the truth between Tables 5 and 7.
- **Spoofing:** the signal can be manipulated by orders placed to be cancelled (`order-book-signals.md:578` (p. 33)).

## Assumptions against the Arena
- **Large-tick stocks (spread 1–2 ticks) and posting only at the touch.** Prosperity spreads are 2–4 ticks (P3 Kelp, Squid Ink) or 13–21 (P4 round 1) *(checked, [micro-price](micro-price.md))*, and our template quotes inside the spread (one tick better than the best quote). The authors say small-tick stocks need quotes inside the spread, which their model doesn't cover (`order-book-signals.md:172` (p. 13)).
- **The rule of thumb carries over without the model.** Half-spread against `ε±(J)` needs no HJB solution. It only needs the expected mid move after our fills, by state, and that is what our markout tables measure.
- **Always filled at the touch, zero latency.** In Prosperity, our fills come from bots crossing our quote or from trades at our price (`CLAUDE.md`, matching rules); the queue question is what `--resting` models. Table 7 shows how much the result depends on the fill assumption.
- **The book is a bot's quote.** In Prosperity the best-level volume is often one bot's fixed size, so `ρ` may mostly encode *which* bot is at the touch. That may still predict, but for a different reason.
- **Their Sharpe ratios are annualised over half-hour windows with parameters re-forecast each window** (`order-book-signals.md:392-428` (p. 25–27)). That is not comparable to a Prosperity day's PnL.

## In our notation
| Paper | Ours |
|---|---|
| `V^b_t`, `V^a_t` | `book.bids[0][1]`, `book.asks[0][1]` (`bots/template.py`); `bid_volume_1`, `ask_volume_1` in the CSVs |
| `Δ/2` | the half-spread earned. For our quotes it is the distance of the quote from `fair` (`make_edge`, `bots/template.py:41`), not half the book's spread |
| `ε±(J)` | the markout of our fills: the mid change after a fill, by side and by the state at the fill. `arena/analysis.py` computes fill markouts from 1 tick ("Markout horizons start at 1 tick", `CLAUDE.md`) but not per imbalance state |
| `φ` | no direct parameter; the template's linear `skew` is the closest |
| `Q̲, Q̄` | `limit` per product in `PARAMS` |

## Traps
- **OCR dropped minus signs in Tables 2–4.** In the markdown, Table 2 shows positive Sharpe ratios at large Q (AA 6.97 and 6.41 at Q = 100 and 200, CSCO 8.50 at Q = 1, ...). In the PDF every cell of Table 2 is negative (`order-book-signals.md:462-477` (p. 30)). Table 3 and Table 4 (ARCC −0.85, −0.41) have the same slip. Read any table from the PDF.
- **OCR:** Table 1 and the Section 3.4 parameter vectors are mangled (column labels shifted, `λ̂¹` for `λ̂⁺`) (`order-book-signals.md:114-120` (p. 8–9), `order-book-signals.md:324-330` (p. 20–21)).
- **Fill assumption:** the headline results (Tables 4–5) assume every market order fills the agent's quote. Quote Table 7, not Table 5, when arguing that the signal pays.
- The appendix parameter tables use `n_Δ = 3` in the text and 2 in the tables (`order-book-signals.md:690` (p. 39, unchecked)); not checked further.

## Read depth
- **Read:** sections 1–5, Appendix B.
- **Checked against the PDF (page images):** `ρ` (eq. 1), eq. (12)–(13), the interpretation of the `ε` and `Δ/2` terms, Tables 2–5 and 7. Table B.8 via the text (GOOG 91.6%).
- **Mapped only:** Section 3.1's point-process definitions (eqs. 2–7), the parameter forecasting of Section 4.2, the proofs (Appendix A), Appendix C.

## Cited by
[book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [queue-position-and-fills](../concepts/queue-position-and-fills.md), [contradictions](../contradictions.md) (row 11).
