---
title: Shared markets and adversaries
type: concept
updated: 2026-10-10
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

## Where they disagree
Nothing to compare: the Prosperity record has no shared-market evidence.

## What it means for our code
`arena.run_market` and `--vs BOT` simulate other bots' resting orders in the same market (`CLAUDE.md`, "Shared market"). Rivals are only bots we bring.

## How to test it here
`ON_THE_DAY.md`, "Is the market shared?" lists the Arena site's hints (they point both ways). If shared: test the bot against a `--vs` rival that snipes one side; add a "no resting orders in thin books" mode; decide beforehand what to do when a book empties.

## Sources
[UChicago](../sources/uchicago-trading-2026.md), [AlgoTrade](../sources/algotrade2026-pitfa19.md), [Linear Utility](../sources/prosperity2-linear-utility.md). [Negative Eevee](../sources/algotrade2026-negative-eevee.md), [Diehm essay](../sources/timo-diehm-medium-article.md).
