---
title: Fernandez-Tapia, "High-frequency trading meets online learning" (2016)
type: source
repo: literature_md/online-learning-market-making
status: partly-read
updated: 2026-10-26
---

# Fernandez-Tapia, "High-frequency trading meets online learning" (Market Microstructure and Liquidity 2(1), 2016)

## What it is
A market maker that **learns its half-spread and its off-centring while trading**, by stochastic gradient (Robbins–Monro), instead of solving a control problem with a price model. Time is cut into periods of `ΔT`; each period the maker posts `S ± δ` around the reference price, and after it updates its quotes from the period's realised payoff. Fills follow Avellaneda–Stoikov's `A·e^{−kδ}`; the price dynamics are left unspecified. The user saved the published version.

## Main results
- **Variables** (`online-learning-market-making.md:107-119` (p. 9–10, checked)): the half-spread `ψ = (δ_a + δ_b)/2` and the off-centring `θ = (δ_a − δ_b)/2`. The period's payoff is `ψN − (θ − Y_ΔT)Q`, with `N` fills, `Q` the inventory gained and `Y_ΔT` the price move: spread earned minus adverse selection.
- **The Brownian benchmark** (Theorem 1, `online-learning-market-making.md:208-210` (p. 13, checked)): `ψ* = (1/k)·(k²σ²ΔT − 1 + e^{−k²σ²ΔT/2}) / (1 − e^{−k²σ²ΔT/2})` and `θ* = 0`. As `ΔT → 0` it tends to `1/k`, GLFT's half-spread at zero risk aversion *(checked: the limit, and a 4,000-path simulation of `1/k + b/a` from eqs. 19–21 at σ = 1.2, k = 0.3: 3.549 against the formula's 3.552 at ΔT = 1)*. The longer a quote lives relative to the price's variance, the wider it should be.
- **The update** (eqs. 22–24, Theorem 3; `online-learning-market-making.md:256` (p. 14, checked), `online-learning-market-making.md:266-268` (p. 14, checked), `online-learning-market-making.md:276` (p. 15)): the gradient of the period's expected payoff given the price path is a 2×2 matrix in `(1 − kψ, k(θ − y))` times the expected fills and inventory. It needs `k` but **not** the price model, and `A` only scales the step. Multiplied by `ρ = e^{−k(|θ| − ψ)}` it satisfies Robbins–Monro and converges for i.i.d. periods. The `θ` update follows the last period's price move, so it is trend-following (footnote 4).
- **Step size** (§4.3, `online-learning-market-making.md:324-330` (p. 17)): a `1/n` step can freeze before converging; a slower step `n^{−0.6}` with Ruppert–Polyak averaging reaches the optimum.
- **Inventory** is not part of the stationary problem; §5 adds a penalty term (skimmed).

## Assumptions against the Arena
- **Stationary periods.** It learns one `(ψ, θ)` for the whole session ("a key hypothesis", `online-learning-market-making.md:374` (p. 20)); a regime change mid-round restarts the learning.
- **Enough periods.** The examples need hundreds of updates. A Prosperity day is 10,000 ticks, so even with a quote that lives one tick there is room, but the gradient is noisy per tick *(inferred)*.
- **`k` is known.** It has to be measured from our own fills first.

## In our notation
| Paper | Ours |
|---|---|
| `ψ` | `make_edge` (`python/bots/template.py:45`) |
| `θ` | the template's quote shift (`skew × q / limit`); here it follows the price, not inventory |
| `ΔT` | how long a quote lives: one tick in the default engine mode |
| the update | `learn_edge` in `python/bots/research/online_edge.py` (a copy of the template): a finite-difference sign step on passive fills' markouts in place of his gradient, so it needs no `k`; state in `traderData` (`IDEAS.md`, "Learning `make_edge` online") |

## Traps
- **Typo in the paper itself:** the numerical example reports `ψ* = 2.52` for `T = 30, σ = 1.2, A = 0.9, k = 0.3` (`online-learning-market-making.md:324-330` (p. 17)), below `1/k = 3.33`. Theorem 1, and `ψ* = 1/k + b/a` with `b ≥ 0`, rule that out for any `σ` and `ΔT` *(checked by simulation above)*. Use the theorem, not the example.
- **Typo in the paper itself:** eqs. 23–24 subtract the gradient while Theorem 3 adds it (`online-learning-market-making.md:266-268` (p. 14), `online-learning-market-making.md:276` (p. 15)). For a maximum, it is added.

## Read depth
- **Read:** sections 1–4 (pp. 1–19) on the page images.
- **Skimmed:** section 5 (inventory penalty) and the conclusion.
- **Unread:** the appendix proofs (pp. 26–40).

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md).
