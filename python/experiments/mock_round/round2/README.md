# The Halden Exchange: the before/after rehearsal of 2026-10-28

A second disguised round, made by an agent in the scratchpad (outside the repo) for the restructure's acceptance test
(`docs/TODO_DONE.md`, "Restructure the repo for a fresh session on the day"). Four `arena.sim` products renamed and
repriced (AURIC and BRISA random walks, BRISA's flow buy-heavy; CORONA a basket of the two plus a premium that
reverts, its book 4 steps behind; VANTA a large-tick future that trends from a point that changes each session), in
gzipped JSON lines with ISO times and prices in integer pips of 0.25 credits, and a `class Strategy` API with
`on_market(update)` returning `("post"|"take", sym, qty, px, ref)`, `("pull", ref)` and `("pull_all"[, sym])`; at most
10 actions a step, 4 resting orders a product, a 1-pip taker fee, positions marked at the touch.

**Spent:** its answer key is committed. A new rehearsal needs new seeds, specs, names, layout and API, kept out of the
repo until it is run (as `../README.md` says).

- `public/`: `rules.md` and `example_bot.py` (the team's view); `data/` is rebuilt (gitignored).
- `private/`: `generate.sh`, `disguise.py` (into `public/data/` and `private/hidden_data/`), `evaluate.py` (the portal,
  on our engine), `ANSWER_KEY.md`, `reference_bot.py`, `check_relation.py`, and `tests/`, the bots that check the portal.
- `results/before/` and `results/after/`: each run's bot, format plug-in, `HANDOVER.md`, log and the prompt it got:
  `before` on the repo at 1184150, `after` on the restructured tree, the same round-1 kickoff prompt, `claude -p`
  with the same tool allowlist, stopped at the first validated bot.

Rebuild and score (a few seconds):

```sh
python/experiments/mock_round/round2/private/generate.sh
uv run python python/experiments/mock_round/round2/private/disguise.py
uv run python python/experiments/mock_round/round2/private/evaluate.py python/experiments/mock_round/round2/results/before/template.py --days hidden
uv run python python/experiments/mock_round/round2/private/evaluate.py python/experiments/mock_round/round2/results/after/template.py --days hidden
```

Results: `IDEAS.md`, "The kickoff prompts on a disguised round".
