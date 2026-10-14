# Schema of the references wiki

This is the "schema" layer of Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
pattern. An agent reads it before touching the wiki. The idea: knowledge is **compiled once into linked
pages and kept current**, instead of re-derived from the raw clones on every question.

## The three layers

| Layer | Where | Who writes it |
|---|---|---|
| **Raw sources** | the clones in `references/<repo>/` (gitignored), downloaded documents (`references/prosperity-wikis/`, made by `references/fetch_notion.py`), saved README snapshots of repos read online (`references/online-snapshots/`), `references/arena-site-snapshot.txt`, and `literature_md/` | nobody: **read-only**. Never edit, never import from them |
| **The wiki** | `references/wiki/` (committed) | the agent. A human reads it |
| **The schema** | this file | human and agent together; change it when a convention stops working |

Two older files stay outside the wiki: `references/README.md` (the human-facing table of repos and the reading
order) and `references/SEARCH_LOG.md` (how the sources were found and what was rejected).

## Page types

| Type | Folder | Purpose |
|---|---|---|
| `source` | `sources/` | one page per raw source: what it is, a code map, **how deeply it was read**, traps. A document in `literature_md/` is a source too, with `repo: literature_md/<slug>` and the page named after the slug |
| `concept` | `concepts/` | one page per idea, **synthesised across sources**: what they say, where they disagree, what it means for our code, how to test it here |
| `comparison` | `contradictions.md` | disagreements between sources, README-versus-code mismatches, open questions |
| `overview` | `overview.md` | the one-page synthesis, with links down to the concepts |

`index.md` lists every page with one line each. `log.md` is append-only.

## Page format

Every page except `index.md` and `log.md` starts with this front matter (plain `key: value` lines, no nesting):

```
---
title: Short human title
type: source | concept | comparison | overview
updated: 2026-10-10
repo: prosperity4-dtu-quant-lab    # source pages only: the folder under references/ (or under the repo root, e.g. literature_md/<doc>), or `none` if there is no local copy
status: read | partly-read | mapped | unread    # source pages only
---
```

