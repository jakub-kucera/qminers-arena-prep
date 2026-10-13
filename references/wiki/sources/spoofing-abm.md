---
title: Wang & Wellman, "Spoofing the limit order book: an agent-based model" (AAMAS 2017)
type: source
repo: literature_md/spoofing-abm
status: read
updated: 2026-10-14
---

# Wang & Wellman, "Spoofing the limit order book: an agent-based model" (AAMAS 2017)

## What it is
A 9-page simulation study. It builds a single-security limit-order-book market whose background traders see noisy observations of a mean-reverting fundamental. Some of them read the book, some don't. It then adds a spoofer that keeps a large fake bid one tick behind the best bid (`spoofing-abm.md:11` (p. 1)).

It is the most concrete published recipe for two of our prep items in [harder-rounds](../concepts/harder-rounds.md):
- the background agents of a day generator (A1);
- a spoofer rival (D3).

ABIDES cites it as the model for its own fundamental-value agents ([abides-simulator](abides-simulator.md)). Fetched 2026-10-14 from the AAMAS proceedings site.

## Main results
- **The fundamental** (eq. 1, `spoofing-abm.md:79` (p. 3, checked)):
  - `r_t = max{0, κ·r̄ + (1−κ)·r_{t−1} + u_t}`, with `u_t ~ N(0, σ_s²)` and `r_0 = r̄`.
  - Parameters: `r̄ = 10⁵`, `κ = 0.05`, `T = 10,000` steps, `σ_s² ∈ {10⁵, 5×10⁵, 10⁶}` (`spoofing-abm.md:177` (p. 5)).
- **A trader's fair value is a Kalman filter on noisy observations** (p. 3; checked on the page image). Each arrival observes `o_t = r_t + n_t`, with `n_t ~ N(0, σ_n²)` and `σ_n² ∈ {10³, 10⁶, 10⁹}`. With `δ` steps since its last arrival:
  - **Predict:** `r̃ ← (1−(1−κ)^δ)·r̄ + (1−κ)^δ·r̃`, and `σ̃² ← (1−κ)^{2δ}·σ̃² + σ_s²·(1−(1−κ)^{2δ})/(1−(1−κ)²)` (`spoofing-abm.md:103` (p. 3, checked)).
  - **Update:** `r̃ = (σ_n²·r̃ + σ̃²·o_t)/(σ_n² + σ̃²)`, and `σ̃² = σ_n²σ̃²/(σ_n² + σ̃²)` (`spoofing-abm.md:107` (p. 3, checked)).
  - **Project to the close** (eq. 2): `r̂_t = (1−(1−κ)^{T−t})·r̄ + (1−κ)^{T−t}·r̃_t` (`spoofing-abm.md:111` (p. 3, checked)).
- **Zero intelligence (ZI) traders** ignore the book. They arrive as a Poisson process (`λ_a = 0.005` per step). Each one cancels its old order, then bids or offers one unit at a uniform random offset of `[R_min, R_max]` from its valuation. It takes the quote instead if that gives it a share `η` of its wanted surplus (`spoofing-abm.md:119` (p. 3, checked)). Private values are drawn with diminishing marginal utility, so a trader's appetite falls with its position, which is capped at `q_max = 10`.
- **Heuristic belief learning (HBL) traders** read the book. They estimate the probability that an order at price `p` trades from the accepted and rejected orders among the last `L` trades. Then they quote the price that maximises expected surplus (`spoofing-abm.md:141` (p. 4, checked)).
- **HBL is adopted in equilibrium in most environments**, more so with more traders, smaller shocks and noisier observations (`spoofing-abm.md:193` (p. 5)). So reading the book pays in this market.
- **The spoofer:**
  - It keeps a 200-lot bid one tick below the best bid from `t = 1,000`, and re-posts it whenever the best bid moves (`spoofing-abm.md:147` (p. 4)). Single-unit traders can't reach it behind the best bid, so it never trades.
  - It raises transaction prices in every environment that has HBL traders, and moves surplus from HBL to ZI (`spoofing-abm.md:213` (p. 6)).
- **But the spoof adds little profit.** An exploiter buys below the fundamental mean, optionally spoofs, then sells above it. It made 206.1 with the spoof and 201.8 without in the thin market, and 50.5 against 46.3 in the thick one (`spoofing-abm.md:237` (p. 7)). Most of the profit is the mean-reversion trade itself.
- **Re-equilibrated with a spoofer present,** fewer traders choose HBL, but HBL persists in most environments: the market stays spoofable (`spoofing-abm.md:241` (p. 7)).

## Assumptions against the Arena
- **Single-unit background orders, and a spoofer that reacts infinitely fast** (`spoofing-abm.md:147` (p. 4)). In a tick-based Arena a fake wall can be hit within the tick, so a real spoofer takes some risk.
- **A thin market:** about 12 lots of depth a side with 28 traders, and 30 with 65 (`spoofing-abm.md:177` (p. 5)). That is Prosperity-like depth next to limits of 50–80 *(inferred)*.
- **The victims are learning bidders, not a market maker that reads walls.** The template's `wall_mid` reads the largest level directly, which a large fake order moves more crudely than it moves an HBL belief function ([fair value](../concepts/fair-value-and-wall-mid.md)) *(inferred)*.

## In our notation
- `r_t` is the hidden fair value the Arena may score against (`ON_THE_DAY.md`, probe 13); `κ` is the reversion per tick behind `arena.diagnose`'s "slow rev"; `r̄` is the template's `level`.
- The Kalman pair (predict, update) is the B3 prep in [harder-rounds](../concepts/harder-rounds.md): a `fair` that treats each tick's wall mid as `o_t`, with a variance it can carry in `traderData`.
- The spoofer is the D3 rival. Against `wall_mid`, the bid one tick behind the best is enough to become the largest level. Against `sized_mid`, it needs a size near the market maker's usual one.

## Traps
- **OCR:** the variance prediction reads `(1−κ)^2·σ̃²` where the PDF has `(1−κ)^{2δ}·σ̃²` (line 103; checked on the page image of p. 3).
- **The spoof's profit gain is small** next to its effect on prices. Don't read "spoofing works" as "spoofing pays a lot".

## Read depth
- **Read:** the whole paper, from the text layer. The formulas on p. 3–4 were checked on the page image.
- **Not read:** the online appendix (equilibrium tables), and the 2021 journal version in *Games* (with Hoang and Vorobeychik), which extends the analysis.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [abides-simulator](abides-simulator.md).
