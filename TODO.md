# Prep to-do

Work left before the Arena (7–8 Nov 2026). Things to find out at the event itself are in
[`ON_THE_DAY.md`](ON_THE_DAY.md). Things only a person can obtain (organiser documents, blocked web pages, books)
are in [`docs/MANUAL_TODO.md`](docs/MANUAL_TODO.md). When an item's "done when" holds, tick it and move it, with
its sub-bullets, to [`docs/TODO_DONE.md`](docs/TODO_DONE.md) under the same heading; add new items as they come up.

## Decisions

Choices only the user can make, each with the options, the evidence and a recommendation.

- [ ] **A second zoo spec with what the Arena's site shows?** Raised by the user 2026-10-26: given the site's new facts, would the models write different bots?
  - Options: (a) keep `python/bots/zoo/SPEC.md` (Prosperity's rules) for every prep-time zoo bot, and put the Arena's real rules into the round's spec on the day (`ON_THE_DAY.md`, "The round's zoo"); (b) add a second spec now, beside it (a used spec is never edited), with our guesses at the Arena's scoring: the end position valued at the touch, a fine per lot over the limit instead of Prosperity's rejection, maybe one product. Run the same models and prompts through it and score the bots under `--mark touch --limit-penalty` (`experiments.study.zoo` would need those two options).
  - Evidence: of the site's facts, only two would reach a bot's code: the price the end position is valued at (`markPrice`) and what a breach costs (`breachPenalty`). Neither one's value is known (`ON_THE_DAY.md`, "Known so far"). The rest (the submission cap, one evaluation at a time, the leaderboard, the metrics' names) is portal mechanics that changes how a team works, not what the model writes. The other teams' models will get the Technical Rules on the day, not the site's code, so a spec built on our guesses can make the zoo less like the field. What (b) could show: whether the template's lead over the zoo depends on those two rules. Cost: the user's time for 2 models × 4 prompts × 2 samples, and the two options in `experiments.study.zoo`.
  - Recommendation: (a). Spend the model time on the open Gemini and ChatGPT prompts with the current spec ("Zoo bots from other LLM providers" below: `mean_reversion` and `momentum`, the older models), which keeps them comparable with the 59 bots so far. The day's spec gets the real rules.

- [ ] **Cap the template's quotes at 20 lots (`make_size` 20 on Kelp and Resin)?** Raised by an audit follow-up, 2026-10-26.
  - Options: (a) keep the full room (`None`), and cap on the day only if probe 3 shows orders arrive late; (b) cap both at 20 now.
  - Evidence (P3 round 1, `uv run python -m arena.grid python/bots/template.py 1 --data p3 --grid PARAMS.KELP.make_size=None,20 --grid PARAMS.RAINFOREST_RESIN.make_size=None,20 --modes all,worse --scenario wfee05:match=worse,fee=0.5 --scenario rest:resting,queue=prob --scenario late:delay=1 --scenario war:resting,vs=python/bots/template.py --engine rust`): both capped make 72,670 / 63,306 / 40,618 / 66,460 (`all` / `worse` / `worse` with a 0.5 fee / resting) against 72,674 / 63,302 / 40,608 / 66,562 uncapped, so nothing on their own; one tick late 45,534 against 40,472 (+12%, the races: `IDEAS.md`, "Orders that arrive a tick late"); but resting against a copy of the template 15,224 against 26,904 (−43%), because the copy takes the room the cap leaves.
  - Recommendation: (a). The cap's gain needs a late exchange, its loss a shared market with full-room rivals, and probes 3 and 4 tell the two apart in the first hour; `ON_THE_DAY.md`, "How are position limits enforced?", says when to cap.
