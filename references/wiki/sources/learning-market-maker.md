---
title: Das, "A learning market-maker in the Glosten–Milgrom model" (2005)
type: source
repo: literature_md/learning-market-maker
status: read
updated: 2026-10-14
---

# Das, "A learning market-maker in the Glosten–Milgrom model" (Quantitative Finance 5(2), 2005; preprint)

## What it is
A 19-page preprint (submitted version) of an algorithm for a market maker that never sees the true value. It keeps a discrete probability distribution over the value, one cent per bin, and updates it by Bayes' rule on every buy, sell or no-order. It then quotes the Glosten–Milgrom prices, bid `E[V | sell]` and ask `E[V | buy]`. The value jumps now and then, informed traders see it with noise, and uninformed traders buy or sell at random.

For us it is the most concrete algorithm for B3 (a hidden fair value) and B4 (anonymous informed flow) in [harder-rounds](../concepts/harder-rounds.md). It is implementable with the standard library. Fetched 2026-10-14 from the author's Virginia Tech page; the GMU link redirects to a homepage.

## Main results
- **The market** (`learning-market-maker.md:45` (p. 3)):
  - Each step, one trader from the crowd sends a one-unit market order, or none.
  - The value jumps with probability `p` (typically 0.001) by `N(0, σ²)`.
  - An informed trader buys if its signal `W = V + N(0, σ_W²)` is above the ask, and sells if it is below the bid.
  - **The market maker is told when a jump happens**, but not its size or direction.
- **The order probabilities** (eqs. 6–9, `learning-market-maker.md:107` (p. 6, checked); checked on the page image), with `α` the informed share and `η` an uninformed trader's chance to buy (and to sell):
  - **Sell:** `Pr(Sell | V) = (1−α)η + α·Pr(ε < P_b − V)`.
  - **Buy:** `Pr(Buy | V) = (1−α)η + α·Pr(ε > P_a − V)`.

  Here `ε ~ N(0, σ_W²)`. The paper splits each equation at `V = P_b` (or `P_a`), but by the symmetry of `ε` each pair is one formula.
- **The value distribution** starts as a Gaussian discretised over `V_0 ± 4σ`. It is updated by Bayes on each order, and the bid and ask are found by stepping down (or up) from `E[V]` until the fixed-point equations are closest to holding (`learning-market-maker.md:143` (p. 7)).
- **Spreads widen after a jump and close within about 30 trades**, whatever the jump size (`learning-market-maker.md:203` (p. 10)).
- **Widening the zero-profit quotes by a "shift"** turns break-even into profit (`learning-market-maker.md:219` (p. 12)). With 70% noisy informed traders:
  - a shift of 0 gives −0.06 cents per step at a 0.35-cent spread;
  - a shift of 1 gives +1.17 at 2.28.

  With few informed traders, profit keeps rising with the shift. With many, too wide a spread stops even the noisy informed traders from trading (`learning-market-maker.md:215` (p. 11)).
- **Inventory control** is a linear shift of both quotes by `−γ·I` after pricing. It cuts the variance of profit (`learning-market-maker.md:225` (p. 12)). That is the template's `skew`.
- **Without being told about jumps, it loses.** Recentring when the last 10 orders hold 5 more buys than sells (or vice versa) gave −0.66 cents per step, with an average error in the value of 4.6 cents (`learning-market-maker.md:261` (p. 14), `learning-market-maker.md:269-271` (p. 14)). The author calls detecting jumps from the order flow future work.

## Assumptions against the Arena
- **Jumps are announced.** No exchange tells us; the unannounced case loses. A changepoint detector ([online-changepoint-detection](online-changepoint-detection.md)) is the missing piece *(inferred)*.
- **One market maker, and every trade goes through it.** In the Arena we are one of several liquidity providers, and only the trades that hit our quotes inform us directly. The data's market trades against the bots' book are a second signal the paper doesn't use.
- **A no-order step is informative** only when we know how often traders arrive. Per-tick snapshots with zero, one or several trades fit this loosely.

## In our notation
- `V` is the hidden fair value; `P_b` and `P_a` are our quotes; `α` is the informed share, estimated from markouts (`arena.analysis`) or from `arena.diagnose`'s `R(50)`.
- The posterior mean `E[V]` replaces `wall_mid` as `fair`, and its spread of probability mass sets `make_edge`. That is the B3/B4 prep in [harder-rounds](../concepts/harder-rounds.md).
- With 1-tick bins over ±4σ (about 400 bins for σ = 50 ticks), one update per tick costs a few hundred multiplications per product. That is well inside the budget measured in [harder-rounds](../concepts/harder-rounds.md), E1.

## Traps
- **The paper's no-order probabilities are wrong** (p. 8, checked on the page image).
  - In the middle case (`P_b ≤ V ≤ P_a`), it adds `Pr(P_b − V < ε) + Pr(V − P_a < ε)`. Each term is at least ½, so the bracket exceeds 1.
  - The outer cases drop one of the two bounds.
  - An informed trader sends no order when `P_b ≤ W ≤ P_a`, so the correct term for every `V` is `α·[Φ((P_a − V)/σ_W) − Φ((P_b − V)/σ_W)]` *(derived here)*.
- **Eq. 11 on p. 6 has a misplaced parenthesis** in the original.
- **OCR:**
  - Line 167 reads `η̃(α, σ_W²)` where the PDF has `η̃(0, σ_W²)`.
  - Line 165 has `η̄` for `η̃`.
  - Eqs. 6–7 lose the conditioning bar (`Pr(Sell V = V_i` …).
- **This is the submitted version, not the published one.** Check numbers against the journal if they matter.

## Read depth
- **Read:** sections 1–3 (the model, the algorithm, the experiments). Formulas on p. 6 and p. 8 checked on the page images.
- **Skimmed:** section 4 (return statistics against TAQ data).

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [informed-counterparties](../concepts/informed-counterparties.md), [online-changepoint-detection](online-changepoint-detection.md).
