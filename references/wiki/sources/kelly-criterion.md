---
title: Thorp, "The Kelly criterion in blackjack, sports betting, and the stock market" (1997)
type: source
repo: literature_md/kelly-criterion
status: partly-read
updated: 2026-10-12
---

# Thorp, "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market" (10th International Conference on Gambling and Risk Taking, 1997; revised May 1998)

## What it is
Thorp's practitioner survey of the Kelly criterion: bet the fraction of capital that maximises the expected log of wealth. It covers coin tossing, formulas for practitioners, how long "the long run" takes, a continuous-time version for securities, fractional Kelly, a portfolio case study, and Thorp's 28 years of using it. It is the theory behind the 25% Kelly staking in the [Qminers 2025](qminers-hackathon-2025.md) solution. For us the value is not the optimal fraction itself, since the Arena has position limits rather than a bankroll that compounds, but three facts about sizing: size scales with edge over variance, betting more than the optimum costs as much growth as betting less while adding risk, and estimated edges are usually too high.

## Main results
- **Maximising expected wealth means betting everything, which makes ruin almost sure** (`kelly-criterion.md:47` (p. 3)). Kelly instead maximises `g(f) = E log(X_n/X_0)/n` (`kelly-criterion.md:67-71` (p. 4, checked)).
- **Even-money coin, win probability p:** `g(f) = p log(1 + f) + q log(1 − f)`, maximised at **`f* = p − q`**, the edge (`kelly-criterion.md:75` (p. 4, checked)).
- **Theorem 1** (`kelly-criterion.md:85` (p. 5)):
  - `g(f) > 0` makes wealth grow without bound, `g(f) < 0` sends it to zero, and `g(f) = 0` makes it oscillate between both.
  - Kelly's wealth becomes an infinite multiple of any essentially different strategy's, and it reaches a fixed goal fastest, both asymptotically.
- **Overbetting has a cliff.** Above a critical fraction `f_c`, growth is negative and capital goes to zero even with an edge. In Example 2.1 (`kelly-criterion.md:101-103` (p. 6, checked)):
  - `p = .53`, so `f* = .06`, and `f_c ≈ .11973`, about twice `f*`.
  - `g(f*) = .001801` per bet, so doubling the bankroll takes about 385 bets.
- **Uneven payoffs:** winning `b` per unit staked gives `f* = (bp − q)/b` (`kelly-criterion.md:109` (p. 6, checked)). Winning `b` or losing `a` gives **`f* = m/(ab)`** with `m = bp − aq` (`kelly-criterion.md:113` (p. 7, checked)). Edge divided by a product of the payoffs is the discrete form of edge over variance.
- **Drawdowns at full Kelly are large:** the probability of ever falling to a fraction `x` of capital is `x^(2m/s²)` (eq. 3.2, `kelly-criterion.md:219` (p. 10, checked)), which is about `x` at full Kelly. So there is a 1 in 2 chance of ever halving.
- **The long run is long** (`kelly-criterion.md:345` (p. 14), Table 4.2, `kelly-criterion.md:347-351` (p. 15)): with `p = .51` and `f* = .02`, after 10,000 bets Kelly is only 0.5 standard deviations ahead of `f = .01` or `f = .03`. It takes 160,000 bets to be 2 standard deviations ahead.
- **Continuous version** for a security with drift `m`, volatility `s` and riskless rate `r` (eq. 7.3, `kelly-criterion.md:528` (p. 24, checked)):
  - **`f* = (m − r)/s²`**, the excess drift over the variance.
  - `g∞(f) = r + f(m − r) − s²f²/2`, so `g∞(f*) = (m − r)²/2s² + r`, which is the Sharpe ratio squared over two plus `r`.
  - It assumes no jumps, continuous rebalancing and no transaction costs (`kelly-criterion.md:558-560` (p. 26)).
- **Fractional Kelly**, betting `c·f*` with `r = 0` (eq. 7.6, `kelly-criterion.md:550` (p. 25, checked); `kelly-criterion.md:556` (p. 26, checked)):
  - **Growth relative to the maximum is `c(2 − c)`.** Half Kelly keeps 3/4 of the growth; `c = 1.5` also keeps 3/4; `c = 2` keeps none.
  - Volatility relative to Kelly is `c`. So overbetting by a factor gives up as much growth as underbetting by the same factor, and adds risk instead of removing it.
- **Drawdown risk under fractional Kelly** (eq. 7.13, `kelly-criterion.md:686-692` (p. 32, checked)):
  - `P(V/V₀ ≤ x at some time) = x^(2/c − 1)`.
  - The chance of ever losing half is **1/2 at full Kelly and 1/8 at half Kelly**. The chance of doubling before halving is 2/3 and 8/9.
