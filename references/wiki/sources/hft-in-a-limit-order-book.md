---
title: Avellaneda & Stoikov, "High-frequency trading in a limit order book" (2008)
type: source
repo: literature_md/hft-in-a-limit-order-book
status: read
updated: 2026-10-12
---

# Avellaneda & Stoikov, "High-frequency trading in a limit order book" (preprint dated 24 April 2006; Quantitative Finance, 2008)

## What it is
The 13-page paper behind every "Avellaneda–Stoikov" market maker. A dealer quotes one bid and one ask around a Brownian mid, is filled by Poisson market orders whose rate decays with the quote's distance from the mid, and maximises exponential utility at a horizon T. The answer comes in two steps: an inventory-adjusted **reservation price**, then a **spread** set by how fast fills fall off with distance. Teams cite it ([DTU](prosperity4-dtu-quant-lab.md), [online articles](online-articles.md) for Hummingbot's version). DTU lost money with it on a pegged product ([contradictions](../contradictions.md), row 1).

## Main results
- **Model:** the mid is `S_t = s + σW_t`, arithmetic Brownian motion (`hft-in-a-limit-order-book.md:29` (p. 3, checked)). The objective is `E[−exp(−γ(X_T + q_T S_T))]`: inventory left at T is valued at the mid, with no liquidation cost.
- **Reservation (indifference) price**, with no trading allowed (`hft-in-a-limit-order-book.md:65-73` (p. 4, checked)):
  - `r^a = s + (1 − 2q)γσ²(T−t)/2` and `r^b = s + (−1 − 2q)γσ²(T−t)/2`.
  - Their average is `r(s, q, t) = s − qγσ²(T − t)`. Long inventory pushes the price at which the dealer is indifferent below the mid.
- **Infinite horizon** (`hft-in-a-limit-order-book.md:79-93` (p. 4, checked)): with a discount `ω`, `r̄^a = s + (1/γ)·ln(1 − (2q+1)γ²σ²/(2ω − γ²q²σ²))` and `r̄^b` with `(2q−1)`, valid for `ω > ½γ²σ²q²`. Choosing `ω = ½γ²σ²(q_max + 1)²` ties it to a maximum inventory. This is a stationary skew with no `T`, non-linear in `q`.
- **Fill intensity** (`hft-in-a-limit-order-book.md:135-157` (p. 6–7)): a power law for market-order sizes and a log impact give `λ(δ) = A·e^{−kδ}`, with `A = Λ/α` and `k = αK`. A power-law impact gives `λ(δ) = B·δ^{−α/β}` instead.
- **Optimal quotes** (implicit, eq. 3.6–3.7, `hft-in-a-limit-order-book.md:193-197` (p. 8, checked)): `s − r^b = δ^b − (1/γ)·ln(1 − γλ^b(δ^b)/∂_δλ^b(δ^b))`, and the same for the ask.
- **Closed-form approximation** (`hft-in-a-limit-order-book.md:207-231` (p. 8–9, checked)):
  - `λ(δ) = A·e^{−kδ}`, and use the static `r` as a proxy for both reservation prices. Then `δ^b = γqσ²(T−t) + (1/γ)·ln(1 + γ/k)` and `δ^a = −γqσ²(T−t) + (1/γ)·ln(1 + γ/k)`.
  - These are distances from the mid. The **spread is `δ^a + δ^b = (2/γ)·ln(1 + γ/k)`**, fixed, centred on `r`.
  - `A` is calibrated so that a quote at `−M/2`, crossing half the market spread, fills with probability 1 in one step: `A·e^{kM/2}·dt = 1` (eq. 3.9).
- **Simulation** (s = 100, T = 1, σ = 2, k = 1.5, M = 0.5, 1,000 paths; `hft-in-a-limit-order-book.md:233-281` (p. 9–11)):
  - At γ = 0.1 the inventory strategy (spread 1.29) makes 62.94 ± 5.89. "Best bid/best ask" (spread 0.5) makes 48.43 ± 14.57. A symmetric quote with the same 1.29 spread around the mid makes **67.21 ± 13.43**.
  - So the skew buys a much lower variance (and a final inventory std of 2.80 against 8.66) at a small cost in mean.
  - At γ = 0.5 the skew halves the profit (33.92 against 66.20). At γ = 0.01 the two are the same.
  - The gain over "best bid/best ask" comes from the **wider spread**, not the skew.

