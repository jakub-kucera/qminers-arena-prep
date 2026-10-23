# Local models with llama.cpp

How to run the zoo's prompts on a model served on the laptop (`TODO_DONE.md`, "(a, part 3)";
`ON_THE_DAY.md`, "The round's zoo"). Measured on the M4 Max with 36 GB, 2026-10-17, llama.cpp
build 11669.

**On the day, use gemma4:26b only, and only if the hosted chats can't be reached.** No team will code
the challenge with a 14–27B model, so local bots don't look like the field; they are an offline
baseline. gemma4 writes a bot in 3–4 minutes and its replies parse cleanly. gpt-oss:20b is faster but
garbles its channel markers, qwen3.8 takes 20–30 minutes, and phi4 and deepseek-r1 added nothing over
them (`IDEAS.md`, "The LLM zoo"). The twenty local bots already made stay in the zoo, but
`experiments.zoo` leaves them out of the field unless `--local`. The other four models are documented
below as measured.

## Install

```sh
brew install llama.cpp      # llama-server, llama-cli, llama-bench
```

## Models

The GGUF files came from Ollama (`ollama pull <model>`), which stores them under hashed names in
`~/.ollama/models/blobs/`. Hard-link them to readable names. A hard link takes no extra space
and survives `ollama rm`.

```sh
mkdir -p ~/models
for m in gemma4:26b gpt-oss:20b qwen3.8:27b phi4:14b deepseek-r1:14b; do
  ln -f "$(ollama show --modelfile $m | awk '/^FROM /{print $2; exit}')" ~/models/${m/:/-}.gguf
done
```

All five are Q4_K_M, except gpt-oss (MXFP4, which `llama-bench` labels "unknown, may not work"; it
runs). Token-generation speed is set by how many weights each token reads. The MoE models read
only the experts they use, so they are 3–4 times faster than dense models of their size.

| File | Type | Size | Prompt reading, tok/s (`pp512`) | Writing, tok/s (`tg128`) | Ollama eval rate |
|---|---|---|---|---|---|
| `gpt-oss-20b.gguf` | MoE, ~3.6B active | 12.8 GiB | 1,392 | 79.2 | 40.3 |
| `gemma4-26b.gguf` | MoE, 8 of 128 experts | 15.9 GiB | 1,244 | 75.7 | 57.9 |
| `phi4-14b.gguf` | dense | 8.4 GiB | 312 | 32.2 | 33.3 |
| `deepseek-r1-14b.gguf` | dense (a Qwen2.5 distill) | 8.4 GiB | 330 | 28.3 | 20.1 |
| `qwen3.8-27b.gguf` | dense, hybrid linear attention | 15.7 GiB | 181 | 18.2 | 9.8 |

`llama-bench` runs at an empty context, which makes its numbers a best case. As the context grows,
gemma4:26b slows, with a step between 16k and 32k
(`llama-bench -fa 1 -p 2048 -n 128 -d 0,8192,16384,32768,49152,65536 -r 2`):

| Context already filled | 0 | 8k | 16k | 32k | 49k | 65k |
|---|---|---|---|---|---|---|
| Reading 2k more, tok/s | 1,211 | 808 | 606 | 272 | 211 | 175 |
| Writing, tok/s | 74.7 | 65.4 | 63.6 | 26.8 | 35.4 | 29.8 |

The 32k row was noisy (± 29 on reading). Through the server, with swap in use, reading near 65k fell
to 90–100 tok/s.

## Serving a model for the zoo

```sh
llama-server -m ~/models/gemma4-26b.gguf -c 32768 -np 1 --jinja --port 8080
curl -s localhost:8080/health          # {"status":"ok"} once the model is loaded
```

- **Sampling:** each model's recommended settings, taken from Ollama's parameters for it (`ollama show --parameters <model>`). Add them to the command; `local.py` sends none and records what the server used:
  - qwen3.8-27b: `--temp 1 --top-k 20 --top-p 0.95 --min-p 0 --presence-penalty 0 --repeat-penalty 1`
  - gemma4-26b: `--temp 1 --top-k 64 --top-p 0.95`
  - gpt-oss-20b: `--temp 1`
  - phi4-14b, deepseek-r1-14b: llama.cpp's defaults (Ollama sets only stop tokens, which the chat template already has).
