# Round 1 handover (rehearsal, 2026-11-03, 00:47–01:47; the Varde Exchange)

## Step 1: what the rules settle, leave open, and contradict (source: `data/arena/round1/rules.md`, §-names below)

**Settled by the rules**
- **Products (§Products):** three, LUMEN (limit 40), QUILL (60), SORREL (30). Not a single-product round.
- **Prices (§Products):** integer cents on a 5-cent tick for every product; results in euros (100 cents); one lot moves by
  its price in cents (no multiplier). Engine unit: the cent; each product's tick 5 units; `CREDITS` 0.01 (euros a cent).
- **Data (§Data):** 3 public sessions × 5,000 steps, JSONL `{t, book{SYM:{bids,asks}}, prints[{sym,px,qty,aggressor}]}`,
  up to 3 levels a side, the book *before* the step's trading; a step's prints are the trades during it. Scored on
  **two other sessions** of the same market (never seen).
- **Entry point (§Your bot):** `class Strategy: __init__(self, limits)`, `on_tick(self, state) -> list[action]`, once a step.
  `state`: `t`, `book`, `prints` (the **previous** step's), `position`, `orders` (resting: `id, sym, px, qty` signed, left),
  `fills` (since the last call: `id, sym, px, qty` signed), `cash` (euros, fees in). State lives on the instance for the
  whole session.
- **Actions (§Your bot):** ≤ **10 a step** (the rest ignored): `{"type":"limit","sym","px","qty"}` (signed qty; id given by the
  exchange, seen in `orders` next step), `{"type":"cancel","id"}`. Cancels before new orders. No IOC, no amend, no market order.
- **Matching (§Matching):** a new order trades with the step's shown book at the book's prices; the rest **rests** until
  filled or cancelled (orders rest: `RESTING = True`). Resting orders fill from the step's **prints** at the order's price,
  best price first then oldest first; a sell print fills bids **at or above** its price (= `--match-trades all`). Fills
  reported next step.
- **Limits (§Limits):** if a step's new orders for a product could take the position past the limit counting what rests,
  **all** that step's new orders for the product are rejected (= the engine's resting-mode rule 2).
- **Fees (§Limits):** 0.1 cent a lot traded (maker and taker alike) and **0.5 cent an order placed**.
- **Runtime (§Limits, §Your bot):** standard library only; > **50 ms** or an exception drops the step's actions; files ≤ 100 kB.
- **Score (§Score):** profit in euros over the scored sessions: cash with fees plus open positions at "the session's
  settlement price". A results file with fills, orders and the log; 3 public submissions.

**Left open**
- The settlement price (last mid? last print? a touch?): assume the last step's mid (`mark` mid).
- Whether a resting order placed at step t can fill from step t's own prints (assume yes, delay 0; calibrate tries 1).
- Queue against other participants' volume at our price: the rules mention none (prints fill *our* orders by price then
  age), so the nearest engine setting is `queue front`; does a print's quantity cap our fill (assume yes)?
- Whether the market is shared with other teams (the prints are "between other participants"; assume a replay, not shared),
  and whether our takes deplete the book (assume a replay: no).
- Whether the book shown includes our own resting orders (assume not, as in the data).
- The Python version; whether prints/logging are allowed; how the 3 rounds combine; a fresh `Strategy` per session (assumed).
- What the order ids look like (assume ints).

**Contradicts how the repo assumes the market works**
- Orders **rest** (the repo's default is per tick): every tool runs as `--resting` via the plug-in.
- A **per-order fee** (0.5 cent an order placed) the engine has no field for: not modelled locally. A bot that reposts
  6 quotes a step pays up to 5,000 × 6 × 0.5 = 15,000 cents (€150) a session: keep quotes that haven't moved (EXECUTION
  does) and count `orders placed × 0.005 €` off every local result by hand.
- **Crossing snapshots:** the engine fills a resting order when a later book crosses it; the rules fill resting orders only
  from prints. Matters only for stale quotes (the template re-prices every step).
- **No queue behind the shown volume** in the rules: the engine's resting mode puts the shown volume ahead (`queue back`).
  Use `queue front` (nearest), widened with `back`/`prob` scenarios until calibrated.
- **Prints the bot sees** are the previous step's, its orders meet this step's: the engine's convention, so a line's prints
  go on its own tick (no shift).
- **Cash in the state** (euros, fees in): the wrapper computes it from fills and orders.
- The 10-action cap counts cancels: `max_actions` 10.

## Uploaded
- **Upload 1, 00:54:5x** (`submit/r1/v1.py`, = `python/bots/qminers/template.py` at this commit): diagnose `--suggest`'s
  PARAMS, SORREL take-only (`make_size` 0, its `level: "day"` dropped; it then never trades). Local, cents, 3 public
  sessions, resting (the plug-in's ENGINE: `all`, `queue front`, mid, 0.1¢ a lot): **133,240** (s1 38,661 · s2 50,818 ·
  s3 43,761), `worse` 124,872; ~10k orders a session. Expected on the portal: €444 a session before the order fee,
  ~€394 after it. Evaluation took seconds (E ≈ 0).
