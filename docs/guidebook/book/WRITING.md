# Writing a chapter: the conventions both books follow

For whoever writes or checks a chapter (an agent session or the auditor). The plans say what goes in each chapter:
`../FIELD_GUIDE_PLAN.md` and `../GUIDEBOOK_PLAN.md`. The reader is in `../research/reader_profile.md`; the stories,
with sources, in `../research/stories.md` (check each against its primary source: the file has had misreadings);
the literature route in `../research/literature_map.md`; the repo's map in `../research/repo_map.md`. The guidebook's
sample chapter, `guidebook/10-backtest.qmd`, sets its depth and tone; the field guide's chapters (`fieldguide/`) are
fact-checked and are what a guidebook chapter grows from.

## The reader and the voice

An engineer with strong ML and statistics, new to markets. Assume probability, overfitting, hyperparameter search,
simulators; build order books, matching, the spread, adverse selection and inventory from zero; give intuition, not
derivations. Plain, concrete sentences; one idea a paragraph; British spelling. No hype, no "simply", no exclamation
marks.

## Every chapter

1. `# <the question>` as the title, then an italic "You'll need …" line naming the terms it uses and the chapters that
   define them (the guidebook's numbering: 1 round, 2 exchange, 3 price, 4 market making, 5 the other side, 6 holding a
   position, 7 what prices do, 8 what else a bot can trade, 9 who else is in the market, 10 backtests, 11 real results,
   12 the portal, 13 sizing risk, 14 the code, 15 the parameters, 16 the day; appendices A glossary, B datasets,
   C commands, D reading route, E the Arena).
2. `## The story`: something that happened, with its number and source.
3. `## The idea`, in `###` sections.
4. The boxes, as Quarto callouts, in this order: `{.callout-note title="What would differ on another market"}` (Parts
   II and IV), `{.callout-note title="If you know ML"}` (the analogy, and where it breaks: always say where),
   `{.callout-tip title="In the repo"}` (files, parameters, commands, IDEAS rows by name),
   `{.callout-warning title="On the Arena"}` (until the event: "*Written after the event, from the round handovers:*"
   and what it will say), `{.callout-note title="Go deeper" appearance="simple"}` (the literature with PDF pages).

## Numbers and sources

- **Every number has a source next to it**: an `IDEAS.md` row by its bold name, a wiki page, a references file at a
  line, a README, or a CSV in `data/` made by a committed command. Find IDEAS rows by name (`grep -n` on the name;
  rows are long single lines, so use `grep -o` with context); line numbers drift.
- **Run what you can.** A number from a committed command that takes under ten minutes is re-run, not copied: the
  engine has changed since some rows were written (the guidebook's round-5 edges moved by 0.2%). If a re-run differs
  from the row, the text uses the re-run, and the figure's CSV carries the command.
- **Units always:** Prosperity in credits, ABIDES in cents, the Varde rehearsal in euros, the other mock rounds in
  their own units (say "in that round's units").
- **"*their claim*"** marks any figure from a team's write-up that our engine didn't reproduce.
- **Keep the markets apart:** nothing measured on Prosperity, ABIDES or a rehearsal is stated as a fact about the Arena.
- **No instruction for the day that `RUNBOOK.md` doesn't give;** point at RUNBOOK and `ON_THE_DAY.md` sections by name.
- **Formulas:** at most two a chapter, each verified against its source. For the literature, check the page with
  `python3 literature_md/pdfpage.py <slug> <line>` and cite the PDF page; for ours, cite the code.

## Markup the builds rely on

- Source citations go in a span the audio drops: `[(\`IDEAS.md\`, "Row name")]{.src}`. Keep it a citation only: the
  audio never reads what's inside, so no explanation goes there.
- Every formula has its spoken sentence: inline `[$...$]{speak="..."}`, display `::: {.eq speak="..."}` around `$$...$$`.
  `scripts/audio.sh guidebook` fails on one without.
- Every table is followed by `::: {.content-visible when-format="audio"}` with a spoken summary of it.
- Every figure: `![Caption, ending with its data source.](../figures/<name>.png){#fig-<id> fig-alt="What it shows, with its key numbers, as a sentence a listener can follow."}`,
  referred to as `@fig-<id>` in the text.
- Prose a voice can read: no symbols for words (write "to", "times", "about"), numbers with their units, code names in
  backticks (the audio turns `make_edge` into "make edge" and a path into its file's name).

## Figures and data (the guidebook)

Each part has its own modules, so the parts never edit the same file: `scripts/parts/data_<part>.py` (a `STEPS` dict
of functions that run committed commands and `write()` a CSV, importing helpers from `make_data`) and
`scripts/parts/figures_<part>.py` (a `FIGURES` list of functions that `read()` a CSV and `save()` a PNG, importing
from `make_figures`, in its light theme's colours). Figures are named `g<nn>_<name>.png`, numbered as in
`GUIDEBOOK_PLAN.md`. Run them with `uv run python docs/guidebook/book/scripts/make_data.py --only <step>` and
`uv run --group analysis python docs/guidebook/book/scripts/make_figures.py --only <function>`, and look at every PNG.

## Checking a chapter before handing it over

- `pandoc guidebook/<file>.qmd -f markdown -t plain --wrap=none -L scripts/audio.lua -o /dev/null` (from `book/`)
  passes: every formula has a sentence.
- Every number re-traced; every story against its primary source; every pointer (RUNBOOK times and headings,
  ON_THE_DAY headings, files, flags with `--help`) exists.
