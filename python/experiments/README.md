# Experiments

One-off studies whose results are in `IDEAS.md` (the row each feeds is named below). Each runs from
the repository's root as `uv run python -m experiments.<name>`. With no options it reproduces the
numbers `IDEAS.md` quotes, on the Prosperity data in `references/`.

**On the day:** the experiments in the first table take the Arena's download in place of their
built-in Prosperity datasets:
- `--data DIR --days ...` picks the data and days, `--format` its plug-in, `--bot` the template
  written for it, and `--products` the products to study (`arena.cli.add_dataset_arguments`);
- the Prosperity-specific pieces get their own options: `--basket`, `--underlying`, `--prefix`,
  `--expiry`, `--war`, `--trade`, and selection_rules' `--train`, `--test` and `--grid`;
- `python/tests/test_experiments.py` runs each on drill-format data, as the Arena's plug-in will
  present its own.

The second table holds the rest: what each studies, and why it doesn't take the day's data.

Every experiment that backtests takes `--engine rust` (and `--allow-stale`), with the same output.

## Re-run on the Arena's data

`ON_THE_DAY.md` or `IDEAS.md`'s "Re-test on the Arena" column names each of these.

| Experiment | What it answers | `IDEAS.md` row | On the day |
|---|---|---|---|
| `adversaries` | What a trapper, a spoofer and a sniper (`python/bots/rivals/`) cost the template, `--resting` | "Adversarial rivals" | `--data D --days ...`. The variants become the bot as is and every product on `sized_mid` or `wall_mid`; the rivals get the data's limits. The rivals are Prosperity bots, so another format runs only the template copy |
| `undercut` | What a copy at `make_edge` 0 costs, per tick and `--resting`; the price war on a fixed fair | "Against a rival that undercuts us" | `--data D --days ... [--war PRODUCT]` for the war table |
| `rival_field` | Candidate settings against fields of rival archetypes (`mm` at three edges, the taker, sniper, spoofer, trapper, a copy), per tick and resting: the payoff matrix, the best reply per field, the max-min and mean choices | "Our settings against a field of rival archetypes" | `--data D --days ... [--products ...] --candidate PARAMS.P.KEY=V1,V2` (repeatable); Prosperity format only until the archetypes' ADAPTERs are rewritten |
| `leaderboard_curves` | From the leaderboard's PnL curves, whether the teams traded on data of their own, alone on the same data, or in one market; calibrated on simulated fields whose answer is known | "Reading the leaderboard's curves" | `--read FILE [--team NAME]`: the leaderboard's data, saved after each deadline |
| `mock_round/` | The agent-only mock round: a disguised round's generator, the portal that scores a bot on its hidden days, its answer key, and the two runs' bots (its README) | "The kickoff prompts on a disguised round" | Spent: a new rehearsal needs new seeds and layout |
| `quote_size` | `make_size` caps against copies and the rivals | "Using less than the full position limit" | `--data D --days ...`; rivals as in `adversaries` |
| `quote_markouts` | The template's passive fills by state (spread, place, imbalance, momentum, inventory), against the wall mid | "Passive fills' value by state" | `--data D --days ...`; spread bins in each product's ticks. Also on the playground's own fills (probe 18) |
| `glft_skew` | σ, A and k per product, and the template's `skew` from GLFT's closed form for each γ | "The skew coefficient from GLFT's closed form" | `--data D --days ...`, every product the bot trades there by default, in its ticks |
| `imbalance` | Does the best-level imbalance ρ predict the mid or the wall mid (Gould & Bonart), and the micro-price candidates | "Book imbalance `ρ` and the micro-price" | `--data D --days ... [--products ...]`; no bot |
| `counterparties` | Whose trades lead the price, and the template's `copy` mode chosen on held-out days | "Following informed counterparties" | `--data D --days ...` if the trades name traders; part 3 (Olivia) is P3's only |
| `baskets` | A basket's spread traded with the level settings, by held-out days | "Trading a basket's spread" | `--data D --days ... --basket NAME=LEG:W,LEG:W` (repeatable; weights −1 for a fixed-sum family); limits and `clear_edge` from the data |
| `p3_smile` | Is there a volatility smile to trade; `smile_fair` by held-out days | "Options: trading implied-volatility deviations from a fitted smile" | `--data D --days ... --underlying U --prefix P --expiry DAY=N,...` |
| `p4_vouchers` | Is each option a fixed function of its underlying: implied vol per strike and day | "What the P4 vouchers are" | `DAYS --data D --underlying U --prefix P --expiry DAY=N,... [--format F]` |
| `p4_vouchers_template` | The underlying's level bet with its options following, by held-out days | "What the P4 vouchers are" | `--data D --days ... --underlying U --prefix P` |
| `p4_level_template` | The level mode by held-out days, and other ways to set the level | "Trading toward a known level" | `--data D --days ... --products A,B` (those `arena.diagnose` notes as reverting to a level) |
| `p4_jumps` | Jumps that snap back, per product and day, and the `jump` mode on every product | "Fading jumps that snap back" | `--data D --days ... --jump-min J [--format F] [--trade]` (`--trade` runs part 2 on any data; `--jump-min` in the data's price unit) |
| `selection_rules` | Which way of picking a grid cell holds up on unseen days; part 2, picking across ten fill-model scenarios (`--part 2`) | "Selection rules on unseen days", "Choosing a cell by its worst case over fill-model scenarios" | `--data D --train ... --test ... --products ... --grid PARAM=V1,V2 --grid ...` once two rounds exist |

## The rest

| Experiment | What it answers | `IDEAS.md` row | Why not on the day's data |
|---|---|---|---|
| `cross_product_timing` | Do a basket's legs lead it, and do one product's trades lead another | "Legs leading the basket" | Data only, Prosperity's baskets hard-coded; read it if the Arena has baskets |
| `format_drill` | Makes drill-format data (and `--sync` copies the template into the drill bot) | — | A tool, not a study |
| `kelp_drift` | Why the template holds Kelp long: each day mirrored (the takers' flow or a bias), Harris's test, and `skew` 0–3 | "`skew` against Kelp's long position" | P3 round 1 hard-coded; on the day, `arena.diagnose`'s buy share and Harris's test on a `--out` timeline answer the same for any product |
| `p4_levels` | How much of the teams' P4 PnL survives without their hard-coded levels | "Trading toward a known level", "What the P4 vouchers are" | Runs other teams' Prosperity bots |
| `quote_inside` | `make_inside` (quoting nearer fair than one tick inside the book) against rivals that quote nearer fair, per tick and resting, and its cost alone | "Quoting nearer fair than one tick inside the book, against rivals that do" | Runs the Prosperity zoo on P3; on the day grid `PARAMS.<P>.make_inside=1,2,3,None` with `arena.grid --scenario` and a `vs=` rival |
| `rust_bench` | Every Rust twin against its Python file, then the speed | — | The parity check (`--parity-only --record`) |
| `selection_rules_sim` | The selection rules on fresh `arena.sim` days; part 2 across the scenarios | "Selection rules on unseen days", "Choosing a cell by its worst case over fill-model scenarios" | Simulated days; calibrate `arena.sim` to the download first (`--spec`) |
| `sim_regimes` | The template's stops and guards when `arena.sim`'s regime changes mid-day | "Regime changes in a market that reacts" | Simulated days |
| `snooping_null_rates` | How often SPA, StepM and the pick name a cell on null grids, with the `worse` and holdout gates (the second audit's A4), each resample studentized by its own omega and by the data's, and their power on one planted cell | "Bootstrap tests of the best cell" | A check of the statistics, on simulated gains |
| `snooping_tests` | SPA and StepM next to the DSR on two grids and null controls | "Bootstrap tests of the best cell" | A check of the statistics; `arena.grid` runs them on any data |
| `stops_held_out` | Do the loss stops hold on days they weren't sized on | "A loss stop per product" | `arena.stress` on the day's data does the same check |
| `trade_clustering` | Do the market trades cluster in time (Hawkes) | "Quoting from clustered order flow" | Data only; untested idea |
| `zoo` | Every zoo bot alone, against the template, in `arena.sim` and in one field | "The LLM zoo" | The day's zoo is written for the Arena's API: score it with `arena.compare` (`ON_THE_DAY.md`, "The round's zoo") |
| `zoo_h2h` | The template against each zoo bot, per product and fill mode | "Why the zoo beat the template head to head" | As `zoo` |
