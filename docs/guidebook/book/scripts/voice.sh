#!/bin/sh
# The voice track: each chapter's audio text read aloud, then one .m4b with a chapter mark per file.
# usage (from docs/guidebook/book, after scripts/audio.sh BOOK): scripts/voice.sh [fieldguide|guidebook] [VOICE]
#   Kokoro (open weights, local) where its model is in ~/.cache/kokoro (kokoro_say.py says where it comes from);
#   otherwise macOS `say`. ffmpeg joins the chapters. Outputs: _out/audio-BOOK/*.m4a and one .m4b.
#   A chapter whose .m4a is newer than its text is not voiced again (delete the .m4a files after changing VOICE).
#   Kokoro on the CPU ran at 4.1 times real time on an M4 Max; Core ML (4.0) and MLX (2.5) were no faster.
set -eu
cd "$(dirname "$0")/.."
book=${1:-fieldguide}
voice=${2:-bf_emma}
dir="_out/audio-$book"
case "$book" in fieldguide) title="The Field Guide" ;; *) title="The Guidebook" ;; esac
list=$(mktemp)
meta=$(mktemp)
trap 'rm -f "$list" "$meta"' EXIT
printf ';FFMETADATA1\ntitle=%s\n' "$title" > "$meta"
start=0
for text in "$dir"/*.txt; do
  name=${text%.txt}
  if [ "$name.m4a" -nt "$text" ]; then  # voiced since its text last changed
    :
  elif [ -f "$HOME/.cache/kokoro/kokoro-v1.0.onnx" ]; then
    uv run --no-project --quiet --with kokoro-onnx --with soundfile python scripts/kokoro_say.py "$text" "$name.wav" --voice "$voice"
  else
    say -f "$text" -o "$name.aiff" && ffmpeg -v error -y -i "$name.aiff" "$name.wav" && rm "$name.aiff"
  fi
  [ "$name.m4a" -nt "$text" ] || { ffmpeg -v error -y -i "$name.wav" -c:a aac -b:a 64k -ac 1 "$name.m4a" && rm "$name.wav"; }
  ms=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$name.m4a" | awk '{printf "%d", $1 * 1000}')
  chapter=$(head -1 "$text" | sed 's/[.]$//')
  printf '[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n' "$start" $((start + ms)) "$chapter" >> "$meta"
  start=$((start + ms))
  echo "file '$PWD/$name.m4a'" >> "$list"
  echo "$name.m4a: $((ms / 60000)) min $((ms / 1000 % 60)) s ($chapter)"
done
out="$dir/$(echo "$title" | tr ' ' '-').m4b"
ffmpeg -v error -y -f concat -safe 0 -i "$list" -i "$meta" -map_metadata 1 -map_chapters 1 -c copy "$out"
echo "$out: $((start / 60000)) min"
