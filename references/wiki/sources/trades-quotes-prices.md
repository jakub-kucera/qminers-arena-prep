---
title: Bouchaud, Bonart, Donier & Gould, "Trades, Quotes and Prices" (book excerpt, 2018)
type: source
repo: literature_md/trades-quotes-prices
status: read
updated: 2026-10-13
---

# Bouchaud, Bonart, Donier & Gould, *Trades, Quotes and Prices: Financial Markets Under the Microscope* (Cambridge University Press, 2018; our copy is a 47-page excerpt)

## What it is
The empirical-physics textbook of market microstructure, built on NASDAQ (LOBSTER) data. Our copy stops early in chapter 2: it has the table of contents, the preface, chapter 1 (who trades and why, and the risks of market-making) and chapter 2 up to section 2.1.4 (the random walk, correlated returns, high-frequency noise). The chapters on price impact (11–14), the Kyle model (15), the spread (16) and the profitability of market-making (17) are **not** in the excerpt. What we have gives two tools: the market maker's break-even condition `s/2 > R∞`, and the volatility signature plot, which separates a price's noise from its real moves.

## Main results
**Chapter 1, the risks of market-making:**
- **Information is statistical:** an informed trade is one whose expected profit over some horizon is positive after costs (`trades-quotes-prices.md:430` (p. 31)). Signals are weak: the spread of outcomes is much larger than the mean predicted move (`trades-quotes-prices.md:438` (p. 32)).
- **Testing a strategy takes long:** at 15% volatility and 5% return, about `(15/5)² = 9` years to tell the return from zero at one sigma (`trades-quotes-prices.md:452` (p. 33); `trades-quotes-prices.md:467` (p. 34)).
- **Speculators trade too much,** overestimating their signals and underestimating costs (`trades-quotes-prices.md:444` (p. 32)).
- **Makers take too:** a market maker who sees another quoting an attractive price takes it, so the line between providing and taking liquidity is blurred (`trades-quotes-prices.md:469` (p. 34)).
- **Adverse selection:** binding quotes get picked off by better-informed traders. With imbalanced flow and fixed quotes, a market maker builds a position on the wrong side (`trades-quotes-prices.md:481-489` (p. 34–35)).
- **Price impact, and the market maker's break-even** (eq. 1.9, `trades-quotes-prices.md:497-507` (p. 36, checked)):
  - With trade sign `ε` (+1 buy, −1 sell) and mid `m`, the long-run impact of a trade is **`R∞ = E[ε·(m∞ − m)]`**, which is positive.
  - A market maker with fixed quotes earns `s/2` per leg and loses `R∞` on average, so **net profit per trade is `s/2 − R∞`**. Market making pays only if `s/2 > R∞`.
- **Skewness: market making is selling insurance** (eq. 1.10–1.11, `trades-quotes-prices.md:519-533` (p. 37, checked)):
  - A toy model: with probability `φ` a trade is informed and predicts a jump of `±J`. Then `R∞ = φJ`, and breaking even needs `s = 2φJ`.
  - The gain per trade has variance `φJ²` and skewness `−φ^(−1/2)`. As informed trades get rarer, the average impact gets harder to estimate (relative precision `√φ`) and the skew grows without bound.
- **Liquidity is thin and fragile** (`trades-quotes-prices.md:535-547` (p. 37–38)):
  - The volume at the best quotes is about 10⁻⁴ of market cap, against 0.5% traded a day. Providers show little to limit being picked off, so *revealed* liquidity is small and *latent* liquidity large.
  - Large orders must be split, so supply and demand are digested slowly and "prices cannot be in equilibrium" (`trades-quotes-prices.md:555` (p. 39)).

**Chapter 2, the statistics of price changes:**
- **Bachelier's first law:** with uncorrelated changes, the variogram `V(τ) = E[(p_{t+τ} − p_t)²]` grows linearly, `V(τ) = Dτ` (eq. 2.1, `trades-quotes-prices.md:618-622` (p. 44, checked)).
- **The signature plot** (eq. 2.8–2.9, `trades-quotes-prices.md:670-676` (p. 45, checked)):
  - **`σ²(τ) = V(τ)/(τ p̄²) = σ_r² [1 + 2 Σ_{u=1}^{τ} (1 − u/τ) C_r(u)]`**, the variance per unit time of changes over `τ`, against `τ`.
  - It is flat for a random walk, rises with trends (`C_r > 0`) and falls with mean reversion (`C_r < 0`).
  - With `C_r(u) = ρ^u`, `σ²(∞)/σ²(1) = (1 + ρ)/(1 − ρ)` (eq. 2.10, `trades-quotes-prices.md:686` (p. 46, checked)).
- **Microstructure noise looks like mean reversion** (eq. 2.11–2.13, `trades-quotes-prices.md:692-706` (p. 46–47, checked)):
  - A price observed as the true price plus noise `η` with variance `σ_η²` and correlation time `τ_η` (bid–ask bounce, pricing errors) adds `(2σ_η²/τ)(1 − e^(−τ/τ_η))` to `σ²(τ)`.
  - That term is largest at short lags and vanishes at long ones: short-lag volatility overstates the real one.
