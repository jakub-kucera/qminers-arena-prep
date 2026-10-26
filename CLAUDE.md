# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Prep tooling for the Qminers Algo Trade Arena, a 24-hour in-person hackathon (7–8 Nov 2026). It
has four 5-hour rounds, and teams submit a Python bot file at the end of each one. The real API
won't be known until the event, so everything here runs on **IMC Prosperity data and its bot
format as a stand-in**. Keep competition-specific code isolated so it can be swapped quickly on
the day (see "Architecture" below, and `RUNBOOK.md` for the day itself).

## Layout

The Python code is in `python/` (`arena/`, `bots/`, `experiments/`, `tests/`, `notebooks/`); `uv sync` installs it editable (`pyproject.toml`, `module-root = "python"`), so every command below runs from the repository's root. `rust/` holds the Rust twins, laid out as `python/` is. The rest of the root is docs (`*.md`: `ARCHITECTURE.md` for how the code fits together, `README.md` the guide, `RUNBOOK.md`, `ON_THE_DAY.md`, `TODO.md`, `IDEAS.md`), `references/` and `literature_md/`.

## Commands

```sh
references/clone.sh                 # fetch the reference repos + Prosperity data at their pinned commits (gitignored, ~2 GB)
uv sync                             # Python 3.12; dev group = pytest, pandas, matplotlib
uv run pytest                       # all tests (~110 s; python/tests/test_rust.py's parity checks are most of it)
uv run pytest python/tests/test_engine.py::test_trade_matching_at_the_same_price   # one test

uv run python -m arena.diagnose 1 --data p4                       # per-product market diagnostics, no bot needed
uv run python -m arena.backtest python/bots/template.py 1                # Prosperity 3 round 1, every day
uv run python -m arena.backtest python/bots/template.py 1-0 --data p2    # Prosperity 2, round 1 day 0
uv run python -m arena.backtest python/bots/template.py 1 --set PARAMS.KELP.make_edge=2 --out results/
uv run python -m arena.backtest python/bots/template.py 1 --resting --vs python/bots/template.py   # orders rest; a rival copy shares the market
uv run python -m arena.backtest python/bots/template.py 1 --engine rust   # the same report and CSVs, on rust/ (compare, stress, sim and the experiments take it too)
uv run python -m arena.backtest python/bots/template.py 1 --mark touch --limit-penalty 5   # positions valued at the touch; a breach charged per lot a tick, not rejected
uv run python -m arena.backtest python/bots/template.py 1 --metrics      # also the figures the Arena's portal shows on a submission, to compare with it
uv run python -m arena.validate python/bots/template.py 1                # pre-submission checks, exit 1 on FAIL
uv run python -m arena.validate python/bots/template.py 1 --max-size 100KB   # ...and the dashboard's file-size cap
uv run python -m arena.compact python/bots/template.py submit/template.py   # over the cap: the same code without comments or docstrings (~26 KB)
uv run python -m arena.grid python/bots/template.py 1 --grid PARAMS.KELP.make_edge=0..3 --modes all,worse --out results/grid.csv
uv run python -m arena.grid python/bots/template.py 1 --grid PARAMS.KELP.make_edge=0..7 --grid PARAMS.KELP.take_edge=0..7 --modes all,worse --screen 0.25   # big grids: screen on the first day, the best quarter on all
uv run python -m arena.grid python/bots/template.py 1 --grid PARAMS.KELP.make_edge=0..15 --grid PARAMS.KELP.take_edge=0..15 --grid PARAMS.KELP.skew=0..9 --sample 1000 --halving 0.5 --modes all,worse --engine rust   # huge grids: a random 1,000 cells, halved day by day
uv run python -m arena.grid python/bots/template.py 1 --grid PARAMS.KELP.make_edge=0..15 --grid PARAMS.KELP.take_edge=0..15 --engine rust   # the same output, its backtests on rust/ (a bot with a Rust twin)
uv run python -m arena.grid python/bots/template.py 1 --grid PARAMS.KELP.make_edge=0.5,1,2 --modes all,worse --scenario rest:resting,queue=prob --scenario war:vs=python/bots/template.py@PARAMS.KELP.make_edge=0 --engine rust   # fill-model scenarios, each with its own settings and rivals
uv run python -m arena.compare python/bots/template.py 1 --bot python/bots/zoo/claude/*.py "python/bots/template.py@PARAMS.KELP.make_edge=1" --modes all,worse   # several bots or variants against a baseline
uv run python -m arena.analysis results/                          # PNGs to results/plots/ + fill/markout tables
uv run python -m arena.stress python/bots/template.py 1                    # the bot on perturbed days (trend, shift, spike, vol x2, no wall)
uv run python -m arena.sim generate data/sim --days 5              # simulated days in the Prosperity layout (--data data/sim)
uv run python -m arena.sim run python/bots/template.py --days 5           # the bot inside the agent market, against replaying the same days
uv run python -m arena.sim run python/bots/template.py --products KELP,RAINFOREST_RESIN,HYDROGEL_PACK --regime trend_up   # a mid-day regime change, in a market that reacts
uv run python -m arena.sim run python/bots/template.py --days 20 --engine rust   # the same output, the market in rust/src/arena/sim.rs (generate takes it too)
uv run python -m arena.backtest python/bots/probe.py 1 --print --no-strict   # the probe bot: one PROBE line per first-hour probe
uv run python -m experiments.format_drill data/drill               # drill-format data, then any tool with --format drill --data data/drill/drill
uv run python -m experiments.format_drill --sync                   # copy the template's DEFAULTS, STRATEGY and EXECUTION into python/bots/drill/template.py
uv run python -m arena.analysis --grid results/grid.csv           # grid heatmaps
uv run --group analysis jupyter lab python/notebooks/analysis.ipynb      # the analysis group adds Jupyter
uv run python -m experiments.p4_levels                            # a one-off study; its numbers are in IDEAS.md
uv run python -m experiments.glft_skew --data data/arena --days 1 --format qminers --bot python/bots/qminers/template.py   # a re-test on the day's data (python/experiments/README.md lists which take it)
uv run python -m experiments.zoo                                  # scores every LLM-written bot in python/bots/zoo/ against the template (--local: local models in the field too)
uv run python -m experiments.zoo_h2h                              # the template against each zoo bot, per product, under all and worse
uv run python -m experiments.adversaries                          # the template against a trapper, spoofers and a sniper (python/bots/rivals/), --resting
uv run python -m experiments.rival_field --engine rust            # candidate settings against fields of rival archetypes (mm at three edges, taker, sniper, spoofer, trapper, a copy)
uv run python -m experiments.leaderboard_curves --engine rust     # can the leaderboard's PnL curves tell a shared market? On the day: --read FILE --team NAME
uv run python -m experiments.quote_inside --engine rust           # make_inside (quotes nearer fair than one tick inside the book) against rivals nearer fair, and alone
uv run python -m experiments.undercut                             # the template against a copy of itself at make_edge 0 (Wang et al.), per tick and --resting
uv run python -m experiments.quote_size                           # make_size caps against rivals: a copy, the trapper, spoofer and sniper
uv run python -m experiments.p3_smile                             # P3's volcanic vouchers: the smile by held-out days, its residual, and the template's smile fair traded on it (~3 min)
uv run python -m experiments.imbalance                            # does the best-level imbalance predict the mid / the wall mid, per product and day
uv run python -m experiments.sim_regimes                          # the template's stops and guards under each arena.sim regime change
uv run python -m experiments.snooping_tests                       # Hansen's SPA and Romano-Wolf's StepM next to the grid's DSR, on two grids and null controls
uv run python -m experiments.selection_rules                      # ten ways of picking a grid cell, scored on days the grid never saw; part 2 across ten fill-model scenarios
uv run python -m experiments.selection_rules_sim                  # the same rules on fresh arena.sim days, tuned on 3 and scored on 20
uv run python -m experiments.rust_bench                           # the Rust port (rust/, needs cargo) against ours: every twin's parity, then speed
uv run python -m experiments.rust_bench --parity-only --record    # after changing a twin (rust/twins.json): check it, then record its hash
```

