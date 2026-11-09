# Qminers Algo Trade Arena: the preparation

Team ThatsMyQuant's month of preparation (7 Oct to 7 Nov 2026) for the Qminers Algo Trade Arena, a 24-hour
algorithmic trading hackathon in Prague. The event itself, our bots, results and what the market turned out to be,
is in **[qminers-arena-2026](https://github.com/jakub-kucera/qminers-arena-2026)**; we finished 16th of 61. This
repository stops on the morning of the event, before the organisers' code and the real API arrived.

## The premise, and why it did not hold

Nothing about the Arena's API was known in advance, so we built on IMC Prosperity data and its bot format as a
stand-in: several products, a market of bots that react to each other, market making around a fair value. The Arena
turned out to be one instrument, a generated tape replayed against our orders, and in three of its four rounds it
rewarded taking on a short-term forecast over making markets. The strategies here did not transfer. The habits did:
learn online from the tape instead of tuning constants, check every change on held-out data, and write every idea down
with its numbers. So did the engine and its source check.

## What is here

| | |
|---|---|
| [`python/arena/`](python/arena/README.md) | A backtesting engine for Prosperity-format data, whose fills matched jmerle's `prosperity3bt` exactly in 15 comparisons, and its tools: diagnose a day's data, backtest, grid search with honest statistics, compare bots, stress tests, a simulated market, the pre-upload source check |
| [`rust/`](rust/README.md) | The engine and the bots again in Rust, about 130 times faster per backtest, kept in step with the Python by hashes and parity tests |
| [`python/bots/`](python/bots/README.md) | The single-file market maker we prepared, the first-hour probe bot, and an **LLM zoo**: 32 bots written by Claude, ChatGPT, Gemini and open models from one specification, played against each other |
| [`references/wiki/`](references/wiki/index.md) | A **wiki of the market-making literature**, 120 pages (concepts and sources) kept by agents from papers and books, with every claim cited |
| [`IDEAS.md`](IDEAS.md) | 115 strategy ideas tested on Prosperity data, each with its command, numbers and verdict |
| [`python/experiments/`](python/experiments/README.md) | The experiments behind `IDEAS.md`, and the agent-run mock rounds that rehearsed the event |
| `docs/guidebook/` | A field guide to the trading behind all this, written for the day (a Quarto book) |
| `ON_THE_DAY.md`, `RUNBOOK.md`, `KICKOFF_PROMPT.md`, `CLAUDE.md` | The plan for the day and the instructions the agent sessions worked from, as they stood when it began |
| [`references/`](references/README.md) | The reference repositories we read (`clone.sh` fetches them, pinned) |

## Setup

```sh
references/clone.sh   # reference repositories and the Prosperity data (~2 GB)
uv sync               # Python 3.13; installs python/ editable, so `python -m arena...` runs from here
uv run pytest         # the parity tests skip without the clones
uv run python -m arena.backtest python/bots/template.py 1 --data p3   # the template on Prosperity 3, round 1
```

Most of this was written with AI agents (Claude Code), working in parallel worktrees and checking each other's
numbers; `CLAUDE.md` is what every session read first.

## Licence

MIT ([`LICENSE`](LICENSE)) for our code and documents. The wiki's short quotations from papers and books belong to
their authors; the converted papers, the reference repositories and the Prosperity data are not included.
