#!/usr/bin/env bash
# The Varde Exchange (rehearsal 4, 2026-11-03): raw simulated sessions in the Prosperity layout, one folder each.
#   REPO=/path/to/qminers_arena private/generate.sh   (REPO defaults to ~/Documents/qminers_arena; used read-only)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO:-$HOME/Documents/qminers_arena}"
TICKS=5000
PRODUCTS=KELP_FLOW,HYDROGEL_PACK,SQUID_INK
SPECS=(
  # LUMEN <- KELP_FLOW: a slow random walk whose takers buy more often than they sell (35%), sizes 2-6 against 1-5
  --spec KELP_FLOW.limit=40
  --spec KELP_FLOW.fundamental.sd=0.15
  --spec KELP_FLOW.maker.half_spread=2
  # QUILL <- HYDROGEL_PACK: back to a level (half-life ~350 steps) the hidden sessions share, walls 12 apart
  --spec HYDROGEL_PACK.limit=60
  --spec HYDROGEL_PACK.fundamental.reversion=0.002
  --spec HYDROGEL_PACK.fundamental.sd=1.4
  --spec HYDROGEL_PACK.maker.half_spread=6
  --spec HYDROGEL_PACK.noise.rate=0.08
  # SORREL <- SQUID_INK: a fast walk with momentum takers
  --spec SQUID_INK.limit=30
  --spec SQUID_INK.fundamental.sd=0.9
  --spec SQUID_INK.momentum.rate=0.05
)
SESSIONS=("s1 41117" "s2 41229" "s3 41383" "s4 58801" "s5 58933")
cd "$REPO"
rm -rf "$HERE/raw"
for row in "${SESSIONS[@]}"; do
  read -r name seed <<<"$row"
  uv run python -m arena.sim generate "$HERE/raw/$name" --days 1 --seed "$seed" --ticks "$TICKS" --jobs 1 \
    --products "$PRODUCTS" "${SPECS[@]}" &
done
wait
