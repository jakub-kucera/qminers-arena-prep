# The LLM zoo

Bots written by language models that have seen nothing but a Prosperity-style spec
(`SPEC.md`) and one prompt (`PROMPTS.md`). Most teams at the Arena will hand the
organisers' docs to a model, and Qminers' own 2024 LLM baseline came second. So these bots are
(1) the baseline the template must beat and (2) a population of rivals for `--vs`
(`references/wiki/concepts/harder-rounds.md`, D2). Results: `IDEAS.md`, "The LLM zoo".

## Layout

```
python/bots/zoo/
  SPEC.md          the spec every model gets, unchanged (P3 round 1's products, Prosperity's API)
  PROMPTS.md       one prompt per archetype: baseline, market_maker, mean_reversion, momentum
  bundle.py        prints SPEC.md + one prompt as a single message
  LOCAL_MODELS.md  serving local models with llama.cpp: an offline fallback, not the field
  claude/          written by fresh Claude agents (no repo context)
  gemini/          paste here what Gemini writes
  chatgpt/         ... ChatGPT / OpenAI models, older ones included
  other/           ... any other provider (Mistral, DeepSeek, Grok, Llama, ...)
```

File names: `<provider folder>/<model>_<prompt>.py`, the model as the provider names it, e.g.
`gemini/gemini-2.5-pro_baseline.py`, `chatgpt/gpt-4o_market_maker.py`, `chatgpt/o3_momentum.py`.
Add a second run of the same pair as `..._baseline_2.py`.

## Running a model cleanly

The point is to see what a model does **on its own**, the way a team's first attempt would look.
So for each (model, prompt):

1. **A fresh conversation.** A new chat, or a temporary / incognito chat where the app has one
   (ChatGPT: Temporary Chat; Gemini: a new chat with Gems off).
2. **Nothing else in context.** Turn off memory and custom instructions (ChatGPT: Settings →
   Personalization; Gemini: Saved info / Gems). No uploaded files, no system prompt in an API
   playground, no web search or canvas tools. Code execution off if the app lets you choose.
3. **One message.** `python3 python/bots/zoo/bundle.py <prompt> | pbcopy`, paste, send. Default
   settings (temperature, thinking or reasoning level): note them if you change any.
4. **Take the first answer.** Copy the code block into `<folder>/<model>_<prompt>.py`, as it is.
   Don't fix it by hand.
5. **One repair turn at most.** Run `uv run python -m arena.validate <file> 1 --allow numpy,pandas`. If it fails
   because the file doesn't run (syntax error, wrong return type, an import that isn't allowed),
   reply once in the same chat with just the error message, and save the new answer over the
   file. Record that in the table below. Don't repair a bot that runs but loses money: that is
   the result.
6. **Add a row to the table below** and run `uv run python -m experiments.study.zoo`.
7. **Give it a Rust twin** at the same path under `rust/src/` (`rust/src/bots/zoo/<provider>/<name>.rs`, a line-by-line translation, declared in `rust/src/bots/zoo/mod.rs`; `rust/README.md`, "Keeping it in step"), so the field runs in Rust too. `python/tests/test_rust.py` fails until it has one.

Which models: Gemini (Gemini 4, and an older one such as 2.5 Pro), and ChatGPT, current and
older (GPT-4o, o3, GPT-4.1, ...). Older models matter: some
teams will use whatever is free. Then all four prompts for the strongest of each, `baseline` for
the rest.

Local models (`local.py`) aren't on that list: no team will code with them. Their twenty bots stay, and
`experiments.study.zoo` leaves them out of the field unless `--local`.

## The bots

