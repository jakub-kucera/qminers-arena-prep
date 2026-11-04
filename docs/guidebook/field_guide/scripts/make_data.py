"""The field guide's data: every CSV in field_guide/data/, each from a committed command or file.

usage (from the repo root; about 3 minutes, most of it calibrate):
  uv run python docs/guidebook/field_guide/scripts/make_data.py [--only NAME ...]

Needs the clones (references/clone.sh: P2 and P3's days), data/abides (experiments.abides_days) and the Varde
rehearsal's sessions, which it rebuilds if they're missing (round4/README.md). Each CSV's first comment line names
the command it came from; make_figures.py draws them. Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1] / "data"
VARDE = ROOT / "python/experiments/mock_round/round4"
VARDE_BOT = VARDE / "results/template.py"
TEMPLATE = "python/bots/template.py"


def run(args: list[str]) -> str:
    """A repo command's printed output (stdout and stderr), failing loudly."""
    done = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"failed: {' '.join(args)}\n{done.stdout[-2000:]}{done.stderr[-2000:]}")
    return done.stdout + done.stderr


def write(name: str, source: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"{name}.csv").open("w", newline="") as file:
        file.write(f"# {source}\n")
        out = csv.writer(file)
        out.writerow(header)
        out.writerows(rows)
    print(f"{name}.csv: {len(rows)} rows")


def number(text: str) -> float:
    return float(text.replace(",", "").replace("+", ""))


def total(output: str) -> float:
    return number(re.search(r"total over \d+ days: ([-\d,]+)", output).group(1))


# -- Prosperity's days, read as the engine reads them ------------------------------------------------------------

def p3_day(day: str = "1-0"):
    from arena.formats import prosperity

    return prosperity.load_days(prosperity.resolve_data_dir("p3"), [day])[0]


def wall_mid(book) -> float | None:
    if not book.bids or not book.asks:
        return None
    bid = max(book.bids, key=lambda level: abs(level[1]))[0]
    ask = max(book.asks, key=lambda level: abs(level[1]))[0]
    return (bid + ask) / 2


def order_book() -> None:
    """F2: one Kelp tick, every level a side, with its mid and wall mid."""
    day = p3_day()
    tick = next(t for t in day.ticks if len(t.books["KELP"].bids) >= 2 and len(t.books["KELP"].asks) >= 2)
    book = tick.books["KELP"]
    rows = [["bid", price, abs(volume)] for price, volume in book.bids] + [["ask", price, abs(volume)] for price, volume in book.asks]
    mid = (max(p for p, _ in book.bids) + min(p for p, _ in book.asks)) / 2
    rows += [["mid", mid, ""], ["wall_mid", wall_mid(book), ""], ["timestamp", tick.timestamp, ""]]
    write("order_book", "arena.formats.prosperity.load_days(p3, ['1-0']): KELP, the first tick with two levels a side",
          ["side", "price", "volume"], rows)


def mid_and_wall() -> None:
    """F4: 300 ticks of Kelp's mid and wall mid."""
    day = p3_day()
    rows = []
    for tick in day.ticks[:300]:
        book = tick.books["KELP"]
        if book.bids and book.asks:
            rows.append([tick.timestamp, (max(p for p, _ in book.bids) + min(p for p, _ in book.asks)) / 2, wall_mid(book)])
    write("mid_and_wall", "arena.formats.prosperity.load_days(p3, ['1-0']): KELP, ticks 0-299", ["timestamp", "mid", "wall_mid"], rows)


# -- Backtests and grids ------------------------------------------------------------------------------------------

def copies() -> None:
    """F6: the template alone, against one copy and against two (per tick)."""
    base = ["-m", "arena.backtest", TEMPLATE, "1", "--data", "p3", "--engine", "rust"]
    rows = [["alone", 1, total(run(base))]]
    for n in (1, 2):
        output = run(base + ["--vs", TEMPLATE] * n)
        rivals = re.search(r"rivals: (.+)", output).group(1)
        rows.append([f"{n} copy" if n == 1 else f"{n} copies", 1, total(output)])
        for k, value in enumerate(re.findall(r"template#\d+ ([-\d,]+)", rivals), start=2):
            rows.append([f"{n} copy" if n == 1 else f"{n} copies", k, number(value)])
    write("copies", "uv run python -m arena.backtest python/bots/template.py 1 --data p3 --engine rust [--vs python/bots/template.py]*n",
          ["field", "bot", "pnl"], rows)


