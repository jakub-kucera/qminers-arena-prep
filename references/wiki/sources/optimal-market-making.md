---
title: Guéant, "Optimal market making" (2017)
type: source
repo: literature_md/optimal-market-making
status: partly-read
updated: 2026-10-12
---

# Guéant, "Optimal market making" (arXiv:1605.01862; Applied Mathematical Finance, 2017)

## What it is
A 43-page generalisation of [GLFT](dealing-with-inventory-risk.md) in three directions:
- any decreasing fill-intensity function, not only `A·e^{−kδ}`;
- both objective families in the literature: utility of terminal wealth (Model A, A–S and GLFT) and expected PnL minus a running inventory penalty (Model B, Cartea–Jaimungal);
- **several correlated assets**, with closed-form approximations of the quotes.

It is the paper for "one book, many products, one risk budget", the shape of Prosperity's later rounds and probably the Arena's. hftbacktest's `Making Multiple Markets.ipynb` builds on it ([hftbacktest](hftbacktest.md)).

## Main results
- **Two objectives** (`optimal-market-making.md:120-135` (p. 6)):
  - **Model A** maximises `E[−exp(−γ(X_T + q_T S_T − ℓ(|q_T|)))]`.
  - **Model B** maximises `E[X_T + q_T S_T − ℓ(|q_T|) − ½γσ²∫q²dt]`.
  - Both reduce to the same ODE system with a parameter `ξ`: `ξ = γ` in A and `ξ = 0` in B. `ξ` acts as aversion to *non-execution* risk and `γ` as aversion to *price* risk (`optimal-market-making.md:599-605` (p. 18, unchecked)).
- **Bounded inventory:** no bid at `q = Q` and no ask at `q = −Q`, as in GLFT (`optimal-market-making.md:63-75` (p. 4, unchecked)).
- **Stationary closed form** for exponential intensities with trade size `Δ` (eqs. 4.6–4.7, `optimal-market-making.md:733` (p. 21, checked)):
  - **Model A:** `δ^b(q) ≈ (1/(ξΔ))·ln(1 + ξΔ/k) + ((2q + Δ)/2)·√(γσ²/(2AΔk) · (1 + ξΔ/k)^{k/(ξΔ)+1})`. With `Δ = 1` and `ξ = γ` this is exactly GLFT.
  - **Model B:** `δ^b(q) ≈ 1/k + ((2q + Δ)/2)·√(γσ²e/(2AΔk))`. The ask is the mirror image.
- **The spread doesn't depend on q, and the skew is linear in q** (eqs. 4.8–4.9, `optimal-market-making.md:758-761` (p. 22, checked)):
  - spread `= (2/k) + Δ·√(γσ²e/(2AΔk))` in Model B;
  - `δ^b − δ^a = 2q·√(…)`;
  - the spread is affine in `σ` and the skew linear in `σ`.
  - "Replacing Λ by βΛ is equivalent to replacing σ² by σ²/β": more liquidity acts like less volatility (`optimal-market-making.md:779` (p. 22)).
- **Multi-asset closed form** (eqs. 5.18–5.19, `optimal-market-making.md:1013-1060` (p. 29–30, checked)):
  - With covariance `Σ` and `D = diag(H^{i″}_ξ(0))`, let `Γ = D^{−½}(D^{½} Σ D^{½})^{½} D^{−½}`.
  - Then asset `i`'s bid is `δ̃^{i*}( √(γ/2)·(Γ^{ii}(2qⁱ + Δⁱ)/2 + Σ_{j≠i} Γ^{ij} q^j) )`, and the ask the same with the sign flipped.
  - **Each product's skew depends on the inventory of all correlated products** through the off-diagonal `Γ^{ij}`.
  - For two credit indices, the more correlated they are, the more a long position in one makes the bid in the other conservative (`optimal-market-making.md:1222` (p. 41)).
- **Why multi-asset matters** (`optimal-market-making.md:794` (p. 23)): a short position in one asset against an almost equal long in a correlated one may need no skew at all, "contrary to what single-asset market making models would suggest".
- The author's own scope: models à la A–S suit "a quote-driven market, or an order-driven market if the tick sizes of the securities are small". On stocks they fail for two reasons: discrete prices and queue priority (`optimal-market-making.md:55-57` (p. 3–4)).

## Assumptions against the Arena
- **Independent Brownian prices with a fixed covariance.** Prosperity's related products are often *exactly* linked (baskets of known components, [baskets](../concepts/baskets-and-fixed-sums.md)) rather than correlated. For a basket, `Σ` is close to singular, and the paper assumes a non-singular correlation matrix (`optimal-market-making.md:806` (p. 24)).
- **Exponential intensity, small tick.** Same caveat as GLFT. Prosperity's 2–21-tick spreads and bot fills mean `A_i` and `k_i` must be measured per product.
- **Model B is the closer fit to a PnL-scored competition:** it maximises expected PnL with an inventory penalty, not a utility. Its quotes have no `log` term: half-spread `1/k` at zero inventory *(inferred from eqs. 4.6–4.9)*.
- **The paper's application is two credit indices,** not an order book with bots.

## In our notation
| Paper | Ours |
|---|---|
| `Sⁱ` | `fair` per product (`python/bots/template.py:347`) |
| `Qⁱ`, `Δⁱ` | `limit` per product; `Δ` = 1 lot (or `make_size`) |
| Model B half-spread at q = 0: `1/k + ½·√(γσ²e/(2Ak))` | `make_edge` (`python/bots/template.py:55`) |
| skew per unit `√(γσ²e/(2Ak))` (Model B) | `skew / limit` (`python/bots/template.py:796`), *inferred* |
| `Σ_{j≠i} Γ^{ij} q^j` | nothing yet. `python/bots/template.py` trades products independently; the `TODO_DONE.md` item "Add multi-product strategies" asks for a cross-product hook in STRATEGY |
| `Σ` | covariance of per-tick `fair` changes across products, estimable from the CSVs |

## Traps
- **OCR: the closed forms (4.6)–(4.9) are wrong in two places** (`optimal-market-making.md:733-761` (p. 21–22)):
  - the factor `(1 + ξΔ/k)^{…}` is printed outside the square root, but the PDF has it inside;
  - the exponent reads `k/(ξΔ + 1)` in (4.6)–(4.8), but the PDF has `k/(ξΔ) + 1`.
  - (4.6) also starts with "o_approx" for `δ_approx`.
- **OCR:** eq. (2.3), the intensity with the inventory cut-off, is garbled ("χ_t^a = Λ^b(δ_t^a)1_{q_t−−Q}") (`optimal-market-making.md:89` (p. 5)); the PDF defines `λ^b = Λ^b(δ^b)1_{q<Q}` and `λ^a = Λ^a(δ^a)1_{q>−Q}`. The same garbling recurs in (5.3).
- The approximations are heuristic. The paper's own Section 6 compares them with the exact ODE solution and says the exact spread does depend on `q` (footnote 19, `optimal-market-making.md:796` (p. 23)).

## Read depth
- **Read:** sections 1–2, 3.4, 4 and 5.1, 5.4; the end of Section 6 and the conclusion.
- **Checked against the PDF (page images):** (4.3)–(4.9), (5.17)–(5.20) and `Γ`.
- **Mapped only:** Section 3 (existence and uniqueness proofs, `optimal-market-making.md:136-598` (p. 6–18)), Section 5.2–5.3, and most of Section 6 (the CDX calibration and figures).

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [many-products-architecture](../concepts/many-products-architecture.md).
