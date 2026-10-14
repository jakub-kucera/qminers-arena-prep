---
title: Acero, Plank & Zhang, "RL with Hawkes-structured networks for market making" (2026)
type: source
repo: literature_md/hawkes-structured-mm
status: read
updated: 2026-10-14
---

# Acero, Plank & Zhang, "Reinforcement learning with Hawkes-structured networks for market making" (ICAIF 2026 preprint)

## What it is
Avellaneda–Stoikov with market orders that excite more market orders (Hawkes processes with general kernels, including power laws), solved by model-free RL. The quoting policy sees the order-flow history only through a few exponentially weighted counts of past arrivals per side. A theorem bounds the loss from that truncation, and the network learns the decay rates end to end (`hawkes-structured-mm.md:11` (p. 1)). This is arXiv 2610.16524v1 (8 pages, accepted at ICAIF 2026), downloaded by the agent. No code is linked.

## Main results
- **The model** (`hawkes-structured-mm.md:61-83` (p. 2, checked)): the buy and sell market orders are independent Hawkes processes, `λ_t^c = λ_0^c(t) + ∫_{[0,t)} g^c(t − s) dM_s^c` (the PDF integrates over `[0, t)`; the markdown has `[0, t]`). An arrival fills the quote with probability `p^c(δ^c)`, and the objective is A–S's: terminal cash plus inventory marked at `S_T − κQ_T`, minus `γ∫Q_t² dt` (eq. 2).
- **The features** (eq. 4, `hawkes-structured-mm.md:141` (p. 3, checked)): `h_j^c(t) = α_j^c Σ_{i: τ_i ≤ t, c_i = c} e^{−β_j^c (t − τ_i)}` for `j = 1..p`. With a kernel that is a mixture of exponentials, these are an exact Markov state. For other kernels, Theorem 1 bounds the regret by the kernel's approximation error (`hawkes-structured-mm.md:130` (p. 3)). In practice the sum runs over the last `L = 32` events (`hawkes-structured-mm.md:162` (p. 4)).
- **Results** (Table 1, `hawkes-structured-mm.md:205` (p. 5)), over 30 seeds:
  - **Against other networks:** the Hawkes-structured network is best on the five settings where the intensity matters. The gain over the best generic network is +5–32%, largest for a power-law kernel (+32.5%), cross-excitation between two assets (+16.6%) and a switching kernel (+11.1%).
  - **Against no memory:** a network without history is 36–57% worse.
  - **The plain exponential-kernel controls:** it ties a network fed the stacked raw history. The authors say the optimal spread depends only weakly on the intensity there (`hawkes-structured-mm.md:196` (p. 5)).
- **Two decay rates go a long way.** The default is two modes per side, initialised at a fast and a slow rate (6.0 and 0.4, `hawkes-structured-mm.md:190` (p. 4)). For a sum of three exponentials, errors floor at six modes. A power law never gets exact (`hawkes-structured-mm.md:245` (p. 7)).
- **The setting:** fills with probability `exp(−10δ)`, an inventory cap of 5, and a mid that trades don't move (`ε± = 0`, `hawkes-structured-mm.md:188` (p. 4, checked)). All of the value comes from predicting the arrival intensity, none from adverse selection.

## Assumptions against the Arena
- **On Prosperity data there is nothing to model** *(checked: `uv run python -m experiments.trade_clustering`, 2026-10-14)*. On P3 and P4 round 1, the chance of a market trade in the 1, 5 or 20 ticks after one, over its unconditional chance, is 0.90–1.04. A buy after a buy is 0.93–1.12. The exchange's takers arrive memorylessly at the tick scale, so the template's state (book plus position) misses nothing that this paper adds (`IDEAS.md`, "Quoting from clustered order flow", `dropped here`).
- **Where it could matter:** a shared market where rival bots react to each other's trades, or an Arena whose takers are self-exciting. Re-run the script on the Arena's days. If a product clusters, the cheap stdlib version is two decaying trade counts per side (one fast, one slow) feeding a `make_edge` or size adjustment, tuned by grid rather than RL.
- **Ticks are not continuous time.** Prosperity has at most one snapshot of trades per tick, so `τ_i` becomes a tick index and the decay is per tick.

## In our notation
For product `X`, keep `h_fast` and `h_slow` per side in `traderData`. Each tick, multiply by `e^{−β}` and add 1 if a market trade hit that side. Widen `make_edge` on the side whose count is high. It costs four floats per product.

## Traps
- **Everything is simulated.** The kernels are the authors' choice, and no real data is used, so the gains measure how well each network represents a known Hawkes process. They don't show that order flow in any market behaves like one.
- **The table is an image.** Table 1's numbers are quoted from the text, not read from the table.
- **The branching ratios are high** (0.75–0.95). With a ratio of 0, the setting reduces to plain A–S, where the features are useless by construction.

## Read depth
- **Read:** sections 1, 3.1, 3.2.3, 4, 5 and 7.
- **Skimmed:** the proof (section 6) and Proposition 1.
- **Unread:** the figures and Table 1 as images.

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md).
