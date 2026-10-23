---
title: Avellaneda & Stoikov, "High-frequency trading in a limit order book" (2008)
type: source
repo: literature_md/hft-in-a-limit-order-book
status: read
updated: 2026-10-13
---

# Avellaneda & Stoikov, "High-frequency trading in a limit order book" (Quantitative Finance 8(3), 2008, pp. 217–224)

## What it is
The paper behind every "Avellaneda–Stoikov" market maker. A dealer quotes one bid and one ask around a Brownian mid, is filled by Poisson market orders whose rate decays with the quote's distance from the mid, and maximises exponential utility at a horizon T. The answer comes in two steps: an inventory-adjusted **reservation price**, then a **spread** set by the inventory risk left and by how fast fills fall off with distance. Teams cite it ([DTU](prosperity4-dtu-quant-lab.md), [Hummingbot](hummingbot-avellaneda-stoikov.md)). DTU lost money with it on a pegged product ([contradictions](../contradictions.md), row 1).

**This is the published version** (received 24 April 2006, final form 3 April 2007, `hft-in-a-limit-order-book.md:33` (p. 2)). It replaced our earlier copy, the 24 April 2006 preprint, on 2026-10-13 (the preprint is kept in `literature_raw/superseded/`, not converted). The two differ in three places that matter, all settled here: the spread formula, the infinite-horizon prices and the simulations (see Traps). PDF page 1 is the publisher's cover sheet; the article is pages 2–9.

## Main results
- **Model:** the mid is `dS_u = σ dW_u`, arithmetic Brownian motion (`hft-in-a-limit-order-book.md:55` (p. 3, checked)). The objective is `E[−exp(−γ(X_T + q_T S_T))]`: inventory left at T is valued at the mid, with no liquidation cost.
- **Reservation (indifference) prices**, with no trading allowed (`hft-in-a-limit-order-book.md:99-107` (p. 4, checked)):
  - `r^a = s + (1 − 2q)γσ²(T−t)/2` and `r^b = s + (−1 − 2q)γσ²(T−t)/2` (eqs. 6–7).
  - Their average is `r(s, q, t) = s − qγσ²(T − t)` (eq. 8). Long inventory pushes the price at which the dealer is indifferent below the mid.
- **Infinite horizon** (`hft-in-a-limit-order-book.md:119-127` (p. 4, checked)): with a discount `ω`, `r̄^a = s + (1/γ)·ln(1 + (1 − 2q)γ²σ²/(2ω − γ²q²σ²))` and `r̄^b = s + (1/γ)·ln(1 + (−1 − 2q)γ²σ²/(2ω − γ²q²σ²))`, valid for `ω > ½γ²σ²q²`. Choosing `ω = ½γ²σ²(q_max + 1)²` bounds the prices. This is a stationary skew with no `T`, non-linear in `q`. At `q = 0`, `r̄^a > s > r̄^b`, as it should be.
- **Fill intensity** (eq. 12, `hft-in-a-limit-order-book.md:187-191` (p. 5, checked)): a power law for market-order sizes and a log impact give `λ(δ) = A·e^{−kδ}`, with `A = Λ/α` and `k = αK`. A power-law impact gives `λ(δ) = B·δ^{−α/β}` instead.
- **Optimal quotes** (implicit, eqs. 18–19, `hft-in-a-limit-order-book.md:233-237` (p. 6, checked)): `s − r^b = δ^b − (1/γ)·ln(1 − γλ^b(δ^b)/∂_δλ^b(δ^b))`, and the same for the ask.
- **Closed-form approximation** (§3.2, `hft-in-a-limit-order-book.md:245-295` (p. 6, checked)):
  - Expand the value function to second order in `q` (eq. 22) and linearise the order-arrival term (eq. 26). The spread is `δ^a + δ^b = −2θ²(s, t) + (2/γ)·ln(1 + γ/k)` (eq. 25) around `r = θ¹ + 2qθ²`, and solving for `θ¹ = s` and `θ² = −½σ²γ(T − t)` gives:
  - **Reservation price `r(s, t) = s − qγσ²(T − t)`** (eq. 29), the same as the frozen-inventory one.
  - **Spread `δ^a + δ^b = γσ²(T − t) + (2/γ)·ln(1 + γ/k)`** (eq. 30), independent of `q`, centred on `r`.
  - So, as distances from the mid: `δ^b = ((1 + 2q)/2)·γσ²(T − t) + (1/γ)·ln(1 + γ/k)` and `δ^a = ((1 − 2q)/2)·γσ²(T − t) + (1/γ)·ln(1 + γ/k)` *(inferred: eq. 29 ∓ half of eq. 30)*. This is the form GLFT's footnote 8 quotes ([GLFT](dealing-with-inventory-risk.md)).
