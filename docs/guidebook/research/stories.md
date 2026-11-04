# Stories for the guidebook, ranked by teaching value

I found 26 stories, all checked against the repo text. Paths are relative to `/Users/jakubkucera/Documents/qminers_arena/` unless they start with `~`. A "their claim" tag means the figure comes from a team's own write-up and our engine did not reproduce it.

---

### 1. The same strategy, the same days, a different fill model, the opposite conclusion
On P3 Kelp the grid picks `make_edge` 1 over 0.5. That gain holds on four days the grid never saw, by +2.2k to +2.8k each, under the optimistic fill rule (`all`). Under the strict rule (`worse`) it reverses, at −1.2k to −2.1k a day. A full-grid permutation test (p 0.55) says Kelp's choice of edge comes from the fill model, not the data. The result looks robust (out of sample, it passes the SPA test) but rests entirely on one assumption about who gets filled.
- **Concept:** fill-model optimism; a backtest's hidden assumptions
- **Source:** `references/wiki/contradictions.md` row 18; `IDEAS.md:214`, `IDEAS.md:234`

### 2. Backtest +2,415, live +436
A Prosperity 4 team, Kayzerjali, measured one product over the same 100k-timestamp window: +2,415 in the backtester, +436 on the live platform (their claim). They rebuilt their loop so the live result was the only objective, with one change per upload and a written stopping rule. Frankfurt Hedgehogs said the same thing of the open-source backtester they used (Jasper's): it "could not accurately model potential fill probabilities after inserting liquidity" *(corrected 2026-11-04 against the README)*.
- **Concept:** passive fills can't be simulated from a replay; the live system is the oracle
- **Source:** `references/online-snapshots/Kayzerjali_Prosperity2026/run_cycle.md:4-5`; `references/prosperity3-frankfurt-hedgehogs/README.md:900`; `references/wiki/contradictions.md` row 10

### 3. The playbook that failed in an agent market (ABIDES)
Every Prosperity-tuned default was taken into ABIDES, an independent simulator with informed and momentum traders.
- The template lost −21,798 under optimistic fills and −362,428 with resting orders. No cell of a 36-cell grid made money resting, and doing nothing beat all of them.
- Trades moved the price: R(50) was +1.31 ticks, against about 0 on Prosperity. Passive fills against the last move lost money on every day.
- The shuffle test: on copies of the days with the events in random order, the same bot made **+4.54M**. On Prosperity's Kelp, real and shuffled were 27,390 against 27,326.

The order of events is the adverse selection.
- **Concept:** adverse selection; zero-intelligence markets against informed ones; a test for whether your edge is real
- **Source:** `IDEAS.md:238`

### 4. Quoting 100 away on an empty book side: 18.6k a day
In P4 round 1, one side of the book was empty on about 7.6% of ticks. A hidden taker would sometimes lift a quote placed about 100 from fair on that side. Baguette Fromage estimated about 18.6k a day on Osmium from it (their claim). The admins later said the generator had **randomly deleted 20% of the bots' orders**. Our engine can't value this at all: no recorded trade ever printed outside the visible book, so a replay fills nothing. Only a live probe can test it.
- **Concept:** hidden liquidity; generator artefacts; edges a backtest can't see
- **Source:** `references/prosperity4-baguette-fromage/README.md:350-365`; `references/prosperity4-du-trading/README.md:77`; `IDEAS.md:266`; `references/wiki/concepts/hidden-takers-and-empty-sides.md:13-15`

### 5. Second place, an unhedged delta, 26th place
Linear Utility (Prosperity 2) were 2nd going into the coconut-coupon round. They traded implied vol around about 16% but could not hedge fully: a delta of 0.53 on 600 coupons against a 300 limit on the underlying. They chose to "run the variance", lost on the delta, made only 145k and fell to 26th. Their verdict: "we were already second place and thus should've went for lower var."
- **Concept:** risk against rank; protecting a lead; delta hedging
- **Source:** `references/prosperity2-linear-utility/README.md:162-170`

### 6. Halving the stake kept first place (Qminers 2024)
Before the in-person final of Qminers' own 2024 hackathon (scores reset, a shorter horizon), the winner simulated the final's 20 competitors with correlated models of varying quality and risk appetite, and chose the Kelly fraction that won most often. Leading after two of three rounds, and finding that the third round's data came from just after covid, he halved the stake so as not to lose the lead if others' models coped better. It was "a minor mistake": the model did best in that period, and at full risk he estimates about 143k against the 107k he finished with (the 107k from the screenshots, per the wiki), but first place held. *(Corrected 2026-11-04: an earlier version read "does not manage to beat all" as losing in his simulation; the README means beating all the other scores combined, as he had in stage one.)* Meanwhile two finalists fell from 1,000 to under 40, and another climbed from about 50 to 69k to finish 2nd.
- **Concept:** optimising for rank, not for expected PnL; variance helps the trailing team
- **Source:** `references/qminers-hackathon-2024/README.md:45-63`; `references/wiki/concepts/risk-and-protecting-a-lead.md:21-22`

### 7. A relative hedge sized by VaR (Frankfurt Hedgehogs)
Frankfurt Hedgehogs (Prosperity 3) held a 200k lead. They no longer believed in their option mean-reversion strategy, which had lost about 50k the round before. They kept some of it anyway, because the teams behind them traded only that: if it paid, those teams would catch up. They sized it so its 95% VaR (about 50k) was 25% of the lead. In the last round, about 190k ahead, they half-hedged the baskets.
- **Concept:** hedging against competitors rather than against the market; VaR sizing
- **Source:** `references/prosperity3-frankfurt-hedgehogs/README.md:616`, `:759`

### 8. Olivia, the informed trader
On P3's Squid Ink one anonymous bot bought exactly 15 lots at the daily low and sold at the daily high. Frankfurt detected her from trade size and running extremes before names were ever revealed, and "positioned accordingly" *(corrected 2026-11-04: an earlier version said they followed her to the position limit, which the README doesn't say)*. Our own measurement: all 19 of her trades over three days were followed by a move her way at 100, 1,000 and 5,000 ticks.
- **Concept:** informed flow; reading counterparties; a signal found by aggregating trades
- **Source:** `references/prosperity3-frankfurt-hedgehogs/README.md:270-319`; `IDEAS.md:190`

