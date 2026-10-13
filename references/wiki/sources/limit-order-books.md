---
title: Gould et al., "Limit order books" (2013)
type: source
repo: literature_md/limit-order-books
status: read
updated: 2026-10-12
---

# Gould, Porter, Williams, McDonald, Fenn & Howison, "Limit order books" (Quantitative Finance 13(11), 2013)

## What it is
A 34-page survey of limit order books (LOBs): a precise vocabulary for them (section 2), the practical problems of studying them (3), the empirical regularities (4), the models (5) and what is still open (6). It has almost no formulas of its own. Its value for us is the vocabulary, the list of facts our data can be tested against, and section 4.6 on price impact, which is the backbone of the [price-impact](../concepts/price-impact.md) page. Most of its data is more than ten years old, which the authors themselves flag.

## Main results
**Mechanics (section 2–3):**
- **A resting limit order is a free option written to the whole market:** a sell order is a call at its price for as long as it rests (Copeland and Galai, `limit-order-books.md:215` (p. 5)). The same idea as Harris's timing option ([Harris](harris-trading-and-exchanges.md)).
- **How an order changes the best prices** (`limit-order-books.md:169-181` (p. 4)): an order inside the spread sets a new best; a marketable order trades at the resting orders' prices, walking the book until filled or out of eligible prices.
- **Priority rules** (`limit-order-books.md:251-261` (p. 6)):
  - **Price-time** (most common) rewards arriving early.
  - **Pro-rata** splits a fill by share of the queue, which makes quoting more than you want to trade a way to gain priority.
  - **Price-size** favours the largest order.
- **The tick size sets the price of priority** (`limit-order-books.md:319` (p. 8)). With a tiny tick, stepping one tick in front of a queue is almost free, so queues stay thin and best prices flicker. With a large tick, queues are long and stepping in front costs a full tick.
- **The visible book is not the intent to trade** (`limit-order-books.md:265-277` (p. 6–7)). Snapshots are sparse, and hidden, iceberg and dark orders exist. Some platforms only send updates at a fixed frequency, so all activity between refreshes is invisible.
- **Fleeting orders make best prices noisy** (`limit-order-books.md:313` (p. 8)): orders placed and cancelled at once move `b(t)` and `a(t)` without any trade. That is *microstructure noise*, not a price change.
- **Statistics on LOB data are fragile** (`limit-order-books.md:343` (p. 9); `limit-order-books.md:353` (p. 9)). Independence and stationarity rarely hold. With long memory the effective sample is much smaller than the number of points, and estimators converge slowly or to arbitrary values. Regime switching makes Hurst estimators report long memory where there is none (`limit-order-books.md:628` (p. 18)).

**Empirical regularities (section 4):**
- **Market orders rarely walk the book:** only 0.1% did on the Stockholm exchange (`limit-order-books.md:419` (p. 11)).
- **Most limit orders are cancelled, not filled:** 70–80% in older data, more than 99.9% in recent FX data (`limit-order-books.md:431-433` (p. 11)).
- **The mean depth profile is hump-shaped:** depth grows over the first few levels away from the best, then falls (`limit-order-books.md:447` (p. 12)).
- **Order placement reacts to the book** (`limit-order-books.md:462-464` (p. 12)):
  - More orders arrive inside the spread when the spread is wide.
  - More arrive inside the spread when the queue at the best on that side is long, read as traders buying priority with a better price.
- **Cancellations follow priority** (`limit-order-books.md:494` (p. 14)): an order is more likely to be cancelled when a new order takes priority over it.
- **Trades are read as news** (`limit-order-books.md:496` (p. 14)): after a sell market order lowers the bid, the ask tends to fall too.
- **The spread and volatility move together,** weakly at fixed time intervals and strongly trade by trade (`limit-order-books.md:502` (p. 14)).