- **Simulation** (`hft-in-a-limit-order-book.md:307-311` (p. 7, checked)): s = 100, T = 1, σ = 2, dt = 0.005, q₀ = 0, k = 1.5, A = 140, 1,000 paths; the "symmetric" benchmark uses the inventory strategy's average spread centred on the mid. Tables 1–3 (`hft-in-a-limit-order-book.md:319-370` (p. 7–8, checked)):

  | γ | Average spread | Inventory: profit ± sd, final q sd | Symmetric: profit ± sd, final q sd |
  |---|---|---|---|
  | 0.01 | 1.35 | 68.6 ± 8.7, 5.1 | 68.8 ± 12.8, 8.7 |
  | 0.1 | 1.49 | 65.0 ± 6.6, 2.9 | 68.4 ± 12.7, 8.4 |
  | 1 | 3.02 | 31.4 ± 5.0, 1.7 | 44.0 ± 11.0, 5.1 |

  - The average spreads are eq. 30 averaged over `t ∈ [0, 1]`: `(2/γ)·ln(1 + γ/k) + γσ²/2` gives 1.35, 1.49 and 3.02 *(computed here; all three match)*.
  - The skew buys a much lower variance of profit and of final inventory, at a cost in mean that grows with γ: almost nothing at γ = 0.01, 5% at γ = 0.1, 29% at γ = 1.

## Assumptions against the Arena
- **Brownian mid, no mean reversion.** For a pegged product (Resin, Osmium at 10,000) inventory is barely risky, since the price comes back, so `σ²(T−t)` overstates the risk: the skew gives away edge, and the `γσ²(T − t)` term widens the spread for no reason. *Inferred*, not tested: a candidate explanation for DTU's 16,593 loss with an A–S reservation price on Osmium (`prosperity4-dtu-quant-lab/README.md:91`).
- **The spread depends on the time left.** With `σ` per tick and `T − t` in ticks to the end of a 10,000-tick day, `γσ²(T − t)` is largest at the open and vanishes at the close, so a fixed `make_edge` can only match it at one time of day *(inferred)*. GLFT show the `(T − t)` dependence is an artefact of the expansion near `T`; far from `T` their exact quotes don't depend on time ([optimal quoting models](../concepts/optimal-quoting-models.md)).
- **Inventory is marked at the mid at T for free.** So the skew *shrinks* to zero near the close. If the Arena liquidates at a bad price, the terminal condition changes and the skew should *grow* near the close instead; Guéant et al. and Cartea et al. 2018 use a liquidation penalty for this. Prosperity zeroes positions at fair value at the end, per IMC's webinar answers as reported in `references/README.md` (Ctrl-Alt-DefeatTheMarket). If that holds for the Arena, A–S's assumption holds too.
- **Continuous prices.** Prosperity has integer ticks and spreads of 2–21 ticks, and Cartea et al. 2018 show that continuous depths rounded to the tick collapse to quoting at the touch ([order-book-signals](order-book-signals.md)).
- **No hard limit:** inventory is unbounded in the finite-horizon version; only `ω` in the infinite-horizon version bounds it. [Guéant, Lehalle & Fernandez-Tapia](dealing-with-inventory-risk.md) add the hard bound.
- **Fills arrive as Poisson market orders reaching our distance from the mid.** In Prosperity, fills come from bots crossing our quote or trading at our price (`ARCHITECTURE.md`, matching rules), so `A` and `k` have to be measured, not derived.

