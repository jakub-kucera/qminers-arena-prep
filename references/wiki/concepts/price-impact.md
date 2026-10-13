---
title: Price impact
type: concept
updated: 2026-10-13
---

# Price impact

## Summary
Price impact is how far the price moves after a trade, in the trade's direction. It matters to us in three ways: what our own takes cost, how much adverse selection our quotes suffer (the `R∞` in a market maker's net edge `s/2 − R∞`), and whether other traders' trades predict the price. The literature agrees that impact is positive, partly transitory and partly permanent, and concave in size; it disagrees on the exact shape. On Prosperity data, measured against the wall mid, the bots' market trades carry almost no permanent impact. Against the raw mid they seem to, but that is a selection effect: trades hit quotes that sit off the wall. Our backtester models no lasting impact of our own trades. The Arena might.

## What the sources say
**What it is:**
- **Instantaneous and permanent** ([Gould et al.](../sources/limit-order-books.md), `literature_md/limit-order-books/limit-order-books.md:520-523` (p. 15)): the instantaneous part is the volume a trade removes; the permanent part is how others change their behaviour afterwards. The permanent part can't be measured exactly, since the market without the trade is never observed (`literature_md/limit-order-books/limit-order-books.md:549` (p. 15)).
- **The same split in the spread** ([Harris](../sources/harris-trading-and-exchanges.md), `literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:6984-6994` (p. 312–313)): a transaction-cost component that reverts (bid–ask bounce) and an adverse-selection component that does not.
- **The market maker's break-even** ([Bouchaud et al.](../sources/trades-quotes-prices.md), `literature_md/trades-quotes-prices/trades-quotes-prices.md:510-516` (p. 35, checked)): with `R∞ = E[ε·(m∞ − m)]` the long-run impact per trade, a maker with fixed quotes nets `s/2 − R∞` per trade. Making pays only while `s/2 > R∞`.
- **Rare informed trades hide in the average** (`literature_md/trades-quotes-prices/trades-quotes-prices.md:528-540` (p. 36, checked)): if a share `φ` of trades predicts a jump `J`, then `R∞ = φJ` and the maker's gain per trade has skewness `−φ^(−1/2)`. Small `φ` means a small average impact and a fat left tail: market making is selling insurance.

**Its shape:**
- **Concave in the size of one market order** (`literature_md/limit-order-books/limit-order-books.md:551-553` (p. 15, checked); `literature_md/limit-order-books/limit-order-books.md:572-580` (p. 16)): power laws `|ω|^α` with α from 0.2 to 0.7 by study, or a logarithm.
- **Linear in order-flow imbalance** ([Cont et al.](../sources/price-impact-of-book-events.md), `literature_md/price-impact-of-book-events/price-impact-of-book-events.md:114-129` (p. 6, checked)): with every level `D` deep, `ΔP = OFI/(2D)`. Trades add nothing once OFI is known, and the square-root impact of volume is an aggregation artefact (`literature_md/price-impact-of-book-events/price-impact-of-book-events.md:449-451` (p. 16–17)).
- **Over a window, concave at short horizons and linear at long ones:** impact against trade imbalance has exponent about 1/3 at 5 minutes and 1 at 195 minutes (`literature_md/limit-order-books/limit-order-books.md:588` (p. 16)).
- **Square-root for large orders split over time:** the queue-reactive model reproduces it in simulation ([Huang et al.](../sources/queue-reactive-model.md), `literature_md/queue-reactive-model/queue-reactive-model.md:327-381` (p. 18–22)). Bouchaud's chapters on it are not in our excerpt.
- **Market orders move the book about four times as much as limit orders of the same size,** and limit orders at the best have a permanent impact (`literature_md/limit-order-books/limit-order-books.md:596` (p. 17)).

