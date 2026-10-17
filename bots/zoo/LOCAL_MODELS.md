# Local models with llama.cpp

How to run the zoo's prompts on a model served on the laptop (`TODO.md`, "(a, part 3)";
`ON_THE_DAY.md`, "The round's zoo"). Measured on the M4 Max with 36 GB, 2026-10-17, llama.cpp
build 11669.

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

`llama-bench` runs at an empty context, which makes its numbers a best case. At a 70k-token context,
gemma4 wrote at 19–28 tok/s instead of 76, and read the last chunks of a long prompt at about
120 tok/s.

## Serving a model for the zoo

```sh
llama-server -m ~/models/gemma4-26b.gguf -c 32768 -np 1 --jinja --port 8080
curl -s localhost:8080/health          # {"status":"ok"} once the model is loaded
```

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
