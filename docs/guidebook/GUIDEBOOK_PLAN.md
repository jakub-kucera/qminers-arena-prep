# The guidebook: build plan for the full book (for the auditor to check)

2026-11-04. Phase 2 of `docs/guidebook/PROPOSAL.md` (its option B): the full guidebook, written after the event, from the
field guide's sources (`FIELD_GUIDE_PLAN.md`), which it grows rather than replaces. Same decisions as the field guide
(the proposal's §10): Quarto, the recommended structure (a spiral of question-titled chapters, each opening on a true
story), the audio text and a voice track. This file says what the book will hold and how to check it; nothing here is
written yet.

## What it is

About 125 pages (about 45k words, 5 hours of audio): a preface, sixteen chapters in five parts, five appendices. The
field guide's ten chapters become ten of the sixteen at about twice the length; six chapters are new. The Arena's real
rounds, which the field guide can't have, run through every chapter as the main case study, next to the three markets
the prep used.

**Started** 2026-11-04 at the user's request, before the event: everything not marked "(Arena)" is written now, and
each chapter's "On the Arena" box says it is written after the event. **The Arena parts start when** the event is over
and its four `data/arena/round*/HANDOVER.md` notes and `leaderboard.json` exist.

**State, 2026-11-04:** every chapter and appendix not marked "(Arena)" is written, each part fact-checked by a second
agent against its primary sources and fixed (commits 28a8bb6 to f29890d): 129 A4 pages, about 44,000 spoken words.
Every CSV and figure reproduces from `make_data.py` and `make_figures.py` run in full. The re-runs moved 17 `IDEAS.md`
rows (dated notes added) and corrected `ON_THE_DAY.md`'s hidden-depth figure, two wiki pages and `rust/README.md`'s day
count. Left: the "(Arena)" parts after the event, and the user's read.

**Where it lives:** `docs/guidebook/book/`, one Quarto project for both books, which share `data/`, `figures/` and
`scripts/`. The guidebook's chapters are `book/guidebook/<nn>-<name>.qmd` (its preface `book/guidebook/_preface.qmd`),
listed in `_quarto-guidebook.yml`; `quarto render --profile guidebook` builds it into `_out/guidebook/`, and
`scripts/audio.sh guidebook` and `scripts/voice.sh guidebook` its audio into `_out/audio-guidebook/`. `index.qmd`
shows each book's preface by profile. The field guide's chapters (`book/fieldguide/`) stay as they are, the edition
read before the event.
Chapter 16 and appendix E are only as good as those notes, which are written on 7–8 Nov (RUNBOOK, "Each round",
deadline − 0:10).
**Done when:** every chapter below is written, the auditor's checklist (end of this file) holds for all of them, and the
HTML, PDF, EPUB, audio text and m4b build from a clean checkout.

## How it differs from the field guide

| | Field guide | Guidebook |
|---|---|---|
| Length | about 35 pages, 13–14k words | about 125 pages, about 45k words |
| Chapters | 10 (★ in the proposal's §5) | 16, plus five appendices |
| Markets | Prosperity, `arena.sim`, ABIDES, the mock rounds | the same, plus the Arena's four rounds (and LOBSTER if it arrives) |
| Per chapter | the story, the idea, ≤2 formulas, four boxes | the same, plus "What would differ on another market" (Parts II and IV), a worked example with the code, and "On the Arena" in place of "On the day" |
| Models | named in a sentence | each model's one formula and what our tests found (Avellaneda–Stoikov, Glosten–Milgrom, Kelly, Black–Scholes) |
| Statistics | PBO and held-out days | PBO, DSR, SPA, StepM, the permutation test, the `pick`, and why we read them at 4% |

## Chapters

Words are targets. Stories are numbered as in `research/stories.md` (R = its runners-up). F-figures are the field
guide's (`FIELD_GUIDE_PLAN.md`), reused; G-figures are new. "(Arena)" marks what needs the event's data.

**Preface: how to read this** (400). Who it is for, the four markets, the chapter furniture, the audio edition.

### Part I. The game

| # | Question | Words | From the field guide | Stories | Figures |
|---|---|---|---|---|---|
| 1 | What happens in a round? | 1,800 | ch. 1, grown | 15 (Varde, end to end); the Arena's round 1 (Arena) | F1 the round's loop; G1 the Arena's round 1 as it went, from its HANDOVER (Arena) |
| 2 | What is an exchange? | 2,800 | ch. 2, grown | the portal's identity (Varde Session 1); R "hidden depth", a misreading (AlgoTrade's ZSE: 34.0% of 1.41M prints outside the three levels a recording kept, of the five the API sent) | F2 an order book; F3 the score's parts; G2 the three data shapes (snapshots, an event log, prints with an aggressor flag) becoming our `Day` of `Tick`s |

