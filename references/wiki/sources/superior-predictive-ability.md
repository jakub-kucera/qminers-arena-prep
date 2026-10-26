---
title: Hansen, "A test for superior predictive ability" (2005)
type: source
repo: literature_md/superior-predictive-ability
status: read
updated: 2026-10-26
---

# Hansen, "A Test for Superior Predictive Ability" (Journal of Business & Economic Statistics, 2005)

## What it is
A 16-page paper that improves on White's (2000) Reality Check (RC), the bootstrap test of whether the best of m alternatives beats a benchmark once the search over all m is accounted for. It is the closest thing to the question `arena.grid` asks: does any cell beat the bot as is? A trading rule is one of its own examples (`superior-predictive-ability.md:37` (p. 2)). White's paper itself could not be downloaded (`MANUAL_TODO.md`); this one restates the RC's statistic and null.

## Main results
- **The setting** (`superior-predictive-ability.md:64-74` (p. 3, checked)): `d_{k,t}` is model k's performance relative to the benchmark at time t (for us, a cell's PnL minus the bot's, per block). H0: `µ = E[d_t] ≤ 0`, every alternative no better than the benchmark. Assumption 1: `d_t` stationary and α-mixing (`superior-predictive-ability.md:76` (p. 3)).
- **The RC is easy to manipulate with poor alternatives** (`superior-predictive-ability.md:169` (p. 5)). Its null distribution assumes every `µ_k = 0`, the least favourable configuration, so adding alternatives that are clearly worse raises its critical value without adding evidence. The power can be driven to zero.
- **Two fixes** (`superior-predictive-ability.md:98-103` (p. 4, checked)):
  - **Studentize:** `T^SPA = max[ max_k √n·d̄_k / ω̂_k , 0 ]` (`superior-predictive-ability.md:98` (p. 4, checked)), so cells are compared in units of their own noise. In the paper's two-model example this lifts power from about 15% to about 53%, as the text puts it (`superior-predictive-ability.md:129` (p. 5)).
  - **A sample-dependent null:** recentre at `µ̂^c_k = d̄_k · 1{√n·d̄_k/ω̂_k ≤ −√(2 log log n)}`. Only cells that are clearly worse keep their (negative) mean; the rest are treated as being as good as the benchmark. `µ̂^l_k = min(d̄_k, 0)` and `µ̂^u_k = 0` bound the p-value from both sides; `µ̂^u` is the studentized RC (`superior-predictive-ability.md:199` (p. 6–7, checked)). Poor cells are not dropped, only their influence is reduced (`superior-predictive-ability.md:197` (p. 6)).
- **The bootstrap** (Section 3, p. 7–8, checked):
  - **Stationary bootstrap** of Politis and Romano: blocks of geometric length with mean `1/q`, wrapping at the end (`superior-predictive-ability.md:223` (p. 7, checked)).
  - **Variance:** `ω̂²_k = γ̂_{0,k} + 2 Σ_{i=1}^{n−1} κ(n, i) γ̂_{i,k}` with `κ(n, i) = (n−i)/n·(1−q)^i + i/n·(1−q)^{n−i}`, the bootstrap's own population variance, rather than an estimate from the resamples (`superior-predictive-ability.md:241-249` (p. 8, checked)).
  - **Recentring:** `Z*_{k,b,t} = d*_{k,b,t} − g_i(d̄_k)` with `g_l(x) = max(0, x)`, `g_c(x) = x·1{x ≥ −√((ω̂²_k/n)·2 log log n)}` and `g_u(x) = x` (`superior-predictive-ability.md:257` (p. 8, checked)).
  - **p-value:** the share of resamples with `T*_b = max(0, max_k √n·Z̄*_{k,b}/ω̂_k)` above `T^SPA` (`superior-predictive-ability.md:271` (p. 8, checked)).
  - It stays valid even if `ω̂_k` is wrong; `ω̂_k = 1` gives back the RC (`superior-predictive-ability.md:275` (p. 8)). Hansen uses "the same estimate of ω²_k" for `T^SPA` and every `T*_b` (same line).
  - **Ours differs there** (since 2026-10-26, `studentize="resample"`, the default): each resample's `T*_b` divides by its own `ω̂*_k`, Hansen's kernel rerun on that resample, as Romano and Wolf's StepM does ([StepM](stepwise-multiple-testing.md)); `T^SPA` and `µ̂^c`'s threshold keep the original's `ω̂_k`. Hansen's validity is asymptotic: on the null grids of `python/experiments/snooping_null_rates.py` (24 cells, 300 blocks, nominal 5%) his fixed `ω̂` rejected in 8.7–22.0% of grids, ours in 5.3–7.7% (5.6–8.4% over 1,000 grids a row) *(checked; `IDEAS.md`, "Bootstrap tests of the best cell")*. `studentize="fixed"` is Hansen's.
