---
title: Stoikov, "The micro-price" (2018)
type: source
repo: literature_md/micro-price
status: read
updated: 2026-10-12
---

# Stoikov, "The micro-price: a high-frequency estimator of future prices" (Quantitative Finance, 2018)

## What it is
A 9-page paper that defines a fair price from the top of the book: the limit of expected future mid-prices given the current imbalance and spread. The function is estimated from Level-1 data as a Markov chain, and on two US stocks it predicts price changes better than the mid or the weighted mid. It is the theory behind the "micro-price" that several Prosperity teams use loosely to mean a volume-weighted mid ([heyman7913](prosperity4-heyman7913.md)).

## Main results
- **Three prices.** The mid `M = ½(Pᵃ + Pᵇ)` (`micro-price.md:51` (p. 2, checked)). The weighted mid `W = I·Pᵃ + (1 − I)·Pᵇ` with the imbalance `I = Qᵇ/(Qᵇ + Qᵃ)`, where `Qᵇ` and `Qᵃ` are the volumes at the best bid and ask (`micro-price.md:69-75` (p. 3, checked)). And the micro-price `P^micro = M + g(I, S)` with spread `S = Pᵃ − Pᵇ` (`micro-price.md:83-87` (p. 3–4, checked)).
- **Why not the weighted mid.** It is noisy, it is not a martingale, and it can move the wrong way. Example: bid 10.00 × 9, ask 10.02 × 27 gives W = 10.005; a sell order of 1 at 10.01 *raises* W to 10.009 (`micro-price.md:79` (p. 3, checked)).
- **Definition.** `P^i_t = E[M_{τ_i} | F_t]` is the expected mid after the i-th mid change, and `P^micro = lim_{i→∞} P^i_t`, which is a martingale and independent of the horizon (`micro-price.md:95-113` (p. 4, checked)). Theorem 1 writes `P^i_t = M_t + Σ_{k=1}^{i} g^k(I_t, S_t)` with `g¹(I, S) = E[M_{τ₁} − M_t | I, S]` and the recursion `g^{i+1}(I, S) = E[g^i(I_{τ₁}, S_{τ₁}) | I, S]` (`micro-price.md:143-155` (p. 4, checked)). It needs two assumptions: (I, S, M) is a Markov state, and mid increments don't depend on the mid's level (`micro-price.md:119-139` (p. 4)).
- **Estimation in a finite state space** (`micro-price.md:188-226` (p. 5, checked)):
  - Bucket the imbalance into n bins, `I_t = j` when `(j−1)/n < Qᵇ/(Qᵇ+Qᵃ) ≤ j/n`, and the spread into m values in ticks. `K` is the vector of possible mid changes (in the paper ±½ and ±1 tick).
  - From the data, estimate `R` (state x → mid moves by k, nm × 4), `Q` (state x → mid unchanged and state y, nm × nm) and `T` (state x → mid moves and state y).
  - Then `G¹ = (1 − Q)⁻¹ R K`, `B = (1 − Q)⁻¹ T`, and `P^i_t = M_t + Σ_{k=0}^{i} B^k G¹`.
- **The recipe** (`micro-price.md:276-286` (p. 6, checked)): symmetrise the data (every tuple `(I_t, S_t, I_{t+1}, S_{t+1}, dM)` also enters as `(1−I_t, S_t, 1−I_{t+1}, S_{t+1}, −dM)`), which guarantees `B*G¹ = 0` and so convergence (Theorem 2: `micro-price.md:230-234` (p. 5–6, checked)). Estimate Q, T, R; compute `G* = P^micro − M = G¹ + Σ_{i≥1} B^i G¹`, a table indexed by (imbalance bin, spread). "In practice, this sum converges very fast."
- **Empirical findings** on BAC (spread mostly 1 tick) and CVX (spread 1–4 ticks), March 2011, one-second data (`micro-price.md:302-310` (p. 8)):
  - The adjustment lies between the mid (0) and the weighted mid (±½ spread), so the micro-price stays inside the spread, though nothing forces it to.
  - **As the spread widens, the imbalance matters less**; for CVX at a 4-tick spread "the micro-price is indistinguishable from the mid-price and the imbalance seems to have no additional information".
  - The adjustment is larger for the large-tick stock (BAC).
  - At 1 minute BAC's realised mid changes are smaller than the prediction (negative autocorrelation, the bid–ask bounce); at 3 minutes they agree. For CVX 10 seconds is enough.
