# Dry run log: round 1

- 15:06 Start. Copied public files to data/arena/round1/. Deadline 19:35; strategy freeze 19:05 (2E = 10 min < 30). Validated bot due 17:05.

## Step 1: rules and API (finished 15:09) — "stop and show me" list

Answers written under each "First hour" / "Before the first submission" / "Every round" item of ON_THE_DAY.md, sourced to `data/arena/round1/rules.md`.

**Not a single product:** three instruments, CALDERA (tick 0.10, limit 15), LUMEN (0.05, 120), OBERON (0.02, 60).

**What the rules settle that contradicts the repo's default (Prosperity) assumptions:**
1. Interface: module-level `trade(snapshot, memory) -> list[dict]` + optional `init(session)`, dict snapshots, no `Trader` class, no datamodel module. New ADAPTER and plug-in (planned).
2. Orders rest (GTC default; IOC available). Repo default is per tick: every backtest must be `--resting` (format `RESTING = True`).
3. Prints fill a resting order only when strictly through its price, never at it: `--match-trades worse`. Queue position never matters, so `--queue` is moot.
4. Crossing snapshot fills at our price up to the shown volume, and the bot sees the snapshot minus it: as our engine's resting mode. But our engine also spends that volume from the tick's market trades (`_spend_crossed`); the rules don't. Small understatement.
5. Limit check: position + all buys (resting+new) > limit rejects every NEW order of that instrument that step (resting untouched): our resting-mode rule, not Prosperity's. Rejected, not charged.
6. Decimal prices, a different tick per product, orders off the grid rejected: loader in integer cents, the bot in ticks (as the drill).
7. State: `memory` dict, JSON-serialised, at most 100,000 chars, reverted on error/timeout. Not a traderData string.
8. At most 50 actions a step; ids are ours (unique, at most 32 chars): ADAPTER must keep an id counter in memory and cap actions.
9. Errors/timeouts discard ALL actions of the call (not per product); 100 ms per call.
10. Scoring: final-snapshot mid (last mid if a side is empty), summed over sessions; no fees, no penalty, no liquidation.
11. Market is a replay, not shared with teams: `--vs`, rivals and the zoo-as-herd don't apply.
12. Submissions: 3/round, 100 kB; a file that fails to load does not count; "your last accepted submission is final" (contradicts the portal code's "mark an earlier one final"). Feedback is on the three public sessions = the download, so the portal score is in-sample (engine check only). Final score on 2 later hidden sessions.

**Left open by the rules:**
- Whether liquidity we consume stays consumed on later snapshots (rules: "they only consume the liquidity they trade against").
- Whether the portal's figures (mark-out price, breachPenalty, pnlSe) are what the rules describe; the portal's "mark final" vs the rules' "last accepted is final".
- How rounds combine and whether ranking is relative; permitted resources and any market-abuse clause (not in the rules).
- Whether a print with an empty aggressor fills both sides' resting orders (rules: by price only, so yes).
- Whether the hidden sessions are like the public ones (level, volatility).
- "Is the data a real series in disguise?": needs approval and budget; not done.

**Assumed approved; carrying on.**

## Step 2: format plug-in + diagnose (finished 15:10)
- `python/arena/formats/qminers.py` (copied from drill.py's pattern, ~270 lines), registered in FORMATS, `RESTING = True`. Prices in integer cents, timestamps seq × 100, prints of seq attached to tick seq (orders placed at seq fill against them; the bot sees them at seq + 1). Wrapper: init/trade, memory JSON round-trip and revert on error, 100k-char memory cap, ids/duplicates/off-grid/50-action checks (raise when strict, drop as the exchange does otherwise).
- `uv run python -m arena.diagnose all --format qminers --data data/arena/round1/data` (1 s):
  - CALDERA: spread 6t, jumps of 6+ spreads snap back (85/86/84% of ~600 a day), wall mid jumps 6% of ticks, slow rev 1.8. Own check: the mid moves ONLY in steps of exactly 6.00 CR (60 ticks), from 130.00 every morning; a huge random walk otherwise (daily sd 26 CR).
  - LUMEN: spread 14t, reverts to a level (slow rev 4.2), MM pays 0.50 of the spread. Daily means 100.22 / 100.03 / 99.76, intraday sd ~0.9 CR (18 ticks): a level at 100.00.
  - OBERON: spread 4t, mid AC1 −0.50 (signature 36.7), wall jumps 30% of ticks, slow rev 4.4, MM pays 0.39. Daily means 50.03 / 50.03 / 49.84, sd 0.1.

## Step 3: our bot (finished 15:12)
- `python/bots/qminers/template.py`: template DEFAULTS/STRATEGY/EXECUTION verbatim, new docstring/imports/PARAMS/ADAPTER (~150 lines of ADAPTER). PARAMS: CALDERA jump mode (jump_min 30, jump_edge 10, make_size 0, fair mid); LUMEN level 2000 ticks (100.00), level_band 20, clear_edge 7, make_edge 2; OBERON wall_mid, make_edge 1.
- First backtest (resting, worse): 6,471,678 cents = 64,716.78 CR over 3 sessions (CALDERA 59,934; LUMEN 5,326; OBERON −544 CR).

## Step 4: validate (finished 15:13)
- `arena.validate ... --format qminers --data data/arena/round1/data --match-trades worse --time-limit-ms 100 --max-size 100KB`: Result OK. Same under `--match-trades all` (PnL within 0.01%).
- Slowest tick 53 ms against a 100 ms limit: the bot's own calls take ≤ 0.3 ms; a deterministic ~10 ms pause at the same seq every run (and 50 ms in the validator) is Python's GC over the backtester's heap, not the bot.
- **Upload candidate 1 (would tell the user now):** `python/bots/qminers/template.py` as of 15:13 (45,687 bytes). Local result on the three public sessions (resting, worse, mark mid): total 64,716.78 CR; by session 21,334.80 / 20,956.69 / 22,425.29; by instrument CALDERA 59,934.30, LUMEN 5,326.05, OBERON −543.57. Expected metrics (session 2026-03-04, CR): fills CALDERA 1,475 / LUMEN 695 / OBERON 5,472; end positions −15 / +120 / −39; marks 52.00 / 100.65 / 50.13; breaches 0; errors 0.
- Upload/portal steps skipped (dry run): no evaluation, no --mark mid/touch/last fit against the portal, E taken as 5 min. The rules settle the mark (mid), so `--mark mid` is used throughout.
- Candidate 1 frozen as `data/arena/round1/c1_template.py`.

## Step 5: improve (finished 15:23)
Every change is the grid's `pick` (StepM, beats the bot as is under worse and all) or a stress setting; held-out days agreed (leave-one-day-out picked the same cell).
- OBERON: make_edge 1 → 4, take_edge 1 → 2: +54,875 cents (−54k → +518). Level (2500 / "day"), weighted_mid, imbalance −1.2: no significant gain (SPA p 0.46–0.81), not taken.
- LUMEN: make_edge 2 → 7: +8,535 (pick). level_band 15 was best in-sample but held-out chose 15/25/20 by day: kept 20. level_exit 0, level_guard 2/3, level_weight 3000: all worse, also under stress.
- CALDERA: take only stays (quoting −2.7..−4.8M, reduce-only quotes −0.5M, limit 6–12 −0.7..−2.6M, jump_edge 4 −116k). The bot captures ~59% of an unlimited-liquidity oracle (~34k CR/day); the gap is the top level's 5–9 lots: a 30-lot flip takes 3–4 steps (checked in the timeline).
- arena.stress: stop_loss ≈ 3× plain drawdown, converted to ticks: CALDERA 11,000, LUMEN 25,000, OBERON 1,000 (never fire in-sample). Worst stressed product: LUMEN on a trend, −1.2k / −1.7k CR over 3 days (against +5.4k plain).
- ADAPTER: prices below one tick are clamped (sells) or dropped (buys) — stress vol2 drove CALDERA's book negative and the bot sent `price -1.7`; PARAMS may now ask for less than the exchange's limit.
- `uv run pytest`: 383 passed, 30 skipped (references/ absent).
- Rust twin not attempted: every grid ran in 5–14 s in Python.

## Step 6: final candidate (15:23, well before 19:05)
- **File to upload:** `python/bots/qminers/template.py` (46,162 bytes). `arena.validate ... --format qminers --data data/arena/round1/data --time-limit-ms 100 --max-size 100KB`: Result OK under `--match-trades worse` and `all`.
- **Local PnL (three public sessions, resting, mark mid), in CR:** worse 65,350.88; all 65,350.88 (identical: under the rules a print at our price never fills us, and the bot rarely rests at the touch).
  - By session: 21,564.14 / 21,167.68 / 22,619.06. By instrument: CALDERA 59,934.30, LUMEN 5,411.40, OBERON 5.18.
  - Expected metrics, session 2026-03-04 (CR): fills CALDERA 1,475 / LUMEN 310 / OBERON 83; volume 8,929 / 2,848 / 442; end positions −15 / +120 / 0; marks 52.00 / 100.65 / 50.13; breaches 0; errors 0.
- **What it is:** the template with the Arena ADAPTER; CALDERA fades every 6.00 jump with the full limit (take only); LUMEN holds ±120 against moves of 1.00 from 100.00 and quotes at the touch; OBERON quotes 4 ticks from the wall mid (≈ flat).
- **Submission plan** (would be told to the user): upload 1 = this file (final at once); only re-upload if the portal's per-instrument PnL disagrees with the figures above beyond the engine's error; keep the third in reserve. Last upload no later than 19:25 (2E = 10 min before 19:35).
- Hidden-session risks: LUMEN's level is a constant 100.00 (all three public days agree; untestable out of sample); CALDERA's jump gate (5 jumps, 60% reversing, measured on the day) switches the fade off if the pattern isn't there.

## Problems found (prompt, docs, tools), each with its fix
1. The rules file is titled "Round 2 Technical Rules" while the prompt says round 1. Fix: name the round consistently in the rehearsal's files (harmless here).
2. **Bug, `arena.grid`'s smoke test dropped `Day.info`** (`python/arena/grid.py:629` rebuilt the Day without it): every grid in a format with per-product ticks crashed (and the drill format would silently price at its 0.01 fallback). Fixed in the working tree; needs a test (TODO.md).
3. `arena.stress` reported "! 9313 bot errors across the runs" with no message; finding them (vol2 drove CALDERA's prices negative, the bot sent `price -1.7`) took a custom script. Fix: print each run's first error. The bot-side fix (clamp prices) is in the ADAPTER.
4. Units: reports, `--metrics` and `arena.stress` print the loader's unit (cents), `stop_loss` and PARAMS are in each product's ticks (0.10 / 0.05 / 0.02), and the portal shows credits. "stop_loss ≈ 3× plain drawdown" is off by 2–10× unless converted. Fix: added a line to ON_THE_DAY.md's format swap; better, have stress print the drawdown in ticks per product.
5. `arena.validate`'s "slowest tick" (43–53 ms against a 100 ms limit) is the backtester's own GC pause at a fixed seq; the bot's calls take ≤ 0.3 ms. Misleading near a tight limit. Fix: `gc.freeze()` after loading days, or report p99 beside the max.
6. `--max-size 100KB` is read as 102,348 bytes (binary units, the dashboard's convention); the rules' "100 kB" may be 100,000. Harmless at 46 KB. Fix: validate could warn when the file is within the gap between the two readings.
7. No tool builds a format's template: the bot was spliced by hand from template.py's DEFAULTS/STRATEGY/EXECUTION (`experiments.format_drill --sync` only targets the drill bot), and nothing checks that the qminers bot's core still matches the template. Fix: generalise `--sync` to any target and add a test like `test_drill.py` (TODO.md).
8. ON_THE_DAY.md's "The format swap" says copy drill.py, but this data was snapshots (like Prosperity) with a function API (like neither); fine, but the data half was closer to prosperity.py's loader. Fix: say "copy whichever of the two is closer, data and API separately".
9. ON_THE_DAY.md has no step for mapping a session onto the template's 0..999,900 timestamps (`flatten_from`, `day_length`, stress sizes assume it) nor for letting PARAMS cap the limit below the exchange's (the drill ADAPTER silently overrides PARAMS' `limit`). Fixed in ON_THE_DAY.md's step 5.
10. ON_THE_DAY.md said `experiments.p4_jumps` is "Prosperity format only until the Arena's loader exists": with the loader it ran (`--format qminers`). Fixed the line.
11. `arena.diagnose` notes the snap-back but not the lattice: CALDERA's mid moves only in exact 6.00 steps, which a custom script found (`p4_jumps`' "on 100s" column hints at it). Fix: a diagnose note "the mid moves on a lattice of N ticks".
12. Our engine also removes a crossed snapshot's volume from that tick's prints (`_spend_crossed`); the rules don't. Under `worse` it barely matters; noted under "Which backtest settings match the playground?".
13. ON_THE_DAY.md is 338 lines (~26k tokens): the Read tool's 25k cap truncates it, so the first read needs two calls. Fix: split "First hour" into its own file, or keep a one-screen summary table of the items with an "answer" column.
14. The prompt's step 4 ("validate under both fill modes the rules make plausible") and its `--mark` fit assume the rules leave these open; here the rules settle both (`worse`, mid). Fix: "if the rules settle the fill mode and the mark, use them, and validate once more under `all` as a sensitivity check".
15. The rules don't say what happens beyond 50 actions a step; the wrapper (and the bot) truncate to 50. Logged as an assumption.
16. The prompt asks to "commit each step" and to "tell me when each step is done", but there was no natural place to record the 'stop and show me' list other than this log; on the real day, the ON_THE_DAY answers serve, but the list of contradictions has no home there. Fix: a "Rules vs our assumptions" subsection under "Rule changes".
17. Time: the validated bot was ready 7 minutes after the start (15:13), well inside the 17:05 target; grids took 5–14 s. The prompt's timeline is generous for a 3-product market of this size; the binding constraint was ideas, not tooling.
