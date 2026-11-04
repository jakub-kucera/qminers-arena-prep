"""One chapter's audio text read by Kokoro (open weights, run locally) into a WAV file.

usage (voice.sh runs it; the model lives outside the repo, in ~/.cache/kokoro):
  uv run --no-project --with kokoro-onnx --with soundfile python scripts/kokoro_say.py IN.txt OUT.wav [--voice bf_emma]

Paragraphs are read one at a time with a short pause between them, so a long chapter never meets the model's input
limit and headings get room to breathe.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile
from kokoro_onnx import Kokoro

MODEL = Path.home() / ".cache/kokoro"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--voice", default="bf_emma")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    kokoro = Kokoro(str(MODEL / "kokoro-v1.0.onnx"), str(MODEL / "voices-v1.0.bin"))
    lang = "en-gb" if args.voice.startswith("b") else "en-us"
    pieces, rate = [], 24000
    for paragraph in [p.strip() for p in args.text.read_text().split("\n\n") if p.strip()]:
        samples, rate = kokoro.create(" ".join(paragraph.split()), voice=args.voice, speed=args.speed, lang=lang)
        pieces += [samples, np.zeros(int(rate * 0.45), dtype=samples.dtype)]
    soundfile.write(args.out, np.concatenate(pieces), rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
