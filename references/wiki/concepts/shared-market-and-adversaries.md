---
title: Shared markets and adversaries
type: concept
updated: 2026-10-13
---

# Shared markets and adversaries

## Summary
IMC Prosperity is a market against bots only. Two events in the clones (UChicago, AlgoTrade) were shared between teams, and their lessons are different: crowded edges decay, and some teams attack other teams' resting orders. Whether the Arena is shared is unknown.

## What the sources say
- **Prosperity: bots only.** Your orders match against the bots' book and trades; other teams cannot affect your fills (`references/README.md`, "How these relate to the Arena").
- **Book-sniping** (UChicago): late in the competition some teams bought out one side of a book and posted extreme prices on the other, trapping resting orders. The winners did not post resting limit orders in products they were unsure about, and avoided options and the prediction market, the thinnest books (`uchicago-trading-2026/README.md:187`, `uchicago-trading-2026/README.md:233`).
- **The other side of that trade** (AlgoTrade): rest tiny orders at the legal price extremes (1 cent and 999,999) so that anyone sweeping the book pays you; the doc itself says fills are not guaranteed and it needs other teams in the market (`algotrade2026-pitfa19/docs/VOIDMAKER_EDGE_PROOF.md:9-30`).
- **Crowded edges decay:** a Ready Trader Go team's arbitrage bots worked alone but "performed poorly when put alongside other traders" (online README, `references/SEARCH_LOG.md`, "Books and articles"); Linear Utility's orchids arbitrage was leaked on Discord and they fell from 2nd to 17th as everyone found it (`prosperity2-linear-utility/README.md:118-137`); UChicago's ETF mispricings became rarer in later rounds (`uchicago-trading-2026/README.md:229`).
- **Exchange failures are part of a live shared event:** sporadic freezes (UChicago, `uchicago-trading-2026/README.md:231`); AlgoTrade's rate-limit disconnects and segment resets (`algotrade2026-pitfa19/.firecrawl/algotrade-participant-guide.md:397`).

- **A winner's account of a shared market** (Negative Eevee, AlgoTrade 2026): "all teams traded in the same shared market" (`algotrade2026-negative-eevee/README.md:7`). Their cross-exchange IOC arbitrage took "almost all of these inefficiencies out of the market as soon as they appeared", and "several teams mentioned that their own cross-exchange arbitrage became much worse around round 2, which was also when our first prototypes went live"; mean reversion "still allowed other teams to enter later; cross-exchange arbitrage did not" (`algotrade2026-negative-eevee/README.md:23`). The edge that survives in a shared market is the one others cannot join late.

- **Measured: the template against the teams' own P4 bots** (2026-10-13; DU, Baguette Fromage and DTU in one market with it, P4 rounds 1–2, `IDEAS.md` has the numbers):
  - **With orders that live one tick,** Osmium's spread is a fixed pie the bots split: the template keeps 45–51% of it against one rival and 20% against three. The drift on Pepper Root pays everyone. This is the Grossman–Miller dilution below, in a simulation.
  - **With resting orders,** the template loses up to 445k on Osmium in a round. A rival's large order far from fair becomes the "largest level", so the template's `wall_mid` follows it (`bots/template.py:256`). At tick 2,400 of round 1 day 0, a 40-lot bid at 9,906 outweighed the market maker's 23-lot wall at 9,991, and the template sold into the real bids. Its fair was 5+ off on 36% of ticks *(checked)*.
  - That is Harris's trap below, played without intent: the rivals' far quotes are not bait, yet they move a fair value built on size.

**What the literature says** ([Harris](../sources/harris-trading-and-exchanges.md), [Cartea et al., book](../sources/algorithmic-and-hft.md)):
- **Our template is a quote matcher.** Quoting one tick in front of the bot's large quote ("penny jumping") gives an option-like payoff: full gain if the price moves our way, a one-tick loss if not, because we can sell back to the large order (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:5889` (p. 261)). That backstop exists only while the large order stays. A rival can **trap** a quote matcher: bait with size, sell into the matcher, cancel the bait (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:5919` (p. 263)).
- **Resting orders give away a timing option.** A faster trader picks off a stale quote after news. Spreads must cover order-management cost plus twice the option's value, more so when cancelling is slow or the product volatile (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:7140-7146` (p. 320)).
- **Bluff-proof pricing:** if our quotes react to the flow we see, they must move by the same amount per unit for buys and sells, large or small, fast or slow. Otherwise a rival can buy with one kind of order and sell with the other at a profit (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:6369-6381` (p. 283–284)). A flow- or imbalance-driven fair value needs this check ([book imbalance](book-imbalance-and-micro-price.md)).
- **Competition erodes the edge:** with n competing market makers, the liquidity discount a trader pays falls like 1/(n+1) (Grossman–Miller, `literature_md/algorithmic-and-hft/algorithmic-and-hft.md:575-579` (p. 41)). Competition among arbitrageurs narrows arbitrage spreads to the costs of the most efficient one (`literature_md/harris-trading-and-exchanges/harris-trading-and-exchanges.md:8801` (p. 391)). This is the theory behind "crowded edges decay".

## Where they disagree
The Prosperity record has no shared-market evidence; our simulation with the teams' bots is the closest (above), and it shows only what bots written for a solo market do to each other. Theory against practice on quoting inside the wall, which Harris's trapper exploits: [contradictions](../contradictions.md), row 16.

## What it means for our code
`arena.run_market` and `--vs BOT` simulate other bots' resting orders in the same market (`CLAUDE.md`, "Shared market"). Rivals are only bots we bring. The template's `wall_mid` takes the largest level on each side, so in a shared market with resting orders it needs a definition that ignores large orders far from the touch. `fair: sized_mid` (the first level from the top with at least `wall_size`) is that definition. Against the three teams' bots it made +39k on Osmium in round 1, where `wall_mid` lost 377k ([fair value](fair-value-and-wall-mid.md)).

## How to test it here
The teams' P4 bots are real rivals for `--vs` (above). In `--resting` they must be wrapped to cancel their orders every tick, or they freeze: their orders pile up and every new one fails the limit check. DU's bot alone on round 1 day 0 made 28 fills, with orders cancelled for a breach on 19,998 product-ticks *(checked)*. Two more `--vs` rivals to build: a **quote-matching trapper** (posts a large bid, sells into anyone who bids one tick above it, cancels), and a **sniper** that takes our resting quotes after the mid moves (the timing option, under `--resting`).

`ON_THE_DAY.md`, "Is the market shared?" lists the Arena site's hints (they point both ways). If shared: test the bot against a `--vs` rival that snipes one side; add a "no resting orders in thin books" mode; decide beforehand what to do when a book empties.

## Sources
[Harris](../sources/harris-trading-and-exchanges.md), [Cartea et al., book](../sources/algorithmic-and-hft.md), [UChicago](../sources/uchicago-trading-2026.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [Linear Utility](../sources/prosperity2-linear-utility.md). [Negative Eevee](../sources/algotrade2026-negative-eevee.md), [Diehm essay](../sources/timo-diehm-medium-article.md).
