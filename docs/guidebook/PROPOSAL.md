# A guidebook to this repo and the trading behind it: proposal

2026-11-04. For the user, and for whoever writes it (the auditor, or another agent session). The research behind it is in
`docs/guidebook/research/`: the reader (`reader_profile.md`), the literature and *Trades, Quotes and Prices*
(`literature_map.md`), the repo (`repo_map.md`), 26 true stories with sources (`stories.md`) and the build tooling
(`tooling.md`).

## 1. The idea, and the one constraint that shapes it

A guidebook is worth writing. The repo's knowledge is spread over about 840 KB of working documents (IDEAS, ON_THE_DAY,
the wiki's 23 concept pages and 97 source pages, 71 converted papers and books), written as a lab notebook for agents,
not as an explanation for a person. Nothing in it says, in order, what a market maker is, why it earns, why it loses,
how we measure that, and where each piece lives in the code.

The constraint is the date. The event starts in three days (7 Nov), and a 100-page book written well, checked and read
does not fit before it. So the proposal is two phases:

- **Phase 1, before the event: a field guide** (30–40 pages, about 2 hours of reading or listening). Only what changes
  how you work on the day: the order book, why making pays and when it doesn't, fill models and why the backtest lies,
  overfitting in ML terms, the portal's metrics and calibrate, and a map of the repo for the day's path.
- **Phase 2, after the event: the guidebook** (100–130 pages). The full structure below, rewritten with the Arena's real
  rules, data and results, which will be the best case study it can have. Dataset-agnostic by then for real: four
  markets as examples (Prosperity, our simulator, ABIDES, the Arena).

A 200+ page book (option C below) isn't worth it: the reference shelf already exists (Bouchaud, Cartea, Harris), and the
guidebook's job is to be the path through it.

## 2. Who it is for

From `research/reader_profile.md`: strong applied ML and statistics (time series, Markov chains, Bayesian optimisation
against a simulator, hyperparameter search, cross-validation), four years of engineering, one sports-betting hackathon;
no order books, market making, adverse selection, impact or stochastic control. So:

- **Assume** probability, statistics, overfitting, search and simulators. Don't explain a standard error or a Poisson
  process.
- **Build from zero** the market: books, matching, the spread, adverse selection, inventory.
- **Give intuition, not derivations,** for the models (Avellaneda–Stoikov, Glosten–Milgrom, Kyle): what each says, the one
  formula that matters, and what our tests found. No HJB equations.
- **Use ML analogies where they are honest,** in a short box per chapter ("If you know ML"):

| Trading idea | The ML idea it resembles | Where the analogy breaks |
|---|---|---|
| A backtest's fill model | a simulator's sim-to-real gap | the gap is one-sided: optimistic fills always look better |
| Adverse selection | selection bias: the fills you get are the ones that hurt | it is adversarial, not random |
| A grid over PARAMS | hyperparameter search | days are few and correlated: 3 folds, not 1,000 |
| Held-out days, leave-one-day-out | time-series cross-validation | the scored day may come from another generator |
| PBO, DSR, SPA, StepM | multiple-comparison corrections for HPO | the test statistic is a PnL path, autocorrelated |
| `calibrate` | system identification, fitting a simulator to logs | twelve aggregate figures, not the hidden state |
| The LLM zoo | baselines and an ensemble of competitors | they are rivals, not models to average |
| ABIDES and the shuffle test | out-of-distribution evaluation, a permutation test | |
| Inventory skew | a regulariser on position | it costs return when the flow is uninformed |

## 3. Length options

| Option | Pages | Words | Audio | Depth | Fits |
|---|---|---|---|---|---|
| **A. Field guide** | 30–40 | 12–15k | about 1.5–2 h | one idea per section, a story each, the day's commands | before 7 Nov |
| **B. Guidebook** | 100–130 | 35–45k | about 4–5 h | each concept with its evidence, code walkthroughs, the catalogue of techniques | after the event, 2–3 weeks part-time |
| C. Book | 200–250 | 80k | about 9 h | exercises, derivations, a chapter per model | not recommended |

