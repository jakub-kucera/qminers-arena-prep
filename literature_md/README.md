# literature_md

Market-microstructure literature converted from `../literature_raw/*.pdf` to markdown with
[Marker](https://github.com/datalab-to/marker), so it can be searched and read by Claude. The
converted output is committed; the source PDFs in `literature_raw/` are gitignored. Regenerate with
`./convert.sh` (setup is in the script header).

**Start from the wiki, not from here.** `../references/wiki/index.md` (section "Literature") lists the documents
that have a source page: their results with the PDF page, which formulas were checked against the PDF, and what
they mean for our code. This folder is the raw text those pages cite.

Each document lives in `<slug>/<slug>.md`, with extracted figures as `_page_N_*.jpeg` next to it and
Marker's `meta.json` (table of contents with page numbers).

| Folder | Source | Useful for |
|---|---|---|
| `micro-price/` | Stoikov, *The micro-price* (9 pp.) | Fair price from top-of-book imbalance and spread; better than mid or weighted mid |
| `hft-in-a-limit-order-book/` | Avellaneda & Stoikov, *High-frequency trading in a limit order book* (13 pp.) | Reservation price and optimal bid/ask quotes under inventory risk |
| `dealing-with-inventory-risk/` | Guéant, Lehalle & Fernandez-Tapia, *Dealing with the inventory risk* (36 pp.) | Market making with a hard inventory bound (HJB / ODE solution) |
| `price-impact-of-book-events/` | Cont, Kukanov & Stoikov, *The price impact of order book events* (26 pp.) | Order-flow imbalance as a linear driver of short-term price changes |
| `limit-order-books/` | Gould et al., *Limit order books*, Quant. Finance 2013 (34 pp.) | Survey: LOB mechanics, empirical facts, models |
| `trades-quotes-prices/` | Bouchaud et al., *Trades, Quotes and Prices* (47 pp. excerpt) | Empirical order-flow and price-impact facts |
| `kelly-criterion/` | Thorp, *The Kelly criterion in blackjack, sports betting, and the stock market* (1997, 40 pp.) | Position sizing: bet fraction from edge and variance, fractional Kelly, growth rate vs. risk |
| `algorithmic-and-hft/` | Cartea, Jaimungal & Penalva, *Algorithmic and High-Frequency Trading* (360 pp.) | Optimal execution, market making, stochastic-control derivations |
| `harris-trading-and-exchanges/` | Harris, *Trading and Exchanges* (656 pp., 2003 draft) | Market structure, order types, who trades and why |
| `queue-position-valuation/` | Moallemi & Yuan, *A Model for Queue Position Valuation in a Limit Order Book* (33 pp.) | What a place in the FIFO queue is worth: a static part (spread earned against adverse selection, which grows with queue position) and an option-like part (value of keeping the position). Backs the queue model in `--resting` |
| `queue-reactive-model/` | Huang, Lehalle & Rosenbaum, *Simulating and analyzing order book data: The queue-reactive model* (29 pp.) | The book as a Markov queue system whose arrival and cancel rates depend on its state; fitting the rates from data and simulating a book. DTU Quant Lab shipped it for queue-aware quoting |
| `dynamics-of-order-positions/` | Guo, Ruan & Zhu, *Dynamics of Order Positions and Related Queues in a Limit Order Book* (42 pp.) | Fluid and diffusion limits for an order's queue position, with closed forms for fill-related quantities. Heavy maths; a reference |
| `queue-imbalance-predictor/` | Gould & Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book* (30 pp.) | Logistic regression of the next mid-price move on bid/ask queue imbalance, on 10 Nasdaq stocks. A simple signal to test on the Prosperity data |
| `optimal-market-making/` | Guéant, *Optimal market making* (43 pp.) | Market making over many assets with inventory limits and skewed quotes. The closest paper to a many-product Arena. hftbacktest's `Making Multiple Markets.ipynb` implements it |
| `probability-of-backtest-overfitting/` | Bailey, Borwein, López de Prado & Zhu, *The Probability of Backtest Overfitting* (34 pp.) | Why the best of many backtests is usually luck, and CSCV, a way to estimate the probability that it is. For `arena.grid` and a capped number of portal submissions |
| `deflated-sharpe-ratio/` | Bailey & López de Prado, *The Deflated Sharpe Ratio* (22 pp.) | A Sharpe ratio corrected for how many strategies were tried, for non-normal returns and for short samples |
| `order-book-signals/` | Cartea, Donnelly & Jaimungal, *Enhancing trading strategies with order book signals*, Applied Mathematical Finance 2018 (accepted manuscript, 42 pp.; free copy from King's College London's repository) | Best-level volume imbalance `ρ` as a predictor of the next market order and its use in a limit-order market-making control problem; why quoting only at the touch suffers adverse selection. The OCR dropped the minus signs in its Sharpe-ratio tables; read tables from the PDF (`references/wiki/sources/order-book-signals.md`) |
| `how-to-almost-win/` | Diehm, *How to (almost) win in Competitive Environments*, Medium, 2025 (7 pp. browser print; decorative images removed) | Not a paper: a mindset essay by a Prosperity 3 runner-up on questioning assumptions and probing the environment. Indexed in the references wiki, not a source of formulas |
| `pseudo-math/` | Bailey, Borwein et al., *Pseudo-Mathematics and Financial Charlatanism* (34 pp.) | The readable version of the above. Theorem 3.1 bounds the backtest length needed for N trials: `MinBTL < 2 ln N / E[max_N]^2` years, for annualized Sharpe ratios on independent trials |

## Suggested reading order

1. **Intuition:** Harris (order-driven markets, liquidity, market makers) and Gould et al. sections 1–3.
2. **Market making:** Avellaneda & Stoikov (learn the result: the reservation price skews with
   inventory, the spread widens with volatility and risk aversion), then Guéant et al. (same idea
   with a hard inventory limit, the Prosperity/Arena setting).
3. **Signals and fair value:** the micro-price, then Cont et al. (order-flow imbalance predicts
   short-term price changes; test it on the Prosperity data).
4. **Sizing:** Thorp on the Kelly criterion (bet fraction from edge; use fractional Kelly because
   edge estimates are noisy; position limits are the bankroll cap).

5. **Queue position** (to check and extend `--resting`): Moallemi & Yuan for the idea, then the two articles in `references/README.md` (Rigtorp, Databento) for the estimate, then Huang et al. and Guo et al. if you need the model behind it.
6. **Validation** (before trusting a grid result or spending a portal submission): `pseudo-math`, then `probability-of-backtest-overfitting`, then `deflated-sharpe-ratio`. They are about long daily-return samples; how far the numbers transfer to a few days of tick data is an open question in `TODO.md`.
7. **Signals and many products:** Gould & Bonart (queue imbalance) and Cartea et al. 2018 (volume imbalance, adverse selection at the touch) next to Cont et al., and Guéant's multi-asset quoting next to Guéant et al.

Cartea et al. and Bouchaud et al. are references to look things up in, not to read through.

## Caveats

- **Equations are OCR, not copied.** Marker emits LaTeX, but it can misread symbols or subscripts
  (e.g. `S_{τ1}, S_{τ1}` where the paper has `I_{τ1}, S_{τ1}`) and leaves stray `---` lines.
  **Check any formula against the PDF before implementing it.** Marker's page numbers (anchors,
  figure names, `meta.json`) are zero-based, so page `N` in the markdown is page `N+1` in a PDF viewer.
