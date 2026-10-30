"""ORGANISER ONLY: can experiments.day.calibrate recover TRUTH from one upload's figures?

    uv run python <ROUND>/private/check_calibrate.py BOT.py UPLOAD_DIR

Runs calibrate's own candidates() x --vary delay=0,1 (144 settings) on the public sessions, through the
portal's loader and adapter (what a team's plug-in would do), on a base of the STATED rules only
(resting, fee_bps 2, maker_fee_bps -0.5, max_actions 6, max_resting 3, limit_penalty 0.25), and scores
each with calibrate's figures() and error() against UPLOAD_DIR/metrics.json plus each product's fills
and volume from the results ZIP's executions CSVs (as calibrate's --results adds them).
"""
import csv
import io
import json
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portal  # noqa: E402
from arena.engine import EngineConfig, QueueModel, TradeMatching, Mark  # noqa: E402
from experiments.day.calibrate import PORTAL, candidates, describe, error, figures  # noqa: E402

STATED = EngineConfig(resting=True, fee_bps=2.0, maker_fee_bps=-0.5, max_actions=6, max_resting=3, limit_penalty=0.25)


def score(bot, config, theirs):
    portal.TRUTH = config
    dates = portal.sessions(portal.DATA["public"])
    results = [portal.run_session(bot, str(portal.DATA["public"]), d)[0] for d in dates]
    ours = figures(results, portal.UNIT, config.limit_penalty)
    err, nearest = error(ours, theirs)
    return err, nearest


def main():
    bot, up = str(Path(sys.argv[1]).resolve()), Path(sys.argv[2])
    doc = json.loads((up / "metrics.json").read_text())
    theirs = {k: float(v) for k, v in doc["metrics"].items() if k in PORTAL and v is not None}
    with zipfile.ZipFile(next(up.glob("*.zip"))) as z:
        for name in z.namelist():
            if name.startswith("executions_"):
                for row in csv.DictReader(io.StringIO(z.read(name).decode())):
                    theirs[f"fills {row['symbol']}"] = theirs.get(f"fills {row['symbol']}", 0.0) + 1
                    theirs[f"volume {row['symbol']}"] = theirs.get(f"volume {row['symbol']}", 0.0) + int(row["qty"])
    configs = candidates(STATED, {"delay": [0, 1]})
    with ProcessPoolExecutor() as pool:
        scored = list(pool.map(score, [bot] * len(configs), configs, [theirs] * len(configs)))
    ranked = sorted(zip(configs, scored), key=lambda x: x[1][0])
    print(f"{len(configs)} settings against {len(theirs)} figures from {up}")
    for config, (err, nearest) in ranked[:8]:
        print(f"{err:7.2%}  {describe(config)}")
    truth = next(e for c, (e, _) in zip(configs, scored) if c == replace(portal.TRUTH.__class__(**{**STATED.__dict__}), trade_matching=TradeMatching.WORSE, queue=QueueModel.PROB, mark=Mark.LAST, delay=1))
    print(f"TRUTH's own error: {truth:.2%}")


if __name__ == "__main__":
    main()
