---
title: Wang & Wellman, "Market manipulation: an adversarial learning framework for detection and evasion" (2020)
type: source
repo: literature_md/manipulation-detection-evasion
status: partly-read
updated: 2026-10-14
---

# Wang & Wellman, "Market manipulation: an adversarial learning framework for detection and evasion" (IJCAI 2020)

## What it is
A generator that rewrites a spoofer's order stream to look like an ordinary trader's while keeping its effect, a discriminator that tries to tell them apart, and an agent-based simulator that checks the effect is kept (`manipulation-detection-evasion.md:11` (p. 1)). From the IJCAI 2020 proceedings site.

## Main results
- **Spoofing can be disguised:** adapted streams mimic a market maker's quoting pattern, look unlike the original spoofer, and still move the price (`manipulation-detection-evasion.md:11` (p. 1)).

## Assumptions against the Arena
- **For the D3 tells** *(inferred)*: rule-based tells (Lee et al.'s 6 ticks and twice the size, [spoofing-traders-empirical](spoofing-traders-empirical.md)) catch a naive spoofer; a disguised one looks like a market maker, so watch the effect (the imbalance before trades, [Tao et al.](detecting-spoofing-strategies.md)) rather than the order's shape.

## In our notation
Nothing to implement.

## Traps
- None found.

## Read depth
- **Read:** abstract and introduction.
- **Skimmed:** the model and experiments.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