- **The portal:** `score` **367.61**, fills 5,056, tradedVolume 8,466, inventory −6, cash 2,310.30, markPrice 233.44,
  breachPenalty 0, pnlSe 22.98, |inventory| q50/68/95/99.7 8/13/27/36. ZIP: `fills_session_{1,2,3}.csv`,
  `orders_session_{1,2,3}.csv`, `log.txt` (empty: no rejections). The run was on the **three public sessions** (its
  step-0 orders are ours on session 1's first book), not "two other sessions".

## Portal against local
- **The score is the sum over the sessions, net of the order fee:** rebuilt from the ZIP's fills (cash, 0.1¢ a lot,
  0.5¢ an order with status `new`, positions at the last mid): 108.47 + 135.14 + 126.07 = **369.67** against 367.61
  (0.6%; the gap is the settlement price, not the last mid exactly). Gross €510.85, lot fees €8.47, **order fees
  €143.24** (28,647 orders): the order fee takes 28% of the gross.
- **Fills: the portal fills less than half our volume under every setting.** Per session the portal's LUMEN makes
  ~1,430 lots passive and ~800 taking, QUILL ~465 and ~120; locally (`all`, resting, front) LUMEN 3,376 passive and
  1,547 taking, QUILL 1,022 and 112 (s1). Total 8,466 lots against 18,772 (`all` resting), 16,554 (`worse` resting),
  11,345–13,419 (delay 1). Yet the portal's gross (€511) is above every local setting's (€410–460).
  Its first fills point at a queue behind the shown volume, re-counted each step: at step 1 a 2-lot buy print at 10155
  gave our ask there 1 lot (1 lot shown ahead at step 0), and a 1-lot sell print at 10145 went to the 5 lots the
  step-1 book showed at our bid, though our bid had been alone there at step 0.
- **calibrate refused** (no setting within 5%: best `none, per tick, mid, delay 1`, 98.1% off on score; the same with
  the order fee added back to the score, `--portal-set score=510.85`, 98.6%). Cause named: the wrapper. Causes found:
  the order fee (no EngineConfig field), and a matching rule none of the 144 settings has. Acted on: **ENGINE kept as
  the rules state it**, the grid's modes widened to `all,worse,none` with a `delay=1` scenario, and every local result
  read net of `orders × €0.005` by hand.
- `markPrice` 233.44 is the mean of the **three** products' last marks (SORREL's too, though we never traded it);
  calibrate averages only the products we traded (300.04).

## Private run against public
<!-- the private (hidden) run's PnL against the public one, per product -->

## Fill model and mark
- None matched (above). The plug-in's `ENGINE` stays the rules': resting, `trade_matching` all, `queue` front, `fee`
  0.001 €/lot, `max_actions` 10, `mark` mid. Grids: `--modes all,worse,none --scenario late:delay=1`; read every PnL
  net of the order fee. Next upload: a bot whose fills tell queue-behind-shown from delay (one passive quote joining the
  best on one product).

## Units map
- Exchange: integer cents, 5-cent tick, euros scored. Engine unit: the cent (`Day.info` unit 0.01 €, tick 0.05 €);
  `CREDITS` 1, so `credits_per_unit` 0.01 (reports in cents, calibrate and `--metrics` in euros). Each product's tick:
  5 cents, so PARAMS prices are in 5-cent ticks (`--suggest`'s are already).
- Clock: step n of 5,000 → engine timestamp n × 200 (0..999,800); the bot is handed `t` = n and maps it back with
  `STEPS` 5,000. A line's prints go on its own tick (the bot sees the previous step's, as the engine hands them).
- Limits: the rules' §Products, in the plug-in's `LIMITS` (the data has none); the bot gets them in `Strategy(limits)`.
- The ZIP's `step` is the session step (not × 200): fill_curve has no scale for it, so its timestamp joins are off;
  calibrate reads only product and quantity, so it is unaffected.

## Rule answers
- Answered by the rules: the list at the top (and under `ON_THE_DAY.md`'s "First hour" items, marked "Rehearsal
  2026-11-03 (Varde)"). Answered by the upload: the score is the sum over sessions, the order fee is charged, rejections
  go to `log.txt`, the public run uses the public sessions, settlement is near the last mid.
- Still open: the matching rule (above), the settlement price exactly, whether the private run's sessions are the
  "two other sessions".

## Re-tests
- `experiments.day.premise` (00:59, the format's rules, Python engine): LUMEN, QUILL and SORREL all **Prosperity-like**
  (trades don't move the wall mid, the margin pays, not large-tick, the forecast doesn't fire); shuffled PnL 49,472 /
  90,315 / 0 against 43,830 / 89,410 / 0 as recorded. The IDEAS.md priors stand; grid from `--suggest`'s entries.
- `experiments.day.structure`: LUMEN and QUILL open at one level every session (2,030 and 9,995 ticks) and revert
  (VR at 1,000 ticks 0.16 and 0.26); SORREL opens near 2,000 and drifts on s1; no repeats, sums or jump grids.
- Not yet: `level` on LUMEN/QUILL at their opening level, `make_edge` 0.5–2, smoothing, stress and stops.

## Leaderboard
<!-- leaderboard.json saved here; experiments.day.leaderboard_curves --read verdict; our standing -->

## Next round
<!-- round N+1's first candidate, and its first three actions -->