### 9. The Marks that weren't Olivia
In P4 round 4 several teams each named a different "informed" Mark (67, 14, 55, 22). Ryan Challman fitted per-trader weights. They failed on the held-out day, and switching them off recovered about $15.8k. Our leave-one-day-out test found no Mark that kept its sign on all three days, and names chosen on two days lost 31k on the third.
- **Concept:** overfitting to noise; leave-one-day-out validation
- **Source:** `references/prosperity4-ryan-challman/README.md:89-91`; `references/wiki/contradictions.md` row 3

### 10. "The result was a disaster": fit on two days, test on the third
In P4 round 5 (50 products), Baguette Fromage's scanners found "absurdly profitable" cross-product relationships. When they forced themselves to fit on two days and test on the third, the relationships collapsed: residuals non-stationary, hedge ratios flipping sign. Separately, one product-day (ROBOT_DISHES, day 4) makes 437k of their Robots' backtest, yet live the Robots finished about −4.3k.
- **Concept:** data mining and multiple testing; one-day concentration
- **Source:** `references/prosperity4-baguette-fromage/README.md:880-902`, `:1041`; `references/wiki/sources/prosperity4-baguette-fromage.md` (Robots row)

### 11. 96% of a product's profit on one day: size it at 0.06
Ryan Challman's ROBOT_DISHES had a lag-1 autocorrelation of −0.001, −0.004 and **−0.290** on its three days, and made $389k on day 4 against $11k and $4k. Rather than gate on day 4's regime, they cut the weight from 0.12 to 0.06, as a hedge against the test day not looking like day 4.
- **Concept:** regime dependence; sizing a fragile edge (Kelly shading)
- **Source:** `references/prosperity4-ryan-challman/README.md:115-141`

