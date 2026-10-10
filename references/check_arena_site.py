#!/usr/bin/env python3
"""Extracts the English and Czech text of arena.qminers.com and diffs it against a saved snapshot.

The site is a JavaScript app: a plain fetch of the page returns an empty <div id="root">. All its text,
including the official rules and the portal's messages, sits in the JavaScript bundle, so this
downloads the bundle and pulls out the readable string literals.

Usage: references/check_arena_site.py           diff the live site against arena-site-snapshot.txt
       references/check_arena_site.py --save    overwrite the snapshot with the live site
Exit code 1 if the text changed. Standard library only.
"""

import difflib
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
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


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
    for match in re.finditer(literal, bundle[start:]):
        raw = next(group for group in match.groups() if group is not None)
        try:
            text = json.loads('"' + raw.replace('"', '\\"').replace("\n", "\\n") + '"')
        except ValueError:
            text = raw
        # Short strings still have to be matched, or the quotes stop pairing up, but aren't worth keeping.
        if len(text) < 6 or text in seen or NOT_TEXT.search(text) or not re.search(r"[A-Za-zÀ-ž]{3,}", text):
            continue
        seen.add(text)
        out.append(" ".join(text.split()))
    return out


def snapshot_text() -> str:
    html = fetch(SITE)
    path = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if not path:
        raise SystemExit("no JavaScript bundle found on the page")
    bundle = fetch(SITE.rstrip("/") + path.group(1))
    header = f"# saved {date.today()} from {path.group(1)}"
    return "\n".join([header, "# ===== OFFICIAL RULES", *rules_text(bundle), "# ===== APP STRINGS", *ui_strings(bundle)]) + "\n"


def main() -> int:
    live = snapshot_text()
    if "--save" in sys.argv:
        SNAPSHOT.write_text(live)
        print(f"saved {SNAPSHOT.name}: {live.count(chr(10))} lines")
        return 0
    old = SNAPSHOT.read_text() if SNAPSHOT.exists() else ""
    keep = lambda text: [line for line in text.splitlines() if not line.startswith("# saved")]
    diff = list(difflib.unified_diff(keep(old), keep(live), "snapshot", "live", lineterm="", n=0))
    print("\n".join(diff) if diff else "arena.qminers.com: no change since the snapshot")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
