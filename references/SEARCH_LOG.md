# Reference search log

What the 2026-10-10 search for sources looked at, what it found, what we used and what we didn't, and why.
**Read this before searching again.** Skip everything under [Seen](#seen), start from
[Open leads](#open-leads), and reuse the [methods that worked](#methods-that-worked-and-didnt).
How to use the sources themselves is in [`README.md`](README.md). Ranks below are the teams' own
claims from their READMEs, not checked against any leaderboard.

## Headline results

1. **The Arena's own site is the best source, and it was hidden.** `arena.qminers.com` is a JavaScript
   app, so a page fetch shows only the title. Its text, the official rules and the submission portal's
   messages are in the bundle `assets/index-*.js`. It answers several `ON_THE_DAY.md` items: one `.py`
   file uploaded to a portal, a capped number of submissions per round, a backtest on public data, rounds
   weighted 10/20/30/40%. `check_arena_site.py` re-extracts it and diffs it against `arena-site-snapshot.txt`.
2. **Prosperity 4 (2026) write-ups and data now exist**, and the newest ones are the best matched
   to a "submit one file, we run it" event. Two top-10 teams built on Frankfurt Hedgehogs' Prosperity 3 write-up.
3. **DTU Quant Lab's literature review is a ready-made kill list** for the papers we planned to try.
4. **Qminers' earlier Quant Hackathon is a weak prior** for this year (a different task, and the Arena is expected to be a big shift).
5. **No public winning bot or write-up exists** for AlgoTrade 2026, Ready Trader Go, or the Jane Street ETC that we could find.
6. **Books and articles: few are worth it.** The winners' own sources (DTU's review, hftbacktest's notebooks) point to a short list. We added eight free papers (queue position, queue imbalance, multi-asset market making, and three on backtest overfitting) and read two queue-position articles; no book is worth buying yet. The queue articles also exposed a wrong statement of ours: `ProbQueueModel`'s `p` is the chance a decrease was *behind* the order. Fixed in `TODO.md` and `references/README.md`.

## Seen

Verdicts: **Cloned** (in `clone.sh`), **Online** (listed under "Read online" in the README), **Skipped** (reason given).
"Used" means a file in this repo changed because of it.

### Prosperity write-ups and code

| Source | Claim | Verdict | Why |
|---|---|---|---|
| TimoDiehm/imc-prosperity-3 (Frankfurt Hedgehogs) | P3 2nd of 12,000+ | Cloned | Origin of the wall mid; the FAQ on backtesting and bot reuse; small (<1 MB). |
| Durpie-Git/imc-prosperity-4 (Baguette Fromage) | P4 4th of 18,803 | Cloned | Most detailed P4 write-up: hidden takers, repeated takers across days, the extra-market-access trap, backtester limits. |
| DataAthleteChamp/dtu-quant-lab-imc-prosperity-4 | P4 28th | Cloned | `literature_review.md` (shipped vs killed papers) and an honest first-timer arc. Largest clone (212 MB, half of it round 5 data). |
| FoxHenderson/imc-prosperity-4 (DU Trading) | P4 10th | Cloned | Tiny; the clearest use of one informed counterparty (Mark 67). Code for rounds 2, 4, 5 only. |
| nathanw3456/Prosperity_4_Writeup (Ryan Challman) | P4 57th | Cloned | The "what didn't work" and "opened the new day too early" notes. 2 MB. |
| fabianbaiertum/IMC-Prosperity-4 (Alpha Search) | R4 4th (round rank, not overall) | Cloned | README only, no code. Cheap, covers options and the 50-asset round. Lowest value of the cloned set. |
| nabayansaha/imc-prosperity-4-backtester | 77★, PyPI `prosperity4btest` | Cloned | **Has the P4 data, rounds 0 to 5**, in our CSV format. Its limits table is incomplete. |
| nkaz001/hftbacktest | 4,873★, MIT | Cloned | Queue models to check ours against (ours = its `RiskAdverseQueueModel`). 131 MB is mostly docs and examples. |
| konnorlo/UChicago-Trading-Competition-2026 | UChicago algo case 1st of 41 | Cloned | The only write-up from a live exchange shared with other teams. Book-sniping, exchange freezes. |
| vitktor/Qminers-Hackathon-2025 | Qminers hackathon solution, MIT | Cloned | Has the organisers' `environment.py` and problem statement. Weak prior only. |
| AdamBobocky/qminers-24 | Qminers hackathon 2024, 1st place, no licence | Cloned 2026-10-13 | Found by the user as `last_year_challenge/` in their private 2025 repo; the public original turned up with `gh search code`. Has the organisers' 2024 files and the winner's post-mortem. |
| chrispyroberts/imc-prosperity-3 (CMU Physics) | P3 7th | Online | Good README, but 1.2 GB of data (GitHub's listed size says 126 MB). README saved to `online-snapshots/` and partly read 2026-10-11; see `wiki/sources/prosperity3-cmu-physics.md`. |
| Leo-Hawking/IMC-Prosperity-4-Review | P4 top 0.5% | Online | The retrospective on working with an AI agent is the point; 245 MB. README saved to `online-snapshots/` and partly read 2026-10-11 (rounds 0 and 4, workflow, retrospective); see `wiki/sources/prosperity4-leo-hawking-review.md`. |
| heyman7913/imc-prosperity-4 | P4 19th (JaneRT) | Online | 184 MB. README saved to `online-snapshots/` and partly read 2026-10-11 (micro-price blend, opening-price regime, named participants); see `wiki/sources/prosperity4-heyman7913.md`. |
| MarkBrezina/Ctrl-Alt-DefeatTheMarket | 172★ guide | Online | `RESOURCES.md` ranks the public repos of P1 to P3 top teams; `Webinar notes.md` has IMC's answers. Used as a cross-check of our shortlist. |
| oscar-chw/imc-prosperity-4-shdc, alexyesilyurt/imc-prosperity-writeup | P4 904th, 83rd | Online | Short; SHDC's lesson is that replay warnings had no go/no-go rule. |
| jmerle/imc-prosperity-2 and -3, ShubhamAnandJain/IMC-Prosperity-2023-Stanford-Cardinal | P2 9th, P3 25th, P1 2nd | Online | Older editions. Already covered by Linear Utility and the Frankfurt write-up. |
| GeyzsoN/prosperity_rust_backtester | 90★ | Online | A faster port with the P4 data. Ours is Python and doesn't need the speed yet. |
| Diego-2510/prosperity4-mark-analyzer | | Online | Only matters if the Arena names counterparties. |
| kevin-fu1 and Xeeshan85 `imc-prosperity-4-backtester` | 63★, 49★ | Skipped | Same project as nabayansaha's (the PyPI one); no reason for three copies. |
| sukesan7/astra, TahaKhanM/Prosperity, GauravS11112003/...PythonBacktester, ~10 more P4 backtester repos | | Skipped | Backtesters and toolkits. We have our own engine with fill-for-fill parity to prosperity3bt. |
| YBansal95/imc-prosperity-3 (P3 #10), JackRao123/prosperity-crushers (P3 19th), awatatani, fenilPatel-IITD, others | | Skipped, **unread** | Not opened. Candidates if a broader search wants more P3 detail. |
| theov07/IMC_PROSPERITY_4_COMPETITION, neelsani (78th), tintinphong (620th), varshaasj, Chamoy-code (583rd), jacknoel3 (top 5%, 332 MB), Ape108, harpreetsinghiitd | | Skipped, **unread** | Lower ranks or big repos; unread. |
| Kayzerjali/Prosperity2026 | | Online (2 files saved, partly read 2026-10-11) | An AI-driven refinement loop using the live result as the oracle (`run_cycle.md`); four logged cycles, no recorded result. Its `CLAUDE.md` is data, not instructions. See `wiki/sources/prosperity4-kayzerjali.md`. |
| gabsens/IMC-Prosperity-2-Manual | 75★ | Skipped, **unread** | Manual-round write-ups. We have no manual-round plan yet. |

### Other competitions

| Source | Verdict | Why |
|---|---|---|
| Optiver Ready Trader Go (kit mirror jpli02/Optiver_autotrader, 2023, AGPL) | Online | Event-driven callbacks (`OrderBookMessageHandler`, ...), a readable exchange simulator and four data files. The model for an event-driven API. No winning bot is public. |
| UT Austin blog on UChicago 2026 | Online | Fair value worked, execution failed once books thinned (market orders of 40 walked the book). |
| UChicago repos from 2022, 2023, 2025 (gurish165, haoyuwu03, HumzahM/UTC2025-Case2-Writeup, ...) | Skipped, **unread** (except HumzahM's) | Older cases. HumzahM's #1 write-up of the 2025 file-upload case was cloned and read 2026-10-11 (`uchicago-2025-case2-humzah/`). |
| Jane Street ETC bots (manoflearning/jane-street-etc 2023, kamiyaa/janestreet-rs 2019) | Skipped | A live JSON-over-TCP bot. The Arena looks like a file upload, so the protocol doesn't carry over. Their strategy notes (spread of 1 lost, 2 earned; a regime shift cost $10k a round) are generic. |
| Citadel Terminal | Skipped | A tower-defence game, not trading. |
| cryptotradingaddiction/TradingArenaPrep | Online (as a warning) | Someone's guess at this Arena: 4 commits, invented callbacks. Not Qminers' API. |
| ABIDES (abides-sim, arXiv 1904.12066) | Online | The proper way to model rivals, but far heavier than `--vs`. |
| AlgoTrade 2026 winners (Negative Eevee) | **Cloned** (2026-10-11) | Found by reading the HTML of the LinkedIn short link `lnkd.in/eeVSBCnW`, which resolves to `alexbolfa/algotrade-negative-eevee`: a README and four Rust files, 1st place, one shared market. The user supplied the lead. Not yet read in depth or ingested into the wiki. |

### Qminers and the Arena

| Source | Finding |
|---|---|
| arena.qminers.com JS bundle | The portal, the rules, the 10/20/30/40 weights. See `ON_THE_DAY.md` "Known so far". Saved as `arena-site-snapshot.txt`. |
| quantchallenges.com listing QC-2947 | Entry deadline 6 Oct 2026, event 7 Nov. Nothing on the API. |
| qminers.com "Competitions & events" and blog | Confirms the Arena is new ("for the first time"). Nothing technical. |
| Quant Hackathon 2020, 2022, 2024, 2025 (CTU news pages, team repos BrystofKlazek, malek-luky, vitktor) | Task is sports betting. The layout of what they hand out is in the README. |
| `gh api orgs/qminers` | 404: no public GitHub org found. |

### Papers (titles and IDs checked against the arXiv API; PDFs checked with `pdfinfo` and `pdftotext`)

**Added to `literature_raw/` and `literature_md/` on 2026-10-10** (all free; the papers' first pages and one theorem were checked, the rest is **unread**):

| Paper | Source | Why |
|---|---|---|
| Huang, Lehalle & Rosenbaum, *Simulating and analyzing order book data: The queue-reactive model* | arXiv 1312.0563 | DTU shipped it for queue-aware quoting. (The first version of this log had the title wrong.) |
| Guo, Ruan & Zhu, *Dynamics of Order Positions and Related Queues in a Limit Order Book* | arXiv 1505.04810 | Queue position and fill probability, for the `--resting` model. |
| Moallemi & Yuan, *A Model for Queue Position Valuation in a Limit Order Book* | moallemi.com/ciamac/papers/queue-value-2016.pdf (SSRN 2996221 returns 403) | Treats a place in the queue as an asset with a value, and validates the model against backtest simulations (per its abstract). |
| Gould & Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book* | arXiv 1512.03492 | A simple, testable signal; complements the micro-price and order-flow-imbalance papers we have. |
| Guéant, *Optimal market making* | arXiv 1605.01862 | Many assets with inventory limits, the closest paper to a many-product Arena. hftbacktest's `Making Multiple Markets.ipynb` implements it. |
| Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* | davidhbailey.com/dhbpapers/backtest-prob.pdf (34 pp.) | How to test for a lucky "best of N" result, for `arena.grid` and capped submissions. |
| Bailey & López de Prado, *The Deflated Sharpe Ratio* | davidhbailey.com/dhbpapers/deflated-sharpe.pdf (22 pp.) | The same idea for a single selected result. |
| Bailey & Borwein et al., *Pseudo-Mathematics and Financial Charlatanism* | carmamaths.org/jon/backtest.pdf (34 pp.) | The readable one; Theorem 3.1 bounds the backtest length you need for N trials (`MinBTL < 2 ln N / E[max_N]^2`). |

**Seen, not added (free, but DTU found little use or the topic hasn't come up):**

| Paper | ID or URL | Verdict |
|---|---|---|
| Gatheral & Jacquier, *Arbitrage-free SVI volatility surfaces* | arXiv 1204.0646 | Conditional: DTU fitted a parabola to the smile and found full SVI added parameter risk. |
| Avellaneda & Lee, *Statistical arbitrage in the US equities market* | math.nyu.edu/~avellane/AvellanedaLeeStatArb071108.pdf (reachable) | Conditional: DTU shipped it only on the 50-product round. |
| Fodra & Labadie, *High-frequency market-making with inventory constraints and directional bets* | arXiv 1206.4810 | Conditional: quoting with a drift signal. |
| Lipton, Pesavento & Sotiropoulos, *Trade arrival dynamics and quote imbalance in a limit order book* | arXiv 1312.0514 | Skipped: overlaps Gould & Bonart. |
| Cartea, Donnelly & Jaimungal, *Enhancing trading strategies with order book signals* | Applied Mathematical Finance 2018; free accepted manuscript at King's College London (the repository reserves text-and-data-mining rights; the user downloaded it) | **Added 2026-10-11** to `literature_raw/` and `literature_md/order-book-signals/`. Only the definition of the imbalance `ρ` is checked against the PDF. |
| Leung & Li, *Optimal mean reversion trading with transaction costs and stop-loss exit* | arXiv 1411.5062 | Skipped: DTU's closed-form exits didn't beat a fixed z-score. |
| ABIDES, ABIDES-MARL | arXiv 1904.12066, 2511.02016 | Skipped: heavier than the question needs. |

**Triaged from a list of about 90 search results the user passed on (2026-10-13).** The first three and the two conditional ones were saved by the user the same day and are in `literature_md/` with source pages; the rest are not fetched. Titles and venues are as the list gave them; authors only where known, not checked. Get free versions (arXiv, SSRN, the authors' pages) or library copies only.

| Paper | Venue | Verdict |
|---|---|---|
| *Limit order trading with a mean reverting reference price* | Risk and Decision Analysis, 2017 | **Worth reading first.** A–S with a mean-reverting price: the case of a pegged product and of `contradictions.md` row 1 (does a skew help on a pegged product?). |
| Guilbaud & Pham, *Optimal high-frequency trading with limit and market orders* | Quantitative Finance, 2013 (SSRN 2011) | **Worth reading.** The spread is a tick-valued Markov chain, and the maker quotes at the best or one tick inside, and may cross: the template's discrete `make`/`take` choice, which the continuous-depth models miss. |
| Fernandez-Tapia, *High-frequency trading meets online learning* | Market Microstructure and Liquidity, 2016 (SSRN 2015) | **Worth reading.** Tunes A–S-style quotes by stochastic approximation while trading: a way to calibrate within a round when the Arena's data gives nothing beforehand. |
| Cont, Stoikov & Talreja, *A stochastic model for order book dynamics* | Operations Research, 2010 (SSRN 2008) | Maybe: fill probability before the mid moves, from queue sizes. Overlaps the micro-price and queue-imbalance papers. |
| *On optimal pricing model for multiple dealers in a competitive market* | Computational Economics, 2017 | Conditional: only if the Arena is a shared market between teams. |
| Guilbaud & Pham, *Optimal HFT in a pro rata microstructure with predictive information* | Mathematical Finance, 2013 | Conditional: only if the Arena matches pro-rata (probe 11). |
| *Instantaneous order impact and high-frequency strategy optimization in limit order books* | Market Microstructure and Liquidity, 2017 | Maybe: a discrete Markov chain on the last order and imbalance, with an optimal limit/market/cancel policy. |
| Lu & Abergel, *Order-book modeling and market making strategies* | Market Microstructure and Liquidity, 2018 | Maybe: argues Markovian book models misstate real participants, and backtests makers in a richer simulator. |
| Kearns et al., *Empirical limitations on high frequency trading profitability* | SSRN, 2010 | Maybe: market-order-only strategies earn little after costs, a prior against taking-heavy bots. |
| Cartea, Jaimungal & Ricci, *Buy low, sell high*; Cartea & Jaimungal on HMM regimes and on risk metrics | SIAM J. Fin. Math. 2014; Applied Math. Finance 2013; SSRN 2012 | Skipped: their book (`literature_md/algorithmic-and-hft/`) covers the same models. |
| *Optimal market making* (Guéant), the queue-reactive model, *Dynamics of order positions* | | Already in `literature_md/`. |
| HFT and market quality, regulation, Hawkes and SPDE scaling limits, LOB surveys, single-exchange empirical studies, a 2025 conference paper on MDPs | | Skipped: about whether HFT is good for markets, or maths without a strategy, or weak venues. |

**arXiv q-fin.TR sweep (2026-10-13).** Seventeen queries through the arXiv API, one per open question (competing makers, agent-based markets, tick size, fill probability, RL, adverse selection, inventory limits, mean reversion, baskets, signals, end-of-day liquidation, options, games, zero-intelligence books, calibration, trading competitions); 40 results each by relevance, 164 unique. The script was a scratch file; the queries are `cat:q-fin.TR AND abs:"market making" AND (...)` with the topic's terms. Most results are off-topic for us: automated market makers and DeFi, Kyle-model insider trading, bond and OTC dealers, deep RL on crypto data.

| arXiv | Paper | Verdict |
|---|---|---|
| 2502.18625 | Albers et al., *The market maker's dilemma* (live Binance experiment) | **Added**: `literature_md/market-makers-dilemma/` |
| 2407.16527 | DeLise, *The negative drift of a limit order fill* | **Added**: `literature_md/negative-drift-of-a-fill/` |
| 2101.03086 | Capponi, Figueroa-López & Yu, *Market making with stochastic liquidity demand* | **Added**: `literature_md/stochastic-liquidity-demand/` |
| 2211.00496 | Han, *Can maker-taker fees prevent algorithmic cooperation in market making?* | **Added**: `literature_md/algorithmic-cooperation-mm/` |
| 2206.05410 | Han, *Cooperation between independent market makers* | Seen: the same finding as 2211.00496, as a repeated game |
| 2307.15599 | Pulido, Rosenbaum & Sfendourakis, *Understanding the worst-kept secret of HFT* | Maybe: a maker who knows the efficient price quotes a predictive imbalance; for `book-imbalance-and-micro-price` |
| 1501.03756 | Passerini & Vazquez, *Optimal trading with alpha predictors* | Maybe: no-trade, make and take zones from a signal and linear costs |
| 2409.02025 | Cao et al., *Logarithmic regret in the ergodic Avellaneda–Stoikov model* | Maybe: learning κ online by maximum likelihood; next to Fernandez-Tapia |
| 2003.01820 | Spooner & Savani, *Robust market making via adversarial RL* | Maybe: an adversary as a proxy for rival bots |
| 1810.04383 | Bergault et al., *Closed-form approximations in multi-asset market making* | Skipped: Guéant 2017 (`optimal-market-making`) covers it |
| 2403.02572 | Lokin & Yu, *Fill probabilities with state-dependent order flows* | Skipped: overlaps the queue-reactive model |
| 2508.20225 | Barzykin et al., *Optimal quoting under adverse selection and price reading* | Skipped: dealer RFQ markets |
| 2607.17991 | Feil & Nendel, *Optimal market making in prediction markets* | Conditional: only if the Arena has binary-payoff products (UChicago 2026 had one) |
| 1907.11053, 2509.10094 | Baldacci et al.; Aïd et al. (several market makers, exchange as principal) | Skipped: about fee and contract design, not quoting |
| 2510.27334 | Jafree et al., *When AI trading agents compete* | Skipped: RL makers against medium-frequency meta-orders |
| 1112.0076 | Della Penna & Reid, *Bandit market makers* | Skipped: prediction-market cost functions |

**ICAIF 2025 proceedings, table of contents (2026-10-13).** The user saved the proceedings' front matter (`literature_raw/ICAIF_2025_proceedings.pdf`, 20 pages: committees, preface, contents; no paper texts, so no reference lists). About 110 titles, roughly nine in ten on LLMs, NLP, fraud, portfolios or insurance. The rest, checked against the arXiv API by title:

| Paper (ICAIF 2025) | Free copy | Verdict |
|---|---|---|
| Wang, Ventre & Polukarov, *Multi-agent RL for market making: competition without collusion* | arXiv 2510.25929 | **Added** (`literature_md/marl-competition-no-collusion/`). Conditional on a shared market: a maker trained to minimise its rival's PnL captures the flow and tightens spreads, the opposite of Han's tacit collusion; a "spiteful" bot matters when ranking is relative |
| *Data-driven trade flow decomposition for ETFs and their constituents* | none found (ACM, open access); the method's precursor is arXiv 2209.10334 | **Added** (`literature_md/etf-trade-flow-decomposition/`). Conditional on ETF or basket products (AlgoTrade had ETFs) |
| *From constituents to index: interpretable price movement prediction via cross-asset order flow* | none found (ACM, open access) | **Added** (`literature_md/cross-asset-order-flow/`); its premise tested on P3 baskets and dropped |
| Zhou et al., *DeltaLag: learning dynamic lead-lag patterns* | arXiv 2511.00390 | Skipped: deep learning on stock portfolios; lead-lag within a product family is already measured (`baskets-and-fixed-sums`) |
| *Attention-based multi-asset order flow networks for mid-price prediction* | none found | Skipped: a neural predictor, not a rule we can carry in a stdlib bot |
| Han, *Algorithmic pricing with independent learners and relative experience replay* | arXiv 2102.09139 | Skipped: the same collusion question as `algorithmic-cooperation-mm` |
| *Learning to scalp*, *Market selection with midpoint matching* (Wellman), *The accidental pump and dump* (Byrd), *Right place, right time* (execution), JaxMARL-HFT, DiffVolume | not checked further | Skipped: simulator or market-design studies without a quoting rule for us |

### Books and articles

The first pass had searched repos and listed books as "not tried". This is that search. **The finding is that the
winners' own sources point to few books.** DTU surveyed several dozen references, shipped 13, and
marked most of the rest "did not survive backtesting". Baguette Fromage shipped a linear skew, not
Avellaneda–Stoikov. So more reading has diminishing returns for strategy; the marginal gains are in *validation*
(Bailey et al.) and in *queue modelling* (the queue papers and articles), which feed our engine and process.

**Articles (all free). Rigtorp, Databento, the Quant.SE thread and Hummingbot's pages were first read through `WebFetch` summaries; since 2026-10-13 all have local copies (see the last column):**

| Article | Verdict | Notes |
|---|---|---|
| [Rigtorp, *Estimating order queue position*](https://rigtorp.se/2013/06/08/estimating-order-queue-position.html) | **Used** (`TODO.md`, `references/README.md`) | The probability model behind hftbacktest's `ProbQueueModel`. A decrease at your level is attributed ahead of you with `p = f(ahead) / (f(ahead) + f(behind))`. The URL was found in hftbacktest's source (our earlier guess was a 404). Local copy 2026-10-13: `literature_md/rigtorp-queue-position/`. |
| [Databento, *Getting queue position from L2 and order book data*](https://databento.com/blog/getting-queue-position-from-l2-and-order-book-data) | **Used** | Compares L2 estimates against order-by-order data: cancels come mostly from the back of the queue, and models that assume too little of that bias overstate passive fills. Our inference, not the article's: `f(x) = log(1 + x)` blames the back more than `f(x) = x` does (front 100, back 10: 9% behind with `x`, 34% with `log(1 + x)`), so it is the closer fit. Our `--resting` model sits at the pessimistic end. Local copy 2026-10-13: `literature_md/databento-queue-position/`, plus its tutorial in `online-snapshots/` (rendered with headless Chrome; its printed formula is the inverse of its code). |
| hftbacktest `examples/` notebooks (local) | **Already cloned**, newly listed | Worked examples of GLFT quoting, multi-asset quoting, queue-based quoting for large ticks, order-book imbalance as an alpha, and the probability queue models. Read these before writing a new quoting module. |
| [keanekwa/Optiver-Ready-Trader-Go](https://github.com/keanekwa/Optiver-Ready-Trader-Go) README (102★) | Read, **not cloned** | A team that ran their bots against each other in a shared simulator: arbitrage bots were "effective by themselves" but "performed poorly when put alongside other traders", so they moved to Avellaneda–Stoikov, which they found most reliable. Their inventory-adjusted mid trader did not beat the plain one, which echoes Baguette Fromage. Supports keeping `--vs`. One team's untested claim. |
| Hummingbot [guide](https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/) and [technical deep dive](https://hummingbot.org/blog/technical-deep-dive-into-the-avellaneda--stoikov-strategy/) on Avellaneda–Stoikov | Read through page-fetch summaries 2026-10-11 | Practical calibration of gamma and kappa: both are derived from the user's min/max spread, not estimated from the book. The RTG README's link to it (blog.hummingbot.org) no longer resolves. Saved 2026-10-13 as `online-snapshots/hummingbot-as-*.md` from the static HTML (`curl` works; the pages are mkdocs). |
| Quant.SE thread "How do we estimate position of our order in order book" | **Blocked** for the fetch tool; **used** | The fetch tool refuses `quant.stackexchange.com`. Cited by hftbacktest next to Rigtorp. Save it as a PDF into `literature_raw/` if wanted. Printed by the user 2026-10-13: `literature_md/quant-se-order-position/`. |
| Optiver's [explainers](https://www.optiver.com/insights/explainers/) | Listing read 2026-10-11 | 33 short primers; ten on options (pricing, Greeks, volatility), one on the order book. A free primer if options appear. |

**Books (paid, none bought; verdicts rest on blog reading lists of uneven quality, plus DTU's notes):**

| Book | Evidence | Verdict |
|---|---|---|
| Natenberg, *Option Volatility and Pricing* | Most-cited options book in the lists; one list says options market makers give it to new hires (not checked). | Only if options come back. DTU shipped the voucher round with Black–Scholes and a fitted smile (`references/prosperity4-dtu-quant-lab/round_3`). |
| Sinclair, *Option Trading* and *Volatility Trading* | An Optiver careers note (2022) says its in-house training used *Option Trading* for years. DTU read *Volatility Trading* and said it informed the smile fit. | Same condition. |
| Vidyamurthy, *Pairs Trading* | The same Optiver note recommends it for Ready Trader Go. DTU: "no cointegrated pair in the R3 mix". | Skip unless a pairs or basket round appears. |
| Chan, *Algorithmic Trading* | Beginner-friendly mean reversion and momentum. | Skip: generic. |
| Hasbrouck, *Empirical Market Microstructure* | A list calls it more quantitative than Harris. | Skip: Cartea et al. (already here) covers the maths. |
| Guéant, *The Financial Mathematics of Market Liquidity*; Lehalle & Laruelle, *Market Microstructure in Practice*; Bouchaud et al., *Trades, Quotes and Prices* (full book) | Fuller versions of papers and an excerpt we have. | Skip: paywalled, and the papers cover what a bot needs. |
| López de Prado, *Advances in Financial Machine Learning* | Its backtesting chapters overlap the Bailey papers. | Skip: the free papers carry the same ideas. |
| Aldridge, *High Frequency Trading*; Johnson, *Algorithmic Trading & DMA* | Generic introductions in the lists. | Skip. |

We only fetched papers that their authors host for free. `literature_raw/` already held the books (Harris, Cartea et al.).

## Used and not used

**Used (files changed):**
- `references/clone.sh` (ten repos), `README.md` (table rows, "Where to look", "Read online", reading order), this log, `check_arena_site.py`, `arena-site-snapshot.txt`.
- `references/wiki/` (written later the same day): a wiki built from reading the strategy code of the clones, in the LLM-wiki pattern (schema, index, log, source and concept pages, lint). Open leads that need the clones should start there; each source page ends with a "Read depth" section.
- `literature_raw/` and `literature_md/convert.sh` (eight papers), `literature_md/README.md`, and `references/README.md` (the two queue articles; a corrected statement of `ProbQueueModel`).
- `ON_THE_DAY.md`: "Known so far" rewritten from the site; the submissions, backtest-data and evaluation-data items; the bot-interface prior.
- `TODO.md`: the research item ticked; new items for the Prosperity 4 data, the conditional papers, the queue model (copy `ProbQueueModel` with `log(1 + x)`), a prior on inventory skew, and a grid item from the Bailey papers (count the trials). The first draft of the queue item stated the probability backwards (the code's `p` is the chance a decrease was *behind* the order); fixed after reading `queue.rs`.

**Not used, and why:**
- *Backtesters other than ours.* Ours matches prosperity3bt fill for fill, and the other P4 backtester copies add nothing we need except the data.
- *Strategy code.* Third-party team code has no licence. We read it for ideas, and `README.md` says not to paste it.
- *The Quant Hackathon's model.* A sports-betting model. Only the layout of what Qminers gave out matters, and only weakly.
- *Live-protocol kits (Jane Street ETC, Ready Trader Go).* Kept as models for an event-driven API, but the Arena's portal suggests a file upload.
- *Heavy simulators (ABIDES).* Heavier than the question needs.
- *The rest of DTU's reading list and the books above.* DTU killed most of it in backtests, and the books are paywalled with no evidence they changed a result.

## Methods that worked and didn't

**Worked:**
- `gh search repos --topic imc-prosperity-4 --sort stars --limit 25 --json ...` and `gh search repos "<phrase>" --sort stars`. Far better recall than `WebSearch`, which returned mostly noise for GitHub content.
- Reading a README without cloning: `gh api repos/OWNER/REPO/readme --jq .content | base64 -d`. Scan its headings first (`grep -n '^#'`), then read only the sections that matter.
- Checking the real size before cloning: sum the blobs from `gh api "repos/OWNER/REPO/git/trees/HEAD?recursive=1"`. GitHub's listed `size` understated chrispyroberts' repo by about 10 times.
- Community aggregators: `Ctrl-Alt-DefeatTheMarket/RESOURCES.md` lists previous top teams by rank for three editions.
- **Single-page apps:** fetch the HTML, find the `<script src>` bundle, fetch it, and pull out the string literals. This is what found the Arena rules. Quotes must be paired from a real string boundary, and short strings must still be matched, or the pairing flips (the bug the first version of `check_arena_site.py` had).
- `WebFetch` for blog posts and docs (hftbacktest docs, CTU news, UT Austin blog).
- The arXiv API over HTTPS (`https://export.arxiv.org/api/query?id_list=...`) to verify paper IDs. Plain HTTP returned nothing.
- **A short link that serves a page instead of redirecting** (`lnkd.in/...`): `curl` the page and grep its HTML for the destination URL. That found the AlgoTrade winners' repo.
- **Public Notion pages**: `references/fetch_notion.py` calls the JSON endpoints a browser uses and writes markdown. Page-name collisions, synced blocks and anchor links needed fixes; check the output for tiny pages.
- **Repos too big to clone** (CMU Physics 1.2 GB, Leo-Hawking 245 MB): `gh api repos/OWNER/REPO/readme --jq .content | base64 -d` saves the README into `references/online-snapshots/`, so wiki citations stay checkable.
- **Take references from sources that already won:** DTU's `literature_review.md` (shipped vs dropped, with reasons) and the links inside hftbacktest's example notebooks and source docstrings (that is where the Rigtorp URL came from). Far better than a blind search.
- OpenAlex (`api.openalex.org/works?search=...`, no key) to check that a paper exists and has an open PDF. Search for the exact title; the default relevance order is fine.
- Testing a PDF link with `curl -sIL` (status and content type), then downloading into a fresh directory and confirming with `pdfinfo` and `pdftotext -l 1` that it is the paper, before moving it to `literature_raw/`.
- `WebFetch` works on rigtorp.se and databento.com.

**Didn't work:**
- `WebFetch` on Medium (403), Notion (returns only "Notion"; `references/fetch_notion.py` reads public Notion pages through their JSON endpoints instead), and SPAs in general.
- `WebSearch` for "winning bot" or "write-up" for AlgoTrade, Ready Trader Go and the Jane Street ETC: nothing public that we could find.
- `gh search repos` with `OR` in the query, and `--owner qminers` (no such org).
- `gh search repos` queries for AlgoTrade: five phrasings returned nothing.
- **Pages that need JavaScript** (Databento's docs) come back empty from `WebFetch` and `curl`. Headless Chrome renders them: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --virtual-time-budget=15000 --dump-dom URL` (or `--print-to-pdf=FILE`). Static sites (Hummingbot's mkdocs) work with plain `curl`.
- `WebFetch` refuses some domains outright (`quant.stackexchange.com`, `web.archive.org`) and gets 403 from Medium. For those, ask the user to print the page to PDF into `literature_raw/`.
- Guessing URLs from memory (Rigtorp's article, `davidhbailey.com/dhbpapers/pseudo-math.pdf`): both 404. Find the link in a source that cites it.
- Semantic Scholar's unauthenticated API: HTTP 429 on every query.
- OpenAlex with `sort=cited_by_count:desc`: returns unrelated, highly cited papers. Do not sort by citations on a fuzzy search.
- `WebSearch` for book recommendations: returns commercial interview-prep listicles. No official IMC, Optiver or Qminers reading list exists that we could find.
- PDFs behind 403 for `curl`: ams.org Notices, escholarship.org, SSRN. Look for an author-hosted copy (davidhbailey.com, carmamaths.org, moallemi.com).

## Open leads

In rough order of value for the effort:
1. **Read what's already cloned.** The suggested order is in `README.md`; `references/wiki/index.md` says where things are, and each source page's "Read depth" says which parts were never read. This is worth more than another search.
2. **Re-run `references/check_arena_site.py` before the event** (and whenever the organisers e-mail). It costs almost nothing and shows rule changes.
3. **Unread but promising:** YBansal95 and JackRao123 (P3 10th and 19th), and the unread parts of heyman7913, CMU Physics and Leo-Hawking (listed on their wiki pages).
4. **Ingest the AlgoTrade winners' repo and the downloaded Prosperity wikis** into `references/wiki/` as source pages (`references/algotrade2026-negative-eevee/`, `references/prosperity-wikis/`).
5. **The queue TODO's reading:** the hftbacktest "Probability Queue Models" and "Queue-Based Market Making in Large Tick Size Assets" notebooks and Moallemi & Yuan (now in `literature_md/`). Rigtorp and Databento are done.
6. **Papers by venue instead of by title** (the user's idea, 2026-10-13), if a question comes up that the wiki can't answer. Better than keyword search because a venue is already filtered for the topic. In order: arXiv's q-fin.TR (Trading and Market Microstructure) listing, which the agent can query itself through the arXiv API; the ACM ICAIF proceedings (AI in finance: market simulators, agent-based markets and RL market making, the closest to a bot-filled Arena; ABIDES came from there); the *Market Microstructure: Confronting Many Viewpoints* conference volumes (Wiley, 2012 onward); the journals *Market Microstructure and Liquidity*, *Quantitative Finance* and *Algorithmic Finance*. Citation chasing from the bibliographies of the books we have (Bouchaud et al., Cartea et al.) is the cheapest of all. Search with a question in hand, not to collect.
7. **If the interface turns out to be event-driven:** find the Ready Trader Go Python kit (2021 to 2022 editions) and the Jane Street ETC wrappers, and build a callback adapter.
8. **Manual-round practice:** gabsens/IMC-Prosperity-2-Manual and the manual sections of the P3 and P4 write-ups, if the Arena has manual-style puzzles. Nothing says it does.
9. **Books:** searched, see the table above. None is worth buying now. If a round brings options, Natenberg or Sinclair become worth a look, and DTU's `round_3` code is the quicker start.
10. ~~**Read the eight new papers properly.**~~ Done 2026-10-12 for all papers except Kelly, Gould et al. 2013 and the Bouchaud excerpt: each has a source page in `references/wiki/sources/` saying which formulas were checked against the PDF.
11. ~~**Check the rest of Cartea, Donnelly & Jaimungal's formulas against the PDF.**~~ Done 2026-10-12 (`references/wiki/sources/order-book-signals.md`). The Hummingbot A–S formulas were checked on 2026-10-13 against the published A–S, which replaced our preprint (`references/wiki/sources/hummingbot-avellaneda-stoikov.md`).

## Do not repeat

- Searching Prosperity topics on GitHub (`imc-prosperity`, `-2`, `-3`, `-4`): done to the top 25 by stars each, plus the queries "imc prosperity 2", "imc prosperity 3", "imc prosperity backtester".
- `WebSearch` for Qminers Arena information: returns the registration form, the listing and the CTU pages, all seen.
- The registration form (it only says "capacity of competition was reached") and Czech or Matfyzák searches (they return only the CTU hackathon pages; one search summary even claimed the Arena doesn't exist, which the site itself disproves).
- Fetching `arena.qminers.com` with `WebFetch` (returns the title only). Use `check_arena_site.py`.
- Searching for book recommendations (done: only blog listicles; the verdicts are in the Books table) and ranking papers by citation counts (Semantic Scholar is rate-limited, OpenAlex sorts badly).
