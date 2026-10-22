# Kickoff prompts

Paste one of these into a fresh agent session, started in the repository's root, at the start of a round. Fill in the `<angle brackets>` and delete any line that doesn't apply. Unzip the round's download into `data/arena/round<N>/` first (`data/` is gitignored), and save the Technical Rules or assignment text there as well, as `rules.md` or the PDF as given.

The agent reads `CLAUDE.md` by itself, so the prompt only says what `CLAUDE.md` can't: which round this is, what the agent has, when it must be done, and what it must not do alone. Each person on the team pastes it with their own track.

## Round 1

```text
This is the Qminers Algo Trade Arena, round 1 of 4, for real. The round ends at <HH:MM>; run `date` now and keep track of the time yourself.

What you have:
- The round's public data: data/arena/round1/
- The organisers' assignment / Technical Rules: data/arena/round1/<rules file>  (or pasted below)
- Anything else they gave (example bot, API docs): <paths, or "nothing">

Your track: <all of it | Checklist | Probes | Data>, as in ON_THE_DAY.md, "Splitting the first hour". Teammates have the others: <who has what>.

Read first, in this order: the rules file in full, then ON_THE_DAY.md, then references/wiki/concepts/reading-the-data-on-day-one.md. Everything in this repo was built on IMC Prosperity as a stand-in. Treat every Prosperity result (IDEAS.md, the template's PARAMS) as a prior to re-test on this data, never as a fact about this market.

Work in this order, and tell me when each step is done:
1. Rules and API. Answer every item of ON_THE_DAY.md's "First hour" that the rules settle, under the item and with its source. List what they leave open, and anything in them that contradicts how the repo assumes the market works (matching, limits, scoring, the bot's interface, the runtime limits, what is allowed). Stop and show me this list before writing code.
2. The format plug-in: python/arena/formats/qminers.py, following ON_THE_DAY.md's "The format swap, step by step", then arena.diagnose on the data.
3. Our bot: a copy of python/bots/template.py with only its imports, PARAMS and ADAPTER rewritten, as python/bots/drill/template.py was. Every product in the data gets a PARAMS entry from what diagnose says.
4. arena.validate on it, under both fill modes the rules make plausible. By <T+2h, HH:MM> I want a validated bot I can upload. That comes before any tuning.
5. Then improve it: the grid's pick under --modes all,worse (or the mode the playground matched), arena.stress, the stop losses, and the IDEAS.md rows that fit these products. Each change must beat the bot before it on held-out days, not only in-sample.
6. At <T+4h30, HH:MM>: stop changing strategy. Run validate on the final candidate and give me the file to upload.

Rules for you:
- I upload. Never upload, and never spend a submission. Before each upload, tell me what the bot is, its local result, and what it should score, so that the portal score can be checked against it (ON_THE_DAY.md, "Spend the round's submissions by a rule written before the first score").
- The bot must be one self-contained .py file: standard library only (unless the rules allow more), deterministic, with its state kept the way the rules say the engine keeps it.
- Ask me before doing anything the rules may forbid, any web search beyond the organisers' own pages, ON_THE_DAY.md's "Is the data a real series in disguise?" search (it needs my approval and a budget), or a run expected to take over 10 minutes.
- --engine rust only works for bots with a Rust twin; the Arena's template has none until someone ports its ADAPTER (ON_THE_DAY.md, "Which backtest settings match the playground?"). Don't port it in round 1 unless grids are what is slowing us down, and then ask first.
- Write what you learn where CLAUDE.md says (ON_THE_DAY.md, IDEAS.md, TODO.md), and commit each step that works. Nothing stays only in the chat.
- Every hour, or when you are blocked, give me five lines: done, in progress, the bot's current local PnL, what you need from me, and the next step.
```

## Rounds 2 to 4

```text
This is the Qminers Algo Trade Arena, round <N> of 4 (weight <20|30|40>%). The round ends at <HH:MM>; run `date` now and keep track of the time yourself.

What you have:
- This round's public data: data/arena/round<N>/; earlier rounds' data: data/arena/round<1..N-1>/
- This round's rules or announcement: <path, or pasted below>
- Our final bot from round <N-1>: python/bots/<file>.py. Its portal score: <score>, our local prediction was <number>. Leaderboard: <our place, the top scores, anything visible about other teams>.
- What we learned last round: ON_THE_DAY.md (the answers written in), IDEAS.md's Arena rows, and git log since the round started.

Your track: <...>. Teammates have <...>.

Work in this order:
1. What changed. Compare this round's rules, products, limits and data with round <N-1>'s: new products, removed ones, changed limits, fees, matching, scoring, news or other new inputs. Go through references/wiki/concepts/harder-rounds.md and say which mechanisms this round shows. Stop and show me this list before changing code.
2. Does last round's bot still run? Run validate on the new data, and backtest it on the new days. That is the baseline, and an upload candidate as soon as it passes.
3. Changes, in this order: the format plug-in and ADAPTER for anything new in the API; then PARAMS for the new products; then re-tuning the old products only where the new data disagrees with the old (diagnose both). Check that a day isn't repeated from an earlier round before treating it as held out (the grid's repeated-day check).
4. By <T+2h, HH:MM>: a validated bot at least as good as the baseline on this round's data.
5. At <T+4h30, HH:MM>: stop changing strategy, run validate, and give me the file.

The rules from round 1 still hold: I upload; one self-contained, deterministic file; ask before anything the rules may forbid, any outside data search, or a long run; write what you learn into the repo and commit each step; a five-line status every hour. This round is worth <weight>%, so <"protect what we have: prefer the grid's worst day over its best PnL" | "we need to catch up: say what it would take">.
```

