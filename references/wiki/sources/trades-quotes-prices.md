---
title: Bouchaud, Bonart, Donier & Gould, "Trades, Quotes and Prices" (book, 2018)
type: source
repo: literature_md/trades-quotes-prices
status: partly-read
updated: 2026-10-13
---

# Bouchaud, Bonart, Donier & Gould, *Trades, Quotes and Prices: Financial Markets Under the Microscope* (Cambridge University Press, 2018; the full book, 463 PDF pages)

## What it is
The empirical-physics textbook of market microstructure, built on NASDAQ order-book data (LOBSTER, 2015). It treats the order book bottom-up: order flow, queues, the impact of trades, and what that implies for market makers and for execution. Each chapter ends with "Take-Home Messages", which give a reliable summary of every chapter.

The thread that matters for us runs through chapters 1, 11, 16, 17 and 21. **A market maker earns half the spread and loses the long-run impact of the trades it takes the other side of; it profits only while half the spread exceeds that impact.** On NASDAQ, competition holds the two at break-even, and simple market making loses money. In the book's own zero-intelligence model (random order flow, no strategy) the impact stays below half the spread, so market making is easy. Measured on Prosperity data, Prosperity sits firmly in the zero-intelligence case (see "Assumptions against the Arena").

This page replaced the one built on a 47-page excerpt (preface to section 2.1.4) on 2026-10-13. The full copy is a library-access PDF; printed page numbers are the PDF page minus 19.

## Main results
**Part I, how and why prices move (ch. 1–2):**
- **Information is statistical:** an informed trade is one whose expected profit over some horizon is positive after costs (`trades-quotes-prices.md:437` (p. 30)). Signals are weak: the spread of outcomes is much larger than the mean predicted move (`trades-quotes-prices.md:445` (p. 31)), and speculators trade too much (`trades-quotes-prices.md:451` (p. 31)). Telling a 5% return at 15% volatility from zero takes about 9 years (`trades-quotes-prices.md:459` (p. 32)).
- **Adverse selection:** binding quotes get picked off by better-informed traders. With fixed quotes and imbalanced flow, a market maker builds a position on the wrong side (`trades-quotes-prices.md:488-496` (p. 33–34)). Market makers also take liquidity when another maker's quote is attractive (`trades-quotes-prices.md:476` (p. 33)).
- **The break-even:** with trade sign `ε` and mid `m`, the long-run impact of a trade is **`R∞ = E[ε·(m∞ − m)]`**. A maker with fixed quotes nets `s/2 − R∞` per trade, so making pays only if `s/2 > R∞` (eq. 1.9, `trades-quotes-prices.md:506-516` (p. 35, checked)).
- **Market making is selling insurance:** if a share `φ` of trades predicts a jump `J`, then `R∞ = φJ`, the break-even spread is `2φJ`, and the gain per trade has variance `φJ²` and skewness `−φ^(−1/2)` (eq. 1.10–1.11, `trades-quotes-prices.md:528-540` (p. 36, checked)).
- **Revealed liquidity is thin, latent liquidity large;** large orders are split, so prices are never in equilibrium (`trades-quotes-prices.md:552-564` (p. 37–38)).
- **The signature plot** `σ²(τ) = σ_r²[1 + 2 Σ_{u=1}^{τ}(1 − u/τ)C_r(u)]` is flat for a random walk and falls with mean reversion (eq. 2.9, `trades-quotes-prices.md:679-685` (p. 44, checked)). With `C_r(u) = ρ^u`, `σ²(∞)/σ²(1) = (1 + ρ)/(1 − ρ)` (eq. 2.10, `trades-quotes-prices.md:695` (p. 45, checked)).
- **Noise that reverts adds** `(2σ_η²/τ)(1 − e^(−τ/τ_η))` to `σ²(τ)`, largest at short lags (eq. 2.12–2.13, `trades-quotes-prices.md:701-713` (p. 45–46, checked)). Liquid markets have nearly flat signature plots (`trades-quotes-prices.md:719` (p. 46)).
- **Heavy tails and bursts:** return tails are power laws with exponent about 3 in every market (`trades-quotes-prices.md:745` (p. 48)). Jumps above 4σ make up about 30% of the variance, many without any news (`trades-quotes-prices.md:823` (p. 52)).
- **Why prices move:** most large moves have no identifiable news (the excess-volatility puzzle, `trades-quotes-prices.md:839` (p. 53)). Signature plots are flat because fast strategies "iron out all irregularities" (`trades-quotes-prices.md:849` (p. 54)), which makes prices statistically efficient without being fundamentally efficient (`trades-quotes-prices.md:853` (p. 54)).

