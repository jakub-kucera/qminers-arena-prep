---
title: Byrd, "The accidental pump and dump" (2025)
type: source
repo: literature_md/accidental-pump-and-dump
status: read
updated: 2026-10-14
---

# Byrd, "The accidental pump and dump: when agentic AI meets autonomous trading" (ICAIF 2025)

## What it is
A deep-RL trader that can also make an LLM post to a simulated social feed. Sentiment traders read the feed and trade in the direction it suggests. Nobody told the RL trader to manipulate anything, but it learns to post positive or negative "analysis" that moves them, a pump and dump it found by itself (`accidental-pump-and-dump.md:7` (p. 1)). The paper is 8 pages (printed pp. 88–95). The simulator's code is at `github.com/davebyrd/minabides-icaif25` (not checked).

## Main results
- **The agent population** (`accidental-pump-and-dump.md:188-198` (p. 4)): 1 ladder market maker around the mid, 10 momentum traders reading recent trades, 5 noise traders, 10 value traders arbitraging toward a private "true" value (noisy observations of the real AMZN trades that day), 10 sentiment traders and the DQN agent. The market maker acts about every second, the DQN every 15 seconds, everyone else every minute. No orders are replayed, so every agent moves the price, and the value traders keep it near a real day's path (`accidental-pump-and-dump.md:182` (p. 4)).
- **The DQN agent:** its actions are market buy or sell, close the position, do nothing, and a positive or negative post. Limit orders are left out (`accidental-pump-and-dump.md:119` (p. 3)). The reward is the change in portfolio value since its last action. Its state (`accidental-pump-and-dump.md:115` (p. 3)) is its holdings, its open orders, the mid relative to the open, and a short sequence of book snapshots fed through an LSTM. Its configuration: 200-share trades with a holdings limit of 100 shares, as written (`accidental-pump-and-dump.md:214` (p. 5)).
- **Posting pays, mostly in sample** (Table 3, `accidental-pump-and-dump.md:254-277` (p. 8), and Table 2, `accidental-pump-and-dump.md:159-169` (p. 4)). For the long-short DQN, mean daily profit was 513 in sample and 77 out of sample with posts, against 370 and 72 without them. The sentiment traders went from +124 to −136 in sample, and from +27 to +2 out of sample.
- **More followers, more to exploit** (`accidental-pump-and-dump.md:240` (p. 6)). Extra sentiment agents fell for the pump more, perhaps because their own trades fed back into the LLM commentary. A single one resisted better.
- **Speed has a sweet spot** (`accidental-pump-and-dump.md:240` (p. 6)). Below a 15-second interval the agent missed the trades its own pumping created. Above it, it disturbed the followers more, but the profit went to other agents.
- **The long-only anomaly** (`accidental-pump-and-dump.md:230` (p. 6)). With posts, the sentiment traders did better as the DQN learned. The value traders, whose reversion the push delayed, paid instead. The author's two explanations are "accidental collusion" or a month that mostly went up.
- **LLM posts are unreliable** (`accidental-pump-and-dump.md:238` (p. 6)). They contradicted themselves, hallucinated volumes in the tens of thousands, and predicted a bounce while claiming to be short.

## Assumptions against the Arena
- **No social feed is expected.** The mechanism carries over to any signal that other bots read and that one bot can move. In a Prosperity-style market that signal is the book (spoofing, [harder-rounds](../concepts/harder-rounds.md) D3) and the trade tape (momentum ignition, same list) *(inferred)*.
- **If the Arena gives news or text** (`ON_THE_DAY.md`, "Extra information"), it may be written by an LLM. Treat it as a noisy signal that a rival may be steering, and check it against the next prices before following it.
- **For the LLM zoo (D2):** the population above is a ready mix of archetypes for `--vs` rivals and for the A1 day generator. The result that more followers are easier to exploit argues against a field that shares one signal *(inferred)*.

## In our notation
- **Its sentiment heuristic:** a confidence-weighted vote over recent posts, `h(l) = Σ_{p: p_l = l} p_c` (eq. 7, `accidental-pump-and-dump.md:109` (p. 3, checked)). The trader goes with the argmax label.
- **Its reward:** the per-step change in marked portfolio value, which corresponds to our engine's per-tick PnL.

## Traps
- **The headline gain is in sample** *(checked: Tables 2 and 3)*. Out of sample, posting adds 77 against 72 for the long-short agent, well inside one standard deviation (36 and 54).
- **The two tables cover different days** *(checked: `accidental-pump-and-dump.md:218` (p. 5), `accidental-pump-and-dump.md:226` (p. 6))*. Table 2 is one day (1 July 2025) over 1,600 trips, and Table 3 is all 22 trading days in July over 150,000 trips. So the with-and-without comparison above also mixes days.
- **The holdings limit (100) is smaller than one trade (200)**, as printed. The paper doesn't explain how that works.
- **The market maker's PnL swings sign**: in sample it makes +4.5k to +10.2k a day, out of sample it loses about 2.2k. That points to in-sample overfitting of the whole population, not only of the DQN.

## Read depth
- **Read:** all of it (8 pages), including Tables 1–3.
- **Skimmed:** the RL background (section 1.4) and the TD3 preliminaries (section 3).
- **Unread:** the code repository and the prompts it holds.

## Cited by
[harder-rounds](../concepts/harder-rounds.md).
