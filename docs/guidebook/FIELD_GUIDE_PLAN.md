# The field guide: build plan (for the auditor to check)

2026-11-04. Phase 1 of `docs/guidebook/PROPOSAL.md`, as the user decided (its §10): the field guide now, in Quarto, the
recommended structure, written by this session, with the audio text and a voice track. This file says what will be
built and how to check it; the guide's sources are in `docs/guidebook/field_guide/`. The full book that grows from it
after the event has its own plan, `GUIDEBOOK_PLAN.md`.

## What it is

About 35 pages (13–14k words): ten chapters, each a question, each opening on a true story, plus a preface and a
two-column glossary. Every number comes from the repo (an IDEAS row, a wiki line, a committed command) or from a team's
write-up marked "their claim". Dataset-agnostic: each idea stated for any market first, then shown on named markets
(Prosperity, our `arena.sim`, ABIDES, the mock rounds).

## Chapters (target words; the stories they open on, from `research/stories.md`)

| # | Question | Words | Opening story | Figures |
|---|---|---|---|---|
| 0 | Preface: how to read this | 300 | | |
| 1 | What happens in a round? | 1,100 | the Varde rehearsal, end to end | F1 the round's loop |
| 2 | What is an exchange? | 1,500 | the portal's identity: Session 1's cash −€2,815, position +€2,925, score €110 | F2 an order book; F3 the score's parts |
| 3 | What is the price? | 1,100 | a rival's far 40-lot order moved the fair by 44 | F4 mid against wall mid |
| 4 | Why does a market maker earn anything? | 1,300 | a copy of the bot halves each one's income | F5 a round trip; F6 income against copies |
| 5 | Who is on the other side? | 1,400 | ABIDES: the playbook lost, the shuffled days made +4.54M | F7 real against shuffled; F8 the smile window |
| 6 | Why is my backtest lying? | 1,400 | +2,415 local against +436 live (their claim) | F9 PnL under each fill model |
| 7 | How do I know a result is real? | 1,600 | the Marks that weren't informed | F10 the grid under two fill models; F11 days as folds |
| 8 | What does the portal tell me? | 1,100 | the fee that was 28% of the gross | F12 calibrate's errors |
| 9 | How is the code laid out? | 1,200 | the late-orders rehearsal: an ADAPTER bug, not a strategy | F13 the architecture |
| 10 | What do I do on the day? | 1,000 | halving the stake kept first place (Qminers 2024) | F14 the day's timeline |
| A | Glossary | 800 | | |

Each chapter ends with the same four boxes: "If you know ML", "In the repo", "On the day", "Go deeper" (sections of the
literature with page ranges, from `research/literature_map.md` §4).

## Figures (`field_guide/figures/`, drawn by `field_guide/scripts/make_figures.py` from `field_guide/data/`)

Every chart reads a CSV in `field_guide/data/`; `field_guide/scripts/make_data.py` regenerates each CSV from committed
commands. Diagrams are drawn in matplotlib too, so one script owns every image.

| Figure | Kind | Data | Made by |
|---|---|---|---|
| F1 the round's loop | diagram | none | boxes: data → diagnose → bot → backtest/grid → validate → upload → metrics → calibrate → back |
| F2 an order book | chart | one P3 round 1 Kelp tick, three levels a side | `load_days` on `--data p3` |
| F3 the score's parts | bars | the Varde upload's three sessions | `mock_round/round4/private/portal.py` on `results/template.py` |
| F4 mid against wall mid | line | 300 ticks of P3 round 1 Kelp | `load_days` |
| F5 a round trip | price, position and PnL | Varde LUMEN, session 1, steps 0–399 | the portal's fills |
| F6 income against copies | bars | 81,292 alone; about 41k each with one copy; about 28k each with two | `IDEAS.md`, "The template against copies of itself" |
| F7 real against shuffled | bars | ABIDES: real −21,798 and shuffled +4.54M; Kelp: 27,390 and 27,326 | `IDEAS.md`, the ABIDES rows (L238 area) |
| F8 the smile window | line | `smile_window` 20 / 200 / 1,000 / 5,000 / 20,000 on P2's coupon | the IDEAS row's `arena.grid` command (cells as printed) |
| F9 PnL under each fill model | bars | P3 round 1: all 72,674, worse 63,302, none 28,217, resting 66,562 | `arena.backtest` in each mode |
| F10 the grid under two fill models | two heatmaps | Kelp `make_edge` × `take_edge` on P3 round 1, Kelp's own PnL | `arena.grid ... --out` (as `sim_fit --compare` ran it) |
| F11 days as folds | diagram | none | leave-one-day-out over three days, against k-fold |
| F12 calibrate's errors | dots | the Varde upload, three settings | `experiments.day.calibrate` through the round's plug-in |
| F13 the architecture | diagram | none | `research/repo_map.md`, A |
| F14 the day's timeline | diagram | the schedule in `ON_THE_DAY.md`, "Known so far" | |

## Formulas, each with its spoken sentence

| Formula | Spoken |
|---|---|
| mid = (best bid + best ask) / 2 | the mid is the average of the best bid and the best ask |
| wall mid = (bid wall + ask wall) / 2 | the wall mid is the midpoint of the largest level on each side |
| PnL = cash + position × price | profit is the cash, plus what the position is worth at the price |
| maker's gain per trade = s/2 − R∞ | a market maker keeps half the spread, less how far the price moves against it afterwards |
| markout at h = side × (mid in h ticks − fill price) | a fill's markout is how much the price moved in its favour h ticks later |
| pnlSe = sd of the session scores × √n | the standard error of a sum of n sessions is their spread times the square root of n |
| PBO = P(the in-sample best ranks below the median out of sample) | the probability of overfitting is how often the best setting on one half of the data falls in the bottom half on the other |

At most one or two per chapter. In the source each is `[$...$]{speak="..."}` (inline) or a `.eq` div with `speak`
(display).

## Builds

- `quarto render` in `field_guide/`: HTML, PDF (TinyTeX), EPUB (MathML).
- **Audio text:** `field_guide/scripts/audio.lua`, run through `quarto pandoc` on each chapter, writes `_audio/<chapter>.txt`:
  - math becomes its `speak` sentence (a formula without one is reported, and the build fails);
  - tables are dropped, with any `.content-visible when-format="audio"` summary kept;
  - code becomes "the command is in the printed edition";
  - a figure becomes "Figure: <its alt text>".
- **Voice:** `field_guide/scripts/voice.sh`. It uses Kokoro (local, open weights) where installed, else macOS `say`, renders one audio file per chapter, and joins them with ffmpeg into one `.m4b` with chapter marks.
- Outputs go in `field_guide/_book/` and `field_guide/_audio/`, both gitignored. The sources, data, scripts and figures are committed.

## Checklist for the auditor

1. Every number in the text is traceable: an IDEAS row or wiki line named next to it, or a CSV in `data/` made by
   `make_data.py`. Re-run `make_data.py` and confirm the CSVs come out the same.
2. "Their claim" marks every figure from a team's write-up that our engine didn't reproduce.
3. Each formula matches its source (the literature's PDF page for the book's results) and has a spoken sentence that
   says the same thing.
4. Each figure shows what its caption says, on one scale, with labels a reader can check against the data.
5. No chapter assumes a term before chapter 2 has defined it, except chapter 1, which is a tour.
6. The ML analogies say where they break.
7. The audio text reads sensibly with no formula, table or code read out as symbols.
8. The four markets are kept apart: nothing measured on Prosperity is stated as a fact about the Arena.