Recommended: A now, B later. A is a strict subset of B's structure (marked ★ in §5), so nothing written for A is thrown
away.

## 4. Structure options

Five ways to order it, then the recommended mix.

1. **Bottom-up (textbook):** order book → prices → market making → adverse selection → inventory → evaluation → the repo.
   Clean dependencies, but the reader waits 60 pages to see why any of it matters. This is how *Trades, Quotes and
   Prices* reads, and the reason it felt long.
2. **Top-down (from the day):** open with a round from start to finish, then drill into each component. Motivating,
   but the first chapter has to use terms it hasn't defined.
3. **Spiral (three passes):** a one-chapter tour of everything at low resolution, then the concepts, then the repo and the
   evidence. Each pass revisits the same ideas deeper. Good for a reader who wants the map first, which this one does.
4. **Case-based:** each chapter opens with a story (`research/stories.md`) and derives the concept from it ("the bot made
   +4.5M on shuffled days and lost money on real ones: why?"). Memorable, and good for audio; can be uneven on its own.
5. **Question-driven:** each chapter answers one question: "Why does a market maker earn anything?", "Why is my backtest
   lying?", "How do I know a grid result is real?", "What does the portal's `pnlSe` mean?". Good as an index, thin as a
   narrative.

**Recommended mix: a spiral skeleton (3), with chapters titled as questions (5), each opening on a story (4).** Part I is
the top-down tour (2) in one chapter; Parts II–IV are the concepts bottom-up (1) but each starts from a case; Part V maps
the repo. Every chapter has the same furniture, which also makes the audio edition easy to navigate:

- the story (a paragraph, with its number);
- the idea in plain words;
- at most one or two formulas, each with a sentence that says it aloud;
- "If you know ML" (the analogy and where it breaks);
- "In the repo" (the file, the parameter, the command, the IDEAS row);
- "On the day" (what to run or check);
- "Go deeper" (one or two sections of the literature, with page ranges).

## 5. Proposed contents (B; ★ = in the field guide A)

**Part I. The game**
1. ★ *What happens in a round?* A whole round from the Varde rehearsal (data, bot, upload, metrics, calibrate's refusal,
   the hidden score), in 15 minutes of reading. Defines every term the rest uses, loosely.
2. ★ *What is an exchange?* The order book, levels, ticks, orders, fills, position limits, PnL. The three data shapes
   (snapshots, an event log, prints with an aggressor flag) and how every format becomes our `Day` of `Tick`s. Story: the
   portal's identity, score = cash + position × mark (the dashboard's Session 1: cash −€2,815, position +€2,925).

**Part II. Why market making pays, and when it doesn't**
3. ★ *What is the price?* Mid, wall mid, micro-price, a smoothed fair; noise against signal (the signature plot). Story: a
   rival's far 40-lot order moved the fair 44 ticks (`sized_mid`'s reason).
4. ★ *Why does a market maker earn anything?* The spread as a fee for immediacy; the break-even `s/2 − R∞`; when it pays
   (uninformed flow) and when it doesn't. Story: two copies of the bot halve each other's income (the spread as a
   shared rent).
5. ★ *Who is on the other side?* Adverse selection, informed flow, markouts. Stories: ABIDES, where the playbook lost and
   the shuffle test made +4.5M; Olivia on Squid Ink; the Marks that weren't informed.
6. *What does holding a position cost?* Inventory risk, skew, Avellaneda–Stoikov in words, and why it lost here. Stories:
   Kelp's long position is the flow; DTU's textbook skew cost 16.6k.
7. *What do the prices do?* Mean reversion, trends, levels, jumps, regime change; the timescale of a signal. Stories:
   `smile_window` 20 against 5,000 (−266k to +442k); DTU's fixed anchor that kept buying.

**Part III. Beyond plain market making**
8. *What else can a bot trade?* Directional bets toward a target, baskets and their spreads, options (Black–Scholes in a
   page, implied vol, delta), copying informed traders. Stories: Linear Utility's unhedged delta (2nd to 26th).
9. *Who else is in the market?* Shared markets, rival bots, the LLM zoo, spoofing, gray areas and the `GRAY_AREA` gate.
   Stories: paying for more competition (the median bid of 50); hidden liquidity on empty book sides.

