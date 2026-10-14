---
title: How the organisers could make the rounds harder
type: concept
updated: 2026-10-14
---

# How the organisers could make the rounds harder

## Summary
The Arena promises a "forgiving" first round and a "sophisticated finale". AI tools are allowed, and in Qminers' 2024 hackathon an LLM baseline beat every team but one. So expect the later rounds to be built so that a generic Prosperity-style bot written by an agent loses.
This page lists the ways a simulator can do that, with the evidence for each, how to spot it on the day and what to prepare now. The likeliest are:
- a reactive simulator scored on seeds we never see;
- a regime that differs between the public and the private run;
- organiser bots that punish the textbook playbook;
- in a shared market, rivals that are mostly agent-written.

Speed is most likely a budget we already meet, not a race (section E).

## What the sources say

**What the Arena says about itself** (`arena-site-snapshot.txt`, read 2026-10-10):
- **The rounds get harder by design.** "Starting with a forgiving market to learn the basics, building up to a sophisticated finale where the best performers will stand out" (`arena-site-snapshot.txt:153`). The weights rise with it: 10/20/30/40% (`ON_THE_DAY.md`, "Known so far").
- **A simulator, not a recording.** It "will simulate a realistic exchange", which "mimics a limit order book, without many real-world operational complexities" (`arena-site-snapshot.txt:151-152`). That argues against network latency, disconnects and multi-venue routing (*inferred*).
- **Four skills, each a lever the organisers can pull:**
  - "Read price action, order flow, and market microstructure" (`arena-site-snapshot.txt:174-175`).
  - Machine learning: "Pattern recognition, prediction models, and adaptive strategies" (`arena-site-snapshot.txt:177`).
  - Game theory: "Anticipate competitors, optimize for edge, manage risk" (`arena-site-snapshot.txt:180-181`).
  - Coding: "Build robust, fast, and reliable execution systems" (`arena-site-snapshot.txt:183-184`).
- **The host** is "a proprietary trading firm ... specializing in algorithmic trading and extreme low-latency engineering" (`arena-site-snapshot.txt:188`).
- **Reruns must reproduce.** There is a public backtest and a private evaluation, and the organisers rerun the top solutions to check them (`ON_THE_DAY.md`, "Known so far"). A rerun that must give the same score means a deterministic evaluation: a replay, or a simulator with a fixed seed. It rules out anything that depends on how fast the bot ran on the wall clock (*inferred*).

**What Qminers did last time** (the 2024 Quant Hackathon, [source](../sources/qminers-hackathon-2024.md)):
- **They ran an LLM baseline, and it came 2nd.** On the qualification leaderboard, `_LLM_BENCHMARK_` scored 25,039, behind the winner's 77,383 and ahead of every other team (3rd: 17,353) (*checked* on `qminers-hackathon-2024/first_stage_scores.png`). So the organisers know what an LLM does with their task. With 2026's agents and the rules allowing AI, the "best performers will stand out" line reads as a target: beat the agent baseline (*inferred*).
- **The final changed the regime and shortened the horizon:**
  - The scores were reset and the horizon cut, "thus introducing more variance" (`qminers-hackathon-2024/README.md:43`).
  - The data was scrambled, and the last round turned out to be just after covid (`qminers-hackathon-2024/README.md:57`).
- **Hard compute limits:** 1 CPU, 5 GB of RAM, and a time-limit status (`qminers-hackathon-2024/COMPETITION_README.md:51`, `qminers-hackathon-2024/COMPETITION_README.md:59`).

