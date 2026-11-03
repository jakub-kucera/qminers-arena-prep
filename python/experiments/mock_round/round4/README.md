# The Varde Exchange: the fourth rehearsal (2026-11-03)

A disguised round whose portal is **not** `arena.engine`: `private/portal.py` matches and scores in its own code,
standard library only, so `experiments.day.calibrate` is tested against an exchange it didn't write (the audit's
round 8, R1). Three `arena.sim` products renamed (LUMEN a slow walk with buy-heavy takers, QUILL back to a level,
SORREL a fast walk with momentum), JSON-lines sessions with an aggressor flag on each print, prices in cents on a
5-cent tick, results in euros, and a class API (`Strategy(limits).on_tick(state)` returning dict actions, ids
assigned by the exchange). The rules state the matching, the limits, a fee per lot **and per order placed**; they
leave out that only half of each print reaches resting orders and that positions are valued at a 100-print VWAP
(`private/ANSWER_KEY.md`). No setting in calibrate's grid reproduces it.

**Spent:** its answer key is committed. A new rehearsal needs a new round, kept out of the repo until it is run.

- `public/`: `rules.md` and `example_bot.py`; `data/` is rebuilt (gitignored).
- `private/`: `generate.sh`, `disguise.py`, `portal.py` (`upload`: the public sessions' metrics as the Arena's portal
  names them, and a results ZIP; `hidden`: the score), `ANSWER_KEY.md`.
- `results/`: the run at `bc8569c` (`claude -p`, the round-1 kickoff prompt as `prompt.txt`, stopped once a
  validated bot was uploaded and calibrate run on it): its bot (`template.py`), format plug-in, `HANDOVER.md` and
  `DRYRUN_LOG.md`.

Rebuild and score (from the repo root, a few seconds):

```sh
python/experiments/mock_round/round4/private/generate.sh
python3 python/experiments/mock_round/round4/private/disguise.py
python3 python/experiments/mock_round/round4/private/portal.py hidden python/experiments/mock_round/round4/results/template.py
python3 python/experiments/mock_round/round4/private/portal.py hidden python/experiments/mock_round/round4/public/example_bot.py
```

The run: a validated bot uploaded at T+0:07, the whole run 14 minutes; calibrate refused ("no setting reproduces
the portal within 5%"), the session pasted nothing, widened the grid's modes and rebuilt the score from the ZIP by
hand, finding the order fee (28% of the gross) and a fill gap. Hidden score €208.77, the example bot's €80.10.
Results: `IDEAS.md`, "The kickoff prompts on a disguised round".
