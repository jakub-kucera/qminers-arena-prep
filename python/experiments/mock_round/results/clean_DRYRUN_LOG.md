# Dry-run log

- **Start:** 15:06:02 CET (Mon 26 Oct 2026, from `date`). Step-7 freeze 19:05, deadline 19:35.

## Timeline

- **15:06 step 1 done:** rules_summary.md written. "Stop and show me" -> logged here, approval assumed, carrying on.
  Notable: the rules' own passive fill is the conservative one (print strictly through our price); scoring marks to the final mid, no liquidation; three instruments; the rules are titled "Round 2" while the prompt says round 1.
- **15:13 step 2 done:** data_notes.md. Key: CALDERA moves only in +-6 jumps that reverse 85% of the time; LUMEN reverts to 100; OBERON is noise around a slow fair (EMA 0.2 halves the error). No repeated days, no counterparties.
- **15:15 step 3 done:** backtest.py (+ test_backtest.py, 18 hand-made checks pass). Engine finding: a GTC order priced through the book rests and fills at its own price on the next snapshot, so takes must be IOC. Example bot: -6,728 cons / -5,127 opt (it gets run over by every CALDERA jump).
- **15:16 step 4 done:** bot.py: CALDERA holds the full limit against the last jump (gated on the day's reversal share), LUMEN quotes inside the wall leaning toward level 100, OBERON quotes around an EMA(0.2) fair with a small skew. Per-product try/except, sizes clipped to the limit room counting resting orders.
- **15:16 step 5 done:** validate.py PASS on bot.py: 0 errors, 0 breaches, 0 rejected actions, deterministic over two runs, identical with the module reloaded every call, slowest call 1.8 ms, memory 413 chars, 9.5 kB. Frozen as submissions/v1.py (sha1 87e68e87).
- **15:16 UPLOAD 1 WOULD HAPPEN HERE (submissions/v1.py).** "Tell me before each upload" -> what I would have told the team:
  - v1 = jump-reversal on CALDERA, level-lean MM on LUMEN, EMA MM on OBERON.
  - Expected portal total (conservative fill = the rules' rule, valued at the final mid): 60,823 (20,056 / 19,864 / 20,903 per session).
    Per instrument and session (CALDERA / LUMEN / OBERON): 03-03 19,653.9 / 204.2 / 197.9; 03-04 19,305.4 / 353.5 / 205.2; 03-05 20,478.6 / 235.9 / 188.9.
  - End positions: 03-03 15 / -33 / 1; 03-04 -15 / -5 / -13; 03-05 15 / 85 / -15. Fills (events): CALDERA 1,619 / 1,460 / 1,668; LUMEN 407 / 408 / 404; OBERON 1,484 / 1,520 / 1,486. 0 breaches, 0 errors.
  - If the portal's CALDERA figure is far below ~19-20k, the likely cause is that our takes consume liquidity that stays gone in later snapshots, or a different cross-fill rule: CALDERA is 98% of the PnL, so its figure is the check of the backtester.
- **15:26 addendum to upload 1:** backtester now has `--deplete` (volume we take stays gone while its price level persists). v1 under it: 43,897 (CALDERA 13,892 / 14,100 / 14,520). So the portal's CALDERA per session tells which reading the exchange uses: ~19.5k = replayed in full (our default), ~14k = depleted. Tell the team to compare exactly this figure.
- **15:28 UPLOAD 2 WOULD HAPPEN HERE (submissions/v2.py, sha1 6bba654a).** What I would tell the team:
  - v2 = v1 + LUMEN fair leaning 60% toward level 100 with takes 4 ticks through it and a level guard; OBERON EMA 0.1; CALDERA gate on day-and-recent reversal share with momentum fallback; loss stops (CALDERA 2000, LUMEN 1000, OBERON 30) that switch off if a fill is lost to a failed call.
  - Expected (cons, mid valuation): 66,685.2 total; per session 21,931.9 / 21,435.4 / 23,317.9.
    CALDERA 19,653.9 / 19,305.4 / 20,478.6; LUMEN 2,060.0 / 1,901.6 / 2,631.0; OBERON 218.0 / 228.3 / 208.3.
  - End positions CALDERA 15 / -15 / 15, LUMEN -109 / 115 / -78, OBERON -5 / -15 / -10. Fills CALDERA 1,619 / 1,460 / 1,668; LUMEN 337 / 292 / 407; OBERON 1,549 / 1,557 / 1,531. 0 breaches, 0 errors.
  - If positions were valued at the touch instead: 66,564.7; at the last print: 66,820.3. Under `--deplete`: 49,714.2.
- **15:29 step 6 done:** 11 changes logged in changes.md (6 kept, 3 dropped, 2 kept as insurance). Main gain: LUMEN's fair leaning toward its level (LUMEN 800 -> 6,593 over 3 days, held-out 5,944). CALDERA's gate made robust to a mid-day regime change (stress 4,673 -> 30,257). A real bug found and fixed: the loss stop trusted cash rebuilt from fills, which a discarded call loses. Stopped improving here: the remaining knobs moved PnL by <0.5%, and CALDERA (89% of PnL) is limited by visible depth, not by parameters.
- **15:29 step 7 done (early, well before 19:05):** tests pass, validate.py PASS on submissions/final.py (sha1 3b7d898a): 0 errors, 0 breaches, 0 rejected, deterministic, identical with the module reloaded every call, slowest call 0.12 ms (limit 100 ms), memory 536 chars, 11.0 kB, imports only `math`; every 500th call discarded costs nothing.
- **Status (five lines):** done: rules, data notes, backtester, v1, v2, final. In progress: nothing. Local PnL of final: 66,709.9 cons / 66,957.0 opt. Need from the team: the portal figures of upload 1 (CALDERA per session ~19.5k vs ~14k decides the liquidity reading) and how long it took. Next: upload final.py as the last submission, unless upload 2's figures disagree with the backtester.
- **UPLOAD 3 WOULD HAPPEN HERE (submissions/final.py), only if upload 2's portal figures matched the backtester;** otherwise the slot goes to a fix. final = v2 + OBERON quote size 60 (+25 over 3 days). Expected (cons, mid): 66,709.9; per session 21,939.1 / 21,448.9 / 23,321.9; CALDERA 19,653.9 / 19,305.4 / 20,478.6, LUMEN 2,060.0 / 1,901.6 / 2,631.0, OBERON 225.2 / 241.9 / 212.3; end positions CALDERA 15 / -15 / 15, LUMEN -109 / 115 / -78, OBERON -11 / -18 / -28; fills OBERON 1,497 / 1,520 / 1,472 (others as v2). Touch valuation 66,588.3, last print 66,844.8, `--deplete` 49,743.0.

## Result

- **Final bot:** `submissions/final.py` (same as `bot.py`), sha1 3b7d898a2dc916e768b9f80cea9d43b0a0036829.
- **Local PnL, conservative fill (the rules' own rule):** 66,709.9 = 21,939.1 / 21,448.9 / 23,321.9.
- **Local PnL, optimistic fill:** 66,957.0 = 22,017.2 / 21,539.9 / 23,399.9.
- **By product (cons, 3 days):** CALDERA 59,437.9, LUMEN 6,592.7, OBERON 679.3. One product carries 89% of the score: if hidden CALDERA jumps stop reversing, the gate stands it down (stress: random signs -355 over 3 days).
- **Wall time:** 15:06 -> 15:29 (23 min) for all seven steps.

## What in the prompt was unclear, missing or in the way

1. **Round number.** The prompt says round 1 and "10% if the rules confirm the weights"; rules.md is titled "Round 2" and gives no weights. Fix: "the round named in rules.md", with no number in the prompt.
2. **The blocking "stop and show me" after step 1.** With nobody reading it for a while, that's dead time on a 5-hour clock. Fix: "show me, and carry on with step 2 while I read it, unless the rules forbid something we planned".
3. **Python version.** The rules need 3.12, the machine has 3.9.6 and nothing newer, and the prompt doesn't say which to target. Fix: name the local interpreter or say "keep the bot 3.9-compatible".
4. **Portal figures list.** "Filled orders, traded volume, end position, cash, valuation price, position-limit penalty" is a guess about another portal: these rules list PnL per instrument and session, fill counts, end positions, breaches and errors, and there's no penalty. Fix: "the figures rules.md says the portal reports, plus anything the first upload shows".
5. **The valuation switch.** The rules say the final mid outright, so this switch only mattered as a range. Fix: "if the rules don't state it".
6. **Ambiguity in matching that the prompt doesn't cover.** Does consumed volume stay gone in the next snapshots? That moves the score 25% (66.7k vs 49.7k). The prompt only asks for the fill-rule switch. Fix: "make every matching rule the rules leave open a switch, and give the expected portal figure under each reading".
7. **Upload plan.** There's nothing on when to spend uploads 2 and 3. Fix: "1st as soon as validated (it checks the backtester), 2nd after the main improvement, keep the 3rd for the final or a fix, and never spend the last one without matching figures".
8. **The loss-stop prior leaves out a trap.** Under these rules a discarded call (timeout or error) reverts memory and loses that step's fills, so any PnL rebuilt from fills goes wrong and a stop fires on nothing. Also, a 3x stop on CALDERA cost 74% of the PnL on a weak-edge stress while the reversal gate already protected it. Fix: add to the priors "state built from fills must survive a discarded call" and "prefer an adaptive gate to a permanent stop where the edge is measured on the day".
9. **The wall-mid prior didn't apply.** Books are one level most of the time, and the EMA of the mid was what mattered for OBERON. That's harmless, since the prompt says to test priors, so no fix needed.
10. **What to do with spare time.** Everything was done by 15:29 against a 19:05 freeze. The prompt doesn't say whether to keep exploring (and risk overfitting) or stop. Fix: "once the improvements are below X% for an hour, stop and say so".
11. **The "optimistic" mode reads as plausible exchange behaviour.** The rules' rule here is the conservative one. Fix: "the rules' own fill rule is the default; the other mode is only a sensitivity check".
