---
title: Submission, evaluation and scoring mechanics
type: concept
updated: 2026-10-13
---

# Submission, evaluation and scoring mechanics

## Summary
What the Arena site says about itself (a portal, one `.py` per round, a capped number of submissions, a public backtest, probably a private rerun) puts it closest to Prosperity and to UChicago's Case 2, not to a live exchange. The comparison events fix several details we should expect: a position-limit cancel rule, a restricted library set, failing runs scoring zero, and hidden evaluation data.

## What the sources say
| Mechanic | Prosperity | Qminers 2025 | UChicago Case 2 | AlgoTrade |
|---|---|---|---|---|
| What you submit | one `Trader` file, `Trader.run(state)` once per tick | one `Model` file, `place_bets` once per day (the same in 2024: `qminers-hackathon-2024/COMPETITION_README.md:31`) | Python stub, one file | a bot you run on a VM |
| Limit rule | cancel all of a product's orders that could breach (`prosperity3-backtester-jmerle/prosperity3bt/runner.py:123`) | reject over-limit bets, all-or-nothing on funds (`qminers-hackathon-2025/src/environment.py:122-140`) | invalid output rescaled; a failing step = 0 (case packet) | order rejected; position floor −200 (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:386-399`) |
| Libraries | Python 3.12 standard library plus pandas, NumPy, `statistics`, `math`, `typing` and `jsonpickle`; other external libraries "not supported" (official: `prosperity-wikis/prosperity4/writing-an-algorithm-in-python-192659.md:609-620`) | pandas, NumPy, scikit-learn, XGBoost in the author's setup (`qminers-hackathon-2025/README.md:11`) | Python 3.12, NumPy, pandas, scikit-learn, SciPy | any language |
| Hidden data | submissions evaluated against bots; practice data public | hidden validation seasons (`qminers-hackathon-2025/src/validate.py:20`) | held-out 12 months | live |
| Failure | engine cancels orders; exceptions per tick | "RTE: KeyError" report (`qminers-hackathon-2025/problem_info_en.md:230-233`); RTE / MLE / TLE statuses, 1 CPU and 5 GB RAM (`qminers-hackathon-2024/COMPETITION_README.md:51-59`) | disqualified, 0 points | disconnect |

- **Prosperity 4 structure** (their claims): rounds 1–2 form a qualifier (200,000 to advance) and the leaderboard resets for rounds 3–5 (`prosperity4-ryan-challman/README.md:11`, `prosperity4-dtu-quant-lab/README.md:57`); Osmium and Pepper Root vanish after round 2; round 2 adds a blind "extra market access" bid via `Trader.bid()` (`prosperity4-baguette-fromage/Strategies/Phase1.py:254`), median bid 50 (`prosperity4-baguette-fromage/README.md:519`).
- **Position limits by edition** (from the backtesters' tables and the teams' code):
  - P2: Amethysts 20, Starfruit 20, Orchids 100, Chocolate 250, Strawberries 350, Roses 60, Gift basket 60, Coconut 300, Coupon 600 (`prosperity2-backtester-jmerle/prosperity2bt/data.py:7-17`).
  - P3: Resin 50, Kelp 50, Squid Ink 50, Croissants 250, Jams 350, Djembes 60, Picnic baskets 60 and 100, Volcanic Rock 400, each voucher 200, Macarons 75 (`prosperity3-backtester-jmerle/prosperity3bt/data.py:7-23`).
  - P4: Emeralds 80 and Tomatoes 80 (tutorial), Osmium 80, Pepper Root 80, Hydrogel 200, Velvetfruit 200, each `VEV_*` 300, round 5 products 10. IMC's own round pages state all of them (`prosperity-wikis/prosperity4/tutorial-round-simulator-practice-f01b6f.md:21-24`, `prosperity-wikis/prosperity4/round-1-trading-groundwork-41267b.md:25-26`, `prosperity-wikis/prosperity4/round-3-gloves-off-2ff551.md:29-31`, `prosperity-wikis/prosperity4/round-5-the-final-stretch-f13f4c.md:27`); the teams' code agrees (`prosperity4-dtu-quant-lab/round_3/algorithmic/trader.py:137-145`, `prosperity4-baguette-fromage/README.md:314`, `prosperity4-ryan-challman/README.md:45`; the P4 backtester lists only round 5 and defaults to 50: `prosperity4-backtester/prosperity4bt/data.py:8`).
