"""The reference clones are on the commits pinned in references/clone.sh.

The wiki's citations, the parity test and the results in IDEAS.md were made on those commits.
Clones that aren't there are skipped (references/clone.sh fetches them).
"""

import re
import subprocess
from pathlib import Path

import pytest

REFERENCES = Path(__file__).parents[2] / "references"
PINS = re.findall(r'^\s*"(\S+)\s+(\S+)\s+([0-9a-f]{40})"$', (REFERENCES / "clone.sh").read_text(), re.M)


def test_every_repo_has_a_pin():
    assert len(PINS) >= 18


@pytest.mark.parametrize("folder, repo, pin", PINS, ids=[folder for folder, _, _ in PINS])
def test_clone_is_on_its_pin(folder, repo, pin):
    if not (REFERENCES / folder / ".git").is_dir():
        pytest.skip(f"{folder} not cloned: run references/clone.sh")
    head = subprocess.run(["git", "-C", str(REFERENCES / folder), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    assert head.stdout.strip() == pin, f"{folder} is off its pin: run references/clone.sh"
