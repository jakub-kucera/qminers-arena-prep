# The field guide: build plan (for the auditor to check)

2026-11-04. Phase 1 of `docs/guidebook/PROPOSAL.md`, as the user decided (its §10): the field guide now, in Quarto, the
recommended structure, written by this session, with the audio text and a voice track. This file says what will be
built and how to check it; the guide's sources are in `docs/guidebook/field_guide/`. The full book that grows from it
after the event has its own plan, `GUIDEBOOK_PLAN.md`.

## What it is

About 35 pages (13–14k words): ten chapters, each a question, each opening on a true story, plus a preface and a
glossary (a definition list, set in two columns in print). Every number comes from the repo (an IDEAS row, a wiki
line, a committed command) or from a team's write-up marked "their claim". Dataset-agnostic: each idea stated for any market first, then shown on named markets
(Prosperity, our `arena.sim`, ABIDES, the mock rounds).

## Chapters (target words; the stories they open on, from `research/stories.md`)

| # | Question | Words | Opening story | Figures |
|---|---|---|---|---|
| 0 | Preface: how to read this | 300 | | |
| 1 | What happens in a round? | 1,100 | the Varde rehearsal, end to end | F1 the round's loop |
| 2 | What is an exchange? | 1,500 | the portal's identity: Session 1's cash −€2,814.63, position +€2,924.84, score €110.21 (`data/sessions.csv`, from the portal's `evaluate`) | F2 an order book; F3 the score's parts |
| 3 | What is the price? | 1,100 | a rival's far 40-lot order moved the fair by 44 | F4 mid against wall mid; F8 the smile window (the fair's timescale) |
| 4 | Why does a market maker earn anything? | 1,300 | a copy of the bot cuts each one's income to about 57% (72.7k alone; 41.4k and 41.8k with a copy) | F5 a round trip; F6 income against copies |
| 5 | Who is on the other side? | 1,400 | ABIDES: the playbook lost, the shuffled days made +4.54M cents (about +$45k) | F7 real against shuffled |
| 6 | Why is my backtest lying? | 1,400 | +2,415 local against +436 live (their claim) | F9 PnL under each fill model |
| 7 | How do I know a result is real? | 1,600 | the Marks that weren't informed | F10 the grid under two fill models; F11 days as folds |
| 8 | What does the portal tell me? | 1,100 | the fee that was 28% of the gross | F12 calibrate's errors |
| 9 | How is the code laid out? | 1,200 | the late-orders rehearsal: an ADAPTER bug, not a strategy | F13 the architecture |
| 10 | What do I do on the day? | 1,000 | halving the stake kept first place (Qminers 2024) | F14 the day's timeline |
| A | Glossary | 800 | | |

Chapter 10 is a dated narrative of why the day runs as it does, pointing at `RUNBOOK.md` for every instruction; it
gives no instruction RUNBOOK doesn't (the audit's round 8, R4: three copies of the day's rules already disagreed).

Each chapter ends with the same four boxes: "If you know ML", "In the repo", "On the day", "Go deeper" (sections of the
literature with page ranges, from `research/literature_map.md` §4).

## Figures (`field_guide/figures/`, drawn by `field_guide/scripts/make_figures.py` from `field_guide/data/`)

Every chart reads a CSV in `field_guide/data/`; `field_guide/scripts/make_data.py` regenerates each CSV from committed
commands. Diagrams are drawn in matplotlib too, so one script owns every image.