### 12. The "flaw" that was the alpha
Ryan Challman's voucher fair, a cumulative mean, lagged the live mid. They "fixed" it with a Black–Scholes fair and lost about 64,000 per strike on training. Every tighter fair (Black–Scholes, microprice, EWMA, daily reset) collapsed the profitable fills: the lag *was* the edge.
- **Concept:** what a fair value is for; don't fix what you don't understand
- **Source:** `references/prosperity4-ryan-challman/README.md:266`

### 13. smile_window 20 against 5,000 on P2's coconut coupon
On P2 round 4's coconut coupon, our options mode with a 20-tick window lost −266,554: the residual's lag-1 autocorrelation was 0.89, so it drifted rather than reverted. With a 5,000-tick window the same strategy made **+441,929** (worst day +114,476), and the same cell won on each held-out day. One parameter, the timescale of the "fair", turned the biggest loss into the biggest gain.
- **Concept:** mean reversion depends on the horizon; check autocorrelation before fading
- **Source:** `IDEAS.md:264`

### 14. The late-orders rehearsal that lost both uploads (Kestrel Bourse)
A mock round's hidden rule was that orders reach the exchange one step late. In both agent runs the code connecting the bot to the exchange (its ADAPTER) did not count orders still in flight. So each run re-posted every step, hit the 3-order cap and overfilled its position limits: public −4,850 and −283, hidden −3,553 and −489, against a plain market maker's +325. Counting in-flight orders alone, in the second run's bot, moved public from −283 to +142 (its breach penalty 198 → 0) and hidden from −489 to −389 (25 → 0); the rest of the hidden loss was quoting BRAM under `worse` matching, a choice of settings *(corrected 2026-11-04 against `docs/guidebook/book/data/kestrel.csv`)*.
- **Concept:** latency; order state; execution bugs dominate strategy
- **Source:** `python/experiments/mock_round/round3/README.md:10-26`; `IDEAS.md:205`

### 15. A fee hidden in plain sight: 28% of gross (Varde Exchange)
In the fourth rehearsal the portal's rules stated a fee per order placed, not just per lot. Our calibration tool refused to fit (98% off at best), so the session rebuilt the score from the results ZIP by hand. It found the order fee was 28% of the gross, and that our engine filled over twice the portal's volume. The rule behind the gap, that only half of each print reached resting orders, was in the answer key; the session didn't find it *(corrected 2026-11-04)*. The bot still scored €208.77 against the example bot's €80.10.
- **Concept:** transaction costs; calibrating a simulator to the real venue; trusting a refusal
- **Source:** `python/experiments/mock_round/round4/README.md:3-10`, `:30-32`; `IDEAS.md:205`

### 16. Whether taken volume stays gone: −27%
In the first mock round the bot made 42,446 on hidden days when the replay restored the book every step. When the volume it took stayed gone, it made 31,172 (−27%). One engine assumption, nothing in the strategy, was worth a quarter of the score.
- **Concept:** market impact in replays; the limits of backtests
- **Source:** `IDEAS.md:205` ("Whether what we take stays gone")

### 17. Market making on jumpy products with resting orders: −1.48M
With orders living one tick, plain market making on P3/P2 basket legs earned 2.7k to 9.8k. With resting orders, Roses lost −1,477k and Chocolate −539k. The next snapshot jumped through the resting quotes, which filled at their own stale price: 114k units on one day. Roses' wall mid moved more than half the spread on 63% of ticks.
- **Concept:** being picked off; stale quotes; adverse selection from jumps
- **Source:** `IDEAS.md:180`

### 18. Kelp's long position is the flow, not a bias
The template sat long on Kelp, which suggests an inventory skew is needed. Mirroring each day (prices reflected, buyers swapped for sellers) gave exactly the negative position and the same PnL. So the bot was symmetric: only 34–36% of Kelp's touch trades are buys. The flow was uninformed (position against the future price change: −0.10 to +0.18), and skew cost PnL at every step: 18,698 → 15,893 under `all`, 14,530 → 9,514 under `worse`.
- **Concept:** inventory risk is only a cost when the flow is informed; a symmetry test
- **Source:** `IDEAS.md:166`

