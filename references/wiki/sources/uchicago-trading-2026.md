---
title: UChicago Trading Competition 2026 (algorithmic case, 1st)
type: source
repo: uchicago-trading-2026
status: partly-read
updated: 2026-10-10
---

# UChicago Trading Competition 2026, algorithmic case (1st of 41, their claim)

## What it is
A README (255 lines) and the organisers' `case-packet.pdf` (11 pages, **two** cases). No code. No licence file. Case 1 is a live exchange shared with the other teams, run locally by each team at the event, on the organisers' own platform; rounds of 15 minutes (10 "days" of 90 seconds, 5 ticks per second). Case 2 is a **file-upload** case.

## Layout and code map
README: format `README.md:77`, assets `README.md:93`, ETF arbitrage `README.md:123`, directional signals `README.md:138`, earnings `README.md:148`, NLP on Fed headlines `README.md:158`, put–call parity `README.md:181`, box spread `README.md:189`, the manual-trading loss `README.md:197`, **risk architecture** `README.md:205`, results `README.md:217`, **reflections** `README.md:227`.

## What carries over
- **Case 2 rules** (`pdftotext case-packet.pdf`): a Python stub and training data are released, you upload code by a deadline, **the default environment is Python 3.12 with only NumPy, pandas, scikit-learn and SciPy**, more packages can be requested, a pre-deadline compile/run test exists whose result "will not be indicative", **code that fails at any time step scores 0**, and ranking is by Sharpe ratio on a held-out 12 months. The closest analogue in the clones to the Arena's portal.
- Case 1: "exceeding risk limits will result in the rejection of your entire order"; limits were announced beforehand and "subject to change on the day"; later rounds have faster-reacting market makers and heavier scoring weights.
- Scoring (`README.md:83`): `(rank − 1)²` per round, lowest total wins, later rounds weighted more: a consistency-rewarding format.
- ETF arbitrage was the steady earner (`README.md:127-136`): sell the three at the bid / buy the ETF at the ask when the sum exceeds the ETF ask plus the 5-tick swap fee, swap, flatten. Directional trades on news gave the large jumps; they calibrated the P/E from the first live quote instead of the packet's constant (`README.md:152-154`).
- Market making and options both failed there (`README.md:113-121`, `README.md:181-195`).
- Position architecture (`README.md:205-213`): 150 of the 200 limit reserved for directional trades, 40 for the arb bot, 10 buffer.
- Defence against book-sniping and the stopping rule (`README.md:233`); the manual-trading loss when the exchange froze (`README.md:203`, `README.md:231`).

## Traps
A one-team account of one live event; the ETF/P-E details depend on that case's rules.

## Read depth
- **Read:** `README.md:77-255`; the packet passages on Case 1 rules and Case 2 (via `pdftotext` and `grep`).
- **Unread:** `README.md:1-76`; the packet's other pages.

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [informed-counterparties](../concepts/informed-counterparties.md).
