# The guidebooks

Two books on the trading behind this repository, written in the week before the event from its experiments and its
literature wiki. They teach market making on the market we prepared for, IMC Prosperity's. The Arena turned out to
be a different market (the hackathon repository's postmortem says how), but the questions they work through still
apply.

| Book | Pages | What it is |
|---|---:|---|
| [The Field Guide](The-Field-Guide.pdf) | 42 | The short one, to read before the day: ten questions, from "What happens in a round?" to "What do I do on the day?", with a glossary |
| [The Guidebook](The-Guidebook.pdf) | 129 | The full one: sixteen chapters, adding position costs, price behaviour, other products, the other traders, risk sizing and every parameter of the bot, plus appendices (glossary, datasets, commands, a reading route through the literature, the Arena round by round) |

The PDFs are built from the sources in [`book/`](book/) as committed. The plans and the research behind the books are
[`PROPOSAL.md`](PROPOSAL.md), [`FIELD_GUIDE_PLAN.md`](FIELD_GUIDE_PLAN.md), [`GUIDEBOOK_PLAN.md`](GUIDEBOOK_PLAN.md)
and [`research/`](research/); [`book/WRITING.md`](book/WRITING.md) holds the rules the text follows.

## Building the PDF, EPUB and HTML

Both books are one [Quarto](https://quarto.org/) project, chosen by profile. You need Quarto (1.8; on macOS its
tarball works without an admin password), with TinyTeX for the PDF:

```sh
quarto install tinytex                           # once: the LaTeX the PDF needs

cd docs/guidebook/book
quarto render                                    # the field guide: HTML, PDF and EPUB into _out/fieldguide/
quarto render --profile guidebook                # the guidebook: the same into _out/guidebook/
quarto render --profile guidebook --to epub      # one format only: pdf, epub or html
```

The figures and their data are committed, so a render needs nothing else. To rebuild them from the repository's data
(the data step needs the reference clones, `references/clone.sh`, and takes about 10 minutes):

```sh
uv run python docs/guidebook/book/scripts/make_data.py                        # book/data/*.csv
uv run --group analysis python docs/guidebook/book/scripts/make_figures.py    # book/figures/*.png
```

## Building the audiobook

The audio edition is the book's text rewritten for listening (each formula read as a sentence, tables and code blocks
replaced by a spoken note, code names and paths read as words), then read aloud and joined into one `.m4b` with a
chapter mark per chapter. It needs pandoc and ffmpeg. For the voice it uses
[Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (open weights, run locally) when its model files,
`kokoro-v1.0.onnx` and `voices-v1.0.bin` from the project's releases, are in `~/.cache/kokoro`, and macOS `say`
otherwise.

```sh
cd docs/guidebook/book
scripts/audio.sh fieldguide      # the audio text, one .txt per chapter, into _out/audio-fieldguide/
scripts/voice.sh fieldguide      # one .m4a per chapter and The-Field-Guide.m4b (default voice bf_emma)
scripts/audio.sh guidebook && scripts/voice.sh guidebook bf_emma    # the guidebook, into _out/audio-guidebook/
```

The field guide runs to about 1 hour 15 minutes of audio and the guidebook to about 4 hours 15 minutes. Kokoro reads
at about four times real time on an Apple M4 Max, so the guidebook takes about an hour to voice. A chapter whose audio
is newer than its text is skipped on the next run; delete the `.m4a` files to re-voice after changing the voice.