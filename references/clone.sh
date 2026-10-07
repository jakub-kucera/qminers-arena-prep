#!/usr/bin/env bash
# Shallow-clones the reference repos described in README.md into this folder.
# The clones are gitignored; only this script and README.md are versioned.
#
# Usage: ./clone.sh            clone any repo that's missing
#        ./clone.sh --update   also pull the ones already cloned
set -euo pipefail

cd "$(dirname "$0")"

# folder                          GitHub repo
REPOS=(
  "prosperity2-linear-utility     ericcccsliu/imc-prosperity-2"
  "prosperity3-alpha-animals      CarterT27/imc-prosperity-3"
  "prosperity3-backtester-jmerle  jmerle/imc-prosperity-3-backtester"
  "prosperity2-backtester-jmerle  jmerle/imc-prosperity-2-backtester"
  "prosperity3-visualizer-jmerle  jmerle/imc-prosperity-3-visualizer"
  "algotrade2026-pitfa19          pitfa19/algotrade2026"
)

case "${1:-}" in
  "") update=false ;;
  --update) update=true ;;
  *) echo "usage: $0 [--update]" >&2; exit 1 ;;
esac

for entry in "${REPOS[@]}"; do
  read -r dir repo <<<"$entry"
  if [[ -d "$dir/.git" ]]; then
    if $update; then
      echo "pull   $dir"
      git -C "$dir" pull --ff-only --quiet
    else
      echo "skip   $dir (already cloned)"
    fi
  else
    echo "clone  $repo -> $dir"
    git clone --depth 1 --quiet "https://github.com/$repo.git" "$dir"
  fi
done