**Part IV. How we know**
10. ★ *Why is my backtest lying?* Fill models (`all`, `worse`, `none`), resting orders and queues, delay, depletion,
    marks. Stories: +2,415 local against +436 live; the same days and opposite conclusions under two fill models; −1.48M
    resting on jumpy products; the late-orders rehearsal.
11. ★ *How do I know a result is real?* Overfitting in ML terms: the grid as hyperparameter search, held-out days,
    neighbourhood and worst day, PBO, DSR, SPA, StepM, the permutation test, the `pick`; why we read the tests at 4%.
    Stories: "the result was a disaster"; 96% of a product's profit on one day.
12. ★ *What does the portal tell me?* The twelve metrics (the dashboard), calibrate as system identification, refusing a
    bad fit. Stories: the fee that was 28% of the gross; whether taken volume stays gone (−27%).
13. *How should I size risk?* Scoring rules, rank against PnL, protecting a lead, round weights and carry-over. Stories:
    halving the stake kept first place (Qminers 2024); Frankfurt's relative hedge; UChicago's frozen exchange.

**Part V. The repo**
14. ★ *How is the code laid out?* The architecture diagram (`research/repo_map.md`, A), the engine and its format
    plug-ins, the template's STRATEGY / EXECUTION / ADAPTER, the tools around it, the Rust twins, the wiki.
15. *What does each parameter do?* The template's parameters, grouped (`research/repo_map.md`, C), with each one's
    verdict from IDEAS and how to read an IDEAS row.
16. ★ *What do I do on the day?* RUNBOOK as a flowchart: the format swap, the probes, the kickoff prompts, the round's
    protocol, the handover.

**Appendices:** a glossary in two columns (the market term and its ML neighbour); the datasets (Prosperity 2–4, our
simulator, ABIDES, LOBSTER, the mock rounds, and what the zoo is: bots, not data); the commands on one page; the reading
route (§8).

**The field guide A** is chapters 1–5 and 10–12, 14 and 16 at half length, plus the glossary: about 35 pages.

## 6. Dataset-agnostic, in practice

