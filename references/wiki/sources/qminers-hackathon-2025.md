---
title: Qminers Quant Hackathon 2025 (organisers' files and one solution)
type: source
repo: qminers-hackathon-2025
status: partly-read
updated: 2026-10-10
---

# Qminers Quant Hackathon 2025 (sports betting; MIT for the author's code)

## What it is
One team's solution to Qminers' own earlier competition, plus the **organisers' files**: the problem statement (`problem_info_en.md`, 235 lines, English translation by the author; `problem_info.md` is the original), the evaluation loop (`src/environment.py`, 165 lines), the runner (`src/evaluate.py`, extended by the author), and data (`data/games.csv`, 1989–2011). The author's own code: `src/model.py` (379 lines), `src/validate.py`, `src/experiments.py`. The user expects the 2026 Arena to be a big shift from this, so treat it as a weak prior only.

## Layout and code map
- `src/environment.py`: `IModel.place_bets(summary, opps, inc)` (`src/environment.py:7-9`), `Environment.run` (`src/environment.py:61-85`), `_validate_bets` (`src/environment.py:122-140`).
- `problem_info_en.md`: assignment `problem_info_en.md:15`, bets frame `problem_info_en.md:203`, technical details `problem_info_en.md:222`, common problems `problem_info_en.md:230`.
- README: "the submission system accepts one file" (`README.md:15`).

## What carries over
- **One class, one method, called once per day** with pandas DataFrames; the bot talks to the evaluator over stdin/stdout ("avoid using stdout in your submitted solution", `problem_info_en.md:225`).
- **Server-side upload with runtime-error reports**: "RTE: KeyError" when the code meets an empty frame or a new ID (`problem_info_en.md:230-233`). Compare the Arena portal's statuses Waiting / Running / Completed / Failed.
- **All-or-nothing validation, and rejection instead of clipping** (`src/environment.py:122-140`): bets on IDs not offered are dropped; a bet below `min_bet` or above `max_bet` is set to 0; if the total exceeds the bankroll, every bet that day is zeroed. Same spirit as Prosperity's "cancel all orders for a product that could breach the limit".
- **Hidden evaluation seasons** (`src/validate.py:20`): the score was on data the teams never saw.
- Result (the author's claim): only models built on top of the bookmaker's own probabilities beat it; more features made logistic regression lose ~45% of its bankroll (`README.md:43-45`).

## Traps
Pandas, daily cadence, bankroll and Kelly staking do not carry over to a trading simulation.

## Read depth
- **Read:** `problem_info_en.md` lines 15–24 and 203–235; `src/environment.py` lines 7–30, 61–152; `README.md`.
- **Mapped:** `src/model.py` by `grep`.
- **Unread:** `src/model.py` bodies, `docs/model_math.pdf`, the rest of the problem statement.

## Cited by
[submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [risk-and-protecting-a-lead](../concepts/risk-and-protecting-a-lead.md), [validation-and-overfitting](../concepts/validation-and-overfitting.md).
