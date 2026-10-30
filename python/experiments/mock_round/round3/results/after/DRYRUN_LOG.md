# Dry run log: rehearsal 3, round 1 (2026-10-30, the "Kestrel Bourse")

One agent, alone, from the round's rules and data to a validated upload and an engine fitted to it. Deadline
13:25. Stopped at 13:06 once both stop conditions held: a validated bot uploaded once, and the engine settings
fitted to its metrics and set in `python/arena/formats/qminers.py`'s `ENGINE`.

## Steps, by the clock (`date`)

| Time | Step |
|---|---|
| 12:25:37 | Start. Read `rules.md` in full, `example_bot.py`, `RUNBOOK.md`, `ON_THE_DAY.md` (two reads), the plug-in skeleton, `drill.py`, the engine's settings. |
| 12:27 | Peeked at the data: book rows are level-indexed (level 1–3 per side), prints at a step's clock trade against that step's book. |
| 12:28 | **Step 1 done:** the rules list (settled, open, contradicting the repo) at the top of `data/arena/round1/HANDOVER.md`. Three products, not one. |
| 12:29 | **Step 2:** `qminers.py` written (level-indexed book-change loader, `ArenaBot` wrapper for `setup(ctx)`/`step(ctx, view)` with cids, the 6-action cut, cid checks; `ENGINE` from the rules: fees, rebate, penalty, caps). `arena.diagnose --suggest` ran first time: BRAM large-tick, OPHIR jumping 8%, TALC slow level. |
| 12:30 | `experiments.day.structure` started in the background (BRAM's wall mid strongly mean-reverting, TALC reverting, 17% of OPHIR's prints at no shown price). Read the day-one wiki page. |
| 12:30–13:01 | **Step 3:** the bot's PARAMS and ADAPTER (`setup`/`step`, an `_Api` around ctx and view, the action budget shared across products by turns, `max_resting` passed to `execute`). Most of this half hour was the agent's own writing time plus a response cut off mid-stream and a heredoc the sandbox refused. |
| 13:01:07 | First backtest: 85,691 units with OPHIR quoting (OPHIR −10,107): OPHIR set to take only (`make_size` 0) by the day-one table's jump row. |
| 13:01:30 | **Step 4:** `arena.validate` OK under `all` and `worse`, 100 ms, 100 kB (55,853 bytes, slowest step 0.2 ms). Local: +4,714 credits (`all`), +1,048 (`worse`). |
| 13:01:48 | **Upload 1** (of 3): **−283.01 credits**, breach penalty 198, 1,937 fills. E ≈ 1 s. |
| 13:02 | Read the ZIP: 1,858 "3 orders already working" refusals on day 1; the orders CSV stamps step 0's orders at 10:00:00.250, so orders arrive a step late. |
| 13:02:30 | `experiments.day.calibrate --scale 0.02 --vary delay=0,1`: exact fit (0.0% on all 12 figures). |
| 13:03 | Fitted settings into `qminers.ENGINE`; `arena.backtest` of the uploaded file now gives −283.02 credits. The swap's three test files passed (21 passed, 2 skipped). |
| 13:04–13:06 | Filed it: rule answers under ON_THE_DAY's "First hour" items, the IDEAS row "Orders that arrive a tick late", HANDOVER's sections, four TODO items, this log; commits. |

Not reached (the stop came first): step 5's grids, `arena.stress`, `experiments.day.premise`, the Rust twin, a
second upload.

## Engine settings chosen, and the evidence

| Setting | Value | Evidence |
|---|---|---|
| `resting` | True | rules §3: GTC orders rest until filled or cancelled |
| `fee_bps`, `maker_fee_bps` | 2, −0.5 | rules §4: taker 2 bps of value, maker rebate 0.5 bps |
| `limit_penalty` | 0.125 (points a lot a step) | rules §4: 0.25 credits a lot beyond the limit after each step, no rejection; matched the portal's 198.00 exactly |
| `max_actions`, `max_resting` | 6, 3 | rules §3 |
| `delay` | 1 | not in the rules: the orders CSV's timestamps, and calibrate (delay 0 never came near) |
| `trade_matching` | worse | calibrate: 0.0% off; no `all` setting in the top 12 |
| `mark` | last | calibrate: 0.0% off against mid 0.9%, touch 3.9% |
| `deplete` | off | calibrate: on is 14.9% off |
| `queue` | back (the default) | can't be told apart: under `worse` the queue doesn't matter; back, prob and front all 0.0% |

## What slowed me down

- **The agent's own writing time**: half an hour between diagnose and the first backtest went on writing the
  ADAPTER and on a response cut off mid-stream, not on running anything. Every tool call took seconds.
- **The sandbox:** a Python heredoc with braces and quotes, `$?`, `&` and a redirect to `/tmp` were refused, and so
  was `cp` out of the round's `uploads/` folder (outside the worktree): the metrics JSON was rewritten by hand from
  the printed output and the ZIP read in place. Writing helper scripts to files worked.
- Reading `ON_THE_DAY.md` in full (two reads) before the plug-in: most of it was not needed for the first upload.

## What in the repo was missing, wrong or misleading

1. **No in-flight orders anywhere in the template.** `execute(..., max_resting=N)` (the swap's step 3) counts only
   what the exchange lists, so on an exchange that applies orders late the bot re-posts every step, runs into the
   cap and overfills its limit. This cost the whole upload (+1,048 expected, −283 scored). `TODO.md`, "Track
   in-flight orders in the qminers ADAPTER" and "A generic in-flight tracker".
2. **`arena.validate` can't catch it before the first upload:** with no delay known, it passed "orders never breach
   a position limit" and reported "most orders working a product 5" against a cap of 3 without failing. The rules
   didn't mention latency; only the first upload showed it. Worth a habit: validate under `--delay 1` too when the
   rules are silent on timing (`ON_THE_DAY.md`'s probe 3 is the only place that says so, and there was no playground).
3. **`calibrate --scale` defaults to the data's unit**, which is wrong where a point is worth 2 credits a lot; I
   caught it only from the rules' "1 point = 2 credits". `TODO.md`, "`experiments.day.calibrate --scale` from the format".
4. **Round 1's HANDOVER.md is also the template** for later rounds; filling it in loses the template. `TODO.md`.
5. **The swap checklist names `drill.py`'s loader for book changes**, but drill's are price-keyed; this feed was
   level-indexed (a level's price changes in place, and level 2 moves up when level 1 empties). Worth a line in
   step 1.
6. **The ADAPTER's seven functions take an `api` object**; a function API (`step(ctx, view)` returning dicts with our
   own ids) needed an `_Api` wrapper and a rewritten entry with a shared action budget. The checklist has no example
   of a function API or of a per-step action cap shared across products.
7. **The "maybe one product a round" prior** (`ON_THE_DAY.md`, "Known so far") was wrong here: three products shared
   a 6-action budget.
8. **`--suggest`'s `stop_loss` values** (1,140 / 13,000 / 13,800) went in unchecked: their unit (ticks of each product)
   isn't stated in diagnose's output, and `arena.stress` wasn't run.
9. **Writing rehearsal answers under ON_THE_DAY's items** adds a line to each real-day item; a per-round answers file
   (HANDOVER's "Rule answers") would keep the day's doc clean.
10. The rules called themselves "Round 2" and pointed at `<ROUND>/public/`, which didn't exist (the data was in
    `data/`): the organisers' slip, handled by `resolve_data_dir` accepting the round folder or its `data/`.
