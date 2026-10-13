---
title: Qminers Quant Hackathon 2024 (the winner's post-mortem and the organisers' files)
type: source
repo: qminers-hackathon-2024
status: partly-read
updated: 2026-10-13
---

# Qminers Quant Hackathon 2024 (NBA betting; the winner's repo, no licence)

## What it is
The 1st-place team's public repo for Qminers' 2024 Quant Hackathon (team SHAQ & KOBE, solo author). It holds a post-mortem (`README.md`) and the **organisers' files**: the Czech README (`COMPETITION_README.md`), the problem statement (`problem_info.md`), the evaluation loop (`src/submit_model/environment.py`, also copied into `src/mapbet/` and `src/meta_model/`), the runner (`src/submit_model/evaluate.py`) and the conda environment (`qqh-2024-env.yml`). Three screenshots show the qualification leaderboard and the finals. The rest is the author's research scripts and models. The user's team found it as `last_year_challenge/` on a branch of their private 2025 repo (`jakub-kucera/QQH-2025`, branch `kuca-ai-merge-2024`). The public original is pinned in `clone.sh`.

The task was sports betting, like 2025, so this is a weak prior on the Arena's task. It is stronger on **how Qminers runs a competition**, because now there are two years to compare.

## Layout and code map
- **Rules and limits:** `COMPETITION_README.md:31` (a class `Model` with `place_bets`), `COMPETITION_README.md:35-43` (forbidden: other data, cooperation, mining the system, network, files outside `/tmp`), `COMPETITION_README.md:45-59` (hidden validation seasons, 1 CPU and 5 GB RAM, one evaluation at a time, a capped number of submissions, RTE / MLE / TLE statuses).
- **The evaluation loop:** `src/submit_model/environment.py:63-87` (`run`, one call per day), `src/submit_model/environment.py:130-148` (`_validate_bets`). The runner sets `min_bet=5`, `max_bet=100` (`src/submit_model/evaluate.py:17`).
- **The problem statement:** a bet can be added to the same game on several days until it is played (`problem_info.md:50`); the technical rules (`problem_info.md:217-223`); the common failure (`problem_info.md:225-228`).
- **The post-mortem:** the qualification (`README.md:9-39`), the finals preparation (`README.md:41-49`), finals day (`README.md:51-63`).
- **The risk model:** `risk_model/main.py:48-101` (a tournament against 15 simulated rivals), `risk_model/boostrap_optimizer.py:30-58` (the log-wealth version).
- **Screenshots** (looked at, not machine-citable): `first_stage_scores.png` (the qualification leaderboard on hyperion), `score_evolution.png` (every finalist's bankroll over the three finals rounds, log scale), `final_scores.png` (16 finalists' final cash).

## What carries over
- **Qminers reuse their evaluator from year to year** *(checked: `diff` of the two `environment.py` files)*. The 2025 loop is the 2024 one with a draw column added and the players table dropped. The README text, the 1 CPU / 5 GB limit and the RTE / MLE / TLE statuses are the same in both years (the 2025 organisers' README was read on the `main` branch of the user's private repo through the GitHub API). If the Arena has a playground, its evaluator may also be handed out, so read it first ([probing](../concepts/probing-the-environment.md)).
- **The format: an online qualification, then an in-person final with the scores reset** (their claim, `README.md:43`). The qualification ran on hidden seasons 1999/00–2004/05 (`COMPETITION_README.md:47-48`); the finals chart runs from 2006 to 2011, so the final used later, unseen data *(checked on the screenshot)*. The final had 3 rounds in one day (`README.md:55`) with a shorter horizon, "thus introducing more variance".
- **The submission cap was 20** in the qualification (their claim, `README.md:33`); the README only says it is limited (`COMPETITION_README.md:53`).
- **The leaderboard shows the other teams' results, and more.** The author watched the others' RAM use, runtime and score (`README.md:67`). The screenshot shows a score and a time per test case for each team, and a `_LLM_BENCHMARK_` entry in 2nd place, likely a baseline the organisers ran with an LLM *(inferred from the name)*.
- **Sandbagging** (their claim, `README.md:35`): the winner capped the qualification profit at 1/10 of the model's so that others wouldn't try harder, and showed the real score only in the last hours. This only works where a submission's public score doesn't count, or where the final one replaces it.
- **The finals data was scrambled**, and working out its period paid: the author recognised round 3 as just after covid (`README.md:57`). Identifying which regime the data comes from is a skill the organisers test, deliberately or not.
- **Risk chosen for the chance of winning, not for growth** (`README.md:45-49`): simulate the final against rivals with weaker, correlated models and varied risk appetites, and choose the Kelly multiplier with the highest share of first places. The code also stakes a quarter of the bankroll at three times its Kelly fraction for the first 1,000 bets, then folds it back in (`risk_model/main.py:68-85`): aggressive early, normal later.
- **Cutting risk while ahead held first place** and cost them some upside: halving the stake in round 3 kept 1st (107k) but, by their estimate, cost about 36k (`README.md:57`, `README.md:63`).
- **A short reset final rewards variance for teams behind** *(checked on the screenshots)*. Several finalists fell to almost nothing (Graviton 38, Sarina_Technologies 17), and Degen climbed from about 50 to 69k in the last round and finished 2nd.

## Traps
- **The README's risk model is not the code.** The README says optuna; the code is a grid. `grid_search_optimize` in `risk_model/main.py:103-107` returns nothing, so line 110 would fail on unpacking. So the tuned multiplier was not produced by this file *(checked by reading)*. The idea stands, not the number.
- Pandas, a daily cadence, a compounding bankroll and Kelly staking don't carry over to a trading simulation with position limits.
- The scores and their attribution are the author's claims. The 77,382 qualification score and the finals table agree with the screenshots.

## Read depth
- **Read:** `README.md`, `COMPETITION_README.md`, `problem_info.md` (the data columns skimmed), `src/submit_model/environment.py`, `src/submit_model/evaluate.py`, `risk_model/` (all three files), the three screenshots.
- **Mapped:** `research/` (26 folders, by name), `src/meta_model/` and `nn/` by file listing.
- **Unread:** the model code (`src/submit_model/model.py`, `src/meta_model/*/model.py`, `nn/`), the notebooks, `odds_backtest/`, `FACTOR_IMPORTANCE.md`.

## Cited by
[submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [probing-the-environment](../concepts/probing-the-environment.md).
