# Can experiments.day.calibrate recover the truth? (organiser note)

**Yes, all four hidden settings except the queue model, which is inert here.**

A perfect calibration of the first upload (a team's plug-in with the stated rules in its ENGINE and
`--vary delay=0,1`) prints as best:

```
worse, resting, {back|prob|front}, last, limit_penalty 0.25, delay 1, fee_bps 2.0, maker_fee_bps -0.5, max_actions 6, max_resting 3
RESTING = True
ENGINE = {"trade_matching": "worse", "mark": "last", "limit_penalty": 0.25, "delay": 1, "fee_bps": 2.0,
          "maker_fee_bps": -0.5, "max_actions": 6, "max_resting": 3}      (+ "queue": "prob" for the exact truth)
```

Checked with `private/check_calibrate.py`, which runs calibrate's own `candidates()` (x delay 0,1 = 144
settings), `figures()` and `error()` through the portal's loader and adapter on the public sessions,
against an upload's `metrics.json` plus each instrument's fills and volume from its results ZIP:

| upload | best error | the truth's error | tied with the truth | next |
|--------|------------|-------------------|---------------------|------|
| mm_bot (upload 2) | 6.25% | 6.25% | queue back / front (deplete: 6.32%) | mark mid 7.88% |
| example_bot (upload 1) | 5.56% | 5.56% | queue back / front, and deplete on/off | mark mid 9.68% |

- **The residual is markPrice only.** The portal's `markPrice` is the mean of the traded instruments'
  marks when more than one traded; calibrate's `figures()` only reads `markPrice` when one instrument
  traded, so it scores 0 against it: an error of 1.0 on one figure of 16 (6.25%) or 18 (5.56%), the
  same for every setting. Every other figure matches exactly (error 0). A one-instrument upload, or
  dropping `markPrice` from the JSON, gives 0.0%.
- **Queue:** under `worse`, prints at the order's price never fill it, so the queue model changes
  nothing: back, prob and front tie exactly. No upload can tell them apart; `prob` is the truth only
  nominally.
- **Deplete** ties when the bot never takes from the book (the example bot's 1-lot joins).
- **Delay** is not in calibrate's default grid: the team has to `--vary delay=0,1` (the orders CSV's
  NEW times, one step after each decision, are the cue). Without it, the best setting is far off.
- **Units:** the portal's figures are credits at 0.02 an engine unit (hundredths of a point x 2 credits);
  calibrate reads the scale from `Day.info["unit"]`, so a plug-in must set `unit = 0.02` (or pass
  `--scale 0.02`). `score` is the sessions' sum, `fills` counts fills, `pnlSe` is calibrate's per-day
  reading, all readings calibrate already has.
- Nothing in the portal's figures is outside what our engine computes: they are calibrate's
  `figures()` of `run_day` results under TRUTH.