- **Concept pages** use these sections, in this order: `Summary` (3 lines), `What the sources say`, `Where they disagree`, `What it means for our code`, `How to test it here`, `Sources`.
- **Source pages** use: `What it is`, `Layout and code map`, `What carries over`, `Traps`, `Read depth`, `Cited by` (the concept pages that use it).
- **Literature source pages** (papers and books in `literature_md/`) use: `What it is`, `Main results` (each formula with its status, rule 9), `Assumptions against the Arena` (what the model assumes that a discrete-tick, hard-limit, bot-filled market breaks), `In our notation` (the paper's symbols against our parameters and data columns), `Traps` (OCR slips found, results that need conditions we lack), `Read depth`, `Cited by`. A book's `Read depth` is a chapter map with PDF pages, saying which chapters were read.

## Rules

1. **Cite with a machine-checkable reference.** Write a backticked path and a line: `` `prosperity4-baguette-fromage/README.md:350` `` or a range `` `…/Phase1.py:368-439` ``. On a source page the path may be relative to its `repo`. Paths of our own files (`bots/template.py:317`) also work. `lint.py` checks that the file exists and the line is in range. Do not cite notebooks by line; name the function or cell.
2. **Say who claims what.** Mark every number as *their claim* (from a README), *checked* (and how: ran it, grepped it, read the line), or *inferred* (and why). A team's rank or PnL is always their claim unless a source says otherwise.
3. **Say what was not read.** A source page's `Read depth` lists what was read, mapped (only `grep`/headings) and unread. An unread part is never summarised.
4. **Flag conflicts, don't pick silently.** When two sources disagree, add a row to `contradictions.md`, link it from both concept pages, and say what test would settle it.
5. **Link to our code.** A concept page names the file in this repo that implements or should implement the idea (`bots/template.py`, `arena/engine.py`) and the `TODO.md` item if one exists.
6. **No third-party code in the wiki, no secrets.** Describe an algorithm in words and formulas; third-party team repos have no licence (see `sources/` for each). Never copy shared credentials, even public ones from a README.
7. **Plain relative markdown links.** No wiki-link syntax, so the pages render on GitHub.
8. **File good answers back.** If a question needed a synthesis the wiki lacked, write it into a concept page (or extend one) and log it.
9. **Literature: the PDF page, and a status for every formula.** A citation into `literature_md/` is followed by the one-based PDF page, as a viewer shows it: `` `literature_md/micro-price/micro-price.md:52` (p. 3) `` or `(p. 3–4)`. `literature_md/pdfpage.py <slug> <line>` finds the page and prints it; `lint.py` checks that the page agrees with the markers around the line. A formula's citation also says whether it was read on the PDF page: `(p. 3, checked)` or `(p. 3, unchecked)` when it is only Marker's OCR. **Only checked formulas go under "What it means for our code"** or into `TODO.md`. A slip found on the way goes under the source page's `Traps`, as `OCR: … where the PDF has …`.

## Workflows

### Ingest (a new source arrives: a repo, a rules page, a log downloaded from the portal)
1. Put the raw source in `references/` (add a row to `clone.sh` for a repo, or save a snapshot). Do not edit it.
2. Read it. Decide honestly what you read, mapped or skipped.
3. Write `sources/<slug>.md`.
4. Update every concept page it touches (usually 3–8) and `contradictions.md` if it conflicts with anything.
5. Add it to `index.md`; append an `ingest` entry to `log.md`.
6. Run `python3 references/wiki/lint.py`.

### Add a document to the literature (a paper, a book or book chapters, a printed web page)
This is how Phase 1 of the literature ingest ran (`log.md`, 2026-10-12). Follow it for every new document. When several arrive at once, plan them as a batch in `TODO.md`, ordered by the to-do items they unblock, and log the batch as one `ingest` entry.

**A. Get it in (a person or the agent):**
1. Put the PDF in `literature_raw/` (gitignored). For a download, check that it is the paper it claims to be: `pdfinfo` and `pdftotext -l 1`. For a book, save only the chapters needed if possible. Things only a person can obtain are listed in `MANUAL_TODO.md`.
2. Add a row to `PAPERS` in `literature_md/convert.sh` (slug and file-name prefix) and run `./convert.sh`. It converts only what has no output yet.
3. Sanity-check the conversion:
   - `python3 literature_md/pdfpage.py <slug> <line>` on a few lines at the start, middle and end must find a page. Most documents have no Marker page anchors; the script falls back to figure names and the headings in `meta.json`. If it reports no text layer (a scanned PDF), every page must be confirmed on the page image.
   - Remove decorative images.
   - Glance at one table and one display formula against the PDF.
4. Add a row to the table in `literature_md/README.md` and the slug to "Not yet ingested" in `index.md`.

**B. Triage:**
- **Paper:** read it whole. Status `read`, or `partly-read` when the proofs are skipped.
- **Book:** don't summarise it.
  - Build a chapter map from `meta.json`: chapter titles with one-based PDF pages (`page_id` + 1), with the OCR'd titles fixed by hand. It goes in the source page's `Read depth`.
  - Read only the chapters a current question or `TODO.md` item needs, and mark the rest `mapped`. Status `partly-read`. The page grows as later questions read more chapters (query workflow, rule 8).
- **Priority:** name the `TODO.md` items or concept pages the document feeds. A document that feeds none can stay mapped.

**C. Read and check:**
1. Read with the question in mind: what result, under which assumptions, measured on what data.
2. For each formula, number or table you keep:
   - Find its page with `pdfpage.py`.
   - **Look at the page image** (the Read tool on the PDF with `pages`); `pdftotext` garbles mathematics.
   - Mark it `(p. N, checked)` or `(p. N, unchecked)` (rule 9).
   - Read every number taken from a table off the PDF: Marker drops minus signs and decimal points.
3. **Recompute worked examples** where the paper gives one (a few lines of standard-library Python). That catches both OCR and the paper's own errors.
4. Go through the OCR failure modes in `literature_md/README.md` ("Caveats"). Record each slip under the source page's `Traps`, as either "OCR: … where the PDF has …" or "Typo in the paper itself" (when the PDF has it too).
5. Where it is cheap, **measure the paper's key assumption on our data** (spread in ticks, how often the mid moves, queue length) and put the number under "Assumptions against the Arena", marked *checked*.

**D. Write:**
1. `sources/<slug>.md` with the literature sections (Page format above). "In our notation" maps the paper's symbols to `path:line` in our code and to CSV columns.
2. The concept pages it touches, under "What the sources say" (theory next to the teams' evidence). A new concept page only when no page covers the idea. Translate the result into our setting under "What it means for our code" and "How to test it here".
3. `contradictions.md` if theory and practice disagree, or theory explains an open row.
4. A dated "From the literature" note on each `TODO.md` item it changes. If it settles a "done when" question, write the decision there.
5. If it changes a conclusion, a bullet in `overview.md`, "What the literature adds".

**E. Close:**
1. Move the slug from "Not yet ingested" to the list in `index.md`, with one line.
2. Add an `ingest` entry to `log.md` naming the documents, the concept pages changed, and the OCR traps found.
3. Run `python3 references/wiki/lint.py` until there are no errors. Read the `unchecked` count it prints: each one is a formula not yet read on the PDF.
4. Commit the wiki pages, `literature_md/<slug>/`, `convert.sh` and the README together.

### Query (answering a question from the wiki)
1. Read `index.md`, then the relevant concept pages, then source pages, and only then the raw file at the cited line.
2. Answer with citations. If the cited line no longer says what the page says, the page is stale: fix it and log a `lint` entry.
3. If the answer is reusable, file it back (rule 8) and log a `query` entry.

### Replace a document with a fuller copy (a full book for an excerpt, a published version for a preprint)
The wiki is rebuilt from the new copy; nothing keeps citing the old one.
1. Save the new PDF under the old file name in `literature_raw/`, so the slug stays the same, and move the old one out. Delete `literature_md/<slug>/` and run `literature_md/convert.sh`.
2. Every citation into the slug now points at the wrong lines. List them with `grep -rn "<slug>.md:" references/wiki`. For each, find the passage in the new markdown, then cite the new line and its page from `pdfpage.py`. Re-check every formula marked `checked` on the new page images; the version may differ.
3. Rewrite the source page from the new copy: "What it is" and "Read depth" for the new version, a new chapter map for a book, and the parts that were missing read now, in the order the open questions need them. File what they add into the concept pages (steps D–E of "Add a document to the literature").
4. Update `literature_md/README.md` (pages, version), run `python3 references/wiki/lint.py --pages` until it is clean, and log a `restructure` entry.

### Lint (before the event and after any large edit)
1. Run `python3 references/wiki/lint.py --pages` (mechanical: front matter, index coverage, links, citations, orphans, log format; for the literature, the cited page against the markers and, with `--pages`, against the PDF text; a status on every formula next to a literature citation; no `unchecked` formula under "What it means for our code"). A `--pages` warning is either a wrong page or a matcher miss: check the PDF, then fix the page or add the line to `MATCH_MISSES` in `lint.py` with the reason.
2. Then check by hand: a seeded random sample of about 40 literature citations, each read against its cited lines; contradictions not yet in `contradictions.md`; claims marked *their claim* that you can now check; clones updated since `updated:` (`clone.sh --update`); concepts mentioned in three or more pages that have no page; gaps a search could fill (list them in `index.md`, "Gaps").
3. Append a `lint` entry to `log.md` saying what changed.

## Scale note

About 25 repo sources, 19 literature documents and 20 concepts: the index file is enough to navigate. Add search tooling only if the wiki grows by an order of magnitude.