| Figure | Kind | Data | Made by |
|---|---|---|---|
| F1 the round's loop | diagram | none | boxes: data → diagnose → bot → backtest/grid → validate → upload → metrics → calibrate → back |
| F2 an order book | chart | one P3 round 1 Kelp tick, three levels a side | `load_days` on `--data p3` |
| F3 the score's parts | bars | the Varde upload's three sessions | `mock_round/round4/private/portal.py`'s `evaluate` on `results/template.py` (no upload counted) |
| F4 mid against wall mid | line | 300 ticks of P3 round 1 Kelp | `load_days` |
| F5 a round trip | price, position and PnL | Varde LUMEN, session 1, steps 0–399 | the portal's fills |
| F6 income against copies | bars | 72,674 alone; 41,352 and 41,848 with one copy; 27,460, 28,970 and 29,515 with two (the template since its 18 Oct `sized_mid` change; the IDEAS row's 81,292 is the earlier template's) | `arena.backtest ... --vs`, run by `make_data.py` (`data/copies.csv`) |
| F7 real against shuffled | bars | ABIDES: real −21,798 and shuffled +4,540,545, **in cents** (ABIDES's own unit: −$218 and +$45,405); Kelp: 27,390 and 27,326 credits | the IDEAS row's `arena.grid ... --permute 20`, run by `make_data.py` |
| F8 the smile window | line | `smile_window` 20 / 200 / 1,000 / 5,000 / 20,000 on P2's coupon, `take_edge` 0.5 | the IDEAS row's `arena.grid` command, run by `make_data.py` |
| F9 PnL under each fill model | bars | P3 round 1: all 72,674, worse 63,302, none 28,217, resting 66,558 (`--resting`, queue `back`, the default; the queue model changes it) | `arena.backtest` in each mode |
| F10 the grid under two fill models | two heatmaps | Kelp `make_edge` × `take_edge` on P3 round 1, Kelp's own PnL | `arena.grid ... --out` (as `sim_fit --compare` ran it) |
| F11 days as folds | diagram | none | leave-one-day-out over three days, against k-fold |
| F12 calibrate's errors | dots | the Varde upload: the per-figure errors of calibrate's best-ranked setting and of the one closest on the fills, against its 5% line | `experiments.day.calibrate` as of bc8569c, through the round's plug-in, `--vary fill_ratio=1,0.5` |
| F13 the architecture | diagram | none | `research/repo_map.md`, A |
| F14 the day's timeline | diagram | the weekend from `ON_THE_DAY.md`'s "The day: timeline and roles" table, the round from `RUNBOOK.md`'s "Each round" table | parsed from both by `make_data.py`, so the figure follows the docs |

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

**Installs** (done 2026-11-04): Quarto 1.8.25 from its macOS tarball in `~/.local/quarto` (the Homebrew cask's pkg
needs an admin password), TinyTeX through `quarto install tinytex`; pandoc, ffmpeg and `say` were present. Kokoro is
installed only when the voice step runs, and `say` stays the fallback. Charts run under `uv run --group analysis`
(matplotlib) in `arena.analysis.THEMES`' light palette.

**Order:** HTML and the audio text first, then PDF and EPUB, the voice last.

- `quarto render` in `field_guide/`: HTML, PDF (TinyTeX), EPUB (MathML).
- **Audio text:** `field_guide/scripts/audio.sh` runs `scripts/audio.lua` through pandoc on each chapter, in
  `_quarto.yml`'s order, and writes `_audio/<nn>-<chapter>.txt`:
  - math becomes its `speak` sentence (a formula without one is reported, and the build fails);
  - tables are dropped, with any `.content-visible when-format="audio"` summary kept (so the glossary is a definition
    list, set in two columns in print, not a table);
  - code becomes "the command is in the printed edition";
  - a figure becomes "Figure: <its alt text>".
  - a source citation written as `[(...)]{.src}` is printed, not read; the "In the repo" box is read as one sentence
    pointing at the printed edition;
  - signs and units are read as words ("plus 2,415", "1,477 thousand").
- **Voice:** `field_guide/scripts/voice.sh`. It uses Kokoro (local, open weights; `scripts/kokoro_say.py`, voice
  `bf_emma`, the model in `~/.cache/kokoro`) where installed, else macOS `say`, renders one audio file per chapter, and
  joins them with ffmpeg into one `.m4b` with chapter marks. About 175 words a minute: the sample chapter is 8.5
  minutes, the whole guide about 80.
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
8. The four markets are kept apart: nothing measured on Prosperity is stated as a fact about the Arena, and each
   number names its unit (Prosperity's credits, ABIDES's cents, the Varde portal's euros).
9. Every opening story matches the Source line in `research/stories.md` (stories are where embellishment creeps in).
10. No instruction for the day that `RUNBOOK.md` doesn't give.

## Schedule and cut line

- **4 Nov:** the data and figures (done, a391c5d); chapter 6, "Why is my backtest lying?", as the sample, built to
  HTML for the user to read. Its depth and length set the rest.
- **4 Nov:** chapters 1–5, then 7 and 8, then 9, 10 and the glossary, in reading order, since the user found
  chapter 6 heard alone hard to follow without the concepts before it (done). Each chapter opens with a "You'll need"
  line naming the terms it uses and where they are defined.
- **4 Nov:** the fact-check pass by a second agent (done): about 30 factual errors and the audio's misreadings, all
  fixed, including the same misreadings in `research/stories.md` and one wiki row. Of the voice's back ends, the CPU
  stayed: Kokoro ran at 4.1 times real time on it, 4.0 through Core ML (which took only half the model's operations)
  and 2.5 through MLX on the GPU.
- **Then:** PDF, EPUB, the audio text and the voice, built from the fixed text; the user reads or listens, and their
  notes are the last pass.
- **If time runs out,** the guide ships with chapters 1–8 and the glossary; 9 and 10 follow after the event as part
  of the guidebook.
