"""The Rust port (rust/) from Python: building it, exporting days for it, and running backtests on it.

rust/ ports arena/engine.py and some bots, each with its Python twin listed in rust/twins.json
(rust/README.md has the table of what is in which language). This module is the bridge:

  export_day    a Day as rust/src/dayfile.rs reads it (the format plug-ins stay in Python)
  bot_spec      a twin bot for Rust: its kind, and its Python file's globals after any --set
                overrides, so the Rust bot reads the same settings (the template's DEFAULTS and
                PARAMS, a rival's constants)
  run_batch     `arena-rs batch`: many backtests on every core, each returning what arena.grid's
                Piece holds (arena.grid --engine rust)
  stale_twins   the twins whose Python file changed since the Rust port was last checked against it

Standard library only, like the rest of arena/ outside analysis.py. Nothing here is needed unless
a tool is asked for the Rust engine.
"""

from __future__ import annotations

import functools
import hashlib
import json
import shutil
import subprocess
from dataclasses import fields
from pathlib import Path

from arena.botfile import BotFile
from arena.engine import EngineConfig
from arena.formats import prosperity
from arena.model import Day

ROOT = Path(__file__).resolve().parent.parent
RUST = ROOT / "rust"
BINARY = RUST / "target" / "release" / "arena-rs"
TWINS = RUST / "twins.json"


def build() -> None:
    """Builds the release binary (cargo skips it when nothing changed)."""
    if shutil.which("cargo") is None:
        raise RuntimeError("the Rust engine needs cargo (brew install rust), see rust/README.md")
    subprocess.run(["cargo", "build", "--release", "--quiet", "--manifest-path", str(RUST / "Cargo.toml")], check=True)


# ---------------------------------------------------------------------------- twins


def twins() -> dict[str, dict]:
    """rust/twins.json: each Python file with a Rust port, by its path from the repo root."""
    return json.loads(TWINS.read_text())


@functools.lru_cache(maxsize=None)
def _kinds() -> dict[str, str]:
    return {path: twin["kind"] for path, twin in twins().items() if "kind" in twin}


def file_hash(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def stale_twins() -> list[str]:
    """The twins whose Python file isn't the one their Rust port was last checked against."""
    return [path for path, twin in twins().items() if file_hash(path) != twin["sha256"]]


def record_hashes() -> None:
    """Writes each twin's current hash: run only after the parity check passed (experiments/rust_bench.py --record)."""
    table = twins()
    for path, twin in table.items():
        twin["sha256"] = file_hash(path)
    TWINS.write_text(json.dumps(table, indent=2) + "\n")


def kind_of(path: Path) -> str:
    """The Rust bot kind of a bot file, or a ValueError naming the bots that have one."""
    try:
        relative = Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        relative = str(path)
    kinds = _kinds()
    if relative not in kinds:
        raise ValueError(f"{path} has no Rust twin (bots with one: {', '.join(kinds)})")
    return kinds[relative]


# ---------------------------------------------------------------------------- bots


def _jsonable(value) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_jsonable(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _jsonable(v) for k, v in value.items())
    return False


@functools.lru_cache(maxsize=None)
def _bot_file(path: Path) -> BotFile:
    return BotFile(path, {"datamodel": prosperity.dm}, strict=False)


def bot_globals(path: Path, overrides: dict[str, object]) -> dict:
    """The bot file's upper-case globals that JSON can hold, after the overrides: what its Rust
    twin reads its settings from."""
    module = _bot_file(Path(path).resolve()).load(overrides)
    return {name: value for name, value in vars(module).items() if name.isupper() and not name.startswith("_") and _jsonable(value)}


def bot_spec(path: Path, overrides: dict[str, object], requote: bool = False) -> dict:
    return {"kind": kind_of(path), "globals": bot_globals(path, overrides), "requote": requote}


def config_json(config: EngineConfig) -> dict:
    return {f.name: (str(getattr(config, f.name)) if f.name in ("trade_matching", "queue") else getattr(config, f.name)) for f in fields(config)}


# ---------------------------------------------------------------------------- days


def _whole(price) -> int:
    if price != int(price):
        raise ValueError(f"the Rust engine takes whole prices, got {price}")
    return int(price)


def _name(text: str) -> str:
    if not text.isprintable() or text != text.strip():
        raise ValueError(f"a trader name in a day file is one printable line, without leading or trailing spaces: {text!r}")
    return text


def export_day(day: Day, path: Path) -> None:
    """Writes the day in rust/src/dayfile.rs's format: products sorted by name plus the day's own
    order, trader names by first appearance, each tick's books in its dict order."""
    products = sorted(day.products)
    index = {p: k for k, p in enumerate(products)}
    names = {"": 0}
    for tick in day.ticks:
        for trades in tick.trades.values():
            for t in trades:
                names.setdefault(_name(t.buyer), len(names))
                names.setdefault(_name(t.seller), len(names))
    lines = ["arena-day 2", f"name {day.name}", f"products {len(products)}", *(f"{p} {day.limits[p]}" for p in products),
             "order" + "".join(f" {index[p]}" for p in day.products), f"names {len(names)}", *names, f"ticks {len(day.ticks)}"]
    side = lambda levels: f"{len(levels)}" + "".join(f" {_whole(price)} {volume}" for price, volume in levels)
    for tick in day.ticks:
        trades = [t for p in tick.trades for t in tick.trades[p]]
        lines.append(f"t {tick.timestamp} {len(tick.books)} {len(trades)} {len(tick.marks)}")
        lines += [f"b {index[p]} {side(book.bids)} {side(book.asks)}" for p, book in tick.books.items()]
        lines += [f"x {index[t.product]} {_whole(t.price)} {t.quantity} {names[t.buyer]} {names[t.seller]} {t.timestamp}" for t in trades]
        lines += [f"m {index[p]} {float(mark)!r}" for p, mark in tick.marks.items()]
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------- batches


def run_batch(day_paths: list[Path], specs: list[dict], tasks: list[dict], threads: int, scratch: Path) -> list[dict]:
    """`arena-rs batch`: each task {day, config, bots: [[name, spec index], ...], blocks, fine} on
    `threads` threads, returning per task the first participant's {pnl, blocks, fine, products,
    fills, errors, breaches, first_error}, in task order."""
    path = scratch / "batch.json"
    path.write_text(json.dumps({"days": [str(p) for p in day_paths], "bots": specs, "tasks": tasks}))
    out = subprocess.run([str(BINARY), "batch", str(path), "--threads", str(threads)], stdout=subprocess.PIPE, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"arena-rs batch failed (exit {out.returncode}); its message is above")
    return [json.loads(line) for line in out.stdout.splitlines()]
