---
title: Vyetrenko et al., "Get real: realism metrics for robust limit order book market simulations" (2019)
type: source
repo: literature_md/lob-simulation-realism
status: read
updated: 2026-10-14
---

# Vyetrenko et al., "Get real: realism metrics for robust limit order book market simulations" (arXiv:1912.04941, 2019)

## What it is
An 11-page catalogue of the stylised facts a simulated limit order book should reproduce, from J.P. Morgan AI Research. It tests two ABIDES configurations against real data. For us it is the acceptance test for a day generator (A1 in [harder-rounds](../concepts/harder-rounds.md)): a generated day should look like the Arena's download before we tune on it. It was on `docs/MANUAL_TODO.md` E as an ACM item, and the agent fetched it from arXiv on 2026-10-14.

## Main results
- **Why replay is not enough:** "simple market replay of historical data is not sufficient for back testing or strategy construction", because the market's response to our orders is missing (`lob-simulation-realism.md:29` (p. 2)). This is the same gap as probe 17 in `ON_THE_DAY.md`.
- **The catalogue:**
  - **Returns** (`lob-simulation-realism.md:79-83` (p. 4)): no autocorrelation beyond about 20 minutes, heavy tails, volatility clustering (the autocorrelation of squared returns), and long-range dependence of absolute returns.
  - **Order flow** (`lob-simulation-realism.md:92-98` (p. 5)): best-level volumes Gamma-distributed, power-law order sizes, gamma or lognormal counts per window, Weibull inter-arrival times.
  - **Intraday patterns** (`lob-simulation-realism.md:105` (p. 5)).
  - **Impact as a power law of participation** (`lob-simulation-realism.md:114-118` (p. 5–6, checked); checked against the PDF's text layer): `P_τ = |V_buy,τ − V_sell,τ|/(V_buy,τ + V_sell,τ)` per window, binned, fitted as `M_i ~ α·P_i^β`.
- **The configurations tested:**
  - **`rmsc01`:** 1 market maker, 50 ZI, 25 HBL and 24 momentum agents (`lob-simulation-realism.md:146` (p. 7)).
    - The market maker re-quotes the top N levels every 10 s (`lob-simulation-realism.md:140` (p. 6)).
    - The momentum agents compare 20- and 50-observation means (`lob-simulation-realism.md:142` (p. 6)).
  - **`sparse_zi_100`:** 100 ZI agents.

  `rmsc01` is closer to real data, but both miss:
  - the absence of return autocorrelation (`lob-simulation-realism.md:160` (p. 7));
  - the U-shaped intraday volume (`rmsc01` shows the reverse, `lob-simulation-realism.md:169` (p. 7));
  - Weibull inter-arrival times.

  The authors expect learning agents are needed to reproduce herding (`lob-simulation-realism.md:185` (p. 8)).

## Assumptions against the Arena
- **The reference is real equities.** The Arena's market is a simulation too, so the target is the Arena's download, not NASDAQ. Use the catalogue as a list of statistics to compare, not as the values to hit *(inferred)*.
- **Prosperity's data already breaks several facts.** Its mid reverts at one tick (`arena.diagnose`'s AC1 of about −0.5 on Kelp), which is the bid–ask bounce of a bot-made book. A generator should match the source it stands in for, not textbook stylised facts.

## In our notation
- `arena.diagnose` already measures part of the catalogue: the mid's AC1 and noise, drift, trade-sign persistence `C(1)` and the move after trades. A generator's day should give a `diagnose` table within the spread of the real days' tables. That is the acceptance test.
- The participation-impact fit is what probe 17 measures for our own takes, and what A2's slicing would be tuned on.

## Traps
- **`P_i` averages `ΔP_τ`** on line 118, where the definition implies `P_τ`. The PDF's text layer has the same, so it is the paper's typo, not OCR.
- **The participation is unsigned** (an absolute value), while `Δm_τ` is signed. Averaging signed moves over bins of unsigned participation would cancel buys against sells. To fit impact, sign the move by the side of the imbalance *(inferred)*.

## Read depth
- **Read:** the whole paper, from the text layer. Figures read from their captions.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [abides-simulator](abides-simulator.md).
