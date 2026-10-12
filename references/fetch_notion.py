#!/usr/bin/env python3
"""Downloads public Notion pages (and the sub-pages they link to) as markdown.

The Prosperity wikis are public Notion pages. Notion renders them with JavaScript, so a plain page fetch returns an
empty shell. This asks the same JSON endpoints a browser uses for a public page, walks the blocks, and writes
markdown. Images and databases are not downloaded; images are kept as links, databases as a note.

Usage: python3 -I references/fetch_notion.py OUT_DIR NAME=PAGE [NAME=PAGE ...] [--max-pages N]
       PAGE is a notion URL or a 32-character page id. Pages found from NAME=PAGE go to OUT_DIR/NAME/.
Example: python3 -I references/fetch_notion.py references/prosperity-wikis \\
             prosperity3=https://imc-prosperity.notion.site/Prosperity-3-Wiki-19ee8453a09380529731c4e6fb697ea4
Only pages in the same Notion workspace as the start page are followed. Standard library only.
The output is third-party text: keep it out of git (references/ is ignored apart from named files).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from collections import deque
from datetime import date
from pathlib import Path

API = "https://www.notion.so/api/v3/"
HEX = re.compile(r"([0-9a-f]{32})", re.I)
PAUSE = 0.6  # seconds between requests (Notion answers 429 when asked faster)


def uuid(raw: str) -> str:
    h = raw.replace("-", "").lower()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def page_id(text: str) -> str | None:
    found = HEX.findall(text.replace("-", ""))
    return uuid(found[-1]) if found else None


def post(endpoint: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    for attempt in range(6):
        try:
            request = urllib.request.Request(API + endpoint, data=data, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                time.sleep(PAUSE)
                return json.load(response)
        except Exception as error:  # network hiccup or rate limit: back off and retry
            if attempt == 5:
                raise
            time.sleep(30 if "429" in str(error) else 2 * (attempt + 1))
    raise RuntimeError("unreachable")


def unwrap(record: dict) -> dict:
    value = record.get("value", {})
    return value.get("value", value) if isinstance(value, dict) else {}


class Workspace:
    def __init__(self) -> None:
        self.blocks: dict[str, dict] = {}

    def add(self, response: dict) -> None:
        for bid, record in response.get("recordMap", {}).get("block", {}).items():
            block = unwrap(record)
            if block.get("id"):
                self.blocks[bid] = block

    def load_page(self, pid: str) -> None:
        stack, chunk = [], 0
        while True:
            response = post("loadPageChunk", {"pageId": pid, "limit": 100, "cursor": {"stack": stack}, "chunkNumber": chunk, "verticalColumns": False})
            self.add(response)
            stack = response.get("cursor", {}).get("stack", [])
            if not stack:
                return
            chunk += 1

    def fetch_missing(self, ids: list[str]) -> None:
        missing = [i for i in ids if i not in self.blocks]
        for start in range(0, len(missing), 50):
            response = post("getRecordValues", {"requests": [{"table": "block", "id": i} for i in missing[start:start + 50]]})
            for item in response.get("results", []):
                block = item.get("value", {})
                block = block.get("value", block) if isinstance(block, dict) else {}
                if block.get("id"):
                    self.blocks[block["id"]] = block

    def get(self, bid: str) -> dict:
        if bid not in self.blocks:
            self.fetch_missing([bid])
        return self.blocks.get(bid, {})

    def title(self, bid: str) -> str:
        return plain(self.get(bid).get("properties", {}).get("title", [])) or "untitled"


def plain(rich: list) -> str:
    return "".join(part[0] for part in rich if part and isinstance(part[0], str))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "page"


class Crawler:
    def __init__(self, out: Path, name: str, max_pages: int) -> None:
        self.ws = Workspace()
        self.out, self.name, self.max_pages = out / name, name, max_pages
        self.queue: deque[str] = deque()
        self.files: dict[str, str] = {}
        self.done: list[tuple[str, str]] = []
        self.skipped: list[str] = []
        self.space: str | None = None

    def filename(self, pid: str) -> str:
        if pid not in self.files:
            # The start of a Notion id is shared by every page in the workspace, so use its end, and never reuse a name.
            name = f"{slug(self.ws.title(pid))}-{pid.replace('-', '')[-6:]}.md"
            while name in self.files.values():
                name = name.replace(".md", "x.md")
            self.files[pid] = name
        return self.files[pid]

    def owner_page(self, bid: str) -> str:
        """Links can point at a heading inside a page; follow the parents up to the page that holds it."""
        for _ in range(12):
            block = self.ws.get(bid)
            if not block or block.get("type") in ("page", None) or not block.get("parent_id"):
                return bid
            bid = block["parent_id"]
        return bid

    def enqueue(self, pid: str) -> None:
        if pid not in self.files:
            self.filename(pid)
            self.queue.append(pid)

    def rich(self, rich: list) -> str:
        out = []
        for part in rich:
            text = part[0]
            marks = part[1] if len(part) > 1 else []
            for mark in marks:
                kind = mark[0]
                if kind == "p":  # mention of a page
                    pid = self.owner_page(mark[1])
                    self.enqueue(pid)
                    text = f"[{self.ws.title(pid)}]({self.filename(pid)})"
                elif kind == "a":
                    url = mark[1]
                    target = page_id(url) if ("notion.site" in url or "notion.so" in url or url.startswith("/")) else None
                    if target:
                        target = self.owner_page(target)
                        self.enqueue(target)
                        text = f"[{text}]({self.filename(target)})"
                    else:
                        text = f"[{text}]({url})"
                elif kind == "b":
                    text = f"**{text}**"
                elif kind == "i":
                    text = f"*{text}*"
                elif kind == "c":
                    text = f"`{text}`"
                elif kind == "s":
                    text = f"~~{text}~~"
                elif kind == "e":
                    text = f"${mark[1]}$"
            out.append(text)
        return "".join(out)

    def render_children(self, parent: dict, indent: str, lines: list[str]) -> None:
        ids = parent.get("content", [])
        self.ws.fetch_missing(ids)
        counter = 0
        for cid in ids:
            block = self.ws.blocks.get(cid)
            if not block:
                continue
            counter = counter + 1 if block.get("type") == "numbered_list" else 0
            self.render(block, indent, lines, counter)

    def render(self, block: dict, indent: str, lines: list[str], number: int) -> None:
        kind = block.get("type", "")
        props = block.get("properties", {})
        text = self.rich(props.get("title", []))
        if kind == "page":  # a sub-page
            pid = block["id"]
            self.enqueue(pid)
            lines.append(f"{indent}- [{self.ws.title(pid)}]({self.filename(pid)})")
            return
        if kind in ("header", "sub_header", "sub_sub_header"):
            lines += ["", f"{'#' * ({'header': 2, 'sub_header': 3, 'sub_sub_header': 4}[kind])} {text}", ""]
        elif kind == "text":
            lines += [f"{indent}{text}", ""] if text else [""]
        elif kind == "bulleted_list":
            lines.append(f"{indent}- {text}")
        elif kind == "numbered_list":
            lines.append(f"{indent}{number}. {text}")
        elif kind == "to_do":
            checked = "x" if plain(props.get("checked", [])) == "Yes" else " "
            lines.append(f"{indent}- [{checked}] {text}")
        elif kind == "toggle":
            lines.append(f"{indent}- **{text}**")
        elif kind == "quote":
            lines += [f"{indent}> {text}", ""]
        elif kind == "callout":
            icon = block.get("format", {}).get("page_icon", "")
            lines += [f"{indent}> {icon} {text}".rstrip(), ""]
        elif kind == "code":
            language = plain(props.get("language", [])).lower()
            lines += [f"{indent}```{language}", plain(props.get("title", [])), f"{indent}```", ""]
        elif kind == "equation":
            lines += [f"{indent}$$ {plain(props.get('title', []))} $$", ""]
        elif kind == "divider":
            lines += ["", "---", ""]
        elif kind in ("image", "file", "pdf", "video", "audio", "embed", "bookmark", "figma"):
            source = plain(props.get("source", [])) or plain(props.get("link", []))
            caption = self.rich(props.get("caption", [])) or kind
            lines += [f"{indent}[{kind}: {caption}]({source}) (not downloaded)", ""]
        elif kind in ("alias", "link_to_page"):
            target = block.get("format", {}).get("alias_pointer", {}).get("id") or block.get("format", {}).get("link_to_page", {}).get("page_id")
            if target:
                self.enqueue(target)
                lines.append(f"{indent}- [{self.ws.title(target)}]({self.filename(target)})")
        elif kind == "table":
            self.render_table(block, lines)
            return
        elif kind in ("collection_view", "collection_view_page"):
            lines += [f"{indent}*(a Notion database lives here; not downloaded)*", ""]
        elif kind == "transclusion_reference":  # a synced copy: the content lives in the original block
            original = block.get("format", {}).get("transclusion_reference_pointer", {}).get("id")
            if original:
                self.ws.fetch_missing([original])
                self.render_children(self.ws.blocks.get(original, {}), indent, lines)
            return
        elif kind in ("column_list", "column", "transclusion_container", "sync_block"):
            pass
        elif text:
            lines += [f"{indent}{text}", ""]
        child_indent = indent + ("    " if kind in ("bulleted_list", "numbered_list", "to_do", "toggle") else "")
        self.render_children(block, child_indent, lines)

    def render_table(self, block: dict, lines: list[str]) -> None:
        order = block.get("format", {}).get("table_block_column_order", [])
        ids = block.get("content", [])
        self.ws.fetch_missing(ids)
        rows = []
        for rid in ids:
            row = self.ws.blocks.get(rid, {}).get("properties", {})
            rows.append([self.rich(row.get(col, [])).replace("|", "\\|").replace("\n", " ") for col in order])
        if not rows:
            return
        lines.append("")
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("|" + "---|" * len(rows[0]))
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    def crawl_page(self, pid: str) -> None:
        self.ws.load_page(pid)
        page = self.ws.get(pid)
        space = page.get("space_id")
        if self.space is None:
            self.space = space
        elif space != self.space:
            raise RuntimeError("a different Notion workspace; not followed")
        title = self.ws.title(pid)
        lines = [f"# {title}", "", f"*Fetched {date.today()} from the public Notion page `{pid.replace('-', '')}` by `references/fetch_notion.py`. Third-party text, not ours.*", ""]
        self.render_children(page, "", lines)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).rstrip() + "\n"
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / self.filename(pid)).write_text(text)
        self.done.append((title, self.filename(pid)))
        print(f"  {self.filename(pid)}  ({len(text)} chars)")

    def run(self, start: list[str]) -> None:
        for pid in start:
            self.enqueue(pid)
        while self.queue and len(self.done) < self.max_pages:
            pid = self.queue.popleft()
            try:
                self.crawl_page(pid)
            except Exception as error:
                self.skipped.append(f"{pid}: {error}")
                print(f"  skipped {pid}: {error}")
        self.skipped += [f"{pid} (page limit)" for pid in self.queue]
        index = [f"# {self.name}: pages downloaded {date.today()}", ""] + [f"- [{title}]({name})" for title, name in self.done]
        if self.skipped:
            index += ["", "## Not downloaded", ""] + [f"- {item}" for item in self.skipped]
        (self.out / "INDEX.md").write_text("\n".join(index) + "\n")


def main(argv: list[str]) -> int:
    max_pages = 200
    if "--max-pages" in argv:
        i = argv.index("--max-pages")
        max_pages = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if len(argv) < 3:
        print(__doc__)
        return 1
    out = Path(argv[1])
    groups: dict[str, list[str]] = {}
    for item in argv[2:]:
        name, _, page = item.partition("=")
        pid = page_id(page)
        if not pid:
            print(f"no page id in {item!r}")
            return 1
        groups.setdefault(name, []).append(pid)
    for name, starts in groups.items():
        print(name)
        Crawler(out, name, max_pages).run(starts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
