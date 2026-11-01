---
title: Guéant, Lehalle & Fernandez-Tapia, "Dealing with the inventory risk" (2013)
type: source
repo: literature_md/dealing-with-inventory-risk
status: read
updated: 2026-10-13
---

# Guéant, Lehalle & Fernandez-Tapia, "Dealing with the inventory risk: a solution to the market making problem" (Mathematics and Financial Economics, 2013)

## What it is
The Avellaneda–Stoikov model with a **hard inventory bound Q**, solved exactly (36 pages). The HJB equations reduce to a linear system of ODEs. Away from the horizon the quotes stop depending on time, and their stationary value has a closed-form approximation, which hftbacktest's GLFT examples implement ([hftbacktest](hftbacktest.md)). It extends the model to a price drift and to market impact (adverse selection). This is the model to use for a position limit, which is the Prosperity and Arena setting.

## Main results
- **Model** (`dealing-with-inventory-risk.md:61-93` (p. 4–5)):
  - Arithmetic Brownian reference price `dS = σdW`; fill intensities `λ(δ) = A·e^{−kδ}` on each side; CARA utility at T.
  - **No bid at q = Q and no ask at q = −Q.** The reference price "can be thought of as a smoothed mid-price" (`dealing-with-inventory-risk.md:75` (p. 4)).
- **Exact solution** (Propositions 1–2, Theorem 1, `dealing-with-inventory-risk.md:121-159` (p. 6–8, checked)):
  - Let `α = (k/2)γσ²` and `η = A(1 + γ/k)^{−(1 + k/γ)}`, and `M` the tridiagonal (2Q+1)-square matrix with diagonal `αq²` and off-diagonal `−η`.
  - Then `v(t) = exp(−M(T−t))·(1, …, 1)'`, and the optimal quotes are `δ^{b*}(t, q) = (1/k)·ln(v_q/v_{q+1}) + (1/γ)·ln(1 + γ/k)` and `δ^{a*}(t, q) = (1/k)·ln(v_q/v_{q−1}) + (1/γ)·ln(1 + γ/k)`.
  - That is a matrix exponential of a (2Q+1)-square matrix: 101 × 101 for a limit of 50.
- **The quotes are almost independent of t far from T** (`dealing-with-inventory-risk.md:165` (p. 8, checked)), "at odds with" Avellaneda–Stoikov's approximation. That approximation, quoted as `δ^{b*} ≈ (1/γ)·ln(1 + γ/k) + ((1 + 2q)/2)·γσ²(T − t)` with `(1 − 2q)/2` for the ask, is only the Taylor expansion near T (footnote 8, `dealing-with-inventory-risk.md:171-177` (p. 8, checked)).
- **Stationary quotes** (Theorem 2, `dealing-with-inventory-risk.md:187-205` (p. 10)): `δ_∞(q)` comes from `f⁰`, the eigenvector of `M`'s smallest eigenvalue.
- **Closed-form approximation** (`dealing-with-inventory-risk.md:225-229` (p. 11, checked)):
  - **`δ^b_∞(q) ≈ (1/γ)·ln(1 + γ/k) + ((2q + 1)/2)·√(σ²γ/(2kA) · (1 + γ/k)^{1 + k/γ})`**
  - `δ^a_∞(q) ≈ (1/γ)·ln(1 + γ/k) − ((2q − 1)/2)·√(…)`
  - **spread `ψ_∞ ≈ (2/γ)·ln(1 + γ/k) + √(σ²γ/(2kA) · (1 + γ/k)^{1 + k/γ})`**
  - Good for small `|q|`, less so near the bound (`dealing-with-inventory-risk.md:241` (p. 12)).
- **Drift `μ`** (`dealing-with-inventory-risk.md:286-288` (p. 13, checked)): both quotes shift by `(μ/(γσ²))·√(…)`, upward for a positive drift. The spread is unchanged.
- **Market impact / adverse selection** `dS = σdW + ξdN^a − ξdN^b` (`dealing-with-inventory-risk.md:294-298` (p. 14, checked)):
  - Each quote moves out by `ξ/2`, the "adverse selection" term.
  - The inventory term is scaled by `e^{kξ/4}`, the "side-effect" (`dealing-with-inventory-risk.md:334-338` (p. 15, checked), `dealing-with-inventory-risk.md:404-410` (p. 19–20)).
- **Comparative statics** (`dealing-with-inventory-risk.md:344-394` (p. 16–18)): the spread widens with `σ²` and narrows with `A` and `k`. The effect of `γ` is ambiguous.
- **Backtest practice** (`dealing-with-inventory-risk.md:416-418` (p. 20)):
  - Round quotes to the nearest tick; re-quote after a fill or a timeout.
  - `A` and `k` "have to depend at least on the actual market bid-ask spread".
  - **`γ` was set so that inventory stayed between −10 and 10 average trade sizes**, so it is a chosen parameter, not an estimated one.
  - The exponential intensity "is only suited to liquid stocks with a small bid-ask spread" (`dealing-with-inventory-risk.md:458-460` (p. 23)).

