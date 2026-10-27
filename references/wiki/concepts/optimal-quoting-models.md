---
title: Optimal quoting models (Avellaneda–Stoikov, GLFT, Guéant)
type: concept
updated: 2026-10-26
---

# Optimal quoting models (Avellaneda–Stoikov, GLFT, Guéant)

## Summary
The standard theory of where to quote is "fair ± half-spread − skew × inventory". The closed forms of Guéant, Lehalle & Fernandez-Tapia (GLFT) and Guéant say the skew is **linear in inventory and independent of time**, which is what `python/bots/template.py` already does with `skew`. What the theory adds is the coefficients: they come from each product's volatility and fill-rate curve, so one risk-aversion knob replaces per-product tuning. It also gives a drift shift, an adverse-selection edge, and a cross-product skew. Its assumptions (a Brownian price, Poisson fills decaying with distance, small ticks) fit pegged products and bot-filled books poorly. So measure `A`, `k` and `σ` first, and keep the skew only where its worst day improves.

## What the sources say
**The models, in order:**
- **[Avellaneda–Stoikov](../sources/hft-in-a-limit-order-book.md):**
  - The reservation price `r = s − qγσ²(T − t)`.
  - The spread `γσ²(T − t) + (2/γ)·ln(1 + γ/k)`, centred on `r` (`literature_md/hft-in-a-limit-order-book/hft-in-a-limit-order-book.md:291-295` (p. 6, checked)), from an expansion in `q` with a linearised arrival term.
  - No inventory bound in the finite-horizon version.
- **[GLFT](../sources/dealing-with-inventory-risk.md):**
  - Adds a hard bound `±Q` (no bid at `Q`) and solves the problem exactly.
  - Far from `T` the quotes don't depend on time, and their closed form is `δ^b ≈ (1/γ)·ln(1 + γ/k) + ((2q + 1)/2)·c₂` and `δ^a ≈ (1/γ)·ln(1 + γ/k) − ((2q − 1)/2)·c₂`, with `c₂ = √(σ²γ/(2kA)·(1 + γ/k)^{1+k/γ})` (`literature_md/dealing-with-inventory-risk/dealing-with-inventory-risk.md:225-229` (p. 11, checked)).
  - A–S's `(T − t)` dependence is only the Taylor expansion near the end (`literature_md/dealing-with-inventory-risk/dealing-with-inventory-risk.md:165-177` (p. 8, checked)).
- **[Guéant 2017](../sources/optimal-market-making.md):**
  - Generalises to any intensity function and to the PnL-with-penalty objective (Model B, the Cartea–Jaimungal family).
  - In Model B the half-spread at zero inventory is `1/k` and the skew per unit is `√(γσ²e/(2Ak))`. "The approximation of the bid-ask spread is independent of q, and the skew is linear in q" (`literature_md/optimal-market-making/optimal-market-making.md:733-761` (p. 21–22, checked)).
  - **For several products, asset i's skew uses `Σ_j Γ^{ij} q^j`,** the inventories of all correlated products (`literature_md/optimal-market-making/optimal-market-making.md:1013-1060` (p. 29–30, checked)).
- **Extensions** (GLFT, `literature_md/dealing-with-inventory-risk/dealing-with-inventory-risk.md:286-338` (p. 13–15, checked)):
  - A price drift `μ` shifts both quotes by `(μ/(γσ²))·c₂`.
  - Adverse selection (the price jumps `ξ` against each fill) adds `ξ/2` to each side.

