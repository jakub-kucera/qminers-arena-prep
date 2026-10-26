#!/usr/bin/env bash
# Regenerates the raw simulated days (Prosperity layout) for the mock round.
# Run from anywhere; uses the repo's simulator.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
PRODUCTS=HYDROGEL_PACK,ROBOT_DISHES,KELP_NOISY
SPECS=(
  --spec HYDROGEL_PACK.limit=120
  --spec HYDROGEL_PACK.fundamental.start=10240
  --spec HYDROGEL_PACK.fundamental.reversion=0.003
  --spec HYDROGEL_PACK.fundamental.sd=1.8
  --spec HYDROGEL_PACK.maker.half_spread=7
  --spec 'HYDROGEL_PACK.maker.size=[15,25]'
  --spec HYDROGEL_PACK.noise.rate=0.04
  --spec ROBOT_DISHES.limit=15
  --spec ROBOT_DISHES.fundamental.start=6300
  --spec ROBOT_DISHES.fundamental.jump_size=60
  --spec ROBOT_DISHES.fundamental.jump_rate=0.025
  --spec ROBOT_DISHES.fundamental.jump_reverse=0.84
  --spec ROBOT_DISHES.maker.half_spread=3
  --spec 'ROBOT_DISHES.maker.size=[4,9]'
  --spec 'ROBOT_DISHES.limit_traders.offset=[3.5,4.5]'
  --spec KELP_NOISY.limit=60
  --spec KELP_NOISY.fundamental.start=1480
  --spec KELP_NOISY.fundamental.sd=0.15
  --spec KELP_NOISY.maker.half_spread=2.25
  --spec KELP_NOISY.maker.noise=1.3
  --spec KELP_NOISY.maker.skew=0.025
  --spec KELP_NOISY.noise.rate=0.3
)
cd "$REPO"
rm -rf "$HERE/raw_public" "$HERE/raw_hidden"
uv run python -m arena.sim generate "$HERE/raw_public" --days 3 --seed 48213 --products "$PRODUCTS" "${SPECS[@]}"
uv run python -m arena.sim generate "$HERE/raw_hidden" --days 2 --seed 77305 --products "$PRODUCTS" "${SPECS[@]}"