def fill_modes() -> None:
    """F9: the same bot and days under each fill model."""
    base = ["-m", "arena.backtest", TEMPLATE, "1", "--data", "p3", "--engine", "rust"]
    modes = [("all", []), ("worse", ["--match-trades", "worse"]), ("none", ["--match-trades", "none"]), ("resting", ["--resting"])]
    rows = [[name, total(run(base + extra))] for name, extra in modes]
    write("fill_modes", "uv run python -m arena.backtest python/bots/template.py 1 --data p3 --engine rust [--match-trades worse|none | --resting]",
          ["mode", "pnl"], rows)


def grid_table(output: str) -> list[dict]:
    lines = output.splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("rank "))
    header = lines[at].replace("min day", "min_day").split()
    rows = []
    for line in lines[at + 1:]:
        if not line.strip() or not line.split()[0].isdigit():
            break
        rows.append(dict(zip(header, line.split())))
    return rows


def kelp_grid() -> None:
    """F10: Kelp's make_edge against take_edge, under all and worse."""
    args = ["-m", "arena.grid", TEMPLATE, "1", "--data", "p3", "--grid", "PARAMS.KELP.make_edge=0,0.5,1,1.5,2,3",
            "--grid", "PARAMS.KELP.take_edge=0,0.5,1,2", "--modes", "all,worse", "--engine", "rust", "--top", "100"]
    rows = [[r["KELP.make_edge"], r["KELP.take_edge"], number(r["pnl(all)"]), number(r["pnl(worse)"])] for r in grid_table(run(args))]
    write("kelp_grid", "uv run python -m arena.grid python/bots/template.py 1 --data p3 --grid PARAMS.KELP.make_edge=0,0.5,1,1.5,2,3 "
          "--grid PARAMS.KELP.take_edge=0,0.5,1,2 --modes all,worse --engine rust", ["make_edge", "take_edge", "pnl_all", "pnl_worse"], rows)


def shuffle() -> None:
    """F7: the shuffle test on ABIDES and on Prosperity's Kelp."""
    rows = []
    for market, data, product in (("ABIDES", "data/abides", "ABM"), ("Prosperity Kelp", "p3", "KELP")):
        output = run(["-m", "arena.grid", TEMPLATE, "1", "--data", data, "--grid", f"PARAMS.{product}.make_edge=0.5,1,2",
                      "--permute", "20", "--engine", "rust"])
        found = re.search(r"best cell's PnL: ([-+\d,]+) on the real days; on the copies mean ([-+\d,]+).*?p ([\d.]+)", output)
        rows.append([market, number(found.group(1)), number(found.group(2)), float(found.group(3))])
    write("shuffle", "uv run python -m arena.grid python/bots/template.py 1 --data data/abides|p3 --grid PARAMS.ABM|KELP.make_edge=0.5,1,2 "
          "--permute 20 --engine rust", ["market", "real", "shuffled_mean", "p"], rows)


def smile_window() -> None:
    """F8: the coupon's smile window, take_edge 0.5 (IDEAS, P2 round 4's coconut coupons)."""
    spec = ('PARAMS.COCONUT_COUPON={"limit": 600, "fair": "wall_mid", "strike": 10000, "smile": (0.0, 0.0, 0.193), '
            '"underlying": "COCONUT", "expiry": 249, "take_edge": 0.5, "make_size": 0, "clear_edge": 0}')
    args = ["-m", "arena.grid", TEMPLATE, "4", "--data", "p2", "--set", spec, "--grid", "PARAMS.COCONUT_COUPON.smile_window=20,200,1000,5000,20000",
            "--grid", "PARAMS.COCONUT_COUPON.take_edge=0.5,2,5,10", "--modes", "all,worse", "--engine", "rust", "--top", "100"]
    cells = [r for r in grid_table(run(args)) if float(r["COCONUT_COUPON.take_edge"]) == 0.5]
    rows = sorted([int(float(r["COCONUT_COUPON.smile_window"])), number(r["pnl(all)"]), number(r["min_day"])] for r in cells)
    write("smile_window", "the IDEAS row \"Prosperity 2 round 4's coconut coupons with the template's options modes\": its arena.grid command; "
          "the take_edge 0.5 cells", ["smile_window", "pnl", "min_day"], rows)


