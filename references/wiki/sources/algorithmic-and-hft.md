---
title: Cartea, Jaimungal & Penalva, "Algorithmic and High-Frequency Trading" (book, 2015)
type: source
repo: literature_md/algorithmic-and-hft
status: partly-read
updated: 2026-10-12
---

# Cartea, Jaimungal & Penalva, *Algorithmic and High-Frequency Trading* (Cambridge University Press, 2015)

## What it is
The standard textbook on stochastic-control trading strategies (360 PDF pages). It covers microstructure basics (Part I), the control toolbox (Part II), and optimal execution, market making, pairs trading and order imbalance (Part III). It is a reference to look things up in, not to read through. Four chapters were read for the questions the wiki has (Phase 2, 2026-10-12): the microstructure primer (ch. 2), market making (ch. 10), pairs trading and statistical arbitrage (ch. 11) and order imbalance (ch. 12). It is the textbook home of Cartea et al. 2018 ([order-book-signals](order-book-signals.md)) and of the running-penalty objective ("Model B" in [Guéant 2017](optimal-market-making.md)).

## Main results
**Chapter 2, microstructure primer:**
- **Grossman–Miller:** n competing risk-averse market makers take a liquidity trader's sale of i units at a discount, `S₁ = μ − γσ²·i/(n+1)`. The discount vanishes as competition n grows (`algorithmic-and-hft.md:575-579` (p. 41, checked)).
- **The static depth trade-off:** maximise `p·e^{−κδ}·δ` per side, giving **`δ* = 1/κ`**, the mean depth of the book (`algorithmic-and-hft.md:685-688` (p. 46, checked)).
- **Kyle (1985):** an insider trades `x* = (v − μ)/(2λ)`, and the price moves linearly with net order flow, `S = μ + λ(x + u)` (`algorithmic-and-hft.md:725-755` (p. 49–50, checked)).
- **Glosten–Milgrom:** a market maker facing a share α of informed traders breaks even with an ask half-spread `Δa = (V_H − μ)/(1 + ((1−α)/α)·(½)/p)`, and the bid likewise (`algorithmic-and-hft.md:785-791` (p. 52, checked)). If liquidity traders are price-sensitive and the spread gets too wide, the market can collapse to no trade (`algorithmic-and-hft.md:825` (p. 54)).

**Chapter 10, market making:**
- **Setup** (`algorithmic-and-hft.md:5729-5745` (p. 263–264)):
  - Market orders arrive at rate λ±, and a quote at depth δ is filled with probability `e^{−κδ}`, so its fill rate is `λ·e^{−κδ}`.
  - The objective is terminal cash, minus a liquidation cost `αq²` and a running inventory penalty `φ∫q²`.
  - Inventory is bounded, `q̲ ≤ q ≤ q̄`.
- **Optimal depths** (eq. 10.8, `algorithmic-and-hft.md:5788-5796` (p. 265, checked)): `δ^{±*}(t, q) = 1/κ± − [h(t, q∓1) − h(t, q)]`, with no quote on the side that would breach the bound.
  - With equal κ on both sides, `h = (1/κ)·log ω` and **`ω(t) = e^{A(T−t)}·z`**, a matrix exponential (eq. 10.10–10.11, `algorithmic-and-hft.md:5820-5830` (p. 266, checked)).
  - `A` is tridiagonal: `−φκq²` on the diagonal, `λ±e^{−1}` off it, and `z_j = e^{−ακj²}`.
- **Without inventory constraints, `δ* = 1/κ` on both sides** (eq. 10.13, `algorithmic-and-hft.md:5884` (p. 270, checked)).
- The penalty induces **mean reversion of inventory**. In the book's simulation the bound is ±10, yet the path never goes beyond ±5 (`algorithmic-and-hft.md:5868` (p. 269)).
- **Quoting only at the touch** (eq. 10.17, `algorithmic-and-hft.md:5950-5956` (p. 272–273, checked)): post a side iff `Δ/2 + h(t, q∓1) − h(t, q) > 0`. That is the half-spread against the value lost by taking on a unit, the same structure as Cartea et al. 2018.
- **Choosing the quoted volume** (`algorithmic-and-hft.md:5976-6032` (p. 273–276)): the size posted on the side that reduces inventory grows with inventory, but not enough to flatten in one fill. With φ = 10⁻³, the agent stops quoting a side once inventory reaches ±7 of a ±20 bound.
- **Utility versus penalty are the same strategy** (eq. 10.19–10.20, `algorithmic-and-hft.md:6064-6090` (p. 277–278, checked)):
  - With exponential utility the depths are `(1/γ)·log(1 + γ/κ) + g(t, q) − g(t, q∓1)`.
  - Setting `φ = ½σ²γ` makes them equal the running-penalty ones up to a constant shift. This reconciles Avellaneda–Stoikov/GLFT with the Cartea–Jaimungal objective.