Chapter 2 adds the data shapes, matching rules in full (price-time priority, what a take does, what rests), position
limits and how each exchange enforces them, and the Arena's own format (Arena).

### Part II. Why market making pays, and when it doesn't

| # | Question | Words | From the field guide | Stories | Figures |
|---|---|---|---|---|---|
| 3 | What is the price? | 2,400 | ch. 3, grown | 21 (a rival's 40-lot order); 12 (the flaw that was the alpha) | F4 mid against wall mid; G3 the signature plot (variance of h-tick returns over h) for Kelp, Resin and an ABIDES day |
| 4 | Why does a market maker earn anything? | 2,600 | ch. 4, grown | 22 (copies); 25 (paying for more competition) | F5 a round trip; F6 income against copies; G4 the Bouchaud margin s/2 − R∞ per product, Prosperity against ABIDES |
| 5 | Who is on the other side? | 2,800 | ch. 5, grown | 3 (ABIDES); 8 (Olivia); 9 (the Marks); 17 (−1.48M resting on jumpy products) | F7 real against shuffled; G5 markouts by horizon, Kelp against ABIDES; G6 Olivia's 19 trades on Squid Ink's price |
| 6 | What does holding a position cost? | 2,400 | new | 18 (Kelp's long position is the flow); 19 (DTU's skew cost 16.6k, their claim) | G7 the mirror test: Kelp's position and its mirror; G8 PnL against `skew` under `all` and `worse` |
| 7 | What do the prices do? | 2,600 | new (F8 moves here from ch. 5) | 13 (`smile_window`); 20 (the fixed anchor that kept buying); R the stress test (81.3k to 19.6k with a trend) | F8 the smile window; G9 the residual's lag-1 autocorrelation against the window; G10 `arena.stress`'s perturbed days |

Chapter 6 holds inventory risk, the skew and Avellaneda–Stoikov in words; chapter 7 mean reversion, trends, levels,
jumps, regime change and a signal's timescale.

### Part III. Beyond plain market making

| # | Question | Words | From the field guide | Stories | Figures |
|---|---|---|---|---|---|
| 8 | What else can a bot trade? | 2,600 | new | 5 (Linear Utility's unhedged delta, 2nd to 26th); 23 (last year's data, R² 0.99); 4 (quoting 100 away on an empty side, their claim) | G11 a basket's spread against its legs over a day; G12 P3's voucher smile (implied vol against strike) |
| 9 | Who else is in the market? | 2,400 | new | 21 (the spoofer 10 ticks behind the best: Kelp 16.8k → −2.1k); R crowding (Negative Eevee); 24 (a logger that wiped the memory) | G13 `experiments.day.rival_field`'s outcomes per rival; G14 the `GRAY_AREA` gate (diagram) |

Chapter 8 covers target modes, baskets, options (Black–Scholes in a page, implied vol, delta) and copying informed
traders. Chapter 9 covers shared markets, the LLM zoo, spoofing, gray areas and the gate that stops them being
submitted by accident.

### Part IV. How we know

| # | Question | Words | From the field guide | Stories | Figures |
|---|---|---|---|---|---|
| 10 | Why is my backtest lying? | 2,600 | ch. 6, grown | 1 (opposite conclusions under two fill models); 2 (+2,415 against +436, their claim); 16 (taken volume stays gone, −27%); 14 (the late orders) | F9 PnL under each fill model; G15 the fill curve (fill rate against distance from the touch); G16 PnL against `--delay` |
| 11 | How do I know a result is real? | 2,800 | ch. 7, grown | 9 (the Marks); 10 ("the result was a disaster"); 11 (96% of a product's profit on one day) | F10 the grid under two fill models; F11 days as folds; G17 the permutation test's null with the real best marked; G18 CSCV's splits (diagram) |
| 12 | What does the portal tell me? | 2,200 | ch. 8, grown | 15 (the 28% fee); the Arena's own calibrate run (Arena) | F12 calibrate's errors; G19 the same on the Arena's first upload (Arena) |
| 13 | How should I size risk? | 2,600 | new (part of ch. 10's story moves here) | 6 (halving the stake); 7 (Frankfurt's relative hedge); 26 (the frozen exchange); 11 again (sizing a fragile edge at 0.06) | G20 rank against the stake in a simulated final (a small Monte Carlo in `make_data.py`); G21 the rounds' weights and what each round's PnL is worth (Arena) |

Chapter 10 covers fill models (`all`, `worse`, `none`), resting orders and queues, delay, depletion and marks. Chapter
11 covers overfitting in ML terms: the grid as hyperparameter search, held-out days, neighbourhood and worst day, PBO,
DSR, SPA, StepM, the permutation test and the `pick`. Chapter 12 covers the twelve metrics and calibrate as system
identification. Chapter 13 covers scoring rules, rank against PnL, protecting a lead, round weights and carry-over.

### Part V. The repo

| # | Question | Words | From the field guide | Stories | Figures |
|---|---|---|---|---|---|
| 14 | How is the code laid out? | 2,400 | ch. 9, grown | 14 (an ADAPTER bug, not a strategy) | F13 the architecture; G22 one tick through the template (fair → take → clear → make → EXECUTION → ADAPTER) |
| 15 | What does each parameter do? | 2,200 | new | R the stress test; one kept and one dropped row read in full | G23 the parameters by group, coloured by verdict (kept, dropped here, open) |
| 16 | What did we do on the day? | 1,800 | ch. 10, rewritten as what happened | the Arena's four rounds (Arena) | F14 the day's timeline, as planned and as it went (Arena) |

Chapter 15 is mostly a table (`research/repo_map.md`, C): the printed edition keeps it, and the audio reads a summary
of it.

### Appendices

| | Appendix | Words | Audio |
|---|---|---|---|
| A | Glossary in two columns: the market term and its ML neighbour (the field guide's, grown) | 1,500 | read |
| B | The datasets: Prosperity 2–4, `arena.sim`, ABIDES, LOBSTER, the mock rounds, the Arena; and what the zoo is (bots, not data) | 1,200 | read |
| C | The commands on one page | 600 | printed only |
| D | The reading route (the proposal's §8, with what each step adds after this book) | 800 | read |
| E | The Arena, round by round: rules, data, what we submitted, scores and rank, what we'd change (Arena) | 2,000 | read |

**Total:** about 45k words: 400 for the preface, 39,400 for the chapters, 6,100 for the appendices.

## Formulas, each with its spoken sentence

About 20, at most two a chapter. The field guide's seven carry over. Every one from the literature is checked against
its PDF page before it is written (`python3 literature_md/pdfpage.py <slug> <line>`; CLAUDE.md's rule), and that page
is cited in the chapter.

| Ch. | Formula | Spoken | Source to verify against |
|---|---|---|---|
| 2 | PnL = cash + position × price | profit is the cash, plus what the position is worth at the price | ours (`arena.engine`) |
| 3 | mid = (best bid + best ask) / 2; wall mid = (bid wall + ask wall) / 2 | (the field guide's) | ours |
| 3 | micro-price, to first order: mid + spread × (I − ½), with I = bid size / (bid size + ask size) | the micro-price leans the mid toward the side with less size, by up to half the spread | `micro-price` (Stoikov) |
| 4 | maker's gain per trade = s/2 − R∞ | (the field guide's) | `trades-quotes-prices` ch. 17 |
| 5 | markout at h = side × (mid in h ticks − fill price) | (the field guide's) | ours (`arena.analysis`); `negative-drift-of-a-fill` |
| 5 | Glosten–Milgrom: the spread grows with the share of informed traders | (the sentence is the formula; one line of algebra in the print) | `trades-quotes-prices` ch. 16 |
| 6 | reservation price r = s − q γ σ² (T − t) | the price a maker quotes around falls by its position times its risk aversion, the variance and the time left | `hft-in-a-limit-order-book` (Avellaneda–Stoikov) |
| 7 | half-life = ln 2 / κ, for a price pulled back at rate κ | the half-life is how long the price takes to close half its gap to the level | `mean-reverting-reference-price` |
| 8 | basket spread = basket − Σ wᵢ × legᵢ | the spread is the basket's price less the weighted sum of its legs | ours (the template's `basket` mode) |
| 8 | Black–Scholes delta = N(d₁) | an option's delta is how many units of the underlying move with it, the normal curve's area up to d-one | the source the wiki's `options-and-vouchers` page cites for it |
| 10 | our `--queue prob` rule: a cancellation lands ahead of us with probability x^N, x our share of the queue ahead, N `--queue-power` | a cancel is more likely to come from ahead of us the more of the queue is in front | ours (`python/arena/cli.py`'s `--queue-power`, the engine); the wiki's `queue-position-and-fills` page for the rule it came from |
| 11 | PBO = P(the in-sample best ranks below the median out of sample) | (the field guide's) | `probability-of-backtest-overfitting` |
| 11 | DSR: the Sharpe ratio deflated by the number of trials | (the sentence; the full expression in the print only) | `deflated-sharpe-ratio` |
| 12 | pnlSe = sd of the session scores × √n | (the field guide's) | ours (`calibrate`; the portal) |
| 13 | Kelly: f* = edge / odds | bet the fraction of your bankroll equal to your edge over the odds | `kelly-criterion` |
| 13 | VaR sizing: size so the 95% loss is a set share of the lead | (the sentence is the formula) | Frankfurt's README:759 |

## Figures

Every chart reads a CSV in `book/data/`, shared with the field guide, made by
`scripts/make_data.py` from committed commands; `scripts/make_figures.py` draws them all, diagrams included. A new
G-figure needs both a `make_data.py` step and a `make_figures.py` function, and its command goes in the caption's
source line.

| Figure | Data | Made by |
|---|---|---|
| G1 the Arena's round 1 (Arena) | the round's HANDOVER and upload log | **hand-entered** CSV from `data/arena/round1/HANDOVER.md`, the exception to the committed-command rule: the caption says so and cites its lines |
| G2 the data shapes | none | diagram |
| G3 the signature plot | P3 round 1, one ABIDES day | `load_days`; the variance of h-tick mid changes over h |
| G4 the Bouchaud margin | IDEAS "Does making pay" (L172) | its command |
| G5 markouts by horizon | P3 round 1 Kelp, ABIDES | `arena.backtest --out` then `arena.analysis`'s markouts |
| G6 Olivia's trades | P3 Squid Ink, three days | `load_days`, her trades by counterparty |
| G7 the mirror test | IDEAS "Kelp's long position" (L166) | its command, a mirrored day |
| G8 PnL against `skew` | P3 round 1 Kelp | `arena.grid --grid PARAMS.KELP.skew=... --modes all,worse` |
| G9 the residual's autocorrelation | P2 round 4's coupon | the IDEAS row's command (L264) |
| G10 perturbed days | P3 round 1 | `arena.stress` |
| G11 a basket's spread | P3 round 2 | `load_days` |
| G12 the voucher smile | P3 round 3 | `experiments.day.p3_smile` |
| G13 the rival field | P3 round 1 | `experiments.day.rival_field` |
| G14 the gate | none | diagram |
| G15 the fill curve | P3 round 1 | `experiments.day.fill_curve` |
| G16 PnL against delay | P3 round 1 | IDEAS "Orders that arrive a tick late" (L200), its command |
| G17 the permutation null | P3 round 1 Kelp | `arena.grid ... --permute 20` |
| G18 CSCV's splits | none | diagram |
| G19 calibrate on the Arena (Arena) | the Arena's first upload | `experiments.day.calibrate` through the day's plug-in |
| G20 rank against the stake | a simulated final | a Monte Carlo in `make_data.py` (seeded), after the Qminers 2024 winner's method |
| G21 the rounds' weights (Arena) | the rounds' real weights and our rounds' PnL | parsed from `data/arena/round*/leaderboard.json` by `make_data.py`; the weights from the Technical Rules, cited |
| G22 one tick through the template | none | diagram |
| G23 the parameters by verdict | `IDEAS.md`'s rows | parsed from `IDEAS.md` by `make_data.py` |

Line numbers like L166 are `IDEAS.md`'s on 2026-11-04 (`research/repo_map.md`, C). The writer finds each row by its
name, since the file's lines will have moved.

## How it gets written

1. **Brief:** the proposal, the research dossier, this plan, the field guide as built, and the four HANDOVERs.
2. **Grow one chapter first,** chapter 10, from the field guide's chapter 6, for the user to read (done 2026-11-04:
   `book/guidebook/10-backtest.qmd`, with G15 and G16 and the queue formula, about 2,300 spoken words). Its depth and length
   set the rest.
3. **Chapters in order,** each with its figures and data steps. Each new chapter has a sample read by the user before
   the next part starts.
4. **A fact-check pass by a second agent** (the checklist below), re-running every command that takes under ten minutes.
5. **Builds:** HTML, PDF, EPUB, the audio text, the voice and the m4b, as the field guide's scripts do.

**Effort:** two to three weeks part-time (the proposal's §9), with the user's review after each part.

## Checklist for the auditor

The field guide's eight points (`FIELD_GUIDE_PLAN.md`), for every chapter, and:

9. Every "(Arena)" item uses the event's data, not a prep number standing in for it, and says which round.
10. Each formula from the literature cites the PDF page it was checked against.
11. Each chapter in Parts II and IV has its "What would differ on another market" paragraph, naming at least two of
    the five markets.
12. Every "dropped here" result is stated as a Prosperity result with its re-test, never as "this doesn't work".
13. The field guide's text, where it survives, is still true after the event. Anything the Arena contradicted is
    rewritten, and the contradiction is a story.
14. Chapter 15's table matches `IDEAS.md`'s verdicts on the day the book is built (`make_data.py` parses them, so a
    rebuild shows a change).
