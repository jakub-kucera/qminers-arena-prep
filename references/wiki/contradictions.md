---
title: Contradictions, mismatches and open questions
type: comparison
updated: 2026-10-10
---

# Contradictions, mismatches and open questions

Where two sources disagree, or a source disagrees with its own code. Each row says what would settle it. Add rows here instead of choosing a side silently (`SCHEMA.md`, rule 4).

| # | Question | One side | The other side | What would settle it | Status |
|---|---|---|---|---|---|
| 1 | Does an inventory skew help on a pegged product? | DTU: an Avellaneda–Stoikov skew on Osmium cost 16,593 in backtest and they reverted to a fixed anchor (`prosperity4-dtu-quant-lab/README.md:91`) | Baguette Fromage shipped a linear skew `10000 - position/12` on the same product (`prosperity4-baguette-fromage/Strategies/Phase1.py:240`); Frankfurt used none (`prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:275-331`) | Sweep `skew` on Prosperity 4 round 1 with `arena.grid`, worst-day ranking (`TODO.md`) | open; neither number reproduced |
| 2 | What is the "wall mid"? | Outermost levels (Frankfurt) | highest-volume level (ours, Baguette round 1), first level with volume ≥ 15 (Baguette round 5, Linear Utility), min-bid/max-ask only if ≥ 2 levels (DTU) | PnL of one market maker per definition on P3/P4 data (`TODO.md`) | open; see [fair-value-and-wall-mid](concepts/fair-value-and-wall-mid.md) |
| 3 | Is any `Mark XX` worth trading? | DU: Mark 67 buying lifts velvetfruit ~2 ticks in 100 timestamps (`prosperity4-du-trading/README.md:149`); DTU shipped Mark 14/38 on Hydrogel (`prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:164-166`) | Ryan Challman: weights failed on the held-out day, switch-off recovered ~$15.8k (`prosperity4-ryan-challman/README.md:89-91`); Baguette Fromage: "too weak, too unstable" (`prosperity4-baguette-fromage/README.md:844-848`) | Per-name forward returns with leave-one-day-out on the P4 round 4 files | open |
| 4 | Does the published code match the write-up? | Frankfurt's README describes basket and option strategies | the "polished" file never trades them *(checked: ran it)* (`prosperity3-frankfurt-hedgehogs/FrankfurtHedgehogs_polished.py:435`) | already settled by running it | resolved: use READMEs for parameters |
| 5 | Does DU's README match its code? | README: Mark 67 signal and Mark 22 logic (`prosperity4-du-trading/README.md:157-173`) | `round4.py` never reads `buyer`/`seller` *(checked: grep)* | already settled | resolved: do not rely on the README's counterparty claims |
| 6 | Is trading the smile worth it? | DTU fitted a parabola and traded it in rounds 3–4 (`prosperity4-dtu-quant-lab/README.md:141-163`) | Baguette Fromage (constant per-strike IV), DU (mean-reverting IV, huge spreads), Alpha Search (unstable surface) concluded no (`prosperity4-baguette-fromage/README.md:769-774`, `prosperity4-du-trading/README.md:120-123`, `prosperity4-alpha-search/README.md:103-109`) | Test on P4 rounds 3–4 data by worst day | open |
| 7 | How to trade the drifting product (Pepper Root)? | Market make around the drift with DP thresholds (Baguette Fromage) | long bias +76/80 with wide fills (DU); accumulate then mean-revert around the future mid (Alpha Search); buy-and-hold was the common baseline | Run the variants on round 1–2 data | open |
| 8 | Is it fair to use data or behaviour leaked from earlier editions? | Linear Utility used the previous year's public data and called it "fair game" (`prosperity2-linear-utility/README.md:182`) | Frankfurt reported the hard-coding loophole and IMC banned it (`prosperity3-frankfurt-hedgehogs/README.md:967-978`) | The Arena's Technical Rules; organisers verify and rerun top solutions (`ON_THE_DAY.md`) | depends on the Arena's rules |
| 9 | Are Prosperity's headline ranks skill? | Alpha Animals was 2nd after round 3 because a bug happened to pay (`prosperity3-alpha-animals/README.md:135`) | the other write-ups attribute their ranks to method | not settleable from the clones | caution only |

## Open questions no source answers
These are in `ON_THE_DAY.md`: whether the Arena is a shared market, the bot interface, the data format, the runtime limits and library list, the scoring formula. The Prosperity record is evidence for a bot-only market with a snapshot per tick; it is not evidence about the Arena's format.