# -- The Varde rehearsal ------------------------------------------------------------------------------------------

def varde_portal():
    if not list((VARDE / "public/data").glob("session_*.jsonl")):
        subprocess.run([str(VARDE / "private/generate.sh")], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(VARDE / "private/disguise.py")], cwd=ROOT, check=True)
    spec = importlib.util.spec_from_file_location("varde_portal", VARDE / "private/portal.py")
    portal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(portal)
    return portal


def varde() -> None:
    """F3, F5 and the portal's twelve figures: the rehearsal's bot on the three public sessions, as an upload scores it
    (portal.evaluate, which `portal.py upload` calls, without counting an upload)."""
    portal = varde_portal()
    metrics, runs = portal.evaluate(VARDE_BOT, "public")
    source = "python/experiments/mock_round/round4/private/portal.py's evaluate(results/template.py, 'public')"
    write("portal_metrics", source, ["metric", "value"], [[k, v] for k, v in metrics.items()])
    write("sessions", source + ": euros; cash is after the fees", ["session", "cash", "position_value", "score", "end_position", "order_fees", "lot_fees"],
          [[name.replace("session_", "Session "), round(r["cash"], 2), round(r["score"] - r["cash"], 2), round(r["score"], 2), r["inventory"],
            round(sum(row[5] == "new" for row in r["orders_log"]) * portal.FEE_ORDER / 100, 2), round(r["volume"] * portal.FEE_LOT / 100, 2)]
           for name, r in runs.items()])
    # F5: LUMEN in session 1, steps 0-399: its mid, our position, cash and PnL at the mid (euros, fees included)
    steps = [json.loads(line) for line in (VARDE / "public/data/session_1.jsonl").read_text().splitlines()][:400]
    run1 = runs["session_1"]
    fills: dict[int, list] = {}
    for t, sym, px, qty, _, liquidity in run1["fills_log"]:
        if sym == "LUMEN":
            fills.setdefault(t, []).append((px, qty, liquidity))
    placed: dict[int, int] = {}
    for t, _, sym, _, _, status in run1["orders_log"]:
        if sym == "LUMEN" and status == "new":
            placed[t] = placed.get(t, 0) + 1
    position, cash, walk, trades = 0, 0.0, [], []
    for step in steps:
        t, book = step["t"], step["book"].get("LUMEN", {})
        cash -= placed.get(t, 0) * portal.FEE_ORDER
        for px, qty, liquidity in fills.get(t, []):
            position += qty
            cash -= qty * px + portal.FEE_LOT * abs(qty)
            trades.append([t, "buy" if qty > 0 else "sell", px / 100, abs(qty), liquidity])
        if book.get("bids") and book.get("asks"):
            mid = (book["bids"][0][0] + book["asks"][0][0]) / 2
            walk.append([t, mid / 100, position, round(cash / 100, 4), round((cash + position * mid) / 100, 4)])
    write("round_trip", source + ": LUMEN, session 1, steps 0-399", ["step", "mid", "position", "cash", "pnl"], walk)
    write("round_trip_fills", source + ": LUMEN's fills, session 1, steps 0-399", ["step", "side", "price", "lots", "liquidity"], trades)


CALIBRATE = """
import importlib.util, multiprocessing, sys
multiprocessing.set_start_method("fork")
spec = importlib.util.spec_from_file_location("varde_format", "python/experiments/mock_round/round4/results/qminers_format.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
import arena.formats
arena.formats.FORMATS["qminers"] = module
from experiments.day import calibrate
sys.exit(calibrate.main(sys.argv[1:]))
"""


