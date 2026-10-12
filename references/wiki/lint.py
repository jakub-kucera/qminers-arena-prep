#!/usr/bin/env python3
"""Mechanical health check of references/wiki (see SCHEMA.md, "Lint").

Checks: front matter, every page listed in index.md, relative links, `path:line` citations (file exists,
line in range, line not blank), orphan pages, log.md entry format. A citation into literature_md/ must be
followed by its PDF page, `(p. N)` or `(p. N, checked)`, and N must agree with the page markers around the line
(literature_md/pdfpage.py); formulas marked `unchecked` are counted.
Citations into a clone that is not present (references/clone.sh not run) are reported as skipped, not as errors.

Usage: python3 references/wiki/lint.py        exit code 1 if there are errors. Standard library only.
"""

from __future__ import annotations

import importlib.util
import re
import sys
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
    """True if the citation points into a clone folder that is absent (not cloned here)."""
    first = path.split("/")[0]
    if repo and repo != "none" and not ((REFERENCES / repo).is_dir() or (ROOT / repo).is_dir()):
        return True
    clones = ("prosperity", "algotrade", "uchicago", "qminers", "hftbacktest", "online-snapshots")
    return "/" in path and not (REFERENCES / first).is_dir() and first.startswith(clones)


def pdfpage():
    spec = importlib.util.spec_from_file_location("pdfpage", LITERATURE / "pdfpage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_page(text: str, end: int, found: Path, first: int, last: int, where: str, errors: list, warnings: list) -> None:
    """A literature citation needs `(p. N)` right after it, and N must lie within the pages its markers allow."""
    note = PDF_PAGE.match(text, end)
    if note is None:
        warnings.append(f"{where}: literature citation without its PDF page '(p. N)'")
        return
    low, high = pdfpage().page_range(found.parent.name, first, last)
    cited_low, cited_high = int(note.group(1)), int(note.group(2) or note.group(1))
    if cited_high < low or (high is not None and cited_low > high):
        allowed = f"pp. {low}-{high}" if high is not None else f"p. {low} or later"
        errors.append(f"{where}: cited p. {note.group(1)} but the page markers allow {allowed}")


def main() -> int:
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
        for match in CITATION.finditer(text):
            path, start, end = match.groups()
            cites += 1
            found = resolve(path, repo)
            if found is None:
                if clone_missing(path, repo):
                    skipped += 1
                else:
                    errors.append(f"{rel}: cited file not found: {path}")
                continue
            lines = found.read_text(errors="replace").splitlines()
            first, last = int(start), int(end or start)
            if not 1 <= first <= last <= len(lines):
                errors.append(f"{rel}: {path}:{start}{'-' + end if end else ''} is outside the file ({len(lines)} lines)")
            elif not lines[first - 1].strip():
                warnings.append(f"{rel}: {path}:{first} is a blank line")
            if found.is_relative_to(LITERATURE) and found.name == f"{found.parent.name}.md":
                check_page(text, match.end(), found, first, last, f"{rel}: {path}:{start}", errors, warnings)
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
    sys.exit(main())