- **API:** OpenAI-compatible at `http://localhost:8080/v1/chat/completions`, and Anthropic's
  Messages API at `/v1/messages`. The `model` field is ignored: the server answers with the one
  model it loaded.
- **`--jinja`:** uses the model's own chat template. The model's thinking comes back apart from the
  answer, as `reasoning_content` next to `content`. Keep both, and take the bot from `content`.
- **`-c 32768`:** the zoo prompt (`bundle.py baseline`) is 1,882 tokens for gemma4. The rest of the
  window is room for the thinking and the bot.
- **`-np 1`:** one slot that owns the whole context. With the default 4 slots, the slots share one
  context, so a half-finished prompt can leave too little room to restore the cached conversation,
  and a small request waits behind a large one.
- **Memory:** a loaded model holds its file size plus its context. Stop the server (Ctrl-C) before
  a memory-heavy grid.
- **One server per port:** a second `llama-server` on a port already in use exits, and requests
  still reach the first one, whatever model that one has loaded. Check with `pgrep -fl llama-server`.

## Writing zoo bots

With the server up: `uv run python python/bots/zoo/local.py <prompt> [--n N] [--effort LEVEL]`. It writes
`other/<model>_<prompt>.py` and a `.json` beside it; its docstring has the protocol. Then add the
README row and run `experiments.zoo`.

Time per bot, both turns where there was a repair (2026-10-17 and 18, `-c 32768`; phi4 at `-c 16384`, its
trained context):

| Model | Time | Tokens written |
|---|---|---|
| phi4-14b (no thinking) | 24–73 s | 0.8–2.3k |
| gpt-oss-20b | 38–146 s | 2.1–8.4k |
| gemma4-26b | 192–254 s | 10–13.5k |
| deepseek-r1-14b | 7.5–13 min | 10–14k |
| qwen3.8-27b, `--effort medium` | 19–29 min | 13–21k |

What the batches found:
- **The repair turn sends the validator's FAIL lines with the traceback under them.** Without the
  traceback a model gets "30000 errors in 30,000 ticks" and nothing to fix: deepseek-r1 answered
  with debugging advice and no code.
- **Qwen3.8's chat template defaults to `reasoning_effort` xhigh,** while Ollama runs it at medium. At
  xhigh it wrote 28k tokens of thinking in 40 minutes without an answer, close to the context's end,
  and was stopped. Use `--effort medium`. The effort goes into the bot's name.
- **gpt-oss garbles its channel markers** (`<|channel|>final code block>`), so llama-server leaves its
  thinking in `content`, with drafts of the code. `local.py` takes the answer after the first
  `<|start|>assistant`.
- **A finished bot can be a disaster.** Of the 20 bots, 18 passed `arena.validate`, and four of those lost
  0.6–2.2 million on P3 round 1 (`IDEAS.md`, "The LLM zoo"). Each sample is one draw: take two or more.

## Chatting and benchmarking

```sh
llama-cli -m ~/models/gemma4-26b.gguf -c 32768         # chat in the terminal
open http://localhost:8080                              # or the server's web chat
llama-bench -m ~/models/gemma4-26b.gguf -fa 1           # pp512 and tg128, 5 runs each
llama-bench -m ~/models/gemma4-26b.gguf -fa 1 -p 0 -d 0,16384   # writing speed at an empty and a 16k context
```

## Not as a coding agent

Claude Code runs against the server's Anthropic endpoint (`ANTHROPIC_BASE_URL=http://localhost:8080
ANTHROPIC_AUTH_TOKEN=none ANTHROPIC_MODEL=gemma4 CLAUDE_CODE_MAX_CONTEXT_TOKENS=131072 claude`),
and it called tools correctly. In this repo, though, its first request was 69k tokens and took
gemma4 4.6 minutes to read. Some requests were then cancelled from the client side after about
60 s and retried from scratch. The zoo doesn't need an agent: one ~2k-token message is
the whole protocol.
