---
title: jmerle's Prosperity 2 backtester
type: source
repo: prosperity2-backtester-jmerle
status: mapped
updated: 2026-10-10
---

# jmerle's Prosperity 2 backtester (MIT, last commit 2024-04-23)

## What it is
The same program as [the Prosperity 3 one](prosperity3-backtester-jmerle.md) for the 2024 edition (`prosperity2bt/`: `runner.py`, `data.py`, `models.py`, `file_reader.py`). Data lives in `prosperity2bt/resources/round{0,1,3,4,6,7}`.

## Layout and code map
`LIMITS` `prosperity2bt/data.py:7`: Amethysts 20, Starfruit 20, Orchids 100, Chocolate 250, Strawberries 350, Roses 60, Gift basket 60, Coconut 300, Coconut coupon 600. Trade files come in two variants: `*_nn.csv` anonymous and `*_wn.csv` with buyer/seller names, present for rounds 1, 3 and 4 *(checked: file listing)*; our loader handles both.

## What carries over
Practice data for the earliest edition (stable 10,000 Amethysts, random-walk Starfruit, baskets, coconut option). Prosperity 3's Resin data was identical to Prosperity 2's Amethysts data (`prosperity3-backtester-jmerle/README.md:79`): organisers reuse generators.

## Traps
Older datamodel; no conversions.

## Read depth
- **Read:** the README head, `LIMITS`, the resource folder listing.
- **Unread:** everything else.

## Cited by
[backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md).
