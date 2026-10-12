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

1. **Cite with a machine-checkable reference.** Write a backticked path and a line: `` `prosperity4-baguette-fromage/README.md:350` `` or a range `` `…/Phase1.py:368-439` ``. On a source page the path may be relative to its `repo`. Paths of our own files (`bots/template.py:151`) also work. `lint.py` checks that the file exists and the line is in range. Do not cite notebooks by line; name the function or cell.
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

### Ingest a document from `literature_md/`
1. Convert it first (`literature_md/convert.sh`, a row in its table, a row in `literature_md/README.md`).
2. Read it; for a book, map the chapters from `meta.json` (pages there are zero-based) and read only the chapters a question needs.
3. For each formula you keep, run `python3 literature_md/pdfpage.py <slug> <line>`, compare it with the PDF text it prints (or the PDF itself, for anything `pdftotext` garbles), and mark it `checked`.
4. Write `sources/<slug>.md`, then steps 4–6 of the ingest above. Translate the result into our setting on the concept page ("What it means for our code"), not only on the source page.

### Query (answering a question from the wiki)
1. Read `index.md`, then the relevant concept pages, then source pages, and only then the raw file at the cited line.
2. Answer with citations. If the cited line no longer says what the page says, the page is stale: fix it and log a `lint` entry.
3. If the answer is reusable, file it back (rule 8) and log a `query` entry.

### Lint (before the event and after any large edit)
1. Run `python3 references/wiki/lint.py` (mechanical: front matter, index coverage, links, citations, orphans, log format).
2. Then check by hand: contradictions not yet in `contradictions.md`; claims marked *their claim* that you can now check; clones updated since `updated:` (`clone.sh --update`); concepts mentioned in three or more pages that have no page; gaps a search could fill (list them in `index.md`, "Gaps").
3. Append a `lint` entry to `log.md` saying what changed.

## Scale note

About 25 repo sources, 19 literature documents and 20 concepts: the index file is enough to navigate. Add search tooling only if the wiki grows by an order of magnitude.
