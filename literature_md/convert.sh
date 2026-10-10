#!/usr/bin/env bash
# Converts the PDFs in ../literature_raw to markdown with Marker (equations -> LaTeX).
# Output goes to <slug>/<slug>.md next to this script (committed).
#
# Setup: uv tool install marker-pdf && brew install llama.cpp   (Marker's equation model needs llama.cpp)
# Usage: ./convert.sh            convert any PDF that has no output yet
#        ./convert.sh --force    redo all
set -euo pipefail

cd "$(dirname "$0")"
RAW=../literature_raw

# slug                          PDF filename prefix in literature_raw
PAPERS=(
  "harris-trading-and-exchanges   Trading and Exchanges"
  "algorithmic-and-hft            Algorithmic_and_High_Frequency_Trading"
  "limit-order-books              limit-order-books"
  "micro-price                    The micro-price"
  "price-impact-of-book-events    The Price Impact of Order Book Events"
  "hft-in-a-limit-order-book      High-frequency trading in a limit order book"
  "dealing-with-inventory-risk    Dealing with the inventory risk"
  "trades-quotes-prices           trades_quotes_prices"
  "kelly-criterion                THE KEILY CRITERION"
  "queue-reactive-model           queue-reactive-model"
  "dynamics-of-order-positions    dynamics-of-order-positions"
  "queue-position-valuation       queue-position-valuation"
  "queue-imbalance-predictor      queue-imbalance-predictor"
  "optimal-market-making          optimal-market-making"
  "probability-of-backtest-overfitting probability-of-backtest-overfitting"
  "deflated-sharpe-ratio          deflated-sharpe-ratio"
  "pseudo-math                    pseudo-math"
)

for entry in "${PAPERS[@]}"; do
  slug=${entry%% *}
  prefix=$(echo "${entry#"$slug"}" | sed 's/^ *//')
  if [[ -f $slug/$slug.md && ${1:-} != --force ]]; then echo "skip $slug"; continue; fi
  pdf=$(ls "$RAW"/"$prefix"*.pdf | head -1)
  echo "== $slug  <-  $pdf"
  tmp=$(mktemp -d)
  marker_single "$pdf" --output_dir "$tmp"
  rm -rf "$slug"; mkdir "$slug"
  mv "$tmp"/*/* "$slug"/
  mv "$slug"/*.md "$slug/$slug.md"
  mv "$slug"/*_meta.json "$slug/meta.json" 2>/dev/null || true
  rm -rf "$tmp"
done