**Part II, order books (ch. 3–4):**
- **Priority:** price-time is by far the most common; pro-rata rewards posting more than you want to trade (`trades-quotes-prices.md:1125-1127` (p. 73)). Iceberg orders hide about 30% of book volume on Euronext (`trades-quotes-prices.md:1138` (p. 74)).
- **Large- and small-tick stocks behave differently:**
  - *Large-tick* stocks have a spread close to one tick; *small-tick* stocks have a spread of many ticks (`trades-quotes-prices.md:1183` (p. 77)).
  - The mean spread is about 0.001 × price unless the tick floors it (`trades-quotes-prices.md:1474` (p. 89)).
  - The volume at the best quotes is about 1% of daily volume for small ticks and up to 10% for large ticks (`trades-quotes-prices.md:1482` (p. 90)).
  - Market orders take under 10% of the best queue on large-tick stocks and more than half on small-tick ones (`trades-quotes-prices.md:1486` (p. 90)).

**Part III, order-book models (ch. 5–8):**
- **Queues as Poisson birth–death processes,** in which long queues need growth and shrink rates nearly equal (`trades-quotes-prices.md:2131` (p. 118)). Large sweeping market orders matter for the fit (`trades-quotes-prices.md:2503` (p. 135)).
- **The race to the bottom** (ch. 7): with the spread at one tick, the price moves only when a best queue empties (`trades-quotes-prices.md:2535` (p. 137)).
  - The queue imbalance `I = V_b/(V_b + V_a)` (eq. 7.1, `trades-quotes-prices.md:2558` (p. 138, unchecked)) strongly predicts which queue empties first: "the worst kept secret of high-frequency traders" (`trades-quotes-prices.md:2568-2576` (p. 139)).
  - Independent diffusive queues give `p₊(I) = (2/π)·arctan(I/(1 − I))` (eq. 7.6, `trades-quotes-prices.md:2627` (p. 141, checked)), which has the wrong concavity. Self-stabilising queues fit better (`trades-quotes-prices.md:2741` (p. 145)).
  - After a race, the emptied level is refilled either by the same side (the mid reverts) or by the other side (the price moves a tick) (`trades-quotes-prices.md:2829-2830` (p. 149)).
- **The Santa Fe zero-intelligence model** (ch. 8) predicts the mean spread well (`trades-quotes-prices.md:3324` (p. 175)).
  - Its impact is constant in lag, `R(τ) ≈ P(V_best = 1) × ½⟨first gap⟩` (eq. 8.8, `trades-quotes-prices.md:3094` (p. 166, unchecked)).
  - Because the first gap is smaller than the spread, the long-run impact stays below half the spread, and **market making is profitable in it**. The authors note this is absent from real markets, where strategic agents remove it (`trades-quotes-prices.md:3098` (p. 166)).

**Part IV, clustering and correlations (ch. 9–10):**
- **Self-excitation:** Hawkes fits put the feedback close to its critical value of 1 (`trades-quotes-prices.md:3913` (p. 203)).
- **Market-order signs have long memory:** `C(ℓ) ≈ c∞/ℓ^γ` with `γ ≈ 0.5` (`trades-quotes-prices.md:3967` (p. 206, unchecked)), so even `C(10000) ≈ 0.005` (`trades-quotes-prices.md:3979` (p. 207)).
  - After a price-changing market order on a large-tick stock, the next order tends to go the other way (`trades-quotes-prices.md:4017` (p. 209)).
  - The variance of order imbalance over a window of N trades shrinks only as N to the power −γ, which keeps market makers' inventories unbalanced (`trades-quotes-prices.md:4035` (p. 211)).
  - With permanent impact, persistent signs would make prices trend: the "efficiency paradox", which liquidity providers resolve (`trades-quotes-prices.md:4045` (p. 212)).
  - The main cause is investors splitting large orders, not herding (`trades-quotes-prices.md:4222` (p. 221)).