- [ ] **Kelp's `make_edge`: keep 0.5, or 1?** Raised 2026-10-26 by the fee grid, where a wider Kelp quote won under `all` at every fee.
  - Options: (a) keep 0.5 (chosen 2026-10-15 for `worse` fills and a reacting market: `docs/TODO_DONE.md`, "Tune Kelp and Squid Ink for `worse` fills?", where 0.5 also beat every zoo bot head to head under `worse`); (b) 1; (c) 1.5.
  - Evidence (P3 round 1, `uv run python -m arena.grid python/bots/template.py 1 --data p3 --grid PARAMS.KELP.make_edge=0.5,1,1.5,2 --modes all,worse --scenario wfee05:match=worse,fee=0.5 --scenario rest:resting,queue=prob --scenario late:delay=1 --engine rust`), `all` / `worse` / `worse` with a 0.5 fee / resting / one tick late: 0.5 makes 72,674 / 63,302 / 40,608 / 66,562 / 40,472; 1 makes 81,366 / 57,764 / 40,623 / 68,058 / 44,019; 1.5 makes 84,512 / 52,294 / 38,936 / 59,968 / 45,173. 1 has the best worst case (40,623) and wins every model but `worse`, where it loses 5,538 (−9%); 1.5 loses 11,008 there and is worst resting. Under `all` with fees (`IDEAS.md`, "Fees") 1.5 leads by more as the fee grows.
  - Recommendation: (a) for now. The default matters only if the day's grid isn't run, and the RUNBOOK re-grids `make_edge` at T+1:00 under the playground's mode with `worse` as the gate (`ON_THE_DAY.md`, "Which modes gate the grid's pick?"); if that grid can't be run, (b) is the safer default because of its worst case.

- [ ] **(a, part 2) Zoo bots from other LLM providers.** The first zoo is all Claude, so it shares one model's habits; the field on the day will be written by many. The user has access to Gemini (4 at least) and to ChatGPT, older models included; others may be added.
  - Needs a person: follow `python/bots/zoo/README.md`, "Running a model cleanly": a fresh chat with memory and custom instructions off, `python3 python/bots/zoo/bundle.py <prompt> | pbcopy`, and the reply saved unchanged as `python/bots/zoo/gemini/<model>_<prompt>.py` (or `chatgpt/`, `other/`). Then `uv run python -m experiments.study.zoo`.
  - Done when: at least Gemini's bots are in `python/bots/zoo/` and in the zoo's results in `IDEAS.md`, with whether they behave unlike Claude's.
  - **2026-10-15, later: `market_maker` for the same three models** (results in the same `IDEAS.md` row). Gemini's is the strongest non-Claude bot (85.2k alone) and beats the committed template head to head under `all` on Squid Ink alone. Left: `mean_reversion` and `momentum` for the three, the older models, and the repair-turn record.
  - **2026-10-15: the first three are in** (`gemini/gemini-3-8-flash-high_baseline.py`, `chatgpt/gpt-5-6-luna_baseline.py`, `other/gpt-oss-120B_baseline.py`; `IDEAS.md`, "The LLM zoo"). They do behave unlike Claude's: both use the weighted mid, not the wall mid, and both chase Squid Ink's trend and lose on it; the template beats both head to head. Left: the other three prompts for the strongest Gemini and ChatGPT models, an older model of each (GPT-4o, Gemini 2.5), and whether a repair turn was used for these three (the README's table says "not recorded").
- [ ] **Zoo bots from the neuralwatt models (Kimi K3, GLM-5.3 Flash, DeepSeek V4.1 Flash).** The user has an account (2026-10-26); to be done later. Three more model families for the zoo, run by script rather than by hand.
  - How: `python/bots/zoo/local.py` already runs the zoo's protocol (SPEC.md and the prompt as the only message, one repair turn, everything logged to a `.json`) against an OpenAI-compatible API, but for a local llama-server: add `--model` (the provider's model name, which then names the bot) and an API key read from an environment variable, keep the default local behaviour, then run each model on `PROMPTS.md`'s prompts. Needs from the user: the API's base URL and the key in an environment variable (`.env` is gitignored; the key once committed was rotated on 2026-10-28, `docs/MANUAL_TODO.md`).
  - Bots go to `python/bots/zoo/other/` (never edited once used); `uv run python -m experiments.study.zoo --local` and `experiments.study.zoo_h2h` then score them. A Rust twin (`CLAUDE.md`) only for the bots worth keeping in the fast `--engine rust` runs.
  - Other uses talked over on 2026-10-26, not started: authoring the next disguised mock round out of sight of whoever plays it (`python/experiments/mock_round/README.md`, "Spent"); a cross-family audit of high-stakes files one at a time (the engine's matching and limits, the template's EXECUTION, the fee and delay code), every finding checked against the code; and a third clean-room agent on the day if the Technical Rules allow AI help and sending the data to a third party, tried out before 7 Nov.
  - Done when: each of the three models has at least the `baseline` and `market_maker` bots in `python/bots/zoo/other/`, scored in `IDEAS.md`'s "The LLM zoo" row with whether they behave unlike the Claude, Gemini and ChatGPT bots.

