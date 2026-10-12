---
title: heyman7913 / JaneRT, Prosperity 4 (19th)
type: source
repo: online-snapshots
status: partly-read
updated: 2026-10-11
---

# heyman7913 (team "JaneRT", Prosperity 4, 19th globally, 7th USA, their claim)

## What it is
A GitHub repo (101 files, 184 MB, 16 code files, no licence) with a 750-line README covering both the algorithmic and manual tracks. Read online; the README is saved as `references/online-snapshots/heyman7913_imc-prosperity-4.README.md`. Code not cloned.

## Layout and code map
Headings: Osmium `heyman7913_imc-prosperity-4.README.md:146`, Pepper Root `heyman7913_imc-prosperity-4.README.md:165`, **micro-price and signal fair value** `heyman7913_imc-prosperity-4.README.md:195`, Velvetfruit `heyman7913_imc-prosperity-4.README.md:268`, Hydrogel `heyman7913_imc-prosperity-4.README.md:290`, options `heyman7913_imc-prosperity-4.README.md:304`, **regime detection from the opening price** `heyman7913_imc-prosperity-4.README.md:356`, **named-participant signals** `heyman7913_imc-prosperity-4.README.md:373`, round 5 from `heyman7913_imc-prosperity-4.README.md:427`, manual track `heyman7913_imc-prosperity-4.README.md:532`.

Read in detail:
- **Osmium** (`heyman7913_imc-prosperity-4.README.md:146-162`): take aggressively beyond 6 ticks of 10,000 (up to 25 units, buckets at 6, 9, 12), otherwise quote in **two layers** (inner ±5, outer ±7) so the position limit does not leave them idle, with an inventory skew; **reserve 25 units for aggressive takes** regardless of passive fills (their biggest early mistake was not doing so). In hindsight they say Avellaneda–Stoikov would have been more principled than their ad hoc skew, and that bots crossing the spread clustered at certain times of day, which they never analysed.
- **Signal fair value** (`heyman7913_imc-prosperity-4.README.md:195-233`): the "micro-price" here is the volume-weighted mid `(bid × ask_vol + ask × bid_vol) / (ask_vol + bid_vol)` (`heyman7913_imc-prosperity-4.README.md:202`), blended `0.30 × micro + 0.70 × slow EMA + 2.0 × imbalance − inventory penalty` (`heyman7913_imc-prosperity-4.README.md:210`), imbalance `(bid_vol − ask_vol) / (bid_vol + ask_vol)`. A Spearman test said the signal predicts next-tick returns and fires on 12.6% of ticks (`heyman7913_imc-prosperity-4.README.md:226`); an imbalance weight of 3.0 was unstable on thin books.
- **Opening-price regime** (`heyman7913_imc-prosperity-4.README.md:356-371`): the day's opening Velvetfruit price indicated the regime; thresholds were blended from three regime centres (5245, 5267.5, 5295.5) with Gaussian weights, so a high-open day did not short at z = 2.5 too early.
- **Named participants** (`heyman7913_imc-prosperity-4.README.md:373-398`): they matched six recurring behavioural fingerprints in the data before names were revealed. **Mark 67**: 963 buys of Velvetfruit in three days, 58.8% positive at 50 ticks, effect lasting ~3,000 ticks; **Mark 55** informed flow on Velvetfruit; **Mark 01 and Mark 22** multi-strike option baskets; Mark 14/38 on Hydrogel. Each signal has a time-to-live (3,000 or 6,000 ticks) (`heyman7913_imc-prosperity-4.README.md:387-396`).

## What carries over
Capacity reservation for takes, two-layer quoting under a tight limit, a signal-fair blend with a Spearman check, opening-price regime thresholds, TTL-based signals. See [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [informed-counterparties](../concepts/informed-counterparties.md).

## Traps
- The "micro-price" is the volume-weighted mid, not Stoikov's micro-price (`literature_md/micro-price/`).
- Event-study numbers are the team's own; the other teams who looked at the same Marks disagree about which ones matter.
- 750 lines; the manual track (about 200 lines) is unrelated to our work.

## Read depth
- **Read:** `heyman7913_imc-prosperity-4.README.md` lines 146–162, 195–233, 356–398.
- **Mapped:** all headings.
- **Unread:** Pepper Root, Velvetfruit, Hydrogel, options, round 5 sections, the manual track, all code.

## Cited by
[market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [informed-counterparties](../concepts/informed-counterparties.md), [drift-and-regime-change](../concepts/drift-and-regime-change.md), [contradictions](../contradictions.md).
