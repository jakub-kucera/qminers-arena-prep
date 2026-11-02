"""Can Kronos, a pretrained forecaster of price bars, see more in a product's prices than the simple fits
a stdlib bot can carry?

usage (from the repo root):
  uv run python -m experiments.study.kronos_zeroshot setup        # Kronos's environment and weights, data/kronos (once)
  uv run python -m experiments.study.kronos_zeroshot              # P3 and P4 round 1, every day, mini and small
  uv run python -m experiments.study.kronos_zeroshot --models base --days 0     # the 102M model, one day each
  uv run python -m experiments.study.kronos_zeroshot --data DIR --round 1 --days 0 1 [--products ...]

Kronos (references/kronos; Shi et al., AAAI 2026, arXiv 2508.02739) is a decoder-only transformer
pretrained on 1-minute to weekly OHLCV bars of real exchanges, which it quantises into tokens. It can't
go in a bot: it needs torch and 31 MB of weights or more, and sees no book. The question is whether it
is worth running beside the day's data as a detector: if it forecasts a product's bars better than an
AR fit, a reversion to a 5-bar mean, or a reversion to the wall mid, all fitted on the same window,
the product has structure our rules miss.

Kronos runs in its own environment (data/kronos/env: Python 3.12, torch, numpy, pandas), never
imported here: this module runs python/experiments/kronos_export/forecast.py under it, once per model
and dataset (its docstring has the bars, the forecasters and the scores), and prints the means over
days. Bars of 10 ticks, 256 bars of context, origins every 4 bars, 10 sampled paths averaged; on an
Apple M-series GPU a day of one product takes about 8 s (mini), 33 s (small) and 140–340 s (base).
Results go into IDEAS.md ("A pretrained bar forecaster (Kronos) as a detector").
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from arena.formats.prosperity import list_days, resolve_data_dir

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "kronos"
ENV = DATA / "env"
KRONOS = ROOT / "references" / "kronos"
FORECAST = ROOT / "python" / "experiments" / "kronos_export" / "forecast.py"
REQUIREMENTS = ["torch==2.15.0", "numpy", "pandas", "einops==0.8.1", "huggingface_hub==0.33.1", "safetensors", "tqdm"]
FORECASTERS = ("ar1", "ar5", "sma_rev", "wall_rev")


def environment(offline: bool) -> dict:
    env = {**os.environ, "PYTHONPATH": str(KRONOS), "HF_HOME": str(DATA / "hf")}
    if offline:
        env["HF_HUB_OFFLINE"] = "1"
    return env


def setup() -> None:
    """Makes data/kronos/env and downloads the pinned models into data/kronos/hf (about 560 MB)."""
    if not (KRONOS / "model" / "kronos.py").exists():
        sys.exit("needs references/kronos: run references/clone.sh")
    subprocess.run(["uv", "venv", "--python", "3.12", str(ENV)], check=True)
    subprocess.run(["uv", "pip", "install", "--python", str(ENV / "bin" / "python"), *REQUIREMENTS], check=True)
    subprocess.run([str(ENV / "bin" / "python"), str(FORECAST), "--download"], check=True, env=environment(False))


def forecast(model: str, folder: Path, round_num: int, days: list[int], products: list[str]) -> list[dict]:
    python = ENV / "bin" / "python"
    if not python.exists():
        sys.exit("needs Kronos's environment: uv run python -m experiments.study.kronos_zeroshot setup")
    cmd = [str(python), str(FORECAST), "--model", model, "--csv-dir", str(folder / f"round{round_num}"),
           "--round", str(round_num), "--days", *map(str, days), "--products", *products]
    done = subprocess.run(cmd, env=environment(True), capture_output=True, text=True)
    if done.returncode:
        sys.exit(done.stderr)
    return [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]


def products_of(folder: Path, round_num: int, day: int) -> list[str]:
    with open(folder / f"round{round_num}" / f"prices_round_{round_num}_day_{day}.csv", newline="") as f:
        return sorted({row["product"] for row in csv.DictReader(f, delimiter=";")})


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def report(rows: list[dict], models: list[str]) -> None:
    products = sorted({r["product"] for r in rows})
    for key, label in (("h1", "R2 against no move, 1 bar (10 ticks) ahead"), ("h5", "R2 against no move, 5 bars ahead"),
                       ("ic1", "IC, 1 bar ahead")):
        h, metric = ("h1", "ic") if key == "ic1" else (key, "r2")
        print(f"\n{label} (mean over days)")
        print(f"{'product':22}" + "".join(f"{m:>9}" for m in models) + "".join(f"{f:>10}" for f in FORECASTERS))
        for p in products:
            line = f"{p:22}"
            for m in models:
                v = [r[f"{h}_kronos"][metric] for r in rows if r["product"] == p and r["model"] == m]
                line += f"{mean(v):+9.2f}" if v else f"{'':9}"
            base = [r for r in rows if r["product"] == p and r["model"] == models[0]]  # the fits are deterministic
            line += "".join(f"{mean([r[f'{h}_{f}'][metric] for r in base]):+10.2f}" for f in FORECASTERS)
            print(line)
    print("\nKronos's mean 5-bar forecast against the realised mean, the tokenizer's round-trip error on the last "
          "close (ticks), the bars' lag-1 autocorrelation, seconds a day")
    for p in products:
        for m in models:
            v = [r for r in rows if r["product"] == p and r["model"] == m]
            if v:
                print(f"{p:22}{m:>6}  forecast {mean([r['kronos_mean_h'] for r in v]):+7.2f}  realised "
                      f"{mean([r['real_mean_h'] for r in v]):+7.2f}  round trip {mean([r['recon_mae'] for r in v]):5.2f}  "
                      f"lag-1 {mean([r['lag1'] for r in v]):+.2f}  {mean([r['secs'] for r in v]):5.0f} s")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.study.kronos_zeroshot")
    parser.add_argument("command", nargs="?", choices=["setup"], help="make Kronos's environment (data/kronos)")
    parser.add_argument("--data", nargs="+", default=["p3", "p4"], help="Prosperity-layout folders or p2/p3/p4")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--days", type=int, nargs="+", help="default: every day of the round")
    parser.add_argument("--products", nargs="+", help="default: every product in the round's files")
    parser.add_argument("--models", default="mini,small", help="any of mini, small, base")
    args = parser.parse_args(argv)
    if args.command == "setup":
        setup()
        return
    models = args.models.split(",")
    rows = []
    for name in args.data:
        folder = resolve_data_dir(name)
        days = args.days or [d for r, d in list_days(folder) if r == args.round]
        products = args.products or products_of(folder, args.round, days[0])
        for model in models:
            start = time.time()
            rows += forecast(model, folder, args.round, days, products)
            print(f"{name} round {args.round} days {days}, {model}: {time.time() - start:.0f} s", file=sys.stderr)
    report(rows, models)


if __name__ == "__main__":
    main()
