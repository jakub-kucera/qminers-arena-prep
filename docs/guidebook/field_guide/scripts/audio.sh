#!/bin/sh
# The audio edition's text: each chapter in _quarto.yml's order through audio.lua, one .txt per chapter in _audio/.
# usage (from docs/guidebook/field_guide): scripts/audio.sh   (fails if a formula has no speak sentence)
set -eu
cd "$(dirname "$0")/.."
mkdir -p _audio
rm -f _audio/*.txt
n=0
for chapter in $(sed -n 's/^    - \(.*\.qmd\)$/\1/p' _quarto.yml); do
  n=$((n + 1))
  out=$(printf '_audio/%02d-%s.txt' "$n" "${chapter%.qmd}")
  pandoc "$chapter" -f markdown -t plain --wrap=none -L scripts/audio.lua | sed -E 's/ +([.,;:])/\1/g' > "$out"
  echo "$out: $(wc -w < "$out" | tr -d ' ') words"
done
