# Guidebook tooling: what's installed, the pipelines compared, and what I recommend

## 1. What's on this Mac (macOS 26.4.1, arm64)

| Tool | Status |
|---|---|
| pandoc | **3.12** in Homebrew, with Lua 5.4 filters |
| pdflatex, xelatex, lualatex, latexmk, kpsewhich, tlmgr | **missing**: there is no TeX distribution at all (no `/Library/TeX`, no MacTeX or BasicTeX cask) |
| tex4ebook, make4ht | missing (they come with TeX Live) |
| ebook-convert (Calibre), Quarto, Typst, asciidoctor (and its pdf/epub3 add-ons), epubcheck | missing |
| java | only the system stub: `java -version` says "Unable to locate a Java Runtime", so epubcheck would need a JDK |
| Other Homebrew tools | ffmpeg 9.0.2, librsvg (`rsvg-convert`), poppler (`pdftotext`), llama.cpp 0.7.0 (includes `llama-tts`, but no TTS model was found) |
| Node 20.20.2 (nvm) | present; no MathJax or Speech Rule Engine packages installed globally |
| uv tools | docling, marker-pdf, pymupdf4llm. No Python TTS packages (piper, kokoro, coqui) |
| TTS | macOS `say` with 72 voices: Samantha, Daniel, Karen, Moira and others for English, Zuzana for Czech. No Premium or Enhanced voices are downloaded. No espeak-ng, piper or sox |

**A smoke test I ran here** (files in `/private/tmp/claude-501/-Users-jakubkucera-Documents-qminers-arena/85c5a0de-831c-45d8-96d5-c489d86fe959/scratchpad/gb`):
- Plain pandoc turned Markdown into an EPUB 3 with native MathML. The original TeX was kept inside it as an annotation.
- A 10-line Lua filter produced the plain-text audio edition. It replaced `[$m=\tfrac{a+b}{2}$]{speak="..."}` with its spoken text and dropped `.print`-only blocks.
- Plain pandoc did **not** resolve the cross-reference `@sec-spread`. That needs Quarto or pandoc-crossref.

## 2. The four pipelines compared

**(a) LaTeX source → PDF with latexmk, EPUB with tex4ebook/make4ht (or pandoc reading LaTeX)**
- **PDF:** the best typesetting available.
- **EPUB math:** pictures by default. tex4ebook switches to MathML only with its `mathml` option, and its MathML often needs `--tidy` or config tweaks to validate. Pandoc's LaTeX reader understands only a subset, and custom macros and environments get lost.
- **Figures:** TikZ figures turn into images.
- **Cross-refs and citations:** excellent in the PDF (biblatex). In the EPUB they depend on tex4ht configuration.
- **For an LLM agent:** writing the LaTeX is easy, but getting tex4ht's output right means fiddling with `.cfg` files and the errors are cryptic.
- **Text for speech:** the hardest of the four, because you have to parse the TeX or the HTML that tex4ht produces.

**(b) Pandoc Markdown as the only source**
- **PDF:** goes through a LaTeX template (xelatex or lualatex), so raw LaTeX is allowed wherever it's needed.
- **EPUB math:** native EPUB 3 with MathML (verified above).
- **Figures:** Markdown image syntax.
- **Cross-refs:** need the pandoc-crossref filter.
- **Citations:** built in (`--citeproc`, CSL styles, `.bib` files).
- **For an LLM agent:** very easy; the source is close to plain text and the diffs are small.
- **Text for speech:** the cleanest of the four. A Lua filter works on pandoc's internal document tree, swapping math for its spoken text and dropping or keeping marked blocks, and pandoc can write `-t plain` or custom SSML through a custom Lua writer.

