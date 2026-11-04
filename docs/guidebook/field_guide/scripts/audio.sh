#!/bin/sh
# The audio edition's text: each chapter in _quarto.yml through audio.lua, one .txt per chapter in _audio/, named so
# that they sort in reading order (the chapter files are numbered; the preface is 00).
# usage (from docs/guidebook/field_guide): scripts/audio.sh   (fails if a formula has no speak sentence)
set -eu
cd "$(dirname "$0")/.."
mkdir -p _audio
for chapter in $(sed -n 's/^    - \(.*\.qmd\)$/\1/p' _quarto.yml); do
  case "$chapter" in index.qmd) out=_audio/00-preface.txt ;; *) out="_audio/${chapter%.qmd}.txt" ;; esac
  pandoc "$chapter" -f markdown -t plain --wrap=none -L scripts/audio.lua | sed -E 's/ +([.,;:])/\1/g' > "$out.new"
  if cmp -s "$out.new" "$out"; then rm "$out.new"; else mv "$out.new" "$out"; fi  # unchanged text keeps its date
  echo "$out: $(wc -w < "$out" | tr -d ' ') words"
done
