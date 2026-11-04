# Report: TQP chapter map, the literature, the wiki, and a reading plan

Nothing in the repo was modified.

## 1. *Trades, Quotes and Prices* (Bouchaud, Bonart, Donier, Gould, 2018)

**Files**
- PDF: `/Users/jakubkucera/Documents/qminers_arena/literature_raw/trades_quotes_prices_full.pdf` (463 pp.)
- Markdown: `/Users/jakubkucera/Documents/qminers_arena/literature_md/trades-quotes-prices/trades-quotes-prices.md` (167k words), with `meta.json` holding the TOC
- Wiki chapter map and results: `/Users/jakubkucera/Documents/qminers_arena/references/wiki/sources/trades-quotes-prices.md`. This page is the best short summary of the book. It lists every useful result with its equation number and page, says which formulas were checked against the PDF, and measures the book's tests on Prosperity data.

**Page numbering.** The PDF page is the printed page plus 19. Chapter 1 starts on PDF p. 24 (printed p. 5).

**Where ~45 pages ends.** The repo used to hold a 47-page excerpt that ran from the preface to §2.1.4, and that is probably what the user read.
- If the user counted 45 PDF pages, they stopped around §2.1.3 "High-Frequency Noise" (PDF p. 45).
- If they counted 45 printed pages, they stopped at the end of chapter 2 (PDF p. 64).
- Either way they have covered the preface, chapter 1 (the book's best chapter for us) and the random-walk and signature-plot part of chapter 2.

**Chapter map with relevance to a hackathon market-making bot (PDF pages)**

| Ch | Title | PDF pp | Relevance | Why |
|---|---|---|---|---|
| 1 | Ecology of Financial Markets | 24–40 | **High** | Adverse selection, and the break-even `s/2 − R∞` (§1.3, eq. 1.9–1.11). This is the repo's central test of whether making pays. |
| 2 | Statistics of Price Changes | 41–58 | Med | §2.1.2–2.1.3 signature plot (eq. 2.9–2.10): the repo uses it to show the mid is noise at one tick. §2.2–2.3 (heavy tails, excess volatility) are background. |
| 3 | Limit Order Books | 63–76 | Med | LOB mechanics, tick and lot size, priority rules (§3.2.1). Vocabulary only. |
| 4 | Empirical Properties of LOBs | 77–93 | Low–Med | NASDAQ statistics. Only §4.8 (large-tick vs small-tick effects) matters. |
| 5 | Single-Queue Dynamics: Simple Models | 97–119 | Low | Master and Fokker–Planck equations for one queue. Heavy maths, never cited. |
| 6 | Single-Queue, Large-Tick | 120–135 | Low | Same, calibrated. Never cited. |
| 7 | Joint-Queue Dynamics (race to the bottom) | 136–152 | **High** | Queue imbalance `I = V_b/(V_b+V_a)` predicts the next mid move, called "the worst kept secret of HFT" (pp. 138–141, eq. 7.6). This is the basis of the repo's imbalance and micro-price signals. |
| 8 | Santa Fe zero-intelligence model | 153–177 | Med | §8.5.4 only (p. 165–166): with random flow, making is profitable. The repo's measurements say Prosperity is this case. |
| 9 | Hawkes processes | 182–205 | Low | Clustering of order arrivals. Prosperity's takers don't cluster. |
| 10 | Long-range persistence of order flow | 206–223 | Low–Med | Trade-sign memory. Weak on Prosperity (`C(1)` ≈ 0.1). |
| 11 | Impact of Market Orders | 227–247 | **High** | The response function `R(ℓ)` (eq. 11.5), which the repo's `trade_impact` measures. Also the footnote that an imbalance-weighted reference price beats the mid for large-tick assets (p. 232). |
| 12 | Impact of Metaorders (square-root law) | 248–263 | Low | Execution of large institutional orders. §12.3.3 is cited once. |
| 13 | Propagator Model | 268–288 | Low | Transient impact theory. |
| 14 | Generalised Propagator Models | 289–305 | Low | Same, extended. |
| 15 | Kyle Model | 309–316 | Med | A short classic model of informed trading, `Λ = σ_F/(2Σ_V)`. |
| 16 | Determinants of the Bid–Ask Spread | 317–337 | **High** | §16.1 Glosten–Milgrom (spread from the informed share) and §16.2 MRR (`R(ℓ) = (s/2)(1 − C(ℓ))`): why spreads exist. |
| 17 | Profitability of Market-Making | 338–351 | **High** | The most directly useful chapter. Eq. 17.3 gives a maker's long-run gain, eq. 17.4 inventory control through quote size (the repo's `size_skew`), and eq. 17.13–17.15 the slow vs fast maker break-even. Includes "easy when prices mean-revert, hard when they trend". |
| 18 | Latent Liquidity, Walrasian Auctions | 356–372 | Low | Meso-scale theory. |
| 19 | Continuous-time double auction impact | 373–384 | Low | Reaction–diffusion theory. |
| 20 | Information content of prices | 385–399 | Low | Efficient-market philosophy. |
| 21 | Optimal Execution | 403–424 | Med–High | Skip §21.2 (Almgren–Chriss, institutional execution). Read §21.3–21.4 (pp. 413–421): market vs limit orders, and limit-order cost `φ·d·ρ` (trend hurts, mean reversion helps). Also the value of queue position and why backtests with phantom orders are "a bit dodgy". |
| 22 | Market Fairness and Stability | 425–440 | Low | Regulation, flash crashes. |
| A.5 | An alternative market-making strategy | 451–452 | Low–Med | Inventory of only −1/0/+1. |