**Part V, price impact (ch. 11–12):**
- **The response function:**
  - `R(1) = ⟨ε_t·(m_{t+1} − m_t)⟩` in market-order time (eq. 11.5, `trades-quotes-prices.md:4342` (p. 232, checked)).
  - For small-tick stocks `R(1)` is proportional to the spread (`trades-quotes-prices.md:4369` (p. 233)).
  - `R(ℓ)` rises to an `R∞` 2–5 times `R(1)`, because signs persist (`trades-quotes-prices.md:4388` (p. 234)).
  - For large-tick stocks, an imbalance-weighted reference price would serve better than the mid (footnote 6, `trades-quotes-prices.md:4350` (p. 232)).
- **Volume barely matters per trade:** `R(υ, 1) ≈ A·(υ/V̄_best)^ζ·⟨s⟩` with `ζ` 0 to 0.3 (eq. 11.7, `trades-quotes-prices.md:4408` (p. 236, unchecked)). That is mostly *selective liquidity taking*: large orders arrive when the opposite queue is large (`trades-quotes-prices.md:4432` (p. 237)).
- **"The most likely outcome has the smallest impact":** a buy after a buy moves the price less than a buy after a sell, which keeps prices unpredictable (`trades-quotes-prices.md:4489-4495` (p. 240)).
- **Aggregate impact over a window** is linear for small imbalances and saturates for large ones (eq. 11.11, `trades-quotes-prices.md:4533` (p. 242, checked)). Kyle's λ falls with the window, roughly as its −0.25 power (`trades-quotes-prices.md:4547` (p. 243)).
- **Reaction dominates prediction at short horizons:** random and informed trades have the same short-term impact (`trades-quotes-prices.md:4553` (p. 243)).
- **The square-root law** for large orders split over time: `I_peak ≈ Y·σ_T·(Q/V_T)^δ` with `Y ≈ 0.5` and `δ` 0.4–0.7 (eq. 12.6, `trades-quotes-prices.md:4726` (p. 253, checked)). Executing 1% of daily volume moves the price by about 10% of its daily volatility (`trades-quotes-prices.md:4750` (p. 255)). It holds between "larger than the best queue" and about 10% of volume. Below that, impact is linear; when executed faster than the book refills, it is convex (`trades-quotes-prices.md:4789-4793` (p. 257)).

**Part VI, propagator models (ch. 13–14):**
- **The propagator:** `m_t = m_{t₀} + Σ G(t − n)·ε_n + Σ ξ_n` (eq. 13.7, `trades-quotes-prices.md:4989` (p. 271, unchecked)). Impact must decay for persistent signs to leave prices diffusive (`trades-quotes-prices.md:5430` (p. 287)).
- **Generalised versions** split market orders by whether they move the price, or include every book event (`trades-quotes-prices.md:5757` (p. 304)).

**Part VII, adverse selection and liquidity provision (ch. 15–17):**
- **Kyle:** `Λ = σ_F/(2Σ_V)` (eq. 15.7, `trades-quotes-prices.md:5868` (p. 312, checked)). This independently confirms that [Cartea et al.](algorithmic-and-hft.md) print λ inverted. The empirical `Λ(T)` decays with the window, unlike in the model (`trades-quotes-prices.md:5943` (p. 315)).
- **Glosten–Milgrom break-even quotes** (eq. 16.1, `trades-quotes-prices.md:5995` (p. 319, checked)):
  - The ask is the expected value *given a buy*, and the bid *given a sell*.
  - With a share `φ` of informed traders, the spread solves eq. 16.5 (`trades-quotes-prices.md:6033` (p. 320, checked)), and `s ≈ 2φσ` for small `φ` (eq. 16.6, `trades-quotes-prices.md:6041` (p. 321, checked)).
  - Real spreads are 1–10% of daily volatility, so the informed share must be small (`trades-quotes-prices.md:6047` (p. 321)), about 1% for a one-day horizon (`trades-quotes-prices.md:6388` (p. 334)).
  - When uninformed traders are too few, no break-even spread exists and the market breaks down (`trades-quotes-prices.md:6077` (p. 322)).
  - The spread narrows as trades reveal information (`trades-quotes-prices.md:6108` (p. 324)). For large orders, two-thirds of the peak impact should remain permanent (`trades-quotes-prices.md:6213` (p. 327)).
