---
title: Dwork et al., "Generalization in adaptive data analysis and holdout reuse" (2015)
type: source
repo: literature_md/reusable-holdout
status: partly-read
updated: 2026-10-19
---

# Dwork, Feldman, Hardt, Pitassi, Reingold & Roth, "Generalization in Adaptive Data Analysis and Holdout Reuse" (arXiv:1506.02629, NeurIPS 2015; the Science paper "The reusable holdout" is its short version)

## What it is
A 29-page computer-science paper on **adaptive** data analysis: each analysis chooses what to test next from the results of earlier ones on the same data. That is how a day of grid search, or a round of portal submissions, actually runs. Its practical result is **Thresholdout**, a way to keep validating against a holdout set many times without overfitting to it. The theory (differential privacy, description length, max-information) is the bulk of the paper and was not read.

## Main results
- **Reusing a holdout adaptively overfits it** (`reusable-holdout.md:570` (p. 21)):
  - **The setup:** n = 10,000 points, 10,000 attributes, labels independent of the data, so no classifier can beat 50%.
  - **What happens:** an analyst picks attributes by their correlation on the training set, checks each on the holdout, and keeps those that agree. The holdout then reports over 63% accuracy for k = 500 attributes, while fresh data shows 50%.
  - **The authors' point** (`reusable-holdout.md:580` (p. 21)): neither cross-validation nor the bootstrap fixes this (`reusable-holdout.md:590` (p. 22)). The only safe approach known before was a fresh holdout for every step that depends on earlier results.
- **Thresholdout** (`reusable-holdout.md:408-428` (p. 15–16, checked)):
  - **Inputs:** a training set `S_t`, a holdout `S_h`, a threshold `T`, a noise scale `σ` and a budget `B`.
  - **Per query `φ`:** if the holdout and training means differ by more than `T̂ + η` (with Laplace noise `η` and noisy threshold `T̂`), it spends one unit of budget and returns the holdout mean plus Laplace noise `ξ ∼ Lap(σ)`. Otherwise it returns the **training** mean. Once `B` is spent it stops answering.
  - **What the analyst learns:** usually only "no overfitting here", one bit; the holdout's value leaks only when a query overfits.
  - **The guarantee:** the number of queries it can answer is exponential in n, as long as the number that overfit is at most about quadratic in n (`reusable-holdout.md:55` (p. 3)).
- **In practice** (`reusable-holdout.md:568` (p. 21)): the experiment used T = 0.04, a noise of 0.01 and Gaussian noise. These are below what the proofs need, but enough there.
- **SparseValidate** (`reusable-holdout.md:538` (p. 19)): ask any yes/no question of the holdout (e.g. "is the holdout accuracy at least α?"), with one budget on all questions and another on "yes" answers.
- **Leaderboards** (`reusable-holdout.md:95` (p. 6)): Blum & Hardt's "Ladder" applies the same idea to a competition leaderboard that participants submit to adaptively. The Ladder itself was not read.

## Assumptions against the Arena
- **i.i.d. samples and queries bounded in [0, 1].** A day of ticks is neither. PnL per block can be scaled into a range, but blocks within a day are dependent *(inferred)*.
- **A large holdout.** The guarantees scale with the holdout's size n; three days, or 30 blocks, give little budget *(inferred)*.
- **The analyst never sees the holdout's raw value** except through the mechanism. In a team that discipline must be enforced by whoever holds the holdout days.
- **What carries over is the design, not the numbers:**
  - Answer from the training days unless the held-out day disagrees beyond a threshold.
  - Count the disagreements, and stop when a pre-set budget of them is spent. *(Inferred.)*
  - This is a concrete rule for "don't open the unseen day early" and for capped portal submissions.

## In our notation
| Paper | Ours |
|---|---|
| training set `S_t`, holdout `S_h` | the days a grid is tuned on, a held-out day (or the portal's hidden evaluation) |
| query `φ`, its mean | a candidate setting, its PnL (scaled) |
| budget `B` | how many times we let a held-out result change a decision |
| threshold `T` | the gap between training and held-out PnL that counts as "overfit" |

## Traps
- **The arXiv title differs from the Science paper's.** The NeurIPS/arXiv version is the long one, with the algorithms and proofs.
- **Its constants are not for direct use.** The authors say so of the theoretical parameters (`reusable-holdout.md:568` (p. 21)).

## Read depth
- **Read:** the abstract, Section 1.1, Section 4.1 (Thresholdout and its pseudocode), Section 4.2's description, Section 5 (experiments) and Section 6.
- **Checked against the PDF (page image):** the Thresholdout pseudocode (p. 16).
- **Not read:** Sections 2–3 (differential privacy, description length, max-information) and the proofs.

## Cited by
[validation-and-overfitting](../concepts/validation-and-overfitting.md).
