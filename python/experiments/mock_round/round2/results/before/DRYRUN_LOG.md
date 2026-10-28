# Dry run log: round 1 of a disguised Arena (the Halden Exchange), 2026-10-28

One agent alone, all tracks. The round opened 15:07 (T+0), with the deadline at 16:07. The rehearsal
stopped at its stop condition, a bot passing `arena.validate` on the round's data.

**The bot to upload:** `python/bots/qminers/template.py` (56,222 bytes, under the 100 kB cap).
Its local result is 48,399 pips = **12,100 credits** over the three public sessions
(16,378 / 18,567 / 13,454 pips). By product: AURIC 2,700, BRISA 16,710, CORONA 31,707,
VANTA −2,718. These come from `uv run python -m arena.backtest python/bots/qminers/template.py all
--format qminers --data data/arena/round1 --queue prob --fee 1 --maker-fee 0 --mark touch`. The
portal's per-product, per-session PnL should be these × 0.25.

## Steps and clock times

| time | T+ | step |
|---|---|---|
| 15:07:49 | 0:00 | `date`; read `rules.md` in full, `example_bot.py`, RUNBOOK.md; listed the data |
| 15:08–15:09 | 0:01 | ON_THE_DAY.md's "Splitting the first hour", "The format swap", "Known so far" and "First hour" |
| 15:09:24 | 0:02 | **Step 1 done:** `data/arena/round1/HANDOVER.md` with what the rules settle, what they leave open, and ten contradictions with the repo's assumptions |
| 15:10–15:11 | 0:03 | read `drill.py`, `drill_exchange.py`, the engine's docstring and config; wrote `python/arena/formats/qminers.py` (about 230 lines) and registered it |
| 15:11:29 | 0:04 | `arena.diagnose all --suggest` ran on the first try (1 s): the loader works |
| 15:12:09–15:12:55 | 0:05 | **Step 3:** the bot, the drill template's DEFAULTS/STRATEGY/EXECUTION with a new header, PARAMS (from `--suggest`, plus take_edge 2 for the fee) and ADAPTER (about 150 lines); first backtest ran: 16,378 pips on session 0 |
| 15:13:01 | 0:05 | **Step 4's first sentence:** `arena.validate ... --time-limit-ms 50 --max-size 100KB`: Result OK (9 s) |
| 15:13:28 | 0:06 | `experiments.premise` crashed (`KeyError: 'arena_bot_template'`): the wrapper must import the bot in `load_bot`. Fixed |
| 15:13:38 | 0:06 | **Step 2 done:** premise (20 s): AURIC, BRISA, CORONA Prosperity-like, VANTA mixed |
| 15:14:05 | 0:06 | `experiments.structure` (2 s) |
| 15:14:16 | 0:07 | backtest on all three sessions, and with VANTA's quotes off |
| 15:15–15:16 | 0:08 | answers under ON_THE_DAY.md's First-hour items; IDEAS.md rows; three TODO.md items |
| 15:16 | 0:09 | re-validated after the plug-in fix, while pytest ran: **FAIL**, slowest call 61.8 ms against the 50 ms limit (mean 0.13, p99 0.34) |
| 15:20 | 0:13 | pytest: 493 passed, 32 skipped (6 min, slowed by the parallel runs); re-validated alone: **Result OK**, slowest 40.6 ms; the slow call is a GC pause (item 6 below) |

## What slowed me down

- **Permission prompts on shell idioms, about 5 minutes lost in total:** `$(...)`, `$?`, `find -exec`,
  `sleep`, `sed -i` on a file outside the worktree, a heredoc with f-string braces, and a `;`
  chain all needed approval or were blocked. Two background runs never started, so
  `experiments.structure` ran 3 minutes later than planned, and `results/r1/` was never created
  because its `mkdir` sat in a blocked command. On the day, write helper scripts to a file and
  run them, and keep each Bash call to one command.