- **The MRR model** (`trades-quotes-prices.md:6241` (p. 328, unchecked)): the traded price moves by `G*` × the sign *surprise*.
  - It predicts **`R(ℓ) = (s/2)(1 − C(ℓ))`** (eq. 16.22, `trades-quotes-prices.md:6277` (p. 329, checked)), so `R∞ = s/2`: "market-making ceases to be profitable when half the bid–ask spread only compensates the long-term impact" (`trades-quotes-prices.md:6283` (p. 329)).
  - Volatility per trade: **`σ̃²∞ = ((1 − C(1)²)/4)·s² + Σ²`** (eq. 16.23, `trades-quotes-prices.md:6303` (p. 330, checked)).
  - Across 120 NASDAQ stocks the MRR relation between spread, lag-1 impact and sign correlation holds well: the fastest market makers break even (`trades-quotes-prices.md:6358` (p. 332)). Locally, spreads widen too little when impact rises and are too wide in quiet periods (`trades-quotes-prices.md:6360` (p. 332)).
  - Volatility per trade is proportional to the spread (`trades-quotes-prices.md:6404` (p. 336)).
- **The profitability of market making** (ch. 17):
  - With fair prices, the next trade at the ask and the next at the bid have the same expected price (`trades-quotes-prices.md:6440` (p. 338)). On large-tick stocks, makers compete for queue priority, not spread (`trades-quotes-prices.md:6448` (p. 339)).
  - **Long-run gain of an always-quoting maker:** `E[G_T] ≈ T·υ₀·E[θ]·(E[s]/2 + ϖ − R∞)` (eq. 17.3, `trades-quotes-prices.md:6498` (p. 341, checked)), with `θ` the fill indicator and `ϖ` a fee or rebate.
  - **"Market-making is easy when prices mean-revert but difficult when prices trend"** (`trades-quotes-prices.md:6500` (p. 341)).
  - **Inventory control through size:** quote `υ_t(ε) = υ₀·max(1 + κψ_{t−1}ε, 0)`, so more size on the side that reduces the position (eq. 17.4, `trades-quotes-prices.md:6514` (p. 342, checked)).
  - **Profit per unit,** eq. 17.12 (`trades-quotes-prices.md:6568` (p. 344, checked)), has two limits:
    - *slow* market making (loose inventory control): `E[s]/2 − R∞` (eq. 17.13);
    - *fast* market making (inventory back to flat after each trade): `(E[s]/2)(1 − C(1)) − R(1)` (eq. 17.14);
    - the break-even spread of the fast maker is `2R(1)/(1 − C(1))` (eq. 17.15, `trades-quotes-prices.md:6599-6609` (p. 345, checked)).
  - **On NASDAQ this simple strategy loses** about 0.10 of the spread per trade before rebates (`trades-quotes-prices.md:6619` (p. 346)). The phase diagram of when slow and fast making pay is Figure 17.2 (`trades-quotes-prices.md:6621` (p. 346)).
  - **Large ticks:** a randomly placed order suffers more adverse selection than a top-of-queue order, because it fills mainly on large, informed sweeps (eq. 17.16, `trades-quotes-prices.md:6643` (p. 347, unchecked)). Top priority earns about 0.2 tick per trade with the rebate (`trades-quotes-prices.md:6663` (p. 348)).
  - Simple market making with inventory control yields negative profits; smarter makers with fast signals "eke out a small profit" (`trades-quotes-prices.md:6679` (p. 349)).

