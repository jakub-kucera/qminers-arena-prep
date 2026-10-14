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
  "order-book-signals             Enhancing_Trading_Strategies_CARTEA"
  "how-to-almost-win              How to (almost) win in Competitive"
  "rigtorp-queue-position         rigtorp-queue-position"
  "databento-queue-position       databento-queue-position"
  "quant-se-order-position        quant-se-order-position"
  "mean-reverting-reference-price mean-reverting-reference-price"
  "limit-and-market-orders        limit-and-market-orders"
  "online-learning-market-making  online-learning-market-making"
  "competing-dealers              competing-dealers"
  "pro-rata-microstructure        pro-rata-microstructure"
  "market-makers-dilemma          market-makers-dilemma"
  "negative-drift-of-a-fill       negative-drift-of-a-fill"
  "stochastic-liquidity-demand    stochastic-liquidity-demand"
  "algorithmic-cooperation-mm     algorithmic-cooperation-mm"
  "marl-competition-no-collusion  Multi-Agent Reinforcement Learning for Market Making"
  "etf-trade-flow-decomposition   Data-driven trade flow decomposition"
  "cross-asset-order-flow         From Constituents to Index"
  "market-making-perceived-collusion  Interactions of Market Making Algorithms"
  "order-stacking-mm                  Market Making under Order Stacking"
  "decomposed-ofi                     Order Flow Decomposition for Price Impact"
  "scaled-beta-policies               Market Making with Scaled Beta"
  "mm-adverse-selection-rl            High Frequency Automated Market Making"
  "classify-trading-agents            Learning to Classify and Imitate"
  "collective-liquidity-taking        Detecting Collective Liquidity"
  "etf-arbitrage-abm                  Stability Effects of Arbitrage in Exchange Traded Funds- An Agent-Based Model_v2"
  "detecting-spoofing-strategies      detecting-spoofing-strategies"
  "spoofing-learning-algorithms       spoofing-learning-algorithms"
  "optimal-spoofing                   optimal-spoofing"
  "manipulation-statistical-physics   manipulation-statistical-physics"
  "learning-not-to-spoof              learning-not-to-spoof"
  "adversarial-attacks-hft            adversarial-attacks-hft"
  "manipulation-detection-evasion     manipulation-detection-evasion"
  "llm-agents-market-simulation       llm-agents-market-simulation"
  "pymarketsim                        pymarketsim"
  "benchmark-manipulation             benchmark-manipulation"
  "market-making-latency              market-making-latency"
  "dtw-lead-lag                       dtw-lead-lag"
  "guessing-games                     guessing-games"
  "accidental-pump-and-dump           accidental-pump-and-dump"
  "spoofing-traders-empirical         spoofing-traders-empirical"
  "hawkes-structured-mm               hawkes-structured-mm"
  "lob-irreversibility                lob-irreversibility"
  "abides-simulator               abides-simulator"
  "lob-simulation-realism         lob-simulation-realism"
  "spoofing-abm                   spoofing-abm"
  "learning-market-maker          learning-market-maker"
  "online-changepoint-detection   online-changepoint-detection"
  "trading-under-manipulation     Learning-based trading strategies in the face of market manipulation"
  "spoofability-and-liquidity     spoofability-and-liquidity"
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