## Assumptions against the Arena
- **Brownian mid, no mean reversion.** For a pegged product (Resin, Osmium at 10,000) inventory is barely risky, since the price comes back, so `σ²(T−t)` overstates the risk and the skew gives away edge. *Inferred*, not tested: a candidate explanation for DTU's 16,593 loss with an A–S reservation price on Osmium (`prosperity4-dtu-quant-lab/README.md:91`).
- **Inventory is marked at the mid at T for free.** So the skew *shrinks* to zero near the close. If the Arena liquidates at a bad price, the terminal condition changes and the skew should *grow* near the close instead; Guéant et al. and Cartea et al. 2018 use a liquidation penalty for this. Prosperity zeroes positions at fair value at the end, per IMC's webinar answers as reported in `references/README.md` (Ctrl-Alt-DefeatTheMarket). If that holds for the Arena, A–S's assumption holds too.
- **Continuous prices.** Prosperity has integer ticks and spreads of 2–21 ticks, and Cartea et al. 2018 show that continuous depths rounded to the tick collapse to quoting at the touch ([order-book-signals](order-book-signals.md)).
- **No hard limit:** inventory is unbounded in the finite-horizon version; only `ω` in the infinite-horizon version bounds it. [Guéant, Lehalle & Fernandez-Tapia](dealing-with-inventory-risk.md) add the hard bound.
- **Fills arrive as Poisson market orders reaching our distance from the mid.** In Prosperity, fills come from bots crossing our quote or trading at our price (`CLAUDE.md`, matching rules), so `A` and `k` have to be measured, not derived.

## In our notation
| Paper | Ours |
|---|---|
| `s` | the fair value (`fair_value`, `bots/template.py:123`) |
| `q` | the position (`plan.net` in `make`) |
| `r = s − qγσ²(T−t)` | `fair − shift`, where `shift = round(skew × q / limit)` (`bots/template.py:200`); equal when `skew = γσ²(T−t) × limit` |
| `δ^a + δ^b = (2/γ)·ln(1 + γ/k)` | `2 × make_edge` (`bots/template.py:39`); as γ → 0 the half-spread tends to `1/k` |
| `σ` | per-tick standard deviation of the fair value, per product |
| `A, k` | fill rate against quote distance from fair, measurable from `_fills.csv` and `_orders.csv` |
| `T − t` | ticks to the end of the day (`timestamp` runs 0…999,900 in Prosperity) |

## Traps
- **Two spread formulas are in circulation.** The paper's closed form is `(2/γ)·ln(1 + γ/k)`, with no `γσ²(T−t)` term (`hft-in-a-limit-order-book.md:227-229` (p. 9, checked)). Hummingbot's version, quoted in [online articles](online-articles.md), adds `γσ²(T − t)`. The paper's simulation spread of 1.29 at γ = 0.1, k = 1.5 matches the formula without the term: 20 × ln(1.0667) = 1.29 *(computed here)*. Don't mix the two when calibrating.
- **OCR:** the condition `ω > ½γ²σ²q²` came out as "ω > 1 γ 2σ 2 q 2", and `ω = ½γ²σ²(q_max + 1)²` as "ω = 1 2 γ 2σ 2 (qmax + 1)2" (`hft-in-a-limit-order-book.md:91-93` (p. 4, checked)).
- The paper's `r` is a proxy: the static reservation price, used in place of solving the HJB (3.3). The closed form is an approximation, not the optimum.
- `δ^b` and `δ^a` are distances from the **mid** `s`, not from `r`.

## Read depth
- **Read:** all sections.
- **Checked against the PDF (page images):** (2.1), the reservation prices, the infinite-horizon prices, (3.6)–(3.12) and the spread. The simulation numbers were checked against Table 1's text and recomputed for the spread.
- **Not checked:** the HJB derivation (3.3).

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
