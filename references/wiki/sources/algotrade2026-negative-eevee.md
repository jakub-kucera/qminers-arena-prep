---
title: Negative Eevee, AlgoTrade 2026 winners
type: source
repo: algotrade2026-negative-eevee
status: partly-read
updated: 2026-10-11
---

# Negative Eevee (AlgoTrade 2026, 1st place, their claim)

## What it is
The cleaned-up repo of the winning team of the live event described in [algotrade2026-pitfa19](algotrade2026-pitfa19.md): a README, a leaderboard image (`images/leaderboard_pnl.jpeg`) and a Rust bot (`algo/src/`: `main.rs`, `runner.rs`, `quote.rs`, `config.rs`, `state.rs`). No licence file. Found through the HTML of the LinkedIn short link `lnkd.in/eeVSBCnW`. The team had been 2nd the year before (LinkedIn post, second-hand).

## Layout and code map
- `README.md:7`: **all teams traded in the same shared market**; 10 exchanges, 25 instruments; data every 100 ms; fresh books could be requested through the API under rate limits; an artificial delay between exchanges existed at first and the organisers later removed it.
- Strategy (`README.md:15-21`): a cross-exchange **IOC arbitrage bot**. Fair value was first the local exchange's average (trading accuracy for speed while the delay existed), then the average of the latest mids from all exchanges listing the product. IOC buys slightly below fair value and sells slightly above (about ±1 cent) into every relevant exchange. They polled order books about every 7 ms, adaptively (faster after price changes). **No hedging**: mispricings flipped many times per second, and hedging would have used API requests better spent on polling and orders.
- `algo/src/quote.rs`: `place_ioc` builds the `add_order` message with `"order_type": "ioc"` (`algo/src/quote.rs:10-22`); `fire_quote_for` sizes the order by position headroom and cash floor (`algo/src/quote.rs:24-80`).
- What they tested and dropped (`README.md:23`): ETF arbitrage, exchange lead-lag, ETF/component lead-lag, CARD/SIMP mean reversion. They existed "but were less profitable or less exclusive. Mean reversion still allowed other teams to enter later; cross-exchange arbitrage did not."
- **Crowding evidence** (`README.md:23`): "Several teams mentioned that their own cross-exchange arbitrage became much worse around round 2, which was also when our first prototypes went live."

## What carries over
Only the lessons about a shared market: speed and exclusivity decide who gets a crossing edge; a signal that "allows other teams to enter later" decays. See [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md). The Arena's portal looks like batch evaluation, where latency is not the contest.

## Traps
- The README says it is cleaned up ("Notes, AI slop and dead experiments were removed", `README.md:26`), so it shows the final idea, not the path.
- Rank and PnL are the team's claim (a leaderboard screenshot).

## Read depth
- **Read:** the whole README; `algo/src/quote.rs:1-80`.
- **Unread:** `main.rs`, `runner.rs`, `state.rs`, `config.rs`.

## Cited by
[shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [cross-market-and-conversions](../concepts/cross-market-and-conversions.md), [submission-and-scoring-mechanics](../concepts/submission-and-scoring-mechanics.md).
