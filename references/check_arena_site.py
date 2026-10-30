#!/usr/bin/env python3
"""Extracts the English and Czech text of arena.qminers.com and diffs it against a saved snapshot.

The site is a JavaScript app: a plain fetch of the page returns an empty <div id="root">. All its text,
including the official rules and the portal's messages, sits in the JavaScript bundle, so this
downloads the bundle and pulls out the readable string literals.

Usage: references/check_arena_site.py           diff the live site against arena-site-snapshot.txt
       references/check_arena_site.py --save    overwrite the snapshot with the live site
Exit code 1 if anything changed. Standard library only.

Besides the text it records what a new build could add without new prose (2026-10-30): the bundle's
SHA-256 and Last-Modified on the first line, every path the app names (its routes and its API calls,
`/rounds/current`, `/evaluations/${e}/final`, ...), and the translation namespaces no code reads (the
10/20/30/40% scoreboard sat in one). Short strings are kept where they are a translation's value
("PnL", "Tie", "Final"), which the length filter used to drop.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

SITE = "https://arena.qminers.com/"
SNAPSHOT = Path(__file__).with_name("arena-site-snapshot.txt")
FIRST_STRING = "Algo Trade Arena challenges you"  # the first app string; the code before it is libraries
NOT_TEXT = re.compile(r"=>|function\s*\(|\bvar \b|prototype|webpack|https?://|\\u00|[;]{2}")


def fetch(url: str) -> str:
    return fetch_with_headers(url)[0]


def fetch_with_headers(url: str) -> tuple[str, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace"), dict(response.headers)


def rules_text(bundle: str) -> list[str]:
    """The official rules are a JSON document inside a template literal."""
    match = re.search(r"JSON\.parse\(`(\{\"title\":\"Official Rules\".*?)`\)", bundle, re.S)
    if not match:
        return ["(official rules not found in the bundle: the site's code has changed)"]
    document = json.loads(match.group(1).replace("\\\\", "\\"))
    lines = []
    for section in document["sections"]:
        lines.append(f"## {section['title']}")
        for block in section["blocks"]:
            if block["type"] == "org":
                lines.append(f"[org] {block['name']}")
            elif "text" in block:
                lines.append(block["text"])
            else:
                lines.extend(f"  - {item}" for item in block.get("items", []))
    return lines


def ui_strings(bundle: str) -> list[str]:
    """Readable string literals of the app itself, in file order, without duplicates."""
    # Start on the opening quote of the first app string, so that quotes pair up correctly after it.
    start = max(bundle.find(FIRST_STRING) - 1, 0)
    literal = r'"((?:[^"\\]|\\.){0,800})"|\'((?:[^\'\\]|\\.){0,800})\'|`((?:[^`\\]|\\.){0,2000})`'
    seen, out = set(), []
    text_part = bundle[start:]
    for match in re.finditer(literal, text_part):
        raw = next(group for group in match.groups() if group is not None)
        try:
            text = json.loads('"' + raw.replace('"', '\\"').replace("\n", "\\n") + '"')
        except ValueError:
            text = raw
        # Short strings still have to be matched, or the quotes stop pairing up; they are kept only as a
        # translation's value (`key:"PnL"`), capitalised, which is how the portal's labels are written.
        value = re.search(r"[\w$\"']\s*:\s*$", text_part[max(match.start() - 40, 0):match.start()]) is not None
        short = len(text) < 6 and not (value and text[:1].isupper() and re.fullmatch(r"[A-Za-zÀ-ž%/ .]{2,}", text))
        if short or text in seen or NOT_TEXT.search(text) or not re.search(r"[A-Za-zÀ-ž]{2,}", text) or (len(text) >= 6 and not re.search(r"[A-Za-zÀ-ž]{3,}", text)):
            continue
        seen.add(text)
        out.append(" ".join(text.split()))
    return out


def paths(bundle: str) -> list[str]:
    """Every route and API path the app names, as written (template parameters kept), sorted."""
    found = re.findall(r'"(/[a-z][A-Za-z0-9/_.-]{1,80})"|`(/[a-z][^`\s]{1,120})`', bundle)
    return sorted({a or b for a, b in found if not (a or b).startswith("/assets/")})


def _object(bundle: str, name: str) -> str | None:
    """The source of the object literal assigned to `name` (`name={...}`), braces matched."""
    match = re.search(r"(?<![\w$])" + re.escape(name) + r"=\{", bundle)
    if not match:
        return None
    depth, i = 0, match.end() - 1
    for j in range(i, len(bundle)):
        depth += {"{": 1, "}": -1}.get(bundle[j], 0)
        if depth == 0:
            return bundle[i + 1 : j]
    return None


def unused_namespaces(bundle: str) -> list[str]:
    """The English translation's top-level keys that no code reads (no t("key...."), no keyPrefix or namespace of it)."""
    match = re.search(r"resources:\{en:\{translation:([\w$]+)\}", bundle)
    body = _object(bundle, match.group(1)) if match else None
    if body is None:
        return ["(the translations weren't found: the site's code has changed)"]
    keys = re.findall(r"(?:^|,)\s*([A-Za-z_$][\w$]*)\s*:", body)
    used = lambda key: re.search(r"[\"'`]" + re.escape(key) + r"[.\"'`]", bundle.replace(body, "")) is not None
    return sorted(key for key in dict.fromkeys(keys) if not used(key))


def snapshot_text() -> str:
    html = fetch(SITE)
    path = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if not path:
        raise SystemExit("no JavaScript bundle found on the page")
    bundle, headers = fetch_with_headers(SITE.rstrip("/") + path.group(1))
    digest = hashlib.sha256(bundle.encode("utf-8")).hexdigest()
    header = f"# saved {date.today()} from {path.group(1)} (sha256 {digest[:16]}, last modified {headers.get('Last-Modified', '?')})"
    return "\n".join([header, "# ===== OFFICIAL RULES", *rules_text(bundle), "# ===== APP STRINGS", *ui_strings(bundle),
                      "# ===== PATHS (routes and API calls)", *paths(bundle),
                      "# ===== TRANSLATION NAMESPACES NO CODE READS", *unused_namespaces(bundle)]) + "\n"


def main() -> int:
    live = snapshot_text()
    if "--save" in sys.argv:
        SNAPSHOT.write_text(live)
        print(f"saved {SNAPSHOT.name}: {live.count(chr(10))} lines")
        return 0
    old = SNAPSHOT.read_text() if SNAPSHOT.exists() else ""
    keep = lambda text: [re.sub(r"^# saved \S+ ", "# ", line) for line in text.splitlines()]  # the date apart; a new build shows
    diff = list(difflib.unified_diff(keep(old), keep(live), "snapshot", "live", lineterm="", n=0))
    print("\n".join(diff) if diff else "arena.qminers.com: no change since the snapshot")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