## The edge plan (2026-10-27)

Agreed with the user 2026-10-27 from two audit notes (`~/Documents/qminers_arena_audit/edge_ideas.md` and
`research_new_ideas.md`, outside the repo; their R-numbers below are the second note's ideas). Order: the filing,
then an independent generator (ABIDES) and its first results, the engine and template items one after another, the
day tools in parallel, and a summary last. Each new feature carries its result on the ABIDES days in its own commit.

- [ ] **LOBSTER's sample, one stock at level 5.** Real adverse selection: what `diagnose`'s "trades move the wall mid" note and negative markouts look like on a real book. Its samples are no longer a public download, so a person requests one (`docs/MANUAL_TODO.md`, "LOBSTER's sample files"); the converter is ready (`experiments.lobster_days`, 2026-10-27). Done when: that item is done.

### Deferred, and what would bring each back

Each idea has an untested row in `IDEAS.md`.
- **A Kalman fair mode** (a filter with gaps, a trend and an error bar): if the ABIDES days show the smoothed fair set by the Kalman formula falls short.
- **Tao's spoof detector made exact (R6's second half):** if probe 22 shows other teams' orders in the feed. Its inputs and the download's baseline are `arena.diagnose`'s `spoof_before` and `spoof_snap` (2026-11-02; `IDEAS.md`, "A spoof tell from the data").
- **A far quote on an empty side** (a template rule: quote a few lots far from the last fair while a side is empty): if probe 14 fills one, or `experiments.day.structure`'s fingerprints show trades outside the book on the download. No Prosperity replay can value it (`IDEAS.md`, "Quoting far away when one side of the book is empty").
- **Cross-product terms (R17a–c):** an informed signal on a leg moving the basket's level, a signal traded through the baskets' limits, two baskets' premium difference: if a round has baskets or named traders.
- **Reading the field (R18):** a taker-mix classifier, rival archetypes from visible orders, how cheaply the closing mark moves: if the market is shared and orders rest.
- **Options (R20):** strikes switched on by a running markout: if a round announces options. Realised against implied vol and long gamma are tested (2026-11-02; `IDEAS.md`, "Options: long gamma where realised vol beats implied": real but small next to the smile takes).
- **A curve-to-archetype reading of the leaderboard:** after the first leaderboard.
- **Ready Trader Go's data and simulator:** if the rules mention fees or order caps.
- **The neuralwatt zoo:** later, as the user said (its item under "Harder-round prep").

## Research

