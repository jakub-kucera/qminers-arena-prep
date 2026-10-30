# Round 1 handover

A template, filled in during the round and finished by deadline − 0:10. Copy it to `data/arena/round<N+1>/` for
the next round. Committed and pushed so the other laptop has it (ON_THE_DAY.md, "Handover note"); the private
run's results and `leaderboard.json` go in this folder too.

## Rules: what they settle, what they leave open, where they contradict the repo
<!-- written 12:10, from data/arena/round1/rules.md (the "Kestrel Bourse Challenge"; its title says "Round 2",
     though this is round 1: a slip in their file, nothing else in it depends on it) -->

**Three products, not one:** BRAM (tick 0.5, limit 80), OPHIR (tick 0.01, limit 60), TALC (tick 0.05, limit 40)
(§1, `data/instruments.csv`). Prices in points as decimal strings; 1 point = 2 credits a lot; scores in credits.

**Settled by the rules** (each also under its ON_THE_DAY.md "First hour" item):
- **Entry:** module-level `setup(ctx)` (optional, 2 s) and `step(ctx, view) -> list` of action dicts, once per
  250 ms step, 6,000 steps a session (§1, §3). `ctx` lives all session; the module is imported fresh per session.
- **Orders rest:** `limit` with `tif` GTC (default) rests until filled or cancelled; IOC exists (§3).
- **Own orders are not in the book** the bot sees (§3, `view.book`).
- **Orders:** our own cid (1–32 chars, never reused in a session), cancel by cid; cancels in a list go before its new
  orders; fills come in the next call's `executions` with MAKER/TAKER; `working` lists our orders oldest first;
  a cancel of a no-longer-working order is ignored, of an unknown cid rejected (§3).