- **Simulations** (Section 4, p. 9–11): SPA^c holds its size and has more power than the RC, most when poor alternatives are present.
- **The empirical case** (`superior-predictive-ability.md:550` (p. 14)): the same inflation forecasts give SPA^c a p-value of 10% and the RC about 96%, "opposite conclusions", because of the poor alternatives.

## Assumptions against the Arena
- **Stationarity and mixing of `d_t`.** Our gains per block of 100 ticks are autocorrelated within a day and change between days. The stationary bootstrap handles the first; day-level changes break the assumption. *(Inferred.)* The leave-one-day-out check in `arena.grid` covers what the bootstrap can't.
- **n and m.** The paper's simulations use n = 200–1,000 and m = 100–1,000 (`superior-predictive-ability.md:303` (p. 9)). One Prosperity day cut into blocks of 100 ticks gives n = 100, so three days give 300 *(checked: `python/experiments/snooping_tests.py`)*, inside that range. With the grid's own 16 blocks it would be far too short.
- **The benchmark is the bot as is**, which matches the question we ask of a grid. A grid without a sensible baseline (all cells new) has no benchmark; the test then needs one chosen in advance.
- **Fixed parameters.** Hansen's framework excludes parameters re-estimated recursively (`superior-predictive-ability.md:23` (p. 2)). A cell's parameters are fixed for the day, so this holds; a bot that fits itself on the day's data is a different case.

## In our notation
| Paper | Ours |
|---|---|
| benchmark `δ_0` | the bot as is (`--set` only), `python/arena/grid.py` `run_grid`'s baseline |
| alternative k, m | a distinct grid cell, the number of distinct cells |
| `d_{k,t}` | the cell's PnL minus the bot's in block t (`python/arena/grid.py:112`, `FINE_TICKS`; filled in `_run_piece`) |
| `q` | 1 / mean bootstrap block length, in blocks (`SPA_Q` in `python/arena/grid.py`, 0.1) |
| `T^SPA`, `p̂_SPA` | `spa()` in `python/arena/stats.py:207-230` |

## Traps
- **Typo in the paper itself:** the stationary bootstrap's recursion prints `⌈n·u_{b,1}⌉` for a fresh draw at t ≥ 2 (p. 7, the page image has it too); the text says the t-th element is then "chosen uniformly on {1, …, n}", which needs `u_{b,t}`. Our code follows the text.
- **OCR:** Marker drops decimal points in the simulation tables ("055" where the PDF has ".055", `superior-predictive-ability.md:309` (p. 9)). Read the tables from the PDF.
- **"Discarding the poor models"** is a misreading the author warns against (`superior-predictive-ability.md:197` (p. 6)): `µ̂^c` keeps them, with their mean.
- **The `ω̂` estimator:** an earlier version estimated it from the resamples; the paper recommends the closed-form bootstrap variance because the resampled one needs very large B (`superior-predictive-ability.md:237-239` (p. 8)).

## Read depth
- **Read:** Sections 1–4 and 6, Section 5's results paragraph.
- **Checked against the PDF (page images):** `T^SPA` and `µ̂^c` (p. 4); `µ̂^l`, `µ̂^u` and the bootstrap recursion (p. 7); `ω̂²`, `γ̂`, `κ`, `Z*`, `g_l`, `g_c`, `g_u`, `T*` and `p̂_SPA` (p. 8).
- **Not read:** the appendix proofs; the inflation regressions in Section 5 beyond its conclusion.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
