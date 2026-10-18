---
title: Guilbaud & Pham, "Optimal high-frequency trading with limit and market orders" (2012)
type: source
repo: literature_md/limit-and-market-orders
status: read
updated: 2026-10-13
---

# Guilbaud & Pham, "Optimal high-frequency trading with limit and market orders" (Quantitative Finance, published online 2012, DOI 10.1080/14697688.2012.708779)

## What it is
A market maker in a book with a **tick-valued spread**: the spread is a Markov chain on 1…m ticks, and at each moment the maker chooses, per side, to quote at the best price or one tick inside it, how much, and whether to cross the spread with a market order. Solved by dynamic programming (a quasi-variational inequality) and backtested on simulated data calibrated to one stock-day (SOGN.PA, 18 April 2011). It is the discrete counterpart of the continuous-depth models in [optimal quoting models](../concepts/optimal-quoting-models.md). The user saved the published version; PDF page 1 is the publisher's cover sheet, so PDF page = printed page + 1.

## Main results
- **The choices** (`limit-and-market-orders.md:107-113` (p. 5, checked)): the bid is `Bb` (the best bid) or `Bb+` (best bid plus a tick), the ask `Ba` or `Ba−`; at a one-tick spread, `Bb+` would be the best ask and so counts as a market order. Market orders are impulses that pay half the spread plus fees.
- **Fill rates per state, from data** (eqs. 10–12, `limit-and-market-orders.md:226-248` (p. 7–8, checked)): the intensity for quote choice `q` at spread `i` ticks is the number of fills while in that state divided by the time spent in it. Their proxy from level-1 data credits a fill at `Bb` only once the traded volume exceeds the queue ahead plus the order's size, and at `Bb+` once it exceeds the order's size. On their stock, improving by a tick roughly doubles the fill rate (Figure 2).
- **The optimal policy** (Figure 3, `limit-and-market-orders.md:458-462` (p. 13, checked)): a table over (inventory, spread). Near flat and at a wide spread: improve both sides. Long: improve the ask and keep the bid at the best (short: the mirror). Past an inventory threshold, which widens as the spread widens (crossing a wide spread costs more): cross with a market order. Far from the end it barely depends on time; near the end it unwinds more aggressively.
- **Backtest** (simulated, 10⁵ paths, 300 s; Table 3, `limit-and-market-orders.md:522-524` (p. 14, checked)): mean terminal wealth / sd / information ratio — optimal 26.8 / 12.6 / 2.12; the same without market orders 25.2 / 12.6 / 2.00; always quoting at the best on both sides 24.3 / 51.5 / 0.47; random quote choice 24.0 / 63.8 / 0.38. Maximum inventory 241, 176, 608 and 772. **The gain is almost all variance:** the means differ by about 10%, the sds by a factor of four.
- **The inventory penalty sets the trade-off:** the net information ratio peaks at a penalty of about 0.8 (Table 4, `limit-and-market-orders.md:550` (p. 15)). Their own caveat: mean performance "seems largely overestimated" in the simulated backtest.

## Assumptions against the Arena
- **A small trader, an exogenous spread and the spread as the only state.** Prosperity's spreads are 2–21 ticks and set by bots (`arena.diagnose`); the paper's stock had 1–6 ticks.
- **Queue position enters only through the proxy for fills at `Bb`.** In Prosperity there is no time priority within a price ([queue position](../concepts/queue-position-and-fills.md)), so `Bb` and `Bb+` differ only in price there.
- **Fills are Cox processes per state**, independent of the order's size.

## In our notation
| Paper | Ours (`bots/template.py`) |
|---|---|
| `Bb+` / `Ba−` | `make` quotes at `best_bid + 1` / `best_ask − 1` when `make_edge` allows (`bots/template.py:700-705`) |
| keep `Bb`, improve `Ba−` when long | a `skew` of about one tick: the shift moves the bid back to the best and the ask one more tick in (`bots/template.py:707-708`) *(inferred from the code)* |
| market order past a threshold | `clear` (`bots/template.py:668`) and `take` |
| `λ_i(q)` per (quote choice, spread) | computable from `_orders.csv` and `_fills.csv` with eqs. 10–11 |

## Traps
- **OCR:** `Bb+` comes out as `Bb<sup>þ</sup>` and `Ba−` as `Ba` (`limit-and-market-orders.md:107` (p. 5)); Table 3's rows are merged into one cell (`limit-and-market-orders.md:524` (p. 14)): read it on the PDF.
- The policy figure is "stylized", not a computed table.

## Read depth
- **Read:** sections 1, 2 (model and estimation), 5 (results), on the page images.
- **Mapped:** sections 3–4 (the HJBQVI and the numerical scheme), by headings.

## Cited by
[optimal-quoting-models](../concepts/optimal-quoting-models.md), [market-making-and-inventory-skew](../concepts/market-making-and-inventory-skew.md), [pro-rata-microstructure](pro-rata-microstructure.md).
