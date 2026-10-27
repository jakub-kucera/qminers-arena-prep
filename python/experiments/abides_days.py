"""Days from ABIDES's RMSC04, a market simulator we didn't write, in the Prosperity layout.

usage (from the repo root):
  uv run python -m experiments.abides_days setup                    # ABIDES's own environment, data/abides/env (once)
  uv run python -m experiments.abides_days generate --days 10       # seeds 1..10 -> data/abides (round 1, days 1..10)
  uv run python -m arena.diagnose 1 --data data/abides              # then any tool, with --data data/abides

Every number in IDEAS.md comes from Prosperity's generator or from arena.sim, calibrated to it.
ABIDES's RMSC04 (references/abides-jpmc, JP Morgan's public ABIDES; Byrd et al.) is one stock,
"ABM", traded by 1,000 noise agents, 102 value agents who see a noisy view of a mean-reverting
fundamental, 12 momentum agents and 2 adaptive market makers, from 09:30 to 16:00. Its book has
no exchange bot's wall at the fair value, and its value agents carry information.

ABIDES runs in its own environment (Python 3.10, numpy, pandas, scipy), never imported here:
`generate` runs python/experiments/abides_export/export.py under data/abides/env/bin/python for
each seed, which writes a day's book, trades and fundamental as plain CSV under data/abides/raw/,
and this module converts them (standard library only):

  - a tick per second: 23,400 a day, timestamps 0, 100, 200, ... as Prosperity's; the book at the
    end of each second, three levels a side, prices in cents (the fundamental starts at 100,000);
  - the market trades at tick k are those of the second after its snapshot, (k, k+1]: the flow
    that meets the quotes a bot sends after seeing tick k;
  - buyer and seller are blank (anonymous, as the Arena may be); with --names, each side's agent
    type (NoiseAgent, ValueAgent, MomentumAgent, AdaptiveMarketMakerAgent), for an upper bound on
    what names would give;
  - the position limit is LIMIT (100 lots: about the volume at the best, two median trades);
  - fundamental_round_1_day_<D>.csv holds the oracle's value at each tick, the answer key.

The days are gitignored; the seeds make them again exactly. A recording of an agent market: it
tests the book's shape and the agents' information, not a market that reacts to our orders
(`TODO.md`, "The edge plan").
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "abides"
ENV = DATA / "env"
ABIDES = ROOT / "references" / "abides-jpmc"
EXPORT = Path(__file__).resolve().parent / "abides_export"
PRODUCT = "ABM"
LIMIT = 100
LEVELS = 3
TICK = 100  # timestamps a second apart, as Prosperity's ticks
REQUIREMENTS = ["numpy<2", "pandas<2.2", "scipy<1.14", "tqdm", "coloredlogs", "psutil"]


def setup() -> None:
    """Makes data/abides/env: Python 3.10 with the libraries ABIDES needs, from wheels. ABIDES's own
    pins (numpy 1.22, pandas 1.2, pomegranate 0.14, gym, ray) don't build on Apple silicon; its code
    runs on these, and export.py's folder supplies the one pomegranate class RMSC04 uses."""
    if not (ABIDES / "abides-markets").exists():
        sys.exit("needs references/abides-jpmc: run references/clone.sh")
    subprocess.run(["uv", "venv", "--python", "3.10", str(ENV)], check=True)
    subprocess.run(["uv", "pip", "install", "--python", str(ENV / "bin" / "python"), *REQUIREMENTS], check=True)


def export(seed: int, out: Path, end: str = "16:00:00", extra: list[str] | None = None) -> dict:
    """Runs one RMSC04 day under ABIDES's Python (extra: export.py's --bot, --set, --resting); returns its meta.json."""
    python = ENV / "bin" / "python"
    if not python.exists():
        sys.exit("needs ABIDES's environment: uv run python -m experiments.abides_days setup")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(
        [str(ABIDES / "abides-core"), str(ABIDES / "abides-markets"), str(EXPORT)])}
    subprocess.run([str(python), str(EXPORT / "export.py"), "--seed", str(seed), "--out", str(out), "--end", end, *(extra or [])],
                   check=True, env=env, cwd=out.parent, stdout=subprocess.DEVNULL)
    return json.loads((out / "meta.json").read_text())


