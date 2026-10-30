# The Kestrel Bourse: the third rehearsal (2026-10-30)

A disguised round whose matching rules differ from the engine's defaults on purpose, made by an agent in the
scratchpad for the before/after test of a format's `ENGINE`, the engine's caps and `experiments.day.calibrate`.
Three `arena.sim` products renamed and repriced (TALC returns to a level that moves on the hidden days, OPHIR a
random walk with informed flow, BRAM a one-tick large-tick book), as level-by-level book changes and prints in CSV
with `HH:MM:SS.mmm` clocks, prices in points worth 2 credits a lot, and a function API (`setup(ctx)`,
`step(ctx, view)` returning order and cancel dicts with our own ids).

The rules state that orders rest, a 2 bp taker fee and a 0.5 bp maker rebate, at most 6 actions a step (cancels
included) and 3 orders working a product, and a breach charged per lot per step. They leave out what the first
upload has to show: trades fill a resting order only strictly through its price (`worse`), positions are marked at
the last trade, and orders reach the exchange one step after the call (`delay` 1). The truth is in
`private/ANSWER_KEY.md`.

**Spent:** its answer key is committed. A new rehearsal needs a new round, kept out of the repo until it is run.

- `public/`: `rules.md` and `example_bot.py`; `data/` is rebuilt (gitignored).
- `private/`: `generate.sh`, `disguise.py`, `portal.py` (an upload: the public sessions' metrics as the Arena's
  portal names them, and a results ZIP; `hidden`: the score), `ANSWER_KEY.md`, `check_calibrate.md` and its script,
  `check_configs.py` (what each hidden rule is worth for a bot), and `tests/`.
- `results/before/` (the repo at 24a536a, before `ENGINE`, the caps and calibrate) and `results/after/` (at
  d586efd): each run's bot, format plug-in, `HANDOVER.md`, log and prompt; `claude -p`, the same tool allowlist,
  stopped once a validated bot was uploaded and the engine fitted to it.

Rebuild and score (from the repo root, a few seconds):

```sh
python/experiments/mock_round/round3/private/generate.sh
uv run python python/experiments/mock_round/round3/private/disguise.py
uv run python python/experiments/mock_round/round3/private/portal.py hidden python/experiments/mock_round/round3/results/before/template.py
uv run python python/experiments/mock_round/round3/private/portal.py hidden python/experiments/mock_round/round3/results/after/template.py
```

Results: `IDEAS.md`, "The kickoff prompts on a disguised round".
