#!/bin/sh
# The audio edition's text: each chapter of a book through audio.lua, one .txt per chapter in _out/audio-<book>/,
# named so that they sort in reading order (the chapter files are numbered; the preface is 00, the glossary 99).
# usage (from docs/guidebook/book): scripts/audio.sh [fieldguide|guidebook]
# Fails, leaving the chapter's last good text in place, if a formula has no speak sentence or a chapter comes out empty.
set -eu
cd "$(dirname "$0")/.."
book=${1:-fieldguide}
dir="_out/audio-$book"
chapters=$(sed -n 's/^ *- \([^ ]*\.qmd\)$/\1/p' "_quarto-$book.yml")
[ -n "$chapters" ] || { echo "audio.sh: no chapters in _quarto-$book.yml" >&2; exit 1; }
mkdir -p "$dir"
tmp=$(mktemp)
trap 'rm -f "$tmp" "$tmp.txt"' EXIT
for chapter in $chapters; do
  name=$(basename "$chapter" .qmd)
  case "$name" in index) name=00-preface ;; glossary) name=99-glossary ;; esac
  out="$dir/$name.txt"
  if [ "$chapter" = index.qmd ]; then  # pandoc doesn't expand Quarto's include: read the book's own preface
    { printf '# Preface: how to read this\n\n'; cat "$book/_preface.qmd"; } > "$tmp"
  else
    cp "$chapter" "$tmp"
  fi
  # pandoc on its own, so its exit status (audio.lua's check) isn't lost in a pipeline
  pandoc "$tmp" -f markdown -t plain --wrap=none -L scripts/audio.lua -o "$tmp.txt" || { echo "audio.sh: $chapter failed" >&2; exit 1; }
  [ -s "$tmp.txt" ] || { echo "audio.sh: $chapter came out empty" >&2; exit 1; }
  sed -E 's/ +([.,;:)])/\1/g; s/\( +/(/g; s/\(\)//g; s/(^|[.?!] )the figure/\1The figure/g; s/([Tt])he wiki.s the wiki page/\1he wiki page/g; s/  +/ /g' "$tmp.txt" > "$out.new"
  if cmp -s "$out.new" "$out"; then rm "$out.new"; else mv "$out.new" "$out"; fi  # unchanged text keeps its date
  echo "$out: $(wc -w < "$out" | tr -d ' ') words"
done