- **Adverse selection through jumps** (eq. 10.22–10.27, `algorithmic-and-hft.md:6114-6162` (p. 279–280, checked)):
  - If each market order moves the mid by ε± in its direction, **each quote moves out by ε±**: `δ^{±*} = 1/κ + ε± − [h(t, q∓1) − h(t, q)]`.
  - h itself changes too, so this is not the old strategy plus ε.
  - When buy and sell market orders arrive at different rates, the mid drifts. **The optimal inventory level is then not zero:** the strategy leans toward the side that appreciates (`algorithmic-and-hft.md:6218` (p. 283)).
- **Short-term alpha from order flow** (eq. 10.30–10.32, `algorithmic-and-hft.md:6220-6290` (p. 283–287)):
  - The drift `α_t` jumps with each market order and mean-reverts.
  - A touch-only maker posts only bids when α is large, and both sides when α and inventory are near zero.
  - Near the horizon, α stops mattering and the strategy just flattens.

**Chapter 11, pairs trading and statistical arbitrage:**
- **Ad hoc bands** (`algorithmic-and-hft.md:6339-6373` (p. 291–294)): open at ±k standard deviations of the co-integration factor and close near its mean.
  - The PnL is multimodal, at multiples of the band.
  - **Sharpe first rises and then falls as the band widens.**
  - A position may still be open at the end.
- **Optimal entry and exit for an Ornstein–Uhlenbeck spread** `dε = κ(θ − ε)dt + σdW`, with cost c and discount ρ (`algorithmic-and-hft.md:6381-6451` (p. 294–296, checked)):
  - The exit level `ε*` solves `(ε* − c)·F₊'(ε*) = F₊(ε*)` (eq. 11.2), where `F±(ε) = ∫₀^∞ u^{ρ/κ−1} e^{∓√(2κ/σ²)(θ−ε)u − u²/2} du`.
  - The entry level solves the analogous equation (11.3).
  - Faster mean reversion or more urgency moves both levels toward the mean.
  - **Double-sided:** the optimal long entry equals the optimal short exit, and vice versa (table, `algorithmic-and-hft.md:6561-6566` (p. 300, checked)). Exit level 1.7460 for κ = 1 and 1.4367 for κ = 4, with θ = 1, σ = 0.5, ρ = c = 0.01; **both recomputed here from (11.2)** *(checked)*.
- **Co-integrated drifts across n assets** (`algorithmic-and-hft.md:6553-6840` (p. 300–310, unchecked)): a Merton-style allocation `π* = (1/γ)(Ω⁻¹δ)α + correction`, where the co-integration correction fades toward the horizon (eq. 11.16). Read for the idea; the formulas were not checked.

**Chapter 12, order imbalance:**
- `ρ` is defined as in Cartea et al. 2018. Studies suggest the touch alone gives the best trade-off between prediction and complexity (`algorithmic-and-hft.md:6885-6911` (p. 312–313)).
- Imbalance is strongly autocorrelated, and positively correlated with the next price change (`algorithmic-and-hft.md:6925` (p. 314)).
- **Regimes as a Markov chain:** the maximum-likelihood transition estimate is simply `Â_ij = n_ij/Σ_j n_ij` (eq. 12.1, `algorithmic-and-hft.md:6933` (p. 315, checked)). It converts to a generator by a matrix logarithm.
- **Market-order rates by regime, ORCL, 1 day** (Table 12.1, `algorithmic-and-hft.md:7068` (p. 321, checked)):
  - Buy rates of 0.037/s neutral and 0.216/s in the most bid-heavy regime, about ×6.
  - Sell rates of 0.048/s neutral and 0.856/s in the most ask-heavy regime, about ×18.
  - After a buy market order, the mid rises a tick within 1 s with probability 0.09–0.30, depending on the regime.

## Assumptions against the Arena
- **Exponential fill probability per market order** `e^{−κδ}` and Poisson market orders, as in Avellaneda–Stoikov and GLFT. In Prosperity fills come from bots, so `λ` and `κ` must be measured from our fills ([optimal quoting](../concepts/optimal-quoting-models.md), "How to test it here").
- **The touch-only models (10.2.2, 10.4.2) assume a spread that is fixed and fills at the touch.** Prosperity's spreads are wide and we quote inside them.
- **Grossman–Miller and Glosten–Milgrom are static, one-period models.** They give the *direction* of effects: more competing makers means less edge, and more informed flow means a wider spread. They are not calibrated to anything.
- **The pairs-trading section assumes a co-integration factor estimated from data.** Prosperity's baskets often have *known* weights (`baskets-and-fixed-sums`), which removes the estimation risk the chapter worries about but keeps the entry/exit problem.

