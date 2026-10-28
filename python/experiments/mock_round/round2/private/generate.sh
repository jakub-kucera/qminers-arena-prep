#!/usr/bin/env bash
# Regenerates the raw simulated sessions (Prosperity layout, one folder each) for the rehearsal round.
#   REPO=/path/to/qminers_arena private/generate.sh      (REPO defaults to ~/Documents/qminers_arena)
# Writes only under private/raw/<session>/. The repo is used read-only (its arena.sim).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-$HOME/Documents/qminers_arena}"
TICKS=7200
PRODUCTS=SQUID_INK,KELP_FLOW,RAINFOREST_RESIN,LARGE_TICK
SPECS=(
  # AURIC <- SQUID_INK: a fast random walk, walls 4 apart, some momentum flow
  --spec SQUID_INK.limit=60
  --spec SQUID_INK.fundamental.sd=0.7
  --spec SQUID_INK.maker.half_spread=2
  --spec 'SQUID_INK.maker.size=[15,25]'
  # BRISA <- KELP_FLOW: a slower walk, walls 5 apart, one-sided (buy-heavy) noise flow
  --spec KELP_FLOW.limit=60
  --spec KELP_FLOW.fundamental.sd=0.45
  --spec KELP_FLOW.maker.half_spread=2.5
  # CORONA's premium <- RAINFOREST_RESIN: Ornstein-Uhlenbeck around 10000, walls 12 apart, thin quoting inside
  --spec RAINFOREST_RESIN.limit=30
  --spec RAINFOREST_RESIN.fundamental.reversion=0.004
  --spec RAINFOREST_RESIN.fundamental.sd=1.0
  --spec RAINFOREST_RESIN.maker.half_spread=6
  --spec 'RAINFOREST_RESIN.maker.size=[8,15]'
  --spec RAINFOREST_RESIN.limit_traders.rate=0.25
  --spec 'RAINFOREST_RESIN.limit_traders.offset=[1.5,4.5]'
  --spec 'RAINFOREST_RESIN.limit_traders.size=[1,4]'
  --spec RAINFOREST_RESIN.limit_traders.life=3
  --spec RAINFOREST_RESIN.noise.rate=0.15
  --spec 'RAINFOREST_RESIN.noise.size=[1,4]'
  --spec RAINFOREST_RESIN.value.rate=0.03
  --spec RAINFOREST_RESIN.value.noise=2.0
  --spec RAINFOREST_RESIN.value.threshold=4.0
  # VANTA <- LARGE_TICK: one-tick spread, deep queues; a trend starts part-way through (per session below)
  --spec LARGE_TICK.limit=40
  --spec LARGE_TICK.fundamental.sd=0.06
  --spec LARGE_TICK.momentum.rate=0.05
  --spec 'LARGE_TICK.momentum.size=[5,15]'
  --spec LARGE_TICK.momentum.threshold=0.3
)
# session  seed  trend start (share of session)  trend (raw ticks a step)
SESSIONS=(
  "pub1 61027 0.25 0.010"
  "pub2 61391 0.50 -0.012"
  "pub3 61744 0.05 0.008"
  "hid1 90518 0.35 -0.010"
  "hid2 90873 0.60 0.014"
)
cd "$REPO"
rm -rf "$HERE/raw"
for row in "${SESSIONS[@]}"; do
  read -r name seed at drift <<<"$row"
  uv run python -m arena.sim generate "$HERE/raw/$name" --days 1 --seed "$seed" --ticks "$TICKS" --jobs 1 \
    --products "$PRODUCTS" "${SPECS[@]}" \
    --spec "LARGE_TICK.fundamental.regime_at=$at" --spec "LARGE_TICK.fundamental.regime_drift=$drift"
done