**Part VIII, meso-scale dynamics (ch. 18–20):**
- **Latent liquidity:** most liquidity is latent; a V-shaped latent book gives the square-root law for fast execution and a decaying propagator for slow (`trades-quotes-prices.md:7023` (p. 371), `trades-quotes-prices.md:7254` (p. 383)).
- **Order-driven prices:** traders predict each other more than fundamentals. Arbitrage removes the predictability it exploits, so markets can be statistically efficient while wrong (`trades-quotes-prices.md:7470-7476` (p. 395)).

**Part IX, practical consequences (ch. 21–22):**
- **Market and limit orders cost about the same on average;** otherwise order flow shifts until they do (`trades-quotes-prices.md:7773` (p. 413)).
- **The martingale argument** (eq. 21.17, `trades-quotes-prices.md:7796` (p. 414, unchecked)): a limit order's better price is offset by the moves it misses. "The attractiveness of limit orders... is therefore an optical illusion – unless one has some information" (`trades-quotes-prices.md:7810` (p. 415)).
- **The rule of thumb:** a limit order's cost is `φ_exec·d·ρ`, with `ρ` the return autocorrelation, so "trending is detrimental and mean-reversion is favourable" (eq. 21.18, `trades-quotes-prices.md:7820-7822` (p. 415, checked)). A larger limit order costs its own impact (`trades-quotes-prices.md:7840` (p. 416)).
- **The value of queue position** (`trades-quotes-prices.md:7868` (p. 417, unchecked)):
  - The expected gain falls with the volume ahead `h`, down to a critical position `h_c` (eq. 21.24, `trades-quotes-prices.md:7930` (p. 420, checked)).
  - With NASDAQ numbers `h_c ≈ 0.5` lot, so only the very front of the queue pays (`trades-quotes-prices.md:7934` (p. 420)).
- **Backtests with phantom orders are "a bit dodgy":** the impact the added orders would have had is about as large as the effects being studied (`trades-quotes-prices.md:7944` (p. 421)).
- **Trading on a signal:** trade fastest at first, and spend a time that grows with the square root of the size (eq. 21.12, `trades-quotes-prices.md:7705` (p. 411, unchecked)).
- **Fairness and stability:** circuit breakers (`trades-quotes-prices.md:8104` (p. 434)). Modern market makers react alike to the same risk signals, so liquidity vanishes when needed most (`trades-quotes-prices.md:8144` (p. 437)).
- **Appendix A.5:** a market maker whose position is only −1, 0 or +1 is long or short a share `2/(3 − C(1))` of the time (eq. A.45, `trades-quotes-prices.md:8551` (p. 451, unchecked)).