The user's sense was right: Parts IV, VI and VIII (chapters 9–10, 13–14 and 18–20) and most of chapters 5, 6 and 12 are not used by this repo.

**Sections the repo cites** (outside the source page: the concept pages `price-impact`, `market-making-and-inventory-skew`, `reading-the-data-on-day-one`, `book-imbalance-and-micro-price`, `queue-position-and-fills`, `fair-value-and-wall-mid`, plus `contradictions.md`, `overview.md` items 13 and 15, and `IDEAS.md` rows 168 and 172):

| Chapter | Sections cited |
|---|---|
| 1 | §1.3 adverse selection, impact, skewness (eq. 1.9–1.11) |
| 2 | §2.1.2 (eq. 2.9–2.10); §2.3.2 flat-volatility puzzle |
| 7 | §7.2–7.3 (imbalance, eq. 7.6) |
| 8 | §8.5.4 |
| 11 | §11.3.1 footnote 6, §11.3.4, §11.5 |
| 12 | §12.3.3 |
| 15 | §15.2 |
| 16 | §16.3 |
| 17 | §17.2.1 (eq. 17.4), §17.2.2 (eq. 17.13–17.15, NASDAQ result), §17.3 (eq. 17.16) |
| 21 | §21.3.3 (eq. 21.18), §21.4 (queue value `h_c`, phantom orders) |

`IDEAS.md` tests two of these:
- **Size skew** (eq. 17.4): tested through the template's `size_skew` parameter.
- **"Does market making pay here?"** (ch. 17): measured on P3 round 1. Prosperity's margin is +0.2 to +0.4 of the spread per trade, against −0.1 on NASDAQ, so Prosperity is the zero-intelligence case.

## 2. The literature folder

Index: `/Users/jakubkucera/Documents/qminers_arena/literature_md/README.md`. It holds **71 documents**, and each has a wiki source page. Page counts are approximate. **S** marks a short, accessible piece that is good to excerpt; **H** marks a heavy one.

**A. Microstructure basics and intuition**
- Harris, *Trading and Exchanges* (632 pp., H; read ch. 13 Dealers pp. 291–309 and ch. 14 Bid/Ask Spreads pp. 310–334, which are prose and very readable)
- Gould et al., *Limit order books* (26 pp., S for §1–3)
- Bouchaud et al., *Trades, Quotes and Prices* (460 pp., H)
- Cartea, Jaimungal & Penalva, *Algorithmic and HFT* (359 pp., H; ch. 2 pp. 36–55 primer; ch. 10 market making pp. 263–289)
- Diehm, `how-to-almost-win` (7 pp., S, a mindset essay)

**B. Market-making models**
- Avellaneda–Stoikov `hft-in-a-limit-order-book` (8 pp., S, the core paper)
- GLFT `dealing-with-inventory-risk` (33 pp., H)
- Guéant `optimal-market-making` (42 pp., H, multi-asset)
- `mean-reverting-reference-price` (16 pp.)
- `limit-and-market-orders` (17 pp.)
- `online-learning-market-making` (39 pp., H)
- `competing-dealers` (34 pp.)
- `pro-rata-microstructure` (31 pp., H)
- `stochastic-liquidity-demand` (53 pp., H)
- `market-making-latency` (37 pp.)
- `order-stacking-mm` (9 pp.)
- `scaled-beta-policies` (9 pp.)
- `hawkes-structured-mm` (8 pp.)
- Learning or RL makers: `algorithmic-cooperation-mm` (8 pp.), `marl-competition-no-collusion` (9 pp.), `market-making-perceived-collusion` (9 pp.), `mm-adverse-selection-rl` (9 pp.)