- **The textbook version** ([Cartea et al., book](../sources/algorithmic-and-hft.md) ch. 10):
  - The running-penalty maker has depths `δ± = 1/κ − [h(t, q∓1) − h(t, q)]`, with `h` from a matrix exponential `ω(t) = e^{A(T−t)}z` (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:5788-5830` (p. 265–266, checked)). That is computable offline for a limit of 50.
  - The utility maximiser is the same strategy up to a constant shift once `φ = ½σ²γ` (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6064-6090` (p. 277–278, checked)). So A–S/GLFT and the penalty models agree.
  - If each market order moves the mid by ε, each quote moves out by ε (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6114-6162` (p. 279–280, checked)).
  - **When buy and sell market orders arrive at different rates, the optimal inventory is not zero:** the maker leans toward the side the drift favours (`literature_md/algorithmic-and-hft/algorithmic-and-hft.md:6218` (p. 283)).
- **A mean-reverting price** ([Ahuja et al.](../sources/mean-reverting-reference-price.md)): A–S with an Ornstein–Uhlenbeck price. Far from the end the optimal quotes are **constants around the long-run mean**, `μ ± (1/γ)·log(1 + γ/κ)`, independent of price and inventory (`literature_md/mean-reverting-reference-price/mean-reverting-reference-price.md:305` (p. 8, checked)). Between that and the last cycle there is a long intermediate regime where the quotes ignore the price and skew with inventory by about `γσ²/(2α)` per unit, γ times the price's stationary variance *(derived from eq. 31)*. Numerical only; no proof.
- **Discrete ticks and the take decision** ([Guilbaud & Pham](../sources/limit-and-market-orders.md)): the maker picks, per side, the best price or one tick inside it, or crosses with a market order, from a table over (inventory, spread in ticks). Long: improve the ask, keep the bid at the best; far out: cross (`literature_md/limit-and-market-orders/limit-and-market-orders.md:458-462` (p. 13, checked)). In their simulated backtest the gain over always quoting at the best is in variance (sd 12.6 against 51.5), not in mean (26.8 against 24.3) (`literature_md/limit-and-market-orders/limit-and-market-orders.md:522-524` (p. 14, checked)).
- **Learning the quotes online** ([Fernandez-Tapia](../sources/online-learning-market-making.md)): stochastic gradient on the half-spread and the off-centring, one update per quote period, needing the fill decay `k` but no price model. The Brownian optimum is `ψ* = (1/k)·(k²σ²ΔT − 1 + e^{−k²σ²ΔT/2})/(1 − e^{−k²σ²ΔT/2})`, which tends to `1/k` as quotes get short-lived (`literature_md/online-learning-market-making/online-learning-market-making.md:208-210` (p. 13, checked)).
- **Discrete periods, a forecast and a closing cost** ([Capponi et al.](../sources/stochastic-liquidity-demand.md)): fills linear in distance, a liquidation cost at the end of the day, and a price forecast that shifts both quotes in proportion to the expected change (`literature_md/stochastic-liquidity-demand/stochastic-liquidity-demand.md:47` (p. 6)).
- **Clustered order flow** ([Acero, Plank & Zhang](../sources/hawkes-structured-mm.md)): A–S with self-exciting market orders. The quotes depend on the history only through a few exponentially decaying counts of past arrivals per side (eq. 4, `literature_md/hawkes-structured-mm/hawkes-structured-mm.md:141` (p. 3, checked)). Prosperity's takers don't cluster (`python/experiments/trade_clustering.py`), so it adds nothing there.

**Calibration in practice:**
- GLFT chose `γ` so that inventory stayed within ±10 average trade sizes. They note that `A` and `k` "have to depend at least on the actual market bid-ask spread" (`literature_md/dealing-with-inventory-risk/dealing-with-inventory-risk.md:416-418` (p. 20)).
- Hummingbot derives `γ` and `κ` from a user-chosen minimum and maximum spread ([Hummingbot](../sources/hummingbot-avellaneda-stoikov.md)): `γ = IRA·(max − min)/(2|q|σ²)`, and `κ` from eq. 30 at the widest spread (`online-snapshots/hummingbot-as-deep-dive.md:110-136`).
- Nobody estimates `γ`; it is a choice.

**Where the models break:**
- Cartea et al. 2018: rounded to the tick, continuous-depth models collapse to quoting at the touch, which loses money to adverse selection on large-tick stocks (`literature_md/order-book-signals/order-book-signals.md:112` (p. 8)).
- The models assume a small tick (GLFT's conclusion; Guéant: "an order-driven market if the tick sizes of the securities are small").

**What the teams did:**
- DTU lost 16,593 in backtest with an A–S reservation price on Osmium and reverted to a fixed anchor, *their claim* (`prosperity4-dtu-quant-lab/README.md:91`).
- Baguette Fromage shipped a linear shift `10000 − position/12` (`prosperity4-baguette-fromage/Strategies/Phase1.py:240`).
- Frankfurt used no skew ([market making](market-making-and-inventory-skew.md)).
- hftbacktest's GLFT notebooks implement the closed form ([hftbacktest](../sources/hftbacktest.md)).

## Where they disagree
- **Which spread formula? Settled 2026-10-13.** The published A–S has `γσ²(T − t) + (2/γ)·ln(1 + γ/k)` (eq. 30), the form GLFT's footnote and Hummingbot quote; only the 2006 preprint, which the wiki used until then, had `(2/γ)·ln(1 + γ/k)` alone ([Avellaneda–Stoikov](../sources/hft-in-a-limit-order-book.md), Traps). GLFT shows the `(T − t)` term is an artefact near `T`, so for a day-long session use the stationary GLFT form.
- **Skew on a pegged product** ([contradictions](../contradictions.md), row 1; **settled for P4 Osmium on 2026-10-13: no skew**). The theory says the skew coefficient is proportional to `σ`, the volatility of the *fair value*, and for a mean-reverting price to its stationary variance ([Ahuja et al.](../sources/mean-reverting-reference-price.md)). On a product pegged at 10,000, that volatility is near zero, so **the models say: little or no skew**, and the limit binds only through "no bid at `Q`". DTU's A–S skew was presumably driven by the mid's noise, not by fair-value risk *(inferred; DTU's code was not checked for which σ it used)*. That is consistent with the losers and winners: Frankfurt (none) and Baguette Fromage (a small fixed shift, about 4 ticks at position 50) against DTU's A–S. Measured on Osmium (P4 rounds 1–2, 6 days, 2026-10-13): `skew` 0 is best on every measure with `wall_mid` (113.8k; 113.3k at 1, 110.0k at 2, 93.4k at 8; 108.7k at 1 under `worse` fills), and a fixed 10,000 makes 99.2k (`uv run python -m arena.grid python/bots/template.py 1 2 --data p4 --set PARAMS.ASH_COATED_OSMIUM.fixed_fair=10000 --grid PARAMS.ASH_COATED_OSMIUM.fair=fixed,wall_mid --grid PARAMS.ASH_COATED_OSMIUM.skew=0,1,2,4,8 --modes all,worse`). The mean-reverting model's other prediction, constant quotes that ignore the price, loses 13% there: its fills depend only on the distance from the reference price, while in Prosperity a quote behind the touch does not fill.

## What it means for our code
- **The template's `skew` is already GLFT's closed form.** `make` shifts both quotes by `round(skew × q / limit)` (`python/bots/template.py:796`). GLFT's stationary quotes shift by `c₂` per unit of `q`, so `skew = c₂ × limit`, and `make_edge` corresponds to `(1/γ)·ln(1 + γ/k) + c₂/2` (`python/bots/template.py:55`) *(inferred from the formulas)*.
- **One knob instead of many:** with `σ_p`, `A_p` and `k_p` measured per product, `skew_p = limit_p · σ_p · √(γe/(2A_p k_p))` (Model B) with a **single** `γ` across products. That is fewer tuned parameters, hence fewer grid trials ([validation](validation-and-overfitting.md)).
- **Drift:** a `drift` parameter that shifts both quotes by `(μ/(γσ²))·c₂` for trending products. P4 Pepper Root has a deterministic `+0.001` per timestamp (`prosperity4-dtu-quant-lab/README.md:85`).
- **Adverse selection:** widening both sides by `ξ/2`, with `ξ` from the fill markouts (`python/arena/analysis.py:189`). This is the model-based version of Cartea's quote filter ([book imbalance](book-imbalance-and-micro-price.md)).
- **Several products:** a cross-product term `Σ_j Γ^{ij} q^j` in the skew for correlated products. That is the cross-product hook asked for in `TODO_DONE.md`, "Add multi-product strategies"; see [many products](many-products-architecture.md).
- **Flatten before the close** (`flatten_from`, built 2026-10-17): A–S and GLFT let the skew *fade* near `T` because inventory is marked at the mid for free. Grow it near the close only if the Arena liquidates at a bad price; Prosperity zeroed positions at fair value (IMC's webinar answers as reported in `references/README.md`, Ctrl-Alt-DefeatTheMarket).
- **The discrete policy is mostly what the template already does** *(inferred)*: `make` quotes one tick inside the best when `make_edge` allows (`make_inside` ticks, 1 by default), a one-tick `skew` turns that into G&P's asymmetric zone (bid back to the best, ask one more tick in), and `clear`/`take` are the market-order zone. What it adds is the estimator: fill rates per (quote position, spread) as fills over time spent in the state, from `_orders.csv` and `_fills.csv` (`literature_md/limit-and-market-orders/limit-and-market-orders.md:226-248` (p. 7–8, checked)).
- **Online tuning of `make_edge`** (tested 2026-10-26, `dropped here`: `IDEAS.md`, "Learning `make_edge` online"). A sign-step learner on passive fills' 5-tick markouts (`python/bots/research/online_edge.py`, `learn_edge`) finds Kelp's best edge under each fill model within a quarter of a day, but its worst case over the models stays below the best fixed edge's: probing costs, and against a copy of the template markouts favour a wider quote than PnL does. Worth re-testing only for a product with no usable history, or as a playground probe of the fill model.

## How to test it here
1. **Measure `A` and `k` per product.**
   - Run the template with fixed `make_edge` values on P3/P4 rounds 1–2.
   - Join `_orders.csv` with `_fills.csv` on `order_id` and compute the fill rate per quote as a function of its distance from the mark (`mark` in `_timeline.csv`).
   - Check whether `log(rate)` is linear in distance. If it isn't, the exponential models don't apply and Guéant's general-intensity formula (4.3)–(4.5) is the fallback.
2. **Measure `σ` per product:** the std of per-tick changes of the fair value, not of the mid.
3. **Compare on the grid:**
   - `skew = 0`;
   - the tuned linear `skew`;
   - the theory value `limit · c₂` with one `γ` swept;
   - `make_edge` set to `1/k` against the tuned one.

   Run under `--match-trades worse` and `--resting`, ranked by worst day.
4. **Pegged products separately:** check whether any skew beats none on Resin and Osmium.

## Sources
[Cartea et al., book](../sources/algorithmic-and-hft.md), [Avellaneda–Stoikov](../sources/hft-in-a-limit-order-book.md), [Hummingbot](../sources/hummingbot-avellaneda-stoikov.md), [GLFT](../sources/dealing-with-inventory-risk.md), [Guéant 2017](../sources/optimal-market-making.md), [Cartea et al. 2018](../sources/order-book-signals.md), [hftbacktest](../sources/hftbacktest.md), [online articles](../sources/online-articles.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Ahuja et al.](../sources/mean-reverting-reference-price.md), [Guilbaud & Pham](../sources/limit-and-market-orders.md), [Fernandez-Tapia](../sources/online-learning-market-making.md), [Capponi et al.](../sources/stochastic-liquidity-demand.md), [Acero, Plank & Zhang](../sources/hawkes-structured-mm.md).