## Assumptions against the Arena
- **A hard bound is our setting.** Prosperity rejects all of a product's orders if they could breach the limit (`ARCHITECTURE.md`, matching rule 2). The paper's "no bid at Q" is the clean version of that.
- **Brownian reference price.** Same caveat as [Avellaneda–Stoikov](hft-in-a-limit-order-book.md): on a pegged product inventory risk is smaller than `σ²` suggests. The drift extension covers a deterministic trend (P4 Pepper Root's `+0.001` per timestamp, [drift](../concepts/drift-and-regime-change.md)), not mean reversion.
- **Exponential intensity and a small spread.** The authors' own caveat. Prosperity's spreads are 2–21 ticks *(checked, [micro-price](micro-price.md))*, and its fills come from bots, so `A·e^{−kδ}` must be checked against our fill data before trusting `A` and `k`.
- **Liquidation at the reference price at T, no penalty;** a penalty "would be mutatis mutandis the same" (`dealing-with-inventory-risk.md:99` (p. 5)).

## In our notation
| Paper | Ours |
|---|---|
| `S_t` (smoothed mid) | `fair` (`python/bots/template.py:370`) |
| `Q` | `limit` per product in `PARAMS` |
| `(1/γ)·ln(1 + γ/k) + ½·c₂`, with `c₂ = √(σ²γ/(2kA)·(1 + γ/k)^{1+k/γ})` | `make_edge` (the half-spread at zero inventory; `python/bots/template.py:63`) |
| `c₂` per unit of inventory | `skew / limit`: the template shifts both quotes by `round(skew × q / limit)` (`python/bots/template.py:847`), so the closed form is our linear skew with `skew = c₂ × limit` *(inferred from the two formulas)* |
| `μ/(γσ²) × c₂` | a drift shift of both quotes; not in the template |
| `ξ/2` | an extra edge on both sides for adverse selection; compare with the fill markouts in `python/arena/analysis.py` |
| `σ` | per-tick volatility of `fair`; Prosperity's tick is 100 timestamps |

## Traps
- **OCR: the square root is misplaced in every closed form.** The markdown puts `(1 + γ/k)^{1+k/γ}` outside `√(σ²γ/(2kA))`; in the PDF the root covers the whole product. This affects the base model (`dealing-with-inventory-risk.md:229` (p. 11)), the drift version (`dealing-with-inventory-risk.md:288` (p. 13)) and the impact version (`dealing-with-inventory-risk.md:334-338` (p. 15)). The base model's spread line `ψ_∞` is missing from the markdown entirely. Coded from the markdown, the skew would be off by a factor of `(1 + γ/k)^{(1+k/γ)/2}`.
- **OCR:** `η = A(1 + γ/k)^{−(1+k/γ)}` loses its `γ` in Proposition 1, and Proposition 2's `α = (k/2)γσ²` loses `k/` (`dealing-with-inventory-risk.md:125-133` (p. 6–7, checked)).
- **OCR:** in the impact model, the first ODE has `e^{−½ξ}` where the PDF has `e^{−(k/2)ξ}` (`dealing-with-inventory-risk.md:304` (p. 14)). In the drift model's limit spread, the denominator `f_q^0 f_{q+1}^0` should be `(f_q^0)²` (`dealing-with-inventory-risk.md:273` (p. 13)).
- **OCR:** footnote 8's formulas read `δ_t^{*t}` and `(1 + 2g)/2` for `δ^{b*}_t` and `(1 + 2q)/2` (`dealing-with-inventory-risk.md:171-173` (p. 8)).
- **Which Avellaneda–Stoikov?** Footnote 8 attributes the `((1 ± 2q)/2)·γσ²(T − t)` approximation to A–S, which gives a spread of `(2/γ)·ln(1 + γ/k) + γσ²(T − t)`, Hummingbot's formula. The published 2008 A–S, our copy since 2026-10-13, has exactly that spread (eq. 30); the 2006 preprint we had before did not. See [Avellaneda–Stoikov](hft-in-a-limit-order-book.md), "Traps".

## Read depth
- **Read:** sections 1–7 and the conclusion.
- **Checked against the PDF (page images):** Propositions 1–2, Theorem 1, footnote 8, Proposition 3 and the closed-form approximations (base, drift, impact), Proposition 5.
- **Not read:** the appendix proofs (`dealing-with-inventory-risk.md:493-844` (p. 25–36)).

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [optimal-market-making](optimal-market-making.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
