"""Writes zoo bots with a local model served by llama-server, following README.md's protocol.

    uv run python bots/zoo/local.py baseline                  # one bot from the loaded model
    uv run python bots/zoo/local.py market_maker --n 2        # two samples
    uv run python bots/zoo/local.py baseline --effort medium   # the chat template's reasoning_effort
    uv run python bots/zoo/local.py baseline --url http://localhost:8081/v1

LOCAL_MODELS.md has the server setup. The model is the one the server loaded: its file name,
without `.gguf`, names the bot (`other/<model>_<prompt>.py`, then `_2`, `_3`, ...). Sampling is
the server's (set it on the llama-server command line); the script sends none.

Each sample: SPEC.md and the prompt as the only message, no system prompt; the first Python code
block of the answer saved unchanged; `arena.validate` on P3 round 1. If the file doesn't run
(syntax, entry point, imports, loading, exceptions), one repair turn in the same conversation with
just the error, and its answer saved over the file. A bot that runs but breaches limits or loses
money is the result. Everything (both turns' answers and thinking, the server's settings, token
counts, timings, the validator's output) goes to a `.json` beside the bot.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

from bundle import bundle, prompts

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = HERE / "other"

# The validator's failures that mean the file doesn't run, as README.md's step 5 lists them.
NOT_RUNNING = ("syntax error", "entry point", "imports outside", "bot failed to load", "errors in")


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def chat(url: str, messages: list[dict], effort: str | None) -> dict:
    body = {"messages": messages}
    if effort:
        body["chat_template_kwargs"] = {"reasoning_effort": effort}
    request = urllib.request.Request(
        f"{url}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=4 * 3600) as response:
        reply = json.load(response)
    message = reply["choices"][0]["message"]
    return {
        "content": message.get("content") or "",
        "reasoning_content": message.get("reasoning_content") or "",
        "finish_reason": reply["choices"][0].get("finish_reason"),
        "usage": reply.get("usage"),
        "timings": reply.get("timings"),
        "seconds": round(time.monotonic() - start, 1),
    }


def code_block(text: str) -> str | None:
    """The answer's first Python code block.

    gpt-oss can garble its channel markers (`<|channel|>final code block>`), and llama-server then
    leaves its thinking in `content`: the answer is what follows the first `<|start|>assistant`,
    sometimes without a code fence after a last `<|message|>`.
    """
    if "<|start|>assistant" in text:
        text = text[text.index("<|start|>assistant"):]
        match = re.search(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.DOTALL)
        if match is None and "<|message|>" in text:
            return text[text.rindex("<|message|>") + len("<|message|>"):].strip() + "\n"
    match = re.search(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.DOTALL)
    return match.group(1) if match else None


def validate(path: Path) -> tuple[str, list[str]]:
    """The validator's output, and its failures that mean the file doesn't run."""
    run = subprocess.run(
        [sys.executable, "-m", "arena.validate", str(path.relative_to(ROOT)), "1", "--allow", "numpy,pandas"],
        cwd=ROOT, capture_output=True, text=True,
    )
    output = run.stdout + run.stderr
    # Each FAIL line with the indented lines under it (the traceback), so a repair turn sees the error.
    failures, in_fail = [], False
    for line in output.splitlines():
        if line.strip().startswith("FAIL"):
            failures.append([line.strip()[len("FAIL"):].strip()])
            in_fail = True
        elif in_fail and line.startswith(" " * 8):
            failures[-1].append(line[8:].replace(f"{ROOT}/", ""))
        else:
            in_fail = False
    return output, ["\n".join(f) for f in failures if f[0].startswith(NOT_RUNNING) or " errors in " in f[0]]


def next_path(model: str, prompt: str) -> Path:
    path, n = OUT / f"{model}_{prompt}.py", 1
    while path.exists():
        n += 1
        path = OUT / f"{model}_{prompt}_{n}.py"
    return path


def sample(url: str, model: str, prompt: str, settings: dict, effort: str | None) -> dict:
    path = next_path(model, prompt)
    messages = [{"role": "user", "content": bundle(prompt)}]
    record = {"model": model, "prompt": prompt, "date": date.today().isoformat(), "file": path.name,
              "reasoning_effort": effort or "the chat template's default", "server": settings, "turns": []}

    turn = chat(url, messages, effort)
    record["turns"].append(turn)
    code = code_block(turn["content"])
    problems = ["no Python code block in the reply"] if code is None else []
    if code is not None:
        path.write_text(code)
        record["validate"], problems = validate(path)

    if problems:
        error = "\n".join(problems)
        messages += [{"role": "assistant", "content": turn["content"]}, {"role": "user", "content": error}]
        record["repair"] = error
        turn = chat(url, messages, effort)
        record["turns"].append(turn)
        code = code_block(turn["content"])
        if code is not None:
            path.write_text(code)
            record["validate"], problems = validate(path)
        else:
            record["validate"] = "no Python code block in the repair reply"

    if path.exists():
        path.with_suffix(".json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    else:
        (OUT / f"{path.stem}.failed.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(prog="local.py", description="Write zoo bots with the model llama-server has loaded.")
    parser.add_argument("prompt", choices=list(prompts()))
    parser.add_argument("--n", type=int, default=1, help="samples to write (default 1)")
    parser.add_argument("--url", default="http://localhost:8080/v1", help="the server's OpenAI-compatible API")
    parser.add_argument("--effort", help="the chat template's reasoning_effort (e.g. low, medium); added to the model's name")
    args = parser.parse_args()

    model = Path(get(f"{args.url}/models")["data"][0]["id"]).name.removesuffix(".gguf")
    if args.effort:
        model += f"-{args.effort}"
    props = get(args.url.removesuffix("/v1") + "/props")
    params = props.get("default_generation_settings", {}).get("params", {})
    keep = ("temperature", "top_k", "top_p", "min_p", "presence_penalty", "repeat_penalty", "n_predict", "seed")
    settings = {"model_path": props.get("model_path"), "n_ctx": props.get("default_generation_settings", {}).get("n_ctx"),
                "build": props.get("build_info"), **{k: params.get(k) for k in keep}}

    for _ in range(args.n):
        record = sample(args.url, model, args.prompt, settings, args.effort)
        last = record["turns"][-1]
        status = record["validate"].strip().splitlines()[-1] if record.get("validate") else "no code"
        print(f"{record['file']}: {sum(t['seconds'] for t in record['turns']):.0f} s, "
              f"{sum((t['usage'] or {}).get('completion_tokens', 0) for t in record['turns'])} tokens written, "
              f"repair: {'yes' if 'repair' in record else 'no'}, {status} ({last['finish_reason']})", flush=True)


if __name__ == "__main__":
    main()