**In the models:**
- **Kyle:** price moves linearly with net order flow, `S = μ + λ(x + u)` ([Cartea et al., book](../sources/algorithmic-and-hft.md), `literature_md/algorithmic-and-hft/algorithmic-and-hft.md:725-755` (p. 49–50, checked)). The book prints λ inverted; the standard value is `σ/(2σ_u)`, which [Bouchaud et al.](../sources/trades-quotes-prices.md) derive independently as `Λ = σ_F/(2Σ_V)` (`literature_md/trades-quotes-prices/trades-quotes-prices.md:5868` (p. 312, checked)).
- **Grossman–Miller:** the discount a liquidity trader pays to sell `i` units is `γσ²·i/(n + 1)`, shrinking with the number of competing makers `n` (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:575-579` (p. 41, checked)).
- **Guéant et al.:** each fill shifts the reference price by `ξ` against the maker, which widens both quotes by `ξ/2` ([dealing with inventory risk](../sources/dealing-with-inventory-risk.md), `literature_md/dealing-with-inventory-risk/dealing-with-inventory-risk.md:294-298` (p. 14, checked)).
- **Asymmetric impact invites manipulation** (Harris, `literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:6369-6381` (p. 283–284)): if buys move a price more than sells, a bluffer buys first and sells later. Quoting that moves equally per unit in both directions can't be bluffed.
- **On NASDAQ the response grows with the lag:** `R(ℓ)` rises to an `R∞` 2–5 times `R(1)` because trade signs persist (`literature_md/trades-quotes-prices/trades-quotes-prices.md:4388` (p. 234)). And "the most likely outcome has the smallest impact": a buy after a buy moves the price less than a buy after a sell (`literature_md/trades-quotes-prices/trades-quotes-prices.md:4495` (p. 240)). On Prosperity data `R(50)` is about `R(1)`, and consecutive trade signs barely correlate ([Bouchaud et al. source page](../sources/trades-quotes-prices.md)).
- **The square-root law has a narrow domain:** from the size of the best queue up to about 10% of the volume. Below it impact is linear; executed faster than the book refills, it is convex (`literature_md/trades-quotes-prices/trades-quotes-prices.md:4789-4793` (p. 257)). Our takes are smaller than a best queue, so the square-root law doesn't apply to them.
- **Short-term impact is reaction, not prediction:** random trades and informed ones have the same short-term impact (`literature_md/trades-quotes-prices/trades-quotes-prices.md:4553` (p. 243)).

**Measured on Prosperity data (2026-10-12).** For each market trade at tick `t`, the sign `ε` is +1 if it printed at or above book `t`'s best ask and −1 at or below the best bid; the 2% that print inside the spread are left out. Book `t` is the book those trades arrived to: 96–97% of them print at one of its prices ([Gould et al.](../sources/limit-order-books.md), "Assumptions against the Arena"). The table gives the taker's edge per unit against book `t`'s wall mid (negative means the taker paid), and the mean of `ε × (price at t + h − price at t)` for the mid and the wall mid:

| Data | Product | Taker's edge | Mid, h = 1 | Mid, h = 50 | Wall mid, h = 1 | Wall mid, h = 50 |
|---|---|---|---|---|---|---|
| P3 r1 | Kelp | −0.93 | +0.28 | +0.27 | +0.01 | −0.01 |
| P3 r1 | Resin | −1.49 | +1.27 | +1.23 | +0.09 | +0.07 |
| P3 r1 | Squid Ink | −0.93 | +0.29 | +0.24 | +0.02 | −0.02 |
| P3 r2 | Croissants | −0.60 | +0.01 | +0.02 | 0.00 | +0.01 |
| P3 r2 | Djembes | −0.63 | +0.01 | −0.07 | 0.00 | −0.07 |
| P3 r2 | Jams | −0.79 | +0.02 | +0.06 | +0.02 | +0.07 |
| P3 r2 | Picnic Basket 1 | −2.23 | +1.44 | +2.11 | +0.12 | +0.79 |
| P3 r2 | Picnic Basket 2 | −1.61 | +0.58 | +1.07 | +0.02 | +0.49 |
| P3 r2 | Squid Ink | −0.90 | +0.29 | +0.45 | +0.02 | +0.19 |
| P2 r1 | Starfruit | −1.33 | +0.91 | +0.86 | +0.05 | 0.00 |

- **Against the wall mid, `R∞` is close to zero** for every product except the two baskets (0.5–0.8 at 50 ticks). The bots' takers pay 0.6–2.2 ticks per unit and the price doesn't follow them, so a maker at the wall mid keeps almost all of it.
- **Against the mid, the same trades look informed** in Kelp, Resin, Squid Ink, Starfruit and the baskets, with a 0.3–1.4 tick "impact" at one tick. It comes at once and doesn't decay, which is not impact but selection. Trades hit quotes that sit off the wall (a bot's ask stepping inside the spread pulls the mid down), and the mid returns to the wall once that quote is gone.
- **An average near zero doesn't exclude rare informed traders.** Olivia's trades in Prosperity 3 were few ([informed counterparties](informed-counterparties.md)); Bouchaud's toy model says exactly that such flow barely moves the mean.
- **Reproduce it** with `arena.analysis.trade_impact`: backtest any bot with `--out`, then pass every day's run to pool them (`uv run python -m arena.analysis <out>` prints it per day and pooled). It reproduces the P3 round 1 rows above exactly.

## Where they disagree
- **Whether trades carry information at all:** theory says yes on average, Prosperity's bots mostly don't ([contradictions](../contradictions.md), rows 12–13).
- **The shape of impact:** power law, logarithm, linear in OFI or square root. They describe different things: one market order, the net flow over an interval, and a large order split over time. Cont et al. argue the square root of *volume* is an aggregation artefact; the square-root law for *split orders* is a separate claim.
- **The reference price:** the literature measures impact against the mid, which works for liquid stocks whose mid is close to a random walk. On Prosperity the mid is mostly noise at one tick ([fair value](fair-value-and-wall-mid.md)), and the same trades show impact against the mid and none against the wall mid.

## What it means for our code
- **Measure fills against the wall mid.** `mark` is the CSV's mid in the Prosperity format (`arena/formats/prosperity.py:125`). On Kelp, Resin or Starfruit, markouts against it mix the mid's noise and the selection effect above into what is meant to be adverse selection. `arena.analysis` takes `reference="wall_mid"` (CLI `--reference wall_mid`) for the fill edge, markouts and the PnL split. The split shows the size of the effect: on P3 round 1, day −1, Resin's takes look like a 6,048 loss against the mark and earn 6,272 against the wall mid.
- **Our own takes have no lasting impact in the backtester:** the next tick's book is the recorded one. Prosperity teams listed market impact and the bots' reaction to inserted liquidity among what their backtesters couldn't model, and used the website for those questions ([backtesting](backtesting-and-tooling.md)). If the Arena's market reacts to our trades, takes cost more than the backtest says, and a take that clears a level moves the mid by about `x/(2D)` (Cont et al.). `ON_THE_DAY.md` has an item and a probe for it.
- **Backtests that add our orders to recorded data are "a bit dodgy"**, because the impact those orders would have had is about as large as the effects being studied (`literature_md/trades-quotes-prices/trades-quotes-prices.md:7944` (p. 421)). That is our engine's default.
- **The template quotes symmetrically:** `skew` moves both quotes by the same amount per unit of position (`bots/template.py:428`), which is Harris's bluff-proof rule. A fair value driven by trade flow would need the same symmetry.

## How to test it here
- **Per product, each round:** taker's edge against the wall mid and the signed wall-mid move at 1–50 ticks after market trades. A product whose wall mid follows the trades has informed flow: widen or skew there, and quote tighter where it doesn't.
- **Our own fills:** compare the wall-mid markout of our passive fills at 1 and 50 ticks (`analysis.markouts(run, reference="wall_mid")`). A markout that keeps falling after 1 tick is `R∞`; one that recovers is noise.
- **On the portal:** probe 17 in `ON_THE_DAY.md`.

## Sources
[Gould et al.](../sources/limit-order-books.md), [Bouchaud et al.](../sources/trades-quotes-prices.md), [Cont et al.](../sources/price-impact-of-book-events.md), [Cartea et al., book](../sources/algorithmic-and-hft.md), [Guéant et al.](../sources/dealing-with-inventory-risk.md), [Huang et al.](../sources/queue-reactive-model.md), [Harris](../sources/harris-trading-and-exchanges.md).
