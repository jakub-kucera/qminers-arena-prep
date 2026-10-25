---
title: Jerome, Palmer & Savani, "Market making with scaled beta policies" (2022)
type: source
repo: literature_md/scaled-beta-policies
status: partly-read
updated: 2026-10-14
---

# Jerome, Palmer & Savani, "Market making with scaled beta policies" (ICAIF 2022)

## What it is
A way to describe a market maker's quotes as a volume profile over many price levels, a scaled beta distribution on each side, covering single-level quotes, uniform "ladders" and quoting at the touch as special cases (`scaled-beta-policies.md:11` (p. 1)). Tested in a simulator replaying LOBSTER data with 50 levels a side (`scaled-beta-policies.md:13` (p. 1)). From the ICAIF 2020–2024 triage.

## Main results
- **Inventory control through the volume profile:** clearing inventory with market orders is costly, and a policy that skews the profile, more volume near the best on the side that reduces inventory and less on the other, controls inventory "using only limit orders" (`scaled-beta-policies.md:85` (p. 3)).

## Assumptions against the Arena
- Many levels and resting orders with queue places; in Prosperity orders live one tick.

## In our notation
The template's `size_skew` scales one quote per side by inventory (`python/bots/template.py:48`); a beta profile is the many-level version. In `IDEAS.md`, size skew on Kelp was best at 0.

## Traps
- None found.

## Read depth
- **Read:** abstract, introduction and contributions.
- **Skimmed:** the experiments.

## Cited by
[market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