def calibrate() -> None:
    """F12: calibrate's per-figure errors on the rehearsal's upload, for the best-ranked setting and the one closest
    on the fills alone (the run's plug-in registered as the day's format, as the session did)."""
    portal = varde_portal()
    metrics, _ = portal.evaluate(VARDE_BOT, "public")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "metrics.json"
        path.write_text(json.dumps({"status": "COMPLETED", "metrics": metrics}))
        output = run(["-c", CALIBRATE, "--bot", str(VARDE_BOT.relative_to(ROOT)), "--days", "all", "--data",
                      str((VARDE / "public/data").relative_to(ROOT)), "--format", "qminers", "--portal", str(path),
                      "--vary", "fill_ratio=1,0.5", "--top", "400"])
    lines = [line for line in output.splitlines() if line.startswith("| ")]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    table = {cells[0].strip("* "): cells for cells in ([c.strip() for c in line.strip("|").split("|")] for line in lines[1:])}
    figures = header[3:]
    theirs = table["the portal"]
    best = next(name for name in table if name != "the portal")
    closest = re.search(r"Closest on the fills alone \([^)]*\): (.+?), worst", output).group(1)
    rows = []
    for label, name in (("ranked best", best), ("closest on the fills", closest)):
        ours = table[name]
        for k, figure in enumerate(figures, start=3):
            a, b = number(theirs[k]), number(ours[k])
            rows.append([label, name, figure, a, b, round(abs(b - a) / abs(a), 4) if a else ("" if b == 0 else 1.0)])
    write("calibrate", "experiments.day.calibrate on the rehearsal's upload: --format qminers (round4/results/qminers_format.py) "
          "--vary fill_ratio=1,0.5", ["setting", "engine_setting", "figure", "portal", "ours", "error"], rows)


# -- The day, from the docs ---------------------------------------------------------------------------------------

def table(path: Path, heading: str) -> list[list[str]]:
    """The first Markdown table under a heading, as rows of cells (the header and its rule left out)."""
    lines = path.read_text().splitlines()
    at = next(i for i, line in enumerate(lines) if line.startswith("#") and heading in line)
    rows = []
    for line in lines[at + 1:]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif rows:
            break
    return [row for row in rows[1:] if not set(row[0]) <= set("-: ")]


def timeline() -> None:
    """F14: the weekend (ON_THE_DAY's timeline table) and one round (RUNBOOK's "Each round" table)."""
    rows, day = [], 0
    for when, official, _ in table(ROOT / "ON_THE_DAY.md", "The day: timeline and roles"):
        if when.startswith("Sun"):
            day = 24
        h1, m1, h2, m2 = map(int, re.search(r"(\d\d):(\d\d)–(\d\d):(\d\d)", when).groups())
        start, end = day + h1 + m1 / 60, day + h2 + m2 / 60
        end += 24 if end <= start else 0
        rows.append(["weekend", start, end, official.replace("**", "")])
    for when, do in table(ROOT / "RUNBOOK.md", "Each round"):
        found = re.match(r"T\+(\d):(\d\d)|deadline − (\d):(\d\d)", when)
        if not found:
            continue
        at = int(found[1]) + int(found[2]) / 60 if found[1] else 5 - int(found[3]) - int(found[4]) / 60
        rows.append(["round", round(at, 3), "", re.split(r"\. |; ", do.replace("`", ""))[0].strip()[:80]])
    write("timeline", "ON_THE_DAY.md, \"The day: timeline and roles\" (hours from Saturday 00:00) and RUNBOOK.md, \"Each round\" "
          "(hours from T, deadline at T+5)", ["part", "start", "end", "label"], rows)


STEPS = {"order_book": order_book, "mid_and_wall": mid_and_wall, "copies": copies, "fill_modes": fill_modes,
         "kelp_grid": kelp_grid, "shuffle": shuffle, "smile_window": smile_window, "varde": varde, "calibrate": calibrate, "timeline": timeline}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="+", choices=sorted(STEPS))
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "python"))
    for name in args.only or STEPS:
        STEPS[name]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
