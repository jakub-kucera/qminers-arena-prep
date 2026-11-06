"""calibrate against the 2026-11-03 rehearsal's portal: which engine settings reproduce an exchange that isn't ours?

usage (from the repo root; the round's sessions rebuilt first if missing, python/experiments/mock_round/round4/README.md):
  uv run python -m experiments.study.varde_calibrate [calibrate's options, e.g. --vary order_fee=0,0.005 --jobs 2]

The rehearsal's portal (private/portal.py) matches and scores in its own code: half of each print for
resting orders, a fee of 0.5 cents an order placed and 0.1 a lot, positions at a 100-print VWAP. Its
upload of results/template.py scored 367.61 euros, and calibrate refused every setting it tried (98% off at
best: IDEAS.md, "The kickoff prompts on a disguised round"). This registers the round's own plug-in
(results/qminers_format.py) as the format qminers, takes the portal's figures for the same file from
portal.evaluate (the public sessions, as an upload scores them, without counting one) and runs
experiments.day.calibrate on them, with any of its options. Standard library only.
"""

from __future__ import annotations

import importlib.util
import json
import multiprocessing
import sys
import tempfile
from pathlib import Path

ROUND = Path("python/experiments/mock_round/round4")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not list((ROUND / "public/data").glob("session_*.jsonl")):
        raise SystemExit("the round's sessions are missing: rebuild them as python/experiments/mock_round/round4/README.md says")
    multiprocessing.set_start_method("fork", force=True)  # calibrate's workers see the registered plug-in
    import arena.formats

    arena.formats.FORMATS["qminers"] = _load("varde_format", ROUND / "results/qminers_format.py")
    from experiments.day import calibrate

    bot = ROUND / "results/template.py"
    metrics, _ = _load("varde_portal", ROUND / "private/portal.py").evaluate(bot.resolve(), "public")
    with tempfile.TemporaryDirectory() as folder:
        portal = Path(folder) / "metrics.json"
        portal.write_text(json.dumps({"status": "COMPLETED", "metrics": metrics}))
        return calibrate.main(["--bot", str(bot), "--days", "all", "--data", str(ROUND / "public/data"), "--format", "qminers",
                               "--portal", str(portal), *argv])


if __name__ == "__main__":
    sys.exit(main())
