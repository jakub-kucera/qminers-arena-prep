# Prep to-do

Work left before the Arena (7–8 Nov 2026). Things to find out at the event itself are in
[`ON_THE_DAY.md`](ON_THE_DAY.md). Things only a person can obtain (organiser documents, blocked web pages, books)
are in [`MANUAL_TODO.md`](MANUAL_TODO.md). When an item's "done when" holds, tick it and move it, with
its sub-bullets, to [`TODO_DONE.md`](TODO_DONE.md) under the same heading; add new items as they come up.

## Decisions

Choices only the user can make, each with the options, the evidence and a recommendation.

- [ ] **A second zoo spec with what the Arena's site shows?** Raised by the user 2026-10-26: given the site's new facts, would the models write different bots?
  - Options: (a) keep `python/bots/zoo/SPEC.md` (Prosperity's rules) for every prep-time zoo bot, and put the Arena's real rules into the round's spec on the day (`ON_THE_DAY.md`, "The round's zoo"); (b) add a second spec now, beside it (a used spec is never edited), with our guesses at the Arena's scoring: the end position valued at the touch, a fine per lot over the limit instead of Prosperity's rejection, maybe one product. Run the same models and prompts through it and score the bots under `--mark touch --limit-penalty` (`experiments.zoo` would need those two options).
  - Evidence: of the site's facts, only two would reach a bot's code: the price the end position is valued at (`markPrice`) and what a breach costs (`breachPenalty`). Neither one's value is known (`ON_THE_DAY.md`, "Known so far"). The rest (the submission cap, one evaluation at a time, the leaderboard, the metrics' names) is portal mechanics that changes how a team works, not what the model writes. The other teams' models will get the Technical Rules on the day, not the site's code, so a spec built on our guesses can make the zoo less like the field. What (b) could show: whether the template's lead over the zoo depends on those two rules. Cost: the user's time for 2 models × 4 prompts × 2 samples, and the two options in `experiments.zoo`.
  - Recommendation: (a). Spend the model time on the open Gemini and ChatGPT prompts with the current spec ("Zoo bots from other LLM providers" below: `mean_reversion` and `momentum`, the older models), which keeps them comparable with the 59 bots so far. The day's spec gets the real rules.

## Harder-round prep

Chosen 2026-10-14 from `references/wiki/concepts/harder-rounds.md` ("Proposals"), in this order.

