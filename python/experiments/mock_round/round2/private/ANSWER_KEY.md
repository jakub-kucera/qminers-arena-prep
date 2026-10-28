# Halden round answer key (PRIVATE: never show to the team)

## How the data was made

```sh
private/generate.sh            # arena.sim days, Prosperity layout -> private/raw/{pub1,pub2,pub3,hid1,hid2}
uv run python private/disguise.py   # -> public/data (3 sessions), private/hidden_data (2 sessions)
```

**Generation.** Each session is one `arena.sim generate --days 1 --ticks 7200` call on the
presets `SQUID_INK,KELP_FLOW,RAINFOREST_RESIN,LARGE_TICK`, with the shared `--spec`s in
`generate.sh`. VANTA's trend differs by session:

| session | date       | seed  | VANTA trend starts at | trend (raw ticks a step) | VANTA move, pips |
|---------|------------|-------|-----------------------|--------------------------|------------------|
| pub1    | 2026-05-11 | 61027 | 25% (step 1800)       | +0.010                   | +202             |
| pub2    | 2026-05-12 | 61391 | 50% (step 3600)       | -0.012                   | -174             |
| pub3    | 2026-05-13 | 61744 | 5% (step 360)         | +0.008                   | +238             |
| hid1    | 2026-05-18 | 90518 | 35% (step 2520)       | -0.010                   | -208             |
| hid2    | 2026-05-19 | 90873 | 60% (step 4320)       | +0.014                   | +180             |

## The products

| symbol | preset           | what it is | pips from raw |
|--------|------------------|------------|---------------|
| AURIC  | SQUID_INK        | random walk, sd 0.7 a step; walls 4 apart (half_spread 2), sizes 15-25; some momentum flow. Limit 60. | raw + 1180 |
| BRISA  | KELP_FLOW        | random walk, sd 0.45; walls 4-6 apart (half_spread 2.5); one-sided noise flow (35% buys, bigger; C(1) 0.13), so a two-sided maker drifts long. Limit 60. | raw - 830 |
| CORONA | RAINFOREST_RESIN | **basket:** AURIC + BRISA + 24 + an OU premium (reversion 0.004 a step, half-life about 170 steps; sd 1.0, so a stationary sd of about 11 pips), quoted by a **wide market maker**: walls 12 apart (half_spread 6), sizes 8-15, thin limit orders inside (rate 0.25, 1.5-4.5 off). **Its book trails the components' value by 4 steps (2 s).** Limit 30. | raw_X - 10000 + 24 + round(fA + fB + 350), where fA and fB are the components' raw fundamentals 4 steps earlier |
| VANTA  | LARGE_TICK       | large tick: a one-tick spread (4 pips) and deep queues (walls of about 320). The fundamental barely moves (sd 0.06 raw a step) **until a trend starts part-way through the session** (table above), with momentum takers (rate 0.05, 5-15 lots). Limit 40. | (raw + 312) x 4 |

**Not published:**
- the fundamentals (`private/raw/*/round1/fundamental_*.csv`);
- the CORONA composition: the rules only say "index certificate on a metals basket";
- the last step's trades.

**Checks on the data** (`uv run python private/check_relation.py public/data/sessions/*.gz private/hidden_data/sessions/*.gz`):
- **Premium:** CORONA's wall mid minus AURIC's and BRISA's has a mean of 22-28 pips and an sd of
  10-13.
- **Lead:** the correlation of CORONA's mid change with the change in AURIC + BRISA is 0.47-0.49
  at a lag of 4 steps, and about 0 at every other lag.

## What a good bot exploits

1. **CORONA's wide spread.** A maker one tick inside 12-pip walls fills about 1,000 times a
   session. This is the biggest edge: about 2.3-2.8k credits a session for `tests/mm_bot.py`.
2. **VANTA's trend.** It is flat, then trends, and the direction and start change by session, so
   it has to be detected intraday. A 600-step momentum rule (all in at 16+ pips, out below 8)
   makes +1.4k to +2.2k a session. A two-sided maker on VANTA loses a little in the trend, and
   the example bot loses up to 1.1k on the hidden days.
3. **AURIC and BRISA:** plain market making around the wall mid makes about 0.45k and 1.0-1.2k a
   session. On BRISA, handle the long drift from the buy-heavy flow with an inventory skew.
4. **CORONA's lead-lag:** shifting CORONA's fair by AURIC + BRISA's change over 4 steps barely
   matters for a passive quoter here, since 1.7 pips of lead is small against 12 pips of spread.
   It is a test of whether the team finds the relation, not a big payer.
   - **Premium lean:** leaning the quotes on the premium's reversion (fair minus 0.5 x the
     premium's deviation from 24) is an overfitting trap. It helped on public (CORONA 8,584
     against 7,349) and cost on hidden (4,285 against 5,552).
5. **Traps in the rules:**
   - **Pip value:** scores are pips x 0.25.
   - **VANTA's tick:** its tick is 4 pips.
   - **The tape:** line n's tape is the trades before snapshot n, not after it.
   - **Touch mark:** a big end position is marked at the touch, which costs half the spread. On
     CORONA that is 6 pips a lot.
   - **Taker fee:** takes cost 1 pip a lot.
   - **The cap:** the resting cap of 4, and pulls applied before posts.

## Scores (evaluate.py, credits)

| bot                         | public (3 sessions) | hidden (2 sessions) |
|-----------------------------|---------------------|---------------------|
| `public/example_bot.py`     | -303.75             | -1,958.75           |
| `private/tests/mm_bot.py`   | 11,488.75           | 8,632.00            |
| `private/reference_bot.py`  | 17,251.00           | 12,195.25           |
| `private/tests/edge_bot.py` | -7.50               | -5.50               |

**Per product:**
- **mm_bot, hidden:** AURIC 990, BRISA 2,273, CORONA 5,495, VANTA -126.
- **reference_bot, hidden:** AURIC 990, BRISA 2,273, CORONA 5,552, VANTA 3,380.

**edge_bot** expects, per session, errors 3 (a slow call, "boom", a non-list), slow calls 1, rejected
actions 8. Any failed assert in it would add an error.

## How the harness implements the rules

`private/evaluate.py` runs `arena.engine.run_day` with
`EngineConfig(resting=True, trade_matching=ALL, queue=PROB, queue_power=1, mark=TOUCH, fee=1, maker_fee=0)`.
- **Prices:** engine prices are pips (Day.info has no `tick`, so the fee unit is 1 pip).
- **Adapter checks:** `HaldenBot` enforces what the engine doesn't:
  - the action format, the 10-action cap and pulls first;
  - the per-order limit check, so the engine's own all-or-nothing check never fires;
  - the 4-resting cap, ref uniqueness, and the 50 ms budget, which raises and so discards the
    actions, while `self` keeps its changes.
- **Tape:** line n+1's tape becomes the engine's trades of tick n.
- **Upload check:** a non-stdlib import, or no `class Strategy` with `on_market`, is rejected
  with exit code 2.
