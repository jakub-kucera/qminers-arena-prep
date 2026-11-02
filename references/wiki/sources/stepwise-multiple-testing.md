---
title: Romano & Wolf, "Stepwise multiple testing as formalized data snooping" (2003/2005)
type: source
repo: literature_md/stepwise-multiple-testing
status: read
updated: 2026-10-26
---

# Romano & Wolf, "Stepwise Multiple Testing as Formalized Data Snooping" (working paper, October 2003; Econometrica 2005)

## What it is
A 36-page working paper (Universitat Pompeu Fabra, paper 712) that extends White's Reality Check from "does the best strategy beat the benchmark?" to "**which** strategies beat it?", with the familywise error rate (FWE), the chance of even one false discovery, held at α (`stepwise-multiple-testing.md:11` (p. 1)). The answer is a step-down method, StepM, plus an argument for studentizing. The published Econometrica version (2005) is not what we have.

## Main results
- **FWE, not FDR** (`stepwise-multiple-testing.md:35` (p. 3)): FWE control avoids every false discovery; the false discovery rate (Benjamini–Hochberg) allows a share of them and finds more. The paper does FWE and leaves FDR to future work.
- **The step-down idea** (Section 3, p. 8–10):
  - **Order and bound:** sort the strategies by their test statistic, then build a joint one-sided confidence region `[w_k − c, ∞)` for all of them. Reject every strategy whose interval excludes 0.
  - **Repeat on the rest:** recompute `c` over the strategies still standing, which gives a smaller `c`, and repeat until nothing more is rejected. White's Reality Check is the first step alone, so StepM is at least as powerful with the same FWE (Theorem 3.1).
- **Algorithm 4.1, the studentized StepM** (`stepwise-multiple-testing.md:274-282` (p. 14, checked)): reject `H_{0,r_k}` when 0 is not in `[w_{T,r_k} − σ̂_{T,r_k}·d_{K_i+1}, ∞)`, i.e. when `z_k = w_k/σ̂_k` exceeds `d`, then step down.
- **Algorithm 4.2** (`stepwise-multiple-testing.md:295-303` (p. 15, checked)): `d` is the 1 − α empirical quantile, over J ≥ 1,000 bootstrap data sets, of `max_{k still standing} (w*_k − θ*_k)/σ̂*_k`. By Remark 3.1 the sample statistic may stand in for `θ*` under the stationary bootstrap (`stepwise-multiple-testing.md:256` (p. 13)).
- **Studentize with time series** (`stepwise-multiple-testing.md:414` (p. 21)): on AR(1) data the basic (unstudentized) method "does not provide a satisfactory control of the FWE in finite sample and is too liberal" for every block size tried; the studentized one controls it. The conclusion repeats it for data with "notable dependence over time" (`stepwise-multiple-testing.md:434` (p. 23)).
- **Block size** (Section 6, `stepwise-multiple-testing.md:357` (p. 18)): it matters, should grow slower than T, and the paper gives a calibration algorithm (6.1), which it calls too costly for its own simulations.
- **Application** (`stepwise-multiple-testing.md:424` (p. 22)): of the 100 largest US stocks, the studentized method finds 6 with a positive CAPM alpha at FWE 10%.

## Assumptions against the Arena
- **Many strategies, one data set,** which is a grid. Each cell is a hypothesis "beats the bot as is".
- **Time-series dependence.** Our block gains are autocorrelated within a day; per the paper, only the studentized version is safe there.
- **Each resample studentized by its own `σ̂*`, as Algorithm 4.2 step 3 does** (since 2026-10-26): `python/arena/stats.py`'s `stepm` reruns Hansen's kernel `ω̂` on each resample's column (`bootstrap`, `python/arena/stats.py:169-191`). For time series the paper says `σ̂*` "can be obtained by applying the same algorithm to the bootstrap data matrix" (`stepwise-multiple-testing.md:311` (p. 15, checked)). It names Götze and Künsch's "natural" block estimator for the moving and circular block bootstraps; ours draws blocks of geometric length, so the kernel is run on the resample as on any series *(ours)*.
- **The fixed scale it replaced** *(ours, not the paper's)*: until 2026-10-26 `stepm` held the original's `ω̂_k` fixed across resamples. On the null grids of `python/experiments/study/snooping_null_rates.py` (24 cells, 300 blocks, 300 grids a row, nominal 5%) that named a noise cell in 8.7–22.3% of grids, the most when the gains are strongly autocorrelated (AR(1) 0.8); each resample's own scale names one in 6.0–8.0% (5.9–8.3% over 1,000 grids a row) *(checked; `IDEAS.md`, "Bootstrap tests of the best cell")*. The ten null controls of `python/experiments/study/snooping_tests.py`, which had found no false rejection, were too few to see it.

## In our notation
| Paper | Ours |
|---|---|
| strategy k, K | a distinct grid cell |
| `w_{T,k}` | mean gain of the cell over the bot as is, per block |
| `σ̂_{T,k}` | `√(ω̂²_k / n)` from Hansen's kernel (`python/arena/stats.py:128-147`) |
| `σ̂*_{T,k}` | the same kernel on resample j's column (`bootstrap`, `python/arena/stats.py:169-191`) |
| `d_{K_i+1}(1−α)` | the `c` in `stepm()` (`python/arena/stats.py:237-260`) |
| J | `--boot` (2,000) |

## Traps
- **The working paper, not the journal version.** Section and algorithm numbers may differ from Econometrica 2005.
- **One-sided.** The tests are for "beats", `θ_k > 0`; the two-sided variant (Section 5) is for "differs".
- **Remark 3.1's shortcut** (the sample statistic for `θ*`) holds for the stationary and circular bootstraps, not the moving-blocks one.

## Read depth
- **Read:** Sections 1, 3, 4, 7.2, 8 and 9; Section 6 skimmed.
- **Checked against the PDF (page images):** Algorithms 4.1 and 4.2 (p. 14–15); eq. (11) and the text on studentizing time series in each resample (p. 14–15, against the PDF's text layer, 2026-10-26).
- **Not read:** Section 2's examples in detail, Section 5, the proofs and Appendices B–C.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