## Assumptions against the Arena
- **NASDAQ stocks in 2015:** competitive high-frequency market makers, rebates of about 0.25 tick, queues hundreds of lots long. Prosperity is a few programmed bots with no fees. The book's NASDAQ conclusion, that simple market making loses, rests on that competition (`trades-quotes-prices.md:6679` (p. 349)). Its zero-intelligence model, where market making is easy, rests on random flow (`trades-quotes-prices.md:3098` (p. 166)).
- **Measured on Prosperity 3 round 1 (2026-10-13), all three days.** The market trades of the template's backtest, classified against their own tick's book (`analysis.trade_impact`'s rules), with the book's break-even terms. Here `s` is the mean spread, `C(1)` the sign correlation of consecutive trades, and `R(1)` and `R(50)` the signed move after 1 and 50 ticks:

  | Product | `s` | `C(1)` | vs | `R(1)` | `R(50)` | slow: `s/2 − R(50)` | fast: `(s/2)(1 − C(1)) − R(1)` |
  |---|---|---|---|---|---|---|---|
  | Kelp | 2.32 | 0.13 | mid | 0.28 | 0.27 | 0.89 | 0.73 |
  | Kelp | | | wall mid | 0.01 | −0.01 | 1.17 | 1.01 |
  | Resin | 5.16 | 0.09 | mid | 1.27 | 1.23 | 1.36 | 1.08 |
  | Resin | | | wall mid | 0.09 | 0.07 | 2.51 | 2.26 |
  | Squid Ink | 2.29 | 0.12 | mid | 0.29 | 0.24 | 0.90 | 0.72 |
  | Squid Ink | | | wall mid | 0.02 | −0.02 | 1.16 | 0.99 |

  - **Both margins are large and positive:** 0.3–0.5 of the spread per unit. On NASDAQ the same strategy loses about 0.1 of the spread. By the book's own criterion, Prosperity is the zero-intelligence case where market making is easy.
  - **Trade signs barely persist:** `C(1)` is 0.09–0.13, against 0.37–0.93 on NASDAQ (Table 11.2, `trades-quotes-prices.md:4489` (p. 240)). Consistent with that, `R(50)` is about `R(1)`, not the 2–5 times the book finds.
  - **The mid mean-reverts at one tick** (lag-1 autocorrelation −0.48 for Kelp, [Gould et al.](limit-order-books.md)), which the book's rule (eq. 21.18) says favours resting orders.
  - The script is not in the repo; `arena.analysis` has the impact table but not `C(1)`. Times are ticks, not market-order counts.
- **If the Arena is shared,** other teams compete for the same spread. The book's argument then predicts the margin shrinks toward break-even, as competition enforces it on NASDAQ (`trades-quotes-prices.md:6358` (p. 332)) *(inferred)*.
- **Tick size:** Prosperity's spreads in P3 round 1 are 2–5 ticks, between the book's large-tick (one tick) and small-tick (many ticks) regimes. Queue priority should matter less than on NASDAQ's large-tick stocks, which fits Leo-Hawking's finding of no queue in Prosperity ([queue position](../concepts/queue-position-and-fills.md)) *(inferred)*.
- **Our backtester adds phantom orders to recorded data,** the case the book calls "a bit dodgy" (`trades-quotes-prices.md:7944` (p. 421)). In Prosperity the bots' trades leave no lasting move, so the error is likely small there. In a reactive Arena market it might not be ([price impact](../concepts/price-impact.md)) *(inferred)*.

## In our notation
| Book | Ours |
|---|---|
| trade sign `ε_t` | +1 for a market trade at or above book `t`'s best ask, −1 at or below the best bid (`arena/analysis.py` `trade_impact`) |
| response `R(ℓ)`, `R∞` | `trade_impact`'s move at `h` ticks (not market-order time) against the mark; `h = 50` as `R∞` |
| sign correlation `C(ℓ)` | the correlation of consecutive classified trade signs; not in `arena.analysis` yet |
| spread `s`, tick `ϑ` | `best_ask − best_bid` in `_timeline.csv`; 1 price unit |
| fee or rebate `ϖ` | 0 in Prosperity |
| fill indicator `θ` | whether our quote filled |
| price skew (shift both quotes) | `skew` in `bots/template.py` |
| size skew `υ₀·max(1 + κψε, 0)` (eq. 17.4) | not in the template; `make_size` is symmetric |
| queue imbalance `I` (eq. 7.1) | Gould & Bonart's `I`; `ρ = 2I − 1` ([book imbalance](../concepts/book-imbalance-and-micro-price.md)) |
| imbalance-weighted reference `p₊(I)·a + p₋(I)·b` | a micro-price-like fair value |
| metaorder | a large position built over many ticks |

## Traps
- **OCR slips:**
  - (1.11) lost the "0 −" in its numerator, and the skewness symbol `ς` became `σ` (`trades-quotes-prices.md:538` (p. 36)).
  - (2.12) has `η_l` and `e^{−τ/η_l}` where the book has `η_t` and `e^{−τ/τ_η}` (`trades-quotes-prices.md:705` (p. 46)).
  - (11.11) divides by `V_D T^χ`; the book has `T^ϰ` (`trades-quotes-prices.md:4533` (p. 242)).
  - (16.22) has `S/2` for `s/2` (`trades-quotes-prices.md:6277` (p. 329)).
  - (21.18) is garbled into `E[Δ(d,ρ) = φ d ρ.] =`; the book has `E[Δ](d, ρ) = φ_exec·d·ρ` (`trades-quotes-prices.md:7820` (p. 415)).
  - (17.4) has `ν` for the volume `υ` (`trades-quotes-prices.md:6514` (p. 342)), and (11.9) lost its conditioning bar (`trades-quotes-prices.md:4489` (p. 240)).
- **Pages:**
  - Marker found no page anchors. `pdfpage.py` bounds pages from figures and headings, and has no confident match for chapter 12's first line.
  - The table of contents is garbled and gives printed pages; PDF = printed + 19.
  - The book's own figures for NASDAQ are in dollar cents and market-order time; ours are in price units and ticks.
- **Decorative images:** the 16 part-opener and logo images were removed after conversion.

## Read depth
Chapter map (PDF page of each chapter's first page; markdown lines):

| Ch. | Title | From PDF p. | Lines | Status |
|---|---|---|---|---|
| — | Front matter, contents, preface | 1 | 1–307 | read (preface) |
| 1 | The Ecology of Financial Markets | 24 | 308–596 | **read** |
| 2 | The Statistics of Price Changes | 41 | 597–907 | **read** to 2.1.4; 2.2–2.4 read for their claims |
| 3 | Limit Order Books | 63 | 921–1174 | 3.2 read; 3.1 mapped |
| 4 | Empirical Properties of Limit Order Books | 77 | 1175–1522 | 4.8 and the take-home messages read |
| 5 | Single-Queue Dynamics: Simple Models | 97 | 1540–2160 | take-home messages only |
| 6 | Single-Queue Dynamics for Large-Tick Stocks | 120 | 2161–2520 | take-home messages only |
| 7 | Joint-Queue Dynamics for Large-Tick Stocks | 136 | 2521–2869 | **read** |
| 8 | The Santa Fe Model for Limit Order Books | 153 | 2870–3353 | 8.5.4 and the take-home messages read |
| 9 | Time Clustering and Hawkes Processes | 182 | 3371–3952 | take-home messages only |
| 10 | Long-Range Persistence of Order Flow | 206 | 3953–4241 | **read** to 10.4.3; 10.5 skimmed |
| 11 | The Impact of Market Orders | 227 | 4257–4597 | **read** |
| 12 | The Impact of Metaorders | 248 | 4598–4913 | 12.3 read; the rest skimmed |
| 13 | The Propagator Model | 268 | 4927–5456 | 13.1–13.2 skimmed; take-home messages |
| 14 | Generalised Propagator Models | 289 | 5457–5781 | take-home messages only |
| 15 | The Kyle Model | 309 | 5795–5962 | **read** |
| 16 | The Determinants of the Bid–Ask Spread | 317 | 5963–6425 | **read** |
| 17 | The Profitability of Market-Making | 338 | 6426–6697 | **read** |
| 18 | Latent Liquidity and Walrasian Auctions | 356 | 6715–7037 | take-home messages only |
| 19 | Impact Dynamics in a Continuous-Time Double Auction | 373 | 7038–7281 | take-home messages only |
| 20 | The Information Content of Prices | 385 | 7282–7515 | take-home messages only |
| 21 | Optimal Execution | 403 | 7531–7985 | **read** (21.1–21.2 skimmed) |
| 22 | Market Fairness and Stability | 425 | 7986–8181 | 22.2 skimmed, 22.3 read |
| A | Appendix (data, Laplace, propagator, TIM/HDIM, an alternative market maker, symbols) | 441 | 8182–8678 | A.5 read |
| — | Index | 460 | 8679–8698 | mapped |

- **Checked against the PDF (page images):** (1.9), `s/2 − R∞`, (1.10)–(1.11), (2.9), (2.10), (2.12), (2.13), (7.6), (11.5), (11.11), (12.6), (15.7), (16.1), (16.5), (16.6), (16.22), (16.23), (17.3), (17.4), (17.12)–(17.15), (21.18), (21.24).
- **Marked unchecked:** (8.8), (11.7), (13.7), (16.18), (17.16), (21.12), (21.17), the queue-value recursion (21.20) and (A.45).

## Cited by
[price-impact](../concepts/price-impact.md), [fair-value-and-wall-mid](../concepts/fair-value-and-wall-mid.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [queue-position-and-fills](../concepts/queue-position-and-fills.md), [book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md), [contradictions](../contradictions.md).