- [ ] **Add the conditional papers only if their topic shows up.** Free, but not read yet, and DTU's review says each helped little: Gatheral & Jacquier, SVI ([arXiv:1204.0646](https://arxiv.org/abs/1204.0646); DTU fitted a parabola and found full SVI added parameter risk); Avellaneda & Lee, statistical arbitrage ([NYU PDF](https://math.nyu.edu/~avellane/AvellanedaLeeStatArb071108.pdf); DTU shipped it only on the 50-product round); Fodra & Labadie, market making with a directional signal ([arXiv:1206.4810](https://arxiv.org/abs/1206.4810)); Lipton et al. ([arXiv:1312.0514](https://arxiv.org/abs/1312.0514); overlaps Gould & Bonart).
  - Skip: Leung & Li (DTU found its thresholds didn't beat a fixed z-score), and the rest of DTU's killed list (VPIN, PIN, Hawkes, copulas, ...) in `references/prosperity4-dtu-quant-lab/docs/literature_review.md`.
  - Done when: a round announces a product type that needs one of them and it has been downloaded, converted and indexed, or the Arena is over.

## Tooling

- [ ] **Refresh the sources and the wiki just before the event.** Run `references/clone.sh --update` (it rewrites the pins and prints each repo it moved), `python3 references/check_arena_site.py`, `python3 references/wiki/lint.py` and `uv run pytest`; read what changed, including the citations into each moved repo (the lint only checks that a cited line exists); commit `clone.sh`; ingest any new source (schema: `references/wiki/SCHEMA.md`).
  - **When:** 5 Nov, finished before 18:00, when the user's weekly Claude limit resets into the event's week. The checker already keeps short UI strings and lists the unused translation namespaces and the bundle's hash (both done 2026-10-30: `docs/TODO_DONE.md`, "Tooling"), so this re-check sees them with nothing to do first.
  - Done when: the lint reports no errors, the Arena site diff has been read and the answers written into `ON_THE_DAY.md`, and `references/wiki/log.md` has a `lint` entry dated that day.
- [ ] **A sampled queue model, only if needed.** `--queue prob` subtracts each cancel's expected share; Chung et al. found that "highly optimistic" against drawing where each cancel fell (binomially, seeded). Only worth building if the playground shows a product where our quotes join a level, since the template's own quote is usually alone at its price.
  - Done when: the playground has shown no such product (close it), or `--queue sample` exists with a test and its row in the README's queue table.
- [ ] **A loss stop that survives discarded calls, only if the Arena discards a failed call's state.** The template's `loss_stop` keeps cash as a tally of the fills it is shown; an exchange that throws away a failed or slow call's state loses that call's fills from it, and the stop can fire on nothing (the mock round's rules did this; `ON_THE_DAY.md`, "Where does state live between calls?"). Done when: the rules or probe 7 show calls can't be discarded (close it), or the stop's PnL comes from what the exchange reports in full, in STRATEGY, the Rust twin and a test.

## Strategy

None open.

## From the 2026-10-28 rehearsal

Both runs of the before/after rehearsal (`IDEAS.md`, "The kickoff prompts on a disguised round"; their logs in `python/experiments/mock_round/round2/results/`) hit these. All five are done (`docs/TODO_DONE.md`, the same heading).

## From the 2026-10-30 rehearsal

The engine-fit rehearsal (`IDEAS.md`, "The kickoff prompts on a disguised round"; logs in `python/experiments/mock_round/round3/results/`).

## Guidebook

- [ ] **A guidebook to the repo and the trading behind it** (the user, 2026-11-04): a field guide (30–40 pages) before the event, a guidebook (100–130 pages) after it, in PDF, EPUB and an audio edition. The proposal, its options and the research dossier: `docs/guidebook/PROPOSAL.md` and `docs/guidebook/research/`.
  - Decisions for the user (the proposal's §10): the field guide now or not; Quarto or LaTeX; the structure; who writes it; how far the audio goes.
  - Decided 2026-11-04 (the user): the field guide now, Quarto, the recommended structure, written by this session, the voice too. Built the same day: 10 chapters, the preface and the glossary, 41 pages, fact-checked by a second agent (`docs/guidebook/book/`, `FIELD_GUIDE_PLAN.md`); the full book's plan is `docs/guidebook/GUIDEBOOK_PLAN.md`.
  - Done when: the field guide is built and read, or the user decides against it; then the guidebook after the event, as a new item.

- [ ] **The guidebook, the full book** (the user, 2026-11-04: "start working on the full book"): `docs/guidebook/GUIDEBOOK_PLAN.md`, sixteen chapters and five appendices, about 45k words, built as the `guidebook` profile of `docs/guidebook/book/`. Begun with chapter 10 as the sample (`book/guidebook/10-backtest.qmd`).
  - 2026-11-04: every chapter not marked "(Arena)" written and fact-checked, part by part (129 pages; `GUIDEBOOK_PLAN.md`, "State").
  - Done when: every chapter not marked "(Arena)" is written and fact-checked, part by part; then, after the event, the Arena's parts from the round handovers, and the plan's checklist holds for all of them.

## Rehearsal and setup

- [ ] **Run a mock round before the event.** One teammate prepares data in a format the others haven't seen, with a stated bot API. The rest go from nothing to a validated submission in 5 hours, working through `ON_THE_DAY.md`.
  - Data: `uv run python -m arena.sim generate <folder> --days 3 --seed <a seed the others don't know>`, with `--spec` changes so the products aren't the presets. Include at least one product type the template isn't tuned for: `ROBOT_DISHES` (jumps that snap back), `KELP_FLOW` (one-sided takers; raise `--spec KELP_FLOW.noise.persistence=0.5` for flow that persists), or `HYDROGEL_PACK` (a level). Then rename the products and rewrite the files into a layout of the preparer's own, so the others have to write a loader. Keep the fundamental files back: they are the answer key.
  - Start the agents from `KICKOFF_PROMPT.md`, so the round tests it too, and end with a handover note (`ON_THE_DAY.md`, "The day: timeline and roles").
  - Postponed 2026-10-24 by the user ("mock not now"). With two of us, one prepares the data and the other runs the round alone, or an agent session prepares it in a folder neither of us opens and both run it.
  - Done when: the round is done, and whatever was slow or confusing is fixed in the tooling or the checklist.
  - **Done by agents 2026-10-26** (`python/experiments/mock_round/`, `IDEAS.md`, "The kickoff prompts on a disguised round"): both prompts went from nothing to a validated bot in under half an hour, and what tripped them is fixed. Left, if there's an afternoon: the same with a person at the keyboard, on new data (its README says how), to time the people, not the agents.
  - **Ready to play (2026-10-26):** a new round made by an agent out of our sight, unlike the first in products, layout, API and scoring, at `~/Documents/qminers_mock_round_2/` (outside the repo). Its `README.md` says how to play: copy `public/` into `data/arena/round1/`, the round-1 kickoff prompt, 5 hours, at most 3 "uploads" through `private/portal.py BOT --days public`, then one `--days hidden` run for the score. Don't open `private/` (the answer key) until it's played. Done when: one of us has played it and the times, the score and what was slow are written here.
- [ ] **Agree the roles and the sleep rota.** We are two (the user, 2026-10-24), both on site all night with no accommodation: no sleep is planned, and a nap on a table or the floor (sleeping bags and mats aren't allowed in the building) only in a round 2 or 3 that looks like the round before.
  - **Changed by the organisers' e-mail of 2 Nov** (`ON_THE_DAY.md`, "Known so far"): nobody may sleep in the building, so the nap on a table or the floor is out; but the on-site rule is dropped, so either of us, or both, may leave to rest. Decide where a nap happens (somewhere within a taxi or night bus of Troja), or plan none. `ON_THE_DAY.md`, "The day: timeline and roles", has the four roles in two pairs (A: driver and recorder; B: data and research), that nap rule and a handover note per round.
  - Done when: the two names are in that section.
- [ ] **Keep the repository private.** `literature_md/` holds Marker conversions of copyrighted books and papers, committed (the audit's L5, `docs/TODO_DONE.md`, "From the audit (2026-10-22)"). Nothing to do while it stays private.
  - The user may make it public after the event if we place well (2026-10-24). Before that: remove `literature_md/` from the whole history (`git filter-repo --path literature_md --invert-paths`, then a force-push; deleting it in a new commit leaves the text in the history) and keep it locally, gitignored; and decide about `references/algo_trade_arena_conversation.json` (the organisers' e-mail and a private chat) and `references/arena-site-snapshot.txt` (the Arena site's text).
  - Done when: the event is over and the repository is still private, or `literature_md/` was removed from the history before any change of visibility.
- [ ] **Check how Claude's usage windows behave, by 5 Nov.** `ON_THE_DAY.md`, "The day: timeline and roles", plans the day's 5-hour resets on two assumptions to check: the window starts at the first message, not rounded to the hour (send a one-line prompt at an odd time, e.g. 10:20, and read the reset time in Claude Code's `/usage`), and a window that expires unused leaves the next to start at the next message.
  - The weekly limit too: read when each account's week resets, and how much of it is left for 7–8 Nov.
    - **The user's account** (2026-10-26): resets Thursdays at 18:00 Prague time (29 Oct, then 5 Nov), so its event week runs 5 Nov 18:00 to 12 Nov 18:00 and holds the whole event. Everything heavy (the refresh, a dry run) is done before 5 Nov 18:00; after it, only what the day needs (`git pull`, the tests). Check on 5 Nov just after 18:00 that the reset happened.
    - The teammate's account: not known yet.
  - The teammate: whether they use Claude, on which plan, and whether they take the 07:30 first prompt.
  - Done when: both assumptions are checked (the plan's times corrected if either fails), each account's weekly reset and headroom are written into that section, and the teammate's choice is in it.
- [ ] **Set up every teammate's laptop by 31 Oct.** Each needs `uv sync`, `references/clone.sh` (2 GB, so not on the venue wifi), cargo for `--engine rust` (`brew install rust`), a passing `uv run pytest` with no "needs cargo" or "needs references" skips (without either, the run still passes but skips every parity check), and the converted literature. Agree who takes which first-hour track in `ON_THE_DAY.md`, and who submits.
  - Done when: everyone has run the template backtest on their own machine, on both engines (`--engine rust`).
