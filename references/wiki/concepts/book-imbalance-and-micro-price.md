---
title: Book imbalance and the micro-price
type: concept
updated: 2026-10-15
---

# Book imbalance and the micro-price

## Summary
The volumes at the best bid and ask predict the direction of the next mid move, and a fair value can be built from that: the weighted mid, or Stoikov's micro-price. The literature agrees the effect is strong only when the spread is about one tick and the queues are long. Prosperity's spreads are 2–21 ticks and its best levels are bot quotes, so on paper the signal should be weak there. **Tested here (2026-10-15): it is strong for the plain mid and useless for the fair value.** On Prosperity data `ρ` predicts the next mid move well (ROC area up to 0.84), but that is the mid's own noise, which the wall mid already removes; as a forecast of the wall mid it adds under 1%, and no form of it made money under `worse` fills or `--resting`.

## What the sources say
**Definitions** (all from the best levels only; formulas checked against the PDFs):
- **Imbalance:** `ρ = (Vᵇ − Vᵃ)/(Vᵇ + Vᵃ) ∈ [−1, 1]` (`literature_md/order-book-signals/order-book-signals.md:77` (p. 5, checked); Gould & Bonart's `I` is the same: `literature_md/queue-imbalance-predictor/queue-imbalance-predictor.md:112` (p. 7, checked)). Stoikov uses `I = Vᵇ/(Vᵇ + Vᵃ) = (1 + ρ)/2` (`literature_md/micro-price/micro-price.md:73` (p. 3, checked)).
- **Weighted mid:** `W = I·Pᵃ + (1 − I)·Pᵇ` (`literature_md/micro-price/micro-price.md:69` (p. 3, checked)). This is what heyman7913 and most teams call the "micro-price" ([heyman7913](../sources/prosperity4-heyman7913.md)).
- **Micro-price:** `M + G*(I, S)`, the expected mid after many more mid changes, read from a table indexed by imbalance bucket and spread. The table is estimated from the data by a Markov chain on symmetrised samples, `G* = G¹ + Σ Bⁱ G¹` (`literature_md/micro-price/micro-price.md:276-286` (p. 6, checked)). It lies between the mid and the weighted mid ([micro-price](../sources/micro-price.md)).
- **Order flow imbalance (OFI):** the net *change* in the best queues between snapshots. It explains the *same* interval's mid change linearly, with R² 65% on 10-second TAQ data. It is not a forecast; the paper never tests one ([Cont et al.](../sources/price-impact-of-book-events.md)).

**Evidence that `ρ` predicts:**
- **Gould & Bonart, 10 Nasdaq stocks** ([source](../sources/queue-imbalance-predictor.md)): a logistic regression of the next mid move's direction on `ρ`. Out of sample, the ROC area is 0.75–0.81 for 1-tick-spread stocks and 0.58–0.64 for small-tick stocks. The squared error drops 20–30% against a coin flip for the first group and **2–6%** for the second (`literature_md/queue-imbalance-predictor/queue-imbalance-predictor.md:356-384` (p. 20–21, checked)).
- **Cartea et al. 2018, 11 Nasdaq stocks** ([source](../sources/order-book-signals.md)): a buy-heavy book means more market buys and larger mid jumps after them.
- **The signal fades with the spread** (Stoikov, [source](../sources/micro-price.md)): at a 4-tick spread, CVX's micro-price "is indistinguishable from the mid-price" (`literature_md/micro-price/micro-price.md:308` (p. 8)). Gould & Bonart give the mechanism: at a 1-tick spread the mid moves only when a queue empties; at wider spreads a new order inside the spread can move it, and the imbalance can't see that coming (`literature_md/queue-imbalance-predictor/queue-imbalance-predictor.md:453` (p. 26)).

- **The size of the effect on one large-tick stock** (Cartea et al., book, Table 12.1, ORCL for one day; [source](../sources/algorithmic-and-hft.md)): buy market orders arrive at 0.037/s when the book is neutral and 0.216/s when it is most bid-heavy. Sell orders arrive at 0.048/s neutral and 0.856/s most ask-heavy (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:7068` (p. 321, checked)). Regimes estimate as a Markov chain with `Â_ij = n_ij/Σ_j n_ij` (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6933` (p. 315, checked)).
- **A flow-driven fair can be gamed** in a shared market: a rival who knows our fair moves more for some orders than others can trade the difference (Harris's bluffing condition, [shared market](shared-market-and-adversaries.md)).

**How it changes quoting** (Cartea et al. 2018):
- **Always quoting at the touch loses money:** the annualised Sharpe ratio is negative for all 11 stocks at every inventory cap (`literature_md/order-book-signals/order-book-signals.md:462-477` (p. 30, checked)).
- **Rule of thumb:** quote a side only if the half-spread you earn exceeds `ε±(J)`, the expected adverse mid move after a fill on that side in the current imbalance-and-spread state (`literature_md/order-book-signals/order-book-signals.md:306-312` (p. 20, checked)). In a buy-heavy book, stop offering.
- **Out of sample:** with the honest fill model (back of the queue), the gain is small and uneven: Sharpe −5…+12, negative for one stock at every setting (`literature_md/order-book-signals/order-book-signals.md:559-574` (p. 33, checked)).

**What the teams found:**
- **heyman7913** blended `0.30 × W + 0.70 × slow EMA + 2.0 × ρ`, minus an inventory penalty, and report a significant Spearman correlation on Osmium. That is their claim (`online-snapshots/heyman7913_imc-prosperity-4.README.md:195-233`).
- **AlgoTrade 2026:** a top-3-level depth imbalance predicts the mid 500 ms ahead with correlations up to ±0.49, **with the sign flipping per instrument** (`algotrade2026-pitfa19/analysis/mm_analysis.md:172-197`). Note it is a different definition (three levels) on a live venue.
- **Baguette Fromage** listed "microstructure imbalance signals" among the round 5 scanners that looked like "unlimited alpha" in sample. Fit on two days and tested on the third, these relationships collapsed (`prosperity4-baguette-fromage/README.md:866-890`).
- **Leo-Hawking:** LLMs "gravitate toward generic topics — microstructure imbalance signals", while local alpha decided ranks (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:581-609`).
- **DTU** lists Stoikov's micro-price among the papers it read; its literature review records what shipped (`prosperity4-dtu-quant-lab/README.md:258`).
- **The race between the best queues** ([Bouchaud et al.](../sources/trades-quotes-prices.md), ch. 7): with a one-tick spread, the price moves when a best queue empties.
  - The imbalance `I` predicts which one empties first, "the worst kept secret of high-frequency traders" (`literature_md/trades-quotes-prices/trades-quotes-prices.md:2568-2576` (p. 139)).
  - Purely random queues give `p₊(I) = (2/π)·arctan(I/(1 − I))` (eq. 7.6, `literature_md/trades-quotes-prices/trades-quotes-prices.md:2627` (p. 141, checked)), with the wrong concavity; queues that stabilise fit better.
  - For large ticks, the book suggests an imbalance-weighted reference price instead of the mid (footnote 6, `literature_md/trades-quotes-prices/trades-quotes-prices.md:4350` (p. 232)).
- **Imbalance as a maker's signal failed live** ([Albers et al.](../sources/market-makers-dilemma.md)): posting only when the imbalance favoured the order, and cancelling when it turned, still lost on the bitcoin perpetual (`literature_md/market-makers-dilemma/market-makers-dilemma.md:428` (p. 22)). What made a little money was the contrary: posting *against* an adverse imbalance when a model predicted it would fail, to hold an early queue place (`literature_md/market-makers-dilemma/market-makers-dilemma.md:693-697` (p. 36)).
- **Order flow across products** ([Lee et al.](../sources/cross-asset-order-flow.md)): the constituents' order-flow imbalance predicts the index's next 5–60 seconds a little better than the index's own (`literature_md/cross-asset-order-flow/cross-asset-order-flow.md:227-233` (p. 6, checked)); on Prosperity's baskets the legs do not lead ([baskets](baskets-and-fixed-sums.md)).
- **Order-flow imbalance by event type** ([Sitaru et al.](../sources/decomposed-ofi.md), 100 Nasdaq stocks, three years): splitting OFI into adds, cancels and trades does not explain the same interval's move better, but forecasts the next ones better, the add part most (`literature_md/decomposed-ofi/decomposed-ofi.md:33` (p. 2)). From snapshots only the trade part and the net book change are computable.

- **The imbalance is what spoofers move** ([Cartea, Jaimungal & Wang](../sources/optimal-spoofing.md), [Cartea, Chang & García-Arenas](../sources/spoofing-learning-algorithms.md)): a large order at one best quote makes traders who read `ρ` expect a move and trade into it (`literature_md/spoofing-learning-algorithms/spoofing-learning-algorithms.md:15` (p. 2)). In a shared market an imbalance signal is the first thing a spoofer exploits; test any `ρ`-based rule with a spoofer rival before trusting it.

## Where they disagree
- **Strong or useless?** On Nasdaq large-tick stocks the signal is strong, and on small-tick ones it is barely better than a coin flip. AlgoTrade and Baguette Fromage found it unstable or not robust out of sample. These are less in conflict than they look: the literature *predicts* a weak signal at wide spreads, which is Prosperity's regime. See [contradictions](../contradictions.md), row 11.
- **Forecast or mark?** In Prosperity the PnL is marked to the market maker's mid, which the wall mid estimates directly ([fair value](fair-value-and-wall-mid.md)). An imbalance forecast can only add to that on the horizon of our holding time; it does not replace the mark.
- **Weighted mid or micro-price?** Stoikov argues the weighted mid is noisy, isn't a martingale and can move the wrong way: a small sell inside the spread *raises* it (`literature_md/micro-price/micro-price.md:79` (p. 3, checked)). Teams use it anyway. Our `wall_mid` ignores small orders for a similar reason ([fair value](fair-value-and-wall-mid.md)).

## What it means for our code
- **Fair value:** `bots/template.py` offers `fair` = `fixed`, `mid`, `wall_mid`, `outer_mid`, `sized_mid` or `weighted_mid` (`W` from the best levels) (`bots/template.py:35`, `bots/template.py:315-343`). `imbalance` (`bots/template.py:42`) takes, clears and makes around `fair + imbalance × ρ`, the linear micro-price, without changing the fair that the stops and targets use (`bots/template.py:285`). Both are off for every product; see "Tested here".
  - Stoikov's table (`mid + G*[bucket(ρ)][spread]`) was not built into the bot: as a forecast, the binned table did no better than the linear `b·ρ` (below).
- **Quote filter** (Cartea's rule): skip a side when the expected markout of a passive fill on that side, in the current `ρ` bucket, is below zero. `arena/analysis.py` already computes markouts, as `sign × (mark later − fill price)` per unit, which is Cartea's `Δ/2 − ε±` at a short horizon. But it is per product and fill type, not per imbalance state (`arena/analysis.py:206-233`).
- **OFI** is no fair-value input on this evidence. Its use is sizing our takes: taking `x` at a level of depth `D` moves the mid by about `x/(2D)` ticks.
- `TODO.md`, "Try the literature's fair values and skew in the template", is where these land.

## Tested here (2026-10-15)
`uv run python -m experiments.imbalance` (P2 round 1, P3 rounds 1 and 5, P4 rounds 1–2); backtest numbers in `IDEAS.md`, from the row "Book imbalance `ρ` and the micro-price".
- **Gould & Bonart's test passes for the plain mid.** Out-of-sample ROC area 0.83 on Kelp, 0.81–0.84 on Osmium and Pepper Root, 0.74 on Starfruit, 0.67 on Squid Ink, 0.54–0.86 on Resin (it depends on the round). `x₁` has the same sign on every day of every product, so row 11's sign flip doesn't happen within a product here. It is strongest at 1–2-tick spreads (Kelp 0.94), as the literature says.
- **But it predicts the mid's noise, not the price.** A small order inside the walls skews `ρ` and moves the mid; when it leaves, the mid snaps back. As a forecast of the wall mid 1–50 ticks ahead, `wall_mid + b·ρ` beats `wall_mid` by under 1% (Osmium 1.150 → 1.141 RMSE at 1 tick). Its `b` is tiny on Kelp (−0.05 tick), +0.6 on Osmium and +0.8 on Pepper Root, each stable across days. The binned table did no better, except on Pepper Root, where its gain is the product's steady drift. The weighted mid's error is 2–3× the wall mid's on Kelp and Resin.
- **Backtests agree.** `weighted_mid` loses everywhere (Kelp −5k to −7k of 63–73k, Starfruit −27k of 105k, Osmium −18k). The `imbalance` tilt moves P4 by under 0.2%. On Kelp it gains under `all` (+2.5k, and +1.7k on held-out round 5) but loses under `worse` (−1.2k), under `--resting` (−1.0k), and against the trapper (−3.3k), which baits exactly this signal. heyman7913's blend on Osmium gained only through its EMA (`smoothing`), not through `ρ`.
- **Not done:** the markouts of our passive fills by `ρ` bucket (Cartea's quote filter, step 2 below).

## How to test it here
1. **Gould & Bonart's design, per product and day, before any code in the bot** (done, above).
   - On P3 and P4 rounds 1–2, take the ticks where the mid changes, `y` = up or down, and `ρ` at the previous tick.
   - Fit `P(up) = 1/(1 + e^{−(x₀ + x₁ρ)})` with leave-one-day-out.
   - Report the ROC area and the squared error against 0.25.
   - Split by spread (Stoikov), and check that the sign of `x₁` is the same on every day (row 11).
2. **Markouts by `ρ` bucket:** group our passive fills by the `ρ` at fill time (three buckets at ±⅓, as Cartea) and compare markouts at 1–5 ticks. A side whose markout is negative in a bucket is a candidate for the filter.
3. **Only then a `fair` option or filter**, compared with `wall_mid` under `--match-trades worse`, `--resting` and `--vs`. Ship only if its worst day is positive (DTU's rule, [validation](validation-and-overfitting.md)).

## Sources
[Bouchaud et al.](../sources/trades-quotes-prices.md), [Cartea et al., book](../sources/algorithmic-and-hft.md), [Harris](../sources/harris-trading-and-exchanges.md), [Stoikov, micro-price](../sources/micro-price.md), [Gould & Bonart](../sources/queue-imbalance-predictor.md), [Cartea, Donnelly & Jaimungal](../sources/order-book-signals.md), [Cont, Kukanov & Stoikov](../sources/price-impact-of-book-events.md), [heyman7913](../sources/prosperity4-heyman7913.md), [AlgoTrade pitfa19](../sources/algotrade2026-pitfa19.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Albers et al.](../sources/market-makers-dilemma.md), [Lee et al.](../sources/cross-asset-order-flow.md), [Sitaru et al.](../sources/decomposed-ofi.md), [Cartea, Jaimungal & Wang](../sources/optimal-spoofing.md), [Cartea, Chang & García-Arenas](../sources/spoofing-learning-algorithms.md).