- Every concept is stated for any market first; the numbers come after, each labelled with its market ("on Prosperity's
  Kelp", "on ABIDES", "in the Varde rehearsal").
- Four markets recur as contrasting cases, not one: Prosperity (a generator with a wall at the value and uninformed
  takers), our `arena.sim` (presets we control), ABIDES (informed and momentum agents, no wall), and after the event the
  Arena itself. LOBSTER if it arrives.
- A boxed "What would differ on another market" paragraph closes each chapter in Parts II and IV.
- Prosperity's history (rounds, teams, products) stays in the stories and the appendix, not in the explanations.

## 7. Format, figures and the audio edition

**Your suggestion was LaTeX.** The research (`research/tooling.md`) found no TeX installed, and three formats from one
LaTeX source work unevenly. The PDF is the best typeset of any option. The EPUB through tex4ebook renders formulas as
images, or as MathML only with fiddling. Text for speech is the hardest of all to get out of LaTeX.

| Option | Source | PDF | EPUB | Audio text | For an agent to maintain |
|---|---|---|---|---|---|
| L1. LaTeX | `.tex` | best | weak (tex4ebook) | hard | easy to write, hard to debug |
| **L2. Quarto book** | Markdown with LaTeX math | very good (via TinyTeX) | native MathML | a Lua filter | easiest |
| L3. Plain pandoc + Makefile | Markdown | very good | native MathML | a Lua filter | easy, cross-refs need a filter |

**Recommended: L2, Quarto.**
- **One source, every format:** Markdown with LaTeX math, with raw LaTeX wherever the PDF needs it. It builds PDF, EPUB
  and an HTML site.
- **Figures from code:** Python cells generate the charts from the repo's own tools and data, so every chart reproduces.
- **The audio edition is one more output:**
  - Each formula carries a spoken sentence, for example `[$m = (a+b)/2$]{speak="the mid is the average of the best bid
    and the best ask"}`.
  - A filter swaps every formula for its sentence, drops the tables, and turns each figure into its one-line
    description.
  - It writes one text file per chapter.
  - The build lists any formula still without a sentence.

To install, with your approval: `brew install quarto`, `quarto install tinytex`, and optionally `npm i -g
speech-rule-engine` (an automatic fallback for formulas without a sentence). Possible voices:
- macOS `say` works now and is plain;
- a downloaded Premium voice is better;
- Kokoro locally is better still;
- a cloud voice is the most natural.

Formulas are few by design: at most one or two a chapter, about 25 in the book, each with its sentence. That suits both
the reader and the audio.

## 8. What to read meanwhile, instead of *Trades, Quotes and Prices* in full

From `research/literature_map.md`. Your 45 pages covered chapter 1 (its best chapter for us) and the start of chapter 2.
The book's useful core is in chapters 7, 11, 16, 17 and 21; chapters 5–6, 9–10, 12–14, 18–20 and 22 aren't used by the
repo at all. A route of about 120 pages:

1. The wiki's page on the book, `references/wiki/sources/trades-quotes-prices.md`: a 20-minute map of the rest, with our
   measurements attached.
2. Harris, *Trading and Exchanges*, ch. 13 "Dealers" and ch. 14 "Bid/Ask Spreads" (PDF pp. 291–334): the plain-prose
   intuition.
3. Bouchaud et al. ch. 16 §16.1–16.2 and ch. 17 (PDF pp. 317–330, 338–350): why spreads exist; does market making pay.
4. Avellaneda & Stoikov (8 pages), then the wiki's `optimal-quoting-models` page.
5. Signals: Stoikov's micro-price (9 pages) and Bouchaud et al. ch. 7 §7.1–7.3 (PDF pp. 137–145).
6. Bouchaud et al. ch. 11 §11.1–11.3 (PDF pp. 227–240) and DeLise, *Negative drift of a fill*: markouts.
7. Bouchaud et al. ch. 21 §21.3–21.4 (PDF pp. 413–421): limit against market orders, the value of queue position.
8. `pseudo-math` (33 pages), the wiki's `validation-and-overfitting`, then PBO: where your ML background transfers
   directly.

## 9. Who writes it, and how it stays true

**The writer:** the auditor (a separate session, as now), working in its own folder,
`~/Documents/qminers_arena_audit/guidebook/`, and reading the repo without changing it, as it does for audits. The
finished sources can move into this repo afterwards (`docs/guidebook/`).

**The steps:**
1. **Brief:** this proposal plus the dossier, and your answers to §10.
2. **Outline and one sample chapter,** chapter 4 or 10, for you to read. Its tone, depth and length set the rest; a
   chapter that misjudges the level is cheap to fix at that point and expensive later.
3. **Chapters in order,** each with its figures generated from committed commands.
4. **A fact-check pass by a second agent:**
   - every number traced to its IDEAS row, wiki line or command, and re-run where it is cheap;
   - every "their claim" kept marked as one;
   - every formula checked against the PDF (the repo's rule for `literature_md/`).
5. **Builds:** PDF, EPUB and the audio text, then the audio itself if you want it.

**Effort:**
- **Field guide A:** about a day of agent time for the draft and half a day for checks and builds. Ready by 6 Nov if
  started tomorrow, and it costs usage before the 5 Nov 18:00 reset, which is when that's cheapest.
- **Guidebook B:** about two to three weeks part-time after the event, chapter by chapter, with your review of each
  part.

## 10. What I need you to decide

1. **Phase 1 now (the field guide before the event), or only the full guidebook after it?** I recommend the field guide
   now: it is short enough to read on the train.
2. **Format:** Quarto as recommended, or LaTeX as you suggested (the PDF would be a little nicer and the EPUB and audio
   harder)?
3. **Structure:** the recommended mix (a spiral of question-titled chapters opening on stories), or a strict bottom-up
   textbook order?
4. **The writer:** the auditor in its own folder, or this session?
5. **Audio:** one plain text file per chapter is enough for now, or do you want the voice and an m4b built too (Kokoro or
   a cloud voice)?