**Where LLMs fail at trading** (Optiver's Applied AI team, web summary, [online articles](../sources/online-articles.md)). They tested models on their intern exam, a six-month trader assessment and market-making games:
- **What the models did well:** they priced fair value, named adverse selection and told informed traders from liquidity providers.
- **Where they failed:**
  - updating fair value consistently as signals kept arriving;
  - planning more than one or two steps ahead;
  - maximising EV: they were "overly conservative" and traded too small;
  - acting on what they had spotted: they traded with a known informed counterparty at negative EV;
  - modelling how other participants react: "simplified or optimistic assumptions" rather than adversarial thinking;
  - edge cases around data releases.

An organiser who wants to separate a team from its agent would build a round around exactly these failures.

**What harder rounds looked like elsewhere:**
- **Optiver Ready Trader Go** (web, [online articles](../sources/online-articles.md)): an ETF against its future, a 2 bp taker fee and a 1 bp maker rebate, and at most 10 active orders and 200 lots resting. Amends can only reduce volume. Three breaches cost access to the exchange for the rest of the round: more than 50 order operations in a rolling second, a position over 100 lots, or more than 10 unhedged lots held for over a minute.
- **AlgoTrade 2026:**
  - The guide lists "reactions to market events" as an edge (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:11`).
  - The market maker skews its quotes on its inventory, and noise traders send random market orders (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:144-146`).
  - The score is log-scaled against the round's top profit (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:417`). The settlement method was "not disclosed in advance" (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:430`).
  - Limits were asymmetric, with a cash floor ([submission mechanics](submission-and-scoring-mechanics.md)).
- **Prosperity's later rounds** added:
  - baskets and options ([baskets](baskets-and-fixed-sums.md), [options](options-and-vouchers.md));
  - conversions with tariffs and outside observations ([cross-market](cross-market-and-conversions.md));
  - counterparty names ([informed counterparties](informed-counterparties.md));
  - jumps that snap back ([jumps](jumps-and-snap-back.md));
  - a blind bid for extra market access (`prosperity4-baguette-fromage/Strategies/Phase1.py:254`).
- **A regime that differed on the live day:** DTU's Hydrogel was about 99% pinned on the handed-out days and 100% noisy on the live one (`prosperity4-dtu-quant-lab/round_4/algorithmic/trader.py:261-296`).
- **Teams attacking teams:** in UChicago's shared market, teams bought out one side of a book and posted extreme prices on the other (`uchicago-trading-2026/README.md:187`). In AlgoTrade, the edges others could join late survived, and the ones they couldn't did not (`algotrade2026-negative-eevee/README.md:23`).
- **What "a realistic exchange simulation" usually means:** JPMorgan's open ABIDES simulator, in its reference config RMSC04 (web, [online articles](../sources/online-articles.md)), runs:
  - 1,000 noise agents;
  - 102 value agents, each with a noisy view of a mean-reverting fundamental that has rare large shocks ("megashocks");
  - 12 momentum agents (moving-average crossovers);
  - 2 adaptive market makers.
  
  Every order, ours included, moves the price, and the agents react. Latency there is a configured delay per agent (50 ns of "computation delay"), not measured CPU time.

## Where they disagree
- **Speed:** the host's low-latency identity and "fast ... execution systems" (`arena-site-snapshot.txt:184`, `arena-site-snapshot.txt:188`) point one way. "Without many real-world operational complexities" (`arena-site-snapshot.txt:152`), a Python-only submission and reproducible reruns point the other. The reading that fits all of them: a time budget per call or per run that the bot must meet, not a race decided by microseconds. Probe 8 in `ON_THE_DAY.md` settles it.
- **Shared or not:** unchanged, see [shared market](shared-market-and-adversaries.md). The finale is the likeliest round to be shared, since game theory is one of the four advertised skills (*inferred*).

## What it means for our code
Each entry gives:
- **likelihood:** our judgement, from the evidence above;
- **breaks:** what it does to a Prosperity-style bot, ours and an agent's alike;
- **tell:** how to spot it on the day;
- **prep:** what to build now.

### A. The market reacts to us
- **A1. A reactive simulator scored on seeds we never see** (likelihood: high). Agents respond to every order: a take moves the price and the level refills slowly, and the market maker skews against the flow it receives. The download is one realisation, and the private run is another.
  - Breaks: our engine replays a recording, so it overstates what takes earn and hides impact. A grid tuned to one path overfits it.
  - Tell: probe 17 (own impact); downloaded days whose statistics differ more than a recording's would; docs that mention agents or seeds.
  - Prep: an agent-based day generator in `arena/`, run inside `run_market` so that agents and bots share one book. Gu et al.'s public PyMarketSim already implements the agents below in Python ([spoofability-and-liquidity](../sources/spoofability-and-liquidity.md)); read it first. The agents: [Wang & Wellman](../sources/spoofing-abm.md)'s mean-reverting fundamental with noisy observers (the recipe [ABIDES](../sources/abides-simulator.md) credits), and its seeding rule (one master seed, one generator per agent, `literature_md/abides-simulator/abides-simulator.md:71` (p. 4)). The acceptance test: [Get Real](../sources/lob-simulation-realism.md)'s statistics, compared through `arena.diagnose` against the real download. It needs an OU fundamental with jumps, value agents with noisy views, noise takers, momentum agents and a market maker that skews on its inventory. With it we can measure impact, tune over many seeds instead of one path, and give the mock round (`TODO.md`) data nobody has seen.
  - Evidence (the spec): PyMarketSim's components are the minimal set: a mean-reverting fundamental, private values, zero-intelligence takers that trade when the quote offers enough surplus, geometric arrivals, a ladder market maker, liquidation at the final fundamental ([Mascioli et al.](../sources/pymarketsim.md), `literature_md/pymarketsim/pymarketsim.md:143` (p. 4)).
  - Evidence (a realism check): a calibrated queue-reactive simulator matched a real book's overall time asymmetry (0.052 against 0.054 nats per event) but almost none of the part that depends on event order (0.0006 against 0.018) ([Yeo, Cha & Hwang](../sources/lob-irreversibility.md), `literature_md/lob-irreversibility/lob-irreversibility.md:282` (p. 8)). Matching spreads and depths doesn't prove a generator is right. Also compare the strategy on generated days with the same days shuffled in blocks.
- **A2. A book that is thin next to the position limit** (likelihood: medium–high; it is the user's idea 1, and A1 makes it worse). When the visible depth is a fraction of the limit, our own trades are the price.
  - Breaks: the template's full-limit targets (`level`, `jump`, `copy`) cross up to their edge in a single tick.
  - Tell: the limit against the median depth at the best level per product; probe 17.
  - Prep: execution that works toward a target over several ticks (a maximum per tick, or a share of the visible depth), and `arena.diagnose` printing the limit-to-depth ratio.
- **A3. A market maker that defends itself** (likelihood: medium; AlgoTrade's did). It widens or skews after it is hit.
  - Breaks: `wall_mid` treated as fixed truth, and the template's takes, which make the next quotes worse.
  - Tell: after our take, does the wall move?
  - Prep: comes with A1.

### B. The price process changes
- **B1. A regime shift between the public and the private run, or within a day** (likelihood: high; Qminers' own 2024 final did it).
  - Breaks: fixed anchors, `level` set from the download's mean, and parameters at a grid's best cell ([drift and regime](drift-and-regime-change.md), [validation](validation-and-overfitting.md)).
  - Tell: the private run can't be seen, so assume it; within a day, the rolling volatility and drift.
  - Prep:
    - a stress harness that perturbs Prosperity days and reruns a bot on each: volatility ×2, an added trend, the level shifted mid-day, an inserted jump, the wall removed for a stretch;
    - in the template, a regime guard (fall back to plain market making when the level bet or the volatility leaves its range) and a per-product loss stop. The detector: [Adams & MacKay](../sources/online-changepoint-detection.md)'s run-length posterior on wall-mid changes (Algorithm 1, `literature_md/online-changepoint-detection/online-changepoint-detection.md:103` (p. 3)).
- **B2. Jumps and scheduled events or news** (likelihood: medium; AlgoTrade's market events, ABIDES's megashocks, Prosperity's snap-backs).
  - Breaks: resting quotes get picked off, and mean reversion keeps fading a level that has really moved.
  - Tell: an event field in the state; jumps clustered at fixed times.
  - Prep: an event-study tool that lines up each event with the moves after it, and a template switch that pulls quotes around events.
- **B3. A hidden fundamental seen through noisy signals, settled at the end** (likelihood: medium; the machine-learning skill, and Optiver's belief-updating failure).
  - Breaks: a fair value from the mid, and a fair value that doesn't learn as signals arrive.
  - Tell: an extra numeric feed in the state, or a settlement rule that names a value other than the last mid.
  - Prep: a Kalman-filter `fair` option (mid and signals in, variance out), and an end-of-round rule aware of the settlement. The filter for a mean-reverting value seen with noise is [Wang & Wellman](../sources/spoofing-abm.md)'s (p. 3, checked; mind the OCR slip in the variance step). For a value that jumps and is revealed only by order flow, [Das](../sources/learning-market-maker.md)'s Bayesian market maker; it loses when jumps aren't announced, which the changepoint detector of B1 addresses.
- **B4. Anonymous informed flow** (likelihood: medium–high).
  - Breaks: symmetric quotes at the touch ([informed counterparties](informed-counterparties.md), [price impact](price-impact.md)).
  - Tell: `arena.diagnose`'s `R(50)` above zero, or negative markouts.
  - Prep: the untested `IDEAS.md` row "Posting a side only when the edge beats the expected adverse move", with the spread adapted from a running markout. [Das](../sources/learning-market-maker.md) shows the trade-off: with many noisily informed traders a small widening pays most, with few, profit keeps rising with the spread (`literature_md/learning-market-maker/learning-market-maker.md:215` (p. 11)).
- **B5. Many products with hidden structure** (likelihood: medium): a factor model, an ETF with weights it doesn't publish, lead-lag between products.
  - Breaks: one strategy per product; LLM bots that look for structure by product name.
  - Tell: correlations of returns across products and lags.
  - Prep: a cross-product diagnose (correlations at lags 0–20, regression weights of each product on the others) offline with pandas; the bot only needs the weights.
  - Evidence: on P3's picnic baskets neither the legs nor the basket lead at 1–20 ticks (`IDEAS.md`, "Legs leading the basket"), and in an agent-based ETF a crash in one leg reaches the other leg inverted, through the arbitrageurs ([Shearer et al.](../sources/etf-arbitrage-abm.md)). If plain lagged correlations are too noisy, dynamic time warping is the published next step ([Zhang et al.](../sources/dtw-lead-lag.md), mapped).
- **B6. Scrambled or anonymised data** (likelihood: high; Qminers 2024 did it). There's no story text to hint at the trick, and the names mean nothing.
  - Breaks: an agent matching names to Prosperity ("Resin, so 10,000").
  - Tell: obvious.
  - Prep: none needed. `arena.diagnose` reads the data, not the names. This is where our prep beats a cold agent.

### C. Rules and costs
- **C1. Fees, maker–taker** (likelihood: medium; Ready Trader Go's 2 bp / −1 bp).
  - Breaks: `take_edge` of 0 or 1, and many small takes.
  - Prep: maker and taker fees in the engine (per unit and in bp), and the template's `take_edge` and `clear` counting the fee.
- **C2. Caps on orders and messages** (likelihood: medium; Ready Trader Go cuts access off for the rest of the round).
  - Breaks: cancel-and-resend every tick, and quotes at many levels.
  - Prep: engine options for the most open orders and the most operations per tick, with a penalty mode, and EXECUTION counting its operations (it already keeps unchanged quotes).
- **C3. A fixed latency** (likelihood: medium–low). The bot sees data k ticks old, or its orders reach the book k ticks late.
  - Breaks: one-tick-inside quotes get sniped, and takes find the level gone.
  - Prep: a `--latency N` engine option.
  - Evidence: on a large-tick asset, making pays only while uninformed market orders hit the quotes often enough against the rate of price jumps, and latency lowers it further ([Gao & Wang](../sources/market-making-latency.md), `literature_md/market-making-latency/market-making-latency.md:7` (p. 1)). Both rates are measurable per product (trades at the best; `arena.diagnose`'s jumps).
- **C4. Asymmetric limits, a cash or margin limit, a cost to borrow** (likelihood: medium; AlgoTrade had +2,000 / −200 and a cash floor).
  - Prep: limits per side in `LIMITS` and in the template's `Plan`.
- **C5. How the close is settled** (likelihood: medium): a closing auction, an undisclosed average over a window (AlgoTrade), or a forced liquidation at a penalty.
  - Prep: the `flatten_from` item already in `TODO.md`.
  - Evidence: when the mark is a VWAP over a window, a few marketable orders near its end move it, and a holder of inventory profits overall even after its trading losses ([Shearer, Rauterberg & Wellman](../sources/benchmark-manipulation.md), `literature_md/benchmark-manipulation/benchmark-manipulation.md:33` (p. 1)). So ask how the close is settled; a one-sided run of market orders in the closing window is the tell of someone doing it.
- **C6. Scoring that isn't plain PnL** (likelihood: medium): Sharpe or a drawdown penalty, a log scale against the top (AlgoTrade), rank points per round, or zero for a loss.
  - Prep: a Sharpe per day and the drawdown in the grid's measures, so `--sort` can rank by them ([risk](risk-and-protecting-a-lead.md)).
- **C7. Library limits** (likelihood: medium).
  - Breaks: agent-written bots, which reach for pandas and numpy by default.
  - Prep: none needed. The template is standard library only and `arena.validate --allow` checks imports.

### D. Opponents
- **D1. A shared market** (likelihood: medium–high in some round). See [shared market](shared-market-and-adversaries.md).
- **D2. A monoculture of agent-written bots** (likelihood: high if the market is shared). Most teams will hand the docs to an agent, so their bots will look alike: a mid or wall-mid fair value, quotes one tick inside, a linear skew, z-score mean reversion.
  - Breaks: they crowd the same edges, so the spread splits about 1/(n+1). They also become a predictable population we can exploit, for example by trapping the penny-jumpers.
  - Prep: build an **LLM zoo**. Give fresh agents (Claude, GPT and Gemini, with no repo context) a Prosperity-style spec. Save the bots they write under `bots/zoo/`. Use them as `--vs` rivals and as the baseline the template must beat. Write down what they all do alike, since that is also the baseline the organisers will design against.
  - Evidence: LLM agents keep to the trading style they are told (value, momentum, market making) and, built on similar foundation models, may respond in correlated ways ([Lopez-Lira](../sources/llm-agents-market-simulation.md), `literature_md/llm-agents-market-simulation/llm-agents-market-simulation.md:35` (p. 4)); its archetype prompts are templates for the zoo. Bots that fit a model to book features are the fragile ones: small, cheap orders can mislead them ([Goldblum et al.](../sources/adversarial-attacks-hft.md)). A field that reads one shared signal is easier to exploit: an RL trader that could steer an LLM-written feed learned, unprompted, to pump the traders following it, and adding more followers made them fall for it more ([Byrd 2025](../sources/accidental-pump-and-dump.md), `literature_md/accidental-pump-and-dump/accidental-pump-and-dump.md:240` (p. 6)). Its gain was mostly in sample, though (77 against 72 a day out of sample).
- **D3. Organiser bots built to punish the playbook** (likelihood: medium–high):
  - spoofed walls that appear and vanish, aimed at `wall_mid`;
  - momentum ignition;
  - traps for penny-jumpers;
  - takers that fade the obvious signal.

  Prep:
  - the trapper and sniper rivals already in `TODO.md`, plus a spoofer that posts a large wall of the market maker's usual size and pulls it before it trades (`sized_mid` doesn't filter that);
  - in the template, trust a wall only after it has persisted for N ticks.

  Evidence: [Wang & Wellman](../sources/spoofing-abm.md) model the spoofer as a 200-lot bid one tick behind the best, re-posted whenever the best bid moves. It reliably raised prices against book-reading traders, but added little to an exploiter's profit (206.1 against 201.8, `literature_md/spoofing-abm/spoofing-abm.md:237` (p. 7)): a fake wall is a cheap distortion, not a big earner. The sequels agree and add what to do about it:
  - **Where it bites:** in thin markets. With a ladder market maker setting liquidity, the tuned spoofer's offset rises from 10 ticks in the most liquid market to 140 in the least, and the book readers lose most there ([Gu et al.](../sources/spoofability-and-liquidity.md), Table 2, `literature_md/spoofability-and-liquidity/spoofability-and-liquidity.md:255` (p. 6)). So check `arena.diagnose`'s spread and depth: a wide, gappy product is where a fake wall moves a size-based fair value most.
  - **The defence:** ignore the level a spoofer would use. Learners that drop the level behind the best quotes lose almost nothing without spoofing (646–652 against 651), and the spoof's gain disappears ([Wang, Hoang & Wellman](../sources/trading-under-manipulation.md), Table 2, p. 6). For the template, that means a `fair` that doesn't follow a new largest level at once: the wall-persistence check above.
  - **Quoting near fair is itself a defence** in a shared market: the market maker's asks near fair sell into the bids a spoof inflates before the spoofer can ([Gu et al.](../sources/spoofability-and-liquidity.md), `literature_md/spoofability-and-liquidity/spoofability-and-liquidity.md:321` (p. 8)).
  - **A ready simulator:** Gu et al.'s PyMarketSim implements this whole model in Python; read it before writing the A1 generator.
  - **How to spot a spoofer on the day:** a spoof only pays if a real trade follows, so compare the book imbalance just before market trades with its usual distribution; a spoofed book is one-sided before the trade and snaps back after ([Tao et al.](../sources/detecting-spoofing-strategies.md), `literature_md/detecting-spoofing-strategies/detecting-spoofing-strategies.md:93` (p. 4)). A rule of thumb from Korea Exchange data: orders at least 6 ticks from the price and twice the usual size, which rarely fill. The real ones were 5.6 times the usual size, and 90% sat more than 10 ticks away ([Lee, Eom & Park](../sources/spoofing-traders-empirical.md), `literature_md/spoofing-traders-empirical/spoofing-traders-empirical.md:75` (p. 11), `literature_md/spoofing-traders-empirical/spoofing-traders-empirical.md:101-105` (p. 15–16)). Translate the thresholds into the product's own baseline, since 6 ticks is inside the quotes on wide Prosperity books. Those spoofs rested about 79 minutes and were cancelled well after the spoofer's trade, so a persistence check alone wouldn't catch them. Their power came from a feed that showed side totals without prices: once the exchange showed prices instead, spoofing fell from 0.81% to 0.26% of buy volume (`literature_md/spoofing-traders-empirical/spoofing-traders-empirical.md:193` (p. 26)). So if the Arena shows a side total or depth beyond the priced levels, keep it out of `fair`. A disguised spoofer can look like a market maker, so watch the effect, not the shape ([Wang & Wellman 2020](../sources/manipulation-detection-evasion.md)); a book-momentum measure also flags spoofing and layering ([Li et al.](../sources/manipulation-statistical-physics.md)).
  - **What a designed spoofer does:** tilt the volume imbalance at the best quotes into the regime where the other side's market orders speed up, and trade into them ([Cartea, Jaimungal & Wang](../sources/optimal-spoofing.md), `literature_md/optimal-spoofing/optimal-spoofing.md:13` (p. 1)). The traders it fools read the imbalance; `wall_mid` reads level sizes, which a spoofed wall also drags.
  - **Spoofing without meaning to:** learning makers discover it, more readily the more inventory risk they tolerate and the wider the spread ([Cartea, Chang & García-Arenas](../sources/spoofing-learning-algorithms.md), `literature_md/spoofing-learning-algorithms/spoofing-learning-algorithms.md:37` (p. 4)), and a plain profit-maximising RL trader found it on its own ([Byrd 2022](../sources/learning-not-to-spoof.md)). So expect it from RL-tuned rivals, and check our own tuned bot for large orders it never lets fill: the organisers verify solutions.
- **D4. Side games** (likelihood: medium): a sealed bid for market access (P4), beauty contests, allocations whose payoff depends on every team's choice.
  - Breaks: agents give the same textbook answer, so the field herds.
  - Prep: little before the day. On the day, ask two or three agents what they would answer, so you know where the herd will be, and decide one level of reasoning beyond it.
  - Evidence: in the original beauty-contest experiment, first-round choices sat one or two steps of reasoning from the mean, not at the equilibrium, and the modal depth did not grow over rounds ([Nagel 1995](../sources/guessing-games.md), `literature_md/guessing-games/guessing-games.md:41` (p. 3)).

### E. Speed (the user's idea 2)
- **E1. A time budget per call or per run** (likelihood: high that one exists; low that it binds us).
  - Measured 2026-10-14 (*checked*):
    - the template takes a mean of 0.15 ms per tick and a p99 of 0.18 ms on P3 round 3 day 2, with 15 products traded (`uv run python -m arena.backtest bots/template.py 3-2`);
    - it takes 0.05 ms per tick on P4 round 5's 50 products, which it doesn't trade (`... 5-2 --data p4`).

    That is about 5,000 times inside Prosperity's 900 ms per call (`prosperity-wikis/prosperity4/writing-an-algorithm-in-python-192659.md:432`).
  - It binds only with:
    - a budget of a few milliseconds;
    - an event-driven API with many events per second;
    - heavy model inference;
    - a `traderData` that grows with history (the classic Prosperity timeout).
  - Prep (cheap): `arena.validate` warns when `traderData` keeps growing, and a profile of the template at 200 products.
- **E2. Speed as priority** (likelihood: low). A race needs measured time, and a measured-time race is not reproducible on a rerun. "Without many real-world operational complexities" and Python-only point the same way. [ABIDES](../sources/abides-simulator.md) does model "heavier thinkers" acting later and less often (`literature_md/abides-simulator/abides-simulator.md:52` (p. 3)), but through a delay configured per agent, not measured (`literature_md/abides-simulator/abides-simulator.md:69` (p. 4)). If the Arena charges such a delay, the docs will say so.
  - Tell: docs that tie order arrival to response time; probe 8 (sleep 50/200/500 ms) showing fills lost to a slow tick rather than a timeout.
  - If it happens:
    - the template is already lean;
    - numpy loses on arrays this small (about 1 µs of overhead per call);
    - a JIT (Numba) is unlikely to be installed or to compile inside a single uploaded file;
    - the wins left are precomputing, keeping state bounded, and skipping work on products that didn't change.
  - Not worth building before the event.

### Proposals, by value for the time
1. **The LLM zoo (D2):** an afternoon. It gives the agent baseline, a rival population and a list of what the organisers will target.
2. **The stress harness and a regime guard with a loss stop (B1):** about a day. It protects every round, and above all the 40% finale.
3. **The agent-based day generator (A1, A3):** 1–2 days. It is the only way to test impact and tuning across seeds, and it doubles as the mock round's data.
4. **Engine options:** fees, latency, order caps, limits per side (C1–C4). Half a day each with tests, and each a template parameter.
5. **Execution that slices toward a target (A2):** half a day.
6. **A spoofer rival and wall persistence (D3):** next to the existing trapper and sniper item.
7. **Risk measures in the grid (C6), a Kalman fair value (B3) and spreads adapted from markouts (B4):** already near rows in `IDEAS.md`.

Not recommended now: speed work beyond the `traderData` check (E).

## How to test it here
- Each "tell" goes into `ON_THE_DAY.md`, which points here ("Which of the harder-round mechanisms does this round have?").
- The zoo is its own test: the template must beat every zoo bot, alone and with `--vs`, under `worse` fills.
- The stress harness is the test for B1: on every perturbed day, no product should lose more than its loss stop.

## Sources
- Literature: [ABIDES](../sources/abides-simulator.md), [Get Real](../sources/lob-simulation-realism.md), [Wang & Wellman](../sources/spoofing-abm.md), [Wang, Hoang & Wellman](../sources/trading-under-manipulation.md), [Gu et al.](../sources/spoofability-and-liquidity.md), [Das](../sources/learning-market-maker.md), [Adams & MacKay](../sources/online-changepoint-detection.md).
- Local: [Qminers 2024](../sources/qminers-hackathon-2024.md) (with `first_stage_scores.png`), `arena-site-snapshot.txt`, [AlgoTrade (pitfa19)](../sources/algotrade2026-pitfa19.md), [Negative Eevee](../sources/algotrade2026-negative-eevee.md), [UChicago 2026](../sources/uchicago-trading-2026.md), [DTU](../sources/prosperity4-dtu-quant-lab.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md).
- Web, through fetch summaries only ([online articles](../sources/online-articles.md)):
  - [Optiver, "Where AI trading models work"](https://www.optiver.com/insights/technology-blog/where-ai-trading-models-work-and-where-they-still-fall-short/)
  - [Ready Trader Go, "How to play"](https://readytradergo.optiver.com/how-to-play/)
  - [ABIDES RMSC04 config](https://github.com/jpmorganchase/abides-jpmc-public/blob/main/abides-markets/abides_markets/configs/rmsc04.py), [Tao et al.](../sources/detecting-spoofing-strategies.md), [Cartea, Jaimungal & Wang](../sources/optimal-spoofing.md), [Cartea, Chang & García-Arenas](../sources/spoofing-learning-algorithms.md), [Li et al.](../sources/manipulation-statistical-physics.md), [Byrd 2022](../sources/learning-not-to-spoof.md), [Goldblum et al.](../sources/adversarial-attacks-hft.md), [Wang & Wellman 2020](../sources/manipulation-detection-evasion.md), [Lopez-Lira](../sources/llm-agents-market-simulation.md), [PyMarketSim](../sources/pymarketsim.md), [Shearer, Rauterberg & Wellman](../sources/benchmark-manipulation.md), [Gao & Wang](../sources/market-making-latency.md), [Zhang et al.](../sources/dtw-lead-lag.md), [Nagel](../sources/guessing-games.md), [Lee, Eom & Park](../sources/spoofing-traders-empirical.md), [Byrd 2025](../sources/accidental-pump-and-dump.md), [Yeo, Cha & Hwang](../sources/lob-irreversibility.md)
