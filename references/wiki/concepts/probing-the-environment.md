---
title: Probing the environment before building strategies
type: concept
updated: 2026-10-13
---

# Probing the environment before building strategies

## Summary
Every team that did well says its first move was an experiment on the environment, not a strategy: tiny, empty or grid-quoting probes to learn how matching, price generation and the bots behave. The biggest edges in the record (the wall mid, empty-side fills, round-number snap-backs, the 10th-tick jump) were found this way.

## What the sources say
- **Question the framing, then map the system** (Frankfurt Hedgehogs): in Ready Trader Go they studied the simulation's source code and rules until they found a way to profit with "very little to do with traditional market making"; in Prosperity they wrote "controlled algorithm tests — not to optimize trading performance, but to test the behavior of the environment itself" (how prices are generated, how matching works, whether bots are predictable) (`literature_md/how-to-almost-win/how-to-almost-win.md:40-60` (p. 3–4)). The essay gives no tactics, and no winning Ready Trader Go bot is public to confirm the claim.
- **A first-round probe pays for every later round** (Leo-Hawking): a grid-quoting probe showed there is no queueing, bots hit only the best price, and active takes can cross levels; hence "quote one better than the best" became the skeleton of every strategy (`online-snapshots/Leo-Hawking_IMC-Prosperity-4-Review.README.md:198-214`).
- **Find what the score is marked to** (Linear Utility, Frankfurt, Baguette Fromage): buy one lot, hold it, and compare the website's PnL curve with candidate fair values; this identified the market maker's mid as the mark (`prosperity2-linear-utility/README.md:109`, `prosperity3-frankfurt-hedgehogs/README.md:882`, `prosperity4-baguette-fromage/README.md:268-272`).
- **Measure the bots' tolerances** (Baguette Fromage, DU): increasingly aggressive quotes found the distance at which a hidden taker still lifts an order (~98–120 from the wall mid) (`prosperity4-baguette-fromage/README.md:356-365`, `prosperity4-du-trading/README.md:55`).
- **Zoom in on the data** (HumzahM): returns jumped on exactly every 10th tick, which made a tiny rule beat 40 teams (`uchicago-2025-case2-humzah/chicago8.py:35`; notebook cells 2–4, see [the source page](../sources/uchicago-2025-case2-humzah.md)).
- **Is the practice data really separate from the scored data?** (CMU Physics): the website's "sample data" turned out to be the first 1,000 timestamps of live day 1 (`online-snapshots/chrispyroberts_imc-prosperity-3.README.md:70`). Teams hard-coded trades; the round was re-run and the hard-coding ruled cheating.
- **Calibrate the local fill model against the oracle** (Kayzerjali): one product showed backtest +2,415 against live +436 on the same window, which is only visible by running the same trader on both (`online-snapshots/Kayzerjali_Prosperity2026/run_cycle.md:4-5`).
- **If the simulator source is handed out, read it.** Qminers' 2025 hackathon shipped its evaluation loop (`qminers-hackathon-2025/src/environment.py:61-85`), and the validation was all-or-nothing and rejecting rather than clipping (`qminers-hackathon-2025/src/environment.py:122-140`). It was the 2024 loop with new columns (`qminers-hackathon-2024/src/submit_model/environment.py:63-87`, *checked with `diff`*), so Qminers reuse their evaluator between years.
- **Work out where the data comes from** (Qminers 2024): the finals data was scrambled, and the winner recognised round 3 as just after covid and changed their risk for it (`qminers-hackathon-2024/README.md:57`).
- **Watch the leaderboard** (Qminers 2024): it showed each team's score, runtime and RAM use, so the winner read the others' models from it, and capped their own public score at a tenth to give nothing away (`qminers-hackathon-2024/README.md:35`, `qminers-hackathon-2024/README.md:67`).

## Where they disagree
Nothing material. The open point is how many probe submissions are affordable: Prosperity allows many uploads, the Arena caps them per round (`ON_THE_DAY.md`, "Known so far"), so probes may have to run on the public backtest or in a playground instead.

## What it means for our code
`ON_THE_DAY.md` already lists 12 mechanical probes (resting, limits, state, time limit, queue position). The record adds data-level probes that are not in it yet (items 13–16 there): the PnL-mark probe, far-quote tolerance on an empty side, "is the practice data a slice of the scored data", and "does a repeat of the same trader give the same fills on the public backtest and in our engine". Since 2026-10-17, `bots/probe.py` runs probes 1–13, 17 and 18 in one run and prints a finding for each. In our engine it finds what the engine does in both modes (`tests/test_probe.py`), so on the platform any other answer is a difference to act on.

## How to test it here
On Prosperity 4 round 1 data, reproduce two findings from the data alone (no submission): the share of ticks with an empty side (7.6% *(checked)*) and the repeat of taker events across days. Then use [hidden-takers-and-empty-sides](hidden-takers-and-empty-sides.md) as the template for what a probe should conclude. The data-only checks are one command now, `arena.diagnose` ([reading the data on day one](reading-the-data-on-day-one.md)): it gives the empty-side share (7–8% on P4 rounds 1–2) with the rest of a product's profile.

## Sources
[Diehm essay](../sources/timo-diehm-medium-article.md), [Leo-Hawking](../sources/prosperity4-leo-hawking-review.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Linear Utility](../sources/prosperity2-linear-utility.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [DU Trading](../sources/prosperity4-du-trading.md), [HumzahM](../sources/uchicago-2025-case2-humzah.md), [CMU Physics](../sources/prosperity3-cmu-physics.md), [Kayzerjali](../sources/prosperity4-kayzerjali.md), [Qminers 2025](../sources/qminers-hackathon-2025.md), [Qminers 2024](../sources/qminers-hackathon-2024.md).
