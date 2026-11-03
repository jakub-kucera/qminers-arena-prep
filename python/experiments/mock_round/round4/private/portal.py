"""The Varde Exchange portal (organiser side). Its own matching and scoring, standard library only: nothing here
imports the qminers_arena repo, so a team's engine fit is tested against an exchange it didn't write.

    python3 private/portal.py upload BOT.py    # a team upload: the 3 public sessions, counted (at most 3)
    python3 private/portal.py hidden BOT.py    # ORGANISER ONLY: the 2 hidden sessions
    python3 private/portal.py status | reset   # uploads used / back to 0 (reset: organiser only)

`upload` prints the submission's metrics as JSON (the Arena portal's field names) and writes uploads/upload_<n>/
with metrics.json and results.zip (fills_<session>.csv, orders_<session>.csv, log.txt).

The truth (ANSWER_KEY.md):
- stated in rules.md: orders rest until filled or cancelled; a new order first trades with the book shown that
  step, at the book's prices; then the step's prints fill resting orders at the order's price, best price first,
  oldest first, on the print's side (a sell print fills bids at or above its price); per-product limits, all of a
  step's new orders for a product rejected if they could breach; 10 actions a step; 50 ms a call; a fee of 0.1
  cent per lot traded and 0.5 cent per order placed; results in euros (100 cents).
- not stated: (1) only half of each print, rounded down, is there for resting orders (the rest went to orders the
  book doesn't show); (2) open positions are valued at the VWAP of the product's last 100 prints of the session.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import statistics
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent
DATA = {"public": sorted((ROUND / "public" / "data").glob("session_*.jsonl")), "hidden": sorted((HERE / "hidden").glob("session_*.jsonl"))}
STATE = HERE / "state.json"
UPLOADS = ROUND / "uploads"
MAX_UPLOADS = 3
LIMITS = {"LUMEN": 40, "QUILL": 60, "SORREL": 30}
TICK = 5
MAX_ACTIONS = 10
BUDGET = 0.050
FEE_LOT, FEE_ORDER = 0.1, 0.5  # cents
PRINT_SHARE = 0.5  # NOT STATED: the share of a print resting orders can take
SETTLE_PRINTS = 100  # NOT STATED: the mark is the VWAP of the last this many prints


def load_strategy(path: Path, limits: dict):
    spec = importlib.util.spec_from_file_location("team_bot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Strategy(dict(limits))


def session(path: Path, bot_path: Path) -> dict:
    steps = [json.loads(line) for line in path.read_text().splitlines()]
    bot = load_strategy(bot_path, LIMITS)
    position = dict.fromkeys(LIMITS, 0)
    cash = 0.0  # cents
    fees = 0.0
    resting: list[dict] = []  # {"id", "sym", "px", "qty" (signed, what's left), "t"}
    next_id = 1
    fills_log, orders_log, log = [], [], []
    unseen_fills: list[dict] = []
    held = []  # per step, sum |position|
    last_prints: list[dict] = []
    fills = volume = 0
    for step in steps:
        t, book, prints = step["t"], step["book"], step["prints"]
        state = {"t": t, "book": json.loads(json.dumps(book)), "prints": last_prints, "position": dict(position),
                 "orders": [dict(o) for o in resting], "fills": unseen_fills, "cash": round((cash - fees) / 100, 4)}
        unseen_fills = []
        start = time.perf_counter()
        try:
            actions = bot.on_tick(state) or []
        except Exception as error:  # noqa: BLE001
            log.append(f"{t} error: {type(error).__name__}: {error}")
            actions = []
        if time.perf_counter() - start > BUDGET:
            log.append(f"{t} too slow ({(time.perf_counter() - start) * 1000:.0f} ms): actions dropped")
            actions = []
        if len(actions) > MAX_ACTIONS:
            log.append(f"{t} {len(actions)} actions: only the first {MAX_ACTIONS} taken")
            actions = actions[:MAX_ACTIONS]
        live = {sym: {"bids": [list(l) for l in b.get("bids", [])], "asks": [list(l) for l in b.get("asks", [])]} for sym, b in book.items()}
        cancels = [a for a in actions if isinstance(a, dict) and a.get("type") == "cancel"]
        places = [a for a in actions if isinstance(a, dict) and a.get("type") == "limit"]
        for a in cancels:
            found = [o for o in resting if o["id"] == a.get("id")]
            if not found:
                log.append(f"{t} cancel {a.get('id')}: no such resting order")
                continue
            resting.remove(found[0])
            orders_log.append([t, found[0]["id"], found[0]["sym"], found[0]["px"], found[0]["qty"], "cancelled"])
        by_sym: dict[str, list] = {}
        for a in places:
            sym, px, qty = a.get("sym"), a.get("px"), a.get("qty")
            if sym not in LIMITS or not isinstance(px, int) or not isinstance(qty, int) or qty == 0 or px % TICK:
                log.append(f"{t} rejected {a}: bad symbol, price (whole cents, a multiple of {TICK}) or quantity")
                continue
            by_sym.setdefault(sym, []).append(a)
        for sym, new in by_sym.items():
            buys = sum(o["qty"] for o in resting if o["sym"] == sym and o["qty"] > 0) + sum(a["qty"] for a in new if a["qty"] > 0)
            sells = -sum(o["qty"] for o in resting if o["sym"] == sym and o["qty"] < 0) - sum(a["qty"] for a in new if a["qty"] < 0)
            if position[sym] + buys > LIMITS[sym] or position[sym] - sells < -LIMITS[sym]:
                log.append(f"{t} {sym}: {len(new)} new orders rejected, they could breach the limit of {LIMITS[sym]}")
                continue
            for a in new:
                order = {"id": next_id, "sym": sym, "px": a["px"], "qty": a["qty"], "t": t}
                next_id += 1
                fees += FEE_ORDER
                orders_log.append([t, order["id"], sym, order["px"], order["qty"], "new"])
                levels = live.get(sym, {}).get("asks" if order["qty"] > 0 else "bids", [])
                for level in levels:  # trade with the book shown, at its prices
                    if order["qty"] == 0 or (order["qty"] > 0 and level[0] > order["px"]) or (order["qty"] < 0 and level[0] < order["px"]):
                        break
                    q = min(abs(order["qty"]), level[1])
                    if q <= 0:
                        continue
                    signed = q if order["qty"] > 0 else -q
                    level[1] -= q
                    order["qty"] -= signed
                    position[sym] += signed
                    cash -= signed * level[0]
                    fees += FEE_LOT * q
                    fills += 1
                    volume += q
                    fill = {"id": order["id"], "sym": sym, "px": level[0], "qty": signed}
                    fills_log.append([t, sym, level[0], signed, order["id"], "taker"])
                    unseen_fills.append(fill)
                if order["qty"]:
                    resting.append(order)
        for p in prints:  # the step's prints fill what rests, half of each
            available = int(p["qty"] * PRINT_SHARE)
            side = 1 if p["aggressor"] == "sell" else -1  # a sell print fills our bids
            eligible = [o for o in resting if o["sym"] == p["sym"] and o["qty"] * side > 0
                        and ((side > 0 and o["px"] >= p["px"]) or (side < 0 and o["px"] <= p["px"]))]
            eligible.sort(key=lambda o: (-o["px"] * side, o["t"], o["id"]))
            for o in eligible:
                if available <= 0:
                    break
                q = min(abs(o["qty"]), available)
                signed = q * side
                available -= q
                o["qty"] -= signed
                position[o["sym"]] += signed
                cash -= signed * o["px"]
                fees += FEE_LOT * q
                fills += 1
                volume += q
                fills_log.append([t, o["sym"], o["px"], signed, o["id"], "maker"])
                unseen_fills.append({"id": o["id"], "sym": o["sym"], "px": o["px"], "qty": signed})
                if o["qty"] == 0:
                    resting.remove(o)
                    orders_log.append([t, o["id"], o["sym"], o["px"], 0, "filled"])
        held.append(sum(abs(v) for v in position.values()))
        last_prints = prints
    marks = {}
    for sym in LIMITS:
        tail = [p for s in steps for p in s["prints"] if p["sym"] == sym][-SETTLE_PRINTS:]
        marks[sym] = sum(p["px"] * p["qty"] for p in tail) / max(sum(p["qty"] for p in tail), 1)
    value = sum(position[s] * marks[s] for s in LIMITS)
    return {"score": (cash - fees + value) / 100, "cash": (cash - fees) / 100, "inventory": sum(position.values()), "marks": marks,
            "fills": fills, "volume": volume, "held": held, "fills_log": fills_log, "orders_log": orders_log, "log": log}


def quantile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(int(q * len(xs)), len(xs) - 1)] if xs else 0.0


def evaluate(bot: Path, which: str) -> tuple[dict, dict]:
    runs = {path.stem: session(path, bot) for path in DATA[which]}
    scores = [r["score"] for r in runs.values()]
    last = list(runs.values())[-1]
    held = [h for r in runs.values() for h in r["held"]]
    metrics = {
        "score": round(sum(scores), 2),
        "fills": sum(r["fills"] for r in runs.values()),
        "tradedVolume": sum(r["volume"] for r in runs.values()),
        "inventory": last["inventory"],
        "cash": round(sum(r["cash"] for r in runs.values()), 2),
        "markPrice": round(statistics.fmean(last["marks"].values()) / 100, 4),
        "breachPenalty": 0.0,
        "pnlSe": round(statistics.stdev(scores) * len(scores) ** 0.5, 2) if len(scores) > 1 else 0.0,
        "absInventoryQ50": quantile(held, 0.5), "absInventoryQ68": quantile(held, 0.68),
        "absInventoryQ95": quantile(held, 0.95), "absInventoryQ997": quantile(held, 0.997),
    }
    return metrics, runs


def results_zip(runs: dict, out: Path) -> None:
    with zipfile.ZipFile(out, "w") as z:
        for name, r in runs.items():
            for kind, header, rows in (("fills", ["step", "symbol", "price_cents", "qty", "order_id", "liquidity"], r["fills_log"]),
                                       ("orders", ["step", "order_id", "symbol", "price_cents", "qty", "status"], r["orders_log"])):
                text = io.StringIO()
                w = csv.writer(text)
                w.writerow(header)
                w.writerows(rows)
                z.writestr(f"{kind}_{name}.csv", text.getvalue())
        z.writestr("log.txt", "\n".join(f"[{name}] {line}" for name, r in runs.items() for line in r["log"]) + "\n")


def static_ok(bot: Path) -> str | None:
    import ast

    try:
        tree = ast.parse(bot.read_text())
    except SyntaxError as error:
        return f"syntax error: {error}"
    if not any(isinstance(n, ast.ClassDef) and n.name == "Strategy" for n in tree.body):
        return "no top-level class Strategy"
    for node in ast.walk(tree):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
        for name in names:
            if name.split(".")[0] not in getattr(sys, "stdlib_module_names", {name.split(".")[0]}):  # 3.10+; older Pythons skip the check
                return f"import outside the standard library: {name}"
    return None


def main(argv: list[str]) -> int:
    state = json.loads(STATE.read_text()) if STATE.exists() else {"uploads": 0}
    if argv[:1] == ["status"]:
        print(json.dumps(state))
        return 0
    if argv[:1] == ["reset"]:
        STATE.write_text(json.dumps({"uploads": 0}))
        return 0
    if len(argv) != 2 or argv[0] not in ("upload", "hidden"):
        print(__doc__)
        return 2
    bot = Path(argv[1]).resolve()
    problem = static_ok(bot)
    if problem:
        print(json.dumps({"status": "REJECTED", "reason": problem}))
        return 1
    if argv[0] == "upload":
        if state["uploads"] >= MAX_UPLOADS:
            print(json.dumps({"status": "REJECTED", "reason": f"all {MAX_UPLOADS} public submissions used"}))
            return 1
        state["uploads"] += 1
        STATE.write_text(json.dumps(state))
    metrics, runs = evaluate(bot, "public" if argv[0] == "upload" else "hidden")
    if argv[0] == "upload":
        folder = UPLOADS / f"upload_{state['uploads']}"
        folder.mkdir(parents=True, exist_ok=True)
        results_zip(runs, folder / "results.zip")
        (folder / "metrics.json").write_text(json.dumps({"status": "COMPLETED", "metrics": metrics}, indent=2))
        print(f"results: {folder / 'results.zip'}; metrics: {folder / 'metrics.json'}", file=sys.stderr)
    print(json.dumps({"status": "COMPLETED", "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
