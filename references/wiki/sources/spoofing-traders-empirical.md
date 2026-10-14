---
title: Lee, Eom & Park, "Microstructure-based manipulation" (2013)
type: source
repo: literature_md/spoofing-traders-empirical
status: read
updated: 2026-10-14
---

# Lee, Eom & Park, "Microstructure-based manipulation: strategic behavior and performance of spoofing traders" (J. Financial Markets 2013)

## What it is
What real spoofers did, from account-level data. The Korea Exchange (KRX) kept every order, cancel and fill with the account behind it, for November 2001 to February 2002, across 549 stocks (`spoofing-traders-empirical.md:23` (p. 2), `spoofing-traders-empirical.md:83` (p. 12)). Until the end of 2001 the KRX showed the five best levels on each side with their prices, plus the **total quantity on each side** without the prices behind it. A large buy far below the market therefore made the whole bid side look heavy, and nobody could tell how far away it sat (`spoofing-traders-empirical.md:31-35` (p. 3–4), footnote 1 at `spoofing-traders-empirical.md:424` (p. 47)). On 2 January 2002 the KRX stopped showing the totals and widened the visible book to ten levels, which gives a natural experiment. The file is the 53-page manuscript version, with tables and figures at the end.

## Main results
- **The definition** (`spoofing-traders-empirical.md:75` (p. 11)): an order at least twice the previous day's average order size, at least 6 ticks from the market price, followed by an order on the other side and then cancelled. Short selling was effectively impossible, so nearly all spoofs were buys that helped a later sale (`spoofing-traders-empirical.md:79` (p. 12)).
- **The shape of a spoof:**
  - **Size:** the average spoof buy was 4,809 shares against 864 for all buys, 5.6 times as large (`spoofing-traders-empirical.md:101` (p. 15)). In the 30 most-spoofed stocks it was 11.1 times as large, and in the 30 least-spoofed 2.4 times. The authors read this as investors knowing about spoofing, so only bigger spoofs fooled them (`spoofing-traders-empirical.md:103` (p. 15)).
  - **Distance:** 89.5% sat more than 10 ticks below the best bid (`spoofing-traders-empirical.md:105` (p. 16)).
  - **Timing:** the sale came 43.3 minutes after the spoof on average, and the cancel another 35.7 minutes later (`spoofing-traders-empirical.md:111` (p. 16)). The authors argue the late cancel is camouflage: a cancel right after the sale would draw a regulator's eye (`spoofing-traders-empirical.md:235` (p. 30)).
  - **How common:** 0.81% of all buy volume, 96% of it from individuals (`spoofing-traders-empirical.md:87` (p. 13)). 18,133 accounts spoofed, 72% of them once, while 62% of the spoofs came from repeat spoofers. One account spoofed 332 times in 10 stocks (`spoofing-traders-empirical.md:117` (p. 17), `spoofing-traders-empirical.md:241` (p. 31)).
- **Who is targeted** (`spoofing-traders-empirical.md:139` (p. 20)): stocks with higher volatility, smaller market value, lower prices and weaker disclosure. Trading volume doesn't matter. Spoofing follows the U-shaped intraday pattern of all orders but is flatter (`spoofing-traders-empirical.md:97` (p. 14)).
- **It pays** (Table 5, `spoofing-traders-empirical.md:165` (p. 22)). The extra profit is 79 bp per trade for spoofers who weren't day trading. Spoofing day traders made 67 bp gross and 21 bp net of a 46 bp cost (definition A), or 83 bp and 37 bp (definition C). All day traders together made 15 bp gross and lost 31 bp net. 58.3% of spoofs had a positive extra profit and 28.3% a negative one, 30.6 binomial standard deviations from a zero median (`spoofing-traders-empirical.md:181` (p. 24)).
- **Showing the prices killed most of it** (Table 6, `spoofing-traders-empirical.md:191-195` (p. 25–26)). Spoofing fell from 0.81% to 0.26% of buy volume. The share placed beyond 10 ticks fell from 89.5% to 40.8%. A spoofer now had to sit inside the visible ten levels, where others could see the price and discount it, and where it risked filling (`spoofing-traders-empirical.md:255` (p. 33)).

## Assumptions against the Arena
- **The mechanism needs a hidden price.** The spoof worked because the side totals included orders whose distance nobody could see. A Prosperity-style feed shows a few levels with their prices and nothing beyond, as the KRX did after the change. So a far spoof is invisible and does nothing, and a spoofer has to sit near the touch, where it can fill. This is the setting of [Wang & Wellman](spoofing-abm.md) and [Cartea, Jaimungal & Wang](optimal-spoofing.md) *(inferred from the rule-change result)*.
- **If the Arena shows a side total or a depth beyond the visible levels**, an imbalance or fair value built from it is exactly what these spoofers targeted. Use only the levels with prices, weighted by distance (`ON_THE_DAY.md`, "Extra information").
- **Absolute thresholds don't transfer.** Six ticks is inside the normal quoting range on wide-spread Prosperity products (P4 Osmium's spread is 16 ticks on 63% of ticks, [micro-price](micro-price.md)). Twice the average size flags the market maker's walls. Use each product's own baseline: beyond the market maker's usual distance, and larger than its usual wall ([hidden takers](../concepts/hidden-takers-and-empty-sides.md)).
- **Long-lived spoofs beat a persistence check.** These rested for about 79 minutes in all, so "trust a wall only after N ticks" ([harder-rounds](../concepts/harder-rounds.md), D3) wouldn't have filtered them. What gave them away was size and distance, then a cancel without a fill *(inferred)*.
- **The targets are thin, volatile, cheap products.** In a multi-product round, expect a spoofer on the product with the widest, noisiest book, which agrees with [Gu et al.](spoofability-and-liquidity.md) on thin markets.

## In our notation
For a level at price `p` with volume `v` on product `X`, the paper's tell is `|p − mid| ≥ 6 ticks` and `v ≥ 2 · v̄_X(previous day)`, followed within the day by our counterparty's opposite trade and a cancel. Only the cancel and the account link need data we lack: Prosperity's book has no order IDs, so "cancelled without trading" has to be read as a level that disappears with no market trade at its price.

## Traps
- **Intent is inferred, not seen.** The authors argue it from size, distance, timing, the rule change and who traded (sections 6.1–6.7). The profit is measured against the price when the spoof was placed, so a rising market inflates it. The KOSPI rose 69 bp a day in the period, which the authors compare with the day traders' 15 bp (`spoofing-traders-empirical.md:167-171` (p. 22–23)).
- **The definition is the sample.** "At least 6 ticks" and "twice the size" select the orders that are then found to be far and large, so the 5.6 times and the 89.5% describe the filter's catch as much as the spoofers.
- **No formulas need checking.** The only equation is the regression for which stocks are targeted (eq. 1, `spoofing-traders-empirical.md:131` (p. 19)).

## Read depth
- **Read:** sections 1, 3–7 and footnote 1.
- **Skimmed:** the literature review (section 2) and the regression table.
- **Unread:** the other footnotes, the appendix tables and figures beyond those cited.

## Cited by
[harder-rounds](../concepts/harder-rounds.md), [hidden-takers-and-empty-sides](../concepts/hidden-takers-and-empty-sides.md), [optimal-spoofing](optimal-spoofing.md), [manipulation-detection-evasion](manipulation-detection-evasion.md).
