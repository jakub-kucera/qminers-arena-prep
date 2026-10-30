# The agent-only mock round of 2026-10-26

A disguised round for rehearsing the day: three products from `arena.sim` (a level, jumps that snap
back, a market maker that doesn't know the price), renamed, repriced and written in a layout and
bot API unlike any in the repo. An agent made it out of sight of the two that ran it (the second
audit's A2; `docs/TODO_DONE.md`, "From the audit (2026-10-26)").

**Spent:** this round's answer key is committed, so its seeds, specs and layout are known. A new
rehearsal needs new data: change the seeds and specs in `private/generate.sh` and the names and
layout in `private/disguise.py` (or have an agent write new ones), and keep the new answer key out
of the repo until the round is run.

- `public/`: what a team is given. `rules.md` and `example_bot.py` are committed; `data/` is rebuilt.
- `private/`: `generate.sh` (the simulator days), `disguise.py` (into `public/data/` and
  `private/hidden_data/`), `evaluate.py` (the portal: a bot file on the public or the hidden days,
  under the rules, on our engine), `ANSWER_KEY.md`, and `tests/`, the bots that check `evaluate.py`.
- `results/`: the two runs' final bots, their logs, and the format plug-in the repo run wrote.

Rebuild and score (a few seconds):

```sh
python/experiments/mock_round/private/generate.sh
uv run python python/experiments/mock_round/private/disguise.py
uv run python python/experiments/mock_round/private/evaluate.py python/experiments/mock_round/results/repo_template.py --days hidden
uv run python python/experiments/mock_round/private/evaluate.py python/experiments/mock_round/results/clean_room.py --days hidden
```

Results: `IDEAS.md`, "The kickoff prompts on a disguised round".

A second round, the Halden Exchange, ran the restructure's before/after rehearsal on 2026-10-28: `round2/README.md`. A third, the Kestrel Bourse, tested the engine fit on 2026-10-30: `round3/README.md`.