**Impact (section 4.6):**
- **Definitions** (`limit-order-books.md:510-525` (p. 14–15)): *price impact* is the change in the best prices caused by an action; *market impact* is its effect on the whole book. Both have an *instantaneous* part (the volume removed) and a *permanent* part (how other traders change their behaviour afterwards).
- **Permanent impact can't be measured exactly,** because the counterfactual (the same market without the order) is never observed (`limit-order-books.md:549` (p. 15)).
- **Order splitting:** a large order is executed as many small ones, hoping liquidity refills between them (`limit-order-books.md:508` (p. 14)).
- **Instantaneous impact is concave in size** (`limit-order-books.md:551-553` (p. 15)):
  - Hasbrouck found it concave on the NYSE.
  - Lillo et al. fitted `|ω|^α` with α between 0.2 and 0.5 across groups of stocks, without goodness-of-fit tests.
  - Zhou found α ≈ 0.66–0.69 for orders filled on arrival (`limit-order-books.md:572` (p. 16)); Potters and Bouchaud preferred a logarithm (`limit-order-books.md:580` (p. 16)).
- **Impact over an interval against trade imbalance is concave** at short horizons and close to linear at long ones: α ≈ 1/3 at 5 minutes and ≈ 1 at 195 minutes (Plerou et al., `limit-order-books.md:588` (p. 16)).
- **Order-flow imbalance fits better than trade imbalance** (Cont et al. 2011, `limit-order-books.md:590` (p. 16)); see [price impact of book events](price-impact-of-book-events.md).
- **Market impact** (Hautsch and Huang, `limit-order-books.md:592-596` (p. 16–17)):
  - A market order's impact is about four times a limit order's of the same size.
  - Limit orders at the best have no immediate impact but a significant permanent one; orders inside the spread have mostly instantaneous impact.

**Stylized facts (section 4.7):**
- **Heavy-tailed returns,** with tails close to a power law of exponent 3 at short timescales, becoming closer to normal over longer ones (`limit-order-books.md:608` (p. 17)).
- **Volatility clustering:** absolute returns have long memory (`limit-order-books.md:610-614` (p. 17–18)).
- **Order signs have long memory** (buys follow buys), largely from order splitting (`limit-order-books.md:616` (p. 18)).
- **Returns have no autocorrelation except a weakly negative one at the shortest lags,** and that window has shrunk over the years, from 20 minutes in old S&P data to none beyond 20 seconds in 2010 NYSE data (`limit-order-books.md:618-620` (p. 18)).
- **Why signs persist but prices don't** (`limit-order-books.md:622` (p. 18)): when market orders are predictable, the opposite queue is deep, so each one moves the price less (Lillo and Farmer).

**Models (section 5):**
- **Cut-off strategies:** take when the spread is below a threshold, otherwise post (`limit-order-books.md:648` (p. 19)). Parlour's version compares the estimated fill probability with a threshold (`limit-order-books.md:656` (p. 19)).
- **Informed traders take when the mispricing is large and post when it is small** (Roşu, `limit-order-books.md:670` (p. 20)), and one informed trader's orders don't fully move the price, so others with the same information can follow.
- **Optimal execution:** under a random walk, split a large order into equal pieces over time (Bertsimas and Lo, `limit-order-books.md:676` (p. 20)). With an exponentially recovering book, the optimum is a large first trade, small steady ones, then a large last one (Alfonsi et al., `limit-order-books.md:684` (p. 21)).
- **Zero-intelligence models** (random order flow, no strategy) predict the mean spread across stocks well (slope 0.99 ± 0.10) but not heavy tails (`limit-order-books.md:714` (p. 22)). Cont et al. (2010) and Cont and de Larrard (2011) are the queue-based versions (`limit-order-books.md:716` (p. 22); `limit-order-books.md:726` (p. 23)), which the [queue-reactive model](queue-reactive-model.md) extends.
- **Parameters that drift over time can produce the stylized facts on their own** (Challet and Stinchcombe, `limit-order-books.md:754` (p. 24)).