def convert(raw: Path, data_dir: Path, day: int, names: bool = False, round_num: int = 1) -> int:
    """Writes one exported day (raw/book.csv, trades.csv, fundamental.csv, meta.json) as
    round<round_num>/prices_..., trades_... and fundamental_... day <day>; returns the ticks written."""
    meta = json.loads((raw / "meta.json").read_text())
    folder = data_dir / f"round{round_num}"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"round_{round_num}_day_{day}"

    with (raw / "book.csv").open(newline="") as file:
        rows = list(csv.DictReader(file))
    # Ticks start at the first second with both sides quoted (the makers arrive a few seconds in).
    first = next(i for i, r in enumerate(rows) if r["bid_price_1"] and r["ask_price_1"])
    rows = rows[first:]
    with (folder / f"prices_{stem}.csv").open("w", newline="") as file:
        out = csv.writer(file, delimiter=";")
        out.writerow(["day", "timestamp", "product"]
                     + [f"{side}_{kind}_{k}" for side in ("bid", "ask") for k in range(1, LEVELS + 1) for kind in ("price", "volume")]
                     + ["mid_price", "profit_and_loss"])
        for k, r in enumerate(rows):
            row = [day, k * TICK, PRODUCT]
            for side in ("bid", "ask"):
                for level in range(1, LEVELS + 1):
                    row += [r[f"{side}_price_{level}"], r[f"{side}_volume_{level}"]]
            bid, ask = r["bid_price_1"], r["ask_price_1"]
            row += [f"{(int(bid) + int(ask)) / 2:.1f}" if bid and ask else "", "0.0"]
            out.writerow(row)

    snapshot_ns = meta["open_ns"] + (first + 1) * 1_000_000_000  # tick 0's snapshot: the end of its second
    with (raw / "trades.csv").open(newline="") as file, (folder / f"trades_{stem}.csv").open("w", newline="") as dest:
        out = csv.writer(dest, delimiter=";")
        out.writerow(["timestamp", "buyer", "seller", "symbol", "currency", "price", "quantity"])
        for t in csv.DictReader(file):
            k = (int(t["time_ns"]) - snapshot_ns - 1) // 1_000_000_000  # in the second after tick k's snapshot
            if not 0 <= k < len(rows):
                continue
            buyer, seller = "", ""
            if names:
                aggressor, passive = t["aggressor_agent_type"], t["passive_agent_type"]
                buyer, seller = (aggressor, passive) if t["aggressor"] == "BUY" else (passive, aggressor)
            out.writerow([k * TICK, buyer, seller, PRODUCT, "CENTS", f"{int(t['price']):.1f}", t["quantity"]])

    with (raw / "fundamental.csv").open(newline="") as file:
        points = [(int(r["time_ns"]), float(r["value"])) for r in csv.DictReader(file)]
    times = [t for t, _ in points]
    with (folder / f"fundamental_{stem}.csv").open("w", newline="") as file:
        out = csv.writer(file, delimiter=";")
        out.writerow(["timestamp", "product", "value"])
        for k in range(len(rows)):
            i = bisect.bisect_right(times, snapshot_ns + k * 1_000_000_000) - 1  # the value at the snapshot
            if i >= 0:
                out.writerow([k * TICK, PRODUCT, f"{points[i][1]:.3f}"])

    limits_path = data_dir / "limits.json"
    limits = json.loads(limits_path.read_text()) if limits_path.exists() else {}
    limits[PRODUCT] = LIMIT
    limits_path.write_text(json.dumps(limits, indent=2, sort_keys=True) + "\n")
    return len(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.abides_days")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="make ABIDES's environment (data/abides/env)")
    gen = sub.add_parser("generate", help="run and convert RMSC04 days")
    gen.add_argument("--days", type=int, default=10)
    gen.add_argument("--seed", type=int, default=1, help="the first day's seed; day d uses seed + d - 1")
    gen.add_argument("--out", type=Path, default=DATA, help="the data folder (default data/abides)")
    gen.add_argument("--end", default="16:00:00", help="the close (09:30 open; RMSC04's own default is 10:00:00)")
    gen.add_argument("--names", action="store_true", help="buyer and seller as the agents' types, not blank")
    args = parser.parse_args(argv)
    if args.command == "setup":
        setup()
        return
    for d in range(1, args.days + 1):
        raw = args.out / "raw" / f"seed{args.seed + d - 1}"
        raw.mkdir(parents=True, exist_ok=True)
        meta = export(args.seed + d - 1, raw, args.end)
        ticks = convert(raw, args.out, d, names=args.names)
        print(f"day {d}: seed {meta['seed']}, {ticks:,} ticks, {meta['trades']:,} trades, {meta['runtime_s']} s")


if __name__ == "__main__":
    main()
