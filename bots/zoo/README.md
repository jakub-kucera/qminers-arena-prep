# The LLM zoo

Bots written by language models that have seen nothing but a Prosperity-style spec
(`SPEC.md`) and one prompt (`PROMPTS.md`). Most teams at the Arena will hand the
organisers' docs to a model, and Qminers' own 2024 LLM baseline came second. So these bots are
(1) the baseline the template must beat and (2) a population of rivals for `--vs`
(`references/wiki/concepts/harder-rounds.md`, D2). Results: `IDEAS.md`, "The LLM zoo".

## Layout

```
bots/zoo/
  SPEC.md          the spec every model gets, unchanged (P3 round 1's products, Prosperity's API)
  PROMPTS.md       one prompt per archetype: baseline, market_maker, mean_reversion, momentum
  bundle.py        prints SPEC.md + one prompt as a single message
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
3. **One message.** `python3 bots/zoo/bundle.py <prompt> | pbcopy`, paste, send. Default
   settings (temperature, thinking or reasoning level): note them if you change any.
4. **Take the first answer.** Copy the code block into `<folder>/<model>_<prompt>.py`, as it is.
   Don't fix it by hand.
5. **One repair turn at most.** Run `uv run python -m arena.validate <file> 1 --allow numpy,pandas`. If it fails
   because the file doesn't run (syntax error, wrong return type, an import that isn't allowed),
   reply once in the same chat with just the error message, and save the new answer over the
   file. Record that in the table below. Don't repair a bot that runs but loses money: that is
   the result.
6. **Add a row to the table below** and run `uv run python -m experiments.zoo`.

Which models: Gemini (Gemini 4, and an older one such as 2.5 Pro), and ChatGPT, current and
older (GPT-4o, o3, GPT-4.1, ...). Older models matter: some
teams will use whatever is free. Then all four prompts for the strongest of each, `baseline` for
the rest.

## The bots

| File | Provider | Model | Date | Prompt | Repair turn | Notes |
|---|---|---|---|---|---|---|
| `claude/haiku-5.5_baseline.py` | Anthropic, a fresh agent told not to read the repo | Claude Haiku 5.5 | 2026-10-15 | baseline | none | fixed 10,000 for Resin, a slow EMA of the mid elsewhere |
| `claude/opus-5.5_baseline.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | baseline | none | wall mid, take / clear / penny, fixed 10,000 for Resin |
| `claude/opus-5.5_market_maker.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | market_maker | none | wall mid, take / clear / penny or join, fixed 10,000 for Resin |
| `claude/opus-5.5_mean_reversion.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | mean_reversion | none | market making on Resin and Kelp, a z-score bet (entry 2.2 sd) on Squid Ink |
| `claude/opus-5.5_momentum.py` | Anthropic, a fresh agent told not to read the repo | Claude Opus 5.5 | 2026-10-15 | momentum | none | an EMA crossover in sds of a random walk; never reaches its entry on P3, so it never trades |
| `claude/sonnet-5.5_baseline.py` | Anthropic, a fresh agent told not to read the repo | Claude Sonnet 5.5 | 2026-10-15 | baseline | none | wall mid, take / penny, fixed 10,000 for Resin |
