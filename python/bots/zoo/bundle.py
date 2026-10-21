"""Prints SPEC.md and one prompt from PROMPTS.md as a single message, ready to paste into a chat.

    python3 python/bots/zoo/bundle.py baseline | pbcopy     # macOS: straight to the clipboard
    python3 python/bots/zoo/bundle.py --list
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).parent


def prompts() -> dict[str, str]:
    text = (HERE / "PROMPTS.md").read_text()
    sections = re.split(r"^## (\S+)\n", text, flags=re.MULTILINE)
    return {name: body.strip() for name, body in zip(sections[1::2], sections[2::2])}


def bundle(name: str) -> str:
    return (HERE / "SPEC.md").read_text().strip() + "\n\n---\n\n" + prompts()[name] + "\n"


if __name__ == "__main__":
    available = prompts()
    if len(sys.argv) != 2 or sys.argv[1] not in [*available, "--list"]:
        sys.exit(f"usage: bundle.py NAME | --list   (names: {', '.join(available)})")
    print("\n".join(available) if sys.argv[1] == "--list" else bundle(sys.argv[1]), end="" if sys.argv[1] != "--list" else "\n")
