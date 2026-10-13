---
title: Harris, "Trading and Exchanges" (book, 2003)
type: source
repo: literature_md/harris-trading-and-exchanges
status: partly-read
updated: 2026-10-12
---

# Harris, *Trading and Exchanges: Market Microstructure for Practitioners* (Oxford University Press, 2003; our copy is a draft, 656 PDF pages)

## What it is
The practitioners' textbook of market microstructure: who trades, why, and how each kind of trader makes or loses money. It is prose with almost no formulas, organised by trader type. Six chapters were read for the questions the wiki has (Phase 2, 2026-10-12): informed traders (10), order anticipators (11), bluffers (12), dealers (13), bid/ask spreads (14) and arbitrageurs (17). Their value for us is a vocabulary for what the bots and rivals in a market are doing, and a few tests we can run on our own fills.

## Main results
**Dealers, ch. 13:**
- A dealer's realized spread, what is actually earned per round trip, is usually smaller than the quoted spread, and negative when prices move against the inventory (`harris-trading-and-exchanges.md:6544` (p. 293)).
- Dealers quote both sides but **price aggressively only the side they want to trade** (`harris-trading-and-exchanges.md:6546` (p. 293)).
- **Controlling inventory:** move *both* quotes against the inventory, change the *sizes* (to sell down: larger ask size, smaller bid size), take another trader's quote when impatient (a negative realized spread), or hedge in a correlated instrument (Table 13-2, `harris-trading-and-exchanges.md:6642-6654` (p. 297–298)).
- **Two inventory risks:**
  - *Diversifiable* risk is price moves unrelated to the inventory; it is benign on average.
  - *Adverse selection* comes from informed traders, and **makes the dealer's inventory imbalance inversely correlated with future price changes** (`harris-trading-and-exchanges.md:6689` (p. 299)).
- **The adverse-selection spread component:** quote the ask at the value estimate *given that the next trader is a buyer*, and the bid *given a seller*. The component grows with trade size (`harris-trading-and-exchanges.md:6768` (p. 302)).
- **Poorly informed dealers (scalpers) must rebalance fast and earn small realized spreads.** Dealers who know fundamental value can hold positions longer (`harris-trading-and-exchanges.md:6863` (p. 306)).
- **Bluff-proof quoting:** with counterparties you can't identify, move your prices "at the same rate per quantity traded", whether buying or selling, for large or small, fast or slow orders (`harris-trading-and-exchanges.md:6891` (p. 307)).

**Bid/ask spreads, ch. 14:**
- **Two components:**
  - The *transaction-cost* component is transitory; it causes bid-ask bounce, and the price reverts.
  - The *adverse-selection* component is permanent; the price does not revert (`harris-trading-and-exchanges.md:6984-6994` (p. 312–313)).
  - Econometric decompositions find adverse selection the larger part in most markets.
  - The Glosten–Milgrom theorem: the adverse-selection component is the pricing error × the probability that the trader is informed, which equals the expected loss to informed traders per trade (`harris-trading-and-exchanges.md:7000` (p. 313)).
- **Uninformed traders lose whichever order type they use** (`harris-trading-and-exchanges.md:7058` (p. 316)):
  - With limit orders, they get filled when wrong and missed when right.
  - With market orders, they pay a spread widened by adverse selection.
- **The timing option:** a resting quote gives faster traders the option to trade against it after news, so a stale quote is "picked off" (`harris-trading-and-exchanges.md:7140` (p. 320)).
  - The equilibrium spread is the cost of managing orders plus twice the timing option's value (`harris-trading-and-exchanges.md:7146` (p. 320)).
  - It is wider when cancelling is slow and when the instrument is volatile.
- **Spread determinants** (Table 14-2): information asymmetry (great), time to cancel (high), volatility (high), order-management cost and value of time (moderate), risk aversion (low).

**Order anticipators, ch. 11:**
- **Quote matching ("penny jumping")** (`harris-trading-and-exchanges.md:5889` (p. 261)):
  - Post one tick in front of a large passive order on the same side.
  - If the price moves your way you gain fully; if not, you sell back to the large order at a one-tick loss. That is an option-like payoff taken from the passive trader.