- **Special cases** (appendices): if the imbalance is independent of future moves, the micro-price is the mid; if the imbalance is a Brownian motion with a particular reset at 0 and 1, it is the weighted mid (`micro-price.md:335-372` (p. 9)).

## Assumptions against the Arena
- **Spreads are wide in Prosperity** *(checked: computed from round 1 day 0 of each edition)*. P3 Kelp: 3 ticks on 52% of ticks, 2–4 on 88%; Squid Ink: 3 ticks on 58%; Resin: 6–10 ticks on 70%. P4 Pepper Root: 13–17 ticks; Osmium: 16 ticks on 63%. The paper's own result says the imbalance carries little at a 4-tick spread, so the micro-price may add nothing over the mid there. This needs measuring per product, not assuming.
- **The mid moves on 60–78% of ticks** in those files *(checked, same data)*, unlike BAC's large-tick mid, so `K` needs every observed mid change, not ±½ and ±1 tick.
- **The book is made by a few bots, not a crowd.** In Prosperity the best-level volume is mostly the market-making bot's quote, whose size may not respond to order flow the way a real queue does. The "wall mid" (the bot's own quote) is a different estimator, and teams found it closer to the mark ([fair value](../concepts/fair-value-and-wall-mid.md)).
- **One-second snapshots, stationary Markov state.** Prosperity ticks are snapshots too, but 10,000 a day; the paper fits a month. A table with n × m cells needs enough visits per cell.

## In our notation
| Paper | Ours |
|---|---|
| `Pᵇ, Qᵇ` / `Pᵃ, Qᵃ` | `book.bids[0]` / `book.asks[0]` as `(price, volume)` in `python/bots/template.py` (volumes positive, `python/arena/model.py:16-17`); `bid_price_1`, `bid_volume_1`, `ask_price_1`, `ask_volume_1` in the CSVs |
| `M` | `mid()`, `python/bots/template.py:356`; `fair: "mid"` |
| `W` | not in the template; one line from the best levels |
| `G*(I, S)` | would be a lookup table in `PARAMS`, estimated offline from the CSVs, since the bot must stay standard library and self-contained |
| a tick | 1 price unit in Prosperity (the paper's 1 cent) |

## Traps
- **OCR:** in the proof of the recursion, `E[… | S_{τ1}, S_{τ1}]` and `g^i(S_{τ1}, S_{τ1})` where the PDF has `S_{τ1}, I_{τ1}` and `g^i(I_{τ1}, S_{τ1})` (`micro-price.md:178` (p. 5)). This is the example quoted in `literature_md/README.md`.
- **OCR:** Theorem 1's formula (5) is garbled into "Pi t = Mt +i k=1 gk (It, St)" (`micro-price.md:145` (p. 4)); the PDF has `P^i_t = M_t + Σ_{k=1}^{i} g^k(I_t, S_t)`.
- **Typo in the paper itself:** Assumption 1 writes the spread as `S_t = (P^a_t + P^b_t)` (`micro-price.md:125` (p. 4, checked)); the PDF has the same "+". The spread is `Pᵃ − Pᵇ`, as defined under (4).
- `(1 − Q)⁻¹` means `(Id − Q)⁻¹`, the identity minus Q.
- The symmetrisation is what makes the sum converge. Without it, a drift in the sample makes `P^i` blow up (`micro-price.md:228` (p. 5)).

## Read depth
- **Read:** all of it, including the appendices.
- **Checked against the PDF (page images):** formulas (1)–(6), the finite-state formulas for `G¹`, `B`, `P^i`, the estimation recipe and `G*`.
- **Not checked:** the figures (images only; their content is described from the text).

## Cited by
[book-imbalance-and-micro-price](../concepts/book-imbalance-and-micro-price.md), [fair-value-and-wall-mid](../concepts/fair-value-and-wall-mid.md).