- [ ] **(a, part 2) Zoo bots from other LLM providers.** The first zoo is all Claude, so it shares one model's habits; the field on the day will be written by many. The user has access to Gemini (4 at least) and to ChatGPT, older models included; others may be added.
  - Needs a person: follow `python/bots/zoo/README.md`, "Running a model cleanly": a fresh chat with memory and custom instructions off, `python3 python/bots/zoo/bundle.py <prompt> | pbcopy`, and the reply saved unchanged as `python/bots/zoo/gemini/<model>_<prompt>.py` (or `chatgpt/`, `other/`). Then `uv run python -m experiments.zoo`.
  - Done when: at least Gemini's bots are in `python/bots/zoo/` and in the zoo's results in `IDEAS.md`, with whether they behave unlike Claude's.
  - **2026-10-15, later: `market_maker` for the same three models** (results in the same `IDEAS.md` row). Gemini's is the strongest non-Claude bot (85.2k alone) and beats the committed template head to head under `all` on Squid Ink alone. Left: `mean_reversion` and `momentum` for the three, the older models, and the repair-turn record.
  - **2026-10-15: the first three are in** (`gemini/gemini-3-8-flash-high_baseline.py`, `chatgpt/gpt-5-6-luna_baseline.py`, `other/gpt-oss-120B_baseline.py`; `IDEAS.md`, "The LLM zoo"). They do behave unlike Claude's: both use the weighted mid, not the wall mid, and both chase Squid Ink's trend and lose on it; the template beats both head to head. Left: the other three prompts for the strongest Gemini and ChatGPT models, an older model of each (GPT-4o, Gemini 2.5), and whether a repair turn was used for these three (the README's table says "not recorded").
## Research

- [ ] **Add the conditional papers only if their topic shows up.** Free, but not read yet, and DTU's review says each helped little: Gatheral & Jacquier, SVI ([arXiv:1204.0646](https://arxiv.org/abs/1204.0646); DTU fitted a parabola and found full SVI added parameter risk); Avellaneda & Lee, statistical arbitrage ([NYU PDF](https://math.nyu.edu/~avellane/AvellanedaLeeStatArb071108.pdf); DTU shipped it only on the 50-product round); Fodra & Labadie, market making with a directional signal ([arXiv:1206.4810](https://arxiv.org/abs/1206.4810)); Lipton et al. ([arXiv:1312.0514](https://arxiv.org/abs/1312.0514); overlaps Gould & Bonart).
  - Skip: Leung & Li (DTU found its thresholds didn't beat a fixed z-score), and the rest of DTU's killed list (VPIN, PIN, Hawkes, copulas, ...) in `references/prosperity4-dtu-quant-lab/docs/literature_review.md`.
  - Done when: a round announces a product type that needs one of them and it has been downloaded, converted and indexed, or the Arena is over.
## Tooling

- [ ] **Refresh the sources and the wiki just before the event.** Run `references/clone.sh --update` (it rewrites the pins and prints each repo it moved), `python3 references/check_arena_site.py`, `python3 references/wiki/lint.py` and `uv run pytest`; read what changed, including the citations into each moved repo (the lint only checks that a cited line exists); commit `clone.sh`; ingest any new source (schema: `references/wiki/SCHEMA.md`).
  - **First** (about 5 Nov): "Make `check_arena_site.py` keep short UI strings" below, so this re-check sees the short strings and the unused translation namespaces too.
  - Done when: the lint reports no errors, the Arena site diff has been read and the answers written into `ON_THE_DAY.md`, and `references/wiki/log.md` has a `lint` entry dated that day.
- [ ] **A sampled queue model, only if needed.** `--queue prob` subtracts each cancel's expected share; Chung et al. found that "highly optimistic" against drawing where each cancel fell (binomially, seeded). Only worth building if the playground shows a product where our quotes join a level, since the template's own quote is usually alone at its price.
  - Done when: the playground has shown no such product (close it), or `--queue sample` exists with a test and its row in the README's queue table.
- [ ] **Make `check_arena_site.py` keep short UI strings.** It drops strings under 6 characters, so it missed the submissions table's "PnL" column (and "Tie", "Final", "Team"), and it can't tell which strings a page uses: the 10/20/30/40% weights sit in a translation namespace no component reads (`ON_THE_DAY.md`, "Known so far", 2026-10-25).
  - **When:** about 5 Nov, just before the re-check in "Refresh the sources and the wiki just before the event" (agreed with the user 2026-10-26), so the snapshot it re-saves is the one the event starts from.
  - Done when: strings at a value position of the translation objects (`key:"…"`) are kept whatever their length, the checker lists the namespaces no code references, the snapshot is re-saved, and the wiki's citations into it are re-mapped.

## Strategy

None open.

## Rehearsal and setup

- [ ] **Run a mock round before the event.** One teammate prepares data in a format the others haven't seen, with a stated bot API. The rest go from nothing to a validated submission in 5 hours, working through `ON_THE_DAY.md`.
  - Data: `uv run python -m arena.sim generate <folder> --days 3 --seed <a seed the others don't know>`, with `--spec` changes so the products aren't the presets. Include at least one product type the template isn't tuned for: `ROBOT_DISHES` (jumps that snap back), `KELP_FLOW` (one-sided takers; raise `--spec KELP_FLOW.noise.persistence=0.5` for flow that persists), or `HYDROGEL_PACK` (a level). Then rename the products and rewrite the files into a layout of the preparer's own, so the others have to write a loader. Keep the fundamental files back: they are the answer key.
  - Start the agent from the kickoff prompt (next item), so the round tests it too, and end with a handover note (`ON_THE_DAY.md`, "The day: timeline and roles").
  - Postponed 2026-10-24 by the user ("mock not now"). With two of us, one prepares the data and the other runs the round alone, or an agent session prepares it in a folder neither of us opens and both run it.
  - Done when: the round is done, and whatever was slow or confusing is fixed in the tooling or the checklist.
- [ ] **Write the competition day's kickoff prompt.** One prompt to paste into a fresh agent session at the start of each round, with the round's data or the real assignment attached, so the agent starts from the repo's own process instead of improvising.
  - It says:
    - where the inputs are: placeholders for the download's folder, the assignment or Technical Rules text, and the round number;
    - what to read first: `CLAUDE.md`, `ON_THE_DAY.md` (the format swap step by step, then the first-hour tracks), and `references/wiki/concepts/reading-the-data-on-day-one.md`;
    - the order of work: the rules and API first, writing the answers into `ON_THE_DAY.md`; then `python/arena/formats/qminers.py` modelled on `drill.py`; then `arena.diagnose`; then the template's ADAPTER and PARAMS; then `arena.validate`;
    - the time budget: a validated, submittable bot well before the round's 5 hours end, improved afterwards, and the times to check in with the user;
    - what not to do without asking: anything the rules may forbid, and `ON_THE_DAY.md`'s data-source search, which needs the user's approval and a budget;
    - what to hand back: the bot file, the `arena.validate` output, and what's still untested.
  - A variant for rounds 2–4 starts from the previous round's bot and the leaderboard, and asks first what changed in the data and rules.
  - Done when: the prompt is committed, the mock round's agent started from it, and whatever it got wrong there is fixed in it.
  - **Drafted 2026-10-23:** `KICKOFF_PROMPT.md`, linked from `ON_THE_DAY.md`'s "Splitting the first hour". It also holds a prompt without the repository, for a teammate's clean-room agent that sees only the organisers' files (a `Priors` block distils our Prosperity results, deleted for a fully clean run). Left: the mock round, where one teammate runs each and the two bots are compared.
  - **Updated 2026-10-26 for the portal facts of 25–26 Oct:** the submission deadline rather than the round's end, one evaluation at a time (the last upload starts at least twice the first evaluation's time before the deadline), the file-size cap, the backtest's `--metrics`, `--mark` and `--limit-penalty` fitted from the first upload, and a round with a single product.
- [ ] **Agree the roles and the sleep rota.** We are two (the user, 2026-10-24), both on site all night with no accommodation: no sleep is planned, and a nap on a table or the floor (sleeping bags and mats aren't allowed in the building) only in a round 2 or 3 that looks like the round before. `ON_THE_DAY.md`, "The day: timeline and roles", has the four roles in two pairs (A: driver and recorder; B: data and research), that nap rule and a handover note per round.
  - Done when: the two names are in that section.
- [ ] **Keep the repository private.** `literature_md/` holds Marker conversions of copyrighted books and papers, committed (the audit's L5, `TODO_DONE.md`, "From the audit (2026-10-22)"). Nothing to do while it stays private.
  - The user may make it public after the event if we place well (2026-10-24). Before that: remove `literature_md/` from the whole history (`git filter-repo --path literature_md --invert-paths`, then a force-push; deleting it in a new commit leaves the text in the history) and keep it locally, gitignored; and decide about `references/algo_trade_arena_conversation.json` (the organisers' e-mail and a private chat) and `references/arena-site-snapshot.txt` (the Arena site's text).
  - Done when: the event is over and the repository is still private, or `literature_md/` was removed from the history before any change of visibility.
- [ ] **Set up every teammate's laptop by 31 Oct.** Each needs `uv sync`, `references/clone.sh` (2 GB, so not on the venue wifi), cargo for `--engine rust` (`brew install rust`), a passing `uv run pytest` with no "needs cargo" or "needs references" skips (without either, the run still passes but skips every parity check), and the converted literature. Agree who takes which first-hour track in `ON_THE_DAY.md`, and who submits.
  - Done when: everyone has run the template backtest on their own machine, on both engines (`--engine rust`).
