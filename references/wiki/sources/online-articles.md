---
title: Online articles read through page-fetch summaries (no local copy)
type: source
repo: none
status: partly-read
updated: 2026-10-14
---

# Online articles read through page-fetch summaries (no local copy)

## What it is
Pages that could be fetched but are not saved in `references/`, so nothing here can be cited by line. Everything below is a summary produced by the fetch tool, not a reading of the full text: check a formula on the page before coding it.

## Layout and code map
- **Optiver explainers** (<https://www.optiver.com/insights/explainers/>): 33 short primers (only 18 listed on the page), of which ten concern options (pricing, Greeks, volatility, strategies) and one the order book ("Orders and the order book"). A free, concise alternative to a textbook if options appear. Titles read, articles not.
- **Optiver, "Where AI trading models work (and where they still fall short)"** (<https://www.optiver.com/insights/technology-blog/where-ai-trading-models-work-and-where-they-still-fall-short/>): their Applied AI team gave LLMs the intern exam, a six-month trader assessment and market-making games. The models handled theory, fair value and naming adverse selection. They were weak at updating beliefs as signals kept arriving, at reasoning more than one or two steps ahead, and at EV-optimal sizing (too conservative). They traded with an informed counterparty they had spotted, and they modelled other participants with "simplified or optimistic assumptions". The median intern scored 61%; no model scores are given.
- **Optiver Ready Trader Go, "How to play"** (<https://readytradergo.optiver.com/how-to-play/>): the rules of a shared ETF-and-future market.
  - Fees: a 2 bp taker fee and a 1 bp maker rebate.
  - Lose access for the rest of the round on: more than 50 order operations in a rolling second, a position over 100 lots, or more than 10 unhedged lots for over a minute.
  - Rejected: more than 10 active orders, more than 200 lots resting, and orders that cross your own.
  - Amends only reduce volume.
  - The ETF's closing price is clamped to within 0.2% of the future's.
- **ABIDES RMSC04 config** (<https://github.com/jpmorganchase/abides-jpmc-public/blob/main/abides-markets/abides_markets/configs/rmsc04.py>): JPMorgan's open agent-based market simulator, reference config.
  - Agents: 1,000 noise agents, 102 value agents (noisy views of a mean-reverting fundamental, `r_bar` 100,000, with rare "megashocks"), 12 momentum agents (moving-average crossovers, sizes 1–10) and 2 adaptive market makers (POV 0.025, 10 levels).
  - Latency: a fixed per-agent computation delay of 50 ns, not measured CPU time.

## What carries over
- If options appear, the Optiver primers are a free, short alternative to a textbook ([options-and-vouchers](../concepts/options-and-vouchers.md)).
- Where LLMs fail, the rules of a harder shared market, and what a "realistic exchange" simulator contains: all three are inputs to [harder-rounds](../concepts/harder-rounds.md).

## Traps
Summaries from a fetch tool can drop or misstate formulas.

## Read depth
- **Read (as summaries):** the Optiver listing; the Optiver AI article, the Ready Trader Go rules page and the ABIDES config (2026-10-14).
- **Unread:** the individual Optiver articles.
- **Moved out on 2026-10-13**, once local copies existed: Rigtorp, Databento and the Quant.SE thread ([rigtorp-queue-position](rigtorp-queue-position.md), [databento-queue-position](databento-queue-position.md), [quant-se-order-position](quant-se-order-position.md)) and Hummingbot's two pages ([hummingbot-avellaneda-stoikov](hummingbot-avellaneda-stoikov.md)).

## Cited by
[options-and-vouchers](../concepts/options-and-vouchers.md), [harder-rounds](../concepts/harder-rounds.md).