- **Data shape** *(checked on P4 files)*: 10,000 ticks per day, timestamps in steps of 100, up to 3 levels per side; names only in P3 round 5 and P4 round 4; day numbers overlap across rounds (P4: R1 −2…0, R2 −1…1, R3 0…2, R4 1…3, R5 2…4). An empty book has `mid_price` 0.0 in P4's files (203 rows); P2 has no zero mids, and P3's 19 are a deep out-of-the-money voucher quoted at 0. Our loader treats the P4 case as no price (`arena/formats/prosperity.py`). P4 rounds 3 and 4 share days 1 and 2: identical books and trades, with counterparty names added in round 4 *(checked: compared the files)*. So the two rounds hold 4 distinct days, not 6. Rounds 1 and 2's shared days differ.
- **Organisers reuse generators and data:** Prosperity 3's Resin data equalled Prosperity 2's Amethysts (`prosperity3-backtester-jmerle/README.md:79`); Prosperity 3 bot behaviour matched Prosperity 2's over 95% (`prosperity3-frankfurt-hedgehogs/README.md:969`); in Prosperity 2 the previous year's public data predicted prices (`prosperity2-linear-utility/README.md:172-190`). The Arena is new, so there is no prior edition.
- **Hardcoding was banned after a report** (Frankfurt, `prosperity3-frankfurt-hedgehogs/README.md:976`): exploiting leaks is risky when organisers verify and rerun solutions (`ON_THE_DAY.md`, "reproducibility").

- **Prosperity 4 limits, from IMC's own wiki** (`prosperity-wikis/prosperity4/writing-an-algorithm-in-python-192659.md:432`): **900 ms per `run` call** (average expected ≤ 100 ms) or the call times out; the algorithm runs 1,000 iterations when you upload it on a sample day different from the scored one, and 10,000 in the scored run (`prosperity-wikis/prosperity4/writing-an-algorithm-in-python-192659.md:13`, `prosperity-wikis/prosperity4/writing-an-algorithm-in-python-192659.md:434-442`); the position-limit rule rejects all of a product's orders if the aggregate could breach it (`prosperity-wikis/prosperity4/writing-an-algorithm-in-python-192659.md:21`). `arena.validate` should check a call time well under 900 ms.
- **Memory and restarts matter**: a logger that pushed a Prosperity 3 submission over 100 MB restarted the Lambda instance and wiped the trader's local variables (CMU Physics, `online-snapshots/chrispyroberts_imc-prosperity-3.README.md:234`). Keep all cross-tick state in `traderData` and the logging small.
- **Qminers' own format, two years running** ([Qminers 2024](../sources/qminers-hackathon-2024.md)): an online qualification with a capped number of submissions (20 in 2024, their claim: `qminers-hackathon-2024/README.md:33`), then an in-person final of 3 rounds in one day, with scores reset, a shorter horizon and later, unseen data (`qminers-hackathon-2024/README.md:43`, `qminers-hackathon-2024/README.md:55`). The 2025 evaluator is the 2024 one with new columns *(checked with `diff`)*. The leaderboard showed every team's score, runtime and RAM (`qminers-hackathon-2024/README.md:67`), and an entry named `_LLM_BENCHMARK_` came 2nd in the qualification (screenshot), likely the organisers' own baseline.
- **Another stub-and-upload shape**: UChicago 2025 Case 2 gave a class with one `allocate_portfolio` method called per tick, state kept in class fields (`uchicago-2025-case2-humzah/chicago8.py:18-27`).

## Where they disagree
Nothing between sources; the Arena's own rules are what is unknown.

## What it means for our code
`arena/formats/prosperity.py` holds `LIMITS` and the loader; `arena/formats/` is where a `qminers.py` goes on the day. The bot must be stdlib-only and keep state in `traderData` because the allowed libraries and persistence are unknown (`CLAUDE.md`). `arena.validate` checks several of the failure modes above.

## How to test it here
Read the Technical Rules first (`ON_THE_DAY.md`). Fill the unknowns in `ON_THE_DAY.md` ("How is the bot called?", limits, libraries, scoring) and update this table with sources.

## Sources
[Qminers 2025](../sources/qminers-hackathon-2025.md), [Qminers 2024](../sources/qminers-hackathon-2024.md), [UChicago](../sources/uchicago-trading-2026.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [jmerle P3 backtester](../sources/prosperity3-backtester-jmerle.md), [P2 backtester](../sources/prosperity2-backtester-jmerle.md), [prosperity4btest](../sources/prosperity4-backtester.md), [Baguette Fromage](../sources/prosperity4-baguette-fromage.md), [Frankfurt](../sources/prosperity3-frankfurt-hedgehogs.md).