- **Real liquid assets have nearly flat signature plots:** the E-mini's falls by only about 20% from 1 second to 20 days (`trades-quotes-prices.md:710` (p. 47)).

## Assumptions against the Arena
- **Measured on Prosperity data (2026-10-12):** the variance per tick of price changes over `τ` ticks, for the mid and the wall mid (largest level on each side), on Prosperity 3 round 1 and Prosperity 2 round 1, all days:

  | Product | Price | τ = 1 | 5 | 50 | 200 | 1000 |
  |---|---|---|---|---|---|---|
  | Kelp | mid | 0.611 | 0.144 | 0.035 | 0.022 | 0.023 |
  | Kelp | wall mid | 0.064 | 0.034 | 0.024 | 0.020 | 0.022 |
  | Starfruit | mid | 2.873 | 0.699 | 0.225 | 0.184 | 0.196 |
  | Starfruit | wall mid | 0.327 | 0.197 | 0.173 | 0.171 | 0.193 |
  | Squid Ink | mid | 3.239 | 2.311 | 2.214 | 1.655 | 1.343 |
  | Squid Ink | wall mid | 2.722 | 2.211 | 2.204 | 1.653 | 1.343 |
  | Resin | mid | 4.461 | 0.893 | 0.089 | 0.022 | 0.005 |
  | Resin | wall mid | 0.247 | 0.049 | 0.005 | 0.001 | 0.000 |

  - **The mid is mostly noise at one tick.** Kelp's mid varies 28 times more per tick at lag 1 than at lag 200; its wall mid only 3 times. That is the book's eq. (2.13) in our data, and the reason the wall mid works as fair value ([fair value](../concepts/fair-value-and-wall-mid.md)).
  - **Squid Ink's wall mid is noisy too,** and its signature keeps falling to lag 1000: it mean-reverts at long horizons as well as at one tick ([drift and regime change](../concepts/drift-and-regime-change.md)).
  - **For sizing, use the long-lag variance,** not the one-tick variance, as `s²` in edge over variance ([risk and sizing](../concepts/risk-and-protecting-a-lead.md)). *(Inferred.)*
  - The script is not in the repo.
- **`R∞` depends on the reference price.** Against the raw mid, Prosperity's market trades look informed; against the wall mid, they are not ([price impact](../concepts/price-impact.md) has the numbers). The book's mid is a fine reference for a liquid stock with a flat signature plot. Prosperity's mid is not.
- **No insiders, but maybe informed bots:** Prosperity's informed traders are bots whose trades can be identified ([informed counterparties](../concepts/informed-counterparties.md)). The toy model's `φ` and `J` are then measurable per counterparty, not hidden.

## In our notation
| Book | Ours |
|---|---|
| `m`, `s` | mid and spread in `_timeline.csv` |
| trade sign `ε` | +1 if a market trade is at or above book `t`'s best ask, −1 at or below the best bid |
| `R∞` | mean of `ε · (wall mid at t + h − wall mid at t)` for large `h` |
| `s/2 − R∞` | a maker's markout per unit at horizon `h` in `arena/analysis.py` |
| `σ²(τ)` | variance of `mark` changes over `τ` ticks, divided by `τ` |
| `η` (microstructure noise) | mid minus wall mid |

## Traps
- **OCR slips:**
  - Eq. (2.12) reads `e^{−τ/η_t}`; the book has `e^{−τ/τ_η}` (`trades-quotes-prices.md:696` (p. 47)).
  - Eq. (2.13) came out as broken plain text (`trades-quotes-prices.md:704` (p. 47)).
  - The covariance line uses `r_t, r_{t'}` where the book has `r_{t'}, r_{t''}` (`trades-quotes-prices.md:652-654` (p. 45)).
  - Eq. (1.3) lost its right-hand side on the first occurrence (`trades-quotes-prices.md:363` (p. 27)), and the skewness symbol `ς` became `S` in (1.11).
- **Page numbers:** the book's printed page is the PDF page minus 20 (PDF p. 36 is printed p. 16). Cite PDF pages.
- **The table of contents is garbled** for parts IV and VI (`trades-quotes-prices.md:145` (p. 11)), and its chapter pages are printed pages. Most chapters it lists are not in the excerpt.
- **The toy model's variance (1.10) leaves out the spread earned,** which the book does on purpose to isolate the jump risk.

## Read depth
- **Read:** everything in the excerpt: preface, chapter 1, chapter 2 to section 2.1.4 (which is cut off mid-sentence).
- **Not in our copy:** chapters 2.2 onward, including the impact chapters 11–14, the Kyle model (15), the spread (16) and market-making profitability (17). The full book is requested in `MANUAL_TODO.md`. When it arrives, this page is rebuilt from it (`SCHEMA.md`, "Replace a document with a fuller copy"), and chapters 11, 16 and 17 are the ones to read first.
- **Checked against the PDF (page images):** eq. (1.9), (2.1), `s/2 − R∞`, (1.10)–(1.11), (2.9), (2.10), (2.12), (2.13). (2.9) and (2.10) were also derived here.

## Cited by
[price-impact](../concepts/price-impact.md), [fair-value-and-wall-mid](../concepts/fair-value-and-wall-mid.md).