### 19. The skew a famous model prescribes, and why it lost
DTU added an Avellaneda–Stoikov inventory skew on P4 Osmium. In their backtest it cost 16,593 (their claim), and they reverted to a fixed anchor. Our grid agreed: skew 0 is best (113.8k, against 93.4k at skew 8). On a pegged, mean-reverting product, a skew that reacts to noise in the mid costs money.
- **Concept:** textbook models and their premises; inventory skew
- **Source:** `references/prosperity4-dtu-quant-lab/README.md:91`; `references/wiki/contradictions.md` row 1

### 20. The fixed anchor that kept buying (DTU round 3)
DTU's static market maker worked on Osmium's peg, so they reused it on Hydrogel. Their handed-out data was about 99% "pinned", but the live day was noisy. Hydrogel drifted 70 ticks in one session, the fixed fair value kept buying into the fall, and the round made +3,686 (rank 2,232).
- **Concept:** regime change; training data unlike the scored data
- **Source:** `references/prosperity4-dtu-quant-lab/docs/journey.md:14-16`; `references/prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:261-296`

### 21. A rival's far order poisons your fair value
Against the other teams' bots with resting orders, the template lost −377k on Osmium. At tick 2,400 a rival's 40-lot bid at 9,906 was larger than the real 23-lot wall at 9,991. The "largest level" rule then put fair at 9,957 against a true 10,001.5, and the bot sold into real bids. A deliberate spoofer 10 ticks behind the best did the same to Kelp (16.8k → −2.1k). A rule using the first level of at least 15 lots (`sized_mid`) was immune at no cost.
- **Concept:** spoofing; robust estimators; shared books
- **Source:** `IDEAS.md:165`, `IDEAS.md:207`

### 22. A second copy halves your market making
Alone, the template makes 72,674 on P3 round 1 (81,292 before its 18 Oct `sized_mid` change; `docs/guidebook/book/data/copies.csv`). Against one copy of itself, each copy makes about 41k; against two copies, about 28k each: each keeps about 57% of the lone income with one copy, so a copy takes a little under half. On Osmium the spread is a fixed pie of 55–62k a round that the bots split. Any second bot at our price halves the market-making income.
- **Concept:** competition among market makers; the spread as a shared rent
- **Source:** `IDEAS.md:164`, `IDEAS.md:165`

### 23. Last year's data predicted this year's prices (R² 0.99)
Puerto Vallarta made 1.2M in one Prosperity 2 round. Hunting for how, Linear Utility regressed this year's products on the *previous* year's public data. Last year's diving gear ×3 predicted roses with R² 0.99, and last year's coconuts predicted coconuts (beta 1.25). They then solved the rest of the competition with a dynamic program on known future prices ("fair game", they said).

In Prosperity 3, Frankfurt found the bots matched the previous year's to over 95%, so teams could hard-code trades at known timestamps. They reported it, and IMC banned hard-coding and re-ran the rounds. In P3, CMU Physics found the website's "sample data" was the first 1,000 timestamps of the live day.
- **Concept:** data leakage; generator reuse; the ethics of exploiting it
- **Source:** `references/prosperity2-linear-utility/README.md:176-182`; `references/prosperity3-frankfurt-hedgehogs/README.md:967-978`; `references/online-snapshots/chrispyroberts_imc-prosperity-3.README.md:70`

### 24. A logger that wiped the bot's memory: 7th to 241st
CMU Physics' visualizer logging pushed the submission past 100 MB of memory. That restarted the AWS Lambda and wiped all in-memory state, which broke the rolling windows behind their basket and Volcanic Rock trades. The trader "effectively bought and sold these products randomly." Separately, Alpha Animals reached 2nd place because a bug left them short the underlying at the limit all day, and it happened to pay.
- **Concept:** operational risk; state management; rank is partly luck
- **Source:** `references/online-snapshots/chrispyroberts_imc-prosperity-3.README.md:234`; `references/prosperity3-alpha-animals/README.md:135`

