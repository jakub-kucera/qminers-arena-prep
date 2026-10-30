"""ORGANISER ONLY: one bot's score per product under the round's TRUTH and under each hidden setting
switched back to the repo engine's default, to show what each unstated rule is worth.

    uv run python <ROUND>/private/check_configs.py BOT.py [public|hidden]
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portal  # noqa: E402
from arena.engine import Mark, QueueModel, TradeMatching  # noqa: E402

VARIANTS = {
    "TRUTH (worse, prob, last, delay 1)": {},
    "matching all (queue prob)": {"trade_matching": TradeMatching.ALL},
    "mark mid": {"mark": Mark.MID},
    "mark touch": {"mark": Mark.TOUCH},
    "delay 0": {"delay": 0},
    "repo defaults for all four (all, back, mid, delay 0)": {"trade_matching": TradeMatching.ALL, "queue": QueueModel.BACK, "mark": Mark.MID, "delay": 0},
}


def one(bot, which, date, change):
    portal.TRUTH = replace(portal.TRUTH, **change)
    result, *_ = portal.run_session(bot, str(portal.DATA[which]), date)
    return {p: result.pnl[p][-1] * portal.UNIT for p in result.products}


def main():
    bot, which = str(Path(sys.argv[1]).resolve()), (sys.argv[2] if len(sys.argv) > 2 else "hidden")
    dates = portal.sessions(portal.DATA[which])
    jobs = [(name, d) for name in VARIANTS for d in dates]
    with ProcessPoolExecutor() as pool:
        out = list(pool.map(one, [bot] * len(jobs), [which] * len(jobs), [d for _, d in jobs], [VARIANTS[n] for n, _ in jobs]))
    print(f"{Path(bot).name} on {which} ({', '.join(dates)}), credits, summed over sessions")
    print(f"{'setting':<55}" + "".join(f"{p:>10}" for p in ("BRAM", "OPHIR", "TALC")) + f"{'total':>10}")
    for k, name in enumerate(VARIANTS):
        rows = out[k * len(dates):(k + 1) * len(dates)]
        per = {p: sum(r[p] for r in rows) for p in rows[0]}
        print(f"{name:<55}" + "".join(f"{per[p]:>10,.1f}" for p in ("BRAM", "OPHIR", "TALC")) + f"{sum(per.values()):>10,.1f}")


if __name__ == "__main__":
    main()
