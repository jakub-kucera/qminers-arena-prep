# Runbook

One page for the day. `ON_THE_DAY.md` has the reasons and the detail behind each line (its sections are
named in brackets), and `KICKOFF_PROMPT.md` starts each agent session. `D` is the round's data
folder, `DAYS` its day specs, and `BOT` our bot, e.g. `python/bots/qminers/template.py`.

## Before the doors open (Sat 08:00)
- `git pull && uv sync && uv run pytest` on every laptop; `references/` was cloned at home.
- Names for A (driver, recorder) and B (data, research) ["The day: timeline and roles"].
- Every laptop on Europe/Prague time, and logged in to the portal during the playground: the e-mailed links are
  single-use ["Known so far"].

## Opening and workshop (09:00–10:30)
1. One person reads the Technical Rules in full and writes each answer into "First hour", with its source.
2. Settle first: the entry point, the data format, whether orders rest, the limits, the Python version and
   allowed imports, the time limit, the submission cap and whether scores come back ["First hour"].
3. By 10:30, a fallback bot or not: an agent writes one only if the cap leaves an extra round-1 upload and the
   ADAPTER may not be validated by 13:00 ["Spend the round's submissions", "A fallback first?"].

## Playground (10:30–12:00): three tracks at once ["Splitting the first hour"]
- **Probes (A):** rewrite `python/bots/probe.py`'s ADAPTER and set `PRODUCT` and `LIMIT`. Check it locally with
  `uv run python -m arena.backtest python/bots/probe.py 1 --print --no-strict`, then run it in the
  playground and read the `PROBE` lines ["Probes"]. If their rules forbid dynamic imports or sleeps, or
  uploads are scarce, delete its RISKY PROBES block first.
- **Data (B):** copy `python/arena/formats/drill.py` to `qminers.py` and register it ["The format swap, step by
  step"]; then run `uv run python -m arena.diagnose DAYS --format qminers --data D` ["What kind of market is
  each product?"].
- **Bot (A):** in a copy of `python/bots/template.py`, rewrite only the imports, PARAMS and ADAPTER. Then
  `uv run python -m arena.validate BOT DAYS --format qminers --data D --time-limit-ms <theirs> --max-size <the dashboard's> [--allow numpy]`.
  Over the cap: `uv run python -m arena.compact BOT <copy>.py`, then validate and upload the copy ["How do submissions work?"].

## Lunch (12:00–13:00)
- Backtest in each fill mode (`--match-trades all|worse|none`, then `--resting`; `--mark` and `--limit-penalty` to match the
  first upload's PnL and metrics, printed by `--metrics`) and keep the one closest to
  the playground for every later run ["Which backtest settings match the playground?"].
- Write round 1's candidates down in order, with the local result of each ["Spend the round's submissions"].

## Each round (T = its start; rounds at 13:00, 19:00, 01:00, 07:00)
| When | Do |
|---|---|
| T+0:00 | Reload the dashboard; download the data (its link goes with the round) and the round's rules; note the submission deadline, which may come before the end. Write what changed into "Rule changes" and "Products". |
| T+0:15 | `arena.diagnose` on the new days; backtest last round's bot on them in each mode; `arena.validate` it: the first candidate. |
| T+0:30 | New products into PARAMS, by `references/wiki/concepts/reading-the-data-on-day-one.md`. Rounds 2–4: by T+1:00, one alternative to last round's approach against it, and every setting gridded again; last round's choices are priors, not defaults ["Choose the approach again each round"]. Options, baskets, named traders or jumps: the experiment for each (`python/experiments/README.md`). |
| T+1:00 | `uv run python -m arena.grid BOT DAYS --format qminers --data D --grid PARAMS.<P>.make_edge=0.5,1,1.5,2 --modes <closest>,worse [--screen 0.25]`. Change a setting only to the summary's `pick` ["Evaluation data"]. Fill model unsure: add a `--scenario` for each one left possible ["Which backtest settings match the playground?"]. |
| T+1:30 | `uv run python -m arena.stress BOT DAYS --format qminers --data D`; set each `stop_loss` to about 3× its plain drawdown ["Stress the bot"]. If the market is shared: `--vs` copies, the round's zoo through `arena.compare`, and the rivals ["Is the market shared"]. |
| T+2:00 | A validated bot at least as good as the last one, uploaded; its portal score against our backtest is the engine's error `T`. |
| deadline − 0:30 | (T+4:30 if the deadline is the round's end; earlier if twice the first evaluation's time is longer.) Stop changing the strategy. Validate the final candidate and upload it. |
| T−0:10 | Check which submission is marked final. Write the handover note. |
| After | Once the private run is done: our PRIVATE entry's results against the public run of the same file; save the leaderboard's data to `data/arena/round<N>/leaderboard.json` and run `uv run python -m experiments.leaderboard_curves --read data/arena/round<N>/leaderboard.json --team <ours>`. Both into the handover note ["The day: timeline and roles", "Is the market shared"]. |

## Rules that hold all day
- Never upload code `arena.validate` hasn't passed, and never spend a submission on untested code.
- Never choose between two variants by portal score when they are within `T` of each other.
- One evaluation at a time, and an upload that completes becomes final: time the first evaluation, and mark the
  chosen one final again after any exploratory upload ["How do submissions work?"].
- Naps only in rounds 2 and 3, in a round that looks like the last, T+0:30 to T+4:00; while A sleeps, B uploads
  only from the written list ["The day: timeline and roles"].
- Before round 4: decide in writing how much risk to keep, from the lead (in weighted points if the rounds are
  weighted; the 10/20/30/40% are unconfirmed) ["How is PnL scored?"].