**C. Fair value and signals (imbalance, order flow)**
- `micro-price` (9 pp., S)
- `queue-imbalance-predictor` (29 pp., S, essentially logistic regression)
- `price-impact-of-book-events` (OFI, 26 pp., S)
- `order-book-signals` (41 pp., H)
- `decomposed-ofi` (20 pp.)

**D. Queue position and fills**
- `queue-position-valuation` (30 pp.)
- `queue-reactive-model` (28 pp.)
- `dynamics-of-order-positions` (39 pp., H)
- `rigtorp-queue-position` (2 pp., S)
- `databento-queue-position` (5 pp., S)
- `quant-se-order-position` (3 pp., S)

**E. Adverse selection and informed flow**
- `market-makers-dilemma` (42 pp., empirical, readable)
- `negative-drift-of-a-fill` (27 pp., S in spirit: fills come with adverse moves)
- `learning-market-maker` (Glosten–Milgrom learner, 18 pp.)
- `collective-liquidity-taking` (9 pp.)
- `classify-trading-agents` (9 pp.)

**F. Statistics and backtest overfitting (most natural for an ML reader)**
- `pseudo-math` (33 pp., S, the readable entry point)
- `probability-of-backtest-overfitting` (PBO and CSCV, 30 pp.)
- `deflated-sharpe-ratio` (21 pp.; the OCR lost the inline math, so read the PDF)
- `superior-predictive-ability` (Hansen SPA, 15 pp., dense)
- `stepwise-multiple-testing` (StepM, 30 pp.)
- `backtesting-haircut` (15 pp., S)
- `reusable-holdout` (Thresholdout, 27 pp.; familiar ground for ML readers)
- `optimal-trading-rules` (39 pp.)
- `online-changepoint-detection` (6 pp., S)
- `kelly-criterion` (sizing, 39 pp., a scanned PDF)

**G. Options.** There is no options paper in the folder; the wiki lists an options text as not obtainable. The only coverage is the concept page `options-and-vouchers` (stdlib Black–Scholes, from team write-ups).

**H. Baskets, ETFs, stat arb and lead-lag**
- `etf-trade-flow-decomposition` (9 pp.)
- `cross-asset-order-flow` (8 pp.)
- `etf-arbitrage-abm` (8 pp.)
- `dtw-lead-lag` (9 pp.)
- Cartea ch. 11 on pairs trading (pp. 290–311)

**I. Simulation, agent-based models and LLM agents**
- `abides-simulator` (13 pp., S)
- `lob-simulation-realism` (9 pp., S)
- `pymarketsim` (8 pp.)
- `spoofing-abm` (9 pp.)
- `llm-agents-market-simulation` (46 pp.)
- `lob-irreversibility` (9 pp.)
- `guessing-games` (Nagel beauty contest, 18 pp.)

**J. Spoofing and manipulation**
- `detecting-spoofing-strategies` (29 pp.)
- `spoofing-learning-algorithms` (60 pp., H)
- `optimal-spoofing` (36 pp., H)
- `manipulation-statistical-physics` (9 pp.)
- `learning-not-to-spoof` (8 pp.)
- `adversarial-attacks-hft` (8 pp.)
- `manipulation-detection-evasion` (7 pp.)
- `spoofing-traders-empirical` (47 pp.)
- `accidental-pump-and-dump` (8 pp.)
- `benchmark-manipulation` (8 pp.)
- `trading-under-manipulation` (8 pp.)
- `spoofability-and-liquidity` (9 pp.)

## 3. The references wiki

Index: `/Users/jakubkucera/Documents/qminers_arena/references/wiki/index.md`. It has **23 concept pages** and **97 source pages**: 71 literature pages and 26 team write-ups, tools and other competitions. It also has `overview.md` (start here) and `contradictions.md`.

The concept pages, in `/Users/jakubkucera/Documents/qminers_arena/references/wiki/concepts/`, are good material for guidebook chapters:

| Page | What it covers |
|---|---|
| fair-value-and-wall-mid | The mark is the market maker's mid; five definitions of "wall mid". |
| market-making-and-inventory-skew | Take / clear / make, and the unsettled question of skew. |
| hidden-takers-and-empty-sides | Quoting ~100 away when a side is empty; recurring takers. |
| drift-and-regime-change | Drifting, pegged and mean-reverting products; fixed anchors that broke. |
| baskets-and-fixed-sums | Known baskets; why searching for unknown ones fails. |
| options-and-vouchers | Why smile trading rarely paid; deep-OTM 0/1; stdlib Black–Scholes. |
| informed-counterparties | Named informed traders ("Olivia", the Marks) and the rollbacks. |
| jumps-and-snap-back | Round-number jumps that reverse; DU's three-tick rule. |
| many-products-architecture | Intents, cluster strategies, ownership, safety nets. |
| validation-and-overfitting | Worst-day, leave-one-day-out, multiple testing, not opening the unseen day. |
| queue-position-and-fills | Our resting model versus hftbacktest's; the evidence on cancels. |
| risk-and-protecting-a-lead | Scoring formats, cutting variance, stopping when safe. |
| shared-market-and-adversaries | Book-sniping, crowded edges, a shared Arena. |
| submission-and-scoring-mechanics | The Arena format against comparison events; limits; data shape. |
| backtesting-and-tooling | Matching rules, the P4 fork, what backtesters cannot do. |
| ai-assisted-work | How winners used agents, and their warnings. |
| cross-market-and-conversions | Orchids, macarons, cross-venue; unsupported by the backtesters. |
| book-imbalance-and-micro-price | `ρ`, the weighted mid, micro-price and OFI; strong only at 1-tick spreads. |
| optimal-quoting-models | A–S, GLFT, Guéant; the closed form equals our linear `skew`. |
| probing-the-environment | Experiments on the simulator first: PnL mark, bot tolerances, no-queue. |
| reading-the-data-on-day-one | `arena.diagnose` notes mapped to strategy choices. |
| price-impact | Instantaneous vs permanent impact; the maker's `s/2 − R∞`. |
| harder-rounds | How organisers could make rounds harder, with tells and ranked prep. |

## 4. Recommended reading companion for an ML reader, in order (instead of TQP in full)

1. **TQP chapter 1 (PDF pp. 24–40), already read.** Add the wiki's TQP source page, "Main results" and "Assumptions against the Arena", as a 20-minute map of the rest of the book with Prosperity numbers attached (`references/wiki/sources/trades-quotes-prices.md`).
2. **Harris ch. 13 "Dealers" and ch. 14 "Bid/Ask Spreads" (PDF pp. 291–322, to the end of §14.4).** This is the plain-prose intuition for why a market maker earns the spread and what makes it lose (inventory, adverse selection). Optionally add Gould et al. §1–3 (pp. 1–9) for LOB vocabulary.
3. **TQP ch. 16 §16.1–16.2 and ch. 17 (PDF pp. 317–330 and 338–350).** Glosten–Milgrom, MRR, and the profitability of market making. This is the theory core and the source of the repo's `size_skew` and its "does making pay" test.
4. **Avellaneda & Stoikov 2008 (8 pp.).** Then the concept page `optimal-quoting-models`, which translates A–S, GLFT and Guéant into the template's `skew` parameter. Skip the GLFT and Guéant papers themselves unless needed; their closed forms have OCR traps.
5. **Signals: Stoikov's micro-price (9 pp.), Gould & Bonart queue imbalance (29 pp.), and TQP ch. 7 §7.1–7.3 (PDF pp. 137–145).** For an ML reader these amount to feature engineering: a logistic regression on book imbalance. Then read the concept page `book-imbalance-and-micro-price`.
6. **Adverse selection in practice: TQP ch. 11 §11.1–11.3 (PDF pp. 227–240), then DeLise, *Negative drift of a fill* (27 pp.).** Markouts and the response function, which is exactly what `arena.analysis` measures, and why backtest fill rules lie.
7. **TQP ch. 21 §21.3–21.4 (PDF pp. 413–421).** Market vs limit orders, the trend vs mean-reversion rule, the value of queue position, and why phantom-order backtests are biased.
8. **Validation: `pseudo-math` (33 pp.), then the concept page `validation-and-overfitting`, then PBO (30 pp.).** This is where the user's ML background transfers directly (multiple testing, holdout reuse). The deflated Sharpe ratio and SPA can wait.

With this route, the user can skip TQP chapters 5–6, 9–10, 12–14, 18–20 and 22. Cartea et al. and Bouchaud are best used as books to look things up in, which is also what the repo's own literature README says.
