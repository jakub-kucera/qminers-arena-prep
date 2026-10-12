---
title: HumzahM, UChicago 2025 Case 2 (1st, portfolio allocation)
type: source
repo: uchicago-2025-case2-humzah
status: read
updated: 2026-10-11
---

# HumzahM, UChicago Trading Competition 2025, Case 2 (1st of 41, their claim)

## What it is
Three files: `chicago8.py` (the final submission, 4.9 KB), `case2.ipynb` (the write-up as notebook markdown plus plots) and `Case2.csv` (the practice data, 4.4 MB). No licence file. Case 2 is the **file-upload** case of that competition: a class template with one method, `allocate_portfolio(asset_prices)`, called once per tick with the prices of 6 assets, returning weights in [−1, 1]; state must be kept in class fields. The same format as Case 2 of 2026 (see [uchicago-trading-2026](uchicago-trading-2026.md)).

## Layout and code map
- `chicago8.py`: `class Allocator` (`chicago8.py:18`), `allocate_portfolio` (`chicago8.py:27`). It uses `tick_number % 10` (`chicago8.py:35`): on the 10th tick take 0.33 against the last return's sign in three assets; otherwise take only the asset with the largest mean recent return, **capping** the size so the expected return is `target_return = 0.0036` (`chicago8.py:65`). The grading function is the organisers'. The file prints the practice-data Sharpe, claimed `1.7307` (`chicago8.py:107`).
- Notebook write-up (cells cited by order, markdown only): (1) "Literally zoom in on the data": the assets were much more stable at tick level than they looked, and **their returns jumped on exactly every 10th tick**; (2) the baseline was "trade whatever was above 0, sell whatever was below, don't trade on the 10th tick", which "would've been enough to place me in the top 3"; (3) three optimisations: trade only the asset with the highest expected return, **cap the return near its mean** to cut variance, and trade the 10th tick with the sign flipped; (4) "I only know of one team that claimed a higher Sharpe on the practice data than us. My guess is that they were using some overfit technique."

## What carries over
- The winning approach was **finding the generator's structure by plotting at the finest scale**, in a few hours, "as scientifically as possible without instantly jumping to optimal portfolio theory and machine learning" (cell 0). Same lesson as [probing-the-environment](../concepts/probing-the-environment.md) and the Prosperity snap-back story ([jumps-and-snap-back](../concepts/jumps-and-snap-back.md)).
- A stub interface with per-call state in fields is a plausible shape for the Arena's file upload.

## Traps
The Sharpe is on the practice data; the final score was on a held-out period. The author calls the capping "something you'd obviously never do in real life". It is a one-evening entry for a short, simple data set.

## Read depth
- **Read:** all of `chicago8.py`; all markdown cells of `case2.ipynb`.
- **Unread:** the notebook's code cells and plots, `Case2.csv`.

## Cited by
[probing-the-environment](../concepts/probing-the-environment.md), [jumps-and-snap-back](../concepts/jumps-and-snap-back.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md).