## Without the repository

For a second, independent attempt: an agent that sees only what the organisers hand out, so it isn't steered (or swamped) by this repo's Prosperity tooling. It is also a check on our own bot: if the clean-room bot beats it, find out why before uploading ours.

- **Start it outside the repo.** Make an empty folder (e.g. `~/arena-clean/round<N>/`), copy in the round's data, the rules and any example bot, and start the agent session there. A session started inside this repo reads `CLAUDE.md` and is no longer clean.
- **No memory or custom instructions** that mention this repo or Prosperity: a fresh account or project, or memory off.
- **The "Priors" block is optional.** It is what our Prosperity prep found, in a few lines and with no code. Keep it for a stronger attempt; delete it for a fully clean-room one.

```text
You are helping our team in a 24-hour algorithmic trading hackathon (the Qminers Algo Trade Arena). It has four rounds of 5 hours; at the end of each, a team uploads one Python bot file, which the organisers run on a simulated limit-order-book exchange. This is round <N> of 4, worth <10|20|30|40>% of the total. It ends at <HH:MM>; run `date` now and keep track of the time yourself.

Everything you have is in this folder:
- the organisers' assignment and Technical Rules: <file, or pasted below>
- the round's public data: <folder>
- <an example bot / API docs / nothing else>
Use nothing else: no web search, no other folders, unless I say so.

The deliverable is one self-contained .py file that follows the rules' bot interface exactly: standard library only unless the rules allow more, deterministic (seed any randomness, never read the clock), keeping state between calls only in the way the rules say the exchange keeps it, and inside every runtime limit.

Work in this order, and tell me when each step is done:
1. Read the rules in full. Write rules_summary.md: the bot's interface (what it is called with, what it returns, how often), order types and how they match and expire, position limits and what happens on a breach, fees, scoring (what open positions are marked to, whether they are liquidated at the end), runtime and memory limits, allowed libraries, and the submission rules. List what the rules leave open or ambiguous. Stop and show me this before writing code.
2. Look at the data. Per product: price units and tick size, the spread and the book's depth, how the mid behaves (does it return to a level, trend, or jump, and do jumps reverse), how often market trades print and at which prices, whether products are related (baskets, options, a common factor), and whether trades name counterparties. Check whether any day repeats another. Write it into data_notes.md with the numbers.
3. A local backtester (backtest.py) that replays the data through the bot's exact interface, enforcing the limits and the breach rule as the rules state them. Make the passive-fill rule a switch: optimistic (a trade at our price fills us) and conservative (only a trade through our price, or a book that crosses us, fills us). Report PnL per product and day, positions, fills, errors and the slowest call. Test it on a few hand-made ticks before trusting it.
4. A simple, robust first bot: per product, a fair value that ignores small orders near the touch (e.g. the mid of the largest levels), take anything mispriced against it, quote passively around it, and push inventory back toward zero near the limit. Never send orders that could breach a limit. Catch exceptions per product so one product's error can't stop the others.
5. Validate it: every day runs with no errors, no breaches, deterministic across two runs, within the time limit, in both fill modes. By <T+2h, HH:MM> give me a file I can upload. That comes before any tuning.
6. Then improve, one change at a time. Tune on some days and check on days the tuning didn't see; prefer a setting whose neighbours also do well over the single best; distrust a gain that disappears under the conservative fill rule. Keep a log (changes.md): each change, its PnL per day in both modes, kept or dropped.
7. At <T+4h30, HH:MM>: stop changing strategy, re-run the validation, and give me the final file.

Rules for you:
- I upload. Never upload or spend a submission. Before each upload, tell me what the bot is and what score you expect from the backtester, so that the portal's score checks the backtester.
- Ask before anything the rules may forbid, and before any run expected to take over 10 minutes.
- Every hour, or when you are blocked: five lines: done, in progress, the bot's current local PnL (both fill modes), what you need from me, the next step.

Priors from practice on similar exchanges (IMC Prosperity), to test on this data, not to trust:
- A backtest that fills passive orders on any trade at their price overstates passive profit, often by a third or more; whatever beats the market under the optimistic rule may lose under the conservative one.
- The mid of the largest book levels (the market maker's "wall") is a far quieter fair value than the plain mid, unless another team's large orders can become the largest level; then use the mid of levels above a size threshold.
- Quoting one tick inside the best price around a good fair value, plus taking clear mispricings, was the core of most profit; inventory skew cost money when holding inventory had no penalty.
- Products that return to a known level pay most when held at the full limit against moves away from it; products that jump and mostly snap back pay for holding against each jump, once the day shows jumps do reverse.
- Days are often reused across rounds; a repeated day is not a held-out test.
- If open positions are liquidated badly at the end, flatten in the last few percent of the day.
- A loss stop per product (about 3 times its normal worst drawdown) limits the damage when a market behaves unlike its data.
```

For rounds 2–4, add this to the prompt above, after the list of files:

```text
This is not the first round. Also in this folder: our final bot from round <N-1> (<file>), its portal score (<score>) against what our backtester predicted (<number>), the leaderboard (<what it shows>), and last round's notes (rules_summary.md, data_notes.md, changes.md). Start with step 1 as a diff: what changed in the rules, products, limits and data since last round, and stop to show me. Then run last round's bot on the new data as the baseline and first upload candidate, and change only what the new data contradicts.
```
