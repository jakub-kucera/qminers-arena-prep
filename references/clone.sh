#!/usr/bin/env bash
# Shallow-clones the reference repos described in README.md into this folder, each at a pinned
# commit. The wiki's path:line citations, the Prosperity data, the parity test and the results in
# IDEAS.md were all made on these commits, so every machine has to be on the same ones.
# The clones are gitignored; only this script and README.md are versioned.
#
# Usage: ./clone.sh            clone any missing repo, and put every clone on its pinned commit
#        ./clone.sh --check    only report clones that aren't on their pin (exit 1 if any)
#        ./clone.sh --update   move every repo to its newest commit and rewrite the pins here.
#                              Then run `python3 references/wiki/lint.py` and `uv run pytest`,
#                              read what changed, and commit this file.
set -euo pipefail

cd "$(dirname "$0")"

# folder                          GitHub repo                                       pinned commit
REPOS=(
  "prosperity2-linear-utility       ericcccsliu/imc-prosperity-2                     348d3b0097ed4fae5265990be08ad9d41ce02f48"
  "prosperity3-alpha-animals        CarterT27/imc-prosperity-3                       17bc67fe8c7274a0e7259715f3c050abb77eea97"
  "prosperity3-backtester-jmerle    jmerle/imc-prosperity-3-backtester               26f52ee4cdc80eb980d058e737a7da6889718562"
  "prosperity2-backtester-jmerle    jmerle/imc-prosperity-2-backtester               29e67179442a9890bbfa0dea8d95b7000c8627b4"
  "prosperity3-visualizer-jmerle    jmerle/imc-prosperity-3-visualizer               fac4b72c77f06ba4c7f6d7beffff105966c0cdf0"
  "algotrade2026-pitfa19            pitfa19/algotrade2026                            fcc4a032e87023c018415c60a0b34857fb53daa2"
  "algotrade2026-negative-eevee     alexbolfa/algotrade-negative-eevee               3b6f070fbcadf82d42eb23d7b0d2f81aefa7a58f"
  "prosperity3-frankfurt-hedgehogs  TimoDiehm/imc-prosperity-3                       6bbc3abfb1f81cb1c8710fdb0b291079ce943202"
  "prosperity4-baguette-fromage     Durpie-Git/imc-prosperity-4                      9d8079e06c8e3553d37fade4d55f75b4035f36ae"
  "prosperity4-du-trading           FoxHenderson/imc-prosperity-4                    e7830f998de501819afbbafe7f9aba38f1e4e646"
  "prosperity4-dtu-quant-lab        DataAthleteChamp/dtu-quant-lab-imc-prosperity-4  b9649b8ae6a052cfe1ec523aa69f90f5e4c32579"
  "prosperity4-ryan-challman        nathanw3456/Prosperity_4_Writeup                 75aa1652b51a2944cd7992cddfbae54ccc071e2a"
  "prosperity4-alpha-search         fabianbaiertum/IMC-Prosperity-4                  b644d1c28512677875e2bc199af2e645043b832b"
  "prosperity4-backtester           nabayansaha/imc-prosperity-4-backtester          0094c681f8cd019889761e6431a1a47ea151aaa8"
  "uchicago-trading-2026            konnorlo/UChicago-Trading-Competition-2026       a79306ae0df7229db0b7d62b2c2085e6add0dbae"
  "uchicago-2025-case2-humzah       HumzahM/UTC2025-Case2-Writeup                    1c0f7a90b5ad6956c797287b53b8a6cabfb33cfe"
  "qminers-hackathon-2025           vitktor/Qminers-Hackathon-2025                   8a42f1ed0a9f9b14a5113f79c6277f3390891415"
  "hftbacktest                      nkaz001/hftbacktest                              5f3ec40b2afb764e0fea112f941ed85523ef4e88"
)

case "${1:-}" in
  "") mode=pin ;;
  --check) mode=check ;;
  --update) mode=update ;;
  *) echo "usage: $0 [--check | --update]" >&2; exit 1 ;;
esac

# Fetches one commit (or the remote's default branch, for HEAD) without history, and checks it out.
checkout() {
  git -C "$1" fetch --quiet --depth 1 origin "$2"
  git -C "$1" checkout --quiet --detach FETCH_HEAD
}

off_pin=0
for entry in "${REPOS[@]}"; do
  read -r dir repo pin <<<"$entry"
  if [[ ! -d "$dir/.git" ]]; then
    if [[ $mode == check ]]; then
      echo "missing $dir"; off_pin=1; continue
    fi
    echo "clone   $repo -> $dir at ${pin:0:12}"
    git init --quiet "$dir"
    git -C "$dir" remote add origin "https://github.com/$repo.git"
    checkout "$dir" "$pin"
  fi
  head=$(git -C "$dir" rev-parse HEAD)
  case $mode in
    check)
      if [[ $head != "$pin" ]]; then echo "off pin $dir: at ${head:0:12}, pinned ${pin:0:12}"; off_pin=1; fi ;;
    pin)
      if [[ $head != "$pin" ]]; then
        echo "pin     $dir: ${head:0:12} -> ${pin:0:12}"
        checkout "$dir" "$pin"
      fi ;;
    update)
      checkout "$dir" HEAD
      new=$(git -C "$dir" rev-parse HEAD)
      if [[ $new != "$pin" ]]; then
        echo "moved   $dir: ${pin:0:12} -> ${new:0:12}"
        sed -i.bak "s/$pin/$new/" clone.sh && rm clone.sh.bak
      fi ;;
  esac
done

if [[ $mode == check && $off_pin == 1 ]]; then
  echo "run references/clone.sh to put every clone on its pin" >&2
  exit 1
fi
if [[ $mode == update ]]; then
  echo "pins rewritten in references/clone.sh: run the wiki lint and the tests, then commit it"
fi
