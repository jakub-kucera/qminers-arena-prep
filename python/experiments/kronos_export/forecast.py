"""Kronos's zero-shot bar forecasts on Prosperity-layout days, against simple fits on the same bars.

Run by Kronos's own Python (data/kronos/env, made by `uv run python -m experiments.study.kronos_zeroshot
setup`), never imported by the repo's code or tests: it imports torch, numpy, pandas and Kronos's
`model` package (references/kronos, on PYTHONPATH). experiments.study.kronos_zeroshot runs it once per
model and dataset and reads one JSON line per (product, day) from stdout.

Bars of K ticks: OHLC of the touch mid (both sides present, else the last), volume from the trades
file, a minute apart. From each origin (every STRIDE bars past the first L), every forecaster sees the
L bars before it and forecasts the close 1..H bars ahead:
  kronos    KronosPredictor.predict_batch (T 1.0, top_p 0.9, the mean of SAMPLES paths)
  ar1, ar5  an AR(p) on bar returns, least squares on the window
  sma_rev   close[t+h] - close[t] on (5-bar mean - close), least squares on the window, per h
  wall_rev  the same on (wall mid - close): the wall mid, the book's largest level a side, is the
            template's fair, so this is what a bot that reads the book already has
Per forecaster: R2 against forecasting no move, IC, sign hit rate. Also Kronos's mean 5-bar forecast
against the mean realised one, and the tokenizer's round-trip error on the last close (encode and
decode the normalised window, no model), in ticks.
"""
import argparse
import json
import sys
import time

import numpy as np
import pandas as pd
import torch
from model import Kronos, KronosPredictor, KronosTokenizer

# Hugging Face revisions the IDEAS.md numbers were made with (2026-11-02)
REVISIONS = {
    "NeoQuasar/Kronos-mini": "f4e68697d9d5aed55cef5c96aabc3376bcad9f81",
    "NeoQuasar/Kronos-small": "901c26c1332695a2a8f243eb2f37243a37bea320",
    "NeoQuasar/Kronos-base": "2b554741eca47781b64468546e77fef3e85130e6",
    "NeoQuasar/Kronos-Tokenizer-2k": "26966d0035065a0cae0ebad7af8ece35bc1fb51c",
    "NeoQuasar/Kronos-Tokenizer-base": "0e0117387f39004a9016484a186a908917e22426",
}
COLS = ["open", "high", "low", "close", "volume", "amount"]


def load(model: str):
    tok_name = "NeoQuasar/Kronos-Tokenizer-2k" if model == "mini" else "NeoQuasar/Kronos-Tokenizer-base"
    tok = KronosTokenizer.from_pretrained(tok_name, revision=REVISIONS[tok_name]).eval()
    name = f"NeoQuasar/Kronos-{model}"
    mdl = Kronos.from_pretrained(name, revision=REVISIONS[name]).eval()
    return tok, KronosPredictor(mdl, tok, max_context=2048 if model == "mini" else 512)


def bars_of(csv_dir: str, rnd: int, day: int, product: str, k: int):
    p = pd.read_csv(f"{csv_dir}/prices_round_{rnd}_day_{day}.csv", sep=";")
    p = p[p["product"] == product].sort_values("timestamp")
    both = p["bid_price_1"].notna() & p["ask_price_1"].notna()
    mid = ((p["bid_price_1"] + p["ask_price_1"]) / 2).where(both).ffill().bfill().to_numpy()

    def wall(side):
        px = p[[f"{side}_price_{i}" for i in (1, 2, 3)]].to_numpy()
        vol = p[[f"{side}_volume_{i}" for i in (1, 2, 3)]].abs().fillna(-1).to_numpy()
        best = np.take_along_axis(px, vol.argmax(axis=1)[:, None], axis=1)[:, 0]
        return np.where(vol.max(axis=1) > 0, best, np.nan)

    wmid = pd.Series((wall("bid") + wall("ask")) / 2).ffill().bfill().to_numpy()
    ts = p["timestamp"].to_numpy()
    try:
        t = pd.read_csv(f"{csv_dir}/trades_round_{rnd}_day_{day}.csv", sep=";")
        vol = t[t["symbol"] == product].groupby("timestamp")["quantity"].sum()
        tick_vol = pd.Series(ts).map(vol).fillna(0).to_numpy()
    except FileNotFoundError:
        tick_vol = np.zeros(len(ts))
    n = len(mid) // k
    m = mid[: n * k].reshape(n, k)
    bars = pd.DataFrame({"open": m[:, 0], "high": m.max(axis=1), "low": m.min(axis=1), "close": m[:, -1],
                         "volume": tick_vol[: n * k].reshape(n, k).sum(axis=1)})
    bars["amount"] = bars["volume"] * bars["close"]
    stamps = pd.Series(pd.date_range("2025-01-06 00:00", periods=n, freq="1min"))
    return bars, stamps, wmid[: n * k].reshape(n, k)[:, -1]


