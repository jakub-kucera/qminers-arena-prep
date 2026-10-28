# Dry run log: round 1 rehearsal, 2026-10-28

Timed rehearsal of round 1 on a disguised exchange, the "Halden Exchange Open" (`data/arena/round1/rules.md`;
four products, resting orders, a 10-action cap, a taker fee, touch marking). One agent, all tracks, no playground
and no portal. Stopped, as instructed, at the first bot that passes `arena.validate`.

**The bot:** `python/bots/qminers/template.py` (56,733 bytes), validated at 15:33:36. Local result on the three
public sessions under the rules' fill model: 44,402 pips = 11,100.50 credits (per session and product:
`data/arena/round1/HANDOVER.md`, "Uploaded").

## Steps and clock times (Europe/Prague)

| time | step |
|---|---|
| 15:26:22 | `date`; start. Read `rules.md` in full, `example_bot.py`, the empty `HANDOVER.md`. |
| 15:26–15:28 | `RUNBOOK.md`, `ON_THE_DAY.md` in full, `ARCHITECTURE.md`'s plug-in paragraphs, `formats/drill.py`, the `qminers.py` skeleton, `engine.py`'s docstring and `run_market` (to map the Halden rules onto resting mode). |
| 15:29 | **Step 1 done:** the rules' answers, what they leave open and the nine contradictions with the repo at the top of `data/arena/round1/HANDOVER.md`. |
| 15:29:54 | Answers written under ON_THE_DAY.md's 17 "First hour" items; committed (8ec3083) **with `test_docs.py` failing**: the file went over its 70,000-character cap. |
| 15:30:11 | Fixed: ON_THE_DAY.md back to one pointer line to the HANDOVER (commit 2). |
| 15:30–15:31 | **Step 2:** `formats/qminers.py` rewritten (loader for gzipped JSON lines, tape shifted one step; a wrapper applying the exchange's per-action rules). One syntax error (a walrus inside a comprehension's iterable). |
| 15:31:36 | `arena.diagnose all --profile --suggest`: loader checked, four products read, a PARAMS entry each. |
| 15:31:44 | `experiments.day.structure` in the background: blocked by a permission prompt (output redirected outside the worktree). Not re-run. |
| 15:32–15:33 | **Step 3:** the template's PARAMS (suggest's) and ADAPTER (`_Api` over the update dict, `class Strategy` with `on_start`/`on_market`, and an action budget for the 10-action and 4-resting caps). |
| 15:33:17 | First backtest, 2026-05-11: 13,992 pips. |
| 15:33:36 | **Step 4:** `arena.validate ... --queue prob --queue-power 1 --mark touch --fee 1 --maker-fee 0 --time-limit-ms 50 --max-size 100KB`: Result OK (all PASS). |
| 15:34:07 | The swap's tests (`test_drill`, `test_skeletons`, `test_qminers_scaffold`, `test_docs`): 37 passed, 2 skipped. |
| 15:35:15 | Committed the plug-in, the bot, the HANDOVER and TODO follow-ups (2bbf24e). Stopped. |

From start to a validated bot: 7 minutes 14 seconds; to the commit: 9 minutes.

## What slowed me down

- **ON_THE_DAY.md's size cap.** The checklist says to write each answer under its "First hour" item, but
  `test_docs.py` caps the file at 70,000 characters and it had 797 left: 17 short answers took it to 73,134. Cost a
  commit with a failing test (my `&&` chain gated on `tail`, not on pytest) and a fix-up commit.
- **The permission layer, not the repo:** heredocs containing `{"` and output redirected outside the worktree were
  refused, so the structure scan never ran and a helper script had to be written to a file first.
- **Mapping the rules onto the engine** took the most thought: which tick's trades the engine matches versus shows
  the bot (`run_market`: the bot sees the previous tick's, orders meet this tick's), so the loader puts line n + 1's
  tape on tick n. Nothing in the docs states that convention in one line; I read the engine to find it.

## What in the repo's docs or tools was missing, wrong or misleading

1. **ON_THE_DAY.md: "write the answer in under each item" is impossible within its own size cap** (above). Either
   the cap gets room for the day or the file says answers go in the round's `HANDOVER.md`.
2. **No skeleton half fitted.** `qminers.py` is a CSV-snapshot loader with a `state -> [api.Order]` wrapper; this
   round was gzipped JSON lines and `on_market(update: dict) -> list[tuple]` with the bot's own refs. Both halves
   were rewritten from scratch; the drill's wrapper was the useful model (`Order.tag`, `fresh_each_tick`).
3. **The engine has no action cap that counts cancels, and no resting-orders cap.** `--max-orders` counts only new
   orders, so the Halden "10 actions including pulls" and "4 resting a product" rules live in the wrapper (and the
   bot's ADAPTER budgets them). `arena.validate`'s "most orders in a tick 15" counts engine orders (a `pull_all`
   becomes one Cancel per order), not the exchange's actions, so it reads like a breach of a 10 cap when it isn't.
4. **The engine's limit rule is Prosperity's** (every new order for the product rejected); Halden rejects one order
   at a time. The wrapper applies Halden's rule first, so the engine never sees a breaching order.
5. **The tape timing leaves one engine difference:** with the shift, a crossing snapshot's volume is spent from the
   next interval's tape (`_spend_crossed` on the same tick's trades), not the one that crossed us: slightly fewer
   trade fills than the exchange would give. Filed in `TODO.md`.
6. **The template's EXECUTION can stack top-up orders** at one price (keep the old order, send the difference), so
   a product can pass 4 resting orders; the ADAPTER resets the product when it would.
7. **The step order in the kickoff prompt:** step 2 asks for `experiments.day.premise` before the bot exists, but
   premise takes `--bot BOT`; it can only run after step 3. The RUNBOOK's premise line also says `--engine rust`,
   which needs the template's twin (not set up in a first hour).
8. **`ARCHITECTURE.md`'s "Formats are plug-ins" is a bold paragraph, not a heading**, while CLAUDE.md, the RUNBOOK
   and the prompt call it a section: `grep '^## Formats'` finds nothing.
9. **`diagnose --suggest` for VANTA** (large-tick, "making at a one-tick spread pays on both sides") gave the one
   product that loses on every session (−6,498 pips over three, at its limit 36% of the time). Not investigated
   before the stop: the first thing to test is VANTA quoting nothing or a capped `make_size`.
10. The rules' own title says "Round 3 Technical Rules" in a round-1 folder (flagged in the HANDOVER as open).
11. `--max-size 100KB` validates against 99,950 bytes: correct for a "100 kB" display, but unexplained in the output.

## Not done (stopped at the validated bot, as instructed)

`experiments.day.structure` and `experiments.day.premise` (so no premise table), the Rust twin's row, any grid,
`arena.stress`, the backtest under `--match-trades worse` as a second fill mode. Listed in `TODO.md`, "Follow-ups
from the 2026-10-28 round-1 rehearsal".