### 25. The red herring: paying for more competition
P4 round 2 let teams bid for "extra market access": about 20% more quotes, but not more trades. Baguette Fromage reasoned that more quotes would tighten spreads and fill the empty sides their hidden-taker edge needed, so they bid zero. The median bid was 50: most teams paid to make their own market making worse.
- **Concept:** market structure; competition compresses spreads
- **Source:** `references/prosperity4-baguette-fromage/README.md:500-519`

### 26. The DJ deck and the frozen exchange (UChicago 2026)
The eventual winners click-traded prediction markets on a physical DJ deck. In round 6 the exchange froze while they held large positions, news hit, and they lost about $200k in seconds: a top-5 round became 35th. In the final round they computed they needed only top 11 of 41 and stopped the bot after about 8 minutes, because rivals were manipulating books in the last minutes.
- **Concept:** tail risk; operational risk; stopping when the lead is safe
- **Source:** `references/uchicago-trading-2026/README.md:197-203`, `:227-233`

---

### Runners-up if you need replacements
- **Orchids arbitrage leaked on Discord.** Linear Utility found a huge local taker (60k in a fifth of a day). A Discord leak let everyone copy it, and they fell to 17th. Concept: an edge's value depends on its exclusivity. Source: `references/prosperity2-linear-utility/README.md:118-137`.
- **Crowding in a shared market.** AlgoTrade's winners, Negative Eevee: other teams' cross-exchange arbitrage "became much worse around round 2," when the winners' own prototypes went live. Source: `references/wiki/sources/algotrade2026-negative-eevee.md` (`README.md:23`).
- **Hidden depth, a misreading.** The team reported 53.9% of trades on one AlgoTrade exchange (ZSE) printing outside the top 3 levels, from a 3,115-print sample; on all 1,411,648 committed prints it is 34.0% outside the last snapshot's levels and 5.7% outside both it and the next (re-run 2026-11-04, `docs/guidebook/book/data/hidden_depth.csv`). But the API sent five levels a side (`references/algotrade2026-pitfa19/.firecrawl/algotrade-api.md:518-546`) and only the recording kept three (`analysis/mm_analysis.md:48-49`): the prints are outside what was recorded, not depth hidden from the market. Source: `references/algotrade2026-pitfa19/analysis/mm_analysis.md:43`, `:153`.
- **Sandbagging.** The Qminers 2024 winner capped his qualification profit at 1/10 so rivals wouldn't try harder. Source: `references/qminers-hackathon-2024/README.md:35`.
- **The bookmaker knows best.** In Qminers 2025 only models built on the bookmaker's own probabilities beat it; adding features cost logistic regression about 45% of its bankroll. Source: `references/qminers-hackathon-2025/README.md:43-45`.
- **The stress test.** A trend over the day took P3 round 1 from 81.3k to 19.6k/14.3k: level bets keep betting on a price that has left. Source: `IDEAS.md:215`.
- **Days reused across rounds.** P3 reuses days across rounds, so most of the older products' round-3 PnL was in sample. Source: `docs/TODO_DONE.md:499-512`.
- **A simulator bug.** In an audit, our bot running inside ABIDES had traded up to 3× its position limit and read its own quotes as the market. Fixing that changed its loss from −617k to −230k. Source: `~/Documents/qminers_arena_audit/audit_round4.md:205`; `IDEAS.md:256`.

### Concepts covered
- **Adverse selection:** 3, 17, 21
- **Fill-model optimism:** 1, 2, 4, 16
- **Overfitting:** 9, 10, 11
- **Risk against rank:** 5, 6, 7, 26
- **Inventory:** 18, 19
- **Mean reversion and regimes:** 13, 20
- **Informed flow:** 8, 9
- **Latency and execution:** 14, 15
- **Hidden liquidity:** 4
- **Competition:** 22, 25
- **Leaks:** 23
- **Operational risk:** 24, 26

Stories 1, 3, 13, 16, 17, 18, 21 and 22 are the repo's own reproducible measurements (each `IDEAS.md` row carries its command). Most of the rest are the teams' own accounts.
