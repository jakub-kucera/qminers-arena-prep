---
title: Gu et al., "The effect of liquidity on the spoofability of financial markets" (ICAIF 2024)
type: source
repo: literature_md/spoofability-and-liquidity
status: read
updated: 2026-10-14
---

# Gu, Wang, Mascioli, Chakraborty, Savani, Turocy & Wellman, "The effect of liquidity on the spoofability of financial markets" (ICAIF 2024)

## What it is
A 9-page simulation study from the [spoofing-abm](spoofing-abm.md) line of work. It adds a ladder market maker, whose spread and rung spacing set the market's liquidity, and asks how liquidity changes what a spoofer earns and does (`spoofability-and-liquidity.md:19` (p. 1)).

The agent split it out of `literature_raw/ICAIF_2024_proceedings.pdf` (PDF pages 260–268; `references/SEARCH_LOG.md` gives the printed page, 239) into `literature_raw/spoofability-and-liquidity.pdf` on 2026-10-14. The simulator, PyMarketSim, is public (`spoofability-and-liquidity.md:190` (p. 4)). It is a Python implementation of the whole model, and the nearest ready-made code for our own day generator (A1 in [harder-rounds](../concepts/harder-rounds.md)).

## Main results
- **The market** (`spoofability-and-liquidity.md:172-178` (p. 4)):
  - 24 background traders (12 ZI, 12 HBL), one market maker and one spoofer, over `T = 10⁴` steps;
  - the fundamental: `r̄ = 10⁵`, `κ = 0.05`, shock variance 10⁴;
  - the background traders arrive every 500 steps each, so about every 20 steps in all.
  
  Unlike in the 2017 model, they observe the current fundamental exactly and project it to the close: `r̃_t = (1−(1−κ)^{T−t})·r̄ + (1−κ)^{T−t}·r_t` (`spoofability-and-liquidity.md:87` (p. 3, checked)).
- **The market maker** arrives about every 29 steps. It cancels its orders, then posts a ladder of `K = 8` one-unit orders each side, spaced `ξ` ticks apart from `r̃_t ∓ ω/2`, trimmed so that none crosses the book (`spoofability-and-liquidity.md:124` (p. 3, checked)). Liquidity is set by `ξ ∈ {10, 50, 100}` and `ω ∈ {16, 64, 256}`, from A1 (dense and tight) to C3 (sparse and wide) (Table 1, `spoofability-and-liquidity.md:200` (p. 5, checked); values from the PDF's text layer).
- **The spoofer** posts a 200-lot bid one tick below the best bid and a one-unit sell at `r̃_t + o` (`spoofability-and-liquidity.md:130` (p. 4, checked)). Three ways to set the offset `o`:
  - **baseline:** `o = 1` (`spoofability-and-liquidity.md:132` (p. 4));
  - **tuned:** a grid over 1–200 in steps of 10 (`spoofability-and-liquidity.md:134` (p. 4));
  - **learned:** a PPO policy on time left, the best bid and ask, the fair estimate, the mid's move, volume and queue imbalance, volatility and RSI (`spoofability-and-liquidity.md:136` (p. 4)).
- **Liquidity is the defence.** In liquid markets spoofing is "substantially less profitable and less detrimental to other traders" (`spoofability-and-liquidity.md:19` (p. 1)). The tuned offset grows from 10 ticks in A1 to 140 in C3 (Table 2, `spoofability-and-liquidity.md:255` (p. 6)).
- **Two regimes:**
  - **Liquid:** many small-margin sales (`spoofability-and-liquidity.md:257` (p. 6)).
  - **Illiquid:** few high-margin ones, where the book-reading traders lose most (`spoofability-and-liquidity.md:267` (p. 7)).
  
  The switch is sharp, at about B1's liquidity: a critical threshold (`spoofability-and-liquidity.md:273` (p. 7)).
- **Speed matters to the spoofer, most in liquid markets.** Arriving every 50 steps instead of every 170, the spoofer gets its fake bid hit less often, sells more, and earns 13–35% more, the most in the liquid A markets (Table 3, `spoofability-and-liquidity.md:281` (p. 7), `spoofability-and-liquidity.md:311` (p. 8)).
- **Why liquidity protects, two mechanisms:**
  - **Belief stabilisation:** the market maker's resting asks near fair offset the fake bid in what learners read (`spoofability-and-liquidity.md:313` (p. 8)).
  - **Order competition:** the market maker's asks sit at the top of the book and sell into the inflated bids before the spoofer can (`spoofability-and-liquidity.md:321` (p. 8)).

## Assumptions against the Arena
- **The market maker quotes around the true fundamental.** It is informed, the way Prosperity's wall is the market maker's fair ([fair value](../concepts/fair-value-and-wall-mid.md)). A spoof that moves learners still can't move the market maker.
- **Single-unit traders, one spoofer, and averages over 40,000 runs.** The regimes are statistical, not something one Arena day would show.

## In our notation
- **Liquidity here is the market maker's `ω` and `ξ`**: the spread and depth that `arena.diagnose` reports per product. A product whose spread and gaps between levels are wide is the C regime, where a fake wall moves book readers most. On such a product, read fair from the market maker's wall size (`sized_mid`), not from any large level, and expect D3 there first *(inferred)*.
- **In a shared market, our own quotes add liquidity.** By the order-competition mechanism, a tight two-sided quote near fair limits what a spoofer can sell into the bids it inflates, which supports quoting through a spoof rather than following it *(inferred)*.
- **PyMarketSim** is a candidate base for the A1 generator: it already implements the fundamental, the ZI and HBL traders, the ladder market maker and the spoofer. Read its code before writing our own.

## Traps
- **OCR: Table 1 is garbled** (line 200): wrong headers ("A3 A2 A3 …") and wrong values. The PDF has `ξ` = 10 / 50 / 100 for columns 1 / 2 / 3 of each letter, `ω` = 16 / 64 / 256 for A / B / C, and `K` = 8 throughout.
- **In the paper itself:** the truncation condition for buy orders lacks a `ξ` (`B_t − (K − x − 1)` on line 128; the PDF's text layer has the same).
- **The spoofer is shielded and reacts within its arrival interval.** The finding that faster spoofers earn more is about the simulated arrival rate, not CPU speed.

## Read depth
- **Read:** the whole paper; Tables 1–3 read from the PDF's text layer.
- **Not read:** PyMarketSim's code.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [spoofing-abm](spoofing-abm.md).