- **Trapping quote matchers** (`harris-trading-and-exchanges.md:5919` (p. 263)): a large trader baits with a big order, sells into the matcher who stepped in front, and cancels the bait. The matcher is left holding the position, with no backstop.
- **Defences:** time precedence plus a large tick makes stepping in front costly (`harris-trading-and-exchanges.md:5933` (p. 263)).
- Front runners, sentiment-oriented technical traders and squeezers are "parasitic". They profit only from others' orders and drive liquidity away.

**Bluffers, ch. 12:**
- **The bluff:** a price manipulator trades to make others believe they are informed, then trades against the momentum traders and liquidity suppliers who follow.
- **The bluffing condition** (`harris-trading-and-exchanges.md:6369-6381` (p. 283–284)): a bluff pays when buys and sells have *different* price impact per unit traded. If buys move the price more, buy first and sell later.
- **The defence for a liquidity supplier:** equal and opposite impact per unit, independent of order size, speed and sequence.
- The traders most exposed are momentum traders and anyone who sets prices from the order flow they see (`harris-trading-and-exchanges.md:6438` (p. 287)).

**Informed traders, ch. 10:**
- **Trade aggressively when the edge will soon be common knowledge or many share it; trade slowly ("stealth trading") when it won't** (`harris-trading-and-exchanges.md:5373-5387` (p. 238–239)).
- There are four kinds: value traders, news traders, information-oriented technical traders and arbitrageurs.
- Informed profits come only from utilitarian (uninformed) traders.
- "The most common mistake informed traders make is to trade when they have no comparative advantage." Past performance is a noisy guide to whether one has it (`harris-trading-and-exchanges.md:5773` (p. 256)).

**Arbitrageurs, ch. 17:**
- **Pure versus speculative arbitrage:** in a pure arbitrage the basis must revert; in a speculative one (pairs, statistical arbitrage) it may be non-stationary and never revert (`harris-trading-and-exchanges.md:8294` (p. 369)).
- Pairs trading fails when the gap comes from an instrument-specific change: Ford rises on SUV sales, and the GM–Ford spread never closes (`harris-trading-and-exchanges.md:8353` (p. 371)).
- **Four risks:** implementation (worse fills than planned), basis, model, and carrying cost.
  - "The most common mistake that arbitrageurs make is to incorrectly identify a change in the basis as an arbitrage opportunity" (`harris-trading-and-exchanges.md:8574` (p. 381)).
  - Slow convergence turns a correct trade into a loss through carrying costs (`harris-trading-and-exchanges.md:8667` (p. 385)).
- **Competition narrows arbitrage spreads to the costs of the most efficient arbitrageur** (`harris-trading-and-exchanges.md:8801` (p. 391)). Where the relation is easy to see, the winners are the fastest; where it is hard, the best analysts.

## Assumptions against the Arena
- **Human dealers and real investors.** In Prosperity the "dealers" are a market-making bot, and the "informed traders" are bots whose rules may be discoverable ([informed counterparties](../concepts/informed-counterparties.md)). Harris's categories still apply, but the motives are programmed.
- **Our template is a quote matcher.** It quotes one tick inside the best book quote (`bots/template.py:203-235`), with the bot's large "wall" behind it as the backstop. That is safe while the wall stays. In a shared market (`--vs`), a rival can use Harris's trap: bait with size, sell into us, cancel. *(Inferred.)*
- **Timing option and resting orders:** in Prosperity orders live one tick, so no quote goes stale. In the Arena, if orders rest and rivals react faster, our resting quotes give away the option ([queue position](../concepts/queue-position-and-fills.md), [shared market](../concepts/shared-market-and-adversaries.md)).
- **Bluffing needs a counterparty that reacts to flow.** Our current `fair` (mid or wall mid) does not react to trades, so it can't be bluffed that way. A flow- or imbalance-driven fair could be ([book imbalance](../concepts/book-imbalance-and-micro-price.md)).