**(c) Quarto book project** (the same pandoc Markdown, plus a project layer)
- **What it adds over (b):** one `_quarto.yml` builds PDF, EPUB and HTML together. Cross-references (`@sec-`, `@fig-`, `@eq-`, `@tbl-`) are built in. It also offers callouts, executable Python code cells that can draw figures, freeze/caching, and TinyTeX management (`quarto install tinytex`).
- **EPUB math:** MathML for EPUB 3 (that is Quarto's default for the format).
- **Known catch:** multi-line display math in book EPUBs has shown up as raw TeX. The workaround is to wrap it in `aligned`, `align` or `equation`.
- **Text for speech:** the same Lua filters as (b), since Quarto runs pandoc. You can add a custom format profile such as `audio` alongside the others.
- **For an LLM agent:** very easy, and the project config is well documented.

**(d) AsciiDoc (Asciidoctor)**
- **Cross-refs and conditionals:** good. Conditional text (`ifdef::audio[]`) is built in.
- **Math:** weaker. `stem` is converted to MathML only for AsciiMath notation. LaTeX math in EPUB or PDF goes through asciidoctor-mathematical, which renders it to SVG or PNG images and is awkward to install.
- **Citations:** need an extension.
- **Toolchain:** Ruby gems, which this Mac doesn't have.
- **Text for speech:** possible, but there's no structured document-tree filter as convenient as pandoc's.

## 3. Making formulas listenable

There are three levels, best first.

1. **Spoken text written by an author, one per formula (recommended for every formula that matters).** In Markdown, put it on the formula as an attribute, `[$...$]{speak="..."}`, and for display math a fenced div `::: {.eq speak="..."}`. If the source were LaTeX, the equivalent is a macro, `\newcommand{\speak}[2]{#1}`, that prints its first argument and hands the second to the audio build.
   - The text explains the formula ("the mid price is the average of the best bid and best ask"); it doesn't read it out symbol by symbol. For a technical guidebook this is far better than any automatic tool.
   - The same text serves as `alttext` or `aria-label` on the EPUB's MathML, which helps screen-reader users.
2. **Conditional content for the audio edition.** Use `.print` and `.audio` divs, or Quarto's `when-format`/`unless-format` and profiles. With them you can drop tables and dense derivations, or replace them with a spoken summary, and replace "see Figure 3" with a one-sentence description of the figure.
3. **Automatic fallback for every formula without a `speak` text.** Speech Rule Engine (`npm i -g speech-rule-engine`, or `npx latex-to-speech`) turns MathML or LaTeX into ClearSpeak text, e.g. `\frac{a}{b}` becomes "a over b".
   - A Lua filter can call it through `pandoc.pipe` and cache the result.
   - MathCAT (Rust, the engine NVDA uses) is an alternative with good ClearSpeak and SimpleSpeak output, but it's more effort to run outside a screen reader.
   - The build should report every formula that still has no `speak` text, so the agent can write the missing ones.

**TTS that handles long text:**
- **Local, available now:** `say -f book.txt -v Samantha -o ch1.aiff`, then ffmpeg to m4b or mp3. It handles whole files, but the quality is basic until you download a Premium voice in System Settings → Accessibility → Spoken Content.
- **Local, better quality (not installed):** Kokoro-82M (through `mlx-audio` or `kokoro-onnx`, very good English on Apple Silicon) or Piper (fast, robotic-ish). The `llama-tts` that's present would need an OuteTTS model and is not worth the effort.
- **Cloud, with SSML** (pauses, `<say-as>`, the right voice for long text): Azure Speech, Amazon Polly (long-form asynchronous jobs), Google TTS. OpenAI and ElevenLabs sound most natural but take only limited SSML.
- **In every case, build per chapter:** one text file per chapter, split into chunks of about 4k characters, joined with ffmpeg into an m4b with chapter marks.

## 4. Recommendation: Quarto book project, Markdown source, Lua filters for the audio edition

**Why:**
- One source that an LLM agent edits easily.
- Built-in cross-refs and citations.
- MathML in the EPUB without image workarounds.
- An HTML version comes free.
- Raw LaTeX remains available for the PDF.
- The audio edition is just another output format with a filter (`speak.lua`, plus `-t plain` or a small SSML writer), not a separate parser.
- Executable code cells fit a book about Python tooling.

If you'd rather not add Quarto, the same design works with plain pandoc plus pandoc-crossref and a Makefile.

**Minimal install (I have not run any of these):**
```sh
brew install quarto                 # bundles its own pandoc; the existing pandoc 3.12 stays
quarto install tinytex              # small TeX Live for the PDF (or: brew install --cask basictex)
# with BasicTeX instead: sudo tlmgr update --self && sudo tlmgr install latexmk collection-fontsrecommended
npm i -g speech-rule-engine         # automatic fallback speech for formulas
# optional:
brew install epubcheck              # pulls in a JDK; validates the EPUB
brew install --cask calibre         # ebook-convert, e.g. for Kindle formats; also lets you look at the EPUB
uv tool install kokoro-onnx         # or mlx-audio: better local TTS than `say`
```
Skip tex4ebook/make4ht and AsciiDoc altogether.

Sources:
- [Quarto ePub options](https://quarto.org/docs/reference/formats/epub.html)
- [Quarto EPUB format source (MathML default)](https://cocalc.com/github/quarto-dev/quarto-cli/blob/main/src/format/epub/format-epub.ts)
- [Multi-line math in Quarto books](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/74549226/multi-line-math-fails-in-quarto)
- [Asciidoctor STEM docs](https://docs.asciidoctor.org/asciidoc/latest/stem)
- [AsciiMath gem](https://docs.asciidoctor.org/asciidoctor/latest/stem/asciimath-gem/)
- [asciidoctor-mathematical](https://awesome.ecosyste.ms/projects/github.com%2Fasciidoctor%2Fasciidoctor-mathematical)
- [latex-to-speech](https://npmjs.com/package/latex-to-speech)
- [SRE CLI](https://app.unpkg.com/speech-rule-engine@5.0.0-alpha.8/files/cjs/common/cli.js)
- [tex4ebook changelog](https://www.github.com/EmmanuelCharpentier/tex4ebook/blob/master/CHANGELOG.md)
- [tex4ht MathML thread](https://tug.org/pipermail/tex4ht/2015q2/001183.html)
- [EPUB MathML fallbacks](https://lists.w3.org/Archives/Public/public-epub3/2019Sep/0012.html)
- [pandoc Lua filters](https://pandoc.org/lua-filters.html)
