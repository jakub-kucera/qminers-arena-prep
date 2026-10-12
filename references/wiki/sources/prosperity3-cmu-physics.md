---
title: CMU Physics, Prosperity 3 (7th)
type: source
repo: online-snapshots
status: partly-read
updated: 2026-10-11
---

# CMU Physics (Prosperity 3, 7th globally and 1st in the US, their claim)

## What it is
A GitHub repo (381 files, **1.2 GB** of data, 55 code files, no licence) with a 410-line README that walks through every round. Read online and saved as `references/online-snapshots/chrispyroberts_imc-prosperity-3.README.md`; not cloned because of the size. Their path: 771st after round 1, 9th after the re-run, 7th to 241st in one round, then back to 7th (`chrispyroberts_imc-prosperity-3.README.md:70-72`, `chrispyroberts_imc-prosperity-3.README.md:228-236`).

## Layout and code map
Read in detail (the README is a long narrative with images):
- **Sample data was part of the live day** (`chrispyroberts_imc-prosperity-3.README.md:70-72`): the website's "sample data" turned out to be the first 1,000 timestamps of live day 1, which let teams hard-code trades. They initially finished 771st; after the round was re-run (hard-coding ruled cheating) they finished 9th, partly by luck: Squid Ink spiked in their favour on the re-run. Afterwards they allocated only 10% of the position to Squid Ink and added spike detection.
- **State-wipe incident** (`chrispyroberts_imc-prosperity-3.README.md:234`): the logging in jmerle's visualizer made the submission **exceed 100 MB of memory, which restarted the AWS Lambda instance and wiped all local variables**, breaking the rolling windows behind their basket and Volcanic Rock trades. The trader "effectively bought and sold these products randomly" and they fell from 7th to 241st. They removed the visualizer logging from later submissions.
- **A fitted smile stopped fitting** (`chrispyroberts_imc-prosperity-3.README.md:236`): their quadratic implied-volatility fit was a poor model on the submission day, so they held long or short vol positions all day; using the mean of a short rolling window of mid implied volatility as the fair IV raised their backtest PnL from about 80k to 200k per day, "even on the day of submission" (their claim).
- Manual track and game-theory modelling take most of the README (not read).

## What carries over
- **Do not keep trading state in memory that a restart can wipe**; keep it in `traderData` (our rule) and keep the logger small. See [many-products-architecture](../concepts/many-products-architecture.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md).
- A rolling-window fair IV beat a fitted smile on a day where the smile broke: [options-and-vouchers](../concepts/options-and-vouchers.md).
- Practice or sample data can be a slice of the scored data: [validation-and-overfitting](../concepts/validation-and-overfitting.md).

## Traps
Rank swings were large; the README says luck played a part. Much of the README is manual-round modelling that does not apply.

## Read depth
- **Read:** `chrispyroberts_imc-prosperity-3.README.md` lines 66–74, 228–238, 403–410.
- **Mapped:** headings (the README has few headings).
- **Unread:** most of the 410 lines, including all manual-round modelling.

## Cited by
[many-products-architecture](../concepts/many-products-architecture.md), [options-and-vouchers](../concepts/options-and-vouchers.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md).
