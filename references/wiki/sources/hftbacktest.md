---
title: hftbacktest (queue models and fill docs)
type: source
repo: hftbacktest
status: partly-read
updated: 2026-10-10
---

# hftbacktest (nkaz001, MIT, Rust core with Python bindings, 4,873 stars)

## What it is
The reference open-source market-making backtester with queue-position and latency models. Cargo workspace: `hftbacktest/` (core), `py-hftbacktest/`, `collector/` and `connector/` (live-trading components; not read), `examples/` (24 notebooks), `docs/` (Sphinx). We read it for its queue models and its honest documentation, not as a backtester: it replays event streams, our data is one snapshot per tick.

## Layout and code map
- `hftbacktest/src/backtest/models/queue.rs`: `RiskAdverseQueueModel` `hftbacktest/src/backtest/models/queue.rs:44` (**ours**), `QueuePos` `hftbacktest/src/backtest/models/queue.rs:100`, the `Probability` trait `hftbacktest/src/backtest/models/queue.rs:125`, **`ProbQueueModel`** `hftbacktest/src/backtest/models/queue.rs:139-219`, `PowerProbQueueFunc` `hftbacktest/src/backtest/models/queue.rs:221`, `LogProbQueueFunc` `hftbacktest/src/backtest/models/queue.rs:245`, the `*2`/`*3` variants `hftbacktest/src/backtest/models/queue.rs:267-340`, order-by-order `L3FIFOQueueModel` `hftbacktest/src/backtest/models/queue.rs:481`.
  The update rule is `est_front = front - (1 - p) * chg + min(back - p * chg, 0)`, then `min(est_front, new_qty)`; trades are subtracted first so they are not counted twice. `p = f(back) / (f(back) + f(front))` is the probability that a decrease was **behind** the order (`hftbacktest/src/backtest/models/queue.rs:125-128`).
- `hftbacktest/src/backtest/proc/`: exchange simulators (`nopartialfillexchange.rs`, `partialfillexchange.rs`, `l3_*`).
- `docs/order_fill.rst` (186 lines): exact fill conditions (a buy fills in full if its price ≥ best ask, or > a sell trade price, or it is at the queue front and equals the trade price); **no market impact**. `docs/debugging_backtesting_and_live_discrepancies.rst` (35 lines): the two causes of backtest-vs-live gaps are latency and the queue model; start with small size.
- `examples/` notebooks (cite by name): `Probability Queue Models`, `Queue-Based Market Making in Large Tick Size Assets`, `GLFT Market Making Model and Grid Trading`, `Making Multiple Markets` (Guéant's model across assets), `Market Making with Alpha - Order Book Imbalance` (its author raised the queue parameter from 2 to 3 for 2025, i.e. fills got harder), `... - APT`, `... - Basis`.

## What carries over
The queue-model family for the `--queue back|prob|front` TODO; the fill-condition list as a cross-check on `python/arena/engine.py`; worked GLFT examples.

## Traps
Event-driven with latency; do not try to run it on tick snapshots.

## Read depth
- **Read:** `hftbacktest/src/backtest/models/queue.rs` lines 100–300 (twice, in different sessions); `docs/order_fill.rst` (first 110 lines); the debugging doc.
- **Mapped:** the other Rust files, notebooks by first cells.
- **Unread:** the rest of the docs, the L3 models, the live connectors.

## Cited by
[queue-position-and-fills](../concepts/queue-position-and-fills.md), [backtesting-and-tooling](../concepts/backtesting-and-tooling.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md).
