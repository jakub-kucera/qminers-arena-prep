# Round 1 handover (rehearsal 3, 2026-10-30; "Kestrel Bourse", deadline 13:25)

## Rules: what they settle, what they leave open, what contradicts the repo
Source for every line: `data/arena/round1/rules.md` (section in brackets); `example_bot.py` agrees where it overlaps.

**Settled by the rules**
- **Products: three, not one** (§1): BRAM (tick 0.5, limit 80), OPHIR (tick 0.01, limit 60), TALC (tick 0.05,
  limit 40); `data/instruments.csv` repeats them. The repo's "maybe one product a round" prior is wrong here.
- **Money** (§1): 1 point = 2 credits a lot; scores, cash, fees, penalties in credits; `markPrice` is credits a lot (points × 2) (§7).
- **Sessions** (§1): 6,000 steps of 250 ms (10:00:00.000–10:24:59.750); each session independent, flat start,
  zero cash, **module imported fresh each session**; three public sessions 2026-09-14/15/16; final score on
  **two hidden later sessions** (§5).
- **Market** (§1, §4): a replay of recorded sessions; "your orders don't change what they do". Not shared with
  other teams as far as the rules say.
- **Bot interface** (§3): module-level `setup(ctx)` (optional, 2 s) and `step(ctx, view) -> list` (required);
  `ctx` lives the whole session (state on it, or module globals: the module lives the session too); `view` has
  step, clock, book (3 levels a side, best first, own orders not shown), prints since the last call (with an
  aggressor BUY/SELL/empty), position, executions since the last call (cid, side, price, size, MAKER/TAKER),
  working orders (cid, side, price, remaining, oldest first).
- **Orders** (§3): `limit` with our own `cid` (1–32 chars, never reused in a session), `tif` GTC (rests until
  filled or cancelled) or IOC; `cancel` by cid. **Orders rest** → `RESTING = True`. Cancels in a list go before
  its new orders; new orders in list order. Price a decimal string or number on the tick grid; size positive int.
- **Caps** (§3): **6 actions a step, cancels included** (the 7th on are dropped); **3 resting orders per
  instrument** (IOC not counted; the 4th refused). Rejected actions are dropped and logged.
- **Matching** (§4): a marketable order takes the shown book at its prices, best first, up to the shown volume;
  resting orders fill later at their own price against "the market's activity: the book and the other
  participants' trades". **No self-trades.**
- **Fees** (§4): taker 2 bps of value, maker **rebate** 0.5 bps (value = price × lots × 2 credits) →
  `fee_bps 2`, `maker_fee_bps -0.5`.