- **Finding the page.** `python3 pdfpage.py <slug> <line>` (or `<first>-<last>`) gives the one-based
  PDF page of a markdown line and prints that page's text. Anchors like `<span id="page-4-0">` exist
  in only 9 of the 19 documents, so the script also uses figure names (`_page_5_Figure_2.jpeg`) and
  the headings' pages in `meta.json` to bound the page, then matches the line's words against
  `pdftotext` to pick it. Wiki pages cite the page it gives, which `references/wiki/lint.py` checks.
- **OCR failure modes seen so far** (2026-10-12, 13 papers; details on each source page under `Traps`).
  Check for these whenever a document is ingested:
  - **Tables:** minus signs dropped (Cartea et al. 2018: an all-negative Sharpe table reads as partly
    positive), decimal points dropped ("2 49" for 2.49), columns shifted. Read every table number
    from the PDF.
  - **Scope of roots and exponents:** a factor moved outside `√…` (every GLFT and Guéant closed form),
    an exponent's parentheses moved (`k/(ξΔ+1)` for `k/(ξΔ)+1`).
  - **Wrong letter in a subscript or superscript:** `P^A` for `P^B` (Cont et al.), `S_{τ1}` for `I_{τ1}`
    (Stoikov), a missing `k/` or `γ` in a parameter definition.
  - **Lost decorations:** bars, hats and tildes vanish, so in-sample and out-of-sample symbols look the
    same (PBO). Indicator functions disappear from expectations.
  - **Inline math lost entirely** in some PDFs (the deflated Sharpe ratio: definitions and example
    values are blank). Such a document must be read from the PDF.
  - **Garbled theorem statements**, a sum turned into "+i k=1 gk", and figure text spilled into the
    body.
  - **Typos in the paper itself** look the same as OCR slips: check the PDF before blaming Marker
    (Stoikov's `S = P^a + P^b`, PBO's 12,780 for C(16, 8) = 12,870).
  - **Form feeds** (`\f`) in the markdown make Python's `splitlines()` disagree with grep's line
    numbers; the tools split on `\n` only.
- **Figures are images only.** Plot contents aren't transcribed.
- **Adding a document:** put the PDF in `../literature_raw/`, add a row to `PAPERS` in `convert.sh`, run
  it, and add a row to the table above. The rest (sanity check, triage, reading, checking, wiki pages)
  is the workflow "Add a document to the literature" in `../references/wiki/SCHEMA.md`.
- Authors and titles in the table above come from the papers' first pages and common knowledge,
  not from the converted text. Fix them if one is wrong.