## Assumptions against the Arena
- **Real exchanges with human and algorithmic traders.** Prosperity's market is a set of programmed bots: in the survey's terms a zero-intelligence or agent-based market. Which stylized facts hold there is an empirical question for each product, not a given *(inferred)*.
- **Measured on Prosperity 3 round 1 (2026-10-12),** all three days:
  - **Trades print against the same tick's book:** 96–97% of the market trades at tick `t` are at a price in book `t`, against 44–68% for book `t − 1`. So book `t` is the book those trades arrived to.
  - **Mid changes are strongly mean-reverting at one tick:** lag-1 autocorrelation −0.48 (Kelp), −0.50 (Resin), −0.17 (Squid Ink) in P3 round 1, far stronger than the survey's "weakly negative".
  - **Heavy tails differ by product:** excess kurtosis 0.4 (Resin), 2.4 (Kelp), 504 (Squid Ink).
  - These are measured on the snapshots, ticks 100 time units apart. `arena.diagnose` reproduces the autocorrelations (column `mid AC1`); the share of trades on book `t` and the kurtosis were a one-off script.
- **Price-time priority** is what our resting mode assumes (`arena/engine.py` docstring). Pro-rata would reward quoting more than we want to trade. The Arena's rule is unknown ([queue position](../concepts/queue-position-and-fills.md)).
- **Tick size:** Prosperity ticks are 1 on prices of 2,000–10,000, a large tick relative to the spread, so queues matter and stepping in front costs a full tick *(inferred)*.

## In our notation
| Paper | Ours |
|---|---|
| `b(t)`, `a(t)`, `m(t)`, `s(t)` | `best_bid`, `best_ask`, mid, spread in `_timeline.csv` |
| depth `n^b(p, t)`, `n^a(p, t)` (bid depth negative) | `Book.bids`, `Book.asks` volumes (both positive) in `arena/model.py` |
| tick size π, lot size σ | 1 price unit, 1 lot in Prosperity |
| market order / limit order | a take (IOC in resting mode) / a quote |
| instantaneous price impact | the volume our take removes from this tick's book |
| permanent price impact | not modelled: the next tick's book is the recorded one |
| trade imbalance `Ω^ω(T)` | signed market-trade volume over a window |

## Traps
- **OCR replaced symbols:** Φ (impact functions) appears as `+` and Ω (trade imbalance) as `0`, e.g. `+m(|ωx|)` and `0ω(T)` (`limit-order-books.md:553` (p. 15), `limit-order-books.md:584-588` (p. 16)). The PDF's own text layer has the same substitution, so pdftotext doesn't help; read the page image.
- **Typo in the paper itself:** Gabaix et al.'s result is printed as "the mean mid-price logarithmic return followed the relationship `Ω^ω(T)^0.5`" with the proportionality sign missing (`limit-order-books.md:588` (p. 16)). Eq. (19) uses `α` though its legend defines `μ`, `λ` and `ν` (`limit-order-books.md:565-567` (p. 16)).
- **Table 1 is garbled** (`limit-order-books.md:197-209` (p. 5)): every number is split across cells.
- **Sign convention:** the paper's bid depths are negative and its sizes negative for buys. Ours are positive volumes and signed quantities.
- **Equations (11) and the text around it are out of order** (`limit-order-books.md:375-379` (p. 10)).
- **Old data:** most findings come from before 2010, and the authors warn that markets have changed since (`limit-order-books.md:767` (p. 24)).

## Read depth
- **Read:** all seven sections. Appendix A (the table of empirical studies) and the references were not read.
- **Formulas:** none are used by the wiki. The impact exponents are reported fits, and the definitions are standard.
- **Checked against the PDF (page image):** p. 16, the impact paragraphs (exponents 0.66 and 0.69, α from 1/3 to 1, the Gabaix typo). The other pages were located with `pdfpage.py`.

## Cited by
[price-impact](../concepts/price-impact.md), [queue-position-and-fills](../concepts/queue-position-and-fills.md).