- **Limits** (§4): **not enforced by rejection**; each lot beyond the limit costs 0.25 credits after every
  step → `limit_penalty 0.125` (points a lot a step, the engine's price units).
- **Scoring** (§5): per session cash (fees included) + end position valued at the end − limit charges; score =
  sum over sessions; ranked on the hidden sessions.
- **Runtime** (§6): Python 3.12, **standard library only** (else rejected at upload, not counted); no files,
  network, subprocess, threads; stdout discarded; **100 ms per step** (a slow call's actions discarded, its ctx
  writes kept); `step` raising or returning a non-list → that step's actions discarded, session goes on.
- **Uploads** (§7): 3 this round; a rejected upload doesn't count; one evaluation at a time; feedback on the
  three **public** sessions (in-sample); the last accepted upload is final.

**Left open (to fit from the first upload or leave as scenarios)**
- The **mark**: which price "valued at the end of the session" uses (mid, touch, last trade, a hidden fair).
- **Queue position** of a resting order (back, prob, front), and whether prints at our price fill us
  (`trade_matching` all / worse), and whether taken book volume stays gone (`deplete`).
- **Latency**: whether an order sent at step n meets step n's book and prints (assumed) or later ones.
- Whether a resting order can fill against the book itself when the book later crosses it (the engine does).
- How `pnlSe` and the |position| quantiles are computed (per session or the run).
- Whether two uploads of one file score the same (a replay suggests yes: deterministic).
- Market-abuse clause: none in the rules.

**Contradicts the repo's assumptions**
- Entry point is a module-level function `step(ctx, view)` returning dicts with our own cids, not
  `Trader().run(state)` nor the drill's callback `Bot.on_tick(api)`; the ADAPTER builds `step`/`setup` itself.
- **The book is level-indexed** (`level` 1–3 per side, a row only when that level changed): not price-keyed
  like the drill's events; a level's price can change in place.
- **Limit breaches are charged, not rejected** (the engine's Prosperity rule 2 rejects): `limit_penalty` on.
- **A 6-action budget shared by all three products** (the template's EXECUTION plans per product with no
  shared budget): the ADAPTER has to ration actions across products each step, or the 7th on are dropped.
- Fees and a maker rebate (the repo assumes none).
- Fresh module per *session* (not per step): globals survive within a session, unlike Prosperity's Lambda.
- Data's first step lists only TALC (BRAM and OPHIR appear at step 1), against §2's "the first step lists every level".
- The rules' title says "Round 2" while the folder is round 1; `<ROUND>/public/` doesn't exist (the data is in `data/`).

## Uploaded
- **Upload 1, 13:01:48, 1 of 3** (`python/bots/qminers/template.py` at commit "format swap", the file kept as
  `data/arena/round1/work/upload1.py`): the template with diagnose `--suggest`'s PARAMS (BRAM wall_mid smoothed 0.54,
  `make_edge` 0.5; TALC wall_mid `make_edge` 1; OPHIR the same but `make_size` 0, take only, by the day-one table's
  jump row). `arena.validate` OK under `all` and `worse` (100 ms, 100 kB; 55,853 bytes, slowest step 0.2 ms).
  Expected before it ran (resting, the rules' fees, penalty and caps, no delay): +1,048 credits under `worse`
  (52,425 units), +4,714 under `all` (235,698 units); no breach. **The portal: −283.01 credits**, fills 1,937,
  volume 13,195, end position 113, breach penalty 198.00, pnlSe 927.57. Evaluation time E ≈ 1 s.

## Portal against local
Far off before calibrating (−283 against +1,048 / +4,714): the exchange applies orders a step late. After it,
`arena.backtest data/arena/round1/work/upload1.py all --format qminers --data data/arena/round1` gives −14,151 units
= −283.02 credits, every figure within rounding: T ≈ 0 on this deterministic replay.
- Why it lost: the bot sees no in-flight order (`working` lists an order only after it arrives), so it posts again
  every step and is refused at the 3-order cap (1,858 refusals on 2026-09-14 alone), and in-flight orders overfill
  BRAM's limit (−29,844 units = −597 credits on BRAM; 198 credits of breach charges). Fix first, in the ADAPTER:
  `TODO.md`, "Track in-flight orders in the qminers ADAPTER".

## Private run against public
<!-- the private (hidden) run's PnL against the public one, per product -->

## Fill model and mark
`experiments.day.calibrate --data data/arena/round1 --days all --format qminers --bot data/arena/round1/work/upload1.py
--portal data/arena/round1/work/upload_1/metrics.json --results <the upload's ZIP> --scale 0.02 --vary delay=0,1`
(144 settings): best **`worse`, resting, `delay 1`, mark `last`**, no depletion, with the rules' `fee_bps 2`,
`maker_fee_bps -0.5`, `limit_penalty 0.125`, `max_actions 6`, `max_resting 3`: 0.0% off on all 12 figures. Next:
mark `mid` 0.9% off, `touch` 3.9%, `deplete` 14.9%. Indistinguishable: queue `back`, `prob`, `front` (under `worse`
the queue doesn't matter). All of it is now `qminers.ENGINE`.

## Units map
- Prices: points, decimals; engine unit 0.01 point (`PRICE_SCALE` 100); ticks BRAM 0.5 = 50 units, OPHIR 0.01 = 1,
  TALC 0.05 = 5. STRATEGY's prices and `stop_loss` in each product's ticks; the ADAPTER sends decimal strings.
- Money: the engine's PnL is in units × lots; **credits = units × 0.02** (2 credits a point a lot): calibrate needs
  `--scale 0.02`. `limit_penalty` 0.125 = 0.25 credits in points. The portal's `markPrice` is the products' mean mark × 2.
- Time: step n (10:00:00.000 + n × 250 ms) → timestamp n × 1,000,000 // 6,000; prints at a step's clock are that tick's
  trades (after its book), which the bot sees a step later. Each session is its own day (the clock resets).
- Limits: `instruments.csv` (80 / 60 / 40), read by the loader; the bot uses min(PARAMS', ctx.instruments').

## Rule answers
Written under each `ON_THE_DAY.md` "First hour" item ("Rehearsal 3 (2026-10-30 ...)"). Still open: queue position
(can't matter under `worse`), the hidden sessions' likeness to the public ones, how `pnlSe` is computed (calibrate
matched it, so it's one of the engine's), whether OPHIR's prints inside the spread (17.2% at no shown price, the
structure scan) are hidden liquidity our orders could meet.

## Data (diagnose, structure)
BRAM large-tick (one-tick spread always, walls ~322, both sides pay), its wall mid strongly mean-reverting (VR 0.35 /
0.22 / 0.14 at 10 / 100 / 1,000) and opening at one level (~150.0) each day; OPHIR 3-tick spread, wall mid jumps on
8% of ticks, 17% of prints at no shown price; TALC 14-tick spread, reverts to a level over ~1,000 ticks (VR 0.30 at
1,000), opens near one level (~124.0). No fixed sums, no repeats. `data/arena/round1/work/structure.txt`.

## Re-tests
Round 1: everything from priors. Not yet run: `experiments.day.premise`, the grids, `arena.stress`.

## Leaderboard
<!-- leaderboard.json saved here; experiments.day.leaderboard_curves --read verdict; our standing -->

## Next round
<!-- round N+1's first candidate, and its first three actions -->
