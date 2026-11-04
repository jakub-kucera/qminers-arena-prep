#!/bin/sh
# The audio edition's text: each chapter in _quarto.yml through audio.lua, one .txt per chapter in _audio/, named so
# that they sort in reading order (the chapter files are numbered; the preface is 00).
# usage (from docs/guidebook/field_guide): scripts/audio.sh [fieldguide|guidebook]   (fails if a formula has no speak
# sentence). The guidebook's text goes to _audio-guidebook/.
set -eu
cd "$(dirname "$0")/.."
profile=${1:-fieldguide}
dir=_audio; [ "$profile" = fieldguide ] || dir="_audio-$profile"
mkdir -p "$dir"
for chapter in $(sed -n 's/^ *- \([^ ]*\.qmd\)$/\1/p' "_quarto-$profile.yml"); do
  case "$chapter" in index.qmd) out="$dir/00-preface.txt" ;; glossary.qmd) out="$dir/11-glossary.txt" ;; *) out="$dir/${chapter%.qmd}.txt" ;; esac
  source=$chapter; [ "$chapter" = index.qmd ] && source="_preface-$profile.qmd"  # pandoc doesn't expand Quarto's include
  { [ "$chapter" = index.qmd ] && printf '# Preface: how to read this\n\n'; cat "$source"; } | pandoc -f markdown -t plain --wrap=none -L scripts/audio.lua | sed -E 's/ +([.,;:])/\1/g; s/(^|[.?!] )the figure/\1The figure/g; s/  +/ /g' > "$out.new"
  if cmp -s "$out.new" "$out"; then rm "$out.new"; else mv "$out.new" "$out"; fi  # unchanged text keeps its date
  echo "$out: $(wc -w < "$out" | tr -d ' ') words"
done
