---
title: Shearer, Byrd, Balch & Wellman, "Stability effects of arbitrage in exchange traded funds: an agent-based model" (2021)
type: source
repo: literature_md/etf-arbitrage-abm
status: partly-read
updated: 2026-10-14
---

# Shearer, Byrd, Balch & Wellman, "Stability effects of arbitrage in exchange traded funds: an agent-based model" (ICAIF 2021)

## What it is
An agent-based market with an ETF and its two underlying symbols, background traders, and ETF arbitrageurs switched on or off; equilibria by empirical game-theoretic analysis (`etf-arbitrage-abm.md:13` (p. 1)). An "impact agent" induces a mini flash crash in one underlying by sending a rapid series of marketable sell orders (`etf-arbitrage-abm.md:43` (p. 2)). From the ICAIF 2020–2024 triage; the user's first file was a copy of another paper, the `_v2` file is this one.

## Main results
- **Arbitrage helps:** with active arbitrageurs the ETF tracks its index more closely and background traders' surplus rises, from the added liquidity (`etf-arbitrage-abm.md:13` (p. 1)).
- **Shocks travel, inverted:** when one underlying crashes, arbitrage moves the *other* underlying the opposite way, since the arbitrageur trades the ETF against both legs (`etf-arbitrage-abm.md:13` (p. 1)).
- **Recovery is faster with arbitrageurs,** who buy the crashed symbol; the crash's size depends more on the market configuration than on them (`etf-arbitrage-abm.md:253` (p. 6)).
- **The arbitrageurs' rule** (`etf-arbitrage-abm.md:175` (p. 4)): trade when the ETF's price is more than a threshold ε away from the index value, either on the ETF alone or on the ETF and its legs; a less conservative variant uses mid prices instead of the touch.

## Assumptions against the Arena
- A two-symbol ETF with published weights; the Arena may hide the weights (`harder-rounds` B5).
- **Our basket mode is this arbitrageur** *(inferred)*: it trades the basket's spread to its legs past a band (`level_band`), and legs with `hedge` follow. The paper's prediction for a scripted crash in one leg: the basket strategy buys the crashed leg's basket cheap and sells the other leg, and the shock reverses faster than without it.

## In our notation
| Paper | Ours |
|---|---|
| ETF − index deviation | the basket's spread to its legs' weighted wall mids |
| threshold ε | `level_band` around `level` (`python/bots/template.py`, the `basket` branch) |
| impact agent's crash | a scripted run of market sells; the harder-round stress harness's shock |

## Traps
- The user's file "Stability Effects of Arbitrage in Exchange Traded Funds- An Agent-Based Model.pdf" is a byte-identical copy of the collective-liquidity-taking paper; `convert.sh` names the `_v2` file.

## Read depth
- **Read:** abstract, introduction, the agents including both arbitrageurs, the flash-crash results and the conclusion.
- **Skimmed:** the game-theoretic set-up and surplus tables.

## Cited by
[baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [harder-rounds](../concepts/harder-rounds.md).