def ar_forecast(close, p, horizon):
    r = np.diff(close)
    x = np.column_stack([np.ones(len(r) - p)] + [r[p - 1 - j: len(r) - 1 - j] for j in range(p)])
    beta, *_ = np.linalg.lstsq(x, r[p:], rcond=None)
    hist, out, cum = list(r[-p:][::-1]), [], 0.0
    for _ in range(horizon):
        nxt = beta[0] + float(np.dot(beta[1:], hist[:p]))
        cum += nxt
        out.append(cum)
        hist.insert(0, nxt)
    return out


def rev_forecast(close, signal, horizon):
    out = []
    for h in range(1, horizon + 1):
        x = np.column_stack([np.ones(len(close) - h), signal[:-h]])
        beta, *_ = np.linalg.lstsq(x, close[h:] - close[:-h], rcond=None)
        out.append(beta[0] + beta[1] * signal[-1])
    return out


def scores(pred, real):
    pred, real = np.asarray(pred), np.asarray(real)
    nz = real != 0
    return {"r2": float(1 - np.sum((real - pred) ** 2) / np.sum(real ** 2)),
            "ic": float(np.corrcoef(pred, real)[0, 1]) if pred.std() > 0 else float("nan"),
            "hit": float(np.mean(np.sign(pred[nz]) == np.sign(real[nz])))}


def run(tok, pred, a, rnd, day, product):
    torch.manual_seed(0)
    bars, stamps, wall_end = bars_of(a.csv_dir, rnd, day, product, a.k)
    close = bars["close"].to_numpy()
    x_sma = pd.Series(close).rolling(5, min_periods=1).mean().to_numpy() - close
    x_wall = wall_end - close
    origins = list(range(a.L, len(bars) - a.H, a.stride))
    res = {name: [] for name in ("kronos", "ar1", "ar5", "sma_rev", "wall_rev")}
    real, recon = [], []
    t0 = time.time()
    for c in range(0, len(origins), a.chunk):
        block = origins[c: c + a.chunk]
        dfs = [bars.iloc[s - a.L: s].reset_index(drop=True) for s in block]
        outs = pred.predict_batch(dfs, [stamps.iloc[s - a.L: s].reset_index(drop=True) for s in block],
                                  [stamps.iloc[s: s + a.H].reset_index(drop=True) for s in block],
                                  pred_len=a.H, T=1.0, top_p=0.9, sample_count=a.samples, verbose=False)
        x = np.stack([df[COLS].to_numpy(np.float32) for df in dfs])
        mu, sd = x.mean(axis=1, keepdims=True), x.std(axis=1, keepdims=True)
        with torch.no_grad():
            z = torch.from_numpy(np.clip((x - mu) / (sd + 1e-5), -5, 5)).to(pred.device)
            back = tok.decode(tok.encode(z, half=True), half=True).cpu().numpy()
        recon += list(back[:, -1, 3] * (sd[:, 0, 3] + 1e-5) + mu[:, 0, 3] - x[:, -1, 3])
        for s, o in zip(block, outs):
            last, window = close[s - 1], slice(s - a.L, s)
            res["kronos"].append(o["close"].to_numpy() - last)
            res["ar1"].append(ar_forecast(close[window], 1, a.H))
            res["ar5"].append(ar_forecast(close[window], 5, a.H))
            res["sma_rev"].append(rev_forecast(close[window], x_sma[window], a.H))
            res["wall_rev"].append(rev_forecast(close[window], x_wall[window], a.H))
            real.append(close[s: s + a.H] - last)
    real = np.array(real)
    out = {"model": a.model, "round": rnd, "day": day, "product": product, "windows": len(origins),
           "secs": round(time.time() - t0, 1), "lag1": float(pd.Series(np.diff(close)).autocorr(1)),
           "kronos_mean_h": float(np.mean(np.array(res["kronos"])[:, -1])), "real_mean_h": float(real[:, -1].mean()),
           "recon_mae": float(np.mean(np.abs(recon)))}
    for h in (1, a.H):
        for name, v in res.items():
            out[f"h{h}_{name}"] = scores(np.array(v)[:, h - 1], real[:, h - 1])
    return out


def main():
    if sys.argv[1:] == ["--download"]:  # setup: every pinned model into HF_HOME
        from huggingface_hub import snapshot_download
        for name, revision in REVISIONS.items():
            snapshot_download(name, revision=revision)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["mini", "small", "base"])
    ap.add_argument("--csv-dir", required=True, help="a round folder of Prosperity-layout CSVs")
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--days", type=int, nargs="+", required=True)
    ap.add_argument("--products", nargs="+", required=True)
    ap.add_argument("--k", type=int, default=10, help="ticks a bar")
    ap.add_argument("--L", type=int, default=256, help="bars of context")
    ap.add_argument("--H", type=int, default=5, help="bars ahead")
    ap.add_argument("--stride", type=int, default=4, help="bars between origins")
    ap.add_argument("--samples", type=int, default=10, help="Kronos's sampled paths, averaged")
    ap.add_argument("--chunk", type=int, default=32, help="origins a batch")
    a = ap.parse_args()
    tok, pred = load(a.model)
    for day in a.days:
        for product in a.products:
            print(json.dumps(run(tok, pred, a, a.round, day, product)), flush=True)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
