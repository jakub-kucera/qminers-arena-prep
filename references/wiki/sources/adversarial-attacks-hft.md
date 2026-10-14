---
title: Goldblum, Schwarzschild, Patel & Goldstein, "Adversarial attacks on machine learning systems for high-frequency trading" (2021)
type: source
repo: literature_md/adversarial-attacks-hft
status: partly-read
updated: 2026-10-14
---

# Goldblum, Schwarzschild, Patel & Goldstein, "Adversarial attacks on machine learning systems for high-frequency trading" (ICAIF 2021; arXiv:2002.09565)

## What it is
Order-book valuation models seen as targets for adversarial attacks: small orders, bounded in cost and detectability, that make a deep-learning price model mispredict (`adversarial-attacks-hft.md:11` (p. 1)). Fetched from arXiv.

## Main results
- **Universal attacks:** perturbations that stay adversarial across market states and model architectures, cheap enough for a real attacker (`adversarial-attacks-hft.md:53` (p. 2)).

## Assumptions against the Arena
- Targets deep-learning predictors; the template's rules (walls, levels, jumps) are not models of that kind.
- **For D2 and D3** *(inferred)*: agent-written bots that fit a model to book features are the fragile ones; an organiser bot that places a few small orders can mislead them.

## In our notation
Nothing in the template is attacked this way; `IDEAS.md`'s imbalance signals would be.

## Traps
- None found.

## Read depth
- **Read:** abstract and introduction.
- **Skimmed:** the attacks and results.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
