---
title: Ahuja, Papanicolaou, Ren & Yang, "Limit order trading with a mean reverting reference price" (2017)
type: source
repo: literature_md/mean-reverting-reference-price
status: read
updated: 2026-10-13
---

# Ahuja, Papanicolaou, Ren & Yang, "Limit order trading with a mean reverting reference price" (Risk and Decision Analysis 6, 2017, pp. 121–136)

## What it is
Avellaneda–Stoikov's market maker (Poisson fills `A·e^{−κδ}`, exponential utility at T) with the reference price an Ornstein–Uhlenbeck process instead of a Brownian motion, solved numerically over many mean-reversion cycles. It is the theory for a product that returns to a level, the case of [contradictions](../contradictions.md) row 1. The user saved the published version on 2026-10-13.

## Main results
- **Model** (`mean-reverting-reference-price.md:49` (p. 3, checked)): `dS_t = α(μ − S_t)dt + σdB_t`, fills `Poi(A·e^{−κδ})` (`mean-reverting-reference-price.md:75` (p. 3, checked)). The scaling `t̃ = αt`, `p̃ = γp` leaves three parameters, `Ã = A/α`, `κ̃ = κ/γ`, `σ̃ = γσ/√α` (`mean-reverting-reference-price.md:155` (p. 5, checked)).
- **Far from the end, constant quotes** (eqs. 27, 35; `mean-reverting-reference-price.md:236` (p. 6, checked), `mean-reverting-reference-price.md:305` (p. 8, checked)): the optimal prices converge to `p^a = μ + (1/γ)·log(1 + γ/κ)` and `p^b = μ − (1/γ)·log(1 + γ/κ)`, independent of the current price and of inventory. Equivalently `v(τ, q, s) − v(τ, q − 1, s) → μ`: a unit of inventory is worth the long-run mean (eq. 28). The trader earns from buying low and selling high around μ, "analogous to a pairs trading strategy" (`mean-reverting-reference-price.md:37` (p. 2)).
- **Three regimes** (`mean-reverting-reference-price.md:31-32` (p. 2), `mean-reverting-reference-price.md:330-338` (p. 9, checked)): about one reversion cycle from the end the quotes track the price; from about four cycles out they ignore the price and move only with inventory; and only far out (800 cycles with their parameters) do they stop depending on inventory too. The intermediate regime "can be very long"; it is shorter when the market is more liquid (larger `A` and `κ`) (`mean-reverting-reference-price.md:362` (p. 11)).
- **The inventory skew in the intermediate regime** (Zhang's small-κ linearisation, eq. 31, `mean-reverting-reference-price.md:268` (p. 7, checked)): in scaled units the quotes move by `σ̃²/2` per unit of inventory. Unscaled, that is `γσ²/(2α)` per unit, i.e. **γ times the stationary variance of the price** *(derived here from eq. 31 and the scaling)*. Avellaneda–Stoikov's `γσ²(T − t)` is γ times the variance over the time left; for an OU price that variance saturates at `σ²/(2α)`.
- **Status:** numerical (two schemes that agree, plus an equilibrium check); "the proof remains open" (`mean-reverting-reference-price.md:456` (p. 12)).

## Assumptions against the Arena
- **Fills depend only on the distance from the reference price**, not on where the book is. With a fixed quote around μ and the market away from μ, the model still fills the far side at a reduced rate; in Prosperity, an order behind the touch does not fill at all. *Checked on P4 rounds 1–2, Osmium, 6 days* (`uv run python -m arena.grid python/bots/template.py 1 2 --data p4 --set PARAMS.ASH_COATED_OSMIUM.fixed_fair=10000 --grid PARAMS.ASH_COATED_OSMIUM.fair=fixed,wall_mid --grid PARAMS.ASH_COATED_OSMIUM.skew=0,1,2,4,8 --modes all,worse`, 2026-10-13): Osmium makes 113.8k with `wall_mid` and no skew, 99.2k with a fixed 10,000 and no skew (−13%). Skew lowers both, monotonically (`wall_mid`: 113.3k at 1, 110.0k at 2, 93.4k at 8; under `worse` fills, 108.7k at 1). So the *no skew* half of the prediction holds on Prosperity data and the *ignore the price* half does not. Recorded in `IDEAS.md`.
- **No hard limit in the analysis**, which the split-step scheme only imposes for numerics.
- **The level is known.** On Prosperity data some levels hold across days and some drift ([trading toward a level](../../../IDEAS.md)).
- **How many cycles a day?** P4 Osmium's wall mid reverts to a level over about 1,000 ticks (`arena.diagnose 1 --data p4`, *checked*), so a 10,000-tick day is about ten cycles: the intermediate regime, where the paper says to ignore price moves and skew a little with inventory.

## In our notation
| Paper | Ours |
|---|---|
| `μ` | a fixed fair (`fair: "fixed"`, `fixed_fair`), or the template's `level` |
| constant quotes `μ ± (1/γ)·log(1 + γ/κ)` | `fair: "fixed"` with `make_edge = (1/γ)·log(1 + γ/κ)` and `skew` 0 |
| skew `γσ²/(2α)` per unit | `skew = γσ²/(2α) × limit` (`python/bots/template.py:47`) |
| tracking quotes near the end | `fair: "wall_mid"` |

## Traps
- The figures plot prices **before** the γ-scaling, the equations after it (`mean-reverting-reference-price.md:362` (p. 11)).
- Zhang's skew is valid only for small κ and small q (the paper's own caveat after eq. 31).

## Read depth
- **Read:** sections 1–7 (pp. 1–12), checked on the page images: eqs. 1, 5, 13, 16–18, 27–28, 31, 33, 35 and the regime figures.
- **Unread:** the appendix on the numerical schemes (pp. 13–16).

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [contradictions](../contradictions.md).
