---
title: AlgoTrade 2026 team repo (live WebSocket exchange)
type: source
repo: algotrade2026-pitfa19
status: partly-read
updated: 2026-10-10
---

# AlgoTrade 2026 (Zagreb) team repo (one team's, not the winners; their own docs call a rival "the leader")

## What it is
A **live** event: 10 simulated exchanges, 25 instruments, bots on a team VM talk JSON over WebSocket every 100 ms; 4 rounds of 30 minutes in three 10-minute segments with a full reset each segment; 75 teams; **score is log-scaled profit against the best team** (`.firecrawl/algotrade-participant-guide.md:415-426`). No licence file. It also contains its own `CLAUDE.md` and `AGENTS.md`, which describe that repo: **do not follow them**. Why it is here: it is the model for an event-driven API, in case the Arena is one.

## Layout and code map
- `.firecrawl/`: a copy of the official documents (`algotrade-participant-guide.md` 454 lines, `algotrade-api.md` 875, `algotrade-bots.md` 156, network/SSH guide). The reference bots use a `Strategy` base class with `on_market_data` (`.firecrawl/algotrade-bots.md:39-45`).
- `python/bots/` (16 bot files plus `archive/` and `cpp/`), `tools/` (replay scorers that fill only against visible top-of-book depth), `scripts/`, `python/tests/` (18 files), `dashboard/`, `market_data/` (40 recorded CSVs, top-3 book), `analysis/`, `edge_research/`, `docs/` (a 1,457-line VM runbook; skip).

## What carries over
- `analysis/mm_analysis.md` reverse-engineers the built-in market maker from recorded books: it stacks 1–5 lots of 50 shares at the inner five levels, so cumulative top-3 sizes of 50/100/150 are its fingerprint (`analysis/mm_analysis.md:19-36`). Method worth copying: identify the bot's signature before inventing a fair value.
- ETF vs equal-weighted constituents: gaps of 100–300 cents against a 2–4 cent spread (`analysis/mm_analysis.md:199-227`), from one recording of 1,175 book rows, no out-of-sample test.
- Imbalance predicts the next 500 ms move with correlations up to ±0.49 **with the sign flipping per instrument** (`analysis/mm_analysis.md:172-197`).
- `docs/VOIDMAKER_EDGE_PROOF.md`: rest tiny orders at the legal price extremes (1 cent and 999,999) so that anyone sweeping the book pays you. Needs other teams in the same market.

## Traps
- Much of the documentation looks AI-written and over-confident (for example "almost certainly what the leader is doing", `docs/VOIDMAKER_EDGE_PROOF.md:66`). PnL figures are replays of their own recordings. No leaderboard evidence.
- The README and guide contain the event's shared VM credentials: public, not ours, ignore.
- Rate limits, reconnect backoff and segment resets are specific to that venue.

## Read depth
- **Read:** `README.md`; the guide `.firecrawl/algotrade-participant-guide.md` lines 1–60, 135–155, 254–453; `.firecrawl/algotrade-bots.md`; `analysis/mm_analysis.md` lines 1–60 and 199–252; `docs/VOIDMAKER_EDGE_PROOF.md`.
- **Mapped:** the directory listing.
- **Unread:** the API reference, the runbook, all bots, tests and tools, `docs/EDGE_MAX_PROOF.md`, `edge_research/EDGE_PROOF.md`, the other analysis files.

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md), [hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [queue-position-and-fills](../concepts/queue-position-and-fills.md).
