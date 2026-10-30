# Dry run log: round 1, the Kestrel Bourse (timed rehearsal, 2026-10-30)

The "before" checkout (24a536a). Start 12:07:09, submission deadline 13:07. Alone, all tracks. Stopped at 12:22, once
a validated bot had been uploaded and the engine had been fitted to its metrics and set in the plug-in.

## Steps and clock times

| Time | Step |
|---|---|
| 12:07 | `date`; read `rules.md` in full, `example_bot.py`, RUNBOOK, ON_THE_DAY.md (two reads), the plug-in skeleton, `drill.py`. |
| 12:09 | **Step 1:** the rules list at the top of `data/arena/round1/HANDOVER.md`: three products (not one), what the rules settle, what they leave open, eight contradictions with the repo's assumptions. |
| 12:10 | **Step 2:** `formats/qminers.py` written (loader for level-change CSVs and prints; wrapper for module-level `setup`/`step` with action dicts, the 6-action and 3-working caps, cancels first). Copied in shape from the mock round's `results/before/qminers_format.py`. `arena.diagnose --profile --suggest` ran first time. `experiments.day.structure` in the background. |
| 12:11 | **Step 3:** the template's PARAMS (suggest's, as given) and ADAPTER (`_Api` over ctx and view, the mock round's action budget: cancels, then takes, then posts, products rotated, posts past the cap dropped). First backtest: +207,343 units = +4,147 credits under `all`. |
| 12:12 | **Step 4:** `arena.validate --time-limit-ms 100 --max-size 100KB`: OK under `all` and `worse` (57 KB, slowest step 7 ms). Backtests: `worse` +492 credits, `none` −540. |
| 12:12–12:15 | Upload attempts: (1) blocked by a permission prompt on `echo "exit $?"`; (2) the portal crashed at import on `EngineConfig(max_actions=...)`; (3) after backporting main's engine caps, it named a file the blocked command never copied (REJECTED, not counted); (4) it evaluated, then crashed importing main's `experiments.day.calibrate`. Status stayed 0 of 3 throughout. Fixed by running the portal from a checkout of main (`git worktree add --detach results/portal_wt main`, our plug-in copied in, `uv run --directory results/portal_wt python …/portal.py upload …`); the engine backport reverted. |
| 12:15:17 | **Upload 1 completed** in ~1 s (E ≈ 1 s): **−4,849.91 credits**, breachPenalty 4,002.25, fills 4,130, volume 38,508, inventory 113. Predicted +4,147 (`all`) / +492 (`worse`). |
| 12:16 | Results ZIP read: the orders file stamps each NEW/CANCEL **one step after** the call that sent it, and the log has ~1,800 "new orders refused: 3 orders already working" a session. Diagnosis: a one-step latency; the bot can't see what it sent last step, so it double-posts, its cancels land late, and doubled quotes overfill the limits. |
| 12:17 | `LATENCY = 1` in the wrapper (a step's actions held and released next step, checked against the orders working on arrival). Upload 1's file: `all` −3,356 credits, 5,608 fills. |
| 12:18 | **`worse`: fills, volume, end position and penalty exact.** `--mark last`: score −242,495.73 units = −4,849.9146 credits, cash −32,874.1646, both the portal's to the cent; `pnlSe` = our "s.e. days". |
| 12:19 | The fitted settings set in the plug-in (`ENGINE`) and read by `arena.cli.setup`; a flagless backtest reproduces the portal. premise: all three products Prosperity-like. `arena.validate` now FAILs the uploaded bot (5,291 refused posts, the portal's own). |
| 12:20–12:23 | HANDOVER, ON_THE_DAY answers (19 items), IDEAS row, TODO items, this log; tests; commits. |

## Engine settings chosen, and the evidence

All in `python/arena/formats/qminers.py`, used by every `arena.*` tool without flags:

| Setting | Value | Evidence |
|---|---|---|
| `RESTING` | True | rules §3 (GTC rests until filled or cancelled) |
| `LATENCY` (new, in the wrapper) | 1 step | upload 1's orders file (NEW a step after the call) and its refusals; with it, every metric matched |
| `trade_matching` | `worse` | under `worse`: fills 4,130, volume 38,508, penalty 4,002.25, end position 113, all exact; `all` gave 5,608 fills, `none` 2,734 |
| `mark` | `last` | score and cash to the cent (mid off by 11.4 credits, touch by 102.4) |
| `limit_penalty` | 0.125 points | rules §4 (0.25 credits a lot a step, 2 credits a point); penalty matched exactly |
| `fee_bps` / `maker_fee_bps` | 2 / −0.5 | rules §4; cash matched to the cent (without the rebate, 863 credits off) |
| queue | `back` (default) | moot under `worse` |

The engine's error `T` on upload 1: 0.

## What slowed me down

1. **The portal didn't run against this checkout** (about 4 minutes, two crashes): it needs `EngineConfig.max_actions` and
   `experiments.day.calibrate`, which exist only on main. A rehearsal-kit problem, not the repo's, but on the day an
   equivalent mismatch would be fatal; filed in TODO.md.
2. **A blocked command half-ran:** the permission prompt on `echo "exit $?"` blocked the whole chain, including the `cp`
   that made the upload copy, so the next upload pointed at a missing file. Keep upload commands to one operation.
3. **Shell loops and variables need approval** in this harness, so each fill-mode run was its own command.
4. Writing HANDOVER through a heredoc failed ("backslash-escaped whitespace"); one Edit per section worked.

## What in the repo's docs or tools was missing, wrong or misleading

1. **Latency had no place in the checklist.** ON_THE_DAY.md covers a late exchange only as probe 3, in a playground. With
   no playground, the only evidence was the results ZIP's timestamps, and neither the calibration pack nor RUNBOOK says to
   read them. The engine's `--delay` can't reproduce this exchange either, because the cap on working orders has to be
   checked when the orders arrive. The wrapper had to hold the actions itself. Filed: TODO.md, "Latency is read from the
   first upload's orders file, not only from probe 3".
2. **The template's ADAPTER pattern assumes its view shows everything it sent.** Neither the drill's pattern nor the mock
   round's handles orders in flight, and the uploaded bot failed because of it (−4,850 against +4,147). Filed: TODO.md,
   "The qminers ADAPTER under a one-step latency". That is the first job after this log.
3. **Engine settings had nowhere to live in this checkout.** Only `RESTING` could sit in a plug-in, so every command needed
   five flags, as the 2026-10-28 rehearsal found (TODO.md, "A format sets the engine settings its rules fix"). I added a
   minimal `ENGINE` read by `arena.cli.setup`. The day experiments still build their own Prosperity-rule config, so
   premise's PnL is not this market's. Main's 87633cf and 9fd3d02 fix both.
4. **The checklist's "timestamps onto 0..999,900 in steps of 100"** can't hold with 6,000 steps (n × 1,000,000 // 6,000
   isn't a multiple of 100). Nothing broke, but the rule reads as if it must.
5. **Validate's "most orders in a tick 10"** counts working orders, not actions sent. With a 6-action cap it reads like a
   breach (the 2026-10-28 rehearsal noted the same; main's 38babf7 fixes it).
6. **Helpful:** the mock round's committed `results/before/qminers_format.py` and template ADAPTER were the closest model
   (a dict API with caps), much closer than `drill.py`. The checklist doesn't point to them; it should.
7. **Process:** the steps' commits were merged into one (the plug-in's latency landed in the same file before step 3's
   commit), against CLAUDE.md's one commit per step.

## State at the stop (12:23)

- Uploads: 1 of 3 used (upload 1, −4,849.91 credits, final by default).
- The committed template is upload 1's bot, which fails `arena.validate` under the fitted wrapper. Next: the in-flight
  ADAPTER fix, validate, then grids under `--modes worse,all,none --gate first --holdout last`.
- `results/portal_wt` is a detached worktree of main used only to run the portal; remove it with
  `git worktree remove results/portal_wt` after the rehearsal.
