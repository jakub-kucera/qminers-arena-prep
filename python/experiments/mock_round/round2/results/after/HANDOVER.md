# Round 1 handover

A template, filled in during the round and finished by deadline − 0:10. Copy it to `data/arena/round<N+1>/` for
the next round. Committed and pushed so the other laptop has it (ON_THE_DAY.md, "Handover note"); the private
run's results and `leaderboard.json` go in this folder too.

## Step 1: what the rules settle, what they leave open, what contradicts the repo (15:29, rehearsal)

Source: `data/arena/round1/rules.md` ("Halden Exchange Open", §1–7), `data/products.json`, `example_bot.py`.

**Not a single product:** four, AURIC, BRISA (spot metals, tick 1, limit 60), CORONA (index certificate on a metals
basket, tick 1, limit 30), VANTA (front-month energy future, **tick 4**, limit 40). Prices are integer pips; 1 pip =
0.25 credits a lot (§1). CORONA is probably a basket of AURIC and BRISA (weights not given: measure them).

**Settled by the rules (each written under its ON_THE_DAY.md "First hour" item):**
- **Entry point** (§3): `class Strategy`, no-arg constructor, optional `on_start(config)` (2 s), required
  `on_market(update) -> list` of action tuples, once per 500 ms step, 7,200 steps a session (n 0..7199).
- **Orders rest** (§3–4): `("post", sym, qty, price, ref)` rests what doesn't trade at once; `("take", ...)` is IOC;
  `("pull", ref)`, `("pull_all"[, sym])`. Refs are ours (positive ints, never reused after an accepted order).
- **Order of processing** (§4): (1) the new snapshot crosses resting orders → maker fill at our price; (2) call;
  (3) every pull first; (4) posts and takes in list order, each checked alone; (5) taker fills against snapshot n;
  (6) the trades printed before snapshot n+1 fill resting orders: through our price at once, at our price after
  the queue ahead.
