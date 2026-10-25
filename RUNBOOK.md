# Runbook

One page for the day. `ON_THE_DAY.md` has the reasons and the detail behind each line (its sections are
named in brackets), and `KICKOFF_PROMPT.md` starts each agent session. `D` is the round's data
folder, `DAYS` its day specs, and `BOT` our bot, e.g. `python/bots/qminers/template.py`.

## Before the doors open (Sat 08:00)
- `git pull && uv sync && uv run pytest` on every laptop; `references/` was cloned at home.
- Names for A (driver, recorder) and B (data, research) ["The day: timeline and roles"].

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
  `uv run python -m arena.validate BOT DAYS --format qminers --data D --time-limit-ms <theirs> [--allow numpy]`.

## Lunch (12:00–13:00)
- Backtest in each fill mode (`--match-trades all|worse|none`, then `--resting`) and keep the one closest to
  the playground for every later run ["Which backtest settings match the playground?"].
- Write round 1's candidates down in order, with the local result of each ["Spend the round's submissions"].

## Each round (T = its start; rounds at 13:00, 19:00, 01:00, 07:00)
| When | Do |
|---|---|
| T+0:00 | Download the data and the round's rules; write what changed into "Rule changes" and "Products". |
| T+0:15 | `arena.diagnose` on the new days; backtest last round's bot on them in each mode; `arena.validate` it: the first candidate. |
| T+0:30 | New products into PARAMS, by `references/wiki/concepts/reading-the-data-on-day-one.md`. Options, baskets, named traders or jumps: the experiment for each (`python/experiments/README.md`). |
| T+1:00 | `uv run python -m arena.grid BOT DAYS --format qminers --data D --grid PARAMS.<P>.make_edge=0.5,1,1.5,2 --modes <closest>,worse [--screen 0.25]`. Change a setting only to the summary's `pick` ["Evaluation data"]. Fill model unsure: add a `--scenario` for each one left possible ["Which backtest settings match the playground?"]. |
| T+1:30 | `uv run python -m arena.stress BOT DAYS --format qminers --data D`; set each `stop_loss` to about 3× its plain drawdown ["Stress the bot"]. If the market is shared: `--vs` copies, the round's zoo through `arena.compare`, and the rivals ["Is the market shared"]. |
| T+2:00 | A validated bot at least as good as the last one, uploaded; its portal score against our backtest is the engine's error `T`. |
| T+4:30 | Stop changing the strategy. Validate the final candidate and upload it. |
| T−0:10 | Check which submission is marked final. Write the handover note. |

## Rules that hold all day
- Never upload code `arena.validate` hasn't passed, and never spend a submission on untested code.
- Never choose between two variants by portal score when they are within `T` of each other.
- One evaluation at a time, and an upload that completes becomes final: time the first evaluation, and mark the
  chosen one final again after any exploratory upload ["How do submissions work?"].
- Naps only in rounds 2 and 3, in a round that looks like the last, T+0:30 to T+4:00; while A sleeps, B uploads
  only from the written list ["The day: timeline and roles"].
- Before round 4 (40%): decide in writing how much risk to keep, from the lead in weighted points ["How is PnL scored?"].
