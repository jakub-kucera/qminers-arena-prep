#!/usr/bin/env bash
# Regenerates the raw simulated sessions (Prosperity layout, one folder each) for the Kestrel round.
#   REPO=/path/to/qminers_arena private/generate.sh      (REPO defaults to ~/Documents/qminers_arena)
# Writes only under private/raw/<session>/. The repo is used read-only (its arena.sim).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-$HOME/Documents/qminers_arena}"
TICKS=6000
PRODUCTS=HYDROGEL_PACK,KELP,LARGE_TICK
SPECS=(
  # TALC <- HYDROGEL_PACK: Ornstein-Uhlenbeck around its level (half-life ~230 steps), walls 14 apart
  --spec HYDROGEL_PACK.limit=40
  --spec HYDROGEL_PACK.fundamental.reversion=0.003
  --spec HYDROGEL_PACK.fundamental.sd=1.6
  --spec HYDROGEL_PACK.maker.half_spread=7
  --spec 'HYDROGEL_PACK.maker.size=[15,25]'
  --spec HYDROGEL_PACK.limit_traders.rate=0.15
  --spec HYDROGEL_PACK.noise.rate=0.06
  # OPHIR <- KELP: a random walk (sd 1.0 a step), walls 4 apart that re-quote AFTER the snapshot
  # (maker.first=False, so the shown walls are a step old), and informed value takers (rate 0.25,
  # view noise 0.1, take when the touch is 0.3 off): their prints lead the mid (R(1) about +0.5 tick)
  --spec KELP.limit=60
  --spec KELP.fundamental.sd=1.0
  --spec KELP.maker.half_spread=2
  --spec KELP.maker.first=False
  --spec KELP.value.rate=0.25
  --spec KELP.value.noise=0.1
  --spec KELP.value.threshold=0.3
  --spec 'KELP.value.size=[3,8]'
  --spec KELP.noise.rate=0.2
  # BRAM <- LARGE_TICK: a one-tick spread, deep queues, a value that barely moves
  --spec LARGE_TICK.limit=80
  --spec LARGE_TICK.fundamental.sd=0.06
)
# session  seed
SESSIONS=(
  "pub1 73112"
  "pub2 73458"
  "pub3 73790"
  "hid1 95204"
  "hid2 95561"
)
cd "$REPO"
rm -rf "$HERE/raw"
for row in "${SESSIONS[@]}"; do
  read -r name seed <<<"$row"
  uv run python -m arena.sim generate "$HERE/raw/$name" --days 1 --seed "$seed" --ticks "$TICKS" --jobs 1 \
    --products "$PRODUCTS" "${SPECS[@]}" &
done
wait
