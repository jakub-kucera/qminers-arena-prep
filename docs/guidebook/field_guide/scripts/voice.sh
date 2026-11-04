#!/bin/sh
# The voice track: each _audio/*.txt read aloud, then one .m4b with a chapter mark per file.
# usage (from docs/guidebook/field_guide, after scripts/audio.sh): scripts/voice.sh [VOICE]
#   Kokoro (open weights, local) where its model is in ~/.cache/kokoro (kokoro_say.py says where it comes from);
#   otherwise macOS `say`. ffmpeg joins the chapters. Outputs: _audio/*.m4a and _audio/The-Field-Guide.m4b.
set -eu
cd "$(dirname "$0")/.."
voice=${1:-bf_emma}
list=_audio/concat.txt
meta=_audio/chapters.txt
: > "$list"
printf ';FFMETADATA1\ntitle=The Field Guide\n' > "$meta"
start=0
for text in _audio/*.txt; do
  case "$text" in */concat.txt|*/chapters.txt) continue ;; esac
  name=${text%.txt}
  if [ -f "$HOME/.cache/kokoro/kokoro-v1.0.onnx" ]; then
    uv run --no-project --quiet --with kokoro-onnx --with soundfile python scripts/kokoro_say.py "$text" "$name.wav" --voice "$voice"
  else
    say -f "$text" -o "$name.aiff" && ffmpeg -v error -y -i "$name.aiff" "$name.wav" && rm "$name.aiff"
  fi
  ffmpeg -v error -y -i "$name.wav" -c:a aac -b:a 64k -ac 1 "$name.m4a" && rm "$name.wav"
  ms=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$name.m4a" | awk '{printf "%d", $1 * 1000}')
  title=$(head -1 "$text" | sed 's/[.]$//')
  printf '[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n' "$start" $((start + ms)) "$title" >> "$meta"
  start=$((start + ms))
  echo "file '$(basename "$name").m4a'" >> "$list"
  echo "$name.m4a: $((ms / 60000)) min $((ms / 1000 % 60)) s ($title)"
done
ffmpeg -v error -y -f concat -safe 0 -i "$list" -i "$meta" -map_metadata 1 -map_chapters 1 -c copy _audio/The-Field-Guide.m4b
rm "$list" "$meta"
echo "_audio/The-Field-Guide.m4b: $((start / 60000)) min"