- **Caps:** at most **6 actions a step, cancels included** (the rest dropped); at most **3 working orders per
  instrument** (a new resting order beyond that is refused; IOC doesn't count) (§3).
- **Limits are charged, not enforced:** each lot beyond the limit costs 0.25 credits after every step (§4).
- **Fees:** taker fills pay 2 bps of value, maker fills earn a 0.5 bp rebate (§4).
- **Matching:** a marketable order takes the book at the book's prices, best first, up to the shown volume; resting
  orders fill later at their own price, "against the market's activity: the book and the other participants'
  trades"; no self-trades (§4).
- **Market:** a replay of recorded sessions; "your orders don't change what they do" (§1). So no other teams in it.
- **Scoring:** per session cash (fees included) + end position valued at the end − limit charges; score = sum over
  sessions; **final on two hidden sessions** recorded after the public ones (§5). Sessions independent, start flat.
- **Runtime:** Python 3.12, standard library only, 100 ms a step (a slow step's actions discarded, its `ctx` writes
  kept), no files/network/threads, stdout discarded; an exception discards that step's actions only (§6).
- **Uploads:** 3, files up to 100 kB (dashboard), one evaluation at a time, last accepted upload is final; each
  upload runs on the **three public sessions** (in-sample: it checks the engine, not the strategy) and returns the
  portal's metrics and a results ZIP with executions, orders, PnL every 10 s and a log (§7).

**Left open** (to fit on the first upload or to treat as a scenario):
- The **mark** of the end position (`markPrice`): mid, touch or last trade.
- **Queue position** of a resting order, and whether a print **at** its price fills it (`--match-trades all` vs
  `worse`), and whether a later book crossing it fills it.
- Whether volume we take **stays gone** from the replayed book (`--deplete`).
- Whether the 3-working cap counts an order that fills in full at once; when a step that breaks it is refused.
- `pnlSe`'s definition; whether the hidden sessions resemble the public ones (no statement).
- Any market-abuse clause: none in the rules.

**Where they contradict how the repo assumes the market works:**
1. The interface is two module-level functions over dicts (`setup(ctx)`, `step(ctx, view)` returning action dicts),
   not `Trader().run(state)`: a new wrapper and ADAPTER.
2. Orders **rest** (the repo's default is per tick): `RESTING = True`.
3. Limits are **charged, not rejected**: `--limit-penalty 0.125` (0.25 credits = 0.125 points a lot a step).
4. **Fees and a rebate:** `--fee-bps 2 --maker-fee-bps -0.5`.
5. **Action cap 6 a step including cancels, 3 working per instrument:** the wrapper applies both; the ADAPTER
   budgets its cancels and posts across the three products.
6. **Units:** score in credits = points × 2; the engine's unit is 0.01 points, so engine PnL × 0.02 = credits.
7. **The prints at `clock` n are trades after book n:** they go on tick n as they are (no shift).
8. The portal's score is **in-sample** (the public sessions); the final is on two hidden sessions.
## Uploaded
<!-- each upload: file, time, why; local PnL under all / worse / --resting; the metrics expected (arena.backtest --metrics) -->
- **Upload 1, 12:15:17, `python/bots/qminers/template.py` as first committed** (diagnose --suggest's PARAMS, the
  ADAPTER's 6-action / 3-working budget; a copy in `results/r1/upload1.py`), validated at 12:12 (`--time-limit-ms 100
  --max-size 100KB`, OK under `all` and `worse`). Expected before the upload (no latency known then): +4,147 credits
  under `all`, +492 under `worse`, −540 under `none`. **The portal: −4,849.91 credits**, COMPLETED, in ~1 s (E ≈ 1 s).
  Metrics: fills 4,130, tradedVolume 38,508, inventory 113, cash −32,874.16, markPrice 210.4, breachPenalty 4,002.25,
  pnlSe 569.80, |inventory| q50/68/95/99.7 82/98/145/186. Results ZIP: `round/uploads/upload_1/results_upload_1.zip`
  (unpacked in `results/r1/upload1_zip/`, gitignored).
- Two earlier attempts didn't count (portal status 0 of 3 after each): the portal crashed importing code this checkout
  lacks (`EngineConfig(max_actions=...)`, `experiments.day.calibrate`), and one named a file a blocked command never
  copied. The portal now runs from a checkout of main (`uv run --directory results/portal_wt ...`) with our plug-in
  copied in (DRYRUN_LOG.md).

## Portal against local
<!-- the portal's figures against our backtest of the same file on the same days; the ratio (T); which fill mode and mark fit -->
- **The gap was latency, not the fill model.** The orders file stamps each NEW and CANCEL one step after the call that
  sent it (q1, q2 sent at 10:00:00.000 appear at 00.250), and the log has ~1,800 "new orders refused: 3 orders already
  working" a session: the bot's view of step n doesn't show what it sent at n − 1, so it posted again, its cancels
  landed a step late, and the doubled quotes filled past the limits (the 4,002 penalty).
- With the plug-in's `LATENCY = 1`, upload 1's file backtests (`--no-strict`: strict mode turns the portal's own
  refusals into errors) as: `all` −3,356 credits, 5,608 fills; **`worse` −4,838.5, 4,130 fills, 38,508 lots, penalty
  4,002.25, end position 113 (all exact)**; `none` −6,172. Then **`--mark last`: score −242,495.73 units = −4,849.9146
  credits, cash −32,874.1646, the portal's to the cent** (mid −4,838.5, touch −4,952.3).
- `T` (the engine's error) on this upload: 0. `pnlSe` = our "s.e. days" (28,489.98 units × 0.02 = 569.80), the standard
  error of the three sessions' PnL. `markPrice` 210.4 = the mean of the products' last-trade marks, in credits a lot.
- Command: `uv run python -m arena.backtest results/r1/upload1.py all --format qminers --data data/arena/round1/data --no-strict --metrics`
  (the format's ENGINE supplies the rest).

## Private run against public
<!-- the private (hidden) run's PnL against the public one, per product -->

## Fill model and mark
<!-- the engine settings that matched the portal: --resting/--queue, --match-trades, --mark, --limit-penalty, --fee -->
- In `python/arena/formats/qminers.py`, used by every tool: `RESTING = True` (rules §3), `LATENCY = 1` (upload 1's
  orders file and refusals), and `ENGINE = {"trade_matching": "worse", "mark": "last", "limit_penalty": 0.125,
  "fee_bps": 2.0, "maker_fee_bps": -0.5}`, which `arena.cli.setup` applies wherever a flag is left at its default
  (backtest, validate, grid, stress, compare). The fees and penalty are the rules' (§4); `worse` and `last` were fitted.
- Queue model: moot under `worse` (it only matters for fills at the order's own price); `back` by default.
- Not covered: the `experiments.day.*` scripts build their own EngineConfig (Prosperity rules, no fees), so their PnL
  is not the portal's; only the latency, in the wrapper, reaches them.
- The grid's modes from now on: `--modes worse,all,none --gate first --holdout last` (ON_THE_DAY.md, "Which modes gate
  the grid's pick?": `worse` matched the portal exactly).

## Units map
<!-- exchange unit → engine unit (1 / PRICE_SCALE) → each product's tick; their timestamps → 0..999,900; where each limit comes from -->
- Exchange: points (decimal strings), 1 point = 2 credits a lot; scores in credits. Engine unit: 0.01 points (the finest
  of the instruments' decimals), so **engine PnL × 0.02 = credits**. Ticks: BRAM 0.5 = 50 units, OPHIR 0.01 = 1, TALC
  0.05 = 5. PARAMS prices and stop_loss are in each product's ticks.
- Time: step n of 6,000 (10:00:00.000 + n × 250 ms) → engine timestamp n × 1,000,000 // 6,000; the wrapper gives the bot
  `view["step"]` and `view["clock"]`, and the template maps the step onto 0..1,000,000 itself.
- Prints at clock n traded after book n: tick n's trades as they are (rules §2).
- Limits from `instruments.csv` (BRAM 80, OPHIR 60, TALC 40), charged not enforced: 0.25 credits = 0.125 points a lot
  a step (`limit_penalty`).

## Rule answers
<!-- which ON_THE_DAY.md items the rules or probes answered (written under each item, with the source), and the ones still open -->
- Settled by the rules and written under ON_THE_DAY.md's "First hour" items: the list at the top of this note.
- Settled by upload 1: one-step latency, `worse` matching, `last` mark, `pnlSe` = the sessions' s.e., markPrice = the
  products' mean mark.
- Still open: queue position (moot under `worse`), whether taken volume stays gone (`--deplete`), whether the hidden
  sessions resemble the public ones, a real series in disguise (not searched).
- **premise** (12:19; it runs its own Prosperity-rule engine here, so read the verdicts, not the PnL): BRAM, OPHIR and
  TALC all **Prosperity-like** (trades don't move the wall mid, the margin pays, the forecast doesn't fire); BRAM large-tick.
- **diagnose** (12:10): BRAM large-tick (1-tick spread 100%), quoting pays on both sides (λ± 0.181 > λ/2 0.016), wall
  mid noisy (smoothing 0.54); OPHIR 3-tick spread, wall mid jumps past half the spread on 8% of ticks ("if orders rest,
  take only"); TALC 14-tick spread, reverts to a level over ~1,000 ticks. **structure**: no repeats, no fixed sums, no
  shared noise; BRAM's wall mid reverts hard at lag 1 (ACF −0.28, VR(1000) 0.14); each day opens near one level
  (BRAM 150.0); TALC's large moves are 5 ticks (88%).

## Re-tests
<!-- which of last round's choices were tested again this round, which were kept untested ("Choose the approach again each round") -->

## Leaderboard
<!-- leaderboard.json saved here; experiments.day.leaderboard_curves --read verdict; our standing -->

## Next round
<!-- round N+1's first candidate, and its first three actions -->
- **First, still in this round: the ADAPTER must allow for the latency** (TODO.md, "The qminers ADAPTER under a
  one-step latency"). The uploaded template now fails `arena.validate` (5,291 refused posts, the portal's own) and
  backtests at the portal's −4,850 credits: count last step's posts as working and last step's cancels as gone before
  `execute`, and size quotes for fills that land before a cancel does. Then validate, then grid under `worse`.
- Then OPHIR's diagnose note (take only, `make_size` 0, against a bot that sends nothing) and BRAM's smoothing and
  make_edge, by `--modes worse,all,none --gate first --holdout last`.
