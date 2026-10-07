# literature_md

Market-microstructure literature converted from `../literature_raw/*.pdf` to markdown with
[Marker](https://github.com/datalab-to/marker), so it can be searched and read by Claude. The
converted output is committed; the source PDFs in `literature_raw/` are gitignored. Regenerate with
`./convert.sh` (setup is in the script header).

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

## Suggested reading order

1. **Intuition:** Harris (order-driven markets, liquidity, market makers) and Gould et al. sections 1–3.
2. **Market making:** Avellaneda & Stoikov (learn the result: the reservation price skews with
   inventory, the spread widens with volatility and risk aversion), then Guéant et al. (same idea
   with a hard inventory limit, the Prosperity/Arena setting).
3. **Signals and fair value:** the micro-price, then Cont et al. (order-flow imbalance predicts
   short-term price changes; test it on the Prosperity data).
4. **Sizing:** Thorp on the Kelly criterion (bet fraction from edge; use fractional Kelly because
   edge estimates are noisy; position limits are the bankroll cap).

Cartea et al. and Bouchaud et al. are references to look things up in, not to read through.

## Caveats

- **Equations are OCR, not copied.** Marker emits LaTeX, but it can misread symbols or subscripts
  (e.g. `S_{τ1}, S_{τ1}` where the paper has `I_{τ1}, S_{τ1}`) and leaves stray `---` lines.
  **Check any formula against the PDF before implementing it.** The pages are zero-based in the
  anchors below and in `meta.json`, so page `N` in the markdown is page `N+1` in a PDF viewer.
- **Finding the page.** The markdown has anchors like `<span id="page-4-0">`, and figures are
  named `_page_5_Figure_2.jpeg`; both give the zero-based page. Read the page with
  `pdftotext -f N+1 -l N+1 -layout ../literature_raw/<file>.pdf -` or open the PDF at that page.
- **Figures are images only.** Plot contents aren't transcribed.
- Authors and titles in the table above come from the papers' first pages and common knowledge,
  not from the converted text. Fix them if one is wrong.