- **Day specs:** `ROUND` (every day in the round) or `ROUND-DAY`, e.g. `1`, `1-0`, `1--1`.
- **`--data` aliases:** `p2` and `p3` point into `references/prosperity{2,3}-backtester-jmerle/.../resources`, `p4` into `references/prosperity4-backtester/prosperity4bt/resources` (rounds 0–5).
- **Tests without the data:** `python/tests/test_parity.py` skips if `references/` hasn't been cloned. All other tests use a tiny CSV fixture from `python/tests/conftest.py`.
- **Notebook check:** `uv run --group analysis jupyter nbconvert --to notebook --execute python/notebooks/analysis.ipynb --output-dir <scratch>` runs it end to end. Commit the notebook without outputs.
- **No linter or formatter is configured.**

## Architecture

`ARCHITECTURE.md` describes every part: read its section before changing the engine, a format, bot
loading, the grid, the simulator, the Rust port, the analysis or the template. The rules that keep
the parts consistent:
- **Standard library only,** except `python/arena/analysis.py`, the one module that imports pandas and matplotlib.
- **The engine knows no format.** A format plug-in (`python/arena/formats/`) provides `PROVIDED_MODULES`, `resolve_data_dir`, `load_days`, `load_bot` and `check_source`, is registered in `FORMATS`, and sets `RESTING = True` if its orders rest. On the day, copy `drill.py`.
- **Change these together:** `report.write_csvs`' columns and `python/arena/analysis.py`; `arena.diagnose`'s note thresholds and `references/wiki/concepts/reading-the-data-on-day-one.md`; the template's DEFAULTS, STRATEGY or EXECUTION and `python/bots/drill/template.py` (`uv run python -m experiments.format_drill --sync`; `python/tests/test_drill.py` fails until you do).
- **Parity with prosperity3bt is pinned:** a change to matching, limits or marking must keep `python/tests/test_parity.py` passing, and its fixture `python/tests/fixtures/parity_bot.py` is frozen. Resting-mode code stays in its own branch of `run_day`; parity covers only the default mode.
- **Rust twins:** a change to a twin's Python code goes into its Rust file too, then `uv run python -m experiments.rust_bench --parity-only --record` (`rust/twins.json`, `rust/README.md`). A new zoo bot needs its own twin.
- **Bot files** (`python/bots/`): one self-contained file, standard library only, all cross-tick state in `traderData`. New strategy logic goes in STRATEGY, order management in EXECUTION, format code in ADAPTER. Never edit a zoo bot or a prompt once used.
- **Charts:** `THEMES`' palettes were checked with the dataviz skill's validator; keep categorical colors in slot order.

