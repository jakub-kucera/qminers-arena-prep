# Dry run log: round 1 rehearsal, the Varde Exchange (2026-11-03, 00:47–01:01)

A timed rehearsal with the round-1 kickoff prompt: three products (LUMEN 40, QUILL 60, SORREL 30), cents on a 5-cent
tick, `class Strategy(limits).on_tick(state)` returning dict actions, orders resting, a 10-action cap, 0.1 cents a lot
and 0.5 cents an order placed, 3 public sessions of 5,000 steps, a mock portal with 3 uploads. Deadline 01:47. Stopped
at the prompt's stop condition: a validated bot uploaded once, calibrate run on it and its refusal followed.

## Timeline (clock from `date`)

| Time | T+ | Step |
|---|---|---|
| 00:47:46 | 0:00 | Start. Read `rules.md` in full, `example_bot.py`, `RUNBOOK.md`, then `ON_THE_DAY.md`'s "Splitting the first hour", "The format swap, step by step" and "First hour". |
| 00:49:30 | 0:02 | **Step 1 done:** the settled / open / contradicting list at the top of `data/arena/round1/HANDOVER.md`. Not a single-product round. |
| 00:50:55 | 0:03 | **Step 2:** `python/arena/formats/qminers.py` written (loader and wrapper, from `drill.py`'s and the mock round 2 class wrapper); `arena.diagnose all --format qminers --data data/arena/round1 --profile --suggest` ran on it at once. |
| 00:51:20 | 0:04 | `experiments.day.structure`: LUMEN and QUILL open at one level every session and revert; no repeats, sums, jump grids. |
| 00:53 | 0:05 | **Step 3:** the template's PARAMS (from `--suggest`) and ADAPTER written; first backtest 73,038 cents (SORREL −56,736). |
| 00:53:30 | 0:06 | Grid `PARAMS.SORREL.make_size=0,None × level=day,None --modes all,worse`: SORREL take-only, 133,240 / 124,872 against 73,038 / 59,239 (held out 121,462; StepM's pick under both modes). |
| 00:54 | 0:06 | **Step 4:** `arena.validate … --time-limit-ms 50 --max-size 100KB`: every check PASS (60 kB, slowest tick 0.1 ms, delay-1 replay clean). |
| 00:54:43 | 0:07 | Upload attempt with `python3 portal.py`: the portal crashed on macOS's Python (`sys.stdlib_module_names`, 3.10+), before any evaluation. |
| 00:54:5x | 0:07 | **Upload 1** (`submit/r1/v1.py`) with `uv run python portal.py upload`: COMPLETED in seconds (E ≈ 0). Score **€367.61**. |
| 00:55:21 | 0:08 | ZIP extracted to `data/arena/round1/upload1/zip`; `fill_curve.py`'s names mapped (swap step 11). `calibrate --help` crashed (a `%` in a help string). |
| 00:56 | 0:09 | **calibrate** (`--portal metrics.json --results <zip>`): **refused**. |
| 00:57 | 0:10 | Score rebuilt from the ZIP by hand; calibrate re-run with the order fee added back (`--portal-set score=510.85`) and with `--top 144`: still refused. |
| 00:58:16 | 0:11 | `calibrate --help` fixed; the swap's tests pass (38, 2 skipped). |
| 00:59:09 | 0:11 | Commit 810515a (plug-in, bot, the uploaded copy, fill_curve's map, HANDOVER). |
| 00:59:40 | 0:12 | `experiments.day.premise` (Python engine, no twin): LUMEN, QUILL, SORREL all **Prosperity-like**. |
| 01:00:19 | 0:13 | ON_THE_DAY answers, TODO "From the 2026-11-03 rehearsal", the IDEAS.md row, this log. |

## What calibrate printed, and what I did with it

The portal: score 367.61, fills 5,056, tradedVolume 8,466, inventory −6, cash 2,310.30, markPrice 233.44,
breachPenalty 0, pnlSe 22.98, |inventory| q50/68/95/99.7 8/13/27/36; from the ZIP, LUMEN 3,978 fills / 6,710 lots,
QUILL 1,078 / 1,756.

calibrate (144 settings, delay 0 and 1): **"NO SETTING REPRODUCES THE PORTAL within 5%: don't paste an ENGINE."**
Best `none, per tick, mid, delay 1` at 98.1% off on score (it scores €7 by barely trading, so it is "nearest" only
because every real setting is further off on `score`, `cash` and `inventory`). Cause named: the wrapper. With the
order fee added back to the score: the same, 98.6%.

What the causes really were (found by hand, from the ZIP):
1. **An order fee the engine can't charge.** Rebuilt from the ZIP's fills (cash, 0.1 cents a lot, 0.5 cents per
   order with status `new`, positions at each session's last mid), the three sessions sum to €369.67 against the
   portal's 367.61 (0.6%): so the score is the **sum over the sessions**, and the order fee took **€143.24 of a
   €510.85 gross** (28,647 orders).
2. **A different matching rule.** Under every setting we fill far more: 8,466 lots on the portal against 18,772
   (`all`, resting, any queue), 16,554 (`worse`), 11,345–13,419 (delay 1); and yet the portal's gross is higher than
   any of ours (€410–460). Its first fills suggest a queue behind each step's shown volume at our price (a 1-lot sell
   print at our bid went to the 5 lots the next snapshot showed there, though our bid had been alone at that price).
3. Readings: `markPrice` is the mean of all three products' last marks (233.44; SORREL included though never traded),
   calibrate's the mean over the traded ones (300.04); `inventory` (−6 against our 7–16) dominates the worst figure.

**Acted on, as the refusal says:** no ENGINE pasted; the plug-in keeps the rules' settings; the grid's modes widened to
`all,worse,none` plus a `delay=1` scenario (HANDOVER, "Fill model and mark"); every local PnL to be read net of
`orders × €0.005`. The local backtest overstates the portal about 2.6× gross (€1,332 against €511 over the three
sessions), so before the next upload a local figure is a ranking, not a forecast.

## The engine settings, and the evidence for each

| Setting | Value | Evidence |
|---|---|---|
| `RESTING` | True | rules §Matching: "What is left rests until it is filled or cancelled". |
| `trade_matching` | all | rules §Matching: "a sell print fills bids at or above its price". The upload's volume says fewer fills than `all` gives; no mode reproduced it. |
| `queue` | front | rules name no queue behind others' shown volume; the upload contradicts it (fills behind the shown volume) but `back` and `prob` were no closer (identical figures to within 30 lots). Kept for want of a better one. |
| `fee` | 0.001 € a lot | rules §Limits: 0.1 cent a lot traded, maker and taker. |
| order fee | not modelled | rules §Limits: 0.5 cent an order placed; confirmed by the rebuilt score. No EngineConfig field (TODO). |
| `max_actions` | 10 | rules §Your bot (cancels count; the rest ignored). The wrapper also cuts at 10 and logs a rejection. |
| `mark` | mid | the settlement price is unstated; the rebuild at the last mid matched to 0.6%. |
| `delay` | 0 | rules: a new order trades with the step's shown book and rests into its prints; fills are listed next step. calibrate couldn't tell. |
| units | `Day.info` unit 0.01, tick 0.05, `CREDITS` 1 | prices in cents, scored in euros; `--metrics` and calibrate print euros, and the rebuilt score agrees. |
| limits | `LIMITS` in the plug-in | rules §Products (the data has none); the bot gets them from `Strategy(limits)`. |

## The bot uploaded

`submit/r1/v1.py` (= `python/bots/qminers/template.py` at 810515a): the template with its ADAPTER rewritten for the
dict API (cancels, then takes, then posts, products rotated against the 10-action cap; takes as plain limits at the
shown price; the exchange's limit unless PARAMS asks for less), PARAMS from `--suggest` (LUMEN and QUILL `wall_mid`,
`make_edge` 1), SORREL take-only. Local 133,240 cents over the three sessions (`all`), 124,872 (`worse`); portal
€367.61 for the same three sessions. Step 5 (grids beyond SORREL, stress, stops, the level on LUMEN/QUILL) wasn't
started: the stop condition came first.

## What slowed me down

- **Permission prompts on ordinary shell use:** compound commands, `>` redirects (even into `results/`), `rm`, `cp`
  from the portal's upload folder, `time`, `awk`. Splicing the ADAPTER took two `Edit` calls and a stray
  `results/adapter.tmp` I couldn't delete; the ZIP had to be unzipped in place of a copy.
- **The portal on macOS's `python3`** (3.9) crashed; `uv run python` worked. One minute.
- **calibrate's refusal named a generic cause** ("the wrapper"); finding the order fee and the matching gap took a
  hand rebuild of the score from the ZIP (about three minutes). Its `--help` crashed.
- Reading `diagnose.suggest` to learn whether `--suggest`'s `stop_loss` is in ticks or cents (ticks).

## What in the repo's docs or tools was missing, wrong or misleading

1. **No per-order fee in the engine** (`EngineConfig` has `fee`, `fee_bps`, `maker_fee*` only), though the
   checklist's step 3 lists the fee fields as if they cover an exchange's charges; here it was 28% of the gross and
   steers every grid toward re-posting. `TODO.md`, "From the 2026-11-03 rehearsal".
2. **No queue model for "behind each snapshot's shown volume"**; `back`, `prob` and `front` gave the same fills
   within 30 lots, all over twice the portal's.
3. **calibrate:** `--help` crashed (fixed here); with an unmodelled cost its ranking by the worst figure picks a
   setting that barely trades; it doesn't print the setting nearest on fills and volume alone; its `markPrice` reading
   averages only the traded products; the refusal's causes list misses "a cost the engine doesn't charge".
4. **fill_curve's ZIP map has no time scale:** the ZIP's `step` isn't the engine's timestamp (× 200 here).
5. **The template's `params_for` comment** (`min(PARAMS.get("limit", DEFAULTS["limit"]), exchange)`) would cap a
   60-lot limit at DEFAULTS' 50; I used the exchange's limit as the fallback.
6. **The checklist's step 2** says `diagnose`'s prices are "in the loader's unit"; `--suggest`'s PARAMS are in the
   bot's ticks where `Day.info` gives a tick (`diagnose.suggest`'s docstring says so; the checklist doesn't).
7. **No wrapper to copy for a dict-action API with exchange-assigned ids:** the mock round 2 wrapper (tuples, own refs)
   was the nearest; mapping the engine's order ids straight through was simplest.
8. **`arena.validate`'s "most orders working a product 22"** reads like a bug; it is EXECUTION's top-ups (a partly
   filled quote kept, the rest posted as a new order), which cost an order fee each here. A note on why would save
   the dig.
9. The rules said the score uses "two other sessions"; the mock portal ran the three public ones. Nothing in the repo
   was wrong there, but the HANDOVER expectation I wrote (€444 a session) was the wrong unit of comparison: the score
   is the sum, and the fill gap made it a third of that per session.
10. RUNBOOK's T+0:15 line runs `premise --engine rust`, which fails without a twin; the prompt said Python until then,
    RUNBOOK doesn't.