- **Queue** (§4): back of the queue; trades at our price eat the volume ahead; other decreases split ahead/behind
  pro rata (our engine's `--queue prob --queue-power 1`); an emptied level or a best price behind ours → front.
- **Limits** (§4.4): per order, counting resting lots: a buy of q is rejected if pos + resting buys + this call's
  accepted buys + q > limit; only that order is rejected. Position can never pass the limit (no penalty).
- **Caps** (§3, §4.4): at most **10 actions a call, pulls included** (the rest dropped); at most **4 resting orders
  a product** (a post beyond is rejected).
- **Fees** (§4): taker fill 1 pip a lot; maker fills free (`--fee 1 --maker-fee 0`).
- **Our own orders in the book** (§3): not shown. **Self-trades** (§4): never. **Impact** (§1): a replay; our
  orders don't change the others; volume that traded with our resting orders is removed from the snapshot/tape we
  are shown. Not a shared market (a replay of the exchange's own participants).
- **Scoring** (§5): per session, cash (fees in) + position at the **touch** of the final snapshot (long at best bid,
  short at best ask; empty side → last mid), in credits (×0.25); sum over products and sessions. **Final score on
  two hidden sessions** recorded after the public ones; the 3 public sessions are feedback only.
- **Sessions** (§1): independent; flat start, fresh import and `Strategy()` per session. State on `self` (§6).
- **Runtime** (§6): Python 3.12, standard library only, no file/network/subprocess/threads; `on_market` ≤ **50 ms**
  (slower: its actions discarded, its changes to `self` kept); an exception or a non-list discards that step's
  actions and the session goes on; stdout discarded.
- **Submissions** (§7): 3 a round (a file rejected at upload doesn't count); feedback = score on the three public
  sessions, PnL per product and session, fill counts (taker lots), end positions, rejected actions, errors, slow
  calls. **The last accepted submission is final** (the rules say nothing of marking an earlier one final).
- **Data** (§2): `data/sessions/<date>.jsonl.gz`, one line a step: `n`, `ts`, `book` (≤3 levels a side,
  `[price, lots]`, best first), `tape` (`[sym, price, lots, aggressor B|S|?]`, the trades since the previous
  line). No trader names; an aggressor flag.

**Left open by the rules:**
- How the hidden sessions differ (only "not the same days"): regime, volatility, CORONA's basket relation.
- CORONA's basket weights and whether its relation to AURIC/BRISA holds intraday (measure on the data).
- The "last mid" used for an empty side at the close when both sides are empty; whether a pull of an unknown or
  filled ref counts as a rejected action; whether the 50 ms is measured on slower hardware than ours.
- Whether line 0's (empty) tape and the unpublished trades after step 7,199 matter (they can't fill us here).
- The rules call themselves "Round 3 Technical Rules" while this is round 1: a typo or a reused document.
- The dashboard's deadline (16:26) is the round's end, per the prompt; no evaluation time is known (E unknown).

**Contradictions with how the repo assumes the market works:**
1. The bot interface: `Strategy.on_market(update)` returning tuples, not `Trader.run(state)`; no `traderData`.
2. Orders rest (RESTING = True, not Prosperity's per-tick orders); IOC and pull/pull_all exist; ids are our refs.
3. Limits reject one order at a time (counting resting lots), not every order for the product.
4. **10 actions a call including pulls, 4 resting a product:** four products × (pull + post) × 2 sides = 16 > 10.
   The ADAPTER must budget actions (keep unchanged quotes, pull only what moved, cut to 10, most valuable first).
5. A taker fee of 1 pip a lot (Prosperity: none), so takes need edge > 1 pip + half the spread.
6. Marked at the touch, not the mid (`--mark touch`); flattening near the close is cheap only through makes.
7. Trades between snapshots n and n+1 fill orders resting after step n: the loader puts line n+1's tape on engine
   tick n, so the bot still sees line n's tape at step n (the engine's previous-tick view).
8. Engine difference left in: a cross at step n spends that volume from line n+1's tape (our engine) rather than
   line n's (theirs): slightly fewer trade fills than the exchange gives; and the engine's limit check is
   Prosperity's, so the wrapper applies the Halden per-order rule before the engine sees an order.
9. Not shared, no probes possible (no playground in this rehearsal); the fill model is taken from the rules.

## Diagnose (15:31, `arena.diagnose all --format qminers --data data/arena/round1 --profile --suggest`)
- AURIC: small-tick (spread 3 ticks), mid mean-reverts at one tick, mid and wall mid both noisy; making pays (0.50 of the spread).
- BRISA: small-tick (4 ticks), wall mid filters the mid's noise; making pays (0.48); takers 36% buys.
- CORONA: small-tick (12 ticks), walls small (median 12, a 15+ level on 13% of sides); making pays (0.49).
- VANTA: large-tick (one-tick spread 100%), Gao & Wang: making at the best pays on both sides; drifts on 3 of 3 days.
- No product's profile changes over the day (spread and trade rate flat by tenth). Structure scan and premise: not run
  before the rehearsal's stop (the scan's background run was blocked by a permission prompt; premise needs the bot).

## Uploaded
<!-- each upload: file, time, why; local PnL under all / worse / --resting; the metrics expected (arena.backtest --metrics) -->
**Candidate 1, validated 15:33, not uploaded (rehearsal):** `python/bots/qminers/template.py` (56,733 bytes), PARAMS
straight from diagnose `--suggest`. `arena.validate ... --queue prob --queue-power 1 --mark touch --fee 1 --maker-fee 0
--time-limit-ms 50 --max-size 100KB`: OK (slowest call 35.6 ms, p99 0.14 ms: the one slow call is the margin to watch).
Expected on the portal (`arena.backtest ... --metrics`, same settings), pips (credits = × 0.25):

| session | AURIC | BRISA | CORONA | VANTA | total pips | credits |
|---|---|---|---|---|---|---|
| 2026-05-11 | 928 | 5,702 | 10,098 | −2,736 | 13,992 | 3,498.00 |
| 2026-05-12 | 316 | 6,679 | 11,360 | −1,319 | 17,036 | 4,259.00 |
| 2026-05-13 | 1,544 | 4,215 | 10,058 | −2,443 | 13,374 | 3,343.50 |
| sum | 2,788 | 16,596 | 31,516 | −6,498 | 44,402 | 11,100.50 |

Fills 16,074 (13,895 orders filled); traded 52,518 lots; no penalty (breaches are rejected). The portal's taker
lots aren't in `--metrics` (`--out` fills, source `book`, give them). VANTA loses every session (at its limit
36% of the time, flat at each close): the first change to test is VANTA quoting nothing or a capped `make_size`,
against this bot on held-out sessions.

## Portal against local
<!-- the portal's figures against our backtest of the same file on the same days; the ratio (T); which fill mode and mark fit -->

## Private run against public
<!-- the private (hidden) run's PnL against the public one, per product -->

## Fill model and mark
From the rules (no upload yet): `--resting` (the format's default), `--queue prob --queue-power 1`,
`--match-trades all`, `--mark touch`, `--fee 1 --maker-fee 0`; no `--limit-penalty` (breaches are rejected).

## Units map
Exchange pip = engine unit (PRICE_SCALE 1, `Day.info[p] = {"tick": 1 or 4, "unit": 1}`); credits = pips × 0.25.
Ticks: AURIC, BRISA, CORONA 1 pip; VANTA 4 pips. Step n → engine timestamp n × 100 (0..719,900). Limits from
`products.json` (60, 60, 30, 40).

## Rule answers
<!-- which ON_THE_DAY.md items the rules or probes answered (written under each item, with the source), and the ones still open -->

## Re-tests
<!-- which of last round's choices were tested again this round, which were kept untested ("Choose the approach again each round") -->

## Leaderboard
<!-- leaderboard.json saved here; experiments.day.leaderboard_curves --read verdict; our standing -->

## Next round
<!-- round N+1's first candidate, and its first three actions -->