## Repo conventions

- **`TODO.md`:** prep work left before the event, each item with a "done when". When that holds, tick the item and move it, with its sub-bullets, to `TODO_DONE.md` under the same heading (cite it there as `TODO_DONE.md`, "<title>"); add new ones as they come up.
- **`RUNBOOK.md`:** one page of the day's commands and checkpoints, each line naming the `ON_THE_DAY.md` section behind it. Keep it to a page: when a command or a time changes, change it here and in `ON_THE_DAY.md` together.
- **`ON_THE_DAY.md`:** the checklist of what to find out about the real Arena. For each item it gives our current assumption and what to change if the Arena differs, and it ends with playground probes. When a session learns an answer, write it in under that item with its source. When a session adds an assumption about the real format, add an item.
- **`IDEAS.md`:** every strategy idea tested on Prosperity data, with its result (date, data, command, numbers), and the ideas not yet tested. Results there are priors for the Arena, not verdicts: never remove an idea because it failed on Prosperity data; mark it `dropped here`, so it is re-tested on the day. Record every new test result in its row.
- **`MANUAL_TODO.md`:** things only a person can obtain (organiser documents, web pages the agent's fetch tool is blocked from, books). Each item says where to save the file and what "done" means. When the user hands something over, ingest it as `references/wiki/SCHEMA.md` describes and tick the item.
- **Nothing stays only in the chat.** Before ending a task, file what it turned up, in the same commit as the work:
  - prep work or a follow-up → `TODO.md`, with a "done when"
  - a new idea or a test result → `IDEAS.md`, with what to re-test on the day
  - a question about the real Arena, or advice for the day → `ON_THE_DAY.md`
  - something only a person can obtain → `MANUAL_TODO.md`
  - a choice only the user can make → `TODO.md`, "Decisions", with the options, the evidence and a recommendation

  When asked what to do next, start from the open items in `TODO.md` and the untested rows of `IDEAS.md`.
- **Results reproduce from the repo.** The command given for a result in `IDEAS.md` or the wiki runs from a clean checkout: a CLI with `--set`, or a script committed under `python/experiments/` along with the result. A scratchpad path is not a command.

- **`references/`:** third-party clones listed in `references/clone.sh`, each pinned to a commit (`python/tests/test_references.py` checks). Read them for ideas, but don't edit or import from them. Move a pin only with `clone.sh --update`, then the lint and the tests.
  - `references/algotrade2026-pitfa19/` contains its own `CLAUDE.md` and `AGENTS.md`. They describe that repo, not this one, so don't follow them.
  - `references/README.md` summarises what each repo is useful for.
  - **`references/wiki/` is the way into the clones and the literature.** It follows Karpathy's LLM-wiki pattern: read `references/wiki/index.md` first, then a concept page, then the source page, and only then the raw file at the cited line. Pages cite code as `path:line`, say what is a team's claim and what was checked, and say what was not read. `references/wiki/SCHEMA.md` has the conventions and the ingest / query / lint workflows. After editing the wiki run `python3 references/wiki/lint.py`; log changes in `references/wiki/log.md`.
  - **Pages cite our code by line** (`python/bots/template.py` most, and `python/arena/*.py`), and the lint only checks that the line exists (and that a range starts a definition). After an edit shifts a cited file's lines, re-map those citations (`grep -rn 'template\.py:[0-9]' references/wiki`, likewise for the file you changed).
- **`literature_md/`:** market-microstructure papers and books, converted from `literature_raw/*.pdf` to markdown by `literature_md/convert.sh` (Marker). Committed (the source PDFs in `literature_raw/` are gitignored); `literature_md/README.md` indexes the documents. For the theory behind a strategy (market making, order-book imbalance, micro-price, price impact), go through the wiki first: the Literature section of `references/wiki/index.md`, then the concept page, and only then the raw text at the cited line.
  - **Verify formulas against the PDF.** Marker's equations are LaTeX but OCR-based, so they can contain slips (e.g. `S_{τ1}, S_{τ1}` where the paper has `I_{τ1}, S_{τ1}`). Before implementing any formula from `literature_md/`, check it against the original PDF page (`python3 literature_md/pdfpage.py <slug> <line>` finds the page and prints its text), and don't trust a formula that disagrees with the surrounding text or with its own derivation.
- **Commits:** commit each finished step on its own, with the docs it changed, once the tests (and the wiki lint, if the wiki changed) pass. A request with several steps gets one commit per step. Author commits as the user (Jakub) only. Never put a `Co-Authored-By: Claude …` trailer, or any other Claude attribution, in commit messages or PR descriptions.