## In our notation
| Harris | Ours |
|---|---|
| realized spread | markout of a round trip; `arena/analysis.py` markouts at 1–N ticks |
| inventory imbalance inversely correlated with future price changes | corr(`position`, future change in `mark`) per product in `_timeline.csv` |
| quote matching | `make` quoting `best_bid + 1` / `best_ask − 1` (`bots/template.py:203-235`) |
| transitory vs permanent spread component | short-horizon markout reversal (transitory) vs persistent markout (permanent) |
| arbitrage basis | basket price − Σ weights × components |

## Traps
- **This is the 2003 draft.** Page numbers and some wording may differ from the printed edition; cite PDF pages.
- **OCR:** the Harris markdown has few formulas but many mangled boxes and tables. For example, Table 14-1 lost its rows (`harris-trading-and-exchanges.md:7066-7076` (p. 317)) and table titles carry stray digits ("TABLE 1313-4"). Box headings ("A Gap in Spreads…") were detected as chapter headings by `meta.json`, so its table of contents is not a chapter list. Use the chapter map below.

## Read depth
Chapter map (PDF pages are the start of each chapter's first section, one-based; markdown lines):

| Ch. | Title | From PDF p. | Lines | Status |
|---|---|---|---|---|
| 1 | Introduction | 16 | 241–390 | mapped |
| 2 | Trading Stories | 24 | 391–747 | mapped |
| 3 | The Trading Industry | 45 | 748–1696 | mapped |
| 4 | Orders and Order Properties | 81 | 1697–2214 | mapped |
| 5 | Market Structures | 102 | 2215–2817 | mapped |
| 6 | Order-driven Markets | 125 | 2818–3465 | mapped |
| 7 | Brokers | 152 | 3466–4312 | mapped |
| 8 | Why People Trade | 191 | 4313–4907 | mapped |
| 9 | Good Markets | 216 | 4908–5302 | mapped |
| 10 | Informed Traders and Market Efficiency | 235 | 5303–5820 | **partly read** (10.4, 10.5 headings, 10.6.5, 10.7–10.8) |
| 11 | Order Anticipators | 258 | 5821–6136 | **read** |
| 12 | Bluffers and Market Manipulation | 272 | 6137–6503 | **read** (12.2.1 examples skimmed) |
| 13 | Dealers | 292 | 6504–6945 | **read** |
| 14 | Bid/Ask Spreads | 310 | 6946–7474 | **read** to 14.4; 14.5–14.6 skimmed; appendix not read |
| 15 | Block Traders | 335 | 7475–7859 | mapped |
| 16 | Value Traders | 351 | 7860–8085 | mapped |
| 17 | Arbitrageurs | 361 | 8086–8876 | **partly read** (17.2, 17.3.2, 17.4, 17.8–17.10) |
| 18 | Buy-side Traders | 394 | 8877–9187 | mapped |
| 19 | Liquidity | 408 | 9188–9526 | mapped |
| 20 | Volatility | 424 | 9527–9727 | mapped |
| 21 | Liquidity and Transaction Cost Measurement | 434 | 9728–10192 | mapped |
| 22 | Performance Evaluation and Prediction | 456 | 10193–11154 | mapped (the performance-prediction problem; candidate for [validation](../concepts/validation-and-overfitting.md)) |
| 23 | Index and Portfolio Markets | 497 | 11155–11368 | mapped |
| 24 | Specialists | 508 | 11369–11792 | mapped |
| 25 | Internalization, Preferencing, and Crossing | 527 | 11793–12009 | mapped |
| 26 | Competition Within and Among Markets | 537 | 12010–12473 | mapped |
| 27 | Floor Versus Automated Trading Systems | 557 | 12474–12732 | mapped |
| 28 | Bubbles, Crashes, and Circuit Breakers | 569 | 12733–13350 | mapped |
| 29 | Insider Trading | 597 | 13351–13699 | mapped |
| — | Bibliography by chapter, index | 614– | 13700–13903 | mapped |

No formulas were taken from this book, so nothing needed checking against the PDF. The claims above are Harris's arguments, not measurements.

## Cited by
[informed-counterparties](../concepts/informed-counterparties.md), [shared-market-and-adversaries](../concepts/shared-market-and-adversaries.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [baskets-and-fixed-sums](../concepts/baskets-and-fixed-sums.md).