- **Estimated edges are too high** (`kelly-criterion.md:624-628` (p. 29); `kelly-criterion.md:636` (p. 30)):
  - With the true drift half the estimate, betting `1.5f*_e` gives growth −0.75 (ruin), full `f*_e` gives zero growth with wild swings, and half Kelly loses nothing.
  - The estimate `m_e` is likely above the truth `m_t`: markets are non-stationary, systems may be "partly or entirely based on data mining", and "systems that do work attract capital", which pushes their returns down.
  - Lessons: **assume `m_t < m_e` and bet `f < f*_e`** by enough to keep growth positive; **`0.5f*_e ≤ f < f*_e`** protects against that and is likely to cost at most 25% of growth.
- **Many securities** (eq. 8.2, `kelly-criterion.md:781` (p. 36, checked)):
  - **`F* = C⁻¹(M − R)`**, with `C` the covariance matrix and `M − R` the excess drifts. Uncorrelated securities each get `(mᵢ − r)/sᵢ²` (`kelly-criterion.md:783` (p. 37, checked)).
  - Two securities with an exact price ratio make `C` singular, so `C⁻¹` doesn't exist (`kelly-criterion.md:787` (p. 37)).
- **Thorp's record:** his partnership compounded at about 20% a year with a standard deviation of about 6% over 28.5 years, across about 1.25 million bets (`kelly-criterion.md:811` (p. 37–38)). This is his claim.
- **Conclusion:** use Kelly or less, never more, and limit the fraction further when the probabilities are uncertain (`kelly-criterion.md:815` (p. 38)).

## Assumptions against the Arena
- **Kelly maximises the long-run growth of capital that is reinvested.** The Arena scores a fixed number of rounds, weighted 10/20/30/40%, probably by PnL or rank against other teams. PnL is not reinvested, and the position limit, not capital, caps the size. So `f*` has no direct meaning here, and maximising log growth is not maximising rank *(inferred)*.
- **What does carry over** *(inferred)*:
  - **Size scales with edge over variance.** A product or signal with a thin edge and a volatile price deserves less of its position limit than one with a fat edge and a quiet price.
  - **Oversizing is as costly as undersizing and riskier.** The `c(2 − c)` curve is flat near the top, so shading the size down costs little.
  - **Backtest edges are overstated,** by exactly the mechanisms Thorp lists. The grid's best cell is the data-mining case ([validation](../concepts/validation-and-overfitting.md)), and rivals attracted to the same edge are the "capital" that erodes it ([shared market](../concepts/shared-market-and-adversaries.md)). Sizing at a fraction of what the backtest suggests is the hedge.
- **No ruin.** A bot can't go broke in the Arena; negative PnL just ranks low. Kelly's cliff becomes a large loss in one round, not the end of the game. Risk appetite comes from the scoring instead ([risk and protecting a lead](../concepts/risk-and-protecting-a-lead.md)).
- **Independent bets.** Market-making fills are not independent bets: inventory carries price risk from one fill to the next, and adverse selection makes fills correlated with the next move ([informed counterparties](../concepts/informed-counterparties.md)).

## In our notation
| Paper | Ours |
|---|---|
| fraction of capital `f` | position over limit, `plan.net / plan.limit` (`bots/template.py:578`) |
| excess drift `m − r` | expected price move per tick from a signal, or edge per fill (half spread minus adverse selection) |
| variance `s²` | variance of per-tick changes of `mark` in `_timeline.csv` |
| `f* = (m − r)/s²` | a target position proportional to predicted move over variance, capped by `limit` |
| fractional Kelly `c` | a multiplier ≤ 1 on that target, or a `make_size` below the full room (`bots/template.py:46`) |
| `m_e` vs `m_t` | the backtest's PnL per unit risk vs what the round delivers |
| `C⁻¹(M − R)` | sizing correlated products together, not one by one ([many products](../concepts/many-products-architecture.md)) |

## Traps
- **The PDF has no text layer** (Acrobat PDFWriter scan). `pdfpage.py` can only bound the page from Marker's markers and interpolate within them; every page above was confirmed on the page image.
- **OCR slip:** lesson (2) renders `f*_e` as `f_*^*`, losing the subscript `e` (`kelly-criterion.md:636` (p. 30)). The PDF has `0.5f*_e ≤ f < f*_e`.
- The paper writes powers as `x^(…)` with a caret, which Marker kept as `x^\wedge(…)`. That is the paper's notation, not an OCR error.
- `m` changes meaning: the expected gain per unit bet in section 2, the drift in section 7. `s` is volatility in section 7 but `s_ii` is a variance in section 8.

## Read depth
- **Read:** sections 1–4 (coin tossing, formulas, the long run), 7 (securities, fractional Kelly, the remarkable formula), 8(d) (the portfolio formula), 9 (experience) and 10 (conclusion).
- **Not read:** sections 5 (blackjack) and 6 (sports betting), and the case study tables of section 8.
- **Checked against the PDF (page images):** `g(f)`, `f* = p − q`, Example 2.1, `(bp − q)/b`, `m/(ab)`, (3.2), Table 4.2, (7.3), (7.4)–(7.6), `c(2 − c)`, the lessons, (7.13) and its 1/2, 1/8, 2/3 and 8/9, (8.2) and its uncorrelated case. `c(2 − c)` and `m/(ab)` were also derived here.

## Cited by
[risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md).
