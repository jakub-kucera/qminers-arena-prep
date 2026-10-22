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