- **The ON_THE_DAY.md First-hour section is long** (112 lines, each item with priors and branches).
  Reading it in full cost about 2 minutes. When the rules answer an item outright, most of its text
  doesn't apply.
- **IDEAS.md's rows are single table lines of up to 4,000 characters.** Appending a result means
  matching an exact anchor inside them. One anchor appeared twice and the script failed once.

## What in the repo's docs or tools was missing, wrong or misleading

1. **A format can't carry the engine settings its rules fix.** The rules settle the queue (`prob`),
   the fee (1 pip a lot for takers, `--maker-fee 0`) and the mark (`touch`), but only `RESTING`
   can live in the plug-in. Every command needs four extra flags, and a missing flag silently
   gives another PnL (TODO.md, "A format sets the engine settings its rules imply").
2. **`experiments.premise` takes no `--fee`, `--mark` or `--queue`,** so its "PnL as recorded"
   (VANTA +63,696) disagrees in sign with the backtest under the rules (VANTA −2,718). Its verdict
   rests on that PnL. The RUNBOOK sends you to it as round 1's first check without saying so.
3. **Undocumented: `load_bot` must import the bot at once.** `arena.cli.bot_module` reads the module
   that `BotFile.load` registers. Neither `formats/__init__.py` nor "The format swap, step by
   step" says so, and the error (`KeyError: 'arena_bot_template'`) doesn't point at the cause
   (TODO.md item).
4. **The engine has no action cap of the rules' kind:** `--max-orders` counts new orders only, while
   the rules cap all actions (pulls included) at 10 a call, and posts at 4 resting a product. The
   plug-in enforces both. `validate`'s "most orders in a tick 15" counts the engine's Cancels after
   a `pull_all` expands, which reads like a breach of the cap and isn't one.
5. **The engine's limit rule in resting mode rejects all of a tick's new orders for the product**
   (`engine.py` docstring). The rules reject only the offending order, so the plug-in applies their
   check first. The swap guide doesn't mention this case.
6. **`arena.validate`'s timing check measures the backtester's garbage collector.** The same file
   passed at 15.6 ms, failed at 61.8 ms while pytest ran, and passed at 40.6 ms idle. Per session,
   one call takes 70–91 ms, at a different step each time (4,467, 6,113, 5,636), and every other
   call is under 1 ms. With `gc.disable()` the slowest call is 2.5 ms. So the pause is a full
   collection over the engine's own objects in the same process, not the bot's work. One spike
   FAILs the whole validate, though the rules only discard that step's actions. Read the p99,
   and see TODO.md, "`arena.validate`'s time check counts the backtester's GC pauses".
7. **The rules' title says "Round 3 Technical Rules"** on round 1's file (HANDOVER.md, contradiction 9).
8. **The crossing-fill tape** differs by a tick between the rules (the volume comes off line n's
   tape) and the engine (off the tick's trades, line n+1's under the loader's mapping): a small
   modelling difference, noted in HANDOVER.md.
9. **The drill swap guide's "step × 100" timestamp mapping** fits a 10,000-step day. For 7,200 steps,
   `n × 1,000,000 // steps` keeps `flatten_from` on the template's scale. The guide says to map the
   session onto 0..999,900, and the parenthesis about the dry run's choice misleads on another
   length.
10. **`arena.validate`'s size cap reads `100KB` as 99,950 bytes,** not 100,000 or 102,400. That is
    harmless at 56 KB, but the margin isn't explained in its output.

## Not done (the rehearsal stopped at the validated bot)

- Step 4's calibration against the portal's metrics and E (no portal), and steps 5–6.
- The leads for step 5 are in HANDOVER.md "Status". VANTA's quotes lose under the rules'
  settings and gain in-sample with `make_size` 0 (+55 against −2,718), which a held-out grid has to
  confirm. Premise's move gate (`gate_move`) is for VANTA, and the fee-aware `take_edge` and
  `clear_edge` are to be gridded on the 1-pip products.
- "Is the data a real series in disguise?": needs the user's approval and a budget.