## In our notation
| Book | Ours |
|---|---|
| `δ±` (depth from the mid) | the quote's distance from `fair`: `make_edge` plus `skew` shift (`bots/template.py:189-221`) |
| `λ±`, `κ±` | rate of fills on each side and its decay with distance; from `_orders.csv` / `_fills.csv` |
| `q̲, q̄` | `-limit`, `limit` |
| `φ` (running penalty), `α` (liquidation cost) | no parameter; the linear `skew` approximates the effect of `φ` |
| `ε±` (mid jump after a market order) | markout of fills at 1 tick (`arena/analysis.py:189`) |
| co-integration factor `ε_t` | the basket spread, e.g. basket − Σ weights × components |

## Traps
- **Typo in the book itself:** Kyle's λ is printed as `λ = 2σ_u/σ` (`algorithmic-and-hft.md:751-755` (p. 50, checked)). Solving the book's own steps (`x* = (v − μ)/(2λ)`, `S = E[v | x + u]`) gives `λ = σ/(2σ_u)` *(computed here)*, the standard Kyle lambda.
- **OCR:** the `F±` integrals of chapter 11 read `u^{ε/κ−1} … u^{−½} u² du` (`algorithmic-and-hft.md:6427-6429` (p. 295)). The PDF has `u^{ρ/κ−1} e^{∓√(2κ/σ²)(θ−ε)u − u²/2}`.
- **OCR:** (10.29) reads `ω(t) = e^{A(T−t)z}`, with z inside the exponent (`algorithmic-and-hft.md:6190` (p. 281)). The stacked vector `ω(t)` starts with `ω(t, q̲)` where the PDF has `ω(t, q̄)` (`algorithmic-and-hft.md:5816` (p. 266)).
- **OCR:** inequality bounds lose their bars: `1_{q<q}` for `1_{q<q̄}`, in (10.9), (10.18) and others.
- **Page numbers:** the printed page numbers are 17 less than the PDF's (printed 248 is PDF p. 265). Cite PDF pages.
- Chapter headings in `meta.json` are OCR'd ("Em pi rica I", "Part 111"); the chapter map below has them fixed.

## Read depth
Chapter map (PDF pages, one-based; markdown lines):

| Ch. | Title | PDF pp. | Lines | Status |
|---|---|---|---|---|
| — | Front matter, preface, how to read | 1–17 | 1–290 | mapped |
| 1 | Electronic Markets and the Limit Order Book | 21–35 | 305–479 | mapped |
| 2 | A Primer on the Microstructure of Financial Markets | 36–55 | 480–832 | **read** (2.1 Grossman–Miller, depth trade-off; 2.2 Kyle; 2.3 Glosten–Milgrom) |
| 3 | Empirical and Statistical Evidence: Prices and Returns (incl. 3.7 empirics of pairs trading) | 56–77 | 833–1301 | mapped |
| 4 | Empirical and Statistical Evidence: Activity and Market Quality | 78–113 | 1302–1929 | mapped |
| 5 | Stochastic Optimal Control and Stopping (Part II) | 117–147 | 1944–2823 | mapped |
| 6 | Optimal Execution with Continuous Trading I (Part III) | 151–174 | 2842–3471 | mapped |
| 7 | Optimal Execution with Continuous Trading II | 175–200 | 3472–4142 | mapped |
| 8 | Optimal Execution with Limit and Market Orders | 201–228 | 4143–4802 | mapped |
| 9 | Targeting Volume | 229–262 | 4803–5722 | mapped |
| 10 | Market Making | 263–289 | 5723–6328 | **read** (10.1–10.4; exercises skipped) |
| 11 | Pairs Trading and Statistical Arbitrage Strategies | 290–311 | 6329–6874 | **read** (11.4's derivation skimmed) |
| 12 | Order Imbalance | 312–331 | 6875–7268 | **read** 12.1–12.2; 12.3–12.4 skimmed |
| A | Stochastic Calculus for Finance | 332–352 | 7269–7580 | mapped |
| — | Bibliography, glossary, index | 353–360 | 7581–7623 | mapped |

Checked against the PDF (page images): Grossman–Miller's `S₁`, the static depth `δ* = 1/κ` (2.3), Glosten–Milgrom half-spreads, Kyle's `x*`, `S` and λ (found the typo), (10.13), (10.17), (10.8)–(10.11), (10.19)–(10.20), (10.22)–(10.27), (11.1)–(11.2) with `F±`, the chapter 11 trigger table (and recomputed), (12.1), Table 12.1. Read but not checked: (11.16), ch. 12's likelihood derivations.

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md), [informed-counterparties](../concepts/informed-counterparties.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md).
