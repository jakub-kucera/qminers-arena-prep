# Round 1 handover (Halden Exchange rules, rehearsal of 2026-10-28)

Deadline 16:07 CET (the dashboard's, = the round's end). Round started 15:07. Source of every
answer below: `data/arena/round1/rules.md` (section §N), unless marked otherwise.

## Status (15:15)

- **Bot:** `python/bots/qminers/template.py` (the template, its PARAMS from `diagnose --suggest`
  with take_edge 2 on the 1-pip products for the taker fee). `arena.validate` passes on all three
  sessions (15:13): 56 KB, slowest call 15.6 ms of 50.
- **Local PnL** (`--queue prob --fee 1 --maker-fee 0 --mark touch`, resting by the format):
  16,378 / 18,567 / 13,454 pips = 48,399 pips, **12,100 credits** over the three public sessions.
  By product: AURIC 2,700, BRISA 16,710, CORONA 31,707, VANTA −2,718 pips. Per session and
  product the portal's feedback should match these × 0.25.
- **Command:** `uv run python -m arena.backtest python/bots/qminers/template.py all --format qminers
  --data data/arena/round1 --queue prob --fee 1 --maker-fee 0 --mark touch`.
- **Premise** (`experiments.premise`, run without the fee or touch mark, which it doesn't take):
  AURIC, BRISA, CORONA Prosperity-like; **VANTA mixed** (shuffled days pay 156k against 64k as
  recorded: the order costs the bot), so its pick is checked against a bot that sends nothing.
- **Structure:** every product opens each day at one level (AURIC 3,181, BRISA 1,200, CORONA
  4,404, VANTA 1,312 in ticks); CORONA has 5-tick jumps (26); no fixed sum holds on held-out days;
  no repeats, no shared noise streams. Output in `results/r1/structure.txt` (not committed).
- **Leads, not yet held out:** VANTA quotes off (`PARAMS.VANTA.make_size=0`) gains on every
  session in-sample (51,172 total against 48,399); VANTA sits at its limit 35–55% of the time
  while the wall mid drifts. Grid it, with the move gate premise names, under `--holdout last`.
- **Next:** step 5 (grids under `--modes all,worse,none --gate first --holdout last` with the
  rules' flags), stopped here because this rehearsal ends at the validated bot.

## Settled by the rules (also written under each ON_THE_DAY.md "First hour" item)

- **Four products, not one:** AURIC, BRISA (spot metals, tick 1 pip, limit 60), CORONA (an index
  certificate on a metals basket, tick 1, limit 30), VANTA (an energy future, **tick 4 pips**,
  limit 40) (§1). Prices are integer pips; 1 pip = 0.25 credits a lot. Our reports are in pips:
  multiply by 0.25 for the portal's credits.
- **Entry point:** a top-level `class Strategy` (no-argument constructor) with `on_market(update)
  -> list` once per 500 ms step, and optional `on_start(config)` before step 0 (§3). Not
  `Trader.run(state)`.
- **Actions** are tuples: `("post", sym, qty, price, ref)` (limit, rests), `("take", ...)` (IOC),
  `("pull", ref)`, `("pull_all",)` / `("pull_all", sym)`; `qty` signed; `ref` a positive int we
  choose, never reused in the session (§3).
- **Orders rest** (§3, §4): posts rest until filled or pulled. RESTING = True.
- **Queue:** a new order joins the back (the displayed volume is ahead). Trades at our price use up
  the volume ahead; other decreases of the level are cancels, **split ahead/behind in proportion
  to their sizes** (= our engine's `--queue prob`, power 1); an emptied level or a best price
  moving behind ours puts us at the front (§4).
- **Fills:** step 1, a new snapshot whose other side reaches our resting price fills us at our
  price up to the shown volume (maker); step 5, takes and crossing posts trade against snapshot n
  (taker); step 6, the tape printed before snapshot n+1 fills resting orders, through our price at
  once, at our price after the queue ahead (= `--match-trades all`, resting) (§4).
- **Timing:** the tape of data line n+1 is what fills orders placed at step n; the bot at step n
  sees line n's tape minus the volume that filled it (§2, §4). The loader puts line n+1's tape on
  tick n, so the engine's "the bot sees the previous tick's trades" matches.
- **The book we see excludes our own orders** (§3). Our own orders never trade with each other (§4).
- **Position limits:** symmetric; each order checked alone, counting resting orders and this
  call's accepted orders on that side: `position + B + q > limit` rejects that order only (§4).
- **Caps:** at most **10 actions a call** (pulls count; the rest dropped) and at most **4 resting
  posts a product** (counting this call's accepted posts) (§3, §4).
- **Fees:** a taker fill costs **1 pip a lot**; maker fills are free (§4). Backtest with
  `--fee 1 --maker-fee 0`.
- **Replay, not reactive:** "Your orders don't change what they do"; each snapshot is as recorded
  except volume that just traded with our resting orders (§1). So takes don't deplete later
  snapshots: no `--deplete`.
- **Scoring:** per session, cash + positions at the **touch** of the final snapshot (long at best
  bid, short at best ask; last mid if that side is empty), fees included; summed over products and
  sessions (§5). Backtest with `--mark touch`.
- **Final score on two hidden sessions** recorded after the public ones (§5); the public three are
  for feedback only. **The last accepted submission is final** (§7).
- **Sessions are independent:** 13:30:00–14:29:59.5 UTC, 7,200 steps; flat and zero cash at the
  start; the file imported and `Strategy()` constructed fresh per session (§1). State lives on
  `self` for the session (§6).
- **Runtime:** Python 3.12, standard library only; no files, network, subprocesses or threads;
  **50 ms per `on_market`** (a slow call's actions are discarded, its changes to `self` kept);
  `on_start` 2 s; an exception or a non-list return discards that step's actions; stdout
  discarded (§6).
- **Submissions:** 3 this round; a file rejected at upload doesn't count; files up to 100 kB (the
  dashboard). Feedback per accepted upload: score, **PnL per product and session**, fill counts
  (incl. taker lots), end positions, rejected actions, errors, slow calls (§7).
- **Data:** 3 public sessions (2026-05-11..13), gzip JSON lines, books 3 levels a side, the tape
  with an aggressor (`B`/`S`/`?`), no trader names (§2).

## Left open by the rules

1. **Is the market shared with other teams?** Not said. §1 describes a replay of the exchange's own
   participants that our orders don't change, which reads as each team alone on the replay.
2. **How rounds combine** and **tie-breaks**: not in the rules.
3. **What a pull of an unknown or already-filled ref does** (ignored or a rejected action).
4. **Whether rejected actions cost anything** beyond being listed (assumed: nothing).
5. **Whether `on_start` raising kills the session.**
6. **Whether the hidden sessions' days are like the public ones** (same hour of day, "recorded
   after"); two sessions only, so the final score is noisy.
7. **Whether a take's leftover can meet the tape** (assumed not: "cancelled" at step 5).
8. **The 50 ms is on their hardware**; ours may be faster. Validate with margin.

## Where the rules contradict how the repo assumes the market works

1. **Bot interface:** `Strategy.on_market(update)` returning action tuples, not
   `Trader.run(state)`; state on `self`, not `traderData`. New plug-in and ADAPTER.
2. **Orders rest with a pro-rata cancel split** (ON_THE_DAY.md assumed no resting): run resting,
   `--queue prob`. On Prosperity, resting quotes on jumping products lost: check diagnose's jump
   notes before quoting any product.
3. **Limit rule:** only the offending order is rejected (Prosperity cancels every order of the
   product; the engine's resting mode rejects all of the tick's new orders for it). The plug-in
   applies the rules' per-order check before the engine sees the orders.
4. **Caps the engine doesn't have:** 10 actions a call including pulls; 4 resting posts a product.
   The plug-in enforces both (drops actions past the 10th, rejects posts over the cap), and the
   ADAPTER keeps within them, pulls first.
5. **Taker fee 1 pip a lot, makers free** (Prosperity: no fees). Takes must clear fair by more than
   a pip to pay.
6. **Scored at the touch, once, at the session's end** (repo default: mid). `--mark touch`.
7. **The final submission is the last accepted one** (§7). "Known so far" (the site's code) says a
   team can mark an earlier one final: if both hold, re-marking is how to choose; the rules alone
   say the last upload decides.
8. **Feedback is per product and session** (the site's metrics looked like one product): enough to
   calibrate the backtest product by product.
9. **The rules' title says "Round 3 Technical Rules"** for round 1: ask the organisers whether
   these are this round's rules.
10. **Crossing fills and the tape:** the rules remove volume a snapshot's cross filled from the tape
    already shown (line n); our engine removes it from the tick's trades (line n+1 under the
    loader's mapping). A small difference, on resting orders the book runs through.
