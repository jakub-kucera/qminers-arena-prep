"""One ABIDES RMSC04 day, written as plain CSV for experiments.abides_days to convert.

Run by ABIDES's own Python (data/abides/env, made by `uv run python -m experiments.abides_days
setup`), never imported by the repo's code or tests: it imports ABIDES and numpy, which the repo
doesn't. experiments.abides_days runs it as

    data/abides/env/bin/python python/experiments/abides_export/export.py --seed S --out DIR [--end 16:00:00]

with PYTHONPATH set to ABIDES's two packages (references/abides-jpmc/abides-core, abides-markets)
and to this folder, whose pomegranate.py stands in for the one class RMSC04 uses.

Writes to DIR:
  book.csv         the book after the last event of each second from the open (09:30:00):
                   second, then bid_price_1, bid_volume_1 .. bid_price_5, bid_volume_5, then the same for asks
                   (empty where a side has fewer levels); prices in cents
  trades.csv       every execution: time_ns, price, quantity, aggressor (BUY or SELL: the side of
                   the incoming order), passive_agent_type, aggressor_agent_type
  fundamental.csv  the oracle's fundamental value through the day (time_ns, value), the answer key
  meta.json        the seed, the config's settings and counts, and `code`: a hash of this folder's .py files,
                   which decide the day (experiments.abides_days won't mix days written by different code)
  agent.json       with --bot: our template's PnL in the market (cents, its position at the last mid), end
                   position, lots filled and calls (template_agent.py)

Every run adds template_agent.TemplateAgent, idle without --bot, so that a run with the bot and the
run it is compared with share ABIDES's latency draws: the market is the same until our first order.
"""

import argparse
import bisect
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from abides_core import abides
from abides_core.utils import str_to_ns
from abides_markets.configs import rmsc04
from abides_markets.utils import generate_latency_model

from template_agent import TemplateAgent, load_template

LEVELS = 5


def code_hash():
    """This folder's .py files, hashed: the same as experiments.abides_days.code_hash."""
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).resolve().parent.glob("*.py")):
        digest.update(path.name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--end", default="16:00:00", help="the market's close (RMSC04's default is 10:00:00)")
    parser.add_argument("--options", default="{}", help="its build_config arguments, a JSON object (e.g. {\"num_momentum_agents\": 0})")
    parser.add_argument("--bot", help="a template file to trade in the market (template_agent.py)")
    parser.add_argument("--set", default="{}", help="its overrides, a JSON object of dotted paths")
    parser.add_argument("--resting", action="store_true", help="keep the quotes that haven't moved, as where orders rest")
    parser.add_argument("--see-own", action="store_true", help="the bot's book keeps its own live orders in (by default they are taken out)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    started = time.time()
    config = rmsc04.build_config(seed=args.seed, end_time=args.end, stdout_log_level="WARNING", log_orders=False, **json.loads(args.options))
    template = load_template(args.bot, json.loads(args.set)) if args.bot else None
    agent = TemplateAgent(len(config["agents"]), "ABM", template, resting=args.resting, see_own=args.see_own,
                          random_state=np.random.RandomState(seed=args.seed + 10_000))
    config["agents"].append(agent)
    config["agent_latency_model"] = generate_latency_model(len(config["agents"]))
    end_state = abides.run(config, kernel_random_state=np.random.RandomState(seed=args.seed))
    exchange = end_state["agents"][0]
    book = exchange.order_books["ABM"]
    agent_type = {agent.id: type(agent).__name__ for agent in end_state["agents"]}

    date = int(pd.to_datetime(json.loads(args.options).get("date", "20210205")).to_datetime64())  # RMSC04's, or --options'
    open_ns, close_ns = date + str_to_ns("09:30:00"), date + str_to_ns(args.end)

    times = [row["QuoteTime"] for row in book.book_log2]
    with (args.out / "book.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["second"] + [f"{side}_{kind}_{i}" for side in ("bid", "ask") for i in range(1, LEVELS + 1)
                                      for kind in ("price", "volume")])
        for second in range((close_ns - open_ns) // 1_000_000_000):
            i = bisect.bisect_right(times, open_ns + (second + 1) * 1_000_000_000) - 1  # the last event in the second
            row = [second]
            for side in ("bids", "asks"):
                levels = list(book.book_log2[i][side])[:LEVELS] if i >= 0 else []
                for level in range(LEVELS):
                    row += [int(levels[level][0]), int(levels[level][1])] if level < len(levels) else ["", ""]
            writer.writerow(row)

    # An execution's price is the passive order's limit price, from its LIMIT or REPLACE entry.
    price, owner, missing, trades = {}, {}, 0, 0
    with (args.out / "trades.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["time_ns", "price", "quantity", "aggressor", "passive_agent_type", "aggressor_agent_type"])
        for event in book.history:
            kind = event["type"]
            if kind == "LIMIT":
                price[event["order_id"]] = event["price"]
                owner[event["order_id"]] = event["agent_id"]
            elif kind == "REPLACE":
                price[event["new_order_id"]] = event["price"]
                owner[event["new_order_id"]] = owner.get(event["old_order_id"])
            elif kind == "EXEC":
                fill = event["price"] if event["price"] is not None else price.get(event["order_id"])
                if fill is None:
                    missing += 1
                    continue
                # side is the passive order's; the aggressor took the other side
                aggressor = "BUY" if event["side"] == "SELL" else "SELL"
                writer.writerow([int(event["time"]), int(fill), int(event["quantity"]), aggressor,
                                 agent_type.get(event["agent_id"], ""), agent_type.get(event["oppos_agent_id"], "")])
                trades += 1

    oracle = config["custom_properties"]["oracle"]
    with (args.out / "fundamental.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["time_ns", "value"])
        for entry in oracle.f_log.get("ABM", []):
            writer.writerow([entry["FundamentalTime"], entry["FundamentalValue"]])

    meta = {"code": code_hash(), "seed": args.seed, "end": args.end, "options": json.loads(args.options), "open_ns": int(open_ns), "book_events": len(times), "trades": trades,
            "trades_without_price": missing, "seconds": int((close_ns - open_ns) // 1_000_000_000),
            "runtime_s": round(time.time() - started, 1)}
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1))
    if template is not None:
        (args.out / "agent.json").write_text(json.dumps(end_state["agents"][-1].result(), indent=1))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
