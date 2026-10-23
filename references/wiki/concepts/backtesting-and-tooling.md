---
title: Backtesting and tooling
type: concept
updated: 2026-10-14
---

# Backtesting and tooling

## Summary
The community backtesters (jmerle's, then the Prosperity 4 fork) implement the matching rules every team relied on, and our engine matches the Prosperity 3 one fill for fill. What the teams added on top, and what they say the backtester cannot do, shapes what to build in our own tooling.

## What the sources say
- **Matching rules:** limits are enforced before matching; an order matches the book first and then market trades at its own price; `--match-trades worse` is the stricter variant Linear Utility used (`prosperity3-backtester-jmerle/README.md:59-67`, `prosperity3-backtester-jmerle/prosperity3bt/runner.py:123-310`). Conversions are not supported (`prosperity3-backtester-jmerle/README.md:83`), which cost Alpha Animals money (`prosperity3-alpha-animals/README.md:88`).
- **Prosperity 4 fork:** per-fill limit clamp, `--limit`, `--round2-access`, `--counterparty-info`, risk metrics (`prosperity4-backtester/prosperity4bt/__main__.py:255-284`, `prosperity4-backtester/prosperity4bt/metrics.py:14`). Default limit 50 for unlisted products (`prosperity4-backtester/prosperity4bt/data.py:8`).
- **Turn a submission log into data** with `parse_submission_logs.py` (`prosperity3-backtester-jmerle/prosperity3bt/parse_submission_logs.py:8-81`): this is how a portal run becomes backtest data.
- **Log format and viewers:** traders print a compressed state (`Logger`) that the visualizer parses (`prosperity3-visualizer-jmerle/src/utils/algorithm.tsx:203-225`); every team built its own dashboard (Frankfurt's: `prosperity3-frankfurt-hedgehogs/README.md:96-163`; DTU's: `prosperity4-dtu-quant-lab/tools/dashboard.py`; Linear Utility's: `prosperity2-linear-utility/README.md:78`).
- **Speed matters for sweeps:** Ryan Challman ran a 50-variant sweep in minutes on a Rust port instead of an afternoon on the Python engine (`prosperity4-ryan-challman/README.md:23`); DTU wrote that a port to a faster language is needed past ~20 products (`prosperity4-dtu-quant-lab/README.md:343`).
- **Per-product PnL attribution on day 1:** DTU's own advice (`prosperity4-dtu-quant-lab/README.md:343`); Alpha Search's carry-versus-capture decomposition (`prosperity4-alpha-search/README.md:44`).
- **What a backtester cannot do** (Frankfurt, Baguette Fromage): bot interactions after inserting liquidity, market impact, conversions (`prosperity3-frankfurt-hedgehogs/README.md:899-900`, `prosperity4-baguette-fromage/README.md:236-243`).
- **Reading the website's PnL** works as a probe of the true price (buy one lot and hold) *(see [fair-value-and-wall-mid](fair-value-and-wall-mid.md))*.
- **Which fill rule is realistic** ([DeLise](../sources/negative-drift-of-a-fill.md)): on Treasury futures, filling every resting order against each market order overstated fills (85% against a live simulator's 60%) and PnL; adding fills on every adverse move to a calibrated random fill rate matched best (`literature_md/negative-drift-of-a-fill/negative-drift-of-a-fill.md:291-306` (p. 22–23)). Our `--resting` has the adverse-move fill (a crossing snapshot fills the order); probe 18 in `ON_THE_DAY.md` measures the real rule.
- **A checklist for simulator realism** ([Vyetrenko et al.](../sources/lob-simulation-realism.md)): the stylised facts a simulated book should reproduce, with formulas; even ABIDES misses some (`literature_md/lob-simulation-realism/lob-simulation-realism.md:13` (p. 1)). Our engine replays recorded books, so the facts hold by construction except where our own orders change the book (`--resting`, `--vs`).

- **The parts of a reactive market** ([PyMarketSim](../sources/pymarketsim.md)): a mean-reverting fundamental, private values, zero-intelligence takers, random arrivals and a ladder market maker (`literature_md/pymarketsim/pymarketsim.md:143` (p. 4)); the spec for the day generator in `harder-rounds` A1.

## Where they disagree
Nothing material.

## What it means for our code
`arena.backtest`, `arena.grid`, `arena.analysis` and `arena.validate` exist; the engine is pinned to jmerle's P3 rules by `python/tests/test_parity.py` and also has a resting-order mode and a shared-market mode (`CLAUDE.md`). Missing: conversions and a visualizer-compatible log writer (`--data p4` and the PnL split, `arena.analysis.pnl_split`, were built: `TODO_DONE.md`).

## How to test it here
Done (`TODO_DONE.md`, "Run the cloned teams' traders through our engine as a cross-check"): four P4 traders give identical PnL per product and day in our engine and in `prosperity4btest`; each one's PnL is on its source page, next to the claim. Frankfurt's file was run on P3 (see its source page).

## Sources
[jmerle P3 backtester](../sources/prosperity3-backtester-jmerle.md), [P2 backtester](../sources/prosperity2-backtester-jmerle.md), [prosperity4btest](../sources/prosperity4-backtester.md), [visualizer](../sources/prosperity3-visualizer-jmerle.md), [hftbacktest](../sources/hftbacktest.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md), [Ryan Challman](../sources/prosperity4-ryan-challman.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Alpha Search](../sources/prosperity4-alpha-search.md), [Alpha Animals](../sources/prosperity3-alpha-animals.md), [DeLise](../sources/negative-drift-of-a-fill.md), [Vyetrenko et al.](../sources/lob-simulation-realism.md), [PyMarketSim](../sources/pymarketsim.md).
