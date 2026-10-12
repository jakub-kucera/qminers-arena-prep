#!/usr/bin/env python3
"""Finds the PDF page of a line in a converted document, and prints that page's text.

Marker's markdown carries three kinds of page markers: `<span id="page-N-…">` anchors (only in documents with
internal links), figure files named `_page_N_…`, and headings, whose pages are in `meta.json`. All are zero-based.
The markers before and after a line bound its page; `pdftotext` then picks the page in that range whose words
match the line best. Pages printed by this script are one-based, as a PDF viewer shows them.

Usage: python3 literature_md/pdfpage.py SLUG LINE[-LAST] [--no-text]     e.g. micro-price 120, micro-price 40-52
       SLUG is the folder name; LINE is a line of SLUG/SLUG.md. Standard library and `pdftotext` (poppler).
references/wiki/lint.py imports `page_range` to check the `(p. N)` after a literature citation.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
from functools import cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "literature_raw"
ANCHOR = re.compile(r'<span id="page-(\d+)-\d+"')
FIGURE = re.compile(r"\]\(_page_(\d+)_")
HEADING = re.compile(r"^#{1,6}\s+(.*)")
WORD = re.compile(r"[A-Za-z]{4,}")


def _norm(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


@cache
def markers(slug: str) -> list[tuple[int, int]]:
    """(line, zero-based page) for every page marker in SLUG/SLUG.md, in line order."""
    lines = (HERE / slug / f"{slug}.md").read_text().splitlines()
    toc = json.loads((HERE / slug / "meta.json").read_text()).get("table_of_contents", [])
    entries = [(_norm(t.get("title", "")), t["page_id"]) for t in toc if t.get("title") and "page_id" in t]
    found, next_entry = [], 0
    for number, line in enumerate(lines, 1):
        pages = [int(p) for p in ANCHOR.findall(line) + FIGURE.findall(line)]
        heading = HEADING.match(line)
        if heading and (title := _norm(heading.group(1))):
            for k in range(next_entry, min(next_entry + 6, len(entries))):
                name = entries[k][0]
                if name and (name.startswith(title) or title.startswith(name)
                             or difflib.SequenceMatcher(None, name, title).ratio() > 0.8):
                    pages.append(entries[k][1])
                    next_entry = k + 1
                    break
        found.extend((number, page) for page in pages)
    return found


def page_range(slug: str, first: int, last: int | None = None) -> tuple[int, int | None]:
    """One-based PDF pages (low, high) that lines first..last can be on; high is None after the last marker."""
    last = last or first
    before = [page for line, page in markers(slug) if line <= first]
    after = [page for line, page in markers(slug) if line > last]
    low = max(before) if before else 0
    high = min(after) if after else None
    if high is not None and high < low:  # a misplaced marker: widen rather than claim a wrong page
        low, high = high, low
    return low + 1, None if high is None else high + 1


def pdf_path(slug: str) -> Path | None:
    """The source PDF, from the slug-to-filename table in convert.sh."""
    for entry in re.findall(r'^\s*"([^"]+)"', (HERE / "convert.sh").read_text(), re.M):
        name, _, prefix = entry.partition(" ")
        if name == slug:
            matches = sorted(RAW.glob(prefix.strip() + "*.pdf"))
            return matches[0] if matches else None
    return None


def pdf_pages(pdf: Path, low: int, high: int) -> dict[int, str]:
    out = subprocess.run(["pdftotext", "-f", str(low), "-l", str(high), "-layout", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    return {low + i: text for i, text in enumerate(out.split("\f")[: high - low + 1])}


def words_near(lines: list[str], number: int, want: int = 12) -> set[str]:
    """Words of the line, widened to neighbouring lines while it has fewer than `want` (formula lines have few)."""
    def words(i: int) -> set[str]:
        text = re.sub(r"\\[A-Za-z]+|<[^>]+>|\$[^$]*\$", " ", lines[i - 1]) if 1 <= i <= len(lines) else ""
        return {w.lower() for w in WORD.findall(text)}
    found, span = words(number), 0
    while len(found) < want and span < 5:
        span += 1
        found |= words(number - span) | words(number + span)
    return found


def locate(slug: str, number: int) -> tuple[int | None, list[tuple[float, int]], tuple[int, int | None]]:
    """Best one-based page for a line, the scored candidates, and the range allowed by the markers."""
    low, high = page_range(slug, number)
    pdf = pdf_path(slug)
    if pdf is None:
        return None, [], (low, high)
    high_search = high if high is not None else low + 3
    pages = pdf_pages(pdf, low, high_search)
    lines = (HERE / slug / f"{slug}.md").read_text().splitlines()
    target = words_near(lines, number)
    scored = sorted(((len(target & {w.lower() for w in WORD.findall(text)}) / max(len(target), 1), page)
                     for page, text in pages.items()), reverse=True)
    best = scored[0][1] if scored and scored[0][0] >= 0.3 else None
    return best, scored, (low, high)


def report(slug: str, number: int) -> int | None:
    best, scored, (low, high) = locate(slug, number)
    allowed = f"pp. {low}–{high}" if high is not None else f"p. {low} or later"
    if pdf_path(slug) is None:
        print(f"{slug}.md:{number}: markers allow {allowed}; PDF not found in {RAW}")
        return None
    others = ", ".join(f"p. {p} {s:.2f}" for s, p in scored[1:3])
    if best is None:
        print(f"{slug}.md:{number}: no confident match; markers allow {allowed} (scores: {others or 'none'})")
        return None
    print(f"{slug}.md:{number} -> PDF p. {best}   (markers allow {allowed}; match {scored[0][0]:.2f}; next {others or 'none'})")
    return best


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    span = re.fullmatch(r"(\d+)(?:[-–](\d+))?", args[1]) if len(args) == 2 else None
    if span is None:
        print(next(part for part in __doc__.split("\n\n") if part.startswith("Usage")))
        return 2
    slug, first, last = args[0], int(span.group(1)), int(span.group(2) or span.group(1))
    if not (HERE / slug / f"{slug}.md").is_file():
        print(f"no such document: {slug}")
        return 2
    pages = [report(slug, n) for n in sorted({first, last})]
    if None in pages:
        return 1
    if len(pages) == 2:
        print(f"cite as (p. {pages[0]}–{pages[1]})" if pages[0] != pages[1] else f"cite as (p. {pages[0]})")
    if "--no-text" not in argv:
        for page in range(pages[0], pages[-1] + 1):
            print(f"--- PDF page {page} ---")
            print(pdf_pages(pdf_path(slug), page, page)[page].rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