| File | Provider | Model | Date | Prompt | Repair turn | Notes |
|---|---|---|---|---|---|---|
| `chatgpt/gpt-5-6-luna_baseline.py` | OpenAI, ChatGPT, run by hand | GPT-5.6 Luna | 2026-10-15 | baseline | not recorded | the best-level weighted mid smoothed by a fast/slow EMA blend, fixed 10,000 for Resin, a momentum-tilted fair for Squid Ink; quotes 6-8 lots |
| `gemini/gemini-3-8-flash-high_baseline.py` | Google, Gemini app, run by hand | Gemini 3.8 Flash, thinking high | 2026-10-15 | baseline | not recorded | a hard-coded Resin ladder around 10,000; Kelp at 0.6 × weighted mid + 0.4 × its EMA; Squid Ink trend-following (EMA crossover, 3-tick return, whole-book imbalance) that crosses the spread on a strong signal |
| `other/gpt-oss-120B_baseline.py` | OpenAI's open-weight model, run by hand | gpt-oss-120B | 2026-10-15 | baseline | not recorded | no fair value: joins the best bid and ask with 10 lots on every product, keeps no state |
| `chatgpt/gpt-5-6-luna_market_maker.py` | OpenAI, ChatGPT, run by hand | GPT-5.6 Luna | 2026-10-15 | market_maker | not recorded | an EMA of the mid plus a momentum term, fixed 10,000 for Resin; quotes a fixed 1-2 ticks from fair (no pennying), 8-10 lots, linear skew |
| `gemini/gemini-3-8-flash-high_market_maker.py` | Google, Gemini app, run by hand | Gemini 3.8 Flash, thinking high | 2026-10-15 | market_maker | not recorded | a weighted mid and EMA blend for Kelp and Squid Ink, a Resin ladder around 10,000 stepped by position; takes, then pennies with all remaining room |
| `other/gpt-oss-120B_market_maker.py` | OpenAI's open-weight model, run by hand | gpt-oss-120B | 2026-10-15 | market_maker | not recorded | a 20-tick average of the mid on every product (no 10,000 for Resin); quotes 2 from it only inside the best. Fails `arena.validate`: takes and quotes share the same room, so 10,280 ticks breach a limit and lose all their orders. Kept as is (it runs; the breach is the result) |
| `claude/haiku-5.5_baseline.py` | Anthropic, a fresh agent told not to read the repo | Claude Haiku 5.5 | 2026-10-15 | baseline | none | fixed 10,000 for Resin, a slow EMA of the mid elsewhere |
| `claude/opus-5.5_baseline.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | baseline | none | wall mid, take / clear / penny, fixed 10,000 for Resin |
| `claude/opus-5.5_market_maker.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | market_maker | none | wall mid, take / clear / penny or join, fixed 10,000 for Resin |
| `claude/opus-5.5_mean_reversion.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | mean_reversion | none | market making on Resin and Kelp, a z-score bet (entry 2.2 sd) on Squid Ink |
| `claude/opus-5.5_momentum.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | momentum | none | an EMA crossover in sds of a random walk; never reaches its entry on P3, so it never trades |
| `claude/sonnet-5.5_baseline.py` | Anthropic, a fresh agent told not to read the repo | Claude Sonnet 5.5 | 2026-10-15 | baseline | none | wall mid, take / penny, fixed 10,000 for Resin |
| `other/qwen3.8-27b-medium_baseline.py` | Qwen, local (`local.py`, llama.cpp) | qwen3.8:27b Q4_K_M, reasoning effort medium | 2026-10-17 | baseline | none | a pure taker: momentum, trend, book imbalance, trade flow and a z-score summed per tick; above 0.4 it crosses the spread with 2–10 lots. No fair value, never quotes |
| `other/qwen3.8-27b-medium_baseline_2.py` | Qwen, local | qwen3.8:27b, effort medium | 2026-10-17 | baseline | none | a taker again: a volatility-scaled blend of mean reversion and momentum sets a target position, reached by crossing the spread (numpy) |
| `other/qwen3.8-27b-medium_market_maker.py` | Qwen, local | qwen3.8:27b, effort medium | 2026-10-17 | market_maker | none | a slow EMA of the mid as fair (no 10,000 for Resin); joins the best bid and ask (no pennying) with 3–8 lots, takes only 4–6 ticks through fair, stops adding past 60% of the limit |
| `other/gemma4-26b_baseline.py` | Google, local | gemma4:26b Q4_K_M, thinking on (default) | 2026-10-17 | baseline | none | passive only: Kelp buys at the bid / sells at the ask beyond 1.5 sd of its mean, Squid Ink follows an EMA, Resin only flattens a position it never opens |
| `other/gemma4-26b_baseline_2.py` | Google, local | gemma4:26b | 2026-10-17 | baseline | none | flips between the full limits by crossing the spread: an SMA crossover on Kelp, a 1.5-sd z-score on Squid Ink |
| `other/gemma4-26b_market_maker.py` | Google, local | gemma4:26b | 2026-10-17 | market_maker | none | "Avellaneda-Stoikov style": a fixed spread around the mean of the history, skewed by position, quoting one side only when not flat |
| `other/gemma4-26b_market_maker_2.py` | Google, local | gemma4:26b | 2026-10-17 | market_maker | none | an EMA fair with a units bug: the inventory skew is `pos × mid × 0.001`, 10 ticks a lot on Resin, so each fill swings its quotes far through the book |
| `other/gpt-oss-20b_baseline.py` | OpenAI's open-weight model, local | gpt-oss:20b MXFP4, reasoning effort medium (default) | 2026-10-17 | baseline | none | buys 1 at the ask and sells 1 at the bid every tick: pays the spread for nothing |
| `other/gpt-oss-20b_baseline_2.py` | OpenAI's open-weight model, local | gpt-oss:20b | 2026-10-17 | baseline | none | never trades: it stores this tick's mid before reading the last one, so its momentum is always 0 |
| `other/gpt-oss-20b_market_maker.py` | OpenAI's open-weight model, local | gpt-oss:20b | 2026-10-17 | market_maker | none | when flat, bids at the best ask and asks at the best bid (crossing both ways, 5 lots). The reply's channel markers were garbled; the file is its final answer, not the draft in its thinking |
| `other/gpt-oss-20b_market_maker_2.py` | OpenAI's open-weight model, local | gpt-oss:20b | 2026-10-17 | market_maker | none | a fixed spread around the integer mid, 1 order a side, stops adding past ±20 |
| `other/qwen3.8-27b-medium_market_maker_2.py` | Qwen, local | qwen3.8:27b, effort medium | 2026-10-18 | market_maker | none | an exponential average of the last 30 mids plus a momentum term; quotes half the spread from it, skewed by position, 4–6 lots; takes 4–6 ticks through fair; leans out of its position over the day's last 10% |
| `other/phi4-14b_baseline.py` | Microsoft, local | phi4:14b Q4_K_M (no thinking) | 2026-10-18 | baseline | yes: the first answer called `json.loads` on the empty first `traderData` | keeps its positions in its own state and never updates them, so it bids 10 lots at the lowest bid level on Resin until it breaches (50,244 orders cancelled); its Kelp and Squid Ink "mid" adds the best levels' volumes, not prices. Fails `arena.validate` on the breaches; kept |
| `other/phi4-14b_baseline_2.py` | Microsoft, local | phi4:14b | 2026-10-18 | baseline | none | holds +10 Resin bid at the lowest bid level, a Kelp "trend" against a running high and low that rarely triggers, Squid Ink only on a crossed book; position from unsigned trade quantities. Barely trades |
| `other/phi4-14b_market_maker.py` | Microsoft, local | phi4:14b | 2026-10-18 | market_maker | none | fair = the mid averaged with the last fair, quotes 1 either side with 10 lots; the ask's size is \|position\|, so it sells only what it holds |
| `other/phi4-14b_market_maker_2.py` | Microsoft, local | phi4:14b | 2026-10-18 | market_maker | none | quotes 1 either side of fixed fairs copied from the spec's example (Resin 10,000, Kelp 2,030, Squid Ink 1,969); its inventory counts unsigned trade quantities and its skew moves both quotes toward each other. Barely trades |
| `other/deepseek-r1-14b_baseline.py` | DeepSeek, local | deepseek-r1:14b Q4_K_M (a Qwen2.5 distill, thinking) | 2026-10-18 | baseline | yes: `NameError: name 'Order' is not defined` every tick | the repair answer leaves out the `datamodel` import again, so it still errors on every tick and never trades. Fails `arena.validate`; kept |
| `other/deepseek-r1-14b_baseline_2.py` | DeepSeek, local | deepseek-r1:14b | 2026-10-18 | baseline | none | long only: when the mid is above its 3-tick average it takes the whole best ask, when below it sells the whole best bid back. Loses 2.2 million |
| `other/deepseek-r1-14b_market_maker.py` | DeepSeek, local | deepseek-r1:14b | 2026-10-18 | market_maker | none | 1 lot at the mid rounded down and up, only where that is inside the best quote; no fair beyond the mid, no state |
| `other/deepseek-r1-14b_market_maker_2.py` | DeepSeek, local | deepseek-r1:14b | 2026-10-18 | market_maker | none | its whole room on each side at the mid ∓ 1 (rounded down); no fair beyond the mid, no skew |

The two repair turns of 2026-10-18 were first sent without the traceback (a bug in `local.py`, since fixed) and were then redone from the same first answer. The `.json` keeps the first attempt under `repair_without_traceback`.
