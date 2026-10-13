---
title: Yang, Gu, Ching & Siu, "On optimal pricing model for multiple dealers in a competitive market" (2017)
type: source
repo: literature_md/competing-dealers
status: partly-read
updated: 2026-10-13
---

# Yang, Gu, Ching & Siu, "On optimal pricing model for multiple dealers in a competitive market" (Computational Economics, 2017)

## What it is
Avellaneda–Stoikov extended to N dealers quoting the same stock. Conditional reading: it matters only if the Arena's teams share one market ([shared market](../concepts/shared-market-and-adversaries.md)). The user saved the published version.

## Main results
- **How competition enters** (Proposition 1, `competing-dealers.md:221-236` (p. 10, checked)): the market-order rate depends on a weighted average of all dealers' distances, `A·e^{−k(β₁δ₁ + … + β_Nδ_N)}`, and dealer i's own rate has an extra factor `e^{−αK(N)δ_i}` with `K(N) = c(1 − 1/N)`. So quoting tighter raises everyone's flow a little and one's own more.
- **Result** (§5.2, `competing-dealers.md:660` (p. 24)): with more dealers, both the profits and the average spreads fall.

## Assumptions against the Arena
- **No price priority.** The best quote does not take the flow: every dealer keeps a share that decays smoothly with its own distance. In a real book, and in our `--vs` engine, the best price fills first, so undercutting by a tick takes the whole flow at that moment. *(Inferred from the model's form.)* The paper's conclusions can only be read qualitatively for the Arena.
- No asymmetric information, the market is "perfect" (`competing-dealers.md:240` (p. 10)).

## In our notation
`--vs` (`arena.engine.run_market`) is the test bench for competition; this paper has no mechanism we could measure there.

## Traps
- The abstract spells the original "Avellande and Stoikov".

## Read depth
- **Read:** sections 3 (the intensities) and 6 (conclusions), the opening of 5.2.
- **Mapped:** sections 2, 4 (the HJB for active and inactive dealers), 5, the appendices, by headings.

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md).
