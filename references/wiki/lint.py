#!/usr/bin/env python3
"""Mechanical health check of references/wiki (see SCHEMA.md, "Lint").

Checks: front matter, every page listed in index.md, relative links, `path:line` citations (file exists,
line in range, line not blank), orphan pages, log.md entry format. A citation into literature_md/ must be
followed by its PDF page, `(p. N)` or `(p. N, checked)`, and N must agree with the page markers around the line
(literature_md/pdfpage.py); formulas marked `unchecked` are counted. A line that cites the literature and quotes a
formula needs `checked` or `unchecked` on one of its literature citations (a heuristic; `Traps` sections, which
quote OCR slips, are exempt), and an `unchecked` citation under "What it means for our code" is an error.
Citations into a clone that is not present (references/clone.sh not run), or into a literature_md/ conversion that
isn't (the conversions stay on disk, out of git since 2026-11-07), are reported as skipped, not as errors.
A cited range into our own Python code (python/bots/, python/arena/, python/experiments/) must start a definition: a `def`, `class`,
decorator, assignment, annotated field or dict entry. These files change, and a range that starts mid-function,
in a docstring or at an import has usually been left behind by an edit (a warning).

Usage: python3 references/wiki/lint.py [--pages]    exit code 1 if there are errors. Standard library only.
       --pages also matches each literature citation's words against the PDF text (pdftotext, about a minute) and
       warns when the cited page is not the one that matches best; scanned PDFs without a text layer are skipped.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from functools import cache
from pathlib import Path

WIKI = Path(__file__).resolve().parent
REFERENCES = WIKI.parent
ROOT = REFERENCES.parent
META = {"SCHEMA.md", "index.md", "log.md", "lint.py"}
TYPES = {"source", "concept", "comparison", "overview"}
STATUSES = {"read", "partly-read", "mapped", "unread"}
CITATION = re.compile(r"`([A-Za-z0-9_./+\-]+\.(?:md|py|rs|tsx|ts|rst|cpp|txt|toml|yml)):(\d+)(?:[-–](\d+))?`")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
PDF_PAGE = re.compile(r"\s*\(p\.\s*(\d+)(?:[-–](\d+))?(?:,\s*(checked|unchecked))?\)")
LITERATURE = ROOT / "literature_md"
# Lines where `--pages` matches the wrong page, each confirmed in the PDF text (log.md, 2026-10-12 lint entry).
MATCH_MISSES = {
    ("queue-imbalance-predictor", 371): "Tables 4 and 5 share this header row; Table 5 and its caption are on p. 21",
    ("limit-order-books", 197): "a short caption, widened into a p. 4 footnote; the caption itself is on p. 5",
}
SPAN = re.compile(r"`([^`]+)`")
RELATION = re.compile(r"[=≈∝≤≥<>]")
LETTER = re.compile(r"[A-Za-zα-ωΑ-Ω]")
OWN_CODE = tuple(ROOT / "python" / folder for folder in ("bots", "arena", "experiments"))
# def, class, a decorator, an assignment, an annotated field (`bids: tuple = ()`) or a dict entry (`"skew": 0.0,`)
DEFINITION = re.compile(r"""\s*(?:(?:async\s+)?def\b|class\b|@|[A-Za-z_][\w.]*\s*(?::[^=]+)?=[^=]|[A-Za-z_]\w*\s*:|["'][^"']+["']\s*:)""")
LOG_ENTRY = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\] (ingest|query|lint|restructure|search) \| .+")


def front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.split("#")[0].strip()
    return fields


def pages() -> list[Path]:
    return sorted(p for p in WIKI.rglob("*.md") if p.name not in META or p.parent != WIKI)


def resolve(path: str, repo: str | None) -> Path | None:
    local = [] if not repo or repo == "none" else [REFERENCES / repo, ROOT / repo]
    for base in local + [REFERENCES, ROOT]:
        if (base / path).is_file():
            return base / path
    return None


def clone_missing(path: str, repo: str | None) -> bool:
    """True if the citation points into a clone folder that is absent (not cloned here), or into a literature_md/
    conversion that is (never committed: a fresh clone has only the folder's README and scripts)."""
    first = path.split("/")[0]
    if first == "literature_md" and path.count("/") >= 2 and not (ROOT / "/".join(path.split("/")[:2])).is_dir():
        return True
    if repo and repo != "none" and not ((REFERENCES / repo).is_dir() or (ROOT / repo).is_dir()):
        return True
    clones = ("prosperity", "algotrade", "uchicago", "qminers", "hftbacktest", "online-snapshots")
    return "/" in path and not (REFERENCES / first).is_dir() and first.startswith(clones)


@cache
def pdfpage():
    spec = importlib.util.spec_from_file_location("pdfpage", LITERATURE / "pdfpage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_page(text: str, end: int, found: Path, first: int, last: int, where: str, errors: list, warnings: list,
               exact: bool = False) -> None:
    """A literature citation needs `(p. N)` right after it, and N must lie within the pages its markers allow.

    With `exact`, the first and last cited lines must also match the cited pages best in the PDF's text.
    """
    note = PDF_PAGE.match(text, end)
    if note is None:
        warnings.append(f"{where}: literature citation without its PDF page '(p. N)'")
        return
    low, high = pdfpage().page_range(found.parent.name, first, last)
    cited_low, cited_high = int(note.group(1)), int(note.group(2) or note.group(1))
    if cited_high < low or (high is not None and cited_low > high):
        allowed = f"pp. {low}-{high}" if high is not None else f"p. {low} or later"
        errors.append(f"{where}: cited p. {note.group(1)} but the page markers allow {allowed}")
    elif exact:
        for line in sorted({first, last}):
            if (found.parent.name, line) in MATCH_MISSES:
                continue
            best = pdfpage().locate(found.parent.name, line)[0]
            if best is not None and not cited_low <= best <= cited_high:
                warnings.append(f"{where}: cited p. {note.group(1)} but line {line} matches p. {best} in the PDF text")


def is_formula(span: str) -> bool:
    """A backticked span that reads as a formula: a relation with a variable on its right, or an expression.

    Code (`--set`, `make_edge=2`, paths), bare symbols (`γ`, `P^i`) and numbers (`p = .51`) are not formulas.
    """
    span = span.strip()
    if len(span) < 3 or span.startswith("-") or CITATION.fullmatch(f"`{span}`"):
        return False
    if re.fullmatch(r"[\w.\[\]\"']+=\S+", span) or re.search(r"\.(py|md|csv)\b", span):
        return False
    relations = list(RELATION.finditer(span))
    if relations:
        return bool(LETTER.search(span[relations[-1].end():]))
    return bool(re.search(r"[+−·√Σ∫]|/", span)) and bool(LETTER.search(span)) and (" " in span or "(" in span)


def check_formulas(text: str, rel: Path, repo: str | None, errors: list, warnings: list) -> None:
    """Rule 9: a formula quoted next to a literature citation needs a status; only checked ones under our code."""
    section = ""
    for number, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        statuses = []
        for match in CITATION.finditer(line):
            found = resolve(match.group(1), repo)
            if found and found.is_relative_to(LITERATURE) and found.name == f"{found.parent.name}.md":
                note = PDF_PAGE.match(line, match.end())
                statuses.append(note.group(3) if note else None)
        if not statuses:
            continue
        if section == "What it means for our code" and "unchecked" in statuses:
            errors.append(f"{rel}:{number}: an unchecked literature formula under 'What it means for our code'")
        if section != "Traps" and not any(statuses) and any(is_formula(s) for s in SPAN.findall(line)):
            warnings.append(f"{rel}:{number}: formula next to a literature citation without 'checked' or 'unchecked'")


def main(argv: list[str]) -> int:
    exact = "--pages" in argv
    errors, warnings, skipped, cites, unchecked = [], [], 0, 0, 0
    index_text = (WIKI / "index.md").read_text()
    inbound: dict[Path, int] = {}
    for page in pages():
        rel = page.relative_to(WIKI)
        text = page.read_text()
        fm = front_matter(text)
        for key in ("title", "type", "updated"):
            if key not in fm:
                errors.append(f"{rel}: front matter lacks '{key}'")
        if fm.get("type") and fm["type"] not in TYPES:
            errors.append(f"{rel}: unknown type '{fm['type']}'")
        if fm.get("type") == "source":
            if fm.get("status") not in STATUSES:
                errors.append(f"{rel}: source page needs status in {sorted(STATUSES)}")
            repo = fm.get("repo")
            if not repo:
                errors.append(f"{rel}: source page needs 'repo'")
        repo = fm.get("repo")
        if str(rel) not in index_text:
            errors.append(f"{rel}: not listed in index.md")
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (page.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{rel}: broken link {target}")
            else:
                inbound[resolved] = inbound.get(resolved, 0) + 1
        unchecked += len(re.findall(r"\(p\.\s*\d+(?:[-–]\d+)?,\s*unchecked\)", text))
        check_formulas(text, rel, repo, errors, warnings)
        for match in CITATION.finditer(text):
            path, start, end = match.groups()
            cites += 1
            absent = repo and repo != "none" and not ((REFERENCES / repo).is_dir() or (ROOT / repo).is_dir())
            found = None if absent else resolve(path, repo)  # the page's clone absent, its `README.md:270` would find ours
            if found is None:
                if clone_missing(path, repo):
                    skipped += 1
                else:
                    errors.append(f"{rel}: cited file not found: {path}")
                continue
            lines = found.read_text(errors="replace").split("\n")  # not splitlines(): it also splits on \f and \u2028, unlike grep
            first, last = int(start), int(end or start)
            if not 1 <= first <= last <= len(lines):
                errors.append(f"{rel}: {path}:{start}{'-' + end if end else ''} is outside the file ({len(lines)} lines)")
            elif not lines[first - 1].strip():
                warnings.append(f"{rel}: {path}:{first} is a blank line")
            elif end and found.suffix == ".py" and any(found.is_relative_to(folder) for folder in OWN_CODE):
                if not DEFINITION.match(lines[first - 1]):
                    warnings.append(f"{rel}: {path}:{start}-{end} doesn't start a definition (moved by an edit?)")
            if found.is_relative_to(LITERATURE) and found.name == f"{found.parent.name}.md":
                check_page(text, match.end(), found, first, last, f"{rel}: {path}:{start}", errors, warnings, exact)
    for line in (WIKI / "index.md").read_text().splitlines():
        for target in LINK.findall(line):
            if not target.startswith(("http", "mailto")):
                inbound[(WIKI / target).resolve()] = inbound.get((WIKI / target).resolve(), 0) + 1
    for page in pages():
        if page.resolve() not in inbound:
            warnings.append(f"{page.relative_to(WIKI)}: orphan (no page links to it)")
    for number, line in enumerate((WIKI / "log.md").read_text().splitlines(), 1):
        if line.startswith("## ") and not LOG_ENTRY.match(line):
            errors.append(f"log.md:{number}: entry does not match '## [YYYY-MM-DD] kind | title'")
    for message in warnings:
        print("warn ", message)
    for message in errors:
        print("ERROR", message)
    print(f"{len(pages())} pages, {cites} citations ({skipped} skipped: clone absent), {unchecked} formulas unchecked, "
          f"{len(warnings)} warnings, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