## In our notation
| Paper | Ours |
|---|---|
| `s` | the fair value (`fair_value`, `python/bots/template.py:294`) |
| `q` | the position (`plan.net` in `make`) |
| `r = s − qγσ²(T−t)` | `fair − shift`, where `shift = round(skew × q / limit)` (`python/bots/template.py:707`); equal when `skew = γσ²(T−t) × limit` |
| `δ^a + δ^b = γσ²(T−t) + (2/γ)·ln(1 + γ/k)` | `2 × make_edge` (`python/bots/template.py:45`), which has no time term; as γ → 0 the half-spread tends to `1/k` |
| `σ` | per-tick standard deviation of the fair value, per product |
| `A, k` | fill rate against quote distance from fair, measurable from `_fills.csv` and `_orders.csv` |
| `T − t` | ticks to the end of the day (`timestamp` runs 0…999,900 in Prosperity) |

## Traps
- **The preprint and the published paper differ; quote the published one.** *(The infinite-horizon prices were checked on both PDFs' page images on 2026-10-13; the preprint's spread and tables are as the earlier version of this page recorded them, checked then against the preprint's page images.)*
  - **Spread:** the preprint's closed form was `(2/γ)·ln(1 + γ/k)`, derived by using the static reservation price as a proxy. The published §3.2 derives it from an expansion in `q` and adds `γσ²(T − t)` (eq. 30). Hummingbot's guide and deep dive use the published formula, though the deep dive cites the paper as "2006" ([Hummingbot](hummingbot-avellaneda-stoikov.md)).
  - **Infinite-horizon prices:** the preprint had `−(2q + 1)` in `r̄^a` and `−(2q − 1)` in `r̄^b`. That puts `r̄^a` below the mid at `q = 0`, so the two were swapped: a typo in the preprint, fixed in print (`(1 − 2q)` for the ask, `(−1 − 2q)` for the bid, consistent with eqs. 6–7).
  - **Simulations:** the preprint used M = 0.5 with `A` calibrated from it, a third "best bid/best ask" benchmark and γ = 0.5; its γ = 0.1 table had a spread of 1.29 and profits 62.94 ± 5.89 (inventory) against 67.21 ± 13.43 (symmetric). The published version sets A = 140, drops the best-bid/ask benchmark and adds γ = 1. Earlier wiki pages quoted the preprint's numbers.
- **The closed form is an approximation**, from a first-order expansion of the arrival term; it is not the optimum of the HJB (15). With a quadratic expansion, `θ²` solves a nonlinear PDE (`hft-in-a-limit-order-book.md:297` (p. 6)).
- `δ^b` and `δ^a` are distances from the **mid** `s`, not from `r`.
- **OCR** (all checked against the page images):
  - eqs. 6–7 read `\frac{\gamma^{\sigma^2}(T - t)}{2}` where the PDF has `γσ²(T − t)/2` (`hft-in-a-limit-order-book.md:99-103` (p. 4, checked));
  - eq. 13 reads `max_{δ∈[0,δ*]} E_t[−exp(−γ(X_t + q_t S_t))]` where the PDF has `max_{δ^a,δ^b} E_t[−exp(−γ(X_T + q_T S_T))]` (`hft-in-a-limit-order-book.md:201` (p. 5, checked));
  - eq. 14 reads `u(x, x, q, t)` for `u(s, x, q, t)` (`hft-in-a-limit-order-book.md:211` (p. 5, checked));
  - eq. 19 reads `r^d`, `δ^d`, `λ^d` for `r^a`, `δ^a`, `λ^a` (`hft-in-a-limit-order-book.md:237` (p. 6, checked));
  - the solution of eq. 28 reads `ð1=2Þ2 ðT tÞ` for `θ² = −(1/2)σ²γ(T − t)` (`hft-in-a-limit-order-book.md:289` (p. 6, checked)), and the bound on `ω` is garbled the same way (`hft-in-a-limit-order-book.md:125` (p. 4, checked));
  - in the prose, Greek letters are dropped, `>` and `<` come out as `4` and `5` ("q40"), and `=` as `¼`.

## Read depth
- **Read:** all sections, including the appendix (the geometric Brownian motion version with a mean–variance objective, `hft-in-a-limit-order-book.md:347-382` (p. 8–9)).
- **Checked against the PDF (page images):** eqs. 1, 3, 6–8, the infinite-horizon prices, 12, 18–30, the simulation parameters and Tables 1–3. The average spreads were recomputed from eq. 30.
- **Not checked:** the derivation of the HJB (15) from (13).

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [hummingbot-avellaneda-stoikov](hummingbot-avellaneda-stoikov.md).
